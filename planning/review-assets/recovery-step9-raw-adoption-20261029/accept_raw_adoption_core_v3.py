"""Root metadata acceptance of a frozen pure component; never invokes that core."""
from pathlib import Path
import ast
import hashlib
import json
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def pin(name):
    path = BASE / name
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def check_record(record):
    path = Path(record["path"])
    assert path.resolve().parent == BASE
    observed = pin(path.name)
    assert observed["bytes"] == record["bytes"], path.name
    assert observed["sha256"] == record["sha256"], path.name


def methods(name):
    tree = ast.parse((BASE / name).read_text(encoding="utf-8"))
    return {
        f"{item.name}.{method.name}": ast.dump(method, include_attributes=False)
        for item in tree.body if isinstance(item, ast.ClassDef)
        for method in item.body if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def main():
    freeze = read("RAW-ADOPTION-CORE-SOURCE-FREEZE-v3.json")
    check_record(freeze["source"])
    for record in freeze["inputs"].values():
        check_record(record)
    assert freeze["source"]["sha256"] == "f4fcae07926927f509f455b1b8e243cec2be8fdbc91fa710aacf14618e9b5bea"
    before, after = methods("raw_adoption_core_v2.py"), methods("raw_adoption_core_v3.py")
    assert before.keys() == after.keys()
    changed = sorted(k for k in before if before[k] != after[k])
    assert changed == ["Owner._component", "Owner.handoff", "Owner.raise_exception"]
    driver = read("RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v3.json")
    assert driver["status"] == "passed" and driver["methods"] == 19
    assert driver["all32_matched"] == 32 and len(driver["runs"]) == 32
    assert driver["checkpoint_count"] == 9 and driver["actual_snapshots"] == 320
    assert not driver["errors"] and not driver["failures"] and not driver["audit_denials"]
    assert driver["source_unchanged"] and driver["FFI_API_calls"] == driver["SDK_calls"] == 0
    own = read("RAW-ADOPTION-OWNER-CONTROLS-PROOF-v3.json")
    assert own["status"] == "PASS" and own["methods"] == 21
    assert not own["errors"] and not own["failures"] and own["source_unchanged"]
    before_regressions = read("RAW-ADOPTION-INDEPENDENT-THREE-REGRESSIONS-BEFORE-v3.json")
    assert before_regressions["status"] == "expected_before_failures"
    assert before_regressions["methods"] == 3 and len(before_regressions["failures"]) == 4
    assert not before_regressions["errors"] and not before_regressions["audit_denials"]
    fixture_peer = read("RAW-ADOPTION-FIXTURE-INDEPENDENT-PEER-v3.json")
    assert fixture_peer["status"] == "CLEAR_EXACT_ONE_FIELD_LITERAL_CORRECTION_ONLY"
    assert fixture_peer["other_31_cases_identical"]
    assert fixture_peer["all_32_step_streams_and_checkpoints_unchanged"]
    assert fixture_peer["all_32_raw_record_and_counter_projections_unchanged"]
    peer = read("RAW-ADOPTION-CORE-SOURCE-INDEPENDENT-PEER-v3.json")
    assert pin("RAW-ADOPTION-CORE-SOURCE-INDEPENDENT-PEER-v3.json")["sha256"] == "4bcb3d67f0458dd8aef7cf1dccbb942033dc8cd78c1e51140d863e20fde57c4e"
    assert peer["status"] == "CLEAR_SOURCE_PURE_INJECTED_CORE_ONLY"
    assert peer["material_blockers"] == []
    check_record(peer["source"])
    check_record(peer["independent_after"])
    for record in (driver, own, peer):
        for flag in ("runtime_authorized", "profile_qualified", "FFI_registration_proven", "production_owner_bound"):
            assert record.get(flag, False) is False, flag
    names = [
        "raw_adoption_core_v3.py", "RAW-ADOPTION-CORE-SOURCE-FREEZE-v3.json",
        "RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v3.json", "RAW-ADOPTION-OWNER-CONTROLS-PROOF-v3.json",
        "RAW-ADOPTION-INDEPENDENT-THREE-REGRESSIONS-BEFORE-v3.json",
        "RAW-ADOPTION-CORE-SOURCE-INDEPENDENT-PEER-v3.json",
        Path(peer["independent_after"]["path"]).name,
        "RAW-ADOPTION-CORE-SOURCE-INDEPENDENT-PEER-v2.json",
        "RAW-ADOPTION-SOURCE-INDEPENDENT-BEFORE-v2.json", "RAW-ADOPTION-WRAPPER-RETURN-BEFORE-v2.json",
        "RAW-ADOPTION-PREPARATION-AND-SOURCE-SCOPE-v2.json",
        "RAW-ADOPTION-FIXTURE-FREEZE-v3.json", "RAW-ADOPTION-FIXTURE-INDEPENDENT-PEER-v3.json",
        "RAW-ADOPTION-FIXTURES-v3.json", "ADOPTION-FIXTURE-SCHEMA-v3.json",
        "RAW-ADOPTION-LITERAL-CORRECTION-PROOF-v3.json",
        "RAW-ADOPTION-HOOK-IDENTITY-HARNESS-CORRECTION-v1.json",
        Path(__file__).name,
    ]
    result = {
        "schema_version": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_V3_PORTABLE_RAW_ADOPTION_SOURCE_PURE_ONLY",
        "scope": "Generic source-issued HARNESS_ONLY raw fact reservation, incremental reconciliation, buffer lifetime, once-only rights and same-object early-context handoff under fictional calls and clocks.",
        "inputs": {name: pin(name) for name in names},
        "verified_frozen_input_pins": len(freeze["inputs"]) + 1,
        "changed_v2_methods": changed,
        "owner_controls_methods": 21,
        "independent_driver_methods": 19,
        "histories": 32, "checkpoints": 9, "snapshots": 320,
        "same_regression_before_methods": 3, "same_regression_before_failures": 4,
        "fixture_correction": "Only the previously declared but unused buffer is included in that case's expected snapshot; the other31 cases and all step/raw/counter projections are unchanged. Test identity-map errors were corrected separately; source deadline/handoff guards were not relaxed.",
        "corrected_boundaries": [
            "Issued snapshot diagnostics are immutable while original exception identity remains available separately.",
            "Identity-query timeout retains its cause and same-Origin deadline; successful handoff advances event sequence once.",
            "Handoff checks current early-source liveness and close authority; failed, unknown and successful closes cannot become live leases.",
            "Injected fresh core-class exceptions latch by identity; already latched exact exceptions are not duplicated.",
            "A known wrapper return remains observed after a later stop, with stopped-call refusal and legal once-only cleanup."
        ],
        "preserved": "All earlier sources, unsuccessful runs, before proofs, limited reviews, HOLDs, fixture/harness candidates and author-helper failures remain immutable.",
        "limits": [
            "Portable source facts supplied after FFI conversion do not close the native-to-Python window or prove actual entered/returned observations.",
            "No actual14-export binding, real first-entry, shared bootstrap/controller owner, loader/journal/output continuation or full-roster/time fit is qualified.",
            "Harness capabilities/typed refs and same-object identities grant no serialized production readiness.",
            "Old known-v7 journal/archive policies do not qualify a future Unicode parent."
        ],
        "actual_API_calls": 0, "old_original_payload_or_source_closure_operations": 0,
        "runtime_authorized": False, "FFI_registration_proven": False,
        "production_owner_bound": False, "originals_authenticated": False,
        "profile_qualified": False, "scientific_validation": "not_established",
        "application_changed": False,
        "next": "Implement a concrete source-only shared-owner continuation seam with one Origin/registry/output/early-byte context/source loader/journal and bounded terminal sequence; separately qualify real FFI and first-entry later."
    }
    destination = BASE / "RAW-ADOPTION-CORE-SCOPED-ACCEPTANCE-v3.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "acceptance": pin(destination.name), "verified_frozen_input_pins": result["verified_frozen_input_pins"]}))


if __name__ == "__main__":
    main()
