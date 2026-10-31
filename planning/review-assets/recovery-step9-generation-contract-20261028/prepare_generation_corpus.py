"""Freeze a separate authored extension; run no schema/native/model oracle."""
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from asof.serde import canonical, encode
from asof.study.diagnostic import load_synthetic_request
from asof.study.diagnostic_codec import bind_question
from asof.study.interpretation_generation import prepare_payload

CACHE = ROOT / "data/cache/r09-generation-corpus-extension-v1-20261028"
OLD = ROOT / "data/cache/r09-native-grammar-corpus-20261028/cases.json"
OLD_SHA = "01286d35689c7005ea67fa817c4b4098cecd05c4233c3949e7ec744bc5f5d97a"
SOURCE_PINS = {
    "src/asof/study/interpretation_grammar.py": "6ee02a55b41b59e3390f9a0c807ef168a646a355c646bde73621d75480ca3c97",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wire(document, ascii=False, escape_less=False):
    text = json.dumps(document, ensure_ascii=ascii, sort_keys=True, separators=(",", ":"))
    return (text.replace("<", "\\u003c") if escape_less else text).encode("utf-8")


def base(text="Invented inference."):
    return dict(answer_status="answered", abstention_reason=None, claims=[dict(
        kind="caution", limitations=["Invented development fixture; no science."],
        quote_refs=["Q0"], text=text,
    )], unresolved=[])


assert sha(OLD) == OLD_SHA
for name, digest in SOURCE_PINS.items():
    assert sha(ROOT / name) == digest
old_rows = json.loads(OLD.read_bytes())
assert len(old_rows) == 109
request = load_synthetic_request("synthetic-context")
known = encode(request)
known_text = ' \t\x00\x1b\x7f\u0085\u2028\u2029\ufeff\u200b\ufdd0\uffff\U0010ffff e\u0301 😀 <|im_end|> <|im_start|> " \\ \n '
known["source_request"]["evidence"][0]["statement"] = known_text
known["source_request"]["evidence"][0]["scientific_record"]["statement"] = known_text
known = bind_question(known["source_request"], known["question"]["question_id"])
variants = {"synthetic-context": request, "synthetic-known-literal-v1": known}
prepared = {name: prepare_payload(value, "asof_interpretation", 0, []) for name, value in variants.items()}
base_schema = canonical(prepared["synthetic-context"]["acceptance_schema"]).decode("utf-8")
assert all(row["schema_json"] == base_schema for row in old_rows)
assert hashlib.sha256(base_schema.encode()).hexdigest() == "a75dd967b16fd387da820e0bd90071aba511aee5363f700e9ac5849f8cc72911"
rows = []


def add(name, document, strict, grammar, *, schema=None, note, variant="synthetic-context", ascii=False, escape_less=False, raw=None):
    if schema is None:
        schema = strict
    payload = raw if raw is not None else wire(document, ascii, escape_less)
    assert isinstance(payload, bytes)
    payload.decode("utf-8")
    rows.append(dict(
        id=name, variant=variant, raw=payload,
        authored=dict(schema_accepted=schema, strict_accepted=strict,
                      generation_membership=grammar, rationale=note),
    ))


for count in (1800, 1801):
    for label, text, ascii_mode in (
        ("ascii", "x" * count, False),
        ("astral_raw", "😀" * count, False),
        ("astral_escaped", "😀" * count, True),
    ):
        add(f"text_{label}_{count}", base(text), count == 1800, count == 1800,
            ascii=ascii_mode, note="Logical decoded scalar bound, not UTF-8 or escape-byte count.")
for label, text, expected in (
    ("nonblank_at_end_1800", " " * 1799 + "x", True),
    ("nonblank_at_start_1800", "x" + " " * 1799, True),
    ("nonblank_at_middle_1800", " " * 899 + "x" + " " * 900, True),
    ("all_blank_1800", " " * 1800, False),
    ("nonblank_after_1800_spaces", " " * 1800 + "x", False),
    ("nonblank_before_1800_spaces", "x" + " " * 1800, False),
):
    add(label, base(text), expected, expected, note="Joint full-string length and at-least-one-nonblank constraint.")
for count in (512, 513):
    for label, char, ascii_mode in (("ascii", "r", False), ("astral_raw", "😀", False), ("astral_escaped", "😀", True)):
        doc = base()
        doc.update(answer_status="partial", abstention_reason=char * count)
        add(f"reason_{label}_{count}", doc, count == 512, count == 512,
            ascii=ascii_mode, note="Reason counts Unicode scalars, including paired escapes as one.")
for label, text, ascii_mode in (
    ("bmp_raw", "éα", False), ("bmp_escaped", "éα", True),
    ("controls_short", "\b\f\n\r\t", False),
    ("controls_unicode", "\x00\x1b\x7f", True),
    ("noncharacters_raw", "\ufdd0\uffff\U0010ffff", False),
    ("noncharacters_escaped", "\ufdd0\uffff\U0010ffff", True),
    ("zero_width_only", "\u200b", False), ("bom_only", "\ufeff", False),
    ("combining_boundary_1800", "e\u0301" * 900, False),
    ("combining_over_1800", "e\u0301" * 901, False),
):
    valid = label != "combining_over_1800"
    add(label, base(text), valid, valid, ascii=ascii_mode,
        note="Values are not normalized; controls/noncharacters/BOM/zero-width are scalar text.")
strip_chars = "".join(chr(cp) for cp in list(range(9, 14)) + list(range(28, 33)) + [133, 160, 5760] + list(range(8192, 8203)) + [8232, 8233, 8239, 8287, 12288])
add("all_strip_whitespace", base(strip_chars), False, False,
    note="Every explicit strip whitespace character, with no nonblank scalar.")
add("strip_whitespace_with_nonblank", base(strip_chars[:14] + "x" + strip_chars[14:]), True, True,
    note="Whitespace around a nonblank scalar remains part of the original value.")
for name, text in (("less_than", "<"), ("runtime_delimiter", "<|im_end|> <|im_start|>")):
    add(name + "_raw", base(text), True, False,
        note="Semantically valid, but raw less-than is outside the declared generation domain.")
    add(name + "_escaped", base(text), True, True, escape_less=True,
        note="Escaping less-than preserves the same decoded value inside the generation domain.")
add("less_than_uppercase_escape", None, True, True, raw=wire(base("<"), escape_less=True).replace(b"\\u003c", b"\\u003C"),
    note="Free text accepts both hex cases; decoded value is unchanged.")
for text, name in (("😀", "astral_uppercase_pair"), ("é", "bmp_uppercase_escape")):
    raw = wire(base(text), ascii=True)
    raw = raw.replace(b"\\ud83d\\ude00", b"\\uD83D\\uDE00").replace(b"\\u00e9", b"\\u00E9")
    add(name, None, True, True, raw=raw, note="Uppercase hex digits represent the same scalar(s).")
for name, text in (("quote_escape", '"'), ("backslash_escape", "\\"), ("solidus_escape", "/")):
    raw = wire(base(text))
    if name == "solidus_escape":
        raw = raw.replace(b'"text":"/"', b'"text":"\\/"')
    add(name, None, True, True, raw=raw, note="Valid JSON short escape, with one decoded scalar.")
for order in (("Q0", "Q1"), ("Q1", "Q0")):
    doc = base()
    doc["claims"][0]["quote_refs"] = list(order)
    add("refs_" + "_".join(order), doc, True, True, note="Both distinct ordered reference pairs remain allowed.")
doc = base()
doc["claims"][0]["quote_refs"] = ["Q0", "Q0"]
add("duplicate_refs", doc, False, False, note="Distinct-reference constraint belongs in grammar and strict validation.")
doc = base()
doc["claims"].append(copy.deepcopy(doc["claims"][0]))
add("duplicate_claim_text_post_only", doc, False, True, schema=True,
    note="Intentional exception: global claim-text uniqueness remains strict post-validation only.")
for label, escaped in (("high", b"\\ud800"), ("low", b"\\udfff"), ("reversed", b"\\udc00\\ud800")):
    raw = wire(base("PLACEHOLDER")).replace(b"PLACEHOLDER", escaped)
    add("unpaired_surrogate_" + label, None, False, False, schema="implementation_dependent_parse", raw=raw,
        note="Strict UTF-8 canonicalization rejects non-scalars; schema parser behavior recorded independently.")
raw = wire(base())
add("trailing_json_value", None, False, False, raw=raw + b"{}", note="Trailing extra JSON value is malformed.")
add("trailing_whitespace", None, True, False, raw=raw + b" \n", note="Strict/schema JSON permit trailing whitespace; compact generation domain does not.")
add("leading_whitespace", None, True, False, raw=b"\n " + raw, note="Strict/schema JSON permit leading whitespace; compact generation domain does not.")
add("duplicate_root_key", None, False, False, schema="implementation_dependent_parse",
    raw=raw.replace(b'"answer_status":"answered"', b'"answer_status":"answered","answer_status":"answered"'),
    note="Strict duplicate-key rejection; schema-library parsing disposition is recorded rather than assumed.")
add("duplicate_claim_key", None, False, False, schema="implementation_dependent_parse",
    raw=raw.replace(b'"kind":"caution"', b'"kind":"caution","kind":"caution"'),
    note="Exact field productions reject duplicate keys; JSON schema alone does not establish strict parsing.")
add("raw_control_invalid_json", None, False, False, raw=wire(base("PLACEHOLDER")).replace(b"PLACEHOLDER", b"\x00"),
    note="Unescaped C0 control is malformed JSON.")
add("alternative_root_key_order", None, True, False,
    raw=json.dumps(base(), ensure_ascii=False, separators=(",", ":")).encode(),
    note="Valid alternate JSON object order is outside the fixed sorted generation domain.")
known_doc = dict(answer_status="answered", abstention_reason=None, claims=[dict(
    kind="source_report", limitations=[], quote_refs=["Q0"], text=known_text,
)], unresolved=[])
add("known_literal_exact_safe", known_doc, True, True, variant="synthetic-known-literal-v1", escape_less=True,
    note="Fixed source variant: Unicode separators, controls, combining marks and delimiter text retain exact values.")
add("known_literal_raw_less_than", known_doc, True, False, variant="synthetic-known-literal-v1",
    note="Same decoded literal is semantically valid; raw less-than spelling is outside generation domain.")
add("known_literal_ascii_escaped", known_doc, True, False, variant="synthetic-known-literal-v1", ascii=True, escape_less=True,
    note="Equivalent alternate literal escapes remain strict/schema-valid but differ from the one declared known-literal spelling.")
known_wrong = copy.deepcopy(known_doc)
known_wrong["claims"][0]["quote_refs"] = ["Q1"]
add("known_literal_wrong_reference", known_wrong, False, False, variant="synthetic-known-literal-v1", escape_less=True,
    note="Exact source literal must remain paired with its own original quote ID.")

assert len({row['id'] for row in rows}) == len(rows)
CACHE.mkdir(exist_ok=False)
(CACHE / "documents").mkdir()
(CACHE / "variants").mkdir()
variant_records = {}
for name, value in variants.items():
    directory = CACHE / "variants" / name
    directory.mkdir()
    p = prepared[name]
    artifacts = {"request.json": value, "prepared.json": p, "payload.json": p["payload"],
                 "schema.json": p["acceptance_schema"], "grammar-artifact.json": p["generation_grammar"]}
    for filename, content in artifacts.items():
        (directory / filename).write_bytes(canonical(content))
    (directory / "grammar.gbnf").write_bytes(p["generation_grammar"]["grammar"].encode("utf-8"))
    variant_records[name] = {filename: dict(path=(directory / filename).relative_to(ROOT).as_posix(), sha256=sha(directory / filename))
                             for filename in tuple(artifacts) + ("grammar.gbnf",)}

oracle_cases, extension = [], []
for row in old_rows:
    oracle_cases.append(dict(id="legacy/" + row["id"], document_json=row["document_json"], schema_json=row["schema_json"]))
for row in rows:
    raw = row.pop("raw")
    path = CACHE / "documents" / (row["id"] + ".json")
    path.write_bytes(raw)
    entry = dict(row, document_path=path.relative_to(ROOT).as_posix(), document_sha256=sha(path), document_bytes=len(raw))
    extension.append(entry)
    oracle_cases.append(dict(id="extension/" + row["id"], document_json=raw.decode("utf-8"),
                             schema_json=canonical(prepared[row["variant"]]["acceptance_schema"]).decode("utf-8")))
(CACHE / "extension-cases.json").write_bytes(canonical(extension))
(CACHE / "oracle-cases.json").write_bytes(canonical(oracle_cases))
dependencies = json.loads((HERE.parent / "recovery-step9-interface-20261027/ORACLE-DEPENDENCIES.json").read_bytes())
old_report = json.loads((HERE.parent / "recovery-step9-native-grammar-20261028/CORPUS-PREPARATION.json").read_bytes())
for item in dependencies["assemblies"]:
    assert sha(item["path"]) == item["sha256"]
executable = Path(old_report["oracle_argv"][0])
oracle_script = Path(old_report["oracle_argv"][4])
assert sha(executable) == old_report["oracle_executable_sha256"]
assert sha(oracle_script) == old_report["oracle_script_sha256"]
pins = {path.relative_to(ROOT).as_posix(): sha(path) for path in CACHE.rglob("*") if path.is_file()}
code = [ROOT / name for name in SOURCE_PINS]
code += [ROOT / "src/asof/study/interpretation_generation.py", ROOT / "src/asof/study/interpretation_interface.py",
         HERE / "prepare_generation_corpus.py", HERE / "finite_gbnf_oracle.py", HERE / "CORPUS-EXTENSION-PROTOCOL.md"]
manifest = dict(schema_version=1, identity="generation-domain-extension-v1", status="frozen_before_oracles",
                cache=CACHE.relative_to(ROOT).as_posix(), original_corpus=dict(path=OLD.relative_to(ROOT).as_posix(), sha256=OLD_SHA, cases=109),
                extension_cases=len(extension), variants=variant_records, files=pins,
                source_pins={path.relative_to(ROOT).as_posix(): sha(path) for path in code},
                schema_same_as_original=True, schema_sha256=hashlib.sha256(base_schema.encode()).hexdigest(),
                oracle=dict(executable=str(executable), executable_sha256=sha(executable), script=str(oracle_script), script_sha256=sha(oracle_script),
                            dependencies=dependencies, maximum_children=1, timeout_seconds=120),
                native_conformance="unverified", execution_authorized=False, science="not attempted")
(CACHE / "FROZEN-INPUTS.json").write_bytes(canonical(manifest))
assert sha(OLD) == OLD_SHA
print(json.dumps(dict(status=manifest["status"], extension_cases=len(extension), old_cases=109,
                     cache=manifest["cache"], manifest_sha256=sha(CACHE / "FROZEN-INPUTS.json"))))
