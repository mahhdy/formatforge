"""
FormatForge - Code Processor
پردازشگر بلوک‌های کد

Converts LaTeX listings/minted/verbatim and HTML <pre><code>
to MDX fenced code blocks. Handles inline code (\texttt, \verb).

قواعد حیاتی:
- بلوک‌های کد همیشه dir="ltr"
- ZWNJ (U+200C) هرگز حذف نشود
- زبان برنامه‌نویسی تشخیص داده شود
- شماره خطوط و عنوان حفظ شود
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

logger = logging.getLogger("formatforge.processors.code")

# ─── Constants / ثابت‌ها ──────────────────────
ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums & Data Models / شمارشی‌ها و مدل‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CodeBlockType(str, Enum):
    """نوع بلوک کد. / Code block type."""

    FENCED = "fenced"
    LATEX_LISTING = "latex_listing"
    LATEX_MINTED = "latex_minted"
    LATEX_VERBATIM = "latex_verbatim"
    HTML_PRE = "html_pre"
    INLINE_TEXTTT = "inline_texttt"
    INLINE_VERB = "inline_verb"


@dataclass
class CodeBlock:
    """
    یک بلوک کد استخراج‌شده.
    A single extracted code block.

    Attributes:
        content: محتوای کد (بدون دلیمیتر)
        block_type: نوع بلوک
        language: زبان برنامه‌نویسی
        title: عنوان (caption)
        label: برچسب برای ارجاع
        line_numbers: آیا شماره خط دارد
        line_number: شماره خط در متن اصلی
        original: رشته اصلی کامل
    """

    content: str
    block_type: CodeBlockType
    language: str = ""
    title: str = ""
    label: str = ""
    line_numbers: bool = False
    line_number: int = 0
    original: str = ""


@dataclass
class CodeStats:
    """
    آمار بلوک‌های کد در سند.
    Statistics about code blocks in a document.
    """

    block_count: int = 0
    inline_count: int = 0
    languages: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        """تعداد کل."""
        return self.block_count + self.inline_count


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Compiled Regex Patterns / الگوهای regex
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# LaTeX \begin{lstlisting}[opts]...\end{lstlisting}
RE_LSTLISTING = re.compile(
    r"\\begin\{lstlisting\}(?:$$([^$$]*)\])?"
    r"(.*?)\\end\{lstlisting\}",
    re.DOTALL,
)

# LaTeX \begin{minted}[opts]{lang}...\end{minted}
RE_MINTED = re.compile(
    r"\\begin\{minted\}(?:$$([^$$]*)\])?"
    r"\{(\w+)\}(.*?)\\end\{minted\}",
    re.DOTALL,
)

# LaTeX \begin{verbatim}...\end{verbatim}
RE_VERBATIM = re.compile(
    r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}",
    re.DOTALL,
)

# HTML <pre><code class="language-X">...</code></pre>
RE_HTML_PRE_CODE = re.compile(
    r"<pre[^>]*>\s*<code"
    r"(?:\s+class=[\"'](?:language-)?(\w+)[\"'])?"
    r"[^>]*>(.*?)</code>\s*</pre>",
    re.DOTALL,
)

# LaTeX \texttt{...}
RE_TEXTTT = re.compile(r"\\texttt\{([^}]*)\}")

# LaTeX \verb|...| (any single-char delimiter)
RE_VERB = re.compile(r"\\verb(.)(.*?)\1")

# Option parsers for lstlisting
RE_LANGUAGE_OPT = re.compile(
    r"language\s*=\s*\{?([^,}\]]+)\}?"
)
RE_CAPTION_OPT = re.compile(
    r"caption\s*=\s*\{?([^,}\]]+)\}?"
)
RE_LABEL_OPT = re.compile(
    r"label\s*=\s*\{?([^,}\]]+)\}?"
)
RE_NUMBERS_OPT = re.compile(
    r"numbers\s*=\s*(left|right)"
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Language Handling / مدیریت زبان
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LANGUAGE_ALIASES: dict[str, str] = {
    "py": "python", "python3": "python",
    "js": "javascript", "ts": "typescript",
    "rb": "ruby", "sh": "bash",
    "shell": "bash", "zsh": "bash",
    "yml": "yaml", "tex": "latex",
    "md": "markdown", "cs": "csharp",
    "c++": "cpp", "c#": "csharp",
    "f#": "fsharp", "htm": "html",
    "objective-c": "objc", "": "text",
}

_LANG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("python", re.compile(
        r"(?:def |import |from |class |if __name__)"
    )),
    ("javascript", re.compile(
        r"(?:function |const |let |var |=>|require\()"
    )),
    ("typescript", re.compile(
        r"(?:interface |type |: string|: number)"
    )),
    ("html", re.compile(
        r"(?:<html|<div|<span|<!DOCTYPE)"
    )),
    ("css", re.compile(
        r"(?:\{[^}]*:[^}]*;|\bcolor:)"
    )),
    ("java", re.compile(
        r"(?:public class |System\.out|void main)"
    )),
    ("cpp", re.compile(
        r"(?:#include|std::|cout|cin|int main\()"
    )),
    ("rust", re.compile(
        r"(?:fn |let mut |println!|impl )"
    )),
    ("go", re.compile(
        r"(?:func |package |fmt\.)"
    )),
    ("bash", re.compile(
        r"(?:#!/bin/|echo |if \[)", re.MULTILINE
    )),
    ("sql", re.compile(
        r"(?:SELECT |FROM |WHERE )", re.IGNORECASE
    )),
    ("latex", re.compile(
        r"(?:\\begin\{|\\end\{|\\section)"
    )),
]


def _normalize_language(lang: str) -> str:
    """نرمال‌سازی نام زبان. / Normalize language name."""
    key = lang.strip().lower()
    return LANGUAGE_ALIASES.get(key, key) if key else "text"


def detect_language(code: str) -> str:
    """
    تشخیص ابتکاری زبان از محتوای کد.
    Heuristic language detection from code content.

    Args:
        code: محتوای کد

    Returns:
        نام زبان تشخیص‌داده‌شده
    """
    if not code or not code.strip():
        return "text"
    for lang, pattern in _LANG_PATTERNS:
        if pattern.search(code):
            return lang
    return "text"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions / توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _parse_listing_options(opts: str) -> dict[str, str]:
    """
    تجزیه گزینه‌های lstlisting.
    Parse lstlisting options like [language=Python,caption=Test].
    """
    result: dict[str, str] = {}
    if not opts:
        return result

    for regex, key in [
        (RE_LANGUAGE_OPT, "language"),
        (RE_CAPTION_OPT, "caption"),
        (RE_LABEL_OPT, "label"),
        (RE_NUMBERS_OPT, "numbers"),
    ]:
        m = regex.search(opts)
        if m:
            result[key] = m.group(1).strip()

    return result


def _label_to_id(label: str) -> str:
    """تبدیل label لاتک به id معتبر MDX."""
    return label.replace(":", "-").replace("_", "-").strip()


def _unescape_html(text: str) -> str:
    """بازگشایی entity‌های HTML."""
    pairs = [
        ("&lt;", "<"), ("&gt;", ">"),
        ("&amp;", "&"), ("&quot;", '"'),
        ("&#39;", "'"), ("&nbsp;", " "),
    ]
    result = text
    for entity, char in pairs:
        result = result.replace(entity, char)
    return result


def _build_fence(
    code: str,
    language: str = "text",
    title: str = "",
    line_numbers: bool = False,
    label: str = "",
) -> str:
    """
    ساخت بلوک کد MDX فنس‌شده.
    Build an MDX fenced code block with metadata.

    Args:
        code: محتوای کد
        language: زبان برنامه‌نویسی
        title: عنوان (اختیاری)
        line_numbers: شماره خطوط
        label: برچسب (اختیاری)

    Returns:
        رشته MDX فنس‌شده
    """
    lang = _normalize_language(language)

    attrs: list[str] = []
    if title:
        attrs.append('title="' + title + '"')
    if line_numbers:
        attrs.append("showLineNumbers")

    attr_str = ""
    if attrs:
        attr_str = " {" + ", ".join(attrs) + "}"

    lines: list[str] = []

    if label:
        lid = _label_to_id(label)
        lines.append("{/* label: " + lid + " */}")
        lines.append("")

    lines.append("```" + lang + attr_str)
    lines.append(code.strip())
    lines.append("```")

    return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Extraction / استخراج
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def extract_code_blocks(
    text: str,
    source_format: str = "latex",
) -> list[CodeBlock]:
    """
    استخراج تمام بلوک‌های کد از متن.
    Extract all code blocks from text based on source format.

    Args:
        text: متن ورودی
        source_format: فرمت منبع (latex/html)

    Returns:
        لیست CodeBlock مرتب بر اساس شماره خط
    """
    blocks: list[CodeBlock] = []

    if source_format in ("latex", "tex"):
        blocks.extend(_extract_latex_blocks(text))
    elif source_format in ("html", "htm"):
        blocks.extend(_extract_html_blocks(text))

    blocks.sort(key=lambda b: b.line_number)
    return blocks


def _extract_latex_blocks(text: str) -> list[CodeBlock]:
    """استخراج بلوک‌های کد LaTeX."""
    blocks: list[CodeBlock] = []

    for m in RE_LSTLISTING.finditer(text):
        opts = _parse_listing_options(m.group(1) or "")
        blocks.append(CodeBlock(
            content=m.group(2).strip(),
            block_type=CodeBlockType.LATEX_LISTING,
            language=opts.get("language", ""),
            title=opts.get("caption", ""),
            label=opts.get("label", ""),
            line_numbers="numbers" in opts,
            line_number=text[:m.start()].count("\n") + 1,
            original=m.group(0),
        ))

    for m in RE_MINTED.finditer(text):
        opts_str = m.group(1) or ""
        opts = _parse_listing_options(opts_str)
        blocks.append(CodeBlock(
            content=m.group(3).strip(),
            block_type=CodeBlockType.LATEX_MINTED,
            language=m.group(2),
            title=opts.get("caption", ""),
            label=opts.get("label", ""),
            line_numbers=(
                "numbers" in opts or "linenos" in opts_str
            ),
            line_number=text[:m.start()].count("\n") + 1,
            original=m.group(0),
        ))

    for m in RE_VERBATIM.finditer(text):
        blocks.append(CodeBlock(
            content=m.group(1).strip(),
            block_type=CodeBlockType.LATEX_VERBATIM,
            language="text",
            line_number=text[:m.start()].count("\n") + 1,
            original=m.group(0),
        ))

    for m in RE_TEXTTT.finditer(text):
        blocks.append(CodeBlock(
            content=m.group(1),
            block_type=CodeBlockType.INLINE_TEXTTT,
            line_number=text[:m.start()].count("\n") + 1,
            original=m.group(0),
        ))

    for m in RE_VERB.finditer(text):
        blocks.append(CodeBlock(
            content=m.group(2),
            block_type=CodeBlockType.INLINE_VERB,
            line_number=text[:m.start()].count("\n") + 1,
            original=m.group(0),
        ))

    return blocks


def _extract_html_blocks(text: str) -> list[CodeBlock]:
    """استخراج بلوک‌های کد HTML."""
    blocks: list[CodeBlock] = []

    for m in RE_HTML_PRE_CODE.finditer(text):
        lang = m.group(1) or ""
        content = _unescape_html(m.group(2))
        blocks.append(CodeBlock(
            content=content.strip(),
            block_type=CodeBlockType.HTML_PRE,
            language=lang,
            line_number=text[:m.start()].count("\n") + 1,
            original=m.group(0),
        ))

    return blocks


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CodeProcessor Class / کلاس پردازشگر کد
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CodeProcessor(BaseProcessor):
    """
    پردازشگر بلوک‌های کد.
    Converts code from LaTeX/HTML to MDX fenced blocks.

    وظایف:
    1. تبدیل lstlisting/minted/verbatim → ```lang
    2. تبدیل HTML <pre><code> → ```lang
    3. تشخیص زبان
    4. حفظ شماره خط و عنوان
    5. اطمینان از LTR
    6. تبدیل inline: \\texttt → `...`, \\verb → `...`
    """

    name: str = "code"
    description: str = "Code block processor / پردازشگر کد"
    priority: int = 15  # قبل از math (20) — محافظت کد

    def __init__(self, config: Any = None) -> None:
        """مقداردهی پردازشگر کد."""
        super().__init__(config)

    def can_process(
        self,
        content: str,
        context: ProcessorContext,
    ) -> bool:
        """آیا محتوا شامل بلوک کد است؟"""
        if not self.enabled:
            return False
        indicators = (
            "\\begin{lstlisting}",
            "\\begin{minted}",
            "\\begin{verbatim}",
            "<pre>", "<code",
            "\\texttt{", "\\verb",
        )
        return any(ind in content for ind in indicators)

    def process(
        self,
        content: str,
        context: ProcessorContext,
    ) -> str:
        """
        پردازش اصلی بلوک‌های کد.
        Main code processing pipeline.
        """
        zwnj_before = content.count(ZWNJ)
        self._logger.info(
            "شروع پردازش کد — ZWNJ=%d", zwnj_before,
        )

        block_count = 0
        inline_count = 0

        # ۱) LaTeX lstlisting
        def _repl_lst(m: re.Match) -> str:
            nonlocal block_count
            opts = _parse_listing_options(m.group(1) or "")
            code = m.group(2).strip()
            lang = opts.get("language", "")
            if not lang:
                lang = detect_language(code)
            title = opts.get("caption", "")
            label = opts.get("label", "")
            nums = "numbers" in opts
            if label:
                context.labels[label] = _label_to_id(label)
            block_count += 1
            return _build_fence(code, lang, title, nums, label)

        content = RE_LSTLISTING.sub(_repl_lst, content)

        # ۲) LaTeX minted
        def _repl_mint(m: re.Match) -> str:
            nonlocal block_count
            opts_str = m.group(1) or ""
            opts = _parse_listing_options(opts_str)
            lang = m.group(2)
            code = m.group(3).strip()
            title = opts.get("caption", "")
            label = opts.get("label", "")
            nums = (
                "numbers" in opts or "linenos" in opts_str
            )
            if label:
                context.labels[label] = _label_to_id(label)
            block_count += 1
            return _build_fence(code, lang, title, nums, label)

        content = RE_MINTED.sub(_repl_mint, content)

        # ۳) LaTeX verbatim
        def _repl_verb_block(m: re.Match) -> str:
            nonlocal block_count
            code = m.group(1).strip()
            block_count += 1
            return _build_fence(code, "text")

        content = RE_VERBATIM.sub(_repl_verb_block, content)

        # ۴) HTML <pre><code>
        def _repl_html(m: re.Match) -> str:
            nonlocal block_count
            lang = m.group(1) or ""
            code = _unescape_html(m.group(2)).strip()
            if not lang:
                lang = detect_language(code)
            block_count += 1
            return _build_fence(code, lang)

        content = RE_HTML_PRE_CODE.sub(_repl_html, content)

        # ۵) Inline \texttt{...} → `...`
        def _repl_texttt(m: re.Match) -> str:
            nonlocal inline_count
            inline_count += 1
            return "`" + m.group(1) + "`"

        content = RE_TEXTTT.sub(_repl_texttt, content)

        # ۶) Inline \verb|...| → `...`
        def _repl_verb(m: re.Match) -> str:
            nonlocal inline_count
            inline_count += 1
            return "`" + m.group(2) + "`"

        content = RE_VERB.sub(_repl_verb, content)

        # بروزرسانی شمارنده‌ها
        context.code_blocks_processed = block_count
        self._logger.info(
            "آمار: blocks=%d, inline=%d",
            block_count, inline_count,
        )

        # بررسی ZWNJ
        zwnj_after = content.count(ZWNJ)
        if zwnj_after != zwnj_before:
            context.add_warning(
                "⚠ [code] ZWNJ: "
                + str(zwnj_before) + "→" + str(zwnj_after)
            )

        return content