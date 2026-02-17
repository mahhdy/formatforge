# -*- coding: utf-8-sig -*-
r"""Image processor for FormatForge.

Processes image references from LaTeX, Markdown, and HTML sources.
Converts to MDX-compatible components.
"""
from __future__ import annotations

import re
import shutil
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .image_models import (
    ImageRef,
    ImageType,
    ImageSourceFormat,
    OptimizedImage,
    AssetMapping,
    AssetMap,
)


logger = logging.getLogger(__name__)

# ============================================================
# Regex patterns
# ============================================================

_BS = chr(92)  # backslash

RE_INCLUDEGRAPHICS = re.compile(
    _BS + _BS + r'includegraphics(?:\[([^\]]*)\])?\{([^{}]*)\}'
)

RE_FIGURE_ENV = re.compile(
    _BS + _BS + r'begin\{figure\}(\[].*?\])?(.*?)' + _BS + _BS + r'end\{figure\}',
    re.DOTALL,
)

RE_WRAPFIGURE_ENV = re.compile(
    _BS + _BS + r'begin\{wrapfigure\}\{([^{}]*)\}\{([^{}]*)\}(.*?)' + _BS + _BS + r'end\{wrapfigure\}',
    re.DOTALL,
)

RE_SUBFIGURE_ENV = re.compile(
    _BS + _BS + r'begin\{subfigure\}\{([^{}]*)\}(.*?)' + _BS + _BS + r'end\{subfigure\}',
    re.DOTALL,
)

RE_CAPTION = re.compile(
    _BS + _BS + r'caption\{([^{}]*)\}'
)

RE_LABEL = re.compile(
    _BS + _BS + r'label\{([^{}]*)\}'
)

RE_MD_IMAGE = re.compile(
    r'!\[([^\]]*)\]\(([^)]+)\)'
)

RE_HTML_IMG = re.compile(
    r'<img\s+([^>]*)/?>', re.IGNORECASE
)

RE_HTML_ATTR = re.compile(
    r'(src|alt|width|height)="([^"]*)"'
)

RE_HTML_VIDEO = re.compile(
    r'<video([^>]*)>(.*?)</video>', re.DOTALL | re.IGNORECASE
)

RE_HTML_AUDIO = re.compile(
    r'<audio([^>]*)>(.*?)</audio>', re.DOTALL | re.IGNORECASE
)

RE_HTML_IFRAME = re.compile(
    r'<iframe([^>]*)>(.*?)</iframe>', re.DOTALL | re.IGNORECASE
)

RE_SVG_INLINE = re.compile(
    r'<svg([^>]*)>(.*?)</svg>', re.DOTALL | re.IGNORECASE
)

RE_WIDTH_OPT = re.compile(
    r'width\s*=\s*([^,\]]+)'
)

RE_HEIGHT_OPT = re.compile(
    r'height\s*=\s*([^,\]]+)'
)

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff',
                    '.webp', '.avif', '.svg', '.pdf', '.eps'}

RASTER_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}


# ============================================================
# ImageProcessor
# ============================================================


class ImageProcessor:
    r"""Processor for converting image references to MDX format.

    Handles LaTeX, Markdown, and HTML image references.
    Supports optimization, asset copying, and path rewriting.
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        r"""Initialize image processor.

        Args:
            config: Optional configuration dictionary.
        """
        self.config = config or {}
        self.optimize_enabled: bool = self.config.get("optimize", False)
        self.max_width: Optional[int] = self.config.get("max_width", None)
        self.output_format: str = self.config.get("output_format", "webp")
        self.assets_dir: str = self.config.get("assets_dir", "assets/images")
        self.slug: str = self.config.get("slug", "document")
        self.caption_position: str = self.config.get("caption_position", "below")

    # --------------------------------------------------------
    # Finding image references
    # --------------------------------------------------------

    def find_image_references(
        self, text: str, source_format: str = "latex"
    ) -> List[ImageRef]:
        r"""Find all image references in source text.

        Args:
            text: Source document text.
            source_format: One of 'latex', 'markdown', 'html'.

        Returns:
            List of ImageRef objects found.
        """
        refs: List[ImageRef] = []

        if source_format == "latex":
            refs.extend(self._find_latex_figures(text))
            refs.extend(self._find_latex_images(text))
        elif source_format == "markdown":
            refs.extend(self._find_markdown_images(text))
        elif source_format == "html":
            refs.extend(self._find_html_images(text))
            refs.extend(self._find_html_media(text))

        return refs

    def _find_latex_figures(self, text: str) -> List[ImageRef]:
        r"""Find LaTeX figure/wrapfigure/subfigure environments."""
        refs: List[ImageRef] = []

        # wrapfigure
        for match in RE_WRAPFIGURE_ENV.finditer(text):
            position = match.group(1)
            width = match.group(2)
            body = match.group(3)
            inner = self._parse_figure_body(body)
            inner.image_type = ImageType.WRAPFIGURE
            inner.source_format = ImageSourceFormat.LATEX
            inner.position = position
            inner.width = width
            inner.original_text = match.group(0)
            refs.append(inner)

        # Regular figure (may contain subfigures)
        for match in RE_FIGURE_ENV.finditer(text):
            body = match.group(2) if match.group(2) else match.group(1) or ''
            # Check for subfigures
            subfigs = list(RE_SUBFIGURE_ENV.finditer(body))
            if subfigs:
                children: List[ImageRef] = []
                for sf in subfigs:
                    child = self._parse_figure_body(sf.group(2))
                    child.image_type = ImageType.SUBFIGURE
                    child.width = sf.group(1)
                    child.source_format = ImageSourceFormat.LATEX
                    children.append(child)
                outer_body = RE_SUBFIGURE_ENV.sub('', body)
                cap_match = RE_CAPTION.search(outer_body)
                lbl_match = RE_LABEL.search(outer_body)

                parent = ImageRef(
                    image_type=ImageType.FIGURE,
                    source_format=ImageSourceFormat.LATEX,
                    caption=cap_match.group(1) if cap_match else None,
                    label=lbl_match.group(1) if lbl_match else None,
                    children=children,
                    original_text=match.group(0),
                )
                refs.append(parent)
            else:
                fig = self._parse_figure_body(body)
                fig.image_type = ImageType.FIGURE
                fig.source_format = ImageSourceFormat.LATEX
                fig.original_text = match.group(0)
                refs.append(fig)

        return refs

    def _find_latex_images(self, text: str) -> List[ImageRef]:
        r"""Find standalone \includegraphics (not inside figure)."""
        refs: List[ImageRef] = []
        # Remove figure environments first to avoid duplicates
        cleaned = RE_FIGURE_ENV.sub('', text)
        cleaned = RE_WRAPFIGURE_ENV.sub('', cleaned)

        for match in RE_INCLUDEGRAPHICS.finditer(cleaned):
            opts = match.group(1) or ''
            path = match.group(2)
            width = None
            height = None
            w_match = RE_WIDTH_OPT.search(opts)
            h_match = RE_HEIGHT_OPT.search(opts)
            if w_match:
                width = w_match.group(1).strip()
            if h_match:
                height = h_match.group(1).strip()
            refs.append(ImageRef(
                src=path,
                image_type=ImageType.STATIC,
                source_format=ImageSourceFormat.LATEX,
                width=width,
                height=height,
                original_text=match.group(0),
            ))

        return refs

    def _parse_figure_body(self, body: str) -> ImageRef:
        r"""Parse the body of a figure environment."""
        # Find includegraphics
        img_match = RE_INCLUDEGRAPHICS.search(body)
        src = img_match.group(2) if img_match else ''
        opts = img_match.group(1) if img_match and img_match.group(1) else ''

        width = None
        height = None
        w_match = RE_WIDTH_OPT.search(opts)
        h_match = RE_HEIGHT_OPT.search(opts)
        if w_match:
            width = w_match.group(1).strip()
        if h_match:
            height = h_match.group(1).strip()

        cap_match = RE_CAPTION.search(body)
        lbl_match = RE_LABEL.search(body)

        caption = cap_match.group(1) if cap_match else None
        label = lbl_match.group(1) if lbl_match else None
        alt = caption or ''

        return ImageRef(
            src=src,
            alt=alt,
            caption=caption,
            label=label,
            width=width,
            height=height,
        )

    def _find_markdown_images(self, text: str) -> List[ImageRef]:
        r"""Find Markdown image references: ![alt](path)."""
        refs: List[ImageRef] = []
        for match in RE_MD_IMAGE.finditer(text):
            alt = match.group(1)
            src = match.group(2)
            refs.append(ImageRef(
                src=src,
                alt=alt,
                image_type=ImageType.STATIC,
                source_format=ImageSourceFormat.MARKDOWN,
                original_text=match.group(0),
            ))
        return refs

    def _find_html_images(self, text: str) -> List[ImageRef]:
        r"""Find HTML <img> tags."""
        refs: List[ImageRef] = []
        for match in RE_HTML_IMG.finditer(text):
            attrs_str = match.group(1)
            attrs = dict(RE_HTML_ATTR.findall(attrs_str))
            refs.append(ImageRef(
                src=attrs.get("src", ""),
                alt=attrs.get("alt", ""),
                image_type=ImageType.STATIC,
                source_format=ImageSourceFormat.HTML,
                width=attrs.get("width"),
                height=attrs.get("height"),
                original_text=match.group(0),
            ))
        return refs

    def _find_html_media(self, text: str) -> List[ImageRef]:
        r"""Find HTML video, audio, iframe, and inline SVG."""
        refs: List[ImageRef] = []

        for match in RE_HTML_VIDEO.finditer(text):
            attrs = dict(RE_HTML_ATTR.findall(match.group(1)))
            refs.append(ImageRef(
                src=attrs.get("src", ""),
                image_type=ImageType.VIDEO,
                source_format=ImageSourceFormat.HTML,
                original_text=match.group(0),
            ))

        for match in RE_HTML_AUDIO.finditer(text):
            attrs = dict(RE_HTML_ATTR.findall(match.group(1)))
            refs.append(ImageRef(
                src=attrs.get("src", ""),
                image_type=ImageType.AUDIO,
                source_format=ImageSourceFormat.HTML,
                original_text=match.group(0),
            ))

        for match in RE_HTML_IFRAME.finditer(text):
            attrs = dict(RE_HTML_ATTR.findall(match.group(1)))
            refs.append(ImageRef(
                src=attrs.get("src", ""),
                image_type=ImageType.IFRAME,
                source_format=ImageSourceFormat.HTML,
                original_text=match.group(0),
            ))

        for match in RE_SVG_INLINE.finditer(text):
            refs.append(ImageRef(
                image_type=ImageType.SVG_INLINE,
                source_format=ImageSourceFormat.HTML,
                original_text=match.group(0),
            ))

        return refs

    # --------------------------------------------------------
    # Image optimization
    # --------------------------------------------------------

    def optimize_image(
        self, path: Path, config: Optional[dict] = None
    ) -> OptimizedImage:
        r"""Optimize a single image file.

        Args:
            path: Path to the image file.
            config: Optional override config.

        Returns:
            OptimizedImage with results.
        """
        cfg = config or self.config
        out_fmt = cfg.get("output_format", self.output_format)
        max_w = cfg.get("max_width", self.max_width)

        if not path.exists():
            logger.warning("Image not found: %s", path)
            return OptimizedImage(
                original_path=path,
                optimized_path=path,
            )

        original_size = path.stat().st_size
        suffix = path.suffix.lower()

        # SVG optimization via svgo
        if suffix == '.svg':
            return self._optimize_svg(path, original_size)

        # Raster optimization via Pillow
        if suffix in RASTER_EXTENSIONS:
            return self._optimize_raster(path, original_size, out_fmt, max_w)

        # Unsupported format — return as-is
        return OptimizedImage(
            original_path=path,
            optimized_path=path,
            original_size=original_size,
            optimized_size=original_size,
            format=suffix.lstrip('.'),
        )

    def _optimize_raster(
        self, path: Path, original_size: int, out_fmt: str, max_w: Optional[int]
    ) -> OptimizedImage:
        r"""Optimize a raster image using Pillow."""
        try:
            from PIL import Image
        except ImportError:
            logger.warning("Pillow not installed, skipping optimization")
            return OptimizedImage(
                original_path=path,
                optimized_path=path,
                original_size=original_size,
                optimized_size=original_size,
            )

        img = Image.open(path)
        w, h = img.size

        # Resize if max_width specified
        if max_w and w > max_w:
            ratio = max_w / w
            new_h = int(h * ratio)
            img = img.resize((max_w, new_h), Image.LANCZOS)
            w, h = max_w, new_h

        out_path = path.with_suffix('.' + out_fmt)
        if out_fmt == 'webp':
            img.save(out_path, 'WEBP', quality=85)
        elif out_fmt == 'avif':
            img.save(out_path, 'AVIF', quality=80)
        else:
            img.save(out_path)

        optimized_size = out_path.stat().st_size
        return OptimizedImage(
            original_path=path,
            optimized_path=out_path,
            original_size=original_size,
            optimized_size=optimized_size,
            format=out_fmt,
            width=w,
            height=h,
        )

    def _optimize_svg(self, path: Path, original_size: int) -> OptimizedImage:
        r"""Optimize SVG using svgo if available."""
        out_path = path.with_name(path.stem + '.min.svg')
        try:
            subprocess.run(
                ['svgo', str(path), '-o', str(out_path)],
                check=True,
                capture_output=True,
            )
            optimized_size = out_path.stat().st_size
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("svgo not available, skipping SVG optimization")
            out_path = path
            optimized_size = original_size

        return OptimizedImage(
            original_path=path,
            optimized_path=out_path,
            original_size=original_size,
            optimized_size=optimized_size,
            format="svg",
        )

    # --------------------------------------------------------
    # Asset copying
    # --------------------------------------------------------

    def copy_assets(
        self,
        refs: List[ImageRef],
        source_dir: Path,
        target_dir: Path,
    ) -> AssetMap:
        r"""Copy image assets to target directory.

        Args:
            refs: List of image references to copy.
            source_dir: Directory containing original images.
            target_dir: Root target directory (assets_dir appended).

        Returns:
            AssetMap with all mappings.
        """
        asset_dir = target_dir / self.assets_dir / self.slug
        asset_dir.mkdir(parents=True, exist_ok=True)

        mappings: List[AssetMapping] = []
        counter = 1

        for ref in refs:
            if not ref.src:
                continue
            source_path = source_dir / ref.src
            if not source_path.exists():
                logger.warning("Source image not found: %s", source_path)
                mappings.append(AssetMapping(
                    original_src=ref.src,
                    copied=False,
                ))
                continue

            ext = source_path.suffix
            new_name = f'{self.slug}-fig-{counter}{ext}'
            new_path = asset_dir / new_name
            new_relative = f'{self.assets_dir}/{self.slug}/{new_name}'

            try:
                shutil.copy2(source_path, new_path)
                optimized = False

                if self.optimize_enabled:
                    opt_result = self.optimize_image(new_path)
                    if opt_result.optimized_path != new_path:
                        new_path = opt_result.optimized_path
                        new_name = new_path.name
                        new_relative = f'{self.assets_dir}/{self.slug}/{new_name}'
                        optimized = True

                mappings.append(AssetMapping(
                    original_src=ref.src,
                    new_src=new_relative,
                    copied=True,
                    optimized=optimized,
                ))
                counter += 1
            except OSError as e:
                logger.error("Failed to copy %s: %s", source_path, e)
                mappings.append(AssetMapping(
                    original_src=ref.src,
                    copied=False,
                ))

        return AssetMap(mappings=mappings)

    # --------------------------------------------------------
    # Rendering to MDX
    # --------------------------------------------------------

    def render_mdx(self, ref: ImageRef, asset_map: Optional[AssetMap] = None) -> str:
        r"""Render a single ImageRef as MDX component.

        Args:
            ref: Image reference to render.
            asset_map: Optional asset map for path rewriting.

        Returns:
            MDX-compatible string.
        """
        # Resolve path
        src = ref.src
        if asset_map:
            new_path = asset_map.get_new_path(ref.src)
            if new_path:
                src = new_path

        if ref.image_type == ImageType.FIGURE:
            if ref.children:
                return self._render_figure_grid(ref, src, asset_map)
            return self._render_figure(ref, src)
        elif ref.image_type == ImageType.WRAPFIGURE:
            return self._render_wrapfigure(ref, src)
        elif ref.image_type == ImageType.VIDEO:
            return self._render_video(ref, src)
        elif ref.image_type == ImageType.AUDIO:
            return self._render_audio(ref, src)
        elif ref.image_type == ImageType.IFRAME:
            return self._render_iframe(ref, src)
        elif ref.image_type == ImageType.SVG_INLINE:
            return ref.original_text  # pass through
        else:
            return self._render_image(ref, src)

    def _render_image(self, ref: ImageRef, src: str) -> str:
        r"""Render simple <Image /> component."""
        alt = ref.alt or ref.caption or ''
        parts = ['<Image']
        parts.append(' src=' + chr(34) + src + chr(34))
        parts.append(' alt=' + chr(34) + alt + chr(34))
        if ref.width:
            parts.append(' width=' + chr(34) + ref.width + chr(34))
        if ref.height:
            parts.append(' height=' + chr(34) + ref.height + chr(34))
        parts.append(' />')
        return ''.join(parts)

    def _render_figure(self, ref: ImageRef, src: str) -> str:
        r"""Render <Figure> component with caption."""
        out_parts: List[str] = []
        label_attr = ''
        if ref.label:
            label_attr = ' id=' + chr(34) + ref.label + chr(34)
        out_parts.append('<Figure' + label_attr + '>')
        out_parts.append('  ' + self._render_image(ref, src))
        if ref.caption:
            out_parts.append('  <figcaption>' + ref.caption + '</figcaption>')
        out_parts.append('</Figure>')
        return chr(10).join(out_parts)

    def _render_wrapfigure(self, ref: ImageRef, src: str) -> str:
        r"""Render wrapped/floated figure."""
        float_side = 'right' if ref.position in ('r', 'R') else 'left'
        out_parts: List[str] = []
        out_parts.append('<Figure float=' + chr(34) + float_side + chr(34) + '>')
        out_parts.append('  ' + self._render_image(ref, src))
        if ref.caption:
            out_parts.append('  <figcaption>' + ref.caption + '</figcaption>')
        out_parts.append('</Figure>')
        return chr(10).join(out_parts)

    def _render_figure_grid(
        self, ref: ImageRef, src: str, asset_map: Optional[AssetMap]
    ) -> str:
        r"""Render <FigureGrid> for subfigures."""
        out_parts: List[str] = []
        label_attr = ''
        if ref.label:
            label_attr = ' id=' + chr(34) + ref.label + chr(34)
        out_parts.append('<FigureGrid' + label_attr + '>')
        for child in ref.children:
            child_src = child.src
            if asset_map:
                new_p = asset_map.get_new_path(child.src)
                if new_p:
                    child_src = new_p
            out_parts.append('  ' + self._render_figure(child, child_src))
        if ref.caption:
            out_parts.append('  <figcaption>' + ref.caption + '</figcaption>')
        out_parts.append('</FigureGrid>')
        return chr(10).join(out_parts)

    @staticmethod
    def _render_video(ref: ImageRef, src: str) -> str:
        r"""Render <Video> component."""
        return '<Video src=' + chr(34) + src + chr(34) + ' />'

    @staticmethod
    def _render_audio(ref: ImageRef, src: str) -> str:
        r"""Render <Audio> component."""
        return '<Audio src=' + chr(34) + src + chr(34) + ' />'

    @staticmethod
    def _render_iframe(ref: ImageRef, src: str) -> str:
        r"""Render <Embed> component for iframes."""
        return '<Embed src=' + chr(34) + src + chr(34) + ' />'

    # --------------------------------------------------------
    # Full text processing
    # --------------------------------------------------------

    def process(
        self,
        text: str,
        source_format: str = "latex",
        asset_map: Optional[AssetMap] = None,
    ) -> str:
        r"""Process all image references in text.

        Args:
            text: Full source text.
            source_format: Input format.
            asset_map: Optional asset map for path rewriting.

        Returns:
            Text with image references replaced by MDX components.
        """
        refs = self.find_image_references(text, source_format)
        result = text
        for ref in refs:
            if ref.original_text:
                mdx = self.render_mdx(ref, asset_map)
                result = result.replace(ref.original_text, mdx, 1)
        return result
