"""
FormatForge - Link Processor Tests
تست‌های پردازشگر لینک‌ها و ارجاعات

Tests for:
- LaTeX href, url conversion
- ref and cref conversion
- cite conversion
- footnote and LTRfootnote conversion
- HTML anchor conversion
- Label collection
- Citation collection
- Footnote collection
- Cross-reference resolution
- ZWNJ preservation
"""

from __future__ import annotations

import pytest

from formatforge.core.processors.link_processor import (
    LinkProcessor,
    LabelInfo,
    FootnoteInfo,
    LinkStats,
    collect_labels,
    collect_citations,
    collect_footnotes,
    resolve_cross_references,
    _label_to_id,
    _detect_label_type,
)
from formatforge.core.processors.base import (
    ProcessorContext,
)

ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def processor() -> LinkProcessor:
    """پردازشگر لینک پیش‌فرض."""
    return LinkProcessor()


@pytest.fixture
def ctx() -> ProcessorContext:
    """زمینه پردازش پیش‌فرض."""
    return ProcessorContext(source_format="latex", language="fa")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: href
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHref:
    r"""تست تبدیل \href."""

    def test_basic_href(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""href ساده."""
        text = r"\href{https://example.com}{کلیک کنید}"
        result = processor.process(text, ctx)
        assert "[" in result
        assert "https://example.com" in result
        assert r"\href" not in result

    def test_href_output_format(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """خروجی فرمت MDX صحیح."""
        text = r"\href{https://test.ir}{لینک}"
        result = processor.process(text, ctx)
        expected = "[لینک](https://test.ir)"
        assert expected in result

    def test_multiple_hrefs(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """چند href در یک متن."""
        text = (
            r"\href{https://a.com}{اول} "
            r"و \href{https://b.com}{دوم}"
        )
        result = processor.process(text, ctx)
        assert "[اول](https://a.com)" in result
        assert "[دوم](https://b.com)" in result

    def test_href_counter(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """شمارنده لینک‌ها."""
        text = (
            r"\href{https://a.com}{x} "
            r"\href{https://b.com}{y}"
        )
        processor.process(text, ctx)
        assert ctx.links_processed >= 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: url
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestUrl:
    r"""تست تبدیل \url."""

    def test_basic_url(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\url{...} → [url](url)."""
        text = r"\url{https://example.com}"
        result = processor.process(text, ctx)
        expected = "[https://example.com](https://example.com)"
        assert expected in result
        assert r"\url" not in result

    def test_url_with_path(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """URL با مسیر."""
        text = r"\url{https://example.com/path/to/page}"
        result = processor.process(text, ctx)
        assert "https://example.com/path/to/page" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: ref
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRef:
    r"""تست تبدیل \ref."""

    def test_basic_ref(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\ref → لینک داخلی."""
        text = r"طبق \ref{eq:euler} داریم"
        result = processor.process(text, ctx)
        assert "[eq-euler](#eq-euler)" in result
        assert r"\ref" not in result

    def test_ref_adds_to_labels(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """ref در context.labels ثبت شود."""
        text = r"\ref{fig:diagram}"
        processor.process(text, ctx)
        assert "fig:diagram" in ctx.labels

    def test_ref_id_conversion(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """label با : و _ تبدیل شود."""
        text = r"\ref{sec:my_section}"
        result = processor.process(text, ctx)
        assert "sec-my-section" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: cref
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCref:
    r"""تست تبدیل \cref."""

    def test_cref_equation(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """cref با پیشوند eq."""
        text = r"\cref{eq:gauss}"
        result = processor.process(text, ctx)
        assert "معادله" in result
        assert "eq-gauss" in result
        assert "#eq-gauss" in result

    def test_cref_figure(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """cref با پیشوند fig."""
        text = r"\cref{fig:arch}"
        result = processor.process(text, ctx)
        assert "شکل" in result
        assert "fig-arch" in result

    def test_cref_table(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """cref با پیشوند tab."""
        text = r"\cref{tab:results}"
        result = processor.process(text, ctx)
        assert "جدول" in result

    def test_cref_theorem(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """cref با پیشوند thm."""
        text = r"\cref{thm:demorgan}"
        result = processor.process(text, ctx)
        assert "قضیه" in result

    def test_cref_no_prefix(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """cref بدون پیشوند شناخته‌شده."""
        text = r"\cref{something}"
        result = processor.process(text, ctx)
        assert "[something](#something)" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: cite
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCite:
    r"""تست تبدیل \cite."""

    def test_basic_cite(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\cite{key} → [^cite-key]."""
        text = r"\cite{knuth1984}"
        result = processor.process(text, ctx)
        assert "[^cite-knuth1984]" in result
        assert r"\cite" not in result

    def test_cite_multiple_keys(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """چند کلید ارجاع."""
        text = r"\cite{smith2020,jones2021}"
        result = processor.process(text, ctx)
        assert "[^cite-smith2020]" in result
        assert "[^cite-jones2021]" in result

    def test_cite_with_option(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\cite[p.~42]{key}."""
        text = r"\cite[p.~42]{book2023}"
        result = processor.process(text, ctx)
        assert "[^cite-book2023]" in result
        assert "p.~42" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: footnote
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFootnote:
    r"""تست تبدیل \footnote."""

    def test_basic_footnote(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\footnote → [^fn-N]."""
        text = r"متن اصلی\footnote{توضیح پانویس} ادامه."
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert "[^fn-1]: توضیح پانویس" in result
        assert r"\footnote" not in result

    def test_multiple_footnotes(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """چند پانویس."""
        text = (
            r"اول\footnote{اولی} "
            r"دوم\footnote{دومی}"
        )
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert "[^fn-2]" in result
        assert "[^fn-1]: اولی" in result
        assert "[^fn-2]: دومی" in result

    def test_footnote_at_end(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """تعاریف پانویس در انتهای خروجی."""
        text = r"متن\footnote{زیرنویس} ادامه"
        result = processor.process(text, ctx)
        lines = result.strip().split("\n")
        last_nonempty = [l for l in lines if l.strip()][-1]
        assert last_nonempty.startswith("[^fn-")

    def test_footnote_counter(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """شمارنده پانویس."""
        text = (
            r"\footnote{a} \footnote{b} \footnote{c}"
        )
        processor.process(text, ctx)
        assert ctx.footnotes_processed == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: LTRfootnote
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLTRFootnote:
    r"""تست تبدیل \LTRfootnote."""

    def test_ltr_footnote(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """LTRfootnote با dir=ltr."""
        text = r"\LTRfootnote{English note}"
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert 'dir="ltr"' in result
        assert "English note" in result

    def test_ltr_footnote_span(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """LTRfootnote درون span."""
        text = r"\LTRfootnote{See RFC 2119}"
        result = processor.process(text, ctx)
        assert "<span" in result
        assert "</span>" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: HTML <a> links
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHTMLLinks:
    """تست تبدیل لینک‌های HTML."""

    def test_basic_html_link(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """HTML anchor ساده."""
        text = '<a href="https://example.com">کلیک</a>'
        result = processor.process(text, ctx)
        assert "[کلیک](https://example.com)" in result
        assert "<a " not in result

    def test_html_link_with_class(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """HTML anchor با class."""
        text = (
            '<a class="ext" href="https://x.com">لینک</a>'
        )
        result = processor.process(text, ctx)
        assert "[لینک](https://x.com)" in result

    def test_empty_text_uses_url(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """متن خالی → URL به عنوان متن."""
        text = '<a href="https://example.com"></a>'
        result = processor.process(text, ctx)
        assert "https://example.com" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: collect_labels
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCollectLabels:
    """تست جمع‌آوری label‌ها."""

    def test_basic_labels(self) -> None:
        """جمع‌آوری label‌های ساده."""
        text = (
            r"\label{eq:euler}" "\n"
            r"\label{fig:diagram}" "\n"
            r"\label{tab:results}"
        )
        labels = collect_labels(text)
        assert len(labels) == 3
        assert "eq:euler" in labels
        assert labels["eq:euler"].label_id == "eq-euler"

    def test_label_type_detection(self) -> None:
        """تشخیص نوع label."""
        text = r"\label{thm:main}"
        labels = collect_labels(text)
        assert labels["thm:main"].label_type == "قضیه"

    def test_empty_text(self) -> None:
        """متن خالی."""
        assert collect_labels("") == {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: collect_citations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCollectCitations:
    """تست جمع‌آوری ارجاعات."""

    def test_basic_citations(self) -> None:
        """جمع‌آوری کلیدهای ارجاع."""
        text = (
            r"\cite{smith2020}" "\n"
            r"\cite{jones2021,brown2022}"
        )
        keys = collect_citations(text)
        assert "smith2020" in keys
        assert "jones2021" in keys
        assert "brown2022" in keys

    def test_no_duplicates(self) -> None:
        """بدون تکرار."""
        text = r"\cite{key1} \cite{key1}"
        keys = collect_citations(text)
        assert keys.count("key1") == 1

    def test_empty(self) -> None:
        """متن خالی."""
        assert collect_citations("") == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: collect_footnotes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCollectFootnotes:
    """تست جمع‌آوری پانویس‌ها."""

    def test_basic_footnotes(self) -> None:
        """جمع‌آوری پانویس‌ها."""
        text = (
            r"اول\footnote{توضیح اول} "
            r"دوم\footnote{توضیح دوم}"
        )
        fns = collect_footnotes(text)
        assert len(fns) == 2
        assert fns[0].text == "توضیح اول"
        assert fns[1].text == "توضیح دوم"

    def test_ltr_footnote_collected(self) -> None:
        """LTRfootnote هم جمع شود."""
        text = r"\LTRfootnote{English text}"
        fns = collect_footnotes(text)
        assert len(fns) == 1
        assert fns[0].is_ltr is True

    def test_mixed_footnotes_ordered(self) -> None:
        """ترتیب صحیح پانویس‌های مختلط."""
        text = (
            r"\footnote{فارسی} "
            r"\LTRfootnote{English}"
        )
        fns = collect_footnotes(text)
        assert len(fns) == 2
        assert fns[0].index == 1
        assert fns[1].index == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: resolve_cross_references
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestResolveCrossReferences:
    """تست حل ارجاعات متقاطع."""

    def test_resolve_with_known_target(self) -> None:
        """ارجاع به هدف شناخته‌شده."""
        content = r"ببینید \ref{eq:main}"
        labels_map = {
            "eq:main": "/ch01#eq-main",
        }
        result = resolve_cross_references(content, labels_map)
        assert "[eq-main](/ch01#eq-main)" in result

    def test_resolve_unknown_target(self) -> None:
        """ارجاع به هدف ناشناخته → anchor محلی."""
        content = r"\ref{eq:unknown}"
        result = resolve_cross_references(content, {})
        assert "[eq-unknown](#eq-unknown)" in result

    def test_resolve_cref_with_type(self) -> None:
        """cref با نوع فارسی."""
        content = r"\cref{fig:arch}"
        labels_map = {"fig:arch": "/ch02#fig-arch"}
        result = resolve_cross_references(content, labels_map)
        assert "شکل" in result
        assert "/ch02#fig-arch" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Helper functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHelpers:
    """تست توابع کمکی."""

    def test_label_to_id(self) -> None:
        """تبدیل label به id."""
        assert _label_to_id("eq:euler") == "eq-euler"
        assert _label_to_id("sec:my_part") == "sec-my-part"
        assert _label_to_id("simple") == "simple"

    def test_detect_label_type_known(self) -> None:
        """نوع شناخته‌شده."""
        assert _detect_label_type("eq:test") == "معادله"
        assert _detect_label_type("fig:test") == "شکل"
        assert _detect_label_type("tab:test") == "جدول"
        assert _detect_label_type("thm:test") == "قضیه"

    def test_detect_label_type_unknown(self) -> None:
        """نوع ناشناخته."""
        assert _detect_label_type("xyz:test") == ""
        assert _detect_label_type("nocolon") == ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: ZWNJ Preservation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestZWNJPreservation:
    """تست حفظ نیم‌فاصله."""

    def test_zwnj_with_href(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """نیم‌فاصله کنار href."""
        text = (
            "لینک" + ZWNJ + "های مفید: "
            + r"\href{https://x.com}{اینجا}"
        )
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, ctx)
        assert result.count(ZWNJ) == zwnj_before

    def test_zwnj_with_footnote(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """نیم‌فاصله کنار footnote."""
        text = (
            "تعریف" + ZWNJ + "های"
            + r"\footnote{توضیح" + ZWNJ + "ات}"
            + " مهم"
        )
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, ctx)
        assert result.count(ZWNJ) == zwnj_before

    def test_zwnj_heavy_document(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """سند سنگین با ZWNJ."""
        text = (
            "کتاب" + ZWNJ + "خانه"
            + ZWNJ + "ی "
            + r"\href{https://lib.ir}{ملی}"
            + " از مرجع" + ZWNJ + "های "
            + r"\cite{ref2020}"
            + " می" + ZWNJ + "باشد."
        )
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, ctx)
        assert result.count(ZWNJ) == zwnj_before


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: can_process
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCanProcess:
    """تست متد can_process."""

    def test_with_href(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(
            r"\href{x}{y}", ctx,
        ) is True

    def test_with_cite(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(
            r"\cite{k}", ctx,
        ) is True

    def test_with_html(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(
            '<a href="x">y</a>', ctx,
        ) is True

    def test_without_links(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process(
            "متن ساده فارسی", ctx,
        ) is False

    def test_disabled(self, ctx: ProcessorContext) -> None:
        p = LinkProcessor()
        p.enabled = False
        assert p.can_process(r"\href{x}{y}", ctx) is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Edge Cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEdgeCases:
    """تست موارد مرزی."""

    def test_empty_content(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        result = processor.process("", ctx)
        assert result == ""

    def test_no_links_passthrough(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        assert processor.can_process("plain text", ctx) is False

    def test_nested_footnote_braces(
        self, processor: LinkProcessor, ctx: ProcessorContext,
    ) -> None:
        """پانویس با {} تودرتو."""
        text = r"\footnote{توضیح {مهم} است}"
        result = processor.process(text, ctx)
        assert "[^fn-1]" in result
        assert "توضیح {مهم} است" in result
