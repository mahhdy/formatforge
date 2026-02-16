"""
Tests for formatforge.utils.logger
تست‌های ماژول لاگر
"""

import logging
import tempfile
from pathlib import Path

import pytest

from formatforge.utils.logger import (
    get_logger,
    reset_logger,
    setup_logger,
)


@pytest.fixture(autouse=True)
def _clean_logger():
    """ریست لاگر قبل و بعد از هر تست."""
    reset_logger()
    yield
    reset_logger()


class TestSetupLogger:
    """تست‌های setup_logger."""

    def test_returns_logger(self):
        """باید یک Logger برگرداند."""
        log = setup_logger()
        assert isinstance(log, logging.Logger)
        assert log.name == "formatforge"

    def test_verbose_sets_debug(self):
        """در حالت verbose سطح باید DEBUG باشد."""
        log = setup_logger(verbose=True)
        assert log.level == logging.DEBUG

    def test_normal_sets_info(self):
        """در حالت عادی سطح باید INFO باشد."""
        log = setup_logger(verbose=False)
        assert log.level == logging.INFO

    def test_no_duplicate_handlers(self):
        """فراخوانی مجدد نباید handler تکراری بسازد."""
        setup_logger()
        setup_logger()
        log = logging.getLogger("formatforge")
        assert len(log.handlers) <= 2

    def test_file_handler(self):
        """باید فایل لاگ بسازد."""
        tmpdir = tempfile.mkdtemp()
        log_file = Path(tmpdir) / "test.log"
        try:
            log = setup_logger(verbose=True, log_file=str(log_file))
            log.info("تست نوشتن لاگ فارسی")

            # flush all handlers
            for h in log.handlers:
                h.flush()

            assert log_file.exists()
            content = log_file.read_text(encoding="utf-8-sig")
            assert "تست" in content

        finally:
            # بستن handler های فایلی قبل از حذف
            for h in list(log.handlers):
                if isinstance(h, logging.FileHandler):
                    h.close()
                    log.removeHandler(h)

            # حذف فایل و پوشه
            try:
                log_file.unlink(missing_ok=True)
                Path(tmpdir).rmdir()
            except OSError:
                pass  # در Windows ممکن است هنوز قفل باشد


class TestGetLogger:
    """تست‌های get_logger."""

    def test_returns_child_logger(self):
        """باید لاگر فرزند برگرداند."""
        log = get_logger("converters")
        assert log.name == "formatforge.converters"

    def test_already_prefixed(self):
        """اگر نام از قبل prefix دارد تکرار نشود."""
        log = get_logger("formatforge.test")
        assert log.name == "formatforge.test"
