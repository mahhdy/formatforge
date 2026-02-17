"""
FormatForge - Scan Command
دستور اسکن ورودی با نمایش Rich و تعامل کاربر

Scan input files/directories, display rich ScanReport,
interactive confirmation (T/E/F/A/Q), and auto-fix encoding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich.columns import Columns

from formatforge.core.scanner.scanner import (
    AssetInfo,
    DocumentEntry,
    ScanReport,
    ScanWarning,
    Scanner,
    fix_encoding_issues,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants / ثابت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_STRUCTURE_LABELS: dict[str, str] = {
    "single_doc": "📄 تک\u200cسند",
    "independent_articles": "📑 مقالات مستقل",
    "multi_chapter_book": "📚 کتاب چندفصلی",
    "related_collection": "📂 مجموعه مرتبط",
}

_FORMAT_ICONS: dict[str, str] = {
    "latex": "📄 LaTeX",
    "html": "🌐 HTML",
    "markdown": "📝 Markdown",
    "docx": "📃 DOCX",
    "pdf": "📕 PDF",
    "rst": "📋 RST",
    "asciidoc": "📓 AsciiDoc",
    "epub": "📖 EPUB",
    "notebook": "📒 Jupyter",
    "unknown": "❓ نامشخص",
}

_ROLE_ICONS: dict[str, str] = {
    "main_entry": "📄",
    "chapter": "📑",
    "appendix": "📎",
    "standalone": "📃",
}

_LANG_LABELS: dict[str, str] = {
    "fa": "🌐 فارسی",
    "en": "🌐 انگلیسی",
    "fa+en": "🌐 فارسی + انگلیسی",
    "unknown": "❓ نامشخص",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Click Command / دستور
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@click.command(name="scan")
@click.argument(
    "input_path",
    type=click.Path(exists=True),
)
@click.option(
    "--recursive", "-r",
    is_flag=True,
    default=False,
    help="اسکن بازگشتی زیرپوشه\u200cها / Scan subdirectories recursively",
)
@click.option(
    "--format", "-f",
    "input_format",
    type=click.Choice(
        ["auto", "latex", "markdown", "html"],
        case_sensitive=False,
    ),
    default="auto",
    help="فرمت ورودی (پیش\u200cفرض: تشخیص خودکار) / Input format",
)
@click.option(
    "--output-report", "-o",
    type=click.Path(),
    default=None,
    help="ذخیره گزارش اسکن در فایل / Save scan report to file",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="خروجی JSON به جای نمایش تعاملی / JSON output",
)
@click.pass_context
def scan(
    ctx: click.Context,
    input_path: str,
    recursive: bool,
    input_format: str,
    output_report: Optional[str],
    output_json: bool,
) -> None:
    """
    🔍 اسکن ورودی و شناسایی ساختار

    \b
    مثال‌ها:
      formatforge scan ./article.tex
      formatforge scan ./book/ --recursive
      formatforge scan ./archive.zip
      formatforge scan ./folder/ -f latex -o report.yaml
    """
    console: Console = ctx.obj.get("console", Console(force_terminal=True))
    verbose: bool = ctx.obj.get("verbose", False)
    resolved = Path(input_path).resolve()

    # ─── هدر ──────────────────────────────
    console.print()
    console.print(
        Panel(
            f"[bold]مسیر:[/] {resolved}\n"
            f"[bold]فرمت:[/] {input_format}\n"
            f"[bold]بازگشتی:[/] {'بله' if recursive else 'خیر'}",
            title="[bold cyan]🔍 اسکن ورودی[/]",
            border_style="cyan",
        )
    )

    # ─── اسکن ─────────────────────────────
    console.print()
    report: Optional[ScanReport] = None

    try:
        with console.status(
            "[bold green]در حال اسکن...",
            spinner="dots",
        ):
            scanner = Scanner()
            report = scanner.scan(
                resolved,
                recursive=recursive,
                format_hint=input_format,
            )
    except FileNotFoundError as exc:
        console.print(f"[bold red]❌ خطا:[/] {exc}")
        raise SystemExit(1)
    except Exception as exc:
        console.print(f"[bold red]❌ خطا در اسکن:[/] {exc}")
        if verbose:
            console.print_exception()
        raise SystemExit(1)

    # ─── خروجی JSON ──────────────────────
    if output_json:
        _print_json_report(console, report)
        if output_report:
            _save_report(console, report, output_report)
        return

    # ─── نمایش Rich ──────────────────────
    _display_report(console, report, verbose)

    # ─── ذخیره گزارش ─────────────────────
    if output_report:
        _save_report(console, report, output_report)

    # ─── تعامل با کاربر ──────────────────
    action = _interactive_prompt(console, report)

    if action == "Q":
        console.print("[yellow]لغو شد.[/]")
        report.cleanup()
        raise SystemExit(0)

    if action in ("F", "A"):
        _auto_fix_encoding(console, report)

    if action in ("T", "A"):
        console.print(
            "\n[bold green]✓ تأیید شد. "
            "آماده مرحله بعد (metadata).[/]"
        )

    if action == "E":
        console.print(
            "\n[bold yellow]📝 حالت ویرایش هنوز پیاده\u200cسازی "
            "نشده. لطفاً فایل گزارش را دستی ویرایش کنید.[/]"
        )

    # ذخیره report در context برای دستورات بعدی
    ctx.obj["scan_report"] = report


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Display Functions / توابع نمایش
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _display_report(
    console: Console,
    report: ScanReport,
    verbose: bool = False,
) -> None:
    """نمایش زیبای ScanReport با Rich."""
    # ─── جدول خلاصه ───────────────────
    _display_summary_table(console, report)

    # ─── درخت ساختار ──────────────────
    console.print()
    _display_structure_tree(console, report)

    # ─── جدول اسناد (verbose) ─────────
    if verbose and report.documents:
        console.print()
        _display_documents_table(console, report)

    # ─── assetها ──────────────────────
    if report.assets:
        console.print()
        _display_assets_table(console, report)

    # ─── هشدارها ──────────────────────
    if report.warnings:
        console.print()
        _display_warnings(console, report)


def _display_summary_table(
    console: Console, report: ScanReport,
) -> None:
    """جدول خلاصه اسکن."""
    structure = _STRUCTURE_LABELS.get(
        report.structure, report.structure,
    )
    fmt = _FORMAT_ICONS.get(
        report.primary_format or "unknown", "❓",
    )
    lang = _LANG_LABELS.get(
        report.primary_language, report.primary_language,
    )

    # شمارش encoding
    bom_count = sum(1 for d in report.documents if d.has_bom)
    no_bom = report.doc_count - bom_count
    enc_status = f"✅ UTF-8 ({bom_count} با BOM"
    if no_bom > 0:
        enc_status += f", [yellow]{no_bom} بدون BOM ⚠[/]"
    enc_status += ")"

    # شمارش asset
    img_count = sum(
        1 for a in report.assets if a.type.startswith("image")
    )
    bib_count = sum(
        1 for a in report.assets if a.type == "bibliography"
    )
    asset_parts = []
    if img_count:
        asset_parts.append(f"{img_count} تصویر")
    if bib_count:
        asset_parts.append(f"{bib_count} کتاب\u200cنامه")
    other = report.asset_count - img_count - bib_count
    if other > 0:
        asset_parts.append(f"{other} سایر")
    asset_str = " + ".join(asset_parts) if asset_parts else "—"

    table = Table(
        title="📊 نتیجه اسکن",
        show_header=False,
        border_style="dim",
        padding=(0, 2),
        min_width=50,
    )
    table.add_column("key", style="bold", justify="right", width=18)
    table.add_column("value", justify="left")

    table.add_row("نوع ساختار", structure)
    table.add_row("فرمت اصلی", fmt)
    table.add_row("زبان", lang)
    table.add_row("encoding", enc_status)
    table.add_row(
        "فایل\u200cها",
        f"{report.doc_count} سند + {asset_str}",
    )
    if report.warning_count:
        w_err = len(report.error_warnings)
        w_warn = sum(
            1 for w in report.warnings if w.level == "warning"
        )
        w_info = sum(
            1 for w in report.warnings if w.level == "info"
        )
        parts = []
        if w_err:
            parts.append(f"[red]{w_err} خطا[/]")
        if w_warn:
            parts.append(f"[yellow]{w_warn} هشدار[/]")
        if w_info:
            parts.append(f"[dim]{w_info} اطلاع[/]")
        table.add_row("هشدارها", " / ".join(parts))

    console.print(table)


def _display_structure_tree(
    console: Console, report: ScanReport,
) -> None:
    """نمایش درخت ساختار اسناد."""
    root_name = Path(report.input_path).name
    tree = Tree(f"📂 {root_name}")

    # گروه‌بندی: main → chapters → standalone
    main_docs = [
        d for d in report.documents if d.role == "main_entry"
    ]
    chapters = [
        d for d in report.documents if d.role == "chapter"
    ]
    standalones = [
        d for d in report.documents
        if d.role not in ("main_entry", "chapter")
    ]

    for doc in main_docs:
        icon = _ROLE_ICONS.get(doc.role, "📃")
        label = _doc_tree_label(doc)
        main_branch = tree.add(f"{icon} {label}")

        # فرزندان (chapters)
        for ch in chapters:
            if ch.parent == doc.path or ch.parent == doc.id:
                ch_icon = _ROLE_ICONS.get(ch.role, "📑")
                ch_label = _doc_tree_label(ch)
                main_branch.add(f"{ch_icon} {ch_label}")

        # وابستگی‌ها
        for dep in doc.dependencies:
            if not any(
                c.path == dep for c in chapters
            ):
                main_branch.add(f"📎 {dep}")

    for doc in standalones:
        icon = _ROLE_ICONS.get(doc.role, "📃")
        label = _doc_tree_label(doc)
        tree.add(f"{icon} {label}")

    # assetها
    if report.assets:
        asset_branch = tree.add("📁 assets/")
        for asset in report.assets[:10]:
            size = _human_size(asset.size_bytes)
            asset_branch.add(
                f"{'🖼' if asset.type.startswith('image') else '📎'} "
                f"{Path(asset.path).name}  [dim]({size})[/]"
            )
        if len(report.assets) > 10:
            asset_branch.add(
                f"[dim]... و {len(report.assets) - 10} فایل دیگر[/]"
            )

    console.print(tree)


def _doc_tree_label(doc: DocumentEntry) -> str:
    """برچسب یک سند برای درخت."""
    parts = [doc.path]

    desc_parts: list[str] = []
    if doc.title_hint:
        desc_parts.append(doc.title_hint)

    role_names = {
        "main_entry": "نقطه ورود اصلی",
        "chapter": "فصل",
        "appendix": "پیوست",
    }
    if doc.role in role_names and not doc.title_hint:
        desc_parts.append(role_names[doc.role])

    if desc_parts:
        parts.append(f"── {' | '.join(desc_parts)}")

    # نشانگرها
    badges: list[str] = []
    if doc.has_math:
        badges.append("∑")
    if doc.has_tikz:
        badges.append("✎")
    if doc.has_tables:
        badges.append("▦")
    if doc.has_code:
        badges.append("</>")
    if doc.has_bibliography:
        badges.append("📚")
    if not doc.has_bom:
        badges.append("[yellow]⚠BOM[/]")

    if badges:
        parts.append(f"  [dim]{' '.join(badges)}[/]")

    return " ".join(parts)


def _display_documents_table(
    console: Console, report: ScanReport,
) -> None:
    """جدول جزئیات اسناد (حالت verbose)."""
    table = Table(
        title="📄 جزئیات اسناد",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=4, justify="center")
    table.add_column("مسیر", width=28)
    table.add_column("فرمت", width=10, justify="center")
    table.add_column("زبان", width=8, justify="center")
    table.add_column("encoding", width=12, justify="center")
    table.add_column("اندازه", width=10, justify="right")
    table.add_column("ویژگی\u200cها", width=14)

    for doc in report.documents:
        features: list[str] = []
        if doc.has_math:
            features.append("∑ریاضی")
        if doc.has_tikz:
            features.append("✎TikZ")
        if doc.has_tables:
            features.append("▦جدول")
        if doc.has_code:
            features.append("</>کد")

        enc_display = doc.encoding
        if not doc.has_bom and doc.encoding.startswith("utf"):
            enc_display = f"[yellow]{doc.encoding}⚠[/]"

        table.add_row(
            doc.id.replace("doc_", ""),
            doc.path,
            doc.format,
            doc.language,
            enc_display,
            _human_size(doc.size_bytes),
            " ".join(features) if features else "—",
        )

    console.print(table)


def _display_assets_table(
    console: Console, report: ScanReport,
) -> None:
    """جدول assetها."""
    table = Table(
        title="📎 فایل\u200cهای وابسته",
        show_header=True,
        header_style="bold blue",
        border_style="dim",
    )
    table.add_column("فایل", width=30)
    table.add_column("نوع", width=16, justify="center")
    table.add_column("اندازه", width=10, justify="right")
    table.add_column("ارجاع", width=8, justify="center")

    for asset in report.assets:
        ref_count = len(asset.referenced_by)
        ref_str = (
            str(ref_count) if ref_count
            else "[yellow]بدون ارجاع[/]"
        )
        table.add_row(
            asset.path,
            asset.type,
            _human_size(asset.size_bytes),
            ref_str,
        )

    console.print(table)


def _display_warnings(
    console: Console, report: ScanReport,
) -> None:
    """نمایش هشدارها."""
    lines: list[str] = []
    for idx, w in enumerate(report.warnings, 1):
        if w.level == "error":
            icon, style = "❌", "red"
        elif w.level == "warning":
            icon, style = "⚠", "yellow"
        else:
            icon, style = "ℹ", "dim"

        line = (
            f"  [{style}]{icon} {idx}. {w.file}: "
            f"{w.message}[/{style}]"
        )
        if w.suggestion:
            line += f"\n     [dim]→ پیشنهاد: {w.suggestion}[/]"
        lines.append(line)

    console.print(Panel(
        "\n".join(lines),
        title="[bold yellow]⚠ هشدارها[/]",
        border_style="yellow",
    ))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Interactive Prompt / تعامل کاربر
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _interactive_prompt(
    console: Console,
    report: ScanReport,
) -> str:
    """
    نمایش منوی تعاملی و دریافت انتخاب کاربر.
    Show interactive menu and get user choice.

    Returns:
        یکی از: T, E, F, A, Q
    """
    console.print()
    console.print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    console.print(
        "  [bold green][T][/] تأیید و ادامه   "
        "[bold blue][E][/] ویرایش ساختار   "
        "[bold yellow][F][/] اصلاح خودکار هشدارها"
    )
    console.print(
        "  [bold cyan][A][/] تأیید + اصلاح   "
        "[bold red][Q][/] لغو"
    )
    console.print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    choice = click.prompt(
        "  انتخاب شما",
        type=click.Choice(
            ["T", "E", "F", "A", "Q"],
            case_sensitive=False,
        ),
        default="T",
    )
    return choice.upper()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Auto-fix / اصلاح خودکار
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _auto_fix_encoding(
    console: Console,
    report: ScanReport,
) -> None:
    """اصلاح خودکار encoding (افزودن BOM)."""
    console.print()
    with console.status(
        "[bold yellow]اصلاح encoding...", spinner="dots",
    ):
        fixed = fix_encoding_issues(report)

    if fixed:
        console.print(
            f"[green]✓ {len(fixed)} فایل اصلاح شد:[/]"
        )
        for f in fixed:
            console.print(f"  [green]+ BOM:[/] {f}")
    else:
        console.print(
            "[dim]همه فایل\u200cها encoding صحیح دارند.[/]"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Report Save / ذخیره گزارش
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _save_report(
    console: Console,
    report: ScanReport,
    output_path: str,
) -> None:
    """ذخیره گزارش به فایل YAML."""
    try:
        import yaml
    except ImportError:
        console.print(
            "[red]پکیج pyyaml نصب نیست. "
            "pip install pyyaml[/]"
        )
        return

    report_path = Path(output_path).resolve()

    data = _report_to_dict(report)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        yaml.dump(
            data,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    console.print(
        f"\n[green]💾 گزارش ذخیره شد:[/] {report_path}"
    )


def _print_json_report(
    console: Console,
    report: ScanReport,
) -> None:
    """چاپ گزارش به فرمت JSON."""
    import json
    data = _report_to_dict(report)
    console.print_json(json.dumps(data, ensure_ascii=False))


def _report_to_dict(report: ScanReport) -> dict:
    """تبدیل ScanReport به dict برای serialization."""
    return {
        "scan_id": report.scan_id,
        "timestamp": report.timestamp,
        "input_path": report.input_path,
        "input_type": report.input_type,
        "total_files": report.total_files,
        "structure": report.structure,
        "documents": [
            {
                "id": d.id,
                "path": d.path,
                "format": d.format,
                "encoding": d.encoding,
                "language": d.language,
                "role": d.role,
                "parent": d.parent,
                "size_bytes": d.size_bytes,
                "dependencies": d.dependencies,
                "images_referenced": d.images_referenced,
                "has_math": d.has_math,
                "has_code": d.has_code,
                "has_tables": d.has_tables,
                "has_bibliography": d.has_bibliography,
                "has_tikz": d.has_tikz,
            }
            for d in report.documents
        ],
        "assets": [
            {
                "path": a.path,
                "type": a.type,
                "size_bytes": a.size_bytes,
                "referenced_by": a.referenced_by,
            }
            for a in report.assets
        ],
        "warnings": [
            {
                "level": w.level,
                "file": w.file,
                "message": w.message,
                "suggestion": w.suggestion,
            }
            for w in report.warnings
        ],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Utility / ابزار
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _human_size(size_bytes: int) -> str:
    """تبدیل بایت به رشته خوانا."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
