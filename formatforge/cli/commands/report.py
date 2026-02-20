"""
FormatForge - Report Command
دستور گزارش‌ها

View, search, and export conversion history and reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# Store for conversion results (in production, this would be a database)
_reports_cache: list[dict] = []


@click.command(name="report")
@click.option(
    "--last", "-n",
    type=click.IntRange(1, 1000),
    default=10,
    help="تعداد آخرین گزارش‌ها / Number of recent reports",
)
@click.option(
    "--export",
    "export_format",
    type=click.Choice(["yaml", "json", "csv", "html"], case_sensitive=False),
    default=None,
    help="فرمت خروجی / Export format",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="مسیر فایل خروجی / Output file path",
)
@click.option(
    "--stats",
    is_flag=True,
    default=False,
    help="نمایش آمار کلی / Show overall statistics",
)
@click.option(
    "--search", "-s",
    type=str,
    default=None,
    help="جستجو در گزارش‌ها / Search reports",
)
@click.option(
    "--id",
    type=str,
    default=None,
    help="شناسه گزارش خاص / Specific report ID",
)
@click.pass_context
def report(
    ctx: click.Context,
    last: int,
    export_format: Optional[str],
    output: Optional[str],
    stats: bool,
    search: Optional[str],
    report_id: Optional[str],
) -> None:
    """
    📊 مشاهده و جستجوی گزارش‌های تبدیل

    \b
    مثال‌ها:
      formatforge report
      formatforge report --last 20
      formatforge report --stats
      formatforge report --search "منطق"
      formatforge report --export csv -o report.csv
      formatforge report --id conv_abc123
    """
    console: Console = ctx.obj.get("console", Console())
    console.print()

    # Load reports from output directory
    reports = _load_reports()
    
    # Show specific report
    if report_id:
        _show_single_report(console, reports, report_id)
        return

    # ─── آمار کلی ────────────────────────
    if stats:
        _show_statistics(console, reports)
        return

    # ─── جستجو ───────────────────────────
    if search:
        reports = _filter_reports(reports, search)
        console.print(
            f"[bold]🔎 جستجو:[/] «{search}» - {len(reports)} نتیجه\n"
        )

    # ─── جدول گزارش ─────────────────────
    display_reports = reports[:last]
    
    if not display_reports:
        console.print(
            Panel(
                "[dim]هیچ گزارشی یافت نشد.[/]\n\n"
                "⏳ در انتظار اجرای تبدیل...",
                title="[bold]📋 گزارش‌ها[/]",
                border_style="dim",
            )
        )
        return

    table = Table(
        title=f"📋 {len(display_reports)} گزارش اخیر",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=5, justify="center")
    table.add_column("شناسه", width=15)
    table.add_column("تاریخ", width=18)
    table.add_column("اسناد", width=8, justify="center")
    table.add_column("موفق", width=8, justify="center")
    table.add_column("کیفیت", width=8, justify="center")

    for i, r in enumerate(display_reports, 1):
        table.add_row(
            str(i),
            r.get("conversion_id", "—")[:12],
            r.get("timestamp", "—")[:16],
            str(r.get("stats", {}).get("total_documents", 0)),
            f"[green]{r.get('stats', {}).get('successful', 0)}[/]",
            f"{r.get('stats', {}).get('average_quality_score', 0):.0f}%",
        )

    console.print(table)

    # ─── خروجی ───────────────────────────
    if export_format and output:
        _export_report(console, display_reports, export_format, output)


def _load_reports() -> list[dict]:
    """Load reports from output directory."""
    reports = []
    output_dir = Path("output")
    
    if not output_dir.exists():
        return reports
    
    # Look for JSON report files
    for json_file in output_dir.glob("*report*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    reports.extend(data)
                elif isinstance(data, dict):
                    reports.append(data)
        except Exception:
            continue
    
    # Also check for individual conversion results
    for result_file in output_dir.glob("*.json"):
        if "report" in result_file.name:
            continue
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "conversion_id" in data:
                    reports.append(data)
        except Exception:
            continue
    
    # Sort by timestamp
    reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return reports


def _show_single_report(
    console: Console,
    reports: list[dict],
    report_id: str,
) -> None:
    """Show details of a specific report."""
    for r in reports:
        if r.get("conversion_id") == report_id:
            console.print(
                Panel(
                    f"[bold]شناسه:[/] {r.get('conversion_id', 'N/A')}\n"
                    f"[bold]زمان:[/] {r.get('timestamp', 'N/A')}\n"
                    f"[bold]وضعیت:[/] {r.get('status', 'N/A')}\n\n"
                    f"[bold]آمار:[/]\n"
                    f"  کل اسناد: {r.get('stats', {}).get('total_documents', 0)}\n"
                    f"  موفق: {r.get('stats', {}).get('successful', 0)}\n"
                    f"  ناموفق: {r.get('stats', {}).get('failed', 0)}\n"
                    f"  کیفیت: {r.get('stats', {}).get('average_quality_score', 0):.1f}%",
                    title=f"[bold]📋 گزارش {report_id[:12]}[/]",
                    border_style="magenta",
                )
            )
            return
    
    console.print(f"[red]گزارش با شناسه {report_id} یافت نشد.[/]")


def _show_statistics(console: Console, reports: list[dict]) -> None:
    """Show overall statistics."""
    if not reports:
        console.print(
            Panel(
                "[dim]هیچ داده‌ای برای نمایش آمار موجود نیست.[/]",
                title="[bold magenta]📈 آمار کلی[/]",
                border_style="magenta",
            )
        )
        return
    
    total_docs = sum(r.get("stats", {}).get("total_documents", 0) for r in reports)
    total_success = sum(r.get("stats", {}).get("successful", 0) for r in reports)
    total_failed = sum(r.get("stats", {}).get("failed", 0) for r in reports)
    
    quality_scores = [
        r.get("stats", {}).get("average_quality_score", 0)
        for r in reports
        if r.get("stats", {}).get("average_quality_score", 0) > 0
    ]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    durations = [
        r.get("stats", {}).get("duration_seconds", 0)
        for r in reports
    ]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    console.print(
        Panel(
            f"  📈 کل تبدیل‌ها:      [bold]{len(reports)}[/]\n"
            f"  📄 کل اسناد:        [bold]{total_docs}[/]\n"
            f"  ✅ موفق:             [bold]{total_success}[/]\n"
            f"  ❌ ناموفق:           [bold]{total_failed}[/]\n"
            f"  📊 میانگین کیفیت:   [bold]{avg_quality:.1f}%[/]\n"
            f"  ⏱  میانگین زمان:    [bold]{avg_duration:.1f}s[/]",
            title="[bold magenta]📈 آمار کلی[/]",
            border_style="magenta",
        )
    )


def _filter_reports(reports: list[dict], search_term: str) -> list[dict]:
    """Filter reports by search term."""
    search_lower = search_term.lower()
    filtered = []
    
    for r in reports:
        # Search in conversion_id, notes, documents
        if search_lower in r.get("conversion_id", "").lower():
            filtered.append(r)
            continue
        
        for note in r.get("notes", []):
            if search_lower in note.lower():
                filtered.append(r)
                break
        
        for doc in r.get("documents", []):
            if search_lower in doc.get("source_path", "").lower():
                filtered.append(r)
                break
    
    return filtered


def _export_report(
    console: Console,
    reports: list[dict],
    export_format: str,
    output_path: str,
) -> None:
    """Export reports to file."""
    output = Path(output_path)
    
    try:
        if export_format == "json":
            with open(output, "w", encoding="utf-8") as f:
                json.dump(reports, f, ensure_ascii=False, indent=2)
        
        elif export_format == "csv":
            import csv
            with open(output, "w", encoding="utf-8", newline="") as f:
                if reports:
                    fieldnames = ["conversion_id", "timestamp", "status", 
                                 "total_documents", "successful", "failed", 
                                 "average_quality_score"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in reports:
                        row = {
                            "conversion_id": r.get("conversion_id", ""),
                            "timestamp": r.get("timestamp", ""),
                            "status": r.get("status", ""),
                        }
                        row.update(r.get("stats", {}))
                        writer.writerow(row)
        
        elif export_format == "html":
            html = _generate_html_report(reports)
            with open(output, "w", encoding="utf-8") as f:
                f.write(html)
        
        console.print(
            f"\n[green]✓ گزارش در {output} ذخیره شد.[/]"
        )
        
    except Exception as e:
        console.print(f"[red]خطا در ذخیره گزارش: {e}[/]")


def _generate_html_report(reports: list[dict]) -> str:
    """Generate HTML report."""
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>FormatForge Reports</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .success { color: green; }
        .failed { color: red; }
    </style>
</head>
<body>
    <h1>FormatForge Reports</h1>
    <table>
        <tr>
            <th>ID</th>
            <th>Timestamp</th>
            <th>Status</th>
            <th>Documents</th>
            <th>Successful</th>
            <th>Failed</th>
            <th>Quality</th>
        </tr>
"""
    for r in reports:
        stats = r.get("stats", {})
        html += f"""        <tr>
            <td>{r.get("conversion_id", "N/A")[:12]}</td>
            <td>{r.get("timestamp", "N/A")[:16]}</td>
            <td>{r.get("status", "N/A")}</td>
            <td>{stats.get("total_documents", 0)}</td>
            <td class="success">{stats.get("successful", 0)}</td>
            <td class="failed">{stats.get("failed", 0)}</td>
            <td>{stats.get("average_quality_score", 0):.1f}%</td>
        </tr>
"""
    
    html += """    </table>
</body>
</html>"""
    return html
