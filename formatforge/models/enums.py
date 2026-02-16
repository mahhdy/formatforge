"""
شمارشی‌های مشترک FormatForge
Shared enumerations used across all models.
"""

from enum import Enum


class DocumentFormat(str, Enum):
    """فرمت‌های سند پشتیبانی‌شده — Supported document formats."""
    LATEX = "latex"
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    PDF = "pdf"
    RST = "rst"
    ASCIIDOC = "asciidoc"
    EPUB = "epub"
    NOTEBOOK = "notebook"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, ext: str) -> "DocumentFormat":
        """تشخیص فرمت از پسوند فایل"""
        ext = ext.lower().lstrip(".")
        mapping = {
            "tex": cls.LATEX, "ltx": cls.LATEX, "sty": cls.LATEX, "cls": cls.LATEX,
            "md": cls.MARKDOWN, "mdx": cls.MARKDOWN, "markdown": cls.MARKDOWN,
            "html": cls.HTML, "htm": cls.HTML, "xhtml": cls.HTML,
            "docx": cls.DOCX,
            "pdf": cls.PDF,
            "rst": cls.RST, "rest": cls.RST,
            "adoc": cls.ASCIIDOC, "asciidoc": cls.ASCIIDOC, "asc": cls.ASCIIDOC,
            "epub": cls.EPUB,
            "ipynb": cls.NOTEBOOK,
        }
        return mapping.get(ext, cls.UNKNOWN)


class DocumentLanguage(str, Enum):
    """زبان سند — Document language."""
    PERSIAN = "fa"
    ENGLISH = "en"
    BILINGUAL = "fa-en"
    UNKNOWN = "unknown"


class DocumentDirection(str, Enum):
    """جهت متن — Text direction."""
    RTL = "rtl"
    LTR = "ltr"


class DocumentType(str, Enum):
    """نوع سند — Document type."""
    ARTICLE = "article"
    BOOK = "book"
    CHAPTER = "chapter"
    PROOF = "proof"
    LECTURE_NOTE = "lecture-note"
    TUTORIAL = "tutorial"
    UNKNOWN = "unknown"


class StructureType(str, Enum):
    """نوع ساختار مجموعه اسناد — Structure type of document collection."""
    SINGLE_DOC = "single_doc"
    INDEPENDENT_ARTICLES = "independent_articles"
    MULTI_CHAPTER_BOOK = "multi_chapter_book"
    RELATED_COLLECTION = "related_collection"
    UNKNOWN = "unknown"


class DocumentRole(str, Enum):
    """نقش فایل در مجموعه — Role of file within collection."""
    MAIN_ENTRY = "main_entry"
    CHAPTER = "chapter"
    APPENDIX = "appendix"
    STANDALONE = "standalone"
    BIBLIOGRAPHY = "bibliography"
    STYLE = "style"
    ASSET = "asset"
    UNKNOWN = "unknown"


class ConversionStatus(str, Enum):
    """وضعیت تبدیل — Conversion status."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class IssueSeverity(str, Enum):
    """شدت مشکل — Issue severity level."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


class QualityGrade(str, Enum):
    """درجه کیفیت — Quality grade."""
    EXCELLENT = "excellent"     # 90-100
    GOOD = "good"               # 75-89
    FAIR = "fair"               # 50-74
    POOR = "poor"               # 0-49

    @classmethod
    def from_score(cls, score: int) -> "QualityGrade":
        if score >= 90:
            return cls.EXCELLENT
        elif score >= 75:
            return cls.GOOD
        elif score >= 50:
            return cls.FAIR
        else:
            return cls.POOR