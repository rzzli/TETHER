"""Review the one-field unused-buffer literal correction, not core behavior."""
from pathlib import Path
import hashlib
import importlib.util
import json
from datetime import datetime, timezone

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def load(name):
    return json.loads((PHASE / name).read_text(encoding="utf-8"))


schema = load("ADOPTION-FIXTURE-SCHEMA-v3.json")
old_schema = load("ADOPTION-FIXTURE-SCHEMA-v2.json")
before, after = load("RAW-ADOPTION-FIXTURES-v2.json"), load("RAW-ADOPTION-FIXTURES-v3.json")
assert pin(PHASE / "ADOPTION-FIXTURE-SCHEMA-v3.json")["sha256"] == "1dfc199ced5a8f055cd82557b1f38defb5fa49d37b31e330e03d6c78f1dfc0ec"
assert pin(PHASE / "RAW-ADOPTION-FIXTURES-v3.json")["sha256"] == "37e3c0d614a5aaeca2125c05e8d94c42707d901e039c41ac02978bb23caacc64"
assert {k for k in schema.keys() | old_schema.keys() if schema.get(k) != old_schema.get(k)} == {"schema_version", "status", "expected_buffer_universe_rule"}
changed = []
for old, new in zip(before["cases"], after["cases"]):
    assert old["id"] == new["id"]
    if old == new: continue
    assert old["id"] == "conflicting_reserve_keeps_original"
    restored = json.loads(json.dumps(new))
    assert restored["expected"]["buffers"] == [{"generation": 0, "hex": "616263", "id": "buf0", "retained": True, "reusable": True}]
    assert restored["initial"]["buffers"] == [{"capacity": 3, "generation": 0, "hex": "616263", "id": "buf0"}]
    restored["expected"]["buffers"] = []
    assert restored == old
    changed.append(old["id"])
assert changed == ["conflicting_reserve_keeps_original"]
spec = importlib.util.spec_from_file_location("own_projection_only", PHASE / "check_raw_adoption_fixture_peer_v1.py")
own_checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(own_checker)
projection = own_checker.inspect("ADOPTION-FIXTURE-SCHEMA-v3.json", "RAW-ADOPTION-FIXTURES-v3.json")
freeze = load("RAW-ADOPTION-FIXTURE-FREEZE-v3.json")
assert pin(PHASE / "RAW-ADOPTION-FIXTURE-FREEZE-v3.json")["sha256"] == "f82b4ad090a4a669ba8568fabe7f9fbd856980ad1b07eecde3533edc2a148e58"
verified = []


def bind(value):
    if type(value) is dict:
        if set(value) == {"path", "bytes", "sha256"}:
            assert pin(Path(value["path"])) == value
            verified.append(value)
        else:
            for item in value.values(): bind(item)
    elif type(value) is list:
        for item in value: bind(item)


bind(freeze)
correction = pin(PHASE / "RAW-ADOPTION-LITERAL-CORRECTION-PROOF-v3.json")
assert correction["sha256"] == "734587b3feeb8bd89a85ee2000293e4ad152cb34c15d64904e4945c40c654710"
record = {
    "schema_version": 3, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "CLEAR_EXACT_ONE_FIELD_LITERAL_CORRECTION_ONLY",
    "reviewer": "/root/native_039_acceptance_audit",
    "scope": "Independent exact v2-to-v3 schema/data delta and structural projections only. This does not accept the separate core implementation or its current counter finding.",
    "schema": projection["schema"], "fixtures": projection["fixtures"],
    "freeze": pin(PHASE / "RAW-ADOPTION-FIXTURE-FREEZE-v3.json"),
    "author_correction_proof": correction,
    "prior_whole_fixture_peer": pin(PHASE / "RAW-ADOPTION-FIXTURE-INDEPENDENT-PEER-v2.json"),
    "checker": pin(Path(__file__).resolve()),
    "reused_projection_checker": pin(PHASE / "check_raw_adoption_fixture_peer_v1.py"),
    "projection": projection, "verified_freeze_pin_records": len(verified),
    "changed_case_ids": changed,
    "exact_change": "Only the already registered, unused buf0 is added to expected.buffers as retained/reusable. A rejected duplicate reservation neither references nor erases that buffer. The schema now explicitly includes every owner-registered buffer in the snapshot.",
    "all_32_step_streams_and_checkpoints_unchanged": True,
    "all_32_raw_record_and_counter_projections_unchanged": True,
    "other_31_cases_identical": True,
    "material_blockers": [], "actual_API_calls": 0,
    "adopter_implementation_imports_or_executions": 0,
    "old_payload_or_source_closure_operations": 0,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "profile_qualified": False, "runtime_authorized": False,
}
out = PHASE / "RAW-ADOPTION-FIXTURE-INDEPENDENT-PEER-v3.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
print(json.dumps(pin(out), sort_keys=True))
