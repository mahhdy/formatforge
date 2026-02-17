"""
FormatForge - Scanner Tests
تست‌های اسکنر یکپارچه

Tests for Scanner class, ScanReport, fix_encoding_issues,
and CLI scan command display functions.
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

import pytest

from formatforge.core.scanner.scanner import (
    AssetInfo,
    DocumentEntry,
    ScanReport,
    ScanWarning,
    Scanner,
    fix_encoding_issues,
    _has_pattern,
    _guess_mime,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures / فیکسچرها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ZWNJ = "\u200c"


@pytest.fixture
def tmp_dir():
    """پوشه موقت."""
    d = Path(tempfile.mkdtemp(prefix="ff_scantest_"))
    yield d
    if d.exists():
        shutil.rmtree(str(d))


@pytest.fixture
def single_tex_file(tmp_dir: Path) -> Path:
    """یک فایل LaTeX فارسی."""
    f = tmp_dir / "article.tex"
    content = (
        "\\documentclass{article}\n"
        "\\usepackage{xepersian}\n"
        "\\begin{document}\n"
        f"\\section{{مقدمه}}\n"
        f"این یک متن فارسی با نیم{ZWNJ}فاصله است.\n"
        "فرمول ساده: $x^2 + y^2 = z^2$\n"
        "\\end{document}\n"
    )
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def single_md_file(tmp_dir: Path) -> Path:
    """یک فایل Markdown فارسی."""
    f = tmp_dir / "readme.md"
    content = (
        "---\ntitle: تست\n---\n\n"
        "# عنوان اصلی\n\n"
        f"متن فارسی با نیم{ZWNJ}فاصله.\n\n"
        "```python\nprint('hello')\n```\n\n"
        "| ستون ۱ | ستون ۲ |\n"
        "|--------|--------|\n"
        "| مقدار  | مقدار  |\n"
    )
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def latex_project(tmp_dir: Path) -> Path:
    """پروژه LaTeX چندفایلی."""
    root = tmp_dir / "book"
    root.mkdir()

    # main.tex
    (root / "main.tex").write_text(
        "\\documentclass{book}\n"
        "\\usepackage{xepersian}\n"
        "\\begin{document}\n"
        "\\input{chapter01}\n"
        "\\input{chapter02}\n"
        "\\bibliography{refs}\n"
        "\\end{document}\n",
        encoding="utf-8-sig",  # با BOM
    )

    # chapter01.tex (بدون BOM)
    (root / "chapter01.tex").write_text(
        f"\\chapter{{فصل اول: مفاهیم پایه}}\n"
        f"متن فارسی{ZWNJ}نمونه.\n"
        "\\begin{equation}\n"
        "  E = mc^2\n"
        "\\end{equation}\n"
        "\\begin{tikzpicture}\n"
        "  \\draw (0,0) -- (1,1);\n"
        "\\end{tikzpicture}\n",
        encoding="utf-8",  # بدون BOM
    )

    # chapter02.tex (بدون BOM)
    (root / "chapter02.tex").write_text(
        f"\\chapter{{فصل دوم: منطق}}\n"
        "\\begin{tabular}{|c|c|}\n"
        "  \\hline\n"
        "  p & q \\\\\n"
        "  \\hline\n"
        "\\end{tabular}\n",
        encoding="utf-8",
    )

    # refs.bib
    (root / "refs.bib").write_text(
        "@book{test,\n"
        "  title={Test Book},\n"
        "  author={Author},\n"
        "  year={2024}\n"
        "}\n",
        encoding="utf-8",
    )

    # figures
    fig = root / "figures"
    fig.mkdir()
    (fig / "diagram.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    )
    (fig / "unused.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 30)

    return root


@pytest.fixture
def sample_archive(tmp_dir: Path) -> Path:
    """یک آرشیو ZIP ساده."""
    zip_path = tmp_dir / "project.zip"
    with zipfile.ZipFile(str(zip_path), "w") as zf:
        zf.writestr(
            "doc.tex",
            "\\documentclass{article}\n\\begin{document}\n"
            + f"سلام{ZWNJ}دنیا" + "\n\\end{document}\n",
        )
        zf.writestr("image.png", b"\x89PNG" + b"\x00" * 20)
    return zip_path


@pytest.fixture
def empty_dir(tmp_dir: Path) -> Path:
    """پوشه خالی."""
    d = tmp_dir / "empty"
    d.mkdir()
    return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Scanner.scan — Single File
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestScanSingleFile:
    """تست اسکن فایل منفرد."""

    def test_scan_tex_file(self, single_tex_file: Path) -> None:
        """اسکن یک فایل LaTeX."""
        scanner = Scanner()
        report = scanner.scan(single_tex_file)

        assert isinstance(report, ScanReport)
        assert report.input_type == "file"
        assert report.structure == "single_doc"
        assert report.doc_count == 1

        doc = report.documents[0]
        assert doc.format == "latex"
        assert doc.role == "standalone"
        assert doc.has_math is True

    def test_scan_md_file(self, single_md_file: Path) -> None:
        """اسکن یک فایل Markdown."""
        scanner = Scanner()
        report = scanner.scan(single_md_file)

        assert report.input_type == "file"
        assert report.doc_count == 1

        doc = report.documents[0]
        assert doc.format == "markdown"
        assert doc.has_code is True
        assert doc.has_tables is True

    def test_scan_persian_language_detected(
        self, single_tex_file: Path,
    ) -> None:
        """زبان فارسی تشخیص داده شود."""
        scanner = Scanner()
        report = scanner.scan(single_tex_file)
        doc = report.documents[0]
        assert "fa" in doc.language

    def test_scan_nonexistent_file(self) -> None:
        """فایل ناموجود باید خطا بدهد."""
        scanner = Scanner()
        with pytest.raises(FileNotFoundError):
            scanner.scan("/nonexistent/file.tex")

    def test_scan_file_encoding_detected(
        self, single_tex_file: Path,
    ) -> None:
        """encoding فایل تشخیص داده شود."""
        scanner = Scanner()
        report = scanner.scan(single_tex_file)
        doc = report.documents[0]
        assert "utf" in doc.encoding.lower()

    def test_scan_format_hint(
        self, single_tex_file: Path,
    ) -> None:
        """format_hint باید اعمال شود."""
        scanner = Scanner()
        report = scanner.scan(
            single_tex_file, format_hint="latex",
        )
        assert report.documents[0].format == "latex"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Scanner.scan — Directory
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestScanDirectory:
    """تست اسکن پوشه."""

    def test_scan_latex_project(
        self, latex_project: Path,
    ) -> None:
        """اسکن پروژه LaTeX چندفایلی."""
        scanner = Scanner()
        report = scanner.scan(latex_project)

        assert report.input_type == "directory"
        assert report.doc_count >= 3
        assert report.total_files > 0

    def test_structure_detected(
        self, latex_project: Path,
    ) -> None:
        """ساختار چندفصلی تشخیص داده شود."""
        scanner = Scanner()
        report = scanner.scan(latex_project)
        assert report.structure in (
            "multi_chapter_book",
            "independent_articles",
            "related_collection",
        )

    def test_assets_found(
        self, latex_project: Path,
    ) -> None:
        """assetها شناسایی شوند."""
        scanner = Scanner()
        report = scanner.scan(latex_project)
        assert report.asset_count >= 1

    def test_content_features_detected(
        self, latex_project: Path,
    ) -> None:
        """ویژگی‌های محتوا تشخیص داده شوند."""
        scanner = Scanner()
        report = scanner.scan(latex_project)

        all_math = any(d.has_math for d in report.documents)
        all_tikz = any(d.has_tikz for d in report.documents)
        all_tables = any(d.has_tables for d in report.documents)
        all_bib = any(d.has_bibliography for d in report.documents)

        assert all_math is True
        assert all_tikz is True
        assert all_tables is True
        assert all_bib is True

    def test_encoding_warnings(
        self, latex_project: Path,
    ) -> None:
        """هشدار encoding بدون BOM تولید شود."""
        scanner = Scanner()
        report = scanner.scan(latex_project)

        bom_warnings = [
            w for w in report.warnings
            if "BOM" in w.message or "bom" in w.message.lower()
        ]
        # chapter01 و chapter02 بدون BOM هستند
        assert len(bom_warnings) >= 1

    def test_empty_directory(self, empty_dir: Path) -> None:
        """پوشه خالی نباید خطا بدهد."""
        scanner = Scanner()
        report = scanner.scan(empty_dir)
        assert report.doc_count == 0
        assert report.asset_count == 0

    def test_primary_format(
        self, latex_project: Path,
    ) -> None:
        """فرمت غالب درست تشخیص داده شود."""
        scanner = Scanner()
        report = scanner.scan(latex_project)
        assert report.primary_format == "latex"

    def test_primary_language(
        self, latex_project: Path,
    ) -> None:
        """زبان غالب فارسی باشد."""
        scanner = Scanner()
        report = scanner.scan(latex_project)
        assert "fa" in report.primary_language


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Scanner.scan — Archive
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestScanArchive:
    """تست اسکن آرشیو."""

    def test_scan_zip(self, sample_archive: Path) -> None:
        """اسکن آرشیو ZIP."""
        scanner = Scanner()
        report = scanner.scan(sample_archive)

        assert report.input_type == "archive"
        assert report.doc_count >= 1
        report.cleanup()

    def test_archive_cleanup(
        self, sample_archive: Path,
    ) -> None:
        """پاک‌سازی موقت آرشیو."""
        scanner = Scanner()
        report = scanner.scan(sample_archive)

        temp = report._archive_temp
        assert temp is not None
        assert Path(temp).exists()

        report.cleanup()
        assert not Path(temp).exists()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ScanReport Properties
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestScanReportProperties:
    """تست property‌های ScanReport."""

    def _make_report(self, docs=None, assets=None, warnings=None):
        """ساخت ScanReport ساده برای تست."""
        return ScanReport(
            scan_id="test_001",
            timestamp="2025-01-01T00:00:00Z",
            input_path="/test",
            input_type="directory",
            total_files=0,
            documents=docs or [],
            assets=assets or [],
            warnings=warnings or [],
        )

    def test_doc_count(self) -> None:
        """شمارش اسناد."""
        docs = [
            DocumentEntry(id="d1", path="a.tex", format="latex"),
            DocumentEntry(id="d2", path="b.tex", format="latex"),
        ]
        r = self._make_report(docs=docs)
        assert r.doc_count == 2

    def test_asset_count(self) -> None:
        """شمارش assetها."""
        assets = [
            AssetInfo(path="img.png", type="image/png"),
        ]
        r = self._make_report(assets=assets)
        assert r.asset_count == 1

    def test_warning_count(self) -> None:
        """شمارش هشدارها."""
        warns = [
            ScanWarning(level="warning", file="a.tex", message="test"),
            ScanWarning(level="error", file="b.tex", message="err"),
            ScanWarning(level="info", file="c.tex", message="info"),
        ]
        r = self._make_report(warnings=warns)
        assert r.warning_count == 3

    def test_error_warnings(self) -> None:
        """فیلتر هشدارهای error."""
        warns = [
            ScanWarning(level="warning", file="a.tex", message="w"),
            ScanWarning(level="error", file="b.tex", message="e1"),
            ScanWarning(level="error", file="c.tex", message="e2"),
        ]
        r = self._make_report(warnings=warns)
        assert len(r.error_warnings) == 2

    def test_primary_format_single(self) -> None:
        """فرمت غالب با یک نوع."""
        docs = [
            DocumentEntry(id="d1", path="a.tex", format="latex"),
            DocumentEntry(id="d2", path="b.tex", format="latex"),
        ]
        r = self._make_report(docs=docs)
        assert r.primary_format == "latex"

    def test_primary_format_mixed(self) -> None:
        """فرمت غالب با چند نوع."""
        docs = [
            DocumentEntry(id="d1", path="a.tex", format="latex"),
            DocumentEntry(id="d2", path="b.tex", format="latex"),
            DocumentEntry(id="d3", path="c.md", format="markdown"),
        ]
        r = self._make_report(docs=docs)
        assert r.primary_format == "latex"

    def test_primary_format_empty(self) -> None:
        """فرمت غالب بدون سند."""
        r = self._make_report()
        assert r.primary_format is None

    def test_primary_language_fa(self) -> None:
        """زبان غالب فارسی."""
        docs = [
            DocumentEntry(
                id="d1", path="a.tex",
                format="latex", language="fa",
            ),
        ]
        r = self._make_report(docs=docs)
        assert r.primary_language == "fa"

    def test_primary_language_mixed(self) -> None:
        """زبان غالب دوزبانه."""
        docs = [
            DocumentEntry(
                id="d1", path="a.tex",
                format="latex", language="fa",
            ),
            DocumentEntry(
                id="d2", path="b.tex",
                format="latex", language="fa+en",
            ),
        ]
        r = self._make_report(docs=docs)
        assert "fa" in r.primary_language

    def test_primary_language_empty(self) -> None:
        """زبان بدون سند."""
        r = self._make_report()
        assert r.primary_language == "unknown"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# fix_encoding_issues
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFixEncodingIssues:
    """تست اصلاح خودکار encoding."""

    def test_add_bom(self, tmp_dir: Path) -> None:
        """افزودن BOM به فایل بدون BOM."""
        f = tmp_dir / "test.tex"
        content = f"سلام{ZWNJ}دنیا"
        f.write_text(content, encoding="utf-8")

        report = ScanReport(
            scan_id="t1",
            timestamp="",
            input_path=str(tmp_dir),
            input_type="directory",
            documents=[
                DocumentEntry(
                    id="d1",
                    path="test.tex",
                    format="latex",
                    encoding="utf-8",
                    has_bom=False,
                ),
            ],
        )

        fixed = fix_encoding_issues(report)
        assert len(fixed) == 1
        assert "test.tex" in fixed[0]

        # بررسی BOM
        raw = f.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"

        # محتوا حفظ شده
        text = f.read_text(encoding="utf-8-sig")
        assert ZWNJ in text

    def test_skip_already_bom(self, tmp_dir: Path) -> None:
        """فایل با BOM نباید دوباره اصلاح شود."""
        f = tmp_dir / "ok.tex"
        f.write_text("سلام", encoding="utf-8-sig")

        report = ScanReport(
            scan_id="t2",
            timestamp="",
            input_path=str(tmp_dir),
            input_type="directory",
            documents=[
                DocumentEntry(
                    id="d1",
                    path="ok.tex",
                    format="latex",
                    encoding="utf-8-sig",
                    has_bom=True,
                ),
            ],
        )

        fixed = fix_encoding_issues(report)
        assert len(fixed) == 0

    def test_skip_nonexistent(self, tmp_dir: Path) -> None:
        """فایل ناموجود باید نادیده گرفته شود."""
        report = ScanReport(
            scan_id="t3",
            timestamp="",
            input_path=str(tmp_dir),
            input_type="directory",
            documents=[
                DocumentEntry(
                    id="d1",
                    path="ghost.tex",
                    format="latex",
                    encoding="utf-8",
                    has_bom=False,
                ),
            ],
        )

        fixed = fix_encoding_issues(report)
        assert len(fixed) == 0

    def test_zwnj_preserved_after_fix(self, tmp_dir: Path) -> None:
        """نیم‌فاصله بعد از افزودن BOM حفظ شود."""
        f = tmp_dir / "zwnj.tex"
        content = f"می{ZWNJ}خواهیم کتاب{ZWNJ}ها را بخوانیم."
        f.write_text(content, encoding="utf-8")

        zwnj_before = content.count(ZWNJ)

        report = ScanReport(
            scan_id="t4",
            timestamp="",
            input_path=str(tmp_dir),
            input_type="directory",
            documents=[
                DocumentEntry(
                    id="d1",
                    path="zwnj.tex",
                    format="latex",
                    encoding="utf-8",
                    has_bom=False,
                ),
            ],
        )

        fix_encoding_issues(report)

        text_after = f.read_text(encoding="utf-8-sig")
        zwnj_after = text_after.count(ZWNJ)

        assert zwnj_after == zwnj_before


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Utility Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestUtilities:
    """تست ابزارهای کمکی."""

    def test_has_pattern_math(self) -> None:
        """تشخیص فرمول ریاضی."""
        import re
        patterns = [re.compile(r"\$[^$]+\$")]
        assert _has_pattern("فرمول $x^2$", patterns) is True
        assert _has_pattern("بدون فرمول", patterns) is False

    def test_guess_mime_png(self) -> None:
        """MIME تصویر PNG."""
        assert _guess_mime("fig/img.png", "image") == "image/png"

    def test_guess_mime_bib(self) -> None:
        """MIME فایل bib."""
        assert _guess_mime("refs.bib", "metadata") == "bibliography"

    def test_guess_mime_unknown(self) -> None:
        """MIME فایل ناشناخته."""
        result = _guess_mime("data.xyz", "unknown")
        assert isinstance(result, str)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Class Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDataClasses:
    """تست ساختار داده‌ها."""

    def test_document_entry_defaults(self) -> None:
        """مقادیر پیش‌فرض DocumentEntry."""
        doc = DocumentEntry(
            id="d1", path="test.tex", format="latex",
        )
        assert doc.role == "standalone"
        assert doc.parent is None
        assert doc.dependencies == []
        assert doc.has_math is False
        assert doc.has_bom is False

    def test_scan_warning_fields(self) -> None:
        """فیلدهای ScanWarning."""
        w = ScanWarning(
            level="warning",
            file="test.tex",
            message="بدون BOM",
            suggestion="افزودن BOM",
        )
        assert w.level == "warning"
        assert w.suggestion == "افزودن BOM"

    def test_asset_info_fields(self) -> None:
        """فیلدهای AssetInfo."""
        a = AssetInfo(
            path="img.png",
            type="image/png",
            size_bytes=1024,
            referenced_by=["doc_001"],
        )
        assert a.size_bytes == 1024
        assert len(a.referenced_by) == 1

    def test_scan_report_cleanup_no_temp(self) -> None:
        """cleanup بدون temp نباید خطا بدهد."""
        r = ScanReport(
            scan_id="t",
            timestamp="",
            input_path="/test",
            input_type="file",
        )
        r.cleanup()  # نباید خطا بدهد


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Import Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestImports:
    """تست اینکه importها درست کار کنند."""

    def test_import_from_scanner_module(self) -> None:
        """import مستقیم از scanner.py."""
        from formatforge.core.scanner.scanner import (
            Scanner,
            ScanReport,
            ScanWarning,
            DocumentEntry,
            AssetInfo,
            fix_encoding_issues,
        )
        assert callable(fix_encoding_issues)

    def test_import_from_package(self) -> None:
        """import از __init__.py پکیج."""
        from formatforge.core.scanner import (
            Scanner,
            ScanReport,
            ScanWarning,
            DocumentEntry,
            AssetInfo,
            fix_encoding_issues,
        )
        assert callable(fix_encoding_issues)

    def test_previous_imports_intact(self) -> None:
        """importهای قبلی همچنان کار کنند."""
        from formatforge.core.scanner import (
            detect_format,
            detect_encoding,
            detect_language,
            analyze_directory,
            extract_archive,
            is_archive,
            cleanup_temp,
        )
        assert callable(detect_format)
        assert callable(analyze_directory)
        assert callable(extract_archive)

    def test_scan_command_import(self) -> None:
        """import دستور scan."""
        from formatforge.cli.commands.scan import scan
        assert callable(scan)
