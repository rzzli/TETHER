"""Compare a sealed primary report to the already completed blind reconstruction."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reconstruct import child, parse, read, require, sha

FIELDS = ("scheduled_count", "raw_metrics", "checked_metrics", "counts", "rates",
          "raw_precision_defined", "checked_precision_defined")


def verify_primary(root, expected):
    root = Path(root)
    seal = parse(read(root/"SEALED.json", expected))
    require(seal["kind"] == "labbench_native_evaluation", "Wrong primary seal kind")
    expected_files = set(seal["outputs"]) | {"journal.jsonl"}
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*")
              if p.is_file() and p != root/"SEALED.json"}
    require(actual == expected_files, "Primary output inventory differs")
    for name, proof in seal["outputs"].items():
        require(proof["path"] == name, "Primary output path differs")
        require(len(read(child(root, name), proof["sha256"])) == proof["bytes"], "Primary output bytes differ")
    read(root/"journal.jsonl", seal["journal_sha256"])
    return seal


def compare(independent_path, independent_sha, evaluation_root, evaluation_sha):
    independent = parse(read(independent_path, independent_sha))
    require(independent["status"] == "pass" and independent["preparation_reference_comparison"] is True,
            "Independent reference reconstruction is not complete")
    seal = verify_primary(evaluation_root, evaluation_sha)
    provenance = parse(read(Path(evaluation_root)/"input-provenance.json"))
    require(seal["input_anchors"]["external_sealed_sha256"] == independent["generation_sealed_sha256"]
            == provenance["generation"]["external_sealed_sha256"], "Primary generation identity differs")
    report_raw = read(Path(evaluation_root)/"REPORT.json")
    report = parse(report_raw)
    for field in FIELDS:
        require(report[field] == independent[field], "Primary comparison differs: "+field)
    require(report["generation_status"] == independent["generation_status"], "Generation status differs")
    return {"status": "pass", "primary_evaluation_comparison": True, "fields_compared": list(FIELDS),
            "scheduled_count": independent["scheduled_count"], "independent_sha256": independent_sha,
            "evaluation_sealed_sha256": evaluation_sha, "primary_report_sha256": sha(report_raw),
            "generation_sealed_sha256": independent["generation_sealed_sha256"],
            "generation_status": independent["generation_status"],
            "reference_files_reopened": False, "new_model_calls": 0, "new_network_requests": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("independent-path", "independent-sha", "evaluation-root", "evaluation-sha", "output"):
        parser.add_argument("--"+name, required=True)
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        result = compare(args.independent_path, args.independent_sha, args.evaluation_root, args.evaluation_sha)
        result.update(completed_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-started,
                      comparison_code_sha256=sha(Path(__file__).read_bytes()))
        (root/"COMPARISON.json").write_text(json.dumps(result, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "scheduled": result["scheduled_count"]}))
    except BaseException as exc:
        (root/"FAILED.json").write_text(json.dumps({"status": "failed", "error_class": type(exc).__name__,
                                                   "message": str(exc)})+"\n", encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
