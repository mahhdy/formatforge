"""
دستور convert — تبدیل فایل(ها) به MDX
Convert command: transform documents to MDX format.
"""

from rich.console import Console

console = Console()


def run_convert(
    input_path: str,
    *,
    output: str | None = None,
    fmt: str | None = None,
    quality_min: int = 80,
    interactive: bool = True,
    auto_fix: bool = False,
    verbose: bool = False,
) -> None:
    """اجرای تبدیل"""
    console.print(f"[bold blue]🔄 تبدیل:[/bold blue] {input_path}")
    console.print("[dim]  (پیاده‌سازی در اسپرینت S06-S09)[/dim]")
    # TODO: S06-S09 — Converter implementations