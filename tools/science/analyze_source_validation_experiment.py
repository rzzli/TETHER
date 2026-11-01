"""Pure descriptive P05d analysis; CLI requires an independently audited ledger.

No producer, compiler, model, source rows, or reference values are imported.
The serialized metrics are data; only the separately pinned P06 audit authorizes
their use by the CLI. Preparation/tests do not authorize an actual analysis.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import stat
import sys
import tempfile

WORKSPACE = Path(__file__).resolve().parents[2]
DERIVED = WORKSPACE / "data/derived"
ASSETS = WORKSPACE / "planning/review-assets/preprint-p05-20261031"
METHOD = "p05.deterministic_source_validation_experiment.v1"
ANALYSIS_METHOD = "p05.descriptive_experiment_analysis.v1"
AUDIT_METHOD = "p05.independent_source_inclusive_experiment_audit.v1"
AUDIT_STATUS = "PASS_INDEPENDENT_EXPERIMENT_AUDIT"
CASES = tuple(f"p05-{i:02d}" for i in range(1, 13))
SCENARIOS = tuple([f"C{i:02d}" for i in range(1, 5)] + [f"F{i:02d}" for i in range(1, 11)])
POLICIES = ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")
TERMINALS = ("returned", "malformed", "failed", "timeout", "interrupted", "unexecuted")
VERDICTS = ("admitted", "rejected", "no_decision")
SHA = re.compile(r"[0-9a-f]{64}\Z")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def schedule():
    """Static contract transcribed from the frozen DRAFT, independent of producer."""
    outputs, decisions = {}, {}
    for case in CASES:
        for arm in ("L", "A"):
            identifier = f"N-{arm}-{case}"
            outputs[identifier] = (case, arm)
            for policy in POLICIES if arm == "L" else ("FULL",):
                decisions[f"D-{identifier}-{policy}"] = (identifier, policy)
    for scenario in SCENARIOS:
        identifier = "S-" + scenario
        outputs[identifier] = (scenario, "fixture")
        for policy in POLICIES:
            decisions[f"D-{identifier}-{policy}"] = (identifier, policy)
    return outputs, decisions


def _index(rows, key, expected):
    need(type(rows) is list and len(rows) == len(expected), f"Exact {len(expected)} {key} records required")
    need(all(type(row) is dict and type(row.get(key)) is str for row in rows), f"Invalid {key} record")
    result = {row[key]: row for row in rows}
    need(len(result) == len(rows) and set(result) == set(expected), f"Duplicate, omitted, or unscheduled {key}")
    return result


def _count(value, label):
    need(type(value) is int and value >= 0, "Invalid count: " + label)
    return value


def _score(row):
    score = row.get("core_score")
    if score is None:
        return {"coverage": None, "thresholds": {k: None for k in ("60", "80", "100")},
                "completion": False, "answerable_facts": None, "answerable_groups": None,
                "family_scores": None, "critical_errors": None, "adapter_status": "not_scored"}
    need(type(score) is dict and score.get("cell_id") == row["cell_id"] and
         score.get("scientific_validation") == "not_established", "Core score identity/scientific scope differs")
    accounting = row.get("fact_accounting")
    need(type(accounting) is dict and type(accounting.get("families")) is dict, "Explicit audited fact accounting required for scored output")
    for name in ("identity_linkage", "reported_context", "reported_measurement", "provider_metric"):
        item = accounting["families"].get(name)
        need(type(item) is dict, "Missing family accounting")
        requested, answerable = _count(item.get("requested"), "requested"), _count(item.get("answerable"), "answerable")
        reasons = item.get("expected_unknown_by_reason")
        need(answerable <= requested and type(reasons) is dict and all(type(k) is str for k in reasons), "Invalid unknown accounting")
        need(sum(_count(n, "unknown reason") for n in reasons.values()) == requested - answerable, "Unknown denominator differs")
        for field in ("matched", "correct_unknown", "omitted", "false_asserted"):
            need(field in item, "Unknown counter must be explicit, not inferred as zero")
            need(item[field] is None or type(item[field]) is int and item[field] >= 0, "Invalid emitted-dependent counter")
    errors = score.get("critical_errors")
    need(type(errors) is list and all(type(x) is dict and type(x.get("reason")) is str for x in errors), "Invalid critical errors")
    family = score.get("family_scores", {}).get("reported_measurement")
    need(type(family) is dict and type(family.get("group_coverage")) is list, "Measurement group counts required")
    groups = family["group_coverage"]
    need(_count(family.get("answerable_groups"), "answerable groups") == len(groups), "Group denominator differs")
    answerable = _count(family.get("answerable_facts"), "answerable facts")
    fractions, total = [], 0
    scorable = score.get("adapter_status") == "scorable"
    for group in groups:
        denominator = _count(group.get("answerable_facts"), "group denominator")
        need(denominator > 0, "Unknown-only groups must not enter answerable denominator")
        total += denominator
        if scorable:
            matched = _count(group.get("matched_facts"), "matched group facts")
            need(matched <= denominator, "Matched count exceeds denominator")
            fractions.append(Fraction(matched, denominator))
        else:
            need(group.get("matched_facts") is None, "Unscorable group has a numeric match count")
    need(total == answerable, "Fact/group denominator differs")
    coverage = sum(fractions, Fraction()) / len(fractions) if fractions else None
    displayed = family.get("coverage")
    need(displayed is None if coverage is None else type(displayed) in (int, float) and
         math.isfinite(displayed) and abs(displayed - float(coverage)) < 1e-12, "Stored coverage differs from group counts")
    eligible = scorable and score.get("answer_status") in ("answered", "partial") and not errors
    thresholds = {key: bool(eligible and coverage >= threshold) if coverage is not None else None
                  for key, threshold in (("60", Fraction(3, 5)), ("80", Fraction(4, 5)), ("100", Fraction(1)))}
    need(score.get("completion") is (thresholds["80"] is True), "Core completion differs from exact grouped threshold")
    need(score.get("primary", {}).get("families") == ["reported_measurement"] or
         score.get("primary", {}).get("families") == ("reported_measurement",), "Unexpected primary family")
    need(score["primary"].get("passes") == thresholds, "Stored thresholds differ from group counts")
    return {"coverage": float(coverage) if coverage is not None else None, "thresholds": thresholds,
            "completion": thresholds["80"] is True, "answerable_facts": answerable,
            "answerable_groups": len(groups), "family_scores": score["family_scores"],
            "critical_errors": dict(Counter(x["reason"] for x in errors)), "adapter_status": score.get("adapter_status")}


def analyze(ledger):
    """Analyze an already audited serialized ledger. Performs no I/O."""
    need(type(ledger) is dict and ledger.get("method") == METHOD and
         ledger.get("scientific_validation") == "not_established", "Wrong experiment/scientific scope")
    need(ledger.get("status") in ("COMPLETED_PENDING_INDEPENDENT_AUDIT", "FAILED_PARTIAL_NOT_QUALIFIED"), "Unknown ledger status")
    need(ledger.get("planned_output_cells") == 38 and ledger.get("planned_decisions") == 90 and
         ledger.get("native_units") == 12 and ledger.get("independent_studies") is None, "Fixed descriptive denominator changed")
    expected_outputs, expected_decisions = schedule()
    outputs = _index(ledger.get("output_cells"), "cell_id", expected_outputs)
    decisions = _index(ledger.get("decision_cells"), "decision_id", expected_decisions)
    for identifier, row in outputs.items():
        case, arm = expected_outputs[identifier]
        need(row.get("case_id") == case and row.get("arm") == arm, "Output schedule association differs")
        need(row.get("stratum") == "native" if case in CASES else
             row.get("stratum") in ("fictional_json_core", "constructed_fictional"), "Output stratum differs")
        need(row.get("terminal") in TERMINALS and row.get("received_terminal") in (None,) + TERMINALS, "Unknown output terminal")
        for flag in ("strict_exact_report", "full_source_admitted", "full_verified_exact"):
            need(row.get(flag) is None or type(row[flag]) is bool, "Invalid admission flag")
        if row.get("full_verified_exact") is True:
            need(row.get("full_source_admitted") is True and row.get("strict_exact_report") is True and
                 row["terminal"] == "returned" and type(row.get("core_score")) is dict,
                 "Exact acceptance lacks source admission/complete return/genuine scored metadata")
    for identifier, row in decisions.items():
        output, policy = expected_decisions[identifier]
        need(row.get("output_cell_id") == output and row.get("policy") == policy and
             row.get("verdict") in VERDICTS and row.get("terminal") in TERMINALS, "Decision schedule/terminal differs")
        need(row["verdict"] == "no_decision" or row["terminal"] == "returned", "Failed/unexecuted decision cannot count as rejection/admission")
        if row["policy"] == "FULL":
            need((row["verdict"] == "admitted") == (outputs[output].get("full_verified_exact") is True),
                 "FULL verdict/exact acceptance differs")
    qualification = ledger.get("native_qualification")
    need(type(qualification) is dict and set(qualification) == set(CASES), "Qualification inventory must include all twelve units")
    case_rows, secondary, unknown_qualification = [], [], []
    for case in CASES:
        q = qualification[case]
        need(q.get("disposition") in ("compiled", "blocked", "unverified"), "Unknown native qualification")
        if q["disposition"] == "compiled":
            facts = _count(q.get("measurement_answerable_facts"), "qualified facts")
            groups = _count(q.get("measurement_answerable_groups"), "qualified groups")
            need((facts == 0) == (groups == 0) and groups <= facts, "Qualified denominator inconsistent")
            if groups:
                secondary.append(case)
        else:
            need(q.get("measurement_answerable_facts") is None and q.get("measurement_answerable_groups") is None,
                 "Unqualified case has an invented denominator")
            if q["disposition"] == "unverified":
                unknown_qualification.append(case)
        arms = {}
        for arm in ("L", "A"):
            row = outputs[f"N-{arm}-{case}"]
            score = _score(row)
            if score["answerable_groups"] is not None:
                need(q["disposition"] == "compiled" and score["answerable_groups"] == q["measurement_answerable_groups"] and
                     score["answerable_facts"] == q["measurement_answerable_facts"], "Scored/qualified denominator differs")
            qualified_return = row.get("full_source_admitted") is True and row["terminal"] == "returned"
            need(not qualified_return or q["disposition"] == "compiled", "Source admission contradicts native qualification")
            arms[arm] = {"terminal": row["terminal"], "received_terminal": row.get("received_terminal"),
                        "exact_report": row.get("strict_exact_report"), "verified_exact": row.get("full_verified_exact") is True,
                        "completion_80": qualified_return and score["completion"], **score,
                        "fact_accounting": row.get("fact_accounting")}
            arms[arm]["completion_80"] = qualified_return and score["completion"]
        case_rows.append({"case_id": case, "qualification": q, "literal": arms["L"], "abstain": arms["A"],
                          "coverage_difference": arms["L"]["coverage"] - arms["A"]["coverage"]
                          if arms["L"]["coverage"] is not None and arms["A"]["coverage"] is not None else None})
    exact = sum(row["literal"]["verified_exact"] for row in case_rows)
    completed = sum(row["literal"]["completion_80"] for row in case_rows)
    secondary_completed = sum(row["literal"]["completion_80"] for row in case_rows if row["case_id"] in secondary)
    fictional_cases = []
    for scenario in SCENARIOS:
        row = outputs["S-" + scenario]
        metrics = _score(row)
        fictional_cases.append({"scenario_id": scenario, "terminal": row["terminal"],
            "received_terminal": row.get("received_terminal"), "exact_report": row.get("strict_exact_report"),
            "source_admitted": row.get("full_source_admitted"), "verified_exact": row.get("full_verified_exact"),
            "measurement_coverage": metrics["coverage"], "measurement_completion": metrics["completion"] if row.get("core_score") is not None else None,
            "answerable_measurement_groups": metrics["answerable_groups"], "critical_errors": metrics["critical_errors"],
            "fact_accounting": row.get("fact_accounting")})
    fictional, paired = {}, {}
    for policy in POLICIES:
        valid, invalid = [], []
        for scenario in SCENARIOS:
            row = decisions[f"D-S-{scenario}-{policy}"]
            (valid if scenario.startswith("C") else invalid).append(row)
        def counts(rows, *, invalid):
            attempted = sum(row["verdict"] != "no_decision" for row in rows)
            errors = sum(row["verdict"] == ("admitted" if invalid else "rejected") for row in rows)
            return {"planned_denominator": len(rows), "attempted_denominator": attempted,
                    "no_decision": len(rows) - attempted, "error_count": errors,
                    "error_rate_planned": errors / len(rows), "error_rate_attempted": errors / attempted if attempted else None}
        fictional[policy] = {"false_acceptance": counts(invalid, invalid=True), "false_rejection": counts(valid, invalid=False),
                             "scenarios": [{"scenario_id": scenario, "truth": "VALID_REPORT" if scenario.startswith("C") else "INVALID",
                                            "verdict": decisions[f"D-S-{scenario}-{policy}"]["verdict"],
                                            "first_failure_stage": decisions[f"D-S-{scenario}-{policy}"].get("first_failure_stage")}
                                           for scenario in SCENARIOS]}
    for left, right in (("FULL", "WITHOUT_WRAPPER"), ("FULL", "WIRE_ONLY"), ("WITHOUT_WRAPPER", "WIRE_ONLY")):
        table = Counter((decisions[f"D-S-{key}-{left}"]["verdict"], decisions[f"D-S-{key}-{right}"]["verdict"]) for key in SCENARIOS)
        paired[left + "_vs_" + right] = {"planned_pairs": 14, "both_attempted": sum(n for (a, b), n in table.items() if "no_decision" not in (a, b)),
                                        "discordant_attempted": sum(n for (a, b), n in table.items() if a != b and "no_decision" not in (a, b)),
                                        "cells": [{"left": a, "right": b, "count": table[(a, b)]} for a in VERDICTS for b in VERDICTS]}
    native_paired = {"planned_pairs": 12, "cells": dict(Counter(
        decisions[f"D-N-L-{case}-FULL"]["verdict"] + "/" + decisions[f"D-N-A-{case}-FULL"]["verdict"] for case in CASES))}
    native_policy_pairs = {}
    for left, right in (("FULL", "WITHOUT_WRAPPER"), ("FULL", "WIRE_ONLY"), ("WITHOUT_WRAPPER", "WIRE_ONLY")):
        table = Counter((decisions[f"D-N-L-{case}-{left}"]["verdict"], decisions[f"D-N-L-{case}-{right}"]["verdict"]) for case in CASES)
        native_policy_pairs[left + "_vs_" + right] = {"planned_pairs": 12,
            "both_attempted": sum(n for (a, b), n in table.items() if "no_decision" not in (a, b)),
            "discordant_attempted": sum(n for (a, b), n in table.items() if a != b and "no_decision" not in (a, b)),
            "cells": [{"left": a, "right": b, "count": table[(a, b)]} for a in VERDICTS for b in VERDICTS]}
    return {"schema_version": 1, "method": ANALYSIS_METHOD, "source_ledger_status": ledger["status"],
            "scientific_validation": "not_established", "inferential_statistics": "none", "independent_study_count": None,
            "planned_output_cells": 38, "planned_decisions": 90, "native_denominator": 12,
            "native_primary": {"verified_exact_count": exact, "verified_exact_rate": exact / 12,
                               "completion_80_count": completed, "completion_80_rate": completed / 12},
            "native_secondary": {"known_qualified_nonzero_count": len(secondary), "unverified_qualification_count": len(unknown_qualification),
                                 "qualified_nonzero_denominator": len(secondary) if not unknown_qualification else None,
                                 "completion_80_count": secondary_completed,
                                 "completion_80_rate": secondary_completed / len(secondary) if secondary and not unknown_qualification else None},
            "native_cases": case_rows, "native_literal_abstain_pairing": native_paired,
            "native_policy_paired_discordance": native_policy_pairs,
            "fictional_cases": fictional_cases, "fictional_policies": fictional, "fictional_paired_discordance": paired,
            "output_terminal_counts": dict(Counter(row["terminal"] for row in outputs.values())),
            "decision_verdict_counts": dict(Counter(row["verdict"] for row in decisions.values())),
            "resources": ledger.get("resources"), "amortized_source_verification": ledger.get("source_verification"),
            "core_aggregate_scope": "secondary genuine-scored subset only; fixed38/90 ledger is primary",
            "limitations": ["Finite selected source units, not independent studies.", "Designed controls do not estimate natural fault prevalence.",
                            "No confidence intervals, significance tests, power or causal/clinical claims."]}


def _pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _parse(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def checked_existing(path):
    path = Path(path)
    need(path.is_absolute(), "Absolute local path required")
    for component in reversed((path,) + tuple(path.parents)):
        info = component.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "Symlink/reparse path denied")
    return path


def read_pinned(path, expected_sha256):
    need(type(expected_sha256) is str and SHA.fullmatch(expected_sha256), "Independent byte SHA256 required")
    path = checked_existing(path)
    before = path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= 16 * 1024**2, "Bounded regular JSON input required")
    with path.open("rb") as stream:
        raw = stream.read(16 * 1024**2 + 1)
        during = stream.fileno()
        opened = os.fstat(during)
    after = path.stat()
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns)
    need(identity(before) == identity(opened) == identity(after) and len(raw) == before.st_size, "Input changed during read")
    need(hashlib.sha256(raw).hexdigest() == expected_sha256, "Externally pinned bytes differ")
    return raw


def validate_audit(audit, ledger_path, ledger_sha256):
    need(type(audit) is dict and audit.get("status") == AUDIT_STATUS and audit.get("method") == AUDIT_METHOD and
         audit.get("source_inclusive") is True and audit.get("independent_projection") is True and
         audit.get("unresolved_findings") == [] and audit.get("scientific_validation") == "not_established", "P06 independent source-inclusive audit required")
    need(audit.get("subject") == {"ledger_path": str(Path(ledger_path)), "ledger_sha256": ledger_sha256}, "Audit is bound to another ledger")


def _publish(path, raw):
    """Atomic no-clobber publication; only newly reserved analysis directory."""
    fd, name = tempfile.mkstemp(prefix=".publishing-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "nt":
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run(ledger_path, ledger_sha256, audit_path, audit_sha256, output, *, approved_ledger_root, approved_audit_root):
    ledger_path, audit_path = Path(ledger_path), Path(audit_path)
    lr, ar, output = Path(approved_ledger_root), Path(approved_audit_root), Path(output)
    need(lr.parent == DERIVED and re.fullmatch(r"preprint-p05-experiment-\d{8}T\d{6}Z", lr.name) and
         ledger_path == lr / "ledger.json", "Root-approved experiment ledger location required")
    need(ar == ASSETS or ar.parent == DERIVED and re.fullmatch(r"preprint-p05-experiment-audit-\d{8}T\d{6}Z", ar.name),
         "Root-approved P06 audit root required")
    need(audit_path.parent == ar and audit_path.name.endswith(".json"), "Audit path outside approved root")
    need(output.parent == DERIVED and re.fullmatch(r"preprint-p05-analysis-\d{8}T\d{6}Z", output.name), "Fresh approved analysis location required")
    checked_existing(DERIVED)
    try:
        output.lstat()
    except FileNotFoundError:
        pass
    else:
        raise ValueError("Output exists; no overwrite/resume")
    # Authenticate both exact byte sequences before parsing or summarizing data.
    ledger_raw, audit_raw = read_pinned(ledger_path, ledger_sha256), read_pinned(audit_path, audit_sha256)
    validate_audit(_parse(audit_raw), ledger_path, ledger_sha256)
    ledger = _parse(ledger_raw)
    summary = analyze(ledger)
    code_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    frozen_code = ledger.get("analysis_code_sha256")
    if frozen_code is not None:
        need(type(frozen_code) is str and SHA.fullmatch(frozen_code) and frozen_code == code_sha256,
             "Current analyzer differs from audited ledger's frozen analysis pin")
    execution = {"analyzer_sha256": code_sha256, "ledger_path": str(ledger_path), "ledger_sha256": ledger_sha256,
                 "audit_path": str(audit_path), "audit_sha256": audit_sha256,
                 "frozen_analysis_pin_match": True if frozen_code is not None else None,
                 "code_policy": "exact ledger pin when present; otherwise root must independently match READY before P07",
                 "environment": {"interpreter": str(Path(sys.executable).absolute()), "python": platform.python_version(),
                                 "platform": sys.platform, "dependencies": "Python standard library only"},
                 "created_at_utc": datetime.now(timezone.utc).isoformat()}
    summary["execution"] = execution
    output.mkdir(exist_ok=False)
    checked_existing(output)
    raw = canonical(summary) + b"\n"
    _publish(output / "analysis.json", raw)
    seal = {"schema_version": 1, "status": "DESCRIPTIVE_ANALYSIS_OF_INDEPENDENTLY_AUDITED_LEDGER",
            "method": ANALYSIS_METHOD, "ledger_sha256": ledger_sha256, "audit_sha256": audit_sha256,
            "code_sha256": code_sha256, "environment": execution["environment"],
            "frozen_analysis_pin_match": execution["frozen_analysis_pin_match"],
            "analysis_sha256": hashlib.sha256(raw).hexdigest(), "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "scientific_validation": "not_established", "model_calls": 0, "network_calls": 0}
    _publish(output / "analysis-seal.json", canonical(seal) + b"\n")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger", "ledger-sha256", "audit", "audit-sha256", "approved-ledger-root", "approved-audit-root", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    run(args.ledger, args.ledger_sha256, args.audit, args.audit_sha256, args.output,
        approved_ledger_root=args.approved_ledger_root, approved_audit_root=args.approved_audit_root)


if __name__ == "__main__":
    main()
