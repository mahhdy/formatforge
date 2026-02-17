"""
FormatForge - Processors Package
پکیج پردازشگرهای تخصصی
"""

from formatforge.core.processors.base import (
    BaseProcessor,
    ProcessorContext,
    ProcessorError,
    PipelineError,
    ProcessorPipeline,
    ProcessorStepResult,
    PipelineResult,
)

from formatforge.core.processors.rtl_processor import (
    RTLProcessor,
)

from formatforge.core.processors.math_processor import (
    MathProcessor,
    MathType,
    MathBlock,
    MathStats,
    extract_math_blocks,
    count_math_blocks,
    validate_math_syntax,
)

from formatforge.core.processors.code_processor import (
    CodeProcessor,
    CodeBlock,
    CodeBlockType,
    CodeStats,
    extract_code_blocks,
    detect_language,
)

from formatforge.core.processors.link_processor import (
    LinkProcessor,
    LabelInfo,
    FootnoteInfo,
    LinkStats,
    collect_labels,
    collect_citations,
    collect_footnotes,
    resolve_cross_references,
)

from formatforge.core.processors.footnote_processor import (
    FootnoteProcessor,
    Footnote,
    FootnoteType,
    FootnoteStats,
    extract_footnotes,
    count_footnotes,
)

from formatforge.core.processors.bibliography_processor import (
    BibliographyProcessor,
    BibEntry,
    BibStats,
    parse_bib_content,
    parse_bib_file,
    entries_to_json,
    generate_bibliography_mdx,
)

__all__ = [
    # base
    "BaseProcessor",
    "ProcessorContext",
    "ProcessorError",
    "PipelineError",
    "ProcessorPipeline",
    "ProcessorStepResult",
    "PipelineResult",
    # rtl
    "RTLProcessor",
    # math
    "MathProcessor",
    "MathType",
    "MathBlock",
    "MathStats",
    "extract_math_blocks",
    "count_math_blocks",
    "validate_math_syntax",
    # code
    "CodeProcessor",
    "CodeBlock",
    "CodeBlockType",
    "CodeStats",
    "extract_code_blocks",
    "detect_language",
    # link
    "LinkProcessor",
    "LabelInfo",
    "FootnoteInfo",
    "LinkStats",
    "collect_labels",
    "collect_citations",
    "collect_footnotes",
    "resolve_cross_references",
    # footnote
    "FootnoteProcessor",
    "Footnote",
    "FootnoteType",
    "FootnoteStats",
    "extract_footnotes",
    "count_footnotes",
    # bibliography
    "BibliographyProcessor",
    "BibEntry",
    "BibStats",
    "parse_bib_content",
    "parse_bib_file",
    "entries_to_json",
    "generate_bibliography_mdx",
]