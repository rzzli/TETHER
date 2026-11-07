"""Finite, value-preserving GBNF preparation; no native recognition or dispatch.

The serialization domain is intentionally smaller than all JSON byte spellings.
The unchanged semantic post-validator remains mandatory after generation.  This
module uses only the standard library and never loads a runtime or model.
"""

from collections.abc import Mapping
import hashlib
import json

from tether_engine.serde import ContractError, freeze


GENERATOR = "strict-interpretation-gbnf-v1"
MAX_GRAMMAR_BYTES = 65536
# Necessary inherited precondition: every quote is a distinct original string
# occurrence in the complete prompt, whose existing maximum is 32768 UTF-8 bytes.
# This alone does not imply that the prompt or complete HTTP payload will fit.
MAX_QUOTE_TEXT_BYTES = 32768
_WHITESPACE = (
    (0x0009, 0x000D),
    (0x001C, 0x0020),
    (0x0085, 0x0085),
    (0x00A0, 0x00A0),
    (0x1680, 0x1680),
    (0x2000, 0x200A),
    (0x2028, 0x2029),
    (0x202F, 0x202F),
    (0x205F, 0x205F),
    (0x3000, 0x3000),
)
_WHITESPACE_POINTS = frozenset(
    value for lower, upper in _WHITESPACE for value in range(lower, upper + 1)
)


def _literal(value):
    """Quote terminal text in GBNF, independently of JSON's escape vocabulary."""
    result = ['"']
    for character in value:
        scalar = ord(character)
        if character in ('"', "\\"):
            result.append("\\" + character)
        elif scalar < 0x20:
            result.append(f"\\u{scalar:04x}")
        else:
            result.append(character)
    result.append('"')
    return "".join(result)


def _json_string(value):
    # Escape every '<', even within a longer known constant.  This preserves the
    # value while precluding a runtime '<|' delimiter across grammar atoms.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def _merged(intervals):
    result = []
    for lower, upper in sorted(intervals):
        if lower > upper:
            continue
        if result and lower <= result[-1][1] + 1:
            result[-1] = (result[-1][0], max(upper, result[-1][1]))
        else:
            result.append((lower, upper))
    return tuple(result)


def _complement(intervals, maximum):
    result, cursor = [], 0
    for lower, upper in _merged(intervals):
        if cursor < lower:
            result.append((cursor, lower - 1))
        cursor = max(cursor, upper + 1)
    if cursor <= maximum:
        result.append((cursor, maximum))
    return tuple(result)


def _class(intervals):
    def escaped(value):
        return f"\\u{value:04x}" if value <= 0xFFFF else f"\\U{value:08x}"

    return (
        "["
        + "".join(
            escaped(lower) if lower == upper else escaped(lower) + "-" + escaped(upper)
            for lower, upper in intervals
        )
        + "]"
    )


class _Builder:
    def __init__(self):
        self.rules = {}
        self._hex_cache = {}
        self.add("empty", '""')
        self.add("hex", "[0-9a-fA-F]")
        for count in range(2, 5):
            self.add(f"hex-{count}", " ".join(["hex"] * count))

    def add(self, name, expression):
        if name in self.rules:
            raise AssertionError("Duplicate internal grammar rule")
        self.rules[name] = expression
        return name

    def hex_language(self, intervals, digits=4):
        """Shared hexadecimal interval trie, accepting both letter cases.

        Each recursive interval is relative to its current numeric prefix. Full
        subtrees use shared fixed-width hex rules; only boundaries are expanded.
        """
        intervals = _merged(intervals)
        maximum = 16**digits - 1
        if intervals == ((0, maximum),):
            return "empty" if digits == 0 else "hex" if digits == 1 else f"hex-{digits}"
        key = (digits, intervals)
        if key in self._hex_cache:
            return self._hex_cache[key]
        if not intervals or digits == 0:
            raise AssertionError("Empty or invalid internal hexadecimal language")
        width = 16 ** (digits - 1)
        groups = {}
        for digit in range(16):
            start, end = digit * width, (digit + 1) * width - 1
            child = tuple(
                (max(lower, start) - start, min(upper, end) - start)
                for lower, upper in intervals
                if lower <= end and upper >= start
            )
            if child:
                suffix = self.hex_language(child, digits - 1)
                groups.setdefault(suffix, []).append(digit)
        alternatives = []
        for suffix, values in groups.items():
            characters = []
            for digit in values:
                character = "0123456789abcdef"[digit]
                characters.append(ord(character))
                if digit >= 10:
                    characters.append(ord(character.upper()))
            head = _class(_merged((value, value) for value in characters))
            alternatives.append(head if suffix == "empty" else f"{head} {suffix}")
        name = f"u-{len(self._hex_cache)}"
        # Children have already occupied their own memo slots.
        self._hex_cache[key] = self.add(name, " | ".join(alternatives))
        return name

    def characters(self):
        raw_whitespace = tuple(
            (max(lower, 0x20), upper) for lower, upper in _WHITESPACE if upper >= 0x20
        )
        excluded = _WHITESPACE + (
            (0, 0x1F),
            (0x22, 0x22),
            (0x3C, 0x3C),
            (0x5C, 0x5C),
            (0xD800, 0xDFFF),
        )
        raw_nonblank = _complement(excluded, 0x10FFFF)
        whitespace_hex = self.hex_language(_WHITESPACE)
        nonblank_hex = self.hex_language(
            _complement(_WHITESPACE + ((0xD800, 0xDFFF),), 0xFFFF)
        )
        high = self.hex_language(((0xD800, 0xDBFF),))
        low = self.hex_language(((0xDC00, 0xDFFF),))
        prefix = _literal("\\u")
        pair = self.add("surrogate-pair", f"{prefix} {high} {prefix} {low}")
        whitespace = [_class(raw_whitespace)]
        whitespace.extend(_literal("\\" + value) for value in ("t", "n", "f", "r"))
        whitespace.append(f"{prefix} {whitespace_hex}")
        nonblank = [_class(raw_nonblank)]
        nonblank.extend(_literal("\\" + value) for value in ('"', "\\", "/", "b"))
        nonblank.extend((f"{prefix} {nonblank_hex}", pair))
        self.add("char-w", " | ".join(whitespace))
        self.add("char-n", " | ".join(nonblank))
        self.add("char-a", "char-w | char-n")

    def exact(self, kind, count):
        if (
            kind not in ("a", "w", "n")
            or type(count) is not int
            or count < 1
            or count & (count - 1)
        ):
            raise AssertionError(
                "Exact helper requires A/W/N and a positive power of two"
            )
        if count == 1:
            return f"char-{kind}"
        name = f"{kind}-e-{count}"
        if name in self.rules:
            return name
        half = count // 2
        if kind in ("a", "w"):
            child = self.exact(kind, half)
            body = f"{child} {child}"
        else:
            a, w, n = (self.exact(k, half) for k in ("a", "w", "n"))
            body = f"{n} {a} | {w} {n}"
        return self.add(name, body)

    def bounded(self, kind, count):
        if kind not in ("a", "n") or type(count) is not int or count < 0:
            raise AssertionError(
                "Bounded helper supports only A/N and a nonnegative count"
            )
        if count == 0:
            # No nonblank length-zero string exists.  Never encode this as epsilon.
            return None if kind == "n" else "empty"
        name = f"{kind}-r-{count}"
        if name in self.rules:
            return name
        block = 1 << (count.bit_length() - 1)
        remainder = count - block
        shorter = self.bounded(kind, block - 1)
        alternatives = [shorter] if shorter else []
        alternatives.append(f"{self.exact(kind, block)} {self.bounded('a', remainder)}")
        if kind == "n":
            tail = self.bounded("n", remainder)
            if tail:
                alternatives.append(f"{self.exact('w', block)} {tail}")
        return self.add(name, " | ".join(alternatives))

    def references(self, count):
        def node(lower, upper):
            if upper - lower == 1:
                return _literal(_json_string(f"Q{lower}")), None
            middle = (lower + upper) // 2
            left, left_pairs = node(lower, middle)
            right, right_pairs = node(middle, upper)
            ids = self.add(f"i-{lower}-{upper}", f"{left} | {right}")
            pairs = [value for value in (left_pairs, right_pairs) if value]
            pairs.extend((f'{left} "," {right}', f'{right} "," {left}'))
            return ids, self.add(f"p-{lower}-{upper}", " | ".join(pairs))

        ids, pairs = node(0, count)
        body = f"{ids} | {pairs}" if pairs else ids
        return self.add("refs", f'"[" ({body}) "]"')

    def document(self, quote_texts, claim_limit):
        self.characters()
        text = self.add(
            "text", f"{_literal(chr(34))} {self.bounded('n', 1800)} {_literal(chr(34))}"
        )
        self.add(
            "reason",
            f"{_literal(chr(34))} {self.bounded('n', 512)} {_literal(chr(34))}",
        )
        items = self.add(
            "text-items",
            " | ".join(' "," '.join([text] * count) for count in range(1, 5)),
        )
        self.add("texts", f'"[" (empty | {items}) "]"')
        self.add("nonempty-texts", f'"[" {items} "]"')
        self.references(len(quote_texts))
        literal_names, bindings, report_ids = {}, [], []
        for quote_id, value in quote_texts.items():
            if len(value) > 1800:
                continue
            report_ids.append(quote_id)
            if value not in literal_names:
                literal_names[value] = self.add(
                    f"l-{len(literal_names)}", _literal(_json_string(value))
                )
            bindings.append(
                _literal("[" + _json_string(quote_id) + '],"text":')
                + " "
                + literal_names[value]
            )
        inference_prefix = _literal('{"kind":')
        inference_kinds = " | ".join(
            _literal(_json_string(value))
            for value in ("scientific_inference", "caution")
        )
        self.add(
            "analysis",
            (
                inference_prefix
                + " ("
                + inference_kinds
                + ") "
                + _literal(',"limitations":')
                + " nonempty-texts "
                + _literal(',"quote_refs":')
                + " refs "
                + _literal(',"text":')
                + " text "
                + _literal("}")
            ),
        )
        claims = ["analysis"]
        if bindings:
            self.add("report-binding", " | ".join(bindings))
            self.add(
                "report",
                (
                    _literal('{"kind":"source_report","limitations":')
                    + " texts "
                    + _literal(',"quote_refs":')
                    + " report-binding "
                    + _literal("}")
                ),
            )
            claims.append("report")
        self.add("claim", " | ".join(claims))
        self.add(
            "claim-items",
            " | ".join(
                ' "," '.join(["claim"] * count) for count in range(1, claim_limit + 1)
            ),
        )
        self.add("claims", '"[" claim-items "]"')
        self.add(
            "root",
            (
                _literal('{"abstention_reason":')
                + " ("
                + _literal('null,"answer_status":"answered","claims":')
                + " claims | reason "
                + _literal(',"answer_status":')
                + " ("
                + _literal('"partial","claims":')
                + " claims | "
                + _literal('"abstained","claims":[]')
                + ")) "
                + _literal(',"unresolved":')
                + " texts "
                + _literal("}")
            ),
        )
        return tuple(report_ids)

    def source(self):
        # Put the public entry first without depending on declaration order.
        names = ["root"] + [name for name in self.rules if name != "root"]
        return "".join(f"{name} ::= {self.rules[name]}\n" for name in names)


def build_grammar(quote_texts, *, claim_limit=3):
    """Return an immutable finite grammar artifact or fail without pruning.

    Catalog insertion order is irrelevant; Q0..Q(n-1) are emitted numerically.
    This function does not certify native grammar recognition, EOG or science.
    """
    if type(claim_limit) is not int or not 1 <= claim_limit <= 3:
        raise ContractError(
            "Grammar claim_limit must be an integer from one through three"
        )
    if not isinstance(quote_texts, Mapping) or not 1 <= len(quote_texts) <= 256:
        raise ContractError(
            "Grammar quote catalog must contain one through 256 entries"
        )
    ids = tuple(f"Q{index}" for index in range(len(quote_texts)))
    if set(quote_texts) != set(ids):
        raise ContractError("Grammar quote IDs must be exactly contiguous Q0..Q(n-1)")
    originals = {quote_id: quote_texts[quote_id] for quote_id in ids}
    for value in originals.values():
        if not isinstance(value, str) or not value:
            raise ContractError(
                "Grammar quote text must be nonblank Unicode scalar text"
            )
    # Check cheap lengths before any scalar iteration, encoding or hashing.
    if sum(len(value) for value in originals.values()) > MAX_QUOTE_TEXT_BYTES:
        raise ContractError(
            "Original quote text exceeds the inherited 32768-byte prompt bound; no pruning"
        )
    text_hashes, text_bytes = {}, 0
    for quote_id, value in originals.items():
        # Long quotes remain valid references. Stream validation/hashing instead
        # of creating an unbounded full-size UTF-8 copy for an omitted literal.
        digest, nonblank = hashlib.sha256(), False
        for offset in range(0, len(value), 65536):
            chunk = value[offset : offset + 65536]
            try:
                encoded_chunk = chunk.encode("utf-8")
            except UnicodeEncodeError as error:
                raise ContractError(
                    "Grammar quote contains an unpaired/non-scalar surrogate"
                ) from error
            text_bytes += len(encoded_chunk)
            if text_bytes > MAX_QUOTE_TEXT_BYTES:
                raise ContractError(
                    "Original quote text exceeds the inherited 32768-byte prompt bound; no pruning"
                )
            digest.update(encoded_chunk)
            if not nonblank:
                nonblank = any(
                    ord(character) not in _WHITESPACE_POINTS for character in chunk
                )
        if not nonblank:
            raise ContractError(
                "Grammar quote text must be nonblank Unicode scalar text"
            )
        text_hashes[quote_id] = digest.hexdigest()
    builder = _Builder()
    report_ids = builder.document(originals, claim_limit)
    grammar = builder.source()
    encoded = grammar.encode("utf-8")
    if len(encoded) > MAX_GRAMMAR_BYTES:
        raise ContractError(
            "Complete generation grammar exceeds 65536 bytes; no pruning"
        )
    return freeze(
        dict(
            schema_version=1,
            generator=GENERATOR,
            grammar=grammar,
            grammar_sha256=hashlib.sha256(encoded).hexdigest(),
            grammar_bytes=len(encoded),
            serialization_domain=dict(
                identity="compact-sorted-scalar-json-v1",
                compact=True,
                object_key_order="sorted",
                decoded_character_unit="Unicode scalar / Python code point",
                unicode_normalization="none",
                raw_less_than=False,
                less_than_escape="\\u003c",
                generic_string_forms=(
                    "raw scalar",
                    "short JSON escape",
                    "BMP Unicode escape",
                    "paired surrogate Unicode escapes",
                ),
                source_report_spelling="one exact value-preserving JSON spelling, with less-than escaped",
                whitespace_codepoints=tuple(sorted(_WHITESPACE_POINTS)),
            ),
            quote_ids=ids,
            source_report_ids=report_ids,
            quote_text_sha256=text_hashes,
            claim_limit=claim_limit,
            post_validation_only=(
                "global claim-text uniqueness",
                "raw and canonical response byte limits",
                "source/request/history authority and temporal eligibility",
                "scientific entailment and validity",
            ),
            native_conformance="unverified",
            metrics=dict(rules=len(builder.rules)),
        )
    )
