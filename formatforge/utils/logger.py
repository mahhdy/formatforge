"""
FormatForge - Logger Setup
راه‌اندازی لاگر با پشتیبانی فارسی

RTL-safe logging with Rich handler support.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme


# ─────────────────────────────────────────────
# Constants / ثابت‌ها
# ─────────────────────────────────────────────

_APP_LOGGER_NAME = "formatforge"

_LOG_FORMAT_FILE = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)

_LOG_FORMAT_SIMPLE = "%(message)s"

_FORMATFORGE_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "critical": "bold white on red",
    "debug": "dim",
    "logging.level.info": "bold cyan",
    "logging.level.warning": "bold yellow",
    "logging.level.error": "bold red",
})

_logger_initialized = False


# ─────────────────────────────────────────────
# Public API / رابط عمومی
# ─────────────────────────────────────────────

def setup_logger(
    verbose: bool = False,
    log_file: Optional[str | Path] = None,
    *,
    no_color: bool = False,
    log_name: str = _APP_LOGGER_NAME,
) -> logging.Logger:
    """
    راه‌اندازی لاگر اصلی اپلیکیشن.
    Setup the main application logger with Rich console + optional file handler.

    ویژگی‌ها:
    - خروجی رنگی RTL-safe با Rich
    - سطح DEBUG در حالت verbose
    - فایل لاگ اختیاری (UTF-8 BOM)
    - بدون تکرار handler در فراخوانی‌های مجدد

    Args:
        verbose: نمایش جزئیات بیشتر (DEBUG)
        log_file: مسیر فایل لاگ (اختیاری)
        no_color: غیرفعال کردن رنگ
        log_name: نام لاگر (پیش‌فرض: formatforge)

    Returns:
        logging.Logger آماده استفاده
    """
    global _logger_initialized  # noqa: PLW0603

    logger = logging.getLogger(log_name)

    # جلوگیری از تکرار handler
    if _logger_initialized and logger.handlers:
        _update_log_level(logger, verbose)
        return logger

    # سطح لاگ
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    # پاک کردن handler های قبلی
    logger.handlers.clear()
    logger.propagate = False

    # ─── Rich Console Handler ─────────────
    console = Console(
        stderr=True,
        no_color=no_color,
        theme=_FORMATFORGE_THEME,
    )

    rich_handler = RichHandler(
        console=console,
        show_time=verbose,
        show_path=verbose,
        show_level=True,
        rich_tracebacks=True,
        tracebacks_show_locals=verbose,
        markup=True,
        log_time_format="[%H:%M:%S]",
    )
    rich_handler.setLevel(level)
    rich_handler.setFormatter(logging.Formatter(_LOG_FORMAT_SIMPLE))
    logger.addHandler(rich_handler)

    # ─── File Handler (اختیاری) ───────────
    if log_file is not None:
        _add_file_handler(logger, log_file, verbose)

    _logger_initialized = True

    logger.debug(
        "لاگر راه‌اندازی شد: level=%s, file=%s",
        logging.getLevelName(level),
        log_file or "—",
    )

    return logger


def get_logger(name: str = _APP_LOGGER_NAME) -> logging.Logger:
    """
    دریافت لاگر با نام مشخص.
    Get a named logger under the formatforge namespace.

    Args:
        name: نام لاگر (مثلاً "formatforge.converters")

    Returns:
        logging.Logger
    """
    if not name.startswith(_APP_LOGGER_NAME):
        name = f"{_APP_LOGGER_NAME}.{name}"
    return logging.getLogger(name)


def reset_logger() -> None:
    """
    ریست لاگر (برای تست).
    Reset logger state for testing.
    """
    global _logger_initialized  # noqa: PLW0603
    logger = logging.getLogger(_APP_LOGGER_NAME)
    logger.handlers.clear()
    _logger_initialized = False


# ─────────────────────────────────────────────
# Helpers / توابع کمکی
# ─────────────────────────────────────────────

def _add_file_handler(
    logger: logging.Logger,
    log_file: str | Path,
    verbose: bool,
) -> None:
    """افزودن handler فایلی با UTF-8 BOM."""
    path = Path(log_file).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(
        filename=str(path),
        mode="a",
        encoding="utf-8-sig",  # UTF-8 with BOM
    )
    file_level = logging.DEBUG if verbose else logging.INFO
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT_FILE))
    logger.addHandler(file_handler)


def _update_log_level(logger: logging.Logger, verbose: bool) -> None:
    """به‌روزرسانی سطح لاگ."""
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
