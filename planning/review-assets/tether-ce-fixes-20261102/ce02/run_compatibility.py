"""Retain focused CE02 compatibility checks, all fictional model transports."""
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
patterns = ["test_local_model.py", "test_backend_hardening.py", "test_runtime_hardening_peer.py",
            "test_selection_cap.py", "test_framework.py", "test_science_role_backend.py",
            "test_science_role_constraint_peer.py", "test_science_comparison_workflow.py"]
destination = Path(__file__).parent / (sys.argv[1] + "-results.json")
if destination.exists():
    raise SystemExit("Refusing to replace an existing result")
suite = unittest.TestSuite()
for pattern in patterns:
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern))
started = time.monotonic()
result = unittest.TextTestRunner(verbosity=1).run(suite)
record = dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
              skips=len(result.skipped), success=result.wasSuccessful(), elapsed_seconds=time.monotonic()-started,
              patterns=patterns, source_sha256=hashlib.sha256((ROOT/"src/asof/local_model.py").read_bytes()).hexdigest(),
              failures_detail=[dict(test=str(test), traceback=trace) for test, trace in result.failures],
              errors_detail=[dict(test=str(test), traceback=trace) for test, trace in result.errors],
              scope="Existing fictional adapter/framework tests; no actual model/network/provider call")
destination.write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
print(json.dumps(record, indent=2))
raise SystemExit(not result.wasSuccessful())
