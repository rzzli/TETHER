"""Retain a metadata-only check of the accepted source before timestamped commits."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
ACCEPTANCE = ROOT / "planning/review-assets/recovery-step9-generation-contract-20261028/acceptance.json"


def pin(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    accepted = json.loads(ACCEPTANCE.read_bytes())
    rows = []
    for name, expected in accepted["source_pins"].items():
        row = pin(ROOT / name)
        row["matches_accepted_source"] = row["sha256"] == expected
        rows.append(row)
    report = {
        "schema_version": 1,
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(row["matches_accepted_source"] for row in rows) else "HOLD",
        "acceptance": pin(ACCEPTANCE),
        "source_pins": rows,
        "retained_tests": accepted["tests"],
        "tests_rerun": False,
        "scope": "Metadata-only checkpoint of 327 accepted source/resource files. No subject import, protected payload, original data or native execution.",
        "chronology": "Commit time is the current checkpoint time; historical development timestamps are not reconstructed.",
        "default_runtime": "0.3.11 / v2",
        "entire_project_complete": False,
    }
    output = BASE / "ACCEPTED-SOURCE-RESUME-CHECK-v1.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    if report["status"] != "PASS":
        raise SystemExit("Source checkpoint differs; do not stage.")
    selected = list(accepted["source_pins"])
    selected += [ACCEPTANCE.relative_to(ROOT).as_posix(),
                 "planning/review-assets/recovery-step9-generation-contract-20261028/CLOSEOUT.md",
                 "planning/review-assets/recovery-step9-generation-contract-20261028/FINAL-CHECK.json",
                 Path(__file__).relative_to(ROOT).as_posix(),
                 output.relative_to(ROOT).as_posix()]
    pathspec = BASE / "accepted-source-pathspec-v1.txt"
    selected.append(pathspec.relative_to(ROOT).as_posix())
    with pathspec.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(selected) + "\n")
    print(json.dumps({"report": pin(output), "pathspec": pin(pathspec),
                      "source_files": len(rows), "commit_paths": len(selected),
                      "mismatches": 0, "source_bytes": sum(row["bytes"] for row in rows)}))


if __name__ == "__main__":
    main()
