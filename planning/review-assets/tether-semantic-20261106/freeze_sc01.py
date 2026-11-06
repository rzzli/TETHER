"""Bind a new descriptive analysis to the old externally anchored experiment.

No model dispatch, fitting, scoring, or rewriting of baseline artifacts occurs.
The independent source preflight must pass before this fresh freeze is written.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "data/benchmark/scifact/native-20261105T234805Z-attempt01"
PREPARED = ROOT / "data/benchmark/scifact/preparation-20261105-attempt03"
ASSETS = ROOT / "planning/review-assets/tether-semantic-20261106"
ANCHORS = {
    "data/benchmark/scifact/native-20261105T234805Z-attempt01/RECEIPT.json": "3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968",
    "data/benchmark/scifact/preparation-20261105-attempt03/manifest.json": "cb32f1384c49b66b912a62120abd7137a8a19b303f3ad052f035f21779c131f8",
    "data/raw/scifact_public/20261105-attempt01/scifact-data.tar.gz": "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be",
    "data/raw/scifact_public/20261105-attempt01/scifact-data.tar.gz.receipt.json": "b2aa9586681fbc22b1dbcd563daa6f49582f71f09331a80df78a5d4553fe4ba2",
    "planning/review-assets/tether-scifact-20261105/actual-attempt01/ROOT-ACCEPTANCE.json": "3426f85542f3a2b3355542e9292168db2f5f2ce39c713836a3c0e7cc1202d462",
    "planning/review-assets/tether-semantic-20261106/decomposition/qualification-attempt01/QUALIFICATION.json": "e4c7b716bea9ed6aff98448b5506509e1aff1ad20c9f502549d373d95c71e3a3",
    "planning/review-assets/tether-semantic-20261106/methods/independent_native_check.py": "68703fe9713580223e0ed918758ab7f87e9bd00205375aa3a753b9ef1bfd83d8",
    "planning/review-assets/tether-semantic-20261106/methods/compare_primary.py": "f4196156da4cb9a4c7703924d5b308b27928794102ad730fac89146a850c663e",
}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pin(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            count += len(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": count}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--preflight-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--analysis-output", required=True, type=Path)
    args = parser.parse_args()
    require(not args.output.exists() and not args.analysis_output.exists(), "Fresh outputs required")
    preflight_pin = pin(args.preflight)
    require(preflight_pin["sha256"] == args.preflight_sha256, "Independent preflight identity")
    require(read(args.preflight)["status"] == "PASS", "Independent source preflight must pass")
    authorities = [preflight_pin, pin(__file__), pin(sys.executable)]
    for relative, expected in ANCHORS.items():
        proof = pin(ROOT / relative)
        require(proof["sha256"] == expected, f"Original authority changed: {relative}")
        authorities.append(proof)
    qual = read(ASSETS / "decomposition/qualification-attempt01/QUALIFICATION.json")
    require(qual["status"] == "PASS" and qual["tests_run"] == 23, "Invented qualification")
    for proof in qual["source_pins"]:
        require(pin(proof["path"]) == proof, "Qualified code changed")
    inputs = {
        "freeze": pin(BASELINE / "DEV-FROZEN.json"),
        "references": pin(PREPARED / "restricted/references_dev.jsonl"),
        "corpus": pin(PREPARED / "views/corpus.jsonl"),
        "dispositions": pin(BASELINE / "dispositions.json"),
        "candidates": pin(BASELINE / "check-inputs/candidates.json"),
        "evaluation": pin(BASELINE / "evaluation.json"),
    }
    old_receipt = read(BASELINE / "RECEIPT.json")
    for name in ("freeze", "dispositions", "candidates", "evaluation"):
        relative = Path(inputs[name]["path"]).relative_to(BASELINE).as_posix()
        require(old_receipt["outputs"][relative] == inputs[name]["sha256"], f"Original receipt join: {name}")
    for name, expected in {
        "corpus": "e9127a5d615558c44343f719ac229683ee874aa427c6c60ba515cd92bbc29c9a",
        "references": "9af5e98502ddeebf25916579f6c96d689572a516ea3c5793711816f5ce933f5e",
    }.items():
        require(inputs[name]["sha256"] == expected, f"Original preparation join: {name}")
    plan = ROOT / "planning/TETHER Semantic Capability Execution Plan 2026-11-06.md"
    plan_bytes = plan.read_bytes()
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / "PLAN-AT-FREEZE.md").open("xb") as stream:
        stream.write(plan_bytes)
    authorities.append(pin(args.output / "PLAN-AT-FREEZE.md"))
    manifest = {
        "schema_version": 1,
        "kind": "scifact_descriptive_decomposition_inputs",
        "mode": "actual", "expected_claim_count": 300,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": inputs, "source_pins": qual["source_pins"],
        "authority_pins": authorities,
        "baseline_identity": {
            "stage_receipt_sha256": ANCHORS[str((BASELINE / 'RECEIPT.json').relative_to(ROOT).as_posix())],
            "preparation_manifest_sha256": ANCHORS[str((PREPARED / 'manifest.json').relative_to(ROOT).as_posix())],
            "independent_source_preflight": preflight_pin,
            "baseline_commit": "5f6f1fa",
        },
        "execution": {"interpreter": pin(sys.executable), "python_version": sys.version,
                      "analysis_output": str(args.analysis_output.resolve()), "provider_spend_usd": 0},
        "scope": "Post hoc descriptive baseline analysis; no tuning, new inference, causal attribution, or scientific improvement claim.",
    }
    manifest_path = args.output / "INPUT-MANIFEST.json"
    write(manifest_path, manifest)
    write(args.output / "FREEZE-RECEIPT.json", {"status": "PASS", "manifest": pin(manifest_path),
                                               "plan": pin(args.output / "PLAN-AT-FREEZE.md")})
    print(json.dumps({"status": "PASS", "manifest": pin(manifest_path)}))


if __name__ == "__main__":
    main()
