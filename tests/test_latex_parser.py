"""
تست‌های تحلیل‌گر LaTeX — S08-C1
Tests for formatforge/core/converters/latex_parser.py

Coverage:
- PreambleInfo parsing (documentclass, packages, commands, envs, fonts, metadata)
- LatexNode types: TextNode, CommentNode, MathNode, CommandNode, EnvironmentNode
- parse_preamble()
- parse_body()
- expand_macros()
- resolve_inputs()
- LatexParser.parse() / parse_file() / parse_with_inputs()
- ZWNJ preservation
- Persian content detection
- Real sample-book.tex file (if available)
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from formatforge.core.converters.latex_parser import (
    ZWNJ,
    CommandNode,
    CommentNode,
    EnvInfo,
    EnvironmentNode,
    FontConfig,
    GroupNode,
    LatexDocument,
    LatexParser,
    MathNode,
    PackageInfo,
    PreambleInfo,
    TextNode,
    _clean_tex,
    _classify_tcb_env,
    _extract_arg,
    _extract_env_body,
    _extract_options,
    _strip_braces,
    expand_macros,
    has_persian,
    parse_body,
    parse_preamble,
    resolve_inputs,
)

# ─── Path to real test file ──────────────────
_SAMPLE_TEX = Path(__file__).parent / "test_files" / "sample-book.tex"
_HAS_SAMPLE = _SAMPLE_TEX.exists()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper fixtures / fixtures کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SIMPLE_TEX = r"""
\documentclass[12pt,a4paper]{book}
\usepackage[dvipsnames]{xcolor}
\usepackage{amsmath,amsthm}
\usepackage{fontspec}
\usepackage[extrafootnotefeatures]{xepersian}
\settextfont[Scale=1.0]{IRLotus}
\setlatintextfont[Scale=0.95]{TeX Gyre Termes}
\newcommand{\myterm}[1]{\textbf{#1}}
\newenvironment{mybox}{\begin{tcolorbox}}{\end{tcolorbox}}
\newtcbtheorem[number within=chapter]{theorem}{قضیه}{enhanced,colback=blue!10}{thm}
\newtcbtheorem[number within=chapter]{definition}{تعریف}{enhanced,colback=green!10}{def}
\newtcolorbox{warningbox}[1][]{enhanced,colback=orange!10,title={#1}}
\title{عنوان آزمایشی}
\author{نویسنده آزمایشی}
\date{2025-01-15}
\begin{document}
\chapter{فصل اول}
Hello \textbf{World}.
$E = mc^2$
\end{document}
"""

MATH_TEX = r"""
\begin{document}
Inline: $a + b = c$ and $x^2$.
Display: $$\int_0^\infty e^{-x}\,dx = 1$$
Env: \[
  \sum_{n=1}^\infty \frac{1}{n^2} = \frac{\pi^2}{6}
\]
Paren: \(f(x) = x^2\)
\end{document}
"""

PERSIAN_TEX = rf"""
\begin{{document}}
این یک متن \textbf{{فارسی}} با نیم{ZWNJ}فاصله است.
\chapter{{فصل{ZWNJ}اول}}
\section{{بخش{ZWNJ}اول}}
\end{{document}}
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestHelpers — توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHelpers:
    """تست‌های توابع کمکی."""

    def test_strip_braces_basic(self):
        assert _strip_braces("{foo}") == "foo"

    def test_strip_braces_whitespace(self):
        assert _strip_braces("  { bar }  ") == "bar"

    def test_strip_braces_no_braces(self):
        assert _strip_braces("foo") == "foo"

    def test_extract_options_empty(self):
        opts, pos = _extract_options("no brackets here", 0)
        assert opts == []
        assert pos == 0

    def test_extract_options_single(self):
        opts, pos = _extract_options("[opt1]rest", 0)
        assert opts == ["opt1"]
        assert pos == 6

    def test_extract_options_multiple(self):
        opts, pos = _extract_options("[a][b][c]rest", 0)
        assert opts == ["a", "b", "c"]

    def test_extract_arg_basic(self):
        arg, pos = _extract_arg("{hello}rest", 0)
        assert arg == "hello"
        assert pos == 7

    def test_extract_arg_nested(self):
        arg, pos = _extract_arg("{outer {inner} end}", 0)
        assert arg == "outer {inner} end"

    def test_extract_arg_no_brace(self):
        arg, pos = _extract_arg("nope", 0)
        assert arg == ""
        assert pos == 0

    def test_extract_env_body_simple(self):
        text = r"content here\end{theorem}"
        body, end = _extract_env_body(text, "theorem", 0)
        assert body == "content here"
        assert text[end:] == ""

    def test_extract_env_body_nested(self):
        text = r"outer \begin{theorem} inner \end{theorem} outer\end{theorem}"
        body, end = _extract_env_body(text, "theorem", 0)
        assert r"\begin{theorem}" in body
        assert r"\end{theorem}" in body

    def test_clean_tex_basic(self):
        result = _clean_tex(r"\textbf{hello}")
        assert result == "hello"

    def test_clean_tex_color(self):
        result = _clean_tex(r"\textcolor{blue}{text}")
        assert "blue" not in result
        assert "text" in result

    def test_clean_tex_rule(self):
        result = _clean_tex(r"\rule{\textwidth}{2pt}")
        assert "rule" not in result

    def test_clean_tex_href(self):
        result = _clean_tex(r"\href{https://example.com}{click here}")
        assert "click here" in result
        assert "https" not in result

    def test_has_persian_true(self):
        assert has_persian("متن فارسی")

    def test_has_persian_false(self):
        assert not has_persian("hello world")

    def test_has_persian_mixed(self):
        assert has_persian("Hello سلام World")

    def test_classify_tcb_theorem(self):
        assert _classify_tcb_env("theorem", "") == "theorem"

    def test_classify_tcb_definition(self):
        assert _classify_tcb_env("mydef", "") == "definition"

    def test_classify_tcb_warning(self):
        assert _classify_tcb_env("warningbox", "") == "warning"

    def test_classify_tcb_note(self):
        assert _classify_tcb_env("notebox", "") == "note"

    def test_classify_tcb_proof(self):
        assert _classify_tcb_env("proofbox", "") == "proof"

    def test_classify_tcb_example(self):
        assert _classify_tcb_env("exm", "") == "example"

    def test_classify_tcb_persian_theorem(self):
        assert _classify_tcb_env("قضیه", "") == "theorem"

    def test_classify_tcb_fallback(self):
        result = _classify_tcb_env("mybox", "")
        assert result == "box"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestPreambleParsing — تحلیل preamble
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPreambleParsing:
    """تست‌های parse_preamble()."""

    @pytest.fixture
    def info(self) -> PreambleInfo:
        preamble_text = SIMPLE_TEX.split(r"\begin{document}")[0]
        return parse_preamble(preamble_text)

    def test_document_class(self, info):
        assert info.document_class == "book"

    def test_document_class_options(self, info):
        assert "12pt" in info.document_class_options
        assert "a4paper" in info.document_class_options

    def test_packages_detected(self, info):
        pkg_names = [p.name for p in info.packages]
        assert "amsmath" in pkg_names
        assert "xepersian" in pkg_names

    def test_package_options(self, info):
        xcolor = next(p for p in info.packages if p.name == "xcolor")
        assert "dvipsnames" in xcolor.options

    def test_xepersian_detected(self, info):
        assert info.fonts.is_xepersian is True

    def test_text_font_extracted(self, info):
        assert info.fonts.text_font == "IRLotus"

    def test_latin_font_extracted(self, info):
        assert info.fonts.latin_font == "TeX Gyre Termes"

    def test_title_extracted(self, info):
        assert "عنوان آزمایشی" in info.title

    def test_author_extracted(self, info):
        assert "نویسنده آزمایشی" in info.author

    def test_date_extracted(self, info):
        assert "2025" in info.date

    def test_custom_command(self, info):
        assert "myterm" in info.custom_commands

    def test_custom_environment(self, info):
        assert "mybox" in info.custom_environments

    def test_tcb_theorem_detected(self, info):
        assert "theorem" in info.tcb_environments
        assert info.tcb_environments["theorem"]["type"] == "theorem"

    def test_tcb_definition_detected(self, info):
        assert "definition" in info.tcb_environments
        assert info.tcb_environments["definition"]["type"] == "definition"

    def test_tcb_warningbox_detected(self, info):
        assert "warningbox" in info.tcb_environments
        assert info.tcb_environments["warningbox"]["type"] == "warning"

    def test_tcb_label_prefix(self, info):
        assert info.tcb_environments["theorem"]["label_prefix"] == "thm"

    def test_raw_stored(self, info):
        assert len(info.raw) > 0

    def test_empty_preamble(self):
        info = parse_preamble("")
        assert info.document_class == "article"
        assert info.packages == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestBodyParsing — تحلیل body
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBodyParsing:
    """تست‌های parse_body()."""

    def test_text_node(self):
        nodes = parse_body("Hello World")
        text_nodes = [n for n in nodes if isinstance(n, TextNode)]
        combined = "".join(n.content for n in text_nodes)
        assert "Hello" in combined

    def test_comment_node(self):
        nodes = parse_body("% this is a comment\nhello")
        comments = [n for n in nodes if isinstance(n, CommentNode)]
        assert any("this is a comment" in c.text for c in comments)

    def test_inline_math_dollar(self):
        nodes = parse_body("text $a+b$ end")
        math = [n for n in nodes if isinstance(n, MathNode)]
        assert len(math) == 1
        assert math[0].display is False
        assert "a+b" in math[0].content

    def test_display_math_dollar(self):
        nodes = parse_body("$$E=mc^2$$")
        math = [n for n in nodes if isinstance(n, MathNode)]
        assert any(m.display and "E=mc^2" in m.content for m in math)

    def test_display_math_bracket(self):
        nodes = parse_body(r"\[ x^2 \]")
        math = [n for n in nodes if isinstance(n, MathNode)]
        assert any(m.display for m in math)

    def test_inline_math_paren(self):
        nodes = parse_body(r"\(f(x)\)")
        math = [n for n in nodes if isinstance(n, MathNode)]
        assert len(math) == 1
        assert not math[0].display

    def test_command_node(self):
        nodes = parse_body(r"\textbf{hello}")
        cmds = [n for n in nodes if isinstance(n, CommandNode)]
        assert any(c.name == "textbf" for c in cmds)

    def test_command_with_opt(self):
        nodes = parse_body(r"\section[short]{Long Title}")
        cmds = [n for n in nodes if isinstance(n, CommandNode)]
        sec = next((c for c in cmds if c.name == "section"), None)
        assert sec is not None
        assert "short" in sec.opts
        assert "Long Title" in sec.args

    def test_environment_node(self):
        nodes = parse_body(r"\begin{itemize}\item one\end{itemize}")
        envs = [n for n in nodes if isinstance(n, EnvironmentNode)]
        assert any(e.name == "itemize" for e in envs)

    def test_environment_body_captured(self):
        nodes = parse_body(r"\begin{theorem}content here\end{theorem}")
        envs = [n for n in nodes if isinstance(n, EnvironmentNode)]
        thm = next((e for e in envs if e.name == "theorem"), None)
        assert thm is not None
        assert "content here" in thm.body

    def test_nested_environment(self):
        tex = r"\begin{itemize}\item \begin{equation}x=1\end{equation}\end{itemize}"
        nodes = parse_body(tex)
        envs = [n for n in nodes if isinstance(n, EnvironmentNode)]
        assert any(e.name == "itemize" for e in envs)

    def test_environment_with_args(self):
        nodes = parse_body(r"\begin{theorem}{My Theorem}{label1}content\end{theorem}")
        envs = [n for n in nodes if isinstance(n, EnvironmentNode)]
        thm = next((e for e in envs if e.name == "theorem"), None)
        assert thm is not None
        assert "My Theorem" in thm.args

    def test_multiple_math_nodes(self):
        nodes = parse_body(MATH_TEX.split(r"\begin{document}")[1].split(r"\end{document}")[0])
        math_nodes = [n for n in nodes if isinstance(n, MathNode)]
        assert len(math_nodes) >= 3

    def test_empty_body(self):
        nodes = parse_body("")
        assert nodes == []

    def test_only_whitespace(self):
        nodes = parse_body("   \n\n  ")
        text = [n for n in nodes if isinstance(n, TextNode)]
        # May produce empty text node, but should not crash
        assert isinstance(nodes, list)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestZWNJPreservation — حفظ نیم‌فاصله
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestZWNJPreservation:
    """تست‌های حفظ نیم‌فاصله در تحلیل‌گر."""

    def test_zwnj_in_text_node(self):
        text = f"متن\u200cبا\u200cنیم‌فاصله"
        nodes = parse_body(text)
        text_content = "".join(
            n.content for n in nodes if isinstance(n, TextNode)
        )
        assert ZWNJ in text_content

    def test_zwnj_count_preserved(self):
        text = f"اول\u200cدوم\u200cسوم\u200cچهارم"
        nodes = parse_body(text)
        text_content = "".join(
            n.content for n in nodes if isinstance(n, TextNode)
        )
        assert text_content.count(ZWNJ) == 3

    def test_zwnj_in_command_arg(self):
        text = f"\\textbf{{برنامه\u200cنویسی}}"
        nodes = parse_body(text)
        cmds = [n for n in nodes if isinstance(n, CommandNode)]
        assert any(ZWNJ in " ".join(c.args) for c in cmds)

    def test_zwnj_in_preamble_title(self):
        preamble = f"\\title{{برنامه\u200cنویسی}}"
        info = parse_preamble(preamble)
        assert ZWNJ in info.title

    def test_zwnj_in_environment_body(self):
        text = f"\\begin{{theorem}}متن\u200cفارسی\\end{{theorem}}"
        nodes = parse_body(text)
        envs = [n for n in nodes if isinstance(n, EnvironmentNode)]
        assert any(ZWNJ in e.body for e in envs)

    def test_zwnj_in_chapter_title(self):
        text = f"\\chapter{{فصل\u200cاول}}"
        nodes = parse_body(text)
        cmds = [n for n in nodes if isinstance(n, CommandNode)]
        chapter = next((c for c in cmds if c.name == "chapter"), None)
        assert chapter is not None
        assert ZWNJ in chapter.args[0]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestExpandMacros — بازگشایی ماکروها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestExpandMacros:
    """تست‌های expand_macros()."""

    def test_basic_expansion(self):
        commands = {"myterm": "term"}
        nodes = [CommandNode(name="myterm", args=["hello"])]
        result = expand_macros(nodes, commands)
        assert any(isinstance(n, TextNode) and "term" in n.content for n in result)

    def test_unknown_command_unchanged(self):
        commands = {}
        node = CommandNode(name="textbf", args=["hello"])
        result = expand_macros([node], commands)
        assert any(isinstance(n, CommandNode) and n.name == "textbf" for n in result)

    def test_expansion_in_environment(self):
        commands = {"myterm": "replaced"}
        env = EnvironmentNode(
            name="theorem",
            body="",
            children=[CommandNode(name="myterm", args=[])],
        )
        result = expand_macros([env], commands)
        assert isinstance(result[0], EnvironmentNode)
        assert any(isinstance(c, TextNode) for c in result[0].children)

    def test_empty_nodes(self):
        result = expand_macros([], {"foo": "bar"})
        assert result == []

    def test_text_node_unchanged(self):
        nodes = [TextNode("hello")]
        result = expand_macros(nodes, {"foo": "bar"})
        assert result == nodes


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestResolveInputs — بازگشایی \input
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestResolveInputs:
    """تست‌های resolve_inputs()."""

    def test_resolve_existing_file(self, tmp_path):
        # Create a subfile
        sub = tmp_path / "sub.tex"
        sub.write_text("Sub content here", encoding="utf-8")
        nodes = [CommandNode(name="input", args=["sub"])]
        result = resolve_inputs(nodes, base_dir=tmp_path)
        text = "".join(
            n.content for n in result if isinstance(n, TextNode)
        )
        assert "Sub content" in text

    def test_missing_file_kept(self, tmp_path):
        nodes = [CommandNode(name="input", args=["nonexistent"])]
        result = resolve_inputs(nodes, base_dir=tmp_path)
        # Should return original node (not crash)
        assert len(result) == 1

    def test_include_command(self, tmp_path):
        sub = tmp_path / "chapter.tex"
        sub.write_text(r"\section{Hello}", encoding="utf-8")
        nodes = [CommandNode(name="include", args=["chapter"])]
        result = resolve_inputs(nodes, base_dir=tmp_path)
        cmds = [n for n in result if isinstance(n, CommandNode)]
        assert any(c.name == "section" for c in cmds)

    def test_no_input_commands(self, tmp_path):
        nodes = [TextNode("hello"), CommandNode(name="textbf", args=["world"])]
        result = resolve_inputs(nodes, base_dir=tmp_path)
        assert len(result) == 2

    def test_zwnj_preserved_in_included_file(self, tmp_path):
        sub = tmp_path / "fa.tex"
        sub.write_text(f"متن\u200cفارسی", encoding="utf-8")
        nodes = [CommandNode(name="input", args=["fa"])]
        result = resolve_inputs(nodes, base_dir=tmp_path)
        text = "".join(
            n.content for n in result if isinstance(n, TextNode)
        )
        assert ZWNJ in text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestLatexParser — تحلیل‌گر اصلی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLatexParser:
    """تست‌های LatexParser.parse()."""

    @pytest.fixture
    def parser(self):
        return LatexParser()

    def test_parse_returns_document(self, parser):
        doc = parser.parse(SIMPLE_TEX)
        assert isinstance(doc, LatexDocument)

    def test_parse_preamble_info(self, parser):
        doc = parser.parse(SIMPLE_TEX)
        assert doc.preamble.document_class == "book"

    def test_parse_body_not_empty(self, parser):
        doc = parser.parse(SIMPLE_TEX)
        assert len(doc.body) > 0

    def test_parse_chapter_command(self, parser):
        doc = parser.parse(SIMPLE_TEX)
        cmds = [n for n in doc.body if isinstance(n, CommandNode)]
        assert any(c.name == "chapter" for c in cmds)

    def test_parse_math_node(self, parser):
        doc = parser.parse(SIMPLE_TEX)
        math = [n for n in doc.body if isinstance(n, MathNode)]
        assert len(math) >= 1

    def test_parse_without_begin_document(self, parser):
        # Should not crash
        doc = parser.parse(r"\chapter{hello} $x+y$")
        assert len(doc.body) > 0

    def test_parse_skips_maketitle(self, parser):
        tex = r"\begin{document}\maketitle text\end{document}"
        doc = parser.parse(tex)
        cmds = [n for n in doc.body if isinstance(n, CommandNode)]
        assert not any(c.name == "maketitle" for c in cmds)

    def test_parse_skips_tableofcontents(self, parser):
        tex = r"\begin{document}\tableofcontents text\end{document}"
        doc = parser.parse(tex)
        cmds = [n for n in doc.body if isinstance(n, CommandNode)]
        assert not any(c.name == "tableofcontents" for c in cmds)

    def test_parse_file(self, parser, tmp_path):
        fpath = tmp_path / "test.tex"
        fpath.write_text(SIMPLE_TEX, encoding="utf-8")
        doc = parser.parse_file(fpath)
        assert doc.source_path == fpath
        assert doc.preamble.document_class == "book"

    def test_parse_custom_envs_from_preamble(self, parser):
        """Custom newtcbtheorem envs recognized in body."""
        tex = SIMPLE_TEX.replace(
            r"\chapter{فصل اول}",
            r"\chapter{فصل اول}" + "\n" + r"\begin{theorem}{My Thm}{t1}content\end{theorem}"
        )
        doc = parser.parse(tex)
        envs = [n for n in doc.body if isinstance(n, EnvironmentNode)]
        assert any(e.name == "theorem" for e in envs)

    def test_parse_abstract_extracted(self, parser):
        tex = r"""
        \begin{document}
        \begin{abstract}
        این چکیده آزمایشی است.
        \end{abstract}
        \chapter{فصل اول}
        \end{document}
        """
        doc = parser.parse(tex)
        assert "چکیده" in doc.preamble.abstract

    def test_parse_with_inputs(self, parser, tmp_path):
        """parse_with_inputs resolves \\input files."""
        sub = tmp_path / "chapter1.tex"
        sub.write_text(r"\section{Sub Section}", encoding="utf-8")
        main = tmp_path / "main.tex"
        main.write_text(
            r"\documentclass{book}" "\n"
            r"\begin{document}" "\n"
            r"\input{chapter1}" "\n"
            r"\end{document}",
            encoding="utf-8",
        )
        doc = parser.parse_with_inputs(main)
        cmds = [n for n in doc.body if isinstance(n, CommandNode)]
        assert any(c.name == "section" for c in cmds)

    def test_zwnj_preserved_through_parser(self, parser):
        doc = parser.parse(PERSIAN_TEX)
        all_text = []
        for node in doc.body:
            if isinstance(node, TextNode):
                all_text.append(node.content)
            elif isinstance(node, CommandNode) and node.args:
                all_text.extend(node.args)
        combined = " ".join(all_text)
        assert ZWNJ in combined

    def test_parse_tcolorbox_envs_in_body(self, parser):
        """Environments defined via newtcolorbox are recognized."""
        tex = SIMPLE_TEX.replace(
            r"\chapter{فصل اول}",
            r"\chapter{فصل اول}" + "\n"
            r"\begin{warningbox}[هشدار]متن هشدار\end{warningbox}"
        )
        doc = parser.parse(tex)
        envs = [n for n in doc.body if isinstance(n, EnvironmentNode)]
        assert any(e.name == "warningbox" for e in envs)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestNodeTypes — تست انواع گره
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestNodeTypes:
    """تست انواع گره LatexNode."""

    def test_text_node_creation(self):
        n = TextNode("hello")
        assert n.content == "hello"

    def test_comment_node_creation(self):
        n = CommentNode("a comment")
        assert n.text == "a comment"

    def test_math_node_display(self):
        n = MathNode(content="x^2", display=True)
        assert n.display is True

    def test_math_node_inline(self):
        n = MathNode(content="x^2", display=False)
        assert n.display is False

    def test_command_node_creation(self):
        n = CommandNode(name="textbf", args=["hello"], opts=[])
        assert n.name == "textbf"
        assert n.args == ["hello"]

    def test_environment_node_creation(self):
        n = EnvironmentNode(name="theorem", body="content")
        assert n.name == "theorem"
        assert n.body == "content"

    def test_environment_node_children(self):
        child = TextNode("child")
        n = EnvironmentNode(name="theorem", body="", children=[child])
        assert n.children[0] is child

    def test_group_node_creation(self):
        n = GroupNode(children=[TextNode("x")])
        assert len(n.children) == 1

    def test_package_info(self):
        p = PackageInfo(name="amsmath", options=["fleqn"])
        assert p.name == "amsmath"
        assert "fleqn" in p.options

    def test_env_info(self):
        e = EnvInfo(name="myenv", begin_def="start", end_def="end")
        assert e.name == "myenv"

    def test_font_config_default(self):
        f = FontConfig()
        assert f.is_xepersian is False

    def test_latex_document_default(self):
        doc = LatexDocument()
        assert doc.preamble is not None
        assert doc.body == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestRealSampleFile — فایل نمونه واقعی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.mark.skipif(not _HAS_SAMPLE, reason="sample-book.tex not available")
class TestRealSampleFile:
    """تست با فایل نمونه واقعی sample-book.tex."""

    @pytest.fixture(scope="class")
    def doc(self) -> LatexDocument:
        parser = LatexParser()
        return parser.parse_file(_SAMPLE_TEX)

    def test_document_class_book(self, doc):
        assert doc.preamble.document_class == "book"

    def test_xepersian_present(self, doc):
        assert doc.preamble.fonts.is_xepersian is True

    def test_amsmath_package(self, doc):
        names = [p.name for p in doc.preamble.packages]
        assert "amsmath" in names

    def test_tikz_package(self, doc):
        names = [p.name for p in doc.preamble.packages]
        assert "tikz" in names

    def test_title_extracted(self, doc):
        assert len(doc.preamble.title) > 0
        # Title may contain Persian and/or English text
        assert has_persian(doc.preamble.title) or "Logic" in doc.preamble.title or "Foundations" in doc.preamble.title

    def test_author_extracted(self, doc):
        assert len(doc.preamble.author) > 0

    def test_tcb_environments_detected(self, doc):
        assert len(doc.preamble.tcb_environments) >= 2

    def test_theorem_env_detected(self, doc):
        assert "theorem" in doc.preamble.tcb_environments

    def test_body_not_empty(self, doc):
        assert len(doc.body) > 0

    def test_chapter_commands_present(self, doc):
        cmds = [n for n in doc.body if isinstance(n, CommandNode)]
        assert any(c.name == "chapter" for c in cmds)

    def test_section_commands_present(self, doc):
        cmds = [n for n in doc.body if isinstance(n, CommandNode)]
        assert any(c.name == "section" for c in cmds)

    def test_math_nodes_present(self, doc):
        """فرمول‌های ریاضی تشخیص داده شوند (بازگشتی)."""
        def count_math(nodes):
            total = 0
            for n in nodes:
                if isinstance(n, MathNode):
                    total += 1
                elif isinstance(n, EnvironmentNode):
                    total += count_math(n.children)
            return total
        assert count_math(doc.body) >= 3

    def test_environment_nodes_present(self, doc):
        envs = [n for n in doc.body if isinstance(n, EnvironmentNode)]
        assert len(envs) >= 3

    def test_zwnj_preserved_in_body(self, doc):
        """نیم‌فاصله در body حفظ شده باشد."""
        all_content: list[str] = []
        for node in doc.body:
            if isinstance(node, TextNode):
                all_content.append(node.content)
            elif isinstance(node, CommandNode) and node.args:
                all_content.extend(node.args)
        combined = " ".join(all_content)
        assert ZWNJ in combined

    def test_no_crash_on_full_parse(self, doc):
        """تحلیل کامل فایل بدون خطا."""
        assert doc is not None

    def test_table_environments_detected(self, doc):
        """محیط‌های جدول تشخیص داده شوند."""
        envs = [n for n in doc.body if isinstance(n, EnvironmentNode)]
        env_names = {e.name for e in envs}
        assert "table" in env_names or "tabular" in env_names

    def test_tikzpicture_detected(self, doc):
        """محیط tikzpicture تشخیص داده شود (بازگشتی)."""
        def find_env(nodes, name):
            for n in nodes:
                if isinstance(n, EnvironmentNode):
                    if n.name == name:
                        return True
                    if find_env(n.children, name):
                        return True
            return False
        assert find_env(doc.body, "tikzpicture")
