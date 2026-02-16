"""
Tests for formatforge.core.scanner.file_detector
تست‌های تشخیص فرمت، encoding و زبان

Uses real fixture files created in tests/fixtures/.
"""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from formatforge.core.scanner.file_detector import (
    DetectionError,
    EncodingInfo,
    LanguageInfo,
    detect_encoding,
    detect_format,
    detect_language,
)


ZWNJ = "\u200c"
FIXTURES = Path(__file__).parent / "fixtures"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixture file generators / تولید فایل‌های نمونه
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture(scope="session", autouse=True)
def create_fixtures():
    """ساخت فایل‌های نمونه واقعی برای تست."""
    FIXTURES.mkdir(parents=True, exist_ok=True)

    # --- LaTeX ---
    (FIXTURES / "sample.tex").write_text(
        "\\documentclass{article}\n"
        "\\usepackage{xepersian}\n"
        "\\begin{document}\n"
        f"سلام{ZWNJ}دنیا\n"
        "\\section{مقدمه}\n"
        "متن فارسی با $x^2$ فرمول.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    # --- LaTeX with BOM ---
    bom_content = (
        "\ufeff\\documentclass{book}\n"
        "\\begin{document}\n"
        f"نیم{ZWNJ}فاصله\n"
        "\\end{document}\n"
    )
    (FIXTURES / "bom_sample.tex").write_bytes(
        bom_content.encode("utf-8")
    )

    # --- HTML ---
    (FIXTURES / "sample.html").write_text(
        '<!DOCTYPE html>\n'
        '<html lang="fa" dir="rtl">\n'
        '<head><title>تست</title></head>\n'
        '<body>\n'
        f'<p>سلام{ZWNJ}دنیا</p>\n'
        '</body>\n</html>\n',
        encoding="utf-8",
    )

    # --- Markdown ---
    (FIXTURES / "sample.md").write_text(
        "---\ntitle: تست\n---\n\n"
        "# عنوان اصلی\n\n"
        f"متن فارسی با نیم{ZWNJ}فاصله.\n\n"
        "- آیتم ۱\n- آیتم ۲\n\n"
        "```python\nprint('hello')\n```\n",
        encoding="utf-8",
    )

    # --- RST ---
    (FIXTURES / "sample.rst").write_text(
        "عنوان اصلی\n"
        "==========\n\n"
        ".. note::\n"
        "   این یک نکته است.\n\n"
        "متن :math:`x^2` با فرمول.\n",
        encoding="utf-8",
    )

    # --- AsciiDoc ---
    (FIXTURES / "sample.adoc").write_text(
        "= عنوان اصلی\n"
        ":author: نویسنده\n\n"
        "== بخش اول\n\n"
        "[NOTE]\n====\nیک نکته\n====\n\n"
        "[source,python]\n----\nprint('hi')\n----\n",
        encoding="utf-8",
    )

    # --- Jupyter Notebook ---
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"language_info": {"name": "python"}},
        "cells": [
            {"cell_type": "markdown", "source": ["# تست"], "metadata": {}},
            {
                "cell_type": "code",
                "source": ["print('hello')"],
                "metadata": {},
                "outputs": [],
                "execution_count": None,
            },
        ],
    }
    (FIXTURES / "sample.ipynb").write_text(
        json.dumps(notebook, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # --- PDF (minimal magic bytes) ---
    (FIXTURES / "sample.pdf").write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\n"
    )

    # --- DOCX (minimal ZIP) ---
    docx_path = FIXTURES / "sample.docx"
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        zf.writestr("word/document.xml", "<w:document/>")

    # --- EPUB (minimal ZIP) ---
    epub_path = FIXTURES / "sample.epub"
    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", '<?xml version="1.0"?><c/>')

    # --- Pure English ---
    (FIXTURES / "english.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Hello world. This is a test document.\n"
        "\\section{Introduction}\n"
        "Some English text here.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    # --- Mixed language ---
    (FIXTURES / "mixed.md").write_text(
        "# Introduction مقدمه\n\n"
        "This is a mixed document with Persian and English.\n\n"
        f"این یک سند دوزبانه{ZWNJ}ای است.\n"
        "We use both **languages** freely.\n"
        f"ریاضی{ZWNJ}ات و logic.\n",
        encoding="utf-8",
    )

    # --- Empty file ---
    (FIXTURES / "empty.txt").write_text("", encoding="utf-8")

    # --- Windows-1256 encoded ---
    try:
        (FIXTURES / "win1256.txt").write_bytes(
            "سلام دنیا".encode("windows-1256")
        )
    except (UnicodeEncodeError, LookupError):
        (FIXTURES / "win1256.txt").write_text("hello", encoding="utf-8")

    # --- No extension ---
    (FIXTURES / "noext_latex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\nHello\\end{document}\n",
        encoding="utf-8",
    )

    yield
    # cleanup نمی‌کنیم — fixture ها برای بررسی دستی مفیدند


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: detect_format
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDetectFormat:
    """تست‌های تشخیص فرمت فایل."""

    def test_latex(self):
        assert detect_format(FIXTURES / "sample.tex") == "latex"

    def test_latex_with_bom(self):
        assert detect_format(FIXTURES / "bom_sample.tex") == "latex"

    def test_html(self):
        assert detect_format(FIXTURES / "sample.html") == "html"

    def test_markdown(self):
        assert detect_format(FIXTURES / "sample.md") == "markdown"

    def test_rst(self):
        assert detect_format(FIXTURES / "sample.rst") == "rst"

    def test_asciidoc(self):
        assert detect_format(FIXTURES / "sample.adoc") == "asciidoc"

    def test_notebook(self):
        assert detect_format(FIXTURES / "sample.ipynb") == "notebook"

    def test_pdf(self):
        assert detect_format(FIXTURES / "sample.pdf") == "pdf"

    def test_docx(self):
        assert detect_format(FIXTURES / "sample.docx") == "docx"

    def test_epub(self):
        assert detect_format(FIXTURES / "sample.epub") == "epub"

    def test_no_extension_latex(self):
        """فایل بدون پسوند باید با تحلیل محتوا تشخیص داده شود."""
        result = detect_format(FIXTURES / "noext_latex")
        assert result == "latex"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            detect_format("/nonexistent/file.tex")

    def test_directory_raises(self):
        with pytest.raises(DetectionError, match="فایل نیست"):
            detect_format(FIXTURES)

    def test_empty_file(self):
        result = detect_format(FIXTURES / "empty.txt")
        assert isinstance(result, str)

    def test_english_latex(self):
        assert detect_format(FIXTURES / "english.tex") == "latex"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: detect_encoding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDetectEncoding:
    """تست‌های تشخیص encoding."""

    def test_returns_encoding_info(self):
        result = detect_encoding(FIXTURES / "sample.tex")
        assert isinstance(result, EncodingInfo)
        assert result.name
        assert 0.0 <= result.confidence <= 1.0

    def test_bom_detected(self):
        result = detect_encoding(FIXTURES / "bom_sample.tex")
        assert result.has_bom is True
        assert result.name == "utf-8-sig"
        assert result.confidence == 1.0

    def test_utf8_no_bom(self):
        result = detect_encoding(FIXTURES / "sample.tex")
        assert "utf" in result.name.lower() or "ascii" in result.name.lower()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            detect_encoding("/nonexistent.txt")

    def test_pdf_encoding(self):
        result = detect_encoding(FIXTURES / "sample.pdf")
        assert isinstance(result, EncodingInfo)

    def test_confidence_range(self):
        result = detect_encoding(FIXTURES / "sample.md")
        assert 0.0 <= result.confidence <= 1.0

    def test_windows_1256(self):
        result = detect_encoding(FIXTURES / "win1256.txt")
        assert isinstance(result, EncodingInfo)
        assert result.confidence > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: detect_language
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDetectLanguage:
    """تست‌های تشخیص زبان."""

    def test_returns_language_info(self):
        result = detect_language("سلام دنیا")
        assert isinstance(result, LanguageInfo)

    def test_persian(self):
        result = detect_language("سلام دنیا این یک متن فارسی است")
        assert result.primary == "fa"
        assert result.has_persian is True
        assert result.persian_ratio > 0.5

    def test_english(self):
        result = detect_language("Hello world this is English text")
        assert result.primary == "en"
        assert result.has_english is True
        assert result.english_ratio > 0.5

    def test_mixed(self):
        text = "سلام hello دنیا world منطق logic"
        result = detect_language(text)
        assert result.primary == "fa+en"
        assert result.has_persian is True
        assert result.has_english is True

    def test_empty(self):
        result = detect_language("")
        assert result.primary == "unknown"

    def test_whitespace(self):
        result = detect_language("   \n\t  ")
        assert result.primary == "unknown"

    def test_code_stripped(self):
        """بلوک‌های کد نباید روی تشخیص تأثیر بگذارند."""
        text = (
            "متن فارسی\n"
            "```python\n"
            "def hello_world():\n"
            "    return 42\n"
            "```\n"
            "ادامه متن فارسی"
        )
        result = detect_language(text)
        assert result.primary == "fa"

    def test_math_stripped(self):
        """فرمول‌های ریاضی نباید روی تشخیص تأثیر بگذارند."""
        text = (
            f"فرض کنیم $x^2 + y^2 = z^2$ و نیم{ZWNJ}فاصله "
            "$$\\int_0^1 f(x) dx = F(1) - F(0)$$ "
            "پس نتیجه می‌گیریم"
        )
        result = detect_language(text)
        assert result.primary == "fa"
        assert result.has_persian is True

    def test_real_latex_file(self):
        content = (FIXTURES / "sample.tex").read_text(encoding="utf-8")
        result = detect_language(content)
        assert result.has_persian is True

    def test_real_mixed_file(self):
        content = (FIXTURES / "mixed.md").read_text(encoding="utf-8")
        result = detect_language(content)
        assert result.primary == "fa+en"

    def test_real_english_file(self):
        content = (FIXTURES / "english.tex").read_text(encoding="utf-8")
        result = detect_language(content)
        assert result.primary == "en"
        assert result.has_english is True

    def test_persian_ratio_range(self):
        result = detect_language("سلام hello")
        assert 0.0 <= result.persian_ratio <= 1.0
        assert 0.0 <= result.english_ratio <= 1.0

    def test_urls_stripped(self):
        """URL ها نباید زبان انگلیسی تشخیص داده شوند."""
        text = (
            "برای اطلاعات بیشتر به "
            "https://example.com/very/long/english/url "
            "مراجعه کنید."
        )
        result = detect_language(text)
        assert result.primary == "fa"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: integration / یکپارچه
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIntegration:
    """تست‌های یکپارچه: ترکیب سه تابع."""

    def test_full_pipeline_persian_latex(self):
        """تشخیص کامل یک فایل LaTeX فارسی."""
        path = FIXTURES / "sample.tex"

        fmt = detect_format(path)
        enc = detect_encoding(path)
        content = path.read_text(encoding="utf-8")
        lang = detect_language(content)

        assert fmt == "latex"
        assert "utf" in enc.name.lower()
        assert lang.has_persian is True

    def test_full_pipeline_html(self):
        """تشخیص کامل فایل HTML."""
        path = FIXTURES / "sample.html"

        fmt = detect_format(path)
        enc = detect_encoding(path)
        content = path.read_text(encoding="utf-8")
        lang = detect_language(content)

        assert fmt == "html"
        assert enc.name
        assert lang.has_persian is True

    def test_full_pipeline_markdown(self):
        """تشخیص کامل فایل Markdown."""
        path = FIXTURES / "sample.md"

        fmt = detect_format(path)
        enc = detect_encoding(path)
        content = path.read_text(encoding="utf-8")
        lang = detect_language(content)

        assert fmt == "markdown"
        assert enc.name
        assert lang.has_persian is True

    def test_full_pipeline_notebook(self):
        """تشخیص کامل فایل Jupyter."""
        path = FIXTURES / "sample.ipynb"

        fmt = detect_format(path)
        enc = detect_encoding(path)

        assert fmt == "notebook"
        assert enc.name
