# -*- coding: utf-8-sig -*-
r"""Tests for admonition_processor module.

Test suite for FormatForge admonition processing.
"""
import pytest

from formatforge.core.processors.admonition_models import (
    AdmonitionRef,
    AdmonitionKind,
    AdmonitionSource,
    ENVIRONMENT_MAP,
    MD_CALLOUT_MAP,
    RST_DIRECTIVE_MAP,
    HTML_CLASS_MAP,
)
from formatforge.core.processors.admonition_processor import AdmonitionProcessor


ZWNJ = chr(0x200C)
BS = chr(92)
LBRACE = chr(123)
RBRACE = chr(125)


@pytest.fixture
def processor() -> AdmonitionProcessor:
    r"""Create a default AdmonitionProcessor instance."""
    return AdmonitionProcessor()


# ============================================================
# Test 1: LaTeX theorem/definition/proof environments
# ============================================================


class TestLatexEnvironments:
    r"""Tests for LaTeX environment detection."""

    def test_theorem_with_title(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing theorem environment with optional title."""
        text = (
            BS + 'begin' + LBRACE + 'theorem' + RBRACE + '[Pythagorean]'
            + chr(10)
            + 'a^2 + b^2 = c^2'
            + chr(10)
            + BS + 'end' + LBRACE + 'theorem' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.THEOREM
        assert refs[0].title == 'Pythagorean'
        assert 'a^2' in refs[0].body
        assert refs[0].component == 'Theorem'

    def test_theorem_without_title(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing theorem without optional title."""
        text = (
            BS + 'begin' + LBRACE + 'theorem' + RBRACE
            + chr(10)
            + 'Some statement.'
            + chr(10)
            + BS + 'end' + LBRACE + 'theorem' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].title is None
        assert 'Some statement.' in refs[0].body

    def test_definition_env(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing definition environment."""
        text = (
            BS + 'begin' + LBRACE + 'definition' + RBRACE + '[Group]'
            + chr(10)
            + 'A group is a set with an operation.'
            + chr(10)
            + BS + 'end' + LBRACE + 'definition' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.DEFINITION
        assert refs[0].component == 'Definition'
        assert refs[0].title == 'Group'

    def test_proof_env(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing proof environment."""
        text = (
            BS + 'begin' + LBRACE + 'proof' + RBRACE
            + chr(10)
            + 'This follows from axiom 1.'
            + chr(10)
            + BS + 'end' + LBRACE + 'proof' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.PROOF
        assert refs[0].component == 'Proof'

    def test_lemma_env(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing lemma environment."""
        text = (
            BS + 'begin' + LBRACE + 'lemma' + RBRACE
            + chr(10)
            + 'A useful lemma.'
            + chr(10)
            + BS + 'end' + LBRACE + 'lemma' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.LEMMA
        assert refs[0].component == 'Theorem'
        assert refs[0].props.get('type') == 'lemma'

    def test_env_with_label(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing environment with label."""
        text = (
            BS + 'begin' + LBRACE + 'theorem' + RBRACE + '[Main]'
            + chr(10)
            + BS + 'label' + LBRACE + 'thm:main' + RBRACE
            + chr(10)
            + 'The main theorem.'
            + chr(10)
            + BS + 'end' + LBRACE + 'theorem' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].label == 'thm:main'
        assert refs[0].title == 'Main'
        assert 'thm:main' not in refs[0].body

    def test_example_env(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing example environment."""
        text = (
            BS + 'begin' + LBRACE + 'example' + RBRACE
            + chr(10)
            + 'Consider x=1.'
            + chr(10)
            + BS + 'end' + LBRACE + 'example' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.EXAMPLE
        assert refs[0].component == 'Example'

    def test_remark_env(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing remark environment."""
        text = (
            BS + 'begin' + LBRACE + 'remark' + RBRACE
            + chr(10)
            + 'Note this fact.'
            + chr(10)
            + BS + 'end' + LBRACE + 'remark' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.REMARK
        assert refs[0].component == 'Admonition'

    def test_multiple_envs(self, processor: AdmonitionProcessor) -> None:
        r"""Test finding multiple environments in one text."""
        text = (
            BS + 'begin' + LBRACE + 'theorem' + RBRACE
            + chr(10) + 'T1' + chr(10)
            + BS + 'end' + LBRACE + 'theorem' + RBRACE
            + chr(10)
            + BS + 'begin' + LBRACE + 'proof' + RBRACE
            + chr(10) + 'P1' + chr(10)
            + BS + 'end' + LBRACE + 'proof' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 2
        assert refs[0].kind == AdmonitionKind.THEOREM
        assert refs[1].kind == AdmonitionKind.PROOF


# ============================================================
# Test 2: tcolorbox
# ============================================================


class TestTcolorbox:
    r"""Tests for tcolorbox detection."""

    def test_tcolorbox_with_title(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing tcolorbox with title option."""
        text = (
            BS + 'begin' + LBRACE + 'tcolorbox' + RBRACE + '[title=Important Note]'
            + chr(10)
            + 'Some important content.'
            + chr(10)
            + BS + 'end' + LBRACE + 'tcolorbox' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].title == 'Important Note'
        assert refs[0].source == AdmonitionSource.LATEX_TCOLORBOX

    def test_tcolorbox_red_is_danger(self, processor: AdmonitionProcessor) -> None:
        r"""Test that red tcolorbox maps to danger."""
        text = (
            BS + 'begin' + LBRACE + 'tcolorbox' + RBRACE + '[colback=red!10]'
            + chr(10)
            + 'Danger zone.'
            + chr(10)
            + BS + 'end' + LBRACE + 'tcolorbox' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.DANGER

    def test_tcolorbox_no_options(self, processor: AdmonitionProcessor) -> None:
        r"""Test tcolorbox without options."""
        text = (
            BS + 'begin' + LBRACE + 'tcolorbox' + RBRACE
            + chr(10)
            + 'Plain box.'
            + chr(10)
            + BS + 'end' + LBRACE + 'tcolorbox' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.NOTE  # default

    def test_tcolorbox_with_label(self, processor: AdmonitionProcessor) -> None:
        r"""Test tcolorbox with label in body."""
        text = (
            BS + 'begin' + LBRACE + 'tcolorbox' + RBRACE + '[title=Tip]'
            + chr(10)
            + BS + 'label' + LBRACE + 'box:tip1' + RBRACE
            + chr(10)
            + 'A useful tip.'
            + chr(10)
            + BS + 'end' + LBRACE + 'tcolorbox' + RBRACE
        )
        refs = processor.find_admonitions(text, 'latex')
        assert len(refs) == 1
        assert refs[0].label == 'box:tip1'
        assert 'box:tip1' not in refs[0].body


# ============================================================
# Test 3: Markdown callouts
# ============================================================


class TestMarkdownCallouts:
    r"""Tests for Markdown callout detection."""

    def test_note_callout(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing > [!NOTE] callout."""
        text = (
            '> [!NOTE]' + chr(10)
            + '> This is a note.' + chr(10)
            + '> Second line.'
        )
        refs = processor.find_admonitions(text, 'markdown')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.NOTE
        assert 'This is a note.' in refs[0].body
        assert 'Second line.' in refs[0].body

    def test_warning_callout(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing > [!WARNING] callout."""
        text = (
            '> [!WARNING] Be careful' + chr(10)
            + '> Something dangerous.'
        )
        refs = processor.find_admonitions(text, 'markdown')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.WARNING
        assert refs[0].title == 'Be careful'

    def test_tip_callout(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing > [!TIP] callout."""
        text = (
            '> [!TIP]' + chr(10)
            + '> A handy tip.'
        )
        refs = processor.find_admonitions(text, 'markdown')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.TIP

    def test_callout_no_body(self, processor: AdmonitionProcessor) -> None:
        r"""Test callout with only header, no body lines."""
        text = '> [!INFO] Just a header'
        refs = processor.find_admonitions(text, 'markdown')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.INFO
        assert refs[0].title == 'Just a header'


# ============================================================
# Test 4: HTML admonition boxes
# ============================================================


class TestHTMLBoxes:
    r"""Tests for HTML admonition box detection."""

    def test_note_div(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing <div class="note">."""
        text = '<div class=' + chr(34) + 'note' + chr(34) + '>Note content here.</div>'
        refs = processor.find_admonitions(text, 'html')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.NOTE
        assert 'Note content here.' in refs[0].body

    def test_warning_div(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing <div class="warning">."""
        text = '<div class=' + chr(34) + 'warning' + chr(34) + '>Watch out!</div>'
        refs = processor.find_admonitions(text, 'html')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.WARNING

    def test_unknown_class_defaults_note(self, processor: AdmonitionProcessor) -> None:
        r"""Test that unknown class defaults to NOTE."""
        text = '<div class=' + chr(34) + 'custom-box' + chr(34) + '>Content.</div>'
        refs = processor.find_admonitions(text, 'html')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.NOTE


# ============================================================
# Test 5: HTML details/summary
# ============================================================


class TestHTMLDetails:
    r"""Tests for HTML details/summary detection."""

    def test_details_with_summary(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing <details><summary>."""
        text = '<details><summary>Click me</summary>Hidden content.</details>'
        refs = processor.find_admonitions(text, 'html')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.DETAILS
        assert refs[0].title == 'Click me'
        assert 'Hidden content.' in refs[0].body
        assert refs[0].component == 'Details'

    def test_details_without_summary(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing <details> without <summary>."""
        text = '<details>Just content.</details>'
        refs = processor.find_admonitions(text, 'html')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.DETAILS
        assert refs[0].title is None


# ============================================================
# Test 6: RST directives
# ============================================================


class TestRSTDirectives:
    r"""Tests for RST admonition directive detection."""

    def test_note_directive(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing .. note:: directive."""
        text = (
            '.. note:: Important' + chr(10)
            + '   This is the body.' + chr(10)
            + '   Second line.'
        )
        refs = processor.find_admonitions(text, 'rst')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.NOTE
        assert refs[0].title == 'Important'
        assert 'This is the body.' in refs[0].body
        assert 'Second line.' in refs[0].body

    def test_warning_directive(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing .. warning:: directive."""
        text = (
            '.. warning::' + chr(10)
            + '   Be careful here.'
        )
        refs = processor.find_admonitions(text, 'rst')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.WARNING

    def test_tip_directive(self, processor: AdmonitionProcessor) -> None:
        r"""Test parsing .. tip:: directive."""
        text = (
            '.. tip::' + chr(10)
            + '   A helpful tip.'
        )
        refs = processor.find_admonitions(text, 'rst')
        assert len(refs) == 1
        assert refs[0].kind == AdmonitionKind.TIP


# ============================================================
# Test 7: MDX rendering
# ============================================================


class TestMDXRendering:
    r"""Tests for MDX component rendering."""

    def test_render_theorem(self, processor: AdmonitionProcessor) -> None:
        r"""Test rendering theorem as MDX component."""
        ref = AdmonitionRef(
            kind=AdmonitionKind.THEOREM,
            title='Pythagorean',
            body='a^2 + b^2 = c^2',
            component='Theorem',
            props={'type': 'theorem'},
            label='thm:pyth',
        )
        result = processor.render_mdx(ref)
        assert '<Theorem' in result
        assert 'Pythagorean' in result
        assert 'thm:pyth' in result
        assert 'a^2 + b^2 = c^2' in result
        assert '</Theorem>' in result

    def test_render_admonition_note(self, processor: AdmonitionProcessor) -> None:
        r"""Test rendering note admonition."""
        ref = AdmonitionRef(
            kind=AdmonitionKind.NOTE,
            body='Remember this.',
            component='Admonition',
            props={'type': 'note'},
        )
        result = processor.render_mdx(ref)
        assert '<Admonition' in result
        assert 'type=' in result
        assert 'note' in result
        assert 'Remember this.' in result
        assert '</Admonition>' in result

    def test_render_details(self, processor: AdmonitionProcessor) -> None:
        r"""Test rendering details component."""
        ref = AdmonitionRef(
            kind=AdmonitionKind.DETAILS,
            title='Click to expand',
            body='Hidden info.',
            component='Details',
        )
        result = processor.render_mdx(ref)
        assert '<Details' in result
        assert 'Click to expand' in result
        assert 'Hidden info.' in result
        assert '</Details>' in result

    def test_render_without_title(self, processor: AdmonitionProcessor) -> None:
        r"""Test rendering without title."""
        ref = AdmonitionRef(
            body='Just body.',
            component='Admonition',
            props={'type': 'note'},
        )
        result = processor.render_mdx(ref)
        assert '<Admonition' in result
        assert 'title=' not in result

    def test_render_empty_body(self, processor: AdmonitionProcessor) -> None:
        r"""Test rendering with empty body."""
        ref = AdmonitionRef(
            component='Admonition',
            props={'type': 'warning'},
        )
        result = processor.render_mdx(ref)
        assert '<Admonition' in result
        assert '</Admonition>' in result


# ============================================================
# Test 8: Full text processing (e2e)
# ============================================================


class TestFullProcess:
    r"""End-to-end tests for admonition processing."""

    def test_process_latex(self, processor: AdmonitionProcessor) -> None:
        r"""Test full process on LaTeX theorem."""
        text = (
            'Before text.' + chr(10)
            + BS + 'begin' + LBRACE + 'theorem' + RBRACE + '[Cool]'
            + chr(10)
            + 'Statement here.'
            + chr(10)
            + BS + 'end' + LBRACE + 'theorem' + RBRACE
            + chr(10)
            + 'After text.'
        )
        result = processor.process(text, 'latex')
        assert '<Theorem' in result
        assert 'Before text.' in result
        assert 'After text.' in result
        assert 'Statement here.' in result

    def test_process_markdown(self, processor: AdmonitionProcessor) -> None:
        r"""Test full process on Markdown callout."""
        text = (
            'Before.' + chr(10)
            + '> [!WARNING] Watch out' + chr(10)
            + '> Be careful.' + chr(10)
            + 'After.'
        )
        result = processor.process(text, 'markdown')
        assert '<Admonition' in result
        assert 'warning' in result

    def test_process_html(self, processor: AdmonitionProcessor) -> None:
        r"""Test full process on HTML box."""
        text = '<p>Before</p><div class=' + chr(34) + 'note' + chr(34) + '>Note body.</div><p>After</p>'
        result = processor.process(text, 'html')
        assert '<Admonition' in result
        assert 'Note body.' in result

    def test_process_preserves_unrelated(self, processor: AdmonitionProcessor) -> None:
        r"""Test that non-admonition text is preserved."""
        text = 'Just regular text, no admonitions.'
        result = processor.process(text, 'latex')
        assert result == text


# ============================================================
# Test 9: Persian content in admonitions
# ============================================================


class TestPersianAdmonitions:
    r"""Tests for Persian content in admonitions."""

    def test_persian_theorem_title(self, processor: AdmonitionProcessor) -> None:
        r"""Test Persian title in theorem."""
        ref = AdmonitionRef(
            kind=AdmonitionKind.THEOREM,
            title='قضیه فیثاغورس',
            body='a^2 + b^2 = c^2',
            component='Theorem',
            props={'type': 'theorem'},
        )
        result = processor.render_mdx(ref)
        assert 'قضیه فیثاغورس' in result

    def test_persian_body(self, processor: AdmonitionProcessor) -> None:
        r"""Test Persian body text."""
        ref = AdmonitionRef(
            body='این یک نکته مهم است.',
            component='Admonition',
            props={'type': 'note'},
        )
        result = processor.render_mdx(ref)
        assert 'این یک نکته مهم است.' in result

    def test_persian_zwnj_preserved(self, processor: AdmonitionProcessor) -> None:
        r"""Test ZWNJ preservation in admonition."""
        body = 'کتاب' + ZWNJ + 'خانه'
        ref = AdmonitionRef(
            body=body,
            component='Admonition',
            props={'type': 'note'},
        )
        result = processor.render_mdx(ref)
        assert ZWNJ in result
        assert 'کتاب' in result
        assert 'خانه' in result


# ============================================================
# Test 10: Models and mappings
# ============================================================


class TestModelsAndMaps:
    r"""Tests for data models and mapping dictionaries."""

    def test_environment_map_completeness(self) -> None:
        r"""Test that ENVIRONMENT_MAP has expected keys."""
        for env in ['theorem', 'lemma', 'definition', 'proof', 'example', 'remark']:
            assert env in ENVIRONMENT_MAP

    def test_md_callout_map_completeness(self) -> None:
        r"""Test that MD_CALLOUT_MAP has expected keys."""
        for key in ['NOTE', 'WARNING', 'TIP', 'DANGER', 'CAUTION']:
            assert key in MD_CALLOUT_MAP

    def test_rst_directive_map_completeness(self) -> None:
        r"""Test that RST_DIRECTIVE_MAP has expected keys."""
        for key in ['note', 'tip', 'warning', 'danger', 'caution']:
            assert key in RST_DIRECTIVE_MAP

    def test_html_class_map_completeness(self) -> None:
        r"""Test that HTML_CLASS_MAP has expected keys."""
        for key in ['note', 'warning', 'danger', 'tip']:
            assert key in HTML_CLASS_MAP

    def test_admonition_ref_defaults(self) -> None:
        r"""Test AdmonitionRef default values."""
        ref = AdmonitionRef()
        assert ref.kind == AdmonitionKind.NOTE
        assert ref.title is None
        assert ref.body == ''
        assert ref.component == 'Admonition'
        assert ref.label is None

