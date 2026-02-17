"""
FormatForge - Persian Typography
اصلاح تایپوگرافی فارسی

Fix Arabic characters (ي→ی, ك→ک), quotation marks ("" → «»),
spacing rules, numeral conversion, and combined normalization.

قواعد حیاتی:
- نیم‌فاصله هرگز حذف نشود
- بلوک‌های کد/ریاضی/URL از تبدیل اعداد مستثنا
- گیومه فارسی: «» نه ""
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from formatforge.core.persian.zwnj_handler import ZWNJ, count_zwnj

logger = logging.getLogger("formatforge.persian.typography")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants / ثابت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ─── Arabic → Persian character map ───
_ARABIC_CHAR_MAP: dict[str, str] = {
    "\u064a": "\u06cc",  # ي → ی
    "\u0643": "\u06a9",  # ك → ک
    "\u0649": "\u06cc",  # ى (alef maksura) → ی
    "\u06c0": "\u06c1",  # ہ → ھ (optional)
}

# ─── Numeral maps ───
_LATIN_TO_PERSIAN: dict[str, str] = {
    "0": "\u06f0", "1": "\u06f1", "2": "\u06f2",
    "3": "\u06f3", "4": "\u06f4", "5": "\u06f5",
    "6": "\u06f6", "7": "\u06f7", "8": "\u06f8",
    "9": "\u06f9",
}

_PERSIAN_TO_LATIN: dict[str, str] = {
    v: k for k, v in _LATIN_TO_PERSIAN.items()
}

_ARABIC_TO_PERSIAN_NUMS: dict[str, str] = {
    "\u0660": "\u06f0", "\u0661": "\u06f1",
    "\u0662": "\u06f2", "\u0663": "\u06f3",
    "\u0664": "\u06f4", "\u0665": "\u06f5",
    "\u0666": "\u06f6", "\u0667": "\u06f7",
    "\u0668": "\u06f8", "\u0669": "\u06f9",
}

# ─── Quote patterns ───
_RE_DOUBLE_QUOTES = re.compile(r'"([^"]*?)"')
_RE_SINGLE_QUOTES = re.compile(r"'([^']*?)'")

# ─── Spacing patterns ───
# حذف فاصله قبل از نشانه‌ها
_RE_SPACE_BEFORE_PUNCT = re.compile(r"\s+([:\u061b\u061f!])")
# اضافه فاصله بعد از نشانه اگر نباشد
_RE_NO_SPACE_AFTER_PUNCT = re.compile(
    r"([.\u060c:\u061b])(?=\S)"
)

# ─── Protected blocks (code, math, URL) ───
_RE_CODE_BLOCK = re.compile(r"```[\s\S]*?```")
_RE_INLINE_CODE = re.compile(r"`[^`]+`")
_RE_DISPLAY_MATH = re.compile(r"\$\$[\s\S]*?\$\$")
_RE_INLINE_MATH = re.compile(r"\$[^$]+\$")
_RE_URL = re.compile(r"https?://\S+")
_RE_HTML_TAG = re.compile(r"<[^>]+>")

_PROTECTED_PATTERNS = [
    _RE_CODE_BLOCK, _RE_INLINE_CODE,
    _RE_DISPLAY_MATH, _RE_INLINE_MATH,
    _RE_URL, _RE_HTML_TAG,
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Core Functions / توابع اصلی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def fix_arabic_characters(text: str) -> str:
    """
    اصلاح کاراکترهای عربی به فارسی.
    Fix Arabic characters to their Persian equivalents.

    تبدیل‌ها:
    - ي (U+064A) → ی (U+06CC)
    - ك (U+0643) → ک (U+06A9)
    - ى (U+0649) → ی (U+06CC)

    Args:
        text: متن ورودی

    Returns:
        متن اصلاح‌شده
    """
    if not text:
        return text

    result = text
    for arabic, persian in _ARABIC_CHAR_MAP.items():
        result = result.replace(arabic, persian)

    return result


def fix_persian_quotes(
    text: str,
    *,
    fix_double: bool = True,
    fix_single: bool = True,
) -> str:
    """
    تبدیل گیومه‌های انگلیسی به فارسی.
    Convert English quotation marks to Persian guillemets.

    تبدیل‌ها:
    - "text" → «text»
    - 'text' → «text» (قابل تنظیم)

    بلوک‌های کد و فرمول مستثنا هستند.

    Args:
        text: متن ورودی
        fix_double: تبدیل "" به «»
        fix_single: تبدیل '' به «»

    Returns:
        متن با گیومه فارسی
    """
    if not text:
        return text

    protected, placeholders = _protect_blocks(text)

    if fix_double:
        protected = _RE_DOUBLE_QUOTES.sub(
            lambda m: "\u00ab" + m.group(1) + "\u00bb", protected
        )

    if fix_single:
        protected = _RE_SINGLE_QUOTES.sub(
            lambda m: "\u00ab" + m.group(1) + "\u00bb", protected
        )

    return _restore_blocks(protected, placeholders)


def fix_persian_spacing(text: str) -> str:
    """
    اصلاح فاصله‌گذاری فارسی.
    Fix Persian spacing rules.

    قواعد:
    - حذف فاصله قبل از : ؛ ؟ !
    - اضافه فاصله بعد از . ، : ؛ (اگر نباشد)

    Args:
        text: متن ورودی

    Returns:
        متن با فاصله‌گذاری صحیح
    """
    if not text:
        return text

    protected, placeholders = _protect_blocks(text)

    # حذف فاصله قبل از نشانه‌ها
    protected = _RE_SPACE_BEFORE_PUNCT.sub(r"\1", protected)

    # اضافه فاصله بعد از نشانه‌ها
    protected = _RE_NO_SPACE_AFTER_PUNCT.sub(r"\1 ", protected)

    return _restore_blocks(protected, placeholders)


def convert_numerals(
    text: str,
    target: str = "persian",
) -> str:
    """
    تبدیل اعداد بین فارسی و لاتین.
    Convert numerals between Persian and Latin.

    بلوک‌های کد، ریاضی و URL مستثنا هستند.

    Args:
        text: متن ورودی
        target: "persian" | "latin" | "keep"

    Returns:
        متن با اعداد تبدیل‌شده
    """
    if not text or target == "keep":
        return text

    protected, placeholders = _protect_blocks(text)

    if target == "persian":
        for latin, persian in _LATIN_TO_PERSIAN.items():
            protected = protected.replace(latin, persian)
        for arabic, persian in _ARABIC_TO_PERSIAN_NUMS.items():
            protected = protected.replace(arabic, persian)
    elif target == "latin":
        for persian, latin in _PERSIAN_TO_LATIN.items():
            protected = protected.replace(persian, latin)

    return _restore_blocks(protected, placeholders)


def normalize_persian(text: str) -> str:
    """
    اعمال تمام اصلاحات تایپوگرافی فارسی.
    Apply all Persian typography fixes in the correct order.

    ترتیب:
    1. اصلاح کاراکترهای عربی
    2. اصلاح گیومه‌ها
    3. اصلاح فاصله‌گذاری
    4. تبدیل اعداد به فارسی

    Args:
        text: متن ورودی

    Returns:
        متن نرمال‌شده
    """
    if not text:
        return text

    zwnj_before = count_zwnj(text)

    result = fix_arabic_characters(text)
    result = fix_persian_quotes(result)
    result = fix_persian_spacing(result)
    result = convert_numerals(result, target="persian")

    zwnj_after = count_zwnj(result)
    if zwnj_after < zwnj_before:
        logger.warning(
            "نیم‌فاصله در normalize از دست رفت: %d → %d",
            zwnj_before, zwnj_after,
        )

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PersianTextProcessor / کلاس پردازشگر
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PersianTextProcessor:
    """
    پردازشگر متن فارسی با تنظیمات.
    Persian text processor driven by PersianConfig.

    این کلاس تمام اصلاحات را بر اساس تنظیمات اعمال می‌کند
    و نیم‌فاصله‌ها را اعتبارسنجی می‌کند.
    """

    def process(self, text: str, config: object) -> str:
        """
        پردازش متن با تنظیمات.
        Process text according to PersianConfig settings.

        Args:
            text: متن ورودی
            config: شیء PersianConfig از config/schema.py

        Returns:
            متن پردازش‌شده
        """
        if not text:
            return text

        zwnj_before = count_zwnj(text)
        result = text

        # ۱) اصلاح کاراکترهای عربی
        if getattr(config, "fix_arabic_yeh", True):
            result = result.replace("\u064a", "\u06cc")
            result = result.replace("\u0649", "\u06cc")

        if getattr(config, "fix_arabic_keh", True):
            result = result.replace("\u0643", "\u06a9")

        # ۲) گیومه
        quotation = getattr(config, "quotation_marks", "guillemet")
        if quotation == "guillemet":
            result = fix_persian_quotes(result)

        # ۳) فاصله‌گذاری
        if getattr(config, "fix_spacing", True):
            result = fix_persian_spacing(result)

        # ۴) اعداد
        numerals = getattr(config, "numerals", "persian")
        result = convert_numerals(result, target=numerals)

        # ۵) اعتبارسنجی ZWNJ
        zwnj_after = count_zwnj(result)
        if zwnj_after < zwnj_before:
            logger.error(
                "ZWNJ loss in PersianTextProcessor: "
                "%d → %d", zwnj_before, zwnj_after,
            )

        return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Block Protection / حفاظت بلوک‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━






def _protect_blocks(
    text: str,
) -> tuple[str, dict[str, str]]:
    """
    حفاظت بلوک‌های کد/ریاضی/URL با placeholder.
    Protect code/math/URL blocks from modification.
    Tokens use only ASCII uppercase letters to survive numeral conversion.
    """
    placeholders: dict[str, str] = {}
    result = text
    _counter = [0]

    def _make_token() -> str:
        n = _counter[0]
        _counter[0] += 1
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        tag = ""
        val = n
        for _ in range(6):
            tag = letters[val % 26] + tag
            val //= 26
        return "\ufffc_PB_" + tag + "_\ufffc"

    for pattern in _PROTECTED_PATTERNS:
        def _replacer(m: re.Match) -> str:
            token = _make_token()
            placeholders[token] = m.group(0)
            return token
        result = pattern.sub(_replacer, result)

    return result, placeholders


def _restore_blocks(
    text: str,
    placeholders: dict[str, str],
) -> str:
    """بازگرداندن بلوک‌های محافظت‌شده."""
    result = text
    for token, original in placeholders.items():
        result = result.replace(token, original)
    return result
