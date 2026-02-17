"""
FormatForge - Footnote Processor
پردازشگر پانوشت‌ها و پی‌نوشت‌ها

Handles extraction and conversion of footnotes, LTR footnotes,
endnotes, and HTML footnote markup to MDX-compatible format.

Rules:
- ZWNJ must never be removed
- LTRfootnote gets dir=ltr wrapper
- Endnotes collected in a dedicated section at the end
- Auto-numbering for all footnote types
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from formatforge.core.processors.base import (
    BaseProcessor,
    ProcessorContext,
    ProcessorError,
)

logger = logging.getLogger("formatforge.processors.footnote")

ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FootnoteType(str, Enum):
    """نوع پانوشت. / Footnote type."""
    REGULAR = "regular"
    LTR = "ltr"
    ENDNOTE = "endnote"
    HTML = "html"


@dataclass
class Footnote:
    """
    یک پانوشت استخراج‌شده.
    A single extracted footnote.
    """
    index: int
    text: str
    fn_type: FootnoteType = FootnoteType.REGULAR
    line_number: int = 0
    original: str = ""

    @property
    def fn_id(self) -> str:
        """شناسه پانوشت."""
        return "fn-" + str(self.index)


@dataclass
class FootnoteStats:
    """آمار پانوشت‌ها. / Footnote statistics."""
    regular_count: int = 0
    ltr_count: int = 0
    endnote_count: int = 0
    html_count: int = 0

    @property
    def total(self) -> int:
        """مجموع."""
        return (
            self.regular_count + self.ltr_count
            + self.endnote_count + self.html_count
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Compiled Regex Patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Regular footnote with nested brace support (1 level)
RE_FOOTNOTE = re.compile(
    r"\\footnote\{((?:[^{}]|\{[^{}]*\})*)\}",
)

RE_LTR_FOOTNOTE = re.compile(
    r"\\LTRfootnote\{((?:[^{}]|\{[^{}]*\})*)\}",
)

RE_ENDNOTE = re.compile(
    r"\\endnote\{((?:[^{}]|\{[^{}]*\})*)\}",
)

# HTML footnote: <sup><a href="#fn1">1</a></sup>
# with matching definition: <li id="fn1">text</li>
RE_HTML_FN_REF = re.compile(
    r'<sup[^>]*>\s*<a\s+href=["\']#(fn\d+)["\'][^>]*>'
    r"(\d+)</a>\s*</sup>",
    re.DOTALL,
)

RE_HTML_FN_DEF = re.compile(
    r'<li\s+id=["\']fn(\d+)["\'][^>]*>(.*?)</li>',
    re.DOTALL,
)

# Existing MD footnote references [^something]
RE_MD_FN_REF = re.compile(r"\[\^([^\]]+)\](?!:)")

# Existing MD footnote definitions [^something]: text
RE_MD_FN_DEF = re.compile(r"^\[\^([^\]]+)\]:\s*(.+)", re.MULTILINE)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def extract_footnotes(
    text: str,
    source_format: str = "latex",
) -> list[Footnote]:
    r"""
    استخراج تمام پانوشت‌ها از متن.
    Extract all footnotes from text.

    Supports \footnote, \LTRfootnote, \endnote, HTML sup/a.

    Args:
        text: متن ورودی
        source_format: فرمت منبع

    Returns:
        لیست Footnote مرتب بر اساس شماره خط
    """
    footnotes: list[Footnote] = []
    idx = 0

    if source_format in ("latex", "tex"):
        for m in RE_FOOTNOTE.finditer(text):
            idx += 1
            footnotes.append(Footnote(
                index=idx,
                text=m.group(1).strip(),
                fn_type=FootnoteType.REGULAR,
                line_number=text[:m.start()].count("\n") + 1,
                original=m.group(0),
            ))

        for m in RE_LTR_FOOTNOTE.finditer(text):
            idx += 1
            footnotes.append(Footnote(
                index=idx,
                text=m.group(1).strip(),
                fn_type=FootnoteType.LTR,
                line_number=text[:m.start()].count("\n") + 1,
                original=m.group(0),
            ))

        for m in RE_ENDNOTE.finditer(text):
            idx += 1
            footnotes.append(Footnote(
                index=idx,
                text=m.group(1).strip(),
                fn_type=FootnoteType.ENDNOTE,
                line_number=text[:m.start()].count("\n") + 1,
                original=m.group(0),
            ))

    elif source_format in ("html", "htm"):
        for m in RE_HTML_FN_REF.finditer(text):
            idx += 1
            footnotes.append(Footnote(
                index=idx,
                text="",
                fn_type=FootnoteType.HTML,
                line_number=text[:m.start()].count("\n") + 1,
                original=m.group(0),
            ))

    footnotes.sort(key=lambda f: f.line_number)
    for i, fn in enumerate(footnotes, 1):
        fn.index = i

    return footnotes


def count_footnotes(text: str, source_format: str = "latex") -> FootnoteStats:
    """
    شمارش پانوشت‌ها.
    Count footnotes by type.
    """
    fns = extract_footnotes(text, source_format)
    stats = FootnoteStats()
    for fn in fns:
        if fn.fn_type == FootnoteType.REGULAR:
            stats.regular_count += 1
        elif fn.fn_type == FootnoteType.LTR:
            stats.ltr_count += 1
        elif fn.fn_type == FootnoteType.ENDNOTE:
            stats.endnote_count += 1
        elif fn.fn_type == FootnoteType.HTML:
            stats.html_count += 1
    return stats


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FootnoteProcessor Class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FootnoteProcessor(BaseProcessor):
    r"""
    پردازشگر پانوشت‌ها.
    Converts \footnote, \LTRfootnote, \endnote, HTML footnotes
    to MDX-compatible [^fn-N] format.
    """

    name: str = "footnote"
    description: str = "Footnote processor / پردازشگر پانوشت"
    priority: int = 25  # after math (20), before link (30)

    def __init__(self, config: Any = None) -> None:
        """مقداردهی پردازشگر پانوشت."""
        super().__init__(config)
        self._counter: int = 0
        self._defs: list[str] = []
        self._endnotes: list[str] = []
        self._stats = FootnoteStats()

    def can_process(
        self, content: str, context: ProcessorContext,
    ) -> bool:
        """آیا محتوا شامل پانوشت است؟"""
        if not self.enabled:
            return False
        indicators = (
            r"\footnote{",
            r"\LTRfootnote{",
            r"\endnote{",
            "<sup",
        )
        return any(ind in content for ind in indicators)

    def process(
        self, content: str, context: ProcessorContext,
    ) -> str:
        """پردازش اصلی پانوشت‌ها."""
        zwnj_before = content.count(ZWNJ)
        self._counter = 0
        self._defs = []
        self._endnotes = []
        self._stats = FootnoteStats()

        self._logger.info(
            "شروع پردازش پانوشت — ZWNJ=%d", zwnj_before,
        )

        # 1) Regular footnotes
        content = self._convert_regular(content)

        # 2) LTR footnotes
        content = self._convert_ltr(content)

        # 3) Endnotes
        content = self._convert_endnotes(content)

        # 4) HTML footnotes
        content = self._convert_html_footnotes(content)

        # 5) Append footnote definitions
        if self._defs:
            content = (
                content.rstrip()
                + "\n\n---\n\n"
                + "\n".join(self._defs)
                + "\n"
            )

        # 6) Append endnote section
        if self._endnotes:
            content = (
                content.rstrip()
                + "\n\n## پی‌نوشت‌ها\n\n"
                + "\n".join(self._endnotes)
                + "\n"
            )

        # Update context
        context.footnotes_processed = self._stats.total
        self._logger.info(
            "آمار: total=%d (regular=%d, ltr=%d, "
            "endnote=%d, html=%d)",
            self._stats.total,
            self._stats.regular_count,
            self._stats.ltr_count,
            self._stats.endnote_count,
            self._stats.html_count,
        )

        # ZWNJ check
        zwnj_after = content.count(ZWNJ)
        if zwnj_after != zwnj_before:
            context.add_warning(
                "⚠ [footnote] ZWNJ: "
                + str(zwnj_before) + " -> " + str(zwnj_after)
            )

        return content

    # ─── Conversion methods ──────────────

    def _next_id(self) -> str:
        """شناسه بعدی پانوشت."""
        self._counter += 1
        return "fn-" + str(self._counter)

    def _convert_regular(self, content: str) -> str:
        r"""Convert \footnote{text} to [^fn-N]."""
        def _repl(m: re.Match) -> str:
            self._stats.regular_count += 1
            fn_id = self._next_id()
            text = m.group(1).strip()
            self._defs.append("[^" + fn_id + "]: " + text)
            return "[^" + fn_id + "]"
        return RE_FOOTNOTE.sub(_repl, content)

    def _convert_ltr(self, content: str) -> str:
        r"""Convert \LTRfootnote{text} to [^fn-N] with LTR."""
        def _repl(m: re.Match) -> str:
            self._stats.ltr_count += 1
            fn_id = self._next_id()
            text = m.group(1).strip()
            ltr_text = (
                '<span dir="ltr">' + text + "</span>"
            )
            self._defs.append(
                "[^" + fn_id + "]: " + ltr_text
            )
            return "[^" + fn_id + "]"
        return RE_LTR_FOOTNOTE.sub(_repl, content)

    def _convert_endnotes(self, content: str) -> str:
        r"""Convert \endnote{text} to numbered endnote list."""
        endnote_idx = 0

        def _repl(m: re.Match) -> str:
            nonlocal endnote_idx
            self._stats.endnote_count += 1
            endnote_idx += 1
            text = m.group(1).strip()
            marker = str(endnote_idx)
            self._endnotes.append(
                marker + ". " + text
            )
            return "<sup>" + marker + "</sup>"
        return RE_ENDNOTE.sub(_repl, content)

    def _convert_html_footnotes(self, content: str) -> str:
        """Convert HTML <sup><a> footnotes to MD format."""
        # First collect definitions
        html_defs: dict[str, str] = {}
        for m in RE_HTML_FN_DEF.finditer(content):
            fn_num = m.group(1)
            fn_text = m.group(2).strip()
            # Strip HTML tags from text
            fn_text = re.sub(r"<[^>]+>", "", fn_text).strip()
            html_defs["fn" + fn_num] = fn_text

        # Remove definition list items
        content = RE_HTML_FN_DEF.sub("", content)

        # Convert references
        def _repl(m: re.Match) -> str:
            self._stats.html_count += 1
            fn_anchor = m.group(1)
            fn_id = self._next_id()
            fn_text = html_defs.get(fn_anchor, "")
            if fn_text:
                self._defs.append(
                    "[^" + fn_id + "]: " + fn_text
                )
            return "[^" + fn_id + "]"

        content = RE_HTML_FN_REF.sub(_repl, content)
        return content