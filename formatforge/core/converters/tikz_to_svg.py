"""
FormatForge - TikZ to SVG Converter — S09-C3
تبدیل TikZ به SVG

Converts LaTeX TikZ diagrams to SVG format:
  1. Extract TikZ code from LaTeX documents
  2. Generate standalone LaTeX for compilation
  3. Compile with pdflatex + dvisvgm to SVG
  4. Return SVG content or path

قواعد حیاتی:
- ZWNJ (U+200C) هرگز حذف نشود
- خطای کامپایل graceful شود
- SVG بهینه‌شده برگردانده شود
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("formatforge.converters.tikz")

# ─── Constants ────────────────────────────────────
ZWNJ = "\u200c"

# Default TikZ libraries to include
DEFAULT_TIKZ_LIBS = [
    "arrows.meta",
    "calc",
    "positioning",
    "shapes.geometric",
    "shapes.misc",
    "decorations.pathreplacing",
    "patterns",
    "spy",
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TikZ to SVG Converter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TikZToSVGConverter:
    """
    تبدیل‌گر TikZ به SVG.
    Converts TikZ diagrams to SVG using LaTeX compilation.

    Requires: pdflatex, dvisvgm

    Usage:
        converter = TikZToSVGConverter()
        svg_content = converter.convert_tikz(tikz_code)
    """

    def __init__(
        self,
        temp_dir: Path | None = None,
        cleanup: bool = True,
    ) -> None:
        self._temp_dir = temp_dir
        self._cleanup = cleanup

        # Check for available tools
        self._has_pdflatex = self._check_tool("pdflatex")
        self._has_dvisvgm = self._check_tool("dvisvgm")

    def _check_tool(self, tool: str) -> bool:
        """Check if a command-line tool is available."""
        return shutil.which(tool) is not None

    def is_available(self) -> bool:
        """Check if TikZ conversion is available."""
        return self._has_pdflatex and self._has_dvisvgm

    def get_availability_status(self) -> dict[str, bool]:
        """Return status of required tools."""
        return {
            "pdflatex": self._has_pdflatex,
            "dvisvgm": self._has_dvisvgm,
            "ready": self.is_available(),
        }

    def extract_tikz_from_latex(self, content: str) -> list[dict[str, str]]:
        """
        استخراج کد TikZ از محتوای LaTeX.
        Returns list of dict with 'code' and 'caption' keys.
        """
        results: list[dict[str, str]] = []

        # Find all tikzpicture environments
        pattern = re.compile(
            r"\\begin\{tikzpicture\}(.*?)\\end\{tikzpicture\}",
            re.DOTALL,
        )

        for match in pattern.finditer(content):
            tikz_code = match.group(1).strip()

            # Look for caption in nearby content
            start = match.end()
            end = min(start + 500, len(content))
            nearby = content[start:end]

            caption_match = re.search(r"\\caption\{([^}]+)\}", nearby)
            caption = caption_match.group(1) if caption_match else ""

            results.append({
                "code": tikz_code,
                "caption": caption,
            })

        return results

    def extract_tikz_from_mdx(self, content: str) -> list[dict[str, Any]]:
        """
        استخراج کد TikZ از محتوای MDX.
        Extract TikZ from <TikZDiagram> tags in MDX.
        """
        results: list[dict[str, Any]] = []

        # Match <TikZDiagram>...</TikZDiagram>
        pattern = re.compile(
            r"<TikZDiagram>(.*?)</TikZDiagram>",
            re.DOTALL,
        )

        for i, match in enumerate(pattern.finditer(content)):
            code = match.group(1).strip()
            results.append({
                "index": i,
                "code": code,
                "start": match.start(),
                "end": match.end(),
            })

        return results

    def convert_tikz(
        self,
        tikz_code: str,
        width: str = "10cm",
        height: str = "8cm",
        libs: list[str] | None = None,
    ) -> str | None:
        """
        تبدیل کد TikZ به SVG.
        Convert TikZ code to SVG.

        Args:
            tikz_code: The TikZ drawing code
            width: Desired width
            height: Desired height
            libs: List of TikZ libraries to use

        Returns:
            SVG content as string, or None on failure
        """
        if not self.is_available():
            logger.warning(
                "TikZ conversion not available. Install pdflatex and dvisvgm."
            )
            return None

        # Build standalone LaTeX document
        latex_doc = self._build_standalone(tikz_code, width, height, libs)

        # Compile to SVG
        return self._compile_to_svg(latex_doc)

    def _build_standalone(
        self,
        tikz_code: str,
        width: str,
        height: str,
        libs: list[str] | None,
    ) -> str:
        """Build standalone LaTeX document for TikZ."""
        libs = libs or DEFAULT_TIKZ_LIBS
        libs_str = ",".join(libs)

        return rf"""\documentclass[border=2pt]{{standalone}}
\usepackage{{tikz}}
\usetikzlibrary{{{libs_str}}}
\begin{{document}}
\begin{{tikzpicture}}[x={width},y={height}]
{tikz_code}
\end{{tikzpicture}}
\end{{document}}
"""

    def _compile_to_svg(self, latex_doc: str) -> str | None:
        """Compile LaTeX to SVG."""
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Write LaTeX file
            tex_file = tmp / "tikz.tex"
            tex_file.write_text(latex_doc, encoding="utf-8")

            # Compile with pdflatex
            try:
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "tikz.tex"],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    logger.warning(f"LaTeX compilation failed: {result.stderr}")
                    return None

                # Check if PDF was created
                pdf_file = tmp / "tikz.pdf"
                if not pdf_file.exists():
                    logger.warning("PDF file not created")
                    return None

                # Convert to SVG using dvisvgm
                svg = self._convert_with_dvisvgm(tmp, pdf_file)
                return svg

            except subprocess.TimeoutExpired:
                logger.warning("LaTeX compilation timed out")
                return None
            except Exception as exc:
                logger.warning(f"TikZ conversion failed: {exc}")
                return None

    def _convert_with_dvisvgm(self, tmp: Path, pdf_file: Path) -> str | None:
        """Convert PDF to SVG using dvisvgm."""
        try:
            result = subprocess.run(
                ["dvisvgm", "--pdf", str(pdf_file), "-o", "tikz.svg"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                svg_file = tmp / "tikz.svg"
                if svg_file.exists():
                    return svg_file.read_text(encoding="utf-8")

            logger.warning(f"dvisvgm failed: {result.stderr}")
            return None

        except Exception as exc:
            logger.warning(f"dvisvgm conversion failed: {exc}")
            return None

    def convert_document_tikz(
        self,
        file_path: Path,
        output_dir: Path | None = None,
    ) -> list[dict[str, Any]]:
        """
        تبدیل تمام TikZ در یک سند LaTeX.
        Convert all TikZ diagrams in a LaTeX document.

        Returns:
            List of results with svg content and metadata
        """
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tikz_blocks = self.extract_tikz_from_latex(content)

        results: list[dict[str, Any]] = []

        for i, block in enumerate(tikz_blocks):
            svg = self.convert_tikz(block["code"])

            results.append({
                "index": i,
                "caption": block["caption"],
                "svg": svg,
                "success": svg is not None,
            })

        return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Utility functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def extract_tikz_references(content: str) -> list[dict[str, Any]]:
    """
    استخراج ارجاعات TikZ از محتوای MDX.
    Extract TikZ references from MDX content for later conversion.
    """
    # Match <TikZDiagram>...</TikZDiagram>
    pattern = re.compile(
        r"<TikZDiagram>(.*?)</TikZDiagram>",
        re.DOTALL,
    )

    refs = []
    for i, match in enumerate(pattern.finditer(content)):
        code = match.group(1).strip()
        refs.append({
            "index": i,
            "code": code,
            "start": match.start(),
            "end": match.end(),
        })

    return refs


def replace_tikz_with_svg(
    content: str,
    svg_map: dict[int, str],
) -> str:
    """
    جایگزینی تگ‌های TikZ با SVG.
    Replace TikZDiagram tags with SVG content.
    """
    refs = extract_tikz_references(content)

    # Sort in reverse to replace from end to start
    refs.reverse()

    result = content
    for ref in refs:
        idx = ref["index"]
        svg = svg_map.get(idx)
        if svg:
            # Wrap SVG in appropriate container
            svg_wrapper = f'\n<div class="tikz-diagram">\n{svg}\n</div>\n'
            result = result[:ref["start"]] + svg_wrapper + result[ref["end"]:]

    return result
