"""Tiny output-collision fixture; reads no biological data or source receipts."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from audit_outputs import reserve_run_directories, save_new_json

HERE = Path(__file__).resolve().parent
WORK = Path(__file__).resolve().parents[4]
fixture = Path(tempfile.mkdtemp(prefix="no-clobber-", dir=WORK / "data/cache/tether-q03"))
report_root, cache_root = fixture / "reports", fixture / "cache"
report, cache = reserve_run_directories("first", report_root, cache_root)
sentinel = cache / "source-slice-evidence.json"
save_new_json(sentinel, {"fixture": "original bytes", "biological_data": False})
before = sentinel.read_bytes()
checks = []

try:
    reserve_run_directories("first", report_root, cache_root)
except FileExistsError:
    checks.append("existing run rejected")
else:
    raise AssertionError("Existing run accepted")
assert sentinel.read_bytes() == before

try:
    save_new_json(sentinel, {"fixture": "replacement"})
except FileExistsError:
    checks.append("existing JSON rejected without byte changes")
else:
    raise AssertionError("Existing file overwritten")
assert sentinel.read_bytes() == before

(cache_root / "cacheonly").mkdir()
try:
    reserve_run_directories("cacheonly", report_root, cache_root)
except FileExistsError:
    checks.append("cache-only collision rejected before report directory creation")
else:
    raise AssertionError("Cache-only collision accepted")
assert not (report_root / "cacheonly").exists()

for unsafe in ["../escape", "..", r"a\b", "/absolute", "", "a" * 81]:
    try:
        reserve_run_directories(unsafe, report_root, cache_root)
    except ValueError:
        continue
    raise AssertionError("Unsafe run ID accepted")
checks.append("unsafe run IDs rejected")

result = {"passed": True, "checks": checks, "fixture_directory": str(fixture), "original_sentinel_sha256": hashlib.sha256(before).hexdigest(), "final_sentinel_sha256": hashlib.sha256(sentinel.read_bytes()).hexdigest(), "raw_source_files_read": 0, "scope": "Output reservation and exclusive JSON writes only; no full audit rerun"}
save_new_json(HERE / "SOURCE-NO-CLOBBER-VERIFICATION.json", result)
print(json.dumps(result, indent=2))
