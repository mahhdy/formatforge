"""
تست‌های E2E تبدیل LaTeX — S09-C4
End-to-end tests for LaTeX conversion pipeline

Coverage:
- Full LaTeX → MDX pipeline
- Multi-chapter book conversion
- LaTeX cleaner integration
- TikZ detection and wrapping
- Metadata extraction
- ZWNJ preservation across pipeline
- Quality validation
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from formatforge.core.converters.base import ConversionContext
from formatforge.core.converters.latex_book_converter import (
    LaTeXBookConverter,
)
from formatforge.core.converters.latex_cleaner import LaTeXCleaner
from formatforge.core.converters.latex_to_mdx import LaTeXToMDXConverter
from formatforge.core.converters.tikz_to_svg import (
    TikZToSVGConverter,
    extract_tikz_references,
    replace_tikz_with_svg,
)
from formatforge.core.converters.latex_parser import ZWNJ

# ─── Path to real test file ──────────────────
_SAMPLE_TEX = Path(__file__).parent.parent / "test_files" / "sample-book.tex"
_HAS_SAMPLE = _SAMPLE_TEX.exists()

# ─── Test fixtures ───────────────────────────

PERSIAN_LATEX = r"""\documentclass[12pt]{book}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{xepersian}
\settextfont{Vazirmatn}
\title{کتاب ریاضی}
\author{علی محمدی}
\date{2025-06-15}
\begin{document}
\chapter{مقدمه}
\section{تعاریف}
متن مقدمه با """ + ZWNJ + r""" نیم‌فاصله.

\subsection{قضیه}
\begin theorem}{قضیه فیثاغورس}{pythagoras}
$a^2 + b^2 = c^2$
\end theorem}

\chapter{نتیجه‌گیری}
خلاصه مطالب.
\end{document}
"""

MIXED_CONTENT_LATEX = r"""
\documentclass{article}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{minted}
\title{Mixed Content Document}
\author{Test Author}
\date{2025-01-01}
\begin{document}

\section{Mathematics}
Inline math: $E = mc^2$

Display math:
\begin{equation}
\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
\end{equation}

\section{Code}
\begin{minted}{python}
def hello():
    print("Hello, world!")
\end{minted}

\section{Figure}
\begin{figure}[h]
centering
includegraphics[width=0.5]{image.png}
\caption{Sample Image}
\label{fig:sample}
\end{figure}

\section{Table}
\begin{tabular}{|c|c|}
\hline
A & B \\
\hline
1 & 2 \\
\hline
\end{tabular}

\end{document}
"""

TIKZ_LATEX = r"""
\documentclass{article}
\usepackage{tikz}
\usetikzlibrary{arrows,shapes}
\title{TikZ Document}
\begin{document}
\begin{center}
\begin{tikzpicture}[node distance=1.5cm]
  \node[draw, circle] (A) {A};
  \node[draw, circle, right of=A] (B) {B};
  \draw[->] (A) -- (B);
\end{tikzpicture}
\caption{Simple TikZ Diagram}
\end{center}
\end{document}
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestFullPipeline — لوله کامل
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFullPipeline:
    """تست‌های لوله کامل LaTeX → MDX."""

    @pytest.fixture
    def latex_converter(self):
        return LaTeXToMDXConverter()

    @pytest.fixture
    def book_converter(self):
        return LaTeXBookConverter()

    @pytest.fixture
    def cleaner(self):
        return LaTeXCleaner()

    @pytest.fixture
    def tikz_converter(self):
        return TikZToSVGConverter()

    def test_persian_latex_to_mdx(self, latex_converter, tmp_path):
        """تبدیل کامل LaTeX فارسی به MDX."""
        test_file = tmp_path / "persian.tex"
        test_file.write_text(PERSIAN_LATEX, encoding="utf-8")
        
        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = latex_converter.convert(test_file, ctx)

        assert result.status == "success"
        
        mdx = ctx.extra.get("mdx_content", "")
        # Check ZWNJ preserved
        assert ZWNJ in mdx
        # Check frontmatter
        assert "---" in mdx

    def test_mixed_content_latex(self, latex_converter, tmp_path):
        """تبدیل محتوای متنوع LaTeX."""
        test_file = tmp_path / "mixed.tex"
        test_file.write_text(MIXED_CONTENT_LATEX, encoding="utf-8")

        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = latex_converter.convert(test_file, ctx)

        assert result.status == "success"
        assert result.quality.math_inline_count > 0
        assert result.quality.math_block_count > 0
        assert result.quality.code_blocks_count > 0

    def test_quality_report(self, latex_converter, tmp_path):
        """بررسی گزارش کیفیت."""
        test_file = tmp_path / "test.tex"
        test_file.write_text(MIXED_CONTENT_LATEX, encoding="utf-8")

        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = latex_converter.convert(test_file, ctx)

        assert result.quality.headings_count > 0
        assert result.quality.math_block_count >= 0
        assert result.quality.code_blocks_count >= 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestBookConversion — تبدیل کتاب
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBookConversion:
    """تست‌های تبدیل کتاب چندفصلی."""

    @pytest.fixture
    def converter(self):
        return LaTeXBookConverter()

    def test_book_detection(self, converter, tmp_path):
        """تشخیص کتاب بودن."""
        test_file = tmp_path / "book.tex"
        test_file.write_text(PERSIAN_LATEX, encoding="utf-8")

        assert converter.is_book(test_file) is True

    def test_book_structure_parsing(self, converter, tmp_path):
        """تحلیل ساختار کتاب."""
        test_file = tmp_path / "book.tex"
        test_file.write_text(PERSIAN_LATEX, encoding="utf-8")

        book = converter.parse_book(test_file)

        assert book.title == "کتاب ریاضی"
        assert book.author == "علی محمدی"
        assert len(book.chapters) == 2
        assert book.lang == "fa"

    def test_book_chapter_slugs(self, converter, tmp_path):
        """بررسی slug فصل‌ها."""
        test_file = tmp_path / "book.tex"
        test_file.write_text(PERSIAN_LATEX, encoding="utf-8")

        book = converter.parse_book(test_file)

        for ch in book.chapters:
            assert ch.slug.startswith(f"{ch.order:02d}-")

    @pytest.mark.skipif(not _HAS_SAMPLE, reason="sample-book.tex not available")
    def test_real_book_conversion(self, converter, tmp_path):
        """تبدیل کتاب واقعی."""
        result = converter.convert_book(_SAMPLE_TEX, tmp_path / "output")

        assert result.status == "success"
        assert result.total_chapters >= 1
        assert result.series_json_path is not None

        # Check series JSON
        series_data = json.loads(
            Path(result.series_json_path).read_text(encoding="utf-8")
        )
        assert "title" in series_data
        assert "chapters" in series_data


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestLaTeXCleaner — پاک‌ساز LaTeX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLaTeXCleaner:
    """تست‌های پاک‌ساز LaTeX."""

    @pytest.fixture
    def cleaner(self):
        return LaTeXCleaner()

    def test_remove_commands(self, cleaner):
        """حذف دستورات غیرضروری."""
        content = r"\documentclass{article}\usepackage{amsmath}\section{Test}"
        cleaned = cleaner.clean(content)

        assert r"\documentclass" not in cleaned
        assert r"\usepackage" not in cleaned
        assert "Test" in cleaned

    def test_preserve_zwnj(self, cleaner):
        """حفظ ZWNJ در پاک‌سازی."""
        content = "Test" + ZWNJ + "content"
        cleaned = cleaner.clean(content)

        assert ZWNJ in cleaned

    def test_clean_preamble(self, cleaner):
        """پاک‌سازی preamble."""
        content = r"\documentclass{article}\usepackage{abc}\begin{document}Body\end{document}"
        cleaned = cleaner.clean_preamble(content)

        assert "Body" in cleaned
        assert r"\documentclass" not in cleaned

    def test_comment_removal(self, cleaner):
        """حذف کامنت‌ها."""
        content = "Hello % This is a comment\nWorld"
        cleaned = cleaner.clean(content)

        assert "%" not in cleaned
        assert "Hello" in cleaned
        assert "World" in cleaned


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestTikZIntegration — یکپارچگی TikZ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTikZIntegration:
    """تست‌های یکپارچگی TikZ."""

    @pytest.fixture
    def latex_converter(self):
        return LaTeXToMDXConverter()

    @pytest.fixture
    def tikz_extractor(self):
        return TikZToSVGConverter()

    def test_tikz_extraction_from_latex(self, tikz_extractor):
        """استخراج TikZ از LaTeX."""
        results = tikz_extractor.extract_tikz_from_latex(TIKZ_LATEX)

        assert len(results) >= 1
        # Check that we got code
        assert "node" in results[0]["code"] or "draw" in results[0]["code"]

    def test_tikz_reference_extraction(self):
        """استخراج ارجاعات TikZ از MDX."""
        mdx = r"""
# Test

<TikZDiagram>
\draw (0,0) -- (1,1);
</TikZDiagram>
"""
        refs = extract_tikz_references(mdx)

        assert len(refs) == 1
        assert "draw" in refs[0]["code"]

    def test_tikz_svg_replacement(self):
        """جایگزینی TikZ با SVG."""
        mdx = r"<TikZDiagram>\draw (0,0);</TikZDiagram>"
        svg_map = {0: "<svg>test</svg>"}

        result = replace_tikz_with_svg(mdx, svg_map)

        assert "<TikZDiagram>" not in result
        assert "<svg>test</svg>" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestMetadataExtraction — استخراج متادیتا
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMetadataExtraction:
    """تست‌های استخراج متادیتا."""

    @pytest.fixture
    def converter(self):
        return LaTeXToMDXConverter()

    def test_title_extraction(self, converter, tmp_path):
        """استخراج عنوان."""
        test_file = tmp_path / "test.tex"
        test_file.write_text(PERSIAN_LATEX, encoding="utf-8")

        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = converter.convert(test_file, ctx)

        mdx = ctx.extra.get("mdx_content", "")
        assert "title:" in mdx
        assert "کتاب ریاضی" in mdx

    def test_author_extraction(self, converter, tmp_path):
        """استخراج نویسنده."""
        test_file = tmp_path / "test.tex"
        test_file.write_text(PERSIAN_LATEX, encoding="utf-8")

        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = converter.convert(test_file, ctx)

        mdx = ctx.extra.get("mdx_content", "")
        assert "author:" in mdx

    def test_date_extraction(self, converter, tmp_path):
        """استخراج تاریخ."""
        test_file = tmp_path / "test.tex"
        test_file.write_text(PERSIAN_LATEX, encoding="utf-8")

        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = converter.convert(test_file, ctx)

        mdx = ctx.extra.get("mdx_content", "")
        assert "date:" in mdx
        assert "2025" in mdx


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestZWNJPreservation — حفظ ZWNJ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestZWNJPreservation:
    """تست‌های حفظ ZWNJ در لوله کامل."""

    @pytest.fixture
    def converter(self):
        return LaTeXToMDXConverter()

    @pytest.fixture
    def book_converter(self):
        return LaTeXBookConverter()

    def test_zwnj_in_conversion(self, converter, tmp_path):
        """حفظ ZWNJ در تبدیل."""
        content = r"""\documentclass{article}
\begin{document}
Test""" + ZWNJ + r"""content
\end{document}
"""
        test_file = tmp_path / "test.tex"
        test_file.write_text(content, encoding="utf-8")

        ctx = ConversionContext(output_dir=tmp_path / "output")
        result = converter.convert(test_file, ctx)

        output = ctx.extra.get("mdx_content", "")
        assert output.count(ZWNJ) == content.count(ZWNJ)

    def test_zwnj_in_book_conversion(self, book_converter, tmp_path):
        """حفظ ZWNJ در تبدیل کتاب."""
        test_file = tmp_path / "book.tex"
        test_file.write_text(PERSIAN_LATEX, encoding="utf-8")

        result = book_converter.convert_book(test_file, tmp_path / "output")

        # Check each chapter
        for ch_result in result.chapter_results:
            if ch_result.output_path:
                content = Path(ch_result.output_path).read_text(encoding="utf-8")
                # ZWNJ should be present in the Persian content
                assert "نیم‌فاصله" in content or ZWNJ in content


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TestErrorHandling — مدیریت خطا
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestErrorHandling:
    """تست‌های مدیریت خطا."""

    @pytest.fixture
    def converter(self):
        return LaTeXToMDXConverter()

    def test_missing_file(self, converter, tmp_path):
        """خطای فایل وجود ندارد."""
        from formatforge.core.converters.base import ConversionError
        ctx = ConversionContext(output_dir=tmp_path / "output")
        
        # The converter raises ConversionError for missing files
        with pytest.raises(ConversionError):
            converter.convert(tmp_path / "nonexistent.tex", ctx)
