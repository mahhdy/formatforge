"""
استثناهای سفارشی FormatForge
Custom exceptions for FormatForge.
"""


class FormatForgeError(Exception):
    """خطای پایه FormatForge — Base error for all FormatForge exceptions."""
    pass


# ──────────────── اسکن / Scanner ────────────────

class ScanError(FormatForgeError):
    """خطا در مرحله اسکن — Error during scanning phase."""
    pass


class UnsupportedFormatError(ScanError):
    """فرمت فایل پشتیبانی نمی‌شود — File format is not supported."""

    def __init__(self, path: str, detected_format: str | None = None):
        self.path = path
        self.detected_format = detected_format
        fmt = f" (detected: {detected_format})" if detected_format else ""
        super().__init__(f"Unsupported file format: {path}{fmt}")


class EncodingError(ScanError):
    """خطای encoding فایل — File encoding error."""

    def __init__(self, path: str, encoding: str | None = None, detail: str = ""):
        self.path = path
        self.encoding = encoding
        msg = f"Encoding error in {path}"
        if encoding:
            msg += f" (detected: {encoding})"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class FileNotFoundError_(ScanError):
    """فایل یافت نشد — File not found (custom to avoid shadowing builtins)."""

    def __init__(self, path: str, context: str = ""):
        self.path = path
        msg = f"File not found: {path}"
        if context:
            msg += f" (referenced in: {context})"
        super().__init__(msg)


class DependencyMissingError(ScanError):
    """فایل وابسته یافت نشد — A dependency file is missing."""

    def __init__(self, missing_path: str, referenced_by: str):
        self.missing_path = missing_path
        self.referenced_by = referenced_by
        super().__init__(
            f"Missing dependency: {missing_path} (referenced by: {referenced_by})"
        )


# ──────────────── متادیتا / Metadata ────────────────

class MetadataError(FormatForgeError):
    """خطا در مرحله متادیتا — Error during metadata phase."""
    pass


class MetadataValidationError(MetadataError):
    """اعتبارسنجی متادیتا ناموفق بود — Metadata validation failed."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Metadata validation failed for '{field}': {message}")


class SlugConflictError(MetadataError):
    """Slug تکراری — Slug already exists."""

    def __init__(self, slug: str, existing_doc: str):
        self.slug = slug
        self.existing_doc = existing_doc
        super().__init__(f"Slug '{slug}' already used by: {existing_doc}")


# ──────────────── تبدیل / Conversion ────────────────

class ConversionError(FormatForgeError):
    """خطا در مرحله تبدیل — Error during conversion phase."""

    def __init__(self, message: str, source_file: str = "", line: int | None = None):
        self.source_file = source_file
        self.line = line
        loc = ""
        if source_file:
            loc += f" in {source_file}"
        if line is not None:
            loc += f" at line {line}"
        super().__init__(f"Conversion error{loc}: {message}")


class MathConversionError(ConversionError):
    """خطا در تبدیل فرمول ریاضی — Error converting math formula."""

    def __init__(self, formula: str, message: str, **kwargs):
        self.formula = formula
        super().__init__(f"Math: {message} | Formula: {formula[:80]}...", **kwargs)


class TikZCompilationError(ConversionError):
    """خطا در کامپایل TikZ — Error compiling TikZ to SVG."""

    def __init__(self, message: str, tikz_code: str = "", **kwargs):
        self.tikz_code = tikz_code
        super().__init__(f"TikZ compilation failed: {message}", **kwargs)


class TableConversionError(ConversionError):
    """خطا در تبدیل جدول — Error converting table."""
    pass


class ImageProcessingError(ConversionError):
    """خطا در پردازش تصویر — Error processing image."""

    def __init__(self, image_path: str, message: str, **kwargs):
        self.image_path = image_path
        super().__init__(f"Image '{image_path}': {message}", **kwargs)


# ──────────────── فارسی / Persian ────────────────

class PersianProcessingError(FormatForgeError):
    """خطا در پردازش متن فارسی — Error processing Persian text."""
    pass


class ZWNJLossError(PersianProcessingError):
    """نیم‌فاصله از دست رفته — ZWNJ characters were lost during processing."""

    def __init__(self, before_count: int, after_count: int, lost_positions: list[int] | None = None):
        self.before_count = before_count
        self.after_count = after_count
        self.lost_positions = lost_positions or []
        super().__init__(
            f"ZWNJ loss detected: {before_count} → {after_count} "
            f"({before_count - after_count} lost)"
        )


# ──────────────── کیفیت / Quality ────────────────

class QualityError(FormatForgeError):
    """خطا در تست کیفیت — Error during quality testing."""
    pass


class QualityBelowThresholdError(QualityError):
    """امتیاز کیفیت زیر حد مجاز — Quality score below threshold."""

    def __init__(self, score: int, threshold: int):
        self.score = score
        self.threshold = threshold
        super().__init__(f"Quality score {score} is below threshold {threshold}")


# ──────────────── استقرار / Deployment ────────────────

class DeploymentError(FormatForgeError):
    """خطا در مرحله استقرار — Error during deployment phase."""
    pass


# ──────────────── AI ────────────────

class AIError(FormatForgeError):
    """خطا در ماژول AI — Error in AI module."""
    pass


class AIProviderNotConfiguredError(AIError):
    """تنظیمات AI انجام نشده — AI provider is not configured."""

    def __init__(self, provider: str):
        super().__init__(f"AI provider '{provider}' is not configured. Set API key in config.")


# ──────────────── پیکربندی / Config ────────────────

class ConfigError(FormatForgeError):
    """خطا در تنظیمات — Error in configuration."""
    pass


# ──────────────── ابزار خارجی / External Tools ────────────────

class ExternalToolError(FormatForgeError):
    """ابزار خارجی موجود نیست یا خطا داد — External tool error."""

    def __init__(self, tool: str, message: str, install_hint: str = ""):
        self.tool = tool
        self.install_hint = install_hint
        msg = f"External tool '{tool}': {message}"
        if install_hint:
            msg += f"\n  → Install: {install_hint}"
        super().__init__(msg)