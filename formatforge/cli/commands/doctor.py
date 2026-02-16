"""
FormatForge - Doctor Command
بررسی سلامت سیستم و وابستگی‌ها

Check that all required tools and dependencies are installed.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# ─────────────────────────────────────────────
# Dependency definitions / تعریف وابستگی‌ها
# ─────────────────────────────────────────────

_EXTERNAL_TOOLS: list[dict[str, str]] = [
    {
        "name": "Python",
        "command": "python --version",
        "required": "true",
        "description": "مفسر پایتون",
    },
    {
        "name": "pandoc",
        "command": "pandoc --version",
        "required": "true",
        "description": "تبدیل‌گر اسناد جهانی",
    },
    {
        "name": "xelatex",
        "command": "xelatex --version",
        "required": "false",
        "description": "کامپایلر LaTeX (برای TikZ/PDF)",
    },
    {
        "name": "node",
        "command": "node --version",
        "required": "false",
        "description": "Node.js (برای MDX و Mermaid)",
    },
    {
        "name": "npm",
        "command": "npm --version",
        "required": "false",
        "description": "مدیر بسته Node.js",
    },
    {
        "name": "mmdc (mermaid-cli)",
        "command": "mmdc --version",
        "required": "false",
        "description": "رندر نمودار Mermaid",
    },
    {
        "name": "git",
        "command": "git --version",
        "required": "false",
        "description": "مدیریت نسخه (برای deploy)",
    },
    {
        "name": "dvisvgm",
        "command": "dvisvgm --version",
        "required": "false",
        "description": "تبدیل TikZ به SVG",
    },
]

_PYTHON_PACKAGES: list[dict[str, str]] = [
    {"name": "click", "import": "click", "required": "true"},
    {"name": "rich", "import": "rich", "required": "true"},
    {"name": "pydantic", "import": "pydantic", "required": "true"},
    {"name": "pyyaml", "import": "yaml", "required": "true"},
    {"name": "jinja2", "import": "jinja2", "required": "true"},
    {"name": "chardet", "import": "chardet", "required": "false"},
    {"name": "python-bidi", "import": "bidi", "required": "false"},
    {"name": "Pillow", "import": "PIL", "required": "false"},
    {"name": "playwright", "import": "playwright", "required": "false"},
    {"name": "openai", "import": "openai", "required": "false"},
    {"name": "httpx", "import": "httpx", "required": "false"},
]


def _check_external_tool(command: str) -> tuple[bool, str]:
    """
    بررسی نصب بودن ابزار خارجی.
    Check if an external tool is installed and get its version.
    """
    try:
        parts = command.split()
        exe = parts[0]
        if shutil.which(exe) is None:
            return False, "یافت نشد"

        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_line = (result.stdout or result.stderr).strip().split("\n")[0]
        return True, version_line[:60]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False, "خطا در اجرا"


def _check_python_package(import_name: str) -> tuple[bool, str]:
    """
    بررسی نصب بودن پکیج Python.
    Check if a Python package is importable and get its version.
    """
    try:
        mod = importlib.import_module(import_name)
        version = getattr(mod, "__version__", "نسخه نامشخص")
        return True, str(version)
    except ImportError:
        return False, "نصب نشده"


@click.command(name="doctor")
@click.option(
    "--fix",
    is_flag=True,
    default=False,
    help="تلاش برای نصب خودکار پکیج‌های Python / Auto-install Python packages",
)
@click.pass_context
def doctor(ctx: click.Context, fix: bool) -> None:
    """
    🩺 بررسی سلامت سیستم و وابستگی‌ها

    \b
    بررسی می‌کند:
      - ابزارهای خارجی: pandoc, xelatex, node, mmdc, git, ...
      - پکیج‌های Python: click, rich, pydantic, pyyaml, jinja2, ...

    \b
    مثال:
      formatforge doctor
      formatforge doctor --fix
    """
    console: Console = ctx.obj.get("console", Console())

    console.print()
    console.print(
        Panel(
            "[bold]بررسی سلامت سیستم و وابستگی\u200cها[/]",
            title="[bold cyan]🩺 FormatForge Doctor[/]",
            border_style="cyan",
        )
    )

    all_ok = True
    missing_packages: list[str] = []

    # ─── ابزارهای خارجی ──────────────────
    console.print("\n[bold underline]🔧 ابزارهای خارجی[/]\n")

    ext_table = Table(
        show_header=True,
        header_style="bold",
        border_style="dim",
        pad_edge=False,
    )
    ext_table.add_column("ابزار", width=22, justify="right", style="bold")
    ext_table.add_column("وضعیت", width=10, justify="center")
    ext_table.add_column("نسخه / توضیح", justify="left")
    ext_table.add_column("نیاز", width=8, justify="center")

    for tool in _EXTERNAL_TOOLS:
        found, info = _check_external_tool(tool["command"])
        required = tool["required"] == "true"

        if found:
            status = "[green]✅[/]"
        elif required:
            status = "[red]❌[/]"
            all_ok = False
        else:
            status = "[yellow]⚠[/]"

        need = "[red]اجباری[/]" if required else "[dim]اختیاری[/]"
        ext_table.add_row(tool["name"], status, info, need)

    console.print(ext_table)

    # ─── پکیج‌های Python ─────────────────
    console.print("\n[bold underline]🐍 پکیج‌های Python[/]\n")

    pkg_table = Table(
        show_header=True,
        header_style="bold",
        border_style="dim",
        pad_edge=False,
    )
    pkg_table.add_column("پکیج", width=20, justify="right", style="bold")
    pkg_table.add_column("وضعیت", width=10, justify="center")
    pkg_table.add_column("نسخه", justify="left", width=20)
    pkg_table.add_column("نیاز", width=8, justify="center")

    for pkg in _PYTHON_PACKAGES:
        found, version = _check_python_package(pkg["import"])
        required = pkg["required"] == "true"

        if found:
            status = "[green]✅[/]"
        elif required:
            status = "[red]❌[/]"
            all_ok = False
            missing_packages.append(pkg["name"])
        else:
            status = "[yellow]⚠[/]"
            missing_packages.append(pkg["name"])

        need = "[red]اجباری[/]" if required else "[dim]اختیاری[/]"
        pkg_table.add_row(pkg["name"], status, version, need)

    console.print(pkg_table)

    # ─── Python version ──────────────────
    console.print(f"\n[dim]🐍 Python: {sys.version}[/]")
    console.print(f"[dim]📂 venv: {sys.prefix}[/]")

    # ─── نتیجه ───────────────────────────
    console.print()
    if all_ok:
        console.print(
            Panel(
                "[bold green]✅ همه وابستگی\u200cهای اجباری نصب هستند![/]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "[bold red]❌ برخی وابستگی\u200cهای اجباری یافت نشدند![/]\n\n"
                "برای نصب پکیج\u200cهای Python:\n"
                f"  [bold]pip install {' '.join(missing_packages)}[/]",
                border_style="red",
            )
        )

    # ─── نصب خودکار ──────────────────────
    if fix and missing_packages:
        console.print("\n[bold]🔧 تلاش برای نصب خودکار...[/]\n")
        for pkg_name in missing_packages:
            try:
                console.print(f"  📦 نصب {pkg_name}...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg_name],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                console.print(f"  [green]✅ {pkg_name} نصب شد.[/]")
            except subprocess.CalledProcessError:
                console.print(f"  [red]❌ خطا در نصب {pkg_name}.[/]")
