"""
دستور init-components — تولید کامپوننت‌های MDX
Init-components command: generate MDX components for website.
"""

from rich.console import Console

console = Console()


def run_init_components(
    *,
    framework: str = "next",
    output: str = "./components/mdx",
    typescript: bool = True,
    verbose: bool = False,
) -> None:
    """تولید کامپوننت‌های MDX"""
    console.print(f"[bold blue]🧩 تولید کامپوننت‌ها:[/bold blue] {framework} → {output}")
    console.print("[dim]  (پیاده‌سازی در اسپرینت S12)[/dim]")
    # TODO: S12 — Component generation