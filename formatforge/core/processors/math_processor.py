"""
FormatForge - Math Processor
پردازشگر فرمول‌های ریاضی

Converts LaTeX math from various input formats to KaTeX-compatible MDX.
Handles inline ($...$), display (
$$
...
$$
), environments (equation, align, ...),
labels, refs, and custom macros.

قواعد حیاتی:
- \\text{فارسی} درون فرمول حفظ شود
- فرمول‌ها همیشه LTR رندر می‌شوند
- \\label{} → id برای ارجاع متقاطع
- \\ref{} / \\cref{} → لینک داخلی MDX
- ZWNJ (نیم‌فاصله) هرگز حذف نشود
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

logger = logging.getLogger("formatforge.processors.math")

# ─── Constants / ثابت‌ها ──────────────────────
ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums & Data Models / شمارشی‌ها و مدل‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MathType(str, Enum):
    """نوع فرمول ریاضی. / Math formula type."""

    INLINE = "inline"
    DISPLAY = "display"


@dataclass
class MathBlock:
    """
    یک بلوک فرمول ریاضی استخراج‌شده.
    A single extracted math block.
    """

    content: str
    math_type: MathType
    label: Optional[str] = None
    line_number: int = 0
    original: str = ""
    environment: Optional[str] = None


@dataclass
class MathStats:
    """
    آمار فرمول‌های ریاضی در سند.
    Statistics about math blocks found in a document.
    """

    inline_count: int = 0
    display_count: int = 0
    labeled_count: int = 0
    environments: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        """تعداد کل فرمول‌ها."""
        return self.inline_count + self.display_count


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Compiled Regex Patterns / الگوهای regex
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Display environments (equation, align, gather, multline, eqnarray)
_RE_ENV = re.compile(
    r"\\begin\{(equation|align|gather|multline|eqnarray)"
    r"(\*?)\}(.*?)\\end\{\1\2\}",
    re.DOTALL,
)

# Display: $$...$$
_RE_BRACKET_DISPLAY = re.compile(
    r"\\$$(.*?)\\$$",
    re.DOTALL,
)

# Inline: \(...\)
_RE_PAREN_INLINE = re.compile(
    r"\\\((.*?)\\\)",
    re.DOTALL,
)

# Display: $$...$$
_RE_DOLLAR_DISPLAY = re.compile(
    r"\$\$(.*?)\$\$",
    re.DOTALL,
)
_RE_DOLLAR_DISPLAY = re.compile(
    r"\$\$(.*?)\$\$",
    re.DOTALL,
)

# Inline: $...$ (not $$)
_RE_DOLLAR_INLINE = re.compile(
    r"(?<!\$)\$(?!\$)((?:[^$\\]|\\.)+?)\$(?!\$)",
)

# Labels inside math
_RE_LABEL = re.compile(r"\\label\{([^}]+)\}")

# References: \ref, \eqref, \cref
_RE_REF = re.compile(r"\\(ref|eqref|cref)\{([^}]+)\}")

# \newcommand / \renewcommand (up to 1 level of nested braces)
_RE_NEWCOMMAND = re.compile(
    r"\\(?:re)?newcommand\{\\(\w+)\}"
    r"(?:\[(\d+)\])?"
    r"\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}",
)

# Environment mapping: source → KaTeX-compatible inner env
_ENV_MAP: dict[str, Optional[str]] = {
    "equation": None,
    "equation*": None,
    "align": "aligned",
    "align*": "aligned",
    "gather": "gathered",
    "gather*": "gathered",
    "multline": "gathered",
    "multline*": "gathered",
    "eqnarray": "aligned",
    "eqnarray*": "aligned",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions / توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _line_number_at(text: str, pos: int) -> int:
    """شماره خط در موقعیت pos."""
    return text[:pos].count("\n") + 1


def _overlaps(
    start: int,
    end: int,
    spans: list[tuple[int, int]],
) -> bool:
    """آیا بازه [start, end) با بازه‌های موجود همپوشانی دارد؟"""
    for s, e in spans:
        if start < e and end > s:
            return True
    return False


def _label_to_id(label: str) -> str:
    """
    تبدیل label لاتک به id معتبر HTML/MDX.
    Convert LaTeX label to valid HTML/MDX id.

    eq:pythagoras → eq-pythagoras
    """
    return label.replace(":", "-").replace("_", "-").strip()


def extract_math_blocks(text: str) -> list[MathBlock]:
    """
    استخراج تمام بلوک‌های ریاضی از متن.
    Extract all math blocks from text.

    ترتیب اسکن:
    1. محیط‌های LaTeX (equation, align, ...)
    2. $$...$$
    3. \\$$...\\$$
    4. \\(...\\)
    5. $...$

    Args:
        text: متن ورودی

    Returns:
        لیست MathBlock مرتب بر اساس شماره خط
    """
    blocks: list[MathBlock] = []
    used: list[tuple[int, int]] = []

    # ۱) محیط‌های LaTeX
    for m in _RE_ENV.finditer(text):
        if _overlaps(m.start(), m.end(), used):
            continue
        used.append((m.start(), m.end()))
        env_name = m.group(1) + m.group(2)
        content = m.group(3)
        label_m = _RE_LABEL.search(content)
        blocks.append(MathBlock(
            content=content.strip(),
            math_type=MathType.DISPLAY,
            label=label_m.group(1) if label_m else None,
            line_number=_line_number_at(text, m.start()),
            original=m.group(0),
            environment=env_name,
        ))

    # ۲)$$...$$
    for m in _RE_DOLLAR_DISPLAY.finditer(text):
        if _overlaps(m.start(), m.end(), used):
            continue
        used.append((m.start(), m.end()))
        content = m.group(1)
        label_m = _RE_LABEL.search(content)
        blocks.append(MathBlock(
            content=content.strip(),
            math_type=MathType.DISPLAY,
            label=label_m.group(1) if label_m else None,
            line_number=_line_number_at(text, m.start()),
            original=m.group(0),
        ))

    # ۳) $$...$$
    for m in _RE_BRACKET_DISPLAY.finditer(text):
        if _overlaps(m.start(), m.end(), used):
            continue
        used.append((m.start(), m.end()))
        content = m.group(1)
        label_m = _RE_LABEL.search(content)
        blocks.append(MathBlock(
            content=content.strip(),
            math_type=MathType.DISPLAY,
            label=label_m.group(1) if label_m else None,
            line_number=_line_number_at(text, m.start()),
            original=m.group(0),
        ))

    # ۴) \(...\)
    for m in _RE_PAREN_INLINE.finditer(text):
        if _overlaps(m.start(), m.end(), used):
            continue
        used.append((m.start(), m.end()))
        blocks.append(MathBlock(
            content=m.group(1).strip(),
            math_type=MathType.INLINE,
            line_number=_line_number_at(text, m.start()),
            original=m.group(0),
        ))

    # ۵) $...$
    for m in _RE_DOLLAR_INLINE.finditer(text):
        if _overlaps(m.start(), m.end(), used):
            continue
        used.append((m.start(), m.end()))
        blocks.append(MathBlock(
            content=m.group(1).strip(),
            math_type=MathType.INLINE,
            line_number=_line_number_at(text, m.start()),
            original=m.group(0),
        ))

    blocks.sort(key=lambda b: b.line_number)
    return blocks


def count_math_blocks(text: str) -> MathStats:
    """
    شمارش بلوک‌های ریاضی و تولید آمار.
    Count math blocks and return statistics.

    Args:
        text: متن ورودی

    Returns:
        MathStats با آمار کامل
    """
    blocks = extract_math_blocks(text)
    stats = MathStats()

    for block in blocks:
        if block.math_type == MathType.INLINE:
            stats.inline_count += 1
        else:
            stats.display_count += 1
        if block.label:
            stats.labeled_count += 1
        if block.environment:
            env = block.environment
            stats.environments[env] = (
                stats.environments.get(env, 0) + 1
            )

    return stats


def validate_math_syntax(
    latex: str,
) -> tuple[bool, Optional[str]]:
    """
    اعتبارسنجی پایه نحو LaTeX ریاضی.
    Basic validation of LaTeX math syntax.

    بررسی‌ها:
    - تعادل براکت‌های {}
    - تطابق begin/end
    - مشکلات رایج

    Args:
        latex: رشته LaTeX ریاضی

    Returns:
        (valid, error_message) — True اگر معتبر
    """
    if not latex or not latex.strip():
        return True, None

    # ─── بررسی تعادل {} ──────────────
    depth = 0
    for i, ch in enumerate(latex):
        if ch == "\\":
            continue
        if ch == "{" and (i == 0 or latex[i - 1] != "\\"):
            depth += 1
        elif ch == "}" and (i == 0 or latex[i - 1] != "\\"):
            depth -= 1
        if depth < 0:
            return False, f"براکت بسته اضافی در موقعیت {i}"
    if depth != 0:
        return False, f"عدم تعادل براکت: {depth} باز بدون بسته"

    # ─── بررسی تطابق begin/end ───────
    begins = re.findall(r"\\begin\{(\w+\*?)\}", latex)
    ends = re.findall(r"\\end\{(\w+\*?)\}", latex)
    if begins != ends:
        return (
            False,
            f"عدم تطابق محیط‌ها: begin={begins} end={ends}",
        )

    return True, None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MathProcessor Class / کلاس پردازشگر ریاضی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MathProcessor(BaseProcessor):
    """
    پردازشگر فرمول‌های ریاضی.
    Converts LaTeX math to KaTeX-compatible MDX.

    وظایف:
    1. بازگشایی ماکروهای سفارشی (\\newcommand)
    2. تبدیل محیط‌ها (equation→ $$, align→aligned, ...)
    3. تبدیل \\[$...\\[$ → $$...$$

    4. تبدیل \\(...\\) → $...$
    5. مدیریت \\label → id و \\ref → لینک
    6. حفظ \\text{فارسی} و ZWNJ
    """

    name: str = "math"
    description: str = "Math formula processor / پردازشگر ریاضی"
    priority: int = 20  # زودتر از RTL و typography

    def __init__(
        self,
        config: Any = None,
        custom_macros: Optional[dict[str, str]] = None,
    ) -> None:
        """
        مقداردهی پردازشگر ریاضی.
        Initialize math processor.

        Args:
            config: تنظیمات عمومی
            custom_macros: ماکروهای سفارشی {نام: بدنه}
        """
        super().__init__(config)
        # name → (arg_count, body)
        self._macros: dict[str, tuple[int, str]] = {}
        if custom_macros:
            for macro_name, body in custom_macros.items():
                self._macros[macro_name] = (0, body)

    # ─── Pipeline hooks ──────────────────

    def can_process(
        self,
        content: str,
        context: ProcessorContext,
    ) -> bool:
        """آیا محتوا شامل فرمول ریاضی است؟"""
        if not self.enabled:
            return False
        indicators = ("$", "\\(", "\\[$", "\\begin{equation",
                       "\\begin{align", "\\begin{gather",
                       "\\begin{multline")
        return any(ind in content for ind in indicators)

    def process(
        self,
        content: str,
        context: ProcessorContext,
    ) -> str:
        """
        پردازش اصلی فرمول‌های ریاضی.
        Main math processing pipeline.
        """
        zwnj_before = content.count(ZWNJ)
        self._logger.info(
            "شروع پردازش ریاضی — ZWNJ=%d", zwnj_before,
        )


        # ۱) استخراج و حذف تعریف ماکروها
        content = self._collect_macros(content)
        # Remove any remaining macro definitions (e.g., \newcommand lines)
        content = _RE_NEWCOMMAND.sub("", content)

        # ۲) بازگشایی ماکروها در مناطق ریاضی
        content = self._expand_macros_in_math(content)

        # ۳) تبدیل محیط‌های LaTeX
        content = self._convert_environments(content, context)

        # ۴) تبدیل \[...$$ → $$...$$

        content = self._convert_bracket_display(content)

        # ۵) تبدیل \(...\) → $...$
        content = self._convert_paren_inline(content)

        # ۶) تبدیل \ref → لینک
        content = self._convert_refs(content, context)

        # ۷) بروزرسانی شمارنده‌ها
        stats = count_math_blocks(content)
        context.math_blocks_processed = stats.display_count
        context.math_inlines_processed = stats.inline_count
        self._logger.info(
            "آمار: inline=%d, display=%d, labeled=%d",
            stats.inline_count,
            stats.display_count,
            stats.labeled_count,
        )

        # ۸) بررسی ZWNJ
        zwnj_after = content.count(ZWNJ)
        if zwnj_after != zwnj_before:
            context.add_warning(
                f"⚠ [math] ZWNJ: {zwnj_before}→{zwnj_after}"
            )

        return content

    # ─── Macro handling / مدیریت ماکرو ───

    def _collect_macros(self, content: str) -> str:
        """
        استخراج \\newcommand از متن و حذف آن‌ها.
        Extract and remove \\newcommand definitions.
        """
        def _record(m: re.Match) -> str:
            name = m.group(1)
            arg_count = int(m.group(2)) if m.group(2) else 0
            body = m.group(3)
            self._macros[name] = (arg_count, body)
            self._logger.debug(
                "ماکرو یافت شد: \\%s[%d] = %s",
                name, arg_count, body,
            )
            return ""

        return _RE_NEWCOMMAND.sub(_record, content)

    def _expand_macros_in_math(self, content: str) -> str:
        """
        بازگشایی ماکروها فقط درون بلوک‌های ریاضی.
        Expand macros only inside math regions.
        """
        if not self._macros:
            return content

        def _expand_in_block(math_str: str) -> str:
            result = math_str
            for name, (arg_count, body) in self._macros.items():
                if arg_count == 0:
                    pattern = re.compile(
                        r"\\" + re.escape(name) + r"(?![a-zA-Z])"
                    )
                    # Use a lambda to safely insert the body (prevents bad escapes)
                    result = pattern.sub(lambda m, b=body: b, result)
                else:
                    # ماکرو با آرگومان: \cmd{arg1}{arg2}
                    arg_pat = r"\{([^}]*)\}" * arg_count
                    pattern = re.compile(
                        r"\\" + re.escape(name) + arg_pat
                    )

                    def _replacer(
                        m: re.Match,
                        _body: str = body,
                        _n: int = arg_count,
                    ) -> str:
                        r = _body
                        for i in range(1, _n + 1):
                            r = r.replace(
                                f"#{i}", m.group(i)
                            )
                        return r

                    result = pattern.sub(_replacer, result)
            return result

        # بازگشایی در display blocks
        content = _RE_DOLLAR_DISPLAY.sub(
            lambda m: "$$" + _expand_in_block(m.group(1)) + "$$",
            content,
        )
        content = _RE_ENV.sub(
            lambda m: (
                f"\\begin{{{m.group(1)}{m.group(2)}}}"
                + _expand_in_block(m.group(3))
                + f"\\end{{{m.group(1)}{m.group(2)}}}"
            ),
            content,
        )
        content = _RE_BRACKET_DISPLAY.sub(
            lambda m: "\\[$" + _expand_in_block(m.group(1)) + "\\[$",
            content,
        )

        # بازگشایی در inline blocks
        content = _RE_PAREN_INLINE.sub(
            lambda m: "\\(" + _expand_in_block(m.group(1)) + "\\)",
            content,
        )
        content = _RE_DOLLAR_INLINE.sub(
            lambda m: "$" + _expand_in_block(m.group(1)) + "$",
            content,
        )

        return content

    # ─── Environment conversion / تبدیل محیط ─

    def _convert_environments(
        self,
        content: str,
        context: ProcessorContext,
    ) -> str:
        """
        تبدیل محیط‌های LaTeX به فرمت KaTeX/MDX.
        Convert LaTeX environments to KaTeX-compatible format.

        equation →         $$        ...        $$        
        (با label) 
        align →         $$
        \\begin{aligned}...\\end{aligned}
        $$                gather →         $$
        \\begin{gathered}...\\end{gathered}
        $$

        """
        def _replace_env(m: re.Match) -> str:
            env_base = m.group(1)
            star = m.group(2)
            inner = m.group(3)
            env_name = env_base + star
            katex_env = _ENV_MAP.get(env_name)

            # استخراج و حذف label
            label = None
            label_m = _RE_LABEL.search(inner)
            if label_m:
                label = label_m.group(1)
                inner = _RE_LABEL.sub("", inner)
                context.labels[label] = _label_to_id(label)

            inner = inner.strip()

            # ساخت خروجی
            label_comment = ""
            if label:
                lid = _label_to_id(label)
                label_comment = (
                    f"\n{{/* label: {lid} */}}\n"
                )


            if katex_env is None:
                # equation → bare $$
                result = f"$${label_comment}\n{inner}\n$$"
            else:
                result = (
                    f"$${label_comment}\n"
                    f"\\begin{{{katex_env}}}\n"
                    f"{inner}\n"
                    f"\\end{{{katex_env}}}\n$$"
                )
            return result

        return _RE_ENV.sub(_replace_env, content)

    # ─── Bracket / Paren conversion ──────

    def _convert_bracket_display(self, content: str) -> str:
        """تبدیل \\$$...\\$$ →$$...$$."""

        def _replace(m: re.Match) -> str:
            inner = m.group(1)
            label = None
            label_m = _RE_LABEL.search(inner)
            if label_m:
                label = label_m.group(1)
                inner = _RE_LABEL.sub("", inner)
            inner = inner.strip()

            if label:
                lid = _label_to_id(label)
                return (
                    f"$$\n{{/* label: {lid} */}}\n"
                    f"{inner}\n$$"
                )
            return f"$$\n{inner}\n$$"

        return _RE_BRACKET_DISPLAY.sub(_replace, content)

    def _convert_paren_inline(self, content: str) -> str:
        """تبدیل \\(...\\) → $...$."""
        return _RE_PAREN_INLINE.sub(
            lambda m: "$" + m.group(1).strip() + "$",
            content,
        )

    # ─── Reference conversion / تبدیل ارجاع ─

    def _convert_refs(
        self,
        content: str,
        context: ProcessorContext,
    ) -> str:
        """
        تبدیل \\ref{eq:x} → لینک داخلی MDX.
        Convert \\ref, \\eqref, \\cref to MDX links.
        """

        def _replace_ref(m: re.Match) -> str:
            ref_type = m.group(1)
            label = m.group(2)
            lid = _label_to_id(label)

            if ref_type == "eqref":
                return f"[({lid})](#{lid})"
            elif ref_type == "cref":
                return f"[معادله {lid}](#{lid})"
            else:
                return f"[{lid}](#{lid})"

        return _RE_REF.sub(_replace_ref, content)