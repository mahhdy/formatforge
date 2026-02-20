"""Main Deployer for FormatForge.

This module orchestrates the deployment process, coordinating between
file organization and asset management.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

from formatforge.core.deployer.file_organizer import FileOrganizer, OrganizedOutput
from formatforge.core.deployer.asset_manager import AssetManager, AssetReport
from formatforge.models.conversion_result import ConversionResult


@dataclass
class DeployReport:
    """Report of deployment operations.
    
    Attributes:
        timestamp: ISO timestamp of deployment.
        source_dir: Source directory path.
        dest_dir: Destination directory path.
        framework: Target website framework.
        files_deployed: Number of MDX files deployed.
        assets_deployed: Number of assets deployed.
        errors: List of deployment errors.
        warnings: List of deployment warnings.
    """
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source_dir: str = ""
    dest_dir: str = ""
    framework: str = "next"
    files_deployed: int = 0
    assets_deployed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "timestamp": self.timestamp,
            "source_dir": self.source_dir,
            "dest_dir": self.dest_dir,
            "framework": self.framework,
            "files_deployed": self.files_deployed,
            "assets_deployed": self.assets_deployed,
            "errors": self.errors,
            "warnings": self.warnings,
        }
    
    def save(self, output_path: Path) -> None:
        """Save report to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class Deployer:
    """Main deployment orchestrator for FormatForge.
    
    Coordinates file organization and asset management to deploy
    converted MDX files to the target website directory.
    """
    
    def __init__(
        self,
        framework: str = "next",
        base_dir: Optional[Path] = None,
    ):
        """Initialize the Deployer.
        
        Args:
            framework: Target website framework (next, astro, gatsby, docusaurus).
            base_dir: Base directory for operations.
        """
        self.framework = framework
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        
        self.file_organizer = FileOrganizer(framework=framework, base_dir=self.base_dir)
        self.asset_manager = AssetManager(base_dir=self.base_dir)
        self.report = DeployReport(framework=framework)
    
    def deploy(
        self,
        conversion_results: list[ConversionResult],
        source_dir: Path,
        dest_dir: Path,
        config: Optional[dict] = None,
    ) -> DeployReport:
        """Deploy converted files to the destination directory.
        
        Args:
            conversion_results: List of conversion results to deploy.
            source_dir: Source directory containing converted files.
            dest_dir: Destination directory for deployment.
            config: Additional deployment configuration.
            
        Returns:
            DeployReport with deployment results.
        """
        config = config or {}
        source_dir = Path(source_dir)
        dest_dir = Path(dest_dir)
        
        # Initialize report
        self.report = DeployReport(
            framework=self.framework,
            source_dir=str(source_dir),
            dest_dir=str(dest_dir),
        )
        
        try:
            # Ensure destination exists
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Organize MDX files
            organized = self.file_organizer.organize(
                results=conversion_results,
                output_dir=dest_dir,
                config=config,
            )
            
            self.report.files_deployed = len(organized.mdx_files)
            
            # Collect and copy assets
            asset_dirs = [source_dir / "assets", source_dir / "figures"]
            assets = self.asset_manager.collect_assets(asset_dirs)
            
            if assets:
                asset_dest = dest_dir / "assets"
                asset_report = self.asset_manager.copy_assets(
                    assets=assets,
                    dest_dir=asset_dest,
                    flatten=config.get("flatten_assets", False),
                )
                self.report.assets_deployed = asset_report.copied_assets
                
                if asset_report.failed_assets:
                    self.report.warnings.extend(
                        f"Failed to copy asset: {a}" for a in asset_report.failed_assets
                    )
            
            # Create series file if needed
            if organized.series_info:
                self.file_organizer.create_series_file(
                    series_info=organized.series_info,
                    output_dir=dest_dir,
                )
            
        except Exception as e:
            self.report.errors.append(str(e))
        
        return self.report
    
    def deploy_single(
        self,
        source_file: Path,
        dest_dir: Path,
        slug: Optional[str] = None,
    ) -> DeployReport:
        """Deploy a single MDX file.
        
        Args:
            source_file: Source MDX file path.
            dest_dir: Destination directory.
            slug: Optional slug for the file.
            
        Returns:
            DeployReport with deployment results.
        """
        source_file = Path(source_file)
        dest_dir = Path(dest_dir)
        
        self.report = DeployReport(
            framework=self.framework,
            source_dir=str(source_file.parent),
            dest_dir=str(dest_dir),
        )
        
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine destination path based on framework
            if self.framework == "docusaurus":
                filename = f"{slug or source_file.stem}.mdx"
                dest_path = dest_dir / filename
            else:
                article_dir = dest_dir / (slug or source_file.stem)
                article_dir.mkdir(parents=True, exist_ok=True)
                dest_path = article_dir / "index.mdx"
            
            import shutil
            shutil.copy2(source_file, dest_path)
            
            self.report.files_deployed = 1
            
        except Exception as e:
            self.report.errors.append(str(e))
        
        return self.report
    
    def verify_deployment(self, dest_dir: Path) -> bool:
        """Verify that deployment was successful.
        
        Args:
            dest_dir: Directory to verify.
            
        Returns:
            True if deployment appears valid.
        """
        dest_dir = Path(dest_dir)
        
        if not dest_dir.exists():
            return False
        
        # Check for MDX files
        mdx_files = list(dest_dir.rglob("*.mdx"))
        return len(mdx_files) > 0
