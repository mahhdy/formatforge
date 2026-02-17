# -*- coding: utf-8-sig -*-
r"""Tests for table_processor module.

Test suite for FormatForge table processing.
"""
import pytest
from formatforge.core.processors.table_models import (
    TableModel,
    TableCell,
    CellStyle,
)
from formatforge.core.processors.table_processor import TableProcessor


ZWNJ = "\u200c"


@pytest.fixture
def processor() -> TableProcessor:
    r"""Create a default TableProcessor instance."""
    return TableProcessor()


@pytest.fixture
def processor_caption_above() -> TableProcessor:
    r"""Create a TableProcessor with caption above."""
    return TableProcessor(config={"caption_position": "above"})


# ============================================================
# Test 1: Simple table
# ============================================================


class TestSimpleTable:
    r"""Tests for simple LaTeX tables without merges."""

    def test_parse_simple_tabular(self, processor: TableProcessor) -> None:
        r"""Test parsing a basic tabular environment."""
        latex = (
            "\\begin{tabular}{|c|c|c|}"
            + "\\n"
            + "A & B & C \\\\"
            + "\\n"
            + "1 & 2 & 3 \\\\"
            + "\\n"
            + "\\end{tabular}"
        )
        model = processor.parse_latex_table(latex)
        assert len(model.headers) == 1
        assert len(model.rows) == 1
        assert model.headers[0][0].content == "A"
        assert model.rows[0][1].content == "2"
        assert model.is_simple is True

    def test_render_simple_markdown(self, processor: TableProcessor) -> None:
        r"""Test rendering simple table as Markdown pipe table."""
        model = TableModel(
            headers=[[
                TableCell(content="Name", is_header=True),
                TableCell(content="Value", is_header=True),
            ]],
            rows=[[
                TableCell(content="x"),
                TableCell(content="10"),
            ]],
            col_alignments=["left", "center"],
        )
        result = processor.render_markdown_table(model)
        assert "| Name | Value |" in result
        assert "| x | 10 |" in result
        assert "---" in result

    def test_simple_table_e2e(self, processor: TableProcessor) -> None:
        r"""End-to-end: simple LaTeX to Markdown pipe table."""
        latex = (
            "\\begin{tabular}{lcc}"
            + "\\n"
            + "Name & Score & Grade \\\\"
            + "\\n"
            + "Alice & 95 & A \\\\"
            + "\\n"
            + "Bob & 82 & B \\\\"
            + "\\n"
            + "\\end{tabular}"
        )
        result = processor.process(latex, source_format="latex")
        assert "|" in result
        assert "Alice" in result
        assert "<table" not in result  # should be Markdown, not HTML


# ============================================================
# Test 2: Multirow / Multicolumn
# ============================================================


class TestMergedTable:
    r"""Tests for tables with multirow and multicolumn."""

    def test_parse_multicolumn(self, processor: TableProcessor) -> None:
        r"""Test parsing multicolumn cells."""
        latex = (
            "\\begin{tabular}{|c|c|c|}"
            + "\\n"
            + "\\multicolumn{2}{|c|}{Header} & C \\\\"
            + "\\n"
            + "1 & 2 & 3 \\\\"
            + "\\n"
            + "\\end{tabular}"
        )
        model = processor.parse_latex_table(latex)
        assert model.has_merged_cells is True
        assert model.headers[0][0].colspan == 2
        assert model.headers[0][0].content == "Header"
        assert model.is_simple is False

    def test_parse_multirow(self, processor: TableProcessor) -> None:
        r"""Test parsing multirow cells."""
        latex = (
            "\\begin{tabular}{|c|c|}"
            + "\\n"
            + "A & B \\\\"
            + "\\n"
            + "\\multirow{2}{*}{X} & 1 \\\\"
            + "\\n"
            + " & 2 \\\\"
            + "\\n"
            + "\\end{tabular}"
        )
        model = processor.parse_latex_table(latex)
        assert model.has_merged_cells is True
        assert model.rows[0][0].rowspan == 2

    def test_merged_renders_html(self, processor: TableProcessor) -> None:
        r"""Test that merged tables render as HTML, not Markdown."""
        model = TableModel(
            headers=[[
                TableCell(content="A", is_header=True, colspan=2),
                TableCell(content="B", is_header=True),
            ]],
            rows=[[
                TableCell(content="1"),
                TableCell(content="2"),
                TableCell(content="3"),
            ]],
            has_merged_cells=True,
        )
        result = processor.render_html_table(model)
        assert "<table" in result
        assert "colspan" in result

    def test_merged_e2e_uses_html(self, processor: TableProcessor) -> None:
        r"""End-to-end: merged table should produce HTML output."""
        model = TableModel(
            headers=[[
                TableCell(content="Merged", is_header=True, colspan=3),
            ]],
            rows=[[
                TableCell(content="a"),
                TableCell(content="b"),
                TableCell(content="c"),
            ]],
            has_merged_cells=True,
        )
        assert model.is_simple is False


# ============================================================
# Test 3: Colored table
# ============================================================


class TestColoredTable:
    r"""Tests for tables with colors."""

    def test_parse_rowcolors(self, processor: TableProcessor) -> None:
        r"""Test detection of rowcolors command."""
        latex = (
            "\\rowcolors{2}{gray!25}{white}"
            + "\\n"
            + "\\begin{tabular}{|c|c|}"
            + "\\n"
            + "A & B \\\\"
            + "\\n"
            + "1 & 2 \\\\"
            + "\\n"
            + "\\end{tabular}"
        )
        model = processor.parse_latex_table(latex)
        assert model.has_colors is True
        assert model.is_simple is False

    def test_parse_cellcolor(self, processor: TableProcessor) -> None:
        r"""Test detection of cellcolor in a cell."""
        latex = (
            "\\begin{tabular}{|c|c|}"
            + "\\n"
            + "A & B \\\\"
            + "\\n"
            + "\\cellcolor{red}1 & 2 \\\\"
            + "\\n"
            + "\\end{tabular}"
        )
        model = processor.parse_latex_table(latex)
        assert model.rows[0][0].style is not None
        assert model.rows[0][0].style.background_color == "red"

    def test_colored_not_simple(self, processor: TableProcessor) -> None:
        r"""Test that colored tables are not considered simple."""
        model = TableModel(
            headers=[[TableCell(content="A", is_header=True)]],
            rows=[[TableCell(content="1")]],
            has_colors=True,
        )
        assert model.is_simple is False


# ============================================================
# Test 4: Table with formulas
# ============================================================


class TestFormulaTable:
    r"""Tests for tables containing math formulas."""

    def test_inline_math_preserved(self, processor: TableProcessor) -> None:
        r"""Test that inline math is preserved in cells."""
        D = chr(36)
        latex = (
            "\\begin{tabular}{|c|c|}"
            + "\\n"
            + "Symbol & Value \\\\"
            + "\\n"
            + D + "x^2" + D + " & 42 \\\\"
            + "\\n"
            + "\\end{tabular}"
        )
        model = processor.parse_latex_table(latex)
        cell_content = model.rows[0][0].content
        assert D in cell_content
        assert "x^2" in cell_content

    def test_formula_in_markdown_output(self, processor: TableProcessor) -> None:
        r"""Test that formulas pass through to Markdown output."""
        D = chr(36)
        formula = D + "x^2" + D
        model = TableModel(
            headers=[[
                TableCell(content="Symbol", is_header=True),
                TableCell(content="Value", is_header=True),
            ]],
            rows=[[
                TableCell(content=formula),
                TableCell(content="42"),
            ]],
        )
        result = processor.render_markdown_table(model)
        assert D in result
        assert "x^2" in result

    def test_formula_in_html_output(self, processor: TableProcessor) -> None:
        r"""Test that formulas pass through to HTML output."""
        D = chr(36)
        formula = D + "alpha" + D
        model = TableModel(
            headers=[[
                TableCell(content="Sym", is_header=True),
            ]],
            rows=[[
                TableCell(content=formula),
            ]],
            has_merged_cells=True,  # force HTML
        )
        result = processor.render_html_table(model)
        assert D in result
        assert "alpha" in result


# ============================================================
# Test 5: Persian table
# ============================================================


class TestPersianTable:
    r"""Tests for Persian RTL tables."""

    def test_rtl_in_html(self, processor: TableProcessor) -> None:
        r"""Test that HTML output includes RTL direction."""
        model = TableModel(
            headers=[[
                TableCell(content='نام', is_header=True),
                TableCell(content='مقدار', is_header=True),
            ]],
            rows=[[
                TableCell(content='الف'),
                TableCell(content='۱'),
            ]],
            is_rtl=True,
            has_merged_cells=True,  # force HTML rendering
        )
        result = processor.render_html_table(model)
        assert "rtl" in result
        assert "dir" in result

    def test_persian_zwnj_preserved(self, processor: TableProcessor) -> None:
        r"""Test that ZWNJ in Persian text is preserved."""
        word = 'کتاب' + ZWNJ + 'خانه'
        model = TableModel(
            headers=[[
                TableCell(content=word, is_header=True),
            ]],
            rows=[],
        )
        result = processor.render_markdown_table(model)
        assert ZWNJ in result
        assert "کتاب" in result
        assert "خانه" in result

    def test_persian_caption_below(self, processor: TableProcessor) -> None:
        r"""Test Persian caption below table (default)."""
        model = TableModel(
            headers=[[
                TableCell(content='ستون', is_header=True),
            ]],
            rows=[[
                TableCell(content='داده'),
            ]],
            caption='جدول آزمایشی',
            caption_position="below",
        )
        result = processor.render_markdown_table(model)
        assert "جدول آزمایشی" in result

    def test_persian_caption_above(self, processor_caption_above: TableProcessor) -> None:
        r"""Test Persian caption above table."""
        model = TableModel(
            headers=[[
                TableCell(content='ستون', is_header=True),
            ]],
            rows=[[
                TableCell(content='داده'),
            ]],
            caption='عنوان جدول',
            caption_position="above",
        )
        result = processor_caption_above.render_markdown_table(model)
        result_lines = result.split("\\n")
        # Caption should appear before the header row
        caption_idx = None
        header_idx = None
        for i, line in enumerate(result_lines):
            if "عنوان جدول" in line:
                caption_idx = i
            if "|" in line and "---" not in line and caption_idx is None:
                header_idx = i
        assert caption_idx is not None

    def test_not_rtl_when_disabled(self) -> None:
        r"""Test that RTL can be disabled."""
        proc = TableProcessor(config={"default_rtl": False})
        model = TableModel(
            headers=[[TableCell(content='Test', is_header=True)]],
            rows=[[TableCell(content='1')]],
            is_rtl=False,
            has_merged_cells=True,
        )
        result = proc.render_html_table(model)
        assert "rtl" not in result


# ============================================================
# Test 6: Special table types (longtable, landscape, tabularx)
# ============================================================


class TestSpecialTables:
    r"""Tests for longtable, landscape, and full-width tables."""

    def test_longtable_wrapper(self, processor: TableProcessor) -> None:
        r"""Test that longtable gets overflow wrapper."""
        model = TableModel(
            headers=[[TableCell(content='H', is_header=True)]],
            rows=[[TableCell(content='D')]],
            is_long=True,
            has_merged_cells=True,  # force HTML
        )
        result = processor.render_html_table(model)
        assert "overflow-x:auto" in result

    def test_landscape_wrapper(self, processor: TableProcessor) -> None:
        r"""Test that landscape table gets className wrapper."""
        model = TableModel(
            headers=[[TableCell(content='H', is_header=True)]],
            rows=[[TableCell(content='D')]],
            is_landscape=True,
            has_merged_cells=True,
        )
        result = processor.render_html_table(model)
        assert "landscape-table" in result

    def test_full_width(self, processor: TableProcessor) -> None:
        r"""Test that tabularx gets width:100%."""
        model = TableModel(
            headers=[[TableCell(content='H', is_header=True)]],
            rows=[[TableCell(content='D')]],
            is_full_width=True,
            has_merged_cells=True,
        )
        result = processor.render_html_table(model)
        assert "100%" in result

    def test_table_with_label(self, processor: TableProcessor) -> None:
        r"""Test that label becomes id attribute."""
        model = TableModel(
            headers=[[TableCell(content='H', is_header=True)]],
            rows=[[TableCell(content='D')]],
            label="tab:results",
            has_merged_cells=True,
        )
        result = processor.render_html_table(model)
        assert "tab:results" in result
        assert "id=" in result


# ============================================================
# Test 7: HTML table parsing
# ============================================================


class TestHTMLTableParsing:
    r"""Tests for parsing HTML tables."""

    def test_simple_html_table(self, processor: TableProcessor) -> None:
        r"""Test parsing a simple HTML table."""
        html = (
            "<table>"
            + "<tr><th>A</th><th>B</th></tr>"
            + "<tr><td>1</td><td>2</td></tr>"
            + "</table>"
        )
        model = processor.parse_html_table(html)
        assert len(model.headers) == 1
        assert len(model.rows) == 1
        assert model.headers[0][0].content == "A"
        assert model.rows[0][1].content == "2"

    def test_html_with_colspan(self, processor: TableProcessor) -> None:
        r"""Test parsing HTML table with colspan."""
        html = (
            "<table>"
            + '<tr><th colspan="2">Merged</th></tr>'
            + "<tr><td>1</td><td>2</td></tr>"
            + "</table>"
        )
        model = processor.parse_html_table(html)
        assert model.has_merged_cells is True
        assert model.headers[0][0].colspan == 2

    def test_html_empty_table(self, processor: TableProcessor) -> None:
        r"""Test parsing when no table found."""
        model = processor.parse_html_table("<p>no table</p>")
        assert len(model.headers) == 0
        assert len(model.rows) == 0


# ============================================================
# Test 8: TableModel properties
# ============================================================


class TestTableModel:
    r"""Tests for TableModel validation and properties."""

    def test_empty_model_is_simple(self) -> None:
        r"""Test that empty model is considered simple."""
        model = TableModel()
        assert model.is_simple is True
        assert model.col_count == 0

    def test_col_count_from_headers(self) -> None:
        r"""Test col_count from headers."""
        model = TableModel(
            headers=[[
                TableCell(content="A"),
                TableCell(content="B"),
                TableCell(content="C"),
            ]]
        )
        assert model.col_count == 3

    def test_col_count_from_rows(self) -> None:
        r"""Test col_count from rows when no headers."""
        model = TableModel(
            rows=[[
                TableCell(content="1"),
                TableCell(content="2"),
            ]]
        )
        assert model.col_count == 2

    def test_not_simple_with_colors(self) -> None:
        r"""Test that has_colors makes is_simple False."""
        model = TableModel(has_colors=True)
        assert model.is_simple is False

    def test_not_simple_with_merged(self) -> None:
        r"""Test that has_merged_cells makes is_simple False."""
        model = TableModel(has_merged_cells=True)
        assert model.is_simple is False

    def test_not_simple_with_landscape(self) -> None:
        r"""Test that is_landscape makes is_simple False."""
        model = TableModel(is_landscape=True)
        assert model.is_simple is False

    def test_not_simple_with_long(self) -> None:
        r"""Test that is_long makes is_simple False."""
        model = TableModel(is_long=True)
        assert model.is_simple is False

    def test_not_simple_with_multiple_header_rows(self) -> None:
        r"""Test that multiple header rows make is_simple False."""
        model = TableModel(
            headers=[
                [TableCell(content="H1")],
                [TableCell(content="H2")],
            ]
        )
        assert model.is_simple is False

