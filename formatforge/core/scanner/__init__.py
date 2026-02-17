"""
FormatForge - Scanner Package
پکیج اسکنر ورودی
"""

from formatforge.core.scanner.file_detector import (
    detect_encoding,
    detect_format,
    detect_language,
    EncodingInfo,
    LanguageInfo,
)
from formatforge.core.scanner.structure_analyzer import (
    analyze_directory,
    analyze_latex_project,
    analyze_markdown_collection,
    find_assets,
    StructureAnalysis,
    DocInfo,
    AssetEntry,
    LatexProjectInfo,
)
from formatforge.core.scanner.archive_handler import (
    extract_archive,
    cleanup_temp,
    is_archive,
    ExtractedArchive,
    ExtractedFile,
    ArchiveError,
)
from formatforge.core.scanner.scanner import (
    Scanner,
    ScanReport,
    ScanWarning,
    DocumentEntry,
    AssetInfo,
    fix_encoding_issues,
)

__all__ = [
    # file_detector
    "detect_encoding",
    "detect_format",
    "detect_language",
    "EncodingInfo",
    "LanguageInfo",
    # structure_analyzer
    "analyze_directory",
    "analyze_latex_project",
    "analyze_markdown_collection",
    "find_assets",
    "StructureAnalysis",
    "DocInfo",
    "AssetEntry",
    "LatexProjectInfo",
    # archive_handler
    "extract_archive",
    "cleanup_temp",
    "is_archive",
    "ExtractedArchive",
    "ExtractedFile",
    "ArchiveError",
    # scanner
    "Scanner",
    "ScanReport",
    "ScanWarning",
    "DocumentEntry",
    "AssetInfo",
    "fix_encoding_issues",
]
