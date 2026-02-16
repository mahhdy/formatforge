"""
FormatForge - Base Processor & Pipeline
کلاس پایه پردازشگر و خط لوله پردازش

Abstract base class for content processors (math, table, image, RTL, ...)
and a pipeline to chain processors in sequence.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("formatforge.processors")

# ─── Constants / ثابت‌ها ──────────────────────
ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Exceptions / استثناها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProcessorError(Exception):
    """خطای عمومی پردازشگر. / General processor error."""
    pass


class PipelineError(ProcessorError):
    """خطا در خط لوله پردازش. / Pipeline execution error."""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ProcessorContext / زمینه پردازش
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ProcessorContext:
    """
    زمینه مشترک بین پردازشگرها.
    Shared context passed through the processor pipeline.

    شامل تنظیمات، متادیتا، شمارنده‌ها و نتایج میانی.
    """

    # ─── ورودی / Input ────────────────────
    source_format: str = "unknown"
    source_path: str = ""
    encoding: str = "utf-8"
    language: str = "fa"

    # ─── تنظیمات / Config ─────────────────
    config: Any = None

    # ─── شمارنده‌ها / Counters ─────────────
    zwnj_count_before: int = 0
    zwnj_count_after: int = 0
    math_blocks_processed: int = 0
    math_inlines_processed: int = 0
    tables_processed: int = 0
    images_processed: int = 0
    code_blocks_processed: int = 0
    headings_processed: int = 0
    links_processed: int = 0
    footnotes_processed: int = 0

    # ─── وضعیت / State ────────────────────
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    imports_needed: set[str] = field(default_factory=set)
    labels: dict[str, str] = field(default_factory=dict)
    assets: list[str] = field(default_factory=list)

    # ─── میانی / Intermediate ─────────────
    extra: dict[str, Any] = field(default_factory=dict)

    def add_warning(self, msg: str) -> None:
        """افزودن هشدار."""
        self.warnings.append(msg)
        logger.warning("Processor warning: %s", msg)

    def add_error(self, msg: str) -> None:
        """افزودن خطا."""
        self.errors.append(msg)
        logger.error("Processor error: %s", msg)

    def require_import(self, component: str) -> None:
        """ثبت نیاز به import یک کامپوننت MDX."""
        self.imports_needed.add(component)

    def count_zwnj(self, text: str) -> int:
        """شمارش نیم‌فاصله‌ها."""
        return text.count(ZWNJ)

    @property
    def has_errors(self) -> bool:
        """آیا خطایی رخ داده."""
        return len(self.errors) > 0

    @property
    def zwnj_preserved(self) -> bool:
        """آیا نیم‌فاصله‌ها حفظ شده‌اند."""
        return self.zwnj_count_before == self.zwnj_count_after


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BaseProcessor / پردازشگر پایه
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BaseProcessor(ABC):
    """
    کلاس پایه انتزاعی برای تمام پردازشگرها.
    Abstract base class for content processors.

    هر پردازشگر یک بخش خاص از محتوا را تبدیل می‌کند:
    - MathProcessor: فرمول‌های ریاضی
    - TableProcessor: جداول
    - ImageProcessor: تصاویر
    - RTLProcessor: جهت‌دهی فارسی
    - CodeProcessor: بلوک‌های کد
    - LinkProcessor: لینک‌ها و ارجاعات
    - PersianProcessor: نیم‌فاصله، گیومه، ارقام
    - ...
    """

    # ─── Class attributes ─────────────────
    name: str = "base"
    description: str = "Base processor"
    priority: int = 100  # عدد کمتر = زودتر اجرا
    enabled: bool = True

    def __init__(self, config: Any = None) -> None:
        """مقداردهی پردازشگر."""
        self.config = config
        self._logger = logging.getLogger(
            f"formatforge.processors.{self.name}"
        )

    @abstractmethod
    def process(
        self,
        content: str,
        context: ProcessorContext,
    ) -> str:
        """
        پردازش محتوا.
        Process the content and return modified version.

        هر پردازشگر:
        1. محتوای ورودی را دریافت می‌کند
        2. بخش مربوطه را تبدیل می‌کند
        3. شمارنده‌ها و وضعیت context را به‌روز می‌کند
        4. محتوای تغییریافته را برمی‌گرداند

        Args:
            content: محتوای فعلی (MDX in progress)
            context: زمینه مشترک پردازش

        Returns:
            محتوای پردازش‌شده

        Raises:
            ProcessorError: اگر پردازش ناموفق باشد
        """
        ...

    def can_process(
        self,
        content: str,
        context: ProcessorContext,
    ) -> bool:
        """
        آیا این پردازشگر برای محتوای فعلی کاربرد دارد؟
        Check if this processor is applicable.

        پیش‌فرض: True. زیرکلاس‌ها می‌توانند بازنویسی کنند.
        مثلاً MathProcessor فقط اگر فرمول ریاضی وجود دارد.

        Args:
            content: محتوای فعلی
            context: زمینه پردازش

        Returns:
            True اگر پردازش لازم باشد
        """
        return self.enabled

    def pre_process(
        self,
        content: str,
        context: ProcessorContext,
    ) -> str:
        """
        پیش‌پردازش (hook اختیاری).
        Optional hook called before process().
        """
        return content

    def post_process(
        self,
        content: str,
        context: ProcessorContext,
    ) -> str:
        """
        پس‌پردازش (hook اختیاری).
        Optional hook called after process().
        """
        return content

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name={self.name!r} "
            f"priority={self.priority} "
            f"enabled={self.enabled}>"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ProcessorResult / نتیجه پردازش
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ProcessorStepResult:
    """نتیجه یک مرحله از خط لوله."""

    processor_name: str
    success: bool
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    content_length_before: int = 0
    content_length_after: int = 0
    zwnj_before: int = 0
    zwnj_after: int = 0


@dataclass
class PipelineResult:
    """نتیجه کامل اجرای خط لوله."""

    success: bool = True
    content: str = ""
    steps: list[ProcessorStepResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    zwnj_count_initial: int = 0
    zwnj_count_final: int = 0
    processors_run: int = 0
    processors_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def zwnj_preserved(self) -> bool:
        """آیا نیم‌فاصله‌ها حفظ شده‌اند."""
        return self.zwnj_count_initial == self.zwnj_count_final


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ProcessorPipeline / خط لوله پردازش
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProcessorPipeline:
    """
    خط لوله پردازشگرها.
    Pipeline that chains multiple processors in priority order.

    مثال استفاده:
        pipeline = ProcessorPipeline()
        pipeline.add(MathProcessor())
        pipeline.add(TableProcessor())
        pipeline.add(RTLProcessor())
        pipeline.add(PersianProcessor())

        result = pipeline.run(content, context)
    """

    def __init__(self, name: str = "default") -> None:
        """مقداردهی خط لوله."""
        self._processors: list[BaseProcessor] = []
        self._name = name
        self._logger = logging.getLogger(
            f"formatforge.processors.pipeline.{name}"
        )

    def add(self, processor: BaseProcessor) -> "ProcessorPipeline":
        """
        افزودن پردازشگر به خط لوله.
        Add a processor to the pipeline. Returns self for chaining.

        Args:
            processor: نمونه پردازشگر

        Returns:
            self (برای زنجیره‌سازی)

        Raises:
            TypeError: اگر ورودی BaseProcessor نباشد
        """
        if not isinstance(processor, BaseProcessor):
            raise TypeError(
                f"پردازشگر باید نمونه BaseProcessor باشد، "
                f"نه {type(processor).__name__}"
            )
        self._processors.append(processor)
        self._logger.debug(
            "پردازشگر افزوده شد: %s (priority=%d)",
            processor.name, processor.priority,
        )
        return self

    def remove(self, name: str) -> bool:
        """
        حذف پردازشگر بر اساس نام.
        Remove a processor by name. Returns True if found.
        """
        before = len(self._processors)
        self._processors = [
            p for p in self._processors if p.name != name
        ]
        removed = len(self._processors) < before
        if removed:
            self._logger.debug("پردازشگر حذف شد: %s", name)
        return removed

    def clear(self) -> None:
        """پاک کردن همه پردازشگرها."""
        self._processors.clear()

    @property
    def processors(self) -> list[BaseProcessor]:
        """لیست پردازشگرها مرتب بر اساس اولویت."""
        return sorted(self._processors, key=lambda p: p.priority)

    @property
    def processor_count(self) -> int:
        """تعداد پردازشگرها."""
        return len(self._processors)

    def run(
        self,
        content: str,
        context: ProcessorContext,
        *,
        stop_on_error: bool = False,
    ) -> PipelineResult:
        """
        اجرای خط لوله پردازش.
        Run all processors in priority order.

        مراحل:
        1. شمارش ZWNJ اولیه
        2. مرتب‌سازی بر اساس اولویت
        3. اجرای هر پردازشگر (pre → process → post)
        4. شمارش ZWNJ نهایی
        5. تولید گزارش

        Args:
            content: محتوای ورودی
            context: زمینه پردازش
            stop_on_error: توقف در اولین خطا

        Returns:
            PipelineResult با محتوای نهایی و گزارش
        """
        pipeline_start = time.time()
        result = PipelineResult()

        # شمارش ZWNJ اولیه
        result.zwnj_count_initial = content.count(ZWNJ)
        context.zwnj_count_before = result.zwnj_count_initial

        self._logger.info(
            "شروع خط لوله «%s»: %d پردازشگر, "
            "ZWNJ اولیه=%d, طول=%d",
            self._name,
            self.processor_count,
            result.zwnj_count_initial,
            len(content),
        )

        # اجرای پردازشگرها به ترتیب اولویت
        current_content = content
        sorted_processors = self.processors

        for processor in sorted_processors:
            step_start = time.time()
            step = ProcessorStepResult(
                processor_name=processor.name,
                success=True,
                content_length_before=len(current_content),
                zwnj_before=current_content.count(ZWNJ),
            )

            # بررسی قابلیت اجرا
            if not processor.can_process(current_content, context):
                result.processors_skipped += 1
                self._logger.debug(
                    "رد شد: %s (can_process=False)", processor.name
                )
                continue

            try:
                # pre_process
                current_content = processor.pre_process(
                    current_content, context
                )

                # process (اصلی)
                self._logger.debug("اجرا: %s", processor.name)
                current_content = processor.process(
                    current_content, context
                )

                # post_process
                current_content = processor.post_process(
                    current_content, context
                )

                result.processors_run += 1

            except ProcessorError as exc:
                step.success = False
                step.error_message = str(exc)
                result.errors.append(
                    f"[{processor.name}] {exc}"
                )
                context.add_error(f"[{processor.name}] {exc}")
                self._logger.error(
                    "خطا در %s: %s", processor.name, exc
                )

                if stop_on_error:
                    result.success = False
                    break

            except Exception as exc:
                step.success = False
                step.error_message = f"خطای غیرمنتظره: {exc}"
                result.errors.append(
                    f"[{processor.name}] خطای غیرمنتظره: {exc}"
                )
                context.add_error(
                    f"[{processor.name}] خطای غیرمنتظره: {exc}"
                )
                self._logger.exception(
                    "خطای غیرمنتظره در %s", processor.name
                )

                if stop_on_error:
                    result.success = False
                    break

            finally:
                step.duration_seconds = round(
                    time.time() - step_start, 4
                )
                step.content_length_after = len(current_content)
                step.zwnj_after = current_content.count(ZWNJ)
                result.steps.append(step)

                # بررسی ZWNJ بعد از هر مرحله
                if step.zwnj_before != step.zwnj_after:
                    diff = step.zwnj_before - step.zwnj_after
                    msg = (
                        f"⚠ [{processor.name}] "
                        f"نیم‌فاصله: {diff} مورد تغییر "
                        f"({step.zwnj_before}→{step.zwnj_after})"
                    )
                    context.add_warning(msg)
                    self._logger.warning(msg)

        # نتایج نهایی
        result.content = current_content
        result.zwnj_count_final = current_content.count(ZWNJ)
        result.total_duration_seconds = round(
            time.time() - pipeline_start, 3
        )
        context.zwnj_count_after = result.zwnj_count_final

        if result.errors:
            result.success = False

        self._logger.info(
            "پایان خط لوله «%s»: %d اجرا, %d رد, "
            "%d خطا, ZWNJ %d→%d, %.3fs",
            self._name,
            result.processors_run,
            result.processors_skipped,
            len(result.errors),
            result.zwnj_count_initial,
            result.zwnj_count_final,
            result.total_duration_seconds,
        )

        return result

    def __repr__(self) -> str:
        names = [p.name for p in self.processors]
        return (
            f"<ProcessorPipeline name={self._name!r} "
            f"processors={names}>"
        )
