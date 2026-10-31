"""Independent finite-subset GBNF oracle; explicitly NOT native qualification."""

from functools import lru_cache
import hashlib
from itertools import product
import json
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from asof.study.interpretation_grammar import _Builder, build_grammar


def scalar(source, at):
    if source[at] != "\\":
        return ord(source[at]), at + 1
    letter = source[at + 1]
    width = {"u": 4, "U": 8, "x": 2}.get(letter)
    if width:
        return int(source[at + 2:at + 2 + width], 16), at + 2 + width
    value = {"t": 9, "r": 13, "n": 10, "\\": 92, '"': 34, "[": 91, "]": 93}[letter]
    return value, at + 2


def tokens(source):
    result, at = [], 0
    while at < len(source):
        if source[at].isspace():
            at += 1
        elif source[at] == '"':
            start = at
            at += 1
            while source[at] != '"':
                at += 2 if source[at] == "\\" else 1
            at += 1
            result.append(("literal", json.loads(source[start:at])))
        elif source[at] == "[":
            at += 1
            intervals = []
            while source[at] != "]":
                first, at = scalar(source, at)
                if source[at] == "-" and source[at + 1] != "]":
                    last, at = scalar(source, at + 1)
                else:
                    last = first
                assert first <= last
                intervals.append((first, last))
            at += 1
            result.append(("class", tuple(intervals)))
        elif source[at] in "()|":
            result.append(source[at])
            at += 1
        else:
            match = re.match(r"[a-z][a-z0-9-]*", source[at:])
            assert match, source[at:]
            result.append(("ref", match.group()))
            at += len(match.group())
    return result


def parse(grammar):
    rules = {}
    # GBNF rule separators are ASCII newlines. U+0085/U+2028/U+2029 remain
    # legitimate raw Unicode inside quoted terminals, not extra rule lines.
    for line in grammar.split("\n"):
        if not line:
            continue
        name, expression = line.split("::=", 1)
        items, at = tokens(expression), 0

        def alternative():
            nonlocal at
            branches = [sequence()]
            while at < len(items) and items[at] == "|":
                at += 1
                branches.append(sequence())
            return ("alt", tuple(branches))

        def sequence():
            nonlocal at
            nodes = []
            while at < len(items) and items[at] not in ("|", ")"):
                item = items[at]
                at += 1
                if item == "(":
                    item = alternative()
                    assert items[at] == ")"
                    at += 1
                nodes.append(item)
            return ("seq", tuple(nodes))

        node = alternative()
        assert at == len(items)
        rules[name.strip()] = node
    return rules


def accepts(rules, name, document):
    @lru_cache(None)
    def ends(node, at):
        kind, value = node
        if kind == "literal":
            return frozenset((at + len(value),)) if document.startswith(value, at) else frozenset()
        if kind == "class":
            return frozenset((at + 1,)) if at < len(document) and any(
                lower <= ord(document[at]) <= upper for lower, upper in value
            ) else frozenset()
        if kind == "ref":
            return ends(rules[value], at)
        if kind == "alt":
            return frozenset(position for child in value for position in ends(child, at))
        assert kind == "seq"
        positions = frozenset((at,))
        for child in value:
            positions = frozenset(end for start in positions for end in ends(child, start))
            if not positions:
                break
        return positions
    return len(document) in ends(rules[name], 0)


