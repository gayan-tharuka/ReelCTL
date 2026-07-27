"""AI pipeline for media identification using Groq API.

Uses Llama 3.3 70B to understand poorly named media files. The AI never
performs filesystem operations — it only analyzes filenames and returns
structured metadata.

Filenames are batched (up to 50 per request) to minimize API calls.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from loguru import logger

from reelctl.config import Settings
from reelctl.models import AIResult, MediaType

# ── Constants ──────────────────────────────────────────────────────────────────

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a media file identification expert. Your job is to analyze media filenames and determine what movie or TV show they represent.

For each filename, determine:
- type: "movie" or "tv"
- title: The clean, official title of the media
- year: Release year (null if unknown)
- season: Season number (null if movie or unknown)
- episode: Episode number (null if movie or unknown)
- quality: Video quality (e.g., "4K", "2160p", "1080p", "720p", etc., null if unknown)
- source: Media source (e.g., "BluRay", "WEB-DL", "WEBRip", "HDRip", etc., null if unknown)
- confidence: Your confidence in the identification (0.0 to 1.0)

Rules:
1. Always use the OFFICIAL title (e.g., "Money Heist" not "La Casa de Papel" for the English title)
2. If a filename is completely unrecognizable (e.g., "movie.mp4"), set confidence very low (< 0.3)
3. Sample files (sample.mkv, SAMPLE_video.avi) should get confidence 0.0
4. Junk files that are not media should get confidence 0.0
5. Anime should be classified as "tv"

Respond with a JSON object containing a single key "results" which is an array of objects, one per filename. Each object must have all the fields listed above.

Example response:
{
  "results": [
    {
      "filename": "Avatar.2009.2160p.BluRay.x265.mkv",
      "type": "movie",
      "title": "Avatar",
      "year": 2009,
      "quality": "2160p",
      "source": "BluRay",
      "season": null,
      "episode": null,
      "confidence": 0.99
    }
  ]
}"""


# ── AI Client ──────────────────────────────────────────────────────────────────


async def identify_media_batch(
    filenames: list[str],
    settings: Settings,
) -> list[AIResult]:
    """Send a batch of filenames to Groq for AI identification.

    Args:
        filenames: List of filenames to identify (max ~50 recommended).
        settings: Application settings with API key.

    Returns:
        List of AIResult objects for each filename.
    """
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY not configured — skipping AI identification")
        return []

    if not filenames:
        return []

    # Build the user prompt
    file_list = "\n".join(f"- {fn}" for fn in filenames)
    user_prompt = f"Identify the following {len(filenames)} media files:\n\n{file_list}"

    logger.info("Sending {} filenames to Groq AI for identification", len(filenames))
    logger.debug("Filenames: {}", filenames)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.groq_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                    "max_tokens": 4096,
                },
            )

            if response.status_code == 429:
                logger.warning("Groq rate limit hit — waiting before retry")
                raise RateLimitError("Groq API rate limit exceeded")

            response.raise_for_status()
            data = response.json()

        return _parse_ai_response(data, filenames)

    except httpx.HTTPStatusError as e:
        logger.error("Groq API error: {} {}", e.response.status_code, e.response.text)
        return []
    except httpx.RequestError as e:
        logger.error("Groq API request failed: {}", e)
        return []
    except Exception as e:
        logger.error("Unexpected error in AI pipeline: {}", e)
        return []


async def identify_media(
    filenames: list[str],
    settings: Settings,
) -> list[AIResult]:
    """Identify media files using AI, automatically batching large lists.

    Splits filenames into batches of `settings.ai_batch_size` and processes
    them sequentially to respect rate limits.

    Args:
        filenames: All filenames to identify.
        settings: Application settings.

    Returns:
        Combined list of AIResult objects.
    """
    if not filenames:
        return []

    all_results: list[AIResult] = []
    batch_size = settings.ai_batch_size

    for i in range(0, len(filenames), batch_size):
        batch = filenames[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(filenames) + batch_size - 1) // batch_size

        logger.info("Processing AI batch {}/{} ({} files)", batch_num, total_batches, len(batch))

        results = await identify_media_batch(batch, settings)
        all_results.extend(results)

    logger.info("AI identification complete: {} results from {} files", len(all_results), len(filenames))
    return all_results


# ── Response Parsing ───────────────────────────────────────────────────────────


def _parse_ai_response(data: dict[str, Any], original_filenames: list[str]) -> list[AIResult]:
    """Parse the Groq API response into AIResult objects.

    Args:
        data: Raw API response JSON.
        original_filenames: The filenames we sent (for fallback matching).

    Returns:
        List of parsed AIResult objects.
    """
    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        results_raw = parsed.get("results", [])
    except (KeyError, json.JSONDecodeError, IndexError) as e:
        logger.error("Failed to parse AI response: {}", e)
        return []

    results: list[AIResult] = []

    for item in results_raw:
        try:
            media_type_str = item.get("type", "unknown")
            if media_type_str == "movie":
                media_type = MediaType.MOVIE
            elif media_type_str == "tv":
                media_type = MediaType.TV
            else:
                media_type = MediaType.UNKNOWN

            result = AIResult(
                filename=item.get("filename", ""),
                media_type=media_type,
                title=item.get("title", "Unknown"),
                year=item.get("year"),
                season=item.get("season"),
                episode=item.get("episode"),
                quality=item.get("quality"),
                source=item.get("source"),
                confidence=float(item.get("confidence", 0.0)),
            )
            results.append(result)

        except Exception as e:
            logger.warning("Failed to parse AI result item: {} — {}", item, e)

    logger.debug("Parsed {} AI results", len(results))
    return results


# ── Exceptions ─────────────────────────────────────────────────────────────────


class RateLimitError(Exception):
    """Raised when the Groq API rate limit is exceeded."""
