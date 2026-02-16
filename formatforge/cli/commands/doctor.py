"""
دستور doctor — بررسی سلامت سیستم
Doctor command: check all dependencies and external tools.
"""

import shutil
import subprocess
import sys

from rich.console import Console
from rich.table import Table

console = Console()


def _check_command(name: str, version_flag: str = "--version") -> tuple[bool, str]:
    """بررسی وجود یک ابزار خط فرمان"""
    path = shutil.which(name)
    if not path:
        return False, "not found"
    try:
        result = subprocess.run(
            [name, version_flag],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip().split("\n")[0][:60]
        if not version:
            version = result.stderr.strip().split("\n")[0][:60]
        return True, version or "found"
    except Exception:
        return True, f"found at {path}"


def _check_python_package(name: str) -> tuple[bool, str]:
    """بررسی وجود یک پکیج Python"""
    try:
        mod = __import__(name.replace("-", "_"))
        version = getattr(mod, "__version__", "installed")
        return True, str(version)
    except ImportError:
        return False, "not installed"


def run_doctor(*, verbose: bool = False) -> None:
    """بررسی سلامت سیستم"""
    console.print("\n[bold blue]🩺 FormatForge Doctor[/bold blue]\n")

    # ── Python ──
    console.print("[bold]Python:[/bold]")
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    icon = "✅" if py_ok else "❌"
    console.print(f"  {icon} Python {py_ver} {'(≥3.11 ✓)' if py_ok else '(need ≥3.11)'}")

    # ── ابزارهای خارجی ──
    console.print("\n[bold]ابزارهای خارجی:[/bold]")

    tools = [
        ("pandoc",      "--version",  "winget install JohnMacFarlane.Pandoc",      True),
        ("xelatex",     "--version",  "Install TeX Live: tug.org/texlive",         True),
        ("biber",       "--version",  "Included in TeX Live",                      False),
        ("dvisvgm",     "--version",  "Included in TeX Live",                      False),
        ("node",        "--version",  "winget install OpenJS.NodeJS",              True),
        ("mmdc",        "--version",  "npm install -g @mermaid-js/mermaid-cli",    False),
        ("magick",      "--version",  "winget install ImageMagick.ImageMagick",    False),
        ("svgo",        "--version",  "npm install -g svgo",                       False),
        ("tesseract",   "--version",  "winget install UB-Mannheim.TesseractOCR",   False),
    ]

    table = Table(show_header=True, header_style="bold")
    table.add_column("وضعیت", width=4, justify="center")
    table.add_column("ابزار", width=12)
    table.add_column("نسخه / وضعیت", width=40)
    table.add_column("ضروری", width=6, justify="center")

    all_required_ok = True
    for name, flag, hint, required in tools:
        found, info = _check_command(name, flag)
        icon = "✅" if found else ("❌" if required else "⚠️")
        req_str = "بله" if required else "خیر"
        if not found:
            info = f"[red]not found[/red] → {hint}"
            if required:
                all_required_ok = False
        table.add_row(icon, name, info, req_str)

    console.print(table)

    # ── پکیج‌های Python ──
    console.print("\n[bold]پکیج‌های Python:[/bold]")

    packages = [
        ("click", True),
        ("rich", True),
        ("pydantic", True),
        ("yaml", True),
        ("bs4", True),
        ("lxml", True),
        ("docx", False),
        ("fitz", False),
        ("PIL", True),
        ("jinja2", True),
        ("chardet", True),
        ("loguru", True),
    ]

    pkg_table = Table(show_header=True, header_style="bold")
    pkg_table.add_column("وضعیت", width=4, justify="center")
    pkg_table.add_column("پکیج", width=20)
    pkg_table.add_column("نسخه", width=20)

    for name, required in packages:
        found, ver = _check_python_package(name)
        icon = "✅" if found else ("❌" if required else "⚠️")
        pkg_table.add_row(icon, name, ver if found else "[red]missing[/red]")

    console.print(pkg_table)

    # ── نتیجه ──
    console.print()
    if all_required_ok:
        console.print("[bold green]✅ تمام ابزارهای ضروری نصب هستند.[/bold green]")
    else:
        console.print("[bold red]❌ برخی ابزارهای ضروری نصب نیستند.[/bold red]")
        console.print("   لطفاً ابزارهای مشخص‌شده را نصب کنید.")

    console.print()