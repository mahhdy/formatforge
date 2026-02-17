# -*- coding: utf-8-sig -*-
r"""Image data models for FormatForge.

Pydantic models for image references and processing results.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


class ImageSourceFormat(str, Enum):
    r"""Source format of the image reference."""

    LATEX = "latex"
    MARKDOWN = "markdown"
    HTML = "html"


class ImageType(str, Enum):
    r"""Type of image or media element."""

    STATIC = "static"         # Regular image
    FIGURE = "figure"         # Figure with caption
    WRAPFIGURE = "wrapfigure" # Wrapped/floated figure
    SUBFIGURE = "subfigure"   # Part of a figure grid
    VIDEO = "video"           # Video element
    AUDIO = "audio"           # Audio element
    IFRAME = "iframe"         # Embedded iframe
    SVG_INLINE = "svg_inline" # Inline SVG


class ImageRef(BaseModel):
    r"""A single image reference found in source text.

    Attributes:
        src: Original source path or URL.
        alt: Alt text for accessibility.
        caption: Figure caption if available.
        label: LaTeX label for cross-reference.
        image_type: Type of image element.
        source_format: Format the reference was found in.
        width: Optional width specification.
        height: Optional height specification.
        position: Float position (for wrapfigure).
        children: Sub-images (for subfigure).
        original_text: The full original source text.
    """

    src: str = ""
    alt: str = ""
    caption: Optional[str] = None
    label: Optional[str] = None
    image_type: ImageType = ImageType.STATIC
    source_format: ImageSourceFormat = ImageSourceFormat.LATEX
    width: Optional[str] = None
    height: Optional[str] = None
    position: Optional[str] = None
    children: List[ImageRef] = Field(default_factory=list)
    original_text: str = ""


class OptimizedImage(BaseModel):
    r"""Result of image optimization.

    Attributes:
        original_path: Path to original image.
        optimized_path: Path to optimized image.
        original_size: Size in bytes before optimization.
        optimized_size: Size in bytes after optimization.
        format: Output format (webp, avif, svg, etc).
        width: Image width in pixels.
        height: Image height in pixels.
    """

    original_path: Path
    optimized_path: Path
    original_size: int = 0
    optimized_size: int = 0
    format: str = ""
    width: Optional[int] = None
    height: Optional[int] = None

    @property
    def savings_percent(self) -> float:
        r"""Calculate percentage of size saved."""
        if self.original_size == 0:
            return 0.0
        return (1 - self.optimized_size / self.original_size) * 100


class AssetMapping(BaseModel):
    r"""Mapping from original path to new asset path.

    Attributes:
        original_src: Original source path in document.
        new_src: New path in assets directory.
        copied: Whether the file was successfully copied.
        optimized: Whether the file was optimized.
    """

    original_src: str = ""
    new_src: str = ""
    copied: bool = False
    optimized: bool = False


class AssetMap(BaseModel):
    r"""Collection of asset mappings for a document."""

    mappings: List[AssetMapping] = Field(default_factory=list)

    def get_new_path(self, original_src: str) -> Optional[str]:
        r"""Look up new path for an original source."""
        for m in self.mappings:
            if m.original_src == original_src:
                return m.new_src
        return None
