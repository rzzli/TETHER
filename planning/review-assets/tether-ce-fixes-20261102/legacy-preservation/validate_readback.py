"""Assert retained old-version results and rehash installed payloads after demo."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
source = Path(sys.argv[1]).resolve()
record = json.loads(source.read_text(encoding="utf-8"))
assert record["status"] == "PASS" and all(item["passed"] for item in record["checks"])
assert record["demo"]["status"] == "completed"
assert record["verified"]["status"] == "integrity_verified"
assert record["verified"]["external_anchor_checked"] is True
assert record["verified"]["launcher_code_verified"] is True
engine = record["verified"]["engine"]
assert engine["semantic_consistency"] == "verified"
assert engine["code_matches_current"] is True
assert engine["source_binding"] == "current_originals"
assert engine["scientific_validity"] == "not_established"
assert record["verified"]["receipt_sha256"] == record["demo"]["receipt_sha256"]
site = ROOT / "data/cache/tether-050-qualified-build/env/Lib/site-packages"
payloads = [item for item in record["checks"] if item["name"] == "installed_wheel_payload"]
for item in payloads:
    assert hashlib.sha256((site / item["module"]).read_bytes()).hexdigest() == item["sha256"], item["module"]
result = dict(status="PASS", source_record=source.name,
              source_record_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              installed_payloads_rehashed_after_demo=len(payloads),
              old_demo="completed", old_semantics="verified", old_code_identity=True,
              scientific_validity="not_established", new_demo_calls=0,
              validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
destination = source.with_name(source.stem + "-READBACK.json")
with destination.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps(result, indent=2))
