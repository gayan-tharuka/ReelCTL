"""Quality and source normalization for ReelCTL.

Normalizes the wide variety of quality and source labels found in media
filenames into a consistent, clean set of labels as defined in the PRD.
"""

from __future__ import annotations

# ── Quality Normalization ──────────────────────────────────────────────────────

QUALITY_MAP: dict[str, str] = {
    # 4K variants
    "2160p": "4K",
    "uhd": "4K",
    "4k": "4K",
    # Standard resolutions
    "1080p": "1080p",
    "1080i": "1080p",
    "720p": "720p",
    "480p": "480p",
    "576p": "SD",
    "sd": "SD",
}

# ── Source Normalization ───────────────────────────────────────────────────────

SOURCE_MAP: dict[str, str] = {
    # BluRay variants
    "blu-ray": "BluRay",
    "bluray": "BluRay",
    "brrip": "BluRay",
    "bdrip": "BluRay",
    "bdremux": "BluRay",
    "bd": "BluRay",
    # WEB variants
    "web-dl": "WEB-DL",
    "webdl": "WEB-DL",
    "webrip": "WEB",
    "web": "WEB",
    "web-rip": "WEB",
    # Other
    "hdrip": "HDRip",
    "dvdrip": "DVD",
    "dvd": "DVD",
    "hdtv": "HDTV",
    "pdtv": "HDTV",
    "dsr": "HDTV",
    "dthrip": "HDTV",
    "cam": "CAM",
    "ts": "TS",
    "telesync": "TS",
    "telecine": "TC",
    "tc": "TC",
    "screener": "SCR",
    "scr": "SCR",
    "r5": "R5",
}

# ── Quality Ranking (higher = better) ─────────────────────────────────────────

QUALITY_RANK: dict[str, int] = {
    "4K": 5,
    "1080p": 4,
    "720p": 3,
    "480p": 2,
    "SD": 1,
}

SOURCE_RANK: dict[str, int] = {
    "BluRay": 7,
    "WEB-DL": 6,
    "WEB": 5,
    "HDRip": 4,
    "HDTV": 3,
    "DVD": 2,
    "CAM": 1,
    "TS": 1,
    "TC": 1,
    "SCR": 1,
}


def normalize_quality(quality: str | None) -> str | None:
    """Normalize a quality string to a standard label.

    Args:
        quality: Raw quality string (e.g., "2160p", "UHD", "1080p").

    Returns:
        Normalized quality label (e.g., "4K", "1080p") or original if unknown.
    """
    if not quality:
        return None
    return QUALITY_MAP.get(quality.lower(), quality)


def normalize_source(source: str | None) -> str | None:
    """Normalize a source string to a standard label.

    Args:
        source: Raw source string (e.g., "BRRip", "WEB-DL", "webrip").

    Returns:
        Normalized source label (e.g., "BluRay", "WEB-DL") or original if unknown.
    """
    if not source:
        return None
    return SOURCE_MAP.get(source.lower(), source)


def quality_score(quality: str | None, source: str | None) -> int:
    """Calculate a numeric quality score for comparison.

    Higher scores indicate better quality. Used for duplicate detection
    to recommend which file to keep.

    Args:
        quality: Normalized quality string.
        source: Normalized source string.

    Returns:
        Numeric score (higher = better quality).
    """
    q_score = QUALITY_RANK.get(quality or "", 0)
    s_score = SOURCE_RANK.get(source or "", 0)
    return q_score * 10 + s_score
