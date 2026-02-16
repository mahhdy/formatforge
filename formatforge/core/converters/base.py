"""
FormatForge - Base Converter & Registry
کلاس پایه تبدیل‌گر و رجیستری فرمت‌ها

Abstract base class for all format converters (LaTeX, HTML, MD, DOCX, ...)
and a registry for discovering and dispatching converters.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Optional, Type

from formatforge.models.conversion_result import (
    ConversionResult,
    DocumentConversionResult,
    QualityReport,
    ZWNJReport,
)
from formatforge.models.metadata import DocumentMetadata
from formatforge.models.scan_report import DocumentInfo

logger = logging.getLogger("formatforge.converters")

# ─── Constants / ثابت‌ها ──────────────────────
ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Exceptions / استثناها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConverterError(Exception):
    """خطای عمومی تبدیل‌گر. / General converter error."""
    pass


class FormatDetectionError(ConverterError):
    """خطا در تشخیص فرمت. / Format detection error."""
    pass


class ConversionError(ConverterError):
    """خطا حین تبدیل. / Error during conversion."""
    pass


class ValidationError(ConverterError):
    """خطا در اعتبارسنجی خروجی. / Output validation error."""
    pass


class ConverterNotFoundError(ConverterError):
    """تبدیل‌گر برای فرمت یافت نشد. / No converter for format."""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Context / زمینه تبدیل
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConversionContext:
    """
    زمینه مشترک بین مراحل تبدیل.
    Shared context passed through converter pipeline stages.

    نگهداری تنظیمات، متادیتا، شمارنده‌ها و وضعیت تبدیل.
    """

    def __init__(
        self,
        config: Any = None,
        metadata: Optional[DocumentMetadata] = None,
        document_info: Optional[DocumentInfo] = None,
        output_dir: Optional[Path] = None,
    ) -> None:
        self.config = config
        self.metadata = metadata
        self.document_info = document_info
        self.output_dir = output_dir or Path("./output")

        # ─── شمارنده‌ها / Counters ────────
        self.zwnj_count_before: int = 0
        self.zwnj_count_after: int = 0
        self.math_block_count: int = 0
        self.math_inline_count: int = 0
        self.table_count: int = 0
        self.image_count: int = 0
        self.code_block_count: int = 0
        self.heading_count: int = 0
        self.footnote_count: int = 0
        self.citation_count: int = 0
        self.crossref_count: int = 0

        # ─── وضعیت / State ────────────────
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.notes: list[str] = []
        self.assets_generated: list[str] = []
        self.imports_needed: set[str] = set()
        self.labels: dict[str, str] = {}  # label → id mapping
        self.dry_run: bool = False

    def add_warning(self, msg: str) -> None:
        """افزودن هشدار."""
        self.warnings.append(msg)
        logger.warning(msg)

    def add_error(self, msg: str) -> None:
        """افزودن خطا."""
        self.errors.append(msg)
        logger.error(msg)

    def add_note(self, msg: str) -> None:
        """افزودن یادداشت."""
        self.notes.append(msg)

    def require_import(self, component: str) -> None:
        """ثبت نیاز به import یک کامپوننت MDX."""
        self.imports_needed.add(component)

    def count_zwnj(self, text: str) -> int:
        """شمارش نیم‌فاصله در متن."""
        return text.count(ZWNJ)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BaseConverter / تبدیل‌گر پایه
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BaseConverter(ABC):
    """
    کلاس پایه انتزاعی برای تمام تبدیل‌گرها.
    Abstract base class for all format converters.

    هر تبدیل‌گر باید متدهای زیر را پیاده‌سازی کند:
    - format_name: نام فرمت
    - file_extensions: پسوندهای فایل
    - detect: تشخیص فرمت
    - extract_metadata: استخراج متادیتا
    - convert: تبدیل محتوا
    - validate_output: اعتبارسنجی خروجی
    """

    # ─── Class-level config / تنظیمات کلاس ──
    format_name: ClassVar[str] = "unknown"
    file_extensions: ClassVar[list[str]] = []
    mime_types: ClassVar[list[str]] = []
    priority: ClassVar[int] = 100  # عدد کمتر = اولویت بالاتر

    def __init__(self, config: Any = None) -> None:
        """
        مقداردهی تبدیل‌گر.
        Initialize converter with optional config.
        """
        self.config = config
        self._logger = logging.getLogger(
            f"formatforge.converters.{self.format_name}"
        )

    # ─── Detection / تشخیص ────────────────

    @abstractmethod
    def detect(self, file_path: Path) -> bool:
        """
        آیا این فایل قابل تبدیل با این تبدیل‌گر است؟
        Can this converter handle the given file?

        بررسی بر اساس:
        - پسوند فایل
        - محتوای فایل (magic bytes)
        - ساختار داخلی

        Args:
            file_path: مسیر فایل ورودی

        Returns:
            True اگر فایل قابل پردازش باشد
        """
        ...

    def detect_by_extension(self, file_path: Path) -> bool:
        """
        تشخیص سریع بر اساس پسوند فایل.
        Quick detection based on file extension only.
        """
        suffix = file_path.suffix.lower()
        return suffix in self.file_extensions

    # ─── Metadata / متادیتا ──────────────

    @abstractmethod
    def extract_metadata(
        self,
        file_path: Path,
        context: Optional[ConversionContext] = None,
    ) -> DocumentMetadata:
        """
        استخراج متادیتا از فایل ورودی.
        Extract metadata from the source file.

        اطلاعاتی مانند عنوان، نویسنده، زبان، تاریخ و ...

        Args:
            file_path: مسیر فایل ورودی
            context: زمینه تبدیل (اختیاری)

        Returns:
            DocumentMetadata استخراج‌شده

        Raises:
            ConversionError: اگر استخراج ناموفق باشد
        """
        ...

    # ─── Conversion / تبدیل ──────────────

    @abstractmethod
    def convert(
        self,
        file_path: Path,
        context: ConversionContext,
    ) -> DocumentConversionResult:
        """
        تبدیل فایل ورودی به MDX.
        Convert the source file to MDX format.

        مراحل تبدیل:
        1. خواندن فایل ورودی
        2. پیش‌پردازش (cleanup، نرمال‌سازی)
        3. شمارش ZWNJ قبل
        4. تبدیل ساختار
        5. پردازش عناصر تخصصی (ریاضی، جدول، ...)
        6. پس‌پردازش (فارسی‌سازی، RTL)
        7. شمارش ZWNJ بعد
        8. تولید خروجی MDX

        Args:
            file_path: مسیر فایل ورودی
            context: زمینه تبدیل شامل تنظیمات و متادیتا

        Returns:
            DocumentConversionResult با وضعیت و خروجی

        Raises:
            ConversionError: اگر تبدیل ناموفق باشد
        """
        ...

    # ─── Validation / اعتبارسنجی ─────────

    @abstractmethod
    def validate_output(
        self,
        result: DocumentConversionResult,
        context: ConversionContext,
    ) -> QualityReport:
        """
        اعتبارسنجی خروجی تبدیل.
        Validate the conversion output.

        بررسی‌ها:
        - حفظ ZWNJ (شمارش قبل/بعد)
        - صحت frontmatter
        - صحت MDX (قابل parse بودن)
        - جهت‌دهی صحیح (bidi)
        - تصاویر لینک‌شده
        - لینک‌های معتبر

        Args:
            result: نتیجه تبدیل
            context: زمینه تبدیل

        Returns:
            QualityReport با امتیاز و جزئیات
        """
        ...

    # ─── Helper Methods / متدهای کمکی ────

    def read_file(self, file_path: Path, encoding: str = "utf-8") -> str:
        """
        خواندن فایل با encoding مناسب.
        Read file content with proper encoding detection.
        """
        resolved = file_path.resolve()
        if not resolved.exists():
            raise ConversionError(
                f"فایل ورودی یافت نشد: {resolved}"
            )

        # تلاش با encoding‌های مختلف
        encodings_to_try = [encoding, "utf-8-sig", "utf-8", "utf-16", "windows-1256"]
        last_error: Optional[Exception] = None

        for enc in encodings_to_try:
            try:
                content = resolved.read_text(encoding=enc)
                self._logger.debug(
                    "فایل %s با encoding %s خوانده شد.", resolved.name, enc
                )
                return content
            except (UnicodeDecodeError, LookupError) as exc:
                last_error = exc
                continue

        raise ConversionError(
            f"خطا در خواندن فایل {resolved}: {last_error}"
        )

    def write_output(
        self,
        content: str,
        output_path: Path,
        dry_run: bool = False,
    ) -> int:
        """
        نوشتن خروجی MDX.
        Write MDX output to file. Returns bytes written.
        """
        if dry_run:
            self._logger.info("حالت آزمایشی — نوشتن %s رد شد.", output_path)
            return len(content.encode("utf-8"))

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # نوشتن با UTF-8 BOM
        bom = "\ufeff"
        full_content = bom + content if not content.startswith(bom) else content
        output_path.write_text(full_content, encoding="utf-8")

        size = output_path.stat().st_size
        self._logger.info(
            "خروجی نوشته شد: %s (%d bytes)", output_path, size
        )
        return size

    def count_zwnj(self, text: str) -> int:
        """شمارش نیم‌فاصله‌ها. / Count ZWNJ characters."""
        return text.count(ZWNJ)

    def verify_zwnj_preservation(
        self,
        before: str,
        after: str,
        context: ConversionContext,
    ) -> ZWNJReport:
        """
        بررسی حفظ نیم‌فاصله‌ها بعد از تبدیل.
        Verify ZWNJ characters are preserved after conversion.
        """
        count_before = self.count_zwnj(before)
        count_after = self.count_zwnj(after)

        context.zwnj_count_before = count_before
        context.zwnj_count_after = count_after

        report = ZWNJReport(
            count_before=count_before,
            count_after=count_after,
        )

        if not report.preserved:
            diff = count_before - count_after
            context.add_warning(
                f"⚠ نیم‌فاصله: {diff} مورد از دست رفته "
                f"({count_before} → {count_after})"
            )

        return report

    def run_full_pipeline(
        self,
        file_path: Path,
        context: ConversionContext,
    ) -> DocumentConversionResult:
        """
        اجرای کامل خط لوله تبدیل.
        Run the full conversion pipeline with timing and error handling.

        ترتیب: extract_metadata → convert → validate_output
        """
        start = time.time()
        doc_id = context.document_info.id if context.document_info else "unknown"

        result = DocumentConversionResult(
            document_id=doc_id,
            source_path=str(file_path),
            status="processing",
        )

        try:
            # ۱) استخراج متادیتا
            self._logger.info("استخراج متادیتا: %s", file_path.name)
            if context.metadata is None:
                context.metadata = self.extract_metadata(file_path, context)

            # ۲) تبدیل
            self._logger.info("تبدیل: %s", file_path.name)
            result = self.convert(file_path, context)

            # ۳) اعتبارسنجی
            if result.status == "success":
                self._logger.info("اعتبارسنجی: %s", file_path.name)
                quality = self.validate_output(result, context)
                quality.compute_score()
                result.quality = quality

        except ConversionError as exc:
            result.status = "failed"
            result.error_message = str(exc)
            context.add_error(str(exc))
            self._logger.error("خطا در تبدیل %s: %s", file_path.name, exc)

        except Exception as exc:
            result.status = "failed"
            result.error_message = f"خطای غیرمنتظره: {exc}"
            context.add_error(f"خطای غیرمنتظره: {exc}")
            self._logger.exception("خطای غیرمنتظره در تبدیل %s", file_path.name)

        finally:
            result.duration_seconds = round(time.time() - start, 3)
            result.notes = context.notes.copy()

        return result

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"format={self.format_name!r} "
            f"extensions={self.file_extensions}>"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ConverterRegistry / رجیستری تبدیل‌گرها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConverterRegistry:
    """
    رجیستری تبدیل‌گرها با الگوی Registry.
    Registry for format converters. Supports:
    - Registration by format name
    - Auto-detection by file extension and content
    - Priority-based selection when multiple match
    """

    def __init__(self) -> None:
        self._converters: dict[str, Type[BaseConverter]] = {}
        self._instances: dict[str, BaseConverter] = {}
        self._logger = logging.getLogger("formatforge.converters.registry")

    def register(
        self,
        format_name: str,
        converter_class: Type[BaseConverter],
    ) -> None:
        """
        ثبت تبدیل‌گر برای یک فرمت.
        Register a converter class for a given format name.

        Args:
            format_name: نام فرمت (مثلاً "latex", "html")
            converter_class: کلاس تبدیل‌گر (زیرکلاس BaseConverter)

        Raises:
            TypeError: اگر کلاس زیرکلاس BaseConverter نباشد
        """
        if not (
            isinstance(converter_class, type)
            and issubclass(converter_class, BaseConverter)
        ):
            raise TypeError(
                f"تبدیل‌گر باید زیرکلاس BaseConverter باشد، "
                f"نه {type(converter_class).__name__}"
            )

        key = format_name.lower().strip()
        self._converters[key] = converter_class
        self._logger.info(
            "تبدیل‌گر ثبت شد: %s → %s",
            key, converter_class.__name__,
        )

    def unregister(self, format_name: str) -> bool:
        """
        حذف تبدیل‌گر.
        Unregister a converter. Returns True if it existed.
        """
        key = format_name.lower().strip()
        removed = self._converters.pop(key, None) is not None
        self._instances.pop(key, None)
        return removed

    def get_converter(
        self,
        format_name: str,
        config: Any = None,
    ) -> BaseConverter:
        """
        دریافت نمونه تبدیل‌گر برای یک فرمت.
        Get a converter instance for the given format.

        Args:
            format_name: نام فرمت
            config: تنظیمات (اختیاری)

        Returns:
            نمونه BaseConverter

        Raises:
            ConverterNotFoundError: اگر فرمت ثبت نشده باشد
        """
        key = format_name.lower().strip()

        if key not in self._converters:
            available = ", ".join(sorted(self._converters.keys()))
            raise ConverterNotFoundError(
                f"تبدیل‌گر برای فرمت «{key}» یافت نشد. "
                f"فرمت‌های موجود: {available}"
            )

        # Lazy instantiation with caching
        if key not in self._instances:
            cls = self._converters[key]
            self._instances[key] = cls(config=config)
            self._logger.debug("نمونه ساخته شد: %s", cls.__name__)

        return self._instances[key]

    def detect_format(self, file_path: Path) -> str:
        """
        تشخیص خودکار فرمت فایل.
        Auto-detect file format using registered converters.

        ترتیب بررسی:
        1. تطبیق پسوند فایل
        2. تحلیل محتوا (detect method)
        3. اولویت‌بندی (priority)

        Args:
            file_path: مسیر فایل

        Returns:
            نام فرمت شناسایی‌شده

        Raises:
            FormatDetectionError: اگر فرمت قابل تشخیص نباشد
        """
        resolved = file_path.resolve()
        if not resolved.exists():
            raise FormatDetectionError(
                f"فایل یافت نشد: {resolved}"
            )

        # مرحله ۱: تطبیق پسوند
        candidates: list[tuple[int, str, Type[BaseConverter]]] = []
        suffix = resolved.suffix.lower()

        for fmt, cls in self._converters.items():
            if suffix in cls.file_extensions:
                candidates.append((cls.priority, fmt, cls))

        # مرحله ۲: تحلیل محتوا (برای کاندیداها)
        if candidates:
            # مرتب‌سازی بر اساس اولویت
            candidates.sort(key=lambda x: x[0])

            for priority, fmt, cls in candidates:
                try:
                    instance = cls()
                    if instance.detect(resolved):
                        self._logger.info(
                            "فرمت تشخیص داده شد: %s (priority=%d)",
                            fmt, priority,
                        )
                        return fmt
                except Exception as exc:
                    self._logger.debug(
                        "خطا در تشخیص %s: %s", fmt, exc
                    )

            # اگر detect هیچ‌کدام True ندا اما پسوند تطبیق خورد
            best = candidates[0]
            self._logger.info(
                "فرمت بر اساس پسوند: %s (fallback)", best[1]
            )
            return best[1]

        # مرحله ۳: بررسی همه تبدیل‌گرها
        for fmt, cls in self._converters.items():
            try:
                instance = cls()
                if instance.detect(resolved):
                    self._logger.info(
                        "فرمت تشخیص داده شد (full scan): %s", fmt
                    )
                    return fmt
            except Exception:
                continue

        raise FormatDetectionError(
            f"فرمت فایل «{resolved.name}» قابل تشخیص نیست. "
            f"پسوند: {suffix}"
        )

    @property
    def registered_formats(self) -> list[str]:
        """لیست فرمت‌های ثبت‌شده."""
        return sorted(self._converters.keys())

    @property
    def converter_count(self) -> int:
        """تعداد تبدیل‌گرهای ثبت‌شده."""
        return len(self._converters)

    def get_info(self) -> dict[str, dict[str, Any]]:
        """
        اطلاعات تمام تبدیل‌گرهای ثبت‌شده.
        Get info about all registered converters.
        """
        info: dict[str, dict[str, Any]] = {}
        for fmt, cls in sorted(self._converters.items()):
            info[fmt] = {
                "class": cls.__name__,
                "extensions": cls.file_extensions,
                "mime_types": cls.mime_types,
                "priority": cls.priority,
            }
        return info

    def __repr__(self) -> str:
        return (
            f"<ConverterRegistry formats={self.registered_formats}>"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global Registry / رجیستری سراسری
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_global_registry: Optional[ConverterRegistry] = None


def get_registry() -> ConverterRegistry:
    """
    دریافت رجیستری سراسری (singleton).
    Get the global converter registry.
    """
    global _global_registry  # noqa: PLW0603
    if _global_registry is None:
        _global_registry = ConverterRegistry()
    return _global_registry


def register_converter(
    format_name: str,
    converter_class: Type[BaseConverter],
) -> None:
    """
    ثبت تبدیل‌گر در رجیستری سراسری.
    Register a converter in the global registry. (Shortcut)
    """
    get_registry().register(format_name, converter_class)
