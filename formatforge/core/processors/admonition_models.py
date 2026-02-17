# -*- coding: utf-8-sig -*-
r"""Admonition data models for FormatForge.

Pydantic models for admonitions, theorems, and special environments.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AdmonitionKind(str, Enum):
    r"""Kind of admonition component in MDX output."""

    NOTE = "note"
    TIP = "tip"
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    CAUTION = "caution"
    IMPORTANT = "important"
    THEOREM = "theorem"
    LEMMA = "lemma"
    COROLLARY = "corollary"
    DEFINITION = "definition"
    EXAMPLE = "example"
    PROOF = "proof"
    REMARK = "remark"
    DETAILS = "details"
    CUSTOM = "custom"


class AdmonitionSource(str, Enum):
    r"""Source format of the admonition."""

    LATEX_ENV = "latex_env"         # theorem, definition, etc.
    LATEX_TCOLORBOX = "latex_tcolorbox"
    MD_CALLOUT = "md_callout"       # > [!NOTE]
    HTML_BOX = "html_box"           # <div class="note">
    RST_DIRECTIVE = "rst_directive"  # .. note::
    HTML_DETAILS = "html_details"   # <details><summary>


class AdmonitionRef(BaseModel):
    r"""A single admonition reference found in source text.

    Attributes:
        kind: Type of admonition (note, warning, theorem, etc).
        title: Optional title text.
        body: Content body of the admonition.
        source: Where this admonition came from.
        label: LaTeX label for cross-reference.
        number: Theorem/definition number if available.
        component: MDX component name to render.
        props: Extra properties for the component.
        original_text: Full original source text.
    """

    kind: AdmonitionKind = AdmonitionKind.NOTE
    title: Optional[str] = None
    body: str = ""
    source: AdmonitionSource = AdmonitionSource.LATEX_ENV
    label: Optional[str] = None
    number: Optional[str] = None
    component: str = "Admonition"
    props: dict = Field(default_factory=dict)
    original_text: str = ""


# ============================================================
# Environment mapping: LaTeX env name -> (component, props)
# ============================================================

ENVIRONMENT_MAP: dict = {
    'theorem':    ('Theorem',    {'type': 'theorem'}),
    'lemma':      ('Theorem',    {'type': 'lemma'}),
    'corollary':  ('Theorem',    {'type': 'corollary'}),
    'proposition':('Theorem',    {'type': 'proposition'}),
    'definition': ('Definition', {}),
    'example':    ('Example',    {}),
    'proof':      ('Proof',      {}),
    'remark':     ('Admonition', {'type': 'note'}),
    'note':       ('Admonition', {'type': 'note'}),
    'warningbox': ('Admonition', {'type': 'warning'}),
    'notebox':    ('Admonition', {'type': 'note'}),
    'caution':    ('Admonition', {'type': 'caution'}),
    'important':  ('Admonition', {'type': 'important'}),
}


# Markdown callout type mapping
MD_CALLOUT_MAP: dict = {
    'NOTE':      AdmonitionKind.NOTE,
    'TIP':       AdmonitionKind.TIP,
    'INFO':      AdmonitionKind.INFO,
    'WARNING':   AdmonitionKind.WARNING,
    'DANGER':    AdmonitionKind.DANGER,
    'CAUTION':   AdmonitionKind.CAUTION,
    'IMPORTANT': AdmonitionKind.IMPORTANT,
    'EXAMPLE':   AdmonitionKind.EXAMPLE,
    'ABSTRACT':  AdmonitionKind.INFO,
    'TODO':      AdmonitionKind.TIP,
    'BUG':       AdmonitionKind.DANGER,
    'QUOTE':     AdmonitionKind.NOTE,
}


# RST directive mapping
RST_DIRECTIVE_MAP: dict = {
    'note':      AdmonitionKind.NOTE,
    'tip':       AdmonitionKind.TIP,
    'warning':   AdmonitionKind.WARNING,
    'danger':    AdmonitionKind.DANGER,
    'caution':   AdmonitionKind.CAUTION,
    'important': AdmonitionKind.IMPORTANT,
    'hint':      AdmonitionKind.TIP,
    'attention': AdmonitionKind.WARNING,
    'error':     AdmonitionKind.DANGER,
    'seealso':   AdmonitionKind.INFO,
}


# HTML class to kind mapping
HTML_CLASS_MAP: dict = {
    'note':      AdmonitionKind.NOTE,
    'tip':       AdmonitionKind.TIP,
    'info':      AdmonitionKind.INFO,
    'warning':   AdmonitionKind.WARNING,
    'danger':    AdmonitionKind.DANGER,
    'caution':   AdmonitionKind.CAUTION,
    'important': AdmonitionKind.IMPORTANT,
    'alert':     AdmonitionKind.WARNING,
    'success':   AdmonitionKind.TIP,
}
