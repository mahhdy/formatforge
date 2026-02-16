"""
FormatForge - Run Command (All-in-One)
دستور اجرای کامل خط لوله

Equivalent to: scan → metadata → convert → test → deploy
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table


_PIPELINE_STEPS = [
    ("🔍 اسکن ورودی", "scan"),
    ("📋 استخراج متادیتا", "metadata"),
    ("🔄 تبدیل محتوا", "convert"),
    ("🧪 تست کیفیت", "test"),
    ("🚀 استقرار", "deploy"),
]


@click.command(name="run")
@click.argument(
    "input_path",
    type=click.Path(exists=True),
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="پوشه خروجی / Output directory",
)
@click.option(
    "--target", "-t",
    type=click.Path(),
    default=None,
    help="پوشه استقرار نهایی / Deploy target directory",
)
@click.option(
    "--quality-min", "-q",
    type=click.IntRange(0, 100),
    default=80,
    help="حداقل امتیاز کیفیت / Minimum quality score",
)
@click.option(
    "--skip-deploy",
    is_flag=True,
    default=False,
    help="بدون استقرار / Skip deployment step",
)
@click.option(
    "--skip-test",
    is_flag=True,
    default=False,
    help="بدون تست / Skip testing step",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="اجرای آزمایشی / Dry run without saving",
)
@click.pass_context
def run(
    ctx: click.Context,
    input_path: str,
    output: Optional[str],
    target: Optional[str],
    quality_min: int,
    skip_deploy: bool,
    skip_test: bool,
    dry_run: bool,
) -> None:
    """
    ⚡ اجرای کامل خط لوله (All-in-One)

    \b
    معادل: scan → metadata → convert → test → deploy

    \b
    مثال‌ها:
      formatforge run ./input/
      formatforge run ./input/ -o ./output/ -t ./blog/content/
      formatforge run ./input/ --skip-deploy --quality-min 90
      formatforge run ./input/ --dry-run
    """
    console: Console = ctx.obj.get("console", Console())
    src = Path(input_path).resolve()
    out = Path(output).resolve() if output else src.parent / "output"
    tgt = Path(target).resolve() if target else out

    # ─── هدر ──────────────────────────────
    console.print()

    steps_info = []
    for label, key in _PIPELINE_STEPS:
        if key == "test" and skip_test:
            steps_info.append(f"  [dim strikethrough]{label}[/] (رد شده)")
        elif key == "deploy" and skip_deploy:
            steps_info.append(f"  [dim strikethrough]{label}[/] (رد شده)")
        else:
            steps_info.append(f"  {label}")

    console.print(
        Panel(
            f"[bold]ورودی:[/]  {src}\n"
            f"[bold]خروجی:[/]  {out}\n"
            f"[bold]مقصد:[/]   {tgt}\n"
            f"[bold]کیفیت:[/]  حداقل {quality_min}%\n"
            f"[bold]آزمایشی:[/] {'بله' if dry_run else 'خیر'}\n\n"
            f"[bold]مراحل:[/]\n" + "\n".join(steps_info),
            title="[bold magenta]⚡ اجرای کامل خط لوله[/]",
            border_style="magenta",
        )
    )

    # ─── تأیید ───────────────────────────
    console.print()
    if not dry_run:
        if not click.confirm("  شروع اجرا؟", default=True):
            console.print("[yellow]  لغو شد.[/]")
            return

    # ─── اجرای خط لوله ───────────────────
    console.print()
    start_time = time.time()

    # تعیین مراحل فعال
    active_steps = []
    for label, key in _PIPELINE_STEPS:
        if key == "test" and skip_test:
            continue
        if key == "deploy" and skip_deploy:
            continue
        active_steps.append((label, key))

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )

    step_results: list[dict[str, str]] = []

    with progress:
        for label, key in active_steps:
            task = progress.add_task(label, total=100)

            # TODO: اتصال به core modules واقعی
            success = _run_pipeline_step(
                key=key,
                src=src,
                out=out,
                tgt=tgt,
                quality_min=quality_min,
                dry_run=dry_run,
                progress=progress,
                task_id=task,
            )

            status = "✅ موفق" if success else "❌ ناموفق"
            step_results.append({
                "label": label,
                "key": key,
                "status": status,
                "success": str(success),
            })

            if not success and key in ("scan", "convert"):
                console.print(
                    f"\n[bold red]❌ خطا در مرحله «{label}» — "
                    "خط لوله متوقف شد.[/]"
                )
                break

    elapsed = time.time() - start_time

    # ─── خلاصه نتایج ─────────────────────
    _display_pipeline_summary(
        console=console,
        results=step_results,
        elapsed=elapsed,
        dry_run=dry_run,
        output_dir=out,
        target_dir=tgt,
        quality_min=quality_min,
    )


def _run_pipeline_step(
    key: str,
    src: Path,
    out: Path,
    tgt: Path,
    quality_min: int,
    dry_run: bool,
    progress: Progress,
    task_id: int,
) -> bool:
    """
    اجرای یک مرحله از خط لوله (skeleton).
    Run a single pipeline step. Returns True on success.

    TODO: اتصال به ماژول‌های واقعی core
    """
    # شبیه‌سازی پیشرفت (placeholder)
    steps = 10
    for i in range(steps):
        time.sleep(0.08)
        progress.advance(task_id, 100 / steps)

    # TODO: جایگزینی با کد واقعی
    #
    # if key == "scan":
    #     from formatforge.core.scanner import InputScanner
    #     scanner = InputScanner(config=get_config())
    #     report = scanner.scan(src)
    #     return report is not None
    #
    # elif key == "metadata":
    #     from formatforge.core.metadata import MetadataExtractor
    #     extractor = MetadataExtractor(config=get_config())
    #     meta = extractor.extract(report)
    #     return meta is not None
    #
    # elif key == "convert":
    #     from formatforge.core.converters import get_converter
    #     converter = get_converter(report, config=get_config())
    #     result = converter.convert(report, meta, output_dir=out, dry_run=dry_run)
    #     return result.status == "completed"
    #
    # elif key == "test":
    #     from formatforge.core.quality import QualityTester
    #     tester = QualityTester(config=get_config())
    #     qr = tester.run(out)
    #     return qr.score >= quality_min
    #
    # elif key == "deploy":
    #     if dry_run:
    #         return True
    #     from formatforge.core.deployer import Deployer
    #     deployer = Deployer(config=get_config())
    #     return deployer.deploy(out, tgt)

    return True


def _display_pipeline_summary(
    console: Console,
    results: list[dict[str, str]],
    elapsed: float,
    dry_run: bool,
    output_dir: Path,
    target_dir: Path,
    quality_min: int,
) -> None:
    """
    نمایش خلاصه نتایج خط لوله.
    Display a summary table of pipeline results.
    """
    console.print()

    # جدول نتایج
    table = Table(
        title="📊 خلاصه اجرای خط لوله",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=4, justify="center")
    table.add_column("مرحله", width=25, justify="right", style="bold")
    table.add_column("وضعیت", width=15, justify="center")

    all_success = True
    for i, result in enumerate(results, 1):
        success = result["success"] == "True"
        if not success:
            all_success = False
        status_display = (
            "[green]✅ موفق[/]" if success else "[red]❌ ناموفق[/]"
        )
        table.add_row(str(i), result["label"], status_display)

    console.print(table)

    # آمار کلی
    total_steps = len(results)
    ok_steps = sum(1 for r in results if r["success"] == "True")

    console.print()

    if dry_run:
        border = "yellow"
        title_text = "[bold yellow]اجرای آزمایشی[/]"
        main_msg = "[yellow]⚠ حالت آزمایشی — هیچ فایلی ذخیره نشد.[/]"
    elif all_success:
        border = "green"
        title_text = "[bold green]✅ تکمیل موفق[/]"
        main_msg = "[bold green]تمام مراحل با موفقیت اجرا شدند![/]"
    else:
        border = "red"
        title_text = "[bold red]⚠ تکمیل ناقص[/]"
        main_msg = f"[red]{ok_steps} از {total_steps} مرحله موفق بود.[/]"

    summary_lines = [
        main_msg,
        "",
        f"  ⏱  مدت زمان:  [bold]{elapsed:.1f}[/] ثانیه",
        f"  📊 مراحل:     [bold]{ok_steps}/{total_steps}[/] موفق",
    ]

    if not dry_run:
        summary_lines.extend([
            f"  📁 خروجی:     {output_dir}",
            f"  🎯 مقصد:      {target_dir}",
        ])

    summary_lines.append(
        f"  🏆 حداقل کیفیت: {quality_min}%"
    )

    console.print(
        Panel(
            "\n".join(summary_lines),
            title=title_text,
            border_style=border,
        )
    )

    # پیشنهادات
    if all_success and not dry_run:
        console.print()
        console.print("  [dim]💡 پیشنهادات:[/]")
        console.print("     [dim]• بررسی خروجی:[/]  formatforge test " + str(output_dir))
        console.print("     [dim]• مشاهده گزارش:[/] formatforge report --last 1")
        console.print()
