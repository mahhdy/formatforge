"""Report Engine for FormatForge.

This module generates comprehensive reports from conversion and deployment
operations, including statistics, quality metrics, and visualizations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from formatforge.models.conversion_result import ConversionResult, ConversionStats
from formatforge.core.deployer.deployer import DeployReport


@dataclass
class ReportSummary:
    """Summary of a report.
    
    Attributes:
        total_documents: Total documents processed.
        successful: Number of successful operations.
        failed: Number of failed operations.
        duration_seconds: Total duration in seconds.
        average_quality: Average quality score.
    """
    total_documents: int = 0
    successful: int = 0
    failed: int = 0
    duration_seconds: float = 0.0
    average_quality: float = 0.0


@dataclass
class ReportConfig:
    """Configuration for report generation.
    
    Attributes:
        include_stats: Include statistics in report.
        include_quality: Include quality metrics.
        include_errors: Include error details.
        include_warnings: Include warning details.
        output_format: Output format (json, html, markdown).
    """
    include_stats: bool = True
    include_quality: bool = True
    include_errors: bool = True
    include_warnings: bool = True
    output_format: str = "json"


class ReportEngine:
    """Engine for generating reports from FormatForge operations.
    
    Supports multiple output formats and can aggregate data from
    conversion results, deployment reports, and quality checks.
    """
    
    def __init__(self, config: Optional[ReportConfig] = None):
        """Initialize the ReportEngine.
        
        Args:
            config: Report configuration.
        """
        self.config = config or ReportConfig()
    
    def generate_conversion_report(
        self,
        results: list[ConversionResult],
    ) -> dict:
        """Generate a report from conversion results.
        
        Args:
            results: List of conversion results.
            
        Returns:
            Report dictionary.
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "type": "conversion",
            "summary": {},
        }
        
        # Aggregate statistics
        total_docs = 0
        total_success = 0
        total_failed = 0
        total_duration = 0.0
        quality_scores = []
        
        for result in results:
            stats = result.stats
            total_docs += stats.total_documents
            total_success += stats.successful
            total_failed += stats.failed
            total_duration += stats.duration_seconds
            
            if stats.average_quality_score > 0:
                quality_scores.append(stats.average_quality_score)
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        report["summary"] = {
            "total_documents": total_docs,
            "successful": total_success,
            "failed": total_failed,
            "duration_seconds": total_duration,
            "average_quality": round(avg_quality, 1),
        }
        
        # Include detailed results if requested
        if self.config.include_errors or self.config.include_warnings:
            report["details"] = []
            
            for result in results:
                for doc in result.documents:
                    if self.config.include_errors and doc.status == "failed":
                        report["details"].append({
                            "document_id": doc.document_id,
                            "source_path": doc.source_path,
                            "status": doc.status,
                            "error": doc.error_message,
                        })
                    
                    if self.config.include_warnings and doc.quality.issues:
                        report["details"].append({
                            "document_id": doc.document_id,
                            "source_path": doc.source_path,
                            "status": doc.status,
                            "warnings": doc.quality.issues,
                        })
        
        return report
    
    def generate_deployment_report(
        self,
        deploy_reports: list[DeployReport],
    ) -> dict:
        """Generate a report from deployment reports.
        
        Args:
            deploy_reports: List of deployment reports.
            
        Returns:
            Report dictionary.
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "type": "deployment",
            "summary": {},
        }
        
        total_files = 0
        total_assets = 0
        errors = []
        warnings = []
        
        for dr in deploy_reports:
            total_files += dr.files_deployed
            total_assets += dr.assets_deployed
            
            if dr.errors:
                errors.extend(dr.errors)
            
            if dr.warnings:
                warnings.extend(dr.warnings)
        
        report["summary"] = {
            "total_files": total_files,
            "total_assets": total_assets,
            "total_deployments": len(deploy_reports),
            "errors_count": len(errors),
            "warnings_count": len(warnings),
        }
        
        if self.config.include_errors and errors:
            report["errors"] = errors
        
        if self.config.include_warnings and warnings:
            report["warnings"] = warnings
        
        return report
    
    def generate_combined_report(
        self,
        conversion_results: Optional[list[ConversionResult]] = None,
        deploy_reports: Optional[list[DeployReport]] = None,
    ) -> dict:
        """Generate a combined report from multiple sources.
        
        Args:
            conversion_results: Optional list of conversion results.
            deploy_reports: Optional list of deployment reports.
            
        Returns:
            Combined report dictionary.
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "type": "combined",
            "sections": {},
        }
        
        if conversion_results:
            report["sections"]["conversion"] = self.generate_conversion_report(
                conversion_results
            )
        
        if deploy_reports:
            report["sections"]["deployment"] = self.generate_deployment_report(
                deploy_reports
            )
        
        return report
    
    def save_report(
        self,
        report: dict,
        output_path: Path,
        format: Optional[str] = None,
    ) -> None:
        """Save report to file.
        
        Args:
            report: Report dictionary.
            output_path: Path to save the report.
            format: Output format (json, html, markdown). Uses config if not specified.
        """
        format = format or self.config.output_format
        output_path = Path(output_path)
        
        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        
        elif format == "markdown":
            content = self._render_markdown(report)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        
        elif format == "html":
            content = self._render_html(report)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
    
    def _render_markdown(self, report: dict) -> str:
        """Render report as Markdown."""
        lines = [
            f"# FormatForge Report",
            f"**Generated:** {report.get('timestamp', 'N/A')}",
            f"**Type:** {report.get('type', 'unknown').capitalize()}",
            "",
        ]
        
        if "summary" in report:
            lines.append("## Summary")
            for key, value in report["summary"].items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        if "details" in report:
            lines.append("## Details")
            for detail in report["details"][:10]:  # Limit to 10
                lines.append(f"- {detail.get('source_path', 'Unknown')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _render_html(self, report: dict) -> str:
        """Render report as HTML."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>FormatForge Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .error {{ color: red; }}
        .warning {{ color: orange; }}
    </style>
</head>
<body>
    <h1>FormatForge Report</h1>
    <p><strong>Generated:</strong> {report.get('timestamp', 'N/A')}</p>
    <p><strong>Type:</strong> {report.get('type', 'unknown').capitalize()}</p>
"""
        
        if "summary" in report:
            html += "    <h2>Summary</h2>\n    <div class='summary'>\n"
            for key, value in report["summary"].items():
                html += f"        <p><strong>{key}:</strong> {value}</p>\n"
            html += "    </div>\n"
        
        html += "</body>\n</html>"
        return html
