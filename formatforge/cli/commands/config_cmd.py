"""
FormatForge - Config Command
مدیریت تنظیمات

Initialize, show, and modify configuration.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax


_DEFAULT_CONFIG_SOURCE = Path(__file__).resolve().parent.parent.parent.parent / "config" / "default_config.yaml"
_USER_CONFIG_TARGET = Path("formatforge.yaml")


@click.group(name="config")
@click.pass_context
def config(ctx: click.Context) -> None:
    """
    ⚙️ مدیریت تنظیمات FormatForge

    \b
    زیردستورات:
      init     ساخت فایل تنظیمات کاربر
      show     نمایش تنظیمات فعلی
      set      تنظیم یک مقدار
      website  تنظیم وب‌سایت (wizard)
    """
    pass


@config.command(name="init")
@click.option(
    "--force", "-f",
    is_flag=True,
    default=False,
    help="بازنویسی فایل موجود / Overwrite existing",
)
@click.pass_context
def config_init(ctx: click.Context, force: bool) -> None:
    """
    📝 ساخت فایل تنظیمات کاربر

    \b
    مثال:
      formatforge config init
      formatforge config init --force
    """
    console: Console = ctx.obj.get("console", Console())
    target = _USER_CONFIG_TARGET.resolve()

    if target.exists() and not force:
        console.print(
            f"[yellow]⚠ فایل {target} از قبل وجود دارد. "
            "از --force برای بازنویسی استفاده کنید.[/]"
        )
        return

    if _DEFAULT_CONFIG_SOURCE.exists():
        shutil.copy2(_DEFAULT_CONFIG_SOURCE, target)
        console.print(
            f"[green]✅ فایل تنظیمات ساخته شد: {target}[/]"
        )
    else:
        console.print(
            f"[red]❌ فایل پیش‌فرض یافت نشد: {_DEFAULT_CONFIG_SOURCE}[/]"
        )


@config.command(name="show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """
    👁 نمایش تنظیمات فعلی

    \b
    مثال:
      formatforge config show
    """
    console: Console = ctx.obj.get("console", Console())

    try:
        from formatforge.config import get_config
        cfg = get_config()
        yaml_str = cfg.model_dump_json(indent=2)

        console.print()
        console.print(
            Panel(
                Syntax(yaml_str, "json", theme="monokai", line_numbers=False),
                title="[bold cyan]⚙️ تنظیمات فعلی[/]",
                border_style="cyan",
            )
        )
    except Exception as exc:
        console.print(f"[red]❌ خطا در بارگذاری تنظیمات: {exc}[/]")


@config.command(name="set")
@click.argument("key", type=str)
@click.argument("value", type=str)
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """
    ✏️ تنظیم یک مقدار

    \b
    مثال:
      formatforge config set conversion.math.engine katex
      formatforge config set general.language en
    """
    console: Console = ctx.obj.get("console", Console())

    # TODO: پیاده‌سازی تغییر مقدار در YAML
    console.print(
        f"[green]✅ تنظیم:[/] [bold]{key}[/] = [bold]{value}[/]\n"
        f"[dim]⏳ در انتظار پیاده\u200cسازی کامل[/]"
    )


@config.command(name="website")
@click.pass_context
def config_website(ctx: click.Context) -> None:
    """
    🌐 تنظیم وب‌سایت (wizard)

    \b
    مثال:
      formatforge config website
    """
    console: Console = ctx.obj.get("console", Console())

    console.print("\n[bold cyan]🌐 تنظیم وب\u200cسایت[/]\n")

    target_dir = click.prompt(
        "  پوشه مقصد محتوا",
        default="./content/",
    )
    base_url = click.prompt(
        "  آدرس وب\u200cسایت",
        default="https://example.com",
    )
    framework = click.prompt(
        "  فریمورک",
        type=click.Choice(["nextjs", "astro", "gatsby", "docusaurus"]),
        default="nextjs",
    )

    console.print(
        Panel(
            f"  پوشه:     {target_dir}\n"
            f"  آدرس:     {base_url}\n"
            f"  فریمورک:  {framework}",
            title="[bold]خلاصه[/]",
            border_style="cyan",
        )
    )
    console.print("[dim]⏳ در انتظار پیاده\u200cسازی کامل[/]")
