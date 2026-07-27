"""Tests for the filesystem scanner."""

from pathlib import Path

from reelctl.models import FileCategory
from reelctl.scanner import find_associated_subtitles, scan_directory


class TestScanDirectory:
    """Tests for scan_directory()."""

    def test_scan_empty_directory(self, tmp_path: Path):
        result = scan_directory(tmp_path)
        assert len(result.files) == 0
        assert result.total_size_bytes == 0

    def test_scan_categorizes_video_files(self, media_dir: Path):
        result = scan_directory(media_dir)
        videos = result.video_files
        assert len(videos) >= 3  # Avatar, Matrix, Money Heist (+ movie.mp4)
        for v in videos:
            assert v.category == FileCategory.VIDEO

    def test_scan_categorizes_subtitle_files(self, media_dir: Path):
        result = scan_directory(media_dir)
        subs = result.subtitle_files
        assert len(subs) == 1
        assert subs[0].extension == "srt"

    def test_scan_categorizes_junk_files(self, media_dir: Path):
        result = scan_directory(media_dir)
        junk = result.junk_files
        assert len(junk) >= 1

    def test_scan_ignores_macos_appledouble_files(self, tmp_path: Path):
        (tmp_path / "._Nowhere.2023.720p.mkv").write_bytes(b"\x00" * 4096)
        (tmp_path / "Nowhere.2023.720p.mkv").write_bytes(b"\x00" * 1024 * 1024)
        result = scan_directory(tmp_path)
        assert len(result.video_files) == 1
        assert result.video_files[0].name == "Nowhere.2023.720p.mkv"
        assert len(result.junk_files) == 1
        assert result.junk_files[0].name == "._Nowhere.2023.720p.mkv"

    def test_scan_records_file_sizes(self, media_dir: Path):
        result = scan_directory(media_dir)
        assert result.total_size_bytes > 0
        for f in result.files:
            assert f.size_bytes >= 0

    def test_scan_nonexistent_directory(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            scan_directory(Path("/nonexistent/path"))

    def test_scan_duration_is_recorded(self, media_dir: Path):
        result = scan_directory(media_dir)
        assert result.scan_duration_seconds >= 0


class TestFindAssociatedSubtitles:
    """Tests for find_associated_subtitles()."""

    def test_finds_matching_subtitle(self, media_dir: Path):
        result = scan_directory(media_dir)
        avatar = [v for v in result.video_files if "Avatar" in v.name][0]
        subs = find_associated_subtitles(avatar, result.subtitle_files)
        assert len(subs) == 1
        assert "en.srt" in subs[0].name

    def test_no_subtitle_for_unmatched_video(self, media_dir: Path):
        result = scan_directory(media_dir)
        matrix = [v for v in result.video_files if "Matrix" in v.name][0]
        subs = find_associated_subtitles(matrix, result.subtitle_files)
        assert len(subs) == 0
