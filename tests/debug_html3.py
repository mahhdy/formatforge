import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
import tempfile, os
from formatforge.core.converters.html_to_mdx import HTMLToMDXConverter
from formatforge.core.converters.base import ConversionContext

html = """<!DOCTYPE html>
<html lang="fa">
<head><title>Test</title></head>
<body>
<h1>Heading One</h1>
<p>A paragraph here.</p>
</body>
</html>"""

with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f:
    f.write(html)
    fname = f.name

# Monkey-patch to trace
from formatforge.core.converters.html_to_mdx import HTMLToMDXConverter
from bs4 import BeautifulSoup

original_convert = HTMLToMDXConverter.convert

def traced_convert(self, file_path, context):
    from formatforge.core.converters.base import ConversionError, ZWNJReport, QualityReport, DocumentConversionResult
    from formatforge.core.converters.jsx_utils import convert_html_to_jsx, generate_imports
    from formatforge.core.processors.base import ProcessorContext
    import time

    start = time.time()
    doc_id = file_path.stem
    self._svg_counter = 0

    result = DocumentConversionResult(
        document_id=doc_id,
        source_path=str(file_path),
        status="processing",
    )

    raw_content = self.read_file(file_path)
    soup = BeautifulSoup(raw_content, "lxml")
    context.metadata = self.extract_metadata(file_path, context)
    body_tag = soup.find("body") or soup

    mdx_body = self._convert_element(body_tag, context, file_path)
    print("AFTER _convert_element:", repr(mdx_body[:200]))

    # standalone
    mdx_body = self._run_standalone_processors(mdx_body, "html")
    print("AFTER standalone processors:", repr(mdx_body[:200]))

    # pipeline
    from formatforge.core.processors.base import ProcessorContext, ProcessorPipeline
    from formatforge.core.processors.math_processor import MathProcessor
    from formatforge.core.processors.code_processor import CodeProcessor
    from formatforge.core.processors.link_processor import LinkProcessor
    from formatforge.core.processors.footnote_processor import FootnoteProcessor
    from formatforge.core.processors.rtl_processor import RTLProcessor

    proc_ctx = ProcessorContext(
        source_format="html",
        source_path=str(file_path),
        language=context.metadata.lang,
        config=self.config,
    )

    pipeline = self._get_pipeline()
    pipe_result = pipeline.run(mdx_body, proc_ctx)
    print("AFTER pipeline:", repr(pipe_result.content[:200]))

    result.status = "success"
    return result

conv = HTMLToMDXConverter()
ctx = ConversionContext()
traced_convert(conv, Path(fname), ctx)
os.unlink(fname)
