"""Subtitle handling for ReelCTL.

Detects subtitle files, extracts language codes, and auto-detects language
from file content when no language code is present in the filename.
"""

from __future__ import annotations

import re
from pathlib import Path

import chardet
from loguru import logger

from reelctl.models import ScannedFile

# ── Known Language Codes ───────────────────────────────────────────────────────

# Common 2-letter and 3-letter language codes
LANGUAGE_CODES: dict[str, str] = {
    "en": "en",
    "eng": "en",
    "english": "en",
    "si": "si",
    "sin": "si",
    "sinhala": "si",
    "es": "es",
    "spa": "es",
    "spanish": "es",
    "fr": "fr",
    "fre": "fr",
    "french": "fr",
    "de": "de",
    "ger": "de",
    "german": "de",
    "it": "it",
    "ita": "it",
    "italian": "it",
    "pt": "pt",
    "por": "pt",
    "portuguese": "pt",
    "ja": "ja",
    "jpn": "ja",
    "japanese": "ja",
    "ko": "ko",
    "kor": "ko",
    "korean": "ko",
    "zh": "zh",
    "chi": "zh",
    "chinese": "zh",
    "ar": "ar",
    "ara": "ar",
    "arabic": "ar",
    "hi": "hi",
    "hin": "hi",
    "hindi": "hi",
    "ru": "ru",
    "rus": "ru",
    "russian": "ru",
    "nl": "nl",
    "dut": "nl",
    "dutch": "nl",
    "sv": "sv",
    "swe": "sv",
    "swedish": "sv",
    "ta": "ta",
    "tam": "ta",
    "tamil": "ta",
}

# Language detection heuristics — common words by language
LANGUAGE_SIGNATURES: dict[str, list[str]] = {
    "en": ["the", "and", "you", "that", "this", "with", "have", "from", "what", "about"],
    "es": ["que", "los", "las", "una", "por", "con", "para", "como", "pero", "más"],
    "fr": ["les", "des", "une", "que", "est", "pas", "pour", "dans", "qui", "sur"],
    "de": ["und", "der", "die", "das", "ist", "nicht", "ein", "ich", "mit", "den"],
    "it": ["che", "non", "una", "per", "sono", "con", "della", "questo", "come", "più"],
    "pt": ["que", "não", "uma", "para", "com", "por", "mais", "como", "dos", "este"],
    "si": ["මම", "ඔබ", "ඔහු", "ඇය", "අපි", "එය", "මේ", "ඒ", "මෙම", "ඔබේ"],
    "ar": ["من", "في", "على", "إلى", "أن", "هذا", "كان", "قال", "ما", "عن"],
    "hi": ["और", "के", "है", "में", "को", "का", "से", "पर", "कि", "यह"],
    "ja": ["の", "に", "は", "を", "た", "が", "で", "て", "と", "し"],
    "ko": ["의", "에", "는", "을", "를", "이", "가", "하", "는", "으로"],
    "zh": ["的", "是", "了", "在", "有", "和", "人", "我", "不", "他"],
    "ru": ["что", "это", "как", "они", "мне", "она", "для", "все", "так", "его"],
}


def extract_language_code(subtitle_file: ScannedFile) -> str | None:
    """Extract language code from a subtitle filename.

    Looks for patterns like: movie.en.srt, movie.eng.srt, movie.english.srt

    Args:
        subtitle_file: The subtitle file to check.

    Returns:
        Normalized 2-letter language code or None.
    """
    stem = subtitle_file.path.stem
    parts = stem.split(".")

    if len(parts) >= 2:
        potential_code = parts[-1].lower()
        if potential_code in LANGUAGE_CODES:
            return LANGUAGE_CODES[potential_code]

    return None


def detect_language_from_content(subtitle_path: Path, sample_size: int = 4096) -> str | None:
    """Auto-detect the language of a subtitle file from its content.

    Reads a sample of the file, detects encoding, then uses word frequency
    analysis to determine the language.

    Args:
        subtitle_path: Path to the subtitle file.
        sample_size: Number of bytes to read for detection.

    Returns:
        2-letter language code or None if detection fails.
    """
    try:
        # Read raw bytes
        raw_bytes = subtitle_path.read_bytes()[:sample_size]

        # Detect encoding
        detection = chardet.detect(raw_bytes)
        encoding = detection.get("encoding", "utf-8") or "utf-8"

        # Decode content
        try:
            text = raw_bytes.decode(encoding, errors="ignore")
        except (UnicodeDecodeError, LookupError):
            text = raw_bytes.decode("utf-8", errors="ignore")

        # Clean text — remove SRT/ASS formatting
        text = _strip_subtitle_formatting(text)
        text_lower = text.lower()

        # Score each language
        best_lang = None
        best_score = 0

        for lang, keywords in LANGUAGE_SIGNATURES.items():
            score = sum(1 for word in keywords if word in text_lower)
            if score > best_score:
                best_score = score
                best_lang = lang

        if best_score >= 3:  # Minimum threshold
            logger.debug(
                "Detected language '{}' (score={}) for {}",
                best_lang,
                best_score,
                subtitle_path.name,
            )
            return best_lang

        logger.debug("Could not detect language for {} (best score={})", subtitle_path.name, best_score)
        return None

    except Exception as e:
        logger.warning("Language detection failed for {}: {}", subtitle_path.name, e)
        return None


def get_subtitle_language(subtitle_file: ScannedFile) -> str | None:
    """Get the language of a subtitle file.

    First tries to extract from filename, then auto-detects from content.

    Args:
        subtitle_file: The subtitle file.

    Returns:
        2-letter language code or None.
    """
    # Try filename first
    code = extract_language_code(subtitle_file)
    if code:
        return code

    # Auto-detect from content
    return detect_language_from_content(subtitle_file.path)


def _strip_subtitle_formatting(text: str) -> str:
    """Remove SRT/ASS/SSA formatting tags to get clean text."""
    # Remove SRT timestamps: 00:01:23,456 --> 00:01:25,789
    text = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}", "", text)
    # Remove sequence numbers (lines with just digits)
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
    # Remove ASS/SSA tags: {\b1}, {\i0}, etc.
    text = re.sub(r"\{\\[^}]+\}", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    return text
