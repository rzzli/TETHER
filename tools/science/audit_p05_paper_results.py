"""Read-only independent P05 descriptive analysis/presentation audit.

Only the pinned P06 ledger, its independent source audit, the retained analysis
and final paper assets are read. No raw sources, source-reference expected facts,
generation packets, producer/analyzer imports, models or network are used.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import re
import struct
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "planning/review-assets/preprint-p05-20261031"
LEDGER = ROOT / "data/derived/preprint-p05-experiment-20261101T091345Z/ledger.json"
AUDIT = ASSETS / "EXPERIMENT-AUDIT-v1.json"
ANALYSIS = ROOT / "data/derived/preprint-p05-analysis-20261101T092110Z/analysis.json"
PINS = {"ledger": "b2a9727ca9ce89865b80ffe80b21a325ea6d91d8844247740ac2c2ecc9a4faa0",
        "audit": "f10f15959f8497821115f65268808c98ae345079c7361722390a479b15506922",
        "analysis": "ee9f02ea3c3692bbd8b7d63d2d2cd545cfd769ccee9ee7454b4ed00c7ac87312"}
CASES = tuple("p05-" + str(i).zfill(2) for i in range(1, 13))
SCENARIOS = tuple(["C" + str(i).zfill(2) for i in range(1, 5)] + ["F" + str(i).zfill(2) for i in range(1, 11)])
POLICIES = ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")
VERDICTS = ("admitted", "rejected", "no_decision")
FAMILIES = ("identity_linkage", "reported_context", "reported_measurement", "provider_metric")
REPORT = {"schema_version": 1, "method": "p05.independent_analysis_presentation_audit.v1", "checks": {}, "unresolved_findings": [],
          "scientific_validation": "not_established", "models": 0, "network_calls": 0, "raw_source_or_reference_expected_values_read": False}
REPORT["retained_prior_audit_attempts"] = [{"report": "ANALYSIS-PRESENTATION-AUDIT-v1-attempt1.json", "sha256": "84c7030a13c3b2047901e2f6bd5d5e3ab69a295e86289eb0ed3717a5f76c3dbf",
    "checker": "audit_p05_paper_results_attempt1.py", "checker_sha256": "ae83008965efd6cb6c357126f2ce64310d21494dbcffb3904b70d3de1a1c43f1",
    "disposition": "four checker comparison defects corrected; no asset or frozen analysis changes", "corrections": ["unavailable unscored error metadata remains null", "structured ledger scope versus descriptive analysis label", "resource-label spacing", "1e-9 point SVG floating serialization tolerance"]}]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def equal(left, right):
    return canonical(left) == canonical(right)


def check(name, condition, **detail):
    REPORT["checks"][name] = {"pass": bool(condition), **detail}
    if not condition:
        REPORT["unresolved_findings"].append(name)


def need(name, condition):
    check(name, condition)
    if not condition:
        raise AssertionError(name)


def qualification_rows(value):
    return dict(value) if type(value) is dict else {row["case_id"]: row for row in value}


def cell_summary(output):
    score = output.get("core_score")
    if score is None:
        return {"terminal": output["terminal"], "received_terminal": output.get("received_terminal"), "adapter_status": None,
                "exact_report": output.get("strict_exact_report"), "verified_exact": output.get("full_verified_exact"), "completion_80": False,
                "coverage": None, "answerable_facts": None, "answerable_groups": None, "thresholds": {k: None for k in ("60", "80", "100")},
                "critical_errors": None, "completion": None, "fact_accounting": output.get("fact_accounting"), "family_scores": None}
    measurement = score["family_scores"]["reported_measurement"]
    fractions = [Fraction(group["matched_facts"], group["answerable_facts"]) for group in measurement["group_coverage"] if group["answerable_facts"] and group["matched_facts"] is not None]
    coverage = sum(fractions, Fraction()) / len(fractions) if fractions and score["adapter_status"] == "scorable" else None
    eligible = score["adapter_status"] == "scorable" and score["answer_status"] in ("answered", "partial") and not score["critical_errors"]
    thresholds = {key: bool(eligible and coverage >= threshold) if coverage is not None else None for key, threshold in (("60", Fraction(3, 5)), ("80", Fraction(4, 5)), ("100", Fraction(1)))}
    check("group_derived_measurement_coverage_" + output["cell_id"], measurement["coverage"] == (float(coverage) if coverage is not None else None))
    # Every frozen task has reported_measurement as its sole primary family.
    check("group_derived_thresholds_" + output["cell_id"], score["primary"]["passes"] == thresholds and score["completion"] is (thresholds["80"] is True))
    return {"terminal": output["terminal"], "received_terminal": output.get("received_terminal"), "adapter_status": score["adapter_status"],
            "exact_report": output.get("strict_exact_report"), "verified_exact": output.get("full_verified_exact"),
            "completion_80": bool(output.get("full_source_admitted") and thresholds["80"] is True), "coverage": float(coverage) if coverage is not None else None,
            "answerable_facts": measurement["answerable_facts"], "answerable_groups": measurement["answerable_groups"], "thresholds": thresholds,
            "critical_errors": dict(Counter(error["reason"] for error in score["critical_errors"])), "completion": score["completion"],
            "fact_accounting": output.get("fact_accounting"), "family_scores": score["family_scores"]}


def paired(decisions, ids, left, right):
    values = [(decisions[(key, left)]["verdict"], decisions[(key, right)]["verdict"]) for key in ids]
    counts = Counter(values)
    return {"planned_pairs": len(ids), "both_attempted": sum(l != "no_decision" and rr != "no_decision" for l, rr in values),
            "discordant_attempted": sum(l != rr and l != "no_decision" and rr != "no_decision" for l, rr in values),
            "cells": [{"left": l, "right": rr, "count": counts[(l, rr)]} for l in VERDICTS for rr in VERDICTS]}


def recompute(ledger, source_audit):
    """Independent arithmetic over the source-audited ledger; no analyzer oracle."""
    need("independent_source_audit_subject", source_audit["status"] == "PASS_INDEPENDENT_EXPERIMENT_AUDIT" and source_audit["subject"]["ledger_sha256"] == PINS["ledger"] and Path(source_audit["subject"]["ledger_path"]) == LEDGER and source_audit["source_inclusive"] is True and source_audit["independent_projection"] is True and source_audit["unresolved_findings"] == [] and source_audit["scientific_validation"] == "not_established")
    outputs, decisions = ledger["output_cells"], ledger["decision_cells"]
    expected_outputs = ["N-" + arm + "-" + case for case in CASES for arm in ("L", "A")] + ["S-" + key for key in SCENARIOS]
    expected_decisions = ["D-N-" + arm + "-" + case + "-" + policy for case in CASES for arm in ("L", "A") for policy in POLICIES if arm == "L" or policy == "FULL"] + ["D-S-" + key + "-" + policy for key in SCENARIOS for policy in POLICIES]
    need("fixed_all38_outputs", [o["cell_id"] for o in outputs] == expected_outputs and len(set(expected_outputs)) == 38)
    need("fixed_all90_decisions", [d["decision_id"] for d in decisions] == expected_decisions and len(set(expected_decisions)) == 90)
    output_map = {o["cell_id"]: o for o in outputs}
    decision_map = {(d["output_cell_id"], d["policy"]): d for d in decisions}
    qualification = qualification_rows(ledger["native_qualification"])
    need("qualification_all12_no_removed_denominators", list(qualification) == list(CASES))
    native, totals = [], {family: Counter() for family in FAMILIES}
    expected_unknowns = Counter()
    threshold_totals = {arm: Counter() for arm in ("L", "A")}
    for case in CASES:
        literal, abstain = output_map["N-L-" + case], output_map["N-A-" + case]
        lv, av = cell_summary(literal), cell_summary(abstain)
        native.append({"case_id": case, "literal": lv, "abstain": av,
                       "coverage_difference": lv["coverage"] - av["coverage"] if lv["coverage"] is not None and av["coverage"] is not None else None,
                       "qualification": qualification[case]})
        for arm, row in (("L", lv), ("A", av)):
            threshold_totals[arm].update(key for key, value in row["thresholds"].items() if value is True)
        for family, row in literal["fact_accounting"]["families"].items():
            totals[family].update({key: row[key] for key in ("requested", "answerable", "matched", "correct_unknown", "omitted", "false_asserted")})
            expected_unknowns.update(row["expected_unknown_by_reason"])
        check("source_audit_native_summary_" + case, source_audit["independent_cell_summary"][literal["cell_id"]]["exact"] is literal["strict_exact_report"] and source_audit["independent_cell_summary"][literal["cell_id"]]["completion"] is literal["core_score"]["completion"])
    verified_exact = sum(row["literal"]["verified_exact"] is True for row in native)
    completed = sum(row["literal"]["completion_80"] is True for row in native)
    qualified = [case for case in CASES if qualification[case]["disposition"] == "compiled" and qualification[case]["measurement_answerable_groups"] > 0]
    secondary_completed = sum(output_map["N-L-" + case]["full_source_admitted"] and cell_summary(output_map["N-L-" + case])["completion_80"] for case in qualified)
    policies, fictional_cases = {}, []
    for key in SCENARIOS:
        output = output_map["S-" + key]
        view = cell_summary(output)
        fictional_cases.append({"scenario_id": key, "terminal": output["terminal"], "received_terminal": output.get("received_terminal"),
            "source_admitted": output.get("full_source_admitted"), "exact_report": output.get("strict_exact_report"), "verified_exact": output.get("full_verified_exact"),
            "measurement_completion": view["completion"], "measurement_coverage": view["coverage"], "answerable_measurement_groups": view["answerable_groups"],
            "critical_errors": view["critical_errors"], "fact_accounting": output.get("fact_accounting")})
    for policy in POLICIES:
        scenarios = []
        for key in SCENARIOS:
            row = decision_map[("S-" + key, policy)]
            truth = "VALID_REPORT" if key.startswith("C") else "INVALID"
            check("predeclared_fixture_truth_" + key + "_" + policy, row["fixture_truth"] == truth)
            scenarios.append({"scenario_id": key, "truth": truth, "verdict": row["verdict"], "first_failure_stage": row["first_failure_stage"]})
        result = {"scenarios": scenarios}
        for name, truth, error in (("false_acceptance", "INVALID", "admitted"), ("false_rejection", "VALID_REPORT", "rejected")):
            subset = [row for row in scenarios if row["truth"] == truth]
            attempted = sum(row["verdict"] != "no_decision" for row in subset)
            errors = sum(row["verdict"] == error for row in subset)
            result[name] = {"planned_denominator": len(subset), "attempted_denominator": attempted, "error_count": errors,
                            "error_rate_planned": errors / len(subset), "error_rate_attempted": errors / attempted if attempted else None,
                            "no_decision": len(subset) - attempted}
        policies[policy] = result
    combinations = (("FULL", "WIRE_ONLY"), ("FULL", "WITHOUT_WRAPPER"), ("WITHOUT_WRAPPER", "WIRE_ONLY"))
    native_pairs = {l + "_vs_" + rr: paired(decision_map, ["N-L-" + c for c in CASES], l, rr) for l, rr in combinations}
    fictional_pairs = {l + "_vs_" + rr: paired(decision_map, ["S-" + key for key in SCENARIOS], l, rr) for l, rr in combinations}
    native_la = Counter(decision_map[("N-L-" + case, "FULL")]["verdict"] + "/" + decision_map[("N-A-" + case, "FULL")]["verdict"] for case in CASES)
    expected = {"planned_output_cells": len(outputs), "planned_decisions": len(decisions), "native_denominator": len(CASES),
        "output_terminal_counts": dict(Counter(o["terminal"] for o in outputs)), "decision_verdict_counts": dict(Counter(d["verdict"] for d in decisions)),
        "native_primary": {"verified_exact_count": verified_exact, "verified_exact_rate": verified_exact / len(CASES), "completion_80_count": completed, "completion_80_rate": completed / len(CASES)},
        "native_secondary": {"known_qualified_nonzero_count": len(qualified), "qualified_nonzero_denominator": len(qualified), "unverified_qualification_count": sum(q["disposition"] == "unverified" for q in qualification.values()), "completion_80_count": secondary_completed, "completion_80_rate": secondary_completed / len(qualified) if qualified else None},
        "native_cases": native, "native_literal_abstain_pairing": {"planned_pairs": len(CASES), "cells": dict(native_la)},
        "native_policy_paired_discordance": native_pairs, "fictional_cases": fictional_cases, "fictional_policies": policies, "fictional_paired_discordance": fictional_pairs,
        "resources": ledger["resources"], "amortized_source_verification": ledger["source_verification"], "core_aggregate_scope": f"secondary genuine-scored subset only; fixed{len(outputs)}/{len(decisions)} ledger is primary",
        "source_ledger_status": ledger["status"], "scientific_validation": "not_established", "independent_study_count": None, "inferential_statistics": "none"}
    extras = {"native_literal_family_totals": {k: dict(v) for k, v in totals.items()}, "native_expected_unknowns": dict(expected_unknowns),
              "native_threshold_pass_counts": {arm: {key: threshold_totals[arm][key] for key in ("60", "80", "100")} for arm in ("L", "A")},
              "received_terminal_counts": dict(Counter(o.get("received_terminal") for o in outputs)),
              "abstain_emitted_facts": sum(output_map["N-A-" + c]["core_score"]["emitted_facts"] for c in CASES),
              "abstain_critical_errors": sum(len(output_map["N-A-" + c]["core_score"]["critical_errors"]) for c in CASES),
              "abstain_false_assertions": sum(f["false_asserted"] for c in CASES for f in output_map["N-A-" + c]["fact_accounting"]["families"].values())}
    operations = []
    for case in CASES:
        literal, abstain = output_map["N-L-" + case], output_map["N-A-" + case]
        shared = literal["shared_case_generation_resources"]
        check("shared_pair_resource_not_doubled_" + case, equal(shared, abstain["shared_case_generation_resources"]))
        operations.append({"case_id": case, "generation_wall_seconds": shared["wall_seconds"], "generation_cpu_seconds": shared["cpu_seconds"],
                           "literal_scoring_wall_seconds": literal["scoring_resources"]["wall_seconds"], "literal_scoring_cpu_seconds": literal["scoring_resources"]["cpu_seconds"],
                           "abstain_scoring_wall_seconds": abstain["scoring_resources"]["wall_seconds"], "abstain_scoring_cpu_seconds": abstain["scoring_resources"]["cpu_seconds"]})
    extras["native_operation_resources"] = operations
    extras["deduplicated_generation_resources"] = {"wall_seconds": sum(row["generation_wall_seconds"] for row in operations), "cpu_seconds": sum(row["generation_cpu_seconds"] for row in operations), "native_pairs": len(operations)}
    extras["native_scoring_resources"] = {"wall_seconds": sum(row["literal_scoring_wall_seconds"] + row["abstain_scoring_wall_seconds"] for row in operations), "cpu_seconds": sum(row["literal_scoring_cpu_seconds"] + row["abstain_scoring_cpu_seconds"] for row in operations), "scored_native_outputs": 2 * len(operations)}
    extras["source_audit_resources"] = source_audit["cost"]
    extras["combined_completed_logical_hash_bytes"] = ledger["resources"]["logical_completed_hash_bytes"] + source_audit["cost"]["logical_completed_hash_bytes"]
    scores = ledger["core_aggregate"]["case_results"]
    extras["secondary_core_subset"] = {"planned_cells": len(scores), "scorable_cells": sum(score["adapter_status"] == "scorable" for score in scores),
                                        "completion_count": sum(score["completion"] for score in scores), "terminal_counts": dict(Counter(score["terminal"] for score in scores)),
                                        "correct_missing_input_count": sum(score["correct_missing_input"] is True for score in scores),
                                        "correct_missing_input_denominator": sum(score["correct_missing_input"] is not None for score in scores)}
    scope = ledger["core_aggregate_scope"]
    included = [output["cell_id"] for output in outputs if output.get("core_score") is not None]
    check("structured_secondary_score_scope", scope["included_cell_ids"] == scope["intended_cell_ids"] == included and scope["excluded_cell_ids"] == [output["cell_id"] for output in outputs if output.get("core_score") is None] and "secondary" in scope["label"] and "primary" in scope["label"])
    return expected, extras


def expected_tables(ledger, audit, expected, extras):
    """Presentation schemas only; every quantity comes from independent arithmetic."""
    cells = {row["cell_id"]: row for row in ledger["output_cells"]}
    native_rows, facts, missing, operations = [], [], [], []
    for case in expected["native_cases"]:
        cid = case["case_id"]
        meas = case["literal"]["fact_accounting"]["families"]["reported_measurement"]
        identity = case["literal"]["fact_accounting"]["families"]["identity_linkage"]
        unknown = meas["expected_unknown_by_reason"]
        missing.append({"case_id": cid, "measurement_requested": meas["requested"], "measurement_answerable": meas["answerable"],
            "measurement_null": unknown.get("null_source_value", 0), "measurement_absent": unknown.get("field_not_in_schema", 0), "measurement_empty": unknown.get("empty_source_value", 0),
            "measurement_other_unknown": sum(v for k, v in unknown.items() if k not in ("null_source_value", "field_not_in_schema", "empty_source_value")),
            "measurement_groups": case["qualification"]["measurement_answerable_groups"], "identity_requested": identity["requested"], "identity_answerable": identity["answerable"],
            "identity_null": identity["expected_unknown_by_reason"].get("null_source_value", 0), "other_exposure": "UNKNOWN", "independent_studies": "not_established"})
        pair = cells["N-L-" + cid]["shared_case_generation_resources"]
        operations.append({"case_id": cid, "shared_pair_wall_seconds": pair["wall_seconds"], "shared_pair_cpu_seconds": pair["cpu_seconds"],
            "literal_scoring_wall_seconds": cells["N-L-" + cid]["scoring_resources"]["wall_seconds"], "literal_scoring_cpu_seconds": cells["N-L-" + cid]["scoring_resources"]["cpu_seconds"],
            "abstain_scoring_wall_seconds": cells["N-A-" + cid]["scoring_resources"]["wall_seconds"], "abstain_scoring_cpu_seconds": cells["N-A-" + cid]["scoring_resources"]["cpu_seconds"],
            "basis": "one shared packet-read/generation pair per case; scoring per returned arm"})
        for arm, key in (("L", "literal"), ("A", "abstain")):
            view, raw = case[key], cells["N-" + arm + "-" + cid]
            measurement = view["fact_accounting"]["families"]["reported_measurement"]
            native_rows.append({"case_id": cid, "arm": arm, "method": "literal" if arm == "L" else "always_abstain", "terminal": view["terminal"],
                "emitted_facts": raw["core_score"]["emitted_facts"], "source_admitted": raw["full_source_admitted"], "exact_report": view["exact_report"], "verified_exact": view["verified_exact"],
                "measurement_coverage": view["coverage"], "answerable_measurement_components": view["answerable_facts"], "answerable_measurement_groups": view["answerable_groups"],
                "pass_60": view["thresholds"]["60"], "pass_80": view["thresholds"]["80"], "pass_100": view["thresholds"]["100"], "completion_80": view["completion_80"],
                "measurement_matched": measurement["matched"], "measurement_correct_unknown": measurement["correct_unknown"], "measurement_omitted": measurement["omitted"],
                "measurement_false_asserted": measurement["false_asserted"], "critical_error_count": sum(view["critical_errors"].values()), "unknown_fact_id_emissions": view["fact_accounting"]["unknown_fact_id_emissions"]})
            for family in sorted(FAMILIES):
                fact = view["fact_accounting"]["families"][family]
                facts.append({"case_id": cid, "arm": arm, "family": family, "requested": fact["requested"], "answerable": fact["answerable"], "answerable_groups": view["family_scores"][family]["answerable_groups"],
                    "family_coverage": view["family_scores"][family]["coverage"], "matched": fact["matched"], "correct_unknown": fact["correct_unknown"], "omitted": fact["omitted"],
                    "false_asserted": fact["false_asserted"], "expected_unknown_by_reason": fact["expected_unknown_by_reason"]})
    control_rows, control_display, policy_rows = [], [], []
    fictional = {row["scenario_id"]: row for row in expected["fictional_cases"]}
    verdict_text = {}
    for policy in POLICIES:
        stats = expected["fictional_policies"][policy]
        for row in stats["scenarios"]:
            key = row["scenario_id"]
            view = fictional[key]
            guards = ledger["guards"]["S-" + key]
            control_rows.append({"scenario_id": key, "truth": row["truth"], "policy": policy, "verdict": row["verdict"], "first_failure_stage": row["first_failure_stage"], "terminal": view["terminal"],
                **{g: guards[g]["status"] for g in ("G0", "G1", "G2", "G3", "G4")}, "schema_status": guards["G4"]["schema_status"], "core_exact_report": view["exact_report"],
                "full_source_admitted": view["source_admitted"], "full_verified_exact": view["verified_exact"], "measurement_coverage": view["measurement_coverage"],
                "measurement_completion": view["measurement_completion"], "answerable_measurement_groups": view["answerable_measurement_groups"]})
            verdict_text[(key, policy)] = row["verdict"] + (" (" + row["first_failure_stage"] + ")" if row["first_failure_stage"] else "")
        fa, fr = stats["false_acceptance"], stats["false_rejection"]
        policy_rows.append({"policy": policy, "invalid_admitted": fa["error_count"], "invalid_planned": fa["planned_denominator"], "invalid_attempted": fa["attempted_denominator"], "invalid_no_decision": fa["no_decision"],
                            "valid_rejected": fr["error_count"], "valid_planned": fr["planned_denominator"], "valid_attempted": fr["attempted_denominator"], "valid_no_decision": fr["no_decision"]})
    for key in SCENARIOS:
        control_display.append({"scenario_id": key, "truth": "VALID_REPORT" if key.startswith("C") else "INVALID", **{p: verdict_text[(key, p)] for p in POLICIES}})
    pair_summary, pair_cells = [], []
    for stratum, collection in (("native_literal_policies", expected["native_policy_paired_discordance"]), ("constructed_controls", expected["fictional_paired_discordance"])):
        for comparison in sorted(collection):
            value = collection[comparison]
            pair_summary.append({"stratum": stratum, "comparison": comparison, **{k: value[k] for k in ("planned_pairs", "both_attempted", "discordant_attempted")}})
            pair_cells.extend({"stratum": stratum, "comparison": comparison, "left_verdict": cell["left"], "right_verdict": cell["right"], "count": cell["count"]} for cell in value["cells"])
    la = expected["native_literal_abstain_pairing"]
    attempted = sum(value for key, value in la["cells"].items() if "no_decision" not in key)
    discordant = sum(value for key, value in la["cells"].items() if "no_decision" not in key and key.split("/")[0] != key.split("/")[1])
    pair_summary.append({"stratum": "native_literal_abstain", "comparison": "literal_FULL_vs_always_abstain_FULL", "planned_pairs": la["planned_pairs"], "both_attempted": attempted, "discordant_attempted": discordant})
    pair_cells.extend({"stratum": "native_literal_abstain", "comparison": "literal_FULL_vs_always_abstain_FULL", "left_verdict": left, "right_verdict": right, "count": la["cells"].get(left + "/" + right, 0)} for left in VERDICTS for right in VERDICTS)
    producer, wrapper, audit_cost = ledger["resources"], ledger["source_verification"]["wrapper_resources"], audit["cost"]
    def phase(name, basis, wall, cpu=None, rss=None, peak=None, hashes=None, overlap="none"):
        return {"phase": name, "basis": basis, "wall_seconds": wall, "cpu_seconds": cpu, "sampled_process_rss_bytes": rss, "process_lifetime_peak_bytes": peak,
                "logical_completed_hash_bytes": hashes, "partial_failed_hash_bytes": None, "physical_io_bytes": None, "platform_cost_usd": None, "overlap": overlap, "scientific_validation": "not_established"}
    resources = [phase("producer_total", f"all {len(ledger['output_cells'])} outputs/{len(ledger['decision_cells'])} decisions plus source verification/retention", producer["wall_seconds"], producer["cpu_seconds"], producer["peak_sampled_process_rss_bytes"], producer["process_lifetime_peak_bytes"], producer["logical_completed_hash_bytes"]),
        phase("native_generation_pairs", "12 shared packet-read/literal+abstain pairs; counted once per case", extras["deduplicated_generation_resources"]["wall_seconds"], extras["deduplicated_generation_resources"]["cpu_seconds"], overlap="subphase within producer_total"),
        phase("native_scoring", "24 retained native output scoring calls", extras["native_scoring_resources"]["wall_seconds"], extras["native_scoring_resources"]["cpu_seconds"], overlap="subphase within producer_total"),
        phase("amortized_source_verification", "one source-inclusive wrapper replay shared across native cells/policies", wrapper["wall_seconds"], hashes=wrapper["logical_bytes_hashed_by_wrapper"] + wrapper["logical_base_completed_hash_bytes"], overlap="subphase within producer_total"),
        phase("independent_source_audit", f"separate source-inclusive audit of all {len(ledger['output_cells'])} outputs/{len(ledger['decision_cells'])} decisions", audit_cost["wall_seconds"], audit_cost["cpu_seconds"], audit_cost["peak_sampled_process_rss_bytes"], audit_cost["process_lifetime_peak_bytes"], audit_cost["logical_completed_hash_bytes"])]
    schedules = [{key: output[key] for key in ("cell_id", "case_id", "arm", "stratum", "terminal", "received_terminal", "raw_bytes")} | {"exact_report": output["strict_exact_report"], "full_source_admitted": output["full_source_admitted"], "full_verified_exact": output["full_verified_exact"]} for output in ledger["output_cells"]]
    decisions = [{key: decision[key] for key in ("decision_id", "output_cell_id", "policy", "verdict", "terminal", "first_failure_stage")} for decision in ledger["decision_cells"]]
    tables = {"native_case_results": native_rows, "native_fact_accounting": facts, "native_missingness": missing, "native_operation_resources": operations,
              "constructed_control_verdicts": control_rows, "constructed_policy_summary": policy_rows, "paired_discordance": pair_summary,
              "paired_verdict_cells": pair_cells, "resource_phases": resources, "output_schedule": schedules, "decision_schedule": decisions}
    display = {"native_fact_accounting": [row for row in facts if row["requested"]], "constructed_control_verdicts": control_display}
    return tables, display


def serialized(value, *, markdown=False):
    if value is None:
        result = "unknown"
    elif type(value) is bool:
        result = "true" if value else "false"
    elif type(value) in (dict, list):
        result = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    elif markdown and type(value) is float:
        result = format(value, ".6g")
    else:
        result = str(value)
    return result.replace("|", "\\|").replace("\n", " ") if markdown else result


def verify_figures(folder, manifest, tables, ledger, source_audit):
    from pypdf import PdfReader
    originals = len(source_audit["original_source_proofs"])
    missing, policies = tables["native_missingness"], tables["constructed_policy_summary"]
    counts = {"source_units": len(CASES), "constructed_scenarios": len(SCENARIOS), "outputs": len(ledger["output_cells"]), "decisions": len(ledger["decision_cells"]), "original_files": originals}
    figure_names = ("figure1-flow", "figure2-availability", "figure3-controls")
    need("all_three_figures", set(manifest["figures"]) == set(figure_names))
    geometry = {}
    for name in figure_names:
        data = read(folder / "figures" / (name + "-data.json"))
        caption = (folder / "figures" / (name + "-caption.md")).read_text(encoding="utf-8").strip()
        check("caption_manifest_binding_" + name, caption == manifest["figure_captions"][name] == manifest["tables_and_outputs"]["figures/" + name + "-data.json"]["caption"])
        check("figure_scientific_scope_" + name, "not independent" in caption.lower() or re.search(r"not [^.]*twelve independent studies", caption.lower()) is not None)
        svg_bytes = (folder / "figures" / (name + ".svg")).read_bytes()
        svg = ET.fromstring(svg_bytes)
        elements = list(svg.iter())
        check("native_vector_svg_" + name, svg.tag.endswith("svg") and not any(e.tag.endswith("image") for e in elements))
        texts = ["".join(e.itertext()) for e in elements if e.tag.endswith("text")]
        check("figure_title_visible_in_svg_" + name, data["title"] in texts)
        pdf = (folder / "figures" / (name + ".pdf")).read_bytes()
        check("native_vector_pdf_structure_" + name, pdf.startswith(b"%PDF-") and len(re.findall(rb"/Type\s*/Page\b", pdf)) == 1 and b"/Subtype /Image" not in pdf)
        reader = PdfReader(io.BytesIO(pdf))
        check("pdf_page_text_and_geometry_" + name, len(reader.pages) == 1 and data["title"] in reader.pages[0].extract_text() and [float(reader.pages[0].mediabox.width), float(reader.pages[0].mediabox.height)] == [data["width_pt"], data["height_pt"]])
        png = (folder / "figures" / (name + "-preview.png")).read_bytes()
        pixels = list(struct.unpack(">II", png[16:24])) if png.startswith(b"\x89PNG\r\n\x1a\n") else []
        check("preview_dimensions_" + name, pixels == manifest["figures"][name]["preview_pixels"] and min(pixels, default=0) > 600)
        rectangles = [{key: float(e.attrib.get(key, 0)) for key in ("x", "y", "width", "height")} for e in elements if e.tag.endswith("rect")]
        if name == "figure1-flow":
            check("figure1_independent_frame_counts", all(data[k] == value for k, value in counts.items()) and data["independence"] == "not_established" and data["shared_helper_algorithms"] is True)
            ids = {node["id"] for node in data["nodes"]}
            arcs = {(edge["source"], edge["target"]) for edge in data["edges"]}
            expected_arcs = {("originals", "generation"), ("originals", "references"), ("generation", "native_outputs"), ("references", "verification"), ("native_outputs", "verification"), ("constructed", "verification"), ("verification", "analysis")}
            check("figure1_custody_topology_without_evaluator_to_generator", ids == {"originals", "generation", "references", "native_outputs", "verification", "constructed", "analysis"} and arcs == expected_arcs)
            check("figure1_node_geometry", all(0 <= n["x"] <= n["x"] + n["w"] <= data["width_pt"] and 0 <= n["y"] <= n["y"] + n["h"] <= data["height_pt"] for n in data["nodes"]))
            check("figure1_caption_counts", str(counts["outputs"]) + " output cells" in caption and str(counts["decisions"]) + " paired decisions" in caption)
        elif name == "figure2-availability":
            expected_rows = [{"case_id": row["case_id"], "answerable": row["measurement_answerable"], "native_null": row["measurement_null"], "requested": row["measurement_requested"]} for row in missing]
            check("figure2_independent_data", equal(data["rows"], expected_rows) and data["answerable_total"] == sum(row["answerable"] for row in expected_rows) and data["native_null_total"] == sum(row["native_null"] for row in expected_rows) and data["requested_total"] == sum(row["requested"] for row in expected_rows) and data["measurement_groups"] == sum(row["measurement_groups"] for row in missing) and data["independent_studies"] == "not_established")
            for i, row in enumerate(expected_rows):
                y, known = 278 - i * 16, 384 * row["answerable"] / row["requested"]
                null = 384 * row["native_null"] / row["requested"]
                actual = [rect for rect in rectangles if rect["y"] == y and rect["height"] == 11]
                wanted = [{"x": 88.0, "y": float(y), "width": float(known), "height": 11.0}]
                if null:
                    wanted.append({"x": 88.0 + known, "y": float(y), "width": float(null), "height": 11.0})
                check("figure2_svg_bar_geometry_" + row["case_id"], actual == wanted)
            check("figure2_caption_quantities", all(f"{value} {phrase}" in caption for value, phrase in ((sum(r["answerable"] for r in expected_rows), "answerable values"), (sum(r["native_null"] for r in expected_rows), "native nulls"), (sum(r["requested"] for r in expected_rows), "slots"))))
            ratio = f"{sum(row['answerable'] for row in expected_rows)}/{sum(row['requested'] for row in expected_rows)}"
            check("figure2_availability_and_coverage_denominators_separate", data["denominator_note"] == ratio + " slots answerable; native nulls are excluded from reporting denominators." and ratio + " availability total is distinct" in caption and "100% group-weighted coverage of answerable components" in caption)
        else:
            check("figure3_independent_data", equal(data["rows"], policies) and data["invalid_scenarios"] == sum(key.startswith("F") for key in SCENARIOS) and data["valid_scenarios"] == sum(key.startswith("C") for key in SCENARIOS) and data["paired_policies"] is True and data["natural_fault_prevalence"] == "not_estimated" and data["independent_studies"] == "not_established")
            for row, y in zip(policies, (233, 181, 129)):
                actual = [rect["width"] for rect in rectangles if rect["x"] == 150 and rect["y"] == y and rect["height"] == 20]
                wanted = [316.0] + ([316.0 * row["invalid_admitted"] / row["invalid_planned"]] if row["invalid_admitted"] else [])
                check("figure3_svg_bar_geometry_" + row["policy"], len(actual) == len(wanted) and all(math.isclose(got, want, rel_tol=0, abs_tol=1e-9) for got, want in zip(actual, wanted)))
                check("figure3_visible_count_label_" + row["policy"], f"{row['invalid_admitted']}/{row['invalid_planned']}" in texts)
                check("figure3_caption_policy_quantity_" + row["policy"], row["policy"] + f" {row['invalid_admitted']}/{row['invalid_planned']}" in caption)
            reject = policies[0]
            check("figure3_caption_valid_rejections", all(row["valid_rejected"] == reject["valid_rejected"] and row["valid_planned"] == reject["valid_planned"] for row in policies) and f"reject {reject['valid_rejected']}/{reject['valid_planned']} technically valid" in caption)
        geometry[name] = {"native_vector_structure": True, "numeric_svg_geometry_checked": name != "figure1-flow", "preview_pixels": pixels, "svg_serialization_tolerance_pt": 1e-9 if name == "figure3-controls" else 0}
    REPORT["figure_structure_and_data"] = geometry


def execute(args):
    started = time.monotonic()
    docs = {}
    for name, path in (("ledger", LEDGER), ("audit", AUDIT), ("analysis", ANALYSIS)):
        need("external_input_pin_" + name, sha(path.read_bytes()) == PINS[name])
        docs[name] = read(path)
    ledger, source_audit, analysis = docs["ledger"], docs["audit"], docs["analysis"]
    expected, extras = recompute(ledger, source_audit)
    for name, value in expected.items():
        check("independent_analysis_section_" + name, equal(analysis[name], value))
    execution = analysis["execution"]
    analyzer_path = ROOT / "tools/science/analyze_source_validation_experiment.py"
    check("frozen_analyzer_and_analysis_execution", sha(analyzer_path.read_bytes()) == execution["analyzer_sha256"] == ledger["analysis_code_sha256"] and execution["ledger_sha256"] == PINS["ledger"] and execution["audit_sha256"] == PINS["audit"] and Path(execution["ledger_path"]) == LEDGER and Path(execution["audit_path"]) == AUDIT and execution["frozen_analysis_pin_match"] is True)
    manifest_path = Path(args.asset_manifest).absolute()
    need("paper_asset_manifest_path", manifest_path == ROOT / "paper/results/ARTIFACTS.json")
    need("external_asset_manifest_bytes", sha(manifest_path.read_bytes()) == args.asset_manifest_sha256)
    manifest, folder = read(manifest_path), manifest_path.parent
    need("paper_output_metadata_scope", manifest["status"] == "BUILT_FROM_FROZEN_AUDITED_METADATA" and manifest["scope"]["scientific_validation"] == "not_established" and manifest["scope"]["independent_studies"] == "not_established" and manifest["presentation_code_written_after_results"] is True)
    for name, item in manifest["inputs"].items():
        path = ROOT / item["path"]
        need("declared_input_allowed_" + name, path in {LEDGER, AUDIT, ANALYSIS, ANALYSIS.parent / "analysis-seal.json", ASSETS / "REGISTER-MANIFEST-v1.json"})
        check("declared_input_hash_" + name, sha(path.read_bytes()) == item["sha256"] and path.stat().st_size == item["bytes"] and item["kind"] == "metadata_only")
        if name in PINS:
            check("external_manifest_input_binding_" + name, item["sha256"] == PINS[name])
    need("all_three_primary_metadata_inputs_declared", set(PINS) <= set(manifest["inputs"]))
    analysis_seal = read(ANALYSIS.parent / "analysis-seal.json")
    check("analysis_seal_all_three_subjects_and_code", analysis_seal["analysis_sha256"] == PINS["analysis"] and analysis_seal["audit_sha256"] == PINS["audit"] and analysis_seal["ledger_sha256"] == PINS["ledger"] and analysis_seal["code_sha256"] == execution["analyzer_sha256"])
    for name in ("builder", "frozen_analyzer"):
        entry = manifest[name]
        check("code_pin_" + name, sha((ROOT / entry["path"]).read_bytes()) == entry["sha256"])
    files = manifest["tables_and_outputs"]
    need("whole_paper_artifact_set", {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()} == set(files) | {"ARTIFACTS.json"} and manifest["manifest_self_excluded"] is True)
    for relative, item in files.items():
        path = folder / relative
        need("output_logical_path_" + relative, path.is_relative_to(folder) and ".." not in Path(relative).parts and item["path"] == path.relative_to(ROOT).as_posix())
        check("output_byte_pin_" + relative, sha(path.read_bytes()) == item["sha256"] and path.stat().st_size == item["bytes"] and bool(item["source_fields"]))
    tables, display = expected_tables(ledger, source_audit, expected, extras)
    for name, rows in tables.items():
        relative = "tables/" + name + ".csv"
        item = files[relative]
        csv_rows = list(csv.DictReader(io.StringIO((folder / relative).read_text(encoding="utf-8"), newline="")))
        columns = item["columns"]
        check("csv_columns_complete_" + name, columns == list(rows[0]) and list(csv_rows[0]) == columns)
        expected_rows = [{key: serialized(row[key]) for key in columns} for row in rows]
        check("all_independent_csv_cells_" + name, csv_rows == expected_rows and item["rows"] == len(rows), rows=len(rows), columns=len(columns))
        md_relative = "tables/" + name + ".md"
        md = files[md_relative]
        lines = [line for line in (folder / md_relative).read_text(encoding="utf-8").splitlines() if line.startswith("|")]
        cells = [[value.strip() for value in re.split(r"(?<!\\)\|", line)[1:-1]] for line in lines]
        md_rows = display.get(name, rows)
        expected_md = [[serialized(row[key], markdown=True) for key in md["columns"]] for row in md_rows]
        check("all_independent_markdown_cells_" + name, cells[0] == md["columns"] and cells[2:] == expected_md and md["rows"] == len(md_rows), rows=len(md_rows))
    need("all_csv_and_markdown_tables_checked", {rel for rel in files if rel.startswith("tables/")} == {"tables/" + name + extension for name in tables for extension in (".csv", ".md")})
    verify_figures(folder, manifest, tables, ledger, source_audit)
    readme = (folder / "README.md").read_text(encoding="utf-8")
    check("readme_scope_and_unknowns", "not twelve independent studies" in readme and "unknown" in readme and "not_established" in readme and "No new endpoint, interval, significance test, power calculation or reweighting" in readme)
    check("unknown_resources_preserved", all(row["physical_io_bytes"] is None and row["platform_cost_usd"] is None for row in tables["resource_phases"]) and ledger["resources"]["partial_failed_hash_bytes"] is None)
    check("no_independence_or_scientific_promotion", analysis["independent_study_count"] is None and analysis["inferential_statistics"] == "none" and manifest["scope"]["independent_studies"] == "not_established")
    REPORT["inputs"] = {name: {"path": str(path), "sha256": PINS[name]} for name, path in (("ledger", LEDGER), ("audit", AUDIT), ("analysis", ANALYSIS))}
    REPORT["asset_manifest"] = {"path": str(manifest_path), "sha256": args.asset_manifest_sha256}
    REPORT["descriptive_quantities"] = extras | {"native_primary": expected["native_primary"], "native_secondary": expected["native_secondary"], "fictional_policies": {p: {key: expected["fictional_policies"][p][key] for key in ("false_acceptance", "false_rejection")} for p in POLICIES}}
    REPORT["coverage"] = {"csv_tables": len(tables), "csv_rows": sum(len(rows) for rows in tables.values()), "markdown_tables": len(tables), "markdown_rows": sum(len(display.get(name, rows)) for name, rows in tables.items()), "figure_data_files": len(manifest["figures"]), "captions": len(manifest["figure_captions"]), "output_artifacts": len(files)}
    REPORT["byte_integrity"] = "PASS" if not REPORT["unresolved_findings"] else "SEE_FINDINGS"
    REPORT["descriptive_quantity_agreement"] = "PASS" if not REPORT["unresolved_findings"] else "SEE_FINDINGS"
    REPORT["visual_qa"] = {"status": "PASS_RENDERED_PREVIEW_REVIEW" if args.visual_reviewed else "PENDING_ROOT_AUTHOR_REVIEW", "reviewed_preview_paths": [str(folder / "figures" / (name + "-preview.png")) for name in manifest["figures"]] if args.visual_reviewed else [], "scope": "rendered PNG preview legibility/labels only; numeric SVG geometry checked separately; scientific validation not established"}
    REPORT["audit_wall_seconds"] = time.monotonic() - started


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-manifest", required=True)
    parser.add_argument("--asset-manifest-sha256", required=True)
    parser.add_argument("--visual-reviewed", action="store_true")
    args = parser.parse_args()
    output = ASSETS / "ANALYSIS-PRESENTATION-AUDIT-v1.json"
    if output.exists():
        raise RuntimeError("Preserve existing audit history")
    try:
        execute(args)
    except BaseException as error:
        REPORT["unresolved_findings"].append("audit_exception:" + type(error).__name__)
        if isinstance(error, AssertionError):
            REPORT["failed_check"] = str(error)
        REPORT["error_class"] = type(error).__name__
    REPORT["status"] = "PASS_INDEPENDENT_ANALYSIS_PRESENTATION_AUDIT" if not REPORT["unresolved_findings"] else "FAIL_INDEPENDENT_ANALYSIS_PRESENTATION_AUDIT"
    REPORT["auditor_sha256"] = sha(Path(__file__).read_bytes())
    output.write_bytes(canonical(REPORT) + b"\n")
    print(json.dumps({"status": REPORT["status"], "checks": len(REPORT["checks"]), "unresolved_findings": REPORT["unresolved_findings"], "report_sha256": sha(output.read_bytes()), "coverage": REPORT.get("coverage"), "visual_qa": REPORT.get("visual_qa")}))
    return 0 if REPORT["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
