"""
نقطه ورود CLI — FormatForge Command Line Interface.
اجرا: python -m formatforge [COMMAND]
"""

import click
from rich.console import Console
from rich.panel import Panel

from formatforge import __version__

console = Console()


class AliasedGroup(click.Group):
    """گروه Click با پشتیبانی از مخفف دستورات"""

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        # Exact match
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        # Prefix match
        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        else:
            ctx.fail(f"Ambiguous command '{cmd_name}'. Could be: {', '.join(sorted(matches))}")
            return None


@click.group(cls=AliasedGroup, invoke_without_command=True)
@click.version_option(__version__, prog_name="FormatForge")
@click.option("--verbose", "-v", is_flag=True, help="نمایش جزئیات بیشتر")
@click.option("--config", "-c", type=click.Path(), help="مسیر فایل تنظیمات")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: str | None) -> None:
    """🔄 FormatForge — ابزار جامع تبدیل اسناد به MDX

    تبدیل LaTeX, Markdown, HTML و سایر فرمت‌ها به MDX
    با پشتیبانی کامل از زبان فارسی و محتوای دوزبانه.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config

    if ctx.invoked_subcommand is None:
        _show_welcome()


def _show_welcome() -> None:
    """نمایش پیام خوش‌آمدگویی"""
    console.print(
        Panel.fit(
            f"[bold blue]FormatForge[/bold blue] v{__version__}\n\n"
            "[dim]ابزار جامع تبدیل اسناد چندفرمتی به MDX[/dim]\n"
            "[dim]با پشتیبانی کامل فارسی / RTL / نیم‌فاصله[/dim]\n\n"
            "برای راهنما: [green]formatforge --help[/green]\n"
            "بررسی سلامت: [green]formatforge doctor[/green]\n"
            "شروع سریع:  [green]formatforge run ./input/[/green]",
            title="🔄 FormatForge",
            border_style="blue",
        )
    )


# ──────────────── دستورات ────────────────

@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--recursive", "-r", is_flag=True, help="اسکن بازگشتی پوشه‌ها")
@click.pass_context
def scan(ctx: click.Context, input_path: str, recursive: bool) -> None:
    """🔍 اسکن و شناسایی ورودی

    بررسی فایل(ها)، تشخیص فرمت، encoding، ساختار و وابستگی‌ها.
    """
    from formatforge.cli.commands.scan import run_scan
    run_scan(input_path, recursive=recursive, verbose=ctx.obj["verbose"])


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="مسیر خروجی")
@click.option("--format", "-f", "fmt", type=str, help="فرمت ورودی (auto-detect)")
@click.option("--quality-min", type=int, default=80, help="حداقل امتیاز کیفیت")
@click.option("--interactive/--batch", default=True, help="حالت تعاملی/دسته‌ای")
@click.option("--auto-fix/--no-auto-fix", default=False, help="اصلاح خودکار مشکلات")
@click.pass_context
def convert(
    ctx: click.Context,
    input_path: str,
    output: str | None,
    fmt: str | None,
    quality_min: int,
    interactive: bool,
    auto_fix: bool,
) -> None:
    """🔄 تبدیل فایل(ها) به MDX

    تبدیل LaTeX, Markdown, HTML و سایر فرمت‌ها به MDX.
    """
    from formatforge.cli.commands.convert import run_convert
    run_convert(
        input_path,
        output=output,
        fmt=fmt,
        quality_min=quality_min,
        interactive=interactive,
        auto_fix=auto_fix,
        verbose=ctx.obj["verbose"],
    )


@cli.command("test")
@click.argument("path", type=click.Path(exists=True))
@click.option("--recursive", "-r", is_flag=True, help="تست بازگشتی")
@click.option("--visual/--no-visual", default=False, help="تست بصری (نیاز به Playwright)")
@click.option("--report-format", type=click.Choice(["text", "json", "html"]), default="text")
@click.pass_context
def test_cmd(ctx: click.Context, path: str, recursive: bool, visual: bool, report_format: str) -> None:
    """🧪 تست کیفیت خروجی MDX

    بررسی ساختار، محتوا، ریاضی، فارسی/RTL و لینک‌ها.
    """
    from formatforge.cli.commands.test_cmd import run_test
    run_test(path, recursive=recursive, visual=visual, report_format=report_format, verbose=ctx.obj["verbose"])


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--target", "-t", type=click.Path(), required=True, help="مسیر مقصد (وب‌سایت)")
@click.option("--git-commit/--no-git-commit", default=False, help="Git commit خودکار")
@click.option("--open-editor/--no-open-editor", default=False, help="باز کردن در ویرایشگر")
@click.pass_context
def deploy(ctx: click.Context, source: str, target: str, git_commit: bool, open_editor: bool) -> None:
    """🚀 استقرار خروجی در وب‌سایت

    کپی فایل‌های MDX و asset ها به مسیر مقصد.
    """
    from formatforge.cli.commands.deploy import run_deploy
    run_deploy(source, target, git_commit=git_commit, open_editor=open_editor, verbose=ctx.obj["verbose"])


@cli.command()
@click.option("--last", "-n", type=int, default=10, help="تعداد آخرین تبدیل‌ها")
@click.option("--stats", is_flag=True, help="نمایش آمار تجمعی")
@click.option("--search", "-s", type=str, help="جستجو در تبدیل‌ها")
@click.option("--export", "export_fmt", type=click.Choice(["yaml", "json", "csv"]), help="خروجی گزارش")
@click.option("--output", "-o", type=click.Path(), help="مسیر فایل خروجی")
@click.pass_context
def report(ctx: click.Context, last: int, stats: bool, search: str | None, export_fmt: str | None, output: str | None) -> None:
    """📊 گزارش مرکزی تبدیل‌ها

    مشاهده تاریخچه، آمار و جستجو در تبدیل‌های انجام‌شده.
    """
    from formatforge.cli.commands.report import run_report
    run_report(last=last, stats=stats, search=search, export_fmt=export_fmt, output=output, verbose=ctx.obj["verbose"])


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="مسیر خروجی")
@click.option("--target", "-t", type=click.Path(), help="مسیر استقرار (وب‌سایت)")
@click.option("--quality-min", type=int, default=80, help="حداقل امتیاز کیفیت")
@click.option("--interactive/--batch", default=True, help="حالت تعاملی/دسته‌ای")
@click.option("--auto-fix/--no-auto-fix", default=False, help="اصلاح خودکار")
@click.pass_context
def run(
    ctx: click.Context,
    input_path: str,
    output: str | None,
    target: str | None,
    quality_min: int,
    interactive: bool,
    auto_fix: bool,
) -> None:
    """⚡ اجرای کامل خط لوله (scan → convert → test → deploy)

    دستور all-in-one: تمام مراحل را به ترتیب اجرا می‌کند.
    """
    from formatforge.cli.commands.run import run_pipeline
    run_pipeline(
        input_path,
        output=output,
        target=target,
        quality_min=quality_min,
        interactive=interactive,
        auto_fix=auto_fix,
        verbose=ctx.obj["verbose"],
    )


@cli.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """🩺 بررسی سلامت سیستم

    بررسی نصب بودن تمام وابستگی‌ها و ابزارهای خارجی.
    """
    from formatforge.cli.commands.doctor import run_doctor
    run_doctor(verbose=ctx.obj["verbose"])


@cli.command("init-components")
@click.option("--framework", type=click.Choice(["next", "astro", "gatsby"]), default="next")
@click.option("--output", "-o", type=click.Path(), required=True, help="مسیر خروجی کامپوننت‌ها")
@click.option("--typescript/--javascript", default=True, help="TypeScript یا JavaScript")
@click.pass_context
def init_components(ctx: click.Context, framework: str, output: str, typescript: bool) -> None:
    """🧩 تولید کامپوننت‌های MDX برای وب‌سایت

    ساخت Theorem, Definition, Proof, Admonition, MermaidDiagram و سایر کامپوننت‌ها.
    """
    from formatforge.cli.commands.init_components import run_init_components
    run_init_components(framework=framework, output=output, typescript=typescript, verbose=ctx.obj["verbose"])


# ──────────────── نقطه ورود ────────────────

def main() -> None:
    """نقطه ورود اصلی"""
    cli(obj={})


if __name__ == "__main__":
    main()