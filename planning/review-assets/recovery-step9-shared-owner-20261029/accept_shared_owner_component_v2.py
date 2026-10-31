"""Root metadata/source acceptance of the frozen small pure lifecycle component."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "SHARED-OWNER-ROOT-SOURCE-SCOPE-v1.json": "4db8622f185edb1488a0066205b6248f0eb37b539e0806d04d748f277ea8e6ee",
    "SHARED-OWNER-ROOT-CORRECTION-SCOPE-v2.json": "298d42f4ab955513a1fe6a8a8cfdd70428199918d25e1147151d9c0fb3f37b48",
    "SHARED-OWNER-INTEGRATION-ACTUAL-EVIDENCE-FREEZE-v2.json": "071cb83afb207185715fe7df3d1403dbad765041c64ae33d8e96c9df56a2a4af",
    "SHARED-OWNER-INTEGRATION-ACTUAL-PROOF-v2.json": "14d78f96fbdb20e2c40e1884c278704f9da93b02c46cd502df87cf1f756698e3",
    "SHARED-OWNER-FIVE-REGRESSIONS-BEFORE-v2.json": "44eddebb07ef0a1e9a9c463881c67b585ca086febe173e914da1a5e790c63e4e",
    "SHARED-OWNER-AUTHOR-CONTROLS-PURE-PROOF-v2.json": "59240694c2153b4691ad113e69ebd16431511ebed92869e19fc2e793078e301f",
    "SHARED-OWNER-AUTHOR-SUPPLEMENT-PURE-PROOF-v2.json": "6532cf40eb19359c9dfdbcba4257413d9a77a512e84ddd87ac0e010907f5e1cf",
    "SHARED-OWNER-ADJACENT-IDENTITY-RETURN-AFTER-v2.json": "fa5981c865a4ac3fb5925e8927e637306c53e8d21e35cbda77a444d708257e93",
    "SHARED-OWNER-SOURCE-INDEPENDENT-HOLD-v1.json": "66b588bf4f077d7d876be73a6a7db6ded99c1bd7b688f03da1091e8472c72845",
}
PEER_NAME = "SHARED-OWNER-SOURCE-INDEPENDENT-PEER-v2.json"
PEER_SHA = "13b1e793e5275efa74ee0e0b98a8fd944d9ca5675657c1ccc1d888c0bc79453d"


def pin(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main():
    inputs = {}
    for name, expected in {**PINS, PEER_NAME: PEER_SHA}.items():
        inputs[name] = pin(HERE / name)
        assert inputs[name]["sha256"] == expected, name
    freeze = read("SHARED-OWNER-INTEGRATION-ACTUAL-EVIDENCE-FREEZE-v2.json")
    for record in freeze["pins"].values():
        path = Path(record["path"])
        assert path.resolve().parent == HERE
        observed = pin(path)
        assert observed == {"bytes": record["bytes"], "sha256": record["sha256"]}, path.name
    run = read("SHARED-OWNER-INTEGRATION-ACTUAL-PROOF-v2.json")
    assert run["status"] == "passed" and run["methods"] == 9
    assert run["histories_executed"] == run["histories_matched"] == 48
    assert run["snapshot_count"] == 372 and len(run["focused_observations"]) == 9
    assert run["actual_full48_fake_dispatches"] == 518 and run["actual_full48_marker_execs"] == 34
    assert not run["errors"] and not run["failures"] and not run["audit_denials"]
    assert all(value is True for value in run["source_unchanged"].values())
    assert all(value is False for value in run["qualification"].values())
    for name, count in (("SHARED-OWNER-AUTHOR-CONTROLS-PURE-PROOF-v2.json", 12), ("SHARED-OWNER-AUTHOR-SUPPLEMENT-PURE-PROOF-v2.json", 4)):
        controls = read(name)
        assert controls["status"] == "PASS" and controls["methods"] == count
    peer = read(PEER_NAME)
    assert peer["status"].startswith("CLEAR") and peer["material_blockers"] == []
    for expected in (PINS["SHARED-OWNER-INTEGRATION-ACTUAL-EVIDENCE-FREEZE-v2.json"], PINS["SHARED-OWNER-INTEGRATION-ACTUAL-PROOF-v2.json"]):
        assert expected in json.dumps(peer, sort_keys=True)
    chronology = freeze["chronology"]
    assert chronology["frozen48_oracle_predates_all_three_subject_implementations"]
    assert chronology["original_five_family_functional_witnesses_and_first48_failures_predate_fixes"]
    assert chronology["consolidated_focused_module_authored_after_v2_source"]
    assert chronology["consolidated_module_preregistered_or_pre_fix_authored"] is False
    inputs[Path(__file__).name] = pin(Path(__file__))
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_V2_SMALL_SHARED_OWNER_SOURCE_PURE_COMPONENT_ONLY",
        "inputs": inputs, "verified_evidence_freeze_pins": len(freeze["pins"]),
        "scope": "Actual new Python methods for one canonical fictional owner and two non-owning views, carrying original time/identity/early bytes/loader/output/journal through the48-history small cohort. No production or platform qualification.",
        "validation": {"histories": 48, "causal_groups": 14, "strict_snapshots": 372,
                       "full48_fake_original_dispatches": 518, "full48_actual_toy_body_executions": 34,
                       "full_suite_methods": 9, "focused_regression_methods": 8,
                       "focused_observations": 9, "author_controls": 12, "supplemental_controls": 4,
                       "independent_source_after_probes": 2,
                       "pure_suite_elapsed_seconds": run["elapsed_seconds"]},
        "fixed_boundaries": [
            "Permanent read-only issuing owner on a continuation and original Origin on its owner.",
            "Known normal wrapper return remains returned alongside a reported stop/original error.",
            "Known publication callback ACKs remain present in all four terminal projections after a late clock failure; completion is still vetoed.",
            "Known compiler returns enter observed-return names before eligibility checks; no late cache/acceptance is granted."
        ],
        "chronology": chronology,
        "preserved": "All initial sources,47/48 and11/12 results, original five-family witnesses, finite HOLD, drafts/literal versions and metadata-helper failures remain unchanged. The shared eight-test module is retrospective, not preregistered.",
        "limits": [
            "Only seven injected original-file operations and fictional output ACKs,209B inputs and N<=4/file<=4096/immutablecapture<=16384; real Win32/FFI/first-entry/full-source/production owner is not qualified.",
            "The raw-storage bound is payload arithmetic, not measured process memory. The0.359s class of pure tests does not establish original-file or integrated300-second feasibility.",
            "Snapshots and source-issued tested refs preserve ordinary immutable observations; this is not a hostile-Python security boundary.",
            "Journal byte/ACK-prefix consistency does not qualify a persisted hash-chain or future Unicode parent format; physical sink durability and isolated public8193-byte cap rejection remain unproven.",
            "No CPU/GGUF/native/model/tokenizer/original-source pass or old actual-run replay, new download, paid query or application dispatch change occurred."
        ],
        "next": "Retain a full-project20-row assessment and critically size/review the real full-roster/clock/FFI/source/journal/resource interfaces before any separate harmless physical qualification or new native protocol.",
        "actual_target_API_calls": 0, "old_original_payload_or_sourceclosure_operations": 0,
        "runtime_authorized": False, "FFI_registration_proven": False,
        "production_owner_bound": False, "originals_authenticated": False,
        "profile_qualified": False, "real_checkers_bound": False,
        "verification_complete": False, "scientific_validation": "not_established",
        "application_changed": False, "provider_spending": 0,
    }
    output = HERE / "SHARED-OWNER-SCOPED-ACCEPTANCE-v2.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "sha256": pin(output)["sha256"], "freeze_pins": result["verified_evidence_freeze_pins"]}))


if __name__ == "__main__":
    main()
