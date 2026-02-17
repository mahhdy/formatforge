# -*- coding: utf-8-sig -*-
r"""Table processor for FormatForge.

Converts LaTeX and HTML tables to MDX-compatible output.
"""
from __future__ import annotations

import re
import logging
from typing import List, Optional, Tuple

from .table_models import TableModel, TableCell, CellStyle


logger = logging.getLogger(__name__)


# ============================================================
# Regex patterns
# ============================================================

RE_LATEX_TABLE_ENV = re.compile(
    r'\\begin{(tabular|tabularx|longtable|sidewaystable)}(.*?)\\end{\1}',
    re.DOTALL,
)

RE_COL_SPEC = re.compile(r'{([^{}]*)}')

RE_MULTICOLUMN = re.compile(r'\\multicolumn{(\d+)}{([^{}]*)}{([^{}]*)}')

RE_MULTIROW = re.compile(r'\\multirow{(\d+)}{([^{}]*)}{([^{}]*)}')

RE_ROWCOLORS = re.compile(r'\\rowcolors{(\d+)}{([^{}]*)}{([^{}]*)}')

RE_CAPTION = re.compile(r'\\caption{([^{}]*)}')

RE_LABEL = re.compile(r'\\label{([^{}]*)}')

RE_CELLCOLOR = re.compile(r'\\cellcolor{([^{}]*)}')

RE_HLINE = re.compile(r'\\(hline|toprule|midrule|bottomrule)')

RE_ROW_SPLIT = re.compile(r'\\\\')

RE_HTML_TABLE = re.compile(r'<table[^>]*>(.*?)</table>', re.DOTALL | re.IGNORECASE)

RE_HTML_TR = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)

RE_HTML_CELL = re.compile(r'<(th|td)([^>]*)>(.*?)</(?:th|td)>', re.DOTALL | re.IGNORECASE)

RE_ATTR = re.compile(r'(colspan|rowspan|style|class)="([^"]*)"')


# ============================================================
# TableProcessor
# ============================================================


class TableProcessor:
    r"""Processor for converting tables to MDX format.

    Converts LaTeX and HTML tables to Markdown or HTML for MDX.
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        r"""Initialize table processor."""
        self.config = config or {}
        self.caption_position: str = self.config.get("caption_position", "below")
        self.default_rtl: bool = self.config.get("default_rtl", True)

    def process(self, text: str, source_format: str = "latex") -> str:
        r"""Process table text and return MDX output."""
        if source_format == "latex":
            model = self.parse_latex_table(text)
        elif source_format == "html":
            model = self.parse_html_table(text)
        else:
            logger.warning("Unknown source format: %s", source_format)
            return text

        if model.is_simple:
            return self.render_markdown_table(model)
        return self.render_html_table(model)

    # --------------------------------------------------------
    # LaTeX parsing
    # --------------------------------------------------------

    def parse_latex_table(self, text: str) -> TableModel:
        r"""Parse a LaTeX table environment into TableModel."""
        env_type, col_spec_str, body = self._detect_latex_env(text)
        if body is None:
            return TableModel()

        col_alignments = self._parse_col_spec(col_spec_str)
        caption, label = self._extract_caption_label(text)
        row_colors = self._detect_row_colors(text)
        headers, rows, has_merged = self._parse_latex_rows(body, len(col_alignments))

        return TableModel(
            headers=headers,
            rows=rows,
            caption=caption,
            label=label,
            is_rtl=self.default_rtl,
            is_long=(env_type == "longtable"),
            is_landscape=(env_type == "sidewaystable"),
            is_full_width=(env_type == "tabularx"),
            has_colors=bool(row_colors),
            has_merged_cells=has_merged,
            col_alignments=col_alignments,
            caption_position=self.caption_position,
        )

    def _detect_latex_env(self, text: str) -> Tuple[str, str, Optional[str]]:
        r"""Detect LaTeX table environment type and extract body."""
        match = RE_LATEX_TABLE_ENV.search(text)
        if not match:
            return ("tabular", "", None)
        env_type = match.group(1)
        inner = match.group(2)
        spec_match = RE_COL_SPEC.search(inner)
        col_spec = spec_match.group(1) if spec_match else ""
        if spec_match:
            body = inner[spec_match.end():]
        else:
            body = inner
        return (env_type, col_spec, body.strip())

    @staticmethod
    def _parse_col_spec(spec: str) -> List[str]:
        r"""Parse LaTeX column spec like |c|l|r| into alignment list."""
        alignments: List[str] = []
        for ch in spec:
            if ch in ('l', 'c', 'r', 'X', 'p'):
                if ch == 'l' or ch == 'X':
                    alignments.append("left")
                elif ch == 'r':
                    alignments.append("right")
                else:
                    alignments.append("center")
        return alignments

    @staticmethod
    def _extract_caption_label(text: str) -> Tuple[Optional[str], Optional[str]]:
        r"""Extract caption and label from LaTeX source."""
        cap_match = RE_CAPTION.search(text)
        label_match = RE_LABEL.search(text)
        caption = cap_match.group(1).strip() if cap_match else None
        label = label_match.group(1).strip() if label_match else None
        return (caption, label)

    @staticmethod
    def _detect_row_colors(text: str) -> Optional[dict]:
        r"""Detect rowcolors command in LaTeX."""
        match = RE_ROWCOLORS.search(text)
        if match:
            return {
                "start": int(match.group(1)),
                "odd_color": match.group(2),
                "even_color": match.group(3),
            }
        return None

    def _parse_latex_rows(
        self, body: str, col_count: int
    ) -> Tuple[List[List[TableCell]], List[List[TableCell]], bool]:
        r"""Parse LaTeX table body into header and data rows."""
        # Remove hline/toprule/midrule/bottomrule
        cleaned = RE_HLINE.sub('', body)
        # Split on \\ (row separator)
        raw_rows = RE_ROW_SPLIT.split(cleaned)

        has_merged = False
        parsed_rows: List[List[TableCell]] = []

        for raw_row in raw_rows:
            # Replace ALL whitespace chars with space, then strip
            # import re as _re
            stripped = raw_row.replace('\\n', ' ').replace('\n', ' ').replace('\r', ' ').strip()
            if not stripped:
                continue
            cells_text = stripped.split('&')
            row_cells: List[TableCell] = []
            for ct in cells_text:
                clean_ct = ct.replace('\\n', ' ').replace('\n', ' ').replace('\r', ' ').strip()
                cell, merged = self._parse_latex_cell(clean_ct)
                if merged:
                    has_merged = True
                row_cells.append(cell)
            # Filter out rows where all cells are empty
            if row_cells and any(c.content.strip() for c in row_cells):
                parsed_rows.append(row_cells)

        # First row is header
        headers: List[List[TableCell]] = []
        rows: List[List[TableCell]] = []
        if parsed_rows:
            header_row = parsed_rows[0]
            for c in header_row:
                c.is_header = True
            headers = [header_row]
            rows = parsed_rows[1:]

        return (headers, rows, has_merged)

    @staticmethod
    def _parse_latex_cell(text: str) -> Tuple[TableCell, bool]:
        r"""Parse a single LaTeX cell, detecting multicolumn/multirow."""
        merged = False
        colspan = 1
        rowspan = 1
        style: Optional[CellStyle] = None
        content = text

        mc_match = RE_MULTICOLUMN.search(content)
        if mc_match:
            colspan = int(mc_match.group(1))
            content = mc_match.group(3)
            merged = True

        mr_match = RE_MULTIROW.search(content)
        if mr_match:
            rowspan = int(mr_match.group(1))
            content = mr_match.group(3)
            merged = True

        cc_match = RE_CELLCOLOR.search(content)
        if cc_match:
            style = CellStyle(background_color=cc_match.group(1))
            content = RE_CELLCOLOR.sub('', content)

        content = content.strip()
        return (
            TableCell(
                content=content,
                colspan=colspan,
                rowspan=rowspan,
                style=style,
            ),
            merged,
        )

    # --------------------------------------------------------
    # HTML parsing
    # --------------------------------------------------------

    def parse_html_table(self, html: str) -> TableModel:
        r"""Parse an HTML table into TableModel."""
        table_match = RE_HTML_TABLE.search(html)
        if not table_match:
            return TableModel()

        table_inner = table_match.group(1)
        tr_matches = RE_HTML_TR.findall(table_inner)

        headers: List[List[TableCell]] = []
        rows: List[List[TableCell]] = []
        has_merged = False
        has_colors = False

        for tr_html in tr_matches:
            cell_matches = RE_HTML_CELL.findall(tr_html)
            row_cells: List[TableCell] = []
            is_header_row = False

            for tag, attrs, content in cell_matches:
                if tag.lower() == "th":
                    is_header_row = True
                cell, m, c = self._parse_html_cell(tag, attrs, content)
                if m:
                    has_merged = True
                if c:
                    has_colors = True
                row_cells.append(cell)

            if row_cells:
                if is_header_row:
                    for c in row_cells:
                        c.is_header = True
                    headers.append(row_cells)
                else:
                    rows.append(row_cells)

        return TableModel(
            headers=headers,
            rows=rows,
            is_rtl=self.default_rtl,
            has_colors=has_colors,
            has_merged_cells=has_merged,
            caption_position=self.caption_position,
        )

    @staticmethod
    def _parse_html_cell(
        tag: str, attrs: str, content: str
    ) -> Tuple[TableCell, bool, bool]:
        r"""Parse a single HTML cell element."""
        colspan = 1
        rowspan = 1
        has_color = False
        style: Optional[CellStyle] = None

        attr_matches = RE_ATTR.findall(attrs)
        for attr_name, attr_val in attr_matches:
            if attr_name == "colspan":
                colspan = int(attr_val)
            elif attr_name == "rowspan":
                rowspan = int(attr_val)
            elif attr_name == "style":
                style = CellStyle(css_class=attr_val)
                if "background" in attr_val or "color" in attr_val:
                    has_color = True
            elif attr_name == "class":
                style = style or CellStyle()
                style.css_class = attr_val

        merged = colspan > 1 or rowspan > 1
        return (
            TableCell(
                content=content.strip(),
                colspan=colspan,
                rowspan=rowspan,
                style=style,
                is_header=(tag.lower() == "th"),
            ),
            merged,
            has_color,
        )

    # --------------------------------------------------------
    # Rendering
    # --------------------------------------------------------

    def render_markdown_table(self, model: TableModel) -> str:
        r"""Render TableModel as Markdown pipe table."""
        out_lines: List[str] = []

        if model.caption and model.caption_position == "above":
            out_lines.append("")
            out_lines.append("**" + model.caption + "**")
            out_lines.append("")

        if model.headers:
            hdr = model.headers[0]
            hdr_line = "| " + " | ".join(c.content for c in hdr) + " |"
            out_lines.append(hdr_line)
            seps: List[str] = []
            for i, c in enumerate(hdr):
                align = model.col_alignments[i] if i < len(model.col_alignments) else "left"
                if align == "center":
                    seps.append(":---:")
                elif align == "right":
                    seps.append("---:")
                else:
                    seps.append("---")
            out_lines.append("| " + " | ".join(seps) + " |")

        for row in model.rows:
            row_line = "| " + " | ".join(c.content for c in row) + " |"
            out_lines.append(row_line)

        if model.caption and model.caption_position == "below":
            out_lines.append("")
            out_lines.append("**" + model.caption + "**")

        return chr(10).join(out_lines)

    def render_html_table(self, model: TableModel) -> str:
        r"""Render TableModel as HTML table for MDX."""
        out_lines: List[str] = []
        indent = "  "

        wrapper_open, wrapper_close = self._get_wrapper(model)
        if wrapper_open:
            out_lines.append(wrapper_open)

        # Build table tag
        attrs_parts: List[str] = []
        if model.label:
            attrs_parts.append(' id=' + chr(34) + model.label + chr(34))
        if model.is_rtl:
            attrs_parts.append(' dir=' + chr(34) + 'rtl' + chr(34))
        if model.is_full_width:
            attrs_parts.append(' style=' + chr(34) + 'width:100%' + chr(34))
        tag_attrs = "".join(attrs_parts)
        out_lines.append("<table" + tag_attrs + ">")

        if model.caption and model.caption_position == "above":
            out_lines.append(indent + "<caption>" + model.caption + "</caption>")

        if model.headers:
            out_lines.append(indent + "<thead>")
            for hdr_row in model.headers:
                out_lines.append(self._render_html_row(hdr_row, indent + indent))
            out_lines.append(indent + "</thead>")

        if model.rows:
            out_lines.append(indent + "<tbody>")
            for row in model.rows:
                out_lines.append(self._render_html_row(row, indent + indent))
            out_lines.append(indent + "</tbody>")

        if model.caption and model.caption_position == "below":
            cap_tag = '<caption style=' + chr(34) + 'caption-side:bottom' + chr(34) + '>'
            out_lines.append(indent + cap_tag + model.caption + '</caption>')

        out_lines.append("</table>")

        if wrapper_close:
            out_lines.append(wrapper_close)

        return chr(10).join(out_lines)

    @staticmethod
    def _get_wrapper(model: TableModel) -> Tuple[Optional[str], Optional[str]]:
        r"""Get wrapper div for special table types."""
        if model.is_long:
            return (
                '<div style=' + chr(34) + 'overflow-x:auto' + chr(34) + '>',
                '</div>',
            )
        if model.is_landscape:
            return (
                '<div className=' + chr(34) + 'landscape-table' + chr(34) + '>',
                '</div>',
            )
        return (None, None)

    @staticmethod
    def _render_html_row(cells: List[TableCell], indent: str) -> str:
        r"""Render a single HTML table row."""
        parts: List[str] = [indent + "<tr>"]
        for cell in cells:
            tag = "th" if cell.is_header else "td"
            attrs = ""
            if cell.colspan > 1:
                attrs += ' colspan=' + chr(34) + str(cell.colspan) + chr(34)
            if cell.rowspan > 1:
                attrs += ' rowspan=' + chr(34) + str(cell.rowspan) + chr(34)
            if cell.style and cell.style.background_color:
                attrs += ' style=' + chr(34) + 'background-color:' + cell.style.background_color + chr(34)
            parts.append(indent + "  <" + tag + attrs + ">" + cell.content + "</" + tag + ">")
        parts.append(indent + "</tr>")
        return chr(10).join(parts)
