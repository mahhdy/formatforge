"""
Content Test Module
ماژول تست محتوا

Tests for element counting and content analysis.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class ContentTestResult(NamedTuple):
    """نتیجه تست محتوا."""
    headings_source: int
    headings_output: int
    formulas_source: int
    formulas_output: int
    images_source: int
    images_output: int
    tables_source: int
    tables_output: int
    code_blocks_source: int
    code_blocks_output: int
    zwnj_source: int
    zwnj_output: int
    
    @property
    def headings_ratio(self) -> float:
        if self.headings_source == 0:
            return 1.0
        return self.headings_output / self.headings_source
    
    @property
    def formulas_ratio(self) -> float:
        if self.formulas_source == 0:
            return 1.0
        return self.formulas_output / self.formulas_source
    
    @property
    def images_ratio(self) -> float:
        if self.images_source == 0:
            return 1.0
        return self.images_output / self.images_source
    
    @property
    def tables_ratio(self) -> float:
        if self.tables_source == 0:
            return 1.0
        return self.tables_output / self.tables_source
    
    @property
    def code_ratio(self) -> float:
        if self.code_blocks_source == 0:
            return 1.0
        return self.code_blocks_output / self.code_blocks_source
    
    @property
    def zwnj_ratio(self) -> float:
        if self.zwnj_source == 0:
            return 1.0
        return self.zwnj_output / self.zwnj_source
    
    @property
    def all_passed(self) -> bool:
        return all([
            self.headings_ratio >= 0.9,
            self.formulas_ratio >= 0.9,
            self.zwnj_ratio == 1.0,
        ])


ZWNJ = '\u200c'


def count_headings(text: str) -> int:
    """شمارش تعداد عناوین."""
    # Markdown headings
    headings = len(re.findall(r'^#{1,6}\s+.+$', text, re.MULTILINE))
    return headings


def count_formulas(text: str) -> int:
    """شمارش تعداد فرمول‌ها."""
    # Inline math: $...$
    inline = len(re.findall(r'\$.*?\$', text))
    
    # Display math: $$...$$ or \[...\]
    display = len(re.findall(r'\$\$.*?\$\$', text, re.DOTALL))
    display += len(re.findall(r'\\\[.*?\\\]', text, re.DOTALL))
    
    return inline + display


def count_images(text: str) -> int:
    """شمارش تعداد تصاویر."""
    # Markdown: ![alt](src)
    md_images = len(re.findall(r'!\[.*?\]\(.*?\)', text))
    
    # MDX: <Image src=... />
    mdx_images = len(re.findall(r'<Image\s+src=', text))
    
    # HTML: <img src=...>
    html_images = len(re.findall(r'<img\s+[^>]*src=', text, re.IGNORECASE))
    
    return md_images + mdx_images + html_images


def count_tables(text: str) -> int:
    """شمارش تعداد جداول."""
    # Markdown tables: |---|
    md_tables = len(re.findall(r'^\|.+\|$', text, re.MULTILINE))
    
    # MDX/HTML tables
    html_tables = len(re.findall(r'<table[^>]*>', text, re.IGNORECASE))
    
    return md_tables + html_tables


def count_code_blocks(text: str) -> int:
    """شمارش تعداد بلوک‌های کد."""
    # Markdown: ```language
    code_blocks = len(re.findall(r'```\w*', text))
    
    # HTML: <pre><code> or <code>
    html_code = len(re.findall(r'<pre><code|<code', text, re.IGNORECASE))
    
    return code_blocks + html_code


def count_zwnj(text: str) -> int:
    """شمارش تعداد ZWNJ."""
    return text.count(ZWNJ)


def analyze_content(source: str, output: str) -> ContentTestResult:
    """
    تحلیل و مقایسه محتوای ورودی و خروجی.
    
    Args:
        source: محتوای ورودی اصلی
        output: محتوای MDX خروجی
        
    Returns:
        ContentTestResult
    """
    return ContentTestResult(
        headings_source=count_headings(source),
        headings_output=count_headings(output),
        formulas_source=count_formulas(source),
        formulas_output=count_formulas(output),
        images_source=count_images(source),
        images_output=count_images(output),
        tables_source=count_tables(source),
        tables_output=count_tables(output),
        code_blocks_source=count_code_blocks(source),
        code_blocks_output=count_code_blocks(output),
        zwnj_source=count_zwnj(source),
        zwnj_output=count_zwnj(output),
    )


def test_content_preservation(source: str, output: str) -> tuple[bool, list[str]]:
    """
    تست حفظ محتوا.
    
    Args:
        source: محتوای ورودی
        output: محتوای خروجی
        
    Returns:
        (is_valid, list_of_issues)
    """
    result = analyze_content(source, output)
    issues = []
    
    # Check ratios
    if result.headings_ratio < 0.9:
        issues.append(f"Headings ratio low: {result.headings_ratio:.1%}")
    
    if result.formulas_ratio < 0.9:
        issues.append(f"Formulas ratio low: {result.formulas_ratio:.1%}")
    
    if result.zwnj_ratio < 1.0:
        issues.append(f"ZWNJ lost: {result.zwnj_source} → {result.zwnj_output}")
    
    return len(issues) == 0, issues
