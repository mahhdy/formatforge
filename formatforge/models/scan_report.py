"""
FormatForge - Scan Report Models
مدل‌های گزارش اسکن ورودی

Models for input scanning results: document info, asset entries,
warnings, and the full ScanReport.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────
# Constants / ثابت‌ها
# ─────────────────────────────────────────────

ZWNJ = "\u200c"

_VALID_INPUT_TYPES = frozenset({
    "file", "directory", "archive", "url", "clipboard",
})

_VALID_STRUCTURES = frozenset({
    "single_doc",
    "independent_articles",
    "multi_chapter_book",
    "related_collection",
})

_VALID_FORMATS = frozenset({
    "latex", "markdown", "html", "docx", "pdf",
    "rst", "adoc", "ipynb", "epub", "unknown",
})

_VALID_ENCODINGS = frozenset({
    "utf-8", "utf-8-bom", "utf-16", "utf-16-le", "utf-16-be",
    "windows-1256", "iso-8859-6", "ascii", "unknown",
})

_VALID_LANGUAGES = frozenset({
    "fa", "en", "fa+en", "unknown",
})

_VALID_ROLES = frozenset({
    "main_entry", "chapter", "appendix", "standalone",
    "preface", "bibliography", "index", "unknown",
})

_VALID_WARNING_LEVELS = frozenset({
    "info", "warning", "error", "critical",
})

_VALID_ASSET_CATEGORIES = frozenset({
    "image/png", "image/jpeg", "image/svg+xml", "image/gif",
    "image/webp", "video/mp4", "audio/mp3",
    "bibliography", "style", "metadata", "font", "other",
})


# ─────────────────────────────────────────────
# Sub-models / مدل‌های فرعی
# ─────────────────────────────────────────────

class ScanWarning(BaseModel):
    """
    هشدار اسکن.
    A single warning/info/error from the scanning process.
    """

    level: str = Field(
        default="warning",
        description="سطح هشدار: info | warning | error | critical",
    )
    file: Optional[str] = Field(
        default=None,
        description="فایل مرتبط با هشدار",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="پیام هشدار",
    )
    suggestion: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="پیشنهاد رفع مشکل",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """بررسی سطح هشدار."""
        v_lower = v.lower().strip()
        if v_lower not in _VALID_WARNING_LEVELS:
            raise ValueError(
                f"سطح هشدار «{v}» نامعتبر. "
                f"مقادیر مجاز: {sorted(_VALID_WARNING_LEVELS)}"
            )
        return v_lower


class ScanAssetEntry(BaseModel):
    """
    اطلاعات یک فایل وابسته (تصویر، بیب‌تکس و...).
    An asset file entry in the scan report.
    """

    path: str = Field(
        ...,
        min_length=1,
        description="مسیر نسبی فایل",
    )
    type: str = Field(
        default="other",
        description="نوع فایل (MIME-like)",
    )
    size_bytes: int = Field(
        default=0,
        ge=0,
        description="حجم فایل به بایت",
    )
    referenced_by: list[str] = Field(
        default_factory=list,
        description="لیست شناسه اسنادی که به این فایل ارجاع داده‌اند",
    )
    entries_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="تعداد ورودی‌ها (مثلاً تعداد مراجع در bib)",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """بررسی نوع فایل."""
        v_lower = v.lower().strip()
        if v_lower not in _VALID_ASSET_CATEGORIES:
            # اجازه مقادیر سفارشی ولی با هشدار
            pass
        return v_lower


class DocumentInfo(BaseModel):
    """
    اطلاعات یک سند شناسایی‌شده.
    Information about a single document found during scanning.
    """

    id: str = Field(
        default_factory=lambda: f"doc_{uuid.uuid4().hex[:8]}",
        description="شناسه یکتای سند",
    )
    path: str = Field(
        ...,
        min_length=1,
        description="مسیر نسبی فایل",
    )
    format: str = Field(
        default="unknown",
        description="فرمت سند: latex | markdown | html | ...",
    )
    encoding: str = Field(
        default="unknown",
        description="رمزگذاری فایل: utf-8 | utf-8-bom | ...",
    )
    language: str = Field(
        default="unknown",
        description="زبان سند: fa | en | fa+en | unknown",
    )
    role: str = Field(
        default="standalone",
        description="نقش سند: main_entry | chapter | appendix | standalone",
    )
    parent: Optional[str] = Field(
        default=None,
        description="شناسه سند والد (اگر وجود دارد)",
    )
    size_bytes: int = Field(
        default=0,
        ge=0,
        description="حجم فایل به بایت",
    )
    estimated_pages: Optional[int] = Field(
        default=None,
        ge=0,
        description="تعداد تخمینی صفحات",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="لیست فایل‌های وابسته (input/include)",
    )
    images_referenced: list[str] = Field(
        default_factory=list,
        description="لیست تصاویر ارجاع‌داده‌شده",
    )

    # ─── Feature flags ────────────────────────

    has_math: bool = Field(default=False, description="شامل فرمول ریاضی")
    has_code: bool = Field(default=False, description="شامل بلوک کد")
    has_tables: bool = Field(default=False, description="شامل جدول")
    has_bibliography: bool = Field(default=False, description="شامل کتاب‌نامه")
    has_tikz: bool = Field(default=False, description="شامل نمودار TikZ")
    has_images: bool = Field(default=False, description="شامل تصویر")
    has_hyperlinks: bool = Field(default=False, description="شامل لینک")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """بررسی فرمت سند."""
        v_lower = v.lower().strip()
        if v_lower not in _VALID_FORMATS:
            raise ValueError(
                f"فرمت «{v}» نامعتبر. مقادیر مجاز: {sorted(_VALID_FORMATS)}"
            )
        return v_lower

    @field_validator("encoding")
    @classmethod
    def validate_encoding(cls, v: str) -> str:
        """بررسی encoding."""
        v_lower = v.lower().strip()
        if v_lower not in _VALID_ENCODINGS:
            raise ValueError(
                f"encoding «{v}» نامعتبر. "
                f"مقادیر مجاز: {sorted(_VALID_ENCODINGS)}"
            )
        return v_lower

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """بررسی زبان."""
        v_lower = v.lower().strip()
        if v_lower not in _VALID_LANGUAGES:
            raise ValueError(
                f"زبان «{v}» نامعتبر. "
                f"مقادیر مجاز: {sorted(_VALID_LANGUAGES)}"
            )
        return v_lower

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """بررسی نقش سند."""
        v_lower = v.lower().strip()
        if v_lower not in _VALID_ROLES:
            raise ValueError(
                f"نقش «{v}» نامعتبر. مقادیر مجاز: {sorted(_VALID_ROLES)}"
            )
        return v_lower

    @model_validator(mode="after")
    def auto_detect_has_images(self) -> "DocumentInfo":
        """اگر تصاویر ارجاع شده، has_images را فعال کن."""
        if self.images_referenced and not self.has_images:
            self.has_images = True
        return self


# ─────────────────────────────────────────────
# Main Model / مدل اصلی
# ─────────────────────────────────────────────

class ScanReport(BaseModel):
    """
    گزارش کامل اسکن ورودی.
    Full scan report produced by the input scanner.
    """

    scan_id: str = Field(
        default_factory=lambda: f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description="شناسه یکتای اسکن",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="زمان اسکن (ISO 8601)",
    )
    input_path: str = Field(
        ...,
        min_length=1,
        description="مسیر ورودی",
    )
    input_type: str = Field(
        default="file",
        description="نوع ورودی: file | directory | archive | url | clipboard",
    )
    total_files: int = Field(
        default=0,
        ge=0,
        description="تعداد کل فایل‌های یافت‌شده",
    )
    structure: str = Field(
        default="single_doc",
        description=(
            "ساختار شناسایی‌شده: single_doc | independent_articles | "
            "multi_chapter_book | related_collection"
        ),
    )

    # ─── اسناد / Documents ───────────────────

    documents: list[DocumentInfo] = Field(
        default_factory=list,
        description="لیست اسناد شناسایی‌شده",
    )

    # ─── فایل‌های وابسته / Assets ────────────

    assets: list[ScanAssetEntry] = Field(
        default_factory=list,
        description="لیست فایل‌های وابسته",
    )

    # ─── هشدارها / Warnings ──────────────────

    warnings: list[ScanWarning] = Field(
        default_factory=list,
        description="لیست هشدارها",
    )

    # ─── تأیید / Confirmation ────────────────

    confirmation_required: bool = Field(
        default=True,
        description="آیا تأیید کاربر لازم است",
    )
    confirmation_prompt: Optional[str] = Field(
        default=None,
        description="متن درخواست تأیید از کاربر",
    )

    @field_validator("input_type")
    @classmethod
    def validate_input_type(cls, v: str) -> str:
        """بررسی نوع ورودی."""
        v_lower = v.lower().strip()
        if v_lower not in _VALID_INPUT_TYPES:
            raise ValueError(
                f"نوع ورودی «{v}» نامعتبر. "
                f"مقادیر مجاز: {sorted(_VALID_INPUT_TYPES)}"
            )
        return v_lower

    @field_validator("structure")
    @classmethod
    def validate_structure(cls, v: str) -> str:
        """بررسی ساختار."""
        v_lower = v.lower().strip()
        if v_lower not in _VALID_STRUCTURES:
            raise ValueError(
                f"ساختار «{v}» نامعتبر. "
                f"مقادیر مجاز: {sorted(_VALID_STRUCTURES)}"
            )
        return v_lower

    # ─── Helpers / متدهای کمکی ───────────────

    @property
    def document_count(self) -> int:
        """تعداد اسناد."""
        return len(self.documents)

    @property
    def asset_count(self) -> int:
        """تعداد فایل‌های وابسته."""
        return len(self.assets)

    @property
    def warning_count(self) -> int:
        """تعداد هشدارها."""
        return len(self.warnings)

    @property
    def error_count(self) -> int:
        """تعداد خطاها (سطح error یا critical)."""
        return sum(
            1 for w in self.warnings
            if w.level in ("error", "critical")
        )

    @property
    def has_errors(self) -> bool:
        """آیا خطای بحرانی وجود دارد."""
        return self.error_count > 0

    def get_main_entry(self) -> Optional[DocumentInfo]:
        """
        یافتن سند اصلی (نقطه ورود).
        Find the main entry document.
        """
        for doc in self.documents:
            if doc.role == "main_entry":
                return doc
        # اگر main_entry نبود، اولین سند standalone
        for doc in self.documents:
            if doc.role == "standalone":
                return doc
        return self.documents[0] if self.documents else None

    def get_chapters(self) -> list[DocumentInfo]:
        """
        لیست فصل‌ها به ترتیب.
        Get chapter documents in order.
        """
        return [d for d in self.documents if d.role == "chapter"]

    def get_warnings_for_file(self, file_path: str) -> list[ScanWarning]:
        """
        هشدارهای مربوط به یک فایل خاص.
        Get all warnings related to a specific file.
        """
        return [w for w in self.warnings if w.file == file_path]

    def generate_confirmation_prompt(self) -> str:
        """
        تولید متن تأیید خودکار بر اساس داده‌ها.
        Generate a user-facing confirmation prompt string.
        """
        main = self.get_main_entry()
        chapters = self.get_chapters()

        structure_names = {
            "single_doc": "سند تکی",
            "independent_articles": "مقالات مستقل",
            "multi_chapter_book": "کتاب چندفصلی",
            "related_collection": "مجموعه مرتبط",
        }

        lines = [
            "\U0001f4c2 ساختار شناسایی\u200cشده:",
            "\u2501" * 30,
            f"  نوع: {structure_names.get(self.structure, self.structure)}",
        ]

        if main:
            lines.append(f"  فرمت اصلی: {main.format}")
            lines.append(f"  زبان: {main.language}")

        lines.append(
            f"  {self.document_count} سند، "
            f"{self.asset_count} فایل وابسته"
        )

        if self.warning_count > 0:
            lines.append(f"  \u26a0 {self.warning_count} هشدار")

        lines.extend([
            "",
            "آیا این تشخیص صحیح است؟ [بله/خیر/ویرایش]",
        ])

        prompt = "\n".join(lines)
        self.confirmation_prompt = prompt
        return prompt
