"""Tests for filename parser."""

from reelctl.models import MediaType
from reelctl.parser import parse_filename


class TestParseFilename:
    """Tests for parse_filename()."""

    def test_parse_movie_with_year_and_quality(self):
        result = parse_filename("Avatar.2009.2160p.BluRay.x265.mkv")
        assert result.title == "Avatar"
        assert result.year == 2009
        assert result.media_type == MediaType.MOVIE

    def test_parse_tv_episode(self):
        result = parse_filename("Money.Heist.S02E04.1080p.WEB-DL.mkv")
        assert result.title == "Money Heist"
        assert result.season == 2
        assert result.episode == 4
        assert result.media_type == MediaType.TV

    def test_parse_movie_without_year(self):
        result = parse_filename("The.Matrix.1080p.BluRay.mkv")
        assert result.title is not None
        assert "Matrix" in result.title

    def test_parse_unknown_filename(self):
        result = parse_filename("movie.mp4")
        assert result.original_filename == "movie.mp4"

    def test_parse_tv_with_season_only(self):
        result = parse_filename("Breaking.Bad.S01E01.mkv")
        assert result.season == 1
        assert result.episode == 1
        assert result.media_type == MediaType.TV

    def test_parse_extracts_codec(self):
        result = parse_filename("Avatar.2009.2160p.BluRay.x265.mkv")
        # guessit should detect x265 as codec
        assert result.codec is not None
