"""
FormatForge - Test Configuration
تنظیمات مشترک تست‌ها

Shared fixtures and configuration for pytest.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


ZWNJ = "\u200c"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """مسیر پوشه fixtures."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR


@pytest.fixture
def tmp_dir():
    """پوشه موقت برای هر تست."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_persian_text() -> str:
    """متن نمونه فارسی با نیم‌فاصله."""
    return (
        f"\u0633\u0644\u0627\u0645{ZWNJ}\u062f\u0646\u06cc\u0627\n"
        f"\u0645\u06cc{ZWNJ}\u062e\u0648\u0627\u0647\u06cc\u0645 "
        f"\u062a\u0633\u062a \u06a9\u0646\u06cc\u0645."
    )


@pytest.fixture
def sample_latex_content() -> str:
    """محتوای LaTeX نمونه."""
    return (
        "\\documentclass{article}\n"
        "\\usepackage{xepersian}\n"
        "\\begin{document}\n"
        f"\u0633\u0644\u0627\u0645{ZWNJ}\u062f\u0646\u06cc\u0627\n"
        "\\section{\u0645\u0642\u062f\u0645\u0647}\n"
        "\u0645\u062a\u0646 \u0641\u0627\u0631\u0633\u06cc "
        "\u0628\u0627 $x^2$ \u0641\u0631\u0645\u0648\u0644.\n"
        "\\end{document}\n"
    )


@pytest.fixture
def sample_html_content() -> str:
    """محتوای HTML نمونه."""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="fa" dir="rtl">\n'
        "<head><title>\u062a\u0633\u062a</title></head>\n"
        "<body>\n"
        f"<p>\u0633\u0644\u0627\u0645{ZWNJ}"
        "\u062f\u0646\u06cc\u0627</p>\n"
        "</body>\n</html>\n"
    )


@pytest.fixture
def sample_markdown_content() -> str:
    """محتوای Markdown نمونه."""
    return (
        "---\ntitle: \u062a\u0633\u062a\n---\n\n"
        "# \u0639\u0646\u0648\u0627\u0646 \u0627\u0635\u0644\u06cc\n\n"
        f"\u0645\u062a\u0646 \u0641\u0627\u0631\u0633\u06cc "
        f"\u0628\u0627 \u0646\u06cc\u0645{ZWNJ}"
        "\u0641\u0627\u0635\u0644\u0647.\n\n"
        "- \u0622\u06cc\u062a\u0645 \u06f1\n"
        "- \u0622\u06cc\u062a\u0645 \u06f2\n"
    )


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """پوشه خروجی موقت"""
    out = tmp_path / "output"
    out.mkdir()
    return out


# ──────────── متون نمونه ────────────

@pytest.fixture
def persian_text_with_zwnj() -> str:
    """متن فارسی با نیم‌فاصله"""
    return "این یک متن نمونه است. می‌خواهیم کتاب‌ها و مقاله‌های خود را تبدیل کنیم."


@pytest.fixture
def persian_text_without_zwnj() -> str:
    """متن فارسی بدون نیم‌فاصله (غلط)"""
    return "این یک متن نمونه است. می خواهیم کتاب ها و مقاله های خود را تبدیل کنیم."



@pytest.fixture
def latex_math_samples() -> dict[str, str]:
    """نمونه فرمول‌های ریاضی LaTeX"""
    return {
        "inline": r"$\neg(p \land q) \equiv (\neg p) \lor (\neg q)$",
        "display": r"$$\sum_{k=0}^{\infty} \frac{x^k}{k!} = e^x$$",
        "equation": (
            r"\begin{equation}" "\n"
            r"  \int_{-\infty}^{+\infty} e^{-x^2}\,dx = \sqrt{\pi}" "\n"
            r"  \label{eq:gaussian}" "\n"
            r"\end{equation}"
        ),
        "align": (
            r"\begin{align}" "\n"
            r"  \nabla \times \mathbf{E} &= -\frac{\partial \mathbf{B}}{\partial t} \label{eq:faraday} \\" "\n"
            r"  \nabla \times \mathbf{B} &= \mu_0 \mathbf{J} \label{eq:ampere}" "\n"
            r"\end{align}"
        ),
        "cases": (
            r"$$|x| = \begin{cases}" "\n"
            r"  x  & \text{اگر } x \geq 0 \\" "\n"
            r"  -x & \text{اگر } x < 0" "\n"
            r"\end{cases}$$"
        ),
        "matrix": (
            r"$$A = \begin{pmatrix}" "\n"
            r"  a_{11} & a_{12} \\" "\n"
            r"  a_{21} & a_{22}" "\n"
            r"\end{pmatrix}$$"
        ),
    }


@pytest.fixture
def mermaid_samples() -> dict[str, str]:
    """نمونه نمودارهای Mermaid"""
    return {
        "flowchart": (
            "```mermaid\n"
            "flowchart TD\n"
            '    A["شروع"] --> B{"شرط"}\n'
            '    B -->|"بله"| C["پایان"]\n'
            '    B -->|"خیر"| A\n'
            "```"
        ),
        "sequence": (
            "```mermaid\n"
            "sequenceDiagram\n"
            "    participant U as کاربر\n"
            "    participant S as سرور\n"
            "    U->>S: درخواست\n"
            "    S-->>U: پاسخ\n"
            "```"
        ),
    }