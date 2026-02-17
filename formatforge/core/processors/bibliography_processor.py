"""
FormatForge - Bibliography Processor
پردازشگر کتاب‌نامه

Reads .bib files, converts entries to structured data,
replaces cite commands with MDX links, and generates
bibliography sections in configurable citation styles.

Rules:
- ZWNJ must never be removed
- Persian and English entries detected and handled separately
- Citation styles: APA, IEEE, or custom
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from formatforge.core.processors.base import (
    BaseProcessor,
    ProcessorContext,
    ProcessorError,
)

logger = logging.getLogger("formatforge.processors.bibliography")

ZWNJ = "\u200c"

# Persian Unicode range for language detection
_RE_PERSIAN_CHAR = re.compile(
    r"[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff]"
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class BibEntry:
    """
    یک مدخل کتاب‌نامه.
    A single bibliography entry.
    """
    entry_id: str
    entry_type: str = "article"
    author: str = ""
    title: str = ""
    year: str = ""
    publisher: str = ""
    journal: str = ""
    volume: str = ""
    pages: str = ""
    url: str = ""
    doi: str = ""
    language: str = "en"
    raw_fields: dict[str, str] = field(default_factory=dict)

    @property
    def author_short(self) -> str:
        """نام کوتاه نویسنده (نام خانوادگی اول)."""
        if not self.author:
            return "?"
        parts = self.author.split(" and ")
        first = parts[0].strip()
        if "," in first:
            return first.split(",")[0].strip()
        words = first.split()
        return words[-1] if words else "?"

    @property
    def cite_label(self) -> str:
        """برچسب ارجاع: [نویسنده, سال]."""
        return self.author_short + ", " + (self.year or "n.d.")

    def to_dict(self) -> dict[str, str]:
        """تبدیل به دیکشنری."""
        return {
            "id": self.entry_id,
            "type": self.entry_type,
            "author": self.author,
            "title": self.title,
            "year": self.year,
            "publisher": self.publisher,
            "journal": self.journal,
            "volume": self.volume,
            "pages": self.pages,
            "url": self.url,
            "doi": self.doi,
            "language": self.language,
        }


@dataclass
class BibStats:
    """آمار کتاب‌نامه. / Bibliography statistics."""
    entry_count: int = 0
    persian_count: int = 0
    english_count: int = 0
    cite_count: int = 0
    types: dict[str, int] = field(default_factory=dict)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Regex Patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# BibTeX entry: @type{id, ... }
RE_BIB_ENTRY = re.compile(
    r"@(\w+)\s*\{\s*([^,\s]+)\s*,\s*(.*?)\n\}",
    re.DOTALL,
)

# BibTeX field: key = {value} or key = "value"
RE_BIB_FIELD = re.compile(
    r"(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}"
    r'|"([^"]*)")',
)

# LaTeX cite commands
RE_CITE = re.compile(
    r"\\cite(?:\[([^\]]*)\])?\{([^}]+)\}",
)

RE_CITEP = re.compile(
    r"\\citep(?:\[([^\]]*)\])?\{([^}]+)\}",
)

RE_CITET = re.compile(
    r"\\citet(?:\[([^\]]*)\])?\{([^}]+)\}",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def detect_entry_language(entry: BibEntry) -> str:
    """
    تشخیص زبان مدخل.
    Detect entry language from title and author fields.
    """
    text = entry.title + " " + entry.author
    persian_chars = len(_RE_PERSIAN_CHAR.findall(text))
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha == 0:
        return "en"
    ratio = persian_chars / total_alpha
    return "fa" if ratio > 0.3 else "en"


def _clean_bibtex_value(val: str) -> str:
    """پاکسازی مقدار BibTeX."""
    if not val:
        return ""
    result = val.strip()
    # Remove surrounding braces
    while result.startswith("{") and result.endswith("}"):
        result = result[1:-1].strip()
    return result


def parse_bib_content(bib_text: str) -> list[BibEntry]:
    """
    تجزیه محتوای BibTeX به لیست مدخل‌ها.
    Parse BibTeX content into list of BibEntry.

    Args:
        bib_text: محتوای فایل .bib

    Returns:
        لیست BibEntry
    """
    entries: list[BibEntry] = []

    for m in RE_BIB_ENTRY.finditer(bib_text):
        entry_type = m.group(1).lower()
        entry_id = m.group(2).strip()
        body = m.group(3)

        raw: dict[str, str] = {}
        for fm in RE_BIB_FIELD.finditer(body):
            key = fm.group(1).lower()
            val = fm.group(2) if fm.group(2) is not None else fm.group(3)
            raw[key] = _clean_bibtex_value(val or "")

        entry = BibEntry(
            entry_id=entry_id,
            entry_type=entry_type,
            author=raw.get("author", ""),
            title=raw.get("title", ""),
            year=raw.get("year", ""),
            publisher=raw.get("publisher", ""),
            journal=raw.get("journal", ""),
            volume=raw.get("volume", ""),
            pages=raw.get("pages", ""),
            url=raw.get("url", ""),
            doi=raw.get("doi", ""),
            raw_fields=raw,
        )
        entry.language = detect_entry_language(entry)
        entries.append(entry)

    return entries


def parse_bib_file(bib_path: Path) -> list[BibEntry]:
    """
    خواندن و تجزیه فایل .bib.
    Read and parse a .bib file.
    """
    if not bib_path.exists():
        raise ProcessorError(
            "فایل bib یافت نشد: " + str(bib_path)
        )
    content = bib_path.read_text(encoding="utf-8-sig")
    return parse_bib_content(content)


def entries_to_json(
    entries: list[BibEntry],
    output_path: Optional[Path] = None,
) -> str:
    """
    تبدیل مدخل‌ها به JSON.
    Convert entries to JSON string. Optionally write to file.
    """
    data = [e.to_dict() for e in entries]
    json_str = json.dumps(
        data, ensure_ascii=False, indent=2,
    )
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str, encoding="utf-8")
        logger.info("JSON written: %s", output_path)
    return json_str


def format_entry_apa(entry: BibEntry) -> str:
    """
    فرمت APA یک مدخل.
    Format a single entry in APA style.
    """
    parts: list[str] = []
    if entry.author:
        parts.append(entry.author)
    if entry.year:
        parts.append("(" + entry.year + ").")
    if entry.title:
        parts.append("*" + entry.title + "*.")
    if entry.journal:
        parts.append(entry.journal + ".")
    if entry.publisher:
        parts.append(entry.publisher + ".")
    if entry.url:
        parts.append(entry.url)
    return " ".join(parts)


def format_entry_ieee(entry: BibEntry) -> str:
    """
    فرمت IEEE یک مدخل.
    Format a single entry in IEEE style.
    """
    parts: list[str] = []
    if entry.author:
        parts.append(entry.author + ",")
    if entry.title:
        parts.append('"' + entry.title + '",')
    if entry.journal:
        parts.append("*" + entry.journal + "*,")
    if entry.volume:
        parts.append("vol. " + entry.volume + ",")
    if entry.pages:
        parts.append("pp. " + entry.pages + ",")
    if entry.year:
        parts.append(entry.year + ".")
    if entry.url:
        parts.append(entry.url)
    return " ".join(parts)


def generate_bibliography_mdx(
    entries: list[BibEntry],
    style: str = "apa",
) -> str:
    """
    تولید بخش کتاب‌نامه MDX.
    Generate the bibliography section in MDX.

    Args:
        entries: لیست مدخل‌ها
        style: سبک ارجاع (apa/ieee)

    Returns:
        بخش کتاب‌نامه MDX
    """
    formatter = format_entry_apa if style == "apa" else format_entry_ieee

    lines: list[str] = []
    lines.append("## کتاب‌نامه")
    lines.append("")

    # Persian entries first
    fa_entries = [e for e in entries if e.language == "fa"]
    en_entries = [e for e in entries if e.language != "fa"]

    if fa_entries:
        lines.append("### منابع فارسی")
        lines.append("")
        for entry in fa_entries:
            anchor = '<span id="ref-' + entry.entry_id + '"></span>'
            lines.append(
                anchor + " " + formatter(entry)
            )
            lines.append("")

    if en_entries:
        if fa_entries:
            lines.append("### منابع انگلیسی")
            lines.append("")
        for entry in en_entries:
            anchor = '<span id="ref-' + entry.entry_id + '"></span>'
            lines.append(
                anchor + " " + formatter(entry)
            )
            lines.append("")

    return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BibliographyProcessor Class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class BibliographyProcessor(BaseProcessor):
    r"""
    پردازشگر کتاب‌نامه.
    Converts \cite commands to MDX links and generates
    bibliography section.
    """

    name: str = "bibliography"
    description: str = "Bibliography processor / پردازشگر کتاب‌نامه"
    priority: int = 35  # after link (30)

    def __init__(
        self,
        config: Any = None,
        bib_entries: Optional[list[BibEntry]] = None,
        style: str = "apa",
    ) -> None:
        """مقداردهی پردازشگر کتاب‌نامه."""
        super().__init__(config)
        self._entries: list[BibEntry] = bib_entries or []
        self._entries_map: dict[str, BibEntry] = {
            e.entry_id: e for e in self._entries
        }
        self._style = style
        self._stats = BibStats()

    def load_bib(self, bib_path: Path) -> None:
        """بارگذاری فایل .bib."""
        self._entries = parse_bib_file(bib_path)
        self._entries_map = {
            e.entry_id: e for e in self._entries
        }
        self._logger.info(
            "بارگذاری %d مدخل از %s",
            len(self._entries), bib_path,
        )

    def load_bib_content(self, bib_text: str) -> None:
        """بارگذاری از متن BibTeX."""
        self._entries = parse_bib_content(bib_text)
        self._entries_map = {
            e.entry_id: e for e in self._entries
        }

    def can_process(
        self, content: str, context: ProcessorContext,
    ) -> bool:
        """آیا محتوا شامل ارجاع است؟"""
        if not self.enabled:
            return False
        return (
            r"\cite" in content
            or r"\citep" in content
            or r"\citet" in content
        )

    def process(
        self, content: str, context: ProcessorContext,
    ) -> str:
        """پردازش اصلی کتاب‌نامه."""
        zwnj_before = content.count(ZWNJ)
        self._stats = BibStats(
            entry_count=len(self._entries),
        )

        self._logger.info(
            "شروع پردازش کتاب‌نامه — entries=%d, ZWNJ=%d",
            len(self._entries), zwnj_before,
        )

        # Count entry types and languages
        for entry in self._entries:
            t = entry.entry_type
            self._stats.types[t] = self._stats.types.get(t, 0) + 1
            if entry.language == "fa":
                self._stats.persian_count += 1
            else:
                self._stats.english_count += 1

        # Convert cite commands
        content = self._convert_cite(content)
        content = self._convert_citep(content)
        content = self._convert_citet(content)

        # Append bibliography section if entries exist
        if self._entries:
            bib_section = generate_bibliography_mdx(
                self._entries, self._style,
            )
            content = (
                content.rstrip() + "\n\n" + bib_section
            )

        self._logger.info(
            "آمار: cites=%d, entries=%d (fa=%d, en=%d)",
            self._stats.cite_count,
            self._stats.entry_count,
            self._stats.persian_count,
            self._stats.english_count,
        )

        # ZWNJ check
        zwnj_after = content.count(ZWNJ)
        if zwnj_after != zwnj_before:
            context.add_warning(
                "⚠ [bibliography] ZWNJ: "
                + str(zwnj_before) + " -> " + str(zwnj_after)
            )

        return content

    # ─── Cite conversion methods ─────────

    def _get_label(self, key: str, opt: str = "") -> str:
        """ساخت برچسب ارجاع برای یک کلید."""
        entry = self._entries_map.get(key)
        if entry:
            label = entry.cite_label
        else:
            label = key
        if opt:
            label = label + ", " + opt
        return label

    def _convert_cite(self, content: str) -> str:
        r"""Convert \cite to [author, year](#ref-key)."""
        def _repl(m: re.Match) -> str:
            self._stats.cite_count += 1
            opt = m.group(1) or ""
            raw_keys = m.group(2)
            parts: list[str] = []
            for k in raw_keys.split(","):
                k = k.strip()
                if not k:
                    continue
                label = self._get_label(k, opt)
                parts.append(
                    "[" + label + "](#ref-" + k + ")"
                )
            return "; ".join(parts)
        return RE_CITE.sub(_repl, content)

    def _convert_citep(self, content: str) -> str:
        r"""Convert \citep to (author, year)."""
        def _repl(m: re.Match) -> str:
            self._stats.cite_count += 1
            opt = m.group(1) or ""
            raw_keys = m.group(2)
            parts: list[str] = []
            for k in raw_keys.split(","):
                k = k.strip()
                if not k:
                    continue
                label = self._get_label(k, opt)
                parts.append(
                    "[" + label + "](#ref-" + k + ")"
                )
            return "(" + "; ".join(parts) + ")"
        return RE_CITEP.sub(_repl, content)

    def _convert_citet(self, content: str) -> str:
        r"""Convert \citet to Author (year)."""
        def _repl(m: re.Match) -> str:
            self._stats.cite_count += 1
            opt = m.group(1) or ""
            raw_keys = m.group(2)
            parts: list[str] = []
            for k in raw_keys.split(","):
                k = k.strip()
                if not k:
                    continue
                entry = self._entries_map.get(k)
                if entry:
                    name = entry.author_short
                    yr = entry.year or "n.d."
                else:
                    name = k
                    yr = ""
                link = (
                    name + " "
                    + "[(" + yr + ")](#ref-" + k + ")"
                )
                if opt:
                    link = link + " " + opt
                parts.append(link)
            return "; ".join(parts)
        return RE_CITET.sub(_repl, content)