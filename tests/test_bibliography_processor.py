"""
FormatForge - Bibliography Processor Tests
تستهای پردازشگر کتابنامه

Tests for:
- BibTeX parsing
- Entry language detection
- cite/citep/citet conversion
- APA and IEEE formatting
- Bibliography MDX generation
- JSON export
- ZWNJ preservation
"""

from __future__ import annotations

import json
import pytest

from formatforge.core.processors.bibliography_processor import (
    BibliographyProcessor,
    BibEntry,
    BibStats,
    parse_bib_content,
    detect_entry_language,
    entries_to_json,
    format_entry_apa,
    format_entry_ieee,
    generate_bibliography_mdx,
)
from formatforge.core.processors.base import (
    ProcessorContext,
)

ZWNJ = "\u200c"


# 
# Sample BibTeX data
# 

SAMPLE_BIB = """
@article{knuth1984,
  author = {Donald E. Knuth},
  title = {Literate Programming},
  journal = {The Computer Journal},
  year = {1984},
  volume = {27},
  pages = {97--111},
}

@book{lamport1994,
  author = {Leslie Lamport},
  title = {LaTeX: A Document Preparation System},
  publisher = {Addison-Wesley},
  year = {1994},
}

@article{ahmadi1400,
  author = {احمدی علی and رضایی محمد},
  title = {روشهای نوین پردازش متن فارسی},
  journal = {مجله علوم رایانه},
  year = {1400},
}
"""


# 
# Fixtures
# 


@pytest.fixture
def entries() -> list[BibEntry]:
    """مدخلهای نمونه."""
    return parse_bib_content(SAMPLE_BIB)


@pytest.fixture
def processor(entries: list[BibEntry]) -> BibliographyProcessor:
    """پردازشگر با مدخلهای نمونه."""
    return BibliographyProcessor(bib_entries=entries)


@pytest.fixture
def ctx() -> ProcessorContext:
    """زمینه پردازش."""
    return ProcessorContext(source_format="latex", language="fa")


# 
# Test: BibTeX Parsing
# 


class TestParsing:
    """تست تجزیه BibTeX."""

    def test_parse_count(self, entries: list[BibEntry]) -> None:
        """تعداد مدخلها."""
        assert len(entries) == 3

    def test_parse_article(self, entries: list[BibEntry]) -> None:
        """تجزیه article."""
        knuth = next(e for e in entries if e.entry_id == "knuth1984")
        assert knuth.entry_type == "article"
        assert knuth.author == "Donald E. Knuth"
        assert knuth.title == "Literate Programming"
        assert knuth.year == "1984"
        assert knuth.journal == "The Computer Journal"

    def test_parse_book(self, entries: list[BibEntry]) -> None:
        """تجزیه book."""
        lamport = next(e for e in entries if e.entry_id == "lamport1994")
        assert lamport.entry_type == "book"
        assert lamport.publisher == "Addison-Wesley"

    def test_parse_persian(self, entries: list[BibEntry]) -> None:
        """تجزیه مدخل فارسی."""
        fa = next(e for e in entries if e.entry_id == "ahmadi1400")
        assert fa.year == "1400"
        assert fa.language == "fa"

    def test_empty_bib(self) -> None:
        """BibTeX خالی."""
        assert parse_bib_content("") == []

    def test_author_short(self, entries: list[BibEntry]) -> None:
        """نام کوتاه نویسنده."""
        knuth = next(e for e in entries if e.entry_id == "knuth1984")
        assert knuth.author_short == "Knuth"

    def test_cite_label(self, entries: list[BibEntry]) -> None:
        """برچسب ارجاع."""
        knuth = next(e for e in entries if e.entry_id == "knuth1984")
        assert knuth.cite_label == "Knuth, 1984"


# 
# Test: Language Detection
# 


class TestLanguageDetection:
    """تست تشخیص زبان مدخل."""

    def test_english_entry(self) -> None:
        """مدخل انگلیسی."""
        entry = BibEntry(
            entry_id="test",
            author="John Smith",
            title="Machine Learning Basics",
        )
        assert detect_entry_language(entry) == "en"

    def test_persian_entry(self) -> None:
        """مدخل فارسی."""
        entry = BibEntry(
            entry_id="test",
            author="محمدی رضا",
            title="مقدمهای بر هوش مصنوعی",
        )
        assert detect_entry_language(entry) == "fa"

    def test_empty_fields(self) -> None:
        """فیلدهای خالی."""
        entry = BibEntry(entry_id="test")
        assert detect_entry_language(entry) == "en"


# 
# Test: Cite Conversion
# 


class TestCiteConversion:
    r"""تست تبدیل \cite."""

    def test_basic_cite(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\cite{key}  [author, year](#ref-key)."""
        text = r"مطابق \cite{knuth1984} داریم."
        result = processor.process(text, ctx)
        assert "Knuth, 1984" in result
        assert "#ref-knuth1984" in result
        assert r"\cite" not in result

    def test_cite_unknown_key(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        """کلید ناشناخته."""
        text = r"\cite{unknown2099}"
        result = processor.process(text, ctx)
        assert "unknown2099" in result
        assert "#ref-unknown2099" in result

    def test_cite_multiple(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        """چند کلید."""
        text = r"\cite{knuth1984,lamport1994}"
        result = processor.process(text, ctx)
        assert "Knuth" in result
        assert "Lamport" in result

    def test_citep(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\citep  (author, year)."""
        text = r"\citep{knuth1984}"
        result = processor.process(text, ctx)
        assert "(" in result
        assert ")" in result
        assert "Knuth" in result

    def test_citet(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\citet  Author (year)."""
        text = r"\citet{knuth1984}"
        result = processor.process(text, ctx)
        assert "Knuth" in result
        assert "(1984)" in result


# 
# Test: Formatting
# 


class TestFormatting:
    """تست فرمت ارجاع."""

    def test_apa_format(self, entries: list[BibEntry]) -> None:
        """فرمت APA."""
        knuth = next(e for e in entries if e.entry_id == "knuth1984")
        result = format_entry_apa(knuth)
        assert "Donald E. Knuth" in result
        assert "(1984)" in result
        assert "*Literate Programming*" in result

    def test_ieee_format(self, entries: list[BibEntry]) -> None:
        """فرمت IEEE."""
        knuth = next(e for e in entries if e.entry_id == "knuth1984")
        result = format_entry_ieee(knuth)
        assert "Donald E. Knuth" in result
        assert '"Literate Programming"' in result

    def test_apa_with_url(self) -> None:
        """APA با URL."""
        entry = BibEntry(
            entry_id="web",
            author="Test",
            title="Page",
            year="2024",
            url="https://example.com",
        )
        result = format_entry_apa(entry)
        assert "https://example.com" in result


# 
# Test: MDX Generation
# 


class TestMDXGeneration:
    """تست تولید بخش کتابنامه MDX."""

    def test_bibliography_section(
        self, entries: list[BibEntry],
    ) -> None:
        """بخش کتابنامه ساخته شود."""
        result = generate_bibliography_mdx(entries)
        assert "## " + "کتاب" + ZWNJ + "نامه" in result

    def test_persian_section(
        self, entries: list[BibEntry],
    ) -> None:
        """بخش منابع فارسی."""
        result = generate_bibliography_mdx(entries)
        assert "### منابع فارسی" in result

    def test_english_section(
        self, entries: list[BibEntry],
    ) -> None:
        """بخش منابع انگلیسی."""
        result = generate_bibliography_mdx(entries)
        assert "### منابع انگلیسی" in result

    def test_anchors(
        self, entries: list[BibEntry],
    ) -> None:
        """anchor برای هر مدخل."""
        result = generate_bibliography_mdx(entries)
        assert 'id="ref-knuth1984"' in result
        assert 'id="ref-lamport1994"' in result

    def test_ieee_style(
        self, entries: list[BibEntry],
    ) -> None:
        """سبک IEEE."""
        result = generate_bibliography_mdx(entries, style="ieee")
        assert "## " + "کتاب" + ZWNJ + "نامه" in result

    def test_bibliography_appended(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        """بخش کتابنامه به انتهای خروجی اضافه شود."""
        text = r"مطابق \cite{knuth1984} داریم."
        result = processor.process(text, ctx)
        assert "## " + "کتاب" + ZWNJ + "نامه" in result


# 
# Test: JSON Export
# 


class TestJSONExport:
    """تست خروجی JSON."""

    def test_json_string(
        self, entries: list[BibEntry],
    ) -> None:
        """تولید JSON string."""
        result = entries_to_json(entries)
        data = json.loads(result)
        assert len(data) == 3

    def test_json_fields(
        self, entries: list[BibEntry],
    ) -> None:
        """فیلدها در JSON."""
        result = entries_to_json(entries)
        data = json.loads(result)
        knuth = next(d for d in data if d["id"] == "knuth1984")
        assert knuth["author"] == "Donald E. Knuth"
        assert knuth["year"] == "1984"

    def test_json_persian(
        self, entries: list[BibEntry],
    ) -> None:
        """فارسی در JSON."""
        result = entries_to_json(entries)
        data = json.loads(result)
        fa = next(d for d in data if d["id"] == "ahmadi1400")
        assert fa["language"] == "fa"

    def test_json_file(
        self, entries: list[BibEntry], tmp_path,
    ) -> None:
        """نوشتن فایل JSON."""
        out = tmp_path / "bib.json"
        entries_to_json(entries, out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 3


# 
# Test: load_bib_content
# 


class TestLoadBib:
    """تست بارگذاری BibTeX."""

    def test_load_from_string(self, ctx: ProcessorContext) -> None:
        """بارگذاری از رشته."""
        p = BibliographyProcessor()
        p.load_bib_content(SAMPLE_BIB)
        text = r"\cite{knuth1984}"
        result = p.process(text, ctx)
        assert "Knuth" in result


# 
# Test: ZWNJ Preservation
# 


class TestZWNJPreservation:
    """تست حفظ نیمفاصله."""

    def test_zwnj_around_cite(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        """نیمفاصله کنار cite."""
        text = (
            "کتاب" + ZWNJ + "خانه "
            + r"\cite{knuth1984}"
            + " برنامه" + ZWNJ + "نویسی"
        )
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, ctx)
        # bibliography section may add ZWNJ in Persian headers
        assert result.count(ZWNJ) >= zwnj_before


# 
# Test: can_process
# 


class TestCanProcess:
    """تست can_process."""

    def test_with_cite(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(r"\cite{x}", ctx) is True

    def test_with_citep(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(r"\citep{x}", ctx) is True

    def test_with_citet(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(r"\citet{x}", ctx) is True

    def test_without(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process("متن ساده", ctx) is False

    def test_disabled(self, ctx: ProcessorContext) -> None:
        p = BibliographyProcessor()
        p.enabled = False
        assert p.can_process(r"\cite{x}", ctx) is False


# 
# Test: Edge Cases
# 


class TestEdgeCases:
    """تست موارد مرزی."""

    def test_empty(
        self, processor: BibliographyProcessor, ctx: ProcessorContext,
    ) -> None:
        """محتوای خالی بدون خطا."""
        assert processor.can_process("", ctx) is False

    def test_no_entries_loaded(
        self, ctx: ProcessorContext,
    ) -> None:
        """بدون مدخل بارگذاریشده."""
        p = BibliographyProcessor()
        text = r"\cite{anything}"
        result = p.process(text, ctx)
        assert "anything" in result

    def test_to_dict(self, entries: list[BibEntry]) -> None:
        """تبدیل به dict."""
        d = entries[0].to_dict()
        assert "id" in d
        assert "author" in d
        assert "title" in d