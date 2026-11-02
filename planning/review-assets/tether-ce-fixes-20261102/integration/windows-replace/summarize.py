"""Validate retained focused evidence; no test or publication retry."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


records = {name:json.loads((HERE/(name+"-results.json")).read_text(encoding="utf-8"))
           for name in ("red", "green", "compatibility", "atomic-maintenance")}
assert not records["red"]["success"] and records["red"]["tests"] == 10
for name in ("green", "compatibility", "atomic-maintenance"):
    assert records[name]["success"] and not any(records[name][key] for key in ("failures","errors","skipped"))
for name,record in records.items():
    assert digest(HERE/(name+"-tests.log")) == record["log_sha256"]
for path in ("src/asof/atomic.py", "src/asof/maintenance.py"):
    assert records["red"]["source_sha256"][path.replace("/", "\\")] == digest(ROOT/path)
for name in ("green", "compatibility", "atomic-maintenance"):
    for path,expected in records[name]["source_sha256"].items():
        assert digest(ROOT/path) == expected
result = dict(status="PASS", checked_at_utc=datetime.now(timezone.utc).isoformat(),
              scope="Targeted bounded atomic-replacement and adjacent regression validation; full gate and independent peer are separate",
              source_sha256={path:digest(ROOT/path) for path in (
                  "src/asof/serde.py", "tests/test_serde_atomic_replace.py", "src/asof/atomic.py", "src/asof/maintenance.py")},
              driver_sha256=digest(HERE/"run_regressions.py"),
              summarizer_sha256=digest(Path(__file__)),
              evidence_sha256={path.name:digest(path) for path in HERE.glob("*-results.json")},
              log_sha256={path.name:digest(path) for path in HERE.glob("*-tests.log")},
              results={name:{key:record[key] for key in ("tests","failures","errors","skipped","success","elapsed_seconds")}
                       for name,record in records.items()},
              native_windows_controls="Actual deny-delete handle: release-before-retry succeeds; held handle remains bounded failure",
              attempt_limit=3, requested_backoff_seconds=[0.05,0.1], eligible_native_errors=[5,32,33],
              no_clobber_sources_unchanged=True, full_gate="root-owned pending",
              caveats=["Original full-gate failure cause remains unestablished; native held-handle control does not prove it was the same cause",
                       "150ms is the requested-sleep bound, not a hard bound on filesystem or scheduler latency",
                       "Mutable write_json remains last-completing-writer-wins, not compare-and-swap or invocation-order preservation"],
              official_references=["https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-",
                                   "https://docs.python.org/3.11/library/os.html#os.replace"],
              provider_spending_usd=0, actual_model_calls=0)
with (HERE/"VALIDATION.json").open("x",encoding="utf-8",newline="\n") as stream:
    json.dump(result,stream,indent=2);stream.write("\n")
print(json.dumps({key:result[key] for key in ("status","source_sha256","results")},indent=2))
