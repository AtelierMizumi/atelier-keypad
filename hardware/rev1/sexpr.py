"""Minimal reader and writer for KiCad s-expression files (standard library only)."""
from __future__ import annotations


class Q(str):
    """A quoted string, as opposed to a bare atom."""


def parse(text: str):
    pos, n = 0, len(text)
    stack: list[list] = [[]]
    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            pos += 1
        elif c == "(":
            new: list = []
            stack[-1].append(new)
            stack.append(new)
            pos += 1
        elif c == ")":
            stack.pop()
            pos += 1
        elif c == '"':
            pos += 1
            buf = []
            while text[pos] != '"':
                if text[pos] == "\\":
                    buf.append(text[pos:pos + 2])
                    pos += 2
                else:
                    buf.append(text[pos])
                    pos += 1
            pos += 1
            stack[-1].append(Q("".join(buf)))
        else:
            start = pos
            while pos < n and text[pos] not in ' \t\r\n()"':
                pos += 1
            stack[-1].append(text[start:pos])
    if len(stack) != 1 or len(stack[0]) != 1:
        raise ValueError("unbalanced s-expression")
    return stack[0][0]


def _atom(a) -> str:
    if isinstance(a, Q):
        return '"' + a + '"'
    if isinstance(a, float):
        return f"{a:.4f}".rstrip("0").rstrip(".") or "0"
    return str(a)


def dump(node, indent: int = 0) -> str:
    if not isinstance(node, list):
        return _atom(node)
    flat = "(" + " ".join(dump(c) for c in node) + ")"
    if len(flat) <= 100 and "\n" not in flat:
        return flat
    pad = "\t" * (indent + 1)
    head, rest = [], list(node)
    while rest and not isinstance(rest[0], list):
        head.append(_atom(rest.pop(0)))
    lines = ["(" + " ".join(head)]
    lines += [pad + dump(c, indent + 1) for c in rest]
    lines.append("\t" * indent + ")")
    return "\n".join(lines)


def find(node: list, key: str):
    """First child list whose head is `key`, or None."""
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def find_all(node: list, key: str) -> list:
    return [c for c in node if isinstance(c, list) and c and c[0] == key]
