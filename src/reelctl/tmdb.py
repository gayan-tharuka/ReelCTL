"""TMDB API client for metadata verification.

Every AI identification result is verified against The Movie Database (TMDB)
to ensure accuracy. Only verified metadata is used in the final output.
"""

from __future__ import annotations

from difflib import SequenceMatcher

import httpx
from loguru import logger

from reelctl.cache import TMDBCache
from reelctl.config import Settings
from reelctl.models import MediaType, TMDBResult

# ── Constants ──────────────────────────────────────────────────────────────────

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


# ── TMDB Client ────────────────────────────────────────────────────────────────


class TMDBClient:
    """Async TMDB API client with caching and verification."""

    def __init__(self, settings: Settings, cache: TMDBCache | None = None) -> None:
        self.settings = settings
        self.cache = cache

        # Prefer access token (Bearer), fall back to API key (query param)
        self._headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if settings.tmdb_access_token:
            self._headers["Authorization"] = f"Bearer {settings.tmdb_access_token}"

        self._api_key = settings.tmdb_api_key
        self._language = settings.language

    def _params(self, **kwargs) -> dict:
        """Build query parameters, adding API key if no Bearer token."""
        params = {"language": self._language, **kwargs}
        if "Authorization" not in self._headers and self._api_key:
            params["api_key"] = self._api_key
        return params

    async def verify_movie(
        self, title: str, year: int | None = None
    ) -> TMDBResult | None:
        """Search TMDB for a movie and verify the match.

        Args:
            title: Movie title from AI identification.
            year: Release year (optional, improves accuracy).

        Returns:
            TMDBResult if a good match is found, None otherwise.
        """
        # Check cache first
        cache_key = f"movie:{title}:{year}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug("TMDB cache hit: {}", cache_key)
                return TMDBResult(**cached)

        logger.info("TMDB search movie: '{}' ({})", title, year or "no year")

        params = self._params(query=title)
        if year:
            params["year"] = year

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{TMDB_BASE_URL}/search/movie",
                    headers=self._headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.error("TMDB movie search failed: {}", e)
            return None

        results = data.get("results", [])
        if not results:
            logger.warning("TMDB: no results for movie '{}'", title)
            return None

        # Find best match
        best = self._find_best_match(results, title, year, is_movie=True)
        if not best:
            return None

        tmdb_result = TMDBResult(
            tmdb_id=best["id"],
            official_title=best.get("title", title),
            year=self._extract_year(best.get("release_date", "")),
            media_type=MediaType.MOVIE,
            genres=[],  # Could fetch full genre list if needed
            poster_url=(
                f"{TMDB_IMAGE_BASE}{best['poster_path']}" if best.get("poster_path") else None
            ),
            verified=True,
        )

        # Cache the result
        if self.cache:
            self.cache.set(cache_key, tmdb_result.model_dump(mode="json"))

        logger.info("TMDB verified movie: {} ({})", tmdb_result.official_title, tmdb_result.year)
        return tmdb_result

    async def verify_tv(
        self,
        title: str,
        year: int | None = None,
        season: int | None = None,
        episode: int | None = None,
    ) -> TMDBResult | None:
        """Search TMDB for a TV show and verify the match.

        Args:
            title: TV show title from AI identification.
            year: First air date year (optional).
            season: Season number (optional, for episode lookup).
            episode: Episode number (optional, for episode name).

        Returns:
            TMDBResult if a good match is found, None otherwise.
        """
        # Check cache
        cache_key = f"tv:{title}:{year}:{season}:{episode}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug("TMDB cache hit: {}", cache_key)
                return TMDBResult(**cached)

        logger.info("TMDB search TV: '{}' S{:02d}E{:02d}", title, season or 0, episode or 0)

        params = self._params(query=title)
        if year:
            params["first_air_date_year"] = year

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{TMDB_BASE_URL}/search/tv",
                    headers=self._headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.error("TMDB TV search failed: {}", e)
            return None

        results = data.get("results", [])
        if not results:
            logger.warning("TMDB: no results for TV '{}'", title)
            return None

        best = self._find_best_match(results, title, year, is_movie=False)
        if not best:
            return None

        show_id = best["id"]
        official_title = best.get("name", title)
        show_year = self._extract_year(best.get("first_air_date", ""))

        # Fetch episode name if we have season + episode
        episode_name = None
        if season and episode:
            episode_name = await self._get_episode_name(show_id, season, episode)

        tmdb_result = TMDBResult(
            tmdb_id=show_id,
            official_title=official_title,
            year=show_year,
            media_type=MediaType.TV,
            genres=[],
            poster_url=(
                f"{TMDB_IMAGE_BASE}{best['poster_path']}" if best.get("poster_path") else None
            ),
            episode_name=episode_name,
            season=season,
            episode=episode,
            verified=True,
        )

        if self.cache:
            self.cache.set(cache_key, tmdb_result.model_dump(mode="json"))

        logger.info("TMDB verified TV: {} S{:02d}E{:02d}", official_title, season or 0, episode or 0)
        return tmdb_result

    async def _get_episode_name(
        self, show_id: int, season: int, episode: int
    ) -> str | None:
        """Fetch the episode name from TMDB.

        Args:
            show_id: TMDB show ID.
            season: Season number.
            episode: Episode number.

        Returns:
            Episode name or None if not found.
        """
        cache_key = f"episode:{show_id}:{season}:{episode}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached.get("name")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{TMDB_BASE_URL}/tv/{show_id}/season/{season}/episode/{episode}",
                    headers=self._headers,
                    params=self._params(),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("TMDB episode lookup failed: {}", e)
            return None

        name = data.get("name")
        if name and self.cache:
            self.cache.set(cache_key, {"name": name})

        return name

    # ── Matching Helpers ───────────────────────────────────────────────────────

    def _find_best_match(
        self,
        results: list[dict],
        title: str,
        year: int | None,
        is_movie: bool,
    ) -> dict | None:
        """Find the best matching result from TMDB search results.

        Uses fuzzy title matching and year validation (±1 year tolerance).
        """
        title_lower = title.lower()
        title_key = "title" if is_movie else "name"
        date_key = "release_date" if is_movie else "first_air_date"

        best_match = None
        best_score = 0.0

        for result in results[:5]:  # Only check top 5 results
            result_title = result.get(title_key, "").lower()
            similarity = SequenceMatcher(None, title_lower, result_title).ratio()

            # Year bonus
            result_year = self._extract_year(result.get(date_key, ""))
            if year and result_year and abs(year - result_year) <= 1:
                similarity += 0.15  # Boost for matching year

            if similarity > best_score:
                best_score = similarity
                best_match = result

        # Require minimum similarity
        if best_score < 0.5:
            logger.warning(
                "TMDB: best match for '{}' has low similarity ({:.2f}), skipping",
                title,
                best_score,
            )
            return None

        return best_match

    @staticmethod
    def _extract_year(date_str: str) -> int | None:
        """Extract year from a TMDB date string (YYYY-MM-DD)."""
        if date_str and len(date_str) >= 4:
            try:
                return int(date_str[:4])
            except ValueError:
                pass
        return None
