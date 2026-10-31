"""Narrow static two-closure delta peer; no transition/component execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def load(name):
    return json.loads((PHASE / name).read_text(encoding="utf-8"))


old = load("SHARED-OWNER-INTEGRATION-FIXTURES-v2.json")
data = load("SHARED-OWNER-INTEGRATION-FIXTURES-v3.json")
old_schema = load("SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json")
schema = load("SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json")
assert pin(PHASE / "SHARED-OWNER-INTEGRATION-FIXTURES-v3.json")["sha256"] == "e12d6485d0bc38b38c5b4bf33edcab22c1471da15858718185f18f1b5179eee2"
assert pin(PHASE / "SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json")["sha256"] == "34c3df0519df387e31439096b8c76e39fc3ce74437e1281346da58ab3a33952e"
assert pin(PHASE / "SHARED-OWNER-INTEGRATION-FIXTURES-v2.json")["sha256"] == "45b17a6c737d6dbd914557f698a74ed92bf18077a0d2b86864cec63b72d037c5"
assert pin(PHASE / "SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json")["sha256"] == "7ea6cb057c749e54a4fa557345ce00076fbd9b6b911eb7d767d9666fd7ddb0c8"
changed_schema_keys = sorted(k for k in old_schema.keys() | schema.keys() if old_schema.get(k) != schema.get(k))
assert changed_schema_keys == ["binding_override_rule", "check_paths", "check_relations", "expected_comparison", "step_error_policy"]
assert schema["check_relations"] == old_schema["check_relations"] + ["one_of"]
assert schema["bounds"] == old_schema["bounds"] and schema["case_exact_keys"] == old_schema["case_exact_keys"]
for key in ("baseline_binding_inputs", "frames_hex", "expected_baseline_serialized_rows", "common", "cohort",
            "public_schema", "public_schema_peer", "exception_inputs", "qualification"):
    assert old[key] == data[key], key
assert len(old["cases"]) == len(data["cases"]) == 48
status_additions, request_additions, old_checks = 0, 0, 0
changed_case_ids = []
cohort = load("SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json")
leaf_size = cohort["blobs"][0]["bytes"]
assert leaf_size == 58
for before, after in zip(old["cases"], data["cases"]):
    assert before["id"] == after["id"]
    assert {k: v for k, v in before.items() if k != "checks"} == {k: v for k, v in after.items() if k != "checks"}
    length = len(before["checks"])
    assert after["checks"][:length] == before["checks"]
    old_checks += length
    extra = after["checks"][length:]
    if extra: changed_case_ids.append(before["id"])
    failed = any(c["at"] == "final" and c["path"] == "pure_seam_complete" and c["relation"] == "eq" and c["value"] is False for c in before["checks"])
    status = dict(at="final", path="status", relation="one_of", value=["REFUSED", "INCOMPLETE"])
    expected = [status] if failed else []
    if failed: status_additions += 1
    if before["id"] == "short_read_attempt_exhaustion":
        known = 0
        for occurrence, rule in enumerate(before["binding_overrides"], 1):
            assert rule["api"] == "ReadFile" and rule["file_id"] == 0 and rule["occurrence"] == occurrence
            assert rule["actions"][1] == dict(hook="store_scalar", value=1)
            assert rule["actions"][2] == dict(hook="store_count", value=1)
            requested = min(65536, leaf_size - known)
            assert requested == 59 - occurrence
            expected.append(dict(at="final", path=f"$binding.ReadFile.0.{occurrence}.arguments.requested", relation="eq", value=requested))
            known += rule["actions"][2]["value"]
            request_additions += 1
        assert known == 17 and leaf_size - known == 41
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
    assert sorted(map(encode, extra)) == sorted(map(encode, expected)), before["id"]
assert (status_additions, request_additions) == (45, 17)
freeze_path = PHASE / "SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v3.json"
assert pin(freeze_path)["sha256"] == "69dd02e73654094ec746ff710f49efd6259f5fa1785616e66f5e5d97d2da428e"
freeze = load(freeze_path.name)
verified = []
for item in list(freeze["pins"].values()) + [freeze["freezer"]]:
    actual_path = Path(item["path"])
    assert actual_path.parent.resolve() == PHASE
    assert pin(actual_path) == item
    verified.append(item)
proof = load("SHARED-OWNER-INTEGRATION-LITERAL-PROOF-v3.json")
assert proof["status"] == "passed" and proof["methods"] == 8
assert proof["errors"] == proof["failures"] == []
assert proof["current_fake_dispatches"] == proof["actual_API_calls"] == 0
assert proof["toy_helpers_executed"] is False and proof["under_test_imported"] is False
prior_static = pin(PHASE / "SHARED-OWNER-LITERAL-INDEPENDENT-PROOF-v2.json")
assert prior_static["sha256"] == "7ba639ba9910693cf6b9b65124cc9533a46ba2a41122948b9eaed35f237d0052"
record = {
    "schema_version": 3, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "CLEAR_LITERAL_PREPARATION_ONLY", "reviewer": "/root/native_039_acceptance_audit",
    "scope": "Exact finite two-closure successor review, reusing the retained whole48 causal/static v2 review. No broad transition/test replay, component import, toy-helper execution or actual fake API dispatch.",
    "fixtures": pin(PHASE / "SHARED-OWNER-INTEGRATION-FIXTURES-v3.json"),
    "schema": pin(PHASE / "SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json"),
    "freeze": pin(freeze_path), "author_literal_proof": pin(PHASE / "SHARED-OWNER-INTEGRATION-LITERAL-PROOF-v3.json"),
    "author_delta_proof": pin(PHASE / "SHARED-OWNER-INTEGRATION-TWO-CLOSURE-DELTA-v3.json"),
    "prior_hold": pin(PHASE / "SHARED-OWNER-LITERAL-INDEPENDENT-PRECHECK-v2.json"),
    "prior_independent_static_proof": prior_static,
    "public_DATA_peer": pin(PHASE / "SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PEER-v2.json"),
    "checker": pin(Path(__file__).resolve()),
    "verified_metadata_pins": len(verified),
    "resolved_findings": [
        {"id": "independent_shortread_arguments", "result": "resolved", "detail": "Seventeen new checks read actual generic binding Spy arguments at the closed $binding path. Values58..42 derive only from frozen size58 and prior scripted defined1-byte counts. They do not read subject CallRef.requested to construct expected values. The18th read is still forbidden with41bytes remaining; aggregateR51 is not reused as a per-file quota."},
        {"id": "finalized_noncomplete_status_domain", "result": "resolved", "detail": "All45 noncomplete histories append strict one_of REFUSED|INCOMPLETE. ACTIVE and both complete statuses are excluded while every old status/causal assertion is retained."},
    ],
    "exact_delta": {"histories": 48, "groups": 14, "new_status_checks": status_additions,
                    "new_request_checks": request_additions, "old_checks_preserved": old_checks,
                    "changed_case_count": len(changed_case_ids), "changed_schema_keys": changed_schema_keys,
                    "all_steps_actions_frames_rawfacts_and_old_checks_unchanged": True,
                    "baseline21calls_27frames_53rows_209bytes_unchanged": True,
                    "no_source_API_or_Snapshot_field_added": True},
    "required_future_driver_rules": [
        "Normalize baseline blob-id/frame_id labels to canonical ordinal/frame only inside the harness; source hooks receive no case/fault labels or expected projections.",
        "Strictly validate all actual Snapshot/FinalResult nested keys, primitive types, domains and caps before expected comparisons; one_of uses strict type comparison.",
        "Retain unexpected dispatch attempts as violations before raising; do not hide them as0. Failed-prefix and original hard-cutoff monitors remain strict, with no callback admitted at/after hard_end.",
        "Identity and original exception objects are checked externally before token normalization; missing contexts cannot pass via None-is-None.",
    ],
    "material_blockers": [],
    "coverage_limits": [
        "Publication size/once-kind coverage is structural/future observed-payload SinkSpy only. Isolated8193/repeatedkind refusal is NOT exercised and no public publication API is introduced.",
        "MalformedN5/B3/M3/alias and foreign-owner/ref controls are honestly composite refusals, not isolated per-field predicates.",
        "The fictional journal tip covers retained acknowledged row bytes, not a persisted per-row hash chain or qualified runtime format.",
        "These are authored literal expectations; no shared-owner source component, loader/helper or fake binding has been run. The eight author methods and this review check preparation data only.",
    ],
    "next_gate": "Root may separately authorize only the planned three-source injected implementation and independent tests against this closed preparation. Actual FFI/Win32 capture, first-entry, production continuation/checkers, full resource fit, originals and runtime/profile remain separately gated.",
    "source_implementation_authorized_by_peer": False, "reviewed_components_imported_or_executed": 0,
    "toy_helpers_executed": False, "current_fake_dispatches": 0, "actual_target_API_calls": 0,
    "old_original_payload_or_source_closure_operations": 0,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "profile_qualified": False, "runtime_authorized": False,
}
out = PHASE / "SHARED-OWNER-LITERAL-INDEPENDENT-PEER-v3.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
md = """# Shared-owner literal v3: independent preparation peer

The exact two-point successor resolves the prior HOLD. No material blocker remains in the finite preparation review. It preserves all 48 histories, actions, frames, raw facts and old assertions; only 45 failed-final-status checks and 17 independent binding-request checks are appended.

Short-read requests are now explicitly 58 through 42, computed from the frozen 58-byte input and prior literal one-byte responses, never from the subject CallRef. All noncomplete finalized cases require REFUSED or INCOMPLETE. The existing 17-read quota still stops before an eighteenth dispatch with 41 bytes remaining.

The retained earlier peer independently reconstructed 21 baseline input call records, 27 frames and 53 serialized rows. Those inputs remain identical. The future driver must validate actual nested DATA types before comparisons, normalize transport labels only in the harness and retain unexpected dispatch attempts as violations without hiding counts. No component, helper, source loader or fake API was executed in this review.

Coverage stays limited: publication bounds are structural/future SinkSpy checks, not isolated 8193-byte or repeated-kind refusal; malformed limits and foreign-owner controls remain composite where declared. The fictional journal tip is not a persisted hash chain or qualified runtime format. Source implementation requires a separate root decision; all real FFI, source, production and profile gates remain pending.

- [Exact peer](SHARED-OWNER-LITERAL-INDEPENDENT-PEER-v3.json)
- [Closed literal freeze](SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v3.json)
- [Preserved prior HOLD](SHARED-OWNER-LITERAL-INDEPENDENT-PRECHECK-v2.json)
"""
md_path = PHASE / "SHARED-OWNER-LITERAL-INDEPENDENT-PEER-v3.md"
with md_path.open("x", encoding="utf-8", newline="\n") as stream: stream.write(md)
print(json.dumps({"status": record["status"], "json": pin(out), "md": pin(md_path)}, sort_keys=True))
