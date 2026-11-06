"""Close the bounded BG01-BG06 goal from pinned reviews and current documents.

This performs no experiment, model, source download, general verifier replay or
paid operation. It checks already-reviewed evidence and current navigation.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def proof(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def pinned_json(path, sha):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha, str(path)
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-review", type=Path, required=True)
    parser.add_argument("--data-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "closure output must be fresh"
    expected = {
        BASE/"requirements/VALIDATION.json": "6029192ef81e7a97d83546e44c4f08bb5be022deac6a6f0d046c6dbe1d766d4a",
        BASE/"requirements/REQUIREMENT-MATRIX.json": "7312fde15def688f41c273921defda940318a0725a5b2d6ce94dbd76d9ee9d01",
        BASE/"science/FINAL-AUDIT-CONFIRMATION.json": "52daff78b8d1300b536803015acab7c257d86e6b9bcb34292ae0ffbc02fb929f",
        args.data_review.resolve(): args.data_sha256,
    }
    reviews = {str(path): pinned_json(path, sha) for path, sha in expected.items()}
    requirement = reviews[str(BASE/"requirements/VALIDATION.json")]
    assert requirement["status"] == "PASS_BOUNDED_DOCUMENT_AND_RECORD_CHECKS"
    assert requirement["active_stage_blockers"] == []
    assert requirement["stage_requirements_complete"] == [f"BG{i:02d}" for i in range(1, 6)]
    matrix = reviews[str(BASE/"requirements/REQUIREMENT-MATRIX.json")]
    assert matrix["status"] == "PASS_REQUIREMENTS_REVIEW_WITH_EXPLICIT_LIMITATIONS"
    assert matrix["active_requirement_blockers"] == []
    assert matrix["active_stage_requirements_complete"] == [f"BG{i:02d}" for i in range(1, 6)]
    matrix_proof = proof(BASE/"requirements/REQUIREMENT-MATRIX.json")
    assert all(matrix_proof[key] == requirement["matrix"][key] for key in ("bytes", "sha256"))
    science = reviews[str(BASE/"science/FINAL-AUDIT-CONFIRMATION.json")]
    assert science["status"] == "PASS"
    audit = ROOT/"planning/TETHER Benchmark Goal Completion Audit 2026-11-06.md"
    assert proof(audit)["sha256"] == science["audit_sha256"]
    audit_review = requirement["final_goal_report_review"]
    assert audit_review["status"] == "PASS_REQUIREMENTS_AND_SCOPE_REVIEW"
    assert audit_review["new_active_requirement_blockers"] == []
    assert all(proof(audit)[key] == audit_review["report"][key] for key in ("bytes", "sha256"))
    data = reviews[str(args.data_review.resolve())]
    assert data["status"] == "pass_scoped_preservation", "preservation review must pass"
    assert data["unresolved_preservation_findings"] == data["actual_byte_hash_mismatches"] == 0
    assert data["checked_source_files_and_outputs_unchanged"] is True
    assert data["original_artifacts_modified"] is False and data["production_reexecution"] is False
    manifest = proof(Path(data["first_pass"]["path"]))
    assert all(manifest[key] == data["first_pass"][key] for key in ("bytes", "sha256"))
    todo = ROOT/"TODO.md"
    body = todo.read_text(encoding="utf-8")
    tasks = re.findall(r"^- \[([ x])\] (BG0[1-6])\b", body, re.M)
    assert len(tasks) == 6 and {task for _, task in tasks} == {f"BG{i:02d}" for i in range(1, 7)}
    assert all(mark == "x" for mark, _ in tasks), "unfinished active goal item"
    docs = [audit, todo, ROOT/"README.md", ROOT/"memory/MEMORY.md", ROOT/"memory/project-goals.md",
            ROOT/"memory/research-log-2026-11-06-benchmark-goal-complete.md",
            ROOT/"reports/TETHER benchmark comparison update 2026-11-06.md",
            ROOT/"planning/TETHER Inspect Comparison Results 2026-11-06.md"]
    links = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        assert "\u00e2\u20ac" not in text, f"encoding corruption: {doc}"
        for match in re.finditer(r"\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)", text):
            target = match.group(1) or match.group(2)
            if target.startswith(("https://", "http://", "#")):
                continue
            clean = re.sub(r":\d+$", "", unquote(target.split("#", 1)[0]))
            resolved = (doc.parent/clean).resolve()
            assert resolved.exists(), f"broken current link: {doc} -> {target}"
            links.append({"source": str(doc), "target": str(resolved)})
    bg05 = ROOT/"planning/review-assets/tether-inspect-20261106/stage/STAGE-ACCEPTANCE-02.json"
    assert all(proof(bg05)[key] == requirement["current_bg05_acceptance"][key] for key in ("bytes", "sha256"))
    acceptance = json.loads(bg05.read_bytes())
    assert acceptance["status"] == "pass" and acceptance["count"] == 60 and acceptance["local_links"] == 34
    for item in acceptance["pins"]:
        assert all(proof(Path(item["path"]))[key] == item[key] for key in ("bytes", "sha256")), item["path"]
    result = {"schema_version": 1, "status": "pass", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "active_goal_tasks": dict((task, "completed") for _, task in tasks),
              "unresolved_active_goal_blockers": [], "current_document_links": len(links),
              "distinct_current_link_targets": len({item["target"] for item in links}),
              "links": links, "review_pins": [proof(path) for path in expected],
              "current_document_pins": [proof(path) for path in docs], "bg05_acceptance": proof(bg05),
              "validator": proof(Path(__file__).resolve()),
              "checkpoint_before_final_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "scope": "Bounded five-stage goal and final documentation audit. Earlier test counts retain original code/version scope. No new experiment or whole biological raw/model inventory check.",
              "scientific_success": False, "full_inspect_production_equivalence": False,
              "whole_clinical_project_complete": False, "submission_ready": False,
              "remaining_separate_work": ["stronger semantic answering and source acquisition experiments", "full runtime migration if justified", "clinical/MR/scoring/T2-T5/H6 and competitor studies", "owner-deferred author facts and publication acceptance"]}
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "pass", "active_tasks": 6, "current_links": len(links),
                      "distinct_targets": result["distinct_current_link_targets"]}))


if __name__ == "__main__":
    main()
