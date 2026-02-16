"""
FormatForge - Document Metadata Models
مدل‌های متادیتای سند برای FormatForge

Pydantic v2 models for document metadata, author info,
series info, and asset tracking with Persian ZWNJ validation.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────
# Constants / ثابت‌ها
# ─────────────────────────────────────────────

ZWNJ = "\u200c"  # نیم‌فاصله

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ARABIC_YEH = "\u064a"        # ي عربی
_ARABIC_KAF = "\u0643"        # ك عربی
_PERSIAN_YEH = "\u06cc"       # ی فارسی
_PERSIAN_KAF = "\u06a9"       # ک فارسی


# ─────────────────────────────────────────────
# Helpers / توابع کمکی
# ─────────────────────────────────────────────

def _count_zwnj(text: str) -> int:
    """شمارش تعداد نیم‌فاصله‌ها در متن."""
    return text.count(ZWNJ)


def _normalize_persian(text: str) -> str:
    """
    اصلاح ي→ی و ك→ک در متن فارسی.
    Normalize Arabic Yeh/Kaf to Persian equivalents.
    """
    text = text.replace(_ARABIC_YEH, _PERSIAN_YEH)
    text = text.replace(_ARABIC_KAF, _PERSIAN_KAF)
    return text


def _validate_persian_text(value: str, field_name: str) -> str:
    """
    اعتبارسنجی و نرمال‌سازی متن فارسی.
    - حفظ ZWNJ
    - اصلاح ي و ك
    - شمارش ZWNJ قبل/بعد

    Validate and normalize Persian text:
    - Preserve ZWNJ
    - Fix Arabic Yeh/Kaf
    - Count ZWNJ before/after normalization
    """
    if not value or not value.strip():
        return value

    zwnj_before = _count_zwnj(value)
    normalized = _normalize_persian(value)
    zwnj_after = _count_zwnj(normalized)

    if zwnj_before != zwnj_after:
        raise ValueError(
            f"فیلد «{field_name}»: تعداد نیم‌فاصله قبل ({zwnj_before}) "
            f"و بعد ({zwnj_after}) نرمال‌سازی متفاوت است!"
        )

    return normalized


def _validate_persian_list(values: list[str], field_name: str) -> list[str]:
    """اعتبارسنجی لیست رشته‌های فارسی."""
    return [_validate_persian_text(v, field_name) for v in values]


# ─────────────────────────────────────────────
# Sub-models / مدل‌های فرعی
# ─────────────────────────────────────────────

class AuthorInfo(BaseModel):
    """
    اطلاعات نویسنده.
    Author information sub-model.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="نام نویسنده (فارسی)",
    )
    name_en: Optional[str] = Field(
        default=None,
        max_length=200,
        alias="nameEn",
        description="Author name (English)",
    )
    email: Optional[str] = Field(
        default=None,
        max_length=254,
        description="آدرس ایمیل نویسنده",
    )
    url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="وب‌سایت نویسنده",
    )
    affiliation: Optional[str] = Field(
        default=None,
        max_length=300,
        description="وابستگی سازمانی نویسنده",
    )

    model_config = {"populate_by_name": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """اعتبارسنجی نام فارسی نویسنده."""
        return _validate_persian_text(v, "author.name")

    @field_validator("affiliation")
    @classmethod
    def validate_affiliation(cls, v: Optional[str]) -> Optional[str]:
        """اعتبارسنجی وابستگی سازمانی."""
        if v is not None:
            return _validate_persian_text(v, "author.affiliation")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """بررسی ساده فرمت ایمیل."""
        if v is not None and "@" not in v:
            raise ValueError("فرمت ایمیل نامعتبر است.")
        return v


class SeriesInfo(BaseModel):
    """
    اطلاعات مجموعه (سری).
    Series information for multi-part documents.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="نام مجموعه",
    )
    order: int = Field(
        ...,
        ge=1,
        description="شماره ترتیب در مجموعه",
    )
    total: Optional[int] = Field(
        default=None,
        ge=1,
        description="تعداد کل بخش‌های مجموعه",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """اعتبارسنجی نام فارسی مجموعه."""
        return _validate_persian_text(v, "series.name")

    @model_validator(mode="after")
    def validate_order_vs_total(self) -> "SeriesInfo":
        """بررسی اینکه ترتیب از کل بیشتر نباشد."""
        if self.total is not None and self.order > self.total:
            raise ValueError(
                f"شماره ترتیب ({self.order}) نمی‌تواند از "
                f"کل ({self.total}) بزرگ‌تر باشد."
            )
        return self


class AssetInfo(BaseModel):
    """
    فایل‌های وابسته سند.
    Document asset references (images, files).
    """

    images: list[str] = Field(
        default_factory=list,
        description="لیست مسیر تصاویر",
    )
    files: list[str] = Field(
        default_factory=list,
        description="لیست مسیر فایل‌های وابسته",
    )


# ─────────────────────────────────────────────
# Main Model / مدل اصلی
# ─────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    """
    شِمای کامل متادیتای هر سند.
    Full document metadata schema for FormatForge MDX output.

    تمام فیلدهای فارسی با ZWNJ-safe validation پردازش می‌شوند.
    """

    # ─── اجباری / Required ───────────────────

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="عنوان فارسی سند",
    )
    title_en: Optional[str] = Field(
        default=None,
        max_length=500,
        alias="titleEn",
        description="عنوان انگلیسی سند",
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="مسیر URL (فقط حروف لاتین، عدد، خط‌تیره)",
    )
    date: str = Field(
        ...,
        description="تاریخ انتشار (ISO 8601)",
    )
    lang: str = Field(
        default="fa",
        pattern=r"^(fa|en|fa-en)$",
        description="زبان اصلی سند",
    )
    dir: str = Field(
        default="rtl",
        pattern=r"^(rtl|ltr)$",
        description="جهت اصلی متن",
    )

    # ─── نویسنده / Author ────────────────────

    author: Optional[AuthorInfo] = Field(
        default=None,
        description="اطلاعات نویسنده",
    )

    # ─── دسته‌بندی / Classification ──────────

    type: str = Field(
        default="article",
        pattern=r"^(article|book|chapter|proof|lecture-note|tutorial)$",
        description="نوع سند",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="برچسب‌ها (فارسی)",
    )
    tags_en: Optional[list[str]] = Field(
        default=None,
        alias="tagsEn",
        description="برچسب‌ها (انگلیسی)",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="دسته‌بندی‌ها",
    )
    series: Optional[SeriesInfo] = Field(
        default=None,
        description="اطلاعات مجموعه (اگر بخشی از سری باشد)",
    )

    # ─── محتوا / Content ─────────────────────

    description: str = Field(
        default="",
        max_length=300,
        description="خلاصه فارسی (حداکثر ۳۰۰ کاراکتر)",
    )
    description_en: Optional[str] = Field(
        default=None,
        max_length=500,
        alias="descriptionEn",
        description="خلاصه انگلیسی",
    )
    abstract: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="چکیده مفصل",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="کلمات کلیدی",
    )
    toc: bool = Field(
        default=True,
        description="نمایش فهرست مطالب",
    )
    math: bool = Field(
        default=False,
        description="آیا شامل فرمول ریاضی است",
    )
    mermaid: bool = Field(
        default=False,
        description="آیا شامل نمودار Mermaid است",
    )
    code_highlight: bool = Field(
        default=False,
        alias="codeHighlight",
        description="آیا شامل بلوک کد است",
    )

    # ─── فایل‌ها / Files ─────────────────────

    source_format: str = Field(
        default="latex",
        alias="sourceFormat",
        description="فرمت اصلی (latex, html, md, ...)",
    )
    source_file: str = Field(
        default="",
        alias="sourceFile",
        description="نام فایل اصلی",
    )
    assets: AssetInfo = Field(
        default_factory=AssetInfo,
        description="فایل‌های وابسته",
    )
    featured_image: Optional[str] = Field(
        default=None,
        alias="featuredImage",
        description="تصویر شاخص",
    )

    # ─── SEO و وب ────────────────────────────

    canonical: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL کانونیکال",
    )
    noindex: bool = Field(
        default=False,
        description="عدم ایندکس توسط موتور جستجو",
    )
    og_image: Optional[str] = Field(
        default=None,
        alias="ogImage",
        description="تصویر Open Graph",
    )

    # ─── تبدیل / Conversion ──────────────────

    converted_at: Optional[str] = Field(
        default=None,
        alias="convertedAt",
        description="زمان تبدیل (ISO 8601)",
    )
    converter_version: str = Field(
        default="0.1.0",
        alias="converterVersion",
        description="نسخه ابزار تبدیل",
    )
    quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        alias="qualityScore",
        description="امتیاز کیفیت (۰ تا ۱۰۰)",
    )
    conversion_notes: Optional[list[str]] = Field(
        default=None,
        alias="conversionNotes",
        description="یادداشت‌های تبدیل",
    )

    model_config = {"populate_by_name": True}

    # ─── Validators / اعتبارسنجی‌ها ─────────

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """اعتبارسنجی و نرمال‌سازی عنوان فارسی."""
        return _validate_persian_text(v, "title")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """بررسی فرمت slug (فقط حروف لاتین کوچک، عدد، خط‌تیره)."""
        if not _SLUG_PATTERN.match(v):
            raise ValueError(
                f"فرمت slug نامعتبر: «{v}». "
                "فقط حروف لاتین کوچک، اعداد و خط‌تیره مجاز است."
            )
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """بررسی فرمت تاریخ ISO 8601."""
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(
                f"فرمت تاریخ نامعتبر: «{v}». از ISO 8601 استفاده کنید."
            )
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """اعتبارسنجی خلاصه فارسی."""
        if v:
            return _validate_persian_text(v, "description")
        return v

    @field_validator("abstract")
    @classmethod
    def validate_abstract(cls, v: Optional[str]) -> Optional[str]:
        """اعتبارسنجی چکیده فارسی."""
        if v is not None:
            return _validate_persian_text(v, "abstract")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """اعتبارسنجی برچسب‌های فارسی."""
        return _validate_persian_list(v, "tags")

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        """اعتبارسنجی دسته‌بندی‌ها."""
        return _validate_persian_list(v, "categories")

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        """اعتبارسنجی کلمات کلیدی."""
        return _validate_persian_list(v, "keywords")

    @field_validator("converted_at")
    @classmethod
    def validate_converted_at(cls, v: Optional[str]) -> Optional[str]:
        """بررسی فرمت زمان تبدیل."""
        if v is not None:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise ValueError(
                    f"فرمت زمان تبدیل نامعتبر: «{v}»."
                )
        return v

    # ─── Helpers / متدهای کمکی ───────────────

    def zwnj_count(self) -> dict[str, int]:
        """
        شمارش ZWNJ در تمام فیلدهای فارسی.
        Count ZWNJ characters across all Persian text fields.
        """
        counts: dict[str, int] = {}
        for field_name in ("title", "description", "abstract"):
            value = getattr(self, field_name, None)
            if value:
                counts[field_name] = _count_zwnj(value)
        for i, tag in enumerate(self.tags):
            c = _count_zwnj(tag)
            if c > 0:
                counts[f"tags[{i}]"] = c
        for i, kw in enumerate(self.keywords):
            c = _count_zwnj(kw)
            if c > 0:
                counts[f"keywords[{i}]"] = c
        return counts

    def to_frontmatter_dict(self) -> dict:
        """
        تبدیل به دیکشنری مناسب frontmatter MDX.
        Convert to a dict suitable for MDX YAML frontmatter.
        """
        data = self.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude_defaults=False,
        )
        return data
