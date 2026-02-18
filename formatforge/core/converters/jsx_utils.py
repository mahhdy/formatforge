"""
FormatForge - JSX Utilities
ابزارهای تبدیل HTML به JSX و تولید import

Converts HTML attributes/elements to JSX-compatible syntax
and generates import statements for used MDX components.

قواعد حیاتی:
- ZWNJ (U+200C) هرگز حذف نشود
- class → className
- for → htmlFor
- style="..." → style={{...}}
- <!-- --> → {/* */}
- self-closing tags: <br> → <br />
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger("formatforge.converters.jsx_utils")

# ─── Constants / ثابت‌ها ──────────────────────
ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HTML → JSX Attribute Mapping / نگاشت صفت‌ها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# HTML attributes → JSX equivalents
_ATTR_MAP: dict[str, str] = {
    "class": "className",
    "for": "htmlFor",
    "tabindex": "tabIndex",
    "readonly": "readOnly",
    "maxlength": "maxLength",
    "minlength": "minLength",
    "colspan": "colSpan",
    "rowspan": "rowSpan",
    "cellpadding": "cellPadding",
    "cellspacing": "cellSpacing",
    "enctype": "encType",
    "crossorigin": "crossOrigin",
    "autocomplete": "autoComplete",
    "autofocus": "autoFocus",
    "autoplay": "autoPlay",
    "formaction": "formAction",
    "novalidate": "noValidate",
    "accesskey": "accessKey",
    "charset": "charSet",
    "datetime": "dateTime",
    "frameborder": "frameBorder",
    "hreflang": "hrefLang",
    "inputmode": "inputMode",
    "srcset": "srcSet",
    "usemap": "useMap",
}

# HTML event handlers → JSX (onclick → onClick, etc.)
_EVENT_HANDLER_RE = re.compile(
    r"\bon(click|change|submit|focus|blur|keydown|keyup|keypress"
    r"|mousedown|mouseup|mouseover|mouseout|mousemove"
    r"|touchstart|touchend|touchmove|load|error|scroll"
    r"|input|reset|contextmenu|dblclick|drag|dragend"
    r"|dragenter|dragleave|dragover|dragstart|drop)\b",
    re.IGNORECASE,
)

# Self-closing HTML tags that need explicit />
_SELF_CLOSING_TAGS = frozenset({
    "br", "hr", "img", "input", "meta", "link",
    "area", "base", "col", "embed", "param",
    "source", "track", "wbr",
})

# Regex patterns
_RE_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)
_RE_SELF_CLOSING = re.compile(
    r"<(" + "|".join(_SELF_CLOSING_TAGS) + r")"
    r"(\s[^>]*)?\s*/?>",
    re.IGNORECASE,
)
_RE_CLASS_ATTR = re.compile(
    r'\bclass\s*=\s*(["\'])(.*?)\1'
)
_RE_FOR_ATTR = re.compile(
    r'\bfor\s*=\s*(["\'])(.*?)\1'
)
_RE_STYLE_ATTR = re.compile(
    r'\bstyle\s*=\s*(["\'])(.*?)\1'
)
_RE_ATTR_GENERIC = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _ATTR_MAP) + r")"
    r'\s*=\s*(["\'])(.*?)\2'
)
_RE_EVENT_ATTR = re.compile(
    r"\b(on[a-z]+)\s*=",
    re.IGNORECASE,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Style Conversion / تبدیل style
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _css_to_jsx_style(css_string: str) -> str:
    """
    تبدیل رشته CSS به شیء JSX style.
    Convert CSS string to JSX style object.

    "color: red; font-size: 14px" → {{color: 'red', fontSize: '14px'}}
    """
    if not css_string or not css_string.strip():
        return "{{}}"

    pairs: list[str] = []
    for declaration in css_string.split(";"):
        declaration = declaration.strip()
        if not declaration or ":" not in declaration:
            continue
        prop, _, value = declaration.partition(":")
        prop = prop.strip()
        value = value.strip()

        # Convert kebab-case to camelCase
        jsx_prop = _kebab_to_camel(prop)

        # Wrap value in quotes (unless it's a number)
        if value and not _is_numeric(value):
            value = f"'{value}'"

        pairs.append(f"{jsx_prop}: {value}")

    return "{{" + ", ".join(pairs) + "}}"


def _kebab_to_camel(name: str) -> str:
    """
    تبدیل kebab-case به camelCase.
    font-size → fontSize, background-color → backgroundColor
    """
    parts = name.split("-")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _is_numeric(value: str) -> bool:
    """آیا مقدار عددی است."""
    try:
        float(value)
        return True
    except ValueError:
        return False


def _event_to_camel(name: str) -> str:
    """
    تبدیل event handler به camelCase.
    onclick → onClick, onmousedown → onMouseDown
    """
    if len(name) <= 2:
        return name
    prefix = name[:2]  # "on"
    rest = name[2:]
    return prefix + rest[0].upper() + rest[1:]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main Conversion Functions / توابع اصلی تبدیل
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def convert_html_to_jsx(html: str) -> str:
    """
    تبدیل HTML به JSX.
    Convert HTML syntax to JSX-compatible syntax.

    تبدیل‌ها:
    - class → className
    - for → htmlFor
    - style="color:red" → style={{color:'red'}}
    - <!-- comment --> → {/* comment */}
    - <br> → <br />
    - tabindex → tabIndex
    - onclick → onClick (etc.)

    Args:
        html: رشته HTML ورودی

    Returns:
        رشته JSX سازگار
    """
    if not html:
        return html

    zwnj_before = html.count(ZWNJ)
    result = html

    # 1) HTML comments → JSX comments
    result = _RE_HTML_COMMENT.sub(
        lambda m: "{/* " + m.group(1).strip() + " */}", result
    )

    # 2) style="..." → style={{...}}
    def _replace_style(m: re.Match) -> str:
        css_str = m.group(2)
        jsx_style = _css_to_jsx_style(css_str)
        return f"style={jsx_style}"

    result = _RE_STYLE_ATTR.sub(_replace_style, result)

    # 3) class="..." → className="..."
    result = _RE_CLASS_ATTR.sub(
        lambda m: f'className={m.group(1)}{m.group(2)}{m.group(1)}',
        result,
    )

    # 4) for="..." → htmlFor="..."
    result = _RE_FOR_ATTR.sub(
        lambda m: f'htmlFor={m.group(1)}{m.group(2)}{m.group(1)}',
        result,
    )

    # 5) Other attributes (tabindex, readonly, etc.)
    def _replace_attr(m: re.Match) -> str:
        attr_name = m.group(1).lower()
        jsx_name = _ATTR_MAP.get(attr_name, attr_name)
        return f'{jsx_name}={m.group(2)}{m.group(3)}{m.group(2)}'

    result = _RE_ATTR_GENERIC.sub(_replace_attr, result)

    # 6) Event handlers: onclick → onClick
    def _replace_event(m: re.Match) -> str:
        return _event_to_camel(m.group(1)) + "="

    result = _RE_EVENT_ATTR.sub(_replace_event, result)

    # 7) Self-closing tags: <br> → <br />, <img ...> → <img ... />
    def _fix_self_closing(m: re.Match) -> str:
        tag = m.group(1)
        attrs = m.group(2) or ""
        attrs = attrs.rstrip("/").rstrip()
        return f"<{tag}{attrs} />"

    result = _RE_SELF_CLOSING.sub(_fix_self_closing, result)

    # ZWNJ check
    zwnj_after = result.count(ZWNJ)
    if zwnj_after != zwnj_before:
        logger.warning(
            "⚠ JSX conversion ZWNJ change: %d → %d",
            zwnj_before, zwnj_after,
        )

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Import Generator / تولید import
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Component patterns to detect in MDX content
COMPONENT_PATTERNS: dict[str, str] = {
    "<Theorem": "Theorem",
    "<Definition": "Definition",
    "<Proof": "Proof",
    "<Admonition": "Admonition",
    "<Figure": "Figure",
    "<MermaidDiagram": "MermaidDiagram",
    "<Citation": "Citation",
    "<CrossRef": "CrossRef",
    "<BilingualBlock": "BilingualBlock",
    "<Details": "Details",
}

# Default import paths (configurable)
DEFAULT_IMPORT_PATHS: dict[str, str] = {
    "Theorem": "@/components/math/Theorem",
    "Definition": "@/components/math/Definition",
    "Proof": "@/components/math/Proof",
    "Admonition": "@/components/ui/Admonition",
    "Figure": "@/components/media/Figure",
    "MermaidDiagram": "@/components/diagrams/MermaidDiagram",
    "Citation": "@/components/refs/Citation",
    "CrossRef": "@/components/refs/CrossRef",
    "BilingualBlock": "@/components/i18n/BilingualBlock",
    "Details": "@/components/ui/Details",
}


def generate_imports(
    content: str,
    import_paths: Optional[dict[str, str]] = None,
) -> str:
    """
    تولید import statements بر اساس کامپوننت‌های استفاده‌شده.
    Generate import statements based on components found in content.

    اسکن محتوا برای الگوهای کامپوننت و تولید import مناسب.

    Args:
        content: محتوای MDX
        import_paths: نگاشت سفارشی نام → مسیر import
                     (پیش‌فرض: DEFAULT_IMPORT_PATHS)

    Returns:
        رشته import statements (هر خط یک import)
    """
    if not content:
        return ""

    paths = import_paths or DEFAULT_IMPORT_PATHS
    detected: list[str] = []

    for pattern, component_name in COMPONENT_PATTERNS.items():
        if pattern in content:
            if component_name in paths:
                detected.append(component_name)

    if not detected:
        return ""

    # Sort for deterministic output
    detected.sort()

    lines: list[str] = []
    for comp in detected:
        path = paths[comp]
        lines.append(f"import {comp} from '{path}';")

    return "\n".join(lines)


def detect_components(content: str) -> list[str]:
    """
    تشخیص کامپوننت‌های استفاده‌شده در محتوا.
    Detect which MDX components are used in content.

    Args:
        content: محتوای MDX

    Returns:
        لیست نام کامپوننت‌ها
    """
    found: list[str] = []
    for pattern, name in COMPONENT_PATTERNS.items():
        if pattern in content:
            found.append(name)
    return sorted(found)
