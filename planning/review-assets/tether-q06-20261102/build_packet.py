"""Build one fresh corrected-paper packet and retain its disposition."""
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.presentation import package_tether_review_v2 as packet

label = sys.argv[1]
if label not in ("first", "repeat"):
    raise ValueError("Use first or repeat")
report = Path(__file__).with_name("PACKET-BUILD-" + label + ".json")
if report.exists():
    raise FileExistsError(report)
stage = ROOT / "data/cache/tether-q06/working-v2"
qualification = stage / "TETHER-QUALIFICATION.json"
record = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
          "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
try:
    record["result"] = packet.package(
        stage, stage / "inputs/portable-results",
        stage / "inputs/wheels/tether_target_agents-0.5.0-py3-none-any.whl",
        stage / "inputs/legacy/asof-research-artifact-0.1.0.zip",
        qualification, hashlib.sha256(qualification.read_bytes()).hexdigest(),
        stage / "data/derived" / ("tether-review-0.5.0-q06-" + label + ".zip"))
except BaseException as error:
    record["failure"] = {"type": type(error).__name__, "message": str(error)}
    raise
finally:
    with report.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
print(json.dumps(record, sort_keys=True))
