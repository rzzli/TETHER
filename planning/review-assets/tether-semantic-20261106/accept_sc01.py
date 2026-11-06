"""Root acceptance for the independently reconstructed descriptive analysis."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "planning/review-assets/tether-semantic-20261106"
PRIMARY = ROOT / "data/benchmark/scifact_diagnostics/20261106-attempt01"
BASELINE = ROOT / "data/benchmark/scifact/native-20261105T234805Z-attempt01"
MANIFEST = ASSETS / "decomposition/actual-freeze-attempt01/INPUT-MANIFEST.json"
MANIFEST_SHA = "f465f1579dd6f71d82d261c0a1230acfc258935c557025f0f0197fe670659203"


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


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def check(proof):
    actual = pin(proof["path"])
    need(actual["sha256"] == proof["sha256"], f"Byte identity: {proof['path']}")
    expected_size = proof.get("bytes", proof.get("size_bytes"))
    if expected_size is not None:
        need(actual["bytes"] == expected_size, f"Byte count: {proof['path']}")
    return actual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--comparison-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    need(not args.output.exists(), "Fresh acceptance required")
    need(pin(MANIFEST)["sha256"] == MANIFEST_SHA, "Manifest identity")
    need(pin(args.comparison)["sha256"] == args.comparison_sha256, "Independent comparator identity")
    manifest = read(MANIFEST)
    observed = [check(p) for p in list(manifest["inputs"].values()) + manifest["source_pins"] + manifest["authority_pins"]]
    original_receipt = read(BASELINE / "RECEIPT.json")
    actual_paths = {p.relative_to(BASELINE).as_posix() for p in BASELINE.rglob("*") if p.is_file()}
    need(actual_paths == set(original_receipt["outputs"]) | {"RECEIPT.json"}, "Original exact fileset")
    for name, digest in original_receipt["outputs"].items():
        need(pin(BASELINE / name)["sha256"] == digest, f"Original output changed: {name}")
    receipt = read(PRIMARY / "RECEIPT.json")
    need(receipt["status"] == "PASS" and receipt["scheduled_claims"] == 300, "Primary receipt")
    need(receipt["analysis_manifest_sha256"] == MANIFEST_SHA, "Primary manifest binding")
    need({p.name for p in PRIMARY.iterdir()} == set(receipt["outputs"]) | {"RECEIPT.json"}, "Primary fileset")
    for name, proof in receipt["outputs"].items():
        observed.append(check(dict(proof, path=str(PRIMARY / name))))
    comparison = read(args.comparison)
    need(comparison["status"] == "PASS" and comparison["claims_checked"] == 300, "Independent comparison")
    for proof in comparison["inputs"].values():
        observed.append(check(proof))
    need(Path(comparison["inputs"]["primary"]["path"]).resolve() == (PRIMARY / "DECOMPOSITION.json").resolve(), "Compared primary identity")
    independent = read(comparison["inputs"]["independent"]["path"])
    need(independent["status"] == "PASS", "Independent native reconstruction")
    need(independent["inputs"]["freeze"]["sha256"] == MANIFEST_SHA, "Independent manifest binding")
    for proof in independent["inputs"].values():
        observed.append(check(proof))
    primary = read(PRIMARY / "DECOMPOSITION.json")
    need(len(primary["cases"]) == 300, "Full scheduled denominator")
    need(sum(primary["summary"]["first_failure_partition"].values()) == 300, "Exhaustive descriptive partition")
    execution_path = ASSETS / "decomposition/actual-execution-attempt01/RUN.json"
    execution = read(execution_path)
    need(execution["status"] == "PASS" and execution["returncode"] == 0, "Execution status")
    result = {
        "schema_version": 1, "status": "PASS", "stage": "SC01",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Sealed baseline descriptive decomposition only; SC02-SC09 remain incomplete.",
        "manifest": pin(MANIFEST), "primary_receipt": pin(PRIMARY / "RECEIPT.json"),
        "independent_comparison": pin(args.comparison), "execution": pin(execution_path),
        "acceptance_source": pin(__file__), "qualification_tests": 23,
        "independent_native_boundary_cases": 14, "claims_checked": 300,
        "original_receipt_outputs_preserved": len(original_receipt["outputs"]),
        "original_exact_fileset_preserved": len(actual_paths),
        "new_analysis_elapsed_seconds": execution["elapsed_seconds"],
        "provider_spend_usd": 0, "summary": primary["summary"],
        "native_metrics": independent["raw_native"]["metrics"],
        "rechecked_pins": observed,
        "limitations": ["Post hoc public-development analysis; not an independent holdout.",
                        "First-failure precedence is descriptive, not causal.",
                        "Unannotated documents are not established biological negatives.",
                        "Independent review is separately implemented AI-assisted review, not external scientific adjudication."]}
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "stage": "SC01", "acceptance": pin(args.output)}))


if __name__ == "__main__":
    main()
