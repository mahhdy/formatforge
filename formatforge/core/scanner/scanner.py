"""
FormatForge - Scanner
اسکنر یکپارچه ورودی

Orchestrate file_detector, structure_analyzer, and archive_handler
to produce a comprehensive ScanReport.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from formatforge.config.schema import AppConfig
from formatforge.core.scanner.archive_handler import (
    ExtractedArchive,
    cleanup_temp,
    extract_archive,
    is_archive,
)
from formatforge.core.scanner.file_detector import (
    EncodingInfo,
    LanguageInfo,
    detect_encoding,
    detect_format,
    detect_language,
)
from formatforge.core.scanner.structure_analyzer import (
    AssetEntry,
    DocInfo,
    StructureAnalysis,
    analyze_directory,
    find_assets,
)
from formatforge.exceptions import ScanError

logger = logging.getLogger("formatforge.scanner")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Classes / کلاس‌های داده
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_UTF8_BOM = b"\xef\xbb\xbf"


@dataclass
class ScanWarning:
    """هشدار اسکن. / Scan warning entry."""
    level: str             # "info" | "warning" | "error"
    file: str
    message: str
    suggestion: str = ""


@dataclass
class DocumentEntry:
    """اطلاعات کامل یک سند اسکن‌شده. / Scanned document entry."""
    id: str
    path: str
    format: str
    encoding: str = "utf-8"
    has_bom: bool = False
    language: str = "unknown"
    role: str = "standalone"
    parent: Optional[str] = None
    size_bytes: int = 0
    dependencies: list[str] = field(default_factory=list)
    images_referenced: list[str] = field(default_factory=list)
    has_math: bool = False
    has_code: bool = False
    has_tables: bool = False
    has_bibliography: bool = False
    has_tikz: bool = False
    title_hint: Optional[str] = None


@dataclass
class AssetInfo:
    """اطلاعات فایل وابسته. / Asset info for report."""
    path: str
    type: str
    size_bytes: int = 0
    referenced_by: list[str] = field(default_factory=list)


@dataclass
class ScanReport:
    """
    گزارش کامل اسکن ورودی.
    Complete scan report matching the FormatForge specification.
    """
    scan_id: str
    timestamp: str
    input_path: str
    input_type: str         # file | directory | archive
    total_files: int = 0
    structure: str = "single_doc"
    documents: list[DocumentEntry] = field(default_factory=list)
    assets: list[AssetInfo] = field(default_factory=list)
    warnings: list[ScanWarning] = field(default_factory=list)
    confirmation_required: bool = True
    # internal: مسیر موقت آرشیو (برای cleanup)
    _archive_temp: Optional[str] = field(
        default=None, repr=False,
    )

    @property
    def doc_count(self) -> int:
        """تعداد اسناد."""
        return len(self.documents)

    @property
    def asset_count(self) -> int:
        """تعداد assetها."""
        return len(self.assets)

    @property
    def warning_count(self) -> int:
        """تعداد هشدارها."""
        return len(self.warnings)

    @property
    def error_warnings(self) -> list[ScanWarning]:
        """هشدارهای سطح error."""
        return [w for w in self.warnings if w.level == "error"]

    @property
    def primary_format(self) -> Optional[str]:
        """فرمت غالب اسناد."""
        if not self.documents:
            return None
        counts: dict[str, int] = {}
        for d in self.documents:
            counts[d.format] = counts.get(d.format, 0) + 1
        return max(counts, key=counts.get)  # type: ignore

    @property
    def primary_language(self) -> str:
        """زبان غالب."""
        langs = [d.language for d in self.documents]
        if any("fa" in la for la in langs):
            return "fa" if all("fa" in la for la in langs) else "fa+en"
        return "en" if langs else "unknown"

    def cleanup(self) -> None:
        """پاک‌سازی فایل‌های موقت آرشیو."""
        if self._archive_temp:
            cleanup_temp(self._archive_temp)
            self._archive_temp = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Content Analysis Patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import re

_MATH_PATTERNS = [
    re.compile(r"\$[^$]+\$"),
    re.compile(r"\$\$[\s\S]+?\$\$"),
    re.compile(r"\\begin\{(equation|align|gather|math)\*?\}"),
]
_CODE_PATTERNS = [
    re.compile(r"```\w*\n", re.MULTILINE),
    re.compile(r"\\begin\{(lstlisting|verbatim|minted)\}"),
]
_TABLE_PATTERNS = [
    re.compile(r"\\begin\{(tabular|longtable|table)\}"),
    re.compile(r"^\|.*\|.*\|", re.MULTILINE),
    re.compile(r"<table[\s>]", re.IGNORECASE),
]
_BIB_PATTERNS = [
    re.compile(r"\\bibliography\{"),
    re.compile(r"\\addbibresource\{"),
    re.compile(r"\\cite[tp]?\{"),
]
_TIKZ_PATTERNS = [
    re.compile(r"\\begin\{tikzpicture\}"),
    re.compile(r"\\tikz\b"),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Scanner Class / کلاس اسکنر
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class Scanner:
    """
    اسکنر یکپارچه ورودی FormatForge.
    Orchestrate detection, analysis, and reporting.
    """

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self._config = config
        self._warnings: list[ScanWarning] = []

    def scan(
        self,
        input_path: str | Path,
        *,
        recursive: bool = True,
        format_hint: str = "auto",
    ) -> ScanReport:
        """
        اسکن ورودی و تولید ScanReport.
        Scan input path and produce comprehensive report.

        Args:
            input_path: مسیر فایل، پوشه یا آرشیو
            recursive: اسکن بازگشتی
            format_hint: راهنمای فرمت (auto | latex | ...)

        Returns:
            ScanReport کامل

        Raises:
            ScanError: خطا در اسکن
            FileNotFoundError: مسیر وجود ندارد
        """
        self._warnings = []
        path = Path(input_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"مسیر یافت نشد: {path}")

        scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ts = datetime.now(timezone.utc).isoformat()

        archive_temp: Optional[str] = None

        # ─── تعیین نوع ورودی ─────────────
        if path.is_file() and is_archive(path):
            input_type = "archive"
            extracted = extract_archive(path)
            archive_temp = extracted.extract_dir
            scan_dir = Path(extracted.extract_dir)
            if extracted.encoding_issues:
                for issue in extracted.encoding_issues:
                    self._add_warning(
                        "info", str(path), issue,
                    )
        elif path.is_file():
            input_type = "file"
            scan_dir = path.parent
        else:
            input_type = "directory"
            scan_dir = path

        # ─── اسکن ────────────────────────
        if input_type == "file":
            report = self._scan_single_file(
                path, scan_id, ts, format_hint,
            )
        else:
            report = self._scan_directory(
                scan_dir, scan_id, ts, format_hint,
            )

        report.input_path = str(path)
        report.input_type = input_type
        report._archive_temp = archive_temp

        logger.info(
            "اسکن %s: %d سند, %d asset, %d هشدار",
            path.name, report.doc_count,
            report.asset_count, report.warning_count,
        )

        return report

    # ─── Single File ──────────────────────

    def _scan_single_file(
        self,
        file_path: Path,
        scan_id: str,
        timestamp: str,
        format_hint: str,
    ) -> ScanReport:
        """اسکن یک فایل منفرد."""
        fmt = (
            format_hint
            if format_hint != "auto"
            else detect_format(file_path)
        )
        enc_info = detect_encoding(file_path)
        content = self._safe_read(file_path, enc_info.name)
        lang_info = detect_language(content)
        size = file_path.stat().st_size

        self._check_encoding_warnings(
            file_path.name, enc_info,
        )

        doc = self._build_document_entry(
            doc_id="doc_001",
            path=file_path.name,
            fmt=fmt,
            enc_info=enc_info,
            lang_info=lang_info,
            content=content,
            size=size,
            role="standalone",
        )

        return ScanReport(
            scan_id=scan_id,
            timestamp=timestamp,
            input_path=str(file_path),
            input_type="file",
            total_files=1,
            structure="single_doc",
            documents=[doc],
            assets=[],
            warnings=list(self._warnings),
        )

    # ─── Directory ────────────────────────

    def _scan_directory(
        self,
        dir_path: Path,
        scan_id: str,
        timestamp: str,
        format_hint: str,
    ) -> ScanReport:
        """اسکن یک پوشه."""
        analysis = analyze_directory(dir_path)
        assets_raw = find_assets(dir_path)

        documents: list[DocumentEntry] = []
        for idx, doc_info in enumerate(analysis.documents, 1):
            doc_path = dir_path / doc_info.path
            if not doc_path.is_file():
                continue

            fmt = (
                format_hint
                if format_hint != "auto"
                else doc_info.format
            )
            enc_info = detect_encoding(doc_path)
            content = self._safe_read(doc_path, enc_info.name)
            lang_info = detect_language(content)
            size = doc_path.stat().st_size

            self._check_encoding_warnings(
                doc_info.path, enc_info,
            )

            doc = self._build_document_entry(
                doc_id=f"doc_{idx:03d}",
                path=doc_info.path,
                fmt=fmt,
                enc_info=enc_info,
                lang_info=lang_info,
                content=content,
                size=size,
                role=doc_info.role,
                parent=doc_info.parent,
                dependencies=doc_info.dependencies,
                images_referenced=doc_info.images_referenced,
                title_hint=doc_info.title_hint,
            )
            documents.append(doc)

        # تبدیل assets
        doc_paths = {d.path for d in documents}
        assets = self._build_assets(
            assets_raw, doc_paths, dir_path,
        )

        # بررسی assetهای بدون ارجاع
        self._check_unreferenced_assets(
            assets, documents,
        )

        total = len(analysis.documents) + len(assets_raw)

        return ScanReport(
            scan_id=scan_id,
            timestamp=timestamp,
            input_path=str(dir_path),
            input_type="directory",
            total_files=total,
            structure=analysis.structure_type,
            documents=documents,
            assets=assets,
            warnings=list(self._warnings),
        )

    # ─── Build Helpers ────────────────────

    def _build_document_entry(
        self,
        *,
        doc_id: str,
        path: str,
        fmt: str,
        enc_info: EncodingInfo,
        lang_info: LanguageInfo,
        content: str,
        size: int,
        role: str = "standalone",
        parent: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
        images_referenced: Optional[list[str]] = None,
        title_hint: Optional[str] = None,
    ) -> DocumentEntry:
        """ساخت DocumentEntry با تحلیل محتوا."""
        enc_name = enc_info.name
        if enc_info.has_bom and "sig" not in enc_name:
            enc_name = f"{enc_name}-bom"

        return DocumentEntry(
            id=doc_id,
            path=path,
            format=fmt,
            encoding=enc_name,
            has_bom=enc_info.has_bom,
            language=lang_info.primary,
            role=role,
            parent=parent,
            size_bytes=size,
            dependencies=dependencies or [],
            images_referenced=images_referenced or [],
            has_math=_has_pattern(content, _MATH_PATTERNS),
            has_code=_has_pattern(content, _CODE_PATTERNS),
            has_tables=_has_pattern(content, _TABLE_PATTERNS),
            has_bibliography=_has_pattern(content, _BIB_PATTERNS),
            has_tikz=_has_pattern(content, _TIKZ_PATTERNS),
            title_hint=title_hint,
        )

    def _build_assets(
        self,
        raw: list[AssetEntry],
        doc_paths: set[str],
        root: Path,
    ) -> list[AssetInfo]:
        """تبدیل AssetEntry به AssetInfo."""
        assets: list[AssetInfo] = []
        for a in raw:
            p = root / a.path
            mime = _guess_mime(a.path, a.category)
            assets.append(AssetInfo(
                path=a.path,
                type=mime,
                size_bytes=a.size_bytes,
                referenced_by=a.referenced_by,
            ))
        return assets

    # ─── Warnings ─────────────────────────

    def _check_encoding_warnings(
        self, file_name: str, enc: EncodingInfo,
    ) -> None:
        """بررسی هشدارهای encoding."""
        if not enc.has_bom and enc.name.startswith("utf"):
            self._add_warning(
                "warning",
                file_name,
                "فایل بدون BOM است. ممکن است نیم\u200cفاصله\u200cها "
                "از دست بروند.",
                "تبدیل به UTF-8 with BOM",
            )

        if enc.confidence < 0.7:
            self._add_warning(
                "warning",
                file_name,
                f"اطمینان encoding پایین: {enc.confidence:.0%}",
                f"بررسی دستی encoding ({enc.name})",
            )

    def _check_unreferenced_assets(
        self,
        assets: list[AssetInfo],
        documents: list[DocumentEntry],
    ) -> None:
        """شناسایی assetهای بدون ارجاع."""
        all_refs: set[str] = set()
        for doc in documents:
            all_refs.update(doc.images_referenced)
            all_refs.update(doc.dependencies)

        for asset in assets:
            name = Path(asset.path).name
            stem = Path(asset.path).stem
            if (
                not asset.referenced_by
                and asset.path not in all_refs
                and name not in all_refs
                and not any(stem in r for r in all_refs)
            ):
                self._add_warning(
                    "info",
                    asset.path,
                    "این فایل در هیچ سندی ارجاع داده نشده.",
                    "حذف یا بررسی",
                )

    def _add_warning(
        self,
        level: str,
        file: str,
        message: str,
        suggestion: str = "",
    ) -> None:
        """افزودن هشدار."""
        self._warnings.append(ScanWarning(
            level=level, file=file,
            message=message, suggestion=suggestion,
        ))

    # ─── Utils ────────────────────────────

    @staticmethod
    def _safe_read(path: Path, encoding: str = "utf-8") -> str:
        """خواندن امن فایل متنی."""
        try:
            enc = encoding.replace("-bom", "-sig")
            return path.read_text(encoding=enc, errors="ignore")
        except (OSError, LookupError):
            try:
                return path.read_text(
                    encoding="utf-8", errors="ignore",
                )
            except OSError:
                return ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Encoding Fix / اصلاح encoding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def fix_encoding_issues(report: ScanReport) -> list[str]:
    """
    اصلاح خودکار مشکلات encoding (افزودن BOM).
    Auto-fix encoding issues by adding UTF-8 BOM.

    Args:
        report: گزارش اسکن

    Returns:
        لیست فایل‌های اصلاح‌شده
    """
    fixed: list[str] = []
    base = Path(report.input_path)
    if not base.is_dir():
        base = base.parent

    for doc in report.documents:
        if doc.has_bom:
            continue
        if not doc.encoding.startswith("utf"):
            continue

        file_path = base / doc.path
        if not file_path.is_file():
            continue

        raw = file_path.read_bytes()
        if raw[:3] == _UTF8_BOM:
            continue

        file_path.write_bytes(_UTF8_BOM + raw)
        doc.has_bom = True
        doc.encoding = "utf-8-sig"
        fixed.append(doc.path)
        logger.info("BOM افزوده شد: %s", doc.path)

    return fixed


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Module Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _has_pattern(
    content: str,
    patterns: list[re.Pattern[str]],
) -> bool:
    """آیا محتوا حداقل یکی از الگوها را دارد؟"""
    return any(p.search(content) for p in patterns)


_MIME_MAP: dict[str, str] = {
    "image": "image/",
    "media": "media/",
    "style": "text/css",
    "font": "font/",
    "metadata": "application/",
}

_EXT_MIMES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".bib": "bibliography",
    ".css": "text/css",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
}


def _guess_mime(path: str, category: str) -> str:
    """حدس نوع MIME."""
    ext = Path(path).suffix.lower()
    return _EXT_MIMES.get(ext, _MIME_MAP.get(category, "unknown"))
