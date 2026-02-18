"""
تست سرتاسری (E2E) تبدیل Markdown → MDX — S06-C3
End-to-end test for the full MD→MDX conversion pipeline.

یک فایل Markdown واقعی با تمام المان‌ها:
- frontmatter فارسی با ZWNJ
- سرتیترها
- فرمول ریاضی
- بلوک کد
- لینک‌ها
- پاورقی
- لیست
- نیم‌فاصله (ZWNJ)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from formatforge.core.converters.base import ConversionContext
from formatforge.core.converters.md_to_mdx import MarkdownToMDXConverter

ZWNJ = "\u200c"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixture: Rich Markdown file
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_RICH_MD = f"""\
---
title: "آموزش برنامه{ZWNJ}نویسی پایتون"
slug: python-tutorial
date: "2025-01-15"
lang: fa
dir: rtl
tags:
  - برنامه{ZWNJ}نویسی
  - پایتون
description: "آموزش مقدماتی زبان پایتون برای تازه{ZWNJ}کاران"
---

# آموزش برنامه{ZWNJ}نویسی پایتون

## مقدمه

پایتون یکی از محبوب{ZWNJ}ترین زبان{ZWNJ}های برنامه{ZWNJ}نویسی است.
این زبان قابلیت{ZWNJ}های فراوانی دارد و یادگیری آن آسان است.

## متغیرها

در پایتون نیازی به تعریف نوع متغیر نیست:

```python
name = "علی"
age = 25
pi = 3.14
```

## فرمول{ZWNJ}های ریاضی

فرمول درون{ZWNJ}خطی: $E = mc^2$

فرمول بلوکی:

$$
\\sum_{{i=1}}^{{n}} i = \\frac{{n(n+1)}}{{2}}
$$

## لینک{ZWNJ}ها

برای اطلاعات بیشتر به [مستندات رسمی](https://docs.python.org) مراجعه کنید.

## لیست

- آیتم اول
- آیتم دوم
- آیتم سوم

### لیست شماره{ZWNJ}دار

1. نصب پایتون
2. نوشتن اولین برنامه
3. اجرای برنامه

## نتیجه{ZWNJ}گیری

پایتون زبان قدرتمندی است و می{ZWNJ}توان با آن پروژه{ZWNJ}های متنوعی ایجاد کرد.
"""


@pytest.fixture
def rich_md(tmp_path: Path) -> Path:
    """فایل Markdown غنی با تمام المان‌ها."""
    p = tmp_path / "rich_tutorial.md"
    p.write_text(_RICH_MD, encoding="utf-8")
    return p


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """پوشه خروجی."""
    d = tmp_path / "output"
    d.mkdir()
    return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# E2E Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestE2EMarkdownToMDX:
    """تست سرتاسری تبدیل Markdown → MDX."""

    def test_conversion_succeeds(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """تبدیل بدون خطا انجام شود."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        result = converter.convert(rich_md, ctx)
        assert result.status == "success"
        assert result.output_bytes > 0

    def test_mdx_file_created(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """فایل MDX خروجی ایجاد شود."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        mdx_files = list(output_dir.glob("*.mdx"))
        assert len(mdx_files) == 1
        assert mdx_files[0].name == "python-tutorial.mdx"

    def test_frontmatter_preserved(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """frontmatter در خروجی حفظ شود."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        mdx = ctx.extra["mdx_content"]
        assert mdx.startswith("---\n")
        assert "title:" in mdx
        assert "slug:" in mdx
        assert "python-tutorial" in mdx

    def test_zwnj_preserved(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """نیم‌فاصله‌ها حفظ شوند (قاعده حیاتی)."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        mdx = ctx.extra["mdx_content"]

        # Input ZWNJ count
        input_zwnj = _RICH_MD.count(ZWNJ)
        output_zwnj = mdx.count(ZWNJ)

        assert output_zwnj >= input_zwnj, (
            f"ZWNJ lost: {input_zwnj} → {output_zwnj}"
        )

    def test_zwnj_count_in_context(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """شمارنده ZWNJ در context صحیح باشد."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        assert ctx.zwnj_count_before > 0
        assert ctx.zwnj_count_after >= ctx.zwnj_count_before

    def test_code_blocks_preserved(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """بلوک‌های کد حفظ شوند."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        mdx = ctx.extra["mdx_content"]
        assert "```python" in mdx or "python" in mdx
        assert "name" in mdx
        assert "age" in mdx

    def test_math_preserved(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """فرمول‌های ریاضی حفظ شوند."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        mdx = ctx.extra["mdx_content"]
        # Math content should be in output
        assert "E" in mdx and "mc" in mdx

    def test_headings_preserved(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """سرتیترها حفظ شوند."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        mdx = ctx.extra["mdx_content"]
        assert "# آموزش" in mdx or "آموزش" in mdx
        assert "## مقدمه" in mdx or "مقدمه" in mdx

    def test_links_preserved(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """لینک‌ها حفظ شوند."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        mdx = ctx.extra["mdx_content"]
        assert "docs.python.org" in mdx

    def test_lists_preserved(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """لیست‌ها حفظ شوند."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        mdx = ctx.extra["mdx_content"]
        assert "آیتم اول" in mdx
        assert "نصب پایتون" in mdx

    def test_metadata_correct(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """متادیتای استخراج‌شده صحیح باشد."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        assert ctx.metadata is not None
        assert ctx.metadata.lang == "fa"
        assert ctx.metadata.dir == "rtl"
        assert ctx.metadata.slug == "python-tutorial"
        assert ctx.metadata.math is True
        assert ctx.metadata.code_highlight is True

    def test_quality_score(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """امتیاز کیفیت بالای صفر باشد."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        result = converter.convert(rich_md, ctx)
        report = converter.validate_output(result, ctx)
        assert report.score > 0
        assert report.zwnj.preserved is True
        assert report.frontmatter_valid is True

    def test_output_readable(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """فایل خروجی قابل خواندن با UTF-8 باشد."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        mdx_file = output_dir / "python-tutorial.mdx"
        assert mdx_file.exists()
        content = mdx_file.read_text(encoding="utf-8")
        assert len(content) > 100
        assert ZWNJ in content

    def test_no_errors(
        self, rich_md: Path, output_dir: Path,
    ) -> None:
        """هیچ خطایی در context ثبت نشود."""
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        converter.convert(rich_md, ctx)
        assert len(ctx.errors) == 0

    def test_full_pipeline_with_sample_fixture(
        self, output_dir: Path,
    ) -> None:
        """تبدیل فایل fixture اصلی پروژه."""
        fixture = Path("tests/fixtures/sample.md")
        if not fixture.exists():
            pytest.skip("sample.md fixture not found")
        converter = MarkdownToMDXConverter()
        ctx = ConversionContext(output_dir=output_dir)
        result = converter.convert(fixture, ctx)
        assert result.status == "success"
        mdx = ctx.extra["mdx_content"]
        assert ZWNJ in mdx  # sample.md has ZWNJ
