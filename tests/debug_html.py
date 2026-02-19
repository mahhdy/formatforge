import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from formatforge.core.converters.html_to_mdx import HTMLToMDXConverter
from formatforge.core.converters.base import ConversionContext
import tempfile, os

html = """<!DOCTYPE html>
<html lang="fa">
<head><title>Test</title></head>
<body>
<h1>Heading One</h1>
<p>A paragraph here.</p>
<ul><li>Item 1</li><li>Item 2</li></ul>
</body>
</html>"""

with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f:
    f.write(html)
    fname = f.name

conv = HTMLToMDXConverter()
ctx = ConversionContext()
result = conv.convert(Path(fname), ctx)
print("STATUS:", result.status)
if result.error_message:
    print("ERROR:", result.error_message)
mdx = ctx.extra.get("mdx_content", "")
print("MDX length:", len(mdx))
print("---MDX---")
print(mdx[:1000])
os.unlink(fname)
