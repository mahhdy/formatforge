# -*- coding: utf-8-sig -*-
r"""Admonition processor for FormatForge.

Processes admonitions, theorems, callouts, and special environments
from LaTeX, Markdown, HTML, and RST sources into MDX components.
"""
from __future__ import annotations

import re
import logging
from typing import List, Optional, Tuple

from .admonition_models import (
    AdmonitionRef,
    AdmonitionKind,
    AdmonitionSource,
    ENVIRONMENT_MAP,
    MD_CALLOUT_MAP,
    RST_DIRECTIVE_MAP,
    HTML_CLASS_MAP,
)


logger = logging.getLogger(__name__)


# ============================================================
# Regex patterns
# ============================================================

_BS = chr(92)  # single backslash char

# LaTeX environment: matches \begin{name}[opt]...\end{name}
# Built with string concat to avoid chat/PS mangling
_ENV_NAMES = '|'.join(ENVIRONMENT_MAP.keys())
RE_LATEX_ENV = re.compile(
    _BS + _BS + r'begin\{(' + _ENV_NAMES + r')\}'
    + r'(.*?)'
    + _BS + _BS + r'end\{' + r'\1' + r'\}',
    re.DOTALL,
)

RE_TCOLORBOX = re.compile(
    _BS + _BS + r'begin\{tcolorbox\}'
    + r'(?:\[([^\]]*)\])?'
    + r'(.*?)'
    + _BS + _BS + r'end\{tcolorbox\}',
    re.DOTALL,
)

RE_LABEL = re.compile(
    _BS + _BS + r'label\{([^{}]*)\}'
)

RE_MD_CALLOUT = re.compile(
    r'^>[ \t]*\[!([A-Z]+)\][ \t]*(.*?)$',
    re.MULTILINE,
)

RE_MD_CALLOUT_BODY = re.compile(
    r'^>\s?(.*)$',
    re.MULTILINE,
)

RE_HTML_BOX = re.compile(
    '<div\\s+class="([^"]*)"[^>]*>(.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)

RE_HTML_DETAILS = re.compile(
    r'<details[^>]*>\s*(?:<summary[^>]*>(.*?)</summary>)?\s*(.*?)\s*</details>',
    re.DOTALL | re.IGNORECASE,
)

RE_RST_DIRECTIVE = re.compile(
    r'^\.\.\s+(note|tip|warning|danger|caution|important|hint|attention|error|seealso)::\s*(.*?)$',
    re.MULTILINE | re.IGNORECASE,
)

RE_TCB_TITLE = re.compile(r'title\s*=\s*([^,\]]+)')
RE_TCB_COLBACK = re.compile(r'colback\s*=\s*([^,\]]+)')


# ============================================================
# AdmonitionProcessor
# ============================================================


class AdmonitionProcessor:
    r"""Processor for converting admonitions and special environments to MDX.

    Handles LaTeX theorem/definition/proof environments, tcolorbox,
    Markdown callouts, HTML boxes, RST directives, and details/summary.
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        r"""Initialize admonition processor."""
        self.config = config or {}

    # --------------------------------------------------------
    # Finding admonitions
    # --------------------------------------------------------

    def find_admonitions(
        self, text: str, source_format: str = "latex"
    ) -> List[AdmonitionRef]:
        r"""Find all admonitions in source text.

        Args:
            text: Source document text.
            source_format: One of 'latex', 'markdown', 'html', 'rst'.

        Returns:
            List of AdmonitionRef objects found.
        """
        refs: List[AdmonitionRef] = []

        if source_format == "latex":
            refs.extend(self._find_latex_envs(text))
            refs.extend(self._find_tcolorbox(text))
        elif source_format == "markdown":
            refs.extend(self._find_md_callouts(text))
        elif source_format == "html":
            refs.extend(self._find_html_boxes(text))
            refs.extend(self._find_html_details(text))
        elif source_format == "rst":
            refs.extend(self._find_rst_directives(text))

        return refs

    def _find_latex_envs(self, text: str) -> List[AdmonitionRef]:
        r"""Find LaTeX theorem/definition/proof/etc environments."""
        refs: List[AdmonitionRef] = []
        for match in RE_LATEX_ENV.finditer(text):
            env_name = match.group(1)
            body = match.group(2).strip() if match.group(2) else ''

            # Extract [optional title] from start of body
            opt_title = None
            if body.startswith('['):
                close_idx = body.find(']')
                if close_idx != -1:
                    opt_title = body[1:close_idx].strip()
                    body = body[close_idx + 1:].strip()

            comp, props = ENVIRONMENT_MAP.get(env_name, ('Admonition', {}))
            kind = self._env_to_kind(env_name)

            # Extract label from body
            label = None
            label_match = RE_LABEL.search(body)
            if label_match:
                label = label_match.group(1)
                body = RE_LABEL.sub('', body).strip()

            refs.append(AdmonitionRef(
                kind=kind,
                title=opt_title,
                body=body,
                source=AdmonitionSource.LATEX_ENV,
                label=label,
                component=comp,
                props=dict(props),
                original_text=match.group(0),
            ))
        return refs
    
    def _find_tcolorbox(self, text: str) -> List[AdmonitionRef]:
        r"""Find LaTeX tcolorbox environments."""
        refs: List[AdmonitionRef] = []
        for match in RE_TCOLORBOX.finditer(text):
            opts = match.group(1) or ''
            body = match.group(2).strip()

            # Extract title from options
            title = None
            title_match = RE_TCB_TITLE.search(opts)
            if title_match:
                title = title_match.group(1).strip()

            # Guess kind from color or title
            kind = self._guess_tcolorbox_kind(opts, title)

            # Extract label from body
            label = None
            label_match = RE_LABEL.search(body)
            if label_match:
                label = label_match.group(1)
                body = RE_LABEL.sub('', body).strip()

            refs.append(AdmonitionRef(
                kind=kind,
                title=title,
                body=body,
                source=AdmonitionSource.LATEX_TCOLORBOX,
                label=label,
                component='Admonition',
                props={'type': kind.value},
                original_text=match.group(0),
            ))
        return refs

    def _find_md_callouts(self, text: str) -> List[AdmonitionRef]:
        r"""Find Markdown callouts: > [!TYPE] title."""
        refs: List[AdmonitionRef] = []
        # Find callout starts
        for match in RE_MD_CALLOUT.finditer(text):
            callout_type = match.group(1).upper()
            title = match.group(2).strip() or None
            kind = MD_CALLOUT_MAP.get(callout_type, AdmonitionKind.NOTE)

            # Collect body lines (subsequent > lines)
            start_pos = match.end()
            body_lines: List[str] = []
            remaining = text[start_pos:]
            for bline in remaining.split(chr(10)):
                stripped = bline.strip()
                if stripped.startswith('>'):
                    content = stripped[1:].strip()
                    body_lines.append(content)
                elif stripped == '' and body_lines:
                    # empty line ends callout only if we have body
                    break
                elif stripped == '':
                    continue  # skip leading blank lines
                else:
                    break

            body = chr(10).join(body_lines)

            # Build original text for replacement
            orig_lines = [match.group(0)]
            for bl in body_lines:
                orig_lines.append('> ' + bl)
            original = chr(10).join(orig_lines)

            refs.append(AdmonitionRef(
                kind=kind,
                title=title,
                body=body,
                source=AdmonitionSource.MD_CALLOUT,
                component='Admonition',
                props={'type': kind.value},
                original_text=original,
            ))
        return refs

    def _find_html_boxes(self, text: str) -> List[AdmonitionRef]:
        r"""Find HTML admonition divs with known classes."""
        refs: List[AdmonitionRef] = []
        for match in RE_HTML_BOX.finditer(text):
            class_str = match.group(1).lower()
            body = match.group(2).strip()

            kind = AdmonitionKind.NOTE
            for cls_name, cls_kind in HTML_CLASS_MAP.items():
                if cls_name in class_str:
                    kind = cls_kind
                    break

            refs.append(AdmonitionRef(
                kind=kind,
                body=body,
                source=AdmonitionSource.HTML_BOX,
                component='Admonition',
                props={'type': kind.value},
                original_text=match.group(0),
            ))
        return refs

    def _find_html_details(self, text: str) -> List[AdmonitionRef]:
        r"""Find HTML <details><summary> elements."""
        refs: List[AdmonitionRef] = []
        for match in RE_HTML_DETAILS.finditer(text):
            summary = match.group(1)
            body = match.group(2).strip()

            refs.append(AdmonitionRef(
                kind=AdmonitionKind.DETAILS,
                title=summary.strip() if summary else None,
                body=body,
                source=AdmonitionSource.HTML_DETAILS,
                component='Details',
                original_text=match.group(0),
            ))
        return refs

    def _find_rst_directives(self, text: str) -> List[AdmonitionRef]:
        r"""Find RST admonition directives: .. note:: etc."""
        refs: List[AdmonitionRef] = []
        for match in RE_RST_DIRECTIVE.finditer(text):
            directive = match.group(1).lower()
            title = match.group(2).strip() or None
            kind = RST_DIRECTIVE_MAP.get(directive, AdmonitionKind.NOTE)

            # Collect indented body lines
            start_pos = match.end()
            body_lines: List[str] = []
            remaining = text[start_pos:]
            for bline in remaining.split(chr(10)):
                if bline.startswith('   ') or bline.startswith(chr(9)):
                    body_lines.append(bline.strip())
                elif bline.strip() == '' and not body_lines:
                    continue  # skip blank lines before body
                elif bline.strip() == '' and body_lines:
                    body_lines.append('')  # preserve inner blank lines
                else:
                    break

            # Strip trailing empty lines
            while body_lines and body_lines[-1] == '':
                body_lines.pop()

            body = chr(10).join(body_lines)

            refs.append(AdmonitionRef(
                kind=kind,
                title=title,
                body=body,
                source=AdmonitionSource.RST_DIRECTIVE,
                component='Admonition',
                props={'type': kind.value},
                original_text=match.group(0),
            ))
        return refs

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def _env_to_kind(env_name: str) -> AdmonitionKind:
        r"""Convert LaTeX environment name to AdmonitionKind."""
        mapping = {
            'theorem': AdmonitionKind.THEOREM,
            'lemma': AdmonitionKind.LEMMA,
            'corollary': AdmonitionKind.COROLLARY,
            'proposition': AdmonitionKind.THEOREM,
            'definition': AdmonitionKind.DEFINITION,
            'example': AdmonitionKind.EXAMPLE,
            'proof': AdmonitionKind.PROOF,
            'remark': AdmonitionKind.REMARK,
            'note': AdmonitionKind.NOTE,
            'warningbox': AdmonitionKind.WARNING,
            'notebox': AdmonitionKind.NOTE,
            'caution': AdmonitionKind.CAUTION,
            'important': AdmonitionKind.IMPORTANT,
        }
        return mapping.get(env_name, AdmonitionKind.NOTE)

    @staticmethod
    def _guess_tcolorbox_kind(opts: str, title: Optional[str]) -> AdmonitionKind:
        r"""Guess tcolorbox admonition kind from options and title."""
        opts_lower = opts.lower()
        title_lower = (title or '').lower()

        # Check colors for hints
        if 'red' in opts_lower or 'danger' in title_lower:
            return AdmonitionKind.DANGER
        if 'yellow' in opts_lower or 'warning' in title_lower:
            return AdmonitionKind.WARNING
        if 'green' in opts_lower or 'tip' in title_lower:
            return AdmonitionKind.TIP
        if 'blue' in opts_lower or 'info' in title_lower:
            return AdmonitionKind.INFO

        # Check title keywords
        for kw, kind in [
            ('theorem', AdmonitionKind.THEOREM),
            ('definition', AdmonitionKind.DEFINITION),
            ('example', AdmonitionKind.EXAMPLE),
            ('proof', AdmonitionKind.PROOF),
            ('note', AdmonitionKind.NOTE),
            ('warning', AdmonitionKind.WARNING),
            ('caution', AdmonitionKind.CAUTION),
        ]:
            if kw in title_lower:
                return kind

        return AdmonitionKind.NOTE

    # --------------------------------------------------------
    # Rendering to MDX
    # --------------------------------------------------------

    def render_mdx(self, ref: AdmonitionRef) -> str:
        r"""Render a single AdmonitionRef as MDX component.

        Args:
            ref: Admonition reference to render.

        Returns:
            MDX-compatible string.
        """
        comp = ref.component
        attrs = self._build_attrs(ref)
        body = ref.body

        out_parts: List[str] = []
        out_parts.append('<' + comp + attrs + '>')
        if body:
            out_parts.append('')
            out_parts.append(body)
            out_parts.append('')
        out_parts.append('</' + comp + '>')
        return chr(10).join(out_parts)

    def _build_attrs(self, ref: AdmonitionRef) -> str:
        r"""Build attribute string for MDX component tag."""
        parts: List[str] = []

        # type prop
        if ref.props.get('type'):
            parts.append(' type=' + chr(34) + ref.props['type'] + chr(34))

        # title prop
        if ref.title:
            parts.append(' title=' + chr(34) + ref.title + chr(34))

        # label as id
        if ref.label:
            parts.append(' id=' + chr(34) + ref.label + chr(34))

        return ''.join(parts)

    # --------------------------------------------------------
    # Full text processing
    # --------------------------------------------------------

    def process(
        self,
        text: str,
        source_format: str = "latex",
    ) -> str:
        r"""Process all admonitions in text.

        Args:
            text: Full source text.
            source_format: Input format.

        Returns:
            Text with admonitions replaced by MDX components.
        """
        refs = self.find_admonitions(text, source_format)
        result = text
        for ref in refs:
            if ref.original_text:
                mdx = self.render_mdx(ref)
                result = result.replace(ref.original_text, mdx, 1)
        return result
