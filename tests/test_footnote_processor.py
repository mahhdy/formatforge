"""
FormatForge - Footnote Processor Tests
تست‌های پردازشگر پانوشت

Tests for:
- Regular footnotes
- LTR footnotes
- Endnotes
- HTML footnotes
- Auto-numbering
- ZWNJ preservation
- Extraction and counting
"""

from __future__ import annotations

import pytest

from formatforge.core.processors.footnote_processor import (
    FootnoteProcessor,
    Footnote,
    FootnoteType,
    FootnoteStats,
    extract_footnotes,
    count_footnotes,
)
from formatforge.core.processors.base import (
    ProcessorContext,
)

ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def processor() -> FootnoteProcessor:
    """پردازشگر پانوشت پیش‌فرض."""
    return FootnoteProcessor()


@pytest.fixture
def ctx() -> ProcessorContext:
    """زمینه پردازش."""
    return ProcessorContext(source_format="latex", language="fa")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Regular Footnotes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRegularFootnotes:
    r"""تست پانوشت عادی \footnote."""

    def test_basic_footnote(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """پانوشت ساده."""
        text = r"متن اصلی\footnote{توضیح اول} ادامه."
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert "[^fn-1]: توضیح اول" in result
        assert r"\footnote" not in result

    def test_multiple_footnotes(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """چند پانوشت."""
        text = (
            r"اول\footnote{یکم} "
            r"دوم\footnote{دوم} "
            r"سوم\footnote{سوم}"
        )
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert "[^fn-2]" in result
        assert "[^fn-3]" in result
        assert "[^fn-1]: یکم" in result
        assert "[^fn-2]: دوم" in result
        assert "[^fn-3]: سوم" in result

    def test_footnote_with_nested_braces(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """پانوشت با {} تودرتو."""
        text = r"\footnote{توضیح {مهم} است}"
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert "توضیح {مهم} است" in result

    def test_footnote_separator(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """تعاریف پانوشت بعد از جداکننده."""
        text = r"متن\footnote{زیرنویس}"
        result = processor.process(text, ctx)
        assert "---" in result

    def test_footnote_counter(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """شمارنده context."""
        text = r"\footnote{a} \footnote{b}"
        processor.process(text, ctx)
        assert ctx.footnotes_processed == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: LTR Footnotes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLTRFootnotes:
    r"""تست پانوشت LTR."""

    def test_ltr_footnote(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """LTRfootnote با dir=ltr."""
        text = r"\LTRfootnote{English note}"
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert 'dir="ltr"' in result
        assert "English note" in result

    def test_ltr_wrapped_in_span(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """LTRfootnote درون span."""
        text = r"\LTRfootnote{See RFC 2119}"
        result = processor.process(text, ctx)
        assert "<span" in result
        assert "</span>" in result

    def test_mixed_regular_and_ltr(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """ترکیب عادی و LTR."""
        text = (
            r"\footnote{فارسی} "
            r"\LTRfootnote{English}"
        )
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert "[^fn-2]" in result
        assert "فارسی" in result
        assert "English" in result
        assert 'dir="ltr"' in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Endnotes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEndnotes:
    r"""تست پی‌نوشت \endnote."""

    def test_basic_endnote(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """endnote ساده."""
        text = r"متن\endnote{توضیح بلند} ادامه."
        result = processor.process(text, ctx)
        assert "<sup>1</sup>" in result
        assert r"\endnote" not in result

    def test_endnote_section(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """بخش پی‌نوشت‌ها ساخته شود."""
        text = r"متن\endnote{اول} و\endnote{دوم}"
        result = processor.process(text, ctx)
        assert "## پی‌نوشت‌ها" in result
        assert "1. اول" in result
        assert "2. دوم" in result

    def test_endnote_numbering(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """شماره‌گذاری endnote."""
        text = (
            r"\endnote{اولی} "
            r"\endnote{دومی} "
            r"\endnote{سومی}"
        )
        result = processor.process(text, ctx)
        assert "<sup>1</sup>" in result
        assert "<sup>2</sup>" in result
        assert "<sup>3</sup>" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: HTML Footnotes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHTMLFootnotes:
    """تست پانوشت HTML."""

    def test_html_footnote_ref(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """تبدیل مرجع HTML."""
        text = (
            '<sup><a href="#fn1">1</a></sup> متن '
            '<li id="fn1">توضیح پانوشت</li>'
        )
        result = processor.process(text, ctx)
        assert "[^fn-" in result
        assert "<sup><a" not in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtraction:
    """تست تابع extract_footnotes."""

    def test_extract_latex(self) -> None:
        """استخراج از LaTeX."""
        text = (
            r"\footnote{اول} "
            r"\LTRfootnote{second} "
            r"\endnote{سوم}"
        )
        fns = extract_footnotes(text, "latex")
        assert len(fns) == 3
        types = {f.fn_type for f in fns}
        assert FootnoteType.REGULAR in types
        assert FootnoteType.LTR in types
        assert FootnoteType.ENDNOTE in types

    def test_extract_ordering(self) -> None:
        """ترتیب بر اساس شماره خط."""
        text = (
            "خط اول\n"
            r"\footnote{دوم}" "\n"
            r"\LTRfootnote{سوم}"
        )
        fns = extract_footnotes(text, "latex")
        assert fns[0].index == 1
        assert fns[1].index == 2

    def test_extract_empty(self) -> None:
        """متن خالی."""
        assert extract_footnotes("", "latex") == []

    def test_count_footnotes(self) -> None:
        """شمارش انواع."""
        text = (
            r"\footnote{a} \footnote{b} "
            r"\LTRfootnote{c} "
            r"\endnote{d}"
        )
        stats = count_footnotes(text, "latex")
        assert stats.regular_count == 2
        assert stats.ltr_count == 1
        assert stats.endnote_count == 1
        assert stats.total == 4


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: ZWNJ Preservation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestZWNJPreservation:
    """تست حفظ نیم‌فاصله."""

    def test_zwnj_in_footnote_text(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """نیم‌فاصله درون پانوشت."""
        fn_text = "توضیح" + ZWNJ + "ات مهم"
        text = r"\footnote{" + fn_text + "}"
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, ctx)
        assert result.count(ZWNJ) == zwnj_before

    def test_zwnj_around_footnote(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """نیم‌فاصله خارج پانوشت."""
        text = (
            "کتاب" + ZWNJ + "خانه"
            + r"\footnote{توضیح}"
            + " برنامه" + ZWNJ + "نویسی"
        )
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, ctx)
        assert result.count(ZWNJ) == zwnj_before

    def test_zwnj_heavy(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """سند سنگین."""
        text = (
            "می" + ZWNJ + "توان"
            + r"\footnote{نمی" + ZWNJ + "شود}"
            + " که" + ZWNJ + " "
            + r"\endnote{باید" + ZWNJ + " بررسی شود}"
        )
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, ctx)
        assert result.count(ZWNJ) >= zwnj_before


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: can_process
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCanProcess:
    """تست can_process."""

    def test_with_footnote(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(
            r"\footnote{x}", ctx,
        ) is True

    def test_with_endnote(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(
            r"\endnote{x}", ctx,
        ) is True

    def test_without(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(
            "متن ساده", ctx,
        ) is False

    def test_disabled(self, ctx: ProcessorContext) -> None:
        p = FootnoteProcessor()
        p.enabled = False
        assert p.can_process(r"\footnote{x}", ctx) is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Edge Cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEdgeCases:
    """تست موارد مرزی."""

    def test_empty(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        result = processor.process("", ctx)
        assert result == ""

    def test_all_types_mixed(
        self, processor: FootnoteProcessor, ctx: ProcessorContext,
    ) -> None:
        """ترکیب همه انواع."""
        text = (
            r"اول\footnote{فارسی} "
            r"دوم\LTRfootnote{English} "
            r"سوم\endnote{پی‌نوشت}"
        )
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert "[^fn-2]" in result
        assert "<sup>1</sup>" in result
        assert "## پی‌نوشت‌ها" in result
        assert ctx.footnotes_processed == 3