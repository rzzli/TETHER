"""Narrow independent literal-v2 delta/projection checks; no adopter exists here."""
import hashlib
import importlib.util
import json
from pathlib import Path

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def load(name):
    return json.loads((PHASE / name).read_text(encoding="utf-8"))


spec = importlib.util.spec_from_file_location("independent_literal_projection_v1", PHASE / "check_raw_adoption_fixture_peer_v1.py")
own_checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(own_checker)
projection = own_checker.inspect("ADOPTION-FIXTURE-SCHEMA-v2.json", "RAW-ADOPTION-FIXTURES-v2.json")
a, b = load("RAW-ADOPTION-FIXTURES-v1.json"), load("RAW-ADOPTION-FIXTURES-v2.json")
old_schema, schema = load("ADOPTION-FIXTURE-SCHEMA-v1.json"), load("ADOPTION-FIXTURE-SCHEMA-v2.json")
assert projection["schema"]["sha256"] == "b4b6670c71d08133670af0af357088447c452f0e973f179c07e69702f900ade5"
assert projection["fixtures"]["sha256"] == "09f79b6a5f7bca50a3da63f3d95a6041e8bc2acf84ec85f1db5d96a4e7c1d5f6"
assert {k for k in old_schema.keys() | schema.keys() if old_schema.get(k) != schema.get(k)} == {"schema_version", "initial_exact_keys", "namespace_state_rule", "defined_zero_scope"}
assert schema["initial_exact_keys"] == old_schema["initial_exact_keys"] + ["namespace_state"]
expected_changed = {"successful_defined_zero", "same_owner_early_handoff", "same_numeric_start_foreign_origin", "same_owner_second_handoff_rejected"}
changed = set()
aggregate = {k: 0 for k in schema["counter_exact_keys"]}
for old, new in zip(a["cases"], b["cases"]):
    assert old["id"] == new["id"]
    assert old["steps"] == new["steps"] and old["checkpoints"] == new["checkpoints"]
    old_initial, new_initial = old["initial"], dict(new["initial"])
    ns = new_initial.pop("namespace_state")
    assert old_initial == new_initial
    assert set(ns) == {"scope", "owner_ref", "output_ref", "namespace_owned", "reservation_ready"}
    assert ns["scope"] == "HARNESS_ONLY"
    assert ns["owner_ref"] == new_initial["current"]["owner"] and ns["output_ref"] == new_initial["current"]["output"]
    assert type(ns["namespace_owned"]) is bool and type(ns["reservation_ready"]) is bool
    assert not ns["reservation_ready"] or ns["namespace_owned"]
    has_early = new_initial["early_context"] is not None
    assert ns["namespace_owned"] is has_early and ns["reservation_ready"] is has_early
    old_expected, new_expected = old["expected"], new["expected"]
    fields = {k for k in old_expected if old_expected[k] != new_expected[k]}
    if fields: changed.add(old["id"])
    if old["id"] == "successful_defined_zero":
        assert fields == {"disposition", "primary_code"}
        assert new_expected["disposition"] == "primitive_complete" and new_expected["primary_code"] is None
        row = new_expected["records"][0]
        assert row["raw_scalar"] == {"tag": "BOOL32", "value": 1}
        assert row["raw_count"] == {"tag": "COUNT32", "value": 0}
        assert row["count_defined"] is True and row["count_state"] == "known_defined"
        assert new_expected["known_read_bytes"] == 0 and new_expected["read_count_unknown"] is False
    elif has_early:
        assert fields == {"namespace_owned", "reservation_ready"}
        assert new_expected["namespace_owned"] is True and new_expected["reservation_ready"] is True
    else:
        assert not fields
    assert old_expected["records"] == new_expected["records"]
    assert old_expected["counters"] == new_expected["counters"]
    for key, value in new_expected["counters"].items(): aggregate[key] += value
assert changed == expected_changed
freeze = load("RAW-ADOPTION-FIXTURE-FREEZE-v2.json")
assert pin(PHASE / "RAW-ADOPTION-FIXTURE-FREEZE-v2.json")["sha256"] == "bb83204db84c64941cad82c760396ce3bc8b91f1d7fd692c29c05a746b3c84ff"
bound = []


def visit(value):
    if type(value) is dict:
        if set(value) == {"path", "bytes", "sha256"}:
            assert pin(Path(value["path"])) == value
            bound.append(value)
        else:
            for child in value.values(): visit(child)
    elif type(value) is list:
        for child in value: visit(child)


visit(freeze)
shape = load("RAW-ADOPTION-LITERAL-SHAPE-PROOF-v2.json")
assert shape["status"] == "passed" and shape["methods"] == 6
assert shape["failures"] == [] and shape["errors"] == []
report = {
    "schema_version": 2, "status": "passed",
    "scope": "Independent literal/projection and exact v1-to-v2 delta inspection only; no raw-adopter behavior or real FFI tested.",
    "checker": pin(Path(__file__).resolve()),
    "reused_own_structural_checker": pin(PHASE / "check_raw_adoption_fixture_peer_v1.py"),
    "projection": projection, "changed_expected_case_ids": sorted(changed),
    "unchanged_step_streams": 32, "unchanged_checkpoints": 9,
    "unchanged_record_and_counter_projections": 32,
    "aggregate_counters": aggregate,
    "verified_freeze_pin_records": len(bound),
    "freeze": pin(PHASE / "RAW-ADOPTION-FIXTURE-FREEZE-v2.json"),
    "adopter_implementation_imports_or_executions": 0, "actual_API_calls": 0,
    "old_payload_or_source_closure_operations": 0,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "profile_qualified": False, "runtime_authorized": False,
}
out = PHASE / "RAW-ADOPTION-FIXTURE-INDEPENDENT-PROOF-v2.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": "passed", "proof": pin(out), "aggregate_counters": aggregate}, sort_keys=True))
