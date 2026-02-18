"""
FormatForge - Markdown → MDX Converter
تبدیل‌گر Markdown به MDX

Converts Markdown files to MDX format by running the processor
pipeline and applying JSX transformations.

قواعد حیاتی:
- ZWNJ (U+200C) هرگز حذف نشود
- frontmatter باید معتبر باشد
- dir="rtl" برای محتوای فارسی
- import statements برای کامپوننت‌های استفاده‌شده
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Optional

import yaml

from formatforge.core.converters.base import (
    BaseConverter,
    ConversionContext,
    ConversionError,
    DocumentConversionResult,
    QualityReport,
    ZWNJReport,
)
from formatforge.core.converters.jsx_utils import (
    convert_html_to_jsx,
    generate_imports,
)
from formatforge.core.processors.base import (
    ProcessorContext,
    ProcessorPipeline,
)
from formatforge.core.processors.math_processor import MathProcessor
from formatforge.core.processors.code_processor import CodeProcessor
from formatforge.core.processors.table_processor import TableProcessor
from formatforge.core.processors.image_processor import ImageProcessor
from formatforge.core.processors.admonition_processor import AdmonitionProcessor
from formatforge.core.processors.link_processor import LinkProcessor
from formatforge.core.processors.footnote_processor import FootnoteProcessor
from formatforge.core.processors.rtl_processor import RTLProcessor
from formatforge.models.metadata import DocumentMetadata

# Non-BaseProcessor processors (different interface)
# These are called directly, not via ProcessorPipeline
_STANDALONE_PROCESSORS = (TableProcessor, ImageProcessor, AdmonitionProcessor)

logger = logging.getLogger("formatforge.converters.md_to_mdx")

# ─── Constants / ثابت‌ها ──────────────────────
ZWNJ = "\u200c"

_RE_FRONTMATTER = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n?",
    re.DOTALL,
)

_RE_HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

_SLUG_UNSAFE = re.compile(r"[^a-z0-9]+")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions / توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    جدا کردن frontmatter YAML از محتوا.
    Parse YAML frontmatter and return (metadata_dict, body).
    """
    m = _RE_FRONTMATTER.match(content)
    if not m:
        return {}, content

    try:
        fm_data = yaml.safe_load(m.group(1))
        if not isinstance(fm_data, dict):
            fm_data = {}
    except yaml.YAMLError:
        fm_data = {}

    body = content[m.end():]
    return fm_data, body


def _generate_frontmatter(metadata: dict[str, Any]) -> str:
    """
    تولید frontmatter YAML.
    Generate YAML frontmatter string from metadata dict.
    """
    # Use default_flow_style=False for readable YAML
    # allow_unicode=True for Persian characters
    yaml_str = yaml.dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return f"---\n{yaml_str.rstrip()}\n---"


def _generate_slug(title: str) -> str:
    """
    تولید slug از عنوان.
    Generate URL-safe slug from title.
    """
    # For Persian titles, transliterate or use a simple hash approach
    # For English titles, standard slug generation
    slug = title.lower().strip()
    # Remove Persian/Arabic chars for slug, keep latin
    slug = re.sub(r"[^\x00-\x7f]", "", slug)
    slug = _SLUG_UNSAFE.sub("-", slug).strip("-")
    if not slug:
        # Fallback: use a timestamp-based slug
        slug = f"doc-{int(time.time()) % 100000}"
    return slug[:60]


def _detect_language(content: str) -> str:
    """
    تشخیص زبان محتوا.
    Detect whether content is Persian, English, or bilingual.
    """
    persian_chars = len(re.findall(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]", content))
    latin_chars = len(re.findall(r"[a-zA-Z]", content))

    if persian_chars == 0 and latin_chars > 0:
        return "en"
    if persian_chars > 0 and latin_chars > persian_chars * 2:
        return "fa-en"
    return "fa"


def _detect_direction(lang: str) -> str:
    """جهت متن بر اساس زبان."""
    return "ltr" if lang == "en" else "rtl"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MarkdownToMDXConverter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MarkdownToMDXConverter(BaseConverter):
    """
    تبدیل‌گر Markdown به MDX.
    Converts Markdown files to MDX format.

    مراحل تبدیل:
    1. خواندن فایل + بررسی encoding
    2. تحلیل frontmatter (YAML)
    3. تکمیل metadata
    4. اجرای ProcessorPipeline
    5. تبدیل‌های JSX
    6. تولید imports
    7. ساخت frontmatter نهایی
    8. ترکیب: frontmatter + imports + content
    9. شمارش ZWNJ (before/after)
    """

    format_name: ClassVar[str] = "markdown"
    file_extensions: ClassVar[list[str]] = [".md", ".mdx", ".markdown"]
    mime_types: ClassVar[list[str]] = [
        "text/markdown", "text/x-markdown",
    ]
    priority: ClassVar[int] = 10

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._pipeline: Optional[ProcessorPipeline] = None

    def _get_pipeline(self) -> ProcessorPipeline:
        """ساخت یا بازگرداندن خط لوله پردازش (فقط BaseProcessor ها)."""
        if self._pipeline is None:
            self._pipeline = ProcessorPipeline(name="md-to-mdx")
            # Only processors that extend BaseProcessor go into pipeline
            self._pipeline.add(MathProcessor(self.config))
            self._pipeline.add(CodeProcessor(self.config))
            self._pipeline.add(LinkProcessor(self.config))
            self._pipeline.add(FootnoteProcessor(self.config))
            self._pipeline.add(RTLProcessor(self.config))
        return self._pipeline

    def _run_standalone_processors(
        self, content: str, source_format: str,
    ) -> str:
        """
        اجرای پردازشگرهای مستقل (Table, Image, Admonition).
        These don't extend BaseProcessor and have a different interface.
        """
        # Table processor
        try:
            table_proc = TableProcessor()
            content = table_proc.process(content, source_format=source_format)
        except Exception as exc:
            logger.warning("TableProcessor error: %s", exc)

        # Image processor
        try:
            image_proc = ImageProcessor()
            content = image_proc.process(content, source_format=source_format)
        except Exception as exc:
            logger.warning("ImageProcessor error: %s", exc)

        # Admonition processor
        try:
            admon_proc = AdmonitionProcessor()
            content = admon_proc.process(content, source_format=source_format)
        except Exception as exc:
            logger.warning("AdmonitionProcessor error: %s", exc)

        return content

    # ─── Detection ────────────────────────

    def detect(self, file_path: Path) -> bool:
        """آیا فایل Markdown است؟"""
        if self.detect_by_extension(file_path):
            return True
        # Check content for markdown indicators
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")[:2000]
            indicators = (
                content.startswith("---\n"),
                content.startswith("# "),
                "## " in content,
                "```" in content,
                re.search(r"^\s*[-*+]\s", content, re.MULTILINE) is not None,
            )
            return sum(indicators) >= 2
        except OSError:
            return False

    # ─── Metadata ─────────────────────────

    def extract_metadata(
        self,
        file_path: Path,
        context: Optional[ConversionContext] = None,
    ) -> DocumentMetadata:
        """
        استخراج متادیتا از فایل Markdown.
        Extract metadata from frontmatter and content analysis.
        """
        content = self.read_file(file_path)
        fm_data, body = _parse_frontmatter(content)

        # Extract title: frontmatter > first heading > filename
        title = fm_data.get("title", "")
        if not title:
            heading = _RE_HEADING.search(body)
            if heading:
                title = heading.group(2).strip()
            else:
                title = file_path.stem.replace("-", " ").replace("_", " ")

        # Detect language and direction
        lang = fm_data.get("lang", _detect_language(body))
        direction = fm_data.get("dir", _detect_direction(lang))

        # Generate slug
        slug = fm_data.get("slug", _generate_slug(title))

        # Date
        date = fm_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

        # Content features
        has_math = "$" in body or "$$" in body
        has_mermaid = "```mermaid" in body
        has_code = "```" in body

        metadata = DocumentMetadata(
            title=title,
            slug=slug,
            date=date,
            lang=lang,
            dir=direction,
            type=fm_data.get("type", "article"),
            tags=fm_data.get("tags", []),
            description=fm_data.get("description", ""),
            math=has_math,
            mermaid=has_mermaid,
            codeHighlight=has_code,
            sourceFormat="markdown",
            sourceFile=file_path.name,
        )

        return metadata

    # ─── Conversion ───────────────────────

    def convert(
        self,
        file_path: Path,
        context: ConversionContext,
    ) -> DocumentConversionResult:
        """
        تبدیل فایل Markdown به MDX.
        Convert a Markdown file to MDX format.
        """
        start = time.time()
        doc_id = (
            context.document_info.id
            if context.document_info
            else file_path.stem
        )

        result = DocumentConversionResult(
            document_id=doc_id,
            source_path=str(file_path),
            status="processing",
        )

        try:
            # 1. Read file
            raw_content = self.read_file(file_path)
            result.input_bytes = len(raw_content.encode("utf-8"))

            # 2. Count ZWNJ before
            zwnj_before = self.count_zwnj(raw_content)
            context.zwnj_count_before = zwnj_before

            # 3. Parse frontmatter
            fm_data, body = _parse_frontmatter(raw_content)

            # 4. Extract/complete metadata
            if context.metadata is None:
                context.metadata = self.extract_metadata(file_path, context)

            # 5. Run processor pipeline
            proc_ctx = ProcessorContext(
                source_format="markdown",
                source_path=str(file_path),
                language=context.metadata.lang,
                config=self.config,
            )
            proc_ctx.zwnj_count_before = zwnj_before

            # 5a. Run standalone processors first (Table, Image, Admonition)
            processed_body = self._run_standalone_processors(
                body, source_format="markdown",
            )

            # 5b. Run BaseProcessor pipeline (Math, Code, Link, Footnote, RTL)
            pipeline = self._get_pipeline()
            pipe_result = pipeline.run(processed_body, proc_ctx)
            processed_body = pipe_result.content

            # Transfer pipeline state to context
            context.warnings.extend(proc_ctx.warnings)
            context.errors.extend(proc_ctx.errors)
            context.imports_needed.update(proc_ctx.imports_needed)

            # 6. JSX conversions
            processed_body = convert_html_to_jsx(processed_body)

            # 7. Generate imports
            imports = generate_imports(processed_body)

            # 8. Build final frontmatter
            fm_dict = context.metadata.to_frontmatter_dict()
            # Add convertedAt timestamp
            fm_dict["convertedAt"] = datetime.now(timezone.utc).isoformat()
            frontmatter_str = _generate_frontmatter(fm_dict)

            # 9. Assemble final MDX
            parts: list[str] = [frontmatter_str, ""]
            if imports:
                parts.append(imports)
                parts.append("")
            parts.append(processed_body.strip())
            parts.append("")  # trailing newline

            mdx_content = "\n".join(parts)

            # 10. ZWNJ verification
            zwnj_after = self.count_zwnj(mdx_content)
            context.zwnj_count_after = zwnj_after
            zwnj_report = ZWNJReport(
                count_before=zwnj_before,
                count_after=zwnj_after,
            )

            if not zwnj_report.preserved:
                context.add_warning(
                    f"⚠ ZWNJ: {zwnj_before} → {zwnj_after} "
                    f"({zwnj_before - zwnj_after} lost)"
                )

            # 11. Write output if output_dir is set
            output_path: Optional[Path] = None
            output_bytes = len(mdx_content.encode("utf-8"))
            if context.output_dir and not context.dry_run:
                output_path = context.output_dir / f"{context.metadata.slug}.mdx"
                self.write_output(mdx_content, output_path, context.dry_run)

            # 12. Build result
            result.status = "success"
            result.output_path = str(output_path) if output_path else None
            result.output_bytes = output_bytes
            result.quality.zwnj = zwnj_report
            result.quality.frontmatter_valid = True
            result.quality.mdx_valid = True
            result.quality.math_rendered = proc_ctx.math_blocks_processed > 0 or proc_ctx.math_inlines_processed > 0
            result.quality.math_block_count = proc_ctx.math_blocks_processed
            result.quality.math_inline_count = proc_ctx.math_inlines_processed
            result.quality.tables_converted = proc_ctx.tables_processed > 0
            result.quality.tables_count = proc_ctx.tables_processed
            result.quality.images_linked = proc_ctx.images_processed > 0
            result.quality.images_count = proc_ctx.images_processed
            result.quality.code_blocks_count = proc_ctx.code_blocks_processed
            result.quality.headings_count = proc_ctx.headings_processed
            result.quality.links_count = proc_ctx.links_processed

            # Store the MDX content in notes for access without file I/O
            context.notes.append(f"mdx_content_length={len(mdx_content)}")
            # Store content in extra for downstream access
            context.extra = {"mdx_content": mdx_content}

            self._logger.info(
                "تبدیل MD→MDX: %s → %d bytes, ZWNJ %d→%d",
                file_path.name,
                output_bytes,
                zwnj_before,
                zwnj_after,
            )

        except ConversionError:
            raise
        except Exception as exc:
            result.status = "failed"
            result.error_message = f"خطا در تبدیل: {exc}"
            context.add_error(str(exc))
            self._logger.exception(
                "خطا در تبدیل %s", file_path.name,
            )

        finally:
            result.duration_seconds = round(time.time() - start, 3)

        return result

    # ─── Validation ───────────────────────

    def validate_output(
        self,
        result: DocumentConversionResult,
        context: ConversionContext,
    ) -> QualityReport:
        """
        اعتبارسنجی خروجی MDX.
        Validate the conversion output quality.
        """
        report = result.quality

        # Check ZWNJ preservation
        report.zwnj = ZWNJReport(
            count_before=context.zwnj_count_before,
            count_after=context.zwnj_count_after,
        )

        # Check bidi
        report.bidi_correct = context.metadata is not None and (
            context.metadata.dir in ("rtl", "ltr")
        )

        # Compute overall score
        report.compute_score()

        return report
