"""Independently declared fictional BG02 cases and oracle (stdlib only).

This module never imports either validator. Expected decisions are authored from
the versioned policy, never copied from execution results. Native sealed-output
preparation is a separate root-owned callback; every produced bundle must be
frozen before paired scoring.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

POLICY_IDS = (
    "EP-WIRE-01", "EP-CASE-01", "EP-PROGRAM-01", "EP-TIME-01", "EP-DAG-01", "EP-DAG-02",
    "EP-SOURCE-01", "EP-PACKET-01", "EP-OBS-01", "EP-SCOPE-01", "EP-FEATURE-01",
    "EP-SCORER-01", "EP-SCORER-02", "EP-POLICY-01", "EP-POLICY-02", "EP-POLICY-03",
    "EP-POLICY-04", "EP-EXEC-01", "EP-EXEC-02", "EP-EXEC-03", "EP-EXEC-04",
    "EP-VERIFY-01", "EP-VERIFY-02", "EP-VERIFY-03", "EP-IO-01", "EP-FAIL-01", "EP-PROCESS-01",
)
HYPOTHESIS_FIELDS = ("target_id", "indication_id", "target_namespace_version",
                     "indication_namespace_version", "intended_action", "modality", "tissue")
ORIGIN = "2024-06-30"
ORIGIN_AT = "2024-06-30T23:59:59.999999+00:00"
BUDGET = dict(max_calls=16, max_input_tokens=32000, max_output_tokens=8000,
              max_cost_usd=0, max_seconds=300, max_retries=0)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_bytes(value):
    return value if isinstance(value, bytes) else canonical(value) + b"\n"


def availability(day="2021-01-01"):
    return dict(first_public_at=day, release_public_at=day, record_public_at=day,
                annotation_public_at=day, retrieved_at="2026-11-02",
                basis="fictional_release_documentation", uncertainty="Fictional; no real availability claim",
                known_public_by=None, evidence_ref=None)


def source_documents(base="core_t1"):
    """Return fresh original-schema documents, before ordinary hash sealing."""
    case = dict(schema_version=2, case_id="FICTIONAL:CASE-1", task="T1", origin=ORIGIN,
        origin_at=ORIGIN_AT,
        hypothesis=dict(target_id="FICTIONAL:TARGET-1", indication_id="FICTIONAL:DISEASE-1",
            target_namespace_version="fictional-target-v1", indication_namespace_version="fictional-disease-v1",
            intended_action="inhibit", modality="small_molecule", tissue="fictional tissue",
            availability=availability()),
        program=dict(program_id="FICTIONAL:PROGRAM-1", molecule_id="FICTIONAL:MOLECULE-1",
            sponsor="Fictional sponsor", phase_at_origin=2, status_at_origin="active",
            eligible_since="2023-01-01", mapping_confidence=1.0, trial_ids=["FICTIONAL:TRIAL-1"],
            availability=availability()),
        endpoint=dict(name="phase_2_to_3", horizon_months=24))
    scope = fingerprint({key: case["hypothesis"][key] for key in HYPOTHESIS_FIELDS})
    observation = dict(observation_id="obs-1", target_id="FICTIONAL:TARGET-1",
        indication_id="FICTIONAL:DISEASE-1", program_id=None, category="genetics", source_kind="primary",
        statement="Fictional study reports a normalized support value of 0.75; this is a software fixture.",
        status="observed", polarity="supports", mechanism_direction="inhibit", study_id="FICTIONAL:STUDY-1",
        dependency_group="fictional-group-1",
        context=dict(species=None, ancestry=None, tissue=None, disease_state=None, intervention=None,
                     comparator=None, cohort_ids=["FICTIONAL:COHORT-1"]),
        quantitative=dict(effect=None, scale=None, standard_error=None, ci_lower=None, ci_upper=None,
                          sample_size=None, adjusted_p_value=None),
        method=dict(code_id="fictional-normalized-support", version="1", parameters={"fictional": True},
                    qc_status="passed", limitations=["Synthetic conformance control; no scientific result"]),
        availability=availability(), features={"genetic_support": 0.75}, feature_scope=scope,
        input_refs=["mapping-1"], computed_at=None, source_locator={"row": 0}, source_metrics={},
        missingness={"species": "Not reported by fictional source"}, publication_date="2021-01-01", publication_year=2021)
    raw = dict(source_id="source-1", dataset_id="fixture_source", release_id="fictional-v1", path="source.json",
        sha256="0" * 64, role="agent_evidence", availability=availability(), temporal_classification="verified_historical",
        source_url="https://example.invalid/source-1", parents=[], computed_at=None, method_id=None, method_version=None,
        receipt_path="receipt.json", receipt_sha256="0" * 64)
    mapping = dict(source_id="mapping-1", dataset_id="fixture_reference", release_id="fictional-v1", path="mapping.json",
        sha256="0" * 64, role="reference", availability=availability("2026-01-01"), temporal_classification="verified_historical",
        source_url="https://example.invalid/mapping-1", parents=["source-1"], computed_at="2026-01-01T00:00:00+00:00",
        method_id="fictional-mapping", method_version="1", receipt_path=None, receipt_sha256=None)
    artifact = dict(artifact_id="packet-1", dataset_id="fixture_evidence", release_id="fictional-v1", path="evidence.json",
        sha256="0" * 64, role="agent_evidence", access_approved=True, temporal_classification="verified_historical",
        availability=availability(), source_url="https://example.invalid/packet-1", input_refs=["mapping-1"])
    snapshot = dict(schema_version=2, snapshot_id="fictional-snapshot-v1", profile="synthetic_demo", origin=ORIGIN,
        origin_at=ORIGIN_AT, allow_reconstructed=False, artifacts=[artifact], sources=[raw, mapping], raw_root=None,
        coverage={"source_completeness": "selected_subset", "scientific_validation": "not_established"})
    catalog = dict(schema_version=1, providers=[dict(provider_id="fictional")], datasets=[
        dict(dataset_id=name, provider_id="fictional", roles=roles, dependencies=[],
             collection_status="planned", parse_status="not_run", validation_status="not_run")
        for name, roles in (("fixture_source", ["agent_evidence"]), ("fixture_reference", ["reference"]),
                            ("fixture_evidence", ["agent_evidence"]), ("fixture_answers", ["evaluation_only"]))])
    receipt = dict(receipt_id="fictional-receipt-1", dataset_id="fixture_source", release_id="fictional-v1",
        relative_path="source.json", sha256="0" * 64, bytes=0, url="https://example.invalid/source-1",
        status="completed", completed_at_utc="2021-01-01T00:00:00+00:00")
    scorer = dict(schema_version=2, model_id="fictional-logistic-v1", kind="synthetic_demo",
        feature_schema="tether-features-v2", aggregation="mean_of_unique_dependency_groups_v2", endpoint="phase_2_to_3",
        horizon_months=24, phases=[2], modalities=["small_molecule"], intended_actions=["inhibit"],
        target_namespace_versions=["fictional-target-v1"], indication_namespace_versions=["fictional-disease-v1"],
        training_origin_max="2022-01-01", training_label_available_max="2023-01-01",
        calibration_label_available_max=None, training_manifest_sha256="a" * 64, calibration="none", intercept=0.25,
        coefficients={"genetic_support": 0.8}, required_features=["genetic_support"], missing_values={}, minimum_coverage=1.0)
    result = dict(case=case, snapshot=snapshot, evidence=dict(schema_version=2, observations=[observation]),
        source=dict(fictional=True, study="FICTIONAL:STUDY-1", support=0.75),
        mapping=dict(fictional=True, target="FICTIONAL:TARGET-1", annotation_version="fictional-v1"),
        receipt=receipt, catalog=catalog, scorer=scorer)
    if base in ("core_t6", "real_t6", "policy_t6"):
        case.update(task="T6", endpoint=None)
        result.pop("scorer")
    if base in ("real_t6", "policy_t6"):
        snapshot["profile"] = "contemporary_assessment"
    if base not in ("core_t1", "core_t6", "real_t6", "policy_t6"):
        raise ValueError("Unknown base fixture: " + base)
    return result


def local_model_config():
    """Declared fictional configuration; materialization injects an in-memory opener.

    Hash strings are fictional identity controls, not claims of actual weights.
    Neither this module nor its tests ever connect to the endpoint.
    """
    return dict(schema_version=1, endpoint="http://127.0.0.1:59999", model_id="fictional-no-model-executed",
        model_provenance=dict(weights_sha256={"fictional.gguf": "b" * 64}, runtime_sha256="c" * 64),
        retrieval=dict(max_records=12, max_request_bytes=12000, wire_format="canonical"),
        max_output_tokens=64, timeout_seconds=10, seed=11, selection_cap=3)


def change(document, path, value, *, op="set"):
    return dict(op=op, document=document, path=list(path), value=copy.deepcopy(value))


def apply_changes(documents, changes):
    for item in changes:
        target = documents[item["document"]]
        path = item["path"]
        for key in path[:-1]:
            target = target[key]
        if item["op"] == "set":
            target[path[-1]] = copy.deepcopy(item["value"])
        elif item["op"] == "delete":
            del target[path[-1]]
        elif item["op"] == "append":
            target[path[-1]].append(copy.deepcopy(item["value"]))
        else:
            raise ValueError("Unknown declared mutation: " + item["op"])


def seal_sources(documents):
    """Seal ordinary supplied bytes only; never repair intentional final faults."""
    snapshot, receipt = documents["snapshot"], documents["receipt"]
    source_bytes = file_bytes(documents["source"])
    receipt.update(sha256=hashlib.sha256(source_bytes).hexdigest(), bytes=len(source_bytes))
    receipt_hash = hashlib.sha256(file_bytes(receipt)).hexdigest()
    for node in snapshot["sources"]:
        if node["source_id"] == "source-1":
            node.update(sha256=receipt["sha256"], receipt_sha256=receipt_hash)
        elif node["source_id"] == "mapping-1":
            node["sha256"] = hashlib.sha256(file_bytes(documents["mapping"])).hexdigest()
    for artifact in snapshot["artifacts"]:
        if artifact["artifact_id"] == "packet-1":
            artifact["sha256"] = hashlib.sha256(file_bytes(documents["evidence"])).hexdigest()
    return documents


def _spec(control_id, title, obligations, *, base="core_t1", decision="accept", observed=None,
          changes=(), after_seal=(), operation="prepare_run", variant="core_v2_catalog1",
          recipe=None, exposed=False, rationale=""):
    return dict(schema_version=1, control_id=control_id, title=title, operation=operation, variant=variant,
        construction_stratum="exposed_regression" if exposed else "new_synthetic_construction",
        preparation=dict(base=base, changes=copy.deepcopy(list(changes)), after_seal=copy.deepcopy(list(after_seal)),
                         recipe=copy.deepcopy(recipe or {})),
        oracle=dict(decision=decision, obligation_ids=list(obligations), observables=copy.deepcopy(observed or {}),
                    rationale=rationale or title))


def case_specs():
    """Every scheduled case, including hard/unimplemented recipes; never filter."""
    S = _spec
    C = change
    scored = dict(prediction_status="scored", probability_is_null=False, selected_observation_ids=["obs-1"], feature_values={"genetic_support": 0.75})
    abstained = dict(prediction_status="abstained", probability_is_null=True)
    audit = dict(prediction_status="audit_only", probability_is_null=True)
    p = ["observations", 0]
    r = ["sources", 0]
    m = ["sources", 1]
    cases = [
        S("EP001", "Eligible T1 produces its declared synthetic score", ["EP-CASE-01", "EP-SCORER-02"], observed=scored),
        S("EP002", "T6 produces audit-only output with no probability", ["EP-CASE-01", "EP-SCORER-02"], base="core_t6", observed=audit),
        S("EP003", "T1 without a frozen scorer validly abstains", ["EP-SCORER-02"], observed=abstained, recipe={"omit_scorer": True}),
        S("EP004", "T6 supplied future program fails before dispatch", ["EP-PROGRAM-01"], base="core_t6", decision="reject", exposed=True,
          changes=[C("case", ["program", "availability", "record_public_at"], "2025-01-01")], observed={"dispatches": 0}),
        S("EP005", "T1 inactive program is invalid", ["EP-PROGRAM-01"], decision="reject", changes=[C("case", ["program", "status_at_origin"], "inactive")]),
        S("EP006", "T6 inactive program is permissible context", ["EP-PROGRAM-01"], base="core_t6", observed=audit,
          changes=[C("case", ["program", "status_at_origin"], "inactive")]),
        S("EP007", "T1 endpoint must match origin phase", ["EP-PROGRAM-01"], decision="reject", changes=[C("case", ["endpoint", "name"], "phase_1_to_2")]),
        S("EP008", "T1 requires a program", ["EP-PROGRAM-01"], decision="reject", changes=[C("case", ["program"], None)]),
        S("EP009", "Program eligibility after origin is invalid", ["EP-PROGRAM-01"], decision="reject", changes=[C("case", ["program", "eligible_since"], "2024-07-01")]),
        S("EP010", "Naive origin timestamp is invalid", ["EP-WIRE-01", "EP-CASE-01"], decision="reject", changes=[C("case", ["origin_at"], "2024-06-30T23:59:59")]),
        S("EP011", "Legacy v1 cannot execute as a new case", ["EP-WIRE-01"], decision="reject", changes=[C("case", ["schema_version"], 1)]),
        S("EP012", "Duplicate JSON key is invalid", ["EP-WIRE-01"], decision="reject", recipe={"file_fault": "duplicate_case_schema_key"}),
        S("EP013", "Boolean program phase is not an integer", ["EP-WIRE-01", "EP-PROGRAM-01"], decision="reject", changes=[C("case", ["program", "phase_at_origin"], True)]),
        S("EP014", "Unknown case contract field rejects", ["EP-WIRE-01"], decision="reject", changes=[C("case", ["invented_field"], 1)]),
        S("EP015", "Packet v1 is not an eligible v2 packet", ["EP-PACKET-01"], decision="reject", changes=[C("evidence", ["schema_version"], 1)]),
        S("EP016", "Duplicate observation identities reject", ["EP-PACKET-01"], decision="reject", recipe={"observations": "duplicate_id"}),
        S("EP017", "Changed original raw bytes reject", ["EP-SOURCE-01"], decision="reject", recipe={"file_fault": "raw_bytes_after_seal"}),
        S("EP018", "Missing eligible original rejects", ["EP-SOURCE-01", "EP-IO-01"], decision="reject", recipe={"file_fault": "missing_raw"}),
        S("EP019", "Reference-only artifact cannot be agent packet", ["EP-PACKET-01"], decision="reject", changes=[C("snapshot", ["artifacts", 0, "role"], "reference")]),
        S("EP020", "Evaluator-only ancestor denies the entire graph", ["EP-DAG-01"], decision="reject", exposed=True,
          changes=[C("snapshot", r + ["role"], "evaluation_only")]),
        S("EP021", "A missing input parent rejects", ["EP-DAG-01"], decision="reject", changes=[C("snapshot", m + ["parents"], ["absent-source"])]),
        S("EP022", "A lineage self-cycle rejects", ["EP-DAG-01"], decision="reject", changes=[C("snapshot", m + ["parents"], ["mapping-1"])]),
        S("EP023", "Observation lineage cannot escape its packet", ["EP-DAG-01", "EP-OBS-01"], decision="reject", recipe={"observation_lineage": "unrelated_source"}),
        S("EP024", "A derived node requires a computation timestamp", ["EP-DAG-01"], decision="reject", changes=[C("snapshot", m + ["computed_at"], None)]),
        S("EP025", "A new computation over eligible old inputs is allowed", ["EP-DAG-02"], observed=scored, exposed=True),
        S("EP026", "Future raw annotation excludes dependent evidence", ["EP-TIME-01", "EP-DAG-02"], observed={**abstained, "exclusion_reasons": ["available_after_origin"], "dispatches": 0},
          changes=[C("snapshot", r + ["availability", "annotation_public_at"], "2025-01-01")]),
        S("EP027", "Future observation availability excludes that record", ["EP-TIME-01"], observed={**abstained, "exclusion_reasons": ["available_after_origin"]},
          changes=[C("evidence", p + ["availability", "record_public_at"], "2025-01-01")]),
        S("EP028", "Future exact publication excludes an otherwise eligible record", ["EP-OBS-01"], observed={**abstained, "exclusion_reasons": ["publication_after_origin"]},
          changes=[C("evidence", p + ["publication_date"], "2024-07-01"), C("evidence", p + ["publication_year"], 2024)]),
        S("EP029", "Future publication year excludes without imputation", ["EP-OBS-01"], observed={**abstained, "exclusion_reasons": ["publication_after_origin"]},
          changes=[C("evidence", p + ["publication_date"], None), C("evidence", p + ["publication_year"], 2025)]),
        S("EP030", "Same-origin publication year can use eligible complete lineage", ["EP-OBS-01"], observed=scored,
          changes=[C("evidence", p + ["publication_date"], None), C("evidence", p + ["publication_year"], 2024)]),
        S("EP031", "Conflicting publication date/year excludes", ["EP-OBS-01"], observed={**abstained, "exclusion_reasons": ["publication_metadata_inconsistent"]},
          changes=[C("evidence", p + ["publication_year"], 2020)]),
        S("EP032", "Unapproved reconstructed history is excluded", ["EP-DAG-02"], base="real_t6", observed={**audit, "exclusion_reasons": ["reconstructed_history_not_approved"]},
          changes=[C("snapshot", ["profile"], "historical_benchmark"), C("snapshot", r + ["temporal_classification"], "reconstructed")]),
        S("EP033", "Explicitly approved reconstructed history remains eligible", ["EP-DAG-02"], base="real_t6", observed={**audit, "selected_observation_ids": ["obs-1"]},
          changes=[C("snapshot", ["profile"], "historical_benchmark"), C("snapshot", ["allow_reconstructed"], True), C("snapshot", r + ["temporal_classification"], "reconstructed")]),
        S("EP034", "Unverified temporal classification excludes", ["EP-DAG-02"], observed={**abstained, "exclusion_reasons": ["temporal_classification_unverified"]},
          changes=[C("snapshot", r + ["temporal_classification"], "unverified")]),
        S("EP035", "Opposite action retains context but not numerical features", ["EP-SCOPE-01"], observed={**abstained, "selected_observation_ids": ["obs-1"], "feature_values": {"genetic_support": None}},
          changes=[C("case", ["hypothesis", "intended_action"], "activate")], exposed=True),
        S("EP036", "Different modality does not transfer scoped features", ["EP-SCOPE-01"], observed={**abstained, "selected_observation_ids": ["obs-1"], "feature_values": {"genetic_support": None}},
          changes=[C("case", ["hypothesis", "modality"], "antibody")]),
        S("EP037", "Different tissue does not transfer scoped features", ["EP-SCOPE-01"], observed={**abstained, "selected_observation_ids": ["obs-1"], "feature_values": {"genetic_support": None}},
          changes=[C("case", ["hypothesis", "tissue"], "other fictional tissue")]),
        S("EP038", "Different target cannot be selected", ["EP-SCOPE-01"], observed={**abstained, "selected_observation_ids": [], "dispatches": 0},
          changes=[C("case", ["hypothesis", "target_id"], "FICTIONAL:OTHER-TARGET")]),
        S("EP039", "Another program's observation stays outside retrieval", ["EP-SCOPE-01"], observed={**abstained, "selected_observation_ids": [], "dispatches": 0},
          changes=[C("evidence", p + ["program_id"], "FICTIONAL:OTHER-PROGRAM")]),
        S("EP040", "Missing numerical derivation scope rejects", ["EP-OBS-01", "EP-SCOPE-01"], decision="reject", changes=[C("evidence", p + ["feature_scope"], None)]),
        S("EP041", "Clinical evidence cannot create numerical features", ["EP-OBS-01"], decision="reject", changes=[C("evidence", p + ["source_kind"], "clinical")]),
        S("EP042", "Failed QC cannot create numerical features", ["EP-OBS-01"], decision="reject", changes=[C("evidence", p + ["method", "qc_status"], "failed")]),
        S("EP043", "Out-of-range normalized support rejects", ["EP-OBS-01"], decision="reject", changes=[C("evidence", p + ["features", "genetic_support"], 1.01)]),
        S("EP044", "Independent dependence groups aggregate by mean", ["EP-FEATURE-01"], observed={**scored, "selected_observation_ids": ["obs-1", "obs-2"], "feature_values": {"genetic_support": 0.5}}, recipe={"observations": "independent_second"}),
        S("EP045", "Conflicting dependent records cause explicit missingness", ["EP-FEATURE-01", "EP-SCORER-02"], observed={**abstained, "feature_values": {"genetic_support": None}, "feature_status": {"genetic_support": "conflicting"}}, recipe={"observations": "same_group_conflict"}),
        S("EP046", "Shared cohort does not add an independent group", ["EP-FEATURE-01"], observed={**scored, "selected_observation_ids": ["obs-1", "obs-2"], "dependency_groups": {"genetic_support": 1}}, recipe={"observations": "shared_cohort"}),
        S("EP047", "Invalid scorer schema rejects before dispatch", ["EP-SCORER-01"], decision="reject", exposed=True, observed={"dispatches": 0}, changes=[C("scorer", ["schema_version"], 1)]),
        S("EP048", "Training labels exactly at origin are forbidden", ["EP-SCORER-01"], decision="reject", exposed=True, observed={"dispatches": 0}, changes=[C("scorer", ["training_label_available_max"], ORIGIN)]),
        S("EP049", "Future calibration labels are forbidden", ["EP-SCORER-01"], decision="reject", observed={"dispatches": 0}, changes=[C("scorer", ["calibration"], "held_out_logistic"), C("scorer", ["calibration_label_available_max"], "2025-01-01")]),
        S("EP050", "Synthetic scorer cannot score contemporary inputs", ["EP-SCORER-01"], decision="reject", changes=[C("snapshot", ["profile"], "contemporary_assessment")]),
        S("EP051", "A valid inapplicable scorer abstains", ["EP-SCORER-02"], observed={**abstained, "prediction_reason": "outside_scorer_applicability"}, changes=[C("scorer", ["horizon_months"], 12)]),
        S("EP052", "No unconfigured imputation is invented", ["EP-SCORER-02"], observed={**abstained, "prediction_reason": "missing_feature_without_frozen_imputation"},
          changes=[C("scorer", ["coefficients", "expression_relevance"], 0.3), C("scorer", ["minimum_coverage"], 0.5)]),
        S("EP053", "Insufficient feature coverage validly abstains", ["EP-SCORER-02"], observed={**abstained, "prediction_reason": "insufficient_feature_coverage"}, changes=[C("scorer", ["coefficients", "expression_relevance"], 0.3)]),
        S("EP054", "Valid zero-call budget makes no dispatch", ["EP-EXEC-01"], observed={**abstained, "dispatches": 0, "selected_observation_ids": []}, recipe={"budget": {"max_calls": 0}}),
        S("EP055", "Negative call budget rejects", ["EP-EXEC-01"], decision="reject", recipe={"budget": {"max_calls": -1}}),
        S("EP056", "Safe relative input path cannot escape the root", ["EP-IO-01", "EP-DAG-01"], decision="reject", changes=[C("snapshot", r + ["path"], "../never-open.json")]),
        S("EP057", "A directory cannot substitute for raw input bytes", ["EP-IO-01"], decision="reject", recipe={"file_fault": "raw_is_directory"}),
        S("EP058", "Same-day information is eligible at the exact day-end cutoff", ["EP-TIME-01"], observed=scored,
          changes=[C("snapshot", r + ["availability"], availability(ORIGIN)), C("evidence", p + ["availability"], availability(ORIGIN))]),
    ]
    # Native sealed preparation recipes are explicit and never dropped merely
    # because a materializer or independent verifier has not implemented one.
    native = [
        ("EP059", "Valid source-inclusive sealed run", ["EP-VERIFY-01", "EP-VERIFY-02"], "valid_scored", "none", "accept", False),
        ("EP060", "Omitted eligible raw-parent proof rejects", ["EP-SOURCE-01", "EP-VERIFY-02"], "valid_scored", "omit_raw_parent_proof_reseal", "reject", True),
        ("EP061", "Journal claim and ledger disagreement rejects", ["EP-EXEC-03", "EP-VERIFY-02"], "valid_scored", "journal_claim_differs_reseal", "reject", True),
        ("EP062", "Contradictory declared call count rejects", ["EP-EXEC-04", "EP-VERIFY-02"], "valid_scored", "run_call_count_reseal", "reject", True),
        ("EP063", "Feature values must rebuild from admitted claims", ["EP-FEATURE-01", "EP-VERIFY-02"], "valid_scored", "feature_value_reseal", "reject", False),
        ("EP064", "Scorer contributions must match coefficients and values", ["EP-SCORER-02", "EP-VERIFY-02"], "valid_scored", "prediction_contribution_reseal", "reject", False),
        ("EP065", "Final trace fingerprint must agree", ["EP-EXEC-04", "EP-VERIFY-02"], "valid_scored", "trace_fingerprint_reseal", "reject", False),
        ("EP066", "Source alteration cannot pass byte integrity", ["EP-SOURCE-01", "EP-VERIFY-01"], "valid_scored", "original_raw_bytes", "reject", False),
        ("EP067", "Auxiliary request output is receipt-bound", ["EP-VERIFY-01"], "valid_scored", "auxiliary_request_bytes", "reject", False),
        ("EP068", "Admission fingerprint binds source claim", ["EP-EXEC-03", "EP-VERIFY-02"], "valid_scored", "claim_fingerprint_reseal", "reject", False),
        ("EP069", "External receipt anchor cannot be replaced", ["EP-VERIFY-01"], "valid_scored", "wrong_external_anchor", "reject", False),
        ("EP070", "Unknown selection never becomes a factual claim", ["EP-EXEC-02", "EP-EXEC-03"], "unknown_selection", "none", "accept", False),
        ("EP071", "Duplicated selection fails review with no duplicate claim", ["EP-EXEC-03"], "duplicate_selection", "none", "accept", False),
        ("EP072", "Known overquote usage is retained as measured on failure", ["EP-EXEC-04"], "known_overquote", "none", "accept", True),
        ("EP073", "Unusable usage remains estimated rather than invented", ["EP-EXEC-04", "EP-FAIL-01"], "malformed_usage", "none", "accept", True),
        ("EP074", "A timeout retains an honest verifiable failed run", ["EP-EXEC-04", "EP-FAIL-01"], "unknown_timeout", "none", "accept", False),
        ("EP075", "Recorded selection binds the request fingerprint", ["EP-EXEC-02"], "valid_recorded", "replay_request_fingerprint_reseal", "reject", False),
        ("EP076", "Interrupted unresolved dispatch is inspect-only", ["EP-FAIL-01", "EP-EXEC-04"], "unresolved_dispatch", "none", "inspect_only", False),
        ("EP077", "Corrupt recovery journal chain rejects", ["EP-FAIL-01", "EP-EXEC-04"], "unresolved_dispatch", "journal_chain", "reject", False),
    ]
    for ident, title, obligations, producer, mutation, decision, exposed in native:
        observed = {}
        if producer in {"unknown_selection", "duplicate_selection", "known_overquote", "malformed_usage", "unknown_timeout"}:
            observed.update(selected_observation_ids=[], probability_is_null=True)
        if producer == "known_overquote":
            observed.update(accounting_basis="adapter_reported", later_dispatches=0)
        if producer in {"malformed_usage", "unknown_timeout"}:
            observed["accounting_basis"] = "quoted_upper_bound_not_measured"
        if producer == "unresolved_dispatch":
            observed.update(recovery_may_dispatch=False, unresolved_attempts=["genetics:1"])
        cases.append(S(ident, title, obligations, operation="inspect_run" if producer == "unresolved_dispatch" else "verify_run",
            decision=decision, observed=observed, recipe=dict(sealed_producer=producer, sealed_mutation=mutation), exposed=exposed))
    policy = [
        ("EP078", "Complete schema2 policy accepts", ["EP-POLICY-01", "EP-POLICY-02", "EP-POLICY-03"], "none", "accept", False),
        ("EP079", "Used receipt completion cannot postdate its bound", ["EP-POLICY-03"], "used_receipt_late", "reject", False),
        ("EP080", "Unused receipt completion cannot postdate its bound", ["EP-POLICY-03"], "unused_receipt_late", "reject", True),
        ("EP081", "Unused receipt URL must bind", ["EP-POLICY-03"], "unused_receipt_url", "reject", False),
        ("EP082", "Unused receipt evidence reference must bind", ["EP-POLICY-03"], "unused_receipt_ref", "reject", False),
        ("EP083", "Equivalent UTC receipt notation is valid", ["EP-POLICY-03"], "receipt_utc_alias", "accept", False),
        ("EP084", "Valid alternative availability basis tolerates later download", ["EP-POLICY-03"], "alternative_basis_later_download", "accept", False),
        ("EP085", "Missing source grant rejects", ["EP-POLICY-02"], "missing_grant", "reject", False),
        ("EP086", "Supplied unused source cannot escape complete inventory", ["EP-POLICY-02"], "ungranted_source", "reject", False),
        ("EP087", "Wrong policy frame anchor rejects", ["EP-POLICY-02"], "wrong_frame", "reject", False),
        ("EP088", "Evaluator product cannot gain an agent-use grant", ["EP-POLICY-01", "EP-POLICY-02"], "evaluator_product", "reject", False),
        ("EP089", "Schema2 policy route rejects an unsupported scorer", ["EP-POLICY-02"], "unsupported_scorer", "reject", False),
        ("EP090", "Altered copied controls cannot verify", ["EP-POLICY-04", "EP-VERIFY-03"], "copied_control_reseal", "reject", False),
        ("EP091", "Altered policy projection cannot verify", ["EP-POLICY-04", "EP-VERIFY-03"], "projection_reseal", "reject", False),
        ("EP092", "Outer dossier must match the sealed engine result", ["EP-VERIFY-03"], "dossier_reseal", "reject", False),
        ("EP093", "Complete unaltered outer policy run verifies", ["EP-POLICY-04", "EP-VERIFY-03"], "valid_outer", "accept", False),
    ]
    for ident, title, obligations, mutation, decision, exposed in policy:
        verify = mutation in {"copied_control_reseal", "projection_reseal", "dossier_reseal", "valid_outer"}
        cases.append(S(ident, title, obligations, base="policy_t6", variant="artifact_policy_v2",
            operation="verify_run" if verify else "prepare_run", decision=decision, exposed=exposed,
            observed=audit if decision == "accept" else {}, recipe={"policy_recipe": mutation}))
    cases.extend([
        S("EP094", "Local structured archive verifies without a live model", ["EP-EXEC-02", "EP-EXEC-04"],
          operation="verify_run", observed=scored, recipe={"local_config": True, "sealed_producer": "local_valid", "sealed_mutation": "none"}),
        S("EP095", "Shared-scientific-field transport preserves local request semantics", ["EP-WIRE-01", "EP-EXEC-02"],
          operation="verify_run", observed=scored, changes=[C("local_model", ["retrieval", "wire_format"], "tether-shared-scientific-fields-v1")],
          recipe={"local_config": True, "sealed_producer": "local_valid", "sealed_mutation": "none"}),
        S("EP096", "Malformed local response retains an honest failed archive", ["EP-EXEC-02", "EP-EXEC-04", "EP-FAIL-01"],
          operation="verify_run", observed={"selected_observation_ids": [], "probability_is_null": True, "accounting_basis": "quoted_upper_bound_not_measured"},
          recipe={"local_config": True, "sealed_producer": "local_malformed_response", "sealed_mutation": "none"}),
        S("EP097", "Local native overquote preserves validated measured usage", ["EP-EXEC-04"], operation="verify_run", exposed=True,
          observed={"selected_observation_ids": [], "probability_is_null": True, "accounting_basis": "adapter_reported", "later_dispatches": 0},
          recipe={"local_config": True, "sealed_producer": "local_known_overquote", "sealed_mutation": "none"}),
        S("EP098", "Invalid local model provenance rejects at preparation", ["EP-EXEC-02"], decision="reject",
          changes=[C("local_model", ["model_provenance", "runtime_sha256"], "not-a-sha256")], recipe={"local_config": True}),
        S("EP099", "Invalid bounded retrieval count rejects at preparation", ["EP-EXEC-02"], decision="reject",
          changes=[C("local_model", ["retrieval", "max_records"], 0)], recipe={"local_config": True}),
        S("EP100", "Unsupported selection cap rejects at preparation", ["EP-EXEC-02"], decision="reject",
          changes=[C("local_model", ["selection_cap"], 4)], recipe={"local_config": True}),
        S("EP101", "Non-loopback model endpoint rejects without network access", ["EP-EXEC-02"], decision="reject",
          changes=[C("local_model", ["endpoint"], "https://example.invalid/never-contact")], recipe={"local_config": True}),
        S("EP102", "Bounded local retrieval retains selected-subset semantics", ["EP-EXEC-02"], operation="verify_run", observed=scored,
          changes=[C("local_model", ["retrieval", "max_records"], 1)],
          recipe={"local_config": True, "observations": "independent_second", "sealed_producer": "local_valid", "sealed_mutation": "none"}),
        S("EP103", "Changed local request hash cannot verify", ["EP-EXEC-02", "EP-VERIFY-02"], operation="verify_run", decision="reject",
          recipe={"local_config": True, "sealed_producer": "local_valid", "sealed_mutation": "local_request_fingerprint_reseal"}),
        S("EP104", "Local response usage must match measured journal accounting", ["EP-EXEC-04", "EP-VERIFY-02"], operation="verify_run", decision="reject",
          recipe={"local_config": True, "sealed_producer": "local_valid", "sealed_mutation": "local_response_usage_reseal"}),
        S("EP105", "Complete schema1 outer facade verifies", ["EP-VERIFY-03", "EP-PROCESS-01"], operation="verify_run", observed=scored,
          recipe={"sealed_producer": "valid_outer_schema1", "sealed_mutation": "none"}),
        S("EP106", "Contradictory outer process supervision rejects", ["EP-PROCESS-01", "EP-VERIFY-03"], operation="verify_run", decision="reject",
          recipe={"sealed_producer": "valid_outer_schema1", "sealed_mutation": "process_supervision_reseal"}),
        S("EP107", "Outer code proof cannot disagree with the trusted runtime", ["EP-VERIFY-03"], operation="verify_run", decision="reject",
          recipe={"sealed_producer": "valid_outer_schema1", "sealed_mutation": "outer_code_proof_reseal"}),
        S("EP108", "Invalid process supervision bounds reject preparation", ["EP-PROCESS-01"], decision="reject",
          recipe={"process_limits": {"timeout_seconds": -1, "max_output_bytes": 1048576}}),
    ])
    # prepare_run means pre-dispatch input validation, not execution. Cases that
    # assert prediction/aggregation/budget-consumption behavior need a native
    # sealed run produced from these exact prepared inputs and options.
    needs_execution = {"EP003", "EP035", "EP036", "EP037", "EP044", "EP045", "EP046",
                       "EP051", "EP052", "EP053", "EP054"}
    excluded = {"EP026", "EP027", "EP028", "EP029", "EP031", "EP032", "EP034"}
    outside_retrieval = {"EP038", "EP039"}
    for item in cases:
        identifier = item["control_id"]
        if identifier in needs_execution:
            item["operation"] = "verify_run"
            item["preparation"]["recipe"].update(sealed_producer="valid_scored", sealed_mutation="none")
        if item["operation"] != "prepare_run":
            continue
        old = item["oracle"]["observables"]
        if item["oracle"]["decision"] == "reject":
            item["oracle"]["observables"] = {}
            continue
        is_t6 = item["preparation"]["base"] in {"core_t6", "real_t6", "policy_t6"}
        observable = dict(admitted_observation_ids=[] if identifier in excluded else ["obs-1"],
            eligible_observation_ids=[] if identifier in excluded | outside_retrieval else ["obs-1"],
            scorer_preflight="dossier_audit_has_no_clinical_probability" if is_t6 else None)
        if "exclusion_reasons" in old:
            observable["exclusion_reasons"] = old["exclusion_reasons"]
        item["oracle"]["observables"] = observable
    cases[0]["title"] = cases[0]["oracle"]["rationale"] = "Eligible T1 inputs and configured synthetic scorer pass preflight"
    cases[1]["title"] = cases[1]["oracle"]["rationale"] = "Eligible T6 inputs declare audit-only scorer preflight"
    return cases


def _special_observations(documents, recipe):
    variant = recipe.get("observations")
    if variant:
        second = copy.deepcopy(documents["evidence"]["observations"][0])
        if variant != "duplicate_id":
            second["observation_id"] = "obs-2"
        if variant in {"independent_second", "shared_cohort"}:
            second.update(study_id="FICTIONAL:STUDY-2", dependency_group="fictional-group-2")
        if variant == "independent_second":
            second["context"]["cohort_ids"] = ["FICTIONAL:COHORT-2"]
        if variant in {"independent_second", "same_group_conflict"}:
            second["features"]["genetic_support"] = 0.25
        documents["evidence"]["observations"].append(second)
    if recipe.get("observation_lineage") == "unrelated_source":
        extra = copy.deepcopy(documents["snapshot"]["sources"][0])
        extra["source_id"] = "unrelated-source"
        documents["snapshot"]["sources"].append(extra)
        documents["evidence"]["observations"][0]["input_refs"] = ["unrelated-source"]


def prepare_documents(spec):
    documents = source_documents(spec["preparation"]["base"])
    recipe = spec["preparation"]["recipe"]
    if recipe.get("local_config"):
        documents["local_model"] = local_model_config()
    _special_observations(documents, recipe)
    apply_changes(documents, spec["preparation"]["changes"])
    if recipe.get("omit_scorer"):
        documents.pop("scorer", None)
    seal_sources(documents)
    apply_changes(documents, spec["preparation"]["after_seal"])
    return documents


def write_source_bundle(root, spec, *, trusted_runtime=None):
    """Write original source files; advanced recipes remain explicit callbacks.

    This returns a validator-visible descriptor and a separate pending recipe.
    A nonempty pending recipe is NOT a completed/scorable case.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    directory = root / "input"
    directory.mkdir()
    documents = prepare_documents(spec)
    for name, value in documents.items():
        (directory / (name + ".json")).write_bytes(file_bytes(value))
    recipe = spec["preparation"]["recipe"]
    fault = recipe.get("file_fault")
    raw_path = directory / "source.json"
    if fault == "duplicate_case_schema_key":
        path = directory / "case.json"
        path.write_bytes(b'{"schema_version":2,' + path.read_bytes()[1:])
    elif fault == "raw_bytes_after_seal":
        raw_path.write_bytes(b'{"fictional":"changed after sealing"}\n')
    elif fault == "missing_raw":
        raw_path.unlink()
    elif fault == "raw_is_directory":
        raw_path.unlink()
        raw_path.mkdir()
    paths = {name: "input/" + name + ".json" for name in ("case", "snapshot", "catalog", "scorer", "local_model") if name in documents}
    if trusted_runtime is not None:
        paths["trusted_runtime"] = str(trusted_runtime)
    descriptor = dict(schema_version=1, control_id=spec["control_id"], operation=spec["operation"], variant=spec["variant"],
        paths=paths, options=dict(budget={**BUDGET, **recipe.get("budget", {})}, disabled=[], review_enabled=True), anchors={})
    if "process_limits" in recipe:
        descriptor["options"]["process_limits"] = copy.deepcopy(recipe["process_limits"])
    pending = {key: copy.deepcopy(recipe[key]) for key in ("sealed_producer", "sealed_mutation", "policy_recipe") if key in recipe}
    return descriptor, pending


def runtime_witness_specs():
    """Separate runtime mutation witnesses; not static paired case denominators."""
    return [dict(witness_id="IMM001", obligation_ids=["EP-SCOPE-01", "EP-EXEC-03"],
                 action="nested mutation through store query method.parameters/features", expected="admitted fingerprint unchanged"),
            dict(witness_id="IMM002", obligation_ids=["EP-EXEC-03"],
                 action="nested mutation through committed ledger claim", expected="committed claim unchanged"),
            dict(witness_id="IMM003", obligation_ids=["EP-EXEC-04"],
                 action="nested mutation through finalized coverage/trace/configuration", expected="final result unchanged")]


def oracle_manifest():
    return dict(schema_version=1, corpus_id="tether-equal-policy-fictional-v1", status="construction_not_frozen",
        independence="Expected outcomes from declared rules; authors exposed to repository and prior regressions",
        cases=[dict(control_id=item["control_id"], operation=item["operation"], variant=item["variant"],
                    construction_stratum=item["construction_stratum"], **copy.deepcopy(item["oracle"])) for item in case_specs()])


def case_manifest():
    """Preparation schedule includes oracle separately; never hand it to validator."""
    return dict(schema_version=1, corpus_id="tether-equal-policy-fictional-v1", status="construction_not_frozen", cases=case_specs())
