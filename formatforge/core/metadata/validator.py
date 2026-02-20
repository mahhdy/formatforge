"""
Metadata Validator Module
ماژول اعتبارسنجی متادیتا

Validates document metadata against required fields and rules.
"""

from __future__ import annotations

from typing import Optional

from formatforge.models.metadata import DocumentMetadata


class ValidationIssue:
    """یک مشکل اعتبارسنجی."""
    
    def __init__(self, field: str, message: str, severity: str = "error"):
        self.field = field
        self.message = message
        self.severity = severity  # error, warning, info
    
    def __repr__(self):
        return f"[{self.severity.upper()}] {self.field}: {self.message}"


class ValidationResult:
    """نتیجه اعتبارسنجی."""
    
    def __init__(self):
        self.issues: list[ValidationIssue] = []
    
    @property
    def is_valid(self) -> bool:
        """آیا متادیتا معتبر است."""
        return not any(i.severity == "error" for i in self.issues)
    
    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]
    
    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]
    
    def add_error(self, field: str, message: str):
        self.issues.append(ValidationIssue(field, message, "error"))
    
    def add_warning(self, field: str, message: str):
        self.issues.append(ValidationIssue(field, message, "warning"))


class MetadataValidator:
    """اعتبارسنج متادیتا."""
    
    REQUIRED_FIELDS = {"title", "slug", "date", "lang", "dir"}
    
    VALID_LANGS = {"fa", "en", "fa-en"}
    VALID_DIRS = {"rtl", "ltr"}
    VALID_TYPES = {"article", "book", "chapter", "proof", "lecture-note", "tutorial"}
    
    @classmethod
    def validate(cls, metadata: DocumentMetadata) -> ValidationResult:
        """
        اعتبارسنجی متادیتا.
        
        Args:
            metadata: متادیتای سند
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            value = getattr(metadata, field, None)
            if not value:
                result.add_error(field, f"فیلد اجباری «{field}» وجود ندارد")
        
        # Validate lang
        if metadata.lang not in cls.VALID_LANGS:
            result.add_error(
                "lang",
                f"زبان «{metadata.lang}» نامعتبر است. "
                f"مقادیر مجاز: {cls.VALID_LANGS}"
            )
        
        # Validate dir
        if metadata.dir not in cls.VALID_DIRS:
            result.add_error(
                "dir",
                f"جهت «{metadata.dir}» نامعتبر است. "
                f"مقادیر مجاز: {cls.VALID_DIRS}"
            )
        
        # Validate type
        if metadata.type not in cls.VALID_TYPES:
            result.add_warning(
                "type",
                f"نوع «{metadata.type}» نامعتبر است. "
                f"مقادیر مجاز: {cls.VALID_TYPES}"
            )
        
        # Validate slug format
        slug = metadata.slug
        if not slug.replace("-", "").replace("_", "").isalnum():
            result.add_error(
                "slug",
                "slug فقط باید شامل حروف لاتین، اعداد، خط‌تیره و زیرخط باشد"
            )
        
        if slug.startswith("-") or slug.startswith("_"):
            result.add_error(
                "slug",
                "slug نباید با خط‌تیره یا زیرخط شروع شود"
            )
        
        # Validate date format (already done by Pydantic, but double-check)
        if metadata.date:
            try:
                from datetime import datetime
                datetime.fromisoformat(metadata.date)
            except ValueError:
                result.add_error("date", "فرمت تاریخ باید ISO 8601 باشد")
        
        # Validate author if present
        if metadata.author:
            if not metadata.author.name:
                result.add_error("author.name", "نام نویسنده اجباری است")
        
        # Check for missing recommended fields
        if not metadata.description:
            result.add_warning(
                "description",
                "توصیه می‌شود description را پر کنید"
            )
        
        if not metadata.tags:
            result.add_warning(
                "tags",
                "توصیه می‌شود حداقل یک برچسب اضافه کنید"
            )
        
        return result
    
    @classmethod
    def validate_required_only(cls, metadata: DocumentMetadata) -> ValidationResult:
        """
        اعتبارسنجی فقط فیلدهای اجباری.
        
        Args:
            metadata: متادیتای سند
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        # Check required fields only
        for field in cls.REQUIRED_FIELDS:
            value = getattr(metadata, field, None)
            if not value:
                result.add_error(field, f"فیلد اجباری «{field}» وجود ندارد")
        
        return result
