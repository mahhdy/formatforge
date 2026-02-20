"""
Quality Module Tests
تست‌های ماژول کیفیت

Tests:
- Structural tests
- RTL/Persian tests
- Quality score calculation
"""

import pytest

from formatforge.core.quality.structural_test import (
    run_structural_tests,
    check_frontmatter_valid,
    check_jsx_syntax,
    test_imports_valid as _check_imports_valid,
    test_mdx_compiles as _check_mdx_compiles,
)

from formatforge.core.quality.rtl_test import (
    run_rtl_tests,
    _check_dir_rtl_set,
    test_lang_fa_set as _check_lang_fa_set,
    _check_zwnj_preserved,
    _test_quotes_correct,
    ZWNJ,
)

from formatforge.core.quality.quality_score import (
    calculate_quality_score,
    analyze_content,
    QualityReport,
)


# ─── Structural Tests ───────────────────────

class TestFrontmatterValidation:
    """تست‌های اعتبارسنجی frontmatter."""

    def test_valid_frontmatter(self):
        """frontmatter معتبر."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: fa
dir: rtl
---
# Content
"""
        valid, error = check_frontmatter_valid(mdx)
        assert valid is True
        assert error is None

    def test_missing_frontmatter(self):
        """frontmatter وجود ندارد."""
        mdx = "# Just content"
        valid, error = check_frontmatter_valid(mdx)
        assert valid is False
        assert error is not None and "missing" in error.lower()

    def test_missing_required_field(self):
        """فیلد اجباری وجود ندارد."""
        mdx = """---
title: "Test"
---
# Content
"""
        valid, error = check_frontmatter_valid(mdx)
        assert valid is False
        assert error is not None


class TestJSXSyntax:
    """تست‌های syntax JSX."""

    def test_valid_jsx(self):
        """JSX معتبر."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: "fa"
---
<div className="container">
  <span>Hello</span>
</div>
"""
        valid, error = check_jsx_syntax(mdx)
        assert valid is True

    def test_class_attribute(self):
        """class به جای className."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: "fa"
---
<div class="container">Hello</div>
"""
        valid, error = check_jsx_syntax(mdx)
        assert valid is False
        assert "className" in error


class TestImportValidation:
    """تست‌های اعتبارسنجی import."""

    def test_imports_valid(self):
        """import ها معتبر."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: "fa"
---
import Theorem from '@/components/Theorem';

<Theorem>Content</Theorem>
"""
        valid, error = _check_imports_valid(mdx)
        assert valid is True

    def test_missing_import(self):
        """import وجود ندارد."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: "fa"
---

<Theorem>Content</Theorem>
"""
        valid, error = _check_imports_valid(mdx)
        assert valid is False
        assert "Theorem" in error


# ─── RTL/Persian Tests ─────────────────────

class TestRTLValidation:
    """تست‌های اعتبارسنجی RTL."""

    def test_dir_rtl_set(self):
        """dir: rtl تنظیم شده."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: fa
dir: rtl
---
# Content
"""
        valid, error = _check_dir_rtl_set(mdx)
        assert valid is True

    def test_dir_missing(self):
        """dir تنظیم نشده."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: fa
---
# Content
"""
        valid, error = _check_dir_rtl_set(mdx)
        assert valid is False


class TestLangValidation:
    """تست‌های اعتبارسنجی زبان."""

    def test_lang_fa(self):
        """lang: fa تنظیم شده."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: fa
dir: rtl
---
# Content
"""
        valid, error = _check_lang_fa_set(mdx)
        assert valid is True

    def test_lang_fa_en(self):
        """lang: fa-en تنظیم شده."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: fa-en
dir: rtl
---
# Content
"""
        valid, error = _check_lang_fa_set(mdx)
        assert valid is True


class TestZWNJPreservation:
    """تست‌های حفظ ZWNJ."""

    def test_zwnj_preserved(self):
        """ZWNJ حفظ شده."""
        source = f"Test{ZWNJ}content"
        output = f"Test{ZWNJ}content"

        report = _check_zwnj_preserved(source, output)

        assert report.count_before == 1
        assert report.count_after == 1
        assert report.is_preserved is True

    def test_zwnj_lost(self):
        """ZWNJ از دست رفته."""
        source = f"Test{ZWNJ}content"
        output = "Testcontent"

        report = _check_zwnj_preserved(source, output)

        assert report.count_before == 1
        assert report.count_after == 0
        assert report.is_preserved is False


class TestQuotationMarks:
    """تست‌های گیومه."""

    def test_persian_quotes(self):
        """گیومه‌های فارسی."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: "fa"
dir: "rtl"
---
# Content

«متن فارسی»
"""
        valid, error = _test_quotes_correct(mdx)
        # Should pass since Persian quotes are used
        assert valid is True


# ─── Quality Score Tests ───────────────────

class TestQualityScore:
    """تست‌های امتیاز کیفیت."""

    def test_perfect_document(self):
        """سند بدون مشکل."""
        source = r"\section{Test}"
        output = """---
title: "Test"
date: "2025-01-01"
lang: "fa"
dir: "rtl"
---
# Test
"""

        report = calculate_quality_score(
            source=source,
            output=output,
            structural_passed=True,
            math_parse_rate=1.0,
            persian_tests_passed=1.0,
            link_validity=1.0,
        )

        assert report.score >= 90

    def test_content_analysis(self):
        """تحلیل محتوا."""
        source = r"\section{Test}" + "\n" + r"\section{Another}"
        output = """---
title: "Test"
date: "2025-01-01"
lang: "fa"
dir: "rtl"
---
# Test

## Another
"""

        report = analyze_content(source, output)

        assert report.headings_source == 2
        assert report.headings_output == 2

    def test_grade_excellent(self):
        """درجه عالی."""
        report = calculate_quality_score(
            source="test",
            output="test",
            structural_passed=True,
            math_parse_rate=1.0,
            persian_tests_passed=1.0,
            link_validity=1.0,
        )

        assert report.score >= 90

    def test_grade_poor(self):
        """درجه ضعیف."""
        report = calculate_quality_score(
            source="test",
            output="",
            structural_passed=False,
            math_parse_rate=0.0,
            persian_tests_passed=0.0,
            link_validity=0.0,
        )

        assert report.score < 50


# ─── Integration Tests ──────────────────────

class TestQualityIntegration:
    """تست‌های یکپارچه کیفیت."""

    def test_full_structural_test(self):
        """تست ساختاری کامل."""
        mdx = """---
title: "Test"
date: "2025-01-01"
lang: "fa"
dir: "rtl"
---
import Theorem from '@/components/Theorem';

<Theorem id="test">Content</Theorem>
"""

        result = run_structural_tests(mdx)

        assert result.frontmatter_valid is True
        assert result.jsx_valid is True
        assert result.imports_valid is True

    def test_full_rtl_test(self):
        """تست RTL کامل."""
        source = f"متن{ZWNJ}تست"
        mdx = f"""---
title: "Test"
date: "2025-01-01"
lang: "fa"
dir: "rtl"
---
# محتوا

متن{ZWNJ}تست
"""

        result = run_rtl_tests(source, mdx)

        assert result.dir_rtl_set is True
        assert result.lang_fa_set is True
        assert result.zwnj_preserved is True
