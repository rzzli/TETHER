"""Stdlib trace line coverage for new study modules; no runtime dependency added."""
import hashlib
import json
import os
import sys
import tempfile
import trace
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data/cache/recovery-step6-coverage-20261026"
CACHE.mkdir(exist_ok=True)
tempfile.tempdir = str(CACHE)
os.environ["TMP"] = os.environ["TEMP"] = str(CACHE)
sys.path.insert(0, str(ROOT))
paths = sorted((ROOT / "src/asof/study").rglob("*.py"))
before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, str(Path(sys.base_prefix) / "Lib")])


def run():
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_study*.py", top_level_dir=str(ROOT))
    return unittest.TextTestRunner(verbosity=1).run(suite)


result = tracer.runfunc(run)
counts = tracer.results().counts
files = []
for path in paths:
    executable = set(trace._find_executable_linenos(str(path)))
    hit = {line for (name, line), count in counts.items() if Path(name).resolve() == path.resolve() and count > 0}
    covered = executable & hit
    files.append(dict(path=path.relative_to(ROOT).as_posix(), executable_lines=len(executable),
                      covered_lines=len(covered), missed_lines=sorted(executable - covered),
                      covered_percent=round(100 * len(covered) / len(executable), 2) if executable else None))
after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
report = dict(status="passed" if result.wasSuccessful() and not result.skipped and before == after else "failed",
              coverage_method="CPython 3.11 stdlib trace executable-line coverage; not branch coverage",
              tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
              unchanged_study_sources=before == after, files=files, native_model_calls=0)
(CACHE / "coverage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key != "files"}, indent=2))
raise SystemExit(0 if report["status"] == "passed" else 1)
