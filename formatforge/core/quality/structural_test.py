"""
Quality Tests - Structural Validation
تست‌های ساختاری برای اعتبارسنجی خروجی MDX

Tests:
- Frontmatter YAML validity
- JSX syntax correctness
- Import validation
- Encoding check
- MDX compilation
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple


class StructuralTestResult(NamedTuple):
    """نتیجه تست ساختاری."""
    frontmatter_valid: bool
    jsx_valid: bool
    imports_valid: bool
    encoding_valid: bool
    mdx_compiles: bool
    
    errors: list[str]
    warnings: list[str]
    
    @property
    def all_passed(self) -> bool:
        return all([
            self.frontmatter_valid,
            self.jsx_valid,
            self.imports_valid,
            self.encoding_valid,
            self.mdx_compiles,
        ])


def check_frontmatter_valid(mdx_content: str) -> tuple[bool, str | None]:
    """
    بررسی اعتبار frontmatter.
    
    Args:
        mdx_content: محتوای MDX
        
    Returns:
        (is_valid, error_message)
    """
    # Check for frontmatter delimiters
    if not mdx_content.startswith('---'):
        return False, "Frontmatter missing: expected --- at start"
    
    # Find second delimiter
    lines = mdx_content.split('\n')
    second_delimiter_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            second_delimiter_idx = i
            break
    
    if second_delimiter_idx is None:
        return False, "Frontmatter closing --- not found"
    
    # Extract frontmatter content
    frontmatter_lines = lines[1:second_delimiter_idx]
    frontmatter_text = '\n'.join(frontmatter_lines)
    
    # Basic YAML validation (check for key: value pairs)
    # Look for required fields
    required_fields = ['title', 'date', 'lang']
    for field in required_fields:
        if not re.search(rf'^{field}\s*:', frontmatter_text, re.MULTILINE):
            return False, f"Required frontmatter field '{field}' is missing"
    
    # Check for proper YAML syntax (no tabs, proper indentation)
    if '\t' in frontmatter_text:
        return False, "Frontmatter contains tabs (use spaces for indentation)"
    
    return True, None


def check_jsx_syntax(mdx_content: str) -> tuple[bool, str | None]:
    """
    بررسی اعتبار syntax JSX.
    
    Args:
        mdx_content: محتوای MDX
        
    Returns:
        (is_valid, error_message)
    """
    # Remove frontmatter for JSX testing
    content = mdx_content
    if mdx_content.startswith('---'):
        idx = mdx_content.find('---', 3)
        if idx > 0:
            content = mdx_content[idx + 3:]
    
    # Check for common JSX issues
    
    # 1. class → className (but not in strings)
    lines = content.split('\n')
    in_string = False
    for line_num, line in enumerate(lines, 1):
        for char_idx, char in enumerate(line):
            if char in ('"', "'", '`'):
                in_string = not in_string
            
            # Check for class= outside of strings
            if not in_string and 'class=' in line:
                # Make sure it's not className already
                match = re.search(r'class=(["\'])(?!Name)', line)
                if match:
                    return False, f"Line {line_num}: use className instead of class"
    
    # 2. Check for unclosed tags
    open_tags = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)[^/>]*>', content)
    close_tags = re.findall(r'</([a-zA-Z][a-zA-Z0-9]*)>', content)
    
    # Simple check - count opening and closing tags
    # This is simplified; a full parser would be better
    for tag in ['div', 'span', 'section', 'article']:
        open_count = open_tags.count(tag)
        close_count = close_tags.count(tag)
        # Allow self-closing tags
        if open_count > close_count + 5:  # Allow some self-closing
            return False, f"Possible unclosed <{tag}> tags"
    
    return True, None


def test_imports_valid(mdx_content: str) -> tuple[bool, str | None]:
    """
    بررسی اعتبار import ها.
    
    Args:
        mdx_content: محتوای MDX
        
    Returns:
        (is_valid, error_message)
    """
    # Extract imports section (between frontmatter and content)
    content = mdx_content
    if mdx_content.startswith('---'):
        idx = mdx_content.find('---', 3)
        if idx > 0:
            content = mdx_content[idx + 3:]
    
    # Find import statements
    import_pattern = r"^import\s+.*\s+from\s+['\"].+['\"]"
    imports = re.findall(import_pattern, content, re.MULTILINE)
    
    # Check for required imports based on content
    required_imports = {
        'Theorem': r'<Theorem',
        'Definition': r'<Definition',
        'Proof': r'<Proof',
        'Admonition': r'<Admonition',
        'Figure': r'<Figure',
        'MermaidDiagram': r'<MermaidDiagram',
        'Citation': r'<Citation\b',
        'CrossRef': r'<CrossRef',
    }
    
    for component, pattern in required_imports.items():
        if re.search(pattern, content):
            # Check if import exists
            if not re.search(rf"import\s+.*{component}.*from", content):
                return False, f"Component <{component}> used but not imported"
    
    return True, None


def test_encoding(path: Path) -> tuple[bool, str | None]:
    """
    بررسی encoding فایل.
    
    Args:
        path: مسیر فایل MDX
        
    Returns:
        (is_valid, error_message)
    """
    try:
        # Read as bytes to check BOM
        with open(path, 'rb') as f:
            raw = f.read(4)
        
        # Check for UTF-8 BOM
        if raw[:3] == b'\xef\xbb\xbf':
            return True, None  # UTF-8 with BOM - good
        
        # Try to decode as UTF-8
        with open(path, 'r', encoding='utf-8') as f:
            f.read()
        
        return True, None
        
    except UnicodeDecodeError as e:
        return False, f"Encoding error: {e}"
    except Exception as e:
        return False, f"Cannot read file: {e}"


def test_mdx_compiles(mdx_content: str) -> tuple[bool, str | None]:
    """
    بررسی اینکه MDX قابل compile است.
    
    این یک check ساده است - در عمل نیاز به MDX runtime داریم.
    
    Args:
        mdx_content: محتوای MDX
        
    Returns:
        (is_valid, error_message)
    """
    # Basic syntax checks that don't require full MDX compiler
    
    # Check for common syntax errors
    errors = []
    
    # 1. Check for unclosed braces in JSX expressions
    open_braces = mdx_content.count('{')
    close_braces = mdx_content.count('}')
    if open_braces != close_braces:
        errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
    
    # 2. Check for unclosed brackets in imports
    if mdx_content.startswith('---'):
        idx = mdx_content.find('---', 3)
        if idx > 0:
            import_section = mdx_content[idx + 3:]
            # Remove strings to avoid false positives
            import_section = re.sub(r'"[^"]*"', '', import_section)
            import_section = re.sub(r"'[^']*'", '', import_section)
            
            open_brackets = import_section.count('[')
            close_brackets = import_section.count(']')
            if open_brackets != close_brackets:
                errors.append(f"Unbalanced brackets in imports")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, None


def run_structural_tests(mdx_content: str, file_path: Path | None = None) -> StructuralTestResult:
    """
    اجرای تمام تست‌های ساختاری.
    
    Args:
        mdx_content: محتوای MDX
        file_path: مسیر فایل (اختیاری)
        
    Returns:
        StructuralTestResult
    """
    errors = []
    warnings = []
    
    # Run all tests
    frontmatter_valid, frontmatter_error = check_frontmatter_valid(mdx_content)
    if frontmatter_error:
        errors.append(frontmatter_error)
    
    jsx_valid, jsx_error = check_jsx_syntax(mdx_content)
    if jsx_error:
        errors.append(jsx_error)
    
    imports_valid, imports_error = test_imports_valid(mdx_content)
    if imports_error:
        errors.append(imports_error)
    
    encoding_valid = True
    if file_path:
        encoding_valid, encoding_error = test_encoding(file_path)
        if encoding_error:
            errors.append(encoding_error)
    
    mdx_compiles, compile_error = test_mdx_compiles(mdx_content)
    if compile_error:
        errors.append(compile_error)
    
    return StructuralTestResult(
        frontmatter_valid=frontmatter_valid,
        jsx_valid=jsx_valid,
        imports_valid=imports_valid,
        encoding_valid=encoding_valid,
        mdx_compiles=mdx_compiles,
        errors=errors,
        warnings=warnings,
    )


# Aliases for backward compatibility
test_frontmatter_valid = check_frontmatter_valid
test_jsx_syntax = check_jsx_syntax
test_imports_valid = test_imports_valid
test_mdx_compiles = test_mdx_compiles
