"""
FormatForge - Configuration Schema
شِمای تنظیمات اپلیکیشن با Pydantic v2 Settings

All configuration models with type hints, defaults, and validators.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# General / عمومی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class GeneralConfig(BaseModel):
    """تنظیمات عمومی اپلیکیشن. / General application settings."""

    language: Literal["fa", "en"] = Field(
        default="fa", description="زبان رابط کاربری"
    )
    verbose: bool = Field(default=True, description="نمایش جزئیات بیشتر")
    color: bool = Field(default=True, description="خروجی رنگی")
    confirm_before_convert: bool = Field(
        default=True, description="تأیید قبل از تبدیل"
    )
    confirm_before_deploy: bool = Field(
        default=True, description="تأیید قبل از استقرار"
    )
    auto_fix_warnings: bool = Field(
        default=False, description="اصلاح خودکار هشدارها"
    )
    temp_dir: str = Field(
        default="~/.formatforge/temp/", description="پوشه موقت"
    )
    log_dir: str = Field(
        default="~/.formatforge/logs/", description="پوشه لاگ"
    )
    report_file: str = Field(
        default="~/.formatforge/central_log.yaml",
        description="فایل گزارش مرکزی",
    )

    @field_validator("temp_dir", "log_dir", "report_file")
    @classmethod
    def expand_user_path(cls, v: str) -> str:
        """تبدیل ~ به مسیر واقعی کاربر."""
        return str(Path(v).expanduser())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Scanner / اسکنر
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SUPPORTED_FORMATS = frozenset({
    "latex", "html", "markdown", "docx", "pdf",
    "rst", "asciidoc", "epub", "notebook",
})


class ScannerConfig(BaseModel):
    """تنظیمات اسکنر ورودی. / Input scanner settings."""

    max_file_size_mb: int = Field(
        default=100, ge=1, le=2048, description="حداکثر اندازه فایل (MB)"
    )
    supported_formats: list[str] = Field(
        default_factory=lambda: [
            "latex", "html", "markdown", "docx", "pdf",
            "rst", "asciidoc", "epub", "notebook",
        ],
        description="فرمت‌های پشتیبانی‌شده",
    )
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            "*.aux", "*.log", "*.synctex*", "*.fls",
            "*.fdb_latexmk", ".git/", "node_modules/",
            "__pycache__/", ".DS_Store", "Thumbs.db",
        ],
        description="الگوهای نادیده‌گرفتن",
    )

    @field_validator("supported_formats")
    @classmethod
    def validate_formats(cls, v: list[str]) -> list[str]:
        """بررسی فرمت‌های معتبر."""
        for fmt in v:
            if fmt.lower() not in _SUPPORTED_FORMATS:
                raise ValueError(
                    f"فرمت «{fmt}» پشتیبانی نمی\u200cشود. "
                    f"مجاز: {sorted(_SUPPORTED_FORMATS)}"
                )
        return [f.lower() for f in v]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Metadata / متادیتا
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DefaultAuthorConfig(BaseModel):
    """اطلاعات نویسنده پیش‌فرض."""

    name: str = Field(default="", description="نام فارسی نویسنده")
    name_en: Optional[str] = Field(
        default=None, alias="nameEn", description="نام انگلیسی"
    )
    email: Optional[str] = Field(default=None, description="ایمیل")

    model_config = {"populate_by_name": True}


class AIAutoCompleteConfig(BaseModel):
    """تنظیمات تکمیل خودکار با AI."""

    description: bool = Field(default=True, description="تولید خلاصه")
    tags: bool = Field(default=True, description="تولید برچسب")
    title_en: bool = Field(default=True, description="ترجمه عنوان")
    slug: bool = Field(default=True, description="تولید slug")


class MetadataConfig(BaseModel):
    """تنظیمات متادیتا و frontmatter. / Metadata settings."""

    default_author: DefaultAuthorConfig = Field(
        default_factory=DefaultAuthorConfig, description="نویسنده پیش‌فرض"
    )
    default_lang: Literal["fa", "en", "fa-en"] = Field(
        default="fa", description="زبان پیش‌فرض"
    )
    default_dir: Literal["rtl", "ltr"] = Field(
        default="rtl", description="جهت پیش‌فرض"
    )
    slug_max_length: int = Field(
        default=60, ge=10, le=200, description="حداکثر طول slug"
    )
    slug_transliterate: bool = Field(
        default=True, description="آیا فارسی به لاتین تبدیل شود"
    )
    ai_provider: Literal[
        "openai", "anthropic", "google", "ollama", "none"
    ] = Field(default="none", description="ارائه‌دهنده AI")
    ai_model: str = Field(default="gpt-4o", description="مدل AI")
    ai_auto_complete: AIAutoCompleteConfig = Field(
        default_factory=AIAutoCompleteConfig, description="تکمیل خودکار AI"
    )
    require_fields: list[str] = Field(
        default_factory=lambda: [
            "title", "slug", "date", "lang", "dir", "author",
        ],
        description="فیلدهای اجباری frontmatter",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Conversion sub-models / زیرمدل‌های تبدیل
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MathConfig(BaseModel):
    """تنظیمات ریاضی. / Math rendering settings."""

    engine: Literal["katex", "mathjax"] = Field(
        default="katex", description="موتور رندر ریاضی"
    )
    display_mode_delimiters: list[str] = Field(
        default_factory=lambda: ["$$", "$$"],
        description="جداکننده حالت نمایشی",
    )
    inline_mode_delimiters: list[str] = Field(
        default_factory=lambda: ["$", "$"],
        description="جداکننده حالت درون‌خطی",
    )
    throw_on_error: bool = Field(
        default=False, description="خطا در فرمول نامعتبر"
    )
    macros: dict[str, str] = Field(
        default_factory=dict, description="ماکروهای سفارشی KaTeX"
    )


class DiagramsConfig(BaseModel):
    """تنظیمات نمودار. / Diagram conversion settings."""

    tikz_to: Literal["svg", "png"] = Field(
        default="svg", description="فرمت خروجی TikZ"
    )
    tikz_dpi: int = Field(
        default=300, ge=72, le=600, description="DPI برای PNG"
    )
    mermaid_to: Literal["component", "svg", "png"] = Field(
        default="component", description="فرمت خروجی Mermaid"
    )
    mermaid_theme: str = Field(
        default="base", description="تم Mermaid"
    )


class ImagesConfig(BaseModel):
    """تنظیمات تصویر. / Image processing settings."""

    optimize: bool = Field(default=True, description="بهینه‌سازی تصاویر")
    convert_to_webp: bool = Field(
        default=True, description="تبدیل به WebP"
    )
    max_width: int = Field(
        default=1200, ge=100, le=4096, description="حداکثر عرض (px)"
    )
    quality: int = Field(
        default=85, ge=1, le=100, description="کیفیت فشرده‌سازی"
    )
    svg_optimize: bool = Field(
        default=True, description="بهینه‌سازی SVG"
    )


class CodeConfig(BaseModel):
    """تنظیمات بلوک کد. / Code block settings."""

    add_line_numbers: bool = Field(
        default=False, description="شماره‌گذاری خطوط"
    )
    default_language: str = Field(
        default="text", description="زبان پیش‌فرض"
    )
    highlight_theme: str = Field(
        default="github-dark", description="تم هایلایت"
    )


class TablesConfig(BaseModel):
    """تنظیمات جدول. / Table conversion settings."""

    complex_to_html: bool = Field(
        default=True, description="جداول پیچیده → HTML"
    )
    simple_to_markdown: bool = Field(
        default=True, description="جداول ساده → MD pipe"
    )


class PersianConfig(BaseModel):
    """
    تنظیمات فارسی‌سازی (حیاتی).
    Persian text processing settings — ZWNJ preservation is mandatory.
    """

    preserve_zwnj: bool = Field(
        default=True, description="حفظ نیم\u200cفاصله (غیرقابل تغییر!)"
    )
    fix_arabic_yeh: bool = Field(
        default=True, description="ي → ی"
    )
    fix_arabic_keh: bool = Field(
        default=True, description="ك → ک"
    )
    fix_spacing: bool = Field(
        default=True, description="اصلاح فاصله\u200cگذاری فارسی"
    )
    numerals: Literal["persian", "latin", "keep"] = Field(
        default="persian", description="نوع ارقام"
    )
    quotation_marks: Literal["guillemet", "standard"] = Field(
        default="guillemet", description="نوع گیومه: «» یا \"\""
    )

    @model_validator(mode="after")
    def enforce_zwnj_preservation(self) -> "PersianConfig":
        """نیم‌فاصله هرگز نباید غیرفعال شود!"""
        if not self.preserve_zwnj:
            self.preserve_zwnj = True
        return self


class MdxConfig(BaseModel):
    """تنظیمات خروجی MDX."""

    component_style: Literal["import", "inline", "global"] = Field(
        default="import", description="سبک کامپوننت"
    )
    jsx_runtime: Literal["react", "preact"] = Field(
        default="react", description="JSX runtime"
    )
    mdx_version: Literal[2, 3] = Field(
        default=3, description="نسخه MDX"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Conversion aggregate / تبدیل
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConversionConfig(BaseModel):
    """تنظیمات کلی تبدیل. / All conversion-related settings."""

    math: MathConfig = Field(default_factory=MathConfig)
    diagrams: DiagramsConfig = Field(default_factory=DiagramsConfig)
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    code: CodeConfig = Field(default_factory=CodeConfig)
    tables: TablesConfig = Field(default_factory=TablesConfig)
    persian: PersianConfig = Field(default_factory=PersianConfig)
    mdx: MdxConfig = Field(default_factory=MdxConfig)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Testing / تست
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestingConfig(BaseModel):
    """تنظیمات تست کیفیت. / Quality testing settings."""

    run_structural: bool = Field(default=True, description="تست ساختاری")
    run_content: bool = Field(default=True, description="تست محتوایی")
    run_math: bool = Field(default=True, description="تست ریاضی")
    run_persian: bool = Field(default=True, description="تست فارسی")
    run_links: bool = Field(default=True, description="تست لینک‌ها")
    run_visual: bool = Field(
        default=False, description="تست بصری (نیاز به Playwright)"
    )
    min_quality_score: int = Field(
        default=80, ge=0, le=100, description="حداقل امتیاز قبول"
    )
    visual_compare_with_source: bool = Field(
        default=False, description="مقایسه بصری با اصل"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Deployment / استقرار
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PostDeployConfig(BaseModel):
    """تنظیمات پس از استقرار."""

    open_in_editor: bool = Field(default=False, description="باز کردن در ادیتور")
    editor_command: str = Field(default="code", description="دستور ادیتور")
    run_dev_server: bool = Field(default=False, description="اجرای سرور dev")
    dev_command: str = Field(default="npm run dev", description="دستور dev")
    git_commit: bool = Field(default=False, description="کامیت خودکار")
    git_push: bool = Field(default=False, description="پوش خودکار")


class DeploymentConfig(BaseModel):
    """تنظیمات استقرار خروجی. / Deployment settings."""

    target_dir: str = Field(
        default="./output/", description="پوشه خروجی نهایی"
    )
    create_backup: bool = Field(default=True, description="ایجاد بکاپ")
    backup_dir: str = Field(
        default="~/.formatforge/backups/", description="پوشه بکاپ"
    )
    overwrite_existing: Literal["ask", "yes", "no", "rename"] = Field(
        default="ask", description="رفتار با فایل موجود"
    )
    post_deploy: PostDeployConfig = Field(
        default_factory=PostDeployConfig, description="تنظیمات پس از استقرار"
    )

    @field_validator("target_dir", "backup_dir")
    @classmethod
    def expand_paths(cls, v: str) -> str:
        """تبدیل ~ به مسیر واقعی."""
        return str(Path(v).expanduser())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Reporting / گزارش
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ReportingConfig(BaseModel):
    """تنظیمات گزارش‌دهی. / Reporting settings."""

    format: Literal["yaml", "json", "csv", "html"] = Field(
        default="yaml", description="فرمت گزارش"
    )
    keep_history: bool = Field(default=True, description="نگه‌داری تاریخچه")
    max_history: int = Field(
        default=1000, ge=10, le=100000, description="حداکثر تاریخچه"
    )
    export_on_milestone: bool = Field(
        default=True, description="خروجی هر ۱۰ تبدیل"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Root / تنظیمات اصلی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AppConfig(BaseModel):
    """
    تنظیمات کامل اپلیکیشن FormatForge.
    Root configuration model aggregating all sections.
    """

    general: GeneralConfig = Field(default_factory=GeneralConfig)
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    testing: TestingConfig = Field(default_factory=TestingConfig)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def enforce_persian_rules(self) -> "AppConfig":
        """اعمال قواعد حیاتی فارسی."""
        # نیم‌فاصله هرگز غیرفعال نشود
        self.conversion.persian.preserve_zwnj = True
        # زبان فارسی → جهت rtl
        if self.metadata.default_lang == "fa":
            self.metadata.default_dir = "rtl"
        return self
