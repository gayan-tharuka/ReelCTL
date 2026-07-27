"""Shared test fixtures for ReelCTL."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from reelctl.models import (
    FileCategory,
    MediaIdentity,
    MediaType,
    ScannedFile,
)


@pytest.fixture
def sample_video_file(tmp_path: Path) -> ScannedFile:
    """Create a sample video ScannedFile."""
    file_path = tmp_path / "Avatar.2009.2160p.BluRay.x265.mkv"
    file_path.write_bytes(b"\x00" * 1024)
    return ScannedFile(
        path=file_path,
        name=file_path.name,
        extension="mkv",
        size_bytes=1024,
        modified_at=datetime.now(),
        category=FileCategory.VIDEO,
    )


@pytest.fixture
def sample_tv_file(tmp_path: Path) -> ScannedFile:
    """Create a sample TV episode ScannedFile."""
    file_path = tmp_path / "Money.Heist.S02E04.1080p.WEB-DL.mkv"
    file_path.write_bytes(b"\x00" * 1024)
    return ScannedFile(
        path=file_path,
        name=file_path.name,
        extension="mkv",
        size_bytes=1024,
        modified_at=datetime.now(),
        category=FileCategory.VIDEO,
    )


@pytest.fixture
def sample_subtitle_file(tmp_path: Path) -> ScannedFile:
    """Create a sample subtitle ScannedFile."""
    file_path = tmp_path / "Avatar.2009.en.srt"
    file_path.write_text("1\n00:00:01,000 --> 00:00:03,000\nHello world\n")
    return ScannedFile(
        path=file_path,
        name=file_path.name,
        extension="srt",
        size_bytes=50,
        modified_at=datetime.now(),
        category=FileCategory.SUBTITLE,
    )


@pytest.fixture
def sample_junk_file(tmp_path: Path) -> ScannedFile:
    """Create a sample junk ScannedFile."""
    file_path = tmp_path / "RARBG.txt"
    file_path.write_text("RARBG tracker info")
    return ScannedFile(
        path=file_path,
        name=file_path.name,
        extension="txt",
        size_bytes=20,
        modified_at=datetime.now(),
        category=FileCategory.JUNK,
    )


@pytest.fixture
def sample_movie_identity(sample_video_file: ScannedFile) -> MediaIdentity:
    """Create a sample movie MediaIdentity."""
    return MediaIdentity(
        source_file=sample_video_file,
        media_type=MediaType.MOVIE,
        title="Avatar",
        year=2009,
        quality="4K",
        source="BluRay",
        tmdb_id=19995,
        confidence=0.99,
        verified=True,
    )


@pytest.fixture
def sample_tv_identity(sample_tv_file: ScannedFile) -> MediaIdentity:
    """Create a sample TV MediaIdentity."""
    return MediaIdentity(
        source_file=sample_tv_file,
        media_type=MediaType.TV,
        title="Money Heist",
        year=2017,
        season=2,
        episode=4,
        episode_name="We're Back",
        quality="1080p",
        source="WEB-DL",
        tmdb_id=71446,
        confidence=0.98,
        verified=True,
    )


@pytest.fixture
def media_dir(tmp_path: Path) -> Path:
    """Create a realistic media directory for testing."""
    # Video files
    (tmp_path / "Avatar.2009.2160p.BluRay.x265.mkv").write_bytes(b"\x00" * 1024)
    (tmp_path / "Matrix1999Bluray1080.mp4").write_bytes(b"\x00" * 1024)
    (tmp_path / "Money.Heist.S01E01.x264.mkv").write_bytes(b"\x00" * 1024)
    (tmp_path / "movie.mp4").write_bytes(b"\x00" * 512)

    # Subtitle
    (tmp_path / "Avatar.2009.en.srt").write_text("1\n00:00:01,000 --> 00:00:03,000\nThe quick brown fox\n")

    # Junk
    (tmp_path / "RARBG.txt").write_text("RARBG")
    (tmp_path / "sample.mkv").write_bytes(b"\x00" * 100)

    return tmp_path
