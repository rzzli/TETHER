"""Source-bound in-memory engineering codec. No filesystem or runtime authority."""
from dataclasses import dataclass
import hashlib
import json
import re
import struct

MAX_PACK_BYTES = 20 * 1024 * 1024
BLOCK = 65536
WIRE_SHA256 = "75605c03fb5b9bac659538035d8205b34df2ae1781b997a3181a1564676aa6c4"
PROFILE_ID = "actual-v3-fullresponse-unicode-controls-v1"
# Exact captured new source bytes. Matching them authenticates no original file.
SOURCE_PINS = (
    ("base_design", 86124, "ddf9fd360d72def0b91bd99b047422bf8ee623c0f8d6e0ba73535e04a7af1abc"),
    ("framing_contract", 16995, "4c4645f53c878e03cf1f0eaec575b3dcf1dcc006375aadc0080819393e4c3d24"),
    ("corpus", 233438, "13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c"),
    ("stages", 227662, "ad688168a366d5e95413ec69731d030c54431663e6574fb93445ced2b580413a"),
    ("profile_contract", 9809, "65a34539dd1bdecb20ed85724c58f80e362113cb4db969f5edf60b48af9a111d"),
    ("analyzer_contract", 8506, "05c214f42e9214691b5675cca58e67a6265dd069d2e7829f604df23c7ccca3e6"),
)
STAGE_IDS = ("mechanism_asof0", "genetics_asof0", "mechanism_vb_chief0", "genetics_vb_chief0")
STRATA = ("stage_source_report", "scalar_field_grid", "ASCII_escape_counterparts",
          "mixed_normalization_escape", "grammar_semantic_JSON_controls", "byte_harness_guards")
DIMENSIONS = ("project_JSON_parse", "Unicode_scalar_JSON", "complete_v3_semantic_validation",
              "generation_grammar_membership", "native_membership", "JSON_syntax")
_FACTORY = object()
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,127}\Z", re.ASCII)
_HEX = re.compile(r"[0-9a-f]*\Z", re.ASCII)


class CodecError(ValueError):
    """Bounded format/source consistency error, never a qualification result."""


def _need(condition, reason):
    if not condition:
        raise CodecError(reason)


def _check(callback):
    _need(callable(callback), "required_check_callback")
    callback()


def _hash(raw, check):
    _check(check)
    state = hashlib.sha256()
    view = memoryview(raw)
    for at in range(0, len(raw), BLOCK):
        check()
        state.update(view[at:at+BLOCK])
        check()
    result = state.hexdigest()
    check()
    return result


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _json(raw, check):
    def pairs(items):
        out = {}
        for key, value in items:
            _need(key not in out, "source_duplicate_JSON_key")
            out[key] = value
        return out
    check()
    try:
        result = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(CodecError("source_nonfinite_JSON")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise CodecError("source_JSON") from error
    check()
    _need(type(result) is dict, "source_object")
    return result


def _id(value, cap=128):
    _need(type(value) is str and 1 <= len(value) <= cap and _ID.fullmatch(value) is not None, "ID_grammar_or_cap")
    return value


def _digest(value):
    _need(type(value) is str and len(value) == 64 and _HEX.fullmatch(value) is not None, "digest_schema")
    return value


def _ternary(value):
    _need(value is None or type(value) is bool, "authored_ternary_type")
    return 2 if value is None else int(value)


def _grammar_bytes(value, declared, check):
    _need(type(value) is str and type(declared) is int and 1 <= declared <= BLOCK and len(value) <= BLOCK, "grammar_source_cap")
    # Count UTF8 bytes before allocating the encoded field, rejecting surrogates.
    count = 0
    for index, char in enumerate(value):
        if index % 1024 == 0: check()
        scalar = ord(char)
        _need(not 0xd800 <= scalar <= 0xdfff and scalar != 0, "grammar_scalar_or_NUL")
        count += 1 if scalar < 0x80 else (2 if scalar < 0x800 else (3 if scalar < 0x10000 else 4))
        _need(count <= BLOCK, "grammar_source_cap")
    _need(count == declared, "grammar_source_size")
    check(); raw = value.encode("utf-8", "strict"); check()
    return raw


@dataclass(frozen=True, slots=True)
class SourceBytes:
    base_design: bytes
    framing_contract: bytes
    corpus: bytes
    stages: bytes
    profile_contract: bytes
    analyzer_contract: bytes


@dataclass(frozen=True, slots=True)
class Grammar:
    id: str
    sha256: str
    raw: bytes


@dataclass(frozen=True, slots=True)
class Stage:
    id: str
    request_sha256: str
    payload_sha256: str
    grammar_index: int


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    ordinal: int
    stage_index: int
    stratum_index: int
    sha256: str
    raw: bytes
    authored_dimensions: tuple
    native_byte_eligible: bool
    harness_kind: int
    token_cap: int


@dataclass(frozen=True, slots=True, init=False)
class ValidatedProfile:
    """Factory-issued captured-byte context; not an authenticated live owner."""
    header_digests: tuple
    grammars: tuple
    stages: tuple
    cases: tuple
    source_pins: tuple
    _factory: object


@dataclass(frozen=True, slots=True)
class DecodedPack:
    sha256: str
    bytes: int
    header_digests: tuple
    grammars: tuple
    stages: tuple
    cases: tuple

    def to_dict(self):
        # Fresh ordinary diagnostic metadata, not a serialized validation token.
        return {"pack_sha256": self.sha256, "bytes": self.bytes, "profile_id": PROFILE_ID,
                "wire_semantics_sha256": self.header_digests[0],
                "grammars": [{"id": g.id, "sha256": g.sha256, "bytes": len(g.raw)} for g in self.grammars],
                "stages": [{"id": s.id, "grammar_index": s.grammar_index,
                            "request_sha256": s.request_sha256, "payload_sha256": s.payload_sha256} for s in self.stages],
                "cases": [{"id": c.id, "ordinal": c.ordinal, "stage_index": c.stage_index,
                           "stratum_index": c.stratum_index, "sha256": c.sha256, "bytes": len(c.raw),
                           "authored_dimensions": list(c.authored_dimensions), "native_byte_eligible": c.native_byte_eligible,
                           "harness_kind": c.harness_kind, "token_cap": c.token_cap} for c in self.cases],
                "profile_qualified": False, "originals_authenticated": False, "runtime_authorized": False,
                "scientific_validation": "not_established"}


def make_profile(sources, *, check):
    """Validate exact captured NEW metadata bytes, then mint immutable context."""
    _check(check)
    _need(type(sources) is SourceBytes, "source_container_type")
    documents = {}
    for name, size, expected_hash in SOURCE_PINS:
        raw = getattr(sources, name)
        # Exact source size is checked before hashing, decoding or copying.
        _need(type(raw) is bytes and len(raw) == size, "source_bytes_or_size")
        _need(_hash(raw, check) == expected_hash, "source_hash")
        documents[name] = _json(raw, check)
    base = documents["base_design"]; framing = documents["framing_contract"]
    semantics = base["semantic_contract"]
    _need(_hash(_canonical(semantics), check) == base["semantic_sha256"], "base_semantics")
    effective = _hash(_canonical({"base_design_semantic_sha256":base["semantic_sha256"],
                                  "framing_semantics":framing["framing_semantics"]}), check)
    _need(effective == WIRE_SHA256 == framing["effective_wire_semantics_sha256"], "effective_wire_fingerprint")
    _need(framing["base_design_semantic_sha256"] == base["semantic_sha256"], "framing_base_binding")
    corpus = documents["corpus"]; stage_document = documents["stages"]
    _need(corpus["profile_id"] == PROFILE_ID == documents["profile_contract"]["profile_id"], "profile_id")
    _need(corpus["contract"]["sha256"] == SOURCE_PINS[4][2], "corpus_contract")
    _need(documents["analyzer_contract"]["profile_contract_sha256"] == SOURCE_PINS[4][2], "analyzer_profile_binding")
    _need(corpus["execution_authorized"] is False and stage_document["execution_authorized"] is False, "source_scope")
    stage_rows = stage_document["stages"]
    _need(type(stage_rows) is list and len(stage_rows) == stage_document["stage_instances"] == 4, "stage_count")
    _need(tuple(row["id"] for row in stage_rows) == STAGE_IDS, "stage_ID_order")
    gram_records = []; gram_hashes = []; stage_records = []
    for row in stage_rows:
        check()
        name = _id(row["id"], 64); h = _digest(row["grammar_sha256"])
        grammar = row["prepared"]["generation_grammar"]["grammar"]
        raw = _grammar_bytes(grammar, row["grammar_bytes"], check)
        _need(_hash(raw, check) == h, "source_grammar_hash")
        if h not in gram_hashes:
            _need(len(gram_hashes) < 2, "unique_grammar_count")
            gram_hashes.append(h); gram_records.append(Grammar("grammar/"+str(len(gram_hashes)-1), h, raw))
        else:
            _need(gram_records[gram_hashes.index(h)].raw == raw, "grammar_hash_alias")
        stage_records.append(Stage(name, _digest(row["request_sha256"]), _digest(row["payload_sha256"]), gram_hashes.index(h)))
    _need(len(gram_records) == 2 and set(gram_hashes) == set(stage_document["unique_grammar_hashes"]), "grammar_roster")
    rows = corpus["cases"]
    _need(type(rows) is list and len(rows) == 84, "case_count")
    case_records = []; seen = set(); strata = [0]*6; eligible = population = 0
    for ordinal, row in enumerate(rows):
        check()
        identity = _id(row["id"])
        _need(identity not in seen and type(row["ordinal"]) is int and row["ordinal"] == ordinal, "case_ID_or_ordinal")
        seen.add(identity)
        _need(row["stage_id"] in STAGE_IDS and row["stratum"] in STRATA, "case_stage_or_stratum")
        stage_index = STAGE_IDS.index(row["stage_id"]); stratum_index = STRATA.index(row["stratum"]); strata[stratum_index] += 1
        _need(row["grammar_sha256"] == gram_records[stage_records[stage_index].grammar_index].sha256, "case_grammar_binding")
        B = row["bytes"]; text = row["raw_hex"]
        _need(type(B) is int and 1 <= B <= 1024 and type(text) is str and len(text) == 2*B and _HEX.fullmatch(text) is not None, "case_raw_shape")
        raw = bytes.fromhex(text)
        h = _digest(row["sha256"]); _need(_hash(raw, check) == h, "source_case_hash")
        expected = row["expected"]; dimensions = tuple(_ternary(expected[k]) for k in DIMENSIONS)
        native_eligible = expected["native_byte_eligible"]
        _need(type(native_eligible) is bool and type(row["coverage_population"]) is bool, "source_boolean")
        try: raw.decode("utf-8", "strict"); utf8 = True
        except UnicodeError: utf8 = False
        kind = 2 if b"\0" in raw else (1 if not utf8 else 0)
        _need(native_eligible is (kind == 0), "native_byte_eligibility")
        _need(native_eligible or expected["native_membership"] is None, "harness_membership_not_null")
        _need(row["coverage_population"] is (native_eligible and expected["generation_grammar_membership"] is True and expected["complete_v3_semantic_validation"] is True), "population_rule")
        _need(type(row["prospective_token_cap"]) is int and row["prospective_token_cap"] == 4*B+32 <= 65536, "source_token_cap")
        eligible += native_eligible; population += row["coverage_population"]
        case_records.append(Case(identity, ordinal, stage_index, stratum_index, h, raw, dimensions, native_eligible, kind, row["prospective_token_cap"]))
    _need(tuple(strata) == (4,42,14,8,10,6) and eligible == 78 and population == 68, "profile_cardinalities")
    result = object.__new__(ValidatedProfile)
    values = {"header_digests":(WIRE_SHA256, SOURCE_PINS[2][2], SOURCE_PINS[3][2], SOURCE_PINS[4][2], SOURCE_PINS[5][2]),
              "grammars":tuple(gram_records), "stages":tuple(stage_records), "cases":tuple(case_records),
              "source_pins":SOURCE_PINS, "_factory":_FACTORY}
    for name, value in values.items(): object.__setattr__(result, name, value)
    check()
    return result


def _profile(profile):
    _need(type(profile) is ValidatedProfile and getattr(profile, "_factory", None) is _FACTORY, "factory_profile_required")


def encode(profile, *, check):
    _check(check); _profile(profile)
    out = bytearray()
    def add(raw):
        _need(len(out)+len(raw) <= MAX_PACK_BYTES, "pack_cap")
        for at in range(0, len(raw), BLOCK):
            check(); out.extend(raw[at:at+BLOCK]); check()
    def integer(n):
        _need(type(n) is int and 0 <= n <= 0xffffffff, "u32_range")
        add(struct.pack("<I", n))
    def identity(value, cap=128):
        raw = _id(value, cap).encode("ascii"); integer(len(raw)); add(raw)
    add(b"R09NU01\0"); integer(1)
    for h in profile.header_digests: add(bytes.fromhex(h))
    for count in (4,2,84,4): integer(count)
    for grammar in profile.grammars:
        identity(grammar.id); add(bytes.fromhex(grammar.sha256)); integer(len(grammar.raw)); add(grammar.raw)
    for stage in profile.stages:
        identity(stage.id,64); add(bytes.fromhex(stage.request_sha256)); add(bytes.fromhex(stage.payload_sha256)); integer(stage.grammar_index)
    for case in profile.cases:
        identity(case.id)
        for n in (case.ordinal,case.stage_index,case.stratum_index): integer(n)
        add(bytes.fromhex(case.sha256)); integer(len(case.raw)); add(case.raw)
        for n in case.authored_dimensions: integer(n)
        integer(int(case.native_byte_eligible)); integer(case.harness_kind); integer(case.token_cap)
    check(); result = bytes(out); check()
    return result


def decode(raw, profile, *, check):
    _check(check); _profile(profile)
    _need(type(raw) is bytes and 188 <= len(raw) <= MAX_PACK_BYTES, "pack_bytes_or_cap")
    view = memoryview(raw); at = 0; seen = set()
    def take(n, cap=BLOCK):
        nonlocal at
        _need(type(n) is int and 0 <= n <= cap and n <= len(raw)-at, "field_cap_or_truncation")
        check(); result = bytes(view[at:at+n]); at += n; check()
        return result
    def integer(): return struct.unpack("<I", take(4))[0]
    def identity(cap=128):
        n = integer()
        _need(1 <= n <= cap, "ID_cap")
        field = take(n,cap)
        try: result = field.decode("ascii", "strict")
        except UnicodeError as error: raise CodecError("ID_ASCII") from error
        _id(result,cap); _need(result not in seen, "duplicate_ID"); seen.add(result)
        return result
    _need(take(8) == b"R09NU01\0" and integer() == 1, "magic_or_version")
    digests = tuple(take(32).hex() for _ in range(5))
    _need(digests == profile.header_digests, "header_digest_binding")
    _need(tuple(integer() for _ in range(4)) == (4,2,84,4), "header_counts")
    grammars = []
    for expected in profile.grammars:
        name = identity(); h = take(32).hex(); n = integer()
        _need(1 <= n <= BLOCK, "grammar_cap")
        body = take(n)
        _need(b"\0" not in body, "grammar_NUL")
        try: body.decode("utf-8", "strict")
        except UnicodeError as error: raise CodecError("grammar_UTF8") from error
        _need(_hash(body,check) == h, "grammar_hash")
        record = Grammar(name,h,body); _need(record == expected, "grammar_source_binding"); grammars.append(record)
    stages = []
    for expected in profile.stages:
        name = identity(64); request = take(32).hex(); payload = take(32).hex(); index = integer()
        _need(index < 2, "stage_grammar_index")
        record = Stage(name,request,payload,index); _need(record == expected, "stage_source_binding"); stages.append(record)
    cases = []
    for ordinal, expected in enumerate(profile.cases):
        name = identity(); number = integer(); stage_index = integer(); stratum_index = integer()
        _need(number == ordinal and stage_index < 4 and stratum_index < 6, "case_indices")
        h = take(32).hex(); B = integer()
        _need(1 <= B <= 1024, "case_bytes_cap")
        body = take(B,1024); _need(_hash(body,check) == h, "case_hash")
        dimensions = tuple(integer() for _ in range(6))
        _need(all(n <= 2 for n in dimensions), "ternary_enum")
        eligible = integer(); kind = integer(); token_cap = integer()
        _need(eligible <= 1 and kind <= 2 and token_cap == min(65536,4*B+32), "case_flags_or_token_cap")
        record = Case(name,number,stage_index,stratum_index,h,body,dimensions,bool(eligible),kind,token_cap)
        _need(record == expected, "case_source_binding"); cases.append(record)
    _need(at == len(raw), "trailing_bytes")
    result = DecodedPack(_hash(raw,check),len(raw),digests,tuple(grammars),tuple(stages),tuple(cases))
    check()
    return result
