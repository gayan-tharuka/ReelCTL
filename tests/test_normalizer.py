"""Tests for quality/source normalization."""

from reelctl.normalizer import normalize_quality, normalize_source, quality_score


class TestNormalizeQuality:
    def test_2160p_to_4k(self):
        assert normalize_quality("2160p") == "4K"

    def test_uhd_to_4k(self):
        assert normalize_quality("UHD") == "4K"

    def test_1080p_unchanged(self):
        assert normalize_quality("1080p") == "1080p"

    def test_720p_unchanged(self):
        assert normalize_quality("720p") == "720p"

    def test_none_returns_none(self):
        assert normalize_quality(None) is None

    def test_unknown_passes_through(self):
        assert normalize_quality("some_random") == "some_random"


class TestNormalizeSource:
    def test_brrip_to_bluray(self):
        assert normalize_source("BRRip") == "BluRay"

    def test_bdrip_to_bluray(self):
        assert normalize_source("BDRip") == "BluRay"

    def test_webrip_to_web(self):
        assert normalize_source("WEBRip") == "WEB"

    def test_webdl_normalized(self):
        assert normalize_source("WEB-DL") == "WEB-DL"

    def test_dvdrip_to_dvd(self):
        assert normalize_source("DVDRip") == "DVD"

    def test_none_returns_none(self):
        assert normalize_source(None) is None


class TestQualityScore:
    def test_4k_bluray_highest(self):
        score = quality_score("4K", "BluRay")
        assert score > quality_score("1080p", "BluRay")

    def test_1080p_better_than_720p(self):
        assert quality_score("1080p", "WEB-DL") > quality_score("720p", "WEB-DL")

    def test_bluray_better_than_web(self):
        assert quality_score("1080p", "BluRay") > quality_score("1080p", "WEB")

    def test_unknown_quality_low_score(self):
        assert quality_score(None, None) == 0
