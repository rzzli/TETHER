"""Re-run `asof verify` with the registry-recorded receipt hash for every canonical dossier, and
independently re-hash registry-listed report files. Output: JSON to stdout."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\Projects\drug_target_agents")
ASOF = ROOT / ".venv" / "Scripts" / "asof.exe"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


registry = json.loads((ROOT / "planning" / "run-registry.json").read_text(encoding="utf-8"))
selected = sys.argv[1] if len(sys.argv) > 1 else registry["canonical_pilot_id"]
report = {"canonical_pilot_id": registry["canonical_pilot_id"], "entries": {}}
for entry in registry["entries"]:
    # Report-file hash checks for every registry entry that lists them.
    checks = []
    for item in entry.get("reports", []):
        target = ROOT / item["path"]
        actual = sha256(target) if target.is_file() else None
        checks.append({"path": item["path"], "match": actual == item["sha256"], "actual": actual})
    report["entries"][entry["id"]] = {"state": entry["state"], "path_exists": (ROOT / entry["path"]).exists(),
                                       "report_checks": checks}
entry = next(e for e in registry["entries"] if e["id"] == selected)
verifications = []
for case in entry["cases"]:
    started = time.monotonic()
    proc = subprocess.run([str(ASOF), "verify", "--run-dir", str(ROOT / case["path"]),
                           "--receipt-sha256", case["receipt_sha256"]],
                          capture_output=True, text=True)
    elapsed = time.monotonic() - started
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"raw_stdout": proc.stdout[:500]}
    verifications.append({"case": case["case_id"], "exit": proc.returncode, "seconds": round(elapsed, 1),
                          "stderr": proc.stderr[:300], "result": payload})
report["verifications"] = verifications
print(json.dumps(report, indent=2))
