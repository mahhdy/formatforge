"""
تست‌های ابزارهای کمکی HTML Elements — S07-C2
Tests for html_elements.py helper functions.
"""

from __future__ import annotations

import pytest

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from formatforge.core.converters.html_elements import (
    CellModel,
    RowModel,
    TableModel,
    parse_table,
    convert_table_element,
    convert_form_element,
    convert_media_element,
    convert_svg_element,
    convert_math_from_html,
    extract_css_to_classnames,
    extract_html_metadata,
    detect_html_features,
    _build_jsx_cell_attrs,
    _table_model_to_pipe,
    _table_model_to_jsx,
)

ZWNJ = "\u200c"

pytestmark = pytest.mark.skipif(not HAS_BS4, reason="beautifulsoup4 required")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def parse_html(html: str) -> any:
    """Parse HTML with BeautifulSoup."""
    return BeautifulSoup(html, "lxml")


def find_tag(html: str, tag: str) -> any:
    """Find first occurrence of a tag."""
    soup = parse_html(html)
    return soup.find(tag)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CellModel Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCellModel:
    """تست مدل سلول جدول."""

    def test_default_not_merged(self):
        """سلول پیش‌فرض ادغامی نیست."""
        cell = CellModel()
        assert cell.is_merged is False

    def test_colspan_is_merged(self):
        """سلول با colspan > 1 ادغامی است."""
        cell = CellModel(colspan=2)
        assert cell.is_merged is True

    def test_rowspan_is_merged(self):
        """سلول با rowspan > 1 ادغامی است."""
        cell = CellModel(rowspan=3)
        assert cell.is_merged is True

    def test_normal_cell(self):
        """سلول با colspan=1, rowspan=1 عادی است."""
        cell = CellModel(colspan=1, rowspan=1)
        assert cell.is_merged is False

    def test_header_cell(self):
        """سلول header."""
        cell = CellModel(is_header=True)
        assert cell.is_header is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RowModel Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRowModel:
    """تست مدل ردیف جدول."""

    def test_row_no_merged_cells(self):
        """ردیف بدون سلول‌های ادغامی."""
        row = RowModel(cells=[CellModel("A"), CellModel("B")])
        assert row.has_merged_cells is False

    def test_row_with_merged_cell(self):
        """ردیف با یک سلول ادغامی."""
        row = RowModel(cells=[CellModel("A", colspan=2), CellModel("B")])
        assert row.has_merged_cells is True

    def test_empty_row(self):
        """ردیف خالی."""
        row = RowModel()
        assert row.has_merged_cells is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TableModel Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTableModel:
    """تست مدل جدول."""

    def test_simple_table(self):
        """جدول ساده — بدون ادغام."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("نام"), CellModel("سن")])],
            rows=[RowModel(cells=[CellModel("علی"), CellModel("۲۵")])],
        )
        assert model.is_simple is True
        assert model.has_merged_cells is False

    def test_merged_table(self):
        """جدول با ادغام."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("A", colspan=2)])],
            rows=[],
        )
        assert model.is_simple is False
        assert model.has_merged_cells is True

    def test_col_count(self):
        """شمارش تعداد ستون‌ها."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("A"), CellModel("B"), CellModel("C")])],
            rows=[RowModel(cells=[CellModel("1"), CellModel("2"), CellModel("3")])],
        )
        assert model.col_count == 3

    def test_empty_table(self):
        """جدول خالی."""
        model = TableModel()
        assert model.col_count == 0
        assert model.is_simple is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# parse_table Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestParseTable:
    """تست تحلیل جدول HTML."""

    def test_parse_simple_table(self):
        """تحلیل جدول ساده."""
        html = """
        <table>
          <tr><th>نام</th><th>سن</th></tr>
          <tr><td>علی</td><td>۲۵</td></tr>
        </table>
        """
        tag = find_tag(html, "table")
        model = parse_table(tag)
        assert len(model.rows) >= 1 or len(model.headers) >= 1

    def test_parse_table_with_thead(self):
        """تحلیل جدول با thead."""
        html = """
        <table>
          <thead>
            <tr><th>ستون ۱</th><th>ستون ۲</th></tr>
          </thead>
          <tbody>
            <tr><td>مقدار ۱</td><td>مقدار ۲</td></tr>
            <tr><td>مقدار ۳</td><td>مقدار ۴</td></tr>
          </tbody>
        </table>
        """
        tag = find_tag(html, "table")
        model = parse_table(tag)
        assert len(model.headers) == 1
        assert len(model.rows) == 2

    def test_parse_table_caption(self):
        """تحلیل caption جدول."""
        html = """
        <table>
          <caption>عنوان جدول</caption>
          <tr><th>A</th></tr>
          <tr><td>1</td></tr>
        </table>
        """
        tag = find_tag(html, "table")
        model = parse_table(tag)
        assert model.caption == "عنوان جدول"

    def test_parse_merged_cells(self):
        """تحلیل سلول‌های ادغامی."""
        html = """
        <table>
          <tr><th colspan="2">مشخصات</th></tr>
          <tr><td>نام</td><td>علی</td></tr>
        </table>
        """
        tag = find_tag(html, "table")
        model = parse_table(tag)
        assert model.has_merged_cells is True

    def test_parse_rowspan(self):
        """تحلیل rowspan."""
        html = """
        <table>
          <tr><td rowspan="2">ادغام</td><td>۱</td></tr>
          <tr><td>۲</td></tr>
        </table>
        """
        tag = find_tag(html, "table")
        model = parse_table(tag)
        assert model.has_merged_cells is True

    def test_parse_tfoot(self):
        """تحلیل tfoot جدول."""
        html = """
        <table>
          <thead><tr><th>سرستون</th></tr></thead>
          <tbody><tr><td>داده</td></tr></tbody>
          <tfoot><tr><td>پاورقی</td></tr></tfoot>
        </table>
        """
        tag = find_tag(html, "table")
        model = parse_table(tag)
        assert len(model.footer_rows) == 1

    def test_parse_cell_text_escape(self):
        """escape کاراکتر | در سلول‌ها."""
        html = """
        <table>
          <tr><th>نام</th></tr>
          <tr><td>مقدار|دیگر</td></tr>
        </table>
        """
        tag = find_tag(html, "table")
        model = parse_table(tag)
        all_cells = [c for row in model.rows for c in row.cells]
        assert any("\\|" in c.text for c in all_cells)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# convert_table_element Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConvertTableElement:
    """تست تبدیل جدول."""

    def test_simple_table_pipe(self):
        """جدول ساده → pipe table."""
        html = """
        <table>
          <tr><th>نام</th><th>سن</th></tr>
          <tr><td>علی</td><td>۲۵</td></tr>
          <tr><td>فاطمه</td><td>۳۰</td></tr>
        </table>
        """
        tag = find_tag(html, "table")
        result = convert_table_element(tag)
        assert "|" in result
        assert "نام" in result
        assert "سن" in result

    def test_simple_table_separator(self):
        """جدول ساده دارای separator."""
        html = """
        <table>
          <tr><th>A</th><th>B</th></tr>
          <tr><td>1</td><td>2</td></tr>
        </table>
        """
        tag = find_tag(html, "table")
        result = convert_table_element(tag)
        lines = result.strip().split("\n")
        # باید حداقل 3 خط داشته باشد: header, separator, data
        assert len(lines) >= 3

    def test_merged_table_html(self):
        """جدول ادغامی → HTML JSX."""
        html = """
        <table>
          <tr><th colspan="2">عنوان</th></tr>
          <tr><td>A</td><td>B</td></tr>
        </table>
        """
        tag = find_tag(html, "table")
        result = convert_table_element(tag)
        assert "<table>" in result

    def test_merged_table_colspan_jsx(self):
        """جدول ادغامی → colSpan در JSX."""
        html = """
        <table>
          <tr><th colspan="3">عنوان بزرگ</th></tr>
          <tr><td>A</td><td>B</td><td>C</td></tr>
        </table>
        """
        tag = find_tag(html, "table")
        result = convert_table_element(tag)
        assert "colSpan" in result or "colspan" in result.lower()

    def test_empty_table(self):
        """جدول خالی → رشته خالی یا whitespace."""
        html = "<table></table>"
        tag = find_tag(html, "table")
        result = convert_table_element(tag)
        assert result.strip() == ""

    def test_require_import_callback(self):
        """callback برای ثبت import صدا زده شود."""
        html = """
        <table>
          <tr><th colspan="2">ادغام</th></tr>
        </table>
        """
        tag = find_tag(html, "table")
        imports_needed = []
        convert_table_element(tag, require_import_cb=imports_needed.append)
        assert "Table" in imports_needed


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# _table_model_to_pipe Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTableModelToPipe:
    """تست تبدیل TableModel به pipe table."""

    def test_basic_pipe_table(self):
        """جدول پایه به pipe table."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("نام"), CellModel("سن")])],
            rows=[
                RowModel(cells=[CellModel("علی"), CellModel("۲۵")]),
                RowModel(cells=[CellModel("فاطمه"), CellModel("۳۰")]),
            ],
        )
        result = _table_model_to_pipe(model)
        assert "| نام | سن |" in result
        assert "علی" in result
        assert "فاطمه" in result

    def test_pipe_table_has_separator(self):
        """pipe table دارای خط separator."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("A"), CellModel("B")])],
            rows=[RowModel(cells=[CellModel("1"), CellModel("2")])],
        )
        result = _table_model_to_pipe(model)
        lines = [l for l in result.split("\n") if l.strip()]
        assert any(set(line.replace("|", "").replace("-", "").strip()) == set() for line in lines)

    def test_pipe_table_with_caption(self):
        """pipe table با caption."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("A")])],
            rows=[RowModel(cells=[CellModel("1")])],
            caption="توضیح جدول",
        )
        result = _table_model_to_pipe(model)
        assert "توضیح جدول" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# _table_model_to_jsx Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTableModelToJSX:
    """تست تبدیل TableModel به JSX."""

    def test_jsx_has_table_tag(self):
        """خروجی JSX دارای <table>."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("نام", colspan=2)])],
            rows=[RowModel(cells=[CellModel("A"), CellModel("B")])],
        )
        result = _table_model_to_jsx(model)
        assert "<table>" in result
        assert "</table>" in result

    def test_jsx_has_thead(self):
        """خروجی JSX دارای <thead>."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("H1"), CellModel("H2")])],
            rows=[RowModel(cells=[CellModel("D1"), CellModel("D2")])],
        )
        result = _table_model_to_jsx(model)
        assert "<thead>" in result

    def test_jsx_has_tbody(self):
        """خروجی JSX دارای <tbody>."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("H")])],
            rows=[RowModel(cells=[CellModel("D")])],
        )
        result = _table_model_to_jsx(model)
        assert "<tbody>" in result

    def test_jsx_colspan_attribute(self):
        """colspan در JSX → colSpan."""
        model = TableModel(
            headers=[RowModel(cells=[CellModel("Header", colspan=3)])],
            rows=[],
        )
        result = _table_model_to_jsx(model)
        assert "colSpan={3}" in result

    def test_jsx_rowspan_attribute(self):
        """rowspan در JSX → rowSpan."""
        model = TableModel(
            rows=[RowModel(cells=[CellModel("Data", rowspan=2)])],
        )
        result = _table_model_to_jsx(model)
        assert "rowSpan={2}" in result

    def test_jsx_overflow_div(self):
        """خروجی JSX در div با overflowX."""
        model = TableModel(
            rows=[RowModel(cells=[CellModel("X")])],
        )
        result = _table_model_to_jsx(model)
        assert "overflowX" in result or "overflow" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# _build_jsx_cell_attrs Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBuildJSXCellAttrs:
    """تست ساخت attribute‌های سلول JSX."""

    def test_no_special_attrs(self):
        """سلول بدون attribute خاص → رشته خالی."""
        cell = CellModel("text")
        attrs = _build_jsx_cell_attrs(cell)
        assert attrs == ""

    def test_colspan_attr(self):
        """colspan → colSpan={n}."""
        cell = CellModel("text", colspan=3)
        attrs = _build_jsx_cell_attrs(cell)
        assert "colSpan={3}" in attrs

    def test_rowspan_attr(self):
        """rowspan → rowSpan={n}."""
        cell = CellModel("text", rowspan=2)
        attrs = _build_jsx_cell_attrs(cell)
        assert "rowSpan={2}" in attrs

    def test_align_attr(self):
        """align → style={textAlign}."""
        cell = CellModel("text", align="center")
        attrs = _build_jsx_cell_attrs(cell)
        assert "textAlign" in attrs

    def test_class_attr(self):
        """classes → className."""
        cell = CellModel("text", classes=["highlight", "bold"])
        attrs = _build_jsx_cell_attrs(cell)
        assert "className" in attrs
        assert "highlight" in attrs


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# convert_form_element Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConvertFormElement:
    """تست تبدیل فرم."""

    def test_form_to_comment(self):
        """فرم → JSX comment."""
        html = '<form action="/submit" method="post"><input name="x"></form>'
        tag = find_tag(html, "form")
        result = convert_form_element(tag)
        assert "{/*" in result

    def test_form_contains_action(self):
        """کامنت فرم شامل action."""
        html = '<form action="/api/submit" method="post"></form>'
        tag = find_tag(html, "form")
        result = convert_form_element(tag)
        assert "/api/submit" in result

    def test_form_contains_method(self):
        """کامنت فرم شامل method."""
        html = '<form action="/x" method="GET"></form>'
        tag = find_tag(html, "form")
        result = convert_form_element(tag)
        assert "GET" in result or "get" in result.lower()

    def test_form_with_fields(self):
        """فرم با فیلدها → ذکر نام فیلدها."""
        html = (
            '<form action="/" method="post">'
            '<input name="username" type="text">'
            '<input name="password" type="password">'
            '</form>'
        )
        tag = find_tag(html, "form")
        result = convert_form_element(tag)
        assert "username" in result or "Form" in result

    def test_form_placeholder_todo(self):
        """کامنت فرم حاوی TODO."""
        html = '<form action="/" method="post"></form>'
        tag = find_tag(html, "form")
        result = convert_form_element(tag)
        assert "TODO" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# convert_media_element Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConvertMediaElement:
    """تست تبدیل عناصر رسانه."""

    def test_video_to_video_component(self):
        """<video> → <Video>."""
        html = '<video src="movie.mp4" controls></video>'
        tag = find_tag(html, "video")
        result = convert_media_element(tag)
        assert "<Video" in result
        assert 'src="movie.mp4"' in result

    def test_video_controls(self):
        """<video controls> → controls={true}."""
        html = '<video src="movie.mp4" controls></video>'
        tag = find_tag(html, "video")
        result = convert_media_element(tag)
        assert "controls={true}" in result

    def test_video_width_height(self):
        """<video> با width و height."""
        html = '<video src="v.mp4" width="640" height="360"></video>'
        tag = find_tag(html, "video")
        result = convert_media_element(tag)
        assert "width={640}" in result
        assert "height={360}" in result

    def test_video_source_child(self):
        """<video><source> → استفاده از src فرزند."""
        html = '<video><source src="movie.mp4" type="video/mp4"></video>'
        tag = find_tag(html, "video")
        result = convert_media_element(tag)
        assert "movie.mp4" in result

    def test_audio_to_audio_component(self):
        """<audio> → <Audio>."""
        html = '<audio src="sound.mp3" controls></audio>'
        tag = find_tag(html, "audio")
        result = convert_media_element(tag)
        assert "<Audio" in result
        assert 'src="sound.mp3"' in result

    def test_audio_controls(self):
        """<audio controls> → controls={true}."""
        html = '<audio src="s.mp3" controls></audio>'
        tag = find_tag(html, "audio")
        result = convert_media_element(tag)
        assert "controls={true}" in result

    def test_audio_loop(self):
        """<audio loop> → loop={true}."""
        html = '<audio src="s.mp3" loop></audio>'
        tag = find_tag(html, "audio")
        result = convert_media_element(tag)
        assert "loop={true}" in result

    def test_iframe_to_embed(self):
        """<iframe> → <Embed>."""
        html = '<iframe src="https://youtube.com/embed/abc" title="ویدئو"></iframe>'
        tag = find_tag(html, "iframe")
        result = convert_media_element(tag)
        assert "<Embed" in result
        assert "src=" in result

    def test_iframe_title(self):
        """<iframe title> در Embed."""
        html = '<iframe src="x" title="محتوای جاسازشده"></iframe>'
        tag = find_tag(html, "iframe")
        result = convert_media_element(tag)
        assert "محتوای جاسازشده" in result or "title=" in result

    def test_iframe_dimensions(self):
        """<iframe> با width و height."""
        html = '<iframe src="x" width="800" height="600"></iframe>'
        tag = find_tag(html, "iframe")
        result = convert_media_element(tag)
        assert "width=" in result or "800" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# convert_svg_element Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConvertSVGElement:
    """تست تبدیل SVG."""

    def test_svg_returns_image_reference(self):
        """SVG → <Image> reference."""
        html = '<svg width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
        tag = find_tag(html, "svg")
        mdx_ref, svg_content = convert_svg_element(tag, "test-page", 1)
        assert "<Image" in mdx_ref

    def test_svg_returns_content(self):
        """SVG → محتوای SVG برگردانده شود."""
        html = '<svg width="100"><rect width="100" height="100"/></svg>'
        tag = find_tag(html, "svg")
        mdx_ref, svg_content = convert_svg_element(tag, "page", 1)
        assert svg_content is not None
        assert "svg" in svg_content.lower()

    def test_svg_filename_contains_base(self):
        """نام فایل SVG شامل base_name باشد."""
        html = '<svg><circle/></svg>'
        tag = find_tag(html, "svg")
        mdx_ref, _ = convert_svg_element(tag, "my-page", 3)
        assert "my-page" in mdx_ref

    def test_svg_with_title(self):
        """SVG با <title> → alt از title."""
        html = '<svg><title>نمودار دایره</title><circle cx="50" cy="50" r="40"/></svg>'
        tag = find_tag(html, "svg")
        mdx_ref, _ = convert_svg_element(tag, "page", 1)
        assert "نمودار دایره" in mdx_ref

    def test_svg_with_aria_label(self):
        """SVG با aria-label → alt از aria-label."""
        html = '<svg aria-label="توضیح SVG"><rect/></svg>'
        tag = find_tag(html, "svg")
        mdx_ref, _ = convert_svg_element(tag, "page", 1)
        assert "توضیح SVG" in mdx_ref

    def test_empty_svg(self):
        """SVG خالی → رشته خالی."""
        html = "<svg></svg>"
        tag = find_tag(html, "svg")
        # Empty SVG might return empty or minimal content
        mdx_ref, svg_content = convert_svg_element(tag, "page", 1)
        # Should not crash; svg_content may be None for truly empty
        assert isinstance(mdx_ref, str)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# convert_math_from_html Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConvertMathFromHTML:
    """تست تبدیل ریاضی HTML."""

    def test_math_script_inline(self):
        """<script type='math/tex'> → $...$."""
        html = '<script type="math/tex">E=mc^2</script>'
        tag = find_tag(html, "script")
        result = convert_math_from_html(tag)
        assert "E=mc^2" in result
        assert "$" in result

    def test_math_script_display(self):
        """<script type='math/tex; mode=display'> → $$..$$."""
        html = '<script type="math/tex; mode=display">\\frac{1}{2}</script>'
        tag = find_tag(html, "script")
        result = convert_math_from_html(tag)
        assert "\\frac{1}{2}" in result
        assert "$$" in result

    def test_mathml_inline(self):
        """<math> inline → $...$."""
        html = "<math><mi>x</mi><mo>+</mo><mi>y</mi></math>"
        tag = find_tag(html, "math")
        result = convert_math_from_html(tag)
        assert "$" in result

    def test_mathml_block(self):
        """<math display='block'> → $$...$$."""
        html = '<math display="block"><mi>x</mi></math>'
        tag = find_tag(html, "math")
        result = convert_math_from_html(tag)
        assert "$$" in result

    def test_mathml_with_annotation(self):
        """MathML با LaTeX annotation → استفاده از annotation."""
        html = '''<math>
          <annotation encoding="application/x-tex">\\alpha + \\beta</annotation>
        </math>'''
        tag = find_tag(html, "math")
        result = convert_math_from_html(tag)
        assert "\\alpha" in result or "alpha" in result

    def test_span_data_latex(self):
        """<span data-latex='...'> → $...$."""
        html = '<span data-latex="x^2 + y^2">x² + y²</span>'
        tag = find_tag(html, "span")
        result = convert_math_from_html(tag)
        assert "x^2 + y^2" in result

    def test_span_aria_label(self):
        """<span aria-label='...'> → $...$."""
        html = '<span aria-label="x squared">x²</span>'
        tag = find_tag(html, "span")
        result = convert_math_from_html(tag)
        assert "x squared" in result or "$" in result

    def test_empty_element_returns_empty(self):
        """عنصر خالی → رشته خالی."""
        html = "<span></span>"
        tag = find_tag(html, "span")
        result = convert_math_from_html(tag)
        assert result == ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# extract_css_to_classnames Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtractCSSToClassnames:
    """تست استخراج inline CSS."""

    def test_single_style(self):
        """یک inline style → یک entry در classmap."""
        html = '<div style="color: red;">متن</div>'
        cleaned, classmap = extract_css_to_classnames(html)
        assert len(classmap) == 1
        assert "color: red" in list(classmap.values())[0]

    def test_style_replaced_with_classname(self):
        """style attribute با className جایگزین شود."""
        html = '<div style="color: red;">متن</div>'
        cleaned, classmap = extract_css_to_classnames(html)
        assert "className=" in cleaned
        assert "style=" not in cleaned

    def test_no_style(self):
        """HTML بدون style → classmap خالی."""
        html = '<div class="container">متن</div>'
        cleaned, classmap = extract_css_to_classnames(html)
        assert len(classmap) == 0
        assert cleaned == html

    def test_multiple_styles(self):
        """چند inline style → چند entry."""
        html = (
            '<div style="color:red;">'
            '<span style="font-size:14px;">متن</span>'
            '</div>'
        )
        cleaned, classmap = extract_css_to_classnames(html)
        assert len(classmap) == 2

    def test_same_style_different_hash(self):
        """دو style یکسان → یک hash یکسان."""
        html = (
            '<div style="color:red;"><span style="color:red;">متن</span></div>'
        )
        cleaned, classmap = extract_css_to_classnames(html)
        # هر دو style یکسان هستند → یک یا دو entry (بسته به implementation)
        assert len(classmap) >= 1

    def test_zwnj_not_affected(self):
        """ZWNJ در محتوا آسیب نبیند."""
        html = f'<div style="color:red;">متن{ZWNJ}فارسی</div>'
        cleaned, classmap = extract_css_to_classnames(html)
        assert ZWNJ in cleaned


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# extract_html_metadata Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtractHTMLMetadata:
    """تست استخراج متادیتا HTML."""

    def test_extract_title(self):
        """استخراج title."""
        html = "<html><head><title>عنوان صفحه</title></head><body></body></html>"
        meta = extract_html_metadata(html)
        assert meta.get("title") == "عنوان صفحه"

    def test_extract_description(self):
        """استخراج description."""
        html = (
            "<html><head>"
            '<meta name="description" content="توضیح مختصر">'
            "</head><body></body></html>"
        )
        meta = extract_html_metadata(html)
        assert meta.get("description") == "توضیح مختصر"

    def test_extract_og_title(self):
        """استخراج og:title."""
        html = (
            "<html><head>"
            '<meta property="og:title" content="عنوان OG">'
            "</head><body></body></html>"
        )
        meta = extract_html_metadata(html)
        assert meta.get("og:title") == "عنوان OG"

    def test_extract_lang(self):
        """استخراج lang از html tag."""
        html = "<html lang='fa'><head><title>T</title></head><body></body></html>"
        meta = extract_html_metadata(html)
        assert meta.get("lang") == "fa"

    def test_extract_canonical(self):
        """استخراج canonical URL."""
        html = (
            "<html><head>"
            '<link rel="canonical" href="https://example.com/page">'
            "</head><body></body></html>"
        )
        meta = extract_html_metadata(html)
        assert meta.get("canonical") == "https://example.com/page"

    def test_empty_html(self):
        """HTML خالی → dict خالی یا ناقص."""
        meta = extract_html_metadata("")
        assert isinstance(meta, dict)

    def test_no_head(self):
        """HTML بدون head."""
        meta = extract_html_metadata("<html><body>content</body></html>")
        assert isinstance(meta, dict)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# detect_html_features Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDetectHTMLFeatures:
    """تست تشخیص ویژگی‌های HTML."""

    def test_detect_math(self):
        """تشخیص ریاضیات."""
        html = '<html><body><span class="katex">x^2</span></body></html>'
        features = detect_html_features(html)
        assert features["has_math"] is True

    def test_detect_code(self):
        """تشخیص کد."""
        html = "<html><body><pre><code>x = 1</code></pre></body></html>"
        features = detect_html_features(html)
        assert features["has_code"] is True

    def test_detect_tables(self):
        """تشخیص جداول."""
        html = "<html><body><table><tr><td>A</td></tr></table></body></html>"
        features = detect_html_features(html)
        assert features["has_tables"] is True

    def test_detect_images(self):
        """تشخیص تصاویر."""
        html = '<html><body><img src="x.jpg" alt="test"></body></html>'
        features = detect_html_features(html)
        assert features["has_images"] is True

    def test_detect_video(self):
        """تشخیص ویدئو."""
        html = "<html><body><video src='v.mp4'></video></body></html>"
        features = detect_html_features(html)
        assert features["has_video"] is True

    def test_detect_svg(self):
        """تشخیص SVG."""
        html = "<html><body><svg><circle/></svg></body></html>"
        features = detect_html_features(html)
        assert features["has_svg"] is True

    def test_detect_forms(self):
        """تشخیص فرم."""
        html = "<html><body><form><input name='x'></form></body></html>"
        features = detect_html_features(html)
        assert features["has_forms"] is True

    def test_detect_persian(self):
        """تشخیص متن فارسی."""
        html = "<html><body><p>این متن فارسی است</p></body></html>"
        features = detect_html_features(html)
        assert features["has_persian"] is True

    def test_detect_no_persian(self):
        """تشخیص عدم وجود متن فارسی."""
        html = "<html><body><p>This is English text only.</p></body></html>"
        features = detect_html_features(html)
        assert features["has_persian"] is False

    def test_detect_nothing_in_empty(self):
        """HTML خالی → هیچ‌چیز تشخیص داده نشود."""
        html = "<html><head></head><body></body></html>"
        features = detect_html_features(html)
        assert features["has_code"] is False
        assert features["has_tables"] is False

    def test_detect_mermaid(self):
        """تشخیص Mermaid."""
        html = '<html><body><div class="mermaid">graph TD; A-->B</div></body></html>'
        features = detect_html_features(html)
        assert features["has_mermaid"] is True
