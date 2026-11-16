"""Compare parent-process maintained coverage with a reviewed platform baseline."""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.quality import runtime_sources

FIELDS = ("covered_lines", "num_statements", "covered_branches", "num_branches")


def canonical_name(name):
    normalized = name.replace("\\", "/")
    for namespace in ("tether_engine", "tether"):
        marker = "/" + namespace + "/"
        if marker in normalized:
            return namespace + "/" + normalized.rsplit(marker, 1)[1]
        if normalized.startswith(namespace + "/"):
            return normalized
    raise ValueError("Unexpected coverage source: " + name)


def check_report(document, validation, baseline, expected):
    if (
        document["meta"]["version"] != "7.17.3"
        or document["meta"].get("branch_coverage") is not True
    ):
        raise ValueError("Coverage version/branch mode differs")
    if (
        validation.get("status") != "passed"
        or validation.get("mode") != "full"
        or validation.get("test_scope", {}).get("profile") != "maintained"
        or validation.get("required_probes_exit_code") != 0
    ):
        raise ValueError("Coverage requires a passing maintained full gate")
    tests = validation["tests"]
    if (
        tests["failures"]
        or tests["errors"]
        or tests["skipped"]
        or type(tests["run"]) is not int
        or tests["run"] < baseline["minimum_tests"]
    ):
        raise ValueError("Test failures, skips or reduced test count")
    seen, totals = set(), dict.fromkeys(FIELDS, 0)
    for path, row in document["files"].items():
        name = canonical_name(path)
        if name not in expected or name in seen:
            raise ValueError("Unexpected or duplicate coverage file")
        seen.add(name)
        values = row["summary"]
        for key in FIELDS:
            if type(values[key]) is not int or values[key] < 0:
                raise ValueError("Invalid coverage count")
            totals[key] += values[key]
        if (
            values["covered_lines"] > values["num_statements"]
            or values["covered_branches"] > values["num_branches"]
        ):
            raise ValueError("Impossible coverage count")
    if seen != set(expected):
        raise ValueError("Coverage omitted a maintained runtime file")
    if any(totals[key] != document["totals"][key] for key in FIELDS):
        raise ValueError("Coverage totals do not reconcile")
    for numerator, denominator, threshold in (
        ("covered_lines", "num_statements", "minimum_line_percent"),
        ("covered_branches", "num_branches", "minimum_branch_percent"),
    ):
        if totals[denominator] <= 0:
            raise ValueError("Empty coverage denominator")
        if Fraction(100 * totals[numerator], totals[denominator]) < Fraction(
            str(baseline[threshold])
        ):
            raise ValueError("Coverage regressed: " + threshold)
    return totals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=ROOT / "tools/coverage-baseline.json")
    args = parser.parse_args(argv)
    try:
        baseline = json.loads(args.baseline.read_text("utf-8"))
        if (
            baseline["schema_version"] != 1
            or baseline["platform"] != sys.platform
            or baseline["python"] != list(sys.version_info[:2])
        ):
            raise ValueError("This coverage baseline does not qualify this platform/runtime")
        totals = check_report(
            json.loads(args.coverage.read_text("utf-8")),
            json.loads(args.validation.read_text("utf-8")),
            baseline,
            runtime_sources(),
        )
        print(json.dumps({"status": "passed", "scope": "parent_process_only", "totals": totals}))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print("Coverage gate: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
