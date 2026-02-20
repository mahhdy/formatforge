"""Asset Manager for FormatForge deployment.

This module handles copying and managing assets (images, fonts, etc.)
during the deployment process.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import shutil


@dataclass
class AssetReport:
    """Report of asset management operations.
    
    Attributes:
        total_assets: Total number of assets processed.
        copied_assets: Number of assets successfully copied.
        skipped_assets: Number of assets skipped.
        failed_assets: List of assets that failed to copy.
        total_bytes: Total size of assets in bytes.
    """
    total_assets: int = 0
    copied_assets: int = 0
    skipped_assets: int = 0
    failed_assets: list[str] = field(default_factory=list)
    total_bytes: int = 0


class AssetManager:
    """Manages assets during the deployment process.
    
    Handles copying images, fonts, CSS, and other static assets
    to the appropriate locations in the output directory.
    """
    
    # Asset extensions to track
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"}
    FONT_EXTENSIONS = {".woff", ".woff2", ".ttf", ".otf", ".eot"}
    STYLE_EXTENSIONS = {".css", ".scss", ".sass"}
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize the AssetManager.
        
        Args:
            base_dir: Base directory for assets. Defaults to current directory.
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.report = AssetReport()
    
    def collect_assets(
        self,
        source_dirs: list[Path],
        asset_type: Optional[str] = None,
    ) -> list[Path]:
        """Collect asset files from source directories.
        
        Args:
            source_dirs: List of directories to search for assets.
            asset_type: Optional filter for asset type (image, font, style, all).
            
        Returns:
            List of asset file paths found.
        """
        assets = []
        allowed_exts = self._get_allowed_extensions(asset_type)
        
        for source_dir in source_dirs:
            if not source_dir.exists():
                continue
            
            for ext in allowed_exts:
                assets.extend(source_dir.rglob(f"*{ext}"))
        
        return assets
    
    def _get_allowed_extensions(self, asset_type: Optional[str]) -> set:
        """Get allowed file extensions based on asset type."""
        if asset_type == "image":
            return self.IMAGE_EXTENSIONS
        elif asset_type == "font":
            return self.FONT_EXTENSIONS
        elif asset_type == "style":
            return self.STYLE_EXTENSIONS
        else:
            return self.IMAGE_EXTENSIONS | self.FONT_EXTENSIONS | self.STYLE_EXTENSIONS
    
    def copy_assets(
        self,
        assets: list[Path],
        dest_dir: Path,
        flatten: bool = False,
    ) -> AssetReport:
        """Copy assets to the destination directory.
        
        Args:
            assets: List of asset paths to copy.
            dest_dir: Destination directory.
            flatten: If True, copy all assets to dest_dir directly.
                     If False, preserve directory structure.
        
        Returns:
            AssetReport with operation results.
        """
        self.report = AssetReport()
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        self.report.total_assets = len(assets)
        
        for asset in assets:
            try:
                if not asset.exists():
                    self.report.skipped_assets += 1
                    continue
                
                if flatten:
                    dest_path = dest_dir / asset.name
                else:
                    # Preserve relative structure
                    dest_path = dest_dir / asset.name
                
                # Avoid overwriting if same file
                if dest_path.exists():
                    # Add suffix to make unique
                    stem = dest_path.stem
                    suffix = dest_path.suffix
                    counter = 1
                    while dest_path.exists():
                        dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                
                shutil.copy2(asset, dest_path)
                self.report.copied_assets += 1
                self.report.total_bytes += asset.stat().st_size
                
            except Exception as e:
                self.report.failed_assets.append(str(asset))
        
        return self.report
    
    def organize_by_type(
        self,
        assets: list[Path],
        dest_dir: Path,
    ) -> dict[str, list[Path]]:
        """Organize assets into type-based subdirectories.
        
        Args:
            assets: List of asset paths to organize.
            dest_dir: Destination base directory.
            
        Returns:
            Dictionary mapping asset type to list of paths.
        """
        organized: dict[str, list[Path]] = {
            "images": [],
            "fonts": [],
            "styles": [],
            "other": [],
        }
        
        dest_dir = Path(dest_dir)
        
        for asset in assets:
            ext = asset.suffix.lower()
            dest_subdir = dest_dir
            
            if ext in self.IMAGE_EXTENSIONS:
                dest_subdir = dest_dir / "images"
                organized["images"].append(asset)
            elif ext in self.FONT_EXTENSIONS:
                dest_subdir = dest_dir / "fonts"
                organized["fonts"].append(asset)
            elif ext in self.STYLE_EXTENSIONS:
                dest_subdir = dest_dir / "styles"
                organized["styles"].append(asset)
            else:
                dest_subdir = dest_dir / "other"
                organized["other"].append(asset)
            
            dest_subdir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_subdir / asset.name
            shutil.copy2(asset, dest_path)
        
        return organized
