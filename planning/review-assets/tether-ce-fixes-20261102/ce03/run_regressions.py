"""Retain a unique CE03 regression attempt; all fixtures are fictional."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "packages/tether/src"), str(ROOT / "packages/tether/tests"),
               str(ROOT), str(ROOT / "tests")]
output = Path(sys.argv[1]).absolute()
output.mkdir(parents=True, exist_ok=False)
temporary = ROOT / "data/cache/tether-ce03-tests" / ("suite-" + output.name)
temporary.mkdir(parents=True, exist_ok=False)
os.environ["TMP"] = os.environ["TEMP"] = str(temporary)
tempfile.tempdir = str(temporary)
names = sys.argv[2:] or ["test_ce03_receipt_time"]
suite = unittest.defaultTestLoader.loadTestsFromNames(names)
with (output / "tests.log").open("w", encoding="utf-8") as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
pins = {}
for relative in ("src/asof/provenance.py", "packages/tether/src/tether/_catalog_binding.py",
                 "packages/tether/tests/test_ce03_receipt_time.py"):
    pins[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
record = dict(utc=datetime.now(timezone.utc).isoformat(), interpreter=sys.executable,
              scope="Fictional CE03 regression suite; no network/model/data collection",
              modules=names, tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
              skipped=len(result.skipped), successful=result.wasSuccessful(), source_sha256=pins,
              runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), temporary_root=str(temporary))
(output / "results.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record, indent=2))
sys.exit(0 if result.wasSuccessful() else 1)
