"""
FormatForge - Conversion Result Models
مدل‌های نتیجه تبدیل

Models for tracking conversion output: statistics, quality reports,
and per-document conversion results.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────
# Sub-models / مدل‌های فرعی
# ─────────────────────────────────────────────

class ZWNJReport(BaseModel):
    """
    گزارش نیم‌فاصله.
    Report on ZWNJ preservation during conversion.
    """

    count_before: int = Field(
        default=0, ge=0, description="تعداد ZWNJ قبل از تبدیل"
    )
    count_after: int = Field(
        default=0, ge=0, description="تعداد ZWNJ بعد از تبدیل"
    )
    preserved: bool = Field(
        default=True, description="آیا همه ZWNJ حفظ شده‌اند"
    )
    lost_positions: list[int] = Field(
        default_factory=list,
        description="موقعیت ZWNJ‌های از دست رفته (شماره خط)",
    )

    @model_validator(mode="after")
    def check_preserved(self) -> "ZWNJReport":
        """بررسی خودکار حفظ ZWNJ."""
        self.preserved = self.count_before == self.count_after
        return self


class QualityReport(BaseModel):
    """
    گزارش کیفیت تبدیل.
    Quality assessment report for a converted document.
    """

    score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="امتیاز کلی کیفیت (۰ تا ۱۰۰)",
    )

    # ─── بررسی‌های فارسی / Persian checks ────

    zwnj: ZWNJReport = Field(
        default_factory=ZWNJReport,
        description="گزارش نیم‌فاصله",
    )
    bidi_correct: bool = Field(
        default=False,
        description="آیا جهت‌دهی دوطرفه صحیح است",
    )
    persian_chars_normalized: bool = Field(
        default=False,
        description="آیا ي و ك به ی و ک تبدیل شده‌اند",
    )
    guillemets_used: bool = Field(
        default=False,
        description="آیا از گیومه «» استفاده شده",
    )

    # ─── بررسی‌های محتوایی / Content checks ──

    math_rendered: bool = Field(
        default=False,
        description="آیا فرمول‌های ریاضی درست تبدیل شده‌اند",
    )
    math_block_count: int = Field(
        default=0, ge=0, description="تعداد بلوک‌های ریاضی"
    )
    math_inline_count: int = Field(
        default=0, ge=0, description="تعداد فرمول‌های درون‌خطی"
    )
    tables_converted: bool = Field(
        default=False,
        description="آیا جداول درست تبدیل شده‌اند",
    )
    tables_count: int = Field(
        default=0, ge=0, description="تعداد جداول"
    )
    images_linked: bool = Field(
        default=False,
        description="آیا تصاویر درست لینک شده‌اند",
    )
    images_count: int = Field(
        default=0, ge=0, description="تعداد تصاویر"
    )
    images_missing: list[str] = Field(
        default_factory=list,
        description="تصاویر گم‌شده",
    )
    code_blocks_count: int = Field(
        default=0, ge=0, description="تعداد بلوک‌های کد"
    )
    headings_count: int = Field(
        default=0, ge=0, description="تعداد سرتیترها"
    )
    links_count: int = Field(
        default=0, ge=0, description="تعداد لینک‌ها"
    )
    links_broken: list[str] = Field(
        default_factory=list,
        description="لینک‌های شکسته",
    )

    # ─── بررسی ساختاری / Structural checks ───

    frontmatter_valid: bool = Field(
        default=False,
        description="آیا frontmatter معتبر است",
    )
    mdx_valid: bool = Field(
        default=False,
        description="آیا خروجی MDX معتبر است (قابل parse)",
    )

    # ─── خلاصه مشکلات / Issues ───────────────

    issues: list[str] = Field(
        default_factory=list,
        description="لیست مشکلات شناسایی‌شده",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="لیست پیشنهادات بهبود",
    )

    def compute_score(self) -> float:
        """
        محاسبه خودکار امتیاز کیفیت.
        Auto-compute quality score based on checks.
        """
        total = 0.0
        max_score = 0.0

        checks = [
            (self.zwnj.preserved, 20.0),
            (self.bidi_correct, 15.0),
            (self.persian_chars_normalized, 5.0),
            (self.guillemets_used, 5.0),
            (self.frontmatter_valid, 10.0),
            (self.mdx_valid, 15.0),
            (self.math_rendered, 10.0),
            (self.tables_converted, 5.0),
            (self.images_linked, 10.0),
            (len(self.links_broken) == 0, 5.0),
        ]

        for passed, weight in checks:
            max_score += weight
            if passed:
                total += weight

        self.score = round((total / max_score) * 100, 1) if max_score > 0 else 0.0
        return self.score


class ConversionStats(BaseModel):
    """
    آمار کلی تبدیل.
    Aggregate statistics for a conversion run.
    """

    total_documents: int = Field(
        default=0, ge=0, description="تعداد کل اسناد"
    )
    successful: int = Field(
        default=0, ge=0, description="تعداد تبدیل‌های موفق"
    )
    failed: int = Field(
        default=0, ge=0, description="تعداد تبدیل‌های ناموفق"
    )
    skipped: int = Field(
        default=0, ge=0, description="تعداد اسناد نادیده گرفته‌شده"
    )
    warnings_count: int = Field(
        default=0, ge=0, description="تعداد هشدارها"
    )
    duration_seconds: float = Field(
        default=0.0, ge=0.0, description="مدت زمان کل (ثانیه)"
    )
    total_input_bytes: int = Field(
        default=0, ge=0, description="حجم کل ورودی (بایت)"
    )
    total_output_bytes: int = Field(
        default=0, ge=0, description="حجم کل خروجی (بایت)"
    )
    average_quality_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="میانگین امتیاز کیفیت"
    )

    @property
    def success_rate(self) -> float:
        """درصد موفقیت."""
        if self.total_documents == 0:
            return 0.0
        return round((self.successful / self.total_documents) * 100, 1)

    @property
    def all_successful(self) -> bool:
        """آیا همه تبدیل‌ها موفق بوده‌اند."""
        return self.failed == 0 and self.successful == self.total_documents

    @model_validator(mode="after")
    def validate_counts(self) -> "ConversionStats":
        """بررسی سازگاری اعداد."""
        total = self.successful + self.failed + self.skipped
        if total > self.total_documents:
            raise ValueError(
                f"مجموع موفق ({self.successful}) + ناموفق ({self.failed}) "
                f"+ نادیده ({self.skipped}) = {total} "
                f"بیشتر از کل ({self.total_documents}) است."
            )
        return self


class DocumentConversionResult(BaseModel):
    """
    نتیجه تبدیل یک سند منفرد.
    Conversion result for a single document.
    """

    document_id: str = Field(
        ..., description="شناسه سند (از ScanReport)"
    )
    source_path: str = Field(
        ..., description="مسیر فایل ورودی"
    )
    output_path: Optional[str] = Field(
        default=None, description="مسیر فایل خروجی MDX"
    )
    status: str = Field(
        default="pending",
        pattern=r"^(pending|processing|success|failed|skipped)$",
        description="وضعیت تبدیل",
    )
    error_message: Optional[str] = Field(
        default=None, description="پیام خطا (در صورت شکست)"
    )
    quality: QualityReport = Field(
        default_factory=QualityReport,
        description="گزارش کیفیت",
    )
    duration_seconds: float = Field(
        default=0.0, ge=0.0, description="مدت زمان تبدیل (ثانیه)"
    )
    input_bytes: int = Field(
        default=0, ge=0, description="حجم ورودی (بایت)"
    )
    output_bytes: int = Field(
        default=0, ge=0, description="حجم خروجی (بایت)"
    )
    notes: list[str] = Field(
        default_factory=list,
        description="یادداشت‌های تبدیل",
    )


# ─────────────────────────────────────────────
# Main Model / مدل اصلی
# ─────────────────────────────────────────────

class ConversionResult(BaseModel):
    """
    نتیجه کامل یک فرآیند تبدیل.
    Full result of a conversion run (one or more documents).
    """

    conversion_id: str = Field(
        default_factory=lambda: f"conv_{uuid.uuid4().hex[:12]}",
        description="شناسه یکتای تبدیل",
    )
    scan_id: str = Field(
        ...,
        description="شناسه اسکن مرتبط (از ScanReport)",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="زمان شروع تبدیل (ISO 8601)",
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="زمان پایان تبدیل (ISO 8601)",
    )
    status: str = Field(
        default="pending",
        pattern=r"^(pending|processing|completed|partial|failed)$",
        description="وضعیت کلی: pending | processing | completed | partial | failed",
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="پوشه خروجی",
    )

    # ─── نتایج جزئی / Per-document results ──

    documents: list[DocumentConversionResult] = Field(
        default_factory=list,
        description="نتایج تبدیل هر سند",
    )

    # ─── آمار / Statistics ───────────────────

    stats: ConversionStats = Field(
        default_factory=ConversionStats,
        description="آمار کلی تبدیل",
    )

    # ─── یادداشت‌ها / Notes ──────────────────

    notes: list[str] = Field(
        default_factory=list,
        description="یادداشت‌های کلی فرآیند",
    )
    converter_version: str = Field(
        default="0.1.0",
        description="نسخه ابزار تبدیل",
    )

    # ─── Helpers / متدهای کمکی ───────────────

    def compute_stats(self) -> ConversionStats:
        """
        محاسبه خودکار آمار بر اساس نتایج جزئی.
        Auto-compute aggregate stats from per-document results.
        """
        total = len(self.documents)
        successful = sum(1 for d in self.documents if d.status == "success")
        failed = sum(1 for d in self.documents if d.status == "failed")
        skipped = sum(1 for d in self.documents if d.status == "skipped")
        warnings_count = sum(len(d.quality.issues) for d in self.documents)
        duration = sum(d.duration_seconds for d in self.documents)
        input_bytes = sum(d.input_bytes for d in self.documents)
        output_bytes = sum(d.output_bytes for d in self.documents)

        scores = [
            d.quality.score for d in self.documents if d.status == "success"
        ]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        self.stats = ConversionStats(
            total_documents=total,
            successful=successful,
            failed=failed,
            skipped=skipped,
            warnings_count=warnings_count,
            duration_seconds=round(duration, 3),
            total_input_bytes=input_bytes,
            total_output_bytes=output_bytes,
            average_quality_score=avg_score,
        )
        return self.stats

    def mark_completed(self) -> None:
        """
        علامت‌گذاری پایان تبدیل.
        Mark the conversion as completed and compute stats.
        """
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.compute_stats()

        if self.stats.failed == 0:
            self.status = "completed"
        elif self.stats.successful > 0:
            self.status = "partial"
        else:
            self.status = "failed"

    def get_failed_documents(self) -> list[DocumentConversionResult]:
        """لیست اسناد ناموفق."""
        return [d for d in self.documents if d.status == "failed"]

    def get_successful_documents(self) -> list[DocumentConversionResult]:
        """لیست اسناد موفق."""
        return [d for d in self.documents if d.status == "success"]

    def summary(self) -> str:
        """
        خلاصه متنی نتیجه تبدیل.
        Generate a human-readable summary string.
        """
        lines = [
            f"\U0001f4ca نتیجه تبدیل: {self.conversion_id}",
            "\u2501" * 40,
            f"  وضعیت:     {self.status}",
            f"  کل اسناد:  {self.stats.total_documents}",
            f"  موفق:      {self.stats.successful}",
            f"  ناموفق:    {self.stats.failed}",
            f"  نادیده:    {self.stats.skipped}",
            f"  مدت:       {self.stats.duration_seconds:.1f} ثانیه",
            f"  کیفیت:     {self.stats.average_quality_score:.1f}/100",
        ]

        failed = self.get_failed_documents()
        if failed:
            lines.append("")
            lines.append("  \u274c اسناد ناموفق:")
            for doc in failed:
                lines.append(f"    - {doc.source_path}: {doc.error_message}")

        return "\n".join(lines)
