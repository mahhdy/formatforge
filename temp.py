path = 'formatforge/core/persian/typography.py'
code = open(path, 'r', encoding='utf-8').read()

old = '''def _protect_blocks(
    text: str,
) -> tuple[str, dict[str, str]]:
    \x22\x22\x22
    \u062d\u0641\u0627\u0638\u062a \u0628\u0644\u0648\u06a9\u200c\u0647\u0627\u06cc \u06a9\u062f/\u0631\u06cc\u0627\u0636\u06cc/URL \u0628\u0627 placeholder.
    Protect code/math/URL blocks from modification.
    \x22\x22\x22
    placeholders: dict[str, str] = {}
    result = text
    counter = 0

    import uuid as _uuid
    for pattern in _PROTECTED_PATTERNS:
        def _replacer(m: re.Match) -> str:
            token = f\x22\ufffcTYPO_{_uuid.uuid4().hex[:8]}\ufffc\x22
            placeholders[token] = m.group(0)
            return token

        result = pattern.sub(_replacer, result)

    return result, placeholders'''

new = '''def _protect_blocks(
    text: str,
) -> tuple[str, dict[str, str]]:
    \x22\x22\x22
    \u062d\u0641\u0627\u0638\u062a \u0628\u0644\u0648\u06a9\u200c\u0647\u0627\u06cc \u06a9\u062f/\u0631\u06cc\u0627\u0636\u06cc/URL \u0628\u0627 placeholder.
    Protect code/math/URL blocks from modification.
    Tokens use only ASCII uppercase letters to survive numeral conversion.
    \x22\x22\x22
    placeholders: dict[str, str] = {}
    result = text
    _counter = [0]

    def _make_token() -> str:
        n = _counter[0]
        _counter[0] += 1
        letters = \x22ABCDEFGHIJKLMNOPQRSTUVWXYZ\x22
        tag = \x22\x22
        val = n
        for _ in range(6):
            tag = letters[val % 26] + tag
            val //= 26
        return \x22\ufffc_PB_\x22 + tag + \x22_\ufffc\x22

    for pattern in _PROTECTED_PATTERNS:
        def _replacer(m: re.Match) -> str:
            token = _make_token()
            placeholders[token] = m.group(0)
            return token
        result = pattern.sub(_replacer, result)

    return result, placeholders'''

if old in code:
    code = code.replace(old, new)
    open(path, 'w', encoding='utf-8').write(code)
    print('SUCCESS: replaced _protect_blocks')
else:
    print('ERROR: old code not found exactly')
    # Show what we have for debugging
    start = code.find('def _protect_blocks')
    print(repr(code[start:start+600]))