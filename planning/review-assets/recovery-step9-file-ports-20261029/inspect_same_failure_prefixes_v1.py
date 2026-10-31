"""Find differing primary expectations after identical fictional failure prefixes.

This is a bounded fixture review, not a port implementation or conformance test.
"""
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
raw = (here / "FILE-PORTS-FIXTURES-v3.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "9e445e2e230689aa7c36e7eba666959dcac87478caf27252154eb02e978109b7"
cases = json.loads(raw)["cases"]
groups = {}
for case in cases:
    prefix, failure = [], None
    for row in case["script"]:
        prefix.append({key: value for key, value in row.items() if key != "before_projection"})
        if row["kind"] in ("clock", "hook") and row["raises"] is not None:
            failure = row["kind"]
        elif row["kind"] == "api":
            if row["outcome"]["raise"] is not None:
                failure = row["name"] + ":unreturned"
            elif row["name"] in ("ReadFile", "WriteFile", "FlushFileBuffers", "CloseHandle", "FindClose") and row["outcome"]["raw_return"]["value"] == 0:
                failure = row["name"] + ":zero"
        if failure is not None:
            break
    if failure is None:
        continue
    key = json.dumps({"actions": case["request"]["actions"], "initial": case["initial"],
                      "facts": case["request"]["facts"], "plan": case["plan"],
                      "path_records": case["path_records"], "prefix": prefix}, sort_keys=True)
    groups.setdefault(key, []).append({"id": case["id"], "failure": failure,
                                     "expected_primary": case["expected"]["primary"]})
differences = [rows for rows in groups.values() if len(rows) > 1 and len({json.dumps(row["expected_primary"]) for row in rows}) > 1]
print(json.dumps({"scope": "Literal fixture prefixes only; inspect candidates manually, no port behavior executed.",
                  "cases": len(cases), "failure_prefix_groups": len(groups),
                  "differing_primary_groups": differences}, indent=2, sort_keys=True))
