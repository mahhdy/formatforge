"""
FormatForge - File Detector
تشخیص فرمت، encoding و زبان فایل

Detect file format (by extension + magic bytes + content analysis),
encoding (BOM + chardet), and language (Persian/English/mixed).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("formatforge.scanner.detector")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Classes / کلاس‌های داده
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class EncodingInfo:
    """
    اطلاعات encoding فایل.
    File encoding detection result.
    """
    name: str
    has_bom: bool = False
    confidence: float = 0.0


@dataclass(frozen=True)
class LanguageInfo:
    """
    اطلاعات زبان محتوا.
    Content language detection result.
    """
    primary: str          # "fa" | "en" | "fa+en" | "unknown"
    has_persian: bool = False
    has_english: bool = False
    persian_ratio: float = 0.0
    english_ratio: float = 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants / ثابت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# --- Extension mapping ---
_EXT_TO_FORMAT: dict[str, str] = {
    # LaTeX
    ".tex": "latex", ".ltx": "latex", ".sty": "latex", ".cls": "latex",
    # HTML
    ".html": "html", ".htm": "html", ".xhtml": "html",
    # Markdown
    ".md": "markdown", ".mdx": "markdown", ".markdown": "markdown",
    # Office
    ".docx": "docx", ".doc": "docx",
    # PDF
    ".pdf": "pdf",
    # RST
    ".rst": "rst", ".rest": "rst",
    # AsciiDoc
    ".adoc": "asciidoc", ".asciidoc": "asciidoc", ".asc": "asciidoc",
    # EPUB
    ".epub": "epub",
    # Jupyter
    ".ipynb": "notebook",
    # Bibliography
    ".bib": "bibtex",
}

# --- Magic bytes (first N bytes) ---
_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"%PDF",                          "pdf"),
    (b"PK\x03\x04",                   "_zip"),      # ZIP (docx, epub, ...)
    (b"{\n",                           "_json_like"), # Possible notebook
    (b'{"',                            "_json_like"),
    (b"<!DOCTYPE html",                "html"),
    (b"<!doctype html",                "html"),
    (b"<html",                         "html"),
    (b"<?xml",                         "_xml"),
]

# --- Content patterns ---
_LATEX_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\\documentclass\b"),
    re.compile(r"\\begin\{document\}"),
    re.compile(r"\\usepackage\b"),
    re.compile(r"\\section\{"),
    re.compile(r"\\chapter\{"),
    re.compile(r"\\newcommand\b"),
    re.compile(r"\\input\{"),
    re.compile(r"\\include\{"),
    re.compile(r"\\begin\{(equation|align|theorem|proof|tikzpicture)\}"),
]

_HTML_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<html[\s>]", re.IGNORECASE),
    re.compile(r"<head[\s>]", re.IGNORECASE),
    re.compile(r"<body[\s>]", re.IGNORECASE),
    re.compile(r"<div[\s>]", re.IGNORECASE),
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"<style[\s>]", re.IGNORECASE),
]

_MARKDOWN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^#{1,6}\s+", re.MULTILINE),
    re.compile(r"^\*\*.*\*\*", re.MULTILINE),
    re.compile(r"^- \[[ x]\]", re.MULTILINE),
    re.compile(r"^\|.*\|.*\|", re.MULTILINE),
    re.compile(r"^```\w*$", re.MULTILINE),
    re.compile(r"^---\s*$", re.MULTILINE),
]

_RST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\.\. \w+::", re.MULTILINE),
    re.compile(r"^={3,}\s*$", re.MULTILINE),
    re.compile(r"^-{3,}\s*$", re.MULTILINE),
    re.compile(r"^~{3,}\s*$", re.MULTILINE),
    re.compile(r":\w+:`[^`]+`"),
]

_ASCIIDOC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^={1,5}\s+\S", re.MULTILINE),
    re.compile(r"^:[\w-]+:\s+", re.MULTILINE),
    re.compile(r"^\[source", re.MULTILINE),
    re.compile(r"^----\s*$", re.MULTILINE),
    re.compile(r"^\[NOTE\]", re.MULTILINE),
]

# --- BOM bytes ---
_UTF8_BOM = b"\xef\xbb\xbf"
_UTF16_LE_BOM = b"\xff\xfe"
_UTF16_BE_BOM = b"\xfe\xff"

# --- Language detection ---
_PERSIAN_RANGE = re.compile(
    "[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff]"
)
_LATIN_RANGE = re.compile(r"[a-zA-Z]")

_MIXED_THRESHOLD = 0.15  # حداقل ۱۵٪ هر زبان برای «دوزبانه»


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Exceptions / استثناها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DetectionError(Exception):
    """خطا در تشخیص. / Detection error."""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Format Detection / تشخیص فرمت
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_format(path: str | Path) -> str:
    """
    تشخیص فرمت فایل بر اساس پسوند + magic bytes + تحلیل محتوا.
    Detect file format using extension, magic bytes, and content analysis.

    ترتیب بررسی:
    1. پسوند فایل → تطبیق سریع
    2. Magic bytes → تأیید یا تصحیح
    3. تحلیل محتوا → تشخیص نهایی

    Args:
        path: مسیر فایل

    Returns:
        نام فرمت: latex | html | markdown | docx | pdf |
                  rst | asciidoc | epub | notebook | bibtex | unknown

    Raises:
        FileNotFoundError: فایل وجود ندارد
        DetectionError: خطا در تشخیص
    """
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"فایل یافت نشد: {file_path}")
    if not file_path.is_file():
        raise DetectionError(f"مسیر یک فایل نیست: {file_path}")

    # ─── مرحله ۱: پسوند ──────────────────
    ext_format = _detect_by_extension(file_path)

    # ─── مرحله ۲: Magic bytes ────────────
    magic_format = _detect_by_magic(file_path)

    # ─── مرحله ۳: ترکیب و تحلیل محتوا ──
    final = _resolve_format(file_path, ext_format, magic_format)

    logger.debug(
        "تشخیص فرمت %s: ext=%s magic=%s → %s",
        file_path.name, ext_format, magic_format, final,
    )
    return final


def _detect_by_extension(file_path: Path) -> Optional[str]:
    """تشخیص بر اساس پسوند."""
    suffix = file_path.suffix.lower()
    return _EXT_TO_FORMAT.get(suffix)


def _detect_by_magic(file_path: Path) -> Optional[str]:
    """تشخیص بر اساس magic bytes."""
    try:
        head = file_path.read_bytes()[:64]
    except OSError:
        return None

    # حذف BOM اگر وجود دارد
    if head[:3] == _UTF8_BOM:
        head = head[3:]

    for magic, fmt in _MAGIC_BYTES:
        if head[:len(magic)].lower().startswith(magic.lower()):
            return fmt

    return None


def _resolve_format(
    file_path: Path,
    ext_fmt: Optional[str],
    magic_fmt: Optional[str],
) -> str:
    """ترکیب نتایج و تحلیل محتوا برای تشخیص نهایی."""

    # ZIP-based formats: docx, epub
    if magic_fmt == "_zip":
        return _resolve_zip_format(file_path, ext_fmt)

    # JSON-like: notebook
    if magic_fmt == "_json_like":
        return _resolve_json_format(file_path, ext_fmt)

    # XML: could be xhtml or other
    if magic_fmt == "_xml":
        if ext_fmt in ("html", "epub"):
            return ext_fmt
        return _try_content_analysis(file_path) or ext_fmt or "html"

    # PDF: magic bytes قطعی
    if magic_fmt == "pdf":
        return "pdf"

    # HTML: magic bytes قطعی
    if magic_fmt == "html":
        if ext_fmt and ext_fmt != "html":
            # پسوند اولویت دارد فقط اگر خیلی مشخص باشد
            return ext_fmt if ext_fmt in ("latex", "rst") else "html"
        return "html"

    # اگر پسوند مشخص است و magic تناقض ندارد
    if ext_fmt and ext_fmt not in ("unknown",):
        return ext_fmt

    # آخرین تلاش: تحلیل محتوا
    content_fmt = _try_content_analysis(file_path)
    if content_fmt:
        return content_fmt

    return "unknown"


def _resolve_zip_format(
    file_path: Path,
    ext_fmt: Optional[str],
) -> str:
    """تشخیص فرمت‌های ZIP-based."""
    if ext_fmt == "docx":
        return "docx"
    if ext_fmt == "epub":
        return "epub"

    # بررسی محتوای ZIP
    try:
        import zipfile
        with zipfile.ZipFile(file_path) as zf:
            names = zf.namelist()
            if any(n.startswith("word/") for n in names):
                return "docx"
            if "META-INF/container.xml" in names:
                return "epub"
            if any(n.endswith(".ipynb") for n in names):
                return "notebook"
    except Exception:
        pass

    return ext_fmt or "unknown"


def _resolve_json_format(
    file_path: Path,
    ext_fmt: Optional[str],
) -> str:
    """تشخیص فرمت‌های JSON-based."""
    if ext_fmt == "notebook":
        return "notebook"

    # بررسی محتوا
    try:
        head = file_path.read_text(encoding="utf-8", errors="ignore")[:2000]
        if '"nbformat"' in head or '"cells"' in head:
            return "notebook"
    except OSError:
        pass

    return ext_fmt or "unknown"


def _try_content_analysis(file_path: Path) -> Optional[str]:
    """تحلیل محتوا برای تشخیص فرمت متنی."""
    try:
        raw = file_path.read_bytes()[:8192]
        # حذف BOM
        if raw[:3] == _UTF8_BOM:
            raw = raw[3:]
        content = raw.decode("utf-8", errors="ignore")
    except OSError:
        return None

    if not content.strip():
        return None

    scores: dict[str, int] = {
        "latex": 0, "html": 0, "markdown": 0,
        "rst": 0, "asciidoc": 0,
    }

    for pat in _LATEX_PATTERNS:
        if pat.search(content):
            scores["latex"] += 2

    for pat in _HTML_PATTERNS:
        if pat.search(content):
            scores["html"] += 1

    for pat in _MARKDOWN_PATTERNS:
        if pat.search(content):
            scores["markdown"] += 1

    for pat in _RST_PATTERNS:
        if pat.search(content):
            scores["rst"] += 1

    for pat in _ASCIIDOC_PATTERNS:
        if pat.search(content):
            scores["asciidoc"] += 1

    # LaTeX bonus: \begin{document} is definitive
    if re.search(r"\\begin\{document\}", content):
        scores["latex"] += 10

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] >= 2:
        return best

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Encoding Detection / تشخیص encoding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ENCODING_FALLBACKS = [
    "utf-8-sig", "utf-8", "utf-16",
    "windows-1256", "iso-8859-6", "cp1252",
]


def detect_encoding(path: str | Path) -> EncodingInfo:
    """
    تشخیص encoding فایل.
    Detect file encoding using BOM analysis + chardet + heuristics.

    ترتیب:
    1. BOM (قطعی)
    2. chardet (اگر نصب باشد)
    3. تلاش ترتیبی

    Args:
        path: مسیر فایل

    Returns:
        EncodingInfo شامل نام، BOM و ضریب اطمینان

    Raises:
        FileNotFoundError: فایل وجود ندارد
    """
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"فایل یافت نشد: {file_path}")

    raw = file_path.read_bytes()

    # ─── مرحله ۱: BOM ────────────────────
    bom_result = _detect_bom(raw)
    if bom_result:
        return bom_result

    # ─── مرحله ۲: chardet ────────────────
    chardet_result = _detect_with_chardet(raw)
    if chardet_result and chardet_result.confidence >= 0.7:
        return chardet_result

    # ─── مرحله ۳: Heuristic ──────────────
    heuristic_result = _detect_heuristic(raw)
    if heuristic_result:
        return heuristic_result

    # ─── Fallback ─────────────────────────
    return EncodingInfo(name="utf-8", has_bom=False, confidence=0.5)


def _detect_bom(raw: bytes) -> Optional[EncodingInfo]:
    """تشخیص BOM."""
    if raw[:3] == _UTF8_BOM:
        return EncodingInfo(name="utf-8-sig", has_bom=True, confidence=1.0)
    if raw[:2] == _UTF16_LE_BOM:
        return EncodingInfo(name="utf-16-le", has_bom=True, confidence=1.0)
    if raw[:2] == _UTF16_BE_BOM:
        return EncodingInfo(name="utf-16-be", has_bom=True, confidence=1.0)
    return None


def _detect_with_chardet(raw: bytes) -> Optional[EncodingInfo]:
    """تشخیص با chardet."""
    try:
        import chardet  # type: ignore[import-untyped]
        result = chardet.detect(raw[:10240])
        if result and result.get("encoding"):
            enc = result["encoding"].lower()
            conf = result.get("confidence", 0.0)
            return EncodingInfo(
                name=enc, has_bom=False, confidence=round(conf, 3),
            )
    except ImportError:
        logger.debug("chardet نصب نیست — از heuristic استفاده می‌شود.")
    return None


def _detect_heuristic(raw: bytes) -> Optional[EncodingInfo]:
    """تشخیص با تلاش ترتیبی."""
    for enc in _ENCODING_FALLBACKS:
        try:
            raw.decode(enc)
            conf = 0.8 if enc.startswith("utf") else 0.6
            return EncodingInfo(
                name=enc, has_bom=False, confidence=conf,
            )
        except (UnicodeDecodeError, LookupError):
            continue
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Language Detection / تشخیص زبان
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_language(content: str) -> LanguageInfo:
    """
    تشخیص زبان محتوا (فارسی / انگلیسی / دوزبانه).
    Detect content language based on character distribution.

    تحلیل:
    - شمارش کاراکترهای فارسی/عربی
    - شمارش کاراکترهای لاتین
    - محاسبه نسبت و تعیین زبان غالب

    Args:
        content: محتوای متنی

    Returns:
        LanguageInfo شامل زبان اصلی و نسبت‌ها
    """
    if not content or not content.strip():
        return LanguageInfo(primary="unknown")

    # حذف بلوک‌های کد و فرمول (محتوای غیرطبیعی)
    cleaned = _strip_code_and_math(content)

    persian_chars = _PERSIAN_RANGE.findall(cleaned)
    latin_chars = _LATIN_RANGE.findall(cleaned)

    p_count = len(persian_chars)
    l_count = len(latin_chars)
    total = p_count + l_count

    if total == 0:
        return LanguageInfo(primary="unknown")

    p_ratio = round(p_count / total, 3)
    l_ratio = round(l_count / total, 3)

    has_persian = p_count > 0
    has_english = l_count > 0

    # تعیین زبان
    if p_ratio >= _MIXED_THRESHOLD and l_ratio >= _MIXED_THRESHOLD:
        primary = "fa+en"
    elif p_ratio > 0.5:
        primary = "fa"
    elif l_ratio > 0.5:
        primary = "en"
    else:
        primary = "unknown"

    return LanguageInfo(
        primary=primary,
        has_persian=has_persian,
        has_english=has_english,
        persian_ratio=p_ratio,
        english_ratio=l_ratio,
    )


def _strip_code_and_math(content: str) -> str:
    """حذف بلوک‌های کد و ریاضی برای تشخیص زبان دقیق‌تر."""
    # حذف بلوک‌های ```...```
    result = re.sub(r"```[\s\S]*?```", " ", content)
    # حذف inline code `...`
    result = re.sub(r"`[^`]+`", " ", result)
    # حذف فرمول display $$...$$
    result = re.sub(r"\$\$[\s\S]*?\$\$", " ", result)
    # حذف فرمول inline $...$
    result = re.sub(r"\$[^$]+\$", " ", result)
    # حذف دستورات LaTeX
    result = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", " ", result)
    result = re.sub(r"\\[a-zA-Z]+", " ", result)
    # حذف URL ها
    result = re.sub(r"https?://\S+", " ", result)
    return result
