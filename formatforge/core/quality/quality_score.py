"""
Quality Score Calculator
محاسبه امتیاز کیفیت 0-100

Based on the algorithm from the main prompt:
- Structure (25 points): frontmatter_valid, jsx_valid, imports_valid, encoding_valid, compiles_ok
- Content (25 points): headings_ratio, formulas_ratio, images_ratio, tables_ratio, code_ratio, words_ratio
- Math (20 points): math_parse_rate
- Persian/RTL (20 points): rtl_set, lang_set, zwnj_preserved, quotes_correct, bidi_correct
- Links (10 points): link_validity
"""

from __future__ import annotations

import re
from typing import NamedTuple


class ContentReport(NamedTuple):
    """گزارش محتوا."""
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
    words_source: int
    words_output: int


class QualityReport(NamedTuple):
    """گزارش کیفیت کامل."""
    score: int  # 0-100
    
    structure_score: float  # /25
    content_score: float   # /25
    math_score: float     # /20
    persian_score: float  # /20
    links_score: float    # /10
    
    # Details
    structural_passed: bool
    content_ratio: float
    math_parse_rate: float
    persian_tests_passed: float
    link_validity: float
    
    warnings: list[str]
    errors: list[str]
    
    @property
    def grade(self) -> str:
        """درجه‌بندی کیفیت."""
        if self.score >= 90:
            return "عالی ✅"
        elif self.score >= 75:
            return "خوب 🟡"
        elif self.score >= 50:
            return "متوسط 🟠"
        else:
            return "ضعیف 🔴"


def count_element(pattern: str, text: str) -> int:
    """شمارش تعداد الگو در متن."""
    return len(re.findall(pattern, text, re.MULTILINE | re.DOTALL))


def analyze_content(source: str, output: str) -> ContentReport:
    """
    تحلیل محتوای ورودی و خروجی.
    
    Args:
        source: محتوای ورودی
        output: محتوای MDX خروجی
        
    Returns:
        ContentReport
    """
    # Remove frontmatter from output for counting
    output_body = output
    if output.startswith('---'):
        idx = output.find('---', 3)
        if idx > 0:
            output_body = output[idx + 3:]
    
    # Count headings
    # LaTeX: \chapter, \section, \subsection, etc.
    headings_source = count_element(r'\\(chapter|section|subsection|subsubsection|paragraph)', source)
    # MDX/MD: #, ##, ###, etc.
    headings_output = count_element(r'^#{1,6}\s+', output_body)
    
    # Count formulas
    # LaTeX: $$, \[, equation, align
    formulas_source = (
        count_element(r'\$\$', source) +
        count_element(r'\\\[', source) +
        count_element(r'\\begin\{(equation|align|gather|multline)\}', source)
    )
    # MDX: $$, $
    formulas_output = count_element(r'\$\$|\$[^\$]+\$', output_body)
    
    # Count images
    # LaTeX: \includegraphics
    images_source = count_element(r'\\includegraphics', source)
    # MDX: <Figure>, ![]()
    images_output = (
        count_element(r'<Figure', output_body) +
        count_element(r'!\[', output_body)
    )
    
    # Count tables
    # LaTeX: \begin{tabular}, \begin{table}
    tables_source = count_element(r'\\begin\{(tabular|longtable|table)\}', source)
    # MDX: <table>, |---| pipe tables
    tables_output = (
        count_element(r'<table', output_body) +
        count_element(r'^\|', output_body)
    )
    
    # Count code blocks
    # LaTeX: \begin{lstlisting}, \begin{minted}
    code_blocks_source = (
        count_element(r'\\begin\{(lstlisting|minted|verbatim)\}', source) +
        count_element(r'```', source)
    )
    # MDX: ``` code blocks
    code_blocks_output = count_element(r'```', output_body)
    
    # Count words (rough)
    words_source = len(source.split())
    words_output = len(output_body.split())
    
    return ContentReport(
        headings_source=headings_source,
        headings_output=headings_output,
        formulas_source=formulas_source,
        formulas_output=formulas_output,
        images_source=images_source,
        images_output=images_output,
        tables_source=tables_source,
        tables_output=tables_output,
        code_blocks_source=code_blocks_source,
        code_blocks_output=code_blocks_output,
        words_source=words_source,
        words_output=words_output,
    )


def calculate_content_score(report: ContentReport) -> float:
    """
    محاسبه امتیاز محتوا (25 امتیاز).
    
    Args:
        report: گزارش محتوا
        
    Returns:
        امتیاز (0-25)
    """
    ratios = []
    
    # Heading ratio
    if report.headings_source > 0:
        ratios.append(min(1.0, report.headings_output / report.headings_source))
    
    # Formula ratio
    if report.formulas_source > 0:
        ratios.append(min(1.0, report.formulas_output / report.formulas_source))
    
    # Image ratio
    if report.images_source > 0:
        ratios.append(min(1.0, report.images_output / report.images_source))
    
    # Table ratio
    if report.tables_source > 0:
        ratios.append(min(1.0, report.tables_output / report.tables_source))
    
    # Code ratio
    if report.code_blocks_source > 0:
        ratios.append(min(1.0, report.code_blocks_output / report.code_blocks_source))
    
    # Word ratio (should be close to 1)
    if report.words_source > 0:
        word_ratio = report.words_output / report.words_source
        # Allow some variation (0.9 to 1.1)
        if 0.9 <= word_ratio <= 1.1:
            ratios.append(1.0)
        elif word_ratio < 0.9:
            ratios.append(word_ratio / 0.9)
        else:
            ratios.append(1.0 - (word_ratio - 1.1) / 0.1)
    
    if not ratios:
        return 25.0  # No content to compare
    
    avg_ratio = sum(ratios) / len(ratios)
    return avg_ratio * 25


def calculate_quality_score(
    source: str,
    output: str,
    structural_passed: bool = True,
    math_parse_rate: float = 1.0,
    persian_tests_passed: float = 1.0,
    link_validity: float = 1.0,
) -> QualityReport:
    """
    محاسبه امتیاز کیفیت کامل (0-100).
    
    Args:
        source: محتوای ورودی
        output: محتوای MDX خروجی
        structural_passed: آیا تست‌های ساختاری پاس شده‌اند
        math_parse_rate: نرخ parse شدن فرمول‌ها (0-1)
        persian_tests_passed: نرخ پاس شدن تست‌های فارسی (0-1)
        link_validity: اعتبار لینک‌ها (0-1)
        
    Returns:
        QualityReport
    """
    warnings = []
    errors = []
    
    # 1. Structure Score (25 points)
    structure_score = 25.0 if structural_passed else 0.0
    
    # 2. Content Score (25 points)
    content_report = analyze_content(source, output)
    # Calculate ratios - if source has 0, use 1.0 (not counted)
    ratios = []
    if content_report.headings_source > 0:
        ratios.append(content_report.headings_output / content_report.headings_source)
    if content_report.formulas_source > 0:
        ratios.append(content_report.formulas_output / content_report.formulas_source)
    if content_report.images_source > 0:
        ratios.append(content_report.images_output / content_report.images_source)
    if content_report.tables_source > 0:
        ratios.append(content_report.tables_output / content_report.tables_source)
    if content_report.code_blocks_source > 0:
        ratios.append(content_report.code_blocks_output / content_report.code_blocks_source)
    
    # If no content to compare, assume full score
    if not ratios:
        content_ratio = 1.0
    else:
        content_ratio = min(ratios)
    content_score = content_ratio * 25
    
    # Check for content warnings
    if content_report.formulas_source > 0 and content_report.formulas_output < content_report.formulas_source:
        warnings.append(f"Some formulas lost: {content_report.formulas_source} source → {content_report.formulas_output} output")
    
    if content_report.tables_source > 0 and content_report.tables_output < content_report.tables_source:
        warnings.append(f"Some tables lost: {content_report.tables_source} source → {content_report.tables_output} output")
    
    # 3. Math Score (20 points)
    math_score = math_parse_rate * 20
    
    # 4. Persian/RTL Score (20 points)
    persian_score = persian_tests_passed * 20
    
    # 5. Links Score (10 points)
    links_score = link_validity * 10
    
    # Total score
    total_score = int(round(
        structure_score + content_score + math_score + persian_score + links_score
    ))
    
    return QualityReport(
        score=total_score,
        structure_score=structure_score,
        content_score=content_score,
        math_score=math_score,
        persian_score=persian_score,
        links_score=links_score,
        structural_passed=structural_passed,
        content_ratio=content_ratio,
        math_parse_rate=math_parse_rate,
        persian_tests_passed=persian_tests_passed,
        link_validity=link_validity,
        warnings=warnings,
        errors=errors,
    )


def compute_score(quality_report: QualityReport) -> int:
    """
    محاسبه امتیاز (backward compatibility).
    
    Args:
        quality_report: گزارش کیفیت
        
    Returns:
        امتیاز (0-100)
    """
    return quality_report.score
