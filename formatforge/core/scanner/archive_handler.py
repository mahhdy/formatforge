"""
FormatForge - Archive Handler
مدیریت فایل‌های آرشیو (ZIP, TAR.GZ, RAR, 7Z)

Extract archives, detect filename encoding for Persian,
validate against zip-bomb / path-traversal, and manage temp dirs.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from formatforge.exceptions import ScanError

logger = logging.getLogger("formatforge.scanner.archive")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Exceptions / استثناها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ArchiveError(ScanError):
    """خطا در پردازش آرشیو — Archive processing error."""

    def __init__(self, path: str, message: str):
        self.archive_path = path
        super().__init__(
            f"Archive error ({Path(path).name}): {message}"
        )


class ArchivePasswordError(ArchiveError):
    """آرشیو رمزدار — Password-protected archive."""

    def __init__(self, path: str):
        super().__init__(path, "آرشیو رمزدار است / Password-protected")


class ArchiveBombError(ArchiveError):
    """محافظت در برابر zip bomb — Zip bomb protection."""

    def __init__(self, path: str, detail: str = ""):
        msg = "احتمال zip bomb"
        if detail:
            msg += f": {detail}"
        super().__init__(path, msg)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants / ثابت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SIMPLE_EXTENSIONS: dict[str, str] = {
    ".zip": "zip",
    ".rar": "rar",
    ".7z": "7z",
    ".tar": "tar",
    ".tgz": "tar_gz",
    ".tbz2": "tar_bz2",
    ".txz": "tar_xz",
}

_COMPOUND_EXTENSIONS: dict[str, str] = {
    ".tar.gz": "tar_gz",
    ".tar.bz2": "tar_bz2",
    ".tar.xz": "tar_xz",
}

_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),
    (b"\x1f\x8b", "tar_gz"),
    (b"BZh", "tar_bz2"),
    (b"\xfd7zXZ\x00", "tar_xz"),
    (b"Rar!\x1a\x07\x00", "rar"),
    (b"Rar!\x1a\x07\x01\x00", "rar"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
]

_MAX_EXTRACT_SIZE: int = 2 * 1024 * 1024 * 1024   # 2 GB
_MAX_FILE_COUNT: int = 10_000

_PERSIAN_RANGE = re.compile(
    "[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff]"
)
_FILENAME_ENCODINGS = (
    "utf-8", "windows-1256", "cp1256", "iso-8859-6", "cp437",
)

_TAR_MODES: dict[str, str] = {
    "tar": "r:", "tar_gz": "r:gz",
    "tar_bz2": "r:bz2", "tar_xz": "r:xz",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Classes / کلاس‌های داده
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ExtractedFile:
    """اطلاعات یک فایل استخراج‌شده. / Single extracted file info."""
    relative_path: str
    absolute_path: str
    size_bytes: int = 0
    original_name: str = ""
    encoding_fixed: bool = False


@dataclass
class ExtractedArchive:
    """نتیجه استخراج آرشیو. / Archive extraction result."""
    archive_path: str
    extract_dir: str
    archive_type: str
    files: list[ExtractedFile] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    encoding_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Public API / رابط عمومی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def is_archive(path: str | Path) -> bool:
    """
    آیا فایل یک آرشیو است؟
    Check if a file is a supported archive (by extension + magic bytes).

    Args:
        path: مسیر فایل

    Returns:
        True اگر فایل آرشیو باشد
    """
    file_path = Path(path)
    if not file_path.is_file():
        return False

    name_lower = file_path.name.lower()
    for ext in _COMPOUND_EXTENSIONS:
        if name_lower.endswith(ext):
            return True

    if file_path.suffix.lower() in _SIMPLE_EXTENSIONS:
        return True

    return _detect_by_magic(file_path) is not None


def extract_archive(
    path: str | Path,
    temp_dir: str | Path | None = None,
) -> ExtractedArchive:
    """
    استخراج آرشیو به پوشه موقت.
    Extract archive to a temporary directory.

    پشتیبانی: ZIP, TAR.GZ/BZ2/XZ, RAR (اختیاری), 7Z (اختیاری)
    شامل: تشخیص encoding نام فایل‌های فارسی، محافظت zip-bomb/path-traversal

    Args:
        path: مسیر فایل آرشیو
        temp_dir: پوشه پایه برای استخراج (None = سیستمی)

    Returns:
        ExtractedArchive شامل مسیر استخراج و لیست فایل‌ها

    Raises:
        FileNotFoundError: آرشیو یافت نشد
        ArchiveError: خطا در استخراج
        ArchivePasswordError: آرشیو رمزدار
        ArchiveBombError: احتمال zip bomb
    """
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"آرشیو یافت نشد: {file_path}")
    if not file_path.is_file():
        raise ArchiveError(str(file_path), "مسیر یک فایل نیست")

    archive_type = _detect_archive_type(file_path)
    if not archive_type:
        raise ArchiveError(str(file_path), "فرمت آرشیو شناسایی نشد")

    extract_path = _create_extract_dir(temp_dir)

    logger.info(
        "استخراج آرشیو %s (نوع: %s) به %s",
        file_path.name, archive_type, extract_path,
    )

    try:
        warnings = _dispatch_extract(
            file_path, extract_path, archive_type
        )
    except ArchiveError:
        cleanup_temp(extract_path)
        raise
    except Exception as exc:
        cleanup_temp(extract_path)
        raise ArchiveError(str(file_path), str(exc)) from exc

    files, enc_issues = _collect_extracted_files(extract_path)
    total_size = sum(f.size_bytes for f in files)

    logger.info(
        "استخراج کامل: %d فایل, %s",
        len(files), _human_size(total_size),
    )

    return ExtractedArchive(
        archive_path=str(file_path),
        extract_dir=str(extract_path),
        archive_type=archive_type,
        files=files,
        total_files=len(files),
        total_size_bytes=total_size,
        encoding_issues=enc_issues,
        warnings=warnings,
    )


def cleanup_temp(path: str | Path) -> None:
    """
    پاک‌سازی پوشه موقت استخراج.
    Remove temporary extraction directory and all contents.

    Args:
        path: مسیر پوشه موقت
    """
    target = Path(path)
    if target.exists() and target.is_dir():
        try:
            shutil.rmtree(str(target))
            logger.debug("پاک‌سازی موقت: %s", target)
        except OSError as exc:
            logger.warning("خطا در پاک‌سازی %s: %s", target, exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Detection / تشخیص نوع آرشیو
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _detect_archive_type(file_path: Path) -> Optional[str]:
    """تشخیص نوع آرشیو از پسوند + magic bytes."""
    name_lower = file_path.name.lower()
    for ext, atype in _COMPOUND_EXTENSIONS.items():
        if name_lower.endswith(ext):
            return atype

    ext_type = _SIMPLE_EXTENSIONS.get(file_path.suffix.lower())
    magic_type = _detect_by_magic(file_path)
    return magic_type or ext_type


def _detect_by_magic(file_path: Path) -> Optional[str]:
    """تشخیص نوع آرشیو از magic bytes."""
    try:
        head = file_path.read_bytes()[:16]
    except OSError:
        return None
    for magic, atype in _MAGIC_SIGNATURES:
        if head[: len(magic)] == magic:
            return atype
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Extraction / استخراج
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _create_extract_dir(
    temp_dir: str | Path | None,
) -> Path:
    """ساخت پوشه موقت برای استخراج."""
    if temp_dir:
        base = Path(temp_dir).resolve()
        base.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="ff_", dir=str(base)))
    return Path(tempfile.mkdtemp(prefix="ff_archive_"))


def _dispatch_extract(
    archive_path: Path,
    extract_dir: Path,
    archive_type: str,
) -> list[str]:
    """انتخاب و اجرای استخراج‌کننده مناسب."""
    if archive_type == "zip":
        return _extract_zip(archive_path, extract_dir)
    if archive_type.startswith("tar"):
        return _extract_tar(archive_path, extract_dir, archive_type)
    if archive_type == "rar":
        return _extract_rar(archive_path, extract_dir)
    if archive_type == "7z":
        return _extract_7z(archive_path, extract_dir)
    raise ArchiveError(
        str(archive_path),
        f"نوع آرشیو پشتیبانی نمی‌شود: {archive_type}",
    )


def _validate_member_path(name: str, extract_dir: Path) -> Path:
    """محافظت در برابر path traversal (zip slip)."""
    target = (extract_dir / name).resolve()
    if not str(target).startswith(str(extract_dir.resolve())):
        raise ArchiveError(
            str(extract_dir), f"Path traversal detected: {name}"
        )
    return target


def _check_limits(
    count: int, total_size: int, path: str,
) -> None:
    """بررسی محدودیت تعداد و حجم (zip bomb)."""
    if count > _MAX_FILE_COUNT:
        raise ArchiveBombError(path, f"تعداد فایل‌ها: {count:,}")
    if total_size > _MAX_EXTRACT_SIZE:
        raise ArchiveBombError(
            path, f"حجم: {_human_size(total_size)}"
        )


# ─── ZIP ──────────────────────────────────────


def _extract_zip(
    archive_path: Path, extract_dir: Path,
) -> list[str]:
    """استخراج آرشیو ZIP با تشخیص encoding فارسی."""
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(str(archive_path), "r") as zf:
            infos = zf.infolist()

            # بررسی رمزدار بودن
            if any(i.flag_bits & 0x1 for i in infos):
                raise ArchivePasswordError(str(archive_path))

            total = sum(i.file_size for i in infos if not i.is_dir())
            _check_limits(len(infos), total, str(archive_path))

            for info in infos:
                if info.is_dir():
                    continue

                fixed_name = _fix_zip_filename(info)
                target = _validate_member_path(
                    fixed_name, extract_dir
                )
                target.parent.mkdir(parents=True, exist_ok=True)

                try:
                    target.write_bytes(zf.read(info.filename))
                except RuntimeError as exc:
                    if "password" in str(exc).lower():
                        raise ArchivePasswordError(
                            str(archive_path)
                        ) from exc
                    warnings.append(
                        f"خطا در استخراج {info.filename}: {exc}"
                    )

    except zipfile.BadZipFile as exc:
        raise ArchiveError(
            str(archive_path), f"فایل ZIP خراب: {exc}"
        ) from exc

    return warnings


def _fix_zip_filename(info: zipfile.ZipInfo) -> str:
    """
    اصلاح encoding نام فایل در ZIP.
    ZIP spec uses CP437 by default; fix for Persian filenames.
    """
    raw_name = info.filename

    # اگر UTF-8 flag ست باشد، نیازی به اصلاح نیست
    if info.flag_bits & 0x800:
        return raw_name

    # تلاش برای decode با encodingهای مختلف
    try:
        raw_bytes = raw_name.encode("cp437")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return raw_name

    for enc in _FILENAME_ENCODINGS:
        try:
            decoded = raw_bytes.decode(enc)
            if _PERSIAN_RANGE.search(decoded):
                logger.debug(
                    "نام فایل اصلاح شد (%s): %s → %s",
                    enc, raw_name, decoded,
                )
                return decoded
        except (UnicodeDecodeError, LookupError):
            continue

    # اگر هیچ encoding فارسی پیدا نشد، UTF-8 fallback
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_name


# ─── TAR / TAR.GZ / TAR.BZ2 / TAR.XZ ────────


def _extract_tar(
    archive_path: Path,
    extract_dir: Path,
    archive_type: str,
) -> list[str]:
    """استخراج آرشیوهای TAR و مشتقات."""
    warnings: list[str] = []
    mode = _TAR_MODES.get(archive_type, "r:*")

    try:
        with tarfile.open(str(archive_path), mode) as tf:
            members = tf.getmembers()

            file_members = [m for m in members if m.isfile()]
            total = sum(m.size for m in file_members)
            _check_limits(len(file_members), total, str(archive_path))

            for member in file_members:
                # محافظت path traversal
                clean_name = _sanitize_tar_name(member.name)
                target = _validate_member_path(
                    clean_name, extract_dir
                )
                target.parent.mkdir(parents=True, exist_ok=True)

                try:
                    source = tf.extractfile(member)
                    if source:
                        target.write_bytes(source.read())
                except Exception as exc:
                    warnings.append(
                        f"خطا در استخراج {member.name}: {exc}"
                    )

    except tarfile.TarError as exc:
        raise ArchiveError(
            str(archive_path), f"فایل TAR خراب: {exc}"
        ) from exc

    return warnings


def _sanitize_tar_name(name: str) -> str:
    """پاک‌سازی نام فایل TAR از کاراکترهای خطرناک."""
    # حذف مسیرهای مطلق و ..
    clean = name.lstrip("/").lstrip("\\")
    parts = Path(clean).parts
    safe_parts = [p for p in parts if p not in ("..", ".")]
    if not safe_parts:
        return "unnamed_file"
    return str(Path(*safe_parts))


# ─── RAR (اختیاری — نیاز به rarfile) ─────────


def _extract_rar(
    archive_path: Path, extract_dir: Path,
) -> list[str]:
    """استخراج آرشیو RAR (نیاز به پکیج rarfile + unrar)."""
    warnings: list[str] = []
    try:
        import rarfile  # type: ignore[import-untyped]
    except ImportError:
        raise ArchiveError(
            str(archive_path),
            "برای استخراج RAR، پکیج rarfile لازم است: "
            "pip install rarfile\n"
            "همچنین unrar باید نصب باشد.",
        )

    try:
        with rarfile.RarFile(str(archive_path), "r") as rf:
            infos = rf.infolist()

            file_infos = [i for i in infos if not i.is_dir()]
            total = sum(i.file_size for i in file_infos)
            _check_limits(len(file_infos), total, str(archive_path))

            for info in file_infos:
                target = _validate_member_path(
                    info.filename, extract_dir
                )
                target.parent.mkdir(parents=True, exist_ok=True)

                try:
                    target.write_bytes(rf.read(info.filename))
                except Exception as exc:
                    if "password" in str(exc).lower():
                        raise ArchivePasswordError(
                            str(archive_path)
                        ) from exc
                    warnings.append(
                        f"خطا در استخراج {info.filename}: {exc}"
                    )

    except rarfile.BadRarFile as exc:
        raise ArchiveError(
            str(archive_path), f"فایل RAR خراب: {exc}"
        ) from exc

    return warnings


# ─── 7Z (اختیاری — نیاز به py7zr) ───────────


def _extract_7z(
    archive_path: Path, extract_dir: Path,
) -> list[str]:
    """استخراج آرشیو 7Z (نیاز به پکیج py7zr)."""
    warnings: list[str] = []
    try:
        import py7zr  # type: ignore[import-untyped]
    except ImportError:
        raise ArchiveError(
            str(archive_path),
            "برای استخراج 7Z، پکیج py7zr لازم است: "
            "pip install py7zr",
        )

    try:
        with py7zr.SevenZipFile(str(archive_path), "r") as sz:
            all_files = sz.getnames()
            _check_limits(len(all_files), 0, str(archive_path))

            # path traversal check
            for name in all_files:
                _validate_member_path(name, extract_dir)

            sz.extractall(path=str(extract_dir))

    except py7zr.PasswordRequired:
        raise ArchivePasswordError(str(archive_path))
    except py7zr.Bad7zFile as exc:
        raise ArchiveError(
            str(archive_path), f"فایل 7Z خراب: {exc}"
        ) from exc
    except Exception as exc:
        if "password" in str(exc).lower():
            raise ArchivePasswordError(
                str(archive_path)
            ) from exc
        raise ArchiveError(
            str(archive_path), str(exc)
        ) from exc

    return warnings


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Post-extraction / پس از استخراج
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _collect_extracted_files(
    extract_dir: Path,
) -> tuple[list[ExtractedFile], list[str]]:
    """جمع‌آوری لیست فایل‌های استخراج‌شده و بررسی encoding."""
    files: list[ExtractedFile] = []
    encoding_issues: list[str] = []

    for item in sorted(extract_dir.rglob("*")):
        if not item.is_file():
            continue

        rel = str(item.relative_to(extract_dir))
        original = rel

        # بررسی و اصلاح نام فایل فارسی
        fixed_name, was_fixed = _fix_persian_filename(
            item, extract_dir
        )

        if was_fixed:
            encoding_issues.append(
                f"نام فایل اصلاح شد: {original} → {fixed_name}"
            )
            rel = fixed_name

        files.append(
            ExtractedFile(
                relative_path=rel,
                absolute_path=str(item),
                size_bytes=item.stat().st_size,
                original_name=original,
                encoding_fixed=was_fixed,
            )
        )

    return files, encoding_issues


def _fix_persian_filename(
    file_path: Path,
    extract_dir: Path,
) -> tuple[str, bool]:
    """
    بررسی و اصلاح نام فایل‌های فارسی.
    Check and fix Persian filenames with encoding issues.

    اصلاح ي→ی و ك→ک در نام فایل

    Returns:
        (fixed_relative_path, was_fixed)
    """
    rel = str(file_path.relative_to(extract_dir))

    # اصلاح ي → ی و ك → ک
    fixed = rel.replace("\u064a", "\u06cc")  # ي → ی
    fixed = fixed.replace("\u0643", "\u06a9")  # ك → ک

    if fixed != rel:
        new_path = extract_dir / fixed
        try:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.rename(new_path)
            return fixed, True
        except OSError as exc:
            logger.warning(
                "تغییر نام فایل ناموفق: %s → %s (%s)",
                rel, fixed, exc,
            )
            return rel, False

    return rel, False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Utilities / ابزارها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _human_size(size_bytes: int) -> str:
    """تبدیل بایت به رشته خوانا. / Human-readable file size."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

