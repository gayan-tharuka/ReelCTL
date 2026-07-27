"""Tests for naming convention builder."""

from pathlib import Path

from reelctl.config import Settings
from reelctl.models import MediaIdentity, MediaType
from reelctl.namer import (
    build_filename,
    build_movie_filename,
    build_movie_folder,
    build_subtitle_filename,
    build_target_path,
    build_tv_filename,
    build_tv_folder,
    sanitize_filename,
)


class TestSanitizeFilename:
    def test_removes_invalid_chars(self):
        assert sanitize_filename('Movie: The "Test"') == "Movie The Test"

    def test_collapses_spaces(self):
        assert sanitize_filename("Movie   Title") == "Movie Title"

    def test_strips_trailing_dots(self):
        assert sanitize_filename("Movie...") == "Movie"


class TestBuildMovieFilename:
    def test_standard_movie(self, sample_movie_identity):
        result = build_movie_filename(sample_movie_identity)
        assert result == "Avatar (2009) [4K BluRay].mkv"

    def test_movie_without_year(self, sample_movie_identity):
        sample_movie_identity.year = None
        result = build_movie_filename(sample_movie_identity)
        assert result == "Avatar [4K BluRay].mkv"

    def test_movie_without_quality(self, sample_movie_identity):
        sample_movie_identity.quality = None
        sample_movie_identity.source = None
        result = build_movie_filename(sample_movie_identity)
        assert result == "Avatar (2009).mkv"


class TestBuildTVFilename:
    def test_standard_tv_with_episode_name(self, sample_tv_identity):
        result = build_tv_filename(sample_tv_identity, include_episode_title=True)
        assert result == "Money Heist - S02E04 - We're Back [1080p WEB-DL].mkv"

    def test_tv_without_episode_name(self, sample_tv_identity):
        result = build_tv_filename(sample_tv_identity, include_episode_title=False)
        assert result == "Money Heist - S02E04 [1080p WEB-DL].mkv"

    def test_tv_without_episode_name_in_identity(self, sample_tv_identity):
        sample_tv_identity.episode_name = None
        result = build_tv_filename(sample_tv_identity, include_episode_title=True)
        assert result == "Money Heist - S02E04 [1080p WEB-DL].mkv"


class TestBuildFolders:
    def test_movie_folder_structure(self, sample_movie_identity):
        settings = Settings()
        folder = build_movie_folder(sample_movie_identity, Path("/media"), settings)
        assert folder == Path("/media/Movies/Avatar (2009)")

    def test_tv_folder_structure(self, sample_tv_identity):
        settings = Settings()
        folder = build_tv_folder(sample_tv_identity, Path("/media"), settings)
        assert folder == Path("/media/TV Shows/Money Heist/Season 02")


class TestBuildSubtitleFilename:
    def test_movie_subtitle_with_language(self, sample_movie_identity):
        result = build_subtitle_filename(sample_movie_identity, "srt", "en")
        assert result == "Avatar (2009).en.srt"

    def test_movie_subtitle_without_language(self, sample_movie_identity):
        result = build_subtitle_filename(sample_movie_identity, "srt")
        assert result == "Avatar (2009).srt"

    def test_tv_subtitle(self, sample_tv_identity):
        result = build_subtitle_filename(sample_tv_identity, "srt", "en")
        assert result == "Money Heist - S02E04.en.srt"
