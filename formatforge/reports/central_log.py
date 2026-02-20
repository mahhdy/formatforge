"""Central Logging for FormatForge.

This module provides centralized logging for all FormatForge operations,
with support for structured logging and log levels.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import logging
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Single log entry.
    
    Attributes:
        timestamp: ISO timestamp of the log entry.
        level: Log level.
        module: Module where the log was generated.
        message: Log message.
        context: Additional context data.
    """
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    level: str = "INFO"
    module: str = ""
    message: str = ""
    context: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "module": self.module,
            "message": self.message,
            "context": self.context,
        }


class CentralLog:
    """Centralized logging for FormatForge.
    
    Provides structured logging with support for file output,
    console output, and log rotation.
    """
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        log_level: str = "INFO",
        console_output: bool = True,
    ):
        """Initialize the CentralLog.
        
        Args:
            log_dir: Directory for log files. Defaults to ./logs.
            log_level: Minimum log level to record.
            console_output: Whether to output to console.
        """
        self.log_dir = log_dir or Path("logs")
        self.log_level = getattr(logging, log_level.upper())
        self.console_output = console_output
        
        self.entries: list[LogEntry] = []
        
        # Set up Python logger
        self.logger = logging.getLogger("formatforge")
        self.logger.setLevel(self.log_level)
        
        if console_output:
            handler = logging.StreamHandler()
            handler.setLevel(self.log_level)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log(
        self,
        level: str,
        message: str,
        module: str = "",
        context: Optional[dict] = None,
    ) -> None:
        """Log a message.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            message: Log message.
            module: Module generating the log.
            context: Additional context data.
        """
        entry = LogEntry(
            level=level,
            module=module,
            message=message,
            context=context or {},
        )
        
        self.entries.append(entry)
        
        # Log to Python logger
        log_method = getattr(self.logger, level.lower())
        log_method(f"[{module}] {message}")
    
    def debug(self, message: str, module: str = "", context: Optional[dict] = None) -> None:
        """Log debug message."""
        self.log("DEBUG", message, module, context)
    
    def info(self, message: str, module: str = "", context: Optional[dict] = None) -> None:
        """Log info message."""
        self.log("INFO", message, module, context)
    
    def warning(self, message: str, module: str = "", context: Optional[dict] = None) -> None:
        """Log warning message."""
        self.log("WARNING", message, module, context)
    
    def error(self, message: str, module: str = "", context: Optional[dict] = None) -> None:
        """Log error message."""
        self.log("ERROR", message, module, context)
    
    def critical(self, message: str, module: str = "", context: Optional[dict] = None) -> None:
        """Log critical message."""
        self.log("CRITICAL", message, module, context)
    
    def save(self, filename: Optional[str] = None) -> Path:
        """Save logs to file.
        
        Args:
            filename: Optional filename. Defaults to formatforge_YYYYMMDD_HHMMSS.log.
            
        Returns:
            Path to the saved log file.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"formatforge_{timestamp}.log"
        
        log_path = self.log_dir / filename
        
        with open(log_path, "w", encoding="utf-8") as f:
            for entry in self.entries:
                f.write(f"[{entry.timestamp}] {entry.level} [{entry.module}] {entry.message}\n")
                if entry.context:
                    f.write(f"  Context: {json.dumps(entry.context, ensure_ascii=False)}\n")
        
        return log_path
    
    def get_entries(
        self,
        level: Optional[str] = None,
        module: Optional[str] = None,
    ) -> list[LogEntry]:
        """Get log entries with optional filtering.
        
        Args:
            level: Filter by log level.
            module: Filter by module name.
            
        Returns:
            Filtered list of log entries.
        """
        entries = self.entries
        
        if level:
            entries = [e for e in entries if e.level == level]
        
        if module:
            entries = [e for e in entries if e.module == module]
        
        return entries
    
    def clear(self) -> None:
        """Clear all log entries."""
        self.entries.clear()
