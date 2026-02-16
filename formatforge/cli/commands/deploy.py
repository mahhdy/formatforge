"""
دستور deploy — استقرار خروجی در وب‌سایت
Deploy command: copy MDX files and assets to website directory.
"""

from rich.console import Console

console = Console()


def run_deploy(
    source: str,
    target: str,
    *,
    git_commit: bool = False,
    open_editor: bool = False,
    verbose: bool = False,
) -> None:
    """اجرای استقرار"""
    console.print(f"[bold blue]🚀 استقرار:[/bold blue] {source} → {target}")
    console.print("[dim]  (پیاده‌سازی در اسپرینت S11)[/dim]")
    # TODO: S11 — Deployer