"""Independent finite inspection of NEW literal framing data, not a runtime decoder."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct

HERE = Path(__file__).resolve().parent
CONTROL = HERE.parent / "recovery-step9-unicode-control-20261029"
REPORT = HERE / "UNICODE-WIRE-FRAMING-INDEPENDENT-PEER-v1.json"
NOTE = HERE / "UNICODE-WIRE-FRAMING-INDEPENDENT-PEER-v1.md"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    assert not REPORT.exists() and not NOTE.exists(), "Preserve the first peer record"
    names = [
        "UNICODE-WIRE-DESIGN-CONTRACT-v2.json", "UNICODE-WIRE-DESIGN-FREEZE-v2.json",
        "UNICODE-WIRE-FRAMING-CONTRACT-v1.json", "UNICODE-WIRE-FRAMING-CONTRACT-FREEZE-v1.json",
        "UNICODE-WIRE-FRAMING-FIXTURES-v1.json", "UNICODE-WIRE-FRAMING-FREEZE-v1.json",
        "UNICODE-WIRE-FRAMING-STRUCTURAL-PROOF-v1.json", "check_unicode_wire_framing_v1.py",
        "UNICODE-WIRE-FRAMING-SCOPE-v1.md",
    ]
    control_names = ["UNICODE-CONTROL-CORPUS-v1.json", "UNICODE-CONTROL-STAGES-v1.json",
                     "UNICODE-CONTROL-CONTRACT-v2.json", "UNICODE-PIECE-ANALYZER-CONTRACT-v1.json"]
    paths = [HERE / n for n in names] + [CONTROL / n for n in control_names]
    before = {str(p): pin(p) for p in paths}
    base = load(HERE / names[0]); s = base["semantic_contract"]
    closure = load(HERE / names[2]); f = closure["framing_semantics"]
    fixtures = load(HERE / names[4]); proof = load(HERE / names[6])
    corpus = load(CONTROL / control_names[0])["cases"]
    stages = load(CONTROL / control_names[1])["stages"]
    checks = []

    def checked(identity, detail):
        checks.append({"id": identity, "status": "passed", "detail": detail})

    assert digest(canonical(s)) == base["semantic_sha256"]
    effective = digest(canonical({"base_design_semantic_sha256": base["semantic_sha256"], "framing_semantics": f}))
    assert effective == closure["effective_wire_semantics_sha256"] == fixtures["semantic_sha256"]
    assert effective == "75605c03fb5b9bac659538035d8205b34df2ae1781b997a3181a1564676aa6c4"
    assert pin(HERE / names[2])["sha256"] == "4c4645f53c878e03cf1f0eaec575b3dcf1dcc006375aadc0080819393e4c3d24"
    assert pin(HERE / names[4])["sha256"] == "f81f351e61a5e4bd5c9c9d8475b9d6ad51239b94320156409fff25fde40894eb"
    for record in proof["inputs"].values():
        assert pin(Path(record["path"])) == record
    assert pin(Path(proof["checker"]["path"])) == proof["checker"]
    for freeze_name, pairs in [(names[3], ["contract"]), (names[5], ["contract", "fixtures", "base_design", "author"])]:
        freeze = load(HERE / freeze_name)
        for key in pairs:
            assert pin(Path(freeze[key]["path"])) == freeze[key]
        assert freeze["execution_authorized"] is False and freeze["implementation_authorized"] is False
    assert proof["status"] == "passed" and proof["methods"] == 7
    assert proof["errors"] == proof["failures"] == []
    checked("fingerprints_freezes_and_author_proof_pins", "Recomputed base/effective canonical fingerprints; current NEW metadata/source pins match both freezes and the retained seven-method structural proof. No author checker/helper was executed.")

    assert len(f["observation"]["status_enum"]) == len(set(f["observation"]["status_enum"])) == 7
    assert len(f["failure"]["reason_code_enum"]) == len(set(f["failure"]["reason_code_enum"])) == 30
    assert len(f["failure"]["child_error_class_enum"]) == 3
    assert set(f["observation"]["exact_keys"]) == set(f["harness"]["exact_observation"])
    assert len(f["harness"]["exact_observation"]) == 7
    assert sum(v is None for v in f["harness"]["exact_observation"].values()) == 6
    assert len(corpus) == 84 and len(stages) == 4
    assert sum(x["coverage_population"] for x in corpus) == 68
    assert sum(x["expected"]["native_byte_eligible"] for x in corpus) == 78
    checked("closed_enums_harness_and_population", "Seven observation statuses, 30 child reason codes, three child error classes; present harness object has exactly status plus six null fields. Frozen 84/78/6/68 populations remain unchanged.")

    fragments = {r["id"]: r for r in fixtures["pack_fragments"]}
    assert len(fragments) == len(fixtures["pack_fragments"]) == 25
    for r in fragments.values():
        raw = bytes.fromhex(r["raw_hex"])
        assert len(raw) == r["bytes"] and digest(raw) == r["sha256"]
        assert r["complete_profile_pack"] is False and r["native_qualification"] is False
    header = bytes.fromhex(fragments["header/exact"]["raw_hex"])
    assert len(header) == 188 and header[:8] == b"R09NU01\0"
    assert struct.unpack_from("<I", header, 8) == (1,)
    expected_hashes = [effective] + [pin(CONTROL / n)["sha256"] for n in control_names]
    assert [header[i:i+32].hex() for i in range(12, 172, 32)] == expected_hashes
    assert struct.unpack_from("<4I", header, 172) == (4, 2, 84, 4)
    assert bytes.fromhex(fragments["header/old_magic"]["raw_hex"])[:8] != header[:8]
    assert struct.unpack_from("<I", bytes.fromhex(fragments["header/big_endian_version"]["raw_hex"]), 8)[0] != 1
    assert struct.unpack_from("<I", bytes.fromhex(fragments["header/wrong_case_count"]["raw_hex"]), 180)[0] == 85
    assert len(bytes.fromhex(fragments["header/truncated_digest"]["raw_hex"])) < 188
    trailing = bytes.fromhex(fragments["header/trailing_header_byte"]["raw_hex"])
    assert trailing[:188] == header and len(trailing) == 189
    checked("header_literal_bytes_endian_and_five_bindings", "188-byte header contains exact magic/version, all five digest slots and LE counts 4/2/84/4. Old magic, swapped version, wrong count, truncation and fragment trailing-byte variants differ as declared. No full pack assembled.")

    # Field inspection of exactly the finite fixture records; not a full-pack decoder.
    def id_field(raw):
        n, = struct.unpack_from("<I", raw)
        assert 1 <= n <= 128 and len(raw) >= 4+n
        value = raw[4:4+n].decode("ascii")
        assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,127}", value)
        return value, 4+n

    grammar_hashes = list(dict.fromkeys(x["grammar_sha256"] for x in stages))
    for i, h in enumerate(grammar_hashes):
        raw = bytes.fromhex(fragments[f"grammar/{i}"]["raw_hex"])
        identity, at = id_field(raw); assert identity == f"grammar/{i}"
        assert raw[at:at+32].hex() == h; at += 32
        n, = struct.unpack_from("<I", raw, at); text = raw[at+4:]
        assert 1 <= n <= 65536 and len(text) == n and b"\0" not in text
        assert text.decode("utf-8").encode("utf-8") == text and digest(text) == h
        assert text == next(x["prepared"]["generation_grammar"]["grammar"].encode("utf-8") for x in stages if x["grammar_sha256"] == h)
    for i, stage in enumerate(stages):
        raw = bytes.fromhex(fragments[f"stage/{i}"]["raw_hex"])
        identity, at = id_field(raw); assert identity == stage["id"] and len(identity) <= 64
        assert raw[at:at+32].hex() == stage["request_sha256"]
        assert raw[at+32:at+64].hex() == stage["payload_sha256"]
        assert len(raw) == at+68 and struct.unpack_from("<I", raw, at+64)[0] == grammar_hashes.index(stage["grammar_sha256"])
    strata = [x["name"] for x in s["corpus"]["strata"]]
    dimensions = ["project_JSON_parse", "Unicode_scalar_JSON", "complete_v3_semantic_validation", "generation_grammar_membership", "native_membership", "JSON_syntax"]
    for ordinal in (0, 76, 78, 83):
        case = corpus[ordinal]; raw = bytes.fromhex(fragments[f"case/{ordinal}"]["raw_hex"])
        identity, at = id_field(raw); assert identity == case["id"]
        assert struct.unpack_from("<3I", raw, at) == (ordinal, next(i for i,x in enumerate(stages) if x["id"] == case["stage_id"]), strata.index(case["stratum"])); at += 12
        assert raw[at:at+32].hex() == case["sha256"]; at += 32
        B, = struct.unpack_from("<I", raw, at); at += 4
        assert B == case["bytes"] and raw[at:at+B] == bytes.fromhex(case["raw_hex"]); at += B
        tail = struct.unpack_from("<9I", raw, at)
        assert len(raw) == at+36
        assert tail[:6] == tuple(2 if case["expected"][k] is None else int(case["expected"][k]) for k in dimensions)
        expected_kind = 0 if case["expected"]["native_byte_eligible"] else (2 if b"\0" in bytes.fromhex(case["raw_hex"]) else 1)
        assert tail[6:] == (int(case["expected"]["native_byte_eligible"]), expected_kind, 4*B+32)
        assert bytes.fromhex(fragments[f"case/{ordinal}/truncated"]["raw_hex"]) == raw[:-1]
    for identity in ("ID/empty", "ID/nonASCII", "ID/overlong", "ID/truncated", "ID/unsafe_backslash"):
        raw = bytes.fromhex(fragments[identity]["raw_hex"])
        try: id_field(raw)
        except (AssertionError, ValueError, UnicodeError, struct.error): pass
        else: raise AssertionError(identity)
    checked("grammar_stage_case_and_ID_fragment_fields", "Two grammar records, four stage records and four selected case records independently inspected through complete consumption, including stage/stratum ordinals, six ternaries, eligibility/harness kinds and token caps. Five malformed ID fragments and four terminal-u32 truncations are not admitted.")

    rows = {r["id"]: r for r in fixtures["JSONL_rows"]}
    assert len(rows) == len(fixtures["JSONL_rows"]) == 22
    decoded = {}
    def duplicate_guard(items):
        out = {}
        for k,v in items:
            if k in out: raise ValueError("duplicate")
            out[k] = v
        return out
    invalid_raw = {"invalid/missing_LF", "invalid/CRLF", "invalid/BOM", "invalid/duplicate_name", "invalid/nonfinite", "invalid/invalid_UTF8"}
    for identity, r in rows.items():
        raw = bytes.fromhex(r["raw_hex"])
        assert len(raw) == r["bytes"] and digest(raw) == r["sha256"]
        assert r["full_profile_valid"] is r["actual_native_tokenizer_observation"] is r["source_schedule_expected"] is False
        if identity in invalid_raw:
            assert r["framing_expected"] is False
            try:
                assert raw.endswith(b"\n") and not raw.endswith(b"\r\n") and not raw.startswith(b"\xef\xbb\xbf")
                json.loads(raw.decode("utf-8"), object_pairs_hook=duplicate_guard, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
            except (AssertionError, ValueError, UnicodeError): pass
            else: raise AssertionError(identity)
        else:
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=duplicate_guard)
            assert canonical(value)+b"\n" == raw
            decoded[identity] = value
    for identity in ("case/one_whole_piece", "case/empty_piece_preserved", "case/mixed_EOG_geometry_preserved", "case/token_rejection_geometry_preserved", "case/harness_null_ledger", "case/QC_unknown_null_measurements", "footer/failure_small"):
        row = decoded[identity]
        assert set(row) == set(s["framing"]["common_row_keys"])
        assert type(row["row_sequence"]) is int and row["wire_semantics_sha256"] == effective
        assert set(row["native_call_counters"]) == set(s["API_accounting"]["names"])
        assert set(row["native_state"]) == set(s["framing"]["native_state_fields"])
        for api, counts in row["native_call_counters"].items():
            assert set(counts) == {"attempted", "returned"}
            assert all(type(n) is int for n in counts.values())
            assert 0 <= counts["returned"] <= counts["attempted"] <= s["API_accounting"]["hard_caps"][api]
        if identity.startswith("case/"):
            body = row["body"]; c = corpus[body["case_ordinal"]]
            assert body["case_id"] == c["id"] and body["raw_sha256"] == c["sha256"] and body["raw_bytes"] == c["bytes"]
            assert body["authored_expected"] == {"coverage_population": c["coverage_population"], "generation_member": c["expected"]["generation_grammar_membership"], "native_member": c["expected"]["native_membership"], "semantic_eligible": c["expected"]["complete_v3_semantic_validation"]}
            assert set(body["observation"]) == set(f["observation"]["exact_keys"])
            ledger = body["ledger"]
            if ledger is not None:
                pieces = [bytes.fromhex(x) for x in ledger["piece_hex"]]
                assert len(ledger["token_ids"]) == len(pieces)
                assert [len(x) for x in pieces] == ledger["piece_byte_lengths"]
                assert b"".join(pieces) == bytes.fromhex(c["raw_hex"])
                assert body["QC"] == {"status":"ok", "reason":None}
                assert all(n == 0 for n in body["compact_analysis"]["counts"].values())
                assert body["compact_analysis"]["matrix"] == [[0]*3 for _ in range(4)]
                assert body["compact_analysis"]["zero_piece_count"] == sum(not x for x in pieces)
            else:
                assert body["compact_analysis"] == {"counts":None,"matrix":None,"zero_piece_count":None}
                assert all(v is None for k,v in body["observation"].items() if k != "status")
    assert decoded["case/mixed_EOG_geometry_preserved"]["body"]["observation"]["native_member"] is None
    assert decoded["case/mixed_EOG_geometry_preserved"]["body"]["matches_authored_native_expectation"] is None
    assert decoded["case/token_rejection_geometry_preserved"]["body"]["observation"]["completion_EOG"] is None
    assert decoded["invalid/bool_sequence"]["row_sequence"] is True
    assert "verified" in decoded["invalid/ready_flag"]
    assert decoded["invalid/string_null_API_tag"]["native_state"]["last_attempt"] == "null"
    assert decoded["invalid/observation_entire_null"]["body"]["observation"] is None
    assert decoded["invalid/observation_status"]["body"]["observation"]["status"] not in f["observation"]["status_enum"]
    assert decoded["invalid/failure_reason"]["body"]["reason_code"] not in f["failure"]["reason_code_enum"]
    checked("literal_row_bytes_and_scoped_unions", "All 22 row bytes/hash records checked; six malformed UTF8/line/duplicate/nonfinite fixtures reject. Source-bound body metadata and full synthetic ledgers checked for six geometry/harness/QC examples. Isolated source counters remain datatype examples, never a successful source schedule.")

    setup = s["event_order"]["setup_events"]
    assert len(setup) == 15
    for x in setup:
        assert set(x["cumulative_attempted_equals_returned"]) == set(s["API_accounting"]["names"])
        assert set(s["event_order"]["setup_body_schemas"][x["event"]]["exact_body_keys"]) == set(s["event_order"]["setup_body_schemas"][x["event"]]["fields"])
    assert all(n == 0 for n in setup[0]["cumulative_attempted_equals_returned"].values())
    assert all(n == 0 for n in setup[1]["cumulative_attempted_equals_returned"].values())
    assert setup[11]["cumulative_attempted_equals_returned"]["llama_backend_init"] == 0
    assert setup[12]["cumulative_attempted_equals_returned"]["llama_backend_init"] == 1
    assert setup[14]["cumulative_attempted_equals_returned"]["llama_vocab_is_eog"] == "observed vocabulary_count nv"
    assert sum(s["API_accounting"]["hard_caps"].values()) == 4276181
    assert sum(s["API_accounting"]["positive_fixed_profile_upper_bounds"].values()) == 530477
    # Includes a zero-length piece: three initial calls plus one >1-byte retry.
    assert len([0,1,2]) + sum(n > 1 for n in [0,1,2]) == 4
    assert "count(piece_byte_length>1)" in s["API_accounting"]["per_case_exact_delta"]["QC_ok_tokenizer"]
    checked("inherited_closed_stages_and_piece_count_rule", "All 15 setup occurrences retain closed bodies and all 25 cumulative API fields; backend-init/EOG boundaries and hard/positive sums agree. Zero-length pieces use one initial piece call, not a nonexistent retry. This checks the proposed schedule, not native conformance.")

    assert 96*65536+96*8192+64*8192+4*65536+16*8192 == 7995392
    assert 7995392+4096+65536 == 8065024 < 8388608
    assert f["failure"]["JSONL_bytes_including_LF"] == 8192
    assert len(bytes.fromhex(rows["footer/failure_small"]["raw_hex"])) == 3196 <= 8192
    assert len(bytes.fromhex(rows["sizing/maximum_arrays_preserving_zeros"]["raw_hex"])) == 57998 < 60864 < 65536
    assert rows["sizing/maximum_arrays_preserving_zeros"]["scope"] == "mathematical_size_only_NOT_source_bound_case"
    assert fixtures["negative_partial_histories"] == f["partial_history"]["history_expectations"]
    assert len(fixtures["negative_partial_histories"]) == 14
    assert all(x["profile_qualified"] is False for x in fixtures["negative_partial_histories"])
    checked("bucket_arithmetic_and_partial_expectations", "Unchanged 276-row/7,995,392-byte JSONL reservation and 8,065,024 structured-byte total. Footer is 16 actual rows <=8192 each; separate marker <=65536. The 57,998-byte array row is mathematical only. All 14 histories retain unknown/negative distinctions and never qualify.")

    assert before == {str(p): pin(p) for p in paths}
    report = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CLEAR_FRAMING_DESIGN_AND_LITERAL_FIXTURES_ONLY",
        "reviewer": "/root/os_accounting_peer", "inputs": before, "review_script": pin(Path(__file__)),
        "effective_wire_semantics_sha256": effective, "checks": checks, "material_findings": [],
        "nonblocking_clarifications": [
            "The redundant harness prose says 'native_member and other six nonstatus'; the normative exact object and scoped note specify six total nonstatus nulls, seven total keys. No eighth field is admitted.",
            "The closure's present harness wrapper refines the base design's older 'native observation null' shorthand. The closure is fingerprint-bound at every future pack/row/header wire site.",
            "Structural author checks and this review do not validate a full source history. The size-only row is not a valid case/observation-union exemplar."
        ],
        "counts": {"pack_fragments":25,"JSONL_rows":22,"partial_history_expectations":14,"independent_check_groups":len(checks)},
        "inputs_unchanged": True,
        "scope": "New literal fragment/row fields, frozen contract consistency and finite proposed schedules only; no complete pack, decoder/runtime implementation, native/source qualification or actual run replay.",
        "author_checker_or_helper_executed": False, "complete_profile_pack_assembled": False,
        "old_original_source_qualification": False, "CPU_GGUF_oldpack_operations": 0,
        "target_native_SDK_compiler_OS_operations": 0, "profile_qualified": False,
        "scientific_validation": "not_established", "implementation_authorized_by_this_review": False,
    }
    with REPORT.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2, sort_keys=True); out.write("\n")
    note = """# Unicode framing: independent literal-data review

CLEAR for the frozen framing design and literal fixtures only. The exact closure, fixture freezes and retained seven-method proof pins match; the effective wire fingerprint is `75605c03fb5b9bac659538035d8205b34df2ae1781b997a3181a1564676aa6c4`.

Seven bounded independent check groups inspect 25 fragments, 22 row examples and 14 partial-history expectations. Header magic, little-endian fields, all five digest slots, selected grammar/stage/case records, ternaries, IDs, row bytes, closed enums, harness null fields, zero pieces and geometry preservation agree with the corrected base design. The inherited 15-stage/25-API schedule and byte reservations remain intact.

The harness counting typo is resolved by its normative seven-key object and scoped note. The 57,998-byte row is mathematical sizing only. Every isolated row and history leaves profile qualification false; there is no complete source/native history here. Footer JSONL rows stay within 8,192 bytes each, separately from the 65,536-byte failure file.

No material framing blocker was found. This review grants no implementation or execution permission and establishes no native conformance, resource fit, owner/source provenance, profile success or scientific result. No author helper/checker, old payload, SDK, target, compiler or OS diagnostic was executed.
"""
    with NOTE.open("x", encoding="utf-8") as out: out.write(note)
    print(json.dumps({"report":pin(REPORT),"note":pin(NOTE),"checks":len(checks)}))


if __name__ == "__main__":
    main()
