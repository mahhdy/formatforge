"""
FormatForge - CLI Entry Point
نقطه ورود اصلی خط فرمان

Usage:
    formatforge --help
    python -m formatforge.cli --help
"""

from __future__ import annotations

import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from formatforge.cli.commands.scan import scan
from formatforge.cli.commands.convert import convert
from formatforge.cli.commands.test_cmd import test
from formatforge.cli.commands.deploy import deploy
from formatforge.cli.commands.report import report
from formatforge.cli.commands.doctor import doctor
from formatforge.cli.commands.run import run
from formatforge.cli.commands.config_cmd import config


# ─────────────────────────────────────────────
# Constants / ثابت‌ها
# ─────────────────────────────────────────────

APP_NAME = "FormatForge"
APP_VERSION = "0.1.0"

console = Console()

_BANNER = r"""
  ███████╗ ██████╗ ██████╗ ███╗   ███╗ █████╗ ████████╗
  ██╔════╝██╔═══██╗██╔══██╗████╗ ████║██╔══██╗╚══██╔══╝
  █████╗  ██║   ██║██████╔╝██╔████╔██║███████║   ██║
  ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║██╔══██║   ██║
  ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║   ██║
  ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝
         ███████╗ ██████╗ ██████╗  ██████╗ ███████╗
         ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
         █████╗  ██║   ██║██████╔╝██║  ███╗█████╗
         ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝
         ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
         ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
"""


# ─────────────────────────────────────────────
# Main group / گروه اصلی
# ─────────────────────────────────────────────

@click.group(
    name="formatforge",
    invoke_without_command=True,
)
@click.version_option(
    version=APP_VERSION,
    prog_name=APP_NAME,
    message=f"%(prog)s نسخه %(version)s",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="نمایش جزئیات بیشتر / Verbose output",
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    help="غیرفعال کردن رنگ / Disable colored output",
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=False),
    default=None,
    help="مسیر فایل تنظیمات / Config file path",
)
@click.pass_context
def app(
    ctx: click.Context,
    verbose: bool,
    no_color: bool,
    config: Optional[str],
) -> None:
    """
    ⚒️  FormatForge — ابزار تبدیل اسناد به MDX فارسی

    تبدیل LaTeX, Markdown, HTML به MDX با پشتیبانی کامل فارسی.

    \b
    دستورات اصلی:
      scan      اسکن ورودی
      convert   تبدیل سند
      test      تست کیفیت
      deploy    استقرار خروجی
      run       اجرای کامل (scan→convert→test→deploy)
      report    گزارش‌ها
      config    مدیریت تنظیمات
      doctor    بررسی سلامت سیستم
    """
    # ذخیره تنظیمات در context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["no_color"] = no_color
    ctx.obj["config_path"] = config
    ctx.obj["console"] = Console(no_color=no_color)

    # اگر بدون دستور صدا زده شد، بنر نمایش بده
    if ctx.invoked_subcommand is None:
        con = ctx.obj["console"]
        con.print(
            Panel(
                Text(_BANNER, style="bold cyan"),
                title=f"[bold white]{APP_NAME} v{APP_VERSION}[/]",
                subtitle="[dim]ابزار تبدیل اسناد به MDX فارسی[/]",
                border_style="cyan",
            )
        )
        con.print()
        con.print(
            "  برای راهنما: [bold green]formatforge --help[/]"
        )
        con.print(
            "  شروع سریع:  [bold green]formatforge run ./input/[/]"
        )
        con.print()


# ─────────────────────────────────────────────
# Register commands / ثبت دستورات
# ─────────────────────────────────────────────

app.add_command(scan)
app.add_command(convert)
app.add_command(test)
app.add_command(deploy)
app.add_command(report)
app.add_command(doctor)
app.add_command(run)
app.add_command(config)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main() -> None:
    """نقطه ورود اصلی."""
    try:
        app()
    except Exception as exc:
        console.print(f"[bold red]❌ خطای غیرمنتظره:[/] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
