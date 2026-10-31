"""Retain a pre-behavioral fixture contradiction, without invoking fake ports."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
raw = (here / "FILE-PORTS-FIXTURES-v3.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "9e445e2e230689aa7c36e7eba666959dcac87478caf27252154eb02e978109b7"
data = json.loads(raw)
selected = {case["id"]: case for case in data["cases"] if case["id"] in ("write_false", "write_false_and_close_failure")}
first = selected["write_false"]
later = selected["write_false_and_close_failure"]
assert first["request"]["actions"] == later["request"]["actions"]
a = [row for row in first["script"] if row["kind"] == "api"]
b = [row for row in later["script"] if row["kind"] == "api"]
assert a[0] == b[0] and a[0]["name"] == "WriteFile"
assert a[0]["outcome"]["raw_return"]["value"] == 0
assert a[0]["outcome"]["raw_return"]["raw_count_defined"] is False
assert first["expected"]["primary"] == "false"
assert later["expected"]["primary"] == "false_and_close_failure"
assert later["expected"]["secondary"] == ["close_failed"]
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "CONFIRMED_EXPECTED_PRIMARY_FIXTURE_DEFECT",
    "input": {"file": "FILE-PORTS-FIXTURES-v3.json", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
    "cases": [first["id"], later["id"]],
    "same_action_and_first_API_step": True,
    "first_failure_API_step": a[0],
    "first_expected_primary": first["expected"]["primary"],
    "second_incorrect_expected_primary": later["expected"]["primary"],
    "unchanged_correct_secondary": later["expected"]["secondary"],
    "root_correction_authorization": "Preserve v3 and limited preparation acceptance. In a separately frozen successor change only this primary expectation to false, retain close_failed as secondary, and obtain exact independent review. Do not tailor source behavior to labels or weaken primary preservation.",
    "actual_port_behavior_executed_by_this_review": False,
    "direct_Win32_or_old_payload_operations": 0,
    "runtime_authorized": False, "profile_qualified": False,
}
output = here / "FILE-PORTS-ROOT-PRIMARY-WITNESS-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
