"""
Preflight Checker Module
ماژول بررسی پیش از تبدیل

Performs pre-flight checks on source documents
before conversion to identify potential issues.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple


class Issue(NamedTuple):
    """یک مشکل شناسایی‌شده."""
    level: str  # error, warning, info
    file: str
    line: int | None
    message: str
    suggestion: str | None = None


class PreflightReport(NamedTuple):
    """گزارش بررسی پیش از تبدیل."""
    issues: list[Issue]
    readiness_score: int  # 0-100
    can_proceed: bool
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "error")
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "warning")
    
    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "info")


class PreflightChecker:
    """بررسی‌کننده پیش از تبدیل."""
    
    def __init__(self, min_readiness: int = 70):
        """
        Args:
            min_readiness: حداقل امتیاز آمادگی برای ادامه
        """
        self.min_readiness = min_readiness
    
    def check(self, file_path: Path | str) -> PreflightReport:
        """
        اجرای تمام بررسی‌ها روی یک فایل.
        
        Args:
            file_path: مسیر فایل
            
        Returns:
            PreflightReport
        """
        path = Path(file_path)
        issues: list[Issue] = []
        
        # Run all checks
        issues.extend(self._check_encoding(path))
        issues.extend(self._check_structure(path))
        issues.extend(self._check_dependencies(path))
        issues.extend(self._check_content(path))
        
        # Calculate readiness score
        readiness = self._calculate_readiness(issues)
        can_proceed = readiness >= self.min_readiness and not any(
            i.level == "error" for i in issues
        )
        
        return PreflightReport(
            issues=issues,
            readiness_score=readiness,
            can_proceed=can_proceed,
        )
    
    def _check_encoding(self, path: Path) -> list[Issue]:
        """بررسی encoding فایل."""
        issues = []
        
        try:
            # Try UTF-8
            content = path.read_text(encoding='utf-8')
            
            # Check for BOM
            bytes_content = path.read_bytes()
            has_bom = bytes_content.startswith(b'\xef\xbb\xbf')
            
            # Check for ZWNJ
            zwnj_count = content.count('\u200c')
            
            # Check for common encoding issues
            if not has_bom:
                # Check for Persian characters that might be misencoded
                persian_chars = re.findall(r'[\u0600-\u06FF]', content)
                if persian_chars and zwnj_count == 0:
                    issues.append(Issue(
                        level="warning",
                        file=str(path),
                        line=None,
                        message="فایل حاوی کاراکترهای فارسی است اما نیم‌فاصله ندارد",
                        suggestion="نیم‌فاصله‌ها ممکن است در تبدیل از دست بروند"
                    ))
            
        except UnicodeDecodeError:
            issues.append(Issue(
                level="error",
                file=str(path),
                line=None,
                message="فایل با encoding UTF-8 قابل خواندن نیست",
                suggestion="فایل را به UTF-8 تبدیل کنید"
            ))
        
        return issues
    
    def _check_structure(self, path: Path) -> list[Issue]:
        """بررسی ساختار فایل."""
        issues = []
        
        suffix = path.suffix.lower()
        
        if suffix == '.tex':
            issues.extend(self._check_latex_structure(path))
        elif suffix in ('.html', '.htm'):
            issues.extend(self._check_html_structure(path))
        elif suffix == '.md':
            issues.extend(self._check_markdown_structure(path))
        
        return issues
    
    def _check_latex_structure(self, path: Path) -> list[Issue]:
        """بررسی ساختار LaTeX."""
        issues = []
        content = path.read_text(encoding='utf-8', errors='ignore')
        
        # Check for document environment
        if r'\begin{document}' not in content:
            issues.append(Issue(
                level="warning",
                file=str(path),
                line=None,
                message=r"\begin{document} یافت نشد",
                suggestion="فایل LaTeX باید محیط document داشته باشد"
            ))
        
        if r'\end{document}' not in content:
            issues.append(Issue(
                level="warning",
                file=str(path),
                line=None,
                message=r"\end{document} یافت نشد",
                suggestion="فایل LaTeX باید محیط document را ببندد"
            ))
        
        # Check for common issues
        # Unbalanced braces
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            issues.append(Issue(
                level="error",
                file=str(path),
                line=None,
                message=f"تعداد {{ ({open_braces}) با }} ({close_braces}) برابر نیست",
                suggestion="تمام آکولادها را بررسی کنید"
            ))
        
        # Check for unclosed environments
        env_pattern = r'\\begin\{(\w+)\}'
        envs = re.findall(env_pattern, content)
        for env in set(envs):
            if f'\\end{{{env}}}' not in content:
                issues.append(Issue(
                    level="error",
                    file=str(path),
                    line=None,
                    message=f"محیط {env} بسته نشده است",
                    suggestion=f"\\end{{{env}}} را اضافه کنید"
                ))
        
        return issues
    
    def _check_html_structure(self, path: Path) -> list[Issue]:
        """بررسی ساختار HTML."""
        issues = []
        
        try:
            from bs4 import BeautifulSoup
            content = path.read_text(encoding='utf-8', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check for basic structure
            if not soup.find('html'):
                issues.append(Issue(
                    level="warning",
                    file=str(path),
                    line=None,
                    message="تگ <html> یافت نشد",
                    suggestion="فایل باید تگ html داشته باشد"
                ))
            
            # Check for unclosed tags (basic check)
            # BeautifulSoup handles this but warns
            if soup.find():
                pass  # Basic structure exists
                
        except Exception as e:
            issues.append(Issue(
                level="error",
                file=str(path),
                line=None,
                message=f"خطا در parse کردن HTML: {e}",
                suggestion="ساختار HTML را بررسی کنید"
            ))
        
        return issues
    
    def _check_markdown_structure(self, path: Path) -> list[Issue]:
        """بررسی ساختار Markdown."""
        issues = []
        content = path.read_text(encoding='utf-8', errors='ignore')
        
        # Check frontmatter
        if content.startswith('---'):
            end_idx = content.find('---', 3)
            if end_idx <= 0:
                issues.append(Issue(
                    level="error",
                    file=str(path),
                    line=None,
                    message="frontmatter بسته نشده است",
                    suggestion="--- را در انتهای frontmatter اضافه کنید"
                ))
        
        return issues
    
    def _check_dependencies(self, path: Path) -> list[Issue]:
        """بررسی وابستگی‌ها (تصاویر، فایل‌های include شده)."""
        issues = []
        
        suffix = path.suffix.lower()
        
        if suffix == '.tex':
            content = path.read_text(encoding='utf-8', errors='ignore')
            
            # Check for \includegraphics references
            img_refs = re.findall(r'\\includegraphics(?:\[([^\]]*)\])?\{([^}]+)\}', content)
            for opts, img_path in img_refs:
                # Check if relative path exists
                img_file = path.parent / img_path
                if not img_file.exists() and not Path(img_path).is_absolute():
                    issues.append(Issue(
                        level="warning",
                        file=str(path),
                        line=None,
                        message=f"تصویر ارجاع‌شده یافت نشد: {img_path}",
                        suggestion="تصویر را در مسیر صحیح قرار دهید"
                    ))
        
        return issues
    
    def _check_content(self, path: Path) -> list[Issue]:
        """بررسی محتوا."""
        issues = []
        content = path.read_text(encoding='utf-8', errors='ignore')
        
        # Check for empty file
        if not content.strip():
            issues.append(Issue(
                level="error",
                file=str(path),
                line=None,
                message="فایل خالی است",
                suggestion="محتوا را به فایل اضافه کنید"
            ))
            return issues
        
        # Check for very large file
        size_mb = len(content.encode('utf-8')) / (1024 * 1024)
        if size_mb > 10:
            issues.append(Issue(
                level="warning",
                file=str(path),
                line=None,
                message=f"فایل بسیار بزرگ است: {size_mb:.1f} MB",
                suggestion="فایل را به بخش‌های کوچکتر تقسیم کنید"
            ))
        
        return issues
    
    def _calculate_readiness(self, issues: list[Issue]) -> int:
        """محاسبه امتیاز آمادگی."""
        if not issues:
            return 100
        
        # Start with 100
        score = 100
        
        # Deduct for each issue type
        for issue in issues:
            if issue.level == "error":
                score -= 15
            elif issue.level == "warning":
                score -= 5
            else:  # info
                score -= 1
        
        return max(0, score)


# Convenience function
def preflight_check(file_path: Path | str, min_readiness: int = 70) -> PreflightReport:
    """بررسی سریع پیش از تبدیل."""
    checker = PreflightChecker(min_readiness)
    return checker.check(file_path)
