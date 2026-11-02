"""Close the local naming checklist only after retained gates and pins agree."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    output = HERE / "RENAME-COMPLETION.json"
    if output.exists():
        raise RuntimeError("Completion record already exists; do not overwrite it")
    records = {}
    reports = {}
    for name in (
        "FRONTDOOR-NAMESPACE-INDEPENDENT-REVIEW-v2.json",
        "WHEEL-PEER-REVIEW-v1.json",
        "ISOLATED-INSTALLED-QUALIFICATION.json",
        "PAPER-RENAME-PEER-REVIEW.json",
        "PACKET-PEER-REVIEW.json",
        "FINAL-CURRENT-DOCS-QA-v1.json",
        "CI-STATIC-REVIEW-v1.json",
        "PRESERVATION-AND-PAPER-QA.json",
    ):
        raw = (HERE / name).read_bytes()
        data = json.loads(raw)
        if not data["status"].startswith("PASS") or data.get("unresolved_findings"):
            raise RuntimeError("Gate not passing: " + name)
        reports[name] = data
        records[name] = {"sha256": sha(raw), "bytes": len(raw), "status": data["status"]}
    checked = 0
    for name in ("FINAL-CURRENT-DOCS-QA-v1.json", "CI-STATIC-REVIEW-v1.json",
                 "FRONTDOOR-NAMESPACE-INDEPENDENT-REVIEW-v2.json"):
        for path, pin in reports[name]["subjects"].items():
            raw = (ROOT / path).read_bytes()
            if sha(raw) != pin["sha256"] or len(raw) != pin["bytes"]:
                raise RuntimeError("Reviewed subject changed: " + path)
            checked += 1
    structural_path = HERE / "STRUCTURAL-CHECK-FINAL.json"
    structural_raw = structural_path.read_bytes()
    structural = json.loads(structural_raw)
    if (structural["providers"], structural["datasets"]) != (83, 178):
        raise RuntimeError("Unexpected catalog counts")
    todo = ROOT / "TODO.md"
    before = todo.read_bytes()
    after = before
    for item in ("N05", "N06"):
        old = ("- [ ] " + item + " ").encode()
        new = ("- [x] " + item + " ").encode()
        if after.count(old) != 1:
            raise RuntimeError("Expected one pending naming task: " + item)
        after = after.replace(old, new, 1)
    for item in range(1, 7):
        if after.count((f"- [x] N{item:02d} ").encode()) != 1:
            raise RuntimeError("Naming checklist incomplete")
    result = {
        "schema_version": 1, "method": "tether.local_rename_completion.v1",
        "status": "PASS_LOCAL_TETHER_RENAME", "role": "evaluation_only",
        "agent_visible": False, "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "project": "TETHER",
        "expansion": "Target Evidence Tracking Harness for Evaluation and Reproducibility",
        "tether_version": "0.4.0", "compatibility_engine_version": "0.3.11",
        "retained_gates": records, "reviewed_subject_pins_rechecked": checked,
        "structural_check": {"sha256": sha(structural_raw), **structural},
        "todo_closure": {"before_sha256": sha(before), "after_sha256": sha(after),
                         "only_changes": ["N05 checkbox", "N06 checkbox"],
                         "authority": "FINAL-CURRENT-DOCS-QA-v1 pending_completion_allowance"},
        "checkpoint": "Timestamped local Git commit including this completion record",
        "hosted_execution": False, "scientific_validation": "not_established",
        "owner_declarations": "deferred", "author_acceptance": "pending",
        "submission_ready": False, "publication_authorized": False,
        "new_model_calls": 0, "new_provider_downloads": 0, "provider_spending_usd": 0,
        "unresolved_rename_findings": [],
    }
    todo.write_bytes(after)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "subject_pins": checked,
                      "completed_naming_tasks": 6, "record_sha256": sha(output.read_bytes())}))


if __name__ == "__main__":
    main()
