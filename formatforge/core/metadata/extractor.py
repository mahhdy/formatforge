"""
Metadata Extractor Module
ماژول استخراج متادیتا

Extracts metadata from various input formats.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from formatforge.models.metadata import DocumentMetadata, AuthorInfo


class MetadataExtractor:
    """
    استخراج متادیتا از فرمت‌های مختلف.
    """
    
    # Format-specific extractors
    FORMAT_EXTRACTORS: dict[str, callable] = {}
    
    @classmethod
    def register(cls, format_name: str):
        """Decorator to register a format extractor."""
        def decorator(func: callable):
            cls.FORMAT_EXTRACTORS[format_name] = func
            return func
        return decorator
    
    @classmethod
    def extract(cls, file_path: Path | str, format: str | None = None) -> DocumentMetadata:
        """
        استخراج متادیتا از فایل.
        
        Args:
            file_path: مسیر فایل
            format: فرمت فایل (اگر None باشد، از پسوند تشخیص داده می‌شود)
            
        Returns:
            DocumentMetadata
        """
        if format is None:
            format = cls._detect_format(file_path)
        
        extractor = cls.FORMAT_EXTRACTORS.get(format)
        if extractor is None:
            # Default extractor
            return cls._extract_default(file_path)
        
        return extractor(file_path)
    
    @classmethod
    def _detect_format(cls, file_path: Path | str) -> str:
        """تشخیص فرمت از پسوند فایل."""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        format_map = {
            '.tex': 'latex',
            '.latex': 'latex',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.mdx': 'markdown',
            '.html': 'html',
            '.htm': 'html',
            '.xhtml': 'html',
            '.docx': 'docx',
            '.pdf': 'pdf',
            '.rst': 'rst',
            '.adoc': 'asciidoc',
            '.asciidoc': 'asciidoc',
            '.epub': 'epub',
            '.ipynb': 'notebook',
            '.nb': 'notebook',
        }
        
        return format_map.get(ext, 'unknown')
    
    @classmethod
    def _extract_default(cls, file_path: Path | str) -> DocumentMetadata:
        """استخراج پیش‌فرض - فقط عنوان از نام فایل."""
        path = Path(file_path)
        title = path.stem.replace('-', ' ').replace('_', ' ').title()
        
        return DocumentMetadata(
            title=title,
            slug=cls._generate_slug(title),
            lang='en',
            dir='ltr',
        )
    
    @staticmethod
    def _generate_slug(title: str) -> str:
        """تولید slug از عنوان."""
        # Replace spaces with hyphens, lowercase
        slug = re.sub(r'[^\w\s-]', '', title)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.lower().strip('-')


# Register LaTeX extractor
@MetadataExtractor.register('latex')
def extract_latex_metadata(file_path: Path | str) -> DocumentMetadata:
    """استخراج متادیتا از LaTeX."""
    from formatforge.core.converters.latex_parser import LatexParser
    
    path = Path(file_path)
    content = path.read_text(encoding='utf-8', errors='ignore')
    
    parser = LatexParser()
    doc = parser.parse(content)
    
    # Extract basic metadata
    title = doc.preamble.get('title', path.stem) if hasattr(doc.preamble, 'get') else path.stem
    author_str = doc.preamble.get('author', '') if hasattr(doc.preamble, 'get') else ''
    date_str = doc.preamble.get('date', '') if hasattr(doc.preamble, 'get') else ''
    
    # Detect language
    lang = 'fa' if any([
        'xepersian' in content.lower(),
        'persian' in content.lower(),
        '\u06a9' in content,  # ک
        '\u06cc' in content,  # ی
    ]) else 'en'
    
    # Detect features
    has_math = bool(re.search(r'\$|\\begin\{(equation|align|gather)', content))
    has_code = bool(re.search(r'\\begin\{(lstlisting|minted|verbatim)', content))
    has_tikz = bool(re.search(r'\\begin\{tikzpicture\}', content))
    
    # Build author
    author = None
    if author_str:
        author = AuthorInfo(name=author_str)
    
    return DocumentMetadata(
        title=title,
        slug=MetadataExtractor._generate_slug(title),
        lang=lang,
        dir='rtl' if lang == 'fa' else 'ltr',
        author=author,
        date=date_str or '2025-01-01',
        sourceFormat='latex',
        sourceFile=path.name,
        math=has_math,
        codeHighlight=has_code,
    )


# Register Markdown extractor
@MetadataExtractor.register('markdown')
def extract_markdown_metadata(file_path: Path | str) -> DocumentMetadata:
    """استخراج متادیتا از Markdown."""
    path = Path(file_path)
    content = path.read_text(encoding='utf-8', errors='ignore')
    
    # Extract frontmatter
    if content.startswith('---'):
        end_idx = content.find('---', 3)
        if end_idx > 0:
            frontmatter = content[3:end_idx]
            title = re.search(r'^title:\s*(.+)$', frontmatter, re.MULTILINE)
            title = title.group(1).strip('"\'') if title else path.stem
            
            lang_match = re.search(r'^lang:\s*(.+)$', frontmatter, re.MULTILINE)
            lang = lang_match.group(1).strip('"\'') if lang_match else 'en'
            
            return DocumentMetadata(
                title=title,
                slug=MetadataExtractor._generate_slug(title),
                lang=lang,
                dir='rtl' if lang == 'fa' else 'ltr',
                sourceFormat='markdown',
                sourceFile=path.name,
                date='2025-01-01',
            )
    
    # No frontmatter - use filename
    title = path.stem.replace('-', ' ').replace('_', ' ').title()
    return DocumentMetadata(
        title=title,
        slug=MetadataExtractor._generate_slug(title),
        lang='en',
        dir='ltr',
        sourceFormat='markdown',
        sourceFile=path.name,
        date='2025-01-01',
    )


# Register HTML extractor
@MetadataExtractor.register('html')
def extract_html_metadata(file_path: Path | str) -> DocumentMetadata:
    """استخراج متادیتا از HTML."""
    from bs4 import BeautifulSoup
    
    path = Path(file_path)
    content = path.read_text(encoding='utf-8', errors='ignore')
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Extract title
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else path.stem
    
    # Extract meta tags
    meta = {}
    for tag in soup.find_all('meta'):
        name = tag.get('name') or tag.get('property', '')
        content_val = tag.get('content', '')
        if name:
            meta[name] = content_val
    
    # Detect language
    html_lang = soup.html.get('lang') if soup.html else None
    lang = str(html_lang) if html_lang else 'en'
    
    return DocumentMetadata(
        title=title,
        slug=MetadataExtractor._generate_slug(title),
        lang=lang,
        dir='rtl' if lang == 'fa' else 'ltr',
        description=meta.get('description', ''),
        sourceFormat='html',
        sourceFile=path.name,
        date='2025-01-01',
    )


# Register DOCX extractor
@MetadataExtractor.register('docx')
def extract_docx_metadata(file_path: Path | str) -> DocumentMetadata:
    """استخراج متادیتا از DOCX."""
    try:
        import docx
    except ImportError:
        return MetadataExtractor._extract_default(file_path)
    
    path = Path(file_path)
    
    try:
        doc = docx.Document(str(path))
        
        # Core properties
        core_props = doc.core_properties
        
        title = core_props.title or path.stem
        author_str = core_props.author or ''
        date_str = str(core_props.created.date()) if core_props.created else ''
        
        # Build author
        author = None
        if author_str:
            author = AuthorInfo(name=author_str)
        
        return DocumentMetadata(
            title=title,
            slug=MetadataExtractor._generate_slug(title),
            lang='en',  # Need to detect
            dir='ltr',
            author=author,
            date=date_str or '2025-01-01',
            sourceFormat='docx',
            sourceFile=path.name,
        )
    except Exception:
        return MetadataExtractor._extract_default(file_path)
