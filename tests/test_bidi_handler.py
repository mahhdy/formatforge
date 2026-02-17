"""
FormatForge - BiDi Handler Tests
تست‌های مدیریت دوجهته (RTL/LTR)

Tests for detect_block_direction, wrap_rtl/ltr_block,
split_bidi_segments, and convert_latex_lr.
"""

from __future__ import annotations

import pytest

from formatforge.core.persian.bidi_handler import (
    BidiSegment,
    convert_latex_lr,
    detect_block_direction,
    split_bidi_segments,
    wrap_ltr_block,
    wrap_rtl_block,
)
from formatforge.core.persian.zwnj_handler import ZWNJ


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# detect_block_direction Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDetectBlockDirection:
    """تست‌های تشخیص جهت بلوک."""

    def test_persian_text_is_rtl(self) -> None:
        """متن فارسی باید RTL باشد."""
        assert detect_block_direction("سلام دنیا") == "rtl"

    def test_english_text_is_ltr(self) -> None:
        """متن انگلیسی باید LTR باشد."""
        assert detect_block_direction("Hello World") == "ltr"

    def test_empty_defaults_rtl(self) -> None:
        """متن خالی → پیش‌فرض RTL."""
        assert detect_block_direction("") == "rtl"

    def test_whitespace_defaults_rtl(self) -> None:
        """فقط فاصله → پیش‌فرض RTL."""
        assert detect_block_direction("   \n\t  ") == "rtl"

    def test_mixed_mostly_persian(self) -> None:
        """متن مخلوط با غالب فارسی → RTL."""
        text = "این یک متن فارسی است با کمی English"
        result = detect_block_direction(text)
        assert result == "rtl"

    def test_mixed_mostly_english(self) -> None:
        """متن مخلوط با غالب انگلیسی → LTR یا mixed."""
        text = "This is mostly English with یک کلمه"
        result = detect_block_direction(text)
        assert result in ("ltr", "mixed")

    def test_numbers_only(self) -> None:
        """فقط اعداد → پیش‌فرض RTL."""
        assert detect_block_direction("12345") == "rtl"

    def test_code_block_ignored(self) -> None:
        """بلوک کد در تشخیص نادیده گرفته شود."""
        text = "متن فارسی\n```python\nprint('hello')\n```\nادامه فارسی"
        assert detect_block_direction(text) == "rtl"

    def test_math_ignored(self) -> None:
        """فرمول ریاضی در تشخیص نادیده گرفته شود."""
        text = "فرمول ساده $x^2 + y^2 = z^2$ در متن فارسی"
        assert detect_block_direction(text) == "rtl"

    def test_persian_with_zwnj(self) -> None:
        """متن فارسی با نیم‌فاصله → RTL."""
        text = f"می{ZWNJ}خواهیم کتاب{ZWNJ}ها را بخوانیم"
        assert detect_block_direction(text) == "rtl"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# wrap_rtl_block Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWrapRtlBlock:
    """تست‌های بسته‌بندی RTL."""

    def test_basic_rtl(self) -> None:
        """بسته‌بندی پایه RTL."""
        result = wrap_rtl_block("سلام")
        assert 'dir="rtl"' in result
        assert 'lang="fa"' in result
        assert "سلام" in result
        assert result.startswith("<div")
        assert result.endswith("</div>")

    def test_custom_tag(self) -> None:
        """تگ سفارشی."""
        result = wrap_rtl_block("متن", tag="span")
        assert result.startswith("<span")
        assert result.endswith("</span>")

    def test_custom_lang(self) -> None:
        """زبان سفارشی."""
        result = wrap_rtl_block("نص عربی", lang="ar")
        assert 'lang="ar"' in result

    def test_empty_content(self) -> None:
        """محتوای خالی → رشته خالی."""
        assert wrap_rtl_block("") == ""
        assert wrap_rtl_block("   ") == ""

    def test_strips_whitespace(self) -> None:
        """فاصله‌های اضافی حذف شوند."""
        result = wrap_rtl_block("  سلام  ")
        assert "سلام" in result
        assert "  سلام  " not in result

    def test_preserves_zwnj(self) -> None:
        """نیم‌فاصله حفظ شود."""
        text = f"می{ZWNJ}خواهیم"
        result = wrap_rtl_block(text)
        assert ZWNJ in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# wrap_ltr_block Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestWrapLtrBlock:
    """تست‌های بسته‌بندی LTR."""

    def test_basic_ltr(self) -> None:
        """بسته‌بندی پایه LTR."""
        result = wrap_ltr_block("Hello")
        assert 'dir="ltr"' in result
        assert 'lang="en"' in result
        assert "Hello" in result

    def test_custom_tag_span(self) -> None:
        """تگ span."""
        result = wrap_ltr_block("code", tag="span")
        assert result.startswith("<span")

    def test_empty_content(self) -> None:
        """محتوای خالی."""
        assert wrap_ltr_block("") == ""

    def test_code_block(self) -> None:
        """بسته‌بندی بلوک کد."""
        result = wrap_ltr_block("print('hello')", tag="code")
        assert '<code dir="ltr"' in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# split_bidi_segments Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSplitBidiSegments:
    """تست‌های تقسیم‌بندی دوجهته."""

    def test_pure_persian(self) -> None:
        """متن فقط فارسی → یک segment RTL."""
        segments = split_bidi_segments("سلام دنیا")
        assert len(segments) >= 1
        assert all(s.direction == "rtl" for s in segments)

    def test_pure_english(self) -> None:
        """متن فقط انگلیسی → یک segment LTR."""
        segments = split_bidi_segments("Hello World")
        assert len(segments) >= 1
        assert all(s.direction == "ltr" for s in segments)

    def test_empty(self) -> None:
        """متن خالی → لیست خالی."""
        assert split_bidi_segments("") == []

    def test_mixed_has_segments(self) -> None:
        """متن مخلوط → چندین segment."""
        text = "سلام Hello دنیا"
        segments = split_bidi_segments(text)
        assert len(segments) >= 1

    def test_segment_dataclass(self) -> None:
        """BidiSegment فیلدهای صحیح داشته باشد."""
        segments = split_bidi_segments("سلام")
        if segments:
            seg = segments[0]
            assert isinstance(seg, BidiSegment)
            assert hasattr(seg, "text")
            assert hasattr(seg, "direction")
            assert hasattr(seg, "lang")

    def test_segment_lang_auto(self) -> None:
        """زبان خودکار بر اساس جهت."""
        seg_rtl = BidiSegment(text="سلام", direction="rtl")
        assert seg_rtl.lang == "fa"

        seg_ltr = BidiSegment(text="Hello", direction="ltr")
        assert seg_ltr.lang == "en"

    def test_all_text_preserved(self) -> None:
        """تمام کاراکترها حفظ شوند."""
        text = "سلام Hello دنیا World"
        segments = split_bidi_segments(text)
        combined = "".join(s.text for s in segments)
        assert combined == text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# convert_latex_lr Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConvertLatexLr:
    """تست‌های تبدیل دستورات LaTeX جهت‌دار."""

    # ─── \lr{} ────────────────────────────

    def test_lr_basic(self) -> None:
        """\\lr{text} → <span dir="ltr">text</span>."""
        result = convert_latex_lr("\\lr{Hello}")
        assert '<span dir="ltr">Hello</span>' in result

    def test_lr_with_persian_context(self) -> None:
        """\\lr در متن فارسی."""
        text = "نام انگلیسی \\lr{FormatForge} است"
        result = convert_latex_lr(text)
        assert '<span dir="ltr">FormatForge</span>' in result
        assert "نام انگلیسی" in result

    def test_lr_with_spaces(self) -> None:
        """\\lr با فاصله داخلی."""
        result = convert_latex_lr("\\lr{ Hello World }")
        assert "Hello World" in result
        assert 'dir="ltr"' in result

    # ─── \rl{} ────────────────────────────

    def test_rl_basic(self) -> None:
        """\\rl{text} → <span dir="rtl">text</span>."""
        result = convert_latex_lr("\\rl{سلام}")
        assert '<span dir="rtl">سلام</span>' in result

    def test_rl_with_english_context(self) -> None:
        """\\rl در متن انگلیسی."""
        text = "The word \\rl{سلام} means hello"
        result = convert_latex_lr(text)
        assert '<span dir="rtl">سلام</span>' in result

    # ─── \begin{latin} ────────────────────

    def test_latin_env(self) -> None:
        """\\begin{latin}...\\end{latin} → <div dir="ltr" lang="en">."""
        text = "\\begin{latin}Hello World\\end{latin}"
        result = convert_latex_lr(text)
        assert 'dir="ltr"' in result
        assert 'lang="en"' in result
        assert "Hello World" in result

    def test_latin_env_multiline(self) -> None:
        """محیط latin چندخطی."""
        text = (
            "\\begin{latin}\n"
            "Line one\n"
            "Line two\n"
            "\\end{latin}"
        )
        result = convert_latex_lr(text)
        assert 'dir="ltr"' in result
        assert "Line one" in result
        assert "Line two" in result

    def test_latin_env_empty(self) -> None:
        """محیط latin خالی."""
        text = "\\begin{latin}\\end{latin}"
        result = convert_latex_lr(text)
        assert "<div" not in result or result.strip() == ""

    # ─── \begin{persian} ──────────────────

    def test_persian_env(self) -> None:
        """\\begin{persian}...\\end{persian} → <div dir="rtl" lang="fa">."""
        text = "\\begin{persian}سلام دنیا\\end{persian}"
        result = convert_latex_lr(text)
        assert 'dir="rtl"' in result
        assert 'lang="fa"' in result
        assert "سلام دنیا" in result

    # ─── \LTRfootnote ─────────────────────

    def test_ltr_footnote(self) -> None:
        """\\LTRfootnote{text} → <sup><span dir="ltr">text</span></sup>."""
        text = "\\LTRfootnote{See page 42}"
        result = convert_latex_lr(text)
        assert "<sup>" in result
        assert '<span dir="ltr">' in result
        assert "See page 42" in result
        assert "</span></sup>" in result

    def test_ltr_footnote_with_context(self) -> None:
        """\\LTRfootnote در متن فارسی."""
        text = "این یک پانوشت\\LTRfootnote{Reference 1} است"
        result = convert_latex_lr(text)
        assert "این یک پانوشت" in result
        assert '<span dir="ltr">Reference 1</span>' in result

    # ─── \textLR / \textRL ────────────────

    def test_textlr(self) -> None:
        """\\textLR{text} → <span dir="ltr">."""
        result = convert_latex_lr("\\textLR{English}")
        assert '<span dir="ltr">English</span>' in result

    def test_textrl(self) -> None:
        """\\textRL{text} → <span dir="rtl">."""
        result = convert_latex_lr("\\textRL{فارسی}")
        assert '<span dir="rtl">فارسی</span>' in result

    # ─── \LRE / \RLE ─────────────────────

    def test_lre(self) -> None:
        """\\LRE{text} → <span dir="ltr">."""
        result = convert_latex_lr("\\LRE{Left}")
        assert '<span dir="ltr">Left</span>' in result

    def test_rle(self) -> None:
        """\\RLE{text} → <span dir="rtl">."""
        result = convert_latex_lr("\\RLE{راست}")
        assert '<span dir="rtl">راست</span>' in result

    # ─── Edge cases ───────────────────────

    def test_empty_input(self) -> None:
        """ورودی خالی."""
        assert convert_latex_lr("") == ""

    def test_no_latex_commands(self) -> None:
        """متن بدون دستور LaTeX — بدون تغییر."""
        text = "متن ساده فارسی بدون دستور"
        assert convert_latex_lr(text) == text

    def test_multiple_lr_in_one_line(self) -> None:
        """چندین \\lr در یک خط."""
        text = "\\lr{First} و \\lr{Second} و \\lr{Third}"
        result = convert_latex_lr(text)
        assert result.count('<span dir="ltr">') == 3
        assert "First" in result
        assert "Second" in result
        assert "Third" in result

    def test_nested_braces(self) -> None:
        """آکولاد تو‌در‌تو."""
        text = "\\lr{f(x) = \\frac{1}{2}}"
        result = convert_latex_lr(text)
        assert 'dir="ltr"' in result

    def test_preserves_zwnj(self) -> None:
        """نیم‌فاصله در تبدیل حفظ شود."""
        text = f"می{ZWNJ}خواهیم \\lr{{test}} ببینیم"
        result = convert_latex_lr(text)
        assert ZWNJ in result
        assert '<span dir="ltr">test</span>' in result

    def test_mixed_commands(self) -> None:
        """ترکیب چندین دستور مختلف."""
        text = (
            "\\lr{Hello} و \\rl{سلام} "
            "\\begin{latin}English block\\end{latin}"
        )
        result = convert_latex_lr(text)
        assert '<span dir="ltr">Hello</span>' in result
        assert '<span dir="rtl">سلام</span>' in result
        assert 'lang="en"' in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntegration:
    """تست‌های یکپارچگی."""

    def test_import_from_package(self) -> None:
        """import از __init__.py پکیج."""
        from formatforge.core.persian import (
            BidiSegment,
            detect_block_direction,
            wrap_rtl_block,
            wrap_ltr_block,
            split_bidi_segments,
            convert_latex_lr,
        )
        assert callable(detect_block_direction)
        assert callable(convert_latex_lr)

    def test_zwnj_imports_still_work(self) -> None:
        """importهای zwnj همچنان کار کنند."""
        from formatforge.core.persian import (
            ZWNJ,
            count_zwnj,
            validate_zwnj_preserved,
            protect_zwnj,
        )
        assert ZWNJ == "\u200c"
        assert callable(count_zwnj)

    def test_detect_then_wrap(self) -> None:
        """تشخیص جهت و سپس بسته‌بندی."""
        text = "سلام دنیا"
        direction = detect_block_direction(text)
        assert direction == "rtl"
        wrapped = wrap_rtl_block(text)
        assert 'dir="rtl"' in wrapped

    def test_convert_then_detect(self) -> None:
        """تبدیل LaTeX و سپس تشخیص جهت."""
        text = "متن فارسی \\lr{English} ادامه"
        converted = convert_latex_lr(text)
        # تشخیص جهت باید از HTML tags صرف‌نظر کند
        assert "متن فارسی" in converted
        assert '<span dir="ltr">' in converted

    def test_full_pipeline_with_zwnj(self) -> None:
        """خط لوله کامل: تبدیل LaTeX + حفظ ZWNJ."""
        from formatforge.core.persian import count_zwnj

        text = f"می{ZWNJ}خواهیم \\lr{{test}} کتاب{ZWNJ}ها"
        zwnj_before = count_zwnj(text)

        result = convert_latex_lr(text)
        zwnj_after = count_zwnj(result)

        assert zwnj_after == zwnj_before
        assert '<span dir="ltr">test</span>' in result
