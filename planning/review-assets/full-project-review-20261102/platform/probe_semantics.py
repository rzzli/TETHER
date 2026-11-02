"""Synthetic adversarial producer/verification probes, no biomedical inputs."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from asof.agents import ExtractiveBackend
from asof.artifacts import verify_run, write_run
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.scorer import ScorerArtifact
from asof.serde import canonical, decode, encode, fingerprint, read_json, write_json
from asof.workflow import run_workflow

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def main():
    output = []
    with tempfile.TemporaryDirectory(prefix="platform-semantic-", dir=ROOT / "data/cache") as name:
        scratch = Path(name)
        fixture = scratch / "fixture"
        shutil.copytree(ROOT / "src/asof/demo/v2", fixture)
        case = decode(Case, read_json(fixture / "case.json"))
        scorer = decode(ScorerArtifact, read_json(fixture / "scorer.json"))
        store = load_snapshot(fixture / "snapshot.json", case)
        result = run_workflow(case, store, ExtractiveBackend(), scorer)
        for label in ("failed", "biologically_absent", "invented_status"):
            coverage = encode(result.coverage)
            coverage["genetics"]["status"] = label
            changed = replace(result, coverage=coverage)
            target = scratch / label
            receipt_hash = write_run(target, changed, store, scorer)
            check = verify_run(target, receipt_hash)
            output.append(dict(probe="contradictory_coverage", category_status=label,
                               run_status=changed.status, probability=changed.prediction.probability,
                               finalized=True, verification=check["semantic_consistency"],
                               externally_anchored=check["external_anchor_checked"]))
        trace = encode(result.trace)
        for event in trace:
            if event["event"] == "review":
                event["details"]["selected"] = []
        previous = None
        for event in trace:
            event.pop("sha256", None)
            event["previous_sha256"] = previous
            event["sha256"] = previous = fingerprint(event)
        target = scratch / "selection_mismatch"
        receipt_hash = write_run(target, replace(result, trace=trace), store, scorer)
        check = verify_run(target, receipt_hash)
        output.append(dict(probe="selected_empty_but_claims_committed", claims=len(result.claims),
                           finalized=True, verification=check["semantic_consistency"],
                           externally_anchored=check["external_anchor_checked"]))
        target = scratch / "dossier_mismatch"
        write_run(target, result, store, scorer)
        with (target / "dossier.md").open("a", encoding="utf-8") as stream:
            stream.write("\nUnbound fictional assertion: all measurements are independently validated.\n")
        receipt = read_json(target / "receipt.json")
        receipt["outputs"]["dossier.md"] = hashlib.sha256((target / "dossier.md").read_bytes()).hexdigest()
        write_json(target / "receipt.json", receipt)
        receipt_hash = hashlib.sha256((target / "receipt.json").read_bytes()).hexdigest()
        check = verify_run(target, receipt_hash)
        output.append(dict(probe="dossier_prose_not_reconstructed", mutated_and_resealed=True,
                           verification=check["semantic_consistency"],
                           externally_anchored_to_mutated_receipt=check["external_anchor_checked"]))
    report = dict(schema_version=1, method="independent_synthetic_semantic_probes",
                  status="CONFIRMED_SEMANTIC_GAPS", probes=output,
                  limits="New synthetic producer fixtures only; not old-receipt forgery. Original external anchor would reject altered bytes. No retained scientific output mutated.")
    (HERE / "SEMANTIC-PROBES-BEFORE.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
