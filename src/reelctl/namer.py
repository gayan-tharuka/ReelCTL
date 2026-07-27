"""Naming convention builder for ReelCTL.

Generates standardized filenames and folder structures for movies and TV shows
following the naming conventions defined in the PRD.

Movies:  Movie Title (Year) [Quality Source].ext
TV:      Series - S01E01 [Quality Source].ext
         Series - S01E01 - Episode Name [Quality Source].ext
"""

from __future__ import annotations

import re
from pathlib import Path

from reelctl.config import Settings
from reelctl.models import MediaIdentity, MediaType

# ── Filename Sanitization ──────────────────────────────────────────────────────

# Characters not allowed in filenames on Windows/macOS/Linux
INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(name: str) -> str:
    """Remove or replace characters invalid in filenames.

    Args:
        name: Raw filename string.

    Returns:
        Sanitized filename safe for all major operating systems.
    """
    # Replace invalid characters with empty string
    sanitized = INVALID_CHARS.sub("", name)
    # Collapse multiple spaces
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    # Remove trailing dots/spaces (Windows issue)
    sanitized = sanitized.rstrip(". ")
    return sanitized


# ── Name Building ──────────────────────────────────────────────────────────────


def build_movie_filename(identity: MediaIdentity) -> str:
    """Build a standardized movie filename.

    Format: Movie Title (Year) [Quality Source].ext

    Args:
        identity: Verified media identity.

    Returns:
        Formatted filename string.
    """
    parts = [identity.title]

    if identity.year:
        parts[0] = f"{identity.title} ({identity.year})"

    # Quality tag
    quality_parts = []
    if identity.quality:
        quality_parts.append(identity.quality)
    if identity.source:
        quality_parts.append(identity.source)

    if quality_parts:
        quality_tag = " ".join(quality_parts)
        parts.append(f"[{quality_tag}]")

    filename = " ".join(parts)
    ext = identity.source_file.extension
    return sanitize_filename(f"{filename}.{ext}")


def build_tv_filename(identity: MediaIdentity, include_episode_title: bool = True) -> str:
    """Build a standardized TV show filename.

    Format: Series - S01E01 [Quality Source].ext
    Or:     Series - S01E01 - Episode Name [Quality Source].ext

    Args:
        identity: Verified media identity.
        include_episode_title: Whether to include the episode name.

    Returns:
        Formatted filename string.
    """
    parts = [identity.title]

    # Episode code
    season = identity.season or 1
    episode = identity.episode or 0
    episode_code = f"S{season:02d}E{episode:02d}"
    parts.append(f"- {episode_code}")

    # Episode name
    if include_episode_title and identity.episode_name:
        parts.append(f"- {identity.episode_name}")

    # Quality tag
    quality_parts = []
    if identity.quality:
        quality_parts.append(identity.quality)
    if identity.source:
        quality_parts.append(identity.source)

    if quality_parts:
        quality_tag = " ".join(quality_parts)
        parts.append(f"[{quality_tag}]")

    filename = " ".join(parts)
    ext = identity.source_file.extension
    return sanitize_filename(f"{filename}.{ext}")


def build_filename(identity: MediaIdentity, settings: Settings) -> str:
    """Build the appropriate filename based on media type.

    Args:
        identity: Verified media identity.
        settings: Application settings.

    Returns:
        Formatted filename string.
    """
    if identity.media_type == MediaType.MOVIE:
        return build_movie_filename(identity)
    elif identity.media_type == MediaType.TV:
        return build_tv_filename(identity, settings.include_episode_title)
    else:
        # Unknown — return original filename
        return identity.source_file.name


# ── Folder Building ────────────────────────────────────────────────────────────


def build_movie_folder(
    identity: MediaIdentity,
    output_root: Path,
    settings: Settings,
) -> Path:
    """Build the target folder path for a movie.

    Format: output_root/Movies/Movie Title (Year)/

    Args:
        identity: Verified media identity.
        output_root: Root output directory.
        settings: Application settings.

    Returns:
        Full folder path.
    """
    movie_dir = sanitize_filename(settings.movie_folder)

    if identity.year:
        folder_name = f"{identity.title} ({identity.year})"
    else:
        folder_name = identity.title

    return output_root / movie_dir / sanitize_filename(folder_name)


def build_tv_folder(
    identity: MediaIdentity,
    output_root: Path,
    settings: Settings,
) -> Path:
    """Build the target folder path for a TV episode.

    Format: output_root/TV Shows/Series/Season XX/

    Args:
        identity: Verified media identity.
        output_root: Root output directory.
        settings: Application settings.

    Returns:
        Full folder path.
    """
    tv_dir = sanitize_filename(settings.tv_folder)
    series_name = sanitize_filename(identity.title)
    season = identity.season or 1
    season_dir = f"Season {season:02d}"

    return output_root / tv_dir / series_name / season_dir


def build_target_path(
    identity: MediaIdentity,
    output_root: Path,
    settings: Settings,
) -> Path:
    """Build the full target file path (folder + filename).

    Args:
        identity: Verified media identity.
        output_root: Root output directory.
        settings: Application settings.

    Returns:
        Full target file path.
    """
    filename = build_filename(identity, settings)

    if identity.media_type == MediaType.MOVIE:
        folder = build_movie_folder(identity, output_root, settings)
    elif identity.media_type == MediaType.TV:
        folder = build_tv_folder(identity, output_root, settings)
    else:
        folder = output_root

    return folder / filename


# ── Subtitle Naming ────────────────────────────────────────────────────────────


def build_subtitle_filename(
    identity: MediaIdentity,
    subtitle_ext: str,
    language_code: str | None = None,
) -> str:
    """Build a subtitle filename matching its video file.

    Format: Movie Title (Year).en.srt

    Args:
        identity: The video's media identity.
        subtitle_ext: The subtitle file extension (e.g., "srt").
        language_code: Language code (e.g., "en", "si"), or None.

    Returns:
        Formatted subtitle filename.
    """
    if identity.media_type == MediaType.MOVIE:
        if identity.year:
            base = f"{identity.title} ({identity.year})"
        else:
            base = identity.title
    elif identity.media_type == MediaType.TV:
        season = identity.season or 1
        episode = identity.episode or 0
        base = f"{identity.title} - S{season:02d}E{episode:02d}"
    else:
        base = identity.source_file.path.stem

    if language_code:
        return sanitize_filename(f"{base}.{language_code}.{subtitle_ext}")
    else:
        return sanitize_filename(f"{base}.{subtitle_ext}")
