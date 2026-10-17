"""Independently re-hash every file in the frozen 2,206-file input manifest (review script; stdlib only)."""
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(r"D:\Projects\drug_target_agents")
RAW = Path(r"E:\projects_data\drug_target_agents_data")
inspection = json.loads((ROOT / "data/derived/literature-coverage-20261017T082208Z/inspection.json").read_bytes().decode("utf-8-sig"))
files = inspection["files"]


def check(entry):
    src = entry["source"]
    target = RAW / src["path"].replace("/", "\\")
    if not target.is_file():
        return {"path": src["path"], "status": "missing"}
    h = hashlib.sha256()
    size = 0
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 22), b""):
            h.update(chunk)
            size += len(chunk)
    ok = h.hexdigest() == src["sha256"] and size == entry["bytes"]
    return {"path": src["path"], "status": "ok" if ok else "mismatch", "bytes": size,
            "expected_bytes": entry["bytes"], "dataset": src["dataset_id"]}


started = time.monotonic()
results = []
with ThreadPoolExecutor(max_workers=4) as pool:
    for i, r in enumerate(pool.map(check, files), 1):
        results.append(r)
        if i % 200 == 0:
            print(f"progress {i}/{len(files)} elapsed {time.monotonic()-started:.0f}s", file=sys.stderr, flush=True)
summary = {
    "files": len(results),
    "ok": sum(r["status"] == "ok" for r in results),
    "missing": [r["path"] for r in results if r["status"] == "missing"],
    "mismatch": [r for r in results if r["status"] == "mismatch"],
    "total_bytes": sum(r.get("bytes", 0) for r in results),
    "elapsed_seconds": round(time.monotonic() - started, 1),
}
print(json.dumps(summary, indent=2))
