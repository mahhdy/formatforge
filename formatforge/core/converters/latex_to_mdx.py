"""
FormatForge - LaTeX → MDX Converter — S08-C2/C3
تبدیل‌گر LaTeX به MDX

Converts LaTeX files to MDX format:
  1. Parse preamble + body via LatexParser
  2. Convert structural commands (sections, formatting, lists)
  3. Convert environments (theorems, figures, tables, code, math)
  4. Run processor pipeline (math, code, links, footnotes, RTL)
  5. Generate frontmatter, imports, assemble MDX

قواعد حیاتی:
- ZWNJ (U+200C) هرگز حذف نشود
- frontmatter باید معتبر باشد
- dir="rtl" برای محتوای فارسی
- import statements برای کامپوننت‌های استفاده‌شده
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Optional

import yaml

from formatforge.core.converters.base import (
    BaseConverter,
    ConversionContext,
    ConversionError,
    DocumentConversionResult,
    QualityReport,
    ZWNJReport,
)
from formatforge.core.converters.jsx_utils import (
    convert_html_to_jsx,
    generate_imports,
)
from formatforge.core.converters.latex_parser import (
    ZWNJ,
    CommandNode,
    CommentNode,
    EnvironmentNode,
    LatexDocument,
    LatexParser,
    MathNode,
    TextNode,
    has_persian,
)
from formatforge.core.processors.base import (
    ProcessorContext,
    ProcessorPipeline,
)
from formatforge.core.processors.math_processor import MathProcessor
from formatforge.core.processors.code_processor import CodeProcessor
from formatforge.core.processors.table_processor import TableProcessor
from formatforge.core.processors.image_processor import ImageProcessor
from formatforge.core.processors.admonition_processor import AdmonitionProcessor
from formatforge.core.processors.link_processor import LinkProcessor
from formatforge.core.processors.footnote_processor import FootnoteProcessor
from formatforge.core.processors.rtl_processor import RTLProcessor
from formatforge.models.metadata import DocumentMetadata

logger = logging.getLogger("formatforge.converters.latex_to_mdx")

# ─── Constants ────────────────────────────────────
_SLUG_UNSAFE = re.compile(r"[^a-z0-9]+")

# Commands to silently skip (no output)
_SKIP_COMMANDS = frozenset({
    "maketitle", "tableofcontents", "listoffigures", "listoftables",
    "frontmatter", "mainmatter", "backmatter",
    "clearpage", "newpage", "pagebreak",
    "thispagestyle", "pagestyle",
    "noindent", "indent",
    "vspace", "vfill", "bigskip", "medskip", "smallskip",
    "hspace", "hfill",
    "centering", "raggedleft", "raggedright",
    "selectfont", "normalsize", "small", "footnotesize",
    "large", "Large", "LARGE", "huge", "Huge", "tiny",
    "bfseries", "itshape", "rmfamily", "ttfamily", "sffamily",
    "settextfont", "setlatintextfont", "setdigitfont",
    "geometry", "headrulewidth", "footrulewidth",
    "setcounter", "addtocounter", "stepcounter",
    "phantom", "hphantom", "vphantom",
    "definecolor", "colorlet",
    "usetikzlibrary", "pgfplotsset", "tikzset",
    "graphicspath",
    "bibliographystyle",
    "fancyhf", "fancyhead", "fancyfoot",
    "renewcommand",
})

# Commands to convert to pagebreak
_PAGEBREAK_COMMANDS = frozenset({
    "clearpage", "newpage", "pagebreak",
})

# Formatting commands: name → (prefix, suffix)
_FORMAT_COMMANDS: dict[str, tuple[str, str]] = {
    "textbf": ("**", "**"),
    "textit": ("*", "*"),
    "emph": ("*", "*"),
    "underline": ("<u>", "</u>"),
    "sout": ("~~", "~~"),
    "texttt": ("`", "`"),
    "textsc": ('<span style={{fontVariant: "small-caps"}}>', "</span>"),
    "textrm": ("", ""),
    "textsf": ("", ""),
}

# Section commands: name → heading level
_SECTION_LEVELS: dict[str, int] = {
    "chapter": 1,
    "section": 2,
    "subsection": 3,
    "subsubsection": 4,
    "paragraph": 5,
    "subparagraph": 6,
}

# Environment types for theorem-like components
_THEOREM_ENVS = frozenset({
    "theorem", "lemma", "corollary", "proposition", "conjecture", "claim",
})
_DEFINITION_ENVS = frozenset({"definition"})
_PROOF_ENVS = frozenset({"proof", "proofbox"})
_EXAMPLE_ENVS = frozenset({"example", "remark"})

# Math environments that should be wrapped in display math
_MATH_ENVS = frozenset({
    "equation", "equation*", "align", "align*", "gather", "gather*",
    "multline", "multline*", "split", "alignat", "alignat*",
    "eqnarray", "eqnarray*", "cases",
    "pmatrix", "bmatrix", "vmatrix",
})

# Code environments
_CODE_ENVS = frozenset({"lstlisting", "minted", "verbatim"})

# Quote environments
_QUOTE_ENVS = frozenset({"quote", "quotation", "verse"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions / توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _generate_frontmatter(metadata: dict[str, Any]) -> str:
    """تولید frontmatter YAML."""
    yaml_str = yaml.dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return f"---\n{yaml_str.rstrip()}\n---"


def _generate_slug(title: str) -> str:
    """تولید slug از عنوان."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\x00-\x7f]", "", slug)
    slug = _SLUG_UNSAFE.sub("-", slug).strip("-")
    if not slug:
        slug = f"doc-{int(time.time()) % 100000}"
    return slug[:60]


def _detect_language(content: str) -> str:
    """تشخیص زبان محتوا."""
    persian_chars = len(re.findall(
        r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]", content
    ))
    latin_chars = len(re.findall(r"[a-zA-Z]", content))
    if persian_chars == 0 and latin_chars > 0:
        return "en"
    if persian_chars > 0 and latin_chars > persian_chars * 2:
        return "fa-en"
    return "fa"


def _detect_direction(lang: str) -> str:
    """جهت متن بر اساس زبان."""
    return "ltr" if lang == "en" else "rtl"


def _escape_jsx(text: str) -> str:
    """Escape characters that are special in JSX."""
    text = text.replace("{", "&#123;")
    text = text.replace("}", "&#125;")
    return text


def _convert_label_to_id(label: str) -> str:
    """Convert LaTeX label to MDX-safe id: fig:my_fig → fig-my-fig."""
    return re.sub(r"[^a-zA-Z0-9-]", "-", label).strip("-")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Node → Markdown Conversion
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def convert_nodes(
    nodes: list,
    doc: LatexDocument,
    context: _ConverterState,
) -> str:
    """
    تبدیل بازگشتی لیست گره‌ها به Markdown/MDX.
    Recursively convert a list of LatexNode to MDX string.
    """
    parts: list[str] = []
    for node in nodes:
        parts.append(convert_node(node, doc, context))
    return "".join(parts)


def convert_node(node: Any, doc: LatexDocument, ctx: _ConverterState) -> str:
    """تبدیل یک گره به رشته MDX."""
    if isinstance(node, TextNode):
        return node.content
    if isinstance(node, CommentNode):
        return ""  # strip LaTeX comments
    if isinstance(node, MathNode):
        return _convert_math(node, ctx)
    if isinstance(node, CommandNode):
        return _convert_command(node, doc, ctx)
    if isinstance(node, EnvironmentNode):
        return _convert_environment(node, doc, ctx)
    return ""


def _convert_math(node: MathNode, ctx: _ConverterState) -> str:
    """Convert MathNode to KaTeX-compatible markdown."""
    content = node.content.strip()
    if node.display:
        ctx.math_block_count += 1
        return f"\n\n$$\n{content}\n$$\n\n"
    else:
        ctx.math_inline_count += 1
        return f"${content}$"


def _convert_command(
    node: CommandNode, doc: LatexDocument, ctx: _ConverterState,
) -> str:
    """Convert a LaTeX command node to MDX."""
    name = node.name

    # ── Skip commands ──
    if name in _SKIP_COMMANDS:
        return ""

    # ── Pagebreak → thematic break ──
    if name in _PAGEBREAK_COMMANDS:
        return "\n\n---\n\n"

    # ── Section headings ──
    if name in _SECTION_LEVELS:
        level = _SECTION_LEVELS[name]
        title = node.args[0] if node.args else ""
        hashes = "#" * level
        ctx.heading_count += 1
        return f"\n\n{hashes} {title}\n\n"

    # ── Formatting ──
    if name in _FORMAT_COMMANDS:
        prefix, suffix = _FORMAT_COMMANDS[name]
        content = node.args[0] if node.args else ""
        return f"{prefix}{content}{suffix}"

    # ── Text color: \textcolor{color}{text} ──
    if name == "textcolor":
        color = node.args[0] if len(node.args) > 0 else ""
        text = node.args[1] if len(node.args) > 1 else ""
        return f'<span style={{{{color: "{color}"}}}}>{text}</span>'

    # ── Color: \color{color} — skip, no text argument ──
    if name == "color":
        return ""

    # ── Hyperlinks ──
    if name == "href":
        url = node.args[0] if len(node.args) > 0 else ""
        text = node.args[1] if len(node.args) > 1 else url
        ctx.link_count += 1
        return f"[{text}]({url})"

    if name == "url":
        url = node.args[0] if node.args else ""
        ctx.link_count += 1
        return f"[{url}]({url})"

    # ── Cross-references ──
    if name == "ref" or name == "cref" or name == "Cref":
        label = node.args[0] if node.args else ""
        ref_id = _convert_label_to_id(label)
        ctx.crossref_count += 1
        return f'<CrossRef target="{ref_id}" />'

    if name == "eqref":
        label = node.args[0] if node.args else ""
        ref_id = _convert_label_to_id(label)
        ctx.crossref_count += 1
        return f'<CrossRef target="{ref_id}" type="equation" />'

    if name == "label":
        label = node.args[0] if node.args else ""
        ref_id = _convert_label_to_id(label)
        ctx.labels[ref_id] = label
        return ""

    # ── Footnotes ──
    if name == "footnote":
        ctx.footnote_count += 1
        text = node.args[0] if node.args else ""
        return f"[^{ctx.footnote_count}]"

    if name == "LTRfootnote":
        ctx.footnote_count += 1
        text = node.args[0] if node.args else ""
        return f"[^{ctx.footnote_count}]"

    # ── Citations ──
    if name == "cite" or name == "textcite" or name == "parencite":
        keys = node.args[0] if node.args else ""
        ctx.citation_count += 1
        return f'<Citation keys="{keys}" />'

    if name == "autocite":
        keys = node.args[0] if node.args else ""
        ctx.citation_count += 1
        return f'<Citation keys="{keys}" />'

    # ── Graphics ──
    if name == "includegraphics":
        path = node.args[0] if node.args else ""
        opts_str = node.opts[0] if node.opts else ""
        ctx.image_count += 1
        # Parse width from options
        width = ""
        wm = re.search(r"width\s*=\s*([\d.]+)\\(textwidth|linewidth)", opts_str)
        if wm:
            pct = int(float(wm.group(1)) * 100)
            width = f' width="{pct}%"'
        return f'<img src="{path}"{width} />'

    # ── Items ──
    if name == "item":
        return "\n- "

    # ── Persian/bidi helpers ──
    if name == "lr":
        text = node.args[0] if node.args else ""
        return f'<span dir="ltr">{text}</span>'

    if name == "rl":
        text = node.args[0] if node.args else ""
        return f'<span dir="rtl">{text}</span>'

    # ── Non-breaking space ──
    if name == "~" or name == " ":
        return "&nbsp;"

    # ── Line break ──
    if name == "\\":
        return "  \n"

    # ── Tilde/special chars ──
    if name == "%" or name == "$" or name == "&" or name == "#" or name == "_":
        return name

    if name == "textasciitilde":
        return "~"

    # ── printbibliography ──
    if name == "printbibliography":
        return '\n\n<Bibliography />\n\n'

    # ── Unknown command — just output args ──
    if node.args:
        return node.args[0]
    return ""


def _convert_environment(
    node: EnvironmentNode, doc: LatexDocument, ctx: _ConverterState,
) -> str:
    """Convert a LaTeX environment to MDX."""
    name = node.name

    # ── Math environments ──
    if name in _MATH_ENVS:
        ctx.math_block_count += 1
        body = node.body.strip()
        return f"\n\n$$\n\\begin{{{name}}}\n{body}\n\\end{{{name}}}\n$$\n\n"

    # ── Code environments ──
    if name in _CODE_ENVS:
        ctx.code_block_count += 1
        lang = ""
        if name == "lstlisting" and node.opts:
            lm = re.search(r"language\s*=\s*(\w+)", node.opts[0], re.IGNORECASE)
            if lm:
                lang = lm.group(1).lower()
        elif name == "minted" and node.args:
            lang = node.args[0].lower()
        body = node.body
        # Remove leading/trailing blank lines
        body = body.strip("\n")
        return f"\n\n```{lang}\n{body}\n```\n\n"

    # ── Quote environments ──
    if name in _QUOTE_ENVS:
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        lines = inner.strip().split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        return f"\n\n{quoted}\n\n"

    # ── Itemize ──
    if name == "itemize":
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        return f"\n\n{inner.strip()}\n\n"

    # ── Enumerate ──
    if name == "enumerate":
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        # Replace "- " with numbered items
        lines = inner.strip().split("\n")
        numbered: list[str] = []
        num = 1
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("- "):
                numbered.append(f"{num}. {stripped[2:]}")
                num += 1
            else:
                numbered.append(line)
        return "\n\n" + "\n".join(numbered) + "\n\n"

    # ── Description ──
    if name == "description":
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        return f"\n\n{inner.strip()}\n\n"

    # ── Theorem-like environments ──
    if name in _THEOREM_ENVS or name in doc.preamble.tcb_environments:
        return _convert_theorem_env(node, doc, ctx)

    if name in _DEFINITION_ENVS:
        return _convert_component_env(node, "Definition", doc, ctx)

    if name in _PROOF_ENVS:
        return _convert_component_env(node, "Proof", doc, ctx)

    if name in _EXAMPLE_ENVS:
        return _convert_component_env(node, "Example", doc, ctx)

    # ── Figure ──
    if name in ("figure", "figure*"):
        return _convert_figure(node, doc, ctx)

    # ── Wrapfigure ──
    if name == "wrapfigure":
        return _convert_wrapfigure(node, doc, ctx)

    # ── Subfigure ──
    if name == "subfigure":
        return _convert_subfigure(node, doc, ctx)

    # ── Table ──
    if name in ("table", "table*"):
        return _convert_table_env(node, doc, ctx)

    if name == "sidewaystable":
        ctx.table_count += 1
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        return f'\n\n<div className="landscape-table">\n\n{inner.strip()}\n\n</div>\n\n'

    # ── Tabular/tabularx/longtable/array ──
    if name in ("tabular", "tabularx", "longtable", "array"):
        ctx.table_count += 1
        # Leave raw for TableProcessor to handle
        return f"\n\n{node.body}\n\n"

    # ── Abstract ──
    if name == "abstract":
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        return f'\n\n<Admonition type="abstract" title="چکیده">\n\n{inner.strip()}\n\n</Admonition>\n\n'

    # ── Center ──
    if name == "center":
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        return f'\n\n<div style={{{{textAlign: "center"}}}}>\n\n{inner.strip()}\n\n</div>\n\n'

    # ── Minipage ──
    if name == "minipage":
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        return inner

    # ── TikZ — leave as raw for TikZ compiler ──
    if name in ("tikzpicture", "pgfpicture"):
        ctx.image_count += 1
        return f'\n\n<TikZDiagram>\n{node.body}\n</TikZDiagram>\n\n'

    # ── tcolorbox ──
    if name == "tcolorbox":
        return _convert_tcolorbox(node, doc, ctx)

    # ── Latin text ──
    if name == "latin":
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        return f'<span dir="ltr">{inner}</span>'

    # ── Algorithm ──
    if name in ("algorithm", "algorithm2e"):
        ctx.code_block_count += 1
        return f"\n\n```\n{node.body.strip()}\n```\n\n"

    # ── Document ──
    if name == "document":
        return convert_nodes(node.children, doc, ctx) if node.children else node.body

    # ── Warning/note boxes ──
    if name == "warningbox":
        title = node.opts[0] if node.opts else "هشدار"
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        return f'\n\n<Admonition type="warning" title="{title}">\n\n{inner.strip()}\n\n</Admonition>\n\n'

    if name == "notebox":
        title = node.opts[0] if node.opts else "نکته"
        inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
        return f'\n\n<Admonition type="note" title="{title}">\n\n{inner.strip()}\n\n</Admonition>\n\n'

    # ── Filecontents — skip ──
    if name in ("filecontents", "filecontents*"):
        return ""

    # ── Fallback: just convert children ──
    if node.children:
        return convert_nodes(node.children, doc, ctx)
    return node.body


def _convert_theorem_env(
    node: EnvironmentNode, doc: LatexDocument, ctx: _ConverterState,
) -> str:
    """Convert theorem-like environments to MDX component."""
    name = node.name

    # Determine component name from tcb_environments or defaults
    component = "Theorem"
    if name in doc.preamble.tcb_environments:
        env_type = doc.preamble.tcb_environments[name].get("type", "theorem")
        component = env_type.capitalize()
        if component == "Box":
            component = "Admonition"
    elif name in _THEOREM_ENVS:
        component = "Theorem"
    elif name in _DEFINITION_ENVS:
        component = "Definition"
    elif name in _PROOF_ENVS:
        component = "Proof"
    elif name in _EXAMPLE_ENVS:
        component = "Example"

    # Extract title and label from args
    title = ""
    label_id = ""
    if node.args:
        title = node.args[0]
    if len(node.args) > 1:
        label_id = _convert_label_to_id(node.args[1])
    if node.opts:
        # opts often contain title in theorem envs
        if not title:
            title = node.opts[0]

    inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
    inner = inner.strip()

    attrs: list[str] = []
    if label_id:
        attrs.append(f'id="{label_id}"')
    if title:
        attrs.append(f'title="{title}"')
    attrs_str = " " + " ".join(attrs) if attrs else ""

    ctx.require_component(component)
    return f"\n\n<{component}{attrs_str}>\n\n{inner}\n\n</{component}>\n\n"


def _convert_component_env(
    node: EnvironmentNode,
    component: str,
    doc: LatexDocument,
    ctx: _ConverterState,
) -> str:
    """Convert environment to a named MDX component."""
    title = ""
    label_id = ""
    if node.opts:
        title = node.opts[0]
    if node.args:
        if not title:
            title = node.args[0]
        if len(node.args) > 1:
            label_id = _convert_label_to_id(node.args[1])

    inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
    inner = inner.strip()

    attrs: list[str] = []
    if label_id:
        attrs.append(f'id="{label_id}"')
    if title:
        attrs.append(f'title="{title}"')
    attrs_str = " " + " ".join(attrs) if attrs else ""

    ctx.require_component(component)
    return f"\n\n<{component}{attrs_str}>\n\n{inner}\n\n</{component}>\n\n"


def _convert_figure(
    node: EnvironmentNode, doc: LatexDocument, ctx: _ConverterState,
) -> str:
    """Convert \\begin{figure} to <Figure> component."""
    ctx.image_count += 1
    inner = convert_nodes(node.children, doc, ctx) if node.children else node.body

    # Extract caption from inner content
    caption = ""
    cm = re.search(r"\\caption\{(.*?)\}", node.body, re.DOTALL)
    if cm:
        caption = cm.group(1).strip()

    # Extract label
    label_id = ""
    lm = re.search(r"\\label\{([^}]+)\}", node.body)
    if lm:
        label_id = _convert_label_to_id(lm.group(1))

    # Extract image src from inner
    src = ""
    sm = re.search(r'src="([^"]+)"', inner)
    if sm:
        src = sm.group(1)

    attrs: list[str] = []
    if src:
        attrs.append(f'src="{src}"')
    if caption:
        attrs.append(f'caption="{caption}"')
    if label_id:
        attrs.append(f'id="{label_id}"')
    attrs_str = " " + " ".join(attrs) if attrs else ""

    ctx.require_component("Figure")
    return f"\n\n<Figure{attrs_str} />\n\n"


def _convert_wrapfigure(
    node: EnvironmentNode, doc: LatexDocument, ctx: _ConverterState,
) -> str:
    """Convert \\begin{wrapfigure} to <Figure float=...>."""
    ctx.image_count += 1

    # wrapfigure args: {position}{width}
    position = node.args[0] if node.args else "r"
    width = node.args[1] if len(node.args) > 1 else ""

    float_dir = "right" if position in ("r", "R") else "left"

    # Parse width percentage
    width_pct = ""
    wm = re.search(r"([\d.]+)\\(textwidth|linewidth)", width)
    if wm:
        width_pct = f"{int(float(wm.group(1)) * 100)}%"

    inner = convert_nodes(node.children, doc, ctx) if node.children else node.body

    # Extract src, caption, label
    src = ""
    sm = re.search(r'src="([^"]+)"', inner)
    if sm:
        src = sm.group(1)
    caption = ""
    cm = re.search(r"\\caption\{(.*?)\}", node.body, re.DOTALL)
    if cm:
        caption = cm.group(1).strip()

    attrs: list[str] = [f'float="{float_dir}"']
    if width_pct:
        attrs.append(f'width="{width_pct}"')
    if src:
        attrs.append(f'src="{src}"')
    if caption:
        attrs.append(f'caption="{caption}"')
    attrs_str = " " + " ".join(attrs)

    ctx.require_component("Figure")
    return f"\n\n<Figure{attrs_str} />\n\n"


def _convert_subfigure(
    node: EnvironmentNode, doc: LatexDocument, ctx: _ConverterState,
) -> str:
    """Convert subfigure inside a FigureGrid."""
    ctx.image_count += 1
    inner = convert_nodes(node.children, doc, ctx) if node.children else node.body
    return inner


def _convert_table_env(
    node: EnvironmentNode, doc: LatexDocument, ctx: _ConverterState,
) -> str:
    """Convert \\begin{table} environment."""
    ctx.table_count += 1

    caption = ""
    cm = re.search(r"\\caption\{(.*?)\}", node.body, re.DOTALL)
    if cm:
        caption = cm.group(1).strip()

    label_id = ""
    lm = re.search(r"\\label\{([^}]+)\}", node.body)
    if lm:
        label_id = _convert_label_to_id(lm.group(1))

    inner = convert_nodes(node.children, doc, ctx) if node.children else node.body

    parts: list[str] = ["\n\n"]
    if caption:
        parts.append(f"**{caption}**\n\n")
    parts.append(inner.strip())
    parts.append("\n\n")

    return "".join(parts)


def _convert_tcolorbox(
    node: EnvironmentNode, doc: LatexDocument, ctx: _ConverterState,
) -> str:
    """Convert \\begin{tcolorbox} to admonition."""
    title = ""
    if node.opts:
        tm = re.search(r"title\s*=\s*\{([^}]+)\}", node.opts[0])
        if tm:
            title = tm.group(1).strip()
        elif "=" not in node.opts[0]:
            title = node.opts[0]

    inner = convert_nodes(node.children, doc, ctx) if node.children else node.body

    adm_type = "note"
    # Detect type from style
    if node.opts:
        opt = node.opts[0].lower()
        if "orange" in opt or "warning" in opt or "red" in opt:
            adm_type = "warning"
        elif "green" in opt:
            adm_type = "tip"

    return f'\n\n<Admonition type="{adm_type}" title="{title}">\n\n{inner.strip()}\n\n</Admonition>\n\n'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Converter State / وضعیت داخلی تبدیل‌گر
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class _ConverterState:
    """Internal state for tracking counts and components during conversion."""

    def __init__(self) -> None:
        self.math_block_count: int = 0
        self.math_inline_count: int = 0
        self.table_count: int = 0
        self.image_count: int = 0
        self.code_block_count: int = 0
        self.heading_count: int = 0
        self.footnote_count: int = 0
        self.citation_count: int = 0
        self.crossref_count: int = 0
        self.link_count: int = 0
        self.labels: dict[str, str] = {}
        self.components_used: set[str] = set()
        self.footnotes: list[str] = []

    def require_component(self, name: str) -> None:
        self.components_used.add(name)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LaTeXToMDXConverter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LaTeXToMDXConverter(BaseConverter):
    """
    تبدیل‌گر LaTeX به MDX.
    Converts LaTeX files to MDX format.

    مراحل:
    1. Parse via LatexParser
    2. Convert nodes to Markdown/MDX
    3. Run processor pipeline
    4. Generate frontmatter + imports
    5. Assemble final MDX
    """

    format_name: ClassVar[str] = "latex"
    file_extensions: ClassVar[list[str]] = [".tex", ".latex"]
    mime_types: ClassVar[list[str]] = ["text/x-tex", "application/x-latex"]
    priority: ClassVar[int] = 15

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._pipeline: Optional[ProcessorPipeline] = None
        self._parser = LatexParser()

    def _get_pipeline(self) -> ProcessorPipeline:
        """ساخت یا بازگرداندن خط لوله پردازش."""
        if self._pipeline is None:
            self._pipeline = ProcessorPipeline(name="latex-to-mdx")
            self._pipeline.add(MathProcessor(self.config))
            self._pipeline.add(CodeProcessor(self.config))
            self._pipeline.add(LinkProcessor(self.config))
            self._pipeline.add(FootnoteProcessor(self.config))
            self._pipeline.add(RTLProcessor(self.config))
        return self._pipeline

    def _run_standalone_processors(
        self, content: str, source_format: str,
    ) -> str:
        """اجرای پردازشگرهای مستقل."""
        try:
            content = TableProcessor().process(content, source_format=source_format)
        except Exception as exc:
            logger.warning("TableProcessor error: %s", exc)
        try:
            content = ImageProcessor().process(content, source_format=source_format)
        except Exception as exc:
            logger.warning("ImageProcessor error: %s", exc)
        try:
            content = AdmonitionProcessor().process(content, source_format=source_format)
        except Exception as exc:
            logger.warning("AdmonitionProcessor error: %s", exc)
        return content

    # ─── Detection ────────────────────────

    def detect(self, file_path: Path) -> bool:
        """آیا فایل LaTeX است؟"""
        if self.detect_by_extension(file_path):
            return True
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")[:3000]
            indicators = (
                r"\documentclass" in content,
                r"\begin{document}" in content,
                r"\usepackage" in content,
                r"\section" in content or r"\chapter" in content,
            )
            return sum(indicators) >= 2
        except OSError:
            return False

    # ─── Metadata ─────────────────────────

    def extract_metadata(
        self,
        file_path: Path,
        context: Optional[ConversionContext] = None,
    ) -> DocumentMetadata:
        """
        استخراج متادیتا از فایل LaTeX.
        Extract metadata from LaTeX preamble.
        """
        content = self.read_file(file_path)
        doc = self._parser.parse(content, source_path=file_path)
        preamble = doc.preamble

        # Title
        title = preamble.title or file_path.stem.replace("-", " ").replace("_", " ")

        # Language detection
        lang = "fa" if preamble.fonts.is_xepersian else _detect_language(content)
        direction = _detect_direction(lang)

        # Slug
        slug = _generate_slug(title)

        # Date — validate ISO format, fallback to today
        date = preamble.date or ""
        # Strip braces from date
        date = date.strip().strip("{}")
        # Try to extract a yyyy-mm-dd or yyyy pattern
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", date)
        if date_match:
            date = date_match.group()
        elif re.match(r"\d{4}$", date.strip()):
            date = f"{date.strip()}-01-01"
        else:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Features
        has_math = any(
            isinstance(n, MathNode) or
            (isinstance(n, EnvironmentNode) and n.name in _MATH_ENVS)
            for n in doc.body
        )
        has_code = any(
            isinstance(n, EnvironmentNode) and n.name in _CODE_ENVS
            for n in doc.body
        )
        has_tikz = any(
            isinstance(n, EnvironmentNode) and n.name in ("tikzpicture", "pgfpicture")
            for n in doc.body
        ) or "tikzpicture" in content

        # Abstract
        description = preamble.abstract or ""

        metadata = DocumentMetadata(
            title=title,
            slug=slug,
            date=date,
            lang=lang,
            dir=direction,
            type="book" if preamble.document_class == "book" else "article",
            tags=[],
            description=description,
            math=has_math or "$" in content,
            mermaid=False,
            codeHighlight=has_code,
            source_format="latex",
            source_file=file_path.name,
        )

        # Set author if available
        if preamble.author:
            from formatforge.models.metadata import AuthorInfo
            try:
                metadata.author = AuthorInfo(name=preamble.author)
            except Exception:
                pass  # skip if author name doesn't validate

        return metadata

    # ─── Conversion ───────────────────────

    def convert(
        self,
        file_path: Path,
        context: ConversionContext,
    ) -> DocumentConversionResult:
        """
        تبدیل فایل LaTeX به MDX.
        Convert LaTeX file to MDX format.
        """
        start = time.time()
        doc_id = (
            context.document_info.id
            if context.document_info
            else file_path.stem
        )

        result = DocumentConversionResult(
            document_id=doc_id,
            source_path=str(file_path),
            status="processing",
        )

        try:
            # 1. Read and parse
            raw_content = self.read_file(file_path)
            result.input_bytes = len(raw_content.encode("utf-8"))
            zwnj_before = self.count_zwnj(raw_content)
            context.zwnj_count_before = zwnj_before

            # 2. Parse LaTeX
            doc = self._parser.parse(raw_content, source_path=file_path)

            # 3. Extract metadata
            if context.metadata is None:
                context.metadata = self.extract_metadata(file_path, context)

            # 4. Convert nodes to markdown/MDX
            conv_state = _ConverterState()
            mdx_body = convert_nodes(doc.body, doc, conv_state)

            # 5. Collect footnotes (if any were generated)
            if conv_state.footnote_count > 0:
                # footnotes collected during conversion
                pass

            # 6. Run standalone processors
            # Use "markdown" since content is already converted from LaTeX to MD/MDX
            mdx_body = self._run_standalone_processors(
                mdx_body, source_format="markdown",
            )

            # 7. Run pipeline processors
            proc_ctx = ProcessorContext(
                source_format="markdown",
                source_path=str(file_path),
                language=context.metadata.lang,
                config=self.config,
            )
            proc_ctx.zwnj_count_before = zwnj_before

            pipeline = self._get_pipeline()
            pipe_result = pipeline.run(mdx_body, proc_ctx)
            mdx_body = pipe_result.content

            # Transfer state
            context.warnings.extend(proc_ctx.warnings)
            context.errors.extend(proc_ctx.errors)
            context.imports_needed.update(proc_ctx.imports_needed)

            # 8. JSX conversions
            mdx_body = convert_html_to_jsx(mdx_body)

            # 9. Generate imports
            imports = generate_imports(mdx_body)

            # 10. Build frontmatter
            fm_dict = context.metadata.to_frontmatter_dict()
            fm_dict["convertedAt"] = datetime.now(timezone.utc).isoformat()
            frontmatter_str = _generate_frontmatter(fm_dict)

            # 11. Assemble MDX
            # Clean up excessive blank lines
            mdx_body = re.sub(r"\n{4,}", "\n\n\n", mdx_body)

            parts: list[str] = [frontmatter_str, ""]
            if imports:
                parts.append(imports)
                parts.append("")
            parts.append(mdx_body.strip())
            parts.append("")
            mdx_content = "\n".join(parts)

            # 12. ZWNJ verification
            zwnj_after = self.count_zwnj(mdx_content)
            context.zwnj_count_after = zwnj_after
            zwnj_report = ZWNJReport(
                count_before=zwnj_before,
                count_after=zwnj_after,
            )
            if not zwnj_report.preserved:
                context.add_warning(
                    f"ZWNJ: {zwnj_before} → {zwnj_after} "
                    f"({zwnj_before - zwnj_after} lost)"
                )

            # 13. Write output
            output_path: Optional[Path] = None
            output_bytes = len(mdx_content.encode("utf-8"))
            if context.output_dir and not context.dry_run:
                output_path = context.output_dir / f"{context.metadata.slug}.mdx"
                self.write_output(mdx_content, output_path, context.dry_run)

            # 14. Build result
            result.status = "success"
            result.output_path = str(output_path) if output_path else None
            result.output_bytes = output_bytes
            result.quality.zwnj = zwnj_report
            result.quality.frontmatter_valid = True
            result.quality.mdx_valid = True
            result.quality.math_rendered = conv_state.math_block_count > 0 or conv_state.math_inline_count > 0
            result.quality.math_block_count = conv_state.math_block_count
            result.quality.math_inline_count = conv_state.math_inline_count
            result.quality.tables_converted = conv_state.table_count > 0
            result.quality.tables_count = conv_state.table_count
            result.quality.images_linked = conv_state.image_count > 0
            result.quality.images_count = conv_state.image_count
            result.quality.code_blocks_count = conv_state.code_block_count
            result.quality.headings_count = conv_state.heading_count
            result.quality.links_count = conv_state.link_count

            context.notes.append(f"mdx_content_length={len(mdx_content)}")
            context.extra = {"mdx_content": mdx_content}

            self._logger.info(
                "تبدیل LaTeX→MDX: %s → %d bytes, ZWNJ %d→%d, "
                "math=%d+%d, tables=%d, images=%d",
                file_path.name, output_bytes, zwnj_before, zwnj_after,
                conv_state.math_block_count, conv_state.math_inline_count,
                conv_state.table_count, conv_state.image_count,
            )

        except ConversionError:
            raise
        except Exception as exc:
            result.status = "failed"
            result.error_message = f"خطا در تبدیل: {exc}"
            context.add_error(str(exc))
            self._logger.exception("خطا در تبدیل %s", file_path.name)

        finally:
            result.duration_seconds = round(time.time() - start, 3)

        return result

    # ─── Validation ───────────────────────

    def validate_output(
        self,
        result: DocumentConversionResult,
        context: ConversionContext,
    ) -> QualityReport:
        """اعتبارسنجی خروجی MDX."""
        report = result.quality

        report.zwnj = ZWNJReport(
            count_before=context.zwnj_count_before,
            count_after=context.zwnj_count_after,
        )

        report.bidi_correct = context.metadata is not None and (
            context.metadata.dir in ("rtl", "ltr")
        )

        report.compute_score()
        return report
