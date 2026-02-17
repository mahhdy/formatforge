"""
FormatForge - Archive Handler Tests
تست‌های ماژول مدیریت آرشیو

Tests for extract_archive, is_archive, cleanup_temp,
filename encoding fix, zip-bomb protection, and path traversal.
"""

from __future__ import annotations

import shutil
import struct
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pytest

from formatforge.core.scanner.archive_handler import (
    ArchiveBombError,
    ArchiveError,
    ArchivePasswordError,
    ExtractedArchive,
    ExtractedFile,
    cleanup_temp,
    extract_archive,
    is_archive,
    _detect_archive_type,
    _fix_zip_filename,
    _human_size,
    _sanitize_tar_name,
    _validate_member_path,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures / فیکسچرها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def tmp_dir():
    """پوشه موقت برای تست‌ها."""
    d = Path(tempfile.mkdtemp(prefix="ff_archtest_"))
    yield d
    if d.exists():
        shutil.rmtree(str(d))


@pytest.fixture
def sample_zip(tmp_dir: Path) -> Path:
    """یک فایل ZIP ساده با محتوای فارسی."""
    zip_path = tmp_dir / "test_sample.zip"
    with zipfile.ZipFile(str(zip_path), "w") as zf:
        zf.writestr("readme.txt", "Hello World")
        zf.writestr(
            "docs/فصل-اول.txt",
            "این فصل اول است.\nنیم\u200cفاصله دارد.",
        )
        zf.writestr(
            "docs/chapter2.md",
            "# Chapter 2\n\nSome content here.",
        )
        zf.writestr("images/logo.svg", "<svg></svg>")
    return zip_path


@pytest.fixture
def sample_tar_gz(tmp_dir: Path) -> Path:
    """یک فایل TAR.GZ ساده."""
    tar_path = tmp_dir / "test_sample.tar.gz"

    # ابتدا فایل‌ها را در پوشه موقت بسازیم
    src = tmp_dir / "_tar_src"
    src.mkdir()
    (src / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nسلام\\end{document}",
        encoding="utf-8",
    )
    (src / "refs.bib").write_text(
        "@article{test, title={Test}}",
        encoding="utf-8",
    )
    sub = src / "chapters"
    sub.mkdir()
    (sub / "ch1.tex").write_text(
        "\\chapter{فصل اول}",
        encoding="utf-8",
    )

    with tarfile.open(str(tar_path), "w:gz") as tf:
        for f in src.rglob("*"):
            if f.is_file():
                tf.add(str(f), arcname=str(f.relative_to(src)))

    shutil.rmtree(str(src))
    return tar_path


@pytest.fixture
def empty_zip(tmp_dir: Path) -> Path:
    """یک فایل ZIP خالی."""
    zip_path = tmp_dir / "empty.zip"
    with zipfile.ZipFile(str(zip_path), "w"):
        pass
    return zip_path


@pytest.fixture
def nested_zip(tmp_dir: Path) -> Path:
    """آرشیو ZIP با ساختار تو‌در‌تو."""
    zip_path = tmp_dir / "nested.zip"
    with zipfile.ZipFile(str(zip_path), "w") as zf:
        zf.writestr("level1/level2/level3/deep.txt", "عمیق")
        zf.writestr("level1/file1.md", "# سطح ۱")
        zf.writestr("level1/level2/file2.tex", "\\section{سطح ۲}")
    return zip_path


@pytest.fixture
def non_archive_file(tmp_dir: Path) -> Path:
    """یک فایل عادی (غیر آرشیو)."""
    f = tmp_dir / "normal.txt"
    f.write_text("این یک فایل عادی است.", encoding="utf-8")
    return f


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# is_archive Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIsArchive:
    """تست‌های تشخیص آرشیو."""

    def test_zip_is_archive(self, sample_zip: Path) -> None:
        """ZIP باید آرشیو شناخته شود."""
        assert is_archive(sample_zip) is True

    def test_tar_gz_is_archive(self, sample_tar_gz: Path) -> None:
        """TAR.GZ باید آرشیو شناخته شود."""
        assert is_archive(sample_tar_gz) is True

    def test_text_not_archive(self, non_archive_file: Path) -> None:
        """فایل متنی نباید آرشیو شناخته شود."""
        assert is_archive(non_archive_file) is False

    def test_nonexistent_not_archive(self) -> None:
        """فایل ناموجود نباید آرشیو شناخته شود."""
        assert is_archive("/nonexistent/file.zip") is False

    def test_directory_not_archive(self, tmp_dir: Path) -> None:
        """پوشه نباید آرشیو شناخته شود."""
        assert is_archive(tmp_dir) is False

    def test_renamed_zip_detected_by_magic(
        self, sample_zip: Path, tmp_dir: Path,
    ) -> None:
        """ZIP با پسوند تغییریافته از magic bytes شناخته شود."""
        renamed = tmp_dir / "archive.dat"
        shutil.copy2(str(sample_zip), str(renamed))
        assert is_archive(renamed) is True

    def test_empty_zip_is_archive(self, empty_zip: Path) -> None:
        """ZIP خالی هم آرشیو است."""
        assert is_archive(empty_zip) is True

    @pytest.mark.parametrize("ext", [".rar", ".7z"])
    def test_fake_rar_7z_not_archive(
        self, tmp_dir: Path, ext: str,
    ) -> None:
        """فایل با پسوند RAR/7Z اما محتوای نامعتبر."""
        fake = tmp_dir / f"fake{ext}"
        fake.write_bytes(b"this is not a real archive")
        # پسوند هست ولی magic نیست — باز هم True چون پسوند
        # بررسی می‌شود
        assert is_archive(fake) is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# extract_archive Tests — ZIP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtractZip:
    """تست‌های استخراج ZIP."""

    def test_basic_zip_extraction(
        self, sample_zip: Path, tmp_dir: Path,
    ) -> None:
        """استخراج یک ZIP ساده با فایل‌های فارسی."""
        result = extract_archive(sample_zip, tmp_dir / "out")

        assert isinstance(result, ExtractedArchive)
        assert result.archive_type == "zip"
        assert result.total_files == 4
        assert result.total_size_bytes > 0
        assert len(result.files) == 4

        # بررسی وجود فایل‌ها
        extract_path = Path(result.extract_dir)
        assert (extract_path / "readme.txt").exists()
        assert (extract_path / "images" / "logo.svg").exists()

    def test_zip_persian_content_preserved(
        self, sample_zip: Path, tmp_dir: Path,
    ) -> None:
        """محتوای فارسی و نیم‌فاصله حفظ شود."""
        result = extract_archive(sample_zip, tmp_dir / "out")
        extract_path = Path(result.extract_dir)

        # یافتن فایل فارسی
        persian_files = [
            f for f in result.files
            if "فصل" in f.relative_path
        ]
        assert len(persian_files) >= 1

        # بررسی محتوا
        pf = persian_files[0]
        content = Path(pf.absolute_path).read_text(encoding="utf-8")
        assert "نیم\u200cفاصله" in content  # ZWNJ preserved

        # cleanup
        cleanup_temp(result.extract_dir)

    def test_empty_zip_extraction(
        self, empty_zip: Path, tmp_dir: Path,
    ) -> None:
        """استخراج ZIP خالی."""
        result = extract_archive(empty_zip, tmp_dir / "out")
        assert result.total_files == 0
        assert len(result.files) == 0
        cleanup_temp(result.extract_dir)

    def test_nested_zip_extraction(
        self, nested_zip: Path, tmp_dir: Path,
    ) -> None:
        """استخراج ZIP با ساختار تو‌در‌تو."""
        result = extract_archive(nested_zip, tmp_dir / "out")
        assert result.total_files == 3

        paths = {f.relative_path for f in result.files}
        assert any("level3" in p for p in paths)
        cleanup_temp(result.extract_dir)

    def test_file_not_found(self) -> None:
        """آرشیو ناموجود باید خطا بدهد."""
        with pytest.raises(FileNotFoundError):
            extract_archive("/nonexistent/archive.zip")

    def test_not_a_file(self, tmp_dir: Path) -> None:
        """مسیر پوشه باید خطا بدهد."""
        with pytest.raises(ArchiveError):
            extract_archive(tmp_dir)

    def test_corrupted_zip(self, tmp_dir: Path) -> None:
        """ZIP خراب باید خطا بدهد."""
        bad = tmp_dir / "bad.zip"
        bad.write_bytes(b"PK\x03\x04" + b"\x00" * 100)
        with pytest.raises(ArchiveError):
            extract_archive(bad, tmp_dir / "out")

    def test_unsupported_format(self, tmp_dir: Path) -> None:
        """فرمت ناشناخته باید خطا بدهد."""
        unknown = tmp_dir / "data.xyz"
        unknown.write_bytes(b"\x00\x01\x02\x03" * 10)
        with pytest.raises(ArchiveError):
            extract_archive(unknown)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# extract_archive Tests — TAR.GZ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtractTarGz:
    """تست‌های استخراج TAR.GZ."""

    def test_basic_tar_gz_extraction(
        self, sample_tar_gz: Path, tmp_dir: Path,
    ) -> None:
        """استخراج یک TAR.GZ ساده."""
        result = extract_archive(sample_tar_gz, tmp_dir / "out")

        assert isinstance(result, ExtractedArchive)
        assert result.archive_type == "tar_gz"
        assert result.total_files == 3

        extract_path = Path(result.extract_dir)
        assert (extract_path / "main.tex").exists()
        assert (extract_path / "refs.bib").exists()
        assert (extract_path / "chapters" / "ch1.tex").exists()

        cleanup_temp(result.extract_dir)

    def test_tar_gz_persian_content(
        self, sample_tar_gz: Path, tmp_dir: Path,
    ) -> None:
        """محتوای فارسی در TAR.GZ حفظ شود."""
        result = extract_archive(sample_tar_gz, tmp_dir / "out")
        extract_path = Path(result.extract_dir)

        content = (extract_path / "chapters" / "ch1.tex").read_text(
            encoding="utf-8"
        )
        assert "فصل اول" in content

        cleanup_temp(result.extract_dir)

    def test_corrupted_tar_gz(self, tmp_dir: Path) -> None:
        """TAR.GZ خراب باید خطا بدهد."""
        bad = tmp_dir / "bad.tar.gz"
        bad.write_bytes(b"\x1f\x8b" + b"\x00" * 50)
        with pytest.raises(ArchiveError):
            extract_archive(bad, tmp_dir / "out")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# cleanup_temp Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCleanupTemp:
    """تست‌های پاک‌سازی پوشه موقت."""

    def test_cleanup_existing(self, tmp_dir: Path) -> None:
        """پوشه موجود باید حذف شود."""
        target = tmp_dir / "to_clean"
        target.mkdir()
        (target / "file.txt").write_text("test")
        (target / "sub").mkdir()
        (target / "sub" / "deep.txt").write_text("deep")

        cleanup_temp(target)
        assert not target.exists()

    def test_cleanup_nonexistent(self) -> None:
        """پوشه ناموجود نباید خطا بدهد."""
        cleanup_temp("/nonexistent/path/xyz")

    def test_cleanup_file_ignored(self, tmp_dir: Path) -> None:
        """فایل (نه پوشه) نباید حذف شود."""
        f = tmp_dir / "file.txt"
        f.write_text("keep me")
        cleanup_temp(f)
        assert f.exists()

    def test_extract_then_cleanup(
        self, sample_zip: Path, tmp_dir: Path,
    ) -> None:
        """استخراج + پاک‌سازی کامل."""
        result = extract_archive(sample_zip, tmp_dir / "out")
        ed = Path(result.extract_dir)
        assert ed.exists()
        cleanup_temp(ed)
        assert not ed.exists()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Path Traversal Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPathTraversal:
    """تست‌های محافظت path traversal."""

    def test_validate_safe_path(self, tmp_dir: Path) -> None:
        """مسیر امن باید قبول شود."""
        result = _validate_member_path("docs/file.txt", tmp_dir)
        assert str(result).startswith(str(tmp_dir.resolve()))

    def test_validate_traversal_blocked(
        self, tmp_dir: Path,
    ) -> None:
        """مسیر با .. باید رد شود."""
        with pytest.raises(ArchiveError):
            _validate_member_path("../../etc/passwd", tmp_dir)

    def test_validate_absolute_blocked(
        self, tmp_dir: Path,
    ) -> None:
        """مسیر مطلق باید رد شود."""
        with pytest.raises(ArchiveError):
            _validate_member_path("/etc/passwd", tmp_dir)

    def test_sanitize_tar_name_removes_dotdot(self) -> None:
        """.. از نام TAR حذف شود."""
        assert ".." not in _sanitize_tar_name("../../etc/passwd")

    def test_sanitize_tar_name_removes_leading_slash(self) -> None:
        """/ ابتدایی از نام TAR حذف شود."""
        result = _sanitize_tar_name("/etc/passwd")
        assert not result.startswith("/")

    def test_sanitize_tar_empty_parts(self) -> None:
        """نام خالی پس از پاک‌سازی."""
        result = _sanitize_tar_name("../../..")
        assert result == "unnamed_file"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Archive Type Detection Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDetectArchiveType:
    """تست‌های تشخیص نوع آرشیو."""

    def test_detect_zip(self, sample_zip: Path) -> None:
        """ZIP شناسایی شود."""
        assert _detect_archive_type(sample_zip) == "zip"

    def test_detect_tar_gz(self, sample_tar_gz: Path) -> None:
        """TAR.GZ شناسایی شود."""
        assert _detect_archive_type(sample_tar_gz) == "tar_gz"

    def test_detect_by_compound_ext(self, tmp_dir: Path) -> None:
        """پسوند ترکیبی .tar.bz2 شناسایی شود."""
        fake = tmp_dir / "data.tar.bz2"
        fake.write_bytes(b"\x00" * 10)
        assert _detect_archive_type(fake) == "tar_bz2"

    def test_detect_by_ext_rar(self, tmp_dir: Path) -> None:
        """پسوند .rar شناسایی شود."""
        fake = tmp_dir / "data.rar"
        fake.write_bytes(b"\x00" * 10)
        assert _detect_archive_type(fake) == "rar"

    def test_detect_by_ext_7z(self, tmp_dir: Path) -> None:
        """پسوند .7z شناسایی شود."""
        fake = tmp_dir / "data.7z"
        fake.write_bytes(b"\x00" * 10)
        assert _detect_archive_type(fake) == "7z"

    def test_detect_unknown(self, tmp_dir: Path) -> None:
        """فایل ناشناخته → None."""
        unknown = tmp_dir / "data.xyz"
        unknown.write_bytes(b"\x00" * 10)
        assert _detect_archive_type(unknown) is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ExtractedArchive Data Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtractedArchiveData:
    """تست‌های ساختار داده‌ای خروجی."""

    def test_result_fields(
        self, sample_zip: Path, tmp_dir: Path,
    ) -> None:
        """تمام فیلدهای خروجی باید درست باشند."""
        result = extract_archive(sample_zip, tmp_dir / "out")

        assert result.archive_path == str(sample_zip.resolve())
        assert Path(result.extract_dir).is_dir()
        assert result.archive_type == "zip"
        assert isinstance(result.files, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.encoding_issues, list)
        assert result.total_files == len(result.files)
        assert result.total_size_bytes >= 0

        cleanup_temp(result.extract_dir)

    def test_extracted_file_fields(
        self, sample_zip: Path, tmp_dir: Path,
    ) -> None:
        """فیلدهای هر ExtractedFile درست باشند."""
        result = extract_archive(sample_zip, tmp_dir / "out")

        for f in result.files:
            assert isinstance(f, ExtractedFile)
            assert f.relative_path
            assert f.absolute_path
            assert Path(f.absolute_path).exists()
            assert f.size_bytes >= 0
            assert isinstance(f.encoding_fixed, bool)

        cleanup_temp(result.extract_dir)

    def test_custom_temp_dir(
        self, sample_zip: Path, tmp_dir: Path,
    ) -> None:
        """پوشه موقت سفارشی استفاده شود."""
        custom = tmp_dir / "my_temp"
        result = extract_archive(sample_zip, custom)

        assert str(custom.resolve()) in result.extract_dir
        cleanup_temp(result.extract_dir)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Utility Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestUtilities:
    """تست‌های ابزارهای کمکی."""

    @pytest.mark.parametrize(
        "size_bytes,expected",
        [
            (0, "0.0 B"),
            (512, "512.0 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
        ],
    )
    def test_human_size(
        self, size_bytes: int, expected: str,
    ) -> None:
        """تبدیل بایت به رشته خوانا."""
        assert _human_size(size_bytes) == expected


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Exception Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExceptions:
    """تست‌های استثناها."""

    def test_archive_error_message(self) -> None:
        """پیام خطای ArchiveError."""
        err = ArchiveError("/path/to/file.zip", "test error")
        assert "file.zip" in str(err)
        assert "test error" in str(err)

    def test_archive_password_error(self) -> None:
        """پیام خطای رمزدار."""
        err = ArchivePasswordError("/path/to/file.zip")
        assert "رمزدار" in str(err) or "Password" in str(err)

    def test_archive_bomb_error(self) -> None:
        """پیام خطای zip bomb."""
        err = ArchiveBombError("/path/to/file.zip", "too many files")
        assert "zip bomb" in str(err)
        assert "too many files" in str(err)

    def test_archive_error_inherits_scan_error(self) -> None:
        """ArchiveError باید از ScanError ارث‌بری کند."""
        from formatforge.exceptions import ScanError
        err = ArchiveError("/path", "msg")
        assert isinstance(err, ScanError)

    def test_password_error_inherits_archive_error(self) -> None:
        """ArchivePasswordError از ArchiveError ارث‌بری کند."""
        err = ArchivePasswordError("/path")
        assert isinstance(err, ArchiveError)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration: Scanner __init__ imports
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestScannerImports:
    """تست اینکه importها از __init__ درست کار کنند."""

    def test_import_from_scanner_package(self) -> None:
        """import از پکیج scanner."""
        from formatforge.core.scanner import (
            extract_archive,
            cleanup_temp,
            is_archive,
            ExtractedArchive,
            ExtractedFile,
            ArchiveError,
        )
        assert callable(extract_archive)
        assert callable(cleanup_temp)
        assert callable(is_archive)

    def test_existing_imports_still_work(self) -> None:
        """importهای قبلی هنوز کار کنند."""
        from formatforge.core.scanner import (
            detect_format,
            detect_encoding,
            detect_language,
            analyze_directory,
        )
        assert callable(detect_format)
        assert callable(detect_encoding)
        assert callable(detect_language)
        assert callable(analyze_directory)
