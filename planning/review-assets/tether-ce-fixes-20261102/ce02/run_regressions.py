"""Retain CE02 fictional regression outcomes; never invokes an actual backend."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
phase = sys.argv[1]
destination = Path(__file__).parent / (phase + "-results.json")
if destination.exists():
    raise SystemExit("Refusing to replace an existing result")
spec = importlib.util.spec_from_file_location("ce02_regressions", ROOT / "tests/test_ce02_usage_accounting.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromModule(module)
started = time.monotonic()
result = unittest.TextTestRunner(verbosity=2).run(suite)
record = dict(phase=phase, tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
              skips=len(result.skipped), success=result.wasSuccessful(), elapsed_seconds=time.monotonic()-started,
              failures_detail=[dict(test=str(test), traceback=trace) for test, trace in result.failures],
              errors_detail=[dict(test=str(test), traceback=trace) for test, trace in result.errors],
              source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (ROOT/"src/asof/local_model.py", ROOT/"src/asof/workflow.py",
                               ROOT/"tests/test_ce02_usage_accounting.py")},
              scope="Fictional in-process opener; no actual model/network/provider call")
destination.write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
print(json.dumps({k:v for k,v in record.items() if k not in ("failures_detail","errors_detail")}, indent=2))
raise SystemExit(not result.wasSuccessful())
