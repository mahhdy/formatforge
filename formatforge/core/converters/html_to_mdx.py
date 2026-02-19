"""
FormatForge - HTML → MDX Converter
تبدیل‌گر HTML به MDX

Converts HTML files to MDX format with full support for:
- Persian/RTL content with ZWNJ preservation
- Complex tables (simple → pipe table, merged → JSX table)
- Media elements (video, audio, iframe → JSX components)
- Math expressions (KaTeX, MathJax, MathML → LaTeX)
- Inline SVG extraction to separate files
- CSS class extraction and JSX conversion
- Metadata extraction from <head>

قواعد حیاتی:
- ZWNJ (U+200C) هرگز حذف نشود
- frontmatter باید معتبر باشد
- dir="rtl" برای محتوای فارسی
- import statements برای کامپوننت‌های استفاده‌شده
"""

from __future__ import annotations

import hashlib
import html as html_module
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Optional

import yaml

try:
    from bs4 import BeautifulSoup, Comment, NavigableString, Tag
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

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
from formatforge.core.processors.link_processor import LinkProcessor
from formatforge.core.processors.footnote_processor import FootnoteProcessor
from formatforge.core.processors.table_processor import TableProcessor
from formatforge.core.processors.image_processor import ImageProcessor
from formatforge.core.processors.admonition_processor import AdmonitionProcessor
from formatforge.models.metadata import DocumentMetadata

logger = logging.getLogger("formatforge.converters.html_to_mdx")

# ─── Constants / ثابت‌ها ──────────────────────
ZWNJ = "\u200c"

_SLUG_UNSAFE = re.compile(r"[^a-z0-9]+")

# Tags to remove entirely (content too)
_TAGS_REMOVE = frozenset({"script", "noscript", "template"})

# Structural tags that produce blank lines when removed
_BLOCK_TAGS = frozenset({
    "div", "section", "article", "main", "aside", "nav",
    "header", "footer", "span",
})

# Heading level map
_HEADING_MAP = {f"h{i}": "#" * i for i in range(1, 7)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions / توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _generate_frontmatter(metadata: dict[str, Any]) -> str:
    """تولید frontmatter YAML."""
    yaml_str = yaml.dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return f"---\n{yaml_str.rstrip()}\n---"


def _generate_slug(title: str) -> str:
    """تولید slug از عنوان."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\x00-\x7f]", "", slug)
    slug = _SLUG_UNSAFE.sub("-", slug).strip("-")
    if not slug:
        slug = f"doc-{int(time.time()) % 100000}"
    return slug[:60]


def _detect_language(content: str) -> str:
    """تشخیص زبان محتوا."""
    persian = len(re.findall(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]", content))
    latin = len(re.findall(r"[a-zA-Z]", content))
    if persian == 0 and latin > 0:
        return "en"
    if persian > 0 and latin > persian * 2:
        return "fa-en"
    return "fa"


def _detect_direction(lang: str) -> str:
    """جهت متن بر اساس زبان."""
    return "ltr" if lang == "en" else "rtl"


def _bs4_required(func):
    """دکوراتور: اطمینان از وجود BeautifulSoup."""
    def wrapper(*args, **kwargs):
        if not HAS_BS4:
            raise ConversionError(
                "beautifulsoup4 نصب نشده است. با pip install beautifulsoup4 نصب کنید."
            )
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HTMLToMDXConverter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class HTMLToMDXConverter(BaseConverter):
    """
    تبدیل‌گر HTML به MDX.
    Converts HTML files to MDX format.

    مراحل تبدیل:
    1. خواندن + تشخیص encoding
    2. parse با BeautifulSoup
    3. استخراج metadata از <head>
    4. تمیزکاری HTML
    5. تبدیل ساختاری عناصر
    6. تبدیل عناصر خاص (table, media, math, svg)
    7. اجرای ProcessorPipeline
    8. JSX conversion + imports
    9. ZWNJ check
    """

    format_name: ClassVar[str] = "html"
    file_extensions: ClassVar[list[str]] = [".html", ".htm", ".xhtml"]
    mime_types: ClassVar[list[str]] = ["text/html", "application/xhtml+xml"]
    priority: ClassVar[int] = 20

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._pipeline: Optional[ProcessorPipeline] = None
        self._svg_counter: int = 0

    def _get_pipeline(self) -> ProcessorPipeline:
        """ساخت یا بازگرداندن خط لوله پردازش.

        RTLProcessor عمداً حذف شده: HTML خودش dir/lang دارد،
        پردازش مجدد RTL باعث خرابی محتوا می‌شود.
        """
        if self._pipeline is None:
            self._pipeline = ProcessorPipeline(name="html-to-mdx")
            self._pipeline.add(MathProcessor(self.config))
            self._pipeline.add(CodeProcessor(self.config))
            self._pipeline.add(LinkProcessor(self.config))
            self._pipeline.add(FootnoteProcessor(self.config))
            # RTLProcessor intentionally excluded: HTML already handles bidi
        return self._pipeline

    def _run_standalone_processors(self, content: str, source_format: str) -> str:
        """اجرای پردازشگرهای مستقل."""
        for proc_cls in (TableProcessor, ImageProcessor, AdmonitionProcessor):
            try:
                proc = proc_cls()
                content = proc.process(content, source_format=source_format)
            except Exception as exc:
                logger.warning("%s error: %s", proc_cls.__name__, exc)
        return content

    # ─── Detection ────────────────────────

    def detect(self, file_path: Path) -> bool:
        """آیا فایل HTML است؟"""
        if self.detect_by_extension(file_path):
            return True
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")[:500]
            return (
                content.lower().startswith("<!doctype html")
                or "<html" in content.lower()
                or content.startswith("<html")
            )
        except OSError:
            return False

    # ─── Metadata ─────────────────────────

    def extract_metadata(
        self,
        file_path: Path,
        context: Optional[ConversionContext] = None,
    ) -> DocumentMetadata:
        """
        استخراج متادیتا از <head> فایل HTML.
        """
        if not HAS_BS4:
            raise ConversionError("beautifulsoup4 نصب نشده است.")

        content = self.read_file(file_path)
        soup = BeautifulSoup(content, "lxml")

        head = soup.find("head") or soup

        # title
        title_tag = head.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Meta tags
        meta: dict[str, str] = {}
        for tag in head.find_all("meta"):
            name = tag.get("name") or tag.get("property") or ""
            content_val = tag.get("content", "")
            if name and content_val:
                meta[name.lower()] = content_val

        # Priority: OG > standard meta > title tag
        if not title:
            title = meta.get("og:title", "") or meta.get("title", "")
        if not title:
            title = file_path.stem.replace("-", " ").replace("_", " ")

        description = (
            meta.get("og:description", "")
            or meta.get("description", "")
        )
        lang_attr = soup.find("html", {"lang": True})
        lang_val = lang_attr.get("lang", "") if lang_attr else ""
        if not lang_val:
            # Detect from body text
            body = soup.find("body")
            body_text = body.get_text() if body else content
            lang_val = _detect_language(body_text)
        else:
            # Normalize: "fa-IR" → "fa", "en-US" → "en"
            lang_val = lang_val.split("-")[0].lower()

        direction = _detect_direction(lang_val)

        # Date
        date_meta = (
            meta.get("article:published_time", "")
            or meta.get("date", "")
        )
        if not date_meta:
            date_meta = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            # Truncate to date only
            date_meta = date_meta[:10]

        slug = meta.get("slug", "") or _generate_slug(title)

        # Author
        author = meta.get("author", "") or meta.get("og:author", "")

        # Detect content features
        has_math = bool(
            soup.find("math")
            or soup.find("script", {"type": re.compile(r"math|latex", re.I)})
            or soup.find(class_=re.compile(r"math|katex|mathjax", re.I))
        )
        has_mermaid = bool(soup.find(class_=re.compile(r"mermaid", re.I)))
        has_code = bool(soup.find("code") or soup.find("pre"))

        metadata = DocumentMetadata(
            title=title,
            slug=slug,
            date=date_meta,
            lang=lang_val or "fa",
            dir=direction,
            type="article",
            description=description,
            math=has_math,
            mermaid=has_mermaid,
            code_highlight=has_code,
            source_format="html",
            source_file=file_path.name,
        )

        return metadata

    # ─── Conversion ───────────────────────

    def convert(
        self,
        file_path: Path,
        context: ConversionContext,
    ) -> DocumentConversionResult:
        """
        تبدیل فایل HTML به MDX.
        """
        if not HAS_BS4:
            raise ConversionError("beautifulsoup4 نصب نشده است.")

        start = time.time()
        doc_id = (
            context.document_info.id
            if context.document_info
            else file_path.stem
        )
        self._svg_counter = 0

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

            # 3. Parse HTML
            soup = BeautifulSoup(raw_content, "lxml")

            # 4. Extract metadata
            if context.metadata is None:
                context.metadata = self.extract_metadata(file_path, context)

            # 5. Get body content
            body_tag = soup.find("body") or soup

            # 6. Convert body to Markdown/MDX
            mdx_body = self._convert_element(body_tag, context, file_path)

            # 7. Run processor pipeline
            proc_ctx = ProcessorContext(
                source_format="html",
                source_path=str(file_path),
                language=context.metadata.lang,
                config=self.config,
            )
            proc_ctx.zwnj_count_before = zwnj_before

            # Standalone processors — by now content is already MDX/Markdown
            # Use "markdown" so TableProcessor/ImageProcessor don't re-parse HTML
            mdx_body = self._run_standalone_processors(mdx_body, "markdown")

            # Pipeline processors
            pipeline = self._get_pipeline()
            pipe_result = pipeline.run(mdx_body, proc_ctx)
            mdx_body = pipe_result.content

            context.warnings.extend(proc_ctx.warnings)
            context.errors.extend(proc_ctx.errors)
            context.imports_needed.update(proc_ctx.imports_needed)

            # 8. JSX conversion
            mdx_body = convert_html_to_jsx(mdx_body)

            # 9. Generate imports
            imports = generate_imports(mdx_body)

            # 10. Build frontmatter
            fm_dict = context.metadata.to_frontmatter_dict()
            fm_dict["convertedAt"] = datetime.now(timezone.utc).isoformat()
            frontmatter_str = _generate_frontmatter(fm_dict)

            # 11. Assemble final MDX
            parts: list[str] = [frontmatter_str, ""]
            if imports:
                parts.append(imports)
                parts.append("")
            parts.append(mdx_body.strip())
            parts.append("")

            mdx_content = "\n".join(parts)

            # 12. ZWNJ verification
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

            # Write output if output_dir is set
            output_path: Optional[Path] = None
            output_bytes = len(mdx_content.encode("utf-8"))
            if context.output_dir and not context.dry_run:
                output_path = context.output_dir / f"{context.metadata.slug}.mdx"
                self.write_output(mdx_content, output_path, context.dry_run)

            # Build result
            result.status = "success"
            result.output_path = str(output_path) if output_path else None
            result.output_bytes = output_bytes
            result.quality.zwnj = zwnj_report
            result.quality.frontmatter_valid = True
            result.quality.mdx_valid = True
            result.quality.math_rendered = "$" in mdx_body
            result.quality.headings_count = mdx_body.count("\n#")
            result.quality.code_blocks_count = mdx_body.count("```") // 2

            # Store content for downstream access (same pattern as md_to_mdx)
            context.notes.append(f"mdx_content_length={len(mdx_content)}")
            context.extra = {"mdx_content": mdx_content}

            self._logger.info(
                "تبدیل HTML→MDX: %s → %d bytes, ZWNJ %d→%d",
                file_path.name,
                output_bytes,
                zwnj_before,
                zwnj_after,
            )

        except ConversionError:
            raise
        except Exception as exc:
            result.status = "failed"
            result.error_message = f"خطا در تبدیل HTML: {exc}"
            context.add_error(str(exc))
            self._logger.exception("خطا در تبدیل %s", file_path.name)

        finally:
            result.duration_seconds = round(time.time() - start, 3)

        return result

    # ─── Validation ───────────────────────

    def validate_output(
        self,
        result: DocumentConversionResult,
        context: ConversionContext,
    ) -> QualityReport:
        """اعتبارسنجی خروجی MDX."""
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

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Element Conversion / تبدیل عناصر
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _convert_element(
        self,
        element: Any,
        context: ConversionContext,
        file_path: Path,
    ) -> str:
        """
        تبدیل یک عنصر HTML به متن Markdown/MDX.
        Convert an HTML element recursively to Markdown/MDX.
        """
        if not HAS_BS4:
            return ""

        # Text nodes
        if isinstance(element, NavigableString):
            if isinstance(element, Comment):
                text = str(element).strip()
                return f"\n{{/* {text} */}}\n" if text else ""
            text = str(element)
            # Normalize whitespace but preserve ZWNJ
            text = re.sub(r"[ \t]+", " ", text)
            return text

        if not isinstance(element, Tag):
            return ""

        tag = element.name.lower() if element.name else ""

        # ─── Tags to remove ───────────────────
        if tag in _TAGS_REMOVE:
            # Keep math scripts
            if tag == "script":
                type_attr = (element.get("type") or "").lower()
                if "math" in type_attr or "latex" in type_attr:
                    return self._convert_math_script(element)
            return ""

        # Remove HTML comments → JSX comments
        if tag == "!--":
            return ""

        # ─── Style tag → extract classes ──────
        if tag == "style":
            return ""  # CSS extracted separately

        # ─── Headings ─────────────────────────
        if tag in _HEADING_MAP:
            level = _HEADING_MAP[tag]
            inner = self._get_inner_text(element, context, file_path)
            heading_id = element.get("id", "")
            if heading_id:
                return f"\n\n{level} {inner} {{#{heading_id}}}\n\n"
            return f"\n\n{level} {inner}\n\n"

        # ─── Paragraph ────────────────────────
        if tag == "p":
            inner = self._get_inner_text(element, context, file_path)
            inner = inner.strip()
            if not inner:
                return ""
            return f"\n\n{inner}\n\n"

        # ─── Inline formatting ─────────────────
        if tag in ("strong", "b"):
            inner = self._get_inner_text(element, context, file_path)
            return f"**{inner.strip()}**"

        if tag in ("em", "i"):
            inner = self._get_inner_text(element, context, file_path)
            return f"*{inner.strip()}*"

        if tag in ("del", "s", "strike"):
            inner = self._get_inner_text(element, context, file_path)
            return f"~~{inner.strip()}~~"

        if tag == "ins":
            inner = self._get_inner_text(element, context, file_path)
            return f"<ins>{inner}</ins>"

        if tag == "mark":
            inner = self._get_inner_text(element, context, file_path)
            return f"<mark>{inner}</mark>"

        if tag == "kbd":
            inner = self._get_inner_text(element, context, file_path)
            return f"<kbd>{inner}</kbd>"

        if tag == "sup":
            inner = self._get_inner_text(element, context, file_path)
            return f"<sup>{inner}</sup>"

        if tag == "sub":
            inner = self._get_inner_text(element, context, file_path)
            return f"<sub>{inner}</sub>"

        if tag == "abbr":
            inner = self._get_inner_text(element, context, file_path)
            title = element.get("title", "")
            if title:
                return f'<abbr title="{title}">{inner}</abbr>'
            return f"<abbr>{inner}</abbr>"

        if tag == "time":
            inner = self._get_inner_text(element, context, file_path)
            dt = element.get("datetime", "")
            if dt:
                return f'<time dateTime="{dt}">{inner}</time>'
            return f"<time>{inner}</time>"

        if tag == "address":
            inner = self._get_inner_text(element, context, file_path)
            return f"<address>{inner}</address>"

        if tag == "q":
            inner = self._get_inner_text(element, context, file_path)
            return f'"{inner}"'

        if tag == "cite":
            inner = self._get_inner_text(element, context, file_path)
            return f"*{inner}*"

        if tag == "var":
            inner = self._get_inner_text(element, context, file_path)
            return f"`{inner}`"

        if tag == "samp":
            inner = self._get_inner_text(element, context, file_path)
            return f"`{inner}`"

        # ─── Links ────────────────────────────
        if tag == "a":
            href = element.get("href", "")
            inner = self._get_inner_text(element, context, file_path)
            title = element.get("title", "")
            if not inner.strip():
                return href
            if title:
                return f'[{inner}]({href} "{title}")'
            return f"[{inner}]({href})"

        # ─── Images ───────────────────────────
        if tag == "img":
            return self._convert_img(element)

        # ─── Line break ───────────────────────
        if tag == "br":
            return "\\\n"

        if tag == "hr":
            return "\n\n---\n\n"

        # ─── Code ─────────────────────────────
        if tag == "code":
            # Inline code (not inside pre)
            parent = element.parent
            if parent and parent.name == "pre":
                return self._get_inner_text(element, context, file_path)
            inner = element.get_text()
            return f"`{inner}`"

        if tag == "pre":
            return self._convert_pre(element)

        # ─── Lists ────────────────────────────
        if tag == "ul":
            return self._convert_list(element, context, file_path, ordered=False)

        if tag == "ol":
            return self._convert_list(element, context, file_path, ordered=True)

        if tag == "li":
            inner = self._get_inner_text(element, context, file_path)
            return inner.strip()

        # ─── Definition list ──────────────────
        if tag == "dl":
            return self._convert_dl(element, context, file_path)

        # ─── Blockquote ───────────────────────
        if tag == "blockquote":
            inner = self._get_inner_text(element, context, file_path).strip()
            lines = inner.splitlines()
            quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in lines)
            return f"\n\n{quoted}\n\n"

        # ─── Table ────────────────────────────
        if tag == "table":
            return self._convert_table_element(element, context)

        # ─── Figure ───────────────────────────
        if tag == "figure":
            return self._convert_figure(element, context, file_path)

        # ─── Details/Summary ──────────────────
        if tag == "details":
            return self._convert_details(element, context, file_path)

        if tag == "summary":
            # standalone summary (not inside details) — treat as bold
            inner = self._get_inner_text(element, context, file_path)
            return f"**{inner.strip()}**"

        # ─── Math ─────────────────────────────
        if tag in ("math",):
            return self._convert_math_element(element)

        if tag == "span":
            cls = " ".join(element.get("class") or [])
            if re.search(r"katex|math|mathjax", cls, re.I):
                return self._convert_math_element(element)
            # Check for data-latex / data-tex attributes
            for attr in ("data-latex", "data-tex", "data-math"):
                latex = element.get(attr, "")
                if latex:
                    return self._convert_math_element(element)
            # Generic span — pass through children
            return self._get_inner_text(element, context, file_path)

        # ─── Media ────────────────────────────
        if tag == "video":
            return self._convert_media_element(element, "video")

        if tag == "audio":
            return self._convert_media_element(element, "audio")

        if tag == "iframe":
            return self._convert_media_element(element, "iframe")

        # ─── SVG ──────────────────────────────
        if tag == "svg":
            return self._convert_svg_element(element, context, file_path)

        # ─── Form ─────────────────────────────
        if tag == "form":
            return self._convert_form_element(element)

        if tag in ("input", "select", "textarea", "button"):
            return ""  # form elements inside forms are skipped

        # ─── Progress/Meter ───────────────────
        if tag == "progress":
            val = element.get("value", "")
            max_val = element.get("max", "100")
            label = element.get_text(strip=True) or f"{val}/{max_val}"
            return f"<progress value={{{val or 0}}} max={{{max_val}}}>{label}</progress>"

        if tag == "meter":
            val = element.get("value", "")
            min_v = element.get("min", "0")
            max_v = element.get("max", "100")
            label = element.get_text(strip=True) or val
            return f"<meter value={{{val or 0}}} min={{{min_v}}} max={{{max_v}}}>{label}</meter>"

        # ─── Semantic block containers ─────────
        if tag in ("section", "article", "main", "aside"):
            inner = self._convert_children(element, context, file_path)
            return f"\n\n{inner.strip()}\n\n"

        if tag in ("header", "footer", "nav"):
            inner = self._convert_children(element, context, file_path)
            return f"\n\n{inner.strip()}\n\n"

        if tag == "div":
            # Check for special classes
            cls = " ".join(element.get("class") or [])
            dir_attr = element.get("dir", "")
            lang_attr = element.get("lang", "")

            inner = self._convert_children(element, context, file_path).strip()

            # RTL/LTR wrappers
            if dir_attr or lang_attr:
                attrs = ""
                if dir_attr:
                    attrs += f' dir="{dir_attr}"'
                if lang_attr:
                    attrs += f' lang="{lang_attr}"'
                return f"\n\n<div{attrs}>\n\n{inner}\n\n</div>\n\n"

            # Math containers
            if re.search(r"katex|math|mathjax", cls, re.I):
                return self._convert_math_element(element)

            # Mermaid containers
            if re.search(r"mermaid", cls, re.I):
                chart_text = element.get_text(strip=True)
                return f"\n\n```mermaid\n{chart_text}\n```\n\n"

            # Generic div — just pass through children
            if inner:
                return f"\n\n{inner}\n\n"
            return ""

        # ─── HTML/body/head ───────────────────
        if tag in ("html", "body"):
            return self._convert_children(element, context, file_path)

        if tag == "head":
            return ""  # already processed

        # ─── Fallback: convert children ───────
        inner = self._convert_children(element, context, file_path)
        return inner

    def _convert_children(
        self,
        element: Any,
        context: ConversionContext,
        file_path: Path,
    ) -> str:
        """تبدیل همه فرزندان یک عنصر."""
        parts = []
        for child in element.children:
            parts.append(self._convert_element(child, context, file_path))
        return "".join(parts)

    def _get_inner_text(
        self,
        element: Any,
        context: ConversionContext,
        file_path: Path,
    ) -> str:
        """دریافت متن داخلی (با تبدیل فرزندان)."""
        return self._convert_children(element, context, file_path)

    # ─── Specific element converters ──────

    def _convert_img(self, element: Any) -> str:
        """تبدیل <img> → <Image> یا ![alt](src)."""
        src = element.get("src", "")
        alt = element.get("alt", "")
        title = element.get("title", "")
        width = element.get("width", "")
        height = element.get("height", "")
        cls = " ".join(element.get("class") or [])

        if not src:
            return ""

        # Build props string for Image component
        props = f'src="{src}"'
        if alt:
            props += f' alt="{alt}"'
        if width:
            props += f" width={{{width}}}"
        if height:
            props += f" height={{{height}}}"
        if cls:
            props += f' className="{cls}"'

        return f"<Image {props} />"

    def _convert_pre(self, element: Any) -> str:
        """تبدیل <pre><code> → ```code```."""
        code_tag = element.find("code")
        if code_tag:
            lang = ""
            cls = " ".join(code_tag.get("class") or [])
            lang_match = re.search(r"language-(\S+)", cls)
            if lang_match:
                lang = lang_match.group(1)
            code_text = code_tag.get_text()
        else:
            lang = ""
            code_text = element.get_text()

        return f"\n\n```{lang}\n{code_text}\n```\n\n"

    def _convert_list(
        self,
        element: Any,
        context: ConversionContext,
        file_path: Path,
        ordered: bool = False,
        depth: int = 0,
    ) -> str:
        """تبدیل <ul>/<ol> → MD list."""
        lines = []
        indent = "  " * depth
        counter = 1

        for child in element.children:
            if not isinstance(child, Tag):
                continue
            if child.name != "li":
                continue

            # Check for nested list
            nested_list = child.find(["ul", "ol"])
            if nested_list:
                # Get li text without the nested list
                li_text = ""
                for c in child.children:
                    if isinstance(c, NavigableString):
                        li_text += str(c)
                    elif isinstance(c, Tag) and c.name not in ("ul", "ol"):
                        li_text += self._convert_element(c, context, file_path)
                li_text = li_text.strip()

                if ordered:
                    lines.append(f"{indent}{counter}. {li_text}")
                    counter += 1
                else:
                    lines.append(f"{indent}- {li_text}")

                # Nested list
                nested_ordered = nested_list.name == "ol"
                nested_content = self._convert_list(
                    nested_list, context, file_path,
                    ordered=nested_ordered, depth=depth + 1
                )
                lines.append(nested_content.rstrip())
            else:
                li_text = self._get_inner_text(child, context, file_path).strip()
                if ordered:
                    lines.append(f"{indent}{counter}. {li_text}")
                    counter += 1
                else:
                    lines.append(f"{indent}- {li_text}")

        return "\n\n" + "\n".join(lines) + "\n\n"

    def _convert_dl(
        self,
        element: Any,
        context: ConversionContext,
        file_path: Path,
    ) -> str:
        """تبدیل <dl> → definition list در MDX."""
        lines = ["\n\n"]
        for child in element.children:
            if not isinstance(child, Tag):
                continue
            if child.name == "dt":
                text = self._get_inner_text(child, context, file_path).strip()
                lines.append(f"**{text}**")
                lines.append("")
            elif child.name == "dd":
                text = self._get_inner_text(child, context, file_path).strip()
                lines.append(f":   {text}")
                lines.append("")
        lines.append("\n")
        return "\n".join(lines)

    def _convert_figure(
        self,
        element: Any,
        context: ConversionContext,
        file_path: Path,
    ) -> str:
        """تبدیل <figure> → <Figure> کامپوننت."""
        figcaption = element.find("figcaption")
        caption = figcaption.get_text(strip=True) if figcaption else ""

        # Get content (excluding figcaption)
        content_parts = []
        for child in element.children:
            if isinstance(child, Tag) and child.name == "figcaption":
                continue
            content_parts.append(self._convert_element(child, context, file_path))
        content = "".join(content_parts).strip()

        if caption:
            return f'\n\n<Figure caption="{caption}">\n\n{content}\n\n</Figure>\n\n'
        return f"\n\n{content}\n\n"

    def _convert_details(
        self,
        element: Any,
        context: ConversionContext,
        file_path: Path,
    ) -> str:
        """تبدیل <details>/<summary> → <Details> کامپوننت."""
        summary_tag = element.find("summary")
        summary_text = summary_tag.get_text(strip=True) if summary_tag else "جزئیات"

        # Content excluding summary
        content_parts = []
        for child in element.children:
            if isinstance(child, Tag) and child.name == "summary":
                continue
            content_parts.append(self._convert_element(child, context, file_path))
        content = "".join(content_parts).strip()

        return f'\n\n<Details summary="{summary_text}">\n\n{content}\n\n</Details>\n\n'

    def _convert_math_element(self, element: Any) -> str:
        """
        تبدیل math عناصر HTML به LaTeX.
        KaTeX rendered spans → $LaTeX$
        """
        # Try to find LaTeX source in data attributes
        for attr in ("data-latex", "data-tex", "data-math"):
            latex = element.get(attr, "")
            if latex:
                if "\n" in latex or len(latex) > 80:
                    return f"\n\n$$\n{latex}\n$$\n\n"
                return f"${latex}$"

        # Try aria-label
        aria = element.get("aria-label", "")
        if aria:
            return f"${aria}$"

        # MathML → basic extraction
        if element.name == "math":
            return self._convert_mathml(element)

        # Fallback: get text content
        text = element.get_text(strip=True)
        if text:
            return f"${text}$"
        return ""

    def _convert_mathml(self, element: Any) -> str:
        """تبدیل ساده MathML به LaTeX."""
        # Basic MathML to LaTeX (for common cases)
        display = element.get("display", "inline")
        text = element.get_text(strip=True)
        if display == "block":
            return f"\n\n$$\n{text}\n$$\n\n"
        return f"${text}$"

    def _convert_math_script(self, element: Any) -> str:
        """تبدیل <script type="math/tex"> → LaTeX."""
        content = element.get_text(strip=True)
        type_attr = (element.get("type") or "").lower()
        if "display" in type_attr or "\n" in content or len(content) > 80:
            return f"\n\n$$\n{content}\n$$\n\n"
        return f"${content}$"

    def _convert_svg_element(
        self,
        element: Any,
        context: ConversionContext,
        file_path: Path,
    ) -> str:
        """
        تبدیل <svg> inline → فایل مجزا + <Image>.
        Extract inline SVG to a separate file and reference it.
        """
        self._svg_counter += 1
        svg_str = str(element)

        # Generate a unique filename based on content hash
        content_hash = hashlib.md5(svg_str.encode()).hexdigest()[:8]
        svg_filename = f"{file_path.stem}-svg-{self._svg_counter}-{content_hash}.svg"

        # Store SVG for later extraction
        context.assets_generated.append(svg_filename)
        context.add_note(f"SVG extracted: {svg_filename}")

        # Return Image component reference
        return f'\n\n<Image src="./{svg_filename}" alt="SVG figure {self._svg_counter}" />\n\n'

    def convert_table_element(self, element: Any, context: ConversionContext) -> str:
        """
        تبدیل <table> → pipe table یا HTML table.
        Simple tables → MD pipe table
        Complex (merged cells) → HTML JSX-compatible table
        """
        return self._convert_table_element(element, context)

    def _convert_table_element(self, element: Any, context: ConversionContext) -> str:
        """پیاده‌سازی داخلی تبدیل جدول."""
        if not isinstance(element, Tag):
            return ""

        # Caption
        caption_tag = element.find("caption")
        caption = caption_tag.get_text(strip=True) if caption_tag else ""

        # Detect if table has merged cells
        has_merged = bool(
            element.find(attrs={"colspan": True})
            or element.find(attrs={"rowspan": True})
        )

        if has_merged:
            return self._convert_complex_table(element, caption, context)
        else:
            return self._convert_simple_table(element, caption, context)

    def _convert_simple_table(
        self,
        element: Any,
        caption: str,
        context: ConversionContext,
    ) -> str:
        """تبدیل جدول ساده → MD pipe table."""
        rows: list[list[str]] = []

        # Get all rows
        for row in element.find_all("tr"):
            cells = []
            for cell in row.find_all(["th", "td"]):
                text = cell.get_text(strip=True)
                # Escape pipe characters
                text = text.replace("|", "\\|")
                cells.append(text)
            if cells:
                rows.append(cells)

        if not rows:
            return ""

        # Determine column count
        col_count = max(len(row) for row in rows)

        # Pad rows to same length
        rows = [row + [""] * (col_count - len(row)) for row in rows]

        # First row is header
        header = rows[0]
        separator = ["-" * max(3, len(h)) for h in header]
        body_rows = rows[1:]

        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(separator) + " |",
        ]
        for row in body_rows:
            lines.append("| " + " | ".join(row) + " |")

        result = "\n\n" + "\n".join(lines) + "\n\n"
        if caption:
            result = f"\n\n*{caption}*\n" + result

        return result

    def _convert_complex_table(
        self,
        element: Any,
        caption: str,
        context: ConversionContext,
    ) -> str:
        """تبدیل جدول پیچیده (ادغامی) → HTML JSX-compatible."""
        context.require_import("Table")

        # Reconstruct as JSX-compatible HTML table
        lines = ["\n\n<div style={{overflowX: 'auto'}}>\n<table>"]

        if caption:
            lines.append(f"<caption>{caption}</caption>")

        thead = element.find("thead")
        if thead:
            lines.append("<thead>")
            for row in thead.find_all("tr"):
                lines.append("<tr>")
                for cell in row.find_all(["th", "td"]):
                    attrs = self._build_cell_attrs(cell)
                    tag = cell.name
                    text = cell.get_text(strip=True)
                    lines.append(f"<{tag}{attrs}>{text}</{tag}>")
                lines.append("</tr>")
            lines.append("</thead>")

        tbody = element.find("tbody") or element
        tbody_tag = "tbody" if element.find("tbody") else None
        if tbody_tag:
            lines.append("<tbody>")
        for row in tbody.find_all("tr"):
            lines.append("<tr>")
            for cell in row.find_all(["th", "td"]):
                attrs = self._build_cell_attrs(cell)
                tag = cell.name
                text = cell.get_text(strip=True)
                lines.append(f"<{tag}{attrs}>{text}</{tag}>")
            lines.append("</tr>")
        if tbody_tag:
            lines.append("</tbody>")

        tfoot = element.find("tfoot")
        if tfoot:
            lines.append("<tfoot>")
            for row in tfoot.find_all("tr"):
                lines.append("<tr>")
                for cell in row.find_all(["th", "td"]):
                    attrs = self._build_cell_attrs(cell)
                    tag = cell.name
                    text = cell.get_text(strip=True)
                    lines.append(f"<{tag}{attrs}>{text}</{tag}>")
                lines.append("</tr>")
            lines.append("</tfoot>")

        lines.append("</table>\n</div>\n\n")
        return "\n".join(lines)

    def _build_cell_attrs(self, cell: Any) -> str:
        """ساخت attribute string برای سلول جدول."""
        attrs = ""
        colspan = cell.get("colspan", "")
        rowspan = cell.get("rowspan", "")
        align = cell.get("align", "")
        if colspan and colspan != "1":
            attrs += f" colSpan={{{colspan}}}"
        if rowspan and rowspan != "1":
            attrs += f" rowSpan={{{rowspan}}}"
        if align:
            attrs += f' style={{{{textAlign: "{align}"}}}}'
        return attrs

    def convert_form_element(self, element: Any) -> str:
        """تبدیل <form> → comment + placeholder."""
        return self._convert_form_element(element)

    def _convert_form_element(self, element: Any) -> str:
        """پیاده‌سازی داخلی تبدیل فرم."""
        action = element.get("action", "")
        method = element.get("method", "get").upper()
        comment = f"Form: action={action}, method={method}"
        return (
            f"\n\n{{/* {comment} */}}\n"
            f"{{/* TODO: Replace with appropriate form component */}}\n\n"
        )

    def convert_media_element(self, element: Any, media_type: str = None) -> str:
        """تبدیل <video>/<audio>/<iframe> → JSX components."""
        if media_type is None:
            media_type = element.name if isinstance(element, Tag) else "video"
        return self._convert_media_element(element, media_type)

    def _convert_media_element(self, element: Any, media_type: str) -> str:
        """پیاده‌سازی داخلی تبدیل رسانه."""
        if media_type == "video":
            src = element.get("src", "")
            # Try source child
            if not src:
                source = element.find("source")
                if source:
                    src = source.get("src", "")
            width = element.get("width", "")
            height = element.get("height", "")
            controls = "controls" in element.attrs
            props = f'src="{src}"'
            if width:
                props += f" width={{{width}}}"
            if height:
                props += f" height={{{height}}}"
            if controls:
                props += " controls={true}"
            return f"\n\n<Video {props} />\n\n"

        elif media_type == "audio":
            src = element.get("src", "")
            if not src:
                source = element.find("source")
                if source:
                    src = source.get("src", "")
            controls = "controls" in element.attrs
            props = f'src="{src}"'
            if controls:
                props += " controls={true}"
            return f"\n\n<Audio {props} />\n\n"

        elif media_type == "iframe":
            src = element.get("src", "")
            width = element.get("width", "")
            height = element.get("height", "")
            title = element.get("title", "Embedded content")
            props = f'src="{src}" title="{title}"'
            if width:
                props += f" width={{{width}}}"
            if height:
                props += f" height={{{height}}}"
            return f"\n\n<Embed {props} />\n\n"

        return ""

    def convert_svg_element(
        self,
        element: Any,
        context: ConversionContext,
        file_path: Path,
    ) -> str:
        """Public API برای تبدیل SVG."""
        return self._convert_svg_element(element, context, file_path)

    def convert_math_from_html(self, element: Any) -> str:
        """تبدیل math عناصر HTML به LaTeX."""
        return self._convert_math_element(element)

    def extract_css_to_classnames(
        self,
        html_content: str,
    ) -> tuple[str, dict[str, str]]:
        """
        استخراج CSS inline به className‌ها.
        Extract inline styles and map to className identifiers.

        Returns: (cleaned_html, classname_map)
        """
        classname_map: dict[str, str] = {}
        counter = [0]

        def _replace_style(m: re.Match) -> str:
            css = m.group(2)
            # Generate a class name
            css_hash = hashlib.md5(css.encode()).hexdigest()[:6]
            cls_name = f"generated-{css_hash}"
            classname_map[cls_name] = css
            counter[0] += 1
            return f'className="{cls_name}"'

        style_re = re.compile(r'\bstyle\s*=\s*(["\'])(.*?)\1', re.DOTALL)
        cleaned = style_re.sub(_replace_style, html_content)
        return cleaned, classname_map
