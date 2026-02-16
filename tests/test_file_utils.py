"""
Tests for formatforge.utils.file_utils
تست‌های ابزارهای فایل
"""

import tempfile
from pathlib import Path

import pytest

from formatforge.utils.file_utils import (
    FileReadResult,
    count_zwnj,
    detect_encoding,
    ensure_directory,
    get_file_size_human,
    read_file_safe,
    write_file_utf8_bom,
)


ZWNJ = "\u200c"


# ─── Fixtures ─────────────────────────────────

@pytest.fixture
def tmp_dir():
    """پوشه موقت."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_persian_file(tmp_dir: Path) -> Path:
    """فایل فارسی نمونه با BOM و ZWNJ."""
    p = tmp_dir / "sample.tex"
    content = f"\ufeffسلام{ZWNJ}دنیا\nمی{ZWNJ}خواهیم تست کنیم."
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def sample_ascii_file(tmp_dir: Path) -> Path:
    """فایل ASCII ساده."""
    p = tmp_dir / "hello.txt"
    p.write_text("Hello world\n", encoding="utf-8")
    return p


# ─── Tests: count_zwnj ──────────────────────

class TestCountZwnj:
    """تست‌های شمارش نیم‌فاصله."""

    def test_no_zwnj(self):
        assert count_zwnj("سلام دنیا") == 0

    def test_one_zwnj(self):
        assert count_zwnj(f"می{ZWNJ}خواهم") == 1

    def test_multiple_zwnj(self):
        text = f"نیم{ZWNJ}فاصله{ZWNJ}ها{ZWNJ}ی فارسی"
        assert count_zwnj(text) == 3

    def test_empty_string(self):
        assert count_zwnj("") == 0


# ─── Tests: detect_encoding ─────────────────

class TestDetectEncoding:
    """تست‌های تشخیص encoding."""

    def test_utf8_bom(self, tmp_dir: Path):
        p = tmp_dir / "bom.txt"
        p.write_bytes(b"\xef\xbb\xbfHello")
        assert detect_encoding(p) == "utf-8-sig"

    def test_utf8_no_bom(self, sample_ascii_file: Path):
        enc = detect_encoding(sample_ascii_file)
        assert enc in ("utf-8", "utf-8-sig", "ascii")

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            detect_encoding("/nonexistent/file.txt")


# ─── Tests: read_file_safe ──────────────────

class TestReadFileSafe:
    """تست‌های خواندن امن فایل."""

    def test_reads_content(self, sample_persian_file: Path):
        result = read_file_safe(sample_persian_file)
        assert isinstance(result, FileReadResult)
        assert "سلام" in result.content
        assert result.zwnj_count == 2

    def test_detects_bom(self, sample_persian_file: Path):
        result = read_file_safe(sample_persian_file)
        assert result.has_bom is True

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            read_file_safe("/nonexistent.txt")

    def test_directory_raises(self, tmp_dir: Path):
        with pytest.raises(ValueError, match="فایل نیست"):
            read_file_safe(tmp_dir)

    def test_size_bytes(self, sample_ascii_file: Path):
        result = read_file_safe(sample_ascii_file)
        assert result.size_bytes > 0

    def test_explicit_encoding(self, sample_ascii_file: Path):
        result = read_file_safe(sample_ascii_file, encoding="utf-8")
        assert result.encoding == "utf-8"


# ─── Tests: write_file_utf8_bom ─────────────

class TestWriteFileUtf8Bom:
    """تست‌های نوشتن فایل با BOM."""

    def test_writes_bom(self, tmp_dir: Path):
        p = tmp_dir / "out.mdx"
        write_file_utf8_bom(p, "سلام")
        raw = p.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"

    def test_content_preserved(self, tmp_dir: Path):
        p = tmp_dir / "out.mdx"
        content = f"نیم{ZWNJ}فاصله"
        write_file_utf8_bom(p, content)
        result = read_file_safe(p)
        assert result.zwnj_count == 1
        assert ZWNJ in result.content

    def test_no_double_bom(self, tmp_dir: Path):
        p = tmp_dir / "out.mdx"
        write_file_utf8_bom(p, "\ufeffسلام")
        raw = p.read_bytes()
        # فقط یک BOM باید باشد
        bom_count = raw.count(b"\xef\xbb\xbf")
        assert bom_count == 1

    def test_creates_parents(self, tmp_dir: Path):
        p = tmp_dir / "a" / "b" / "c" / "out.txt"
        write_file_utf8_bom(p, "test")
        assert p.exists()

    def test_returns_bytes_written(self, tmp_dir: Path):
        p = tmp_dir / "out.txt"
        written = write_file_utf8_bom(p, "hello")
        assert written > 0


# ─── Tests: ensure_directory ─────────────────

class TestEnsureDirectory:
    """تست‌های ساخت پوشه."""

    def test_creates_new(self, tmp_dir: Path):
        new_dir = tmp_dir / "new" / "nested"
        result = ensure_directory(new_dir)
        assert result.exists()
        assert result.is_dir()

    def test_existing_ok(self, tmp_dir: Path):
        result = ensure_directory(tmp_dir)
        assert result.exists()


# ─── Tests: get_file_size_human ──────────────

class TestGetFileSizeHuman:
    """تست‌های نمایش اندازه."""

    def test_bytes(self):
        assert "B" in get_file_size_human(500)

    def test_kilobytes(self):
        assert "KB" in get_file_size_human(2048)

    def test_megabytes(self):
        assert "MB" in get_file_size_human(2 * 1024 * 1024)
