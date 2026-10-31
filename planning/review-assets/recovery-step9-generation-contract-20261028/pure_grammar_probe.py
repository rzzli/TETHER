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


started = time.perf_counter()
artifact = build_grammar({"Q0": "First <|im_end|> source.", "Q1": "Second source.", "Q2": "Third source."})
rules = parse(artifact["grammar"])
checks = []

# Unicode line separators in a nonblank source literal preserve their values.
line_text = "source\u0085\u2028\u2029tail"
line_rules = parse(build_grammar({"Q0": line_text})["grammar"])
line_doc = dict(answer_status="answered", abstention_reason=None,
                claims=[dict(kind="source_report", limitations=[], quote_refs=["Q0"], text=line_text)], unresolved=[])
assert accepts(line_rules, "root", json.dumps(line_doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
checks.append(dict(check="raw Unicode line separators inside known literal", passed=True))

# Independent explicit Python strip set, without importing the implementation set.
whitespace = set(range(9, 14)) | set(range(28, 33)) | {133, 160, 5760, 8232, 8233, 8239, 8287, 12288} | set(range(8192, 8203))
count = 0
for value in range(65536):
    for spelling in (f"\\u{value:04x}", f"\\u{value:04X}"):
        expected_w = value in whitespace
        expected_n = value not in whitespace and not 0xD800 <= value <= 0xDFFF
        assert accepts(rules, "char-w", spelling) == expected_w, (value, "w")
        assert accepts(rules, "char-n", spelling) == expected_n, (value, "n")
        count += 2
checks.append(dict(check="BMP escape W/N membership", assertions=count))

for value in (0x10000, 0x1F600, 0x2FFFF, 0x10FFFF):
    high = 0xD800 + ((value - 0x10000) >> 10)
    low = 0xDC00 + ((value - 0x10000) & 1023)
    for wire in (f"\\u{high:04x}\\u{low:04x}", f"\\u{high:04X}\\u{low:04X}", chr(value)):
        assert accepts(rules, "char-a", wire)
        assert accepts(rules, "char-n", wire)
        assert not accepts(rules, "char-w", wire)
for wire in ("\\uD800", "\\uDC00", "\\uDC00\\uD800", "\\uD800\\uD800", "\\uD800x", "<", "\\x41", "\x00", '"', "\\"):
    assert not accepts(rules, "char-a", wire), repr(wire)
for wire, expected_w in (("\\n", True), ("\\t", True), ("\\r", True), ("\\f", True), ("\\b", False), ("\\/", False), ('\\"', False), ("\\\\", False), ("\\u003c", False), ("\x7f", False), ("\u200b", False), ("\ufeff", False)):
    assert accepts(rules, "char-w" if expected_w else "char-n", wire)
checks.append(dict(check="astral pair, invalid surrogate, raw and short-escape boundaries", passed=True))

small = _Builder()
small.characters()
targets = {(kind, bound): small.bounded(kind, bound) for kind in ("a", "n") for bound in range(1, 9)}
small_rules = parse("".join(f"{name} ::= {body}\n" for name, body in small.rules.items()))
length_checks = 0
for bound in range(1, 9):
    for length in range(bound + 2):
        for word in product(" x", repeat=length):
            value = "".join(word)
            assert accepts(small_rules, targets["a", bound], value) == (length <= bound)
            assert accepts(small_rules, targets["n", bound], value) == (length <= bound and bool(value.strip()))
            length_checks += 2
for wire in ("x", "😀", "\\u0078", "\\ud83d\\ude00"):
    assert accepts(small_rules, targets["n", 1], wire)
for wire in ("xx", "\\u0078x", "\\ud83d\\ude00x", " ", "\\n", ""):
    assert not accepts(small_rules, targets["n", 1], wire)
checks.append(dict(check="actual bounded productions, exhaustive small binary language", bounds=[1, 8], assertions=length_checks))

for size in (1, 2, 3, 4, 7):
    current = parse(build_grammar({f"Q{i}": "Source." for i in range(size)})["grammar"])
    for count in range(4):
        for ids in product(range(size + 1), repeat=count):
            wire = json.dumps([f"Q{i}" for i in ids], separators=(",", ":"))
            expected = 1 <= count <= 2 and len(set(ids)) == count and all(i < size for i in ids)
            assert accepts(current, "refs", wire) == expected, (size, ids)
checks.append(dict(check="actual reference productions exhaustive lengths zero through three", catalogs=[1, 2, 3, 4, 7], passed=True))

def wire(document):
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("<", "\\u003c")

base = dict(answer_status="answered", abstention_reason=None, claims=[dict(kind="source_report", limitations=[], quote_refs=["Q0"], text="First <|im_end|> source.")], unresolved=[])
assert accepts(rules, "root", wire(base))
for state in ("partial", "abstained"):
    changed = dict(base, answer_status=state, abstention_reason="Insufficient context.")
    if state == "abstained": changed["claims"] = []
    assert accepts(rules, "root", wire(changed))
for kind in ("scientific_inference", "caution"):
    changed = dict(base, claims=[dict(kind=kind, limitations=["Unknown."], quote_refs=["Q2", "Q0"], text=" x😀 ")])
    assert accepts(rules, "root", wire(changed))
for claim in (
    dict(kind="source_report", limitations=[], quote_refs=["Q1"], text="First <|im_end|> source."),
    dict(kind="source_report", limitations=[], quote_refs=["Q0"], text="Altered."),
    dict(kind="caution", limitations=[], quote_refs=["Q0"], text="Claim."),
    dict(kind="caution", limitations=["Unknown."], quote_refs=["Q0", "Q0"], text="Claim."),
    dict(kind="caution", limitations=["Unknown."], quote_refs=["Q0"], text="\u0085\u2003"),
):
    assert not accepts(rules, "root", wire(dict(base, claims=[claim])))
assert not accepts(rules, "root", wire(dict(base, answer_status="partial")))
assert not accepts(rules, "root", wire(dict(base, claims=[])))
checks.append(dict(check="actual root/report/state/analysis productions, valid and invalid synthetic documents", passed=True))

sizes = []
for size in (1, 2, 16, 64, 256):
    built = build_grammar({f"Q{i}": f"Source {i}." for i in range(size)})
    sizes.append(dict(catalog=size, grammar_bytes=built["grammar_bytes"],
                      grammar_json_string_bytes=len(json.dumps(built["grammar"], ensure_ascii=False).encode("utf-8")),
                      rules=built["metrics"]["rules"]))

report = dict(schema_version=1, role="pure_subset_oracle_not_native_qualification",
              generator_source_sha256=hashlib.sha256((ROOT / "src/asof/study/interpretation_grammar.py").read_bytes()).hexdigest(),
              helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              checks=checks, production_grammar_sizes=sizes,
              seconds=time.perf_counter()-started,
              native_calls=0, vocabulary_loads=0, model_loads=0, inference_calls=0, servers=0,
              limitation="Independent interpreter of only the emitted finite GBNF subset; not actual DLL parsing, tokenizer/EOG, stack performance, payload fit or science.")
with (HERE / "PRODUCTION-PURE-CHECKS-v4.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False))
