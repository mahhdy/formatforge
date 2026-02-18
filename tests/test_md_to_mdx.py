"""
تست‌های تبدیل‌گر Markdown → MDX — S06-C1
Tests for the MarkdownToMDXConverter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from formatforge.core.converters.base import ConversionContext
from formatforge.core.converters.md_to_mdx import (
    MarkdownToMDXConverter,
    _detect_language,
    _detect_direction,
    _generate_slug,
    _parse_frontmatter,
    _generate_frontmatter,
)

ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def converter() -> MarkdownToMDXConverter:
    return MarkdownToMDXConverter()


@pytest.fixture
def ctx() -> ConversionContext:
    return ConversionContext()


@pytest.fixture
def simple_md(tmp_path: Path) -> Path:
    """فایل Markdown ساده."""
    p = tmp_path / "test.md"
    p.write_text(
        "---\n"
        "title: تست ساده\n"
        "slug: test-simple\n"
        "date: '2025-01-01'\n"
        "lang: fa\n"
        "dir: rtl\n"
        "---\n\n"
        "# عنوان اصلی\n\n"
        f"متن فارسی با نیم{ZWNJ}فاصله.\n\n"
        "- آیتم ۱\n"
        "- آیتم ۲\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def math_md(tmp_path: Path) -> Path:
    """فایل Markdown با فرمول ریاضی."""
    p = tmp_path / "math.md"
    p.write_text(
        "---\n"
        "title: ریاضی\n"
        "slug: math-test\n"
        "date: '2025-01-01'\n"
        "---\n\n"
        "# فرمول‌ها\n\n"
        "درون‌خطی: $E=mc^2$\n\n"
        "بلوکی:\n\n"
        "$$\n\\int_0^1 x^2 dx = \\frac{1}{3}\n$$\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def code_md(tmp_path: Path) -> Path:
    """فایل Markdown با بلوک کد."""
    p = tmp_path / "code.md"
    p.write_text(
        "---\n"
        "title: code-example\n"
        "slug: code-example\n"
        "date: '2025-01-01'\n"
        "---\n\n"
        "```python\n"
        "def hello():\n"
        "    print('hello')\n"
        "```\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def no_frontmatter_md(tmp_path: Path) -> Path:
    """فایل Markdown بدون frontmatter."""
    p = tmp_path / "bare.md"
    p.write_text(
        "# عنوان\n\nمتن ساده\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def english_md(tmp_path: Path) -> Path:
    """فایل Markdown انگلیسی."""
    p = tmp_path / "english.md"
    p.write_text(
        "---\n"
        "title: english-doc\n"
        "slug: english-doc\n"
        "date: '2025-01-01'\n"
        "lang: en\n"
        "dir: ltr\n"
        "---\n\n"
        "# Hello World\n\n"
        "This is an English document.\n",
        encoding="utf-8",
    )
    return p


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Frontmatter Parsing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFrontmatter:
    """تست تحلیل frontmatter."""

    def test_parse_valid(self) -> None:
        content = "---\ntitle: تست\nslug: test\n---\n\nBody text"
        fm, body = _parse_frontmatter(content)
        assert fm["title"] == "تست"
        assert fm["slug"] == "test"
        assert "Body text" in body

    def test_parse_no_frontmatter(self) -> None:
        content = "# Title\n\nBody"
        fm, body = _parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parse_empty_frontmatter(self) -> None:
        content = "---\n---\n\nBody"
        fm, body = _parse_frontmatter(content)
        assert "Body" in body

    def test_generate_frontmatter(self) -> None:
        data = {"title": "تست", "slug": "test", "dir": "rtl"}
        result = _generate_frontmatter(data)
        assert result.startswith("---\n")
        assert result.endswith("\n---")
        assert "title:" in result
        assert "تست" in result

    def test_zwnj_in_frontmatter(self) -> None:
        content = f"---\ntitle: نیم{ZWNJ}فاصله\nslug: test\n---\nBody"
        fm, _ = _parse_frontmatter(content)
        assert ZWNJ in fm["title"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Language Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLanguageDetection:
    """تست تشخیص زبان."""

    def test_persian(self) -> None:
        assert _detect_language("متن فارسی") == "fa"

    def test_english(self) -> None:
        assert _detect_language("English text only") == "en"

    def test_bilingual(self) -> None:
        result = _detect_language("یک two three four five six")
        assert result in ("en", "fa-en")

    def test_direction_fa(self) -> None:
        assert _detect_direction("fa") == "rtl"

    def test_direction_en(self) -> None:
        assert _detect_direction("en") == "ltr"

    def test_direction_fa_en(self) -> None:
        assert _detect_direction("fa-en") == "rtl"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Slug Generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSlugGeneration:
    """تست تولید slug."""

    def test_english_title(self) -> None:
        slug = _generate_slug("Hello World")
        assert slug == "hello-world"

    def test_persian_title(self) -> None:
        slug = _generate_slug("تست فارسی")
        # Persian chars removed, fallback
        assert slug.startswith("doc-") or len(slug) > 0

    def test_max_length(self) -> None:
        slug = _generate_slug("a" * 100)
        assert len(slug) <= 60


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDetection:
    """تست تشخیص فرمت."""

    def test_detect_md_extension(
        self, converter: MarkdownToMDXConverter, simple_md: Path,
    ) -> None:
        assert converter.detect(simple_md) is True

    def test_detect_mdx_extension(
        self, converter: MarkdownToMDXConverter, tmp_path: Path,
    ) -> None:
        p = tmp_path / "test.mdx"
        p.write_text("# Hello", encoding="utf-8")
        assert converter.detect(p) is True

    def test_reject_non_md(
        self, converter: MarkdownToMDXConverter, tmp_path: Path,
    ) -> None:
        p = tmp_path / "test.tex"
        p.write_text("\\documentclass{article}", encoding="utf-8")
        assert converter.detect(p) is False

    def test_detect_by_extension_only(
        self, converter: MarkdownToMDXConverter,
    ) -> None:
        assert converter.detect_by_extension(Path("test.md")) is True
        assert converter.detect_by_extension(Path("test.txt")) is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Metadata Extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMetadataExtraction:
    """تست استخراج متادیتا."""

    def test_extract_from_frontmatter(
        self, converter: MarkdownToMDXConverter, simple_md: Path,
    ) -> None:
        metadata = converter.extract_metadata(simple_md)
        assert "تست" in metadata.title
        assert metadata.slug == "test-simple"
        assert metadata.lang == "fa"
        assert metadata.dir == "rtl"

    def test_extract_without_frontmatter(
        self, converter: MarkdownToMDXConverter, no_frontmatter_md: Path,
    ) -> None:
        metadata = converter.extract_metadata(no_frontmatter_md)
        assert metadata.title == "عنوان"  # from heading
        assert metadata.source_format == "markdown"

    def test_math_detection(
        self, converter: MarkdownToMDXConverter, math_md: Path,
    ) -> None:
        metadata = converter.extract_metadata(math_md)
        assert metadata.math is True

    def test_code_detection(
        self, converter: MarkdownToMDXConverter, code_md: Path,
    ) -> None:
        metadata = converter.extract_metadata(code_md)
        assert metadata.code_highlight is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Full Conversion
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConversion:
    """تست تبدیل کامل."""

    def test_simple_conversion(
        self,
        converter: MarkdownToMDXConverter,
        simple_md: Path,
        ctx: ConversionContext,
    ) -> None:
        result = converter.convert(simple_md, ctx)
        assert result.status == "success"
        assert result.input_bytes > 0
        assert result.output_bytes > 0

    def test_zwnj_preserved(
        self,
        converter: MarkdownToMDXConverter,
        simple_md: Path,
        ctx: ConversionContext,
    ) -> None:
        result = converter.convert(simple_md, ctx)
        assert result.status == "success"
        mdx = ctx.extra.get("mdx_content", "")
        assert ZWNJ in mdx
        assert ctx.zwnj_count_after >= ctx.zwnj_count_before

    def test_frontmatter_in_output(
        self,
        converter: MarkdownToMDXConverter,
        simple_md: Path,
        ctx: ConversionContext,
    ) -> None:
        converter.convert(simple_md, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        assert mdx.startswith("---\n")
        assert "title:" in mdx
        assert "slug:" in mdx

    def test_math_conversion(
        self,
        converter: MarkdownToMDXConverter,
        math_md: Path,
        ctx: ConversionContext,
    ) -> None:
        result = converter.convert(math_md, ctx)
        assert result.status == "success"
        mdx = ctx.extra.get("mdx_content", "")
        # Math formulas should be preserved
        assert "$" in mdx or "$$" in mdx

    def test_code_conversion(
        self,
        converter: MarkdownToMDXConverter,
        code_md: Path,
        ctx: ConversionContext,
    ) -> None:
        result = converter.convert(code_md, ctx)
        assert result.status == "success"
        mdx = ctx.extra.get("mdx_content", "")
        assert "```python" in mdx or "python" in mdx

    def test_english_conversion(
        self,
        converter: MarkdownToMDXConverter,
        english_md: Path,
        ctx: ConversionContext,
    ) -> None:
        result = converter.convert(english_md, ctx)
        assert result.status == "success"
        mdx = ctx.extra.get("mdx_content", "")
        assert "Hello World" in mdx

    def test_output_file_written(
        self,
        converter: MarkdownToMDXConverter,
        simple_md: Path,
        tmp_path: Path,
    ) -> None:
        ctx = ConversionContext(output_dir=tmp_path / "output")
        converter.convert(simple_md, ctx)
        # Check that file was created
        output_files = list((tmp_path / "output").glob("*.mdx"))
        assert len(output_files) == 1

    def test_dry_run(
        self,
        converter: MarkdownToMDXConverter,
        simple_md: Path,
        tmp_path: Path,
    ) -> None:
        ctx = ConversionContext(
            output_dir=tmp_path / "output",
        )
        ctx.dry_run = True
        result = converter.convert(simple_md, ctx)
        assert result.status == "success"
        # No file should be created in dry run
        output_dir = tmp_path / "output"
        if output_dir.exists():
            assert list(output_dir.glob("*.mdx")) == []

    def test_nonexistent_file(
        self,
        converter: MarkdownToMDXConverter,
        ctx: ConversionContext,
    ) -> None:
        from formatforge.core.converters.base import ConversionError

        with pytest.raises(ConversionError):
            converter.convert(Path("/nonexistent.md"), ctx)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Converter Properties
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConverterProperties:
    """تست خصوصیات تبدیل‌گر."""

    def test_format_name(self, converter: MarkdownToMDXConverter) -> None:
        assert converter.format_name == "markdown"

    def test_extensions(self, converter: MarkdownToMDXConverter) -> None:
        assert ".md" in converter.file_extensions
        assert ".mdx" in converter.file_extensions

    def test_repr(self, converter: MarkdownToMDXConverter) -> None:
        r = repr(converter)
        assert "markdown" in r.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestValidation:
    """تست اعتبارسنجی خروجی."""

    def test_validate_quality(
        self,
        converter: MarkdownToMDXConverter,
        simple_md: Path,
        ctx: ConversionContext,
    ) -> None:
        result = converter.convert(simple_md, ctx)
        assert result.status == "success"
        report = converter.validate_output(result, ctx)
        assert report.score > 0
        assert report.zwnj.preserved is True
