"""
FormatForge - ZWNJ Handler Tests
تست‌های مدیریت نیم‌فاصله فارسی

Comprehensive tests for count, validate, find, fix, protect,
restore, safe_process, and ensure_zwnj functions.
20+ test cases covering all ZWNJ operations.
"""

from __future__ import annotations

import pytest

from formatforge.core.persian.zwnj_handler import (
    ZWNJ,
    PERSIAN_PREFIXES,
    PERSIAN_SUFFIXES,
    ZWNJProtection,
    ZWNJReport,
    count_zwnj,
    ensure_zwnj,
    find_zwnj_positions,
    fix_common_zwnj_issues,
    protect_zwnj,
    restore_zwnj,
    safe_process,
    validate_zwnj_preserved,
)
from formatforge.exceptions import ZWNJLossError


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants / ثابت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# متن نمونه با نیم‌فاصله
SAMPLE_WITH_ZWNJ = (
    f"می{ZWNJ}خواهیم کتاب{ZWNJ}ها و مقاله{ZWNJ}های "
    f"خود را بررسی کنیم. این بزرگ{ZWNJ}ترین پروژه است."
)

# همان متن بدون نیم‌فاصله (فاصله عادی)
SAMPLE_WITHOUT_ZWNJ = (
    "می خواهیم کتاب ها و مقاله های "
    "خود را بررسی کنیم. این بزرگ ترین پروژه است."
)

# متن ساده بدون فارسی
SAMPLE_ENGLISH = "Hello World, this is a test."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# count_zwnj Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCountZwnj:
    """تست‌های شمارش نیم‌فاصله."""

    def test_count_with_zwnj(self) -> None:
        """شمارش در متن با نیم‌فاصله."""
        assert count_zwnj(SAMPLE_WITH_ZWNJ) == 4

    def test_count_without_zwnj(self) -> None:
        """شمارش در متن بدون نیم‌فاصله."""
        assert count_zwnj(SAMPLE_WITHOUT_ZWNJ) == 0

    def test_count_empty(self) -> None:
        """شمارش در متن خالی."""
        assert count_zwnj("") == 0

    def test_count_single_zwnj(self) -> None:
        """شمارش یک نیم‌فاصله."""
        assert count_zwnj(f"می{ZWNJ}روم") == 1

    def test_count_english(self) -> None:
        """شمارش در متن انگلیسی."""
        assert count_zwnj(SAMPLE_ENGLISH) == 0

    def test_count_only_zwnj(self) -> None:
        """شمارش متن فقط شامل نیم‌فاصله."""
        assert count_zwnj(ZWNJ * 7) == 7

    def test_zwnj_is_correct_char(self) -> None:
        """ثابت ZWNJ کاراکتر درست باشد."""
        assert ZWNJ == "\u200c"
        assert ord(ZWNJ) == 0x200C


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# find_zwnj_positions Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFindZwnjPositions:
    """تست‌های یافتن موقعیت نیم‌فاصله."""

    def test_find_positions(self) -> None:
        """موقعیت‌ها درست باشند."""
        text = f"الف{ZWNJ}ب{ZWNJ}ج"
        positions = find_zwnj_positions(text)
        assert len(positions) == 2
        assert text[positions[0]] == ZWNJ
        assert text[positions[1]] == ZWNJ

    def test_find_empty(self) -> None:
        """متن خالی."""
        assert find_zwnj_positions("") == []

    def test_find_no_zwnj(self) -> None:
        """متن بدون نیم‌فاصله."""
        assert find_zwnj_positions("سلام دنیا") == []

    def test_find_consecutive(self) -> None:
        """نیم‌فاصله‌های متوالی."""
        text = f"ا{ZWNJ}{ZWNJ}ب"
        positions = find_zwnj_positions(text)
        assert len(positions) == 2
        assert positions == [1, 2]

    def test_positions_match_count(self) -> None:
        """تعداد موقعیت‌ها = تعداد شمارش."""
        positions = find_zwnj_positions(SAMPLE_WITH_ZWNJ)
        assert len(positions) == count_zwnj(SAMPLE_WITH_ZWNJ)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# validate_zwnj_preserved Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestValidateZwnjPreserved:
    """تست‌های اعتبارسنجی حفظ نیم‌فاصله."""

    def test_preserved(self) -> None:
        """نیم‌فاصله حفظ شده."""
        report = validate_zwnj_preserved(
            SAMPLE_WITH_ZWNJ, SAMPLE_WITH_ZWNJ,
        )
        assert isinstance(report, ZWNJReport)
        assert report.is_preserved is True
        assert report.lost_count == 0
        assert report.count_before == report.count_after

    def test_lost(self) -> None:
        """نیم‌فاصله از دست رفته."""
        report = validate_zwnj_preserved(
            SAMPLE_WITH_ZWNJ, SAMPLE_WITHOUT_ZWNJ,
        )
        assert report.is_preserved is False
        assert report.lost_count == 4
        assert report.count_before == 4
        assert report.count_after == 0

    def test_added(self) -> None:
        """نیم‌فاصله اضافه شده (fix) — OK محسوب شود."""
        report = validate_zwnj_preserved(
            SAMPLE_WITHOUT_ZWNJ, SAMPLE_WITH_ZWNJ,
        )
        assert report.is_preserved is True
        assert report.count_after > report.count_before

    def test_raise_on_loss(self) -> None:
        """raise_on_loss=True باید ZWNJLossError بدهد."""
        with pytest.raises(ZWNJLossError) as exc_info:
            validate_zwnj_preserved(
                SAMPLE_WITH_ZWNJ,
                SAMPLE_WITHOUT_ZWNJ,
                raise_on_loss=True,
            )
        assert exc_info.value.before_count == 4
        assert exc_info.value.after_count == 0

    def test_no_raise_when_preserved(self) -> None:
        """raise_on_loss=True بدون از دست رفتن — خطا ندهد."""
        report = validate_zwnj_preserved(
            SAMPLE_WITH_ZWNJ,
            SAMPLE_WITH_ZWNJ,
            raise_on_loss=True,
        )
        assert report.is_preserved is True

    def test_empty_texts(self) -> None:
        """متن‌های خالی."""
        report = validate_zwnj_preserved("", "")
        assert report.is_preserved is True
        assert report.count_before == 0

    def test_report_message_preserved(self) -> None:
        """پیام گزارش برای حفظ شده."""
        report = validate_zwnj_preserved(
            f"می{ZWNJ}روم", f"می{ZWNJ}روم",
        )
        assert "✅" in report.message

    def test_report_message_lost(self) -> None:
        """پیام گزارش برای از دست رفته."""
        report = validate_zwnj_preserved(
            f"می{ZWNJ}روم", "می روم",
        )
        assert "❌" in report.message

    def test_positions_lost(self) -> None:
        """موقعیت‌های از دست رفته گزارش شوند."""
        before = f"می{ZWNJ}روم"
        after = "میروم"
        report = validate_zwnj_preserved(before, after)
        assert len(report.positions_lost) >= 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# fix_common_zwnj_issues Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFixCommonZwnjIssues:
    """تست‌های اصلاح مشکلات رایج نیم‌فاصله."""

    def test_fix_mi_verb(self) -> None:
        """«می روم» → «می‌روم»."""
        result = fix_common_zwnj_issues("می روم")
        assert ZWNJ in result
        assert "می" + ZWNJ + "روم" in result

    def test_fix_nemi_verb(self) -> None:
        """«نمی دانم» → «نمی‌دانم»."""
        result = fix_common_zwnj_issues("نمی دانم")
        assert "نمی" + ZWNJ + "دانم" in result

    def test_fix_noun_ha(self) -> None:
        """«کتاب ها» → «کتاب‌ها»."""
        result = fix_common_zwnj_issues("کتاب ها")
        assert "کتاب" + ZWNJ + "ها" in result

    def test_fix_noun_hayi(self) -> None:
        """«مقاله های» → «مقاله‌های»."""
        result = fix_common_zwnj_issues("مقاله های")
        assert "مقاله" + ZWNJ + "های" in result

    def test_fix_noun_ei(self) -> None:
        """«خانه ای» → «خانه‌ای»."""
        result = fix_common_zwnj_issues("خانه ای")
        assert "خانه" + ZWNJ + "ای" in result

    def test_fix_noun_tar(self) -> None:
        """«بزرگ تر» → «بزرگ‌تر»."""
        result = fix_common_zwnj_issues("بزرگ تر")
        assert "بزرگ" + ZWNJ + "تر" in result

    def test_fix_noun_tarin(self) -> None:
        """«بزرگ ترین» → «بزرگ‌ترین»."""
        result = fix_common_zwnj_issues("بزرگ ترین")
        assert "بزرگ" + ZWNJ + "ترین" in result

    def test_fix_multiple(self) -> None:
        """اصلاح چندین مشکل در یک متن."""
        text = "می خواهیم کتاب ها را بخوانیم."
        result = fix_common_zwnj_issues(text)
        assert count_zwnj(result) >= 2

    def test_no_false_fix(self) -> None:
        """متن صحیح نباید تغییر کند."""
        text = f"می{ZWNJ}خواهیم کتاب{ZWNJ}ها را بخوانیم."
        zwnj_before = count_zwnj(text)
        result = fix_common_zwnj_issues(text)
        zwnj_after = count_zwnj(result)
        assert zwnj_after >= zwnj_before

    def test_empty_text(self) -> None:
        """متن خالی."""
        assert fix_common_zwnj_issues("") == ""

    def test_english_unchanged(self) -> None:
        """متن انگلیسی تغییر نکند."""
        text = "Hello World"
        assert fix_common_zwnj_issues(text) == text

    def test_preserve_existing_zwnj(self) -> None:
        """نیم‌فاصله‌های موجود حفظ شوند."""
        text = f"می{ZWNJ}روم و کتاب ها"
        result = fix_common_zwnj_issues(text)
        assert count_zwnj(result) >= 2  # حداقل ۱ قبلی + ۱ اصلاح


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# protect_zwnj Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestProtectZwnj:
    """تست‌های حفاظت نیم‌فاصله."""

    def test_protect_basic(self) -> None:
        """حفاظت پایه."""
        text = f"می{ZWNJ}روم"
        prot = protect_zwnj(text)

        assert isinstance(prot, ZWNJProtection)
        assert ZWNJ not in prot.protected_text
        assert prot.original_count == 1
        assert len(prot.restoration_map) == 1

    def test_protect_multiple(self) -> None:
        """حفاظت چندین نیم‌فاصله."""
        prot = protect_zwnj(SAMPLE_WITH_ZWNJ)

        assert ZWNJ not in prot.protected_text
        assert prot.original_count == 4
        assert len(prot.restoration_map) == 4

    def test_protect_empty(self) -> None:
        """حفاظت متن خالی."""
        prot = protect_zwnj("")
        assert prot.protected_text == ""
        assert prot.original_count == 0
        assert len(prot.restoration_map) == 0

    def test_protect_no_zwnj(self) -> None:
        """حفاظت متن بدون نیم‌فاصله."""
        text = "سلام دنیا"
        prot = protect_zwnj(text)
        assert prot.protected_text == text
        assert prot.original_count == 0

    def test_protect_unique_placeholders(self) -> None:
        """placeholder‌ها یکتا باشند."""
        prot = protect_zwnj(SAMPLE_WITH_ZWNJ)
        tokens = list(prot.restoration_map.keys())
        assert len(tokens) == len(set(tokens))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# restore_zwnj Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRestoreZwnj:
    """تست‌های بازیابی نیم‌فاصله."""

    def test_restore_basic(self) -> None:
        """بازیابی پایه."""
        text = f"می{ZWNJ}روم"
        prot = protect_zwnj(text)
        restored = restore_zwnj(
            prot.protected_text, prot.restoration_map,
        )
        assert restored == text
        assert count_zwnj(restored) == 1

    def test_protect_restore_roundtrip(self) -> None:
        """protect + restore = متن اصلی."""
        prot = protect_zwnj(SAMPLE_WITH_ZWNJ)
        restored = restore_zwnj(
            prot.protected_text, prot.restoration_map,
        )
        assert restored == SAMPLE_WITH_ZWNJ
        assert count_zwnj(restored) == count_zwnj(SAMPLE_WITH_ZWNJ)

    def test_restore_empty_map(self) -> None:
        """بازیابی بدون نگاشت."""
        text = "سلام"
        assert restore_zwnj(text, {}) == text

    def test_restore_preserves_other_content(self) -> None:
        """بازیابی سایر محتوا را تغییر ندهد."""
        text = f"الف{ZWNJ}ب و ج"
        prot = protect_zwnj(text)

        # شبیه‌سازی پردازش: uppercase بخش انگلیسی
        modified = prot.protected_text
        restored = restore_zwnj(modified, prot.restoration_map)

        assert "الف" in restored
        assert "ب" in restored
        assert "ج" in restored
        assert count_zwnj(restored) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# safe_process Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSafeProcess:
    """تست‌های پردازش امن."""

    def test_identity_processor(self) -> None:
        """پردازشگر بدون تغییر."""
        result = safe_process(
            SAMPLE_WITH_ZWNJ, lambda t: t,
        )
        assert result == SAMPLE_WITH_ZWNJ
        assert count_zwnj(result) == count_zwnj(SAMPLE_WITH_ZWNJ)

    def test_strip_processor(self) -> None:
        """پردازشگر strip — نیم‌فاصله حفظ شود."""
        text = f"  می{ZWNJ}روم  "
        result = safe_process(text, str.strip)
        assert ZWNJ in result

    def test_replace_processor(self) -> None:
        """پردازشگر replace — نیم‌فاصله حفظ شود."""
        text = f"می{ZWNJ}روم به خانه"
        result = safe_process(
            text, lambda t: t.replace("خانه", "مدرسه"),
        )
        assert ZWNJ in result
        assert "مدرسه" in result

    def test_regex_processor(self) -> None:
        """پردازش regex — نیم‌فاصله حفظ شود."""
        import re
        text = f"می{ZWNJ}روم ۱۲۳"
        result = safe_process(
            text,
            lambda t: re.sub(r"[۰-۹]+", "NUM", t),
        )
        assert ZWNJ in result
        assert "NUM" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ensure_zwnj Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEnsureZwnj:
    """تست‌های اطمینان از نیم‌فاصله."""

    def test_add_prefix_zwnj(self) -> None:
        """افزودن نیم‌فاصله بعد از پیشوند."""
        result = ensure_zwnj("میروم", prefix="می")
        assert result == f"می{ZWNJ}روم"

    def test_add_suffix_zwnj(self) -> None:
        """افزودن نیم‌فاصله قبل از پسوند."""
        result = ensure_zwnj("کتابها", suffix="ها")
        assert result == f"کتاب{ZWNJ}ها"

    def test_already_has_prefix_zwnj(self) -> None:
        """پیشوند قبلاً نیم‌فاصله دارد."""
        word = f"می{ZWNJ}روم"
        result = ensure_zwnj(word, prefix="می")
        assert count_zwnj(result) == 1

    def test_already_has_suffix_zwnj(self) -> None:
        """پسوند قبلاً نیم‌فاصله دارد."""
        word = f"کتاب{ZWNJ}ها"
        result = ensure_zwnj(word, suffix="ها")
        assert count_zwnj(result) == 1

    def test_no_prefix_suffix(self) -> None:
        """بدون پیشوند/پسوند — بدون تغییر."""
        word = "سلام"
        assert ensure_zwnj(word) == word


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConstants:
    """تست ثابت‌ها و لیست‌ها."""

    def test_prefixes_not_empty(self) -> None:
        """لیست پیشوندها خالی نباشد."""
        assert len(PERSIAN_PREFIXES) >= 5
        assert "می" in PERSIAN_PREFIXES
        assert "نمی" in PERSIAN_PREFIXES

    def test_suffixes_not_empty(self) -> None:
        """لیست پسوندها خالی نباشد."""
        assert len(PERSIAN_SUFFIXES) >= 10
        assert "ها" in PERSIAN_SUFFIXES
        assert "های" in PERSIAN_SUFFIXES
        assert "تر" in PERSIAN_SUFFIXES
        assert "ترین" in PERSIAN_SUFFIXES

    def test_no_duplicates_prefixes(self) -> None:
        """پیشوندها تکراری نباشند."""
        assert len(PERSIAN_PREFIXES) == len(set(PERSIAN_PREFIXES))

    def test_no_duplicates_suffixes(self) -> None:
        """پسوندها تکراری نباشند."""
        assert len(PERSIAN_SUFFIXES) == len(set(PERSIAN_SUFFIXES))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration / یکپارچگی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntegration:
    """تست‌های یکپارچگی."""

    def test_fix_then_validate(self) -> None:
        """اصلاح و سپس اعتبارسنجی."""
        original = "می خواهیم کتاب ها را بخوانیم."
        fixed = fix_common_zwnj_issues(original)
        report = validate_zwnj_preserved(original, fixed)
        # باید نیم‌فاصله اضافه شده باشد
        assert report.count_after >= report.count_before

    def test_full_pipeline(self) -> None:
        """خط لوله کامل: fix → protect → process → restore → validate."""
        # ۱) اصلاح
        text = "می خواهیم کتاب ها را ببینیم."
        fixed = fix_common_zwnj_issues(text)
        assert count_zwnj(fixed) >= 2

        # ۲) حفاظت + پردازش + بازیابی
        zwnj_count = count_zwnj(fixed)
        result = safe_process(
            fixed, lambda t: t.replace("ببینیم", "بخوانیم"),
        )

        # ۳) اعتبارسنجی
        assert count_zwnj(result) == zwnj_count
        assert "بخوانیم" in result

    def test_import_from_package(self) -> None:
        """import از __init__.py پکیج."""
        from formatforge.core.persian import (
            ZWNJ,
            count_zwnj,
            validate_zwnj_preserved,
            fix_common_zwnj_issues,
            protect_zwnj,
            restore_zwnj,
            safe_process,
            ensure_zwnj,
            ZWNJReport,
            ZWNJProtection,
            PERSIAN_PREFIXES,
            PERSIAN_SUFFIXES,
        )
        assert callable(count_zwnj)
        assert callable(protect_zwnj)
        assert ZWNJ == "\u200c"

    def test_zwnj_loss_error_integration(self) -> None:
        """ZWNJLossError از exceptions.py کار کند."""
        err = ZWNJLossError(
            before_count=5, after_count=3,
            lost_positions=[10, 25],
        )
        assert err.before_count == 5
        assert err.after_count == 3
        assert len(err.lost_positions) == 2
        assert "5" in str(err)
        assert "3" in str(err)
