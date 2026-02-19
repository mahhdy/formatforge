"""
FormatForge - LaTeX Parser — S08-C1
تحلیل‌گر ساختار LaTeX

Parses LaTeX source into a structured document model:
  PreambleInfo  — packages, custom commands/envs, font settings, metadata
  LatexDocument — preamble + list[LatexNode] body
  LatexNode     — TextNode | CommandNode | EnvironmentNode | MathNode |
                  CommentNode | GroupNode

قواعد حیاتی:
- ZWNJ (U+200C) هرگز حذف نشود
- متن فارسی داخل \\lr{}, \\LTRfootnote{} و \\begin{latin} باید حفظ شود
- \\input / \\include به صورت بازگشایی فایل پشتیبانی می‌شوند
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

# ─── Constants ────────────────────────────────────
ZWNJ = "\u200c"

# Regex for a simple LaTeX command name: letters only (no digits after \)
_RE_CMD_NAME = re.compile(r"\\([a-zA-Z@]+)\*?")

# Detect any Persian / Arabic Unicode ranges
_RE_PERSIAN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]"
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data models / مدل‌های داده
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TextNode:
    """Plain text segment — متن ساده."""
    content: str


@dataclass
class CommentNode:
    """LaTeX % comment — کامنت."""
    text: str


@dataclass
class MathNode:
    """Math expression — فرمول ریاضی."""
    content: str
    display: bool = False    # True → $$…$$ / \[…\], False → $…$ / \(…\)


@dataclass
class GroupNode:
    """Braced group {…} — گروه."""
    children: list["LatexNode"] = field(default_factory=list)


@dataclass
class CommandNode:
    """LaTeX command like \textbf{…} — دستور LaTeX."""
    name: str                                   # e.g. "textbf"
    args: list[str] = field(default_factory=list)    # mandatory {}
    opts: list[str] = field(default_factory=list)    # optional []
    star: bool = False


@dataclass
class EnvironmentNode:
    """\\begin{name}…\\end{name} — محیط LaTeX."""
    name: str
    opts: list[str] = field(default_factory=list)    # optional []
    args: list[str] = field(default_factory=list)    # mandatory {}
    body: str = ""                              # raw body text
    children: list["LatexNode"] = field(default_factory=list)


# Union type for all node kinds
LatexNode = Union[TextNode, CommentNode, MathNode, GroupNode, CommandNode, EnvironmentNode]


@dataclass
class PackageInfo:
    """معلومات بسته LaTeX."""
    name: str
    options: list[str] = field(default_factory=list)


@dataclass
class FontConfig:
    """تنظیمات فونت."""
    text_font: Optional[str] = None
    latin_font: Optional[str] = None
    digit_font: Optional[str] = None
    math_font: Optional[str] = None
    is_xepersian: bool = False


@dataclass
class EnvInfo:
    """اطلاعات محیط سفارشی (\newenvironment)."""
    name: str
    begin_def: str = ""
    end_def: str = ""


@dataclass
class PreambleInfo:
    """
    اطلاعات استخراج‌شده از preamble LaTeX.
    Structured preamble data: packages, commands, metadata.
    """
    document_class: str = "article"
    document_class_options: list[str] = field(default_factory=list)
    packages: list[PackageInfo] = field(default_factory=list)
    custom_commands: dict[str, str] = field(default_factory=dict)
    custom_environments: dict[str, EnvInfo] = field(default_factory=dict)
    fonts: FontConfig = field(default_factory=FontConfig)
    title: str = ""
    author: str = ""
    date: str = ""
    abstract: str = ""
    # newtcbtheorem / newtcboxtheorem environments
    tcb_environments: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Raw preamble text (for fallback parsing)
    raw: str = ""


@dataclass
class LatexDocument:
    """
    سند LaTeX تحلیل‌شده.
    Parsed LaTeX document with preamble and body nodes.
    """
    preamble: PreambleInfo = field(default_factory=PreambleInfo)
    body: list[LatexNode] = field(default_factory=list)
    source_path: Optional[Path] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Low-level text helpers / توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _strip_braces(text: str) -> str:
    """Remove outermost braces if present: {foo} → foo."""
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text[1:-1].strip()
    return text


def _extract_options(text: str, pos: int) -> tuple[list[str], int]:
    """
    Extract optional [...] arguments starting at pos.
    Returns (list_of_opts, new_pos).
    """
    opts: list[str] = []
    while pos < len(text) and text[pos] == "[":
        end = text.find("]", pos)
        if end == -1:
            break
        opts.append(text[pos + 1:end].strip())
        pos = end + 1
        # skip whitespace
        while pos < len(text) and text[pos] in " \t":
            pos += 1
    return opts, pos


def _extract_arg(text: str, pos: int) -> tuple[str, int]:
    """
    Extract one mandatory {…} argument starting at pos.
    Handles nested braces.  Returns (content, new_pos).
    """
    while pos < len(text) and text[pos] in " \t\n":
        pos += 1
    if pos >= len(text) or text[pos] != "{":
        return "", pos
    depth = 0
    start = pos + 1
    i = pos
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    return text[start:], len(text)


def _extract_env_body(text: str, env_name: str, start: int) -> tuple[str, int]:
    """
    Extract the body of \\begin{env_name}...\\end{env_name} starting
    right after the opening \\begin{...} (at position *start*).
    Returns (body_text, position_after_end).
    Handles nested same-name environments.
    """
    depth = 1
    pos = start
    begin_pat = re.compile(
        r"\\begin\s*\{" + re.escape(env_name) + r"\}"
    )
    end_pat = re.compile(
        r"\\end\s*\{" + re.escape(env_name) + r"\}"
    )
    body_start = pos
    while pos < len(text):
        bm = begin_pat.search(text, pos)
        em = end_pat.search(text, pos)
        if em is None:
            # malformed — take rest
            return text[body_start:], len(text)
        if bm is not None and bm.start() < em.start():
            depth += 1
            pos = bm.end()
        else:
            depth -= 1
            if depth == 0:
                return text[body_start:em.start()], em.end()
            pos = em.end()
    return text[body_start:], len(text)


def has_persian(text: str) -> bool:
    """True if text contains Persian/Arabic characters."""
    return bool(_RE_PERSIAN.search(text))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Preamble Parser / تحلیل‌گر preamble
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Regex patterns for preamble extraction
_RE_DOCCLASS = re.compile(
    r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}"
)
_RE_USEPACKAGE = re.compile(
    r"\\usepackage\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}"
)
_RE_NEWCOMMAND = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand)\s*\{\\([^}]+)\}"
    r"\s*(?:\[\d+\])?\s*\{(.*?)\}",
    re.DOTALL,
)
_RE_NEWENVIRONMENT = re.compile(
    r"\\(?:newenvironment|renewenvironment)\s*\{([^}]+)\}"
    r"\s*(?:\[\d+\])?\s*\{(.*?)\}\s*\{(.*?)\}",
    re.DOTALL,
)
_RE_NEWTCBTHEOREM = re.compile(
    r"\\newtcbtheorem\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}\s*\{([^}]+)\}\s*\{(.*?)\}\s*\{([^}]*)\}",
    re.DOTALL,
)
_RE_NEWTCOLORBOX = re.compile(
    r"\\newtcolorbox\s*\{([^}]+)\}\s*(?:\[[^\]]*\]\s*)*\{(.*?)\}",
    re.DOTALL,
)
_RE_TITLE = re.compile(r"\\title\s*\{", re.DOTALL)
_RE_AUTHOR = re.compile(r"\\author\s*\{", re.DOTALL)
_RE_DATE = re.compile(r"\\date\s*\{", re.DOTALL)
_RE_SETTEXTFONT = re.compile(
    r"\\settextfont\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}"
)
_RE_SETLATINFONT = re.compile(
    r"\\setlatintextfont\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}"
)
_RE_SETDIGITFONT = re.compile(
    r"\\setdigitfont\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}"
)
_RE_HYPERSETUP = re.compile(r"\\hypersetup\s*\{(.*?)\}", re.DOTALL)


def _clean_tex(text: str) -> str:
    """Strip LaTeX formatting commands from text, keeping readable content."""
    # Remove comments
    text = re.sub(r"%.*", "", text)
    # Remove common formatting commands, keeping their argument
    text = re.sub(r"\\(?:textbf|textit|emph|textsc|textrm|texttt|text)\{([^}]*)\}", r"\1", text)
    # Remove color commands
    text = re.sub(r"\\(?:color|textcolor)\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:color|textcolor)\{[^}]*\}", "", text)
    # Remove size commands
    text = re.sub(r"\\(?:large|Large|LARGE|huge|Huge|small|tiny|normalsize|footnotesize)\s*", "", text)
    # Remove font switching commands
    text = re.sub(r"\\(?:bfseries|itshape|rmfamily|ttfamily|sffamily)\s*", "", text)
    # Remove rule commands
    text = re.sub(r"\\rule\{[^}]*\}\{[^}]*\}", "", text)
    # Remove \\[...] spacing
    text = re.sub(r"\\\\\s*(?:\[[^\]]*\])?", " ", text)
    # Remove \href{url}{text} → text
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    # Remove \url{...}
    text = re.sub(r"\\url\{([^}]*)\}", r"\1", text)
    # Remove \label{...}
    text = re.sub(r"\\label\{[^}]*\}", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_preamble(text: str) -> PreambleInfo:
    """
    تحلیل preamble LaTeX و استخراج اطلاعات ساختاریافته.
    Parse preamble text → PreambleInfo.
    """
    info = PreambleInfo(raw=text)

    # Document class
    m = _RE_DOCCLASS.search(text)
    if m:
        info.document_class = m.group(2).strip()
        if m.group(1):
            info.document_class_options = [
                o.strip() for o in m.group(1).split(",") if o.strip()
            ]

    # Packages
    for m in _RE_USEPACKAGE.finditer(text):
        opts = [o.strip() for o in m.group(1).split(",")] if m.group(1) else []
        # Multiple packages in one \usepackage{}
        pkg_names = [p.strip() for p in m.group(2).split(",") if p.strip()]
        for pkg in pkg_names:
            info.packages.append(PackageInfo(name=pkg, options=opts))

    # Detect xepersian
    info.fonts.is_xepersian = any(
        p.name == "xepersian" for p in info.packages
    )

    # Custom commands (\newcommand)
    for m in _RE_NEWCOMMAND.finditer(text):
        info.custom_commands[m.group(1)] = m.group(2)

    # Custom environments (\newenvironment)
    for m in _RE_NEWENVIRONMENT.finditer(text):
        env_name = m.group(1)
        info.custom_environments[env_name] = EnvInfo(
            name=env_name,
            begin_def=m.group(2),
            end_def=m.group(3),
        )

    # tcolorbox theorem environments
    for m in _RE_NEWTCBTHEOREM.finditer(text):
        env_name = m.group(1).strip()
        display_name = m.group(2).strip()
        style = m.group(3)
        label_prefix = m.group(4).strip()
        # Determine type from display name
        env_type = _classify_tcb_env(display_name, style)
        info.tcb_environments[env_name] = {
            "display_name": display_name,
            "type": env_type,
            "label_prefix": label_prefix,
            "style": style,
        }

    # plain newtcolorbox (warningbox, notebox, proofbox …)
    for m in _RE_NEWTCOLORBOX.finditer(text):
        env_name = m.group(1).strip()
        style = m.group(2)
        env_type = _classify_tcb_env(env_name, style)
        if env_name not in info.tcb_environments:
            info.tcb_environments[env_name] = {
                "display_name": env_name,
                "type": env_type,
                "label_prefix": "",
                "style": style,
            }

    # Font settings (XePersian)
    m = _RE_SETTEXTFONT.search(text)
    if m:
        info.fonts.text_font = m.group(1).strip()
    m = _RE_SETLATINFONT.search(text)
    if m:
        info.fonts.latin_font = m.group(1).strip()
    m = _RE_SETDIGITFONT.search(text)
    if m:
        info.fonts.digit_font = m.group(1).strip()

    # Metadata: title, author, date — use _extract_arg for proper nested brace handling
    m = _RE_TITLE.search(text)
    if m:
        # Position of opening { is m.end() - 1
        arg, _ = _extract_arg(text, m.end() - 1)
        info.title = _clean_tex(arg)
    m = _RE_AUTHOR.search(text)
    if m:
        arg, _ = _extract_arg(text, m.end() - 1)
        info.author = _clean_tex(arg)
    m = _RE_DATE.search(text)
    if m:
        arg, _ = _extract_arg(text, m.end() - 1)
        info.date = _clean_tex(arg)

    # hypersetup pdftitle / pdfauthor override
    m = _RE_HYPERSETUP.search(text)
    if m:
        hs = m.group(1)
        pm = re.search(r"pdftitle\s*=\s*\{([^}]*)\}", hs)
        if pm and not info.title:
            info.title = pm.group(1).strip()
        pm = re.search(r"pdfauthor\s*=\s*\{([^}]*)\}", hs)
        if pm and not info.author:
            info.author = pm.group(1).strip()

    return info


def _classify_tcb_env(name: str, style: str) -> str:
    """
    Determine semantic type of a tcolorbox environment from its name/style.
    Returns one of: theorem, definition, proof, example, warning, note, box
    """
    name_lower = name.lower()
    style_lower = style.lower()

    if any(kw in name_lower for kw in ("theorem", "thm", "قضیه")):
        return "theorem"
    if any(kw in name_lower for kw in ("definition", "def", "تعریف")):
        return "definition"
    if any(kw in name_lower for kw in ("proof", "proofbox", "اثبات")):
        return "proof"
    if any(kw in name_lower for kw in ("example", "exm", "مثال")):
        return "example"
    if any(kw in name_lower for kw in ("warning", "warn", "هشدار")):
        return "warning"
    if any(kw in name_lower for kw in ("note", "نکته", "notebox")):
        return "note"
    # Fallback: inspect style colors
    if "accenTorange" in style_lower or "fb8c00" in style_lower:
        return "warning"
    if "primaryblue" in style_lower or "1a73e8" in style_lower:
        return "note"
    return "box"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Body Parser / تحلیل‌گر body
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Math delimiters (ordered longest-first to avoid partial matches)
_MATH_DISPLAY_OPEN = [r"\[", "$$"]
_MATH_DISPLAY_CLOSE = {r"\[": r"\]", "$$": "$$"}
_MATH_INLINE_OPEN = [r"\(", "$"]
_MATH_INLINE_CLOSE = {r"\(": r"\)", "$": "$"}

# Well-known environments that should be parsed as EnvironmentNode
_KNOWN_ENVS: frozenset[str] = frozenset({
    # Theorem-like
    "theorem", "definition", "proof", "example", "lemma", "corollary",
    "proposition", "remark", "claim", "conjecture",
    # Lists
    "itemize", "enumerate", "description",
    # Math
    "equation", "equation*", "align", "align*", "gather", "gather*",
    "multline", "multline*", "cases", "pmatrix", "bmatrix", "vmatrix",
    "split", "alignat", "alignat*", "eqnarray", "eqnarray*",
    # Tables
    "tabular", "tabularx", "longtable", "array",
    "table", "table*", "sidewaystable",
    # Floats
    "figure", "figure*", "wrapfigure", "subfigure",
    # Code
    "lstlisting", "minted", "verbatim",
    # Algorithm
    "algorithm", "algorithm2e",
    # Quotes
    "quote", "quotation", "verse",
    # Structural
    "abstract", "titlepage", "minipage", "center",
    # Latin text
    "latin",
    # TikZ
    "tikzpicture", "pgfpicture",
    # tcolorbox
    "tcolorbox",
    # Custom (will be extended from preamble)
    "notebox", "warningbox", "proofbox",
    # filecontents
    "filecontents", "filecontents*",
    # document
    "document",
})


def parse_body(text: str, custom_envs: Optional[set[str]] = None) -> list[LatexNode]:
    """
    تحلیل body LaTeX → list[LatexNode].
    Parse body text (after \\begin{document}) into a list of LatexNode.

    Handles:
    - Math: $…$, $$…$$, \\(…\\), \\[…\\], equation env
    - Commands: \\cmd[opt]{arg}…
    - Environments: \\begin{name}…\\end{name}
    - Comments: %…
    - Plain text
    """
    known = set(_KNOWN_ENVS)
    if custom_envs:
        known |= custom_envs

    nodes: list[LatexNode] = []
    pos = 0
    text_buf: list[str] = []

    def flush_text() -> None:
        if text_buf:
            content = "".join(text_buf)
            if content:
                nodes.append(TextNode(content))
            text_buf.clear()

    while pos < len(text):
        ch = text[pos]

        # ── Comment ─────────────────────────────
        if ch == "%" and (pos == 0 or text[pos - 1] != "\\"):
            flush_text()
            end = text.find("\n", pos)
            if end == -1:
                end = len(text)
            nodes.append(CommentNode(text[pos + 1:end]))
            pos = end + 1
            continue

        # ── Display math: $$ or \[ ───────────────
        matched_display = False
        for open_delim in _MATH_DISPLAY_OPEN:
            if text[pos:pos + len(open_delim)] == open_delim:
                close_delim = _MATH_DISPLAY_CLOSE[open_delim]
                end_pos = text.find(close_delim, pos + len(open_delim))
                if end_pos != -1:
                    flush_text()
                    math_content = text[pos + len(open_delim):end_pos]
                    nodes.append(MathNode(content=math_content, display=True))
                    pos = end_pos + len(close_delim)
                    matched_display = True
                    break
        if matched_display:
            continue

        # ── Inline math: $ or \( ────────────────
        if ch == "$" and not text[pos:pos + 2] == "$$":
            # inline $…$
            end_pos = _find_matching_dollar(text, pos + 1)
            if end_pos != -1:
                flush_text()
                nodes.append(MathNode(content=text[pos + 1:end_pos], display=False))
                pos = end_pos + 1
                continue
        if text[pos:pos + 2] == r"\(":
            end_pos = text.find(r"\)", pos + 2)
            if end_pos != -1:
                flush_text()
                nodes.append(MathNode(content=text[pos + 2:end_pos], display=False))
                pos = end_pos + 2
                continue

        # ── Backslash: command or environment ───
        if ch == "\\":
            # Check \begin{...}
            benv = re.match(r"\\begin\s*\{([^}]+)\}", text[pos:])
            if benv:
                env_name = benv.group(1).strip()
                after_begin = pos + benv.end()
                # Extract optional and mandatory args after \begin{name}
                opts, after_begin = _extract_options(text, after_begin)
                args: list[str] = []
                tmp = after_begin
                while tmp < len(text) and text[tmp] == "{":
                    arg, tmp = _extract_arg(text, tmp)
                    args.append(arg)
                    while tmp < len(text) and text[tmp] in " \t":
                        tmp += 1
                after_begin = tmp
                # Extract body
                body, after_end = _extract_env_body(text, env_name, after_begin)
                flush_text()
                env_node = EnvironmentNode(
                    name=env_name,
                    opts=opts,
                    args=args,
                    body=body,
                )
                # Recursively parse body for known envs (not raw code/math)
                if env_name not in (
                    "lstlisting", "minted", "verbatim",
                    "tikzpicture", "pgfpicture",
                    "filecontents", "filecontents*",
                ):
                    env_node.children = parse_body(body, custom_envs)
                nodes.append(env_node)
                pos = after_end
                continue

            # Regular command
            cmd_match = re.match(r"\\([a-zA-Z@]+)(\*?)", text[pos:])
            if cmd_match:
                cmd_name = cmd_match.group(1)
                star = bool(cmd_match.group(2))
                after_cmd = pos + cmd_match.end()
                # Skip whitespace before args
                while after_cmd < len(text) and text[after_cmd] in " \t\n":
                    after_cmd += 1
                opts2, after_cmd = _extract_options(text, after_cmd)
                args2: list[str] = []
                # Read up to 3 mandatory args
                for _ in range(3):
                    if after_cmd < len(text) and text[after_cmd] == "{":
                        arg, after_cmd = _extract_arg(text, after_cmd)
                        args2.append(arg)
                        while after_cmd < len(text) and text[after_cmd] in " \t":
                            after_cmd += 1
                    else:
                        break
                flush_text()
                nodes.append(CommandNode(
                    name=cmd_name,
                    args=args2,
                    opts=opts2,
                    star=star,
                ))
                pos = after_cmd
                continue
            else:
                # Single non-letter command like \\, \_, \{, \}, \$
                if pos + 1 < len(text):
                    flush_text()
                    nodes.append(CommandNode(name=text[pos + 1], args=[], opts=[]))
                    pos += 2
                    continue

        # ── Regular character ────────────────────
        text_buf.append(ch)
        pos += 1

    flush_text()
    return nodes


def _find_matching_dollar(text: str, start: int) -> int:
    """
    Find the closing $ for inline math starting at *start*.
    Returns position of closing $ or -1.
    Skips escaped \\$.
    """
    pos = start
    while pos < len(text):
        if text[pos] == "$":
            if pos == 0 or text[pos - 1] != "\\":
                return pos
        pos += 1
    return -1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Macro Expansion / بازگشایی ماکروها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def expand_macros(
    nodes: list[LatexNode],
    commands: dict[str, str],
) -> list[LatexNode]:
    """
    بازگشایی \\newcommand‌ها در درخت گره‌ها.
    Expand custom commands defined in \\newcommand.
    Simple single-pass text substitution on CommandNode names.
    """
    result: list[LatexNode] = []
    for node in nodes:
        if isinstance(node, CommandNode) and node.name in commands:
            # Replace with TextNode of the expansion (simplified)
            expansion = commands[node.name]
            result.append(TextNode(expansion))
        elif isinstance(node, EnvironmentNode):
            expanded_children = expand_macros(node.children, commands)
            new_node = EnvironmentNode(
                name=node.name,
                opts=node.opts,
                args=node.args,
                body=node.body,
                children=expanded_children,
            )
            result.append(new_node)
        else:
            result.append(node)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Input Resolution / بازگشایی \input
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def resolve_inputs(
    nodes: list[LatexNode],
    base_dir: Path,
    _depth: int = 0,
) -> list[LatexNode]:
    """
    بازگشایی \\input{file} و \\include{file}.
    Replace \\input / \\include commands with parsed content of the file.
    Max recursion depth: 10.
    """
    if _depth > 10:
        return nodes

    result: list[LatexNode] = []
    for node in nodes:
        if isinstance(node, CommandNode) and node.name in ("input", "include"):
            if node.args:
                fname = node.args[0].strip()
                if not fname.endswith(".tex"):
                    fname += ".tex"
                fpath = base_dir / fname
                if fpath.exists():
                    try:
                        content = fpath.read_text(encoding="utf-8")
                        child_nodes = parse_body(content)
                        child_nodes = resolve_inputs(child_nodes, base_dir, _depth + 1)
                        result.extend(child_nodes)
                        continue
                    except OSError:
                        pass
            result.append(node)
        elif isinstance(node, EnvironmentNode):
            new_children = resolve_inputs(node.children, base_dir, _depth)
            new_node = EnvironmentNode(
                name=node.name,
                opts=node.opts,
                args=node.args,
                body=node.body,
                children=new_children,
            )
            result.append(new_node)
        else:
            result.append(node)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Top-level Parser / تحلیل‌گر اصلی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Regex to split at \begin{document}
_RE_BEGIN_DOCUMENT = re.compile(r"\\begin\s*\{document\}", re.IGNORECASE)
_RE_END_DOCUMENT = re.compile(r"\\end\s*\{document\}", re.IGNORECASE)

# Structural markers to skip in body (frontmatter commands)
_SKIP_COMMANDS = frozenset({
    "frontmatter", "mainmatter", "backmatter",
    "maketitle", "tableofcontents",
    "listoffigures", "listoftables",
})


class LatexParser:
    """
    تحلیل‌گر اصلی LaTeX.
    Main parser: takes raw LaTeX text → LatexDocument.

    Usage:
        parser = LatexParser()
        doc = parser.parse(content)
        doc = parser.parse_file(path)
    """

    def parse(self, content: str, source_path: Optional[Path] = None) -> LatexDocument:
        """
        تحلیل متن LaTeX.
        Parse full LaTeX source text into LatexDocument.
        """
        # Split preamble / body
        bm = _RE_BEGIN_DOCUMENT.search(content)
        if bm:
            preamble_text = content[:bm.start()]
            after_begin = content[bm.end():]
        else:
            # No \begin{document} — treat entire text as body
            preamble_text = ""
            after_begin = content

        # Trim \end{document}
        em = _RE_END_DOCUMENT.search(after_begin)
        body_text = after_begin[:em.start()] if em else after_begin

        preamble_info = parse_preamble(preamble_text)

        # Extract abstract from body
        abs_match = re.search(
            r"\\begin\s*\{abstract\}(.*?)\\end\s*\{abstract\}",
            body_text, re.DOTALL
        )
        if abs_match:
            preamble_info.abstract = _clean_tex(abs_match.group(1))

        # Collect custom env names from preamble
        custom_env_names = (
            set(preamble_info.custom_environments.keys())
            | set(preamble_info.tcb_environments.keys())
        )

        body_nodes = parse_body(body_text, custom_envs=custom_env_names)

        # Filter skip commands at top level
        body_nodes = [
            n for n in body_nodes
            if not (isinstance(n, CommandNode) and n.name in _SKIP_COMMANDS)
        ]

        doc = LatexDocument(
            preamble=preamble_info,
            body=body_nodes,
            source_path=source_path,
        )
        return doc

    def parse_file(self, path: Path) -> LatexDocument:
        """
        خواندن و تحلیل فایل LaTeX.
        Read a .tex file and parse it.
        """
        content = path.read_text(encoding="utf-8")
        return self.parse(content, source_path=path)

    def parse_with_inputs(self, path: Path) -> LatexDocument:
        """
        تحلیل فایل LaTeX با بازگشایی \\input/\\include.
        Parse file and recursively resolve \\input{file} references.
        """
        doc = self.parse_file(path)
        doc.body = resolve_inputs(doc.body, base_dir=path.parent)
        doc.body = expand_macros(doc.body, doc.preamble.custom_commands)
        return doc
