"""
مدل گزارش اسکن — Scan Report Model.
نتیجه مرحله اسکن و شناسایی ورودی.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from formatforge.models.enums import (
    DocumentFormat,
    DocumentLanguage,
    DocumentRole,
    IssueSeverity,
    StructureType,
)


# ──────────── مدل‌های فرعی ────────────


class EncodingInfo(BaseModel):
    """اطلاعات encoding فایل — File encoding information."""

    name: str = Field("utf-8", description="نام encoding")
    has_bom: bool = Field(False, description="آیا BOM دارد")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="ضریب اطمینان")


class ScanIssue(BaseModel):
    """مشکل شناسایی‌شده — Detected issue during scanning."""

    severity: IssueSeverity = Field(..., description="شدت مشکل")
    file: str = Field("", description="فایل مربوطه")
    line: int | None = Field(None, description="شماره خط (اختیاری)")
    message: str = Field(..., description="پیام مشکل")
    suggestion: str = Field("", description="پیشنهاد اصلاح")
    auto_fixable: bool = Field(False, description="آیا قابل اصلاح خودکار است")


class ImageReference(BaseModel):
    """ارجاع تصویر — Image reference found in document."""

    path: str = Field(..., description="مسیر تصویر")
    exists: bool = Field(True, description="آیا فایل وجود دارد")
    referenced_by: list[str] = Field(default_factory=list, description="فایل‌های ارجاع‌دهنده")


class DependencyInfo(BaseModel):
    """اطلاعات وابستگی — Dependency file information."""

    path: str = Field(..., description="مسیر فایل وابسته")
    type: str = Field(..., description="نوع وابستگی (input, include, bibliography, image)")
    exists: bool = Field(True, description="آیا وجود دارد")
    referenced_by: str = Field("", description="فایل ارجاع‌دهنده")


class ScannedDocument(BaseModel):
    """اطلاعات یک سند اسکن‌شده — Information about a scanned document."""

    id: str = Field(..., description="شناسه منحصربه‌فرد")
    path: str = Field(..., description="مسیر نسبی فایل")
    format: DocumentFormat = Field(..., description="فرمت شناسایی‌شده")
    encoding: EncodingInfo = Field(default_factory=EncodingInfo, description="اطلاعات encoding")
    language: DocumentLanguage = Field(
        DocumentLanguage.UNKNOWN,
        description="زبان شناسایی‌شده",
    )
    role: DocumentRole = Field(DocumentRole.STANDALONE, description="نقش فایل")
    parent: str | None = Field(None, description="شناسه سند والد (برای فصل‌ها)")
    size_bytes: int = Field(0, ge=0, description="حجم فایل (بایت)")
    estimated_pages: int | None = Field(None, description="تعداد تقریبی صفحات")

    # وابستگی‌ها
    dependencies: list[str] = Field(
        default_factory=list,
        description="مسیر فایل‌های include/input شده",
    )
    images_referenced: list[str] = Field(
        default_factory=list,
        description="مسیر تصاویر ارجاع‌شده",
    )

    # ویژگی‌های محتوا
    has_math: bool = Field(False, description="شامل فرمول ریاضی")
    has_code: bool = Field(False, description="شامل بلوک کد")
    has_tables: bool = Field(False, description="شامل جدول")
    has_bibliography: bool = Field(False, description="شامل کتاب‌نامه")
    has_tikz: bool = Field(False, description="شامل نمودار TikZ")
    has_mermaid: bool = Field(False, description="شامل نمودار Mermaid")

    # آمار سریع
    zwnj_count: int = Field(0, ge=0, description="تعداد نیم‌فاصله‌ها")
    word_count_approx: int = Field(0, ge=0, description="تعداد تقریبی کلمات")

    @computed_field
    @property
    def size_human(self) -> str:
        """حجم فایل به شکل خوانا"""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        else:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"


class ScannedAsset(BaseModel):
    """اطلاعات فایل وابسته (تصویر، فونت و...) — Scanned asset file."""

    path: str = Field(..., description="مسیر نسبی")
    type: str = Field(..., description="MIME type")
    size_bytes: int = Field(0, ge=0, description="حجم (بایت)")
    referenced_by: list[str] = Field(
        default_factory=list,
        description="شناسه اسنادی که به آن ارجاع دارند",
    )


# ──────────── مدل اصلی ────────────


class ScanReport(BaseModel):
    """
    گزارش کامل اسکن — Complete scan report.
    خروجی مرحله ۱ (Stage 1) خط لوله تبدیل.
    """

    # شناسه و زمان
    scan_id: str = Field(..., description="شناسه اسکن")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="زمان اسکن (ISO 8601)",
    )

    # ورودی
    input_path: str = Field(..., description="مسیر ورودی")
    input_type: str = Field(
        "file",
        description="نوع ورودی (file, directory, archive, url, clipboard)",
    )

    # ساختار
    structure: StructureType = Field(
        StructureType.UNKNOWN,
        description="نوع ساختار شناسایی‌شده",
    )

    # اسناد و فایل‌ها
    documents: list[ScannedDocument] = Field(
        default_factory=list,
        description="لیست اسناد شناسایی‌شده",
    )
    assets: list[ScannedAsset] = Field(
        default_factory=list,
        description="لیست فایل‌های وابسته",
    )
    all_dependencies: list[DependencyInfo] = Field(
        default_factory=list,
        description="گراف وابستگی کامل",
    )

    # مشکلات
    issues: list[ScanIssue] = Field(
        default_factory=list,
        description="مشکلات شناسایی‌شده",
    )

    # تأیید
    confirmation_required: bool = Field(True, description="آیا تأیید کاربر لازم است")

    # ─── فیلدهای محاسبه‌ای ───

    @computed_field
    @property
    def total_files(self) -> int:
        """تعداد کل فایل‌ها"""
        return len(self.documents) + len(self.assets)

    @computed_field
    @property
    def total_documents(self) -> int:
        """تعداد اسناد"""
        return len(self.documents)

    @computed_field
    @property
    def total_assets(self) -> int:
        """تعداد فایل‌های وابسته"""
        return len(self.assets)

    @computed_field
    @property
    def total_size_bytes(self) -> int:
        """حجم کل"""
        doc_size = sum(d.size_bytes for d in self.documents)
        asset_size = sum(a.size_bytes for a in self.assets)
        return doc_size + asset_size

    @computed_field
    @property
    def error_count(self) -> int:
        """تعداد خطاها"""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @computed_field
    @property
    def warning_count(self) -> int:
        """تعداد هشدارها"""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    @computed_field
    @property
    def primary_format(self) -> DocumentFormat:
        """فرمت اصلی (شایع‌ترین)"""
        if not self.documents:
            return DocumentFormat.UNKNOWN
        formats = [d.format for d in self.documents]
        return max(set(formats), key=formats.count)

    @computed_field
    @property
    def primary_language(self) -> DocumentLanguage:
        """زبان اصلی"""
        if not self.documents:
            return DocumentLanguage.UNKNOWN
        langs = [d.language for d in self.documents if d.language != DocumentLanguage.UNKNOWN]
        if not langs:
            return DocumentLanguage.UNKNOWN
        return max(set(langs), key=langs.count)

    # ─── متدها ───

    def get_document_by_id(self, doc_id: str) -> ScannedDocument | None:
        """دریافت سند با شناسه"""
        for doc in self.documents:
            if doc.id == doc_id:
                return doc
        return None

    def get_main_document(self) -> ScannedDocument | None:
        """دریافت سند اصلی (main_entry)"""
        for doc in self.documents:
            if doc.role == DocumentRole.MAIN_ENTRY:
                return doc
        # اگر main_entry نبود، اولین standalone
        for doc in self.documents:
            if doc.role == DocumentRole.STANDALONE:
                return doc
        return self.documents[0] if self.documents else None

    def get_chapters(self) -> list[ScannedDocument]:
        """دریافت فصل‌ها (مرتب)"""
        chapters = [d for d in self.documents if d.role == DocumentRole.CHAPTER]
        return sorted(chapters, key=lambda d: d.path)

    def get_missing_dependencies(self) -> list[DependencyInfo]:
        """دریافت وابستگی‌های گمشده"""
        return [d for d in self.all_dependencies if not d.exists]

    def get_auto_fixable_issues(self) -> list[ScanIssue]:
        """دریافت مشکلات قابل اصلاح خودکار"""
        return [i for i in self.issues if i.auto_fixable]

    def has_critical_issues(self) -> bool:
        """آیا مشکل بحرانی وجود دارد"""
        return self.error_count > 0

    @classmethod
    def create(cls, scan_id: str, input_path: str, input_type: str = "file") -> "ScanReport":
        """ساخت نمونه خالی — Create empty report."""
        return cls(scan_id=scan_id, input_path=input_path, input_type=input_type)