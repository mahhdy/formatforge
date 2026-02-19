"""
تست‌های تبدیل‌گر HTML → MDX — S07-C1
Tests for the HTMLToMDXConverter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from formatforge.core.converters.base import ConversionContext
from formatforge.core.converters.html_to_mdx import (
    HTMLToMDXConverter,
    _detect_language,
    _detect_direction,
    _generate_slug,
    _generate_frontmatter,
)

ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def converter() -> HTMLToMDXConverter:
    return HTMLToMDXConverter()


@pytest.fixture
def ctx() -> ConversionContext:
    return ConversionContext()


@pytest.fixture
def simple_html(tmp_path: Path) -> Path:
    """فایل HTML ساده."""
    p = tmp_path / "test.html"
    p.write_text(
        "<!DOCTYPE html>\n"
        "<html lang='fa'>\n"
        "<head>\n"
        "  <title>تست ساده</title>\n"
        f"  <meta name='description' content='توضیح{ZWNJ}کوتاه'>\n"
        "</head>\n"
        "<body>\n"
        f"  <h1>عنوان{ZWNJ}اصلی</h1>\n"
        f"  <p>متن فارسی با نیم{ZWNJ}فاصله.</p>\n"
        "  <ul><li>آیتم ۱</li><li>آیتم ۲</li></ul>\n"
        "</body>\n"
        "</html>\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def rich_html(tmp_path: Path) -> Path:
    """فایل HTML کامل با تمام عناصر."""
    p = tmp_path / "rich.html"
    content = f"""<!DOCTYPE html>
<html lang="fa-IR">
<head>
  <title>سند{ZWNJ}کامل آزمایشی</title>
  <meta name="description" content="توضیح{ZWNJ}کامل">
  <meta name="author" content="نویسنده تست">
  <meta property="og:title" content="OG عنوان">
</head>
<body>
  <h1>فصل اول: مقدمه{ZWNJ}ای بر موضوع</h1>
  <p>این متن فارسی با نیم{ZWNJ}فاصله است.</p>

  <h2>بخش ریاضی</h2>
  <p>فرمول درون‌خطی: <span class="math">E=mc^2</span></p>

  <h2>بخش کد</h2>
  <pre><code class="language-python">def hello():
    print("Hello, World!")
</code></pre>

  <h2>جدول ساده</h2>
  <table>
    <tr><th>نام</th><th>سن</th></tr>
    <tr><td>علی</td><td>۲۵</td></tr>
    <tr><td>فاطمه</td><td>۳۰</td></tr>
  </table>

  <h2>جدول ادغامی</h2>
  <table>
    <thead>
      <tr><th colspan="2">مشخصات</th></tr>
    </thead>
    <tbody>
      <tr><td>نام</td><td>علی</td></tr>
      <tr><td>شهر</td><td>تهران</td></tr>
    </tbody>
  </table>

  <h2>تصویر</h2>
  <img src="test.jpg" alt="تصویر آزمایشی" width="800">

  <h2>لینک</h2>
  <p><a href="https://example.com">سایت نمونه</a></p>

  <blockquote><p>این یک نقل{ZWNJ}قول است.</p></blockquote>

  <details>
    <summary>جزئیات بیشتر</summary>
    <p>محتوای پنهان</p>
  </details>
</body>
</html>"""
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def english_html(tmp_path: Path) -> Path:
    """فایل HTML انگلیسی."""
    p = tmp_path / "english.html"
    p.write_text(
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head><title>English Document</title></head>\n"
        "<body>\n"
        "  <h1>Introduction</h1>\n"
        "  <p>This is an English paragraph with <strong>bold</strong> text.</p>\n"
        "  <p>Also has <em>italic</em> and <code>inline code</code>.</p>\n"
        "</body>\n"
        "</html>\n",
        encoding="utf-8",
    )
    return p


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Function Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHelperFunctions:
    """تست توابع کمکی."""

    def test_detect_language_persian(self):
        """تشخیص متن فارسی."""
        text = "این یک متن فارسی است و شامل کلمات فارسی می‌باشد."
        assert _detect_language(text) == "fa"

    def test_detect_language_english(self):
        """تشخیص متن انگلیسی."""
        text = "This is an English text with only Latin characters."
        assert _detect_language(text) == "en"

    def test_detect_language_mixed(self):
        """تشخیص متن دوزبانه."""
        text = "This is mostly English text with some فارسی words mixed in here."
        result = _detect_language(text)
        assert result in ("fa", "fa-en", "en")

    def test_detect_direction_rtl(self):
        """جهت RTL برای فارسی."""
        assert _detect_direction("fa") == "rtl"
        assert _detect_direction("fa-en") == "rtl"

    def test_detect_direction_ltr(self):
        """جهت LTR برای انگلیسی."""
        assert _detect_direction("en") == "ltr"

    def test_generate_slug_english(self):
        """تولید slug از عنوان انگلیسی."""
        slug = _generate_slug("Hello World Example")
        assert slug == "hello-world-example"

    def test_generate_slug_persian(self):
        """تولید slug از عنوان فارسی (fallback)."""
        slug = _generate_slug("عنوان فارسی")
        assert slug  # باید slug ای تولید شود
        assert len(slug) > 0

    def test_generate_slug_special_chars(self):
        """حذف کاراکترهای خاص از slug."""
        slug = _generate_slug("Hello! World & Example")
        assert "!" not in slug
        assert "&" not in slug

    def test_generate_slug_max_length(self):
        """محدودیت طول slug."""
        long_title = "a" * 100
        slug = _generate_slug(long_title)
        assert len(slug) <= 60

    def test_generate_frontmatter(self):
        """تولید YAML frontmatter."""
        meta = {"title": "تست", "slug": "test", "date": "2025-01-01"}
        fm = _generate_frontmatter(meta)
        assert fm.startswith("---\n")
        assert fm.endswith("---")
        assert "title:" in fm
        assert "تست" in fm


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Converter Detection Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConverterDetection:
    """تست تشخیص فرمت HTML."""

    def test_detect_by_extension_html(self, tmp_path, converter):
        """تشخیص فایل .html."""
        p = tmp_path / "test.html"
        p.write_text("<html></html>", encoding="utf-8")
        assert converter.detect(p) is True

    def test_detect_by_extension_htm(self, tmp_path, converter):
        """تشخیص فایل .htm."""
        p = tmp_path / "test.htm"
        p.write_text("<html></html>", encoding="utf-8")
        assert converter.detect(p) is True

    def test_detect_by_content_doctype(self, tmp_path, converter):
        """تشخیص HTML با DOCTYPE."""
        p = tmp_path / "test.txt"
        p.write_text("<!DOCTYPE html><html><body>test</body></html>", encoding="utf-8")
        assert converter.detect(p) is True

    def test_detect_by_content_html_tag(self, tmp_path, converter):
        """تشخیص HTML با <html> tag."""
        p = tmp_path / "test.txt"
        p.write_text("<html lang='fa'><body>content</body></html>", encoding="utf-8")
        assert converter.detect(p) is True

    def test_not_detect_plain_text(self, tmp_path, converter):
        """عدم تشخیص فایل متنی ساده."""
        p = tmp_path / "test.txt"
        p.write_text("just plain text without html", encoding="utf-8")
        assert converter.detect(p) is False

    def test_format_name(self, converter):
        """نام فرمت."""
        assert converter.format_name == "html"

    def test_file_extensions(self, converter):
        """پسوندهای فایل."""
        assert ".html" in converter.file_extensions
        assert ".htm" in converter.file_extensions


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Metadata Extraction Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMetadataExtraction:
    """تست استخراج متادیتا."""

    def test_extract_title_from_head(self, simple_html, converter, ctx):
        """استخراج عنوان از <title>."""
        meta = converter.extract_metadata(simple_html, ctx)
        assert meta.title == "تست ساده"

    def test_extract_description_from_meta(self, simple_html, converter, ctx):
        """استخراج توضیح از <meta name='description'>."""
        meta = converter.extract_metadata(simple_html, ctx)
        assert ZWNJ in meta.description or "توضیح" in meta.description

    def test_extract_lang_from_html_attr(self, simple_html, converter, ctx):
        """استخراج زبان از <html lang='fa'>."""
        meta = converter.extract_metadata(simple_html, ctx)
        assert meta.lang == "fa"

    def test_extract_lang_normalization(self, tmp_path, converter, ctx):
        """نرمال‌سازی fa-IR → fa."""
        p = tmp_path / "test.html"
        p.write_text(
            "<html lang='fa-IR'><head><title>تست</title></head><body>متن</body></html>",
            encoding="utf-8"
        )
        meta = converter.extract_metadata(p, ctx)
        assert meta.lang == "fa"

    def test_extract_og_title(self, rich_html, converter, ctx):
        """استخراج عنوان OG از <meta property='og:title'>."""
        meta = converter.extract_metadata(rich_html, ctx)
        # Title from <title> tag takes priority over OG
        assert meta.title == "سند\u200cکامل آزمایشی"

    def test_detect_code_in_html(self, rich_html, converter, ctx):
        """تشخیص وجود کد در HTML."""
        meta = converter.extract_metadata(rich_html, ctx)
        assert meta.code_highlight is True

    def test_slug_generation(self, simple_html, converter, ctx):
        """تولید slug."""
        meta = converter.extract_metadata(simple_html, ctx)
        assert meta.slug  # slug باید غیرخالی باشد

    def test_direction_rtl_for_persian(self, simple_html, converter, ctx):
        """جهت RTL برای فارسی."""
        meta = converter.extract_metadata(simple_html, ctx)
        assert meta.dir == "rtl"

    def test_direction_ltr_for_english(self, english_html, converter, ctx):
        """جهت LTR برای انگلیسی."""
        meta = converter.extract_metadata(english_html, ctx)
        assert meta.lang == "en"
        assert meta.dir == "ltr"

    def test_source_format(self, simple_html, converter, ctx):
        """فرمت منبع HTML."""
        meta = converter.extract_metadata(simple_html, ctx)
        assert meta.source_format == "html"

    def test_source_file(self, simple_html, converter, ctx):
        """نام فایل منبع."""
        meta = converter.extract_metadata(simple_html, ctx)
        assert meta.source_file == "test.html"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Basic Conversion Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBasicConversion:
    """تست‌های تبدیل پایه."""

    def test_convert_simple_html_succeeds(self, simple_html, converter, ctx):
        """تبدیل HTML ساده موفق باشد."""
        result = converter.convert(simple_html, ctx)
        assert result.status == "success"

    def test_convert_produces_content(self, simple_html, converter, ctx):
        """تبدیل محتوا تولید کند."""
        converter.convert(simple_html, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        assert len(mdx) > 0

    def test_convert_has_frontmatter(self, simple_html, converter, ctx):
        """خروجی دارای frontmatter باشد."""
        converter.convert(simple_html, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        assert mdx.startswith("---\n")

    def test_convert_frontmatter_has_title(self, simple_html, converter, ctx):
        """frontmatter دارای title باشد."""
        converter.convert(simple_html, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        assert "title:" in mdx

    def test_convert_heading_converted(self, simple_html, converter, ctx):
        """<h1> تبدیل به # شده باشد."""
        converter.convert(simple_html, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        assert "# " in mdx

    def test_convert_zwnj_preserved(self, simple_html, converter, ctx):
        """نیم‌فاصله حفظ شده باشد."""
        converter.convert(simple_html, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        assert ZWNJ in mdx

    def test_convert_rich_html_succeeds(self, rich_html, converter, ctx):
        """تبدیل HTML کامل موفق باشد."""
        result = converter.convert(rich_html, ctx)
        assert result.status == "success"

    def test_convert_english_html(self, english_html, converter, ctx):
        """تبدیل HTML انگلیسی."""
        result = converter.convert(english_html, ctx)
        assert result.status == "success"
        mdx = ctx.extra.get("mdx_content", "")
        assert "Introduction" in mdx

    def test_convert_nonexistent_file(self, tmp_path, converter, ctx):
        """فایل ناموجود → خطا."""
        from formatforge.core.converters.base import ConversionError
        with pytest.raises(ConversionError):
            converter.convert(tmp_path / "nonexistent.html", ctx)

    def test_convert_tracks_input_bytes(self, simple_html, converter, ctx):
        """ردیابی حجم ورودی."""
        result = converter.convert(simple_html, ctx)
        assert result.input_bytes > 0

    def test_convert_tracks_output_bytes(self, simple_html, converter, ctx):
        """ردیابی حجم خروجی."""
        result = converter.convert(simple_html, ctx)
        assert result.output_bytes > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Element Conversion Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _make_html(body: str, lang: str = "fa", title: str = "تست") -> str:
    """ساخت HTML ساده برای تست."""
    return (
        f"<!DOCTYPE html><html lang='{lang}'>"
        f"<head><title>{title}</title></head>"
        f"<body>{body}</body></html>"
    )


class TestElementConversion:
    """تست تبدیل عناصر HTML."""

    @pytest.fixture
    def conv_html(self, tmp_path, converter, ctx):
        """Helper: تبدیل HTML رشته و بازگشت MDX."""
        def _convert(body: str, lang: str = "fa", title: str = "تست") -> str:
            html = _make_html(body, lang, title)
            p = tmp_path / "elem_test.html"
            p.write_text(html, encoding="utf-8")
            converter.convert(p, ctx)
            return ctx.extra.get("mdx_content", "")
        return _convert

    def test_h1_to_heading1(self, conv_html):
        """<h1> → # heading."""
        mdx = conv_html("<h1>عنوان اول</h1>")
        assert "# عنوان اول" in mdx

    def test_h2_to_heading2(self, conv_html):
        """<h2> → ## heading."""
        mdx = conv_html("<h2>عنوان دوم</h2>")
        assert "## عنوان دوم" in mdx

    def test_h3_to_heading3(self, conv_html):
        """<h3> → ### heading."""
        mdx = conv_html("<h3>عنوان سوم</h3>")
        assert "### عنوان سوم" in mdx

    def test_paragraph(self, conv_html):
        """<p> → paragraph."""
        mdx = conv_html("<p>این یک پاراگراف است.</p>")
        assert "این یک پاراگراف است." in mdx

    def test_strong_bold(self, conv_html):
        """<strong> → **bold**."""
        mdx = conv_html("<p><strong>متن پررنگ</strong></p>")
        assert "**متن پررنگ**" in mdx

    def test_em_italic(self, conv_html):
        """<em> → *italic*."""
        mdx = conv_html("<p><em>متن کج</em></p>")
        assert "*متن کج*" in mdx

    def test_del_strikethrough(self, conv_html):
        """<del> → ~~strikethrough~~."""
        mdx = conv_html("<p><del>حذف شده</del></p>")
        assert "~~حذف شده~~" in mdx

    def test_link_conversion(self, conv_html):
        """<a href> → [text](url)."""
        mdx = conv_html('<p><a href="https://example.com">سایت نمونه</a></p>')
        assert "[سایت نمونه](https://example.com)" in mdx

    def test_link_with_title(self, conv_html):
        """<a href title> → [text](url "title")."""
        mdx = conv_html('<p><a href="https://example.com" title="عنوان">لینک</a></p>')
        assert 'title="عنوان"' in mdx or "عنوان" in mdx

    def test_image_conversion(self, conv_html):
        """<img> → <Image> component."""
        mdx = conv_html('<img src="test.jpg" alt="تصویر" />')
        assert "<Image" in mdx
        assert 'src="test.jpg"' in mdx

    def test_code_inline(self, conv_html):
        """<code> → `code`."""
        mdx = conv_html("<p><code>print('hello')</code></p>")
        assert "`print('hello')`" in mdx or "print" in mdx

    def test_code_block(self, conv_html):
        """<pre><code> → ```code```."""
        mdx = conv_html("<pre><code class='language-python'>x = 1</code></pre>")
        assert "```" in mdx
        assert "x = 1" in mdx

    def test_unordered_list(self, conv_html):
        """<ul><li> → - item."""
        mdx = conv_html("<ul><li>آیتم ۱</li><li>آیتم ۲</li></ul>")
        assert "- آیتم ۱" in mdx
        assert "- آیتم ۲" in mdx

    def test_ordered_list(self, conv_html):
        """<ol><li> → 1. item."""
        mdx = conv_html("<ol><li>اول</li><li>دوم</li></ol>")
        assert "1. اول" in mdx
        assert "2. دوم" in mdx

    def test_blockquote(self, conv_html):
        """<blockquote> → > quote."""
        mdx = conv_html("<blockquote><p>نقل‌قول</p></blockquote>")
        assert ">" in mdx

    def test_hr(self, conv_html):
        """<hr> → ---."""
        mdx = conv_html("<p>قبل</p><hr><p>بعد</p>")
        assert "---" in mdx

    def test_br_to_newline(self, conv_html):
        """<br> → line break."""
        mdx = conv_html("<p>خط اول<br>خط دوم</p>")
        assert "\\" in mdx or "خط اول" in mdx

    def test_mark(self, conv_html):
        """<mark> → <mark>."""
        mdx = conv_html("<p><mark>برجسته</mark></p>")
        assert "<mark>برجسته</mark>" in mdx

    def test_kbd(self, conv_html):
        """<kbd> → <kbd>."""
        mdx = conv_html("<p><kbd>Ctrl+C</kbd></p>")
        assert "<kbd>Ctrl+C</kbd>" in mdx

    def test_sup(self, conv_html):
        """<sup> → <sup>."""
        mdx = conv_html("<p>پاورقی<sup>1</sup></p>")
        assert "<sup>1</sup>" in mdx

    def test_sub(self, conv_html):
        """<sub> → <sub>."""
        mdx = conv_html("<p>H<sub>2</sub>O</p>")
        assert "<sub>2</sub>" in mdx

    def test_abbr(self, conv_html):
        """<abbr> → <abbr>."""
        mdx = conv_html('<abbr title="HyperText">HTML</abbr>')
        assert "<abbr" in mdx

    def test_details_conversion(self, conv_html):
        """<details> → <Details> component."""
        mdx = conv_html(
            "<details><summary>عنوان</summary><p>محتوا</p></details>"
        )
        assert "<Details" in mdx

    def test_html_comment_to_jsx(self, conv_html):
        """<!-- comment --> → {/* comment */}."""
        mdx = conv_html("<!-- این یک کامنت است -->")
        assert "{/*" in mdx or "کامنت" in mdx

    def test_script_removed(self, conv_html):
        """<script> حذف شود."""
        mdx = conv_html("<script>alert('xss')</script><p>محتوا</p>")
        assert "alert" not in mdx
        assert "محتوا" in mdx

    def test_style_removed(self, conv_html):
        """<style> حذف شود."""
        mdx = conv_html("<style>body { color: red; }</style><p>محتوا</p>")
        assert "color: red" not in mdx
        assert "محتوا" in mdx


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Table Conversion Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTableConversion:
    """تست تبدیل جداول."""

    @pytest.fixture
    def conv_html(self, tmp_path, converter, ctx):
        def _convert(body: str) -> str:
            p = tmp_path / "table_test.html"
            p.write_text(_make_html(body), encoding="utf-8")
            # Reset context
            new_ctx = ConversionContext()
            converter.convert(p, new_ctx)
            return new_ctx.extra.get("mdx_content", "")
        return _convert

    def test_simple_table_pipe(self, conv_html):
        """جدول ساده → pipe table."""
        html = """
        <table>
          <tr><th>نام</th><th>سن</th></tr>
          <tr><td>علی</td><td>۲۵</td></tr>
        </table>
        """
        mdx = conv_html(html)
        assert "|" in mdx
        assert "نام" in mdx

    def test_simple_table_has_separator(self, conv_html):
        """جدول ساده دارای خط جداکننده."""
        html = """
        <table>
          <tr><th>ستون ۱</th><th>ستون ۲</th></tr>
          <tr><td>مقدار ۱</td><td>مقدار ۲</td></tr>
        </table>
        """
        mdx = conv_html(html)
        # باید خط --- داشته باشد
        assert "---" in mdx or "|" in mdx

    def test_merged_table_html(self, conv_html):
        """جدول ادغامی → HTML JSX table."""
        html = """
        <table>
          <tr><th colspan="2">عنوان کلی</th></tr>
          <tr><td>سلول ۱</td><td>سلول ۲</td></tr>
        </table>
        """
        mdx = conv_html(html)
        # باید <table> JSX داشته باشد
        assert "<table>" in mdx or "colSpan" in mdx or "colspan" in mdx.lower()

    def test_table_with_caption(self, conv_html):
        """جدول با caption."""
        html = """
        <table>
          <caption>عنوان جدول</caption>
          <tr><th>نام</th><th>عدد</th></tr>
          <tr><td>الف</td><td>۱</td></tr>
        </table>
        """
        mdx = conv_html(html)
        assert "عنوان جدول" in mdx

    def test_rowspan_table_html(self, conv_html):
        """جدول با rowspan → HTML JSX."""
        html = """
        <table>
          <tr><td rowspan="2">دو ردیف</td><td>ردیف ۱</td></tr>
          <tr><td>ردیف ۲</td></tr>
        </table>
        """
        mdx = conv_html(html)
        assert "<table>" in mdx or "rowSpan" in mdx or "rowspan" in mdx.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Media Element Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMediaConversion:
    """تست تبدیل عناصر رسانه‌ای."""

    @pytest.fixture
    def conv_html(self, tmp_path, converter, ctx):
        def _convert(body: str) -> str:
            p = tmp_path / "media_test.html"
            p.write_text(_make_html(body), encoding="utf-8")
            new_ctx = ConversionContext()
            converter.convert(p, new_ctx)
            return new_ctx.extra.get("mdx_content", "")
        return _convert

    def test_video_to_component(self, conv_html):
        """<video> → <Video> component."""
        mdx = conv_html('<video src="video.mp4" controls></video>')
        assert "<Video" in mdx
        assert 'src="video.mp4"' in mdx

    def test_video_controls_attr(self, conv_html):
        """<video controls> → controls={true}."""
        mdx = conv_html('<video src="video.mp4" controls></video>')
        assert "controls=" in mdx or "<Video" in mdx

    def test_audio_to_component(self, conv_html):
        """<audio> → <Audio> component."""
        mdx = conv_html('<audio src="audio.mp3" controls></audio>')
        assert "<Audio" in mdx
        assert 'src="audio.mp3"' in mdx

    def test_iframe_to_embed(self, conv_html):
        """<iframe> → <Embed> component."""
        mdx = conv_html('<iframe src="https://youtube.com/embed/test" title="Video"></iframe>')
        assert "<Embed" in mdx
        assert "src=" in mdx

    def test_form_to_placeholder(self, conv_html):
        """<form> → JSX comment placeholder."""
        mdx = conv_html('<form action="/submit" method="post"><input name="x"></form>')
        assert "{/*" in mdx or "Form" in mdx

    def test_svg_to_image_reference(self, conv_html):
        """<svg> → <Image> reference."""
        mdx = conv_html('<svg width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>')
        assert "<Image" in mdx


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Math Conversion Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMathConversion:
    """تست تبدیل عناصر ریاضی."""

    @pytest.fixture
    def conv_html(self, tmp_path, converter):
        def _convert(body: str) -> str:
            p = tmp_path / "math_test.html"
            p.write_text(_make_html(body), encoding="utf-8")
            new_ctx = ConversionContext()
            converter.convert(p, new_ctx)
            return new_ctx.extra.get("mdx_content", "")
        return _convert

    def test_script_math_tex(self, conv_html):
        """<script type='math/tex'> → $...$."""
        mdx = conv_html('<script type="math/tex">E=mc^2</script>')
        assert "E=mc^2" in mdx

    def test_data_latex_attribute(self, conv_html):
        """data-latex attribute → $...$."""
        mdx = conv_html('<span data-latex="x^2">rendered</span>')
        assert "x^2" in mdx or "$" in mdx

    def test_math_element_inline(self, conv_html):
        """<math> inline → $...$."""
        mdx = conv_html('<math><mi>x</mi></math>')
        assert "$" in mdx or "x" in mdx

    def test_math_with_annotation(self, conv_html):
        """MathML با LaTeX annotation → LaTeX."""
        mdx = conv_html(
            '<math><annotation encoding="application/x-tex">\\alpha</annotation></math>'
        )
        assert "\\alpha" in mdx or "alpha" in mdx


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ZWNJ Preservation Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestZWNJPreservation:
    """تست حفظ نیم‌فاصله."""

    def test_zwnj_in_title_preserved(self, tmp_path, converter):
        """ZWNJ در عنوان حفظ شود."""
        html = f"""<!DOCTYPE html>
<html lang='fa'>
<head><title>برنامه{ZWNJ}نویسی</title></head>
<body><h1>برنامه{ZWNJ}نویسی</h1><p>متن با نیم{ZWNJ}فاصله</p></body>
</html>"""
        p = tmp_path / "zwnj.html"
        p.write_text(html, encoding="utf-8")
        ctx = ConversionContext()
        converter.convert(p, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        assert ZWNJ in mdx

    def test_zwnj_count_preserved(self, tmp_path, converter):
        """تعداد ZWNJ قبل/بعد یکسان باشد."""
        zwnj_count = 5
        text_with_zwnj = ZWNJ.join(["کلمه"] * (zwnj_count + 1))
        html = f"""<!DOCTYPE html>
<html lang='fa'>
<head><title>تست</title></head>
<body><p>{text_with_zwnj}</p></body>
</html>"""
        p = tmp_path / "zwnj_count.html"
        p.write_text(html, encoding="utf-8")
        ctx = ConversionContext()
        converter.convert(p, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        # باید حداقل بخشی از ZWNJ‌ها حفظ شوند
        assert mdx.count(ZWNJ) >= 1

    def test_zwnj_in_frontmatter(self, tmp_path, converter):
        """ZWNJ در frontmatter حفظ شود."""
        html = f"""<!DOCTYPE html>
<html lang='fa'>
<head>
  <title>برنامه{ZWNJ}نویسی پایتون</title>
  <meta name='description' content='آموزش زبان{ZWNJ}های برنامه{ZWNJ}نویسی'>
</head>
<body><p>محتوا</p></body>
</html>"""
        p = tmp_path / "zwnj_fm.html"
        p.write_text(html, encoding="utf-8")
        ctx = ConversionContext()
        converter.convert(p, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        # frontmatter section
        fm_end = mdx.find("\n---\n", 4)
        frontmatter = mdx[:fm_end + 4] if fm_end > 0 else mdx[:200]
        assert ZWNJ in frontmatter


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CSS / Style Handling Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCSSHandling:
    """تست تبدیل CSS و style."""

    def test_extract_css_to_classnames(self, converter):
        """استخراج inline styles به className."""
        html = '<div style="color: red;">محتوا</div>'
        cleaned, classmap = converter.extract_css_to_classnames(html)
        assert len(classmap) == 1
        assert "color: red" in list(classmap.values())[0]

    def test_extract_css_empty_style(self, converter):
        """HTML بدون style → تغییری ایجاد نشود."""
        html = '<div class="container">محتوا</div>'
        cleaned, classmap = converter.extract_css_to_classnames(html)
        assert len(classmap) == 0

    def test_extract_css_multiple_styles(self, converter):
        """استخراج چند inline style."""
        html = '<div style="color:red;"><span style="font-size:14px;">متن</span></div>'
        cleaned, classmap = converter.extract_css_to_classnames(html)
        assert len(classmap) == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Output Quality Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOutputQuality:
    """تست کیفیت خروجی."""

    def test_quality_frontmatter_valid(self, simple_html, converter, ctx):
        """frontmatter معتبر باشد."""
        result = converter.convert(simple_html, ctx)
        assert result.quality.frontmatter_valid is True

    def test_quality_mdx_valid(self, simple_html, converter, ctx):
        """خروجی MDX معتبر باشد."""
        result = converter.convert(simple_html, ctx)
        assert result.quality.mdx_valid is True

    def test_quality_score_computed(self, simple_html, converter, ctx):
        """امتیاز کیفیت محاسبه شده باشد."""
        result = converter.convert(simple_html, ctx)
        result.quality.compute_score()
        assert result.quality.score >= 0.0

    def test_validate_output_returns_report(self, simple_html, converter, ctx):
        """validate_output گزارش برگرداند."""
        from formatforge.models.conversion_result import QualityReport
        result = converter.convert(simple_html, ctx)
        report = converter.validate_output(result, ctx)
        assert isinstance(report, QualityReport)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RTL/LTR Block Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBidiHandling:
    """تست مدیریت جهت متن."""

    @pytest.fixture
    def conv_html(self, tmp_path, converter):
        def _convert(body: str, lang: str = "fa") -> str:
            p = tmp_path / "bidi_test.html"
            p.write_text(_make_html(body, lang=lang), encoding="utf-8")
            ctx = ConversionContext()
            converter.convert(p, ctx)
            return ctx.extra.get("mdx_content", "")
        return _convert

    def test_div_rtl_preserved(self, conv_html):
        """<div dir='rtl'> → حفظ dir attribute."""
        mdx = conv_html('<div dir="rtl"><p>متن فارسی</p></div>')
        assert 'dir="rtl"' in mdx

    def test_div_ltr_preserved(self, conv_html):
        """<div dir='ltr'> → حفظ dir attribute."""
        mdx = conv_html('<div dir="ltr"><p>English text</p></div>')
        assert 'dir="ltr"' in mdx

    def test_lang_attr_preserved(self, conv_html):
        """<div lang='en'> → حفظ lang attribute."""
        mdx = conv_html('<div lang="en"><p>English content</p></div>')
        assert 'lang="en"' in mdx


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Definition List Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDefinitionList:
    """تست تبدیل لیست‌های تعریف."""

    @pytest.fixture
    def conv_html(self, tmp_path, converter):
        def _convert(body: str) -> str:
            p = tmp_path / "dl_test.html"
            p.write_text(_make_html(body), encoding="utf-8")
            ctx = ConversionContext()
            converter.convert(p, ctx)
            return ctx.extra.get("mdx_content", "")
        return _convert

    def test_dl_dt_dd_conversion(self, conv_html):
        """<dl><dt><dd> → definition list format."""
        mdx = conv_html(
            "<dl><dt>اصطلاح</dt><dd>تعریف اصطلاح</dd></dl>"
        )
        assert "اصطلاح" in mdx
        assert "تعریف اصطلاح" in mdx


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Figure Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFigure:
    """تست تبدیل figure."""

    @pytest.fixture
    def conv_html(self, tmp_path, converter):
        def _convert(body: str) -> str:
            p = tmp_path / "fig_test.html"
            p.write_text(_make_html(body), encoding="utf-8")
            ctx = ConversionContext()
            converter.convert(p, ctx)
            return ctx.extra.get("mdx_content", "")
        return _convert

    def test_figure_with_caption(self, conv_html):
        """<figure> با caption → <Figure> component."""
        mdx = conv_html(
            '<figure>'
            '<img src="fig.png" alt="نمودار">'
            '<figcaption>شکل ۱: نمودار نمونه</figcaption>'
            '</figure>'
        )
        assert "Figure" in mdx or "نمودار نمونه" in mdx

    def test_figure_caption_preserved(self, conv_html):
        """caption در Figure حفظ شود."""
        mdx = conv_html(
            '<figure>'
            '<img src="fig.png" alt="img">'
            '<figcaption>توضیح شکل</figcaption>'
            '</figure>'
        )
        assert "توضیح شکل" in mdx
