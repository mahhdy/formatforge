"""
Convert all test files and generate HTML output for review.
تبدیل تمام فایل‌های تست و تولید خروجی HTML برای بررسی
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from formatforge.core.converters.base import ConversionContext
from formatforge.core.converters.html_to_mdx import HTMLToMDXConverter
from formatforge.core.converters.md_to_mdx import MarkdownToMDXConverter
from formatforge.core.converters.latex_to_mdx import LaTeXToMDXConverter

TEST_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = TEST_DIR / "output"

# Map extensions to converter classes
CONVERTERS = {
    ".tex": ("LaTeX", LaTeXToMDXConverter),
    ".html": ("HTML", HTMLToMDXConverter),
    ".htm": ("HTML", HTMLToMDXConverter),
    ".md": ("Markdown", MarkdownToMDXConverter),
    ".markdown": ("Markdown", MarkdownToMDXConverter),
}

# Files to skip (no converter available)
SKIP_EXTENSIONS = {".docx", ".adoc", ".rst", ".epub"}


def mdx_to_html(mdx_content: str, title: str) -> str:
    """Convert MDX content to a viewable HTML page with Mermaid + KaTeX."""
    import re
    import html as html_mod
    import markdown

    # ── Extract frontmatter ──────────────────
    frontmatter = ""
    body = mdx_content
    if mdx_content.startswith("---"):
        idx = mdx_content.find("---", 3)
        if idx > 0:
            frontmatter = mdx_content[3:idx].strip()
            body = mdx_content[idx + 3:].strip()

    # ── Remove duplicate RTL frontmatter block ──
    body = re.sub(r"^---\s*\ndir:\s*\"rtl\"\s*\nlang:\s*\"fa\"\s*\n---\s*\n?", "", body)

    # ── Remove import lines ──────────────────
    lines = body.split("\n")
    imports = []
    content_lines = []
    for line in lines:
        if line.strip().startswith("import "):
            imports.append(line.strip())
        else:
            content_lines.append(line)
    body = "\n".join(content_lines)

    # ── Remove MDX comment blocks {/* ... */} ──
    body = re.sub(r"\{/\*.*?\*/\}", "", body, flags=re.DOTALL)

    # ── Remove <div dir="ltr"> wrappers ──
    body = re.sub(r'<div\s+dir=["\']ltr["\'][^>]*>\s*\n?', '', body)
    body = re.sub(r'\n?</div>\s*(?=\n|$)', '', body)

    # ── Convert JSX-style style attributes to valid HTML ──
    # style={{key: 'val'}} → style="key: val"
    def fix_jsx_style(m):
        jsx = m.group(1)
        # Simple conversion: camelCase to kebab-case, remove quotes
        css_parts = []
        for pair in re.findall(r"(\w+)\s*:\s*'([^']*)'", jsx):
            prop = re.sub(r'([A-Z])', lambda x: '-' + x.group(1).lower(), pair[0])
            css_parts.append(f"{prop}: {pair[1]}")
        return f'style="{"; ".join(css_parts)}"'
    body = re.sub(r'style=\{\{(.*?)\}\}', fix_jsx_style, body)

    # ── Protected blocks storage ──
    protected = []  # list of (placeholder_text, html_output)

    def protect(html_out: str) -> str:
        """Replace content with a placeholder and store the HTML."""
        idx = len(protected)
        ph = f"\n\nPROTECTED_BLOCK_{idx}_ENDBLOCK\n\n"
        protected.append(html_out)
        return ph

    # ── Protect fenced code blocks (``` ... ```) ──
    def protect_code_block(m):
        lang = m.group(1) or ""
        code = m.group(2)
        escaped = html_mod.escape(code.rstrip())
        if lang:
            return protect(f'<pre><code class="language-{lang}">{escaped}</code></pre>')
        return protect(f'<pre><code>{escaped}</code></pre>')

    # Mermaid blocks → <pre class="mermaid"> (rendered by Mermaid.js)
    def protect_mermaid_block(m):
        code = m.group(1)
        # Clean stray HTML tags
        code = re.sub(r'<div[^>]*>', '', code)
        code = re.sub(r'</div>', '', code)
        return protect(f'<pre class="mermaid">\n{code.strip()}\n</pre>')

    # Process mermaid blocks first (before generic code blocks)
    body = re.sub(r"```mermaid\s*\n(.*?)```[^\n]*", protect_mermaid_block, body, flags=re.DOTALL)
    # Then all other code blocks
    body = re.sub(r"```(\w*)\s*\n(.*?)```", protect_code_block, body, flags=re.DOTALL)

    # ── Protect MermaidDiagram JSX blocks ──
    def protect_mermaid_jsx(m):
        chart = m.group(1).replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
        return protect(f'<pre class="mermaid">\n{chart.strip()}\n</pre>')
    body = re.sub(
        r"<MermaidDiagram[^>]*>\s*\{`(.*?)`\}\s*</MermaidDiagram>",
        protect_mermaid_jsx, body, flags=re.DOTALL,
    )
    body = re.sub(
        r'<MermaidDiagram[^>]*chart=\{`(.*?)`\}[^>]*/?>',
        protect_mermaid_jsx, body, flags=re.DOTALL,
    )

    # ── Protect math blocks ──
    def protect_math_block(m):
        code = m.group(1).strip()
        return protect(f'<div class="math-block" dir="ltr">$${code}$$</div>')
    body = re.sub(r"\$\$(.*?)\$\$", protect_math_block, body, flags=re.DOTALL)

    # Protect inline math
    def protect_math_inline(m):
        code = m.group(1)
        return f'MATHINLINE_{len(protected)}_X'  # inline, no newlines
    math_inlines = []
    def save_math_inline(m):
        code = m.group(1)
        idx = len(math_inlines)
        math_inlines.append(code)
        return f"MATHINLINE_{idx}_X"
    body = re.sub(r"(?<!\$)\$([^$\n]+?)\$(?!\$)", save_math_inline, body)

    # ── Convert ALL JSX/MDX components to HTML BEFORE markdown ──

    # <Image ... /> → <img> (handle broken nested quotes in src)
    def convert_image_jsx(m):
        full = m.group(0)
        # Extract last alt="..." (most reliable)
        alt_m = re.search(r'alt="([^"]*)"', full)
        alt = alt_m.group(1) if alt_m else ""
        # Extract src - take first URL-like value after src=
        src_m = re.search(r'src="(https?://[^"\s]+)', full)
        src = src_m.group(1) if src_m else ""
        return protect(f'<figure><img src="{html_mod.escape(src)}" alt="{html_mod.escape(alt)}" style="max-width:100%"/><figcaption>{html_mod.escape(alt)}</figcaption></figure>')
    body = re.sub(r'<Image\s.*?/>', convert_image_jsx, body)

    # <Admonition type="...">...</Admonition>
    def convert_admonition(m):
        atype = m.group(1)
        content = m.group(2).strip()
        # Convert inner markdown
        inner = markdown.markdown(content, extensions=["tables", "fenced_code"])
        return protect(f'<div class="admonition admonition-{atype}"><div class="admonition-title">{atype}</div>{inner}</div>')
    body = re.sub(
        r'<Admonition\s+type=["\'](\w+)["\'][^>]*>(.*?)</Admonition>',
        convert_admonition, body, flags=re.DOTALL,
    )

    # <Theorem>, <Definition>, <Proof>, etc.
    for comp, cls in [("Theorem", "theorem"), ("Definition", "definition"),
                       ("Proof", "proof"), ("Lemma", "lemma"),
                       ("Corollary", "corollary"), ("Example", "example")]:
        def convert_math_env(m, cls=cls, comp=comp):
            attrs = m.group(1)
            content = m.group(2).strip()
            title_m = re.search(r'title=["\']([^"\']+)["\']', attrs)
            t = title_m.group(1) if title_m else comp
            inner = markdown.markdown(content, extensions=["tables", "fenced_code"])
            return protect(f'<div class="math-env {cls}"><div class="math-env-title">{html_mod.escape(t)}</div>{inner}</div>')
        body = re.sub(rf"<{comp}([^>]*)>(.*?)</{comp}>", convert_math_env, body, flags=re.DOTALL)

    # <Citation id="..." />
    body = re.sub(r'<Citation[^>]*id=["\']([^"\']+)["\'][^>]*/?>',
                  r'<span class="citation">[\1]</span>', body)
    # <CrossRef target="..." />
    body = re.sub(r'<CrossRef[^>]*target=["\']([^"\']+)["\'][^>]*/?>',
                  r'<a class="crossref" href="#">\1</a>', body)
    # <Figure src="..." caption="..." />
    body = re.sub(
        r'<Figure[^>]*src=["\']([^"\']+)["\'][^>]*caption=["\']([^"\']+)["\'][^>]*/?>',
        r'<figure><img src="\1" alt="\2"/><figcaption>\2</figcaption></figure>',
        body,
    )
    # <Details summary="...">...</Details>
    body = re.sub(
        r'<Details[^>]*summary=["\']([^"\']+)["\'][^>]*>(.*?)</Details>',
        r'<details><summary>\1</summary>\2</details>',
        body, flags=re.DOTALL,
    )

    # Remove any remaining unknown JSX self-closing tags
    body = re.sub(r'<([A-Z]\w+)\s+[^>]*/>', lambda m: protect(
        f'<div class="jsx-component">[{m.group(1)} component]</div>'
    ), body)
    # Remove remaining unknown JSX open/close tags but keep content
    body = re.sub(r'<([A-Z]\w+)[^>]*>(.*?)</\1>', lambda m: m.group(2), body, flags=re.DOTALL)

    # ── Protect raw HTML blocks that markdown might mangle ──
    def protect_html_block(m):
        return protect(m.group(0))
    # Protect <div ...>...</div> blocks (non-greedy, single blocks)
    body = re.sub(r'<div\b[^>]*>.*?</div>', protect_html_block, body, flags=re.DOTALL)
    # Protect <table>...</table>
    body = re.sub(r'<table\b[^>]*>.*?</table>', protect_html_block, body, flags=re.DOTALL)

    # ── Convert Markdown to HTML ──
    md = markdown.Markdown(extensions=[
        "tables",
        "fenced_code",
        "footnotes",
        "attr_list",
        "def_list",
        "toc",
    ])
    body_html = md.convert(body)

    # ── Restore all protected blocks ──
    for i, html_block in enumerate(protected):
        placeholder = f"PROTECTED_BLOCK_{i}_ENDBLOCK"
        body_html = body_html.replace(placeholder, html_block)
        body_html = body_html.replace(f"<p>{placeholder}</p>", html_block)

    # ── Restore inline math ──
    for i, code in enumerate(math_inlines):
        body_html = body_html.replace(f"MATHINLINE_{i}_X",
            f'<span class="math-inline" dir="ltr">${code}$</span>')

    # ── Build full HTML page ─────────────────
    fm_escaped = html_mod.escape(frontmatter)

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html_mod.escape(title)}</title>

    <!-- Vazirmatn font for Persian -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" />

    <!-- KaTeX for math rendering -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" />
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body, {{
            delimiters: [
                {{left: '$$', right: '$$', display: true}},
                {{left: '$', right: '$', display: false}}
            ],
            throwOnError: false
        }});"></script>

    <!-- Mermaid for diagrams -->
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            flowchart: {{ htmlLabels: true, useMaxWidth: true }},
            securityLevel: 'loose',
        }});
    </script>

    <!-- Highlight.js for code -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.10.0/build/styles/github.min.css" />
    <script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.10.0/build/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>

    <style>
        :root {{
            --bg: #ffffff;
            --text: #1a1a1a;
            --code-bg: #f6f8fa;
            --border: #d0d7de;
            --accent: #0969da;
            --accent-light: #ddf4ff;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Vazirmatn', 'Segoe UI', Tahoma, sans-serif;
            line-height: 1.9;
            color: var(--text);
            background: var(--bg);
            max-width: 960px;
            margin: 0 auto;
            padding: 2rem 2.5rem;
            direction: rtl;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin: 1.8em 0 0.6em;
            line-height: 1.35;
            font-weight: 700;
        }}
        h1 {{ font-size: 2rem; border-bottom: 2px solid var(--accent); padding-bottom: 0.4em; }}
        h2 {{ font-size: 1.65rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }}
        h3 {{ font-size: 1.35rem; }}
        h4 {{ font-size: 1.15rem; }}
        p {{ margin: 0.8em 0; }}

        /* Code */
        pre {{
            background: var(--code-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem 1.2rem;
            overflow-x: auto;
            direction: ltr;
            text-align: left;
            margin: 1.2em 0;
            font-size: 0.88em;
        }}
        code {{
            font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
            font-size: 0.9em;
        }}
        :not(pre) > code {{
            background: var(--code-bg);
            padding: 0.15em 0.4em;
            border-radius: 4px;
            border: 1px solid var(--border);
        }}

        /* Mermaid diagrams */
        pre.mermaid {{
            background: #fff;
            border: 2px solid #e1e4e8;
            border-radius: 10px;
            padding: 1.5rem;
            text-align: center;
            direction: ltr;
        }}

        /* Math */
        .math-block {{
            direction: ltr;
            text-align: center;
            margin: 1.5em 0;
            padding: 1em;
            background: #fafbfc;
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow-x: auto;
        }}
        .math-inline {{
            direction: ltr;
            unicode-bidi: isolate;
        }}

        /* Blockquote */
        blockquote {{
            border-right: 4px solid var(--accent);
            padding: 0.6em 1.2em;
            margin: 1.2em 0;
            background: var(--accent-light);
            border-radius: 0 6px 6px 0;
            color: #24292f;
        }}
        blockquote p {{ margin: 0.4em 0; }}

        /* Tables */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1.2em 0;
            font-size: 0.95em;
        }}
        th, td {{
            border: 1px solid var(--border);
            padding: 0.6em 1em;
            text-align: right;
        }}
        th {{ background: var(--code-bg); font-weight: 600; }}
        tr:nth-child(even) {{ background: #f6f8fa; }}

        /* Images & figures */
        img {{ max-width: 100%; height: auto; border-radius: 6px; }}
        figure {{ margin: 1.5em 0; text-align: center; }}
        figcaption {{ color: #57606a; font-size: 0.9em; margin-top: 0.5em; }}

        /* Links */
        a {{ color: var(--accent); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}

        /* Lists */
        ul, ol {{ margin: 0.8em 0; padding-right: 2em; }}
        li {{ margin: 0.3em 0; }}
        li > ul, li > ol {{ margin: 0.2em 0; }}

        hr {{ border: none; border-top: 1px solid var(--border); margin: 2.5em 0; }}

        /* Admonitions */
        .admonition {{
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1em 1.2em;
            margin: 1.2em 0;
        }}
        .admonition-title {{
            font-weight: 700;
            margin-bottom: 0.5em;
            text-transform: capitalize;
        }}
        .admonition-note {{ border-right: 4px solid #0969da; background: #ddf4ff; }}
        .admonition-warning {{ border-right: 4px solid #d4a72c; background: #fff8c5; }}
        .admonition-tip {{ border-right: 4px solid #1a7f37; background: #dafbe1; }}
        .admonition-caution {{ border-right: 4px solid #cf222e; background: #ffebe9; }}
        .admonition-important {{ border-right: 4px solid #8250df; background: #fbefff; }}

        /* Math environments (theorem, definition, proof, ...) */
        .math-env {{
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1em 1.2em;
            margin: 1.2em 0;
        }}
        .math-env-title {{
            font-weight: 700;
            margin-bottom: 0.4em;
        }}
        .theorem {{ border-right: 4px solid #8250df; background: #fbefff; }}
        .definition {{ border-right: 4px solid #0969da; background: #ddf4ff; }}
        .proof {{ border-right: 4px solid #57606a; background: #f6f8fa; }}
        .lemma {{ border-right: 4px solid #bf8700; background: #fff8c5; }}
        .example {{ border-right: 4px solid #1a7f37; background: #dafbe1; }}

        /* Citation & CrossRef */
        .citation {{ color: var(--accent); font-weight: 600; }}
        .crossref {{ color: #8250df; }}

        /* Details/Summary */
        details {{
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.8em 1.2em;
            margin: 1em 0;
        }}
        summary {{
            cursor: pointer;
            font-weight: 600;
            color: var(--accent);
        }}

        /* Footnotes */
        .footnote {{ font-size: 0.85em; }}
        .footnote-ref {{ vertical-align: super; font-size: 0.75em; }}

        /* Frontmatter panel */
        .frontmatter-panel {{
            background: var(--code-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1em 1.2em;
            margin-bottom: 2em;
            font-size: 0.82em;
            direction: ltr;
            text-align: left;
        }}
        .frontmatter-panel summary {{ color: #57606a; font-size: 0.95em; }}
        .frontmatter-panel pre {{ border: none; background: transparent; padding: 0.5em 0; margin: 0; }}

        .imports-panel {{
            background: #fff8c5;
            border: 1px solid #d4a72c;
            border-radius: 8px;
            padding: 0.6em 1em;
            margin-bottom: 1.5em;
            font-size: 0.82em;
            direction: ltr;
        }}
        .imports-panel code {{ font-size: 0.85em; }}
    </style>
</head>
<body>
    <details class="frontmatter-panel">
        <summary>Frontmatter (YAML metadata)</summary>
        <pre>{fm_escaped}</pre>
    </details>
"""

    if imports:
        html += '    <details class="imports-panel" open>\n'
        html += "        <summary>MDX Imports</summary>\n"
        for imp in imports:
            html += f"        <code>{html_mod.escape(imp)}</code><br/>\n"
        html += "    </details>\n"

    html += f"""
    <article class="content">
{body_html}
    </article>
</body>
</html>"""
    return html


def convert_file(file_path: Path, output_dir: Path) -> dict:
    """Convert a single file and return result info."""
    suffix = file_path.suffix.lower()
    result = {
        "file": file_path.name,
        "format": suffix,
        "status": "unknown",
        "mdx_file": None,
        "html_file": None,
        "warnings": [],
        "errors": [],
        "mdx_lines": 0,
    }

    if suffix in SKIP_EXTENSIONS:
        result["status"] = "skipped"
        result["errors"].append(f"No converter for {suffix}")
        return result

    if suffix not in CONVERTERS:
        result["status"] = "unsupported"
        result["errors"].append(f"Unknown extension: {suffix}")
        return result

    fmt_name, converter_class = CONVERTERS[suffix]
    result["format"] = fmt_name

    try:
        converter = converter_class()
        context = ConversionContext()

        # Detect
        detected = converter.detect(file_path)
        if not detected:
            result["warnings"].append(f"detect() returned False for {file_path.name}")

        # Extract metadata
        metadata = converter.extract_metadata(file_path, context)
        context.metadata = metadata

        # Convert
        conversion_result = converter.convert(file_path, context)

        if conversion_result.status == "success":
            # Content is stored in context.extra["mdx_content"]
            mdx_content = context.extra.get("mdx_content", "")
            result["status"] = "success"
            result["mdx_lines"] = len(mdx_content.splitlines())
            result["warnings"] = context.warnings[:5]  # limit

            # Save MDX
            mdx_file = output_dir / f"{file_path.stem}.mdx"
            mdx_file.write_text(mdx_content, encoding="utf-8")
            result["mdx_file"] = mdx_file.name

            # Save HTML
            html_content = mdx_to_html(mdx_content, metadata.title or file_path.stem)
            html_file = output_dir / f"{file_path.stem}.html"
            html_file.write_text(html_content, encoding="utf-8")
            result["html_file"] = html_file.name

        else:
            result["status"] = "failed"
            result["errors"].append(conversion_result.error_message or "Conversion failed")

    except Exception as e:
        result["status"] = "error"
        result["errors"].append(f"{type(e).__name__}: {e}")
        traceback.print_exc()

    return result


def main():
    """Convert all test files and generate report."""
    import io, os
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("=" * 60)
    print("FormatForge - Test File Conversion")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Find all test files (exclude .py scripts and the output dir)
    test_files = sorted(
        f for f in TEST_DIR.iterdir()
        if f.is_file() and f.suffix.lower() != ".py"
    )

    results = []
    for f in test_files:
        print(f"\n{'─' * 40}")
        print(f"Converting: {f.name}")
        r = convert_file(f, OUTPUT_DIR)
        results.append(r)

        status_icon = {"success": "OK", "skipped": "SKIP", "error": "ERR", "failed": "FAIL", "unsupported": "N/A"}
        icon = status_icon.get(r["status"], "?")
        print(f"  [{icon}] {r['format']} → {r['status']}")
        if r["mdx_lines"]:
            print(f"  MDX: {r['mdx_lines']} lines → {r['mdx_file']}")
        if r["html_file"]:
            print(f"  HTML: {r['html_file']}")
        for w in r["warnings"][:3]:
            print(f"  WARN: {w}")
        for e in r["errors"][:3]:
            print(f"  ERROR: {e}")

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")

    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] in ("error", "failed"))
    unsupported = sum(1 for r in results if r["status"] == "unsupported")

    print(f"Total files:   {total}")
    print(f"Success:       {success}")
    print(f"Skipped:       {skipped} (no converter)")
    print(f"Errors:        {errors}")
    print(f"Unsupported:   {unsupported}")
    print(f"\nOutput dir: {OUTPUT_DIR}")

    # Generate index HTML
    index_html = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="utf-8" />
    <title>FormatForge - Conversion Results</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: 2rem auto; padding: 1rem; }
        h1 { color: #2563eb; }
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #e0e0e0; padding: 0.6em 1em; text-align: left; }
        th { background: #f4f4f4; }
        .success { color: #10b981; font-weight: bold; }
        .error, .failed { color: #ef4444; font-weight: bold; }
        .skipped { color: #f59e0b; }
        a { color: #2563eb; }
    </style>
</head>
<body>
    <h1>FormatForge - Conversion Results</h1>
    <table>
        <tr><th>File</th><th>Format</th><th>Status</th><th>MDX Lines</th><th>Output</th></tr>
"""
    for r in results:
        cls = r["status"]
        link = ""
        if r["html_file"]:
            link = f'<a href="{r["html_file"]}">HTML</a>'
        if r["mdx_file"]:
            link += f' | <a href="{r["mdx_file"]}">MDX</a>'
        err_info = ""
        if r["errors"]:
            err_info = f"<br/><small>{r['errors'][0][:80]}</small>"
        index_html += f'        <tr><td>{r["file"]}</td><td>{r["format"]}</td><td class="{cls}">{r["status"]}{err_info}</td><td>{r["mdx_lines"]}</td><td>{link}</td></tr>\n'

    index_html += """    </table>
</body>
</html>"""

    index_path = OUTPUT_DIR / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    print(f"\nIndex page: {index_path}")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
