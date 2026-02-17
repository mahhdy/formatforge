"""
FormatForge - ZWNJ Handler
مدیریت نیم‌فاصله (ZWNJ) فارسی

Count, validate, protect, restore, and fix ZWNJ (U+200C)
in Persian text. This is the most critical module for
preserving Persian typography during document conversion.

قاعده حیاتی: نیم‌فاصله هرگز حذف نشود!
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from formatforge.exceptions import ZWNJLossError

logger = logging.getLogger("formatforge.persian.zwnj")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants / ثابت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ZWNJ = "\u200c"

# ─── پیشوندها (باید نیم‌فاصله قبل از فعل/اسم بیایند) ───
PERSIAN_PREFIXES: list[str] = [
    "می",
    "نمی",
    "بر",
    "در",
    "بی",
    "هم",
    "بار",
]

# ─── پسوندها (باید نیم‌فاصله بعد از اسم بیایند) ───
PERSIAN_SUFFIXES: list[str] = [
    "ها",
    "های",
    "هایی",
    "ای",
    "ام",
    "ات",
    "اش",
    "مان",
    "تان",
    "شان",
    "تر",
    "ترین",
    "گر",
    "ور",
    "گری",
    "ساز",
    "سازی",
    "آمیز",
    "کننده",
    "شده",
    "شدن",
    "کردن",
    "گونه",
    "وار",
    "مند",
    "بندی",
    "نامه",
    "دار",
    "خواه",
]

# ─── الگوهای رایج پیشوند+فاصله (باید نیم‌فاصله شود) ───
_PREFIX_PATTERNS: list[re.Pattern[str]] = []
for _pf in PERSIAN_PREFIXES:
    _PREFIX_PATTERNS.append(
        re.compile(
            rf"(?<=\S)({re.escape(_pf)})\s+(?=[^\s\d\W])",
            re.UNICODE,
        )
    )

# ─── الگوهای رایج فاصله+پسوند (باید نیم‌فاصله شود) ───
_SUFFIX_PATTERNS: list[re.Pattern[str]] = []
for _sf in PERSIAN_SUFFIXES:
    _SUFFIX_PATTERNS.append(
        re.compile(
            rf"(?<=\S)\s+({re.escape(_sf)})(?=[\s\.\,\:\;!?\)،؛»\n]|$)",
            re.UNICODE,
        )
    )

# ─── الگوهای خاص ───
# «می» + فاصله + فعل → نیم‌فاصله
_MI_VERB_PATTERN = re.compile(
    r"\b(می|نمی)\s+([\u0600-\u06ff\u0750-\u077f"
    r"\ufb50-\ufdff\ufe70-\ufeff]{2,})",
    re.UNICODE,
)

# اسم + فاصله + «ها» → نیم‌فاصله
_NOUN_HA_PATTERN = re.compile(
    r"([\u0600-\u06ff\u0750-\u077f"
    r"\ufb50-\ufdff\ufe70-\ufeff]{2,})\s+(ها|های|هایی)(?=[\s\.\,\:\;!?\)،؛»\n]|$)",
    re.UNICODE,
)

# اسم + فاصله + «ای» → نیم‌فاصله
_NOUN_EI_PATTERN = re.compile(
    r"([\u0600-\u06ff\u0750-\u077f"
    r"\ufb50-\ufdff\ufe70-\ufeff]{2,})\s+(ای)(?=[\s\.\,\:\;!?\)،؛»\n]|$)",
    re.UNICODE,
)

# اسم + فاصله + «تر/ترین» → نیم‌فاصله
_NOUN_TAR_PATTERN = re.compile(
    r"([\u0600-\u06ff\u0750-\u077f"
    r"\ufb50-\ufdff\ufe70-\ufeff]{2,})\s+(تر|ترین)(?=[\s\.\,\:\;!?\)،؛»\n]|$)",
    re.UNICODE,
)

# حفاظت: placeholder
_PLACEHOLDER_PREFIX = "\ufff9ZWNJ_"
_PLACEHOLDER_SUFFIX = "\ufffb"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Classes / کلاس‌های داده
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ZWNJReport:
    """
    گزارش بررسی نیم‌فاصله.
    ZWNJ validation report.
    """
    count_before: int
    count_after: int
    is_preserved: bool
    lost_count: int = 0
    positions_lost: list[int] = field(default_factory=list)
    message: str = ""

    def __post_init__(self) -> None:
        self.lost_count = max(0, self.count_before - self.count_after)
        self.is_preserved = self.count_after >= self.count_before
        if self.is_preserved:
            self.message = (
                f"✅ نیم‌فاصله حفظ شد ({self.count_before} عدد)"
            )
        else:
            self.message = (
                f"❌ {self.lost_count} نیم‌فاصله از دست رفت "
                f"({self.count_before} → {self.count_after})"
            )


@dataclass
class ZWNJProtection:
    """
    نتیجه حفاظت نیم‌فاصله.
    ZWNJ protection result with restoration map.
    """
    protected_text: str
    restoration_map: dict[str, str]
    original_count: int


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Core Functions / توابع اصلی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def count_zwnj(text: str) -> int:
    """
    شمارش نیم‌فاصله‌ها در متن.
    Count ZWNJ characters in text.

    Args:
        text: متن ورودی

    Returns:
        تعداد نیم‌فاصله‌ها
    """
    return text.count(ZWNJ)


def find_zwnj_positions(text: str) -> list[int]:
    """
    یافتن موقعیت تمام نیم‌فاصله‌ها.
    Find all ZWNJ character positions in text.

    Args:
        text: متن ورودی

    Returns:
        لیست اندیس‌های نیم‌فاصله
    """
    return [i for i, ch in enumerate(text) if ch == ZWNJ]


def validate_zwnj_preserved(
    before: str,
    after: str,
    *,
    raise_on_loss: bool = False,
) -> ZWNJReport:
    """
    بررسی حفظ نیم‌فاصله‌ها بعد از پردازش.
    Validate that ZWNJ characters were preserved after processing.

    مقایسه تعداد و موقعیت نیم‌فاصله‌ها قبل و بعد از تبدیل.

    Args:
        before: متن قبل از پردازش
        after: متن بعد از پردازش
        raise_on_loss: آیا در صورت از دست رفتن خطا بدهد

    Returns:
        ZWNJReport شامل نتیجه بررسی

    Raises:
        ZWNJLossError: اگر raise_on_loss=True و نیم‌فاصله کم شود
    """
    count_b = count_zwnj(before)
    count_a = count_zwnj(after)

    positions_b = set(find_zwnj_positions(before))
    positions_a = set(find_zwnj_positions(after))

    # موقعیت‌هایی که از دست رفته‌اند
    lost = sorted(positions_b - positions_a)

    report = ZWNJReport(
        count_before=count_b,
        count_after=count_a,
        is_preserved=(count_b <= count_a),
        positions_lost=lost,
    )

    if not report.is_preserved:
        logger.warning(
            "نیم‌فاصله از دست رفت: %d → %d (افت: %d)",
            count_b, count_a, report.lost_count,
        )
        if raise_on_loss:
            raise ZWNJLossError(
                before_count=count_b,
                after_count=count_a,
                lost_positions=lost,
            )
    else:
        logger.debug(
            "نیم‌فاصله حفظ شد: %d عدد", count_b,
        )

    return report


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fix / اصلاح
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def fix_common_zwnj_issues(text: str) -> str:
    """
    اصلاح مشکلات رایج نیم‌فاصله در متن فارسی.
    Fix common ZWNJ issues in Persian text.

    اصلاحات:
    - «می روم» → «می‌روم»
    - «نمی دانم» → «نمی‌دانم»
    - «کتاب ها» → «کتاب‌ها»
    - «بزرگ تر» → «بزرگ‌تر»
    - «خانه ای» → «خانه‌ای»

    Args:
        text: متن ورودی

    Returns:
        متن اصلاح‌شده با نیم‌فاصله صحیح
    """
    if not text:
        return text

    result = text

    # ─── «می/نمی» + فاصله + فعل ──────
    result = _MI_VERB_PATTERN.sub(
        lambda m: m.group(1) + ZWNJ + m.group(2),
        result,
    )

    # ─── اسم + فاصله + «ها/های/هایی» ─
    result = _NOUN_HA_PATTERN.sub(
        lambda m: m.group(1) + ZWNJ + m.group(2),
        result,
    )

    # ─── اسم + فاصله + «ای» ──────────
    result = _NOUN_EI_PATTERN.sub(
        lambda m: m.group(1) + ZWNJ + m.group(2),
        result,
    )

    # ─── اسم + فاصله + «تر/ترین» ─────
    result = _NOUN_TAR_PATTERN.sub(
        lambda m: m.group(1) + ZWNJ + m.group(2),
        result,
    )

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Protect & Restore / حفاظت و بازیابی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def protect_zwnj(text: str) -> ZWNJProtection:
    """
    حفاظت نیم‌فاصله‌ها با جایگزینی placeholder قبل از پردازش.
    Replace ZWNJ with unique placeholders before processing.

    هر نیم‌فاصله با یک placeholder یکتا جایگزین می‌شود
    تا در پردازش‌های بعدی (regex, HTML parse, ...) از دست نرود.

    Args:
        text: متن ورودی

    Returns:
        ZWNJProtection شامل متن محافظت‌شده و نگاشت بازیابی
    """
    if not text:
        return ZWNJProtection(
            protected_text="",
            restoration_map={},
            original_count=0,
        )

    original_count = count_zwnj(text)
    restoration_map: dict[str, str] = {}
    result = text

    positions = find_zwnj_positions(text)

    # از آخر به اول جایگزین کن تا اندیس‌ها خراب نشوند
    for pos in reversed(positions):
        token = (
            f"{_PLACEHOLDER_PREFIX}"
            f"{uuid.uuid4().hex[:8]}"
            f"{_PLACEHOLDER_SUFFIX}"
        )
        restoration_map[token] = ZWNJ
        result = result[:pos] + token + result[pos + 1:]

    logger.debug(
        "حفاظت ZWNJ: %d نیم‌فاصله → %d placeholder",
        original_count, len(restoration_map),
    )

    return ZWNJProtection(
        protected_text=result,
        restoration_map=restoration_map,
        original_count=original_count,
    )


def restore_zwnj(
    text: str,
    restoration_map: dict[str, str],
) -> str:
    """
    بازگرداندن نیم‌فاصله‌ها از placeholderها.
    Restore ZWNJ characters from placeholders.

    Args:
        text: متن با placeholderها
        restoration_map: نگاشت placeholder → ZWNJ

    Returns:
        متن با نیم‌فاصله‌های بازیابی‌شده
    """
    if not restoration_map:
        return text

    result = text
    for token, original in restoration_map.items():
        result = result.replace(token, original)

    restored_count = count_zwnj(result)
    expected = len(restoration_map)

    if restored_count < expected:
        logger.warning(
            "بازیابی ناقص: %d/%d نیم‌فاصله بازگشت",
            restored_count, expected,
        )

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience / توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def safe_process(
    text: str,
    processor: callable,
    *args,
    **kwargs,
) -> str:
    """
    پردازش امن متن با حفاظت نیم‌فاصله.
    Safely process text while protecting ZWNJ characters.

    مراحل:
    1. حفاظت نیم‌فاصله‌ها
    2. اجرای تابع پردازش
    3. بازیابی نیم‌فاصله‌ها
    4. اعتبارسنجی

    Args:
        text: متن ورودی
        processor: تابع پردازش
        *args: آرگومان‌های اضافی
        **kwargs: آرگومان‌های کلیدی

    Returns:
        متن پردازش‌شده با نیم‌فاصله‌های حفظ‌شده
    """
    protection = protect_zwnj(text)
    processed = processor(
        protection.protected_text, *args, **kwargs,
    )
    restored = restore_zwnj(processed, protection.restoration_map)

    validate_zwnj_preserved(text, restored)

    return restored


def ensure_zwnj(
    word: str,
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
) -> str:
    """
    اطمینان از وجود نیم‌فاصله بین پیشوند/پسوند و کلمه.
    Ensure ZWNJ exists between prefix/suffix and word.

    Args:
        word: کلمه اصلی
        prefix: پیشوند (مانند «می»)
        suffix: پسوند (مانند «ها»)

    Returns:
        کلمه با نیم‌فاصله صحیح
    """
    result = word
    if prefix:
        if result.startswith(prefix) and not result.startswith(
            prefix + ZWNJ
        ):
            rest = result[len(prefix):]
            if rest and rest[0] != ZWNJ:
                result = prefix + ZWNJ + rest
    if suffix:
        if result.endswith(suffix) and not result.endswith(
            ZWNJ + suffix
        ):
            base = result[: -len(suffix)]
            if base and base[-1] != ZWNJ:
                result = base + ZWNJ + suffix
    return result
