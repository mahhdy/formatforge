"""
دستور scan — اسکن و شناسایی ورودی
Scan command: detect format, encoding, structure, dependencies.
"""

from rich.console import Console

console = Console()


def run_scan(input_path: str, *, recursive: bool = False, verbose: bool = False) -> None:
    """اجرای اسکن ورودی"""
    console.print(f"[bold blue]🔍 اسکن:[/bold blue] {input_path}")
    console.print("[dim]  (پیاده‌سازی در اسپرینت S02)[/dim]")
    # TODO: S02 — Scanner implementation