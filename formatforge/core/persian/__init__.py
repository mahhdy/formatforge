"""
FormatForge - Persian Package
پکیج فارسی‌سازی — مدیریت نیم‌فاصله، دوجهته و تایپوگرافی
"""

from formatforge.core.persian.zwnj_handler import (
    ZWNJ,
    PERSIAN_PREFIXES,
    PERSIAN_SUFFIXES,
    ZWNJReport,
    ZWNJProtection,
    count_zwnj,
    find_zwnj_positions,
    validate_zwnj_preserved,
    fix_common_zwnj_issues,
    protect_zwnj,
    restore_zwnj,
    safe_process,
    ensure_zwnj,
)

from formatforge.core.persian.bidi_handler import (
    BidiSegment,
    DirectionType,
    detect_block_direction,
    wrap_rtl_block,
    wrap_ltr_block,
    split_bidi_segments,
    convert_latex_lr,
)

from formatforge.core.persian.typography import (
    fix_arabic_characters,
    fix_persian_quotes,
    fix_persian_spacing,
    convert_numerals,
    normalize_persian,
    PersianTextProcessor,
)

__all__ = [
    # zwnj_handler
    "ZWNJ",
    "PERSIAN_PREFIXES",
    "PERSIAN_SUFFIXES",
    "ZWNJReport",
    "ZWNJProtection",
    "count_zwnj",
    "find_zwnj_positions",
    "validate_zwnj_preserved",
    "fix_common_zwnj_issues",
    "protect_zwnj",
    "restore_zwnj",
    "safe_process",
    "ensure_zwnj",
    # bidi_handler
    "BidiSegment",
    "DirectionType",
    "detect_block_direction",
    "wrap_rtl_block",
    "wrap_ltr_block",
    "split_bidi_segments",
    "convert_latex_lr",
    # typography
    "fix_arabic_characters",
    "fix_persian_quotes",
    "fix_persian_spacing",
    "convert_numerals",
    "normalize_persian",
    "PersianTextProcessor",
]
