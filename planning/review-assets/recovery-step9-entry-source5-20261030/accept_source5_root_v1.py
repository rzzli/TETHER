"""Root retained-data acceptance for the narrow Source5 source/synthetic guard."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

BASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    proof_path = BASE / "NATIVE25-COMPONENT-PROOF-v5.json"
    peer_path = BASE / "SOURCE5-NATIVE25-INDEPENDENT-ACTUAL-REVIEW-v1.json"
    assert pin(proof_path)["sha256"] == "757e9a88c262f476d7744dc227a4aab752fca17e810589ced4f12e33654f5551"
    assert pin(peer_path)["sha256"] == "69d147429f4dd9ad8761abe3ee020227af7f1651a6b81a3dd3983e4ea2fc883d"
    proof = json.loads(proof_path.read_bytes())
    peer = json.loads(peer_path.read_bytes())
    assert peer["status"] == "CLEAR_ACTUAL_SOURCE5_43_COMPONENT_BRANCHES_ONLY"
    assert proof["status"] == "COMPONENT_OBSERVATIONS_PASSED_WITH_EXPLICIT_DEFERRED"
    assert proof["counts"] == dict(COMPONENT_PASS=43, DEFERRED_NOT_EXECUTED=4, STATIC_DECLARATION_ONLY=1)
    assert proof["setup_error"] is None and proof["evidence_error"] is None
    assert not proof["cooperative_deadline_late"] and not proof["changed_pins"] and not proof["audit_denials"]
    assert proof["evidence"]["persistence_complete"] is True
    freeze = json.loads((BASE / "NATIVE25-COMPONENT-FREEZE-v5.json").read_bytes())
    for selected in freeze["pins"].values():
        assert pin(Path(selected["path"])) == selected
    artifacts = proof["evidence"]["artifacts"]
    assert len(artifacts) == 188
    for selected in artifacts:
        actual = pin(Path(selected["path"]))
        assert all(actual[k] == selected[k] for k in ("path", "bytes", "sha256"))
    rows = {row["id"]: row for row in proof["rows"]}
    for name in ("scalar_kind_mismatch", "count_kind_mismatch"):
        row = rows["N25.5." + name]
        assert row["outcome"] == "COMPONENT_PASS" and not row["unexpected_source_returns"]
        assert len(row["expected_errors"]) == 1
        assert row["expected_errors"][0]["code"] == "NATIVE_STATE_NOT_REPRESENTABLE"
    selected_names = [
        "ENTRY-SOURCE-PAUSE-v5.json", "ENTRY-SOURCE-DELTA-v5.json",
        "NATIVE25-COMPONENT-FREEZE-v5.json", "SOURCE5-NATIVE25-INDEPENDENT-STATIC-REVIEW-v1.json",
        "SOURCE5-RESUME-STATIC-PIN-CHECK-v2.json", "NATIVE25-COMPONENT-EXECUTION-SCOPE-v5.json",
        "NATIVE25-COMPONENT-BINDING-v5.json", "NATIVE25-COMPONENT-ATTEMPT-v5.json",
        "NATIVE25-COMPONENT-PROOF-v5.json", "SOURCE5-NATIVE25-INDEPENDENT-ACTUAL-REVIEW-v1.json",
        "SOURCE5-NATIVE25-INDEPENDENT-ACTUAL-REVIEW-v1.md", "preflight_entry_kernel_v5.py",
    ]
    report = dict(
        schema_version=1, at_utc=datetime.now(timezone.utc).isoformat(),
        status="ACCEPTED_SOURCE5_API_AXIS_KIND_GUARD_SOURCE_SYNTHETIC_ONLY",
        evidence={name: pin(BASE / name) for name in selected_names},
        counts=proof["counts"], independent_retained_data_checks=1493,
        worlds=20, data_objects=26, snapshots=30,
        artifacts=dict(files=188, bytes=sum(p["bytes"] for p in artifacts)),
        retained_execution=dict(files=190, bytes=sum(p["bytes"] for p in artifacts) + pin(proof_path)["bytes"] + proof["attempt"]["bytes"]),
        elapsed_seconds=proof["elapsed_seconds"], call_gate=proof["call_gate"],
        accepted="Only the exact RawCallStore API/axis-kind guard and 43 unchanged source/synthetic controls. The two prior malformed-kind returns now refuse with preserved raw bytes.",
        history="Source4 controls31/12,38/5,41/2 and all original failures remain preserved. 244 other source functions/methods and predicates unchanged. Source4 E08/122 and C79 compiled fake scope unchanged; neither rerun.",
        qualification=dict(native25_complete=False, full_entry=False, native_C=False,
                           actual_Win32=False, native_bank=False, positive_lease=False,
                           physical14=False, real_roster=False, RSS=False, model=False,
                           scientific_validation=False, entire_project_complete=False),
        default_runtime="AsOf0.3.11/v2;327 application pins unchanged;1774 tests retained, not rerun",
        provider_spend_usd=0, downloader_or_monitor_changed=False,
        next_gate="Resolve bridge design findings B1-B4 and clarifications, then independently freeze positive native-bank/ticket expectations before source/build/execution.",
        timing_scope=proof["timing_scope"], root_activity="Metadata/hash/retained-proof checks only; no subject replay")
    output = BASE / "SOURCE5-ROOT-ACCEPTANCE-v1.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps(pin(output)))


if __name__ == "__main__":
    main()
