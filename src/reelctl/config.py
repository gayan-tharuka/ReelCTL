"""Configuration management for ReelCTL.

Loads settings from (in priority order):
1. Environment variables
2. .env file in current directory
3. ~/.config/reelctl/config.toml
4. ./config.toml (local fallback)
5. Built-in defaults
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Constants ──────────────────────────────────────────────────────────────────

APP_NAME = "reelctl"
XDG_CONFIG_DIR = Path.home() / ".config" / APP_NAME
CONFIG_FILENAME = "config.toml"
CACHE_DB_FILENAME = "cache.db"


def _get_config_dir() -> Path:
    """Return the XDG config directory, creating it if needed."""
    XDG_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return XDG_CONFIG_DIR


def _get_cache_path() -> Path:
    """Return the path to the SQLite cache database."""
    return _get_config_dir() / CACHE_DB_FILENAME


# ── Settings Model ─────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """Application settings with multi-source loading."""

    model_config = SettingsConfigDict(
        env_prefix="REELCTL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    tmdb_api_key: str = Field(default="", alias="TMDB_API_KEY")
    tmdb_access_token: str = Field(default="", alias="TMDB_ACCESS_TOKEN")

    # General
    language: str = "en"
    delete_junk: bool = True
    include_episode_title: bool = True

    # Folder names
    movie_folder: str = "Movies"
    tv_folder: str = "TV Shows"

    # Behavior
    dry_run: bool = True

    # AI
    groq_model: str = "llama-3.3-70b-versatile"
    ai_confidence_threshold: float = 0.80
    ai_batch_size: int = 50

    # Cache
    cache_ttl_days: int = 30


def _load_toml_config() -> dict:
    """Load configuration from TOML files.

    Checks XDG config dir first, then local directory.
    """
    config_paths = [
        XDG_CONFIG_DIR / CONFIG_FILENAME,
        Path(CONFIG_FILENAME),
    ]

    for config_path in config_paths:
        if config_path.exists():
            logger.debug("Loading config from {}", config_path)
            with open(config_path, "rb") as f:
                return tomllib.load(f)

    logger.debug("No config.toml found, using defaults")
    return {}


def load_settings() -> Settings:
    """Load settings from all sources and return a merged Settings instance."""
    # Load .env file first so env vars are available
    load_dotenv()

    # Load TOML config
    toml_config = _load_toml_config()

    # Map TOML keys to settings fields
    field_mapping = {
        "groq_api": "groq_api_key",
        "tmdb_api": "tmdb_api_key",
    }

    mapped_config = {}
    for key, value in toml_config.items():
        mapped_key = field_mapping.get(key, key)
        mapped_config[mapped_key] = value

    # Create settings — env vars and .env take priority over TOML
    settings = Settings(**mapped_config)

    # Validate critical keys
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set — AI features will be unavailable")
    if not settings.tmdb_api_key and not settings.tmdb_access_token:
        logger.warning("TMDB API key not set — verification will be unavailable")

    return settings
