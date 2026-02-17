"""
FormatForge - BiDi Handler
مدیریت دوجهته (RTL/LTR) متن فارسی

Detect text direction, wrap RTL/LTR blocks, split bidi segments,
and convert LaTeX directional commands to HTML/MDX equivalents.

قواعد:
- بدنه اصلی: dir="rtl" + lang="fa"
- بلوک‌های کد/ریاضی: dir="ltr"
- \lr{} → <span dir="ltr">
- \begin{latin} → <div dir="ltr" lang="en">
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger("formatforge.persian.bidi")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants / ثابت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DirectionType = Literal["rtl", "ltr", "mixed"]

_RTL_RANGE = re.compile(
    "[\u0600-\u06ff\u0750-\u077f\u0590-\u05ff"
    "\ufb50-\ufdff\ufe70-\ufeff]"
)
_LTR_RANGE = re.compile(r"[a-zA-Z]")

_MIXED_THRESHOLD = 0.10  # حداقل ۱۰٪ هر جهت

# ─── LaTeX patterns ───
_RE_LR = re.compile(
    r"\\lr\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
    re.DOTALL,
)
_RE_RL = re.compile(
    r"\\rl\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
    re.DOTALL,
)
_RE_LATIN_ENV = re.compile(
    r"\\begin\{latin\}(.*?)\\end\{latin\}",
    re.DOTALL,
)
_RE_PERSIAN_ENV = re.compile(
    r"\\begin\{persian\}(.*?)\\end\{persian\}",
    re.DOTALL,
)
_RE_LTR_FOOTNOTE = re.compile(
    r"\\LTRfootnote\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
    re.DOTALL,
)
_RE_TEXTLR = re.compile(
    r"\\textLR\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
    re.DOTALL,
)
_RE_TEXTRL = re.compile(
    r"\\textRL\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
    re.DOTALL,
)
_RE_LRE = re.compile(
    r"\\LRE\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
    re.DOTALL,
)
_RE_RLE = re.compile(
    r"\\RLE\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
    re.DOTALL,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Classes / کلاس‌های داده
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class BidiSegment:
    """
    یک بخش متن با جهت مشخص.
    A text segment with known direction and language.
    """
    text: str
    direction: DirectionType
    lang: str = ""

    def __post_init__(self) -> None:
        if not self.lang:
            self.lang = "fa" if self.direction == "rtl" else "en"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Direction Detection / تشخیص جهت
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def detect_block_direction(text: str) -> DirectionType:
    """
    تشخیص جهت یک بلوک متن.
    Detect the primary direction of a text block.

    تحلیل بر اساس نسبت کاراکترهای RTL و LTR.
    بلوک‌های کد و فرمول قبل از تحلیل حذف می‌شوند.

    Args:
        text: متن ورودی

    Returns:
        "rtl" | "ltr" | "mixed"
    """
    if not text or not text.strip():
        return "rtl"  # پیش‌فرض فارسی

    cleaned = _strip_code_math(text)

    rtl_chars = len(_RTL_RANGE.findall(cleaned))
    ltr_chars = len(_LTR_RANGE.findall(cleaned))
    total = rtl_chars + ltr_chars

    if total == 0:
        return "rtl"

    rtl_ratio = rtl_chars / total
    ltr_ratio = ltr_chars / total

    if rtl_ratio >= _MIXED_THRESHOLD and ltr_ratio >= _MIXED_THRESHOLD:
        if rtl_ratio >= 0.5:
            return "rtl"
        return "mixed"

    if rtl_ratio > ltr_ratio:
        return "rtl"

    return "ltr"


def _strip_code_math(text: str) -> str:
    """حذف بلوک‌های کد و ریاضی برای تحلیل جهت."""
    result = re.sub(r"```[\s\S]*?```", " ", text)
    result = re.sub(r"`[^`]+`", " ", result)
    result = re.sub(r"\$\$[\s\S]*?\$\$", " ", result)
    result = re.sub(r"\$[^$]+\$", " ", result)
    result = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", " ", result)
    result = re.sub(r"\\[a-zA-Z]+", " ", result)
    result = re.sub(r"https?://\S+", " ", result)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Block Wrapping / بسته‌بندی بلوک
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def wrap_rtl_block(
    content: str,
    *,
    tag: str = "div",
    lang: str = "fa",
) -> str:
    """
    بسته‌بندی محتوا در بلوک RTL.
    Wrap content in an RTL block element.

    Args:
        content: محتوای داخلی
        tag: تگ HTML (div, span, p, ...)
        lang: زبان (fa, ar, ...)

    Returns:
        HTML با dir="rtl"
    """
    content = content.strip()
    if not content:
        return ""
    return f'<{tag} dir="rtl" lang="{lang}">{content}</{tag}>'


def wrap_ltr_block(
    content: str,
    *,
    tag: str = "div",
    lang: str = "en",
) -> str:
    """
    بسته‌بندی محتوا در بلوک LTR.
    Wrap content in an LTR block element.

    Args:
        content: محتوای داخلی
        tag: تگ HTML (div, span, ...)
        lang: زبان (en, ...)

    Returns:
        HTML با dir="ltr"
    """
    content = content.strip()
    if not content:
        return ""
    return f'<{tag} dir="ltr" lang="{lang}">{content}</{tag}>'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BiDi Segmentation / تقسیم‌بندی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def split_bidi_segments(text: str) -> list[BidiSegment]:
    """
    تقسیم متن به بخش‌های RTL و LTR.
    Split text into directional segments.

    هر بخش متوالی با جهت یکسان در یک segment قرار می‌گیرد.

    Args:
        text: متن ورودی

    Returns:
        لیست BidiSegment
    """
    if not text:
        return []

    segments: list[BidiSegment] = []
    current_chars: list[str] = []
    current_dir: DirectionType | None = None

    for ch in text:
        ch_dir = _char_direction(ch)

        if ch_dir == "neutral":
            current_chars.append(ch)
            continue

        if current_dir is None:
            current_dir = ch_dir

        if ch_dir == current_dir:
            current_chars.append(ch)
        else:
            if current_chars:
                segments.append(BidiSegment(
                    text="".join(current_chars),
                    direction=current_dir,
                ))
            current_chars = [ch]
            current_dir = ch_dir

    if current_chars:
        direction = current_dir or "rtl"
        segments.append(BidiSegment(
            text="".join(current_chars),
            direction=direction,
        ))

    return _merge_small_segments(segments)


def _char_direction(ch: str) -> DirectionType | str:
    """تشخیص جهت یک کاراکتر."""
    if _RTL_RANGE.match(ch):
        return "rtl"
    if _LTR_RANGE.match(ch):
        return "ltr"
    return "neutral"


def _merge_small_segments(
    segments: list[BidiSegment],
    min_length: int = 2,
) -> list[BidiSegment]:
    """ادغام بخش‌های کوچک با بخش قبلی."""
    if len(segments) <= 1:
        return segments

    merged: list[BidiSegment] = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        content = seg.text.strip()
        if len(content) < min_length and prev.direction != "neutral":
            merged[-1] = BidiSegment(
                text=prev.text + seg.text,
                direction=prev.direction,
                lang=prev.lang,
            )
        elif seg.direction == prev.direction:
            merged[-1] = BidiSegment(
                text=prev.text + seg.text,
                direction=prev.direction,
                lang=prev.lang,
            )
        else:
            merged.append(seg)

    return merged


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LaTeX Conversion / تبدیل دستورات LaTeX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def convert_latex_lr(text: str) -> str:
    """
    تبدیل دستورات جهت LaTeX به HTML/MDX.
    Convert LaTeX directional commands to HTML equivalents.

    تبدیل‌ها:
    - \lr{text} → <span dir="ltr">text</span>
    - \rl{text} → <span dir="rtl">text</span>
    - \textLR{text} → <span dir="ltr">text</span>
    - \textRL{text} → <span dir="rtl">text</span>
    - \LRE{text} → <span dir="ltr">text</span>
    - \RLE{text} → <span dir="rtl">text</span>
    - \\begin{latin}...\\end{latin} → <div dir="ltr" lang="en">...</div>
    - \\begin{persian}...\\end{persian} → <div dir="rtl" lang="fa">...</div>
    - \LTRfootnote{text} → <sup><span dir="ltr">text</span></sup>

    Args:
        text: متن LaTeX

    Returns:
        متن با دستورات HTML جایگزین
    """
    if not text:
        return text

    result = text

    # ─── Environment blocks (باید قبل از inline باشد) ───
    result = _RE_LATIN_ENV.sub(
        lambda m: _wrap_env(m.group(1), "ltr", "en"),
        result,
    )
    result = _RE_PERSIAN_ENV.sub(
        lambda m: _wrap_env(m.group(1), "rtl", "fa"),
        result,
    )

    # ─── LTRfootnote ─────────────────────
    result = _RE_LTR_FOOTNOTE.sub(
        lambda m: (
            '<sup><span dir="ltr">'
            + m.group(1).strip()
            + "</span></sup>"
        ),
        result,
    )

    # ─── Inline commands ──────────────────
    # \lr{} and friends → <span dir="ltr">
    for pattern in (_RE_LR, _RE_TEXTLR, _RE_LRE):
        result = pattern.sub(
            lambda m: f'<span dir="ltr">{m.group(1).strip()}</span>',
            result,
        )

    # \rl{} and friends → <span dir="rtl">
    for pattern in (_RE_RL, _RE_TEXTRL, _RE_RLE):
        result = pattern.sub(
            lambda m: f'<span dir="rtl">{m.group(1).strip()}</span>',
            result,
        )

    return result


def _wrap_env(content: str, direction: str, lang: str) -> str:
    """بسته‌بندی محتوای environment."""
    stripped = content.strip()
    if not stripped:
        return ""
    return (
        f'\n<div dir="{direction}" lang="{lang}">\n'
        f"{stripped}\n"
        f"</div>\n"
    )
