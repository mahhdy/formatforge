"""
مدل متادیتای سند — Document Metadata Model.
شامل تمام اطلاعات frontmatter و SEO مورد نیاز برای MDX.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from formatforge.models.enums import (
    DocumentDirection,
    DocumentFormat,
    DocumentLanguage,
    DocumentType,
)

# ──────────── ثابت‌ها ────────────

ZWNJ = "\u200c"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX_LENGTH = 60


# ──────────── مدل‌های فرعی ────────────


class AuthorInfo(BaseModel):
    """اطلاعات نویسنده — Author information."""

    name: str = Field(..., min_length=1, description="نام نویسنده (فارسی)")
    name_en: str | None = Field(None, description="نام نویسنده (انگلیسی)")
    email: str | None = Field(None, description="ایمیل")
    url: str | None = Field(None, description="وب‌سایت")
    affiliation: str | None = Field(None, description="وابستگی سازمانی")


class SeriesInfo(BaseModel):
    """اطلاعات مجموعه — Series information (for multi-chapter books)."""

    name: str = Field(..., description="نام مجموعه")
    slug: str = Field(..., description="Slug مجموعه")
    order: int = Field(..., ge=0, description="ترتیب در مجموعه")
    total: int | None = Field(None, ge=1, description="تعداد کل اجزا")


class AssetReference(BaseModel):
    """ارجاع به فایل وابسته — Asset file reference."""

    path: str = Field(..., description="مسیر فایل")
    type: str = Field(..., description="نوع فایل (image/png, image/svg, etc.)")
    alt_text: str | None = Field(None, description="متن جایگزین (برای تصاویر)")
    original_path: str | None = Field(None, description="مسیر اصلی قبل از تبدیل")


# ──────────── مدل اصلی ────────────


class DocumentMetadata(BaseModel):
    """
    متادیتای کامل یک سند — Complete document metadata.
    این مدل مستقیماً به frontmatter فایل MDX تبدیل می‌شود.

    Full metadata schema for a document. This model maps directly
    to the MDX frontmatter output.
    """

    # ─── اجباری (Required) ───
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="عنوان سند (فارسی)",
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=SLUG_MAX_LENGTH,
        description="مسیر URL (فقط a-z, 0-9, -)",
    )
    date: str = Field(
        ...,
        description="تاریخ انتشار (ISO 8601: YYYY-MM-DD)",
    )
    lang: DocumentLanguage = Field(
        DocumentLanguage.PERSIAN,
        description="زبان اصلی سند",
    )
    dir: DocumentDirection = Field(
        DocumentDirection.RTL,
        description="جهت اصلی متن",
    )

    # ─── نویسنده ───
    author: AuthorInfo | None = Field(None, description="اطلاعات نویسنده")

    # ─── عنوان انگلیسی ───
    title_en: str | None = Field(None, max_length=200, description="عنوان انگلیسی")

    # ─── دسته‌بندی ───
    type: DocumentType = Field(
        DocumentType.ARTICLE,
        description="نوع سند",
    )
    tags: list[str] = Field(default_factory=list, description="برچسب‌ها (فارسی)")
    tags_en: list[str] = Field(default_factory=list, description="برچسب‌ها (انگلیسی)")
    categories: list[str] = Field(default_factory=list, description="دسته‌بندی‌ها")
    series: SeriesInfo | None = Field(None, description="اطلاعات مجموعه")

    # ─── محتوا ───
    description: str = Field(
        "",
        max_length=500,
        description="خلاصه (فارسی، حداکثر ۵۰۰ کاراکتر)",
    )
    description_en: str | None = Field(None, max_length=500, description="خلاصه انگلیسی")
    abstract: str | None = Field(None, description="چکیده مفصل")
    keywords: list[str] = Field(default_factory=list, description="کلمات کلیدی")
    toc: bool = Field(True, description="نمایش فهرست مطالب")
    math: bool = Field(False, description="آیا شامل ریاضی است")
    mermaid: bool = Field(False, description="آیا شامل نمودار Mermaid است")
    code_highlight: bool = Field(False, description="آیا شامل کد است")

    # ─── فایل‌ها ───
    source_format: DocumentFormat = Field(
        DocumentFormat.UNKNOWN,
        description="فرمت اصلی",
    )
    source_file: str = Field("", description="نام فایل اصلی")
    assets: list[AssetReference] = Field(
        default_factory=list,
        description="فایل‌های وابسته",
    )
    featured_image: str | None = Field(None, description="تصویر شاخص")

    # ─── SEO و وب ───
    canonical: str | None = Field(None, description="URL کانونیکال")
    no_index: bool = Field(False, description="عدم ایندکس توسط موتور جستجو")
    og_image: str | None = Field(None, description="تصویر Open Graph")

    # ─── تبدیل ───
    converted_at: str | None = Field(None, description="زمان تبدیل (ISO 8601)")
    converter_version: str | None = Field(None, description="نسخه FormatForge")
    quality_score: int | None = Field(None, ge=0, le=100, description="امتیاز کیفیت")
    conversion_notes: list[str] = Field(
        default_factory=list,
        description="یادداشت‌های تبدیل",
    )

    # ─── اعتبارسنجی (Validators) ───

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """بررسی فرمت slug — Validate slug format (a-z, 0-9, hyphens only)."""
        v = v.strip().lower()
        if not SLUG_PATTERN.match(v):
            raise ValueError(
                f"Slug نامعتبر: '{v}'. فقط حروف کوچک لاتین، اعداد و خط‌تیره مجاز است."
            )
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """بررسی فرمت تاریخ — Validate ISO 8601 date format."""
        v = v.strip()
        try:
            datetime.fromisoformat(v)
        except ValueError:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"تاریخ نامعتبر: '{v}'. فرمت مورد نیاز: YYYY-MM-DD")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """بررسی عنوان — Title should not be empty after stripping."""
        v = v.strip()
        if not v:
            raise ValueError("عنوان نمی‌تواند خالی باشد")
        return v

    @model_validator(mode="after")
    def set_direction_from_language(self) -> "DocumentMetadata":
        """تنظیم خودکار جهت بر اساس زبان — Auto-set direction from language."""
        if self.lang == DocumentLanguage.ENGLISH and self.dir == DocumentDirection.RTL:
            # اگر زبان انگلیسی است ولی RTL تنظیم شده، اصلاح نمی‌کنیم
            # ممکن است عمدی باشد
            pass
        return self

    # ─── متدهای کمکی ───

    def has_zwnj(self) -> bool:
        """آیا عنوان شامل نیم‌فاصله است؟"""
        return ZWNJ in self.title

    def to_frontmatter_dict(self) -> dict:
        """تبدیل به دیکشنری frontmatter — Convert to frontmatter dict for MDX."""
        data = {
            "title": self.title,
            "slug": self.slug,
            "date": self.date,
            "lang": self.lang.value,
            "dir": self.dir.value,
        }

        if self.title_en:
            data["titleEn"] = self.title_en
        if self.author:
            data["author"] = self.author.model_dump(exclude_none=True)
        if self.type != DocumentType.UNKNOWN:
            data["type"] = self.type.value
        if self.tags:
            data["tags"] = self.tags
        if self.tags_en:
            data["tagsEn"] = self.tags_en
        if self.categories:
            data["categories"] = self.categories
        if self.series:
            data["series"] = self.series.model_dump(exclude_none=True)
        if self.description:
            data["description"] = self.description
        if self.description_en:
            data["descriptionEn"] = self.description_en
        if self.math:
            data["math"] = True
        if self.mermaid:
            data["mermaid"] = True
        if self.code_highlight:
            data["codeHighlight"] = True
        if self.toc:
            data["toc"] = True
        if self.featured_image:
            data["featuredImage"] = self.featured_image
        if self.source_format != DocumentFormat.UNKNOWN:
            data["sourceFormat"] = self.source_format.value
        if self.converted_at:
            data["convertedAt"] = self.converted_at
        if self.converter_version:
            data["converterVersion"] = self.converter_version
        if self.quality_score is not None:
            data["qualityScore"] = self.quality_score

        return data

    def to_frontmatter_yaml(self) -> str:
        """تبدیل به رشته YAML frontmatter — Convert to YAML frontmatter string."""
        import yaml

        data = self.to_frontmatter_dict()
        yaml_str = yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )
        return f"---\n{yaml_str}---\n"

    @classmethod
    def create_minimal(
        cls,
        title: str,
        slug: str,
        date: str | None = None,
    ) -> "DocumentMetadata":
        """ساخت نمونه حداقلی — Create minimal metadata instance."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return cls(title=title, slug=slug, date=date)