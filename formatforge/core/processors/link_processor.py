"""
FormatForge - Link and Reference Processor
پردازشگر لینک‌ها و ارجاعات

Converts LaTeX links (href, url, ref, cref, cite, footnote)
and HTML anchor tags to MDX format. Collects labels and resolves
cross-references between chapters.

Rules:
- ZWNJ (U+200C) must never be removed
- Cross-chapter refs become relative MDX links
- Footnotes become [^fn-N] format
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from formatforge.core.processors.base import (
    BaseProcessor,
    ProcessorContext,
    ProcessorError,
)

logger = logging.getLogger("formatforge.processors.link")

ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class LabelInfo:
    """اطلاعات یک برچسب. / Label information."""
    label: str
    label_id: str = ""
    label_type: str = "unknown"
    line_number: int = 0

    def __post_init__(self) -> None:
        if not self.label_id:
            self.label_id = _label_to_id(self.label)


@dataclass
class FootnoteInfo:
    """اطلاعات یک پانویس. / Footnote information."""
    index: int
    text: str
    is_ltr: bool = False
    line_number: int = 0


@dataclass
class LinkStats:
    """آمار لینک‌ها و ارجاعات. / Link statistics."""
    href_count: int = 0
    url_count: int = 0
    ref_count: int = 0
    cref_count: int = 0
    cite_count: int = 0
    footnote_count: int = 0
    html_link_count: int = 0

    @property
    def total(self) -> int:
        """مجموع لینک‌ها."""
        return (
            self.href_count + self.url_count + self.ref_count
            + self.cref_count + self.cite_count
            + self.footnote_count + self.html_link_count
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Compiled Regex Patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RE_HREF = re.compile(
    r"\\href\{([^}]+)\}\{([^}]*)\}",
)
RE_URL = re.compile(
    r"\\url\{([^}]+)\}",
)
RE_REF = re.compile(
    r"\\ref\{([^}]+)\}",
)
RE_CREF = re.compile(
    r"\\cref\{([^}]+)\}",
)
RE_CITE = re.compile(
    # r"\\cite(?:$$([^$$]*)\])?\{([^}]+)\}",
    r"\\cite(?:\[([^\]]*)\])?\{([^}]+)\}",
)
RE_FOOTNOTE = re.compile(
    r"\\footnote\{((?:[^{}]|\{[^{}]*\})*)\}",
)
RE_LTR_FOOTNOTE = re.compile(
    r"\\LTRfootnote\{((?:[^{}]|\{[^{}]*\})*)\}",
)
RE_HTML_LINK = re.compile(
    r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>'
    r"(.*?)</a>",
    re.DOTALL,
)
RE_LABEL = re.compile(
    r"\\label\{([^}]+)\}",
)

_LABEL_TYPE_MAP: dict[str, str] = {
    "eq": "معادله",
    "fig": "شکل",
    "tab": "جدول",
    "sec": "بخش",
    "ch": "فصل",
    "thm": "قضیه",
    "lem": "لم",
    "def": "تعریف",
    "lst": "کد",
    "alg": "الگوریتم",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _label_to_id(label: str) -> str:
    """تبدیل label لاتک به id معتبر MDX."""
    return label.replace(":", "-").replace("_", "-").strip()


def _detect_label_type(label: str) -> str:
    """تشخیص نوع label از پیشوند."""
    prefix = label.split(":")[0] if ":" in label else ""
    return _LABEL_TYPE_MAP.get(prefix, "")


def collect_labels(
    text: str,
    source_format: str = "latex",
) -> dict[str, LabelInfo]:
    r"""
    جمع‌آوری تمام label‌ها از متن.
    Collect all \label{} from text.

    Args:
        text: متن ورودی
        source_format: فرمت منبع

    Returns:
        دیکشنری label: LabelInfo
    """
    labels: dict[str, LabelInfo] = {}
    for m in RE_LABEL.finditer(text):
        label = m.group(1)
        labels[label] = LabelInfo(
            label=label,
            label_type=_detect_label_type(label),
            line_number=text[:m.start()].count("\n") + 1,
        )
    return labels


def collect_citations(
    text: str,
    source_format: str = "latex",
) -> list[str]:
    r"""
    جمع‌آوری کلیدهای ارجاع.
    Collect all \cite{key} keys from text.
    """
    keys: list[str] = []
    for m in RE_CITE.finditer(text):
        raw = m.group(2)
        for k in raw.split(","):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys


def collect_footnotes(
    text: str,
    source_format: str = "latex",
) -> list[FootnoteInfo]:
    r"""
    جمع‌آوری تمام پانویس‌ها.
    Collect all \footnote{} and \LTRfootnote{} from text.
    """
    footnotes: list[FootnoteInfo] = []
    idx = 1

    for m in RE_FOOTNOTE.finditer(text):
        footnotes.append(FootnoteInfo(
            index=idx,
            text=m.group(1).strip(),
            is_ltr=False,
            line_number=text[:m.start()].count("\n") + 1,
        ))
        idx += 1

    for m in RE_LTR_FOOTNOTE.finditer(text):
        footnotes.append(FootnoteInfo(
            index=idx,
            text=m.group(1).strip(),
            is_ltr=True,
            line_number=text[:m.start()].count("\n") + 1,
        ))
        idx += 1

    footnotes.sort(key=lambda f: f.line_number)
    for i, fn in enumerate(footnotes, 1):
        fn.index = i

    return footnotes


def resolve_cross_references(
    content: str,
    labels_map: dict[str, str],
) -> str:
    r"""
    جایگزینی ارجاعات با لینک‌های واقعی.
    Replace \ref and \cref with actual links using labels_map.

    Args:
        content: محتوا با ارجاعات
        labels_map: label to target_path_or_anchor

    Returns:
        محتوا با لینک‌های حل‌شده
    """
    def _resolve_ref(m: re.Match) -> str:
        label = m.group(1)
        lid = _label_to_id(label)
        target = labels_map.get(label, "#" + lid)
        return "[" + lid + "](" + target + ")"

    def _resolve_cref(m: re.Match) -> str:
        label = m.group(1)
        lid = _label_to_id(label)
        ltype = _detect_label_type(label)
        target = labels_map.get(label, "#" + lid)
        if ltype:
            return "[" + ltype + " " + lid + "](" + target + ")"
        return "[" + lid + "](" + target + ")"

    result = RE_REF.sub(_resolve_ref, content)
    result = RE_CREF.sub(_resolve_cref, result)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LinkProcessor Class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class LinkProcessor(BaseProcessor):
    r"""
    پردازشگر لینک‌ها و ارجاعات.
    Converts LaTeX/HTML links and references to MDX.

    Handles: \href, \url, \ref, \cref, \cite,
    \footnote, \LTRfootnote, HTML <a>.
    """

    name: str = "link"
    description: str = "Link and reference processor"
    priority: int = 30

    def __init__(self, config: Any = None) -> None:
        """مقداردهی پردازشگر لینک."""
        super().__init__(config)
        self._footnote_counter: int = 0
        self._footnote_defs: list[str] = []
        self._stats = LinkStats()

    def can_process(
        self, content: str, context: ProcessorContext,
    ) -> bool:
        """آیا محتوا شامل لینک یا ارجاع است؟"""
        if not self.enabled:
            return False
        indicators = (
            r"\href{", r"\url{", r"\ref{", r"\cref{",
            r"\cite", r"\footnote{", r"\LTRfootnote{",
            "<a ",
        )
        return any(ind in content for ind in indicators)

    def process(
        self, content: str, context: ProcessorContext,
    ) -> str:
        """پردازش اصلی لینک‌ها و ارجاعات."""
        zwnj_before = content.count(ZWNJ)
        self._footnote_counter = 0
        self._footnote_defs = []
        self._stats = LinkStats()

        self._logger.info(
            "شروع پردازش لینک — ZWNJ=%d", zwnj_before,
        )

        content = self._convert_href(content)
        content = self._convert_url(content)
        content = self._convert_refs(content, context)
        content = self._convert_crefs(content, context)
        content = self._convert_cites(content, context)
        content = self._convert_footnotes(content)
        content = self._convert_ltr_footnotes(content)
        content = self._convert_html_links(content)

        if self._footnote_defs:
            content = (
                content.rstrip()
                + "\n\n"
                + "\n".join(self._footnote_defs)
                + "\n"
            )

        context.links_processed = self._stats.total
        context.footnotes_processed = self._stats.footnote_count
        self._logger.info(
            "آمار: total=%d", self._stats.total,
        )

        zwnj_after = content.count(ZWNJ)
        if zwnj_after != zwnj_before:
            context.add_warning(
                "⚠ [link] ZWNJ: "
                + str(zwnj_before) + " → " + str(zwnj_after)
            )
        return content

    # ─── Conversion methods ──────────────

    def _convert_href(self, content: str) -> str:
        r"""Convert \href{url}{text} to [text](url)."""
        def _repl(m: re.Match) -> str:
            self._stats.href_count += 1
            return "[" + m.group(2) + "](" + m.group(1) + ")"
        return RE_HREF.sub(_repl, content)

    def _convert_url(self, content: str) -> str:
        r"""Convert \url{url} to [url](url)."""
        def _repl(m: re.Match) -> str:
            self._stats.url_count += 1
            url = m.group(1)
            return "[" + url + "](" + url + ")"
        return RE_URL.sub(_repl, content)

    def _convert_refs(
        self, content: str, context: ProcessorContext,
    ) -> str:
        r"""Convert \ref{label} to [id](#id)."""
        def _repl(m: re.Match) -> str:
            self._stats.ref_count += 1
            label = m.group(1)
            lid = _label_to_id(label)
            context.labels.setdefault(label, lid)
            return "[" + lid + "](#" + lid + ")"
        return RE_REF.sub(_repl, content)

    def _convert_crefs(
        self, content: str, context: ProcessorContext,
    ) -> str:
        r"""Convert \cref{label} to [type id](#id)."""
        def _repl(m: re.Match) -> str:
            self._stats.cref_count += 1
            label = m.group(1)
            lid = _label_to_id(label)
            ltype = _detect_label_type(label)
            context.labels.setdefault(label, lid)
            if ltype:
                return (
                    "[" + ltype + " " + lid
                    + "](#" + lid + ")"
                )
            return "[" + lid + "](#" + lid + ")"
        return RE_CREF.sub(_repl, content)

    def _convert_cites(
        self, content: str, context: ProcessorContext,
    ) -> str:
        r"""Convert \cite[opt]{key} to [^cite-key]."""
        def _repl(m: re.Match) -> str:
            self._stats.cite_count += 1
            opt = m.group(1) or ""
            raw_keys = m.group(2)
            parts: list[str] = []
            for k in raw_keys.split(","):
                k = k.strip()
                if k:
                    cid = "cite-" + _label_to_id(k)
                    parts.append("[^" + cid + "]")
            result = ", ".join(parts)
            if opt:
                result = result + " (" + opt + ")"
            return result
        return RE_CITE.sub(_repl, content)

    def _next_fn_id(self) -> str:
        """شماره بعدی پانویس."""
        self._footnote_counter += 1
        return "fn-" + str(self._footnote_counter)

    def _convert_footnotes(self, content: str) -> str:
        r"""Convert \footnote{text} to [^fn-N]."""
        def _repl(m: re.Match) -> str:
            self._stats.footnote_count += 1
            fn_id = self._next_fn_id()
            text = m.group(1).strip()
            self._footnote_defs.append(
                "[^" + fn_id + "]: " + text
            )
            return "[^" + fn_id + "]"
        return RE_FOOTNOTE.sub(_repl, content)

    def _convert_ltr_footnotes(self, content: str) -> str:
        r"""Convert \LTRfootnote{text} to [^fn-N] with LTR."""
        def _repl(m: re.Match) -> str:
            self._stats.footnote_count += 1
            fn_id = self._next_fn_id()
            text = m.group(1).strip()
            ltr_text = (
                '<span dir="ltr">' + text + "</span>"
            )
            self._footnote_defs.append(
                "[^" + fn_id + "]: " + ltr_text
            )
            return "[^" + fn_id + "]"
        return RE_LTR_FOOTNOTE.sub(_repl, content)

    def _convert_html_links(self, content: str) -> str:
        """Convert <a href> to [text](url)."""
        def _repl(m: re.Match) -> str:
            self._stats.html_link_count += 1
            url = m.group(1)
            text = m.group(2).strip()
            if not text:
                text = url
            return "[" + text + "](" + url + ")"
        return RE_HTML_LINK.sub(_repl, content)