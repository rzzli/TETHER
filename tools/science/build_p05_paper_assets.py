"""Post-result presentation only: pinned P05 metadata -> tables/vector figures.

No source records, expected reference facts, raw candidates or human data are
opened. This does not rescore, alter endpoints or change frozen study code.
Run the PDF operation marker once before the first --build, outside this script.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "paper/results"
OUT = DEFAULT_OUT
ANALYSIS = ROOT / "data/derived/preprint-p05-analysis-20261101T092110Z/analysis.json"
LEDGER = ROOT / "data/derived/preprint-p05-experiment-20261101T091345Z/ledger.json"
AUDIT = ROOT / "planning/review-assets/preprint-p05-20261031/EXPERIMENT-AUDIT-v1.json"
SEAL = ANALYSIS.parent / "analysis-seal.json"
REGISTER = ROOT / "planning/review-assets/preprint-p05-20261031/REGISTER-MANIFEST-v1.json"
ANALYZER = ROOT / "tools/science/analyze_source_validation_experiment.py"
PINS = {
    "analysis": (ANALYSIS, "ee9f02ea3c3692bbd8b7d63d2d2cd545cfd769ccee9ee7454b4ed00c7ac87312"),
    "ledger": (LEDGER, "b2a9727ca9ce89865b80ffe80b21a325ea6d91d8844247740ac2c2ecc9a4faa0"),
    "audit": (AUDIT, "f10f15959f8497821115f65268808c98ae345079c7361722390a479b15506922"),
    "analysis_seal": (SEAL, "b409027e70d6b6efa51024a3179353932d4828bf03003c05769a8618e606c993"),
    "register": (REGISTER, "2c363c14a03b94ed39e285f9fac502fd8eff9bd3f3c81dc7faebe0309897c414"),
}
ANALYZER_SHA = "e61d18dcc8f571766e419b4c535f3e18ef0c2a00531a620a8a9cbba6c8dfaeed"
POPLER = Path("C:/Users/zzric/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.EXE")
POLICIES = ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")
CASES = tuple(f"p05-{i:02d}" for i in range(1, 13))
SCENARIOS = tuple([f"C{i:02d}" for i in range(1, 5)] + [f"F{i:02d}" for i in range(1, 11)])
CAPTIONS = {
    "figure1-flow": "Separate source-only branches and retained evaluation flow. The generation packet and evaluator reference branches reread the same frozen originals; preparation helpers are shared. The independent source-inclusive audit reconstructs original records separately. Twelve native technical source units and fourteen exposed, constructed JSON/core controls contribute 38 output cells and 90 paired decisions. These are not independent studies, and technical source fidelity establishes no biological, model or clinical superiority.",
    "figure2-availability": "Availability of the four requested native measurement components in each of twelve selected source units: 40 answerable values and 8 native nulls across 48 slots. Each unit has one measurement group. Native nulls are excluded from reporting denominators; no value is imputed. The 40/48 availability total is distinct from the literal arm's 100% group-weighted coverage of answerable components. Bars describe source availability, not twelve independent studies. Scientific measurement validity remains unestablished.",
    "figure3-controls": "Admissions among ten deliberately constructed invalid scenarios under paired diagnostic policies: FULL 0/10, WITHOUT_WRAPPER 2/10 and WIRE_ONLY 7/10. All three reject 0/4 technically valid controls. The policies inspect the same retained candidates; repeated decisions are not independent observations. These exposed generic JSON/core controls test named contract mechanisms, do not estimate natural fault prevalence, and establish no biological or clinical superiority. Contract-valid source reporting is distinct from scientific truth.",
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def pinned_inputs():
    documents, proofs = {}, {}
    for label, (path, expected) in PINS.items():
        raw = path.read_bytes()
        need(len(raw) <= 64 * 1024**2 and sha(raw) == expected, "Pinned input changed: " + label)
        documents[label] = json.loads(raw, object_pairs_hook=strict_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite input")))
        proofs[label] = dict(path=path.relative_to(ROOT).as_posix(), sha256=expected, bytes=len(raw), kind="metadata_only")
    a, l, u, seal, register = (documents[k] for k in ("analysis", "ledger", "audit", "analysis_seal", "register"))
    need(sha(ANALYZER.read_bytes()) == ANALYZER_SHA == seal["code_sha256"] == a["execution"]["analyzer_sha256"], "Frozen analyzer changed")
    need(seal["analysis_sha256"] == PINS["analysis"][1] and seal["audit_sha256"] == PINS["audit"][1] and
         seal["ledger_sha256"] == PINS["ledger"][1], "Analysis seal subject differs")
    need(u["status"] == "PASS_INDEPENDENT_EXPERIMENT_AUDIT" and u["source_inclusive"] is True and
         not u["unresolved_findings"] and u["subject"]["ledger_sha256"] == PINS["ledger"][1], "Independent audit is unqualified")
    need(a["execution"]["ledger_sha256"] == PINS["ledger"][1] and a["execution"]["audit_sha256"] == PINS["audit"][1] and
         a["execution"]["frozen_analysis_pin_match"] is True, "Analysis anchors differ")
    need(a["scientific_validation"] == "not_established" and a["independent_study_count"] is None and a["inferential_statistics"] == "none",
         "Do not introduce scientific or independent-study qualification")
    need(a["planned_output_cells"] == len(l["output_cells"]) == 38 and a["planned_decisions"] == len(l["decision_cells"]) == 90,
         "Complete schedule differs")
    need(tuple(x["case_id"] for x in a["native_cases"]) == CASES and a["native_denominator"] == 12 and
         a["native_primary"]["verified_exact_count"] == a["native_primary"]["completion_80_count"] == 12, "Native frozen results differ")
    need(tuple(x["scenario_id"] for x in a["fictional_cases"]) == SCENARIOS and register["original_parent_count"] == 137,
         "Source/control frame differs")
    need([a["fictional_policies"][p]["false_acceptance"]["error_count"] for p in POLICIES] == [0, 2, 7] and
         all(a["fictional_policies"][p]["false_rejection"]["error_count"] == 0 for p in POLICIES), "Constructed-control results differ")
    return documents, proofs


def cell_value(value):
    if value is None:
        return "unknown"
    if type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return str(value)


def markdown_value(value):
    if type(value) is float:
        value = format(value, ".6g")
    return cell_value(value).replace("|", "\\|").replace("\n", " ")


class Artifacts:
    def __init__(self):
        self.outputs, self.sections = {}, {}

    def write(self, relative, raw, *, section, source_fields, extra=None):
        path = OUT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.outputs[relative] = dict(path="paper/results/" + relative, sha256=sha(raw), bytes=len(raw),
            section=section, source_fields=source_fields, **(extra or {}))
        return path

    def json(self, relative, value, **kwargs):
        return self.write(relative, (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode(), **kwargs)

    def table(self, name, rows, *, title, note, source_fields, columns=None, md_columns=None, md_rows=None):
        need(bool(rows), "Empty presentation table")
        columns = list(columns or rows[0])
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: cell_value(row[key]) for key in columns})
        self.write("tables/" + name + ".csv", stream.getvalue().encode(), section=title, source_fields=source_fields,
                   extra=dict(rows=len(rows), columns=columns))
        display_columns = list(md_columns or columns)
        display_rows = list(md_rows if md_rows is not None else rows)
        lines = ["# " + title, "", note, "", "| " + " | ".join(display_columns) + " |",
                 "| " + " | ".join("---" for _ in display_columns) + " |"]
        lines += ["| " + " | ".join(markdown_value(row[key]) for key in display_columns) + " |" for row in display_rows]
        self.write("tables/" + name + ".md", ("\n".join(lines) + "\n").encode(), section=title, source_fields=source_fields,
                   extra=dict(rows=len(display_rows), columns=display_columns, display_only_rounding="six significant digits"))


def make_tables(docs, art):
    a, ledger, audit = (docs[k] for k in ("analysis", "ledger", "audit"))
    cells = {x["cell_id"]: x for x in ledger["output_cells"]}
    native_rows, accounting, missingness, timings = [], [], [], []
    for case in a["native_cases"]:
        key = case["case_id"]
        measurement = case["literal"]["fact_accounting"]["families"]["reported_measurement"]
        identity = case["literal"]["fact_accounting"]["families"]["identity_linkage"]
        unknowns = measurement["expected_unknown_by_reason"]
        missingness.append(dict(case_id=key, measurement_requested=measurement["requested"],
            measurement_answerable=measurement["answerable"], measurement_null=unknowns.get("null_source_value", 0),
            measurement_absent=unknowns.get("field_not_in_schema", 0), measurement_empty=unknowns.get("empty_source_value", 0),
            measurement_other_unknown=sum(v for k, v in unknowns.items() if k not in ("null_source_value", "field_not_in_schema", "empty_source_value")),
            measurement_groups=case["qualification"]["measurement_answerable_groups"], identity_requested=identity["requested"],
            identity_answerable=identity["answerable"], identity_null=identity["expected_unknown_by_reason"].get("null_source_value", 0),
            other_exposure="UNKNOWN", independent_studies="not_established"))
        pair = cells["N-L-" + key]["shared_case_generation_resources"]
        need(pair == cells["N-A-" + key]["shared_case_generation_resources"], "Shared pair measurements differ")
        timings.append(dict(case_id=key, shared_pair_wall_seconds=pair["wall_seconds"], shared_pair_cpu_seconds=pair["cpu_seconds"],
            literal_scoring_wall_seconds=cells["N-L-" + key]["scoring_resources"]["wall_seconds"],
            literal_scoring_cpu_seconds=cells["N-L-" + key]["scoring_resources"]["cpu_seconds"],
            abstain_scoring_wall_seconds=cells["N-A-" + key]["scoring_resources"]["wall_seconds"],
            abstain_scoring_cpu_seconds=cells["N-A-" + key]["scoring_resources"]["cpu_seconds"],
            basis="one shared packet-read/generation pair per case; scoring per returned arm"))
        for arm, label in (("L", "literal"), ("A", "abstain")):
            result = case[label]
            cell = cells["N-" + arm + "-" + key]
            meas = result["fact_accounting"]["families"]["reported_measurement"]
            native_rows.append(dict(case_id=key, arm=arm, method="literal" if arm == "L" else "always_abstain",
                terminal=result["terminal"], emitted_facts=cell["core_score"]["emitted_facts"], source_admitted=cell["full_source_admitted"],
                exact_report=result["exact_report"], verified_exact=result["verified_exact"], measurement_coverage=result["coverage"],
                answerable_measurement_components=result["answerable_facts"], answerable_measurement_groups=result["answerable_groups"],
                pass_60=result["thresholds"]["60"], pass_80=result["thresholds"]["80"], pass_100=result["thresholds"]["100"],
                completion_80=result["completion_80"], measurement_matched=meas["matched"], measurement_correct_unknown=meas["correct_unknown"],
                measurement_omitted=meas["omitted"], measurement_false_asserted=meas["false_asserted"],
                critical_error_count=sum(result["critical_errors"].values()), unknown_fact_id_emissions=result["fact_accounting"]["unknown_fact_id_emissions"]))
            for family, fact in result["fact_accounting"]["families"].items():
                accounting.append(dict(case_id=key, arm=arm, family=family, requested=fact["requested"], answerable=fact["answerable"],
                    answerable_groups=result["family_scores"][family]["answerable_groups"], family_coverage=result["family_scores"][family]["coverage"],
                    matched=fact["matched"], correct_unknown=fact["correct_unknown"], omitted=fact["omitted"],
                    false_asserted=fact["false_asserted"], expected_unknown_by_reason=fact["expected_unknown_by_reason"]))
    need(sum(x["measurement_answerable"] for x in missingness) == 40 and sum(x["measurement_null"] for x in missingness) == 8,
         "Measurement availability differs")
    art.table("native_case_results", native_rows, title="Native reporting results: twelve units, two arms",
        note="Measurement-only equal-group coverage; 60/80/100 columns retain frozen threshold flags. All 24 returns stay visible. Native unknowns are excluded from answerable coverage denominators and reported separately. These are twelve technical units, not independent studies.",
        source_fields=["analysis.native_cases[].literal/abstain", "ledger.output_cells[].core_score.emitted_facts"],
        md_columns=["case_id", "method", "emitted_facts", "measurement_coverage", "pass_60", "pass_80", "pass_100", "verified_exact", "measurement_correct_unknown", "measurement_omitted", "critical_error_count"])
    art.table("native_fact_accounting", accounting, title="Native requested facts, matches, unknowns and omissions",
        note="CSV retains all four families, including zero-request families. Markdown shows the requested identity/measurement families. Matched counts refer to unique answerable facts; correctly unknown is separate. Unknown-only coverage is not zero.",
        source_fields=["analysis.native_cases[].literal/abstain.fact_accounting", "analysis.native_cases[].literal/abstain.family_scores"],
        md_columns=["case_id", "arm", "family", "requested", "answerable", "matched", "correct_unknown", "omitted", "false_asserted"],
        md_rows=[row for row in accounting if row["requested"]])
    art.table("native_missingness", missingness, title="Native slot availability and missingness",
        note="Count each source unit once: four native measurement components per unit, one group. Native null means unavailable source information; it is not biological absence or zero. Forty answerable slots and eight nulls across 48 requests.",
        source_fields=["analysis.native_cases[].qualification", "analysis.native_cases[].literal.fact_accounting"],
        md_columns=["case_id", "measurement_requested", "measurement_answerable", "measurement_null", "measurement_absent", "measurement_empty", "identity_answerable", "identity_null"])
    art.table("native_operation_resources", timings, title="Native generation pairs and scoring resources",
        note="Count the shared literal/abstain generation pair ONCE per case; the same pair is retained on both arms in the ledger. Values are process measurements, not independent runtime replicates; zero denotes the timer's recorded resolution.",
        source_fields=["ledger.output_cells[].shared_case_generation_resources (arm L once per case)", "ledger.output_cells[].scoring_resources"])
    controls, verdict_lookup = [], {}
    fictional = {x["scenario_id"]: x for x in a["fictional_cases"]}
    for policy in POLICIES:
        for row in a["fictional_policies"][policy]["scenarios"]:
            key = row["scenario_id"]
            metadata = fictional[key]
            guard = ledger["guards"]["S-" + key]
            controls.append(dict(scenario_id=key, truth=row["truth"], policy=policy, verdict=row["verdict"],
                first_failure_stage=row["first_failure_stage"], terminal=metadata["terminal"],
                G0=guard["G0"]["status"], G1=guard["G1"]["status"], G2=guard["G2"]["status"], G3=guard["G3"]["status"],
                G4=guard["G4"]["status"], schema_status=guard["G4"]["schema_status"],
                core_exact_report=metadata["exact_report"], full_source_admitted=metadata["source_admitted"],
                full_verified_exact=metadata["verified_exact"], measurement_coverage=metadata["measurement_coverage"],
                measurement_completion=metadata["measurement_completion"], answerable_measurement_groups=metadata["answerable_measurement_groups"]))
            verdict_lookup[key, policy] = row["verdict"] + (" (" + row["first_failure_stage"] + ")" if row["first_failure_stage"] else "")
    display_controls = [dict(scenario_id=key, truth=next(x["truth"] for x in controls if x["scenario_id"] == key),
        **{policy: verdict_lookup[key, policy] for policy in POLICIES}) for key in SCENARIOS]
    art.table("constructed_control_verdicts", controls, title="Constructed controls: every scenario and paired policy",
        note="Four technically valid and ten deliberately invalid, exposed generic JSON/core scenarios. G0 retention/byte anchors; G1 provenance; G2 P05 eligibility/inventory wrapper; G3 base source replay/native-type QC; G4 emitted schema/exact report. Common guard outcomes are retained while policy verdicts apply frozen omission masks. C04 exact admission coexists with undefined measurement coverage/false completion. No independent-study or natural-corruption estimate.",
        source_fields=["analysis.fictional_policies[].scenarios", "analysis.fictional_cases[]", "ledger.guards[S-scenario]"],
        md_columns=["scenario_id", "truth", *POLICIES], md_rows=display_controls)
    policy_summary = []
    for policy in POLICIES:
        f = a["fictional_policies"][policy]
        policy_summary.append(dict(policy=policy, invalid_admitted=f["false_acceptance"]["error_count"], invalid_planned=f["false_acceptance"]["planned_denominator"],
            invalid_attempted=f["false_acceptance"]["attempted_denominator"], invalid_no_decision=f["false_acceptance"]["no_decision"],
            valid_rejected=f["false_rejection"]["error_count"], valid_planned=f["false_rejection"]["planned_denominator"],
            valid_attempted=f["false_rejection"]["attempted_denominator"], valid_no_decision=f["false_rejection"]["no_decision"]))
    art.table("constructed_policy_summary", policy_summary, title="Constructed invalid admissions and valid rejections",
        note="Counts only within each designed control stratum: ten invalid scenarios and four technically valid reports. Paired decisions are not independent observations.",
        source_fields=["analysis.fictional_policies[].false_acceptance/false_rejection"])
    paired, pair_cells = [], []
    for stratum, collection in (("native_literal_policies", a["native_policy_paired_discordance"]), ("constructed_controls", a["fictional_paired_discordance"])):
        for name, item in collection.items():
            paired.append(dict(stratum=stratum, comparison=name, planned_pairs=item["planned_pairs"], both_attempted=item["both_attempted"],
                               discordant_attempted=item["discordant_attempted"]))
            for cell in item["cells"]:
                pair_cells.append(dict(stratum=stratum, comparison=name, left_verdict=cell["left"], right_verdict=cell["right"], count=cell["count"]))
    la = a["native_literal_abstain_pairing"]
    paired.append(dict(stratum="native_literal_abstain", comparison="literal_FULL_vs_always_abstain_FULL", planned_pairs=la["planned_pairs"],
                       both_attempted=sum(count for pair,count in la["cells"].items() if "no_decision" not in pair),
                       discordant_attempted=la["cells"].get("admitted/rejected", 0) + la["cells"].get("rejected/admitted", 0)))
    for left in ("admitted", "rejected", "no_decision"):
        for right in ("admitted", "rejected", "no_decision"):
            pair_cells.append(dict(stratum="native_literal_abstain", comparison="literal_FULL_vs_always_abstain_FULL",
                left_verdict=left, right_verdict=right, count=la["cells"].get(left + "/" + right, 0)))
    art.table("paired_discordance", paired, title="Paired descriptive discordance by stratum",
        note="Each pair uses the same unit/scenario and retained bytes. No pooling of the twelve native units with fourteen constructed scenarios; no intervals, significance tests or independence claims.",
        source_fields=["analysis.native_policy_paired_discordance", "analysis.fictional_paired_discordance", "analysis.native_literal_abstain_pairing"])
    art.table("paired_verdict_cells", pair_cells, title="All paired verdict cells, including zeros",
        note="Nine possible verdict combinations are retained for each of seven predeclared descriptive comparisons; zeros are observed accounting cells, not missing cases.",
        source_fields=["analysis.*paired_discordance.*.cells", "analysis.native_literal_abstain_pairing.cells"])
    producer, wrapper, cost = a["resources"], a["amortized_source_verification"]["wrapper_resources"], audit["cost"]
    generation_wall = sum(x["shared_pair_wall_seconds"] for x in timings)
    generation_cpu = sum(x["shared_pair_cpu_seconds"] for x in timings)
    scoring_wall = sum(x["literal_scoring_wall_seconds"] + x["abstain_scoring_wall_seconds"] for x in timings)
    scoring_cpu = sum(x["literal_scoring_cpu_seconds"] + x["abstain_scoring_cpu_seconds"] for x in timings)
    def phase(name, basis, wall, cpu=None, rss=None, peak=None, hashes=None, overlap="none"):
        return dict(phase=name, basis=basis, wall_seconds=wall, cpu_seconds=cpu, sampled_process_rss_bytes=rss,
            process_lifetime_peak_bytes=peak, logical_completed_hash_bytes=hashes, partial_failed_hash_bytes=None, physical_io_bytes=None, platform_cost_usd=None,
            overlap=overlap, scientific_validation="not_established")
    resource_rows = [
        phase("producer_total", "all 38 outputs/90 decisions plus source verification/retention", producer["wall_seconds"], producer["cpu_seconds"],
              producer["peak_sampled_process_rss_bytes"], producer["process_lifetime_peak_bytes"], producer["logical_completed_hash_bytes"]),
        phase("native_generation_pairs", "12 shared packet-read/literal+abstain pairs; counted once per case", generation_wall, generation_cpu,
              overlap="subphase within producer_total"),
        phase("native_scoring", "24 retained native output scoring calls", scoring_wall, scoring_cpu, overlap="subphase within producer_total"),
        phase("amortized_source_verification", "one source-inclusive wrapper replay shared across native cells/policies", wrapper["wall_seconds"],
              hashes=wrapper["logical_bytes_hashed_by_wrapper"] + wrapper["logical_base_completed_hash_bytes"], overlap="subphase within producer_total"),
        phase("independent_source_audit", "separate source-inclusive audit of all 38 outputs/90 decisions", cost["wall_seconds"], cost["cpu_seconds"],
              cost["peak_sampled_process_rss_bytes"], cost["process_lifetime_peak_bytes"], cost["logical_completed_hash_bytes"]),
    ]
    art.table("resource_phases", resource_rows, title="Resource phases with explicit overlap and unknowns",
        note="Do not add producer subphases to the producer total. Shared generation is counted once per native case. Phase-specific memory/CPU not measured stay unknown; process-lifetime peak is not an arm-specific peak. Physical I/O/platform cost are unknown. Policy projections are not separate end-to-end timing runs.",
        source_fields=["analysis.resources", "analysis.amortized_source_verification.wrapper_resources", "ledger.output_cells[].shared_case_generation_resources/scoring_resources", "audit.cost"],
        md_columns=["phase", "wall_seconds", "cpu_seconds", "sampled_process_rss_bytes", "process_lifetime_peak_bytes", "logical_completed_hash_bytes", "overlap"])
    schedules = [dict(cell_id=x["cell_id"], case_id=x["case_id"], arm=x["arm"], stratum=x["stratum"], terminal=x["terminal"],
        received_terminal=x["received_terminal"], raw_bytes=x["raw_bytes"], exact_report=x["strict_exact_report"],
        full_source_admitted=x["full_source_admitted"], full_verified_exact=x["full_verified_exact"]) for x in ledger["output_cells"]]
    art.table("output_schedule", schedules, title="Complete 38-output terminal accounting",
        note="All scheduled outputs remain in accounting, including the two malformed constructed returns. Native and constructed strata are separate; this mixed schedule is not a success denominator.",
        source_fields=["ledger.output_cells[]"])
    decisions = [dict(decision_id=x["decision_id"], output_cell_id=x["output_cell_id"], policy=x["policy"], verdict=x["verdict"],
        terminal=x["terminal"], first_failure_stage=x["first_failure_stage"]) for x in ledger["decision_cells"]]
    art.table("decision_schedule", decisions, title="Complete 90-decision accounting",
        note="Thirty-six native literal policy decisions, twelve native abstention decisions and 42 constructed decisions. Global 57 admitted/33 rejected is accounting only, never a pooled success endpoint.",
        source_fields=["ledger.decision_cells[]"])
    return missingness, policy_summary, resource_rows


def figure_data(docs, missingness, policy_summary):
    nodes = [
        dict(id="originals", x=160, y=335, w=184, h=43, title="Frozen original frame", lines=["137 retained originals", "receipt / role / cutoff checks"]),
        dict(id="generation", x=24, y=250, w=204, h=54, title="Generation branch", lines=["original-only source packets", "literal assembler / always abstain"]),
        dict(id="references", x=276, y=250, w=204, h=54, title="Evaluator branch", lines=["separate original rereads", "source-replayed references"]),
        dict(id="native_outputs", x=24, y=162, w=204, h=54, title="Native output bytes", lines=["12 units x 2 deterministic arms", "24 retained native outputs"]),
        dict(id="verification", x=276, y=162, w=204, h=54, title="Source-inclusive verification", lines=["exact facts / unknowns / guard policies", "38 outputs / 90 paired decisions"]),
        dict(id="constructed", x=24, y=76, w=204, h=48, title="Constructed candidates", lines=["14 exposed JSON/core scenarios", "untrusted fictional attempts"]),
        dict(id="analysis", x=276, y=76, w=204, h=48, title="Frozen descriptive analysis", lines=["12 native units + 14 control scenarios", "source-audited retained metadata"]),
    ]
    edges = [dict(source="originals", target="generation", points=[[188,335],[126,304]]),
        dict(source="originals", target="references", points=[[316,335],[378,304]]),
        dict(source="generation", target="native_outputs", points=[[126,250],[126,216]]),
        dict(source="references", target="verification", points=[[378,250],[378,216]]),
        dict(source="native_outputs", target="verification", points=[[228,189],[276,189]]),
        dict(source="constructed", target="verification", points=[[228,100],[252,100],[252,175],[276,175]]),
        dict(source="verification", target="analysis", points=[[378,162],[378,124]])]
    return {
        "figure1-flow": dict(title="Separate source-only branches", width_pt=504, height_pt=410, nodes=nodes, edges=edges,
            source_units=12, constructed_scenarios=14, outputs=38, decisions=90, original_files=docs["register"]["original_parent_count"],
            independence="not_established", shared_helper_algorithms=True, source="pinned analysis/ledger/audit/register metadata; schematic custody paths"),
        "figure2-availability": dict(title="Native measurement-slot availability", width_pt=504, height_pt=370,
            rows=[dict(case_id=x["case_id"], answerable=x["measurement_answerable"], native_null=x["measurement_null"], requested=x["measurement_requested"]) for x in missingness],
            answerable_total=40, native_null_total=8, requested_total=48, measurement_groups=12, independent_studies="not_established",
            denominator_note="40/48 slots answerable; native nulls are excluded from reporting denominators."),
        "figure3-controls": dict(title="Admissions of constructed invalid scenarios", width_pt=504, height_pt=320,
            rows=policy_summary, invalid_scenarios=10, valid_scenarios=4, paired_policies=True, natural_fault_prevalence="not_estimated", independent_studies="not_established"),
    }


def build_figures(data, art):
    from reportlab import rl_config
    from reportlab.graphics import renderPDF, renderSVG
    from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
    from reportlab.lib.colors import HexColor, white
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from pypdf import PdfReader
    from PIL import Image
    rl_config.invariant = 1
    ink, muted, teal, pale, blue, amber = map(HexColor, ("#183344", "#506675", "#276D77", "#DFE7EA", "#527B9D", "#C78B34"))
    results = {}
    def label(d, x, y, value, size=9, color=ink, bold=False, anchor="start"):
        d.add(String(x, y, value, fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=size, fillColor=color, textAnchor=anchor))
    def rule(d, x1, y1, x2, y2, color=pale, width=0.7):
        d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width))
    def arrow(d, points):
        for p, q in zip(points, points[1:]):
            rule(d, *p, *q, color=muted, width=1)
        p, q = points[-2], points[-1]
        import math
        angle = math.atan2(q[1]-p[1], q[0]-p[0])
        length, wing = 6, 2.7
        back = (q[0]-length*math.cos(angle), q[1]-length*math.sin(angle))
        d.add(Polygon([q[0],q[1],back[0]+wing*math.sin(angle),back[1]-wing*math.cos(angle),
                       back[0]-wing*math.sin(angle),back[1]+wing*math.cos(angle)], fillColor=muted, strokeColor=muted))
    for name, values in data.items():
        width, height = values["width_pt"], values["height_pt"]
        d = Drawing(width, height)
        d.add(Rect(0, 0, width, height, fillColor=white, strokeColor=None))
        if name == "figure1-flow":
            label(d, 24, 394, values["title"], 14, bold=True)
            for edge in values["edges"]:
                arrow(d, edge["points"])
            for node in values["nodes"]:
                x,y,w,h = (node[k] for k in ("x","y","w","h"))
                fill = HexColor("#F1F6F7") if node["id"] not in ("constructed", "analysis") else HexColor("#F8F3E8") if node["id"] == "constructed" else HexColor("#E8F0F5")
                d.add(Rect(x,y,w,h,rx=5,ry=5,fillColor=fill,strokeColor=pale,strokeWidth=0.8))
                label(d, x+w/2, y+h-16, node["title"], 10, bold=True, anchor="middle")
                for i,line in enumerate(node["lines"]):
                    need(stringWidth(line,"Helvetica",8.5) <= w-12, "Flow label exceeds box")
                    label(d,x+w/2,y+h-29-i*11,line,8.5,color=muted,anchor="middle")
            label(d,24,48,"Preparation helpers are shared; the independent audit projects originals separately.",8.3,color=muted)
            label(d,24,33,"Arrows show custody paths, not independent data sets or biological validation.",8.3,color=muted)
            label(d,24,18,"Twelve native source units are not twelve independent studies.",8.3,color=muted)
        elif name == "figure2-availability":
            label(d,24,346,values["title"],14,bold=True)
            label(d,24,328,"Twelve source units; four requested native components per unit",9,color=muted)
            d.add(Rect(88,305,9,9,fillColor=teal,strokeColor=None))
            label(d,102,306,"Answerable native value (40)",8.7)
            d.add(Rect(298,305,9,9,fillColor=pale,strokeColor=None))
            label(d,312,306,"Native null (8)",8.7)
            left, span = 88, 384
            for tick in range(5):
                x=left+span*tick/4
                rule(d,x,89,x,289)
                label(d,x,75,str(tick),8.5,color=muted,anchor="middle")
            for i,row in enumerate(values["rows"]):
                y=278-i*16
                label(d,77,y+2,row["case_id"],8.8,anchor="end")
                known_width=span*row["answerable"]/4
                null_width=span*row["native_null"]/4
                d.add(Rect(left,y,known_width,11,fillColor=teal,strokeColor=None))
                if null_width:
                    d.add(Rect(left+known_width,y,null_width,11,fillColor=pale,strokeColor=None))
                    label(d,left+known_width+null_width/2,y+2,str(row["native_null"]),8,color=ink,anchor="middle")
                label(d,left+known_width/2,y+2,str(row["answerable"]),8,color=white,bold=True,anchor="middle")
            label(d,280,58,"Requested measurement components per source unit",9,color=muted,anchor="middle")
            label(d,24,37,values["denominator_note"],8.3,color=muted)
            label(d,24,22,"One measurement group per unit; no independent-study or biological inference.",8.3,color=muted)
        else:
            label(d,24,296,values["title"],14,bold=True)
            label(d,24,278,"Ten deliberately invalid, exposed controls; paired policies",9,color=muted)
            left,span=150,316
            display={"FULL":"FULL","WITHOUT_WRAPPER":"WITHOUT_WRAPPER","WIRE_ONLY":"WIRE_ONLY"}
            for tick in range(0,11,2):
                x=left+span*tick/10
                rule(d,x,109,x,253)
                label(d,x,95,str(tick),8.5,color=muted,anchor="middle")
            for row,y,color in zip(values["rows"],(233,181,129),(teal,blue,amber)):
                label(d,left-12,y+5,display[row["policy"]],9,bold=True,anchor="end")
                d.add(Rect(left,y,span,20,fillColor=HexColor("#F3F6F7"),strokeColor=None))
                length=span*row["invalid_admitted"]/10
                if length:
                    d.add(Rect(left,y,length,20,fillColor=color,strokeColor=None))
                label(d,left+length+7,y+5,f"{row['invalid_admitted']}/10",10,bold=True)
            label(d,308,77,"Constructed invalid scenarios admitted",9,color=muted,anchor="middle")
            label(d,24,53,"Valid reports rejected: 0/4 under every policy.",9,bold=True)
            label(d,24,35,"Designed generic JSON/core controls; no estimate of natural fault prevalence.",8.3,color=muted)
            label(d,24,20,"Paired decisions are not independent studies; scientific validation is not established.",8.3,color=muted)
        pdf,svg,png=(OUT/"figures"/(name+suffix) for suffix in (".pdf",".svg","-preview.png"))
        pdf.parent.mkdir(parents=True,exist_ok=True)
        renderPDF.drawToFile(d,str(pdf),title=values["title"],author="",creator="P05 post-result presentation from pinned metadata")
        renderSVG.drawToFile(d,str(svg))
        subprocess.run([str(POPLER),"-singlefile","-r","160","-png",str(pdf),str(png.with_suffix(""))],check=True,capture_output=True)
        reader=PdfReader(str(pdf))
        need(len(reader.pages)==1 and values["title"] in reader.pages[0].extract_text(),"PDF page/text validation failed")
        need(len(reader.pages[0].images)==0 and b"<image" not in svg.read_bytes(),"Vector figure contains a raster image")
        with Image.open(png) as preview:
            dimensions=list(preview.size)
            need(min(dimensions)>600,"Preview unexpectedly small")
        for path in (pdf,svg,png):
            relative=path.relative_to(OUT).as_posix()
            raw=path.read_bytes()
            art.outputs[relative]=dict(path="paper/results/"+relative,sha256=sha(raw),bytes=len(raw),section=values["title"],
                source_fields=["figures/"+name+"-data.json"],format=path.suffix.lstrip("."),vector=path.suffix in (".pdf",".svg"))
        results[name]=dict(pdf_pages=1,pdf_raster_images=0,media_box_pt=[width,height],preview_pixels=dimensions,
            caption="figures/"+name+"-caption.md",data="figures/"+name+"-data.json",manual_visual_review="required separately; not inferred from machine checks")
    return results


def build(docs,proofs):
    import reportlab,pypdf,PIL
    art=Artifacts()
    missingness,policies,resources=make_tables(docs,art)
    data=figure_data(docs,missingness,policies)
    for name,value in data.items():
        art.json("figures/"+name+"-data.json",value,section=value["title"],source_fields=["pinned analysis/ledger/audit/register metadata; see tables"],extra=dict(caption=CAPTIONS[name]))
        art.write("figures/"+name+"-caption.md",(CAPTIONS[name]+"\n").encode(),section=value["title"],source_fields=["figures/"+name+"-data.json"])
    figures=build_figures(data,art)
    readme="""# P05 paper results: deterministic technical source validation

These post-result presentation artifacts consume pinned analyzed metadata only.
The literal assembler reports complete verified source facts and passes 80% measurement completion in 12/12 selected native units. Always-abstain completes 0/12 and emits no fact assertions. Forty of 48 native measurement slots are answerable; eight are native nulls. These twelve units are not twelve independent studies.

Constructed invalid admissions are FULL 0/10, WITHOUT_WRAPPER 2/10 and WIRE_ONLY 7/10. All three reject 0/4 technically valid controls. The fourteen exposed generic JSON/core controls are separate from native cases and do not estimate natural corruption prevalence. Technical fidelity does not establish biological, model or clinical superiority. No new endpoint, interval, significance test, power calculation or reweighting is introduced.

FULL requires all frozen retention/provenance, P05 eligibility/inventory, base source-replay and exact-report checks. WITHOUT_WRAPPER omits only the P05 mapping/eligibility/inventory wrapper (G2), retaining the actual base guards. WIRE_ONLY requires retention/hash anchoring plus output schema/bounds and does not qualify factual source reporting. These weaker policies are diagnostic projections of retained guard outcomes, not usable clinical methods. Measurement coverage averages matched answerable-component fractions equally across groups; native nulls are excluded, so 40/48 source availability is distinct from 100% literal reporting coverage.

## Files and use

`tables/` contains CSV plus readable Markdown for all 24 native arm returns, 96 family-accounting rows, 12 source missingness rows, 42 constructed policy verdicts, seven paired comparisons/all 63 verdict cells, resource phases, complete 38-output and 90-decision accounting. CSV `unknown` means unavailable; it never substitutes zero. Undefined zero-answerable-group coverage stays unavailable. Markdown rounds only displayed floats to six significant digits; CSV retains Python round-trip numeric spelling.

`figures/` contains three native-vector PDF/SVG figures, 160 dpi PNG previews, exact machine-readable figure data and separate captions. Figures require visual review of the current previews; PDF page counts/text and PNG dimensions are checked by the builder. The artifact manifest maps every generated output to its exact sources, columns/rows and hash. The manifest itself is excluded from its recursive output hashes.

* Native tables: [arm results](tables/native_case_results.md), [fact accounting](tables/native_fact_accounting.md), [missingness](tables/native_missingness.md).
* Constructed controls: [all verdicts/stages](tables/constructed_control_verdicts.md), [policy totals](tables/constructed_policy_summary.md), [paired discordance](tables/paired_discordance.md).
* Resources: [phases](tables/resource_phases.md), [shared generation/scoring by case](tables/native_operation_resources.md).
* Complete accounting: [38 outputs](tables/output_schedule.md), [90 decisions](tables/decision_schedule.md), [all paired verdict cells](tables/paired_verdict_cells.md).
* Vector figures: [source flow](figures/figure1-flow.pdf), [native availability](figures/figure2-availability.pdf), [constructed admissions](figures/figure3-controls.pdf). Caption files sit beside the figures.

## Resource interpretation

Producer total includes all generation/guard/source-verification/retention work. The native generation row deduplicates the shared literal/abstain pair once per case; native scoring sums 24 measured calls. The 197.812 s source wrapper is a subphase within the 203.828 s producer total, not an extra cost to add to it. The independent audit is separately 7.125 s. Policy verdict projections are not independent end-to-end runtime runs. Phase-specific memory/CPU, physical I/O, partial failed hash bytes and platform costs remain unknown where unmeasured. Overall process-lifetime peak is distinct from sampled RSS and cannot be attributed to an arm.

## Rebuild

Use the already available bundled Python runtime (reportlab/pypdf/Pillow), without installing packages. Run the PDF skill marker exactly once immediately before the first PDF generation for the authoring operation; it is deliberately outside this rebuild script. Then run:

```powershell
& 'C:/Users/zzric/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/science/build_p05_paper_assets.py --build --analysis data/derived/preprint-p05-analysis-20261101T092110Z/analysis.json --analysis-sha256 ee9f02ea3c3692bbd8b7d63d2d2cd545cfd769ccee9ee7454b4ed00c7ac87312 --ledger data/derived/preprint-p05-experiment-20261101T091345Z/ledger.json --ledger-sha256 b2a9727ca9ce89865b80ffe80b21a325ea6d91d8844247740ac2c2ecc9a4faa0 --audit planning/review-assets/preprint-p05-20261031/EXPERIMENT-AUDIT-v1.json --audit-sha256 f10f15959f8497821115f65268808c98ae345079c7361722390a479b15506922
```

`--check-inputs` performs metadata/hash checks without writing or generating PDFs. Source audit status and the analysis seal are checked, and the current frozen analyzer SHA must match. The original ledger retains its pre-audit `COMPLETED_PENDING_INDEPENDENT_AUDIT` status; the separately pinned PASS source-inclusive audit establishes the later verification state without rewriting the ledger.

PDF invariant mode is enabled, with ReportLab standard Helvetica/Helvetica-Bold fonts and no external font-file path. Rebuilding under the same local Python/ReportLab/Poppler/font environment is expected to repeat payload bytes; cross-platform font substitution, SVG text rendering and dependency changes can differ. For a fresh-directory repeat, add `--output-root tmp/pdfs/p05-paper-rebuild` (an empty workspace directory). Package-relative manifest paths remain the logical `paper/results/` paths. Compare all CSV/Markdown/SVG/PDF/PNG payload hashes; manual visual review remains separate.

This rendering code was written after results were available. It only formats frozen results and records its own code hash; it does not modify source inputs, READY, the experiment, analyzer, original records or evaluator facts. No models, network, new downloads, spending or monitors are used. Source/expected-reference/human/protected inputs are forbidden. Scientific validation and independent-study qualification remain not_established. Independent numeric review and author/root visual review remain separate acceptance evidence.
"""
    art.write("README.md",readme.encode(),section="P07 presentation interpretation and reproduction",source_fields=list(proofs))
    version=subprocess.run([str(POPLER),"-v"],capture_output=True,text=True,check=True)
    poppler=(version.stdout+version.stderr).splitlines()[0]
    manifest=dict(schema_version=1,status="BUILT_FROM_FROZEN_AUDITED_METADATA",presentation_code_written_after_results=True,
        builder=dict(path=Path(__file__).relative_to(ROOT).as_posix(),sha256=sha(Path(__file__).read_bytes())),
        frozen_analyzer=dict(path=ANALYZER.relative_to(ROOT).as_posix(),sha256=ANALYZER_SHA),inputs=proofs,
        tool_versions=dict(python=platform.python_version(),interpreter=sys.executable,reportlab=reportlab.Version,pypdf=pypdf.__version__,Pillow=PIL.__version__,poppler=poppler),
        rendering=dict(invariant_pdf=True,fonts=["Helvetica","Helvetica-Bold"],font_policy="ReportLab standard fourteen fonts; no external font-file paths",
            reproducibility="same local dependency/font/rendering environment only; no cross-platform byte promise",package_paths="logical paper/results paths independent of temporary physical output root"),
        scope=dict(native_units=12,independent_studies="not_established",constructed_scenarios=14,scheduled_outputs=38,paired_decisions=90,
                   source_ledger_status=docs["analysis"]["source_ledger_status"],independent_audit_status=docs["audit"]["status"],scientific_validation="not_established"),
        tables_and_outputs=art.outputs,figures=figures,figure_captions=CAPTIONS,manifest_self_excluded=True,
        numeric_review="separate independent source-ledger/audit comparison required",models=0,network_calls=0,new_downloads=0,provider_spending_usd=0,platform_cost_usd=None)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"ARTIFACTS.json").write_text(json.dumps(manifest,ensure_ascii=True,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return manifest


def main(argv=None):
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build",action="store_true")
    action.add_argument("--check-inputs",action="store_true")
    parser.add_argument("--output-root",type=Path,default=DEFAULT_OUT,help="Default paper/results, or an empty workspace directory for byte-reproduction checks")
    for key in ("analysis","ledger","audit"):
        parser.add_argument("--"+key,type=Path,default=PINS[key][0])
        parser.add_argument("--"+key+"-sha256",default=PINS[key][1])
    args=parser.parse_args(argv)
    requested_out=args.output_root.resolve()
    need(requested_out.is_relative_to(ROOT) and requested_out != ROOT,"Output root must be inside this workspace")
    if requested_out != DEFAULT_OUT:
        need(not requested_out.exists() or not any(requested_out.iterdir()),"Fresh reproduction directory must be empty")
    OUT=requested_out
    for key in ("analysis","ledger","audit"):
        need(getattr(args,key).resolve()==PINS[key][0] and getattr(args,key+"_sha256")==PINS[key][1],"Only the pinned metadata inputs are permitted")
    docs,proofs=pinned_inputs()
    if args.check_inputs:
        print(json.dumps(dict(status="PASS_PINNED_METADATA_ONLY",native_units=12,outputs=38,decisions=90,input_sha256={key:value["sha256"] for key,value in proofs.items()}),sort_keys=True))
    else:
        manifest=build(docs,proofs)
        print(json.dumps(dict(status=manifest["status"],output_root=str(OUT),figures=3,pdfs=3,svg=3,previews=3,generated_files=len(manifest["tables_and_outputs"])),sort_keys=True))


if __name__=="__main__":
    main()
