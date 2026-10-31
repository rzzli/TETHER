"""Data/text-only QA; no runtime helper imports or API/process calls."""
from __future__ import annotations
import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(r"D:\Projects\drug_target_agents")
PHASE = ROOT / "planning/review-assets/recovery-step9-native-recognition-20261028"
DOC = ROOT / "planning/Project Progress Reassessment 2026-10-28 - ABI Module Policy.md"
RUN = ROOT / "data/cache/r09-detached-ABI-observation-v2-20261028T233241Z"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    text = DOC.read_bytes().decode("utf-8", errors="strict")
    assert not text.startswith("\ufeff") and "\ufffd" not in text
    rows = re.findall(r"^\| (R\d\d|HR[1-4]) \|", text, re.M)
    assert rows == [f"R{i:02d}" for i in range(1, 17)] + [f"HR{i}" for i in range(1, 5)]
    gates = re.findall(r"^([1-6])\. \*\*", text, re.M)
    assert gates == list("123456")
    links = []
    for label, target in re.findall(r"\[([^\]]+)\]\((<[^>]+>|[^)]+)\)", text):
        target = target.strip("<>")
        assert not target.startswith(("http:", "https:")), "No external facts require web QA here"
        path = (DOC.parent / target.split("#", 1)[0]).resolve()
        assert path.is_file(), (label, str(path))
        links.append({"label": label, "target": str(path)})
    report = load(RUN / "parent-report.json")
    observations = report["terminal_observation"]["observations"]
    job = observations["job_snapshot"]
    assert job["raw"] == job["value"] == report["final_job_snapshot"]
    assert job["predicate"] == "passed" and job["raw_publication"] == "returned"
    assert job["ordinal"] == 4 and job["problem"] is None
    memory = observations["memory_limits_and_peaks"]
    assert memory["value"] == report["memory_limits_and_peaks"]
    drain = observations["capture_drain"]
    assert drain["stderr"] == {"calls": [], "eof": True, "polls_reserved": 0, "status": "already_observed_EOF"}
    assert drain["stdout"]["eof"] is True and drain["stdout"]["polls_reserved"] == 1
    assert len(drain["stdout"]["calls"]) == 1
    call = drain["stdout"]["calls"][0]
    assert call["value"] is None and drain["stdout"]["status"] == "observed_pipe_EOF"
    terminal = report["terminal_observation"]
    for item in (job, memory, call):
        assert item["attempt_reserved"] is item["call_attempted"] is item["return_observed"] is True
        assert item["status"] == "returned"
        assert terminal["started_at"] <= item["started_at"] <= item["returned_at"] <= terminal["ended_at"] < terminal["work_deadline"]
    events = [json.loads(x) for x in (RUN / "execution/journal.jsonl").read_text().splitlines()]
    reservations = [e["details"] for e in events if e["event"] == "detached_ABI_terminal_call_reserved"]
    assert len(reservations) == 3
    protocol = load(RUN / "effective-protocol.json")
    wanted = {p["path"] for p in protocol["inputs"]} | {
        str(PHASE / "DETACHED-ABI-OBSERVATION-PROTOCOL-v2.json"), str(RUN / "effective-protocol.json")}
    assert len(wanted) == 204
    assert {x["path"] for x in report["lease_ownership"]} == wanted
    assert {x["path"] for x in report["final_input_recheck"]["outcomes"]} == wanted
    expected = {
        PHASE / "DETACHED-ABI-V2-RESULT-VERIFICATION.json": "4b2a3cd7b09c14a8dc3d444ea6e815c8fefeeb9952cfa9724615af77769e9c24",
        PHASE / "TYPED-ABI-BUILD-V4-RESULT-VERIFICATION.json": "48535ac53123db5246c95b7d7ed9211695531e687346e9854ca98d5c51d17473",
        ROOT / "planning/review-assets/recovery-step9-generation-contract-20261028/acceptance.json": "491feb0f5fbeefb9df841de46d104b160e3ad4832241b449115037b79961070b",
        ROOT / "planning/Project Progress Reassessment 2026-10-28 - ABI Export Failure.md": "274c0f56a8c797596db45ff1bcf932831b272161ab2b7e932b3ef49fce3de71e",
    }
    evidence = []
    for path, expected_sha in expected.items():
        assert sha(path) == expected_sha, str(path)
        evidence.append({"path": str(path), "sha256": expected_sha})
    md = PHASE / "DETACHED-ABI-V2-RESULT-VERIFICATION.md"
    mdtext = md.read_bytes().decode("utf-8", errors="strict")
    assert "unapproved_non_native_module" in mdtext
    result = {
        "schema_version": 1, "status": "passed",
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "assessment": {"path": str(DOC), "bytes": DOC.stat().st_size, "sha256": sha(DOC)},
        "verification_markdown": {"path": str(md), "sha256": sha(md)},
        "checker": {"path": str(Path(__file__)), "sha256": sha(Path(__file__))},
        "UTF8": "strict, no BOM/replacement characters", "status_rows": rows,
        "ordered_next_gates": 6, "local_links_checked": links,
        "evidence_pins": evidence,
        "supplemental_actual_result_checks": {
            "terminal_job_raw_value_final_report_equal": True,
            "terminal_limits_value_final_report_equal": True,
            "all_three_returned_observations_within_reserved_deadline": True,
            "EOF_call_and_already_observed_EOF_reconciled": True,
            "exact_204_input_protocol_paths_equal_lease_and_recheck_paths": True},
        "activity": {"actual_children": 0, "SDK_or_target_API_calls": 0,
                     "native_loads": 0, "GGUF_reads": 0, "protected_payload_reads": 0},
        "limitations": "Text/evidence QA, not a new framework test or scientific/native qualification."
    }
    out = PHASE / "ABI-MODULE-POLICY-REASSESSMENT-QA.json"
    with out.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps({"status": "passed", "rows": len(rows), "gates": 6, "links": len(links),
                      "document_sha256": sha(DOC), "QA_sha256": sha(out), "verification_MD_sha256": sha(md)}))


if __name__ == "__main__":
    main()
