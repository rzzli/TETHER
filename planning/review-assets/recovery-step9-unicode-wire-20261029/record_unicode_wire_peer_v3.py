"""Incremental corrected design review, no pack/bridge/decoder implementation."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.absolute()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    paths = {name: HERE / name for name in ("UNICODE-WIRE-DESIGN-CONTRACT-v1.json", "UNICODE-WIRE-DESIGN-CONTRACT-v2.json",
        "UNICODE-WIRE-DESIGN-FREEZE-v1.json", "UNICODE-WIRE-DESIGN-FREEZE-v2.json", "UNICODE-WIRE-INDEPENDENT-DESIGN-REVIEW-v1.json")}
    pins = {name: pin(path) for name, path in paths.items()}
    assert pins["UNICODE-WIRE-DESIGN-CONTRACT-v2.json"]["sha256"] == "ddf9fd360d72def0b91bd99b047422bf8ee623c0f8d6e0ba73535e04a7af1abc"
    assert pins["UNICODE-WIRE-INDEPENDENT-DESIGN-REVIEW-v1.json"]["sha256"] == "f430969e8561472273bd8f06b088aad62d72e358cb90e3a711ba53085fe594f4"
    assert pins["UNICODE-WIRE-DESIGN-FREEZE-v2.json"]["sha256"].startswith("c127d1db")
    old = json.loads(paths["UNICODE-WIRE-DESIGN-CONTRACT-v1.json"].read_text(encoding="utf-8"))["semantic_contract"]
    current = json.loads(paths["UNICODE-WIRE-DESIGN-CONTRACT-v2.json"].read_text(encoding="utf-8"))
    s = current["semantic_contract"]
    assert hashlib.sha256(canonical(s)).hexdigest() == current["semantic_sha256"] == "9a313df2dca6632a0863f547322e1aeced26346a3ab709686f07c16623c714e3"
    changed = [key for key in s if s[key] != old[key]]
    assert changed == ["API_accounting", "case_row", "coverage", "event_order", "framing", "wire_size"]
    footer = s["wire_size"]["JSONL_buckets"]["footer"]
    assert footer == dict(bytes_each=8192, max_rows=16, maximum_bytes=131072)
    assert s["wire_size"]["failure_JSONL_bytes"] == 8192 and s["wire_size"]["failure_marker_file_bytes"] == 65536
    schedule = s["event_order"]["setup_events"]; schemas = s["event_order"]["setup_body_schemas"]
    names = set(s["API_accounting"]["names"])
    assert len(schedule) == 15 and len(schemas) == 11 and len(names) == 25
    previous = dict.fromkeys(names, 0)
    for row in schedule:
        schema = schemas[row["event"]]
        assert set(schema["exact_body_keys"]) == set(schema["fields"])
        assert set(row["body_selectors"]) <= set(schema["fields"])
        vector = row["cumulative_attempted_equals_returned"]
        assert set(vector) == names
        for name, value in vector.items():
            if name == "llama_vocab_is_eog" and value == "observed vocabulary_count nv": continue
            assert type(value) is int and previous[name] <= value <= s["API_accounting"]["hard_caps"][name]
        previous = vector
    assert all(value == 0 for value in schedule[0]["cumulative_attempted_equals_returned"].values())
    assert all(value == 0 for value in schedule[1]["cumulative_attempted_equals_returned"].values())
    typed = schedule[2]["cumulative_attempted_equals_returned"]
    assert {k: v for k, v in typed.items() if v} == dict(llama_model_default_params=1, llama_version=1)
    assert all(row["cumulative_attempted_equals_returned"] == typed for row in schedule[3:11])
    assert schedule[11]["cumulative_attempted_equals_returned"]["llama_backend_init"] == 0
    assert schedule[12]["cumulative_attempted_equals_returned"]["llama_backend_init"] == 1
    assert schedule[13]["cumulative_attempted_equals_returned"]["llama_model_load_from_splits"] == 0
    assert schedule[14]["cumulative_attempted_equals_returned"]["llama_model_load_from_splits"] == 1
    assert schedule[14]["cumulative_attempted_equals_returned"]["llama_vocab_is_eog"] == "observed vocabulary_count nv"
    defaults = schemas["typed_version_and_defaults_observed"]["fields"]["defaults"]["exact_typed_value"]
    effective = schemas["before_model_load_from_three_explicit_splits"]["fields"]["effective_params"]["exact_typed_value"]
    layout = schemas["exact_core_modules_loaded_exports_resolved"]["fields"]["layouts"]["exact_typed_value"]
    assert len(defaults) == len(effective) == 17 and sum(len(v) if type(v) is dict else 1 for v in layout.values()) == 31
    assert s["framing"]["native_state_fields"]["last_attempt"][0] is None
    assert s["framing"]["native_state_fields"]["last_return"][0] is None
    envelope = s["wire_size"]["fixed_case_sizing_envelope"]
    overhead = len(canonical(envelope)+b"\n")-sum(len(canonical(v)) for v in envelope["body"]["ledger"].values())
    assert overhead == 6408 < 8192
    assert len(s["framing"]["native_state_fields"]) == 45
    assert s["API_accounting"]["hard_caps"] == old["API_accounting"]["hard_caps"]
    assert s["bounds"] == old["bounds"] and s["corpus"] == old["corpus"] and s["pack"] == old["pack"]
    record = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="CLEAR_DESIGN_FOR_LITERAL_FRAMING_SPEC_AND_FIXTURES_ONLY_NOT_IMPLEMENTATION",
        artifacts=pins, semantic_sha256=current["semantic_sha256"], recorder=pin(Path(__file__)),
        changed_semantic_sections=changed,
        resolved_v1_findings=["Each of16footerJSONLrows<=8192; separatefailureFILE<=65536; no pooled64Krow",
            "Closed setupbody schemas and full cumulative25API vectors plus case/prefix/cleanup source-delta formulas",
            "Valid geometryQC/ledger retained despite nativeEOGdisagreement; nativeunknown/mismatch independently failsprofile",
            "ActualJSONnull API-name union and measured6408fieldmax envelope"],
        setup_closure=dict(occurrences=15, closed_body_families=11, API_entries_per_vector=25,
            typed_defaults=17, typed_effective_params=17, layout_leaves=31,
            module_inventory_setup_occurrences=4, extra_module_rows_authorized=False,
            limit="Inventories are nested arrays in those rows, plus batchfooter. Whole row mustfit8192 or explicitly fail; no universal64-module fit, silent split or extra row allocation."),
        zero_piece_accounting=dict(rule="N+count(piece length>1)",
            examples=[dict(lengths=[0,0,1], N=3, tokenize_calls=2, piece_calls=3),
                      dict(lengths=[0,2,1], N=3, tokenize_calls=2, piece_calls=4)],
            interpretation="AllNincludeszero-length tokens; capacity1needsretry only forpiece length>1. Full ledger is computed before ordinary grammar rejection; rejection at r changes apply/accept, not precomputed token/piece counts."),
        row_positions=dict(setup=15, cases=168, coverage=183, selection=184, normal_complete_rows="188+U<=192", reserved_max_rows=276),
        original_caps_preserved=True, counter_or_time_fit_claim=False,
        mandatory_literal_framing_gates=[
            "Freeze exact finite observation/failure reason/status enums and harness observationnull-versus-object shape; then bind the normative framing schema/fingerprint before implementation",
            "Literal fragments only: exact8byte magic/little-endian fields/ternary/null/lengths/IDs/truncation/trailing bytes; no full native pack builder",
            "Rows at/exceeding each8192/65536bucket and total quota; oversized repeated module inventories must fail instead of splitting/truncating",
            "Zero-piece/multi-byte required-size retries; before/result write-ack lag, all25stage deltas and45state types; partial/failed/pending native histories",
            "GeometryQCok versus token rejection/mixedEOG/nativeunknown, complete84scan, counts/firstselection/de-dup and no favorable filtering",
            "Failure before/after complete-looking rows, bounded JSONL/file diagnostics and primary/late/terminal veto DAG without self-hash cycle"],
        scope="Incremental design review only; no literal framing serializer/decoder, actual pack/bridge/parent or runtime implementation is approved by this peer.",
        material_blockers_for_next_design_fixture_stage=[],
        activity=dict(old_source_qualification=0, CPU_GGUF_oldpack_operations=0, native_SDK_compiler_OS_runtime_calls=0,
                      only_new_design_metadata_and_pure_arithmetic=True),
        execution_authorized=False, implementation_authorized=False, profile_qualified=False,
        scientific_validation="not_established", previous_negative_and_external_timeout_unchanged=True)
    raw = (json.dumps(record, indent=2, allow_nan=False)+"\n").encode("utf-8")
    path = HERE / "UNICODE-WIRE-INDEPENDENT-DESIGN-REVIEW-v2.json"
    with path.open("xb") as stream: stream.write(raw)
    print(json.dumps(pin(path)))


if __name__ == "__main__":
    main()
