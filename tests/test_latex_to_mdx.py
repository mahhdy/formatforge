"""
تست‌های تبدیل‌گر LaTeX → MDX — S08-C2/C3
Tests for formatforge/core/converters/latex_to_mdx.py

Coverage:
- Structural conversion: sections, formatting, lists
- Environment conversion: theorems, figures, tables, code, math
- Full converter: detect, extract_metadata, convert, validate_output
- ZWNJ preservation
- Persian content handling
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from formatforge.core.converters.base import ConversionContext
from formatforge.core.converters.latex_parser import (
    ZWNJ,
    CommandNode,
    EnvironmentNode,
    LatexDocument,
    LatexParser,
    MathNode,
    PreambleInfo,
    TextNode,
)
from formatforge.core.converters.latex_to_mdx import (
    LaTeXToMDXConverter,
    _ConverterState,
    _convert_label_to_id,
    _detect_direction,
    _detect_language,
    _escape_jsx,
    _generate_slug,
    convert_node,
    convert_nodes,
)

# ─── Path to real test file ──────────────────
_SAMPLE_TEX = Path(__file__).parent / "test_files" / "sample-book.tex"
_HAS_SAMPLE = _SAMPLE_TEX.exists()


# ─── Fixtures ────────────────────────────────

SIMPLE_TEX = r"""
\documentclass[12pt,a4paper]{article}
\usepackage{amsmath}
\usepackage[extrafootnotefeatures]{xepersian}
\settextfont{Vazirmatn}
\title{عنوان آزمایشی}
\author{نویسنده آزمایشی}
\date{2025-01-15}
\begin{document}
\chapter{فصل اول}
Hello \textbf{World}.
$E = mc^2$
Some text here.
\end{document}
"""

MATH_TEX = r"""
\documentclass{article}
\begin{document}
Inline: $a + b = c$ and display:
$$\int_0^\infty e^{-x}\,dx = 1$$
Environment:
\begin{equation}
  x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
\end{equation}
\begin{align}
  a &= b + c \\
  d &= e + f
\end{align}
\end{document}
"""

STRUCTURE_TEX = r"""
\documentclass{book}
\begin{document}
\chapter{Chapter One}
\section{Section A}
Some text.
\subsection{Subsection A.1}
More text.
\subsubsection{Sub-sub}
Deep text.
\paragraph{A paragraph}
Para text.
\end{document}
"""

FORMATTING_TEX = r"""
\documentclass{article}
\begin{document}
\textbf{bold} and \emph{italic} and \texttt{code}.
\underline{underlined} and \sout{strikethrough}.
\textsc{Small Caps} here.
\href{https://example.com}{click here}
\end{document}
"""

LIST_TEX = r"""
\documentclass{article}
\begin{document}
\begin{itemize}
\item First
\item Second
\item Third
\end{itemize}
\begin{enumerate}
\item Alpha
\item Beta
\end{enumerate}
\end{document}
"""

THEOREM_TEX = r"""
\documentclass{article}
\newtcbtheorem[number within=chapter]{theorem}{قضیه}{enhanced}{thm}
\begin{document}
\begin{theorem}{De Morgan}{demorgan}
$(A \cup B)^c = A^c \cap B^c$
\end{theorem}
\begin{definition}[تعریف مجموعه]
A set is a collection of distinct objects.
\end{definition}
\begin{proof}
This is trivial.
\end{proof}
\begin{example}
Here is an example.
\end{example}
\end{document}
"""

FIGURE_TEX = r"""
\documentclass{article}
\begin{document}
\begin{figure}[h]
\centering
\includegraphics[width=0.8\textwidth]{images/diagram.png}
\caption{A test diagram}
\label{fig:test}
\end{figure}
\end{document}
"""

CODE_TEX = r"""
\documentclass{article}
\begin{document}
\begin{lstlisting}[language=Python]
def hello():
    print("Hello World")
\end{lstlisting}
\begin{minted}{javascript}
console.log("Hello");
\end{minted}
\begin{verbatim}
raw text here
\end{verbatim}
\end{document}
"""

TABLE_TEX = r"""
\documentclass{article}
\begin{document}
\begin{table}[h]
\caption{Test Table}
\label{tab:test}
\begin{tabular}{|l|c|r|}
\hline
Name & Age & Score \\
\hline
Ali & 25 & 90 \\
Sara & 30 & 85 \\
\hline
\end{tabular}
\end{table}
\end{document}
"""

PERSIAN_TEX = rf"""
\documentclass{{article}}
\usepackage[extrafootnotefeatures]{{xepersian}}
\settextfont{{Vazirmatn}}
\title{{مبانی منطق ریاضی}}
\begin{{document}}
\chapter{{فصل{ZWNJ}اول}}
این یک متن \textbf{{فارسی}} با نیم{ZWNJ}فاصله است.
$x^2 + y^2 = z^2$
\begin{{theorem}}{{قضیه دمورگان}}{{dm}}
$(A \cup B)^c = A^c \cap B^c$
\end{{theorem}}
\end{{document}}
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestHelpers — توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHelpers:
    """تست‌های توابع کمکی."""

    def test_generate_slug_english(self):
        slug = _generate_slug("Hello World")
        assert slug == "hello-world"

    def test_generate_slug_persian_fallback(self):
        slug = _generate_slug("عنوان فارسی")
        assert slug.startswith("doc-")

    def test_generate_slug_mixed(self):
        slug = _generate_slug("مبانی Logic ریاضی")
        assert "logic" in slug

    def test_detect_language_persian(self):
        assert _detect_language("این یک متن فارسی است") == "fa"

    def test_detect_language_english(self):
        assert _detect_language("This is English text") == "en"

    def test_detect_language_mixed(self):
        lang = _detect_language("Hello سلام World مرحبا")
        assert lang in ("fa", "fa-en")

    def test_detect_direction_rtl(self):
        assert _detect_direction("fa") == "rtl"

    def test_detect_direction_ltr(self):
        assert _detect_direction("en") == "ltr"

    def test_escape_jsx(self):
        result = _escape_jsx("a{b}c")
        assert "{" not in result or "&#123;" in result

    def test_convert_label_to_id(self):
        assert _convert_label_to_id("fig:my_fig") == "fig-my-fig"
        assert _convert_label_to_id("thm:demorgan") == "thm-demorgan"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestStructuralConversion — تبدیل ساختاری
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestStructuralConversion:
    """تست‌های تبدیل دستورات ساختاری LaTeX."""

    @pytest.fixture
    def parser(self):
        return LatexParser()

    def test_chapter_to_h1(self, parser):
        doc = parser.parse(STRUCTURE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "# Chapter One" in result

    def test_section_to_h2(self, parser):
        doc = parser.parse(STRUCTURE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "## Section A" in result

    def test_subsection_to_h3(self, parser):
        doc = parser.parse(STRUCTURE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "### Subsection A.1" in result

    def test_subsubsection_to_h4(self, parser):
        doc = parser.parse(STRUCTURE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "#### Sub-sub" in result

    def test_paragraph_to_h5(self, parser):
        doc = parser.parse(STRUCTURE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "##### A paragraph" in result

    def test_heading_count(self, parser):
        doc = parser.parse(STRUCTURE_TEX)
        ctx = _ConverterState()
        convert_nodes(doc.body, doc, ctx)
        assert ctx.heading_count == 5

    def test_bold(self, parser):
        doc = parser.parse(FORMATTING_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "**bold**" in result

    def test_italic(self, parser):
        doc = parser.parse(FORMATTING_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "*italic*" in result

    def test_code_inline(self, parser):
        doc = parser.parse(FORMATTING_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "`code`" in result

    def test_underline(self, parser):
        doc = parser.parse(FORMATTING_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "<u>underlined</u>" in result

    def test_strikethrough(self, parser):
        doc = parser.parse(FORMATTING_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "~~strikethrough~~" in result

    def test_small_caps(self, parser):
        doc = parser.parse(FORMATTING_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "small-caps" in result

    def test_href(self, parser):
        doc = parser.parse(FORMATTING_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "[click here](https://example.com)" in result

    def test_link_count(self, parser):
        doc = parser.parse(FORMATTING_TEX)
        ctx = _ConverterState()
        convert_nodes(doc.body, doc, ctx)
        assert ctx.link_count >= 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestListConversion — تبدیل لیست‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestListConversion:
    """تست‌های تبدیل لیست‌ها."""

    @pytest.fixture
    def parser(self):
        return LatexParser()

    def test_itemize_produces_bullets(self, parser):
        doc = parser.parse(LIST_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "- First" in result
        assert "- Second" in result

    def test_enumerate_produces_numbers(self, parser):
        doc = parser.parse(LIST_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "1. Alpha" in result or "1." in result
        assert "2. Beta" in result or "2." in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestMathConversion — تبدیل ریاضی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMathConversion:
    """تست‌های تبدیل فرمول‌های ریاضی."""

    @pytest.fixture
    def parser(self):
        return LatexParser()

    def test_inline_math(self, parser):
        doc = parser.parse(MATH_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "$a + b = c$" in result

    def test_display_math_dollars(self, parser):
        doc = parser.parse(MATH_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "$$" in result

    def test_equation_env(self, parser):
        doc = parser.parse(MATH_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "\\begin{equation}" in result
        assert "\\end{equation}" in result

    def test_align_env(self, parser):
        doc = parser.parse(MATH_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "\\begin{align}" in result

    def test_math_counts(self, parser):
        doc = parser.parse(MATH_TEX)
        ctx = _ConverterState()
        convert_nodes(doc.body, doc, ctx)
        assert ctx.math_inline_count >= 1
        assert ctx.math_block_count >= 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestEnvironmentConversion — تبدیل محیط‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEnvironmentConversion:
    """تست‌های تبدیل محیط‌های LaTeX."""

    @pytest.fixture
    def parser(self):
        return LatexParser()

    def test_theorem_component(self, parser):
        doc = parser.parse(THEOREM_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "<Theorem" in result
        assert "De Morgan" in result

    def test_theorem_label(self, parser):
        doc = parser.parse(THEOREM_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "demorgan" in result

    def test_definition_component(self, parser):
        doc = parser.parse(THEOREM_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "<Definition" in result

    def test_proof_component(self, parser):
        doc = parser.parse(THEOREM_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "<Proof" in result

    def test_example_component(self, parser):
        doc = parser.parse(THEOREM_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "<Example" in result

    def test_figure_component(self, parser):
        doc = parser.parse(FIGURE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "<Figure" in result
        assert "diagram.png" in result

    def test_figure_caption(self, parser):
        doc = parser.parse(FIGURE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "test diagram" in result.lower() or "A test diagram" in result

    def test_figure_label_id(self, parser):
        doc = parser.parse(FIGURE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "fig-test" in result

    def test_image_count(self, parser):
        doc = parser.parse(FIGURE_TEX)
        ctx = _ConverterState()
        convert_nodes(doc.body, doc, ctx)
        assert ctx.image_count >= 1

    def test_table_env(self, parser):
        doc = parser.parse(TABLE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "Test Table" in result
        assert ctx.table_count >= 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestCodeConversion — تبدیل کد
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCodeConversion:
    """تست‌های تبدیل محیط‌های کد."""

    @pytest.fixture
    def parser(self):
        return LatexParser()

    def test_lstlisting(self, parser):
        doc = parser.parse(CODE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "```python" in result.lower() or "```Python" in result

    def test_minted(self, parser):
        doc = parser.parse(CODE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "```javascript" in result

    def test_verbatim(self, parser):
        doc = parser.parse(CODE_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert "raw text here" in result

    def test_code_block_count(self, parser):
        doc = parser.parse(CODE_TEX)
        ctx = _ConverterState()
        convert_nodes(doc.body, doc, ctx)
        assert ctx.code_block_count == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestZWNJPreservation — حفظ نیم‌فاصله
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestZWNJPreservation:
    """تست‌های حفظ نیم‌فاصله."""

    @pytest.fixture
    def parser(self):
        return LatexParser()

    def test_zwnj_in_chapter_title(self, parser):
        doc = parser.parse(PERSIAN_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        assert ZWNJ in result

    def test_zwnj_in_text(self, parser):
        doc = parser.parse(PERSIAN_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        zwnj_count = result.count(ZWNJ)
        assert zwnj_count >= 2

    def test_zwnj_count_preserved_in_conversion(self, parser):
        """ZWNJ count should not decrease through conversion."""
        doc = parser.parse(PERSIAN_TEX)
        ctx = _ConverterState()
        result = convert_nodes(doc.body, doc, ctx)
        # Original has 2 ZWNJ (chapter + text), result should have at least 2
        assert result.count(ZWNJ) >= 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestConverterDetect — تشخیص فرمت
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConverterDetect:
    """تست‌های detect()."""

    @pytest.fixture
    def converter(self):
        return LaTeXToMDXConverter()

    def test_detect_by_extension(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(r"\documentclass{article}", encoding="utf-8")
        assert converter.detect(f) is True

    def test_detect_by_content(self, converter, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(
            r"\documentclass{article}" "\n" r"\begin{document}" "\n"
            r"\section{Hello}" "\n" r"\end{document}",
            encoding="utf-8",
        )
        assert converter.detect(f) is True

    def test_detect_not_latex(self, converter, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Hello World\n\nSome text", encoding="utf-8")
        assert converter.detect(f) is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestMetadataExtraction — استخراج متادیتا
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMetadataExtraction:
    """تست‌های extract_metadata()."""

    @pytest.fixture
    def converter(self):
        return LaTeXToMDXConverter()

    def test_title_extracted(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(SIMPLE_TEX, encoding="utf-8")
        meta = converter.extract_metadata(f)
        assert "آزمایشی" in meta.title

    def test_lang_persian_detected(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(PERSIAN_TEX, encoding="utf-8")
        meta = converter.extract_metadata(f)
        assert meta.lang == "fa"

    def test_dir_rtl_for_persian(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(PERSIAN_TEX, encoding="utf-8")
        meta = converter.extract_metadata(f)
        assert meta.dir == "rtl"

    def test_source_format_latex(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(SIMPLE_TEX, encoding="utf-8")
        meta = converter.extract_metadata(f)
        assert meta.source_format == "latex"

    def test_math_detected(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(MATH_TEX, encoding="utf-8")
        meta = converter.extract_metadata(f)
        assert meta.math is True

    def test_slug_generated(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(SIMPLE_TEX, encoding="utf-8")
        meta = converter.extract_metadata(f)
        assert len(meta.slug) > 0

    def test_author_extracted(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(SIMPLE_TEX, encoding="utf-8")
        meta = converter.extract_metadata(f)
        assert meta.author is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestFullConversion — تبدیل کامل
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFullConversion:
    """تست‌های convert() — خط لوله کامل."""

    @pytest.fixture
    def converter(self):
        return LaTeXToMDXConverter()

    def _convert(self, converter, tex_content, tmp_path):
        """Helper: write tex, convert, return result + mdx content."""
        f = tmp_path / "test.tex"
        f.write_text(tex_content, encoding="utf-8")
        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = converter.convert(f, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        return result, mdx, ctx

    def test_convert_simple(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, SIMPLE_TEX, tmp_path)
        assert result.status == "success"
        assert len(mdx) > 0

    def test_convert_has_frontmatter(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, SIMPLE_TEX, tmp_path)
        assert mdx.startswith("---\n")
        assert "\n---\n" in mdx

    def test_convert_has_title_in_frontmatter(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, SIMPLE_TEX, tmp_path)
        assert "آزمایشی" in mdx

    def test_convert_has_heading(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, STRUCTURE_TEX, tmp_path)
        assert "# Chapter One" in mdx

    def test_convert_has_math(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, MATH_TEX, tmp_path)
        assert "$$" in mdx

    def test_convert_has_code(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, CODE_TEX, tmp_path)
        assert "```" in mdx

    def test_convert_has_theorem(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, THEOREM_TEX, tmp_path)
        assert "<Theorem" in mdx or "<Definition" in mdx or "<Proof" in mdx

    def test_convert_has_figure(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, FIGURE_TEX, tmp_path)
        assert "<Figure" in mdx

    def test_convert_output_bytes(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, SIMPLE_TEX, tmp_path)
        assert result.output_bytes > 0

    def test_convert_duration(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, SIMPLE_TEX, tmp_path)
        assert result.duration_seconds >= 0

    def test_convert_zwnj_preserved(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, PERSIAN_TEX, tmp_path)
        assert ZWNJ in mdx
        assert ctx.zwnj_count_after >= ctx.zwnj_count_before

    def test_convert_quality_report(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, MATH_TEX, tmp_path)
        assert result.quality is not None
        assert result.quality.math_block_count >= 1

    def test_convert_writes_file(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, SIMPLE_TEX, tmp_path)
        assert result.output_path is not None
        output = Path(result.output_path)
        assert output.exists()

    def test_convert_converts_at_timestamp(self, converter, tmp_path):
        result, mdx, ctx = self._convert(converter, SIMPLE_TEX, tmp_path)
        assert "convertedAt" in mdx

    def test_convert_persian_content(self, converter, tmp_path):
        """Full pipeline with Persian text."""
        result, mdx, ctx = self._convert(converter, PERSIAN_TEX, tmp_path)
        assert result.status == "success"
        assert "فارسی" in mdx

    def test_convert_failed_on_missing_file(self, converter, tmp_path):
        """Convert fails gracefully for missing file."""
        f = tmp_path / "nonexistent.tex"
        ctx = ConversionContext()
        with pytest.raises(Exception):
            converter.convert(f, ctx)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestValidation — اعتبارسنجی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestValidation:
    """تست‌های validate_output()."""

    @pytest.fixture
    def converter(self):
        return LaTeXToMDXConverter()

    def test_validate_returns_report(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(SIMPLE_TEX, encoding="utf-8")
        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = converter.convert(f, ctx)
        report = converter.validate_output(result, ctx)
        assert report is not None
        assert hasattr(report, "score")

    def test_validate_bidi_correct(self, converter, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(PERSIAN_TEX, encoding="utf-8")
        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = converter.convert(f, ctx)
        report = converter.validate_output(result, ctx)
        assert report.bidi_correct is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestConverterState — وضعیت تبدیل‌گر
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConverterState:
    """تست‌های _ConverterState."""

    def test_initial_counts(self):
        state = _ConverterState()
        assert state.math_block_count == 0
        assert state.heading_count == 0

    def test_require_component(self):
        state = _ConverterState()
        state.require_component("Theorem")
        state.require_component("Definition")
        assert "Theorem" in state.components_used
        assert "Definition" in state.components_used


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestRealSampleFile — فایل نمونه واقعی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.mark.skipif(not _HAS_SAMPLE, reason="sample-book.tex not available")
class TestRealSampleFile:
    """تست با فایل نمونه واقعی sample-book.tex."""

    @pytest.fixture(scope="class")
    def converter(self):
        return LaTeXToMDXConverter()

    @pytest.fixture(scope="class")
    def conversion_result(self, converter, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("latex_output")
        ctx = ConversionContext(output_dir=tmp)
        result = converter.convert(_SAMPLE_TEX, ctx)
        mdx = ctx.extra.get("mdx_content", "")
        return result, mdx, ctx

    def test_conversion_success(self, conversion_result):
        result, mdx, ctx = conversion_result
        assert result.status == "success"

    def test_has_frontmatter(self, conversion_result):
        result, mdx, ctx = conversion_result
        assert mdx.startswith("---\n")

    def test_has_headings(self, conversion_result):
        result, mdx, ctx = conversion_result
        assert "# " in mdx or "## " in mdx

    def test_has_math(self, conversion_result):
        result, mdx, ctx = conversion_result
        assert "$$" in mdx

    def test_has_theorem_components(self, conversion_result):
        result, mdx, ctx = conversion_result
        assert "<Theorem" in mdx or "<Definition" in mdx

    def test_zwnj_preserved(self, conversion_result):
        result, mdx, ctx = conversion_result
        assert ZWNJ in mdx
        assert ctx.zwnj_count_after >= 1

    def test_output_bytes_reasonable(self, conversion_result):
        result, mdx, ctx = conversion_result
        assert result.output_bytes > 1000

    def test_math_blocks_detected(self, conversion_result):
        result, mdx, ctx = conversion_result
        assert result.quality.math_block_count >= 1

    def test_no_raw_latex_commands(self, conversion_result):
        """Check common LaTeX commands are converted."""
        result, mdx, ctx = conversion_result
        # These should not appear in output (preamble commands)
        assert r"\documentclass" not in mdx
        assert r"\maketitle" not in mdx
