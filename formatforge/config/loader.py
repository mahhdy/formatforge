"""
FormatForge - Configuration Loader
بارگذاری و ادغام تنظیمات

Load, merge, and cache application configuration from YAML files.
Implements singleton pattern for global config access.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import yaml

from formatforge.config.schema import AppConfig


# ─────────────────────────────────────────────
# Constants / ثابت‌ها
# ─────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "default_config.yaml"
_USER_CONFIG_CANDIDATES = [
    Path("formatforge.yaml"),
    Path("formatforge.yml"),
    Path(".formatforge.yaml"),
    Path("config/user_config.yaml"),
]

logger = logging.getLogger("formatforge.config")


# ─────────────────────────────────────────────
# Deep merge / ادغام عمیق
# ─────────────────────────────────────────────

def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    ادغام عمیق دو دیکشنری. مقادیر override بر base ارجحیت دارند.
    Deep-merge two dicts. Values in *override* take precedence.

    Args:
        base: دیکشنری پایه (پیش‌فرض)
        override: دیکشنری بازنویسی (کاربر)

    Returns:
        دیکشنری ادغام‌شده
    """
    result = copy.deepcopy(base)

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


# ─────────────────────────────────────────────
# YAML helpers / خواندن YAML
# ─────────────────────────────────────────────

def _read_yaml(path: Path) -> dict[str, Any]:
    """
    خواندن فایل YAML.
    Read a YAML file and return its contents as a dict.

    Args:
        path: مسیر فایل YAML

    Returns:
        محتوای فایل به صورت dict

    Raises:
        FileNotFoundError: اگر فایل وجود نداشته باشد
        ValueError: اگر فایل YAML معتبر نباشد
    """
    resolved = path.resolve()

    if not resolved.exists():
        raise FileNotFoundError(
            f"فایل تنظیمات یافت نشد: {resolved}"
        )

    if not resolved.is_file():
        raise ValueError(
            f"مسیر داده‌شده یک فایل نیست: {resolved}"
        )

    logger.debug("خواندن فایل تنظیمات: %s", resolved)

    text = resolved.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"خطا در خواندن YAML از {resolved}: {exc}"
        ) from exc

    if data is None:
        logger.warning("فایل تنظیمات خالی است: %s", resolved)
        return {}

    if not isinstance(data, dict):
        raise ValueError(
            f"محتوای فایل YAML باید dict باشد، نه {type(data).__name__}"
        )

    return data


def _find_user_config() -> Optional[Path]:
    """
    جستجوی خودکار فایل تنظیمات کاربر.
    Auto-discover user config file from common locations.

    Returns:
        مسیر فایل یافت‌شده یا None
    """
    for candidate in _USER_CONFIG_CANDIDATES:
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_file():
            logger.info(
                "فایل تنظیمات کاربر یافت شد: %s", resolved
            )
            return resolved

    logger.debug("فایل تنظیمات کاربر یافت نشد.")
    return None


# ─────────────────────────────────────────────
# Public API / رابط عمومی
# ─────────────────────────────────────────────

def load_default_config() -> dict[str, Any]:
    """
    بارگذاری تنظیمات پیش‌فرض.
    Load the default configuration from default_config.yaml.

    Returns:
        دیکشنری تنظیمات پیش‌فرض
    """
    if _DEFAULT_CONFIG_PATH.exists():
        return _read_yaml(_DEFAULT_CONFIG_PATH)

    logger.warning(
        "فایل تنظیمات پیش‌فرض یافت نشد: %s — استفاده از مقادیر Pydantic",
        _DEFAULT_CONFIG_PATH,
    )
    return {}


def load_config(path: Optional[str | Path] = None) -> AppConfig:
    """
    بارگذاری تنظیمات از فایل YAML.
    Load configuration from a YAML file, merged over defaults.

    Args:
        path: مسیر فایل تنظیمات کاربر (اختیاری).
              اگر None باشد، جستجوی خودکار انجام می‌شود.

    Returns:
        AppConfig با تمام تنظیمات ادغام‌شده
    """
    # ۱) بارگذاری پیش‌فرض
    default_data = load_default_config()

    # ۲) بارگذاری کاربر
    user_path: Optional[Path] = None
    if path is not None:
        user_path = Path(path).resolve()
    else:
        user_path = _find_user_config()

    user_data: dict[str, Any] = {}
    if user_path is not None:
        try:
            user_data = _read_yaml(user_path)
            logger.info("تنظیمات کاربر بارگذاری شد: %s", user_path)
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("خطا در بارگذاری تنظیمات کاربر: %s", exc)

    # ۳) ادغام
    merged = merge_configs(default_data, user_data)

    return merged


def merge_configs(
    default: dict[str, Any],
    user: dict[str, Any],
) -> AppConfig:
    """
    ادغام تنظیمات پیش‌فرض و کاربر و ساخت AppConfig.
    Deep-merge default and user configs, then validate with Pydantic.

    Args:
        default: دیکشنری تنظیمات پیش‌فرض
        user: دیکشنری تنظیمات کاربر

    Returns:
        AppConfig اعتبارسنجی‌شده
    """
    merged_data = _deep_merge(default, user) if user else default.copy()

    logger.debug("ادغام تنظیمات: %d کلید پیش‌فرض + %d کلید کاربر",
                 len(default), len(user))

    config = AppConfig.model_validate(merged_data)

    logger.info(
        "تنظیمات نهایی: زبان=%s, فرمت‌ها=%d, AI=%s",
        config.general.language,
        len(config.scanner.supported_formats),
        config.metadata.ai_provider,
    )

    return config


# ─────────────────────────────────────────────
# Singleton / نمونه یکتا
# ─────────────────────────────────────────────

_config_instance: Optional[AppConfig] = None
_config_lock = Lock()


def get_config(
    path: Optional[str | Path] = None,
    *,
    force_reload: bool = False,
) -> AppConfig:
    """
    دریافت نمونه یکتای تنظیمات (Singleton).
    Get the global AppConfig singleton. Thread-safe.

    Args:
        path: مسیر فایل (فقط بار اول یا force_reload)
        force_reload: بارگذاری مجدد اجباری

    Returns:
        AppConfig singleton
    """
    global _config_instance  # noqa: PLW0603

    if _config_instance is not None and not force_reload:
        return _config_instance

    with _config_lock:
        # Double-check locking
        if _config_instance is not None and not force_reload:
            return _config_instance

        _config_instance = load_config(path)
        logger.info("نمونه یکتای تنظیمات ساخته شد.")
        return _config_instance


def reset_config() -> None:
    """
    ریست نمونه یکتا (برای تست).
    Reset the singleton (useful for testing).
    """
    global _config_instance  # noqa: PLW0603
    with _config_lock:
        _config_instance = None
        logger.debug("نمونه یکتای تنظیمات ریست شد.")
