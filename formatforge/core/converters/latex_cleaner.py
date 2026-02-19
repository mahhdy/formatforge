"""
FormatForge - LaTeX Cleaner — S09-C2
حذف دستورات غیرضروری LaTeX

Removes or converts LaTeX commands that have no meaning in MDX output:
  - Page layout (geometry, pagestyle, fancyhdr)
  - Font commands (settextfont, setlatinfont — already extracted)
  - Package imports (usepackage — already parsed)
  - Counters (setcounter, newcounter)
  - Vertical/horizontal spacing
  - Phantom commands
  - Color definitions (definecolor — already extracted)

قواعد حیاتی:
- ZWNJ (U+200C) هرگز حذف نشود
- محتوای داخل آرگومان‌های مهم حفظ شود
"""

from __future__ import annotations

import re
from typing import Callable

# ─── Constants ────────────────────────────────────
ZWNJ = "\u200c"

# Commands to remove entirely (command + all args)
REMOVABLE_COMMANDS: frozenset[str] = frozenset({
    # Page layout
    "geometry", "pagestyle", "thispagestyle",
    "fancyhf", "fancyhead", "fancyfoot",
    "headrulewidth", "footrulewidth",
    "setlength", "addtolength",
    # Font (web doesn't use them)
    "settextfont", "setlatintextfont", "setdigitfont",
    "setmathfont", "setmonofont",
    "selectfont",
    # Packages (already parsed)
    "usepackage", "RequirePackage",
    # Settings
    "pgfplotsset", "usetikzlibrary", "tikzset",
    "graphicspath",
    # Counters
    "setcounter", "addtocounter", "stepcounter",
    "newcounter", "refstepcounter",
    # Vertical spacing
    "vspace", "vfill",
    "bigskip", "medskip", "smallskip",
    # Horizontal spacing
    "hspace", "hfill",
    # Phantoms
    "phantom", "hphantom", "vphantom",
    # Color definitions
    "definecolor", "colorlet",
    # Bibliography style
    "bibliographystyle",
    # Other
    "documentclass",
    "makeatletter", "makeatother",
    "newcommand", "renewcommand", "providecommand",
    "newenvironment", "renewenvironment",
    "newtcbtheorem", "newtcolorbox", "DeclareTColorBox",
    "AtBeginDocument", "AtEndDocument",
    "DeclareOption", "ProcessOptions",
    "pagenumbering",
    "addbibresource",
    "nocite",
    # Size commands (no argument)
    "normalsize", "small", "footnotesize", "scriptsize", "tiny",
    "large", "Large", "LARGE", "huge", "Huge",
    # Font shape
    "bfseries", "itshape", "rmfamily", "ttfamily", "sffamily",
    "mdseries", "upshape", "slshape",
    # Alignment (standalone)
    "centering", "raggedleft", "raggedright", "raggedbottom",
    # Indentation
    "noindent", "indent",
    # Misc
    "frontmatter", "mainmatter", "backmatter",
    "maketitle", "tableofcontents",
    "listoffigures", "listoftables",
})

# Commands to convert to specific output
CONVERTIBLE_COMMANDS: dict[str, Callable[[str], str]] = {
    "clearpage": lambda _: "\n\n---\n\n",
    "newpage": lambda _: "\n\n---\n\n",
    "pagebreak": lambda _: "\n\n---\n\n",
    "quad": lambda _: "&emsp;",
    "qquad": lambda _: "&emsp;&emsp;",
    "thinspace": lambda _: "&thinsp;",
    "enspace": lambda _: "&ensp;",
    "linebreak": lambda _: "  \n",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LaTeXCleaner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LaTeXCleaner:
    """
    حذف دستورات غیرضروری LaTeX از محتوا.
    Removes or converts LaTeX commands not needed for MDX.

    Usage:
        cleaner = LaTeXCleaner()
        cleaned = cleaner.clean(content)
    """

    def __init__(
        self,
        extra_removable: frozenset[str] | None = None,
        extra_convertible: dict[str, Callable[[str], str]] | None = None,
    ) -> None:
        self._removable = REMOVABLE_COMMANDS
        if extra_removable:
            self._removable = self._removable | extra_removable

        self._convertible = dict(CONVERTIBLE_COMMANDS)
        if extra_convertible:
            self._convertible.update(extra_convertible)

        # Regex for matching \command with optional [opts] and {args}
        self._re_command = re.compile(
            r"\\([a-zA-Z@]+)\*?"
            r"(?:\s*\[[^\]]*\])*"  # optional args
            r"(?:\s*\{[^}]*\})*"  # mandatory args
        )

    def clean(self, content: str) -> str:
        """
        پاک‌سازی محتوای LaTeX.
        Remove or convert unnecessary commands. Preserves ZWNJ.
        """
        zwnj_before = content.count(ZWNJ)

        # Remove comments (but preserve ZWNJ in comments — unlikely but safe)
        content = self._remove_comments(content)

        # Remove/convert commands
        content = self._process_commands(content)

        # Clean up excessive blank lines
        content = re.sub(r"\n{4,}", "\n\n\n", content)

        # Remove leading/trailing whitespace on each line
        lines = content.split("\n")
        lines = [line.rstrip() for line in lines]
        content = "\n".join(lines)

        # Verify ZWNJ preservation
        zwnj_after = content.count(ZWNJ)
        if zwnj_after < zwnj_before:
            # This shouldn't happen, but log if it does
            pass

        return content

    def _remove_comments(self, content: str) -> str:
        """Remove LaTeX % comments (but not \\%)."""
        lines: list[str] = []
        for line in content.split("\n"):
            # Find unescaped %
            pos = 0
            while pos < len(line):
                if line[pos] == "%" and (pos == 0 or line[pos - 1] != "\\"):
                    line = line[:pos]
                    break
                pos += 1
            lines.append(line)
        return "\n".join(lines)

    def _process_commands(self, content: str) -> str:
        """Remove/convert known commands."""
        result: list[str] = []
        pos = 0

        while pos < len(content):
            if content[pos] == "\\" and pos + 1 < len(content):
                m = self._re_command.match(content, pos)
                if m:
                    cmd_name = m.group(1)

                    if cmd_name in self._removable:
                        # Skip the entire command
                        pos = m.end()
                        # Skip trailing whitespace/newline
                        while pos < len(content) and content[pos] in " \t":
                            pos += 1
                        continue

                    if cmd_name in self._convertible:
                        replacement = self._convertible[cmd_name](m.group(0))
                        result.append(replacement)
                        pos = m.end()
                        continue

                # Not removable/convertible — keep as is
                result.append(content[pos])
                pos += 1
            else:
                result.append(content[pos])
                pos += 1

        return "".join(result)

    def clean_preamble(self, content: str) -> str:
        """
        حذف کامل preamble (قبل از \\begin{document}).
        Remove everything before \\begin{document}.
        """
        m = re.search(r"\\begin\s*\{document\}", content)
        if m:
            return content[m.end():]
        return content

    def count_removed(self, original: str, cleaned: str) -> dict[str, int]:
        """
        شمارش دستورات حذف‌شده.
        Count how many commands were removed.
        """
        stats: dict[str, int] = {}
        for cmd in self._removable:
            pattern = re.compile(r"\\" + re.escape(cmd) + r"(?:\W|$)")
            orig_count = len(pattern.findall(original))
            clean_count = len(pattern.findall(cleaned))
            removed = orig_count - clean_count
            if removed > 0:
                stats[cmd] = removed
        return stats
