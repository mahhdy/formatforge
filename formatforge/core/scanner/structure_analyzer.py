"""
FormatForge - Structure Analyzer
تحلیل ساختار پوشه و پروژه

Analyze directory structure to detect project type,
LaTeX dependencies, markdown collections, and assets.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from formatforge.core.scanner.file_detector import detect_format

logger = logging.getLogger("formatforge.scanner.structure")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants / ثابت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_DOC_EXTENSIONS = frozenset({
    ".tex", ".ltx", ".md", ".mdx", ".markdown",
    ".html", ".htm", ".xhtml", ".docx", ".pdf",
    ".rst", ".rest", ".adoc", ".asciidoc",
    ".ipynb", ".epub",
})

_MEDIA_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".avif", ".bmp", ".tiff", ".tif",
    ".mp4", ".webm", ".mp3", ".wav", ".ogg",
})

_IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".avif", ".bmp",
})

_STYLE_EXTENSIONS = frozenset({
    ".css", ".scss", ".sty", ".cls", ".bst",
})

_META_EXTENSIONS = frozenset({
    ".bib", ".json", ".yaml", ".yml", ".toml", ".xml",
})

_FONT_EXTENSIONS = frozenset({
    ".ttf", ".otf", ".woff", ".woff2",
})

_IGNORE_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".venv",
    "venv", ".tox", ".mypy_cache", ".pytest_cache",
})

# LaTeX patterns
_RE_INPUT = re.compile(r"\\input\{([^}]+)\}")
_RE_INCLUDE = re.compile(r"\\include\{([^}]+)\}")
_RE_BIBLIOGRAPHY = re.compile(r"\\bibliography\{([^}]+)\}")
_RE_BIBRESOURCE = re.compile(r"\\addbibresource\{([^}]+)\}")
_RE_GRAPHICSPATH = re.compile(r"\\graphicspath\{([^}]+)\}")
_RE_INCLUDEGRAPHICS = re.compile(
    r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"
)
_RE_DOCUMENTCLASS = re.compile(
    r"\\documentclass(?:\[[^\]]*\])?\{(\w+)\}"
)
_RE_BEGIN_DOC = re.compile(r"\\begin\{document\}")

# Markdown image: ![alt](path)
_RE_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

# Markdown frontmatter
_RE_MD_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Classes / کلاس‌های داده
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class AssetEntry:
    """اطلاعات یک فایل وابسته."""
    path: str
    category: str
    size_bytes: int = 0
    referenced_by: list[str] = field(default_factory=list)


@dataclass
class DocInfo:
    """اطلاعات یک سند."""
    path: str
    format: str
    role: str = "standalone"
    parent: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)
    images_referenced: list[str] = field(default_factory=list)
    title_hint: Optional[str] = None


@dataclass
class LatexProjectInfo:
    """اطلاعات پروژه LaTeX."""
    main_file: Optional[str] = None
    document_class: Optional[str] = None
    chapters: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    bib_files: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    graphics_paths: list[str] = field(default_factory=list)
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    is_multi_file: bool = False


@dataclass
class StructureAnalysis:
    """نتیجه تحلیل ساختار."""
    structure_type: str
    root_path: str
    documents: list[DocInfo] = field(default_factory=list)
    assets: list[AssetEntry] = field(default_factory=list)
    latex_project: Optional[LatexProjectInfo] = None
    total_files: int = 0
    doc_count: int = 0
    asset_count: int = 0
    primary_format: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# analyze_directory
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_directory(path: str | Path) -> StructureAnalysis:
    """
    تحلیل ساختار پوشه و تعیین نوع پروژه.
    Analyze a directory to determine project structure.
    """
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"پوشه یافت نشد: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"مسیر یک پوشه نیست: {root}")

    all_files = _collect_files(root)
    docs, assets = _categorize_files(root, all_files)

    format_counts: dict[str, int] = {}
    for d in docs:
        format_counts[d.format] = format_counts.get(d.format, 0) + 1
    primary = (
        max(format_counts, key=format_counts.get)  # type: ignore
        if format_counts else None
    )

    latex_info: Optional[LatexProjectInfo] = None
    if primary == "latex":
        latex_info = analyze_latex_project(root)
        docs = _enrich_docs_from_latex(docs, latex_info)

    structure_type = _determine_structure(docs, latex_info, primary)

    logger.info(
        "تحلیل %s: %d سند, %d asset, نوع=%s",
        root.name, len(docs), len(assets), structure_type,
    )

    return StructureAnalysis(
        structure_type=structure_type,
        root_path=str(root),
        documents=docs,
        assets=assets,
        latex_project=latex_info,
        total_files=len(all_files),
        doc_count=len(docs),
        asset_count=len(assets),
        primary_format=primary,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# analyze_latex_project
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_latex_project(path: str | Path) -> LatexProjectInfo:
    """
    تحلیل پروژه LaTeX.
    Analyze a LaTeX project: main file, deps, bibliography.
    """
    root = Path(path).resolve()
    info = LatexProjectInfo()

    tex_files = sorted(root.rglob("*.tex"))
    if not tex_files:
        return info

    # یافتن فایل اصلی
    for tf in tex_files:
        content = _safe_read(tf)
        if _RE_BEGIN_DOC.search(content):
            dc_match = _RE_DOCUMENTCLASS.search(content)
            if dc_match:
                info.main_file = str(tf.relative_to(root))
                info.document_class = dc_match.group(1)
                break

    if not info.main_file:
        for name in ("main.tex", "index.tex", "root.tex"):
            if (root / name).exists():
                info.main_file = name
                break

    if not info.main_file and tex_files:
        info.main_file = str(tex_files[0].relative_to(root))

    # تحلیل وابستگی‌ها
    for tf in tex_files:
        rel = str(tf.relative_to(root))
        content = _safe_read(tf)
        deps: list[str] = []

        for pat in (_RE_INPUT, _RE_INCLUDE):
            for m in pat.finditer(content):
                dep = _normalize_tex_path(m.group(1))
                deps.append(dep)
                info.inputs.append(dep)

        for pat in (_RE_BIBLIOGRAPHY, _RE_BIBRESOURCE):
            for m in pat.finditer(content):
                bib = m.group(1).strip()
                if not bib.endswith(".bib"):
                    bib += ".bib"
                info.bib_files.append(bib)

        for m in _RE_INCLUDEGRAPHICS.finditer(content):
            info.images.append(m.group(1).strip())

        for m in _RE_GRAPHICSPATH.finditer(content):
            paths = re.findall(r"\{([^}]+)\}", m.group(1))
            info.graphics_paths.extend(paths)

        if deps:
            info.dependency_graph[rel] = deps

    # تشخیص فصل‌ها
    if info.main_file:
        main_content = _safe_read(root / info.main_file)
        for pat in (_RE_INPUT, _RE_INCLUDE):
            for m in pat.finditer(main_content):
                ch = _normalize_tex_path(m.group(1))
                if ch not in info.chapters:
                    info.chapters.append(ch)

    info.is_multi_file = len(info.chapters) > 0 or len(info.inputs) > 1
    info.bib_files = sorted(set(info.bib_files))
    info.images = sorted(set(info.images))
    info.inputs = sorted(set(info.inputs))

    return info


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# analyze_markdown_collection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_markdown_collection(path: str | Path) -> list[DocInfo]:
    """
    تحلیل مجموعه فایل‌های Markdown.
    Analyze markdown files: frontmatter, images, links.
    """
    root = Path(path).resolve()
    docs: list[DocInfo] = []

    md_exts = {".md", ".mdx", ".markdown"}
    md_files = sorted(
        f for f in root.rglob("*")
        if f.suffix.lower() in md_exts and f.is_file()
    )

    for mf in md_files:
        rel = str(mf.relative_to(root))
        content = _safe_read(mf)

        # استخراج تصاویر: ![alt](path)
        image_list = _RE_MD_IMAGE.findall(content)

        # استخراج عنوان
        title = _extract_md_title(content)

        docs.append(DocInfo(
            path=rel,
            format="markdown",
            role="standalone",
            images_referenced=image_list,
            title_hint=title,
        ))

    return docs


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# find_assets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def find_assets(path: str | Path) -> list[AssetEntry]:
    """
    یافتن فایل‌های وابسته: تصاویر، فونت‌ها، CSS، bib.
    Find all asset files in a directory tree.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        return []

    assets: list[AssetEntry] = []
    for f in _collect_files(root):
        cat = _get_asset_category(f)
        if cat is not None:
            assets.append(AssetEntry(
                path=str(f.relative_to(root)),
                category=cat,
                size_bytes=f.stat().st_size if f.exists() else 0,
            ))

    return assets


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Internal Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _collect_files(root: Path) -> list[Path]:
    """جمع‌آوری بازگشتی فایل‌ها."""
    result: list[Path] = []
    for item in sorted(root.rglob("*")):
        if item.is_file() and not any(
            p in item.parts for p in _IGNORE_DIRS
        ):
            result.append(item)
    return result


def _get_asset_category(f: Path) -> Optional[str]:
    """دسته‌بندی فایل وابسته (بدون document)."""
    ext = f.suffix.lower()
    if ext in _IMAGE_EXTENSIONS:
        return "image"
    if ext in _MEDIA_EXTENSIONS and ext not in _IMAGE_EXTENSIONS:
        return "media"
    if ext in _STYLE_EXTENSIONS:
        return "style"
    if ext in _META_EXTENSIONS:
        return "metadata"
    if ext in _FONT_EXTENSIONS:
        return "font"
    return None


def _is_document(f: Path) -> bool:
    """آیا فایل یک سند است؟"""
    return f.suffix.lower() in _DOC_EXTENSIONS


def _categorize_files(
    root: Path, files: list[Path],
) -> tuple[list[DocInfo], list[AssetEntry]]:
    """دسته‌بندی فایل‌ها به اسناد و وابسته‌ها."""
    docs: list[DocInfo] = []
    assets: list[AssetEntry] = []

    for f in files:
        rel = str(f.relative_to(root))

        if _is_document(f):
            try:
                fmt = detect_format(f)
            except Exception:
                fmt = "unknown"
            docs.append(DocInfo(path=rel, format=fmt))
        else:
            cat = _get_asset_category(f)
            if cat is not None:
                assets.append(AssetEntry(
                    path=rel,
                    category=cat,
                    size_bytes=f.stat().st_size,
                ))

    return docs, assets


def _determine_structure(
    docs: list[DocInfo],
    latex_info: Optional[LatexProjectInfo],
    primary: Optional[str],
) -> str:
    """تعیین نوع ساختار پروژه."""
    if len(docs) <= 1:
        return "single_doc"

    if latex_info and latex_info.is_multi_file:
        if latex_info.document_class in ("book", "report", "memoir"):
            return "multi_chapter_book"
        if len(latex_info.chapters) >= 2:
            return "multi_chapter_book"

    if primary:
        same_fmt = sum(1 for d in docs if d.format == primary)
        if same_fmt == len(docs) and len(docs) >= 2:
            return "independent_articles"

    formats = {d.format for d in docs}
    if len(formats) >= 2:
        return "related_collection"

    return "independent_articles"


def _enrich_docs_from_latex(
    docs: list[DocInfo],
    info: LatexProjectInfo,
) -> list[DocInfo]:
    """تکمیل اطلاعات اسناد از تحلیل LaTeX."""
    chapter_set = set(info.chapters)
    for doc in docs:
        name_no_ext = Path(doc.path).stem
        if doc.path == info.main_file:
            doc.role = "main_entry"
        elif doc.path in chapter_set or name_no_ext in chapter_set:
            doc.role = "chapter"
            doc.parent = info.main_file
        deps = info.dependency_graph.get(doc.path, [])
        doc.dependencies = deps
    return docs


def _normalize_tex_path(raw: str) -> str:
    """نرمال‌سازی مسیر LaTeX."""
    p = raw.strip()
    if not Path(p).suffix:
        p += ".tex"
    return p.replace("\\", "/")


def _safe_read(path: Path) -> str:
    """خواندن امن فایل متنی."""
    try:
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return ""


def _extract_md_title(content: str) -> Optional[str]:
    """استخراج عنوان از Markdown."""
    fm = _RE_MD_FRONTMATTER.match(content)
    if fm:
        for line in fm.group(1).splitlines():
            stripped = line.strip()
            if stripped.startswith("title:"):
                return stripped.split(":", 1)[1].strip().strip("\"'")

    for line in content.splitlines()[:30]:
        if line.startswith("# ") and not line.startswith("##"):
            return line[2:].strip()

    return None
