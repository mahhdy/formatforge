"""File Organizer for FormatForge deployment.

This module organizes the output files into the appropriate directory structure
for the target website (Next.js, Astro, Gatsby, etc.).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import shutil

from formatforge.models.conversion_result import ConversionResult, DocumentConversionResult


@dataclass
class OrganizedOutput:
    """Represents organized output structure for deployment.
    
    Attributes:
        base_path: The base output directory path.
        mdx_files: List of organized MDX file paths.
        asset_files: List of organized asset file paths.
        series_info: Series metadata if this is a book.
        bibliography_path: Path to bibliography JSON if exists.
    """
    base_path: Path
    mdx_files: list[Path] = field(default_factory=list)
    asset_files: list[Path] = field(default_factory=list)
    series_info: Optional[dict] = None
    bibliography_path: Optional[Path] = None


class FileOrganizer:
    """Organizes converted files into the target website structure.
    
    Supports different website frameworks:
    - Next.js: content/{slug}/index.mdx
    - Astro: src/content/docs/{slug}.mdx
    - Gatsby: content/{slug}/index.mdx
    - Docusaurus: docs/{slug}.mdx
    """
    
    FRAMEWORK_PATTERNS = {
        "next": {
            "article_dir": "{slug}/",
            "main_file": "index.mdx",
            "asset_dir": "{slug}/assets/",
        },
        "astro": {
            "article_dir": "{slug}/",
            "main_file": "index.mdx",
            "asset_dir": "assets/{slug}/",
        },
        "gatsby": {
            "article_dir": "{slug}/",
            "main_file": "index.mdx",
            "asset_dir": "assets/{slug}/",
        },
        "docusaurus": {
            "article_dir": "",
            "main_file": "{slug}.mdx",
            "asset_dir": "assets/{slug}/",
        },
    }
    
    def __init__(self, framework: str = "next", base_dir: Optional[Path] = None):
        """Initialize the FileOrganizer.
        
        Args:
            framework: Target website framework (next, astro, gatsby, docusaurus).
            base_dir: Base directory for output. Defaults to current directory.
        """
        self.framework = framework.lower()
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        
        if self.framework not in self.FRAMEWORK_PATTERNS:
            raise ValueError(
                f"Unknown framework: {framework}. "
                f"Supported: {list(self.FRAMEWORK_PATTERNS.keys())}"
            )
        
        self.pattern = self.FRAMEWORK_PATTERNS[self.framework]
    
    def organize(
        self,
        results: list[ConversionResult],
        output_dir: Path,
        config: Optional[dict] = None,
    ) -> OrganizedOutput:
        """Organize conversion results into the target directory structure.
        
        Args:
            results: List of conversion results to organize.
            output_dir: Target output directory.
            config: Additional configuration options.
            
        Returns:
            OrganizedOutput with all organized file paths.
        """
        config = config or {}
        output_dir = Path(output_dir)
        organized = OrganizedOutput(base_path=output_dir)
        
        # Process each conversion result
        for result in results:
            # Process each document within the conversion result
            for doc in result.documents:
                if doc.status != "success" or not doc.output_path:
                    continue
                
                # Determine document type from notes or source
                doc_type = self._infer_doc_type(doc, config)
                slug = doc.document_id or "unknown"
                
                # Determine directory structure based on document type
                if doc_type == "book" or doc_type == "chapter":
                    organized = self._organize_book(doc, output_dir, organized, config)
                else:
                    organized = self._organize_article(doc, output_dir, organized)
        
        return organized
    
    def _infer_doc_type(self, doc: DocumentConversionResult, config: dict) -> str:
        """Infer the document type from the document."""
        # Check notes for type hints
        for note in doc.notes:
            if "book" in note.lower():
                return "book"
            if "chapter" in note.lower():
                return "chapter"
        
        # Check source path for book indicators
        source = doc.source_path.lower()
        if "book" in source or "chapters" in source:
            return "book"
        
        return "article"
    
    def _organize_article(
        self,
        doc: DocumentConversionResult,
        output_dir: Path,
        organized: OrganizedOutput,
    ) -> OrganizedOutput:
        """Organize a single article into the output directory.
        
        Args:
            doc: Document conversion result.
            output_dir: Target output directory.
            organized: Current organized output state.
            
        Returns:
            Updated OrganizedOutput.
        """
        slug = doc.document_id or "unknown"
        
        # Create article directory
        article_dir = output_dir / self.pattern["article_dir"].format(slug=slug)
        article_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy main MDX file
        if doc.output_path:
            source_path = Path(doc.output_path)
            if source_path.exists():
                main_file = self.pattern["main_file"]
                dest_path = article_dir / main_file
                shutil.copy2(source_path, dest_path)
                organized.mdx_files.append(dest_path)
        
        return organized
    
    def _organize_book(
        self,
        doc: DocumentConversionResult,
        output_dir: Path,
        organized: OrganizedOutput,
        config: dict,
    ) -> OrganizedOutput:
        """Organize a book with chapters into the output directory.
        
        Args:
            doc: Document conversion result for the book.
            output_dir: Target output directory.
            organized: Current organized output state.
            config: Configuration options.
            
        Returns:
            Updated OrganizedOutput.
        """
        # For books, organize with series info
        organized.series_info = {
            "name": doc.document_id,
            "title": Path(doc.source_path).stem,
            "slug": doc.document_id,
        }
        
        # Process as article (single file or main entry)
        return self._organize_article(doc, output_dir, organized)
    
    def create_series_file(
        self,
        series_info: dict,
        output_dir: Path,
    ) -> Path:
        """Create a _series.json file for book series.
        
        Args:
            series_info: Series metadata information.
            output_dir: Directory to create the file in.
            
        Returns:
            Path to the created series.json file.
        """
        import json
        
        series_file = output_dir / "_series.json"
        
        series_data = {
            "title": series_info.get("title", ""),
            "slug": series_info.get("slug", ""),
            "chapters": series_info.get("chapters", []),
        }
        
        with open(series_file, "w", encoding="utf-8") as f:
            json.dump(series_data, f, ensure_ascii=False, indent=2)
        
        return series_file
