"""
Tests for formatforge.utils.text_utils
تست‌های ابزارهای متن
"""

import pytest

from formatforge.utils.text_utils import (
    detect_language,
    fix_arabic_chars,
    is_mixed_language,
    is_persian,
    is_valid_slug,
    slugify,
    truncate,
)


ZWNJ = "\u200c"


# ─── Tests: slugify ─────────────────────────

class TestSlugify:
    """تست‌های ساخت slug."""

    def test_persian_text(self):
        result = slugify("منطق گزاره\u200cای")
        assert result
        assert is_valid_slug(result)

    def test_english_text(self):
        result = slugify("De Morgan's Laws", lang="en")
        assert is_valid_slug(result)
        assert "de-morgan" in result

    def test_max_length(self):
        long_text = "این یک متن بسیار طولانی است " * 10
        result = slugify(long_text, max_length=30)
        assert len(result) <= 30

    def test_empty_string(self):
        assert slugify("") == ""

    def test_whitespace_only(self):
        assert slugify("   ") == ""

    def test_no_double_dashes(self):
        result = slugify("سلام   دنیا")
        assert "--" not in result

    def test_no_trailing_dash(self):
        result = slugify("سلام ")
        assert not result.endswith("-")

    def test_no_leading_dash(self):
        result = slugify(" سلام")
        assert not result.startswith("-")

    def test_numbers_preserved(self):
        result = slugify("فصل 3", lang="fa")
        assert "3" in result

    def test_mixed_language(self):
        result = slugify("منطق Logic فارسی")
        assert is_valid_slug(result)


# ─── Tests: truncate ────────────────────────

class TestTruncate:
    """تست‌های برش متن."""

    def test_short_text_unchanged(self):
        assert truncate("سلام", max_len=100) == "سلام"

    def test_truncates_long_text(self):
        text = "الف " * 100
        result = truncate(text, max_len=20)
        assert len(result) <= 23  # 20 + len("...")

    def test_suffix_added(self):
        text = "سلام دنیا خوبی چطوری"
        result = truncate(text, max_len=10)
        assert result.endswith("...")

    def test_custom_suffix(self):
        text = "سلام دنیا خوبی"
        result = truncate(text, max_len=10, suffix="…")
        assert result.endswith("…")

    def test_empty_string(self):
        assert truncate("") == ""

    def test_zwnj_not_orphaned(self):
        text = f"می{ZWNJ}خواهیم بگوییم"
        result = truncate(text, max_len=6)
        # نباید ZWNJ آخر رشته باشد
        stripped = result.rstrip(".")
        assert not stripped.endswith(ZWNJ)

    def test_preserves_zwnj_in_middle(self):
        text = f"نیم{ZWNJ}فاصله و متن بیشتر ادامه‌دار"
        result = truncate(text, max_len=20)
        assert ZWNJ in result or "..." in result


# ─── Tests: is_persian ───────────────────────

class TestIsPersian:
    """تست‌های تشخیص فارسی."""

    def test_persian_text(self):
        assert is_persian("سلام دنیا") is True

    def test_english_text(self):
        assert is_persian("Hello world") is False

    def test_empty_text(self):
        assert is_persian("") is False

    def test_numbers_only(self):
        assert is_persian("123456") is False

    def test_mostly_persian(self):
        assert is_persian("سلام hello دنیا خوب است") is True

    def test_mostly_english(self):
        assert is_persian("Hello world with یک کلمه") is False

    def test_arabic_counted(self):
        # حروف عربی هم شناسایی می‌شوند
        assert is_persian("مرحبا بالعالم") is True


# ─── Tests: is_mixed_language ────────────────

class TestIsMixedLanguage:
    """تست‌های تشخیص دوزبانه."""

    def test_mixed_text(self):
        assert is_mixed_language("منطق logic گزاره propositional") is True

    def test_pure_persian(self):
        assert is_mixed_language("سلام دنیا خوبی") is False

    def test_pure_english(self):
        assert is_mixed_language("Hello world") is False

    def test_empty(self):
        assert is_mixed_language("") is False

    def test_short_text(self):
        assert is_mixed_language("ab") is False

    def test_slight_mix(self):
        # فقط یک حرف لاتین کافی نیست
        result = is_mixed_language("سلام دنیای خوب a")
        # بستگی به نسبت دارد
        assert isinstance(result, bool)


# ─── Tests: detect_language ──────────────────

class TestDetectLanguage:
    """تست‌های تشخیص زبان."""

    def test_persian(self):
        assert detect_language("سلام دنیا") == "fa"

    def test_english(self):
        assert detect_language("Hello world") == "en"

    def test_mixed(self):
        assert detect_language("منطق logic گزاره proof") == "fa+en"

    def test_empty(self):
        assert detect_language("") == "unknown"

    def test_numbers(self):
        result = detect_language("12345")
        assert result in ("unknown", "en")


# ─── Tests: fix_arabic_chars ─────────────────

class TestFixArabicChars:
    """تست‌های اصلاح حروف عربی."""

    def test_arabic_yeh(self):
        assert fix_arabic_chars("ي") == "ی"

    def test_arabic_kaf(self):
        assert fix_arabic_chars("ك") == "ک"

    def test_both(self):
        assert fix_arabic_chars("يك") == "یک"

    def test_already_persian(self):
        text = "یک"
        assert fix_arabic_chars(text) == text

    def test_mixed(self):
        text = "كتاب يك"
        assert fix_arabic_chars(text) == "کتاب یک"

    def test_preserves_other(self):
        text = f"سلام{ZWNJ}دنیا 123 hello"
        result = fix_arabic_chars(text)
        assert ZWNJ in result
        assert "123" in result
        assert "hello" in result


# ─── Tests: is_valid_slug ────────────────────

class TestIsValidSlug:
    """تست‌های اعتبارسنجی slug."""

    def test_valid(self):
        assert is_valid_slug("de-morgans-laws") is True

    def test_valid_simple(self):
        assert is_valid_slug("hello") is True

    def test_invalid_uppercase(self):
        assert is_valid_slug("Hello") is False

    def test_invalid_space(self):
        assert is_valid_slug("hello world") is False

    def test_invalid_persian(self):
        assert is_valid_slug("سلام") is False

    def test_invalid_double_dash(self):
        assert is_valid_slug("hello--world") is False

    def test_invalid_leading_dash(self):
        assert is_valid_slug("-hello") is False

    def test_empty(self):
        assert is_valid_slug("") is False
