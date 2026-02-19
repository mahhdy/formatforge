"""
FormatForge - HTML Element Helpers
ابزارهای کمکی تبدیل عناصر پیچیده HTML به MDX

Provides helper functions and classes for converting complex HTML elements
to MDX/JSX format:
- TableModel: structured representation of HTML tables
- convert_table_element: smart table converter (simple/complex)
- convert_form_element: form → placeholder
- convert_media_element: video/audio/iframe → JSX
- convert_svg_element: inline SVG → file reference
- convert_math_from_html: KaTeX/MathJax/MathML → LaTeX
- extract_css_to_classnames: inline styles → className map

قواعد حیاتی:
- ZWNJ (U+200C) هرگز حذف نشود
- colspan/rowspan در JSX → colSpan/rowSpan
- HTML events → camelCase JSX
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TableModel / مدل جدول
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class CellModel:
    """نمایش یک سلول جدول."""
    text: str = ""
    colspan: int = 1
    rowspan: int = 1
    is_header: bool = False
    align: str = ""
    style: str = ""
    classes: list[str] = field(default_factory=list)

    @property
    def is_merged(self) -> bool:
        """آیا سلول ادغامی است؟"""
        return self.colspan > 1 or self.rowspan > 1


@dataclass
class RowModel:
    """نمایش یک ردیف جدول."""
    cells: list[CellModel] = field(default_factory=list)
    is_header: bool = False
    classes: list[str] = field(default_factory=list)

    @property
    def has_merged_cells(self) -> bool:
        return any(c.is_merged for c in self.cells)


@dataclass
class TableModel:
    """نمایش ساختارمند یک جدول HTML."""
    headers: list[RowModel] = field(default_factory=list)
    rows: list[RowModel] = field(default_factory=list)
    footer_rows: list[RowModel] = field(default_factory=list)
    caption: str = ""
    label: str = ""
    classes: list[str] = field(default_factory=list)
    style: str = ""

    @property
    def has_merged_cells(self) -> bool:
        """آیا جدول دارای سلول‌های ادغامی است؟"""
        all_rows = self.headers + self.rows + self.footer_rows
        return any(row.has_merged_cells for row in all_rows)

    @property
    def is_simple(self) -> bool:
        """آیا جدول ساده است (بدون ادغام)؟"""
        return not self.has_merged_cells

    @property
    def col_count(self) -> int:
        """تعداد ستون‌ها."""
        all_rows = self.headers + self.rows
        if not all_rows:
            return 0
        return max(len(row.cells) for row in all_rows)


def parse_table(element: Any) -> TableModel:
    """
    تحلیل <table> HTML → TableModel.
    Parse an HTML table element into a structured TableModel.

    Args:
        element: BeautifulSoup Tag برای <table>

    Returns:
        TableModel با ساختار کامل جدول
    """
    if not HAS_BS4:
        return TableModel()

    model = TableModel()

    # Caption
    caption_tag = element.find("caption")
    if caption_tag:
        model.caption = caption_tag.get_text(strip=True)

    # Classes
    model.classes = list(element.get("class") or [])

    # Parse thead
    thead = element.find("thead")
    if thead:
        for row_tag in thead.find_all("tr"):
            row = _parse_row(row_tag, is_header=True)
            model.headers.append(row)

    # Parse tbody (or direct rows)
    tbody = element.find("tbody")
    row_container = tbody if tbody else element
    for row_tag in row_container.find_all("tr", recursive=False if tbody else True):
        # Skip rows already parsed in thead/tfoot
        if row_tag.parent and row_tag.parent.name in ("thead", "tfoot"):
            continue
        row = _parse_row(row_tag, is_header=False)
        model.rows.append(row)

    # If no separate thead, promote first row to header
    if not model.headers and model.rows:
        first_row = model.rows[0]
        if all(c.is_header for c in first_row.cells):
            model.headers.append(model.rows.pop(0))

    # Parse tfoot
    tfoot = element.find("tfoot")
    if tfoot:
        for row_tag in tfoot.find_all("tr"):
            row = _parse_row(row_tag, is_header=False)
            model.footer_rows.append(row)

    return model


def _parse_row(row_tag: Any, is_header: bool = False) -> RowModel:
    """تحلیل یک ردیف <tr>."""
    row = RowModel(is_header=is_header)
    row.classes = list(row_tag.get("class") or [])

    for cell_tag in row_tag.find_all(["th", "td"]):
        cell = CellModel()
        cell.text = cell_tag.get_text(strip=True).replace("|", "\\|")
        cell.is_header = cell_tag.name == "th"
        cell.align = cell_tag.get("align", "")
        cell.style = cell_tag.get("style", "")
        cell.classes = list(cell_tag.get("class") or [])

        try:
            cell.colspan = int(cell_tag.get("colspan", 1))
        except (ValueError, TypeError):
            cell.colspan = 1

        try:
            cell.rowspan = int(cell_tag.get("rowspan", 1))
        except (ValueError, TypeError):
            cell.rowspan = 1

        row.cells.append(cell)

    return row


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Table Conversion / تبدیل جدول
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def convert_table_element(element: Any, require_import_cb=None) -> str:
    """
    تبدیل هوشمند <table> → MD pipe table یا HTML JSX.

    - ساده (بدون ادغام) → Markdown pipe table
    - ادغامی (colspan/rowspan) → HTML <table> JSX-compatible

    Args:
        element: BeautifulSoup Tag برای <table>
        require_import_cb: callback برای ثبت نیاز به import (اختیاری)

    Returns:
        رشته Markdown یا JSX
    """
    if not HAS_BS4:
        return ""

    model = parse_table(element)

    if model.is_simple:
        return _table_model_to_pipe(model)
    else:
        if require_import_cb:
            require_import_cb("Table")
        return _table_model_to_jsx(model)


def _table_model_to_pipe(model: TableModel) -> str:
    """تبدیل TableModel ساده → MD pipe table."""
    lines = []

    if model.caption:
        lines.append(f"\n*{model.caption}*")

    # Headers
    if model.headers:
        header_cells = [c.text for c in model.headers[0].cells]
        separator = ["-" * max(3, len(h)) for h in header_cells]
        lines.append("\n| " + " | ".join(header_cells) + " |")
        lines.append("| " + " | ".join(separator) + " |")

        # Additional header rows (rare)
        for row in model.headers[1:]:
            lines.append("| " + " | ".join(c.text for c in row.cells) + " |")
    elif model.rows:
        # Promote first data row to header
        first = model.rows[0]
        header_cells = [c.text for c in first.cells]
        separator = ["-" * max(3, len(h)) for h in header_cells]
        lines.append("\n| " + " | ".join(header_cells) + " |")
        lines.append("| " + " | ".join(separator) + " |")
        # Data rows (skip first)
        for row in model.rows[1:]:
            lines.append("| " + " | ".join(c.text for c in row.cells) + " |")
        return "\n".join(lines) + "\n\n"

    # Data rows
    for row in model.rows:
        lines.append("| " + " | ".join(c.text for c in row.cells) + " |")

    # Footer rows
    if model.footer_rows:
        lines.append("| " + " | ".join(["---"] * model.col_count) + " |")
        for row in model.footer_rows:
            lines.append("| " + " | ".join(c.text for c in row.cells) + " |")

    return "\n".join(lines) + "\n\n"


def _table_model_to_jsx(model: TableModel) -> str:
    """تبدیل TableModel پیچیده → HTML JSX-compatible."""
    lines = ["\n<div style={{overflowX: 'auto'}}>", "<table>"]

    if model.caption:
        lines.append(f"<caption>{model.caption}</caption>")

    # thead
    if model.headers:
        lines.append("<thead>")
        for row in model.headers:
            lines.append("<tr>")
            for cell in row.cells:
                attrs = _build_jsx_cell_attrs(cell)
                tag = "th" if cell.is_header else "td"
                lines.append(f"<{tag}{attrs}>{cell.text}</{tag}>")
            lines.append("</tr>")
        lines.append("</thead>")

    # tbody
    if model.rows:
        lines.append("<tbody>")
        for row in model.rows:
            lines.append("<tr>")
            for cell in row.cells:
                attrs = _build_jsx_cell_attrs(cell)
                tag = "th" if cell.is_header else "td"
                lines.append(f"<{tag}{attrs}>{cell.text}</{tag}>")
            lines.append("</tr>")
        lines.append("</tbody>")

    # tfoot
    if model.footer_rows:
        lines.append("<tfoot>")
        for row in model.footer_rows:
            lines.append("<tr>")
            for cell in row.cells:
                attrs = _build_jsx_cell_attrs(cell)
                tag = "td"
                lines.append(f"<{tag}{attrs}>{cell.text}</{tag}>")
            lines.append("</tr>")
        lines.append("</tfoot>")

    lines.append("</table>")
    lines.append("</div>\n")
    return "\n".join(lines)


def _build_jsx_cell_attrs(cell: CellModel) -> str:
    """ساخت attribute string JSX برای سلول."""
    attrs = ""
    if cell.colspan > 1:
        attrs += f" colSpan={{{cell.colspan}}}"
    if cell.rowspan > 1:
        attrs += f" rowSpan={{{cell.rowspan}}}"
    if cell.align:
        attrs += f' style={{{{textAlign: "{cell.align}"}}}}'
    if cell.classes:
        attrs += f' className="{" ".join(cell.classes)}"'
    return attrs


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Form Conversion / تبدیل فرم
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def convert_form_element(element: Any) -> str:
    """
    تبدیل <form> → comment + placeholder.
    Forms in MDX are converted to a comment placeholder.

    Args:
        element: BeautifulSoup Tag برای <form>

    Returns:
        رشته MDX با comment
    """
    if not HAS_BS4:
        return ""

    action = element.get("action", "") if isinstance(element, Tag) else ""
    method = (element.get("method", "get") or "get").upper()
    fields = []

    for inp in element.find_all(["input", "select", "textarea"]) if HAS_BS4 else []:
        name = inp.get("name", "")
        type_attr = inp.get("type", inp.name)
        if name:
            fields.append(f"{name}({type_attr})")

    fields_str = ", ".join(fields) if fields else "no named fields"
    comment = f"Form[action={action}, method={method}, fields={fields_str}]"

    return (
        f"\n\n{{/* {comment} */}}\n"
        f"{{/* TODO: Replace with <Form> component or equivalent */}}\n\n"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Media Conversion / تبدیل رسانه
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def convert_media_element(element: Any) -> str:
    """
    تبدیل <video>/<audio>/<iframe> → JSX components.

    - <video> → <Video src="..." />
    - <audio> → <Audio src="..." />
    - <iframe> → <Embed src="..." />

    Args:
        element: BeautifulSoup Tag

    Returns:
        رشته JSX کامپوننت
    """
    if not HAS_BS4 or not isinstance(element, Tag):
        return ""

    tag = element.name.lower()

    if tag == "video":
        return _convert_video(element)
    elif tag == "audio":
        return _convert_audio(element)
    elif tag == "iframe":
        return _convert_iframe(element)
    return ""


def _get_media_src(element: Any) -> str:
    """استخراج src از media element یا فرزند <source>."""
    src = element.get("src", "")
    if not src:
        source = element.find("source")
        if source:
            src = source.get("src", "")
    return src or ""


def _convert_video(element: Any) -> str:
    """<video> → <Video> کامپوننت."""
    src = _get_media_src(element)
    props = f'src="{src}"' if src else 'src=""'

    width = element.get("width", "")
    height = element.get("height", "")
    poster = element.get("poster", "")
    controls = "controls" in element.attrs
    autoplay = "autoplay" in element.attrs or "autoPlay" in element.attrs
    loop = "loop" in element.attrs
    muted = "muted" in element.attrs

    if width:
        props += f" width={{{width}}}"
    if height:
        props += f" height={{{height}}}"
    if poster:
        props += f' poster="{poster}"'
    if controls:
        props += " controls={true}"
    if autoplay:
        props += " autoPlay={true}"
    if loop:
        props += " loop={true}"
    if muted:
        props += " muted={true}"

    return f"\n\n<Video {props} />\n\n"


def _convert_audio(element: Any) -> str:
    """<audio> → <Audio> کامپوننت."""
    src = _get_media_src(element)
    props = f'src="{src}"' if src else 'src=""'

    controls = "controls" in element.attrs
    loop = "loop" in element.attrs
    muted = "muted" in element.attrs
    autoplay = "autoplay" in element.attrs

    if controls:
        props += " controls={true}"
    if loop:
        props += " loop={true}"
    if muted:
        props += " muted={true}"
    if autoplay:
        props += " autoPlay={true}"

    return f"\n\n<Audio {props} />\n\n"


def _convert_iframe(element: Any) -> str:
    """<iframe> → <Embed> کامپوننت."""
    src = element.get("src", "")
    title = element.get("title", "Embedded content")
    width = element.get("width", "")
    height = element.get("height", "")
    allow = element.get("allow", "")

    props = f'src="{src}" title="{title}"'
    if width:
        props += f" width={{{width}}}"
    if height:
        props += f" height={{{height}}}"
    if allow:
        props += f' allow="{allow}"'

    return f"\n\n<Embed {props} />\n\n"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SVG Conversion / تبدیل SVG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def convert_svg_element(
    element: Any,
    base_name: str = "page",
    counter: int = 1,
) -> tuple[str, Optional[str]]:
    """
    تبدیل inline <svg> → فایل مجزا + <Image>.

    Args:
        element: BeautifulSoup Tag برای <svg>
        base_name: نام پایه فایل (از file_path.stem)
        counter: شماره ترتیبی SVG

    Returns:
        tuple(mdx_reference, svg_content)
        - mdx_reference: رشته MDX برای <Image>
        - svg_content: محتوای SVG برای ذخیره (یا None اگر خالی)
    """
    if not HAS_BS4 or not isinstance(element, Tag):
        return "", None

    svg_str = str(element)
    if not svg_str.strip():
        return "", None

    # Generate unique filename
    content_hash = hashlib.md5(svg_str.encode()).hexdigest()[:8]
    svg_filename = f"{base_name}-svg-{counter}-{content_hash}.svg"

    # Get alt text from title or aria-label
    title_tag = element.find("title")
    alt = title_tag.get_text(strip=True) if title_tag else f"SVG figure {counter}"
    aria = element.get("aria-label", "")
    if aria:
        alt = aria

    mdx_ref = f'\n\n<Image src="./{svg_filename}" alt="{alt}" />\n\n'
    return mdx_ref, svg_str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Math Conversion / تبدیل ریاضی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def convert_math_from_html(element: Any) -> str:
    """
    تبدیل math عناصر HTML به LaTeX.

    - KaTeX rendered spans → $LaTeX$
    - MathJax rendered → $LaTeX$
    - MathML → LaTeX (تبدیل پایه)
    - <script type="math/tex"> → $LaTeX$

    Args:
        element: BeautifulSoup Tag

    Returns:
        رشته LaTeX ($...$ یا $$...$$)
    """
    if not HAS_BS4 or not isinstance(element, Tag):
        return ""

    tag = element.name.lower() if element.name else ""

    # Script with math content
    if tag == "script":
        return _convert_math_script(element)

    # MathML <math>
    if tag == "math":
        return _convert_mathml_element(element)

    # Span with KaTeX/MathJax class
    cls = " ".join(element.get("class") or [])
    if re.search(r"katex|mathjax|math", cls, re.I):
        return _extract_latex_from_katex(element)

    # data-latex / data-tex attribute
    for attr in ("data-latex", "data-tex", "data-math", "data-content"):
        latex = element.get(attr, "")
        if latex:
            if _is_display_math(element, latex):
                return f"\n\n$$\n{latex}\n$$\n\n"
            return f"${latex}$"

    # aria-label often contains the LaTeX
    aria = element.get("aria-label", "")
    if aria:
        return f"${aria}$"

    # Fallback: get text
    text = element.get_text(strip=True)
    if text:
        if _is_display_math(element, text):
            return f"\n\n$$\n{text}\n$$\n\n"
        return f"${text}$"

    return ""


def _is_display_math(element: Any, content: str) -> bool:
    """آیا ریاضیات display mode است؟"""
    cls = " ".join(element.get("class") or [])
    if re.search(r"display|block", cls, re.I):
        return True
    if element.name in ("div", "p"):
        return True
    if "\n" in content or len(content) > 80:
        return True
    return False


def _convert_math_script(element: Any) -> str:
    """<script type="math/..."> → LaTeX."""
    content = element.get_text(strip=True)
    type_attr = (element.get("type") or "").lower()
    is_display = "display" in type_attr
    if is_display or "\n" in content or len(content) > 80:
        return f"\n\n$$\n{content}\n$$\n\n"
    return f"${content}$"


def _convert_mathml_element(element: Any) -> str:
    """تبدیل ساده MathML → LaTeX."""
    display = element.get("display", "inline")
    # Try to get LaTeX from annotation
    annotation = element.find("annotation", {"encoding": re.compile(r"tex", re.I)})
    if annotation:
        latex = annotation.get_text(strip=True)
        if display == "block":
            return f"\n\n$$\n{latex}\n$$\n\n"
        return f"${latex}$"

    # Fallback: plain text from MathML
    text = element.get_text(strip=True)
    if display == "block":
        return f"\n\n$$\n{text}\n$$\n\n"
    return f"${text}$"


def _extract_latex_from_katex(element: Any) -> str:
    """استخراج LaTeX از KaTeX rendered element."""
    # KaTeX stores LaTeX in .katex-mathml annotation
    mathml = element.find("annotation", {"encoding": re.compile(r"tex", re.I)})
    if mathml:
        latex = mathml.get_text(strip=True)
        if _is_display_math(element, latex):
            return f"\n\n$$\n{latex}\n$$\n\n"
        return f"${latex}$"

    # Try data attributes
    for attr in ("data-latex", "data-tex"):
        latex = element.get(attr, "")
        if latex:
            if _is_display_math(element, latex):
                return f"\n\n$$\n{latex}\n$$\n\n"
            return f"${latex}$"

    # Fallback
    text = element.get_text(strip=True)
    return f"${text}$" if text else ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CSS Extraction / استخراج CSS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def extract_css_to_classnames(
    html_content: str,
) -> tuple[str, dict[str, str]]:
    """
    استخراج inline styles به className‌ها.

    - style="color:red" → className="generated-abc123"
    - Returns map: {className: cssRule}

    Args:
        html_content: رشته HTML ورودی

    Returns:
        tuple(cleaned_html, classname_map)
        - cleaned_html: HTML با className به‌جای style
        - classname_map: {className: css_string}
    """
    classname_map: dict[str, str] = {}

    def _replace_style(m: re.Match) -> str:
        css = m.group(2)
        css_hash = hashlib.md5(css.encode()).hexdigest()[:6]
        cls_name = f"ff-{css_hash}"
        classname_map[cls_name] = css
        return f'className="{cls_name}"'

    style_re = re.compile(r'\bstyle\s*=\s*(["\'])(.*?)\1', re.DOTALL)
    cleaned = style_re.sub(_replace_style, html_content)
    return cleaned, classname_map


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Metadata Extraction / استخراج متادیتا
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def extract_html_metadata(html_content: str) -> dict[str, str]:
    """
    استخراج متادیتا از <head> HTML.

    Args:
        html_content: محتوای HTML

    Returns:
        dict متادیتا: title, description, author, og:*, etc.
    """
    if not HAS_BS4:
        return {}

    soup = BeautifulSoup(html_content, "lxml")
    meta: dict[str, str] = {}

    # Title
    title_tag = soup.find("title")
    if title_tag:
        meta["title"] = title_tag.get_text(strip=True)

    # Meta tags
    for tag in soup.find_all("meta"):
        name = tag.get("name") or tag.get("property") or ""
        content = tag.get("content", "")
        if name and content:
            meta[name.lower()] = content

    # Canonical URL
    canonical = soup.find("link", {"rel": "canonical"})
    if canonical:
        meta["canonical"] = canonical.get("href", "")

    # HTML lang attribute
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        meta["lang"] = html_tag.get("lang", "")

    return meta


def detect_html_features(html_content: str) -> dict[str, bool]:
    """
    تشخیص ویژگی‌های محتوای HTML.

    Args:
        html_content: محتوای HTML

    Returns:
        dict ویژگی‌ها: has_math, has_code, has_tables, etc.
    """
    if not HAS_BS4:
        # Fallback to regex
        return {
            "has_math": bool(re.search(r"katex|mathjax|<math", html_content, re.I)),
            "has_code": bool(re.search(r"<code|<pre", html_content, re.I)),
            "has_tables": bool(re.search(r"<table", html_content, re.I)),
            "has_mermaid": bool(re.search(r"mermaid", html_content, re.I)),
            "has_images": bool(re.search(r"<img", html_content, re.I)),
            "has_video": bool(re.search(r"<video|<iframe", html_content, re.I)),
            "has_svg": bool(re.search(r"<svg", html_content, re.I)),
            "has_forms": bool(re.search(r"<form", html_content, re.I)),
            "has_persian": bool(re.search(r"[\u0600-\u06FF]", html_content)),
        }

    soup = BeautifulSoup(html_content, "lxml")

    return {
        "has_math": bool(
            soup.find("math")
            or soup.find(class_=re.compile(r"katex|mathjax|math-", re.I))
            or soup.find("script", {"type": re.compile(r"math|tex", re.I)})
        ),
        "has_code": bool(soup.find("code") or soup.find("pre")),
        "has_tables": bool(soup.find("table")),
        "has_mermaid": bool(soup.find(class_=re.compile(r"mermaid", re.I))),
        "has_images": bool(soup.find("img") or soup.find("figure")),
        "has_video": bool(soup.find("video") or soup.find("iframe")),
        "has_svg": bool(soup.find("svg")),
        "has_forms": bool(soup.find("form")),
        "has_persian": bool(re.search(r"[\u0600-\u06FF]", html_content)),
    }
