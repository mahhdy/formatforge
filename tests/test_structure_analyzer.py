"""
Tests for formatforge.core.scanner.structure_analyzer
تست‌های تحلیل ساختار پوشه و پروژه

Creates realistic project structures in temp directories.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from formatforge.core.scanner.structure_analyzer import (
    AssetEntry,
    DocInfo,
    LatexProjectInfo,
    StructureAnalysis,
    analyze_directory,
    analyze_latex_project,
    analyze_markdown_collection,
    find_assets,
)


ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures / فیکسچرها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture
def tmp(tmp_path: Path) -> Path:
    """پوشه موقت."""
    return tmp_path


@pytest.fixture
def single_latex(tmp: Path) -> Path:
    """پروژه LaTeX تک‌فایلی."""
    tex = tmp / "article.tex"
    tex.write_text(
        "\\documentclass{article}\n"
        "\\usepackage{xepersian}\n"
        "\\begin{document}\n"
        f"\\section{{\u0645\u0642\u062f\u0645\u0647}}\n"
        f"\u0633\u0644\u0627\u0645{ZWNJ}\u062f\u0646\u06cc\u0627\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    return tmp


@pytest.fixture
def multi_chapter_book(tmp: Path) -> Path:
    """پروژه کتاب LaTeX چندفصلی."""
    # main.tex
    (tmp / "main.tex").write_text(
        "\\documentclass{book}\n"
        "\\usepackage{xepersian}\n"
        "\\begin{document}\n"
        "\\input{ch01}\n"
        "\\input{ch02}\n"
        "\\input{appendix}\n"
        "\\bibliography{refs}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    # chapters
    for name, title in [("ch01", "مقدمه"), ("ch02", "منطق"), ("appendix", "پیوست")]:
        (tmp / f"{name}.tex").write_text(
            f"\\chapter{{{title}}}\n"
            f"\u0645\u062a\u0646 {title}\n"
            "\\includegraphics{figures/fig1.png}\n",
            encoding="utf-8",
        )
    # bib
    (tmp / "refs.bib").write_text(
        "@article{ref1, author={Test}, title={Test}, year={2025}}\n",
        encoding="utf-8",
    )
    # figures
    fig_dir = tmp / "figures"
    fig_dir.mkdir()
    (fig_dir / "fig1.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
    (fig_dir / "fig2.svg").write_text("<svg/>", encoding="utf-8")

    return tmp


@pytest.fixture
def independent_articles(tmp: Path) -> Path:
    """مجموعه مقالات مستقل."""
    for i in range(3):
        (tmp / f"article{i+1}.tex").write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            f"Article {i+1} content.\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
    return tmp


@pytest.fixture
def markdown_collection(tmp: Path) -> Path:
    """مجموعه فایل‌های Markdown."""
    (tmp / "intro.md").write_text(
        "---\ntitle: \u0645\u0642\u062f\u0645\u0647\n---\n\n"
        "# \u0645\u0642\u062f\u0645\u0647\n\n"
        f"\u0645\u062a\u0646{ZWNJ}\u0641\u0627\u0631\u0633\u06cc\n\n"
        "![diagram](images/fig1.png)\n",
        encoding="utf-8",
    )
    (tmp / "chapter1.md").write_text(
        "---\ntitle: \u0641\u0635\u0644 \u06f1\n---\n\n"
        "# \u0641\u0635\u0644 \u0627\u0648\u0644\n\n"
        "content here\n",
        encoding="utf-8",
    )
    img_dir = tmp / "images"
    img_dir.mkdir()
    (img_dir / "fig1.png").write_bytes(b"\x89PNG" + b"\x00" * 20)
    return tmp


@pytest.fixture
def mixed_project(tmp: Path) -> Path:
    """پروژه ترکیبی."""
    (tmp / "readme.md").write_text("# Readme\n", encoding="utf-8")
    (tmp / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nHi\n\\end{document}\n",
        encoding="utf-8",
    )
    (tmp / "page.html").write_text(
        "<!DOCTYPE html><html><body>Hi</body></html>\n",
        encoding="utf-8",
    )
    (tmp / "style.css").write_text("body { dir: rtl; }\n", encoding="utf-8")
    (tmp / "logo.png").write_bytes(b"\x89PNG" + b"\x00" * 10)
    return tmp


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: analyze_directory
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAnalyzeDirectory:
    """تست‌های تحلیل پوشه."""

    def test_single_doc(self, single_latex: Path):
        result = analyze_directory(single_latex)
        assert isinstance(result, StructureAnalysis)
        assert result.structure_type == "single_doc"
        assert result.doc_count == 1
        assert result.primary_format == "latex"

    def test_multi_chapter_book(self, multi_chapter_book: Path):
        result = analyze_directory(multi_chapter_book)
        assert result.structure_type == "multi_chapter_book"
        assert result.doc_count >= 4
        assert result.primary_format == "latex"
        assert result.latex_project is not None
        assert result.latex_project.is_multi_file is True

    def test_independent_articles(self, independent_articles: Path):
        result = analyze_directory(independent_articles)
        assert result.structure_type == "independent_articles"
        assert result.doc_count == 3

    def test_mixed_project(self, mixed_project: Path):
        result = analyze_directory(mixed_project)
        assert result.structure_type in (
            "related_collection", "independent_articles"
        )
        assert result.doc_count >= 3
        assert result.asset_count >= 1

    def test_empty_dir(self, tmp: Path):
        result = analyze_directory(tmp)
        assert result.structure_type == "single_doc"
        assert result.doc_count == 0

    def test_not_found(self):
        with pytest.raises(FileNotFoundError):
            analyze_directory("/nonexistent/path")

    def test_not_a_directory(self, single_latex: Path):
        tex = single_latex / "article.tex"
        with pytest.raises(NotADirectoryError):
            analyze_directory(tex)

    def test_has_assets(self, multi_chapter_book: Path):
        result = analyze_directory(multi_chapter_book)
        assert result.asset_count >= 2  # fig1.png + fig2.svg

    def test_total_files(self, multi_chapter_book: Path):
        result = analyze_directory(multi_chapter_book)
        assert result.total_files >= 6


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: analyze_latex_project
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAnalyzeLatexProject:
    """تست‌های تحلیل پروژه LaTeX."""

    def test_finds_main_file(self, multi_chapter_book: Path):
        info = analyze_latex_project(multi_chapter_book)
        assert info.main_file == "main.tex"

    def test_document_class(self, multi_chapter_book: Path):
        info = analyze_latex_project(multi_chapter_book)
        assert info.document_class == "book"

    def test_chapters_found(self, multi_chapter_book: Path):
        info = analyze_latex_project(multi_chapter_book)
        assert len(info.chapters) == 3
        assert "ch01.tex" in info.chapters
        assert "ch02.tex" in info.chapters

    def test_bib_files(self, multi_chapter_book: Path):
        info = analyze_latex_project(multi_chapter_book)
        assert "refs.bib" in info.bib_files

    def test_images_found(self, multi_chapter_book: Path):
        info = analyze_latex_project(multi_chapter_book)
        assert len(info.images) >= 1
        assert "figures/fig1.png" in info.images

    def test_dependency_graph(self, multi_chapter_book: Path):
        info = analyze_latex_project(multi_chapter_book)
        assert "main.tex" in info.dependency_graph
        deps = info.dependency_graph["main.tex"]
        assert "ch01.tex" in deps

    def test_is_multi_file(self, multi_chapter_book: Path):
        info = analyze_latex_project(multi_chapter_book)
        assert info.is_multi_file is True

    def test_single_file_not_multi(self, single_latex: Path):
        info = analyze_latex_project(single_latex)
        assert info.is_multi_file is False

    def test_empty_dir(self, tmp: Path):
        info = analyze_latex_project(tmp)
        assert info.main_file is None
        assert info.is_multi_file is False

    def test_role_assignment(self, multi_chapter_book: Path):
        result = analyze_directory(multi_chapter_book)
        roles = {d.path: d.role for d in result.documents}
        assert roles.get("main.tex") == "main_entry"
        # chapters should have chapter role
        chapter_roles = [
            r for p, r in roles.items()
            if p.startswith("ch")
        ]
        assert all(r == "chapter" for r in chapter_roles)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: analyze_markdown_collection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAnalyzeMarkdownCollection:
    """تست‌های تحلیل مجموعه Markdown."""

    def test_finds_md_files(self, markdown_collection: Path):
        docs = analyze_markdown_collection(markdown_collection)
        assert len(docs) == 2

    def test_extracts_title(self, markdown_collection: Path):
        docs = analyze_markdown_collection(markdown_collection)
        titles = [d.title_hint for d in docs if d.title_hint]
        assert len(titles) >= 1

    def test_extracts_images(self, markdown_collection: Path):
        docs = analyze_markdown_collection(markdown_collection)
        intro = next(d for d in docs if "intro" in d.path)
        assert "images/fig1.png" in intro.images_referenced

    def test_format_is_markdown(self, markdown_collection: Path):
        docs = analyze_markdown_collection(markdown_collection)
        assert all(d.format == "markdown" for d in docs)

    def test_empty_dir(self, tmp: Path):
        docs = analyze_markdown_collection(tmp)
        assert docs == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: find_assets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFindAssets:
    """تست‌های یافتن فایل‌های وابسته."""

    def test_finds_images(self, multi_chapter_book: Path):
        assets = find_assets(multi_chapter_book)
        image_assets = [a for a in assets if a.category == "image"]
        assert len(image_assets) >= 2

    def test_finds_metadata(self, multi_chapter_book: Path):
        assets = find_assets(multi_chapter_book)
        meta = [a for a in assets if a.category == "metadata"]
        assert len(meta) >= 1  # refs.bib

    def test_finds_styles(self, mixed_project: Path):
        assets = find_assets(mixed_project)
        styles = [a for a in assets if a.category == "style"]
        assert len(styles) >= 1  # style.css

    def test_size_bytes(self, multi_chapter_book: Path):
        assets = find_assets(multi_chapter_book)
        for a in assets:
            assert a.size_bytes >= 0

    def test_no_docs_in_assets(self, multi_chapter_book: Path):
        assets = find_assets(multi_chapter_book)
        categories = {a.category for a in assets}
        assert "document" not in categories

    def test_empty_dir(self, tmp: Path):
        assert find_assets(tmp) == []

    def test_not_a_dir(self, single_latex: Path):
        tex = single_latex / "article.tex"
        assert find_assets(tex) == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests: edge cases / موارد مرزی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEdgeCases:
    """تست‌های موارد مرزی."""

    def test_nested_directories(self, tmp: Path):
        """پوشه‌های تودرتو."""
        sub = tmp / "chapters" / "part1"
        sub.mkdir(parents=True)
        (sub / "intro.tex").write_text(
            "\\documentclass{article}\n\\begin{document}\nHi\n\\end{document}\n",
            encoding="utf-8",
        )
        result = analyze_directory(tmp)
        assert result.doc_count >= 1

    def test_git_dir_ignored(self, tmp: Path):
        """پوشه .git نادیده گرفته شود."""
        git_dir = tmp / ".git" / "objects"
        git_dir.mkdir(parents=True)
        (git_dir / "data.bin").write_bytes(b"\x00" * 100)
        (tmp / "readme.md").write_text("# Hi\n", encoding="utf-8")
        result = analyze_directory(tmp)
        assert result.total_files == 1  # only readme.md

    def test_latex_without_begin_document(self, tmp: Path):
        """فایل .sty بدون begin{document}."""
        (tmp / "custom.sty").write_text(
            "\\NeedsTeXFormat{LaTeX2e}\n"
            "\\ProvidesPackage{custom}\n"
            "\\newcommand{\\hi}{Hello}\n",
            encoding="utf-8",
        )
        result = analyze_directory(tmp)
        assert result.doc_count >= 1

    def test_frontmatter_title_extraction(self, tmp: Path):
        """استخراج عنوان از frontmatter."""
        (tmp / "test.md").write_text(
            '---\ntitle: "\u062a\u0633\u062a \u0639\u0646\u0648\u0627\u0646"\n---\n\nContent.\n',
            encoding="utf-8",
        )
        docs = analyze_markdown_collection(tmp)
        assert docs[0].title_hint is not None
