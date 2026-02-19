"""
FormatForge - LaTeX Book Converter — S09-C1
تبدیل‌گر کتاب چندفصلی LaTeX

Handles multi-chapter LaTeX books:
  1. Detect book structure (single file with \\chapter or multi-file with \\input)
  2. Split into per-chapter MDX files
  3. Generate _series.json with chapter metadata
  4. Fix cross-chapter references
  5. Manage shared vs per-chapter assets

قواعد حیاتی:
- ZWNJ (U+200C) هرگز حذف نشود
- هر فصل یک فایل MDX مجزا
- ارجاعات بین فصل‌ها اصلاح شوند
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from formatforge.core.converters.base import (
    ConversionContext,
    ConversionError,
    DocumentConversionResult,
)
from formatforge.core.converters.latex_parser import (
    ZWNJ,
    CommandNode,
    EnvironmentNode,
    LatexDocument,
    LatexNode,
    LatexParser,
    MathNode,
    TextNode,
    has_persian,
)
from formatforge.core.converters.latex_to_mdx import (
    LaTeXToMDXConverter,
    _ConverterState,
    _detect_direction,
    _detect_language,
    _generate_frontmatter,
    _generate_slug,
    convert_nodes,
)

logger = logging.getLogger("formatforge.converters.latex_book")

# ─── Constants ────────────────────────────────────
_SLUG_UNSAFE = re.compile(r"[^a-z0-9]+")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ChapterInfo:
    """اطلاعات یک فصل."""
    order: int
    title: str
    slug: str
    nodes: list[LatexNode] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    mdx_content: str = ""


@dataclass
class BookStructure:
    """ساختار کتاب."""
    title: str = ""
    slug: str = ""
    author: str = ""
    date: str = ""
    lang: str = "fa"
    chapters: list[ChapterInfo] = field(default_factory=list)
    bibliography_entries: list[dict[str, str]] = field(default_factory=list)


@dataclass
class BookConversionResult:
    """نتیجه تبدیل کتاب."""
    status: str = "processing"
    error_message: str = ""
    book_slug: str = ""
    chapter_results: list[DocumentConversionResult] = field(default_factory=list)
    series_json_path: Optional[str] = None
    total_chapters: int = 0
    duration_seconds: float = 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LaTeXBookConverter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LaTeXBookConverter:
    """
    تبدیل‌گر کتاب چندفصلی LaTeX.
    Converts multi-chapter LaTeX books to per-chapter MDX files.

    Supports:
    - Single .tex file with multiple \\chapter commands
    - Multi-file project with main.tex + \\input{chapter_n}
    - Cross-chapter reference resolution
    - _series.json generation
    """

    def __init__(self, config: Any = None) -> None:
        self.config = config
        self._parser = LatexParser()
        self._converter = LaTeXToMDXConverter(config)

    # ─── Detection ────────────────────────

    def is_book(self, file_path: Path) -> bool:
        """
        تشخیص کتاب بودن فایل LaTeX.
        Returns True if the file is a book (has \\chapter commands or documentclass book).
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")[:5000]
            is_book_class = bool(re.search(
                r"\\documentclass.*\{book\}", content
            ))
            has_chapters = content.count(r"\chapter") >= 2
            has_inputs = bool(re.search(r"\\(?:input|include)\{", content))
            return is_book_class or has_chapters or (has_inputs and r"\chapter" in content)
        except OSError:
            return False

    def detect_structure(self, file_path: Path) -> str:
        """
        تشخیص نوع ساختار کتاب.
        Returns "single" (all in one file) or "multi" (\\input-based).
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"\\(?:input|include)\{", content):
                return "multi"
            return "single"
        except OSError:
            return "single"

    # ─── Parsing ──────────────────────────

    def parse_book(self, file_path: Path) -> BookStructure:
        """
        تحلیل ساختار کتاب LaTeX.
        Parse book structure and split into chapters.
        """
        structure_type = self.detect_structure(file_path)

        if structure_type == "multi":
            doc = self._parser.parse_with_inputs(file_path)
        else:
            doc = self._parser.parse_file(file_path)

        book = BookStructure()

        # Extract book-level metadata from preamble
        preamble = doc.preamble
        book.title = preamble.title or file_path.stem
        book.slug = _generate_slug(book.title)
        book.author = preamble.author or ""
        book.lang = "fa" if preamble.fonts.is_xepersian else _detect_language(
            " ".join(n.content for n in doc.body if isinstance(n, TextNode))
        )

        # Date
        date_raw = preamble.date or ""
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", date_raw)
        if date_match:
            book.date = date_match.group()
        elif re.match(r"\d{4}$", date_raw.strip()):
            book.date = f"{date_raw.strip()}-01-01"
        else:
            book.date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Split nodes into chapters
        book.chapters = self._split_chapters(doc)

        return book

    def _split_chapters(self, doc: LatexDocument) -> list[ChapterInfo]:
        """
        تقسیم گره‌های body به فصل‌ها.
        Split body nodes at \\chapter commands.
        """
        chapters: list[ChapterInfo] = []
        current_nodes: list[LatexNode] = []
        current_title = ""
        order = 0

        for node in doc.body:
            if isinstance(node, CommandNode) and node.name == "chapter":
                # Save previous chapter (if any content)
                if current_title and current_nodes:
                    slug = self._chapter_slug(order, current_title)
                    chapters.append(ChapterInfo(
                        order=order,
                        title=current_title,
                        slug=slug,
                        nodes=current_nodes,
                    ))
                    order += 1

                current_title = node.args[0] if node.args else f"Chapter {order + 1}"
                current_nodes = []
            else:
                current_nodes.append(node)

        # Save last chapter
        if current_title and current_nodes:
            slug = self._chapter_slug(order, current_title)
            chapters.append(ChapterInfo(
                order=order,
                title=current_title,
                slug=slug,
                nodes=current_nodes,
            ))

        # If no chapters found, treat entire body as one chapter
        if not chapters and doc.body:
            title = doc.preamble.title or "Document"
            chapters.append(ChapterInfo(
                order=0,
                title=title,
                slug=_generate_slug(title),
                nodes=doc.body,
            ))

        return chapters

    def _chapter_slug(self, order: int, title: str) -> str:
        """Generate slug for a chapter: 00-introduction."""
        base = _generate_slug(title)
        if not base or base.startswith("doc-"):
            # Use order-based slug for Persian titles
            base = f"chapter-{order + 1}"
        return f"{order:02d}-{base}"

    # ─── Conversion ───────────────────────

    def convert_book(
        self,
        file_path: Path,
        output_dir: Path,
        config: Any = None,
    ) -> BookConversionResult:
        """
        تبدیل کتاب LaTeX به فایل‌های MDX مجزا.
        Convert entire book to per-chapter MDX files.
        """
        start = time.time()
        result = BookConversionResult()

        try:
            # 1. Parse book structure
            book = self.parse_book(file_path)
            result.book_slug = book.slug
            result.total_chapters = len(book.chapters)

            # 2. Create output directory
            book_dir = output_dir / book.slug
            book_dir.mkdir(parents=True, exist_ok=True)

            # 3. Convert each chapter
            for chapter in book.chapters:
                ch_result = self._convert_chapter(
                    chapter, book, file_path, book_dir,
                )
                result.chapter_results.append(ch_result)

            # 4. Fix cross-chapter references
            self._fix_cross_references(book, book_dir)

            # 5. Generate _series.json
            series_path = book_dir / "_series.json"
            series_data = self._generate_series_json(book)
            series_path.write_text(
                json.dumps(series_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            result.series_json_path = str(series_path)

            # Check overall status
            failed = [r for r in result.chapter_results if r.status != "success"]
            if failed:
                result.status = "partial"
                result.error_message = f"{len(failed)} of {len(book.chapters)} chapters failed"
            else:
                result.status = "success"

        except Exception as exc:
            result.status = "failed"
            result.error_message = str(exc)
            logger.exception("خطا در تبدیل کتاب %s", file_path.name)

        finally:
            result.duration_seconds = round(time.time() - start, 3)

        return result

    def _convert_chapter(
        self,
        chapter: ChapterInfo,
        book: BookStructure,
        source_path: Path,
        output_dir: Path,
    ) -> DocumentConversionResult:
        """Convert a single chapter to MDX."""
        result = DocumentConversionResult(
            document_id=chapter.slug,
            source_path=str(source_path),
            status="processing",
        )
        start = time.time()

        try:
            # Create a temporary LatexDocument for this chapter
            from formatforge.core.converters.latex_parser import LatexDocument, PreambleInfo
            chapter_doc = LatexDocument(
                preamble=PreambleInfo(),  # minimal preamble
                body=chapter.nodes,
                source_path=source_path,
            )

            # Convert nodes to MDX body
            conv_state = _ConverterState()
            mdx_body = convert_nodes(chapter.nodes, chapter_doc, conv_state)

            # Collect labels from this chapter
            chapter.labels = conv_state.labels.copy()

            # Build frontmatter
            from formatforge.models.metadata import DocumentMetadata
            lang = book.lang
            direction = _detect_direction(lang)

            metadata = DocumentMetadata(
                title=chapter.title,
                slug=chapter.slug,
                date=book.date,
                lang=lang,
                dir=direction,
                type="chapter",
                tags=[],
                description="",
                math=conv_state.math_block_count > 0 or conv_state.math_inline_count > 0,
                source_format="latex",
                source_file=source_path.name,
            )

            fm_dict = metadata.to_frontmatter_dict()
            fm_dict["series"] = book.slug
            fm_dict["chapterOrder"] = chapter.order
            fm_dict["convertedAt"] = datetime.now(timezone.utc).isoformat()
            frontmatter_str = _generate_frontmatter(fm_dict)

            # Generate imports
            from formatforge.core.converters.jsx_utils import generate_imports
            imports = generate_imports(mdx_body)

            # Clean up excessive blank lines
            mdx_body = re.sub(r"\n{4,}", "\n\n\n", mdx_body)

            # Assemble MDX
            parts: list[str] = [frontmatter_str, ""]
            if imports:
                parts.append(imports)
                parts.append("")
            parts.append(mdx_body.strip())
            parts.append("")
            mdx_content = "\n".join(parts)

            chapter.mdx_content = mdx_content

            # Write output
            output_path = output_dir / f"{chapter.slug}.mdx"
            output_path.write_text(
                "\ufeff" + mdx_content, encoding="utf-8"
            )

            result.status = "success"
            result.output_path = str(output_path)
            result.output_bytes = len(mdx_content.encode("utf-8"))
            result.quality.math_block_count = conv_state.math_block_count
            result.quality.math_inline_count = conv_state.math_inline_count
            result.quality.tables_count = conv_state.table_count
            result.quality.images_count = conv_state.image_count
            result.quality.code_blocks_count = conv_state.code_block_count
            result.quality.headings_count = conv_state.heading_count

            logger.info(
                "فصل %d: %s → %d bytes",
                chapter.order, chapter.slug, result.output_bytes,
            )

        except Exception as exc:
            result.status = "failed"
            result.error_message = str(exc)
            logger.exception("خطا در تبدیل فصل %s", chapter.slug)

        finally:
            result.duration_seconds = round(time.time() - start, 3)

        return result

    def _fix_cross_references(
        self, book: BookStructure, output_dir: Path,
    ) -> None:
        """
        اصلاح ارجاعات بین فصل‌ها.
        Fix cross-chapter references in generated MDX files.
        """
        # Build global label → (chapter_slug, label_id) map
        label_map: dict[str, tuple[str, str]] = {}
        for chapter in book.chapters:
            for label_id, original_label in chapter.labels.items():
                label_map[label_id] = (chapter.slug, label_id)

        # Update each chapter's MDX
        for chapter in book.chapters:
            mdx_path = output_dir / f"{chapter.slug}.mdx"
            if not mdx_path.exists():
                continue

            content = mdx_path.read_text(encoding="utf-8")
            updated = content

            # Replace CrossRef targets with full paths for other chapters
            for label_id, (ch_slug, lid) in label_map.items():
                if ch_slug != chapter.slug:
                    # Cross-chapter reference
                    old_ref = f'target="{label_id}"'
                    new_ref = f'target="/{book.slug}/{ch_slug}#{lid}"'
                    updated = updated.replace(old_ref, new_ref)

            if updated != content:
                mdx_path.write_text(updated, encoding="utf-8")

    def _generate_series_json(self, book: BookStructure) -> dict[str, Any]:
        """
        تولید _series.json.
        Generate series metadata JSON.
        """
        chapters_list = []
        for ch in book.chapters:
            chapters_list.append({
                "order": ch.order,
                "slug": ch.slug,
                "title": ch.title,
            })

        series: dict[str, Any] = {
            "title": book.title,
            "slug": book.slug,
            "author": book.author,
            "lang": book.lang,
            "chapters": chapters_list,
        }

        return series
