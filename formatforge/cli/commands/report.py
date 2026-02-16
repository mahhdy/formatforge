"""
دستور report — گزارش مرکزی تبدیل‌ها
Report command: view conversion history and statistics.
"""

from rich.console import Console

console = Console()


def run_report(
    *,
    last: int = 10,
    stats: bool = False,
    search: str | None = None,
    export_fmt: str | None = None,
    output: str | None = None,
    verbose: bool = False,
) -> None:
    """اجرای گزارش"""
    console.print("[bold blue]📊 گزارش مرکزی[/bold blue]")
    console.print("[dim]  (پیاده‌سازی در اسپرینت S11)[/dim]")
    # TODO: S11 — Central log & reports