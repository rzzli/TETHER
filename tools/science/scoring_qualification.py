"""Fail-closed review of declared historical scoring plans; never train a model.

This module checks declarations and contradictions. It does not verify payloads,
discover missing ancestors, establish scientific validity, or authorize fitting.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import re
from typing import Any


ENDPOINTS = {"clinical_success", "registry_next_phase_actual_start", "verified_experimental_dosing"}
PARTITIONS = {"train", "calibration", "test"}
PREDICTOR_ROLES = {"agent_evidence", "reference"}


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result if result.tzinfo is not None else None


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def review_scoring_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Review a plan, returning holds and ``fit_allowed=False`` on every path."""
    holds: dict[str, list[str]] = {key: [] for key in
        ("scope", "features", "chronology", "models", "labels", "splits", "preprocessing", "science")}
    identities: dict[str, str] = {}
    identity_roles: dict[str, str] = {}

    def hold(category: str, reason: str) -> None:
        holds[category].append(reason)

    def artifact(item: Any, category: str, prefix: str) -> bool:
        if not isinstance(item, dict):
            hold(category, prefix + ":artifact_required")
            return False
        identity, digest = item.get("artifact_id"), item.get("sha256")
        valid = True
        if not _text(identity):
            hold(category, prefix + ":identity_required")
            valid = False
        if not isinstance(digest, str) or re.fullmatch(r"[a-fA-F0-9]{64}", digest) is None:
            hold(category, prefix + ":sha256_required")
            valid = False
        if valid:
            if identity in identities and identities[identity] != digest.lower():
                hold(category, prefix + ":conflicting_identity_hash")
            identities[identity] = digest.lower()
            for role in (item.get('role'), item.get('source_role')):
                if not isinstance(role, str):
                    continue
                role_class = 'predictor' if role in PREDICTOR_ROLES else role
                if identity in identity_roles and identity_roles[identity] != role_class:
                    hold(category, prefix + ':conflicting_identity_role')
                identity_roles[identity] = role_class
        return valid

    def feature_ancestor(item: Any, origin: datetime | None, prefix: str) -> None:
        artifact(item, "features", prefix)
        item = item if isinstance(item, dict) else {}
        if item.get("role") not in PREDICTOR_ROLES:
            hold("features", prefix + ":predictor_role_required")
        available = _time(item.get("available_by"))
        if available is None:
            hold("chronology", prefix + ":availability_unverified")
        elif origin is not None and available > origin:
            hold("chronology", prefix + ":knowledge_after_row_origin")
        if item.get("current_fallback") is not False:
            hold("features", prefix + ":current_fallback_or_unknown")

    origin = _time(plan.get("test_origin_at"))
    if origin is None:
        hold("chronology", "test_origin_required")
    if plan.get("endpoint_id") not in ENDPOINTS:
        hold("scope", "named_endpoint_required")
    if plan.get("output_mode") not in {"probability", "rank_only"}:
        hold("scope", "output_mode_required")
    if plan.get("test_outcomes_accessed") is not False:
        hold("scope", "test_outcome_isolation_unqualified")
    if plan.get("predictor_bundle_qualified") is not True:
        hold("features", "predictor_bundle_not_qualified")

    schema = plan.get("feature_schema", {})
    artifact(schema, "features", "feature_schema")
    schema = schema if isinstance(schema, dict) else {}
    if not isinstance(schema.get("columns"), list) or not schema.get("columns") or any(not _text(c) for c in schema.get("columns", [])):
        hold("features", "feature_columns_required")
    elif len(set(schema["columns"])) != len(schema["columns"]):
        hold("features", "duplicate_feature_columns")
    if schema.get("frozen_before_test_outcomes") is not True or schema.get("selection_used_test_outcomes") is not False:
        hold("features", "feature_schema_or_selection_not_sealed")
    required_roles = schema.get("scientific_model_roles")
    if not isinstance(required_roles, list) or any(not _text(r) for r in required_roles) or len(set(required_roles)) != len(required_roles):
        hold("models", "explicit_unique_model_role_inventory_required")
        required_roles = []
    recipe = plan.get("derivation", {})
    artifact(recipe, "features", "derivation")
    recipe = recipe if isinstance(recipe, dict) else {}
    for field in ("deterministic", "same_recipe_all_partitions", "no_later_information"):
        if recipe.get(field) is not True:
            hold("features", "derivation_" + field + "_required")
    # A later execution time alone is not later scientific knowledge.
    if _time(recipe.get("computed_at")) is None:
        hold("features", "derivation_computation_timestamp_required")

    rows = plan.get("rows")
    if not isinstance(rows, list) or not rows:
        hold("scope", "qualified_training_calibration_test_rows_not_supplied")
        rows = []
    row_ids: set[str] = set()
    partition_counts: Counter = Counter()
    classes = {"train": Counter(), "calibration": Counter()}
    program_partitions: dict[str, set[str]] = {}
    component_partitions: dict[str, set[str]] = {}
    for index, row in enumerate(rows):
        prefix = f"row_{index}"
        if not isinstance(row, dict):
            hold("scope", prefix + ":row_contract_required")
            continue
        row_id, partition = row.get("row_id"), row.get("partition")
        if not _text(row_id) or row_id in row_ids:
            hold("splits", prefix + ":unique_row_id_required")
        elif isinstance(row_id, str):
            row_ids.add(row_id)
        if partition not in PARTITIONS:
            hold("splits", prefix + ":partition_required")
        else:
            partition_counts[partition] += 1
        for field, registry in (("program_id", program_partitions), ("dependence_component_id", component_partitions)):
            value = row.get(field)
            if not _text(value):
                hold("splits", prefix + ":" + field + "_required")
            elif partition in PARTITIONS:
                registry.setdefault(value, set()).add(partition)
        row_origin = _time(row.get("origin_at"))
        if row_origin is None:
            hold("chronology", prefix + ":row_origin_required")
        elif origin is not None:
            if partition == "test" and row_origin != origin:
                hold("chronology", prefix + ":test_row_origin_mismatch")
            if partition in {"train", "calibration"} and row_origin >= origin:
                hold("chronology", prefix + ":development_origin_not_before_test")
        if row.get("features_qualified") is not True or row.get("complete_feature_lineage") is not True:
            hold("features", prefix + ":feature_qualification_and_complete_lineage_required")
        ancestors = row.get("ancestors")
        if not isinstance(ancestors, list) or not ancestors:
            hold("features", prefix + ":feature_ancestors_required")
            ancestors = []
        kinds = set()
        for ai, ancestor in enumerate(ancestors):
            feature_ancestor(ancestor, row_origin, prefix + f":ancestor_{ai}")
            if isinstance(ancestor, dict) and _text(ancestor.get("kind")):
                kinds.add(ancestor["kind"])
        if not {"source", "mapping"} <= kinds:
            hold("features", prefix + ":source_and_mapping_lineage_required")

        models = row.get("models")
        if not isinstance(models, list):
            hold("models", prefix + ":model_inventory_required")
            models = []
        actual_roles = []
        for mi, model in enumerate(models):
            mp = prefix + f":model_{mi}"
            artifact(model, "models", mp)
            model = model if isinstance(model, dict) else {}
            actual_roles.append(model.get("scientific_role"))
            revision = model.get("revision")
            if not isinstance(revision, str) or re.fullmatch(r"[0-9a-fA-F]{40}", revision) is None:
                hold("models", mp + ":immutable_revision_required")
            released = _time(model.get("released_by"))
            if released is None or (row_origin is not None and released > row_origin):
                hold("models", mp + ":model_release_not_qualified_at_row_origin")
            assets = model.get("assets", [])
            asset_kinds = set()
            if not isinstance(assets, list):
                assets = []
            for asset in assets:
                artifact(asset, "models", mp + ":asset")
                if isinstance(asset, dict) and _text(asset.get("kind")):
                    asset_kinds.add(asset["kind"])
                    if asset["kind"] != 'runtime':
                        # This is an information-availability bound, not the
                        # file's creation, conversion, download or execution time.
                        feature_ancestor(asset, row_origin, mp + ":" + asset["kind"])
                    elif asset["kind"] == "runtime":
                        if asset.get("role") != "execution_runtime" or asset.get("information_bearing") is not False or asset.get("scientific_adaptation") is not False:
                            hold("models", mp + ":runtime_must_be_explicitly_non_scientific")
                else:
                    hold('models', mp + ':asset_kind_required')
            if not {"weights", "tokenizer", "config", "runtime"} <= asset_kinds:
                hold("models", mp + ":complete_model_assets_required")
            if model.get("complete_adaptation_lineage") is not True or not isinstance(model.get("adaptations"), list):
                hold("models", mp + ":adaptation_lineage_required")
            else:
                for ai, adaptation in enumerate(model["adaptations"]):
                    feature_ancestor(adaptation, row_origin, mp + f":adaptation_{ai}")
        if sorted(str(r) for r in actual_roles) != sorted(required_roles):
            hold("models", prefix + ":scientific_model_roles_incomplete_or_extra")

        label = row.get("label")
        if partition == "test":
            if label is not None:
                hold("labels", prefix + ":test_label_must_remain_sealed")
        elif partition in {"train", "calibration"}:
            artifact(label, "labels", prefix + ":label")
            label = label if isinstance(label, dict) else {}
            valid_binary = label.get("status") == "qualified_binary" and type(label.get("value")) is int and label["value"] in (0, 1)
            if not valid_binary:
                hold("labels", prefix + ":qualified_binary_label_required")
            else:
                classes[partition][label["value"]] += 1
            purpose = "training_label" if partition == "train" else "calibration_label"
            if label.get("purpose") != purpose or label.get("source_role") != "evaluation_only":
                hold("labels", prefix + ":isolated_supervised_label_role_required")
            if label.get("endpoint_id") != plan.get("endpoint_id"):
                hold("labels", prefix + ":endpoint_mismatch")
            if label.get("ascertainment_qualified") is not True:
                hold("labels", prefix + ":ascertainment_unqualified")
            available = _time(label.get("available_by"))
            horizon = _time(label.get("horizon_at"))
            if available is None or (origin is not None and available >= origin):
                hold("chronology", prefix + ":label_not_available_before_test_origin")
            if horizon is None or (row_origin is not None and horizon <= row_origin):
                hold("chronology", prefix + ":development_label_horizon_required")
            if available is not None and horizon is not None and horizon > available:
                hold("chronology", prefix + ":label_not_mature_at_availability")
            label_sources = label.get("sources")
            if label.get("complete_label_lineage") is not True or not isinstance(label_sources, list) or not label_sources:
                hold("labels", prefix + ":complete_label_source_lineage_required")
                label_sources = []
            for si, source in enumerate(label_sources):
                sp = prefix + f":label_source_{si}"
                artifact(source, "labels", sp)
                source = source if isinstance(source, dict) else {}
                if source.get("role") != "evaluation_only":
                    hold("labels", sp + ":outcome_source_role_required")
                source_available = _time(source.get("available_by"))
                if source_available is None or (origin is not None and source_available >= origin):
                    hold("chronology", sp + ":source_not_available_before_test_origin")
                if source_available is not None and available is not None and source_available > available:
                    hold("chronology", sp + ":source_after_declared_label_availability")
    for name, registry in (("program", program_partitions), ("dependence_component", component_partitions)):
        if any(len(parts) > 1 for parts in registry.values()):
            hold("splits", name + "_leaks_across_partitions")
    if any(partition_counts[p] == 0 for p in PARTITIONS):
        hold("splits", "train_calibration_test_membership_required")
    for partition in classes:
        if not classes[partition][0] or not classes[partition][1]:
            hold("labels", partition + ":both_binary_classes_required_not_sufficiency_proof")

    splits = plan.get("split_manifest", {})
    artifact(splits, "splits", "split_manifest")
    splits = splits if isinstance(splits, dict) else {}
    if splits.get("frozen_before_fitting") is not True or splits.get("dependence_graph_qualified") is not True:
        hold("splits", "sealed_grouped_split_and_dependence_graph_required")
    preprocessing = plan.get("preprocessing", {})
    artifact(preprocessing, "preprocessing", "preprocessing")
    preprocessing = preprocessing if isinstance(preprocessing, dict) else {}
    if preprocessing.get("fit_partitions") != ["train"] or preprocessing.get("selection_and_transforms_train_only") is not True:
        hold("preprocessing", "all_learned_preprocessing_and_selection_train_only")
    scorer = plan.get("scorer_spec", {})
    artifact(scorer, "preprocessing", "scorer_spec")
    scorer = scorer if isinstance(scorer, dict) else {}
    if not _text(scorer.get("estimator_id")) or scorer.get("hyperparameters_frozen") is not True or scorer.get("selection_used_test_outcomes") is not False:
        hold("preprocessing", "scorer_estimator_and_selection_plan_required")
    if plan.get("output_mode") == "probability":
        calibration = plan.get("calibration", {})
        artifact(calibration, "preprocessing", "calibration")
        calibration = calibration if isinstance(calibration, dict) else {}
        if calibration.get("fit_partitions") != ["calibration"] or calibration.get("method_frozen") is not True:
            hold("preprocessing", "separate_frozen_calibration_plan_required")
    science = plan.get("scientific_design", {})
    science = science if isinstance(science, dict) else {}
    for field in ("training_cohort_qualified", "sample_adequacy_qualified", "dependence_qualified", "discrimination_power_qualified"):
        if science.get(field) is not True:
            hold("science", field + "_required")
    if plan.get("output_mode") == "probability" and science.get("calibration_precision_qualified") is not True:
        hold("science", "calibration_precision_qualified_required")
    if plan.get("uses_genetics") is not False and plan.get("uses_genetics") is not True:
        hold("science", "genetics_usage_must_be_explicit")
    if plan.get("uses_genetics") is True and plan.get("genetics_method_qualified") is not True:
        hold("science", "genetics_gate_required_only_when_genetics_used")
    if plan.get("independent_payload_and_design_review_passed") is not True:
        hold("science", "independent_payload_and_design_review_required")
    ready = not any(holds.values())
    return {
        "decision": "independent_review_only_no_fit_authorized" if ready else "no_fit",
        "ready_for_independent_review": ready,
        "fit_allowed": False,
        "trained_models": 0,
        "calibrated_models": 0,
        "new_features": 0,
        "probabilities_emitted": 0,
        "holds": holds,
        "declared_class_counts": {p: {"negative": c[0], "positive": c[1]} for p, c in classes.items()},
        "verification_limit": "Declaration consistency only; no payload, scientific-validity or fitting authorization claim.",
    }
