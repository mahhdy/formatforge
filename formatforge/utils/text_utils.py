"""
FormatForge - Text Utilities
ابزارهای کمکی متن

Persian-aware text utilities: slugify, truncation, language detection.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional


# ─────────────────────────────────────────────
# Constants / ثابت‌ها
# ─────────────────────────────────────────────

ZWNJ = "\u200c"

# محدوده‌های یونیکد فارسی/عربی
_PERSIAN_RANGE = re.compile(
    "["
    "\u0600-\u06ff"   # Arabic
    "\u0750-\u077f"   # Arabic Supplement
    "\ufb50-\ufdff"   # Arabic Presentation Forms-A
    "\ufe70-\ufeff"   # Arabic Presentation Forms-B
    "]"
)

_LATIN_RANGE = re.compile(r"[a-zA-Z]")

_ARABIC_YEH = "\u064a"    # ي
_ARABIC_KAF = "\u0643"    # ك
_PERSIAN_YEH = "\u06cc"   # ی
_PERSIAN_KAF = "\u06a9"   # ک

# جدول حروف‌نگاری فارسی → لاتین (ساده‌شده)
_TRANSLITERATION_MAP: dict[str, str] = {
    "آ": "a", "ا": "a", "ب": "b", "پ": "p", "ت": "t",
    "ث": "s", "ج": "j", "چ": "ch", "ح": "h", "خ": "kh",
    "د": "d", "ذ": "z", "ر": "r", "ز": "z", "ژ": "zh",
    "س": "s", "ش": "sh", "ص": "s", "ض": "z", "ط": "t",
    "ظ": "z", "ع": "a", "غ": "gh", "ف": "f", "ق": "gh",
    "ک": "k", "گ": "g", "ل": "l", "م": "m", "ن": "n",
    "و": "v", "ه": "h", "ی": "y",
    # ارقام فارسی
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    # نیم‌فاصله و فاصله
    ZWNJ: "-",
    " ": "-",
}

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MULTI_DASH = re.compile(r"-{2,}")
_NON_SLUG_CHARS = re.compile(r"[^a-z0-9-]")


# ─────────────────────────────────────────────
# Slugify / ساخت slug
# ─────────────────────────────────────────────

def slugify(
    text: str,
    lang: str = "fa",
    *,
    max_length: int = 60,
    transliterate: bool = True,
) -> str:
    """
    تبدیل متن به slug مناسب URL.
    Convert text to URL-friendly slug.

    ویژگی‌ها:
    - حروف‌نگاری فارسی → لاتین (قابل غیرفعال‌سازی)
    - حذف کاراکترهای غیرمجاز
    - محدودیت طول
    - اصلاح خط‌تیره‌های تکراری

    Args:
        text: متن ورودی
        lang: زبان متن (fa | en)
        max_length: حداکثر طول slug
        transliterate: آیا فارسی به لاتین تبدیل شود

    Returns:
        slug خوانا و معتبر

    Examples:
        >>> slugify("منطق گزاره‌ای")
        'mantigh-gozareay'
        >>> slugify("De Morgan's Laws", lang="en")
        'de-morgans-laws'
    """
    if not text or not text.strip():
        return ""

    # نرمال‌سازی یونیکد
    result = unicodedata.normalize("NFKC", text.strip())

    # اصلاح ي و ك
    result = fix_arabic_chars(result)

    # حروف‌نگاری فارسی
    if transliterate and lang in ("fa", "fa-en"):
        result = _transliterate_persian(result)
    else:
        # فقط حروف لاتین نگه دار
        result = result.lower()

    # حذف کاراکترهای غیرمجاز
    result = _NON_SLUG_CHARS.sub("-", result)

    # خط‌تیره‌های تکراری
    result = _MULTI_DASH.sub("-", result)

    # حذف خط‌تیره ابتدا/انتها
    result = result.strip("-")

    # محدودیت طول
    if len(result) > max_length:
        result = result[:max_length].rstrip("-")

    return result


# ─────────────────────────────────────────────
# Truncate / برش متن
# ─────────────────────────────────────────────

def truncate(
    text: str,
    max_len: int = 300,
    *,
    suffix: str = "...",
    preserve_zwnj: bool = True,
) -> str:
    """
    برش متن با حفظ نیم‌فاصله.
    Truncate text to max_len, preserving ZWNJ integrity.

    Args:
        text: متن ورودی
        max_len: حداکثر طول (پیش‌فرض: ۳۰۰)
        suffix: پسوند برش (پیش‌فرض: ...)
        preserve_zwnj: حفظ نیم‌فاصله هنگام برش

    Returns:
        متن برش‌خورده

    Examples:
        >>> truncate("سلام دنیا", max_len=5)
        'سلام...'
    """
    if not text:
        return ""

    if len(text) <= max_len:
        return text

    cut_at = max_len - len(suffix)
    if cut_at <= 0:
        return suffix[:max_len]

    truncated = text[:cut_at]

    # حفظ نیم‌فاصله: اگر آخرین کاراکتر ZWNJ است حذفش نکن
    if preserve_zwnj and truncated and truncated[-1] == ZWNJ:
        # یک کاراکتر عقب‌تر ببر تا ZWNJ وسط کلمه نماند
        truncated = truncated[:-1]

    # برش روی کلمه (نه وسط کلمه)
    last_space = truncated.rfind(" ")
    last_zwnj = truncated.rfind(ZWNJ)
    break_point = max(last_space, last_zwnj)

    if break_point > cut_at // 2:
        truncated = truncated[:break_point]

    return truncated.rstrip() + suffix


# ─────────────────────────────────────────────
# Language Detection / تشخیص زبان
# ─────────────────────────────────────────────

def is_persian(text: str) -> bool:
    """
    آیا متن عمدتاً فارسی/عربی است؟
    Check if text is predominantly Persian/Arabic.

    Args:
        text: متن ورودی

    Returns:
        True اگر بیش از ۵۰٪ کاراکترهای حرفی فارسی/عربی باشند

    Examples:
        >>> is_persian("سلام دنیا")
        True
        >>> is_persian("Hello world")
        False
    """
    if not text or not text.strip():
        return False

    persian_count = len(_PERSIAN_RANGE.findall(text))
    latin_count = len(_LATIN_RANGE.findall(text))
    total = persian_count + latin_count

    if total == 0:
        return False

    return persian_count / total > 0.5


def is_mixed_language(text: str) -> bool:
    """
    آیا متن دوزبانه (فارسی + انگلیسی) است؟
    Check if text contains significant amounts of both Persian and Latin.

    Args:
        text: متن ورودی

    Returns:
        True اگر هر دو زبان حداقل ۱۵٪ محتوا باشند

    Examples:
        >>> is_mixed_language("منطق logic گزاره‌ای")
        True
        >>> is_mixed_language("سلام دنیا")
        False
    """
    if not text or not text.strip():
        return False

    persian_count = len(_PERSIAN_RANGE.findall(text))
    latin_count = len(_LATIN_RANGE.findall(text))
    total = persian_count + latin_count

    if total < 3:
        return False

    persian_ratio = persian_count / total
    latin_ratio = latin_count / total

    threshold = 0.15
    return persian_ratio >= threshold and latin_ratio >= threshold


def detect_language(text: str) -> str:
    """
    تشخیص زبان متن.
    Detect text language: fa, en, or fa+en.

    Args:
        text: متن ورودی

    Returns:
        "fa" | "en" | "fa+en" | "unknown"
    """
    if not text or not text.strip():
        return "unknown"

    if is_mixed_language(text):
        return "fa+en"
    if is_persian(text):
        return "fa"

    latin_count = len(_LATIN_RANGE.findall(text))
    if latin_count > 0:
        return "en"

    return "unknown"


# ─────────────────────────────────────────────
# Persian Text Helpers / ابزارهای متن فارسی
# ─────────────────────────────────────────────

def fix_arabic_chars(text: str) -> str:
    """
    اصلاح ي→ی و ك→ک.
    Fix Arabic Yeh/Kaf to Persian equivalents.

    Args:
        text: متن ورودی

    Returns:
        متن اصلاح‌شده
    """
    return text.replace(_ARABIC_YEH, _PERSIAN_YEH).replace(
        _ARABIC_KAF, _PERSIAN_KAF
    )


def is_valid_slug(slug: str) -> bool:
    """
    آیا slug معتبر است؟
    Check if a slug matches the required pattern.

    Args:
        slug: رشته slug

    Returns:
        True اگر slug معتبر باشد
    """
    return bool(_SLUG_PATTERN.match(slug))


# ─────────────────────────────────────────────
# Internal Helpers / توابع داخلی
# ─────────────────────────────────────────────

def _transliterate_persian(text: str) -> str:
    """حروف‌نگاری ساده فارسی → لاتین."""
    result: list[str] = []
    for char in text.lower():
        if char in _TRANSLITERATION_MAP:
            result.append(_TRANSLITERATION_MAP[char])
        elif char.isascii() and (char.isalnum() or char == "-"):
            result.append(char)
        elif char in (" ", "\t", "\n"):
            result.append("-")
        else:
            # حذف کاراکترهای ناشناخته
            result.append("-")
    return "".join(result)
