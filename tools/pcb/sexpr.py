"""Minimal S-expression reader/writer for KiCad files.

A list is a Python list whose first item is the tag (a Sym). Strings that were
quoted in the file are `str`; bare tokens are `Sym` (a str subclass), so the
writer can put the quotes back exactly where KiCad expects them.
"""


class Sym(str):
    pass


def parse(text):
    pos = 0
    n = len(text)
    stack = [[]]
    while pos < n:
        c = text[pos]
        if c in ' \t\r\n':
            pos += 1
        elif c == '(':
            stack.append([])
            pos += 1
        elif c == ')':
            done = stack.pop()
            stack[-1].append(done)
            pos += 1
        elif c == '"':
            pos += 1
            out = []
            while text[pos] != '"':
                if text[pos] == '\\':
                    pos += 1
                    out.append({'n': '\n', 't': '\t'}.get(text[pos], text[pos]))
                else:
                    out.append(text[pos])
                pos += 1
            pos += 1
            stack[-1].append(''.join(out))
        else:
            start = pos
            while pos < n and text[pos] not in ' \t\r\n()':
                pos += 1
            stack[-1].append(Sym(text[start:pos]))
    assert len(stack) == 1, 'unbalanced parentheses'
    return stack[0][0]


def _atom(a):
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, str):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    if isinstance(a, float):
        s = ('%.6f' % a).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(a)


def dump(node, indent=0):
    """Serialise with one child list per line (KiCad accepts any whitespace)."""
    if not isinstance(node, list):
        return _atom(node)
    flat = '(' + ' '.join(dump(c) for c in node) + ')'
    if len(flat) <= 100 or not any(isinstance(c, list) for c in node):
        return flat
    pad = '  ' * (indent + 1)
    head = [dump(c) for c in node if not isinstance(c, list)]
    out = '(' + ' '.join(head)
    for c in node:
        if isinstance(c, list):
            out += '\n' + pad + dump(c, indent + 1)
    return out + '\n' + '  ' * indent + ')'


def tag(node):
    return node[0] if isinstance(node, list) and node else None


def children(node, name):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == name]


def child(node, name):
    for c in node[1:]:
        if isinstance(c, list) and c and c[0] == name:
            return c
    return None
