"""Authorized nonbenchmark check of the exact frozen question/query/HTTP path."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.labbench.retrieval import retrieve, verify_retrieval, select_passages


def main():
    question = "How does photosynthesis use chlorophyll to convert sunlight into chemical energy?"
    output = ROOT / "data/benchmark/labbench/nonbenchmark-source-probe-20261106-attempt01"
    manifest = retrieve(question, output)
    sha = hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest()
    verified = verify_retrieval(output, sha, question)
    packet = select_passages(verified, question)
    report = {"kind": "nonbenchmark_source_feasibility_only", "question": question,
              "manifest_path": str(output / "manifest.json"), "manifest_sha256": sha,
              "queries": list(manifest["queries"]), "request_statuses": [
                  {"kind": r["kind"], "status": r["status"], "http_status": r.get("http_status"),
                   "error_type": r.get("error_type"), "failure_cause": r.get("failure_cause")}
                  for r in manifest["requests"]],
              "retained_pmcids": [source["source_id"] for source in manifest["sources"]],
              "coverage": dict(manifest["coverage"]), "passage_coverage": dict(packet["coverage"]),
              "costs": dict(manifest["costs"]), "source_inclusive_verification": "pass",
              "benchmark_questions_or_hints_used": False, "candidate_generation": False}
    path = ROOT / "planning/review-assets/tether-labbench-20261106/data/NONBENCHMARK-PROBE-01.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
