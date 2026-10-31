"""Retain reviewed0.3.1 wheel/config as data before changing the live package."""
import hashlib
import json
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEST = ROOT / "data/reference/recovery-r07-verifier-031-20261026"
DEST.mkdir(parents=True, exist_ok=False)
sources = [ROOT / "data/cache/recovery-step7-wheel-20261026/dist/asof_target_agents-0.3.1-py3-none-any.whl",
           ROOT / "src/asof/archive/semantic_dependencies.json", ROOT / "src/asof/__init__.py"]
records = []
for source in sources:
    data = source.read_bytes()
    output = DEST / source.name
    output.write_bytes(data)
    assert output.read_bytes() == data
    records.append({"original": str(source.relative_to(ROOT)).replace("\\", "/"),
                    "archive": str(output.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
report = {"schema_version": 1, "status": "reviewed_frozen_verifier_preserved_before_live_changes",
          "version": "0.3.1", "python": platform.python_version(), "files": records,
          "operator_selected_trusted_wheel": True, "automatic_archived_import": False,
          "guard": "frozen-r07-verification-before-v2.json",
          "native_calls": 0, "original_run_or_receipt_modified": False,
          "independent_new_format_relocation_claimed": False,
          "off_machine_backup_claimed": False}
(HERE / "frozen-verifier-preservation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], "files": len(records), "wheel_sha256": records[0]["sha256"]}))
