"""Record atomic replacement regression attempts without replacing evidence."""
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
phase = sys.argv[1]
destination = HERE / (phase + "-results.json")
log_path = HERE / (phase + "-tests.log")
if destination.exists() or log_path.exists():
    raise SystemExit("Refusing to replace retained evidence")
patterns = ["tests.test_serde_atomic_replace"] if len(sys.argv) < 3 else sys.argv[2:]
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in patterns)
started = time.monotonic()
with log_path.open("x", encoding="utf-8") as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
record = dict(phase=phase, tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
              skipped=len(result.skipped), success=result.wasSuccessful(), elapsed_seconds=time.monotonic()-started,
              modules=patterns, log_sha256=hashlib.sha256(log_path.read_bytes()).hexdigest(),
              source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (ROOT/"src/asof/serde.py",ROOT/"tests/test_serde_atomic_replace.py",
                               ROOT/"src/asof/atomic.py",ROOT/"src/asof/maintenance.py")},
              driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              failures_detail=[dict(test=str(test),traceback=trace) for test,trace in result.failures],
              errors_detail=[dict(test=str(test),traceback=trace) for test,trace in result.errors],
              scope="Deterministic fictional errors and private native Win32 file handles; no model/network action")
with destination.open("x",encoding="utf-8") as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
print(log_path.read_text(encoding="utf-8"))
print(json.dumps({k:v for k,v in record.items() if not k.endswith("_detail")},indent=2))
raise SystemExit(not result.wasSuccessful())
