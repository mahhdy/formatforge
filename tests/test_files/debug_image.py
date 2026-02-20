"""Debug why <Image> tags aren't being replaced."""
import re
import sys
import html as html_mod

sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('tests/test_files/output/sample-mermaid.mdx', 'r', encoding='utf-8') as f:
    mdx_content = f.read()

body = mdx_content
idx = body.find('---', 3)
body = body[idx + 3:].strip()

# Remove duplicate RTL
body = re.sub(r'^---\s*\ndir:\s*"rtl"\s*\nlang:\s*"fa"\s*\n---\s*\n?', '', body)

# Remove imports
lines = body.split('\n')
body = '\n'.join(l for l in lines if not l.strip().startswith('import '))

# Remove MDX comments
body = re.sub(r'\{/\*.*?\*/\}', '', body, flags=re.DOTALL)

# Remove div wrappers
body = re.sub(r'<div\s+dir=["\']ltr["\'][^>]*>\s*\n?', '', body)
body = re.sub(r'\n?</div>\s*(?=\n|$)', '', body)

print(f"Image tags in body: {len(re.findall(r'<Image', body))}")

# Simulate protect
protected = []
def protect(html_out):
    i = len(protected)
    ph = f'\n\nPROTECTED_BLOCK_{i}_ENDBLOCK\n\n'
    protected.append(html_out)
    return ph

# Protect mermaid
def pm(m):
    code = m.group(1)
    code = re.sub(r'<div[^>]*>', '', code)
    code = re.sub(r'</div>', '', code)
    return protect(f'<pre class="mermaid">\n{code.strip()}\n</pre>')
body = re.sub(r"```mermaid\s*\n(.*?)```[^\n]*", pm, body, flags=re.DOTALL)

# Protect code blocks
def pc(m):
    lang = m.group(1) or ""
    code = m.group(2)
    esc = html_mod.escape(code.rstrip())
    return protect(f'<pre><code class="language-{lang}">{esc}</code></pre>')
body = re.sub(r"```(\w*)\s*\n(.*?)```", pc, body, flags=re.DOTALL)

print(f"Image tags after code block protection: {len(re.findall(r'<Image', body))}")

# Now check for the actual Image tags
for i, line in enumerate(body.split('\n')):
    if '<Image' in line:
        print(f"  Line {i}: {line[:100]}")

# Try the Image regex
matches = re.findall(r'<Image\s.*?/>', body)
print(f"\nImage regex matches: {len(matches)}")
for m in matches:
    print(f"  {m[:100]}")
