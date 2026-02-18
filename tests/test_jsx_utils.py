"""
تست‌های JSX Utilities — S06-C2
Tests for HTML→JSX conversion and import generation.
"""

from __future__ import annotations

import pytest

from formatforge.core.converters.jsx_utils import (
    COMPONENT_PATTERNS,
    DEFAULT_IMPORT_PATHS,
    convert_html_to_jsx,
    detect_components,
    generate_imports,
    _css_to_jsx_style,
    _kebab_to_camel,
    _event_to_camel,
)

ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: CSS → JSX style
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCSSToJSXStyle:
    """تست تبدیل CSS به JSX style."""

    def test_simple_property(self) -> None:
        result = _css_to_jsx_style("color: red")
        assert "color" in result
        assert "'red'" in result

    def test_kebab_case(self) -> None:
        result = _css_to_jsx_style("font-size: 14px")
        assert "fontSize" in result
        assert "'14px'" in result

    def test_multiple_properties(self) -> None:
        result = _css_to_jsx_style("color: red; font-size: 14px")
        assert "color" in result
        assert "fontSize" in result

    def test_numeric_value(self) -> None:
        result = _css_to_jsx_style("opacity: 0.5")
        assert "0.5" in result
        # Numeric values should not be quoted
        assert "'0.5'" not in result

    def test_empty_string(self) -> None:
        result = _css_to_jsx_style("")
        assert result == "{{}}"

    def test_background_color(self) -> None:
        result = _css_to_jsx_style("background-color: #fff")
        assert "backgroundColor" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: kebab → camelCase
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestKebabToCamel:
    """تست تبدیل kebab-case به camelCase."""

    def test_font_size(self) -> None:
        assert _kebab_to_camel("font-size") == "fontSize"

    def test_background_color(self) -> None:
        assert _kebab_to_camel("background-color") == "backgroundColor"

    def test_no_dash(self) -> None:
        assert _kebab_to_camel("color") == "color"

    def test_multiple_dashes(self) -> None:
        assert _kebab_to_camel("border-top-width") == "borderTopWidth"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: event → camelCase
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEventToCamel:
    """تست تبدیل event handler."""

    def test_onclick(self) -> None:
        assert _event_to_camel("onclick") == "onClick"

    def test_onmousedown(self) -> None:
        assert _event_to_camel("onmousedown") == "onMousedown"

    def test_onchange(self) -> None:
        assert _event_to_camel("onchange") == "onChange"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: HTML → JSX conversion
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConvertHTMLToJSX:
    """تست تبدیل HTML به JSX."""

    def test_class_to_classname(self) -> None:
        result = convert_html_to_jsx('<div class="container">')
        assert 'className="container"' in result
        assert 'class=' not in result

    def test_for_to_htmlfor(self) -> None:
        result = convert_html_to_jsx('<label for="name">')
        assert 'htmlFor="name"' in result
        assert 'for=' not in result

    def test_style_conversion(self) -> None:
        result = convert_html_to_jsx('<div style="color: red">')
        assert "style={{" in result
        assert "color" in result

    def test_html_comment_to_jsx(self) -> None:
        result = convert_html_to_jsx("<!-- comment -->")
        assert "{/*" in result
        assert "*/}" in result
        assert "comment" in result

    def test_br_self_closing(self) -> None:
        result = convert_html_to_jsx("<br>")
        assert "<br />" in result

    def test_hr_self_closing(self) -> None:
        result = convert_html_to_jsx("<hr>")
        assert "<hr />" in result

    def test_img_self_closing(self) -> None:
        result = convert_html_to_jsx('<img src="test.png">')
        assert '<img src="test.png" />' in result

    def test_already_self_closed(self) -> None:
        result = convert_html_to_jsx("<br />")
        assert "<br />" in result

    def test_tabindex(self) -> None:
        result = convert_html_to_jsx('<div tabindex="0">')
        assert 'tabIndex="0"' in result

    def test_empty_input(self) -> None:
        assert convert_html_to_jsx("") == ""

    def test_none_input(self) -> None:
        assert convert_html_to_jsx(None) is None

    def test_no_html(self) -> None:
        text = "Just plain text"
        assert convert_html_to_jsx(text) == text

    def test_multiple_conversions(self) -> None:
        html = '<div class="box" style="color: red"><!-- note --><br></div>'
        result = convert_html_to_jsx(html)
        assert "className" in result
        assert "style={{" in result
        assert "{/*" in result
        assert "<br />" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: ZWNJ preservation in JSX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestJSXZWNJPreservation:
    """تست حفظ نیم‌فاصله در تبدیل JSX."""

    def test_zwnj_in_class(self) -> None:
        html = f'<div class="می{ZWNJ}شود">text</div>'
        result = convert_html_to_jsx(html)
        assert ZWNJ in result

    def test_zwnj_in_content(self) -> None:
        html = f"<p>نمی{ZWNJ}توان</p>"
        result = convert_html_to_jsx(html)
        assert result.count(ZWNJ) == 1

    def test_zwnj_preserved_count(self) -> None:
        html = f"<p>می{ZWNJ}شود و نمی{ZWNJ}توان</p>"
        result = convert_html_to_jsx(html)
        assert result.count(ZWNJ) == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Import Generator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestGenerateImports:
    """تست تولید import statements."""

    def test_single_component(self) -> None:
        content = '<Theorem title="test">body</Theorem>'
        imports = generate_imports(content)
        assert "import Theorem from" in imports

    def test_multiple_components(self) -> None:
        content = (
            "<Theorem>t</Theorem>\n"
            "<Admonition type='note'>a</Admonition>"
        )
        imports = generate_imports(content)
        assert "import Theorem" in imports
        assert "import Admonition" in imports

    def test_no_components(self) -> None:
        content = "Just regular markdown text"
        imports = generate_imports(content)
        assert imports == ""

    def test_empty_content(self) -> None:
        assert generate_imports("") == ""

    def test_mermaid_diagram(self) -> None:
        content = "<MermaidDiagram>graph LR</MermaidDiagram>"
        imports = generate_imports(content)
        assert "MermaidDiagram" in imports

    def test_custom_import_paths(self) -> None:
        custom = {"Theorem": "./components/Theorem"}
        content = "<Theorem>test</Theorem>"
        imports = generate_imports(content, import_paths=custom)
        assert "'./components/Theorem'" in imports

    def test_sorted_output(self) -> None:
        content = "<Proof>p</Proof>\n<Admonition>a</Admonition>"
        imports = generate_imports(content)
        lines = imports.strip().split("\n")
        assert len(lines) == 2
        # Should be alphabetically sorted
        assert "Admonition" in lines[0]
        assert "Proof" in lines[1]

    def test_all_standard_components(self) -> None:
        # All patterns should have corresponding import paths
        for pattern, name in COMPONENT_PATTERNS.items():
            assert name in DEFAULT_IMPORT_PATHS, (
                f"Component {name} missing from DEFAULT_IMPORT_PATHS"
            )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Component Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDetectComponents:
    """تست تشخیص کامپوننت‌ها."""

    def test_detect_theorem(self) -> None:
        found = detect_components("<Theorem>test</Theorem>")
        assert "Theorem" in found

    def test_detect_multiple(self) -> None:
        found = detect_components(
            "<Theorem>t</Theorem><Proof>p</Proof>"
        )
        assert "Theorem" in found
        assert "Proof" in found

    def test_detect_none(self) -> None:
        found = detect_components("plain text")
        assert found == []

    def test_sorted(self) -> None:
        found = detect_components(
            "<Proof>p</Proof><Admonition>a</Admonition>"
        )
        assert found == sorted(found)
