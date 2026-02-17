"""
FormatForge - Typography Tests
تست‌های تایپوگرافی فارسی

Tests for fix_arabic_characters, fix_persian_quotes,
fix_persian_spacing, convert_numerals, normalize_persian,
and PersianTextProcessor. 30+ test cases.
"""

from __future__ import annotations

import pytest

from formatforge.core.persian.typography import (
    PersianTextProcessor,
    convert_numerals,
    fix_arabic_characters,
    fix_persian_quotes,
    fix_persian_spacing,
    normalize_persian,
)
from formatforge.core.persian.zwnj_handler import ZWNJ, count_zwnj


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# fix_arabic_characters Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFixArabicCharacters:
    """تست‌های اصلاح کاراکترهای عربی."""

    def test_fix_yeh(self) -> None:
        """ي (U+064A) → ی (U+06CC)."""
        assert fix_arabic_characters("\u064a") == "\u06cc"

    def test_fix_keh(self) -> None:
        """ك (U+0643) → ک (U+06A9)."""
        assert fix_arabic_characters("\u0643") == "\u06a9"

    def test_fix_alef_maksura(self) -> None:
        """ى (U+0649) → ی (U+06CC)."""
        assert fix_arabic_characters("\u0649") == "\u06cc"

    def test_fix_in_word(self) -> None:
        """اصلاح در داخل کلمه."""
        # "كتاب" با ك عربی → "کتاب" با ک فارسی
        assert fix_arabic_characters("\u0643\u062a\u0627\u0628") == "\u06a9\u062a\u0627\u0628"

    def test_fix_multiple(self) -> None:
        """اصلاح چندین کاراکتر."""
        text = "\u064a\u0643"  # ي + ك
        result = fix_arabic_characters(text)
        assert "\u064a" not in result
        assert "\u0643" not in result
        assert "\u06cc" in result
        assert "\u06a9" in result

    def test_no_change_correct(self) -> None:
        """متن صحیح فارسی تغییر نکند."""
        text = "سلام دنیا"
        assert fix_arabic_characters(text) == text

    def test_empty(self) -> None:
        """متن خالی."""
        assert fix_arabic_characters("") == ""

    def test_english_unchanged(self) -> None:
        """متن انگلیسی تغییر نکند."""
        text = "Hello World"
        assert fix_arabic_characters(text) == text

    def test_preserves_zwnj(self) -> None:
        """نیم‌فاصله حفظ شود."""
        text = f"می{ZWNJ}خواهیم"
        result = fix_arabic_characters(text)
        assert count_zwnj(result) == count_zwnj(text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# fix_persian_quotes Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFixPersianQuotes:
    """تست‌های اصلاح گیومه."""

    def test_double_quotes(self) -> None:
        '''"text" → «text».'''
        result = fix_persian_quotes('"سلام"')
        assert "\u00ab" in result  # «
        assert "\u00bb" in result  # »
        assert '"' not in result

    def test_single_quotes(self) -> None:
        """'text' → «text»."""
        result = fix_persian_quotes("'سلام'")
        assert "\u00ab" in result
        assert "\u00bb" in result

    def test_disable_single_quotes(self) -> None:
        """غیرفعال کردن تبدیل تک‌نقل‌قول."""
        result = fix_persian_quotes("'test'", fix_single=False)
        assert "'" in result

    def test_disable_double_quotes(self) -> None:
        """غیرفعال کردن تبدیل جفت‌نقل‌قول."""
        result = fix_persian_quotes('"test"', fix_double=False)
        assert '"' in result

    def test_code_block_protected(self) -> None:
        """گیومه در بلوک کد تغییر نکند."""
        text = 'متن "فارسی" و ```python\nprint("hello")\n```'
        result = fix_persian_quotes(text)
        assert 'print("hello")' in result

    def test_inline_code_protected(self) -> None:
        """گیومه در inline code تغییر نکند."""
        text = 'متن "فارسی" و `"code"`'
        result = fix_persian_quotes(text)
        assert '`"code"`' in result

    def test_multiple_quotes(self) -> None:
        """چندین گیومه در یک متن."""
        text = '"اول" و "دوم" و "سوم"'
        result = fix_persian_quotes(text)
        assert result.count("\u00ab") == 3
        assert result.count("\u00bb") == 3

    def test_empty(self) -> None:
        """متن خالی."""
        assert fix_persian_quotes("") == ""

    def test_preserves_zwnj(self) -> None:
        """نیم‌فاصله حفظ شود."""
        text = f'"می{ZWNJ}خواهیم"'
        result = fix_persian_quotes(text)
        assert count_zwnj(result) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# fix_persian_spacing Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFixPersianSpacing:
    """تست‌های اصلاح فاصله‌گذاری."""

    def test_remove_space_before_colon(self) -> None:
        """حذف فاصله قبل از :."""
        result = fix_persian_spacing("سلام :")
        assert "سلام:" in result

    def test_remove_space_before_semicolon(self) -> None:
        """حذف فاصله قبل از ؛."""
        result = fix_persian_spacing("متن \u061b")
        assert "متن\u061b" in result

    def test_remove_space_before_question(self) -> None:
        """حذف فاصله قبل از ؟."""
        result = fix_persian_spacing("چطور \u061f")
        assert "چطور\u061f" in result

    def test_remove_space_before_exclamation(self) -> None:
        """حذف فاصله قبل از !."""
        result = fix_persian_spacing("عالی !")
        assert "عالی!" in result

    def test_add_space_after_period(self) -> None:
        """اضافه فاصله بعد از نقطه."""
        result = fix_persian_spacing("جمله.ادامه")
        assert "جمله. ادامه" in result

    def test_add_space_after_comma(self) -> None:
        """اضافه فاصله بعد از ویرگول فارسی."""
        result = fix_persian_spacing("یک\u060cدو")
        assert "\u060c " in result

    def test_no_double_space(self) -> None:
        """فاصله تکراری ایجاد نشود."""
        result = fix_persian_spacing("جمله. ادامه")
        assert ". " in result
        assert ".  " not in result

    def test_empty(self) -> None:
        """متن خالی."""
        assert fix_persian_spacing("") == ""

    def test_preserves_zwnj(self) -> None:
        """نیم‌فاصله حفظ شود."""
        text = f"می{ZWNJ}خواهیم :"
        result = fix_persian_spacing(text)
        assert count_zwnj(result) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# convert_numerals Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConvertNumerals:
    """تست‌های تبدیل اعداد."""

    def test_latin_to_persian(self) -> None:
        """0-9 → ۰-۹."""
        result = convert_numerals("0123456789", target="persian")
        assert result == "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"

    def test_persian_to_latin(self) -> None:
        """۰-۹ → 0-9."""
        result = convert_numerals(
            "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9",
            target="latin",
        )
        assert result == "0123456789"

    def test_keep(self) -> None:
        """keep → بدون تغییر."""
        text = "123 و ۴۵۶"
        assert convert_numerals(text, target="keep") == text

    def test_in_persian_text(self) -> None:
        """تبدیل اعداد در متن فارسی."""
        text = "صفحه 42 از 100"
        result = convert_numerals(text, target="persian")
        assert "42" not in result
        assert "\u06f4\u06f2" in result

    def test_code_block_protected(self) -> None:
        """اعداد در بلوک کد تغییر نکنند."""
        text = "عدد 5 و ```python\nx = 42\n```"
        result = convert_numerals(text, target="persian")
        assert "x = 42" in result

    def test_inline_code_protected(self) -> None:
        """اعداد در inline code تغییر نکنند."""
        text = "عدد 5 و `x = 42`"
        result = convert_numerals(text, target="persian")
        assert "`x = 42`" in result

    def test_math_protected(self) -> None:
        """اعداد در فرمول ریاضی تغییر نکنند."""
        text = "عدد 5 و $x^2 = 4$"
        result = convert_numerals(text, target="persian")
        assert "$x^2 = 4$" in result

    def test_url_protected(self) -> None:
        """اعداد در URL تغییر نکنند."""
        text = "عدد 5 و https://example.com/page/42"
        result = convert_numerals(text, target="persian")
        assert "https://example.com/page/42" in result

    def test_arabic_numerals_to_persian(self) -> None:
        """اعداد عربی → فارسی."""
        result = convert_numerals("\u0661\u0662\u0663", target="persian")
        assert result == "\u06f1\u06f2\u06f3"

    def test_empty(self) -> None:
        """متن خالی."""
        assert convert_numerals("", target="persian") == ""

    def test_preserves_zwnj(self) -> None:
        """نیم‌فاصله حفظ شود."""
        text = f"می{ZWNJ}خواهیم 5 کتاب"
        result = convert_numerals(text, target="persian")
        assert count_zwnj(result) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# normalize_persian Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestNormalizePersian:
    """تست‌های نرمال‌سازی کامل."""

    def test_all_fixes_applied(self) -> None:
        """تمام اصلاحات اعمال شود."""
        # ي عربی + گیومه انگلیسی + عدد لاتین
        text = '"\u064aک" متن 5'
        result = normalize_persian(text)

        # ي → ی
        assert "\u064a" not in result
        # گیومه → «»
        assert "\u00ab" in result
        # 5 → ۵
        assert "5" not in result
        assert "\u06f5" in result

    def test_preserves_zwnj(self) -> None:
        """نیم‌فاصله در normalize حفظ شود."""
        text = f'می{ZWNJ}خواهیم "کتاب{ZWNJ}ها" 3 جلد'
        zwnj_before = count_zwnj(text)
        result = normalize_persian(text)
        zwnj_after = count_zwnj(result)
        assert zwnj_after >= zwnj_before

    def test_empty(self) -> None:
        """متن خالی."""
        assert normalize_persian("") == ""

    def test_correct_order(self) -> None:
        """ترتیب صحیح اصلاحات."""
        # اعداد باید بعد از گیومه‌ها تبدیل شوند
        text = '"صفحه 5"'
        result = normalize_persian(text)
        assert "\u00ab" in result  # « موجود
        assert "\u06f5" in result  # ۵ موجود

    def test_code_blocks_safe(self) -> None:
        """بلوک‌های کد امن بمانند."""
        text = 'عدد "5" و ```python\nx = 42\nprint("hello")\n```'
        result = normalize_persian(text)
        assert 'print("hello")' in result
        assert "x = 42" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PersianTextProcessor Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class _MockPersianConfig:
    """Mock PersianConfig for testing."""

    def __init__(self, **kwargs):
        self.preserve_zwnj = kwargs.get("preserve_zwnj", True)
        self.fix_arabic_yeh = kwargs.get("fix_arabic_yeh", True)
        self.fix_arabic_keh = kwargs.get("fix_arabic_keh", True)
        self.fix_spacing = kwargs.get("fix_spacing", True)
        self.numerals = kwargs.get("numerals", "persian")
        self.quotation_marks = kwargs.get("quotation_marks", "guillemet")


class TestPersianTextProcessor:
    """تست‌های کلاس PersianTextProcessor."""

    def test_process_default_config(self) -> None:
        """پردازش با تنظیمات پیش‌فرض."""
        processor = PersianTextProcessor()
        config = _MockPersianConfig()
        text = '"\u064a\u0643" عدد 5'
        result = processor.process(text, config)

        assert "\u064a" not in result
        assert "\u0643" not in result
        assert "\u00ab" in result
        assert "\u06f5" in result

    def test_process_disable_yeh(self) -> None:
        """غیرفعال کردن اصلاح ي."""
        processor = PersianTextProcessor()
        config = _MockPersianConfig(fix_arabic_yeh=False)
        text = "\u064a"
        result = processor.process(text, config)
        assert "\u064a" in result

    def test_process_disable_keh(self) -> None:
        """غیرفعال کردن اصلاح ك."""
        processor = PersianTextProcessor()
        config = _MockPersianConfig(fix_arabic_keh=False)
        text = "\u0643"
        result = processor.process(text, config)
        assert "\u0643" in result

    def test_process_latin_numerals(self) -> None:
        """اعداد لاتین حفظ شوند."""
        processor = PersianTextProcessor()
        config = _MockPersianConfig(numerals="latin")
        text = "\u06f5"
        result = processor.process(text, config)
        assert "5" in result

    def test_process_keep_numerals(self) -> None:
        """اعداد بدون تغییر."""
        processor = PersianTextProcessor()
        config = _MockPersianConfig(numerals="keep")
        text = "5 و \u06f6"
        result = processor.process(text, config)
        assert result == text

    def test_process_standard_quotes(self) -> None:
        """گیومه استاندارد (بدون تبدیل)."""
        processor = PersianTextProcessor()
        config = _MockPersianConfig(quotation_marks="standard")
        text = '"test"'
        result = processor.process(text, config)
        assert '"' in result

    def test_process_preserves_zwnj(self) -> None:
        """نیم‌فاصله در پردازش حفظ شود."""
        processor = PersianTextProcessor()
        config = _MockPersianConfig()
        text = f'می{ZWNJ}خواهیم "کتاب{ZWNJ}ها" 3 جلد'
        zwnj_before = count_zwnj(text)
        result = processor.process(text, config)
        zwnj_after = count_zwnj(result)
        assert zwnj_after >= zwnj_before

    def test_process_empty(self) -> None:
        """متن خالی."""
        processor = PersianTextProcessor()
        config = _MockPersianConfig()
        assert processor.process("", config) == ""

    def test_process_with_real_config(self) -> None:
        """تست با PersianConfig واقعی از schema."""
        try:
            from formatforge.config.schema import PersianConfig
            config = PersianConfig()
            processor = PersianTextProcessor()
            text = '"\u064a\u0643" عدد 5'
            result = processor.process(text, config)
            assert "\u064a" not in result
            assert "\u06f5" in result
        except ImportError:
            pytest.skip("PersianConfig not available")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntegration:
    """تست‌های یکپارچگی."""

    def test_import_from_package(self) -> None:
        """import از __init__.py پکیج."""
        from formatforge.core.persian import (
            fix_arabic_characters,
            fix_persian_quotes,
            fix_persian_spacing,
            convert_numerals,
            normalize_persian,
            PersianTextProcessor,
        )
        assert callable(fix_arabic_characters)
        assert callable(normalize_persian)

    def test_zwnj_imports_still_work(self) -> None:
        """importهای zwnj همچنان کار کنند."""
        from formatforge.core.persian import (
            ZWNJ, count_zwnj, protect_zwnj,
        )
        assert ZWNJ == "\u200c"

    def test_bidi_imports_still_work(self) -> None:
        """importهای bidi همچنان کار کنند."""
        from formatforge.core.persian import (
            detect_block_direction, convert_latex_lr,
            wrap_rtl_block, BidiSegment,
        )
        assert callable(detect_block_direction)

    def test_full_pipeline(self) -> None:
        """خط لوله کامل: ZWNJ + BiDi + Typography."""
        from formatforge.core.persian import (
            count_zwnj, fix_common_zwnj_issues,
            convert_latex_lr,
        )

        # ۱) اصلاح ZWNJ
        text = "می خواهیم کتاب ها ببینیم"
        fixed = fix_common_zwnj_issues(text)

        # ۲) تبدیل LaTeX
        text2 = fixed + " \\lr{test}"
        converted = convert_latex_lr(text2)

        # ۳) تایپوگرافی
        final = normalize_persian(converted)

        # بررسی‌ها
        assert count_zwnj(final) >= 2
        assert '<span dir="ltr">' in final

    def test_arabic_fix_then_normalize(self) -> None:
        """اصلاح عربی و سپس نرمال‌سازی."""
        text = '\u064a\u0643 "5" متن'
        result = normalize_persian(text)
        assert "\u064a" not in result
        assert "\u0643" not in result
        assert "\u00ab" in result
        assert "\u06f5" in result
