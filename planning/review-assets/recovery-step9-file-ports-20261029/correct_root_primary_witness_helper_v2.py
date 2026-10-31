"""Preserve a root metadata-helper schema mistake and correct its assertion."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
raw = (here / "record_root_primary_fixture_witness_v1.py").read_bytes()
old = b'assert later["expected"]["secondary"] == "close_failed"'
new = b'assert later["expected"]["secondary"] == ["close_failed"]'
assert raw.count(old) == 1
assert not (here / "FILE-PORTS-ROOT-PRIMARY-WITNESS-v1.json").exists()
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "ROOT_METADATA_HELPER_STOPPED_BEFORE_PUBLICATION",
    "failure": "The root helper assumed expected.secondary was a scalar string; the fixture schema uses a list. Its assertion stopped with exit1 before witness publication. This is not another fixture or port defect.",
    "failed_helper": {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
    "correction": "A separately named helper compares against [close_failed]; no source, fixture, expected outcome or behavioral test changes.",
    "port_behavior_or_runtime_executed": False,
}
with (here / "FILE-PORTS-ROOT-PRIMARY-HELPER-FAILURE-v1.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
with (here / "record_root_primary_fixture_witness_v2.py").open("xb") as stream:
    stream.write(raw.replace(old, new))
print("Preserved failed metadata helper; created corrected v2 schema assertion.")
