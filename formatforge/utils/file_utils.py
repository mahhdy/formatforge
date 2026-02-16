"""
FormatForge - File Utilities
ابزارهای کمکی فایل

Safe file reading/writing with encoding detection and ZWNJ counting.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("formatforge.utils.file")

# ─────────────────────────────────────────────
# Constants / ثابت‌ها
# ─────────────────────────────────────────────

ZWNJ = "\u200c"
UTF8_BOM = b"\xef\xbb\xbf"
UTF16_LE_BOM = b"\xff\xfe"
UTF16_BE_BOM = b"\xfe\xff"

_ENCODING_ATTEMPTS = [
    "utf-8-sig",    # UTF-8 with BOM
    "utf-8",        # UTF-8 without BOM
    "utf-16",       # UTF-16 (auto BOM detect)
    "windows-1256", # Arabic Windows
    "iso-8859-6",   # Arabic ISO
    "cp1252",       # Western Windows
]


# ─────────────────────────────────────────────
# Data Classes / کلاس‌های داده
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class FileReadResult:
    """
    نتیجه خواندن فایل.
    Result of reading a file safely.
    """
    content: str
    encoding: str
    has_bom: bool
    size_bytes: int
    zwnj_count: int


# ─────────────────────────────────────────────
# Core Functions / توابع اصلی
# ─────────────────────────────────────────────

def detect_encoding(path: str | Path) -> str:
    """
    تشخیص encoding فایل.
    Detect file encoding by BOM analysis and content probing.

    ترتیب بررسی:
    1. BOM bytes (قطعی)
    2. chardet / charset_normalizer (اگر نصب باشد)
    3. تلاش ترتیبی با encoding‌های رایج

    Args:
        path: مسیر فایل

    Returns:
        نام encoding تشخیص داده شده

    Raises:
        FileNotFoundError: فایل وجود ندارد
    """
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"فایل یافت نشد: {file_path}")

    # مرحله ۱: بررسی BOM
    raw_head = file_path.read_bytes()[:4]

    if raw_head[:3] == UTF8_BOM:
        return "utf-8-sig"
    if raw_head[:2] == UTF16_LE_BOM:
        return "utf-16-le"
    if raw_head[:2] == UTF16_BE_BOM:
        return "utf-16-be"

    # مرحله ۲: chardet (اگر نصب باشد)
    try:
        import chardet  # type: ignore[import-untyped]
        raw = file_path.read_bytes()
        detection = chardet.detect(raw)
        if detection and detection.get("confidence", 0) > 0.7:
            enc = detection["encoding"]
            if enc:
                logger.debug(
                    "chardet تشخیص داد: %s (confidence=%.2f)",
                    enc, detection["confidence"],
                )
                return enc.lower()
    except ImportError:
        pass

    # مرحله ۳: تلاش ترتیبی
    raw_bytes = file_path.read_bytes()
    for enc in _ENCODING_ATTEMPTS:
        try:
            raw_bytes.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    return "utf-8"  # fallback


def read_file_safe(
    path: str | Path,
    encoding: Optional[str] = None,
) -> FileReadResult:
    """
    خواندن امن فایل با تشخیص خودکار encoding.
    Read a file safely with auto encoding detection.

    ویژگی‌ها:
    - تشخیص خودکار encoding (اگر مشخص نشده باشد)
    - شناسایی BOM
    - شمارش ZWNJ
    - گزارش اندازه

    Args:
        path: مسیر فایل
        encoding: encoding دلخواه (اختیاری — اگر None: تشخیص خودکار)

    Returns:
        FileReadResult شامل محتوا، encoding، BOM و شمارش ZWNJ

    Raises:
        FileNotFoundError: فایل وجود ندارد
        ValueError: خطا در خواندن با تمام encoding‌ها
    """
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"فایل یافت نشد: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"مسیر یک فایل نیست: {file_path}")

    size_bytes = file_path.stat().st_size

    # تشخیص encoding
    if encoding is None:
        encoding = detect_encoding(file_path)

    # بررسی BOM
    has_bom = False
    raw_head = file_path.read_bytes()[:4]
    if raw_head[:3] == UTF8_BOM:
        has_bom = True
    elif raw_head[:2] in (UTF16_LE_BOM, UTF16_BE_BOM):
        has_bom = True

    # خواندن محتوا
    content = _read_with_fallback(file_path, encoding)

    # شمارش ZWNJ
    zwnj_count = count_zwnj(content)

    logger.debug(
        "فایل خوانده شد: %s (enc=%s, bom=%s, zwnj=%d, size=%d)",
        file_path.name, encoding, has_bom, zwnj_count, size_bytes,
    )

    return FileReadResult(
        content=content,
        encoding=encoding,
        has_bom=has_bom,
        size_bytes=size_bytes,
        zwnj_count=zwnj_count,
    )


def write_file_utf8_bom(
    path: str | Path,
    content: str,
    *,
    create_parents: bool = True,
) -> int:
    """
    نوشتن فایل با UTF-8 BOM.
    Write content to file with UTF-8 BOM encoding.

    Args:
        path: مسیر فایل خروجی
        content: محتوای متنی
        create_parents: ساخت پوشه‌های والد

    Returns:
        تعداد بایت‌های نوشته‌شده
    """
    file_path = Path(path).resolve()

    if create_parents:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    # حذف BOM تکراری
    bom_char = "\ufeff"
    clean = content.lstrip(bom_char)

    # نوشتن با BOM
    raw = bom_char.encode("utf-8") + clean.encode("utf-8")
    file_path.write_bytes(raw)

    written = len(raw)
    logger.debug("فایل نوشته شد: %s (%d bytes)", file_path.name, written)
    return written


def count_zwnj(text: str) -> int:
    """
    شمارش نیم‌فاصله‌ها.
    Count ZWNJ (U+200C) characters in text.

    Args:
        text: متن ورودی

    Returns:
        تعداد نیم‌فاصله‌ها
    """
    return text.count(ZWNJ)


def ensure_directory(path: str | Path) -> Path:
    """
    اطمینان از وجود پوشه (ساخت اگر نیست).
    Ensure a directory exists, creating it if necessary.

    Args:
        path: مسیر پوشه

    Returns:
        Path مطلق پوشه
    """
    dir_path = Path(path).resolve()
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_file_size_human(size_bytes: int) -> str:
    """
    تبدیل اندازه فایل به فرمت خوانا.
    Convert bytes to human-readable string.
    """
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} TB"


# ─────────────────────────────────────────────
# Helpers / توابع کمکی
# ─────────────────────────────────────────────

def _read_with_fallback(file_path: Path, preferred: str) -> str:
    """خواندن فایل با fallback روی encoding‌های مختلف."""
    # اول encoding ترجیحی
    try:
        return file_path.read_text(encoding=preferred)
    except (UnicodeDecodeError, LookupError):
        pass

    # سپس لیست fallback
    for enc in _ENCODING_ATTEMPTS:
        if enc == preferred:
            continue
        try:
            return file_path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue

    raise ValueError(
        f"خطا در خواندن فایل «{file_path.name}» "
        f"با تمام encoding‌های موجود."
    )
