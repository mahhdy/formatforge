"""
FormatForge - Deploy Command
دستور استقرار خروجی

Deploy converted MDX files to target directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import shutil

import click
from rich.console import Console
from rich.panel import Panel


@click.command(name="deploy")
@click.argument(
    "source_path",
    type=click.Path(exists=True),
)
@click.option(
    "--target", "-t",
    type=click.Path(),
    default=None,
    help="پوشه مقصد / Target directory",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="ایجاد بکاپ / Create backup",
)
@click.option(
    "--overwrite",
    type=click.Choice(["ask", "yes", "no", "rename"], case_sensitive=False),
    default="ask",
    help="رفتار با فایل موجود / Overwrite behavior",
)
@click.option(
    "--git-commit",
    is_flag=True,
    default=False,
    help="کامیت خودکار در Git / Auto git commit",
)
@click.option(
    "--git-push",
    is_flag=True,
    default=False,
    help="پوش خودکار به Git / Auto git push",
)
@click.option(
    "--open-editor",
    is_flag=True,
    default=False,
    help="باز کردن در ادیتور / Open in editor after deploy",
)
@click.option(
    "--framework",
    type=click.Choice(["next", "astro", "gatsby", "docusaurus"], case_sensitive=False),
    default="next",
    help="فریم‌ورک مقصد / Target framework",
)
@click.pass_context
def deploy(
    ctx: click.Context,
    source_path: str,
    target: Optional[str],
    backup: bool,
    overwrite: str,
    git_commit: bool,
    git_push: bool,
    open_editor: bool,
    framework: str,
) -> None:
    """
    🚀 استقرار خروجی MDX در پوشه مقصد

    \b
    مثال‌ها:
      formatforge deploy ./output/ --target C:/Projects/blog/
      formatforge deploy ./output/ --git-commit --git-push
      formatforge deploy ./output/ --overwrite rename
      formatforge deploy ./output/ --framework astro
    """
    console: Console = ctx.obj.get("console", Console())
    src = Path(source_path).resolve()
    tgt = Path(target).resolve() if target else Path("./deploy_output").resolve()

    # ─── هدر ──────────────────────────────
    console.print()
    console.print(
        Panel(
            f"[bold]منبع:[/]     {src}\n"
            f"[bold]مقصد:[/]     {tgt}\n"
            f"[bold]فریم‌ورک:[/] {framework}\n"
            f"[bold]بکاپ:[/]     {'بله' if backup else 'خیر'}\n"
            f"[bold]بازنویسی:[/] {overwrite}\n"
            f"[bold]Git commit:[/] {'بله' if git_commit else 'خیر'}\n"
            f"[bold]Git push:[/]   {'بله' if git_push else 'خیر'}",
            title="[bold blue]🚀 استقرار[/]",
            border_style="blue",
        )
    )

    # ─── تأیید ───────────────────────────
    console.print()
    if not click.confirm("  آیا از استقرار اطمینان دارید؟", default=True):
        console.print("[yellow]  لغو شد.[/]")
        return

    # ─── استقرار ─────────────────────────
    with console.status("[bold green]در حال استقرار...", spinner="dots"):
        try:
            from formatforge.core.deployer import Deployer
            
            # Initialize deployer
            deployer = Deployer(framework=framework)
            
            # Collect MDX files from source
            mdx_files = list(src.rglob("*.mdx"))
            
            if not mdx_files:
                console.print("[yellow]هیچ فایل MDX یافت نشد![/]")
                return
            
            # Create backup if requested
            if backup and tgt.exists():
                backup_dir = tgt.parent / f"{tgt.name}_backup"
                console.print(f"[dim]ایجاد بکاپ در {backup_dir}[/]")
                shutil.copytree(tgt, backup_dir, dirs_exist_ok=True)
            
            # Deploy each file
            deployed_count = 0
            for mdx_file in mdx_files:
                # Calculate relative path for slug
                rel_path = mdx_file.relative_to(src)
                slug = rel_path.stem
                
                # Deploy single file
                deployer.deploy_single(
                    source_file=mdx_file,
                    dest_dir=tgt,
                    slug=slug,
                )
                deployed_count += 1
            
            console.print(f"[green]✓ {deployed_count} فایل مستقر شد[/]")
            
        except Exception as e:
            console.print(f"[red]خطا در استقرار: {e}[/]")
            return

    console.print(
        Panel(
            f"[green]✅ استقرار کامل شد![/]\n\n"
            f"  مقصد: {tgt}\n"
            f"  فایل‌ها: {deployed_count}",
            title="[bold green]نتیجه[/]",
            border_style="green",
        )
    )
    
    # Git operations
    if git_commit:
        console.print("\n[dim]در حال آماده‌سازی Git...[/]")
        # TODO: Implement git commit
        console.print("[dim]⏳ در انتظار پیاده‌سازی git commit[/]")
    
    if git_push:
        console.print("[dim]در حال پush...[/]")
        # TODO: Implement git push
        console.print("[dim]⏳ در انتظار پیاده‌سازی git push[/]")
