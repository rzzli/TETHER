"""Root acceptance of retained new-source evidence; does not import the subject."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
ALLOWED = {
    HERE,
    ASSETS / "recovery-step9-shared-owner-20261029",
    ASSETS / "recovery-step9-production-preflight-20261029",
}
EXPECTED = {
    "INDEXED-ACCOUNTING-SOURCE-PAUSE-v3.json": "8c0103972a4cd33365e0b642e8d9ae44981d6121a31d644cfc2e443c1f20390c",
    "INDEXED-ACCOUNTING-ACTUAL-EVIDENCE-FREEZE-v3.json": "2be26673ca6d3ca71c0025d0917538dc17f22d41523bbab37c906f22df4c2d58",
    "INDEXED-ACCOUNTING-INDEPENDENT-ACTUAL-PROOF-v3.json": "173bfdeba4a25bab32ac676c1af194805cd33dc847b2616e12f4ffa7a905d660",
    "INDEXED-ACCOUNTING-AUTHOR-CONTROLS-PURE-PROOF-v3.json": "80d93cc5a7d5f53229380b79c8d65d02d70130fa563a33acbaee0aaa900c9b91",
    "INDEXED-ACCOUNTING-AUTHOR-SUPPLEMENT-PURE-PROOF-v3.json": "a86d0da9642ef79a0432e50cea7a3f4d203824a29c3f367746daca06549bbe81",
}


def pin(path):
    assert path.resolve().parent in ALLOWED, str(path)
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--peer-name", required=True)
    parser.add_argument("--peer-sha256", required=True)
    args = parser.parse_args()
    assert Path(args.peer_name).name == args.peer_name
    evidence = {}
    for name, expected in {**EXPECTED, args.peer_name: args.peer_sha256}.items():
        evidence[name] = pin(HERE / name)
        assert evidence[name]["sha256"] == expected, name
    freeze = read("INDEXED-ACCOUNTING-ACTUAL-EVIDENCE-FREEZE-v3.json")
    assert len(freeze["inputs"]) == 31
    for record in freeze["inputs"].values():
        observed = pin(Path(record["path"]))
        assert observed == record, record["path"]
    run = read("INDEXED-ACCOUNTING-INDEPENDENT-ACTUAL-PROOF-v3.json")
    assert run["status"] == "passed" and run["methods"] == 15
    assert run["histories_executed"] == run["histories_matched"] == 48
    assert run["snapshot_count"] == 372
    assert run["actual_full48_fake_dispatches"] == 518 and run["actual_full48_marker_execs"] == 34
    assert not run["failures"] and not run["errors"] and not run["audit_denials"]
    assert len(run["method_outcomes"]) == 15 and all(row["status"] == "passed" for row in run["method_outcomes"])
    assert all(v is True for v in run["source_unchanged"].values())
    assert all(v is True for v in run["test_unchanged"].values())
    assert all(v is False for v in run["qualification"].values())
    assert run["actual_target_API_calls"] == run["original_payload_or_sourceclosure_operations"] == 0
    assert len(freeze["actual_hot_metrics"]) == 4
    for row in freeze["actual_hot_metrics"]:
        metric = row["metrics"]
        assert row["window"] == "clean_hot"
        assert metric["iterated_items"] == metric["membership_items"] == metric["slice_copied_items"] == 0
        assert metric["direct_index_items"] <= 16 and metric["len_calls"] <= 32
    assert len(freeze["explicit_canonical_report_metrics"]) == 18
    for row in freeze["explicit_canonical_report_metrics"]:
        assert row["window"] == "canonical_report_allowed"
        assert row["metrics"]["iterated_items"] == row["calls"]
    assert len(freeze["quarantine_checks"]) == 5
    for row in freeze["quarantine_checks"]:
        assert row["refused"] and row["original_primary_preserved"] and row["source_facts_and_progress_unchanged"]
        assert row["binding_dispatches"] == row["sink_callbacks"] == 0 and row["clock"] == 100
    for name, count in (("INDEXED-ACCOUNTING-AUTHOR-CONTROLS-PURE-PROOF-v3.json", 12), ("INDEXED-ACCOUNTING-AUTHOR-SUPPLEMENT-PURE-PROOF-v3.json", 4)):
        controls = read(name)
        assert controls["status"] == "PASS" and controls["methods"] == count
        assert len(controls["results"]) == count and all(row["passed"] is True for row in controls["results"])
    peer = read(args.peer_name)
    assert peer["status"].startswith("CLEAR") and peer["material_blockers"] == []
    peer_text = json.dumps(peer, sort_keys=True)
    for name in ("INDEXED-ACCOUNTING-ACTUAL-EVIDENCE-FREEZE-v3.json", "INDEXED-ACCOUNTING-INDEPENDENT-ACTUAL-PROOF-v3.json"):
        assert EXPECTED[name] in peer_text, name
    evidence[Path(__file__).name] = pin(Path(__file__))
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_V3_INDEXED_ACCOUNTING_SOURCE_PURE_N4_ONLY",
        "inputs": evidence, "verified_evidence_freeze_pins": 31,
        "validation": {"independent_methods": 15, "unchanged_histories": 48,
                       "same_regression_methods": 8, "precode_indexed_methods": 6,
                       "author_methods": 12, "supplemental_author_methods": 4,
                       "strict_snapshots": 372, "fake_dispatches_full48": 518,
                       "actual_toy_body_executions_full48": 34,
                       "hot_windows_without_global_scans": 4,
                       "one_pass_canonical_reports": 18, "quarantine_checks": 5,
                       "independent_pure_seconds": run["elapsed_seconds"]},
        "accepted": ["Canonical ordinal/file indices without hidden global hot-work traversal.",
                     "Raw-first, once-only read folding including defined zero and idempotent identical replay.",
                     "Fault quarantine after append/index/fold interruption; original facts and cleanup rights preserved.",
                     "One explicit O(N+r) reporting pass; reports cannot repair a failed cache or resume work."],
        "chronology": freeze["chronology"],
        "limits": freeze["limits"],
        "preserved": "All accepted V2 sources, first pre-code harness HOLD, before proofs and the unchanged 48/SAME8/PRECODE6 expectations. First coherent V3 passed without correction or rerun.",
        "next": "Role-aware metadata admission envelope, streaming/capture policy, query/call retention and bounded output design before any separately approved production profile or physical operation.",
        "application_changed": False, "application_tests_rerun": False,
        "provider_spending": 0, "actual_target_API_calls": 0,
        "original_payload_or_sourceclosure_operations": 0,
        "qualification": dict(run["qualification"]), "scientific_validation": "not_established",
    }
    destination = HERE / "INDEXED-ACCOUNTING-SCOPED-ACCEPTANCE-v3.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "sha256": pin(destination)["sha256"], "verified_pins": 31}))


if __name__ == "__main__":
    main()
