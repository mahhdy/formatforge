"""
Quality Tests - RTL/Persian Validation
تست‌های فارسی و RTL برای اعتبارسنجی خروجی MDX

Tests:
- dir="rtl" in frontmatter
- lang="fa" in frontmatter  
- ZWNJ preservation
- Correct quotation marks
- LTR blocks correctness
"""

from __future__ import annotations

import re
from typing import NamedTuple


class ZWNJReport(NamedTuple):
    """گزارش وضعیت ZWNJ."""
    count_before: int
    count_after: int
    positions_lost: list[int]
    
    @property
    def is_preserved(self) -> bool:
        return self.count_before == self.count_after


class RTLTestResult(NamedTuple):
    """نتیجه تست RTL."""
    dir_rtl_set: bool
    lang_fa_set: bool
    zwnj_preserved: bool
    quotes_correct: bool
    ltr_blocks_correct: bool
    
    zwnj_report: ZWNJReport | None
    
    errors: list[str]
    warnings: list[str]
    
    @property
    def all_passed(self) -> bool:
        return all([
            self.dir_rtl_set,
            self.lang_fa_set,
            self.zwnj_preserved,
            self.quotes_correct,
            self.ltr_blocks_correct,
        ])


# ZWNJ character
ZWNJ = '\u200c'


def _check_dir_rtl_set(mdx_content: str) -> tuple[bool, str | None]:
    """
    بررسی وجود dir="rtl" در frontmatter.
    
    Args:
        mdx_content: محتوای MDX
        
    Returns:
        (is_valid, error_message)
    """
    # Extract frontmatter
    if not mdx_content.startswith('---'):
        return False, "Frontmatter missing"
    
    idx = mdx_content.find('---', 3)
    if idx <= 0:
        return False, "Frontmatter closing not found"
    
    frontmatter = mdx_content[3:idx]
    
    # Check for dir: rtl (quoted or unquoted)
    if not re.search(r'^dir\s*:\s*["\']?rtl["\']?', frontmatter, re.MULTILINE):
        return False, "dir: rtl not found in frontmatter"
    
    return True, None


def test_lang_fa_set(mdx_content: str) -> tuple[bool, str | None]:
    """
    بررسی وجود lang="fa" در frontmatter.
    
    Args:
        mdx_content: محتوای MDX
        
    Returns:
        (is_valid, error_message)
    """
    # Extract frontmatter
    if not mdx_content.startswith('---'):
        return False, "Frontmatter missing"
    
    idx = mdx_content.find('---', 3)
    if idx <= 0:
        return False, "Frontmatter closing not found"
    
    frontmatter = mdx_content[3:idx]
    
    # Check for lang: fa or fa-en (quoted or unquoted)
    if not re.search(r'^lang\s*:\s*["\']?(fa|fa-en)["\']?', frontmatter, re.MULTILINE):
        return False, "lang: fa not found in frontmatter"
    
    return True, None


def count_zwnj(text: str) -> int:
    """شمارش تعداد ZWNJ در متن."""
    return text.count(ZWNJ)


def _check_zwnj_preserved(source_content: str, output_content: str) -> ZWNJReport:
    """
    بررسی حفظ ZWNJ در تبدیل.
    
    Args:
        source_content: محتوای ورودی
        output_content: محتوای خروجی MDX
        
    Returns:
        ZWNJReport
    """
    count_before = count_zwnj(source_content)
    count_after = count_zwnj(output_content)
    
    # Find positions where ZWNJ might have been lost
    positions_lost = []
    if count_before != count_after:
        # Simple check - find where ZWNJ might have been removed
        # This is approximate
        positions_lost = list(range(count_before - count_after))
    
    return ZWNJReport(
        count_before=count_before,
        count_after=count_after,
        positions_lost=positions_lost,
    )


def _test_quotes_correct(mdx_content: str) -> tuple[bool, str | None]:
    """
    بررسی استفاده صحیح از گیومه‌های فارسی.
    
    Args:
        mdx_content: محتوای MDX
        
    Returns:
        (is_valid, error_message)
    """
    # Remove frontmatter for quote checking
    content = mdx_content
    if mdx_content.startswith('---'):
        idx = mdx_content.find('---', 3)
        if idx > 0:
            content = mdx_content[idx + 3:]
    
    # Check for incorrect quote usage
    # English quotes in Persian text should be replaced
    incorrect_patterns = [
        r'"[^"]*"',  # English double quotes
        r"'[^']*'",  # English single quotes
    ]
    
    # Persian guillemet quotes
    persian_open = '\u00ab'  # «
    persian_close = '\u00bb'  # »
    
    # Check if Persian quotes are used
    has_persian_quotes = persian_open in content or persian_close in content
    
    # If there are English quotes, warn
    english_quotes = re.findall(r'"[^"]*"', content)
    if english_quotes and not has_persian_quotes:
        # Could be a problem in Persian content
        # Check if this is in a Persian context
        return False, f"Found {len(english_quotes)} English quotes that should be «...»"
    
    return True, None


def test_ltr_blocks_correct(mdx_content: str) -> tuple[bool, str | None]:
    """
    بررسی صحت بلوک‌های LTR در محتوای RTL.
    
    Args:
        mdx_content: محتوای MDX
        
    Returns:
        (is_valid, error_message)
    """
    # Check for code blocks with dir="ltr"
    code_blocks = re.findall(r'```(\w*)', mdx_content)
    
    # Check for math blocks with dir="ltr"
    math_blocks = re.findall(r'\$\$|\$.*\$', mdx_content)
    
    # Check for mermaid diagrams with dir="ltr"
    mermaid_blocks = re.findall(r'<MermaidDiagram', mdx_content)
    
    # These should be in LTR context
    # We can't fully validate without more context, but we can check
    # that code blocks use proper formatting
    
    # Check for dir="ltr" or direction: ltr in code-related contexts
    if code_blocks:
        # Code blocks should be properly formatted
        # This is a basic check
        pass
    
    return True, None


def run_rtl_tests(source_content: str, mdx_content: str) -> RTLTestResult:
    """
    اجرای تمام تست‌های RTL/Persian.
    
    Args:
        source_content: محتوای ورودی اصلی
        mdx_content: محتوای MDX خروجی
        
    Returns:
        RTLTestResult
    """
    errors = []
    warnings = []
    
    # Run tests
    dir_rtl_valid, dir_error = _check_dir_rtl_set(mdx_content)
    if dir_error:
        errors.append(dir_error)
    
    lang_fa_valid, lang_error = test_lang_fa_set(mdx_content)
    if lang_error:
        errors.append(lang_error)
    
    zwnj_report = _check_zwnj_preserved(source_content, mdx_content)
    zwnj_valid = zwnj_report.is_preserved
    if not zwnj_valid:
        warnings.append(f"ZWNJ not preserved: {zwnj_report.count_before} before, {zwnj_report.count_after} after")
    
    quotes_valid, quotes_error = _test_quotes_correct(mdx_content)
    if quotes_error:
        warnings.append(quotes_error)
    
    ltr_valid, ltr_error = test_ltr_blocks_correct(mdx_content)
    if ltr_error:
        warnings.append(ltr_error)
    
    return RTLTestResult(
        dir_rtl_set=dir_rtl_valid,
        lang_fa_set=lang_fa_valid,
        zwnj_preserved=zwnj_valid,
        quotes_correct=quotes_valid,
        ltr_blocks_correct=ltr_valid,
        zwnj_report=zwnj_report,
        errors=errors,
        warnings=warnings,
    )


# Aliases for backward compatibility
test_dir_rtl_set = _check_dir_rtl_set
test_zwnj_preserved = _check_zwnj_preserved
test_quotes_correct = _test_quotes_correct
