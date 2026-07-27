"""Filesystem scanner for ReelCTL.

Recursively scans directories and categorizes every file by extension.
Designed for performance — targets 10,000 files in under 30 seconds.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from reelctl.models import FileCategory, ScanResult, ScannedFile, categorize_extension


def scan_directory(root: Path) -> ScanResult:
    """Recursively scan a directory and categorize all files.

    Args:
        root: The root directory to scan.

    Returns:
        ScanResult with all discovered files grouped by category.

    Raises:
        FileNotFoundError: If root doesn't exist.
        NotADirectoryError: If root is not a directory.
    """
    root = root.resolve()

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    logger.info("Scanning directory: {}", root)
    start_time = time.perf_counter()

    files: list[ScannedFile] = []
    total_size = 0
    errors = 0

    for item in root.rglob("*"):
        if item.is_file():
            try:
                stat = item.stat()
                ext = item.suffix.lstrip(".")
                category = categorize_extension(ext)

                scanned = ScannedFile(
                    path=item,
                    name=item.name,
                    extension=ext,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    category=category,
                )
                files.append(scanned)
                total_size += stat.st_size

            except (PermissionError, OSError) as e:
                logger.warning("Cannot access file {}: {}", item, e)
                errors += 1

    duration = time.perf_counter() - start_time

    result = ScanResult(
        root_path=root,
        files=files,
        total_size_bytes=total_size,
        scan_duration_seconds=round(duration, 3),
    )

    logger.info(
        "Scan complete: {} files ({} video, {} subtitle, {} junk, {} unknown) in {:.2f}s",
        len(files),
        len(result.video_files),
        len(result.subtitle_files),
        len(result.junk_files),
        len(result.unknown_files),
        duration,
    )

    if errors:
        logger.warning("{} files could not be accessed", errors)

    return result


def find_associated_subtitles(
    video_file: ScannedFile, all_subtitles: list[ScannedFile]
) -> list[ScannedFile]:
    """Find subtitle files associated with a video file.

    Matches by:
    1. Same directory + same base name (e.g., movie.mkv ↔ movie.en.srt)
    2. Same directory + video name is a prefix of subtitle name
    3. Same directory + subtitle name is a prefix of video name (common case:
       Avatar.2009.en.srt matches Avatar.2009.2160p.BluRay.mkv)

    Args:
        video_file: The video file to find subtitles for.
        all_subtitles: All subtitle files from the scan.

    Returns:
        List of associated subtitle files.
    """
    video_dir = video_file.path.parent
    video_stem = video_file.path.stem

    associated: list[ScannedFile] = []

    for sub in all_subtitles:
        if sub.path.parent != video_dir:
            continue

        sub_stem = sub.path.stem

        # Strip language code from subtitle stem for matching
        # e.g., "Avatar.2009.en" → "Avatar.2009"
        sub_base = sub_stem
        parts = sub_stem.rsplit(".", 1)
        if len(parts) == 2 and len(parts[1]) <= 3:
            sub_base = parts[0]

        # Exact match: movie.srt for movie.mkv
        if sub_stem == video_stem:
            associated.append(sub)
        # Language-coded: movie.en.srt → stem is "movie.en", starts with video stem
        elif sub_stem.startswith(video_stem + "."):
            associated.append(sub)
        # Reverse: video stem starts with subtitle base
        # e.g., video "Avatar.2009.2160p.BluRay.x265" starts with sub base "Avatar.2009"
        elif video_stem.startswith(sub_base + ".") or video_stem == sub_base:
            associated.append(sub)

    return associated
