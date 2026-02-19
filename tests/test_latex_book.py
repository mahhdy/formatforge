"""
تست‌های تبدیل‌گر کتاب LaTeX — S09-C1
Tests for formatforge/core/converters/latex_book_converter.py

Coverage:
- Book detection (is_book, detect_structure)
- Chapter splitting (_split_chapters)
- Per-chapter conversion
- _series.json generation
- Cross-chapter reference resolution
- ZWNJ preservation in book context
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from formatforge.core.converters.latex_book_converter import (
    BookConversionResult,
    BookStructure,
    ChapterInfo,
    LaTeXBookConverter,
)
from formatforge.core.converters.latex_parser import ZWNJ

# ─── Path to real test file ──────────────────
_SAMPLE_TEX = Path(__file__).parent / "test_files" / "sample-book.tex"
_HAS_SAMPLE = _SAMPLE_TEX.exists()


# ─── Test fixtures ───────────────────────────

BOOK_TEX = rf"""
\documentclass[12pt]{{book}}
\usepackage{{amsmath}}
\usepackage[extrafootnotefeatures]{{xepersian}}
\settextfont{{Vazirmatn}}
\title{{مبانی منطق ریاضی}}
\author{{علی محمدی}}
\date{{2025-06-15}}
\begin{{document}}
\chapter{{مقدمه}}
این فصل اول است.
$a + b = c$
\section{{بخش{ZWNJ}اول}}
متن بخش اول.

\chapter{{منطق گزاره‌ای}}
این فصل دوم است.
\begin{{theorem}}{{قضیه دمورگان}}{{dm}}
$(A \cup B)^c = A^c \cap B^c$
\end{{theorem}}

\chapter{{نتیجه‌گیری}}
خلاصه مطالب.
\end{{document}}
"""

MULTI_FILE_MAIN_TEX = r"""
\documentclass{book}
\title{Test Book}
\begin{document}
\input{chapter01}
\input{chapter02}
\end{document}
"""

ARTICLE_TEX = r"""
\documentclass{article}
\begin{document}
\section{Introduction}
Hello world.
\end{document}
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestDetection — تشخیص کتاب
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDetection:
    """تست‌های تشخیص کتاب."""

    @pytest.fixture
    def converter(self):
        return LaTeXBookConverter()

    def test_is_book_true(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        assert converter.is_book(f) is True

    def test_is_book_false_article(self, converter, tmp_path):
        f = tmp_path / "article.tex"
        f.write_text(ARTICLE_TEX, encoding="utf-8")
        assert converter.is_book(f) is False

    def test_detect_structure_single(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        assert converter.detect_structure(f) == "single"

    def test_detect_structure_multi(self, converter, tmp_path):
        f = tmp_path / "main.tex"
        f.write_text(MULTI_FILE_MAIN_TEX, encoding="utf-8")
        assert converter.detect_structure(f) == "multi"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestParsing — تحلیل ساختار
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestParsing:
    """تست‌های تحلیل ساختار کتاب."""

    @pytest.fixture
    def converter(self):
        return LaTeXBookConverter()

    def test_parse_book_title(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        book = converter.parse_book(f)
        assert "منطق" in book.title

    def test_parse_book_author(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        book = converter.parse_book(f)
        assert "محمدی" in book.author or "علی" in book.author

    def test_parse_book_lang(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        book = converter.parse_book(f)
        assert book.lang == "fa"

    def test_parse_book_chapters_count(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        book = converter.parse_book(f)
        assert len(book.chapters) == 3

    def test_parse_book_chapter_titles(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        book = converter.parse_book(f)
        titles = [ch.title for ch in book.chapters]
        assert "مقدمه" in titles[0]
        assert "منطق" in titles[1]
        assert "نتیجه" in titles[2]

    def test_parse_book_chapter_slugs(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        book = converter.parse_book(f)
        for ch in book.chapters:
            assert ch.slug.startswith(f"{ch.order:02d}-")

    def test_parse_book_chapter_order(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        book = converter.parse_book(f)
        orders = [ch.order for ch in book.chapters]
        assert orders == [0, 1, 2]

    def test_parse_book_chapter_nodes_not_empty(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        book = converter.parse_book(f)
        for ch in book.chapters:
            assert len(ch.nodes) > 0

    def test_parse_article_as_single_chapter(self, converter, tmp_path):
        """Article (no chapters) treated as single chapter."""
        f = tmp_path / "article.tex"
        f.write_text(ARTICLE_TEX, encoding="utf-8")
        book = converter.parse_book(f)
        assert len(book.chapters) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestConversion — تبدیل کتاب
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConversion:
    """تست‌های تبدیل کتاب."""

    @pytest.fixture
    def converter(self):
        return LaTeXBookConverter()

    def test_convert_book_success(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        assert result.status == "success"

    def test_convert_book_creates_chapters(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        assert result.total_chapters == 3
        assert len(result.chapter_results) == 3

    def test_convert_book_creates_files(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        converter.convert_book(f, out)
        # Find MDX files in the book directory
        book_dir = list(out.iterdir())[0]  # book slug dir
        mdx_files = list(book_dir.glob("*.mdx"))
        assert len(mdx_files) == 3

    def test_convert_book_chapter_has_frontmatter(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        converter.convert_book(f, out)
        book_dir = list(out.iterdir())[0]
        mdx_files = sorted(book_dir.glob("*.mdx"))
        content = mdx_files[0].read_text(encoding="utf-8")
        # Strip BOM
        if content.startswith("\ufeff"):
            content = content[1:]
        assert content.startswith("---\n")

    def test_convert_book_chapter_has_series(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        converter.convert_book(f, out)
        book_dir = list(out.iterdir())[0]
        mdx_files = sorted(book_dir.glob("*.mdx"))
        content = mdx_files[0].read_text(encoding="utf-8")
        assert "series:" in content

    def test_convert_book_chapter_has_math(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        converter.convert_book(f, out)
        book_dir = list(out.iterdir())[0]
        mdx_files = sorted(book_dir.glob("*.mdx"))
        content = mdx_files[0].read_text(encoding="utf-8")
        assert "$" in content

    def test_convert_book_zwnj_preserved(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        converter.convert_book(f, out)
        book_dir = list(out.iterdir())[0]
        mdx_files = sorted(book_dir.glob("*.mdx"))
        # Check first chapter has ZWNJ
        content = mdx_files[0].read_text(encoding="utf-8")
        assert ZWNJ in content

    def test_convert_book_chapter_results_success(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        for ch_result in result.chapter_results:
            assert ch_result.status == "success"

    def test_convert_book_duration(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        assert result.duration_seconds >= 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestSeriesJson — _series.json
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSeriesJson:
    """تست‌های تولید _series.json."""

    @pytest.fixture
    def converter(self):
        return LaTeXBookConverter()

    def test_series_json_created(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        assert result.series_json_path is not None
        assert Path(result.series_json_path).exists()

    def test_series_json_valid(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        data = json.loads(Path(result.series_json_path).read_text(encoding="utf-8"))
        assert "title" in data
        assert "chapters" in data
        assert len(data["chapters"]) == 3

    def test_series_json_chapter_order(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        data = json.loads(Path(result.series_json_path).read_text(encoding="utf-8"))
        orders = [ch["order"] for ch in data["chapters"]]
        assert orders == [0, 1, 2]

    def test_series_json_has_slugs(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        data = json.loads(Path(result.series_json_path).read_text(encoding="utf-8"))
        for ch in data["chapters"]:
            assert "slug" in ch
            assert len(ch["slug"]) > 0

    def test_series_json_has_titles(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        data = json.loads(Path(result.series_json_path).read_text(encoding="utf-8"))
        for ch in data["chapters"]:
            assert "title" in ch
            assert len(ch["title"]) > 0

    def test_series_json_persian_preserved(self, converter, tmp_path):
        f = tmp_path / "book.tex"
        f.write_text(BOOK_TEX, encoding="utf-8")
        out = tmp_path / "output"
        result = converter.convert_book(f, out)
        raw = Path(result.series_json_path).read_text(encoding="utf-8")
        assert "منطق" in raw


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestDataModels — مدل‌های داده
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDataModels:
    """تست‌های مدل‌های داده."""

    def test_chapter_info_creation(self):
        ch = ChapterInfo(order=0, title="Test", slug="00-test")
        assert ch.order == 0
        assert ch.slug == "00-test"

    def test_book_structure_default(self):
        book = BookStructure()
        assert book.chapters == []
        assert book.lang == "fa"

    def test_book_result_default(self):
        result = BookConversionResult()
        assert result.status == "processing"
        assert result.total_chapters == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestRealSampleFile — فایل نمونه واقعی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.mark.skipif(not _HAS_SAMPLE, reason="sample-book.tex not available")
class TestRealSampleFile:
    """تست با فایل نمونه واقعی sample-book.tex."""

    @pytest.fixture(scope="class")
    def converter(self):
        return LaTeXBookConverter()

    @pytest.fixture(scope="class")
    def book(self, converter):
        return converter.parse_book(_SAMPLE_TEX)

    @pytest.fixture(scope="class")
    def conversion_result(self, converter, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("book_output")
        return converter.convert_book(_SAMPLE_TEX, tmp)

    def test_is_book(self, converter):
        assert converter.is_book(_SAMPLE_TEX) is True

    def test_five_chapters(self, book):
        assert len(book.chapters) == 5

    def test_lang_persian(self, book):
        assert book.lang == "fa"

    def test_title_extracted(self, book):
        assert len(book.title) > 0

    def test_conversion_success(self, conversion_result):
        assert conversion_result.status == "success"

    def test_all_chapters_converted(self, conversion_result):
        assert len(conversion_result.chapter_results) == 5
        for ch in conversion_result.chapter_results:
            assert ch.status == "success"

    def test_series_json_has_5_chapters(self, conversion_result):
        data = json.loads(
            Path(conversion_result.series_json_path).read_text(encoding="utf-8")
        )
        assert len(data["chapters"]) == 5

    def test_zwnj_preserved(self, conversion_result):
        """ZWNJ should appear in at least one chapter."""
        for ch in conversion_result.chapter_results:
            if ch.output_path:
                content = Path(ch.output_path).read_text(encoding="utf-8")
                if ZWNJ in content:
                    return
        pytest.fail("ZWNJ not found in any chapter output")
