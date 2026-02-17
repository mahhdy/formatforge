# -*- coding: utf-8-sig -*-
r"""Tests for image_processor module.

Test suite for FormatForge image processing.
"""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from formatforge.core.processors.image_models import (
    ImageRef,
    ImageType,
    ImageSourceFormat,
    OptimizedImage,
    AssetMapping,
    AssetMap,
)
from formatforge.core.processors.image_processor import ImageProcessor


ZWNJ = chr(0x200C)
BS = chr(92)  # backslash
LBRACE = chr(123)  # {
RBRACE = chr(125)  # }


@pytest.fixture
def processor() -> ImageProcessor:
    r"""Create a default ImageProcessor instance."""
    return ImageProcessor()


@pytest.fixture
def tmp_dirs():
    r"""Create temporary source and target directories."""
    source = tempfile.mkdtemp()
    target = tempfile.mkdtemp()
    yield Path(source), Path(target)
    shutil.rmtree(source, ignore_errors=True)
    shutil.rmtree(target, ignore_errors=True)


# ============================================================
# Test 1: LaTeX image detection
# ============================================================


class TestLatexImages:
    r"""Tests for LaTeX image reference detection."""

    def test_includegraphics_simple(self, processor: ImageProcessor) -> None:
        r"""Test finding a simple includegraphics."""
        text = BS + 'includegraphics' + LBRACE + 'img/photo.png' + RBRACE
        refs = processor.find_image_references(text, "latex")
        assert len(refs) == 1
        assert refs[0].src == "img/photo.png"
        assert refs[0].image_type == ImageType.STATIC

    def test_includegraphics_with_options(self, processor: ImageProcessor) -> None:
        r"""Test includegraphics with width/height options."""
        text = (
            BS + 'includegraphics[width=0.8' + BS + 'textwidth]'
            + LBRACE + 'figures/diagram.pdf' + RBRACE
        )
        refs = processor.find_image_references(text, "latex")
        assert len(refs) == 1
        assert refs[0].src == "figures/diagram.pdf"
        assert refs[0].width is not None
        assert '0.8' in refs[0].width

    def test_figure_environment(self, processor: ImageProcessor) -> None:
        r"""Test parsing a figure environment with caption and label."""
        text = (
            BS + 'begin' + LBRACE + 'figure' + RBRACE + '[h]'
            + chr(10)
            + BS + 'includegraphics' + LBRACE + 'img/test.png' + RBRACE
            + chr(10)
            + BS + 'caption' + LBRACE + 'Test caption' + RBRACE
            + chr(10)
            + BS + 'label' + LBRACE + 'fig:test' + RBRACE
            + chr(10)
            + BS + 'end' + LBRACE + 'figure' + RBRACE
        )
        refs = processor.find_image_references(text, "latex")
        assert len(refs) == 1
        assert refs[0].image_type == ImageType.FIGURE
        assert refs[0].caption == "Test caption"
        assert refs[0].label == "fig:test"
        assert refs[0].src == "img/test.png"

    def test_wrapfigure(self, processor: ImageProcessor) -> None:
        r"""Test parsing wrapfigure environment."""
        text = (
            BS + 'begin' + LBRACE + 'wrapfigure' + RBRACE
            + LBRACE + 'r' + RBRACE + LBRACE + '0.5' + BS + 'textwidth' + RBRACE
            + chr(10)
            + BS + 'includegraphics' + LBRACE + 'img/side.png' + RBRACE
            + chr(10)
            + BS + 'caption' + LBRACE + 'Side image' + RBRACE
            + chr(10)
            + BS + 'end' + LBRACE + 'wrapfigure' + RBRACE
        )
        refs = processor.find_image_references(text, "latex")
        assert len(refs) == 1
        assert refs[0].image_type == ImageType.WRAPFIGURE
        assert refs[0].position == "r"
        assert refs[0].caption == "Side image"

    def test_subfigure(self, processor: ImageProcessor) -> None:
        r"""Test parsing figure with subfigures."""
        text = (
            BS + 'begin' + LBRACE + 'figure' + RBRACE
            + chr(10)
            + BS + 'begin' + LBRACE + 'subfigure' + RBRACE + LBRACE + '0.45' + BS + 'textwidth' + RBRACE
            + chr(10)
            + BS + 'includegraphics' + LBRACE + 'img/a.png' + RBRACE
            + chr(10)
            + BS + 'caption' + LBRACE + 'Sub A' + RBRACE
            + chr(10)
            + BS + 'end' + LBRACE + 'subfigure' + RBRACE
            + chr(10)
            + BS + 'begin' + LBRACE + 'subfigure' + RBRACE + LBRACE + '0.45' + BS + 'textwidth' + RBRACE
            + chr(10)
            + BS + 'includegraphics' + LBRACE + 'img/b.png' + RBRACE
            + chr(10)
            + BS + 'caption' + LBRACE + 'Sub B' + RBRACE
            + chr(10)
            + BS + 'end' + LBRACE + 'subfigure' + RBRACE
            + chr(10)
            + BS + 'caption' + LBRACE + 'Both images' + RBRACE
            + chr(10)
            + BS + 'end' + LBRACE + 'figure' + RBRACE
        )
        refs = processor.find_image_references(text, "latex")
        assert len(refs) == 1
        assert refs[0].image_type == ImageType.FIGURE
        assert len(refs[0].children) == 2
        assert refs[0].children[0].image_type == ImageType.SUBFIGURE
        assert refs[0].children[0].src == "img/a.png"
        assert refs[0].children[1].src == "img/b.png"
        assert refs[0].caption == "Both images"

    def test_no_duplicate_includegraphics(self, processor: ImageProcessor) -> None:
        r"""Standalone includegraphics inside figure should not duplicate."""
        text = (
            BS + 'begin' + LBRACE + 'figure' + RBRACE
            + chr(10)
            + BS + 'includegraphics' + LBRACE + 'img/only.png' + RBRACE
            + chr(10)
            + BS + 'end' + LBRACE + 'figure' + RBRACE
        )
        refs = processor.find_image_references(text, "latex")
        # Should find 1 (figure), not 2 (figure + standalone)
        assert len(refs) == 1
        assert refs[0].image_type == ImageType.FIGURE


# ============================================================
# Test 2: Markdown image detection
# ============================================================


class TestMarkdownImages:
    r"""Tests for Markdown image detection."""

    def test_simple_md_image(self, processor: ImageProcessor) -> None:
        r"""Test finding ![alt](path)."""
        text = '![A photo](images/photo.jpg)'
        refs = processor.find_image_references(text, "markdown")
        assert len(refs) == 1
        assert refs[0].src == "images/photo.jpg"
        assert refs[0].alt == "A photo"
        assert refs[0].source_format == ImageSourceFormat.MARKDOWN

    def test_multiple_md_images(self, processor: ImageProcessor) -> None:
        r"""Test finding multiple Markdown images."""
        text = (
            '![One](a.png)' + chr(10)
            + 'Some text' + chr(10)
            + '![Two](b.png)'
        )
        refs = processor.find_image_references(text, "markdown")
        assert len(refs) == 2
        assert refs[0].alt == "One"
        assert refs[1].alt == "Two"

    def test_md_image_persian_alt(self, processor: ImageProcessor) -> None:
        r"""Test Markdown image with Persian alt text."""
        alt_text = chr(0x062A) + chr(0x0635) + chr(0x0648) + chr(0x06CC) + chr(0x0631)  # 'تصویر'
        text = '![' + alt_text + '](img/persian.png)'
        refs = processor.find_image_references(text, "markdown")
        assert len(refs) == 1
        assert alt_text in refs[0].alt


# ============================================================
# Test 3: HTML image detection
# ============================================================


class TestHTMLImages:
    r"""Tests for HTML image and media detection."""

    def test_simple_img_tag(self, processor: ImageProcessor) -> None:
        r"""Test finding <img> tag."""
        text = '<img src=' + chr(34) + 'photo.jpg' + chr(34) + ' alt=' + chr(34) + 'A photo' + chr(34) + ' />'
        refs = processor.find_image_references(text, "html")
        assert len(refs) == 1
        assert refs[0].src == "photo.jpg"
        assert refs[0].alt == "A photo"
        assert refs[0].source_format == ImageSourceFormat.HTML

    def test_img_with_dimensions(self, processor: ImageProcessor) -> None:
        r"""Test <img> with width and height."""
        text = '<img src=' + chr(34) + 'pic.png' + chr(34) + ' width=' + chr(34) + '400' + chr(34) + ' height=' + chr(34) + '300' + chr(34) + '>'
        refs = processor.find_image_references(text, "html")
        assert len(refs) == 1
        assert refs[0].width == "400"
        assert refs[0].height == "300"

    def test_video_tag(self, processor: ImageProcessor) -> None:
        r"""Test finding <video> tag."""
        text = '<video src=' + chr(34) + 'clip.mp4' + chr(34) + '></video>'
        refs = processor.find_image_references(text, "html")
        assert len(refs) == 1
        assert refs[0].image_type == ImageType.VIDEO

    def test_audio_tag(self, processor: ImageProcessor) -> None:
        r"""Test finding <audio> tag."""
        text = '<audio src=' + chr(34) + 'sound.mp3' + chr(34) + '></audio>'
        refs = processor.find_image_references(text, "html")
        assert len(refs) == 1
        assert refs[0].image_type == ImageType.AUDIO

    def test_iframe_tag(self, processor: ImageProcessor) -> None:
        r"""Test finding <iframe> tag."""
        text = '<iframe src=' + chr(34) + 'https://example.com' + chr(34) + '></iframe>'
        refs = processor.find_image_references(text, "html")
        assert len(refs) == 1
        assert refs[0].image_type == ImageType.IFRAME

    def test_inline_svg(self, processor: ImageProcessor) -> None:
        r"""Test finding inline SVG."""
        text = '<svg width=' + chr(34) + '100' + chr(34) + '><circle r=' + chr(34) + '50' + chr(34) + '/></svg>'
        refs = processor.find_image_references(text, "html")
        assert len(refs) == 1
        assert refs[0].image_type == ImageType.SVG_INLINE


# ============================================================
# Test 4: MDX rendering
# ============================================================


class TestMDXRendering:
    r"""Tests for MDX component rendering."""

    def test_render_simple_image(self, processor: ImageProcessor) -> None:
        r"""Test rendering a simple image as <Image />."""
        ref = ImageRef(
            src="photo.jpg",
            alt="A photo",
            image_type=ImageType.STATIC,
        )
        result = processor.render_mdx(ref)
        assert '<Image' in result
        assert 'photo.jpg' in result
        assert 'A photo' in result
        assert '/>' in result

    def test_render_figure(self, processor: ImageProcessor) -> None:
        r"""Test rendering a figure with caption."""
        ref = ImageRef(
            src="diagram.png",
            alt="Diagram",
            caption="My diagram",
            label="fig:diag",
            image_type=ImageType.FIGURE,
        )
        result = processor.render_mdx(ref)
        assert '<Figure' in result
        assert 'fig:diag' in result
        assert '<figcaption>My diagram</figcaption>' in result
        assert '</Figure>' in result

    def test_render_wrapfigure_right(self, processor: ImageProcessor) -> None:
        r"""Test rendering a right-floated wrapfigure."""
        ref = ImageRef(
            src="side.png",
            position="r",
            caption="Side img",
            image_type=ImageType.WRAPFIGURE,
        )
        result = processor.render_mdx(ref)
        assert 'float=' in result
        assert 'right' in result
        assert '<figcaption>Side img</figcaption>' in result

    def test_render_wrapfigure_left(self, processor: ImageProcessor) -> None:
        r"""Test rendering a left-floated wrapfigure."""
        ref = ImageRef(
            src="side.png",
            position="l",
            image_type=ImageType.WRAPFIGURE,
        )
        result = processor.render_mdx(ref)
        assert 'left' in result

    def test_render_figure_grid(self, processor: ImageProcessor) -> None:
        r"""Test rendering subfigures as FigureGrid."""
        ref = ImageRef(
            image_type=ImageType.FIGURE,
            caption="Grid caption",
            label="fig:grid",
            children=[
                ImageRef(src="a.png", alt="A", caption="Sub A", image_type=ImageType.SUBFIGURE),
                ImageRef(src="b.png", alt="B", caption="Sub B", image_type=ImageType.SUBFIGURE),
            ],
        )
        result = processor.render_mdx(ref)
        assert '<FigureGrid' in result
        assert 'fig:grid' in result
        assert 'a.png' in result
        assert 'b.png' in result
        assert 'Grid caption' in result
        assert '</FigureGrid>' in result

    def test_render_video(self, processor: ImageProcessor) -> None:
        r"""Test rendering video component."""
        ref = ImageRef(
            src="clip.mp4",
            image_type=ImageType.VIDEO,
        )
        result = processor.render_mdx(ref)
        assert '<Video' in result
        assert 'clip.mp4' in result

    def test_render_audio(self, processor: ImageProcessor) -> None:
        r"""Test rendering audio component."""
        ref = ImageRef(
            src="sound.mp3",
            image_type=ImageType.AUDIO,
        )
        result = processor.render_mdx(ref)
        assert '<Audio' in result
        assert 'sound.mp3' in result

    def test_render_iframe(self, processor: ImageProcessor) -> None:
        r"""Test rendering iframe as Embed."""
        ref = ImageRef(
            src="https://example.com",
            image_type=ImageType.IFRAME,
        )
        result = processor.render_mdx(ref)
        assert '<Embed' in result
        assert 'https://example.com' in result

    def test_render_with_asset_map(self, processor: ImageProcessor) -> None:
        r"""Test that asset map rewrites path."""
        ref = ImageRef(
            src="old/photo.jpg",
            alt="Photo",
            image_type=ImageType.STATIC,
        )
        asset_map = AssetMap(mappings=[
            AssetMapping(
                original_src="old/photo.jpg",
                new_src="assets/images/doc/doc-fig-1.jpg",
                copied=True,
            )
        ])
        result = processor.render_mdx(ref, asset_map)
        assert 'assets/images/doc/doc-fig-1.jpg' in result
        assert 'old/photo.jpg' not in result


# ============================================================
# Test 5: Asset copying
# ============================================================


class TestAssetCopying:
    r"""Tests for image asset copying."""

    def test_copy_single_asset(self, tmp_dirs) -> None:
        r"""Test copying a single image asset."""
        source_dir, target_dir = tmp_dirs
        # Create a dummy image file
        img_dir = source_dir / 'img'
        img_dir.mkdir()
        dummy_img = img_dir / 'photo.png'
        dummy_img.write_bytes(b'PNG fake content')

        processor = ImageProcessor(config={"slug": "test-doc"})
        refs = [ImageRef(src='img/photo.png')]
        result = processor.copy_assets(refs, source_dir, target_dir)

        assert len(result.mappings) == 1
        assert result.mappings[0].copied is True
        assert 'test-doc-fig-1.png' in result.mappings[0].new_src

    def test_copy_missing_file(self, tmp_dirs) -> None:
        r"""Test copying when source file does not exist."""
        source_dir, target_dir = tmp_dirs
        processor = ImageProcessor()
        refs = [ImageRef(src='nonexistent.png')]
        result = processor.copy_assets(refs, source_dir, target_dir)

        assert len(result.mappings) == 1
        assert result.mappings[0].copied is False

    def test_copy_empty_src_skipped(self, tmp_dirs) -> None:
        r"""Test that refs with empty src are skipped."""
        source_dir, target_dir = tmp_dirs
        processor = ImageProcessor()
        refs = [ImageRef(src='')]
        result = processor.copy_assets(refs, source_dir, target_dir)
        assert len(result.mappings) == 0

    def test_asset_map_lookup(self) -> None:
        r"""Test AssetMap.get_new_path lookup."""
        am = AssetMap(mappings=[
            AssetMapping(original_src="a.png", new_src="assets/a.png", copied=True),
            AssetMapping(original_src="b.png", new_src="assets/b.png", copied=True),
        ])
        assert am.get_new_path("a.png") == "assets/a.png"
        assert am.get_new_path("b.png") == "assets/b.png"
        assert am.get_new_path("c.png") is None


# ============================================================
# Test 6: Full text processing (e2e)
# ============================================================


class TestFullProcess:
    r"""End-to-end tests for image processing."""

    def test_process_latex_simple(self, processor: ImageProcessor) -> None:
        r"""Test full process on simple LaTeX includegraphics."""
        text = 'Before ' + BS + 'includegraphics' + LBRACE + 'img.png' + RBRACE + ' after'
        result = processor.process(text, "latex")
        assert '<Image' in result
        assert 'img.png' in result
        assert 'Before' in result
        assert 'after' in result

    def test_process_markdown(self, processor: ImageProcessor) -> None:
        r"""Test full process on Markdown."""
        text = 'Hello ![pic](photo.jpg) world'
        result = processor.process(text, "markdown")
        assert '<Image' in result
        assert 'photo.jpg' in result
        assert 'Hello' in result

    def test_process_html(self, processor: ImageProcessor) -> None:
        r"""Test full process on HTML."""
        text = '<p><img src=' + chr(34) + 'x.png' + chr(34) + ' alt=' + chr(34) + 'X' + chr(34) + '></p>'
        result = processor.process(text, "html")
        assert '<Image' in result
        assert 'x.png' in result

    def test_process_preserves_unrelated_text(self, processor: ImageProcessor) -> None:
        r"""Test that non-image text is preserved."""
        text = "Just some text with no images"
        result = processor.process(text, "latex")
        assert result == text


# ============================================================
# Test 7: Model properties
# ============================================================


class TestModels:
    r"""Tests for data model properties."""

    def test_optimized_image_savings(self) -> None:
        r"""Test savings percentage calculation."""
        opt = OptimizedImage(
            original_path=Path('a.png'),
            optimized_path=Path('a.webp'),
            original_size=1000,
            optimized_size=300,
        )
        assert opt.savings_percent == 70.0

    def test_optimized_image_zero_original(self) -> None:
        r"""Test savings when original size is zero."""
        opt = OptimizedImage(
            original_path=Path('a.png'),
            optimized_path=Path('a.webp'),
            original_size=0,
            optimized_size=0,
        )
        assert opt.savings_percent == 0.0

    def test_asset_map_empty(self) -> None:
        r"""Test AssetMap with no mappings."""
        am = AssetMap()
        assert am.get_new_path("anything") is None

    def test_image_ref_defaults(self) -> None:
        r"""Test ImageRef default values."""
        ref = ImageRef()
        assert ref.src == ""
        assert ref.alt == ""
        assert ref.caption is None
        assert ref.image_type == ImageType.STATIC
        assert ref.children == []

# ============================================================
# Test 8: Persian content in images
# ============================================================


class TestPersianImages:
    r"""Tests for Persian content in image processing."""

    def test_persian_caption_preserved(self, processor: ImageProcessor) -> None:
        r"""Test that Persian caption text is preserved."""
        ref = ImageRef(
            src="img.png",
            caption='تصویر آزمایشی',
            image_type=ImageType.FIGURE,
        )
        result = processor.render_mdx(ref)
        assert 'تصویر آزمایشی' in result

    def test_persian_alt_preserved(self, processor: ImageProcessor) -> None:
        r"""Test that Persian alt text is preserved."""
        ref = ImageRef(
            src="img.png",
            alt='یک تصویر',
        )
        result = processor.render_mdx(ref)
        assert 'یک تصویر' in result

    def test_persian_zwnj_in_caption(self, processor: ImageProcessor) -> None:
        r"""Test ZWNJ preservation in caption."""
        caption = 'کتاب' + ZWNJ + 'خانه'
        ref = ImageRef(
            src="img.png",
            caption=caption,
            image_type=ImageType.FIGURE,
        )
        result = processor.render_mdx(ref)
        assert ZWNJ in result
        assert 'کتاب' in result
        assert 'خانه' in result
