"""Junk file detection for ReelCTL.

Identifies known junk files commonly found in media downloads:
torrent tracker files, samples, system files, and NFO files.
"""

from __future__ import annotations

import re

from loguru import logger

from reelctl.models import FileCategory, ScannedFile

# ── Known Junk Patterns ───────────────────────────────────────────────────────

# Exact filename matches (case-insensitive)
JUNK_FILENAMES: set[str] = {
    "rarbg.txt",
    "rarbg_do_not_mirror.exe",
    "yts.mx.txt",
    "yify.txt",
    "eztv.txt",
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
    "www.yts.mx.jpg",
    "www.yts.am.jpg",
}

# Filename prefixes that indicate junk
JUNK_PREFIXES: list[str] = [
    "torrent downloaded from",
    "downloaded from",
    "please seed",
    "if you liked this",
]

# Regex patterns for junk files
JUNK_PATTERNS: list[re.Pattern] = [
    re.compile(r"^sample[\._\-]", re.IGNORECASE),       # sample.mkv, sample_video.avi
    re.compile(r"[\._\-]sample\.", re.IGNORECASE),       # video_sample.mkv
    re.compile(r"^RARBG", re.IGNORECASE),                # RARBG*.txt
    re.compile(r"^www\..+\.(jpg|png|txt)$", re.IGNORECASE),  # www.site.com.jpg
]


def is_junk_file(scanned_file: ScannedFile) -> bool:
    """Determine if a file is junk.

    Checks against known junk filenames, prefixes, patterns,
    and the junk extension category.

    Args:
        scanned_file: The file to evaluate.

    Returns:
        True if the file is considered junk.
    """
    name_lower = scanned_file.name.lower()

    # Already categorized as junk by extension
    if scanned_file.category == FileCategory.JUNK:
        return True

    # Exact filename match
    if name_lower in JUNK_FILENAMES:
        return True

    # Prefix match
    for prefix in JUNK_PREFIXES:
        if name_lower.startswith(prefix):
            return True

    # Regex pattern match
    for pattern in JUNK_PATTERNS:
        if pattern.search(scanned_file.name):
            return True

    # Very small video files are likely samples (< 50MB)
    if scanned_file.category == FileCategory.VIDEO and scanned_file.size_bytes < 50 * 1024 * 1024:
        if "sample" in name_lower:
            return True

    return False


def detect_junk_files(files: list[ScannedFile]) -> list[ScannedFile]:
    """Find all junk files in a list of scanned files.

    Args:
        files: List of scanned files to check.

    Returns:
        List of files identified as junk.
    """
    junk_files = [f for f in files if is_junk_file(f)]

    if junk_files:
        logger.info("Detected {} junk files", len(junk_files))
        for jf in junk_files:
            logger.debug("  Junk: {}", jf.name)

    return junk_files
