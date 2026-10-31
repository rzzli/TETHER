"""Final checkpoint QA: byte hashes, retained reports and current documentation."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tomllib
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = HERE / "FINAL-CHECK.json"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    assert not OUTPUT.exists()
    acceptance_path = HERE / "acceptance.json"
    expected = "491feb0f5fbeefb9df841de46d104b160e3ad4832241b449115037b79961070b"
    assert sha(acceptance_path) == expected
    acceptance = json.loads(acceptance_path.read_bytes())
    assert acceptance["status"] == "accepted_pure_generation_contract_engineering_only"
    assert acceptance["tests"] == dict(run=1774, failures=0, errors=0, skipped=[])
    assert acceptance["entire_project_complete"] is False
    assert acceptance["new_v3_execution_authorized"] is False
    assert acceptance["native_conformance"] == "unverified"
    evidence = acceptance["evidence_files"]
    assert len(evidence) == 2418
    # All content is hashed as bytes. In particular, protected payloads are never
    # decoded by this audit, and GGUF/model file access is not permitted.
    for name, expected_pin in evidence.items():
        path = Path(name) if Path(name).is_absolute() else ROOT / name
        assert path.suffix.lower() != ".gguf"
        assert sha(path) == expected_pin["sha256"]
        assert path.stat().st_size == expected_pin["bytes"]
    assert len(acceptance["source_pins"]) == 327
    for name, digest in acceptance["source_pins"].items():
        assert sha(ROOT / name) == digest
    assert tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"] == "0.3.11"
    assert len(acceptance["protected_hash_only_checks"]) == 2
    assert not (ROOT / "data/cache/r09-generation-frozen-completion-20261028/failure.json").exists()
    assert sha(HERE / "FROZEN-VERIFIER-CHECKS.json") == "c780b0643756aa3006c25cb3a01a0066bcc38cc3d603f9285c53754786848e50"
    assert acceptance["matching_verifiers"] == 10
    assert acceptance["matching_verifier_qualification"]["retained_successes"] == 7
    assert acceptance["matching_verifier_qualification"]["declared_completion_successes"] == 3

    documents = [
        ROOT / "README.md", ROOT / "CHANGELOG.md", ROOT / "TODO.md",
        ROOT / "docs/INTERPRETATION_GENERATION.md", ROOT / "docs/NATIVE_INTERPRETATION.md",
        ROOT / "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
        ROOT / "planning/Recovery Status and Next Gates 2026-10-26.md",
        ROOT / "planning/Project Progress Reassessments.md",
        ROOT / "planning/Project Progress Reassessment 2026-10-28 - R09 Generation.md",
        ROOT / "memory/MEMORY.md", ROOT / "memory/project-goals.md",
        ROOT / "memory/research-log-2026-10-28-r09-generation-acceptance.md",
    ] + [HERE / name for name in (
        "CLOSEOUT.md", "COMPLETION-ATTEMPT-DISPOSITION.md",
        "AMENDMENT-3-OPTIONAL-ENVIRONMENT-CACHES.md", "BYTECODE-SERIALIZATION-NOTE.md",
        "PUBLICATION-CORRECTION.md", "NEXT-GATE-CRITICAL-REVIEW.md",
        "NATIVE-RECOGNIZER-REQUIREMENTS.md", "SCHEMA-ORACLE-DISPOSITION.md",
    )]
    document_hashes, local_links, external_links = {}, 0, 0
    for path in documents:
        text = path.read_text(encoding="utf-8")
        document_hashes[path.relative_to(ROOT).as_posix()] = sha(path)
        for match in re.finditer(r"\[[^\]]*\]\((<[^>]+>|[^)]+)\)", text):
            target = match.group(1).strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            else:
                target = re.split(r'\s+"', target, maxsplit=1)[0]
            if target.startswith(("https://", "http://", "mailto:", "#")):
                external_links += 1
                continue
            target = unquote(target.split("#", 1)[0])
            target = re.sub(r":\d+$", "", target)
            resolved = Path(target) if Path(target).is_absolute() else path.parent / target
            assert resolved.exists(), f"Missing link in {path}: {target}"
            local_links += 1
    assessment = documents[8].read_text(encoding="utf-8")
    assert set(re.findall(r"^\| (R\d\d) ", assessment, re.M)) == {f"R{i:02d}" for i in range(1, 17)}
    assert set(re.findall(r"^\| (HR\d) ", assessment, re.M)) == {f"HR{i}" for i in range(1, 5)}
    todo = (ROOT / "TODO.md").read_text(encoding="utf-8")
    assert "- [x] R09 pure v3 generation contract accepted as 0.3.11" in todo
    assert "- [ ] R09 Implement minimal interpretation" in todo
    assert "- [ ] R10 Complete the timed independent human development pilot." in todo
    assert "- [x] Reassess full project after pure 0.3.11 acceptance:" in todo
    for name in ("GENERATION-ASSESSMENT-QA.json", "ACCEPTANCE-PUBLICATION-V5-RESULT.json"):
        value = json.loads((HERE / name).read_bytes())
        assert value["status"].startswith("passed")
    # Recheck the final anchor after metadata and documentation work.
    assert sha(acceptance_path) == expected
    report = dict(schema_version=1, at_utc=datetime.now(timezone.utc).isoformat(),
                  status="passed", milestone="accepted_pure_generation_engineering_only",
                  version="0.3.11", acceptance_sha256=expected, evidence_files_checked=2418,
                  unchanged_source_pins=327, protected_hash_only_files=2,
                  protected_payloads_decoded=False, current_documents=len(documents),
                  local_links_checked=local_links, external_links_not_rechecked=external_links,
                  document_hashes=document_hashes, recovery_rows=16, human_gate_rows=4,
                  original_primary_attempt="failed_preserved", matching_preserved_versions=10,
                  entire_R09_complete=False, entire_project_complete=False,
                  native_conformance="unverified", scientific_validation="not_established",
                  new_model_native_or_dataset_calls=0, full_suite_rerun_for_prose=False)
    with OUTPUT.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in (
        "status", "version", "evidence_files_checked", "unchanged_source_pins",
        "current_documents", "local_links_checked", "entire_project_complete")}))


if __name__ == "__main__":
    main()
