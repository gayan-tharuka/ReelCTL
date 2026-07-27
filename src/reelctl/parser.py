"""Local filename parsing using guessit.

Extracts media metadata (title, year, season, episode, quality, source)
from filenames before sending to the AI for enhanced understanding.
"""

from __future__ import annotations

from guessit import guessit
from loguru import logger

from reelctl.models import MediaType, ParsedMedia
from reelctl.normalizer import normalize_quality, normalize_source


def parse_filename(filename: str) -> ParsedMedia:
    """Parse a media filename using guessit and normalize results.

    Args:
        filename: The filename to parse (e.g., "Avatar.2009.2160p.BluRay.x265.mkv").

    Returns:
        ParsedMedia with extracted and normalized metadata.
    """
    logger.debug("Parsing filename: {}", filename)

    try:
        guess = guessit(filename)
    except Exception as e:
        logger.warning("guessit failed for '{}': {}", filename, e)
        return ParsedMedia(original_filename=filename)

    # Determine media type
    guess_type = guess.get("type", "")
    if guess_type == "movie":
        media_type = MediaType.MOVIE
    elif guess_type == "episode":
        media_type = MediaType.TV
    else:
        media_type = MediaType.UNKNOWN

    # Extract quality and source, then normalize
    raw_quality = str(guess.get("screen_size", "")) or None
    raw_source = str(guess.get("source", "")) or None

    quality = normalize_quality(raw_quality) if raw_quality else None
    source = normalize_source(raw_source) if raw_source else None

    parsed = ParsedMedia(
        original_filename=filename,
        title=guess.get("title"),
        year=guess.get("year"),
        season=guess.get("season"),
        episode=guess.get("episode"),
        quality=quality,
        source=source,
        codec=str(guess.get("video_codec", "")) or None,
        release_group=str(guess.get("release_group", "")) or None,
        media_type=media_type,
    )

    logger.debug("Parsed result: {} → {}", filename, parsed.title)
    return parsed


def parse_files(filenames: list[str]) -> list[ParsedMedia]:
    """Parse multiple filenames.

    Args:
        filenames: List of filenames to parse.

    Returns:
        List of ParsedMedia results.
    """
    return [parse_filename(fn) for fn in filenames]
