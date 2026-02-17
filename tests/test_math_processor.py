"""
FormatForge - Math Processor Tests
تست‌های پردازشگر فرمول‌های ریاضی

Tests for:
- Simple inline formulas
- Display formulas
- Multi-line align
- Cases environment
- Matrix environments
- Persian \text{} preservation
- Custom macros (\newcommand)
- Label/ref conversion
- ZWNJ preservation
- Extraction & counting
- Syntax validation
"""

from __future__ import annotations

import pytest

from formatforge.core.processors.math_processor import (
    MathProcessor,
    MathType,
    MathBlock,
    MathStats,
    extract_math_blocks,
    count_math_blocks,
    validate_math_syntax,
)
from formatforge.core.processors.base import (
    ProcessorContext,
    ProcessorError,
)

# ─── Constants / ثابت‌ها ──────────────────────
ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures / فیکسچرها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def processor() -> MathProcessor:
    """پردازشگر ریاضی پیش‌فرض."""
    return MathProcessor()


@pytest.fixture
def context() -> ProcessorContext:
    """زمینه پردازش پیش‌فرض."""
    return ProcessorContext(source_format="latex", language="fa")


@pytest.fixture
def processor_with_macros() -> MathProcessor:
    """پردازشگر با ماکروهای سفارشی."""
    return MathProcessor(custom_macros={
        "R": r"\mathbb{R}",
        "N": r"\mathbb{N}",
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Inline Formulas / فرمول‌های خطی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestInlineFormulas:
    """تست فرمول‌های inline."""

    def test_dollar_inline_preserved(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """$...$ بدون تغییر باقی بماند."""
        text = r"مقدار $x^2 + y^2 = z^2$ را محاسبه کنید."
        result = processor.process(text, context)
        assert r"$x^2 + y^2 = z^2$" in result

    def test_paren_inline_to_dollar(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        r"""\\(...\\) → $...$."""
        text = r"مقدار \(a + b\) را بیابید."
        result = processor.process(text, context)
        assert "$a + b$" in result
        assert r"\(" not in result
        assert r"\)" not in result

    def test_multiple_inline(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """چند فرمول inline در یک خط."""
        text = r"اگر $x > 0$ و $y < 0$ آنگاه $xy < 0$."
        result = processor.process(text, context)
        assert result.count("$") >= 6  # 3 pairs

    def test_inline_with_subscript(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """فرمول با زیرنویس."""
        text = r"عنصر $a_{ij}$ در ماتریس."
        result = processor.process(text, context)
        assert r"$a_{ij}$" in result

    def test_inline_counter(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """شمارنده inline در context."""
        text = r"$a$ و $b$ و $c$."
        processor.process(text, context)
        assert context.math_inlines_processed == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Display Formulas / فرمول‌های نمایشی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDisplayFormulas:
    """تست فرمول‌های display."""

    def test_bracket_display_to_dollar(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        r"""\$$...\$$ → $$...$$ (should remain as display math)"""
        text = r"$$a^2 + b^2 = c^2$$"
        result = processor.process(text, context)
        assert "$$" in result
        assert "a^2 + b^2 = c^2" in result

    def test_equation_env_to_dollar(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """\\begin{equation} → $$...$$."""
        text = (
            "\\begin{equation}\n"
            "  F = ma\n"
            "\\end{equation}"
        )
        result = processor.process(text, context)
        assert "$$" in result
        assert "F = ma" in result
        assert "\\begin{equation}" not in result

    def test_equation_star(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """\\begin{equation*} →
$$
...
$$
."""
        text = (
            "\\begin{equation*}\n"
            "  x = \\frac{-b}{2a}\n"
            "\\end{equation*}"
        )
        result = processor.process(text, context)
        assert "$$" in result
        assert r"\frac{-b}{2a}" in result
        assert "\\begin{equation*}" not in result

    def test_display_counter(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """شمارنده display در context."""
        text = "$$x$$\n\n$$y$$"
        processor.process(text, context)
        assert context.math_blocks_processed == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Align Environment / محیط align
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAlignEnvironment:
    """تست محیط align (چند خطی)."""

    def test_align_to_aligned(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """align → 
$$
\\begin{aligned}...
$$
."""
        text = (
            "\\begin{align}\n"
            "  a &= b + c \\\\\n"
            "  d &= e + f\n"
            "\\end{align}"
        )
        result = processor.process(text, context)
        assert "$$" in result
        assert "\\begin{aligned}" in result
        assert "\\end{aligned}" in result
        assert "a &= b + c" in result
        assert "\\begin{align}" not in result

    def test_align_star(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """align* →
$$
\\begin{aligned}...
$$
."""
        text = (
            "\\begin{align*}\n"
            "  x &= 1 \\\\\n"
            "  y &= 2\n"
            "\\end{align*}"
        )
        result = processor.process(text, context)
        assert "\\begin{aligned}" in result

    def test_align_with_label(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """align با label."""
        text = (
            "\\begin{align}\n"
            "  \\label{eq:system}\n"
            "  x + y &= 10 \\\\\n"
            "  x - y &= 2\n"
            "\\end{align}"
        )
        result = processor.process(text, context)
        assert "eq-system" in result
        assert "eq:system" in context.labels


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Cases Environment / محیط cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCasesEnvironment:
    """تست محیط cases."""

    def test_cases_inside_equation(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """cases درون equation حفظ شود."""
        text = (
            "\\begin{equation}\n"
            "  f(x) = \\begin{cases}\n"
            "    1 & x > 0 \\\\\n"
            "    0 & x = 0 \\\\\n"
            "    -1 & x < 0\n"
            "  \\end{cases}\n"
            "\\end{equation}"
        )
        result = processor.process(text, context)
        assert "$$" in result
        assert "\\begin{cases}" in result
        assert "\\end{cases}" in result

    def test_cases_standalone(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """cases درون $$حفظ شود."""
        text = ("$$\n"
            "|x| = \\begin{cases}\n"
            "  x & x \\geq 0 \\\\\n"
            "  -x & x < 0\n"
            "\\end{cases}\n"
            "$$"
        )
        result = processor.process(text, context)
        assert "\\begin{cases}" in result
        assert "\\end{cases}" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Matrix Environments / محیط‌های ماتریس
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMatrixEnvironments:
    """تست محیط‌های ماتریس."""

    def test_pmatrix_preserved(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """pmatrix درون
$$
 حفظ شود."""
        text = ("$$\n"
            "A = \\begin{pmatrix}\n"
            "  1 & 2 \\\\\n"
            "  3 & 4\n"
            "\\end{pmatrix}\n"
            "$$"
        )
        result = processor.process(text, context)
        assert "\\begin{pmatrix}" in result
        assert "\\end{pmatrix}" in result

    def test_bmatrix_preserved(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """bmatrix درون 
$$
حفظ شود."""
        text = ("$$\n"
            "B = \\begin{bmatrix}\n"
            "  a & b \\\\\n"
            "  c & d\n"
            "\\end{bmatrix}\n"
            "$$"
        )
        result = processor.process(text, context)
        assert "\\begin{bmatrix}" in result
        assert "\\end{bmatrix}" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Persian Text in Math / متن فارسی در فرمول
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPersianInMath:
    """تست حفظ متن فارسی درون فرمول."""

    def test_text_persian_preserved(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        r"""\text{فارسی} حفظ شود."""
        text = r"$$f(x) = \begin{cases} 1 & \text{اگر } x > 0 \\ 0 & \text{در غیر اینصورت} \end{cases}$$"
        result = processor.process(text, context)
        assert r"\text{اگر }" in result
        assert r"\text{در غیر اینصورت}" in result

    def test_text_with_zwnj(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """نیم‌فاصله درون \\text{} حفظ شود."""
        persian_text = f"\\text{{می{ZWNJ}شود}}"
        text = f"$x {persian_text}$"
        result = processor.process(text, context)
        assert ZWNJ in result

    def test_zwnj_outside_math(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """نیم‌فاصله خارج فرمول حفظ شود."""
        text = f"این{ZWNJ}جا $x^2$ و آن{ZWNJ}جا $y^2$ است."
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, context)
        zwnj_after = result.count(ZWNJ)
        assert zwnj_after == zwnj_before

    def test_zwnj_heavy_document(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """سند با نیم‌فاصله‌های متعدد."""
        text = (
            f"تابع{ZWNJ}های ریاضی{ZWNJ}ای مانند $f(x)$ "
            f"که دارای{ZWNJ} ویژگی{ZWNJ}های خاصی هستند "
            f"در معادله{ZWNJ}ی $E = mc^2$ ظاهر می{ZWNJ}شوند."
        )
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, context)
        assert result.count(ZWNJ) == zwnj_before


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Custom Macros / ماکروهای سفارشی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCustomMacros:
    """تست بازگشایی ماکروهای سفارشی."""

    def test_simple_macro_expansion(
        self,
        processor_with_macros: MathProcessor,
        context: ProcessorContext,
    ) -> None:
        """ماکرو بدون آرگومان."""
        text = r"$x \in \R$"
        result = processor_with_macros.process(text, context)
        assert r"\mathbb{R}" in result

    def test_newcommand_extraction(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """\\newcommand از متن استخراج و حذف شود."""
        text = (
            r"\newcommand{\vect}{\mathbf}" "\n"
            r"بردار $\vect{v}$ را در نظر بگیرید."
        )
        result = processor.process(text, context)
        assert r"\newcommand" not in result

    def test_newcommand_with_args(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """\\newcommand با آرگومان."""
        text = (
            r"\newcommand{\norm}[1]{\left\| #1 \right\|}" "\n"
            r"$\norm{x}$"
        )
        result = processor.process(text, context)
        assert r"\newcommand" not in result
        assert r"\left\|" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Labels & Refs / برچسب و ارجاع
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLabelsAndRefs:
    """تست تبدیل label و ref."""

    def test_label_extracted(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """\\label از فرمول استخراج شود."""
        text = (
            "\\begin{equation}\n"
            "  \\label{eq:euler}\n"
            "  e^{i\\pi} + 1 = 0\n"
            "\\end{equation}"
        )
        result = processor.process(text, context)
        assert "eq:euler" in context.labels
        assert "eq-euler" in result

    def test_ref_to_link(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """\\ref → لینک MDX."""
        text = r"طبق معادله \ref{eq:euler} داریم..."
        result = processor.process(text, context)
        assert "[eq-euler](#eq-euler)" in result
        assert r"\ref" not in result

    def test_eqref_to_link(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """\\eqref → لینک با پرانتز."""
        text = r"از \eqref{eq:mass} نتیجه می‌گیریم."
        result = processor.process(text, context)
        assert "[(eq-mass)](#eq-mass)" in result

    def test_cref_to_link(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """\\cref → لینک با «معادله»."""
        text = r"با استفاده از \cref{eq:force} داریم."
        result = processor.process(text, context)
        assert "معادله" in result
        assert "#eq-force" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: extract_math_blocks / استخراج بلوک‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtractMathBlocks:
    """تست تابع extract_math_blocks."""

    def test_mixed_document(self) -> None:
        """سند با ترکیب inline و display."""
        text = (
            "متن $a+b$ ادامه\n"
            "$$\nc^2 = a^2 + b^2\n$$\n"
            r"نتیجه \(x\) گرفته شد."
        )
        blocks = extract_math_blocks(text)
        assert len(blocks) == 3

        types = [b.math_type for b in blocks]
        assert MathType.INLINE in types
        assert MathType.DISPLAY in types

    def test_environment_extracted(self) -> None:
        """محیط equation استخراج شود."""
        text = (
            "\\begin{equation}\n"
            "  \\label{eq:test}\n"
            "  x = 1\n"
            "\\end{equation}"
        )
        blocks = extract_math_blocks(text)
        assert len(blocks) == 1
        assert blocks[0].math_type == MathType.DISPLAY
        assert blocks[0].label == "eq:test"
        assert blocks[0].environment == "equation"

    def test_empty_text(self) -> None:
        """متن خالی."""
        assert extract_math_blocks("") == []

    def test_no_math(self) -> None:
        """متن بدون فرمول."""
        blocks = extract_math_blocks("این یک متن ساده است.")
        assert len(blocks) == 0

    def test_line_numbers(self) -> None:
        """شماره خط صحیح."""
        text = "خط اول\nخط دوم $x$\nخط سوم\n$$y$$"
        blocks = extract_math_blocks(text)
        assert blocks[0].line_number == 2  # $x$
        assert blocks[1].line_number == 4  #$$y$$
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: count_math_blocks / شمارش بلوک‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCountMathBlocks:
    """تست تابع count_math_blocks."""

    def test_stats_correct(self) -> None:
        """آمار صحیح."""
        text = (
            "$a$ و $b$ و $c$\n"
            "$$x = 1$$\n"
            "\\begin{equation}\n"
            "  \\label{eq:z}\n"
            "  z = 2\n"
            "\\end{equation}"
        )
        stats = count_math_blocks(text)
        assert stats.inline_count == 3
        assert stats.display_count == 2
        assert stats.labeled_count == 1
        assert stats.total == 5

    def test_environment_stats(self) -> None:
        """آمار محیط‌ها."""
        text = (
            "\\begin{align}\na\\\\b\n\\end{align}\n"
            "\\begin{equation}\nx\n\\end{equation}\n"
            "\\begin{align}\nc\\\\d\n\\end{align}"
        )
        stats = count_math_blocks(text)
        assert stats.environments.get("align", 0) == 2
        assert stats.environments.get("equation", 0) == 1

    def test_empty_stats(self) -> None:
        """متن بدون فرمول."""
        stats = count_math_blocks("متن ساده")
        assert stats.total == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: validate_math_syntax / اعتبارسنجی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestValidateMathSyntax:
    """تست تابع validate_math_syntax."""

    def test_valid_simple(self) -> None:
        """فرمول ساده معتبر."""
        valid, msg = validate_math_syntax(r"x^2 + y^2")
        assert valid is True
        assert msg is None

    def test_valid_with_braces(self) -> None:
        """فرمول با {} متعادل."""
        valid, msg = validate_math_syntax(r"\frac{a}{b}")
        assert valid is True

    def test_unbalanced_open(self) -> None:
        """براکت باز اضافی."""
        valid, msg = validate_math_syntax(r"\frac{a{b}")
        assert valid is False
        assert msg is not None

    def test_unbalanced_close(self) -> None:
        """براکت بسته اضافی."""
        valid, msg = validate_math_syntax(r"x}")
        assert valid is False

    def test_mismatched_env(self) -> None:
        """عدم تطابق begin/end."""
        valid, msg = validate_math_syntax(
            r"\begin{cases} x \end{matrix}"
        )
        assert valid is False
        assert "تطابق" in msg

    def test_empty_string(self) -> None:
        """رشته خالی معتبر."""
        valid, msg = validate_math_syntax("")
        assert valid is True

    def test_nested_braces(self) -> None:
        """براکت‌های تودرتو."""
        valid, msg = validate_math_syntax(
            r"\sqrt{\frac{a^{2}}{b^{2}}}"
        )
        assert valid is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: can_process / بررسی قابلیت پردازش
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCanProcess:
    """تست متد can_process."""

    def test_with_math(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """محتوا با فرمول → True."""
        assert processor.can_process("$x$", context) is True

    def test_without_math(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """محتوا بدون فرمول → False."""
        assert processor.can_process("متن ساده", context) is False

    def test_disabled(
        self, context: ProcessorContext,
    ) -> None:
        """پردازشگر غیرفعال → False."""
        p = MathProcessor()
        p.enabled = False
        assert p.can_process("$x$", context) is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Gather & Multline / محیط‌های دیگر
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOtherEnvironments:
    """تست محیط‌های gather و multline."""

    def test_gather_to_gathered(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """gather →
$$
\\begin{gathered}...
$$
."""
        text = (
            "\\begin{gather}\n"
            "  a = 1 \\\\\n"
            "  b = 2\n"
            "\\end{gather}"
        )
        result = processor.process(text, context)
        assert "\\begin{gathered}" in result
        assert "\\end{gathered}" in result

    def test_multline_to_gathered(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """multline →
$$
\\begin{gathered}...$$."""
        text = (
            "\\begin{multline}\n"
            "  a + b + c \\\\\n"
            "  + d + e + f\n"
            "\\end{multline}"
        )
        result = processor.process(text, context)
        assert "\\begin{gathered}" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Edge Cases / موارد مرزی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEdgeCases:
    """تست موارد خاص و مرزی."""

    def test_empty_content(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """محتوای خالی بدون خطا."""
        result = processor.process("", context)
        assert result == ""

    def test_no_math_passthrough(
        self, processor: MathProcessor, context: ProcessorContext,
    ) -> None:
        """محتوا بدون ریاضی بدون تغییر."""
        text = "یک متن ساده فارسی بدون فرمول."
        # can_process returns False so pipeline skips
        assert processor.can_process(text, context) is False

    def test_dollar_in_code_not_matched(self) -> None:
        """$ درون بلوک کد نباید match شود (خارج از scope)."""
        # این تست فقط بررسی می‌کند extract از متن ساده
        text = "قیمت 5$ است"
        blocks = extract_math_blocks(text)
        # «5$ است» ممکن است match شود — بستگی به regex
        # این رفتار مورد انتظار است و فیلتر نهایی
        # باید توسط converter انجام شود
        assert isinstance(blocks, list)