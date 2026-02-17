"""
FormatForge - Code Processor Tests
تست‌های پردازشگر بلوک‌های کد

Tests for:
- LaTeX lstlisting conversion
- LaTeX minted conversion
- LaTeX verbatim conversion
- HTML <pre><code> conversion
- Inline \texttt and \verb
- Language detection
- Title/caption preservation
- Label/id conversion
- Line numbers
- ZWNJ preservation
- Extraction and counting
"""

from __future__ import annotations

import pytest

from formatforge.core.processors.code_processor import (
    CodeProcessor,
    CodeBlock,
    CodeBlockType,
    CodeStats,
    extract_code_blocks,
    detect_language,
    _normalize_language,
    _build_fence,
)
from formatforge.core.processors.base import (
    ProcessorContext,
)

# ─── Constants / ثابت‌ها ──────────────────────
ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures / فیکسچرها
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def processor() -> CodeProcessor:
    """پردازشگر کد پیش‌فرض."""
    return CodeProcessor()


@pytest.fixture
def ctx() -> ProcessorContext:
    """زمینه پردازش پیش‌فرض."""
    return ProcessorContext(source_format="latex", language="fa")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: LaTeX lstlisting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLstlisting:
    """تست تبدیل lstlisting."""

    def test_basic_lstlisting(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """lstlisting ساده بدون گزینه."""
        text = (
            "\\begin{lstlisting}\n"
            "print('hello')\n"
            "\\end{lstlisting}"
        )
        result = processor.process(text, ctx)
        assert "```" in result
        assert "print('hello')" in result
        assert "\\begin{lstlisting}" not in result

    def test_lstlisting_with_language(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """lstlisting با زبان مشخص."""
        text = (
            "\\begin{lstlisting}[language=Python]\n"
            "def foo():\n"
            "    return 42\n"
            "\\end{lstlisting}"
        )
        result = processor.process(text, ctx)
        assert "```python" in result
        assert "def foo():" in result

    def test_lstlisting_with_caption(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """lstlisting با عنوان."""
        text = (
            "\\begin{lstlisting}[language=Java,"
            "caption=Hello World]\n"
            'System.out.println("Hi");\n'
            "\\end{lstlisting}"
        )
        result = processor.process(text, ctx)
        assert "```java" in result
        assert 'title="Hello World"' in result

    def test_lstlisting_with_label(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """lstlisting با label."""
        text = (
            "\\begin{lstlisting}[language=Python,"
            "label=lst:example]\n"
            "x = 1\n"
            "\\end{lstlisting}"
        )
        result = processor.process(text, ctx)
        assert "lst-example" in result
        assert "lst:example" in ctx.labels

    def test_lstlisting_with_numbers(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """lstlisting با شماره خطوط."""
        text = (
            "\\begin{lstlisting}[language=Python,"
            "numbers=left]\n"
            "a = 1\n"
            "b = 2\n"
            "\\end{lstlisting}"
        )
        result = processor.process(text, ctx)
        assert "showLineNumbers" in result

    def test_lstlisting_counter(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """شمارنده بلوک‌ها."""
        text = (
            "\\begin{lstlisting}\nx=1\n\\end{lstlisting}\n"
            "\\begin{lstlisting}\ny=2\n\\end{lstlisting}"
        )
        processor.process(text, ctx)
        assert ctx.code_blocks_processed == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: LaTeX minted
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMinted:
    """تست تبدیل minted."""

    def test_basic_minted(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """minted ساده."""
        text = (
            "\\begin{minted}{python}\n"
            "print('hello')\n"
            "\\end{minted}"
        )
        result = processor.process(text, ctx)
        assert "```python" in result
        assert "print('hello')" in result
        assert "\\begin{minted}" not in result

    def test_minted_cpp(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """minted با زبان C++."""
        text = (
            "\\begin{minted}{cpp}\n"
            "#include <iostream>\n"
            "int main() { return 0; }\n"
            "\\end{minted}"
        )
        result = processor.process(text, ctx)
        assert "```cpp" in result

    def test_minted_with_linenos(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """minted با شماره خطوط."""
        text = (
            "\\begin{minted}[linenos]{python}\n"
            "x = 1\n"
            "\\end{minted}"
        )
        result = processor.process(text, ctx)
        assert "showLineNumbers" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: LaTeX verbatim
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestVerbatim:
    """تست تبدیل verbatim."""

    def test_basic_verbatim(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """verbatim ساده."""
        text = (
            "\\begin{verbatim}\n"
            "some plain text\n"
            "\\end{verbatim}"
        )
        result = processor.process(text, ctx)
        assert "```text" in result
        assert "some plain text" in result
        assert "\\begin{verbatim}" not in result

    def test_verbatim_preserves_whitespace(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """verbatim فاصله‌ها را حفظ کند."""
        text = (
            "\\begin{verbatim}\n"
            "  line1\n"
            "    line2\n"
            "\\end{verbatim}"
        )
        result = processor.process(text, ctx)
        assert "  line1" in result
        assert "    line2" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: HTML <pre><code>
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHTMLPreCode:
    """تست تبدیل HTML pre/code."""

    def test_basic_html(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """HTML ساده."""
        text = (
            '<pre><code class="language-python">'
            "x = 1"
            "</code></pre>"
        )
        result = processor.process(text, ctx)
        assert "```python" in result
        assert "x = 1" in result
        assert "<pre>" not in result

    def test_html_no_language(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """HTML بدون زبان مشخص."""
        text = (
            "<pre><code>"
            "def foo(): pass"
            "</code></pre>"
        )
        result = processor.process(text, ctx)
        assert "```" in result
        assert "def foo(): pass" in result

    def test_html_entities_decoded(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """HTML entities بازگشایی شوند."""
        text = (
            '<pre><code class="language-html">'
            "&lt;div&gt;test&lt;/div&gt;"
            "</code></pre>"
        )
        result = processor.process(text, ctx)
        assert "<div>test</div>" in result

    def test_html_class_without_prefix(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """کلاس بدون پیشوند language-."""
        text = (
            '<pre><code class="javascript">'
            "const x = 1;"
            "</code></pre>"
        )
        result = processor.process(text, ctx)
        assert "```javascript" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Inline code
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestInlineCode:
    """تست تبدیل inline code."""

    def test_texttt(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\texttt{} → `...`."""
        text = r"تابع \texttt{print} را صدا بزنید."
        result = processor.process(text, ctx)
        assert "`print`" in result
        assert "\\texttt" not in result

    def test_verb(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\verb|...| → `...`."""
        text = r"دستور \verb|ls -la| را اجرا کنید."
        result = processor.process(text, ctx)
        assert "`ls -la`" in result
        assert "\\verb" not in result

    def test_verb_other_delimiter(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        r"""\verb+...+ با جداکننده دیگر."""
        text = r"مقدار \verb+x=1+ را ببینید."
        result = processor.process(text, ctx)
        assert "`x=1`" in result

    def test_multiple_texttt(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """چند texttt در یک خط."""
        text = (
            r"توابع \texttt{foo} و \texttt{bar} را ببینید."
        )
        result = processor.process(text, ctx)
        assert "`foo`" in result
        assert "`bar`" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Language Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLanguageDetection:
    """تست تشخیص زبان."""

    def test_python_detection(self) -> None:
        """تشخیص Python."""
        code = "def foo():\n    return 42"
        assert detect_language(code) == "python"

    def test_javascript_detection(self) -> None:
        """تشخیص JavaScript."""
        code = "const x = () => { return 1; };"
        assert detect_language(code) == "javascript"

    def test_html_detection(self) -> None:
        """تشخیص HTML."""
        code = "<div>hello</div>"
        assert detect_language(code) == "html"

    def test_cpp_detection(self) -> None:
        """تشخیص C++."""
        code = "#include <iostream>\nint main() {}"
        assert detect_language(code) == "cpp"

    def test_bash_detection(self) -> None:
        """تشخیص Bash."""
        code = "#!/bin/bash\necho hello"
        assert detect_language(code) == "bash"

    def test_sql_detection(self) -> None:
        """تشخیص SQL."""
        code = "SELECT * FROM users WHERE id = 1"
        assert detect_language(code) == "sql"

    def test_unknown_returns_text(self) -> None:
        """ناشناخته → text."""
        assert detect_language("random stuff") == "text"

    def test_empty_returns_text(self) -> None:
        """خالی → text."""
        assert detect_language("") == "text"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Language Normalization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLanguageNormalization:
    """تست نرمال‌سازی نام زبان."""

    def test_py_to_python(self) -> None:
        assert _normalize_language("py") == "python"

    def test_js_to_javascript(self) -> None:
        assert _normalize_language("js") == "javascript"

    def test_sh_to_bash(self) -> None:
        assert _normalize_language("sh") == "bash"

    def test_yml_to_yaml(self) -> None:
        assert _normalize_language("yml") == "yaml"

    def test_empty_to_text(self) -> None:
        assert _normalize_language("") == "text"

    def test_case_insensitive(self) -> None:
        assert _normalize_language("Python") == "python"

    def test_unknown_passthrough(self) -> None:
        assert _normalize_language("fortran") == "fortran"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: ZWNJ Preservation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestZWNJPreservation:
    """تست حفظ نیم‌فاصله."""

    def test_zwnj_outside_code(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """نیم‌فاصله خارج کد حفظ شود."""
        text = (
            "کلاس" + ZWNJ + "های مختلف:\n"
            "\\begin{lstlisting}[language=Python]\n"
            "x = 1\n"
            "\\end{lstlisting}\n"
            "تابع" + ZWNJ + "ها"
        )
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, ctx)
        assert result.count(ZWNJ) == zwnj_before

    def test_zwnj_heavy_document(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """سند با نیم‌فاصله‌های زیاد."""
        text = (
            "برنامه" + ZWNJ + "نویسی "
            "شیء" + ZWNJ + "گرا با "
            "\\texttt{class} "
            "در زبان" + ZWNJ + "های مختلف."
        )
        zwnj_before = text.count(ZWNJ)
        result = processor.process(text, ctx)
        assert result.count(ZWNJ) == zwnj_before


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: extract_code_blocks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtractCodeBlocks:
    """تست تابع extract_code_blocks."""

    def test_latex_mixed(self) -> None:
        """استخراج انواع مختلف LaTeX."""
        text = (
            "\\begin{lstlisting}[language=Python]\n"
            "x=1\n\\end{lstlisting}\n"
            "\\begin{minted}{java}\ny=2\n\\end{minted}\n"
            "\\begin{verbatim}\nplain\n\\end{verbatim}"
        )
        blocks = extract_code_blocks(text, "latex")
        assert len(blocks) == 3
        types = {b.block_type for b in blocks}
        assert CodeBlockType.LATEX_LISTING in types
        assert CodeBlockType.LATEX_MINTED in types
        assert CodeBlockType.LATEX_VERBATIM in types

    def test_html_extraction(self) -> None:
        """استخراج HTML."""
        text = (
            '<pre><code class="language-python">'
            "x=1</code></pre>"
        )
        blocks = extract_code_blocks(text, "html")
        assert len(blocks) == 1
        assert blocks[0].language == "python"

    def test_inline_extraction(self) -> None:
        """استخراج inline."""
        text = r"Use \texttt{foo} and \verb|bar|."
        blocks = extract_code_blocks(text, "latex")
        inlines = [
            b for b in blocks
            if b.block_type in (
                CodeBlockType.INLINE_TEXTTT,
                CodeBlockType.INLINE_VERB,
            )
        ]
        assert len(inlines) == 2

    def test_empty_text(self) -> None:
        """متن خالی."""
        assert extract_code_blocks("", "latex") == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: _build_fence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBuildFence:
    """تست تابع _build_fence."""

    def test_simple_fence(self) -> None:
        """فنس ساده."""
        result = _build_fence("x = 1", "python")
        assert "```python" in result
        assert "x = 1" in result
        assert result.endswith("```")

    def test_fence_with_title(self) -> None:
        """فنس با عنوان."""
        result = _build_fence("x = 1", "python", title="Test")
        assert 'title="Test"' in result

    def test_fence_with_line_numbers(self) -> None:
        """فنس با شماره خط."""
        result = _build_fence(
            "x = 1", "python", line_numbers=True,
        )
        assert "showLineNumbers" in result

    def test_fence_with_label(self) -> None:
        """فنس با label."""
        result = _build_fence(
            "x = 1", "python", label="lst:test",
        )
        assert "lst-test" in result

    def test_fence_all_options(self) -> None:
        """فنس با تمام گزینه‌ها."""
        result = _build_fence(
            "code", "js",
            title="Demo",
            line_numbers=True,
            label="lst:demo",
        )
        assert "```javascript" in result
        assert 'title="Demo"' in result
        assert "showLineNumbers" in result
        assert "lst-demo" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: can_process
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCanProcess:
    """تست متد can_process."""

    def test_with_lstlisting(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """با lstlisting → True."""
        text = "\\begin{lstlisting}\nx\n\\end{lstlisting}"
        assert processor.can_process(text, ctx) is True

    def test_with_texttt(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """با texttt → True."""
        assert processor.can_process(
            r"\texttt{x}", ctx,
        ) is True

    def test_with_html_pre(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """با HTML pre → True."""
        assert processor.can_process(
            "<pre><code>x</code></pre>", ctx,
        ) is True

    def test_without_code(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """بدون کد → False."""
        assert processor.can_process(
            "متن ساده فارسی", ctx,
        ) is False

    def test_disabled(
        self, ctx: ProcessorContext,
    ) -> None:
        """غیرفعال → False."""
        p = CodeProcessor()
        p.enabled = False
        assert p.can_process("\\texttt{x}", ctx) is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test: Edge Cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEdgeCases:
    """تست موارد مرزی."""

    def test_empty_content(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """محتوای خالی بدون خطا."""
        result = processor.process("", ctx)
        assert result == ""

    def test_multiple_blocks_mixed(
        self, processor: CodeProcessor, ctx: ProcessorContext,
    ) -> None:
        """ترکیب بلوک و inline."""
        text = (
            "تابع \\texttt{foo} را ببینید:\n"
            "\\begin{lstlisting}[language=Python]\n"
            "def foo(): pass\n"
            "\\end{lstlisting}\n"
            "و دستور \\verb|bar| را اجرا کنید."
        )
        result = processor.process(text, ctx)
        assert "`foo`" in result
        assert "`bar`" in result
        assert "```python" in result
        assert ctx.code_blocks_processed == 1