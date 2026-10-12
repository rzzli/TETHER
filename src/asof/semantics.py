"""Recompute source/ledger/feature/prediction bindings without claiming scientific truth."""
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .agents import Usage
from .chrono import eligible_artifacts, observation_exclusion
from .contracts import Case, Category, Claim, EvidenceStatus, Profile, Snapshot
from .features import build_features
from .provenance import InputGraph, catalog_index
from .scorer import abstain, score
from .serde import ContractError, decode, encode, fingerprint


def check_execution(run, case, snapshot, configuration, claims, trace):
    """Reconcile finalized metadata, configuration, claims and accounted attempts."""
    from .workflow import Budget, add_usage
    run, configuration, trace = encode(run), encode(configuration), encode(trace)
    if (run.get("schema_version") != 2 or run.get("case_id") != case.case_id or
            run.get("snapshot_id") != snapshot.snapshot_id or run.get("profile") != snapshot.profile.value or
            run.get("backend_id") != configuration.get("backend_id")):
        raise ContractError("Semantic run identity mismatch")
    budget = decode(Budget, run["budget"])
    budget.validate()
    if budget != decode(Budget, configuration.get("budget")):
        raise ContractError("Semantic run budget/configuration mismatch")
    plans = [event["details"] for event in trace if event["event"] == "plan"]
    if (len(plans) != 1 or plans[0].get("snapshot_id") != snapshot.snapshot_id or
            fingerprint(plans[0].get("configuration")) != fingerprint(configuration) or
            fingerprint(plans[0].get("steps")) != fingerprint(run.get("plan"))):
        raise ContractError("Semantic plan/configuration mismatch")
    if ([step["category"] for step in run["plan"]] != [category.value for category in Category] or
            set(run["coverage"]) != {category.value for category in Category}):
        raise ContractError("Semantic specialist inventory mismatch")
    for step in run["plan"]:
        coverage = run["coverage"][step["category"]]
        if step["observed_records"] != coverage["available_observations"]:
            raise ContractError("Semantic plan/coverage mismatch")
        initial = "disabled" if step["category"] in configuration["disabled"] else (
            "ready" if step["observed_records"] else "no_observed_evidence")
        if step["initial_status"] != initial:
            raise ContractError("Semantic configured specialist status mismatch")
    attempts, accounted, committed = {}, set(), []
    used = measured = estimated = Usage(0, 0, 0)
    for event in trace:
        details = event["details"]
        if event["event"] == "dispatch":
            key = details["attempt_id"]
            if key in attempts or set(attempts) != accounted:
                raise ContractError("Semantic duplicate or overlapping dispatch")
            quote = decode(Usage, details["reserved"])
            quote.validate()
            if (details["category"] not in run["coverage"] or
                    details["category"] in configuration["disabled"] or
                    details["attempt"] < 1 or details["attempt"] > budget.max_retries + 1 or
                    key != f"{details['category']}:{details['attempt']}"):
                raise ContractError("Semantic invalid specialist attempt")
            if (len(attempts) >= budget.max_calls or used.input_tokens + quote.input_tokens > budget.max_input_tokens or
                    used.output_tokens + quote.output_tokens > budget.max_output_tokens or
                    used.cost_usd + quote.cost_usd > budget.max_cost_usd):
                raise ContractError("Semantic dispatch exceeded its reservation budget")
            attempts[key] = quote
        elif event["event"] == "attempt_accounted":
            key = details["attempt_id"]
            if key not in attempts or key in accounted:
                raise ContractError("Semantic unmatched or duplicate usage accounting")
            usage = decode(Usage, details["usage"])
            usage.validate()
            if details["basis"] == "adapter_reported":
                measured = add_usage(measured, usage)
            elif details["basis"] == "quoted_upper_bound_not_measured":
                if usage != attempts[key]:
                    raise ContractError("Semantic unmeasured usage differs from reservation")
                estimated = add_usage(estimated, usage)
            else:
                raise ContractError("Semantic unknown accounting basis")
            used = add_usage(used, usage)
            accounted.add(key)
        elif event["event"] == "claim_committed":
            committed.append(details["claim"])
    if set(attempts) != accounted:
        raise ContractError("Semantic finalized run contains an unresolved attempt")
    if (type(run["calls"]) is not int or run["calls"] != len(attempts) or
            used != decode(Usage, run["usage"]) or
            measured != decode(Usage, run["measured_usage"]) or
            estimated != decode(Usage, run["estimated_usage"])):
        raise ContractError("Semantic run accounting/journal mismatch")
    if fingerprint(committed) != fingerprint(claims):
        raise ContractError("Semantic journal/ledger claim mismatch")


def check_semantics(case, snapshot, claims, features, prediction, coverage, configuration,
                    status, model, admitted, catalog_policy, root, trace):
    case.validate()
    if snapshot.schema_version != 2 or snapshot.origin_at != case.origin_at or snapshot.origin != case.origin:
        raise ContractError("Semantic case/snapshot origin mismatch")
    if snapshot.profile != Profile.DEMO and not catalog_policy:
        raise ContractError("Semantic real-data snapshot requires archived catalog policy")
    graph = InputGraph(snapshot, Path(root), catalog_index(catalog_policy) if catalog_policy else None)
    seen = set()
    artifacts = {item.artifact_id: item for item, reason in eligible_artifacts(snapshot, graph, case) if reason is None}
    artifact_inputs = {key: frozenset(graph.closure(item.input_refs)) for key, item in artifacts.items()}
    for claim in claims:
        observation, citation = claim.evidence.observation, claim.evidence.citation
        digest = fingerprint(claim.evidence)
        if digest != claim.admitted_fingerprint or digest != admitted.get(observation.observation_id):
            raise ContractError("Semantic source-to-claim fingerprint mismatch")
        if observation.observation_id in seen:
            raise ContractError("Semantic duplicate claim")
        seen.add(observation.observation_id)
        if (observation.target_id != case.hypothesis.target_id or observation.indication_id != case.hypothesis.indication_id or
                claim.specialist != observation.category or
                observation.program_id is not None and (case.program is None or observation.program_id != case.program.program_id)):
            raise ContractError("Semantic claim outside hypothesis/program capability")
        artifact = artifacts.get(citation.artifact_id)
        if (artifact is None or citation.artifact_sha256 != artifact.sha256 or
                citation.dataset_id != artifact.dataset_id or citation.release_id != artifact.release_id or
                citation.source_url != artifact.source_url):
            raise ContractError("Semantic citation mismatch")
        if (observation_exclusion(observation, artifact, graph, case, artifact_inputs[artifact.artifact_id]) or
                observation.status != EvidenceStatus.OBSERVED):
            raise ContractError("Semantic claim contains ineligible information")
        expected_id = "claim-" + fingerprint({"case": case.case_id, "evidence": claim.evidence})[:20]
        if claim.claim_id != expected_id or claim.extraction_mode != "verbatim_source_selection":
            raise ContractError("Semantic claim identity mismatch")
    counts = Counter(claim.specialist.value for claim in claims)
    for category, item in coverage.items():
        if item["selected_observations"] != counts[category]:
            raise ContractError("Semantic coverage/ledger mismatch")
    missingness = {category: tuple(item["status"] for item in value["nonobserved"])
                   + (("source_incomplete",) if snapshot.coverage and
                      snapshot.coverage.get("source_completeness") != "complete" else ())
                   for category, value in coverage.items()}
    rebuilt = build_features(claims, case, missingness)
    if fingerprint(rebuilt) != fingerprint(features):
        raise ContractError("Semantic ledger-to-feature mismatch")
    expected = abstain(case, "run_incomplete", model) if status != "completed" else score(case, snapshot.profile, rebuilt, model)
    if snapshot.profile == Profile.DEMO:
        expected = replace(expected, synthetic=True)
    if fingerprint(expected) != fingerprint(prediction):
        raise ContractError("Semantic feature-to-prediction mismatch")
    if not trace or trace[-1]["event"] != "finalize":
        raise ContractError("Semantic final trace event missing")
    final = trace[-1]["details"]
    if (final["feature_sha256"] != fingerprint(features) or
            final["prediction_sha256"] != fingerprint(prediction) or final["status"] != status):
        raise ContractError("Semantic trace/output fingerprint mismatch")
    if configuration.get("hypothesis_key") != case.hypothesis.key:
        raise ContractError("Semantic hypothesis key mismatch")

