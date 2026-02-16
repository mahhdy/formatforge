"""
مدل نتیجه تبدیل — Conversion Result Model.
خروجی مرحله ۳ (Stage 3) و مراحل بعدی خط لوله.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from formatforge.models.enums import (
    ConversionStatus,
    DocumentFormat,
    IssueSeverity,
    QualityGrade,
)
from formatforge.models.metadata import DocumentMetadata


# ──────────── مدل‌های آماری ────────────


class ElementCounts(BaseModel):
    """شمارش عناصر سند — Element counts for content comparison."""

    headings: int = Field(0, ge=0, description="تعداد عناوین")
    paragraphs: int = Field(0, ge=0, description="تعداد پاراگراف‌ها")
    math_inline: int = Field(0, ge=0, description="تعداد فرمول‌های inline")
    math_display: int = Field(0, ge=0, description="تعداد فرمول‌های display")
    images: int = Field(0, ge=0, description="تعداد تصاویر")
    tables: int = Field(0, ge=0, description="تعداد جداول")
    code_blocks: int = Field(0, ge=0, description="تعداد بلوک‌های کد")
    lists: int = Field(0, ge=0, description="تعداد لیست‌ها")
    footnotes: int = Field(0, ge=0, description="تعداد پانوشت‌ها")
    citations: int = Field(0, ge=0, description="تعداد ارجاعات")
    cross_refs: int = Field(0, ge=0, description="تعداد ارجاعات متقاطع")
    links_internal: int = Field(0, ge=0, description="تعداد لینک‌های داخلی")
    links_external: int = Field(0, ge=0, description="تعداد لینک‌های خارجی")
    admonitions: int = Field(0, ge=0, description="تعداد جعبه‌های ویژه")
    diagrams_tikz: int = Field(0, ge=0, description="تعداد نمودارهای TikZ")
    diagrams_mermaid: int = Field(0, ge=0, description="تعداد نمودارهای Mermaid")
    words_approx: int = Field(0, ge=0, description="تعداد تقریبی کلمات")
    zwnj_count: int = Field(0, ge=0, description="تعداد نیم‌فاصله‌ها")

    @computed_field
    @property
    def total_math(self) -> int:
        """مجموع فرمول‌ها"""
        return self.math_inline + self.math_display

    @computed_field
    @property
    def total_diagrams(self) -> int:
        """مجموع نمودارها"""
        return self.diagrams_tikz + self.diagrams_mermaid

    @computed_field
    @property
    def total_links(self) -> int:
        """مجموع لینک‌ها"""
        return self.links_internal + self.links_external


class ConversionStats(BaseModel):
    """آمار تبدیل — Conversion statistics."""

    source_counts: ElementCounts = Field(
        default_factory=ElementCounts,
        description="شمارش عناصر ورودی",
    )
    output_counts: ElementCounts = Field(
        default_factory=ElementCounts,
        description="شمارش عناصر خروجی",
    )
    duration_seconds: float = Field(0.0, ge=0, description="مدت تبدیل (ثانیه)")
    output_size_bytes: int = Field(0, ge=0, description="حجم خروجی MDX (بایت)")
    assets_size_bytes: int = Field(0, ge=0, description="حجم فایل‌های وابسته (بایت)")

    @computed_field
    @property
    def total_output_size(self) -> int:
        """حجم کل خروجی"""
        return self.output_size_bytes + self.assets_size_bytes

    @computed_field
    @property
    def zwnj_preserved(self) -> bool:
        """آیا نیم‌فاصله‌ها حفظ شده‌اند"""
        return self.source_counts.zwnj_count == self.output_counts.zwnj_count

    @computed_field
    @property
    def zwnj_diff(self) -> int:
        """اختلاف تعداد نیم‌فاصله"""
        return self.source_counts.zwnj_count - self.output_counts.zwnj_count

    def element_ratio(self, element: str) -> float:
        """نسبت عنصر خروجی به ورودی (1.0 = کامل)"""
        src = getattr(self.source_counts, element, 0)
        out = getattr(self.output_counts, element, 0)
        if src == 0:
            return 1.0 if out == 0 else 0.0
        return min(out / src, 1.0)


# ──────────── مشکلات تبدیل ────────────


class ConversionIssue(BaseModel):
    """مشکل شناسایی‌شده در تبدیل — Issue found during conversion."""

    severity: IssueSeverity = Field(..., description="شدت")
    stage: str = Field("conversion", description="مرحله (conversion, test, deploy)")
    source_file: str = Field("", description="فایل مبدأ")
    source_line: int | None = Field(None, description="خط مبدأ")
    message: str = Field(..., description="پیام")
    suggestion: str = Field("", description="پیشنهاد اصلاح")
    auto_fixed: bool = Field(False, description="آیا خودکار اصلاح شد")
    element_type: str = Field("", description="نوع عنصر (math, table, image, ...)")


# ──────────── فایل خروجی ────────────


class OutputFile(BaseModel):
    """اطلاعات فایل خروجی — Output file information."""

    path: str = Field(..., description="مسیر خروجی")
    type: str = Field("mdx", description="نوع: mdx, svg, png, webp, json")
    size_bytes: int = Field(0, ge=0, description="حجم (بایت)")
    is_main: bool = Field(False, description="آیا فایل MDX اصلی است")
    source_path: str | None = Field(None, description="مسیر فایل مبدأ")


# ──────────── گزارش کیفیت ────────────


class QualityReport(BaseModel):
    """گزارش تست کیفیت — Quality test report."""

    # امتیازهای جزئی (هر کدام 0-100)
    structural_score: int = Field(0, ge=0, le=100, description="امتیاز ساختاری")
    content_score: int = Field(0, ge=0, le=100, description="امتیاز محتوایی")
    math_score: int = Field(0, ge=0, le=100, description="امتیاز ریاضی")
    persian_score: int = Field(0, ge=0, le=100, description="امتیاز فارسی/RTL")
    link_score: int = Field(0, ge=0, le=100, description="امتیاز لینک‌ها")
    visual_score: int | None = Field(None, ge=0, le=100, description="امتیاز بصری (اختیاری)")

    # جزئیات
    tests_passed: int = Field(0, ge=0, description="تعداد تست‌های موفق")
    tests_failed: int = Field(0, ge=0, description="تعداد تست‌های ناموفق")
    tests_skipped: int = Field(0, ge=0, description="تعداد تست‌های نادیده‌گرفته‌شده")

    # مشکلات
    issues: list[ConversionIssue] = Field(
        default_factory=list,
        description="مشکلات کیفیتی",
    )

    @computed_field
    @property
    def total_score(self) -> int:
        """امتیاز کلی (وزنی) — Weighted total quality score."""
        # وزن‌ها: ساختاری 25%, محتوا 25%, ریاضی 20%, فارسی 20%, لینک 10%
        score = (
            self.structural_score * 0.25
            + self.content_score * 0.25
            + self.math_score * 0.20
            + self.persian_score * 0.20
            + self.link_score * 0.10
        )
        return round(score)

    @computed_field
    @property
    def grade(self) -> QualityGrade:
        """درجه کیفیت"""
        return QualityGrade.from_score(self.total_score)

    @computed_field
    @property
    def total_tests(self) -> int:
        """تعداد کل تست‌ها"""
        return self.tests_passed + self.tests_failed + self.tests_skipped

    def passes_threshold(self, threshold: int = 80) -> bool:
        """آیا از حد مجاز عبور می‌کند"""
        return self.total_score >= threshold


# ──────────── نتیجه تبدیل اصلی ────────────


class ConversionResult(BaseModel):
    """
    نتیجه کامل تبدیل یک سند — Complete conversion result for one document.
    خروجی مرحله ۳ (Stage 3).
    """

    # شناسه و وضعیت
    conversion_id: str = Field(..., description="شناسه تبدیل")
    status: ConversionStatus = Field(..., description="وضعیت تبدیل")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="زمان تبدیل",
    )

    # ورودی
    source_path: str = Field(..., description="مسیر فایل ورودی")
    source_format: DocumentFormat = Field(..., description="فرمت ورودی")

    # خروجی
    output_files: list[OutputFile] = Field(
        default_factory=list,
        description="فایل‌های خروجی",
    )
    mdx_content: str | None = Field(
        None,
        description="محتوای MDX تولیدشده (برای تک‌فایل)",
        exclude=True,  # از سریالایز JSON/YAML مستثنی
    )

    # متادیتا
    metadata: DocumentMetadata | None = Field(None, description="متادیتای استخراج‌شده")

    # آمار
    stats: ConversionStats = Field(
        default_factory=ConversionStats,
        description="آمار تبدیل",
    )

    # کیفیت
    quality: QualityReport | None = Field(None, description="گزارش کیفیت")

    # مشکلات
    issues: list[ConversionIssue] = Field(
        default_factory=list,
        description="مشکلات تبدیل",
    )

    # ─── فیلدهای محاسبه‌ای ───

    @computed_field
    @property
    def is_success(self) -> bool:
        """آیا تبدیل موفق بود"""
        return self.status == ConversionStatus.SUCCESS

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
    def quality_score(self) -> int:
        """امتیاز کیفیت (0-100)"""
        if self.quality:
            return self.quality.total_score
        return 0

    @computed_field
    @property
    def main_output_file(self) -> str | None:
        """مسیر فایل MDX اصلی"""
        for f in self.output_files:
            if f.is_main:
                return f.path
        return self.output_files[0].path if self.output_files else None

    # ─── متدها ───

    def add_issue(
        self,
        severity: IssueSeverity,
        message: str,
        *,
        source_file: str = "",
        source_line: int | None = None,
        suggestion: str = "",
        auto_fixed: bool = False,
        element_type: str = "",
    ) -> None:
        """اضافه کردن مشکل"""
        self.issues.append(
            ConversionIssue(
                severity=severity,
                message=message,
                source_file=source_file,
                source_line=source_line,
                suggestion=suggestion,
                auto_fixed=auto_fixed,
                element_type=element_type,
            )
        )

    def add_output_file(
        self,
        path: str,
        type: str = "mdx",
        size_bytes: int = 0,
        is_main: bool = False,
        source_path: str | None = None,
    ) -> None:
        """اضافه کردن فایل خروجی"""
        self.output_files.append(
            OutputFile(
                path=path,
                type=type,
                size_bytes=size_bytes,
                is_main=is_main,
                source_path=source_path,
            )
        )

    @classmethod
    def create_success(
        cls,
        conversion_id: str,
        source_path: str,
        source_format: DocumentFormat,
    ) -> "ConversionResult":
        """ساخت نتیجه موفق — Create successful result."""
        return cls(
            conversion_id=conversion_id,
            status=ConversionStatus.SUCCESS,
            source_path=source_path,
            source_format=source_format,
        )

    @classmethod
    def create_failure(
        cls,
        conversion_id: str,
        source_path: str,
        source_format: DocumentFormat,
        error_message: str,
    ) -> "ConversionResult":
        """ساخت نتیجه ناموفق — Create failed result."""
        result = cls(
            conversion_id=conversion_id,
            status=ConversionStatus.FAILED,
            source_path=source_path,
            source_format=source_format,
        )
        result.add_issue(IssueSeverity.ERROR, error_message)
        return result


# ──────────── نتایج دسته‌ای ────────────


class BatchConversionResult(BaseModel):
    """نتیجه تبدیل دسته‌ای — Batch conversion result for multiple documents."""

    batch_id: str = Field(..., description="شناسه دسته")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="زمان شروع",
    )
    results: list[ConversionResult] = Field(
        default_factory=list,
        description="نتایج تک‌تک تبدیل‌ها",
    )
    total_duration_seconds: float = Field(0.0, ge=0, description="مدت کل")

    @computed_field
    @property
    def total(self) -> int:
        return len(self.results)

    @computed_field
    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.is_success)

    @computed_field
    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if r.status == ConversionStatus.FAILED)

    @computed_field
    @property
    def avg_quality_score(self) -> int:
        scores = [r.quality_score for r in self.results if r.quality_score > 0]
        return round(sum(scores) / len(scores)) if scores else 0

    @computed_field
    @property
    def all_zwnj_preserved(self) -> bool:
        """آیا تمام نیم‌فاصله‌ها در تمام اسناد حفظ شده"""
        return all(r.stats.zwnj_preserved for r in self.results)