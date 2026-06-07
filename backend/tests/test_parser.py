from pathlib import Path

import pytest

from app.models.input import NovelChapter, NovelText
from app.services.parser import parse_docx, parse_file, parse_txt


class TestParseTxt:
    def test_standard_chapters(self, sample_txt_short: Path):
        result = parse_txt(str(sample_txt_short))
        assert isinstance(result, NovelText)
        assert len(result.chapters) == 3
        assert result.chapters[0].chapter_index == 0
        assert "第一章" in result.chapters[0].chapter_title
        assert len(result.chapters[0].raw_text) > 0

    def test_medium_novel(self, sample_txt_medium: Path):
        result = parse_txt(str(sample_txt_medium))
        assert len(result.chapters) == 10
        assert result.title == "sample_medium"

    def test_no_chapters_fallback(self, sample_txt_no_chapters: Path):
        result = parse_txt(str(sample_txt_no_chapters))
        assert len(result.chapters) == 1
        assert result.chapters[0].chapter_title == "全文"

    def test_title_from_filename(self, sample_txt_short: Path):
        result = parse_txt(str(sample_txt_short))
        assert result.title == "sample_short"

    def test_chapter_text_not_empty(self, sample_txt_short: Path):
        result = parse_txt(str(sample_txt_short))
        for ch in result.chapters:
            assert len(ch.raw_text.strip()) > 0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_txt("/nonexistent/file.txt")

    def test_invalid_extension(self, tmp_path: Path):
        p = tmp_path / "test.pdf"
        p.write_text("test", encoding="utf-8")
        with pytest.raises(ValueError, match="不支持的文件格式"):
            parse_txt(str(p))


class TestParseDocx:
    def test_parse_sample_docx(self, sample_docx: Path):
        result = parse_docx(str(sample_docx))
        assert isinstance(result, NovelText)
        assert len(result.chapters) >= 1
        for ch in result.chapters:
            assert ch.chapter_title
            assert len(ch.raw_text) > 0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_docx("/nonexistent/file.docx")

    def test_invalid_extension(self, tmp_path: Path):
        p = tmp_path / "test.txt"
        p.write_text("test", encoding="utf-8")
        with pytest.raises(ValueError, match="不支持的文件格式"):
            parse_docx(str(p))


class TestParseFile:
    def test_dispatches_to_txt(self, sample_txt_short: Path):
        result = parse_file(str(sample_txt_short))
        assert isinstance(result, NovelText)
        assert len(result.chapters) == 3

    def test_dispatches_to_docx(self, sample_docx: Path):
        result = parse_file(str(sample_docx))
        assert isinstance(result, NovelText)
        assert len(result.chapters) >= 1

    def test_unsupported_extension(self):
        with pytest.raises(ValueError, match="不支持的文件格式"):
            parse_file("test.pdf")
