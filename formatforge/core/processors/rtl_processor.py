"""
FormatForge - RTL Processor
پردازشگر جهت‌دهی RTL/LTR برای MDX فارسی

Ensure dir="rtl" and lang="fa" in frontmatter,
add dir="ltr" to code/math blocks, wrap all-English blocks,
preserve ZWNJ, and optionally fix typography/Arabic chars.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from formatforge.core.processors.base import (
    BaseProcessor,
    ProcessorContext,
    ProcessorError,
)
from formatforge.core.persian.zwnj_handler import (
    ZWNJ,
    count_zwnj,
    validate_zwnj_preserved,
)
from formatforge.core.persian.bidi_handler import (
    detect_block_direction,
    wrap_ltr_block,
)
from formatforge.core.persian.typography import (
    fix_arabic_characters,
    fix_persian_spacing,
    fix_persian_quotes,
    convert_numerals,
)

logger = logging.getLogger("formatforge.processors.rtl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants / ثابت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_RE_FRONTMATTER = re.compile(
    r"^---\s*\n(.*?)\n---", re.DOTALL
)
_RE_CODE_BLOCK = re.compile(
    r"(```\w*)(.*?)(```)", re.DOTALL
)
_RE_DISPLAY_MATH = re.compile(
    r"(\$\$)([\s\S]*?)(\$\$)"
)
_RE_PARAGRAPH = re.compile(
    r"\n\n([^\n]+(?:\n(?!\n)[^\n]+)*)"
)
_RE_HTML_DIR = re.compile(r'dir="(rtl|ltr)"')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RTLProcessor / پردازشگر RTL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class RTLProcessor(BaseProcessor):
    """
    پردازشگر جهت‌دهی RTL/LTR.
    Ensure correct bidirectional layout for Persian MDX.

    وظایف:
    1. dir="rtl" در frontmatter
    2. lang="fa" در frontmatter
    3. dir="ltr" برای بلوک‌های کد
    4. dir="ltr" برای بلوک‌های ریاضی display
    5. wrap بلوک‌های تمام‌انگلیسی
    6. حفظ ZWNJ (شمارش قبل/بعد)
    7. اصلاح تایپوگرافی فارسی
    8. اصلاح کاراکترهای عربی
    """

    name = "rtl"
    description = "RTL/LTR direction processor for Persian MDX"
    priority = 90  # بعد از math/table، قبل از deploy

    def process(
        self,
        content: str,
        context: ProcessorContext,
    ) -> str:
        """
        پردازش اصلی RTL.
        Main RTL processing pipeline.

        Args:
            content: محتوای MDX
            context: زمینه پردازش

        Returns:
            محتوای با جهت‌دهی صحیح
        """
        if not content or not content.strip():
            return content

        zwnj_before = count_zwnj(content)
        result = content

        # ۱) Frontmatter: dir + lang
        result = self._ensure_frontmatter_dir(result, context)

        # ۲) بلوک‌های کد → dir="ltr"
        result = self._process_code_blocks(result, context)

        # ۳) بلوک‌های ریاضی display → dir="ltr"
        result = self._process_math_blocks(result, context)

        # ۴) بلوک‌های تمام‌انگلیسی → wrap
        result = self._wrap_english_blocks(result, context)

        # ۵) اصلاح کاراکترهای عربی
        if self._get_config("fix_arabic_yeh", True):
            result = self._fix_arabic_safe(result)

        # ۶) اصلاح تایپوگرافی
        if self._get_config("fix_spacing", True):
            result = self._fix_typography_safe(result)

        # ۷) بررسی حفظ ZWNJ
        zwnj_after = count_zwnj(result)
        report = validate_zwnj_preserved(content, result)
        if not report.is_preserved:
            context.add_warning(
                f"RTLProcessor: {report.message}"
            )
            logger.warning(
                "ZWNJ change in RTL: %d → %d",
                zwnj_before, zwnj_after,
            )

        return result

    # ─── 1. Frontmatter ───────────────────

    def _ensure_frontmatter_dir(
        self, content: str, context: ProcessorContext,
    ) -> str:
        """اطمینان از dir='rtl' و lang='fa' در frontmatter."""
        match = _RE_FRONTMATTER.match(content)
        if not match:
            return self._add_frontmatter(content)

        fm_body = match.group(1)
        modified = False

        # dir
        if "dir:" not in fm_body:
            fm_body += '\ndir: "rtl"'
            modified = True
        elif 'dir: "ltr"' in fm_body:
            fm_body = fm_body.replace(
                'dir: "ltr"', 'dir: "rtl"'
            )
            modified = True

        # lang
        if "lang:" not in fm_body:
            fm_body += '\nlang: "fa"'
            modified = True

        if modified:
            rest = content[match.end():]
            return f"---\n{fm_body}\n---{rest}"

        return content

    def _add_frontmatter(self, content: str) -> str:
        """افزودن frontmatter اگر وجود ندارد."""
        fm = '---\ndir: "rtl"\nlang: "fa"\n---\n\n'
        return fm + content

    # ─── 2. Code blocks ──────────────────

    def _process_code_blocks(
        self, content: str, context: ProcessorContext,
    ) -> str:
        """افزودن dir='ltr' به بلوک‌های کد."""
        count = [0]

        def _wrap_code(m: re.Match) -> str:
            opening = m.group(1)
            body = m.group(2)
            closing = m.group(3)
            count[0] += 1
            return (
                f'<div dir="ltr">\n\n'
                f"{opening}{body}{closing}"
                f"\n\n</div>"
            )

        result = _RE_CODE_BLOCK.sub(_wrap_code, content)
        context.code_blocks_processed += count[0]
        return result

    # ─── 3. Math blocks ──────────────────

    def _process_math_blocks(
        self, content: str, context: ProcessorContext,
    ) -> str:
        """افزودن dir='ltr' به بلوک‌های ریاضی display."""
        count = [0]

        def _wrap_math(m: re.Match) -> str:
            opening = m.group(1)
            body = m.group(2)
            closing = m.group(3)
            count[0] += 1
            return (
                f'<div dir="ltr">\n\n'
                f"{opening}{body}{closing}"
                f"\n\n</div>"
            )

        result = _RE_DISPLAY_MATH.sub(_wrap_math, content)
        context.math_blocks_processed += count[0]
        return result

    # ─── 4. English blocks ────────────────

    def _wrap_english_blocks(
        self, content: str, context: ProcessorContext,
    ) -> str:
        """شناسایی و wrap پاراگراف‌های تمام‌انگلیسی."""
        lines = content.split("\n\n")
        result_parts: list[str] = []

        for block in lines:
            stripped = block.strip()
            if not stripped:
                result_parts.append(block)
                continue

            # Skip frontmatter, code, math, HTML
            if self._is_special_block(stripped):
                result_parts.append(block)
                continue

            direction = detect_block_direction(stripped)
            if direction == "ltr":
                wrapped = wrap_ltr_block(stripped)
                result_parts.append(wrapped)
            else:
                result_parts.append(block)

        return "\n\n".join(result_parts)

    def _is_special_block(self, text: str) -> bool:
        """آیا بلوک خاص است (کد/ریاضی/HTML/frontmatter)."""
        if text.startswith("---"):
            return True
        if text.startswith("```"):
            return True
        if text.startswith("$$"):
            return True
        if text.startswith("<"):
            return True
        if _RE_HTML_DIR.search(text):
            return True
        return False

    # ─── 5. Arabic fix ────────────────────

    def _fix_arabic_safe(self, content: str) -> str:
        """اصلاح کاراکترهای عربی (بدون تغییر کد/ریاضی)."""
        parts = self._split_protected(content)
        result_parts: list[str] = []

        for text, is_protected in parts:
            if is_protected:
                result_parts.append(text)
            else:
                result_parts.append(
                    fix_arabic_characters(text)
                )

        return "".join(result_parts)

    # ─── 6. Typography fix ────────────────

    def _fix_typography_safe(self, content: str) -> str:
        """اصلاح تایپوگرافی (بدون تغییر کد/ریاضی)."""
        parts = self._split_protected(content)
        result_parts: list[str] = []

        for text, is_protected in parts:
            if is_protected:
                result_parts.append(text)
            else:
                result_parts.append(
                    fix_persian_spacing(text)
                )

        return "".join(result_parts)

    # ─── Helpers ──────────────────────────

    def _split_protected(
        self, content: str,
    ) -> list[tuple[str, bool]]:
        """
        تقسیم محتوا به بخش‌های محافظت‌شده و آزاد.
        Split content into (text, is_protected) tuples.
        """
        parts: list[tuple[str, bool]] = []
        patterns = [
            re.compile(r"```[\s\S]*?```"),
            re.compile(r"`[^`]+`"),
            re.compile(r"\$\$[\s\S]*?\$\$"),
            re.compile(r"\$[^$]+\$"),
            re.compile(r"<[^>]+>"),
        ]

        combined = "|".join(p.pattern for p in patterns)
        master = re.compile(combined)

        last_end = 0
        for m in master.finditer(content):
            if m.start() > last_end:
                parts.append((content[last_end:m.start()], False))
            parts.append((m.group(0), True))
            last_end = m.end()

        if last_end < len(content):
            parts.append((content[last_end:], False))

        return parts

    def _get_config(self, key: str, default: Any = None) -> Any:
        """دریافت تنظیمات."""
        if self.config is None:
            return default
        if hasattr(self.config, key):
            return getattr(self.config, key)
        if hasattr(self.config, "conversion"):
            persian = getattr(
                self.config.conversion, "persian", None
            )
            if persian and hasattr(persian, key):
                return getattr(persian, key)
        return default
