import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup, Tag, NavigableString

html = """<!DOCTYPE html>
<html lang="fa">
<head><title>Test</title></head>
<body>
<h1>Heading One</h1>
<p>A paragraph here.</p>
<ul><li>Item 1</li><li>Item 2</li></ul>
</body>
</html>"""

soup = BeautifulSoup(html, "lxml")
body = soup.find("body")
print("Body type:", type(body))
print("Body name:", body.name if body else None)
print("Body children types:")
for child in body.children:
    print("  ", type(child).__name__, repr(str(child)[:50]))

print()
print("Test convert_element on body:")
from formatforge.core.converters.html_to_mdx import HTMLToMDXConverter
from formatforge.core.converters.base import ConversionContext
from pathlib import Path

conv = HTMLToMDXConverter()
ctx = ConversionContext()
result = conv._convert_element(body, ctx, Path("test.html"))
print("Result:", repr(result[:500]))
