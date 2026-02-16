"""
Pytest configuration and shared fixtures.
تنظیمات و fixture های مشترک تست.
"""

import os
from pathlib import Path

import pytest


# ──────────── مسیرها ────────────

@pytest.fixture
def test_files_dir() -> Path:
    """مسیر پوشه فایل‌های تست"""
    return Path(__file__).parent / "test_files"


@pytest.fixture
def sample_latex(test_files_dir: Path) -> Path:
    """مسیر فایل LaTeX نمونه"""
    return test_files_dir / "sample-book.tex"


@pytest.fixture
def sample_markdown(test_files_dir: Path) -> Path:
    """مسیر فایل Markdown نمونه"""
    return test_files_dir / "sample-mermaid.md"


@pytest.fixture
def sample_html(test_files_dir: Path) -> Path:
    """مسیر فایل HTML نمونه"""
    return test_files_dir / "sample-page.html"


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
        "display": r"
$$
\sum_{k=0}^{\infty} \frac{x^k}{k!} = e^x
$$
",
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
            r"
$$
|x| = \begin{cases}" "\n"
            r"  x  & \text{اگر } x \geq 0 \\" "\n"
            r"  -x & \text{اگر } x < 0" "\n"
            r"\end{cases}
$$
"
        ),
        "matrix": (
            r"
$$
A = \begin{pmatrix}" "\n"
            r"  a_{11} & a_{12} \\" "\n"
            r"  a_{21} & a_{22}" "\n"
            r"\end{pmatrix}
$$
"
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