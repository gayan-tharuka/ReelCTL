"""SQLite caching layer for ReelCTL.

Caches TMDB API responses locally to avoid duplicate API calls across runs.
Default TTL is 30 days.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from loguru import logger

from reelctl.config import _get_config_dir

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_TTL_DAYS = 30
SECONDS_PER_DAY = 86400


class TMDBCache:
    """SQLite-backed cache for TMDB API responses."""

    def __init__(
        self,
        db_path: Path | None = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> None:
        """Initialize the cache.

        Args:
            db_path: Path to the SQLite database file.
                     Defaults to ~/.config/reelctl/cache.db
            ttl_days: Number of days before cache entries expire.
        """
        self.db_path = db_path or (_get_config_dir() / "cache.db")
        self.ttl_seconds = ttl_days * SECONDS_PER_DAY
        self._conn: sqlite3.Connection | None = None
        self._initialize()

    def _initialize(self) -> None:
        """Create the cache database and table if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()
        logger.debug("Cache initialized at {}", self.db_path)

    def get(self, key: str) -> dict | None:
        """Retrieve a cached value if it exists and hasn't expired.

        Args:
            key: Cache key (e.g., "movie:Avatar:2009").

        Returns:
            Cached dictionary or None if not found/expired.
        """
        if not self._conn:
            return None

        cursor = self._conn.execute(
            "SELECT value, created_at FROM cache WHERE key = ?", (key,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        value_str, created_at = row

        # Check TTL
        if time.time() - created_at > self.ttl_seconds:
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
            logger.debug("Cache expired for key: {}", key)
            return None

        try:
            return json.loads(value_str)
        except json.JSONDecodeError:
            logger.warning("Corrupted cache entry for key: {}", key)
            return None

    def set(self, key: str, value: dict) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key.
            value: Dictionary to cache (must be JSON-serializable).
        """
        if not self._conn:
            return

        value_str = json.dumps(value, default=str)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO cache (key, value, created_at)
            VALUES (?, ?, ?)
            """,
            (key, value_str, time.time()),
        )
        self._conn.commit()

    def clear(self) -> None:
        """Remove all cached entries."""
        if self._conn:
            self._conn.execute("DELETE FROM cache")
            self._conn.commit()
            logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """Remove expired entries from the cache.

        Returns:
            Number of entries removed.
        """
        if not self._conn:
            return 0

        cutoff = time.time() - self.ttl_seconds
        cursor = self._conn.execute(
            "DELETE FROM cache WHERE created_at < ?", (cutoff,)
        )
        self._conn.commit()
        count = cursor.rowcount
        if count:
            logger.info("Cleaned up {} expired cache entries", count)
        return count

    def stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with total entries and approximate size.
        """
        if not self._conn:
            return {"entries": 0, "size_bytes": 0}

        cursor = self._conn.execute("SELECT COUNT(*) FROM cache")
        count = cursor.fetchone()[0]

        size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {"entries": count, "size_bytes": size}

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __del__(self) -> None:
        self.close()
