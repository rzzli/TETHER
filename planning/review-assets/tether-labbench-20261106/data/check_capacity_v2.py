"""Task-only prompt capacity qualification; no inference or reference reads."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.labbench.model import make_payload, DEFAULT_CONFIGURATION
from experiments.labbench.native_contract import validate_query


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    query_path = ROOT / "data/benchmark/labbench/preparation-20261106-attempt02/queries.json"
    raw = query_path.read_bytes()
    expected = "a9addd24e15f69f602da3b9abd6279dc6f6d528093c5cf2174a42ccee3f33e9d"
    assert sha(raw) == expected
    queries = json.loads(raw)
    assert len(queries) == 199 and len({q["id"] for q in queries}) == 199
    failures = []
    for query in queries:
        try:
            validate_query(query)
        except Exception as exc:
            failures.append({"id": query["id"], "error_class": type(exc).__name__})
    text = "Fictional capacity content. "
    text = (text * (1000 // len(text) + 1))[:1000]
    assert len(text.encode("utf-8")) == 1000
    sources = [{"source_id": f"fictional-capacity-{i}:p0001", "sha256": sha(text.encode()),
                "text": text} for i in range(8)]
    scenarios = {}
    for name, offered in (("no_sources", []), ("eight_fictional_1000byte_ascii_sources", sources)):
        sizes, errors = [], []
        for query in queries:
            try:
                payload = make_payload(query, offered)
                sizes.append(len(payload["prompt"].encode("utf-8")))
            except Exception as exc:
                errors.append({"id": query["id"], "error_class": type(exc).__name__})
        scenarios[name] = {"passed": len(sizes), "failure_ids": [e["id"] for e in errors],
                           "failures": errors, "min_prompt_bytes": min(sizes) if sizes else None,
                           "max_prompt_bytes": max(sizes) if sizes else None,
                           "source_text_bytes": sum(len(s["text"].encode()) for s in offered)}
    paths = [Path(__file__).resolve(), ROOT / "experiments/labbench/model.py",
             ROOT / "experiments/labbench/native_contract.py"]
    report = {"kind": "task_only_capacity_no_inference", "checked_at": datetime.now(timezone.utc).isoformat(),
              "query_sha256": expected, "scheduled": 199, "native_query_valid": 199-len(failures),
              "native_query_failures": failures, "scenarios": scenarios,
              "max_prompt_bytes_configuration": DEFAULT_CONFIGURATION["max_prompt_bytes"],
              "module_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p.read_bytes()) for p in paths},
              "model_calls": 0, "network_requests": 0, "references_or_source_hints_read": False,
              "actual_source_unicode_escaping": "Unknown until actual source packets. Non-ASCII JSON escaping can increase prompt bytes; overcapacity must remain explicit without cohort removal.",
              "supersedes_capacity_measurement": "TASK-CAPACITY-01.json used the earlier v1 prompt; original evidence remains retained.",
              "pass": not failures and all(s["passed"] == 199 for s in scenarios.values())}
    output = Path(__file__).with_name("TASK-CAPACITY-02.json")
    with output.open("xb") as stream:
        stream.write(json.dumps(report, sort_keys=True, indent=2).encode()+b"\n")
    print(json.dumps({"pass": report["pass"], "scheduled": 199, "scenarios": scenarios,
                      "report_sha256": sha(output.read_bytes()), "model_calls": 0}))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
