"""Portable post-result P05 presentation, version1.

Ports the frozen P07 table serialization and ReportLab geometry; no new endpoint.
Only explicitly pinned public evaluator/source metadata and payload commitments
are read. No original sources, reference facts, raw outputs or old tools import.
Run the PDF skill operation marker externally before the first authoring build.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

METHOD = "p09.portable_p05_presentation.v1"
SOURCE_POLICY_SHA = "8d88c5dca9dfbebfd7851a6e50b5d668bdedd0a6f35bd0b77aebdff01fabf6c1"
COMPARISON_SHA = "1fc123d3c368d355c1f3d66a76eeaacea9ae954c6a6fad9aa3d05390d225cce0"
LEGACY_MANIFEST_SHA = "84d4a31e842d3085133d384429729ef2501425d33bf2b92f65d9c64699a87428"
LEGACY_BUILDER_SHA = "b731f711fa4cb4ecff1204067ee4cb259f67f97141bb75a823a0425a25d41093"
OUT = None
POPLER = None
DEADLINE = None
INPUT_PINS = {
    "comparison": COMPARISON_SHA,
    "source_policy": SOURCE_POLICY_SHA,
    "historical_resources": "af588a157854752e66ff4de8393d000af727d1c15a1542fb6a01b9ba4ddb2970",
    "expected_payloads": "30dfdeceabe87bf4db58ec78e5106cf4a73f3286d788962d21033f27312b48c8",
}

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
        deadline_check()
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
        subprocess.run([str(POPLER),"-singlefile","-r","160","-png",str(pdf),str(png.with_suffix(""))],check=True,capture_output=True,
                       timeout=min(30, max(0.001, DEADLINE-time.monotonic())))
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


def deadline_check():
    if DEADLINE is not None and time.monotonic() >= DEADLINE:
        raise TimeoutError("Portable presentation deadline expired")


def read_pinned(path, expected, label):
    deadline_check()
    need(type(expected) is str and re.fullmatch(r"[0-9a-f]{64}", expected), "Exact SHA-256 required: " + label)
    need(expected == INPUT_PINS[label], "This version accepts only the reviewed public metadata pin: " + label)
    path = Path(path)
    need(path.is_file() and path.stat().st_size <= 4 * 1024**2, "Public metadata file absent or over 4 MiB: " + label)
    raw = path.read_bytes()
    need(sha(raw) == expected, "Public metadata byte anchor differs: " + label)
    value = json.loads(raw, object_pairs_hook=strict_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite public metadata")))
    need(type(value) is dict, "Public metadata object required: " + label)
    return value, dict(logical_input=label, filename=path.name, sha256=expected, bytes=len(raw), kind="public_metadata_only")


def payload_names():
    tables = ("native_case_results", "native_fact_accounting", "native_missingness", "native_operation_resources",
        "constructed_control_verdicts", "constructed_policy_summary", "paired_discordance", "paired_verdict_cells",
        "resource_phases", "output_schedule", "decision_schedule")
    return ({"tables/" + name + suffix for name in tables for suffix in (".csv", ".md")} |
            {"figures/" + name + suffix for name in CAPTIONS
             for suffix in (".pdf", ".svg", "-preview.png", "-data.json", "-caption.md")})


def load_public_inputs(args):
    values, proofs = {}, {}
    for label in INPUT_PINS:
        values[label], proofs[label] = read_pinned(getattr(args, label), getattr(args, label + "_sha256"), label)
    bridge, policy, resources, expected = (values[k] for k in INPUT_PINS)
    need(bridge["method"] == "p09.p05_comparison_bridge.v1" and bridge["source_policy_sha256"] == SOURCE_POLICY_SHA,
         "Comparison/source policy binding differs")
    for label in ("comparison", "historical_resources", "expected_payloads"):
        need(values[label]["role"] == "evaluation_only" and values[label]["agent_visible"] is False,
             "Presentation comparison metadata must remain evaluator-only")
    need(policy["method"] == "p09.source_policy.v1" and policy["snapshot"]["raw_root"] is None and
         len(policy["inventory"]) == 137 and len(policy["cases"]) == len(policy["tasks"]) == 12,
         "Public source-only frame differs")
    need(resources["method"] == "p09.presentation_resource_metadata.v1" and
         resources["historical_ledger_sha256"] == bridge["historical_artifacts"]["ledger"]["sha256"] and
         resources["historical_audit_sha256"] == bridge["historical_artifacts"]["audit"]["sha256"],
         "Historical resource provenance differs")
    need(expected["method"] == "p09.presentation_expected_payloads.v1" and
         expected["old_manifest_sha256"] == LEGACY_MANIFEST_SHA and
         set(expected["payloads"]) == payload_names() and len(expected["payloads"]) == 37 and
         "README.md" not in expected["payloads"], "Reviewed prior public payload manifest differs")
    for name, pin in expected["payloads"].items():
        need(set(pin) == {"sha256", "bytes"} and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]) and
             type(pin["bytes"]) is int and 0 < pin["bytes"] <= 4 * 1024**2, "Malformed payload commitment: " + name)
    analysis = bridge["historical_analysis"]
    need(analysis["scientific_validation"] == "not_established" and analysis["independent_study_count"] is None and
         analysis["inferential_statistics"] == "none" and analysis["native_denominator"] == 12,
         "Frozen scientific/denominator limits differ")
    need(tuple(x["case_id"] for x in analysis["native_cases"]) == CASES and
         tuple(x["scenario_id"] for x in analysis["fictional_cases"]) == SCENARIOS and
         len(bridge["outputs"]) == analysis["planned_output_cells"] == 38 and
         len(bridge["decisions"]) == analysis["planned_decisions"] == 90, "Frozen output/decision schedule differs")
    need(resources["independent_source_audit"]["status"] == "PASS_INDEPENDENT_EXPERIMENT_AUDIT",
         "Historical resource audit status differs")
    outputs = deepcopy(bridge["outputs"])
    native_ids = {"N-" + arm + "-" + case for case in CASES for arm in ("L", "A")}
    need(set(resources["native_output_resources"]) == native_ids, "Exactly 24 historical native resource records required")
    for output in outputs:
        if output["cell_id"] in native_ids:
            item = resources["native_output_resources"][output["cell_id"]]
            need(set(item) == {"shared_case_generation_resources", "scoring_resources"}, "Unexpected resource projection field")
            output.update(deepcopy(item))
    decisions = deepcopy(bridge["decisions"])
    for decision in decisions:
        suffix = "-" + decision["policy"]
        need(decision["decision_id"].startswith("D-") and decision["decision_id"].endswith(suffix), "Malformed decision identity")
        cell = decision["decision_id"][2:-len(suffix)]
        need(cell in {x["cell_id"] for x in outputs} and
             decision.get("output_cell_id", cell) == cell, "Decision/output identity differs")
        decision["output_cell_id"] = cell
    # Local names below preserve the ported P07 formatting interface. They are
    # in-memory views of the four pinned public inputs, never old private reads.
    docs = dict(analysis=analysis,
        ledger=dict(output_cells=outputs, decision_cells=decisions, guards=bridge["guards"]),
        audit=resources["independent_source_audit"], register=dict(original_parent_count=len(policy["inventory"])))
    return docs, proofs, expected


PORTABLE_RESULTS_README = """# Portable reconstruction of historical P05 presentation

This separately versioned exporter rebuilds the historical P07 presentation from four explicitly pinned public metadata inputs. It reads no original sources, reference facts, raw outputs or private archive. All 37 CSV/Markdown table and PDF/SVG/PNG/data/caption payloads are checked against a reviewed projection of the original result manifest. This README and ARTIFACTS.json are new portable artifacts; they do not claim the old manifest or README byte identity.

The historical literal arm had complete verified exact reports and 80% measurement completion in 12/12 native source units; always-abstain completed 0/12. Source availability was 40 answerable and 8 null components among 48 requested slots, distinct from 100% literal coverage over answerable groups. The 12 units are not independent studies. Constructed invalid admissions were FULL 0/10, WITHOUT_WRAPPER 2/10 and WIRE_ONLY 7/10; all policies rejected 0/4 technically valid controls. The 14 exposed constructed JSON/core controls are a separate stratum. These remain technical source-fidelity results, with no biological, model or clinical superiority established.

`tables/` contains 11 CSVs and 11 readable Markdown views covering native arms/families/missingness, all constructed verdicts and guard stages, paired discordance, resource phases and the complete 38-output/90-decision schedule. `figures/` contains three vector PDF/SVG figures, 160 dpi PNG previews, exact figure data and captions. CSV unknown values remain unknown. The frozen geometry/captions and table serialization were ported after results were known; no new endpoint, inference or reweighting is performed.

Every resource value inside the tables is a retained historical measurement. Shared literal/abstain generation is counted once per native case; scoring covers 24 native calls, and source verification overlaps the historical producer total. These values are not costs of this new presentation build. Its elapsed time is recorded separately in the new manifest. Unmeasured historical physical I/O/platform costs remain unknown.

Rebuild using Python with already available reportlab, pypdf and Pillow, plus Poppler's pdftoppm supplied explicitly or on PATH. See the exporter directory's README for the full command. No dependency installation or network access occurs. ReportLab invariant PDF mode and standard Helvetica/Helvetica-Bold fonts are used; no font files are bundled. Byte identity is checked for this exact historical payload set under the same rendering environment, with no cross-platform byte promise. Current visual review remains a separate check.

Public source-policy metadata is a reconstruction dependency descriptor. Rendering these tables does not execute native source replay or verify the original private archive/seal chain. Comparison data remains evaluator-only, excluded from generation until new output sealing. Author declarations and public-deposit authorization are separate.
"""


def build_portable(docs, proofs, expected):
    import reportlab, pypdf, PIL
    started, cpu_started = time.monotonic(), time.process_time()
    need(not OUT.exists(), "A fresh absent output directory is required; no overwrite or resume")
    OUT.mkdir(parents=True, exist_ok=False)
    art = Artifacts()
    deadline_check()
    missingness, policies, _ = make_tables(docs, art)
    data = figure_data(docs, missingness, policies)
    for name, value in data.items():
        art.json("figures/" + name + "-data.json", value, section=value["title"],
            source_fields=["public comparison historical_analysis plus source-policy inventory"], extra=dict(caption=CAPTIONS[name]))
        art.write("figures/" + name + "-caption.md", (CAPTIONS[name] + "\n").encode(),
            section=value["title"], source_fields=["figures/" + name + "-data.json"])
    figures = build_figures(data, art)
    need(set(art.outputs) == payload_names(), "Generated historical payload set differs")
    comparisons = []
    for name, pin in expected["payloads"].items():
        actual = art.outputs[name]
        need(actual["sha256"] == pin["sha256"] and actual["bytes"] == pin["bytes"], "Historical payload mismatch: " + name)
        comparisons.append(dict(path=name, sha256=actual["sha256"], bytes=actual["bytes"], matches_historical=True))
    art.write("README.md", PORTABLE_RESULTS_README.encode(), section="New portable interpretation/rebuild instructions",
              source_fields=list(proofs))
    for name, item in art.outputs.items():
        item["path"] = name
        item["provenance_note"] = "Historical field labels in ported table mappings name original provenance; runtime inputs are the four public metadata files."
    deadline_check()
    version = subprocess.run([str(POPLER), "-v"], capture_output=True, text=True, check=True, timeout=10)
    poppler = (version.stdout + version.stderr).splitlines()[0]
    need(sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) <= 16 * 1024**2, "Presentation output exceeds 16 MiB")
    manifest = dict(schema_version=2, method=METHOD, status="PASS_PORTABLE_HISTORICAL_PAYLOAD_REPRODUCTION",
        authority="post-result presentation only; no native source execution or new study authority",
        builder=dict(filename=Path(__file__).name, sha256=sha(Path(__file__).read_bytes())),
        ported_formatting=dict(historical_builder_sha256=LEGACY_BUILDER_SHA, historical_manifest_sha256=LEGACY_MANIFEST_SHA,
            unchanged_payload_count=37, portable_readme_replacement=True, old_manifest_impersonated=False),
        inputs=proofs, historical_payload_comparisons=comparisons,
        historical_resources="retained old measurements; not this presentation build's resource cost",
        new_presentation_build_resources=dict(wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu_started,
            physical_io_bytes=None, platform_cost_usd=None),
        tool_versions=dict(python=platform.python_version(), reportlab=reportlab.Version, pypdf=pypdf.__version__, Pillow=PIL.__version__,
            poppler=poppler, pdftoppm_sha256=sha(Path(POPLER).read_bytes())),
        rendering=dict(invariant_pdf=True, fonts=["Helvetica", "Helvetica-Bold"], external_font_files=False,
            reproducibility="same rendering environment only; no cross-platform byte promise"),
        scope=dict(native_units=12, constructed_scenarios=14, outputs=38, decisions=90,
            independent_studies="not_established", scientific_validation="not_established", new_endpoints=0),
        tables_and_outputs=art.outputs, figures=figures, figure_captions=CAPTIONS, manifest_self_excluded=True,
        input_bytes_limit=4*1024**2, output_bytes_limit=16*1024**2,
        deadline_enforcement="cooperative phase checks; bounded Poppler subprocesses; no hard OS watchdog",
        model_calls=0, network_calls=0, new_downloads=0, provider_spending_usd=0,
        original_payload_reads=0, expected_reference_reads=0, raw_output_reads=0)
    (OUT / "ARTIFACTS.json").write_text(json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    global OUT, POPLER, DEADLINE
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--check-inputs", action="store_true")
    for label in INPUT_PINS:
        parser.add_argument("--" + label.replace("_", "-"), type=Path, required=True)
        parser.add_argument("--" + label.replace("_", "-") + "-sha256", required=True)
    parser.add_argument("--output-root", type=Path, help="Fresh absent directory; never overwrites historical results")
    parser.add_argument("--pdftoppm", help="Explicit executable, or resolve pdftoppm from PATH")
    parser.add_argument("--seconds", type=int, default=120)
    args = parser.parse_args(argv)
    need(1 <= args.seconds <= 300, "Presentation wall budget must be 1..300 seconds")
    DEADLINE = time.monotonic() + args.seconds
    docs, proofs, expected = load_public_inputs(args)
    if args.check_inputs:
        print(json.dumps(dict(status="PASS_PUBLIC_PRESENTATION_METADATA_ONLY", input_sha256={k:v["sha256"] for k,v in proofs.items()},
            historical_payloads=37, old_readme_replaced=True), sort_keys=True))
        return
    need(args.output_root is not None, "--output-root is required for build")
    OUT = args.output_root.absolute()
    executable = args.pdftoppm or shutil.which("pdftoppm")
    need(executable is not None, "Supply --pdftoppm or put pdftoppm on PATH; no automatic install")
    resolved = shutil.which(str(executable))
    need(resolved is not None, "pdftoppm executable unavailable")
    POPLER = Path(resolved).absolute()
    manifest = build_portable(docs, proofs, expected)
    print(json.dumps(dict(status=manifest["status"], output_root=str(OUT), historical_payload_matches=37,
        portable_readme=True, new_manifest=True, pdfs=3, generated_payloads=38), sort_keys=True))


if __name__ == "__main__":
    main()

