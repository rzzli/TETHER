"""Versioned P05 fictional JSON controls, distinct from native Parquet replay.

Recipes/corruptions and G0--G4 projections preserve the frozen P05 behavior.
Generation uses only a neutral task, invented source rows and a flat original
Snapshot. Evaluation separately reopens authored sources through unchanged core
proof/role/compiler guards. No oracle labels, old tools or native inputs enter
this module. These exposed constructed controls establish no scientific truth.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import time
from types import SimpleNamespace

from asof.atomic import publish_bytes
from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.provenance import InputGraph, catalog_index
from asof.serde import ContractError, canonical, encode, fingerprint, parse_json
from asof.study.source_fact_adapters import adapt_output
from asof.study.source_fact_evaluation import score_cell
from asof.study.source_fact_sources import compile_reference, verify_reference
from asof.study.stable_read import checked_path, deadline_check, hash_file, read_file, stable_files
from asof.wire import same_json

from . import policy_v1 as policy
from .baseline_v1 import literal_report

VERSION = "p05.portable_fictional_controls.v1"
SCENARIOS = tuple([f"C{n:02d}" for n in range(1, 5)] + [f"F{n:02d}" for n in range(1, 11)])
POLICIES = ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")
STAGES = ("G0", "G1", "G2", "G3", "G4")
MEASUREMENTS = ("beta", "standardError", "pValueMantissa", "pValueExponent")
DOMAIN = "generic_JSON_core_and_applicable_P05_predicates"


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _cutoff():
    return datetime.fromisoformat(policy.CUTOFF.replace("Z", "+00:00"))


@dataclass(frozen=True)
class ControlScenario:
    """Trusted authoring result, not a serialized reference or acceptance token.

    fixture_root is supplied by the caller to prepare_controls independently of
    the evaluator Snapshot's declared raw_root. Nested documents remain ordinary
    JSON-compatible objects; callers retain responsibility for configuration.
    """

    scenario_id: str
    fixture_root: Path
    case: dict
    task: dict
    groups: dict
    generation_snapshot: Snapshot
    evaluation_snapshot: Snapshot
    catalog: dict
    original_source_anchors: tuple[dict, ...]

    @property
    def cell_id(self):
        return "S-" + self.scenario_id


def prepare_controls(root, deadline):
    """Author fourteen fresh toy source/receipt scenarios; no output or score.

    Return an insertion-ordered dict C01--C04,F01--F10 of ControlScenario objects.
    This reads no pre-existing fixture, expected-hash map or native source. The
    destination must be fresh; partial failure is retained and never resumed.
    """
    deadline_check(deadline)
    root = Path(root).absolute()
    root.mkdir(parents=True, exist_ok=False)
    scenarios = {}
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    source_bytes = 0
    for key in SCENARIOS:
        deadline_check(deadline)
        raw_root = root / key / "originals"
        raw_root.mkdir(parents=True)
        case = dict(case_id="fiction-" + key, targetId="ENSG_FICTIONAL", diseaseId="EFO_FICTIONAL",
                    studyLocusId="locus-fictional", release_id="25.09")
        gwas = dict(id="fictional-evidence", targetId=case["targetId"], diseaseId=case["diseaseId"],
            studyLocusId=case["studyLocusId"], studyId="STUDY_A", variantId="VARIANT_A", datasourceId="gwas_credible_sets",
            datatypeId="genetic_association", publicationDate="2026-01-01", evidenceDate="2026-01-01")
        credible = dict(studyLocusId=case["studyLocusId"], studyId="STUDY_A", variantId="VARIANT_A",
                        beta=1.25, standardError=0.25, pValueMantissa=2.0, pValueExponent=-6)
        if key in ("C02", "F07"):
            credible.update(beta=None, pValueMantissa="")
            del credible["standardError"]
        if key == "C04":
            credible.update({name: None for name in MEASUREMENTS})
        if key == "F09":
            credible["beta"] = True
        if key == "F03":
            gwas["releaseDate"] = "2026-11-02"
        credible_rows = [credible]
        if key in ("C03", "F04"):
            credible_rows.append(dict(credible, studyId="STUDY_B", variantId="VARIANT_B", standardError=-0.5))
        mapping = {
            "target": [dict(values=dict(id=case["targetId"], approvedSymbol="FICTIONAL_GENE"), locator={})],
            "disease": [dict(values=dict(id=case["diseaseId"], name="Fictional phenotype"), locator={})],
            "hgnc": [dict(values=dict(ensembl_gene_id=case["targetId"], symbol="FICTIONAL_GENE",
                                    hgnc_id="HGNC:FICTIONAL", status="Approved"), locator={})]}
        products = [("gwas", {"rows": [gwas]}), ("credible", {"rows": credible_rows}), ("mapping", mapping)]
        if key == "F02":
            products.append(("forbidden", {"invented": "not a real evaluator artifact"}))
        nodes, anchors = [], []
        catalog = dict(schema_version=1, datasets=[])
        for name, document in products:
            deadline_check(deadline)
            path = raw_root / (name + ".json")
            payload = canonical(document) + b"\n"
            publish_bytes(path, payload)
            dataset = "fiction_" + name
            role = "evaluation_only" if name == "forbidden" else "reference" if name == "mapping" else "agent_evidence"
            receipt = dict(status="completed", dataset_id=dataset, release_id="25.09", relative_path=path.name,
                sha256=_digest(payload), bytes=len(payload), url="https://example.invalid/" + name,
                completed_at_utc=observed.isoformat())
            receipt_raw = canonical(receipt) + b"\n"
            receipt_path = raw_root / (name + ".receipt.json")
            publish_bytes(receipt_path, receipt_raw)
            available = Availability(None, None, None, None, observed.date(), "public_download_receipt", "fictional only",
                                     observed, _digest(receipt_raw))
            nodes.append(SourceNode("fiction-" + name, dataset, "25.09", path.name, _digest(payload), role,
                available, TemporalClass.CONTEMPORARY, receipt["url"], receipt_path=receipt_path.name,
                receipt_sha256=_digest(receipt_raw)))
            anchors.extend((dict(path=path.name, sha256=_digest(payload), bytes=len(payload)),
                            dict(path=receipt_path.name, sha256=_digest(receipt_raw), bytes=len(receipt_raw))))
            source_bytes += len(payload) + len(receipt_raw)
            catalog["datasets"].append(dict(dataset_id=dataset, roles=[role]))
        _need(source_bytes <= 4 * 1024**2, "Fictional source cap exceeded")
        original_nodes = tuple(nodes[:3])
        generation_snapshot = Snapshot(2, "fiction-" + key, Profile.CONTEMPORARY, _cutoff().date(), False, (),
            original_nodes, str(raw_root), {"scope": "fictional_JSON_only"}, _cutoff())
        if key == "F02":
            original = nodes[0]
            nodes[0] = SourceNode(original.source_id, original.dataset_id, original.release_id, original.path,
                original.sha256, original.role, original.availability, original.temporal_classification,
                original.source_url, parents=("fiction-forbidden",), computed_at=observed,
                method_id="fiction-derived", method_version="1", receipt_path=original.receipt_path,
                receipt_sha256=original.receipt_sha256)
        evaluation_snapshot = Snapshot(2, "fiction-" + key, Profile.CONTEMPORARY, _cutoff().date(), False, (),
            tuple(nodes), str(raw_root), {"scope": "fictional_JSON_only"}, _cutoff())

        def row(value, source_id, index, family):
            return dict(source_id=source_id, family=family, locator=dict(format="json", pointer=f"/rows/{index}"),
                        physical_row_0based=index, values=value)

        groups = dict(gwas_credible_sets=[row(gwas, "fiction-gwas", 0, "gwas_credible_sets")],
            credible_set=[row(value, "fiction-credible", i, "credible_set") for i, value in
                          enumerate(credible_rows[:1] if key == "F04" else credible_rows)])
        task = policy.build_task(case, groups)
        if key == "F01":
            # Preserve stale declared source/receipt anchors, then alter observed bytes.
            with (raw_root / "gwas.json").open("ab") as stream:
                stream.write(b" ")
        scenario = ControlScenario(key, root, case, task, groups, generation_snapshot,
                                   evaluation_snapshot, catalog, tuple(anchors))
        description = dict(schema_version=1, method=VERSION, scenario_id=key, fixture_domain=DOMAIN,
            case=case, task=task, generation_snapshot=encode(generation_snapshot),
            evaluation_snapshot=encode(evaluation_snapshot), catalog=catalog,
            original_source_anchors=anchors, fixture_is_native_P05_build=False,
            candidate_outputs_created=False)
        publish_bytes(root / key / "scenario.json", canonical(description) + b"\n")
        scenarios[key] = scenario
    deadline_check(deadline)
    return scenarios


def generate_control(scenario, deadline):
    """Pure baseline + predeclared byte corruption; no evaluator/source reads."""
    deadline_check(deadline)
    _need(isinstance(scenario, ControlScenario) and scenario.scenario_id in SCENARIOS,
          "Authored scheduled control required")
    raw = literal_report(scenario.task, scenario.generation_snapshot, scenario.groups)
    key = scenario.scenario_id
    if key in ("F05", "F06", "F07"):
        output = parse_json(raw)
        fact = next(f for f in output["facts"] if f["source"]["field"] == "beta")
        if key == "F05":
            fact["value"] = 2.25
        elif key == "F06":
            fact["source"]["locator"] = dict(format="json", pointer="/rows/999")
        else:
            fact["unknown_reason"] = "field_not_in_schema"
        raw = canonical(output)
    elif key == "F08":
        raw = raw[:-1] + b',"status":"answered"}'
    elif key == "F10":
        raw += b" " * (262145 - len(raw))
    _need(len(raw) <= 512 * 1024, "Fictional raw retention cap exceeded")
    deadline_check(deadline)
    return raw


def _guard_result(function):
    started, cpu_started = time.monotonic(), time.process_time()
    try:
        value = function()
        return dict(status="pass", error_class=None, reason=None, wall_seconds=time.monotonic()-started,
                    cpu_seconds=time.process_time()-cpu_started), value
    except ContractError as error:
        return dict(status="rejected", error_class=type(error).__name__, reason=str(error)[:400],
                    wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu_started), None


def _wrapper(scenario, raw_root, deadline):
    """Real pure predicates + exhaustive JSON rows, not native column admission."""
    case = scenario.case
    mapping = parse_json(read_file(raw_root / "mapping.json", deadline, 1024**2))
    indexes = policy.mapping_index(mapping)
    groups = dict(gwas_credible_sets=[], credible_set=[])
    for name, family in (("gwas", "gwas_credible_sets"), ("credible", "credible_set")):
        rows = parse_json(read_file(raw_root / (name + ".json"), deadline, 1024**2))["rows"]
        for index, values in enumerate(rows):
            deadline_check(deadline)
            if values.get("studyLocusId") != case["studyLocusId"]:
                continue
            if family == "gwas_credible_sets" and (values.get("targetId"), values.get("diseaseId")) != (case["targetId"], case["diseaseId"]):
                continue
            decision = (policy.eligibility(values, indexes, cutoff=_cutoff()) if family == "gwas_credible_sets" else
                        dict(date_guard=policy.date_guard(values, _cutoff())))
            reasons = list(decision.get("exclusion_reasons", decision["date_guard"]["exclusion_reasons"]))
            if "annotationDate" in values:
                lower, upper, _ = policy.source_date_interval(values["annotationDate"], "annotationDate")
                _need(lower is None or policy.interval_status(lower, upper, _cutoff()) == "within_cutoff",
                      "annotationDate rejected")
            if not reasons:
                groups[family].append(dict(source_id="fiction-" + name, family=family,
                    locator=dict(format="json", pointer=f"/rows/{index}"), physical_row_0based=index, values=values))
    policy.normalization_proof(case, groups["gwas_credible_sets"], indexes)
    rebuilt = policy.build_task(case, groups)
    _need(same_json(rebuilt, scenario.task), "Exhaustive eligible JSON inventory/task differs; no subset-completeness claim")
    originals = groups["gwas_credible_sets"] + groups["credible_set"]
    supplied = scenario.groups["gwas_credible_sets"] + scenario.groups["credible_set"]
    _need(len(originals) == len(supplied) and all(same_json(a["values"], b["values"]) and
          same_json(a["locator"], b["locator"]) and a["source_id"] == b["source_id"]
          for a, b in zip(originals, supplied)), "Supplied values/bindings differ from originals")
    return dict(eligible_rows=len(originals), domain="generic_JSON_pure_predicates_only")


def project_decision(stages, policy_name, *, decision_id):
    """Project retained real stage results; no oracle supplies a decision.

    All policies retain G0. WIRE_ONLY additionally retains the real common
    typed adapter, including its task binding, but establishes no source-verified
    report admission. It is a constructed diagnostic, not a clinical method.
    """
    _need(policy_name in POLICIES, "Unscheduled fictional policy")
    required = (("G0",) if policy_name == "WIRE_ONLY" else ("G0", "G1", "G3", "G4")
                if policy_name == "WITHOUT_WRAPPER" else STAGES)
    checks = [(stage, stages[stage]["status"]) for stage in required]
    if policy_name == "WIRE_ONLY":
        checks.append(("G4", stages["G4"]["schema_status"]))
    rejection = next((stage for stage, status in checks if status == "rejected"), None)
    missing = next((stage for stage, status in checks if status not in ("pass", "rejected")), None)
    verdict = "rejected" if rejection else "no_decision" if missing else "admitted"
    return dict(decision_id=decision_id, policy=policy_name, verdict=verdict, first_failure_stage=rejection,
        terminal="unexecuted" if verdict == "no_decision" else "returned",
        required_stages=list(required) + (["G4_schema_only"] if policy_name == "WIRE_ONLY" else []),
        reason=stages[rejection].get("reason") if rejection else "required_stage_not_attempted" if missing else None,
        projection=True, scientific_validation="not_established")


def report_exactness(reference, raw, *, cell_id):
    score = score_cell(reference, raw, cell_id=cell_id)
    exact = (score["terminal"] == "returned" and score["adapter_status"] == "scorable" and
             not score["critical_errors"] and score["answer_status"] == "answered" and
             score["emitted_facts"] == len(reference.document["facts"]))
    return exact, score


def reference_counts(reference):
    facts = reference.document["facts"]
    measurements = [f for f in facts if f["family"] == "reported_measurement" and f["value"] is not None]
    return dict(requested_facts=len(facts), measurement_answerable_facts=len(measurements),
        measurement_answerable_groups=len({(f["record_key"], f["group"]) for f in measurements}))


def fact_accounting(reference, raw):
    adapted = adapt_output(raw, wire_format="typed_facts_v1", task_id=reference.document["task_id"],
                           task_sha256=reference.document["task_sha256"])
    expected = {f["fact_id"]: f for f in reference.document["facts"]}
    emitted = adapted["output"]["facts"] if adapted["status"] == "scorable" else None
    multiplicity = Counter(f["fact_id"] for f in emitted) if emitted is not None else Counter()
    families = {}
    for family in ("identity_linkage", "reported_context", "reported_measurement", "provider_metric"):
        selected = [f for f in expected.values() if f["family"] == family]
        row = dict(requested=len(selected), answerable=sum(f["value"] is not None for f in selected),
            expected_unknown_by_reason=dict(Counter(f["unknown_reason"] for f in selected if f["value"] is None)),
            correct_unknown=0 if emitted is not None else None, omitted=0 if emitted is not None else None,
            matched=0 if emitted is not None else None, false_asserted_values=0 if emitted is not None else None)
        if emitted is not None:
            row["omitted"] = sum(multiplicity[f["fact_id"]] == 0 for f in selected)
            for fact in emitted:
                original = expected.get(fact["fact_id"])
                if original is None or original["family"] != family:
                    continue
                same = all(same_json(fact[k], original[k]) for k in ("value", "unit", "source", "unknown_reason"))
                if original["value"] is None and same and multiplicity[fact["fact_id"]] == 1:
                    row["correct_unknown"] += 1
                if original["value"] is not None and same and multiplicity[fact["fact_id"]] == 1:
                    row["matched"] += 1
                if fact["value"] is not None and not same:
                    row["false_asserted_values"] += 1
        row["false_asserted"] = row["false_asserted_values"]
        families[family] = row
    return dict(families=families,
        unknown_fact_id_emissions=sum(f["fact_id"] not in expected for f in emitted) if emitted is not None else None,
        adapter_status=adapted["status"])


def evaluate_control(scenario, raw, deadline):
    """Run actual G0--G4/core guards and return genuine score or None."""
    deadline_check(deadline)
    _need(isinstance(scenario, ControlScenario) and scenario.scenario_id in SCENARIOS,
          "Authored scheduled control required")
    key = scenario.scenario_id
    raw_root = checked_path(scenario.fixture_root, key + "/originals")
    snapshot = scenario.evaluation_snapshot
    _need(Path(snapshot.raw_root) == raw_root, "Serialized fixture cannot grant a raw root")
    task = scenario.task
    stages = {name: dict(status="unexecuted", reason="preceding_admission_not_passed", error_class=None) for name in STAGES}

    def integrity():
        paths = [checked_path(raw_root, x["path"]) for x in scenario.original_source_anchors]
        with stable_files(paths, deadline=deadline):
            for item, path in zip(scenario.original_source_anchors, paths):
                _need(dict(hash_file(path, deadline)) == {"sha256": item["sha256"], "bytes": item["bytes"]},
                      "Fictional original/receipt anchor differs")
        return True

    stages["G0"], _ = _guard_result(integrity)
    reference = None
    if stages["G0"]["status"] == "pass":
        def provenance():
            graph = InputGraph(snapshot, raw_root, catalog_index(scenario.catalog))
            refs = tuple(graph.nodes)
            _need(graph.exclusion(refs, SimpleNamespace(cutoff=_cutoff())) is None,
                  "Fictional source graph after cutoff")
            paths = [graph.path(n) for n in snapshot.sources] + [checked_path(raw_root, n.receipt_path)
                    for n in snapshot.sources if n.receipt_path]
            with stable_files(paths, deadline=deadline):
                return graph.verify(refs, {})
        stages["G1"], _ = _guard_result(provenance)
    if stages["G1"]["status"] == "pass":
        paths = [checked_path(raw_root, item["path"]) for item in scenario.original_source_anchors]
        with stable_files(paths, deadline=deadline):
            stages["G2"], _ = _guard_result(lambda: _wrapper(scenario, raw_root, deadline))

        def base():
            compiled = compile_reference(task, snapshot, raw_root, scenario.catalog, deadline=deadline,
                                         approved_raw_root=raw_root)
            return verify_reference(encode(compiled.document), compiled.fingerprint, task, snapshot, raw_root,
                scenario.catalog, deadline=deadline, approved_raw_root=raw_root)
        # G3 is still attempted after G2 rejects, preserving residual policies.
        stages["G3"], reference = _guard_result(base)
    adapter = adapt_output(raw, wire_format="typed_facts_v1", task_id=task["task_id"], task_sha256=fingerprint(task))
    schema_status = "pass" if adapter["status"] == "scorable" else "rejected"
    score = None
    if reference is not None:
        exact, score = report_exactness(reference, raw, cell_id=scenario.cell_id)
        stages["G4"] = dict(status="pass" if exact else "rejected", reason=None if exact else "not_complete_exact_report",
                            error_class=None, schema_status=schema_status)
    else:
        stages["G4"] = dict(status="unexecuted", reason="no_source_verified_reference", error_class=None,
                            schema_status=schema_status)
    decisions = [project_decision(stages, name, decision_id=f"D-S-{key}-{name}") for name in POLICIES]
    deadline_check(deadline)
    return dict(stages=stages, decisions=decisions, score=score, adapter_status=adapter["status"],
        raw_terminal="malformed" if adapter["status"] == "malformed" else "returned",
        measurement_completion=score["completion"] if score is not None else None,
        primary_coverage=score["primary"]["coverage"] if score is not None else None,
        reference_fingerprint=reference.fingerprint if reference is not None else None,
        reference_counts=reference_counts(reference) if reference is not None else None,
        fact_accounting=fact_accounting(reference, raw) if reference is not None else None,
        scientific_validation="not_established")
