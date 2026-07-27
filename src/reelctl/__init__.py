"""ReelCTL - AI-Powered Media Organizer."""

__version__ = "1.0.0"
__app_name__ = "reelctl"

import sys
from pathlib import Path

from loguru import logger

# ── Logging Setup ──────────────────────────────────────────────────────────────

LOG_DIR = Path("logs")


def setup_logging(log_dir: Path | None = None) -> None:
    """Configure loguru for ReelCTL.

    Creates a daily log file in the specified directory with detailed
    formatting for every operation, API call, warning, and error.
    """
    target_dir = log_dir or LOG_DIR

    # Remove default stderr handler
    logger.remove()

    # Console handler — only warnings and above
    logger.add(
        sys.stderr,
        level="WARNING",
        format="<level>{level: <8}</level> | {message}",
        colorize=True,
    )

    # File handler — everything, daily rotation
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(target_dir / "{time:YYYY-MM-DD}.log"),
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="00:00",  # New file at midnight
        retention="30 days",
        encoding="utf-8",
    )
