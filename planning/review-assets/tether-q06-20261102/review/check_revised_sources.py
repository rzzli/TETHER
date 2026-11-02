"""Bounded independent Q06 source checks; no engine, raw sources or model calls.

Only explicitly named manuscript, result-table and retained review/report files
are opened. This checks arithmetic and editing/qualification bindings, not
scientific truth, provider authenticity or the full historic source audit.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
inputs = {}
checks = []
computed = {}


def read(rel):
    path = ROOT / rel
    raw = path.read_bytes()
    inputs[rel] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return raw.decode("utf-8-sig")


def obj(rel):
    return json.loads(read(rel))


def table(name):
    return list(csv.DictReader(io.StringIO(read("paper/results/tables/" + name))))


def check(name, condition, detail=None):
    checks.append({"name": name, "passed": bool(condition), "detail": detail})


man = read("paper/revisions/20261102/manuscript.md")
sup = read("paper/revisions/20261102/supplement.md")
notes = read("paper/revisions/20261102/REVISION-NOTES.md")
old_man = read("paper/manuscript.md")
old_sup = read("paper/supplement.md")
check("original_manuscript_pin", inputs["paper/manuscript.md"]["sha256"] == "99ee5893568d4734a393669a88e06920c882d65aa064e7f20a9ad689488e096f")
check("original_supplement_pin", inputs["paper/supplement.md"]["sha256"] == "1f5c2073c7736d7a1b300c375bf84fb574d31df89ff57fa35b45feb60f80daa6")
check("bibliography_exact_text", old_man.split("## References\n", 1)[1] == man.split("## References\n", 1)[1])
for name, before, after in [("manuscript", old_man, man), ("supplement", old_sup, sup)]:
    rows = [line for line in before.splitlines() if line.startswith("|")]
    check(name + "_all_original_table_lines_retained", all(line in after.splitlines() for line in rows), len(rows))
    old_hashes = set(re.findall(r"\b[0-9a-f]{64}\b", before))
    check(name + "_old_explicit_sha256_anchors_retained", old_hashes <= set(re.findall(r"\b[0-9a-f]{64}\b", after)), len(old_hashes))
for rel, body in [("paper/revisions/20261102/manuscript.md", man), ("paper/revisions/20261102/supplement.md", sup)]:
    for target in re.findall(r"\]\(([^)]+)\)", body):
        if "://" not in target and not target.startswith("#"):
            check("local_link:" + rel + ":" + target, (ROOT / rel).parent.joinpath(target).resolve().is_file())

native = table("native_missingness.csv")
groups = Counter(int(row["measurement_answerable"]) for row in native)
check("native_group_distribution", groups == {2: 1, 3: 6, 4: 5}, dict(groups))
check("one_measurement_group_per_native_unit", len(native) == 12 and all(int(row["measurement_groups"]) == 1 for row in native))
expected_sums = {"measurement_requested": 48, "measurement_answerable": 40, "measurement_null": 8, "measurement_absent": 0, "measurement_empty": 0, "measurement_other_unknown": 0, "identity_requested": 132, "identity_answerable": 108, "identity_null": 24}
for key, expected in expected_sums.items():
    value = sum(int(row[key]) for row in native)
    check("native_sum:" + key, value == expected, value)
check("native_exposure_and_independence_unqualified", all(row["other_exposure"] == "UNKNOWN" and row["independent_studies"] == "not_established" for row in native))
for n in sorted(groups):
    for m in range(n + 1):
        check(f"native80_equals100:n={n},matched={m}", (5 * m >= 4 * n) == (m == n))
    threshold_counts = [next(m for m in range(n + 1) if 5 * m >= 3 * n), next(m for m in range(n + 1) if 5 * m >= 4 * n), n]
    check(f"supplement_threshold_table:n={n}", f"| {n} | {groups[n]} | {threshold_counts[0]} | {threshold_counts[1]} | {threshold_counts[2]} |" in sup, threshold_counts)

results = table("native_case_results.csv")
for arm, exact, emitted in [("L", "true", 15), ("A", "false", 0)]:
    rows = [r for r in results if r["arm"] == arm]
    check("native_arm:" + arm, len(rows) == 12 and all(r["verified_exact"] == exact and r["completion_80"] == exact and all(r[k] == exact for k in ["pass_60", "pass_80", "pass_100"]) and int(r["emitted_facts"]) == emitted and int(r["critical_error_count"]) == 0 for r in rows))
outputs = table("output_schedule.csv")
decisions = table("decision_schedule.csv")
controls = table("constructed_control_verdicts.csv")
check("complete_output_schedule", len(outputs) == 38 and Counter(r["terminal"] for r in outputs) == {"returned": 36, "malformed": 2})
check("complete_decision_schedule", len(decisions) == 90 and Counter(r["verdict"] for r in decisions) == {"admitted": 57, "rejected": 33})
check("constructed_decisions", len(controls) == 42 and len({r["scenario_id"] for r in controls}) == 14)
for policy, invalid_admitted in [("FULL", 0), ("WITHOUT_WRAPPER", 2), ("WIRE_ONLY", 7)]:
    rows = [r for r in controls if r["policy"] == policy]
    valid = [r for r in rows if r["truth"] == "VALID_REPORT"]
    invalid = [r for r in rows if r["truth"] != "VALID_REPORT"]
    check("control_results:" + policy, len(valid) == 4 and len(invalid) == 10 and sum(r["verdict"] == "rejected" for r in valid) == 0 and sum(r["verdict"] == "admitted" for r in invalid) == invalid_admitted)

phases = {r["phase"]: r for r in table("resource_phases.csv")}
wall_share = Decimal(phases["amortized_source_verification"]["wall_seconds"]) / Decimal(phases["producer_total"]["wall_seconds"]) * 100
hash_ratio = Decimal(phases["producer_total"]["logical_completed_hash_bytes"]) / Decimal(2866248239)
computed["verification_wall_percent"] = str(wall_share)
computed["production_logical_source_frame_equivalents"] = str(hash_ratio)
check("wall_share_rounds_97_0485", f"{wall_share:.4f}" == "97.0485")
check("logical_hash_ratio_rounds_49_0021", f"{hash_ratio:.4f}" == "49.0021")
check("verification_is_nested", phases["amortized_source_verification"]["overlap"] == "subphase within producer_total")
check("physical_io_and_platform_cost_unmeasured", all(r[k] == "unknown" for r in phases.values() for k in ["physical_io_bytes", "platform_cost_usd"]))
check("combined_logical_hash_bytes", sum(int(phases[k]["logical_completed_hash_bytes"]) for k in ["producer_total", "independent_source_audit"]) == 143349572350)

pilot = obj("runs/preprint-p04-typed-report-20261101T053531Z/report.json")
dispatches = Counter(s["stage"] for c in pilot["cells"] for s in c["stage_records"] if s["dispatched"])
computed["p04_dispatches"] = dict(dispatches)
check("p04_dispatch_counts", dispatches == {"plain": 3, "proposal": 2} and dispatches["audit"] == 0 and pilot["actual_calls"] == 5)
check("p04_terminals", Counter(c["terminal"] for c in pilot["cells"]) == {"returned": 7, "malformed": 4, "failed": 1})
check("p04_reported_tokens", pilot["measured_usage"]["input_tokens"] == 13582 and pilot["measured_usage"]["output_tokens"] == 5726)

q01 = obj("planning/review-assets/tether-q01-20261102/VALIDATION.json")
q02 = obj("planning/review-assets/tether-q02-20261102/VALIDATION.json")
software = obj("paper/release/tether-v2/SOFTWARE-QUALIFICATION.json")
check("portable_summary_q01_anchor", software["qualification_anchors"]["q01"] == inputs["planning/review-assets/tether-q01-20261102/VALIDATION.json"]["sha256"])
check("portable_summary_q02_anchor", software["qualification_anchors"]["q02"] == inputs["planning/review-assets/tether-q02-20261102/VALIDATION.json"]["sha256"])
check("portable_wheel_properties", all(software["wheel"][k] == q02["wheel"][k] for k in software["wheel"]))
check("software_summary_counts", software["checks"]["q01_at_0_4_2"]["package_tests"] == q01["package_tests"]["count"] == 86 and software["checks"]["q02_at_0_5_0"]["package_tests"] == q02["package_tests"]["count"] == 129)
check("q02_originals_subset_and_zero_dispatches", q02["source_preparation"] == {"case": "OSMR", "originals": 18, "bytes": 442815104, "engine_dispatches": 0, "remaining_raw_not_freshly_verified": 230})
check("q02_policy_counts", {k: q02["final_policy"][k] for k in ["products", "artifacts", "allowed_uses", "blocked_uses", "status_promotions"]} == {"products": 178, "artifacts": 266, "allowed_uses": 10, "blocked_uses": 7, "status_promotions": 0})
attempts = obj("planning/review-assets/tether-q03-20261102/data/SOURCE-AUDIT-ATTEMPTS.json")
check("q03_failed_then_success", [r["exit_code"] for r in attempts["attempts"]] == [1, 0])
check("q03_executed_code_pins_absent", all(r["executed_script_sha256"] is None for r in attempts["attempts"]))
check("q03_failed_projections_not_retained", attempts["first_attempt_retention"]["projection_bytes_retained"] is False and attempts["first_attempt_retention"]["projection_sha256_retained"] is False)

# Pin text authorities independently reviewed in SOURCE-REVIEW.md, without
# promoting word matching to a test of their substantive interpretation.
for rel in [
    "paper/REVIEW-ERRATA-20261102.md",
    "docs/TETHER-VERIFICATION-SCOPE.md",
    "docs/TETHER-CATALOG-POLICY.md",
    "planning/Project Progress Reassessment 2026-11-02 - Bounded TETHER Release.md",
    "planning/Project Progress Reassessment 2026-11-02 - Artifact Catalog Policy.md",
    "planning/Project Progress Reassessment 2026-11-02 - Source Composition Feasibility.md",
    "planning/review-assets/full-project-review-20261102/results/RESULTS-REVIEW.md",
    "planning/review-assets/tether-q03-20261102/review/INDEPENDENT-FEASIBILITY-REVIEW.md",
    "planning/review-assets/tether-q03-20261102/review/ROUTE-REVIEW.md",
    "planning/review-assets/tether-q03-20261102/data/SOURCE-FEASIBILITY.md",
    "paper/release/tether-v2/CURRENT-SOFTWARE.md",
]:
    if (ROOT / rel).is_file():
        read(rel)
    else:
        check("required_companion:" + rel, False)

check("inputs_stable_through_check", all(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == meta["sha256"] for rel, meta in inputs.items()))
record = {
    "schema_version": 1,
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS_NAMED_SOURCE_CHECKS" if all(c["passed"] for c in checks) else "FINDINGS",
    "scope": "Independent arithmetic, retained-result counts, source editing safeguards and qualification anchors. See accompanying manual source review; no scientific validation or PDF/package qualification.",
    "inputs": inputs,
    "computed": computed,
    "checks": checks,
    "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "prohibited_inputs_read": False,
    "raw_provider_payloads_read": False,
    "model_calls": 0,
    "source_study_rerun": False,
}
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
out = HERE / ("SOURCE-CHECK-" + stamp + ".json")
with out.open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps({"record": str(out), "status": record["status"], "checks": len(checks), "findings": [c for c in checks if not c["passed"]], "computed": computed}, indent=2))
