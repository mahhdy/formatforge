"""
دستور run — اجرای کامل خط لوله
Run command: execute full pipeline (scan → convert → test → deploy).
"""

from rich.console import Console

console = Console()


def run_pipeline(
    input_path: str,
    *,
    output: str | None = None,
    target: str | None = None,
    quality_min: int = 80,
    interactive: bool = True,
    auto_fix: bool = False,
    verbose: bool = False,
) -> None:
    """اجرای کامل خط لوله"""
    console.print(f"[bold blue]⚡ اجرای کامل:[/bold blue] {input_path}")
    console.print("[dim]  (پیاده‌سازی در اسپرینت S12)[/dim]")
    # TODO: S12 — Full pipeline