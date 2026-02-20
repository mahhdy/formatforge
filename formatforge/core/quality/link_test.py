"""
Link Test Module
ماژول تست لینک‌ها

Tests for link validation in MDX output.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple


class LinkInfo(NamedTuple):
    """اطلاعات یک لینک."""
    url: str
    text: str
    is_internal: bool
    is_anchor: bool
    line: int | None = None


class LinkTestResult(NamedTuple):
    """نتیجه تست لینک."""
    total_links: int
    internal_links: int
    external_links: int
    anchor_links: int
    broken_internal: list[str]
    broken_anchors: list[str]
    
    @property
    def valid_internal_count(self) -> int:
        return self.internal_links - len(self.broken_internal)
    
    @property
    def all_valid(self) -> bool:
        return len(self.broken_internal) == 0 and len(self.broken_anchors) == 0


def extract_links(text: str) -> list[LinkInfo]:
    """استخراج تمام لینک‌ها از متن."""
    links = []
    
    # Markdown links: [text](url)
    for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', text):
        text_content = match.group(1)
        url = match.group(2)
        
        # Determine link type
        is_anchor = url.startswith('#')
        is_internal = not url.startswith(('http://', 'https://', 'mailto:'))
        
        links.append(LinkInfo(
            url=url,
            text=text_content,
            is_internal=is_internal,
            is_anchor=is_anchor,
        ))
    
    # HTML links: <a href="url">text</a>
    for match in re.finditer(r'<a\s+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>', text, re.IGNORECASE):
        url = match.group(1)
        text_content = match.group(2)
        
        is_anchor = url.startswith('#')
        is_internal = not url.startswith(('http://', 'https://', 'mailto:'))
        
        links.append(LinkInfo(
            url=url,
            text=text_content,
            is_internal=is_internal,
            is_anchor=is_anchor,
        ))
    
    return links


def extract_anchors(text: str) -> list[str]:
    """استخراج تمام anchor ها از متن."""
    anchors = []
    
    # Markdown headings with IDs: ## Title {#anchor} or ## Title {#custom-id}
    for match in re.finditer(r'^#{1,6}\s+.+?\{#([^}]+)\}', text, re.MULTILINE):
        anchors.append(match.group(1))
    
    # HTML IDs: <element id="anchor">
    for match in re.finditer(r'<(\w+)\s+[^>]*id=["\']([^"\']+)["\']', text):
        anchors.append(match.group(2))
    
    # Auto-generated IDs from headings: ## Title → id="title"
    for match in re.finditer(r'^#{1,6}\s+(.+)$', text, re.MULTILINE):
        heading_text = match.group(1).strip()
        # Generate ID from heading (lowercase, spaces to hyphens)
        auto_id = re.sub(r'[^a-z0-9\s-]', '', heading_text.lower())
        auto_id = re.sub(r'[\s]+', '-', auto_id)
        anchors.append(auto_id)
    
    return anchors


def validate_internal_links(
    text: str,
    mdx_files: list[Path] | None = None,
    assets_dir: Path | None = None,
) -> LinkTestResult:
    """
    اعتبارسنجی لینک‌های داخلی.
    
    Args:
        text: محتوای MDX
        mdx_files: لیست فایل‌های MDX برای بررسی لینک‌های بین‌فایلی
        assets_dir: پوشه assets برای بررسی لینک‌های تصویر
        
    Returns:
        LinkTestResult
    """
    links = extract_links(text)
    anchors = extract_anchors(text)
    
    internal_links = [l for l in links if l.is_internal]
    external_links = [l for l in links if not l.is_internal]
    anchor_links = [l for l in links if l.is_anchor]
    
    broken_internal = []
    broken_anchors = []
    
    # Check each internal link
    for link in internal_links:
        url = link.url
        
        # Anchor links
        if url.startswith('#'):
            anchor_id = url[1:]
            if anchor_id not in anchors:
                broken_anchors.append(url)
            continue
        
        # File links (.md or .mdx)
        if url.endswith(('.md', '.mdx')):
            if mdx_files:
                # Check if file exists
                found = any(f.name == url or f.stem == Path(url).stem for f in mdx_files)
                if not found:
                    broken_internal.append(url)
            continue
        
        # Asset links (images, etc.)
        if assets_dir and url.startswith(('images/', 'assets/', '/')):
            # Try relative to assets_dir
            asset_path = assets_dir / url.lstrip('/')
            if not asset_path.exists():
                broken_internal.append(url)
    
    return LinkTestResult(
        total_links=len(links),
        internal_links=len(internal_links),
        external_links=len(external_links),
        anchor_links=len(anchor_links),
        broken_internal=broken_internal,
        broken_anchors=broken_anchors,
    )


def validate_external_links(links: list[LinkInfo]) -> tuple[list[str], list[str]]:
    """
    اعتبارسنجی لینک‌های خارجی (بدون HTTP request).
    
    فقط فرمت را بررسی می‌کند، نه اینکه لینک واقعاً کار کند.
    
    Args:
        links: لیست لینک‌ها
        
    Returns:
        (invalid_format, mailto_links)
    """
    invalid_format = []
    mailto_links = []
    
    for link in links:
        if not link.is_internal:
            url = link.url
            
            # Check mailto
            if url.startswith('mailto:'):
                mailto_links.append(url)
                continue
            
            # Check valid URL format
            if not re.match(r'^https?://', url):
                invalid_format.append(url)
    
    return invalid_format, mailto_links


def test_all_links(
    text: str,
    mdx_files: list[Path] | None = None,
    assets_dir: Path | None = None,
) -> LinkTestResult:
    """
    تست تمام لینک‌ها.
    
    Args:
        text: محتوای MDX
        mdx_files: لیست فایل‌های MDX
        assets_dir: پوشه assets
        
    Returns:
        LinkTestResult
    """
    return validate_internal_links(text, mdx_files, assets_dir)
