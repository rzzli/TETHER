"""Review method-plan misuse without running genetics or admitting a feature.

These checks distinguish declared statistical inputs from scientific qualification.
They do not inspect payloads or establish that a caller's qualification assertions
are true. Numeric implementations/reference comparisons remain a separate gate.
"""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any


METHODS = {"coloc_abf_beta", "coloc_abf_p", "coloc_susie", "mr_wald", "mr_ivw"}
HISTORICAL_INPUT_ROLES = {"agent_evidence", "reference"}


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def review_method_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Return declared-plan readiness and retained holds, never feature admission.

    ``traits`` contains exposure/outcome field-name inventories, not data arrays.
    ``lineage`` must identify/hash every declared ancestor, explicitly permit its
    predictor-input role and bound availability for historical use. This validates
    declarations, not source payloads or completeness of an external lineage graph.
    Unknown ancestry/overlap/source trust is not filled in here.
    """
    algorithm: list[str] = []
    scientific: list[str] = []
    historical: list[str] = []
    admission: list[str] = []
    method = plan.get("method")
    if method not in METHODS:
        algorithm.append("unsupported_method")
    traits = plan.get("traits", [])
    if not isinstance(traits, list) or len(traits) != 2 or any(not isinstance(t, dict) for t in traits):
        algorithm.append("two_trait_contracts_required")
        traits = []

    for index, trait in enumerate(traits):
        names = trait.get("fields", [])
        fields = set(names) if isinstance(names, list) and all(isinstance(n, str) for n in names) else set()
        prefix = f"trait_{index}:"
        if method in {"coloc_abf_beta", "coloc_susie"}:
            if not {"beta", "varbeta"} <= fields:
                algorithm.append(prefix + "beta_varbeta_required")
            if trait.get("type") not in {"quant", "cc"}:
                algorithm.append(prefix + "trait_type_required")
            # runsusie delegates to check_dataset, retaining its scale contract.
            if trait.get("type") == "quant":
                if "sdY" not in fields and not {"N", "MAF"} <= fields:
                    algorithm.append(prefix + "sdY_or_N_MAF_required")
            if "sdY" in fields and trait.get("type") == "quant" and trait.get("scale_qualified") is not True:
                scientific.append(prefix + "sdY_scale_unqualified")
        if method == "coloc_abf_p":
            if not {"pvalues", "MAF", "N"} <= fields:
                algorithm.append(prefix + "pvalues_MAF_N_required")
            if trait.get("type") not in {"quant", "cc"}:
                algorithm.append(prefix + "trait_type_required")
            if trait.get("type") == "cc" and "s" not in fields:
                algorithm.append(prefix + "case_fraction_required")
        if method == "coloc_susie" and "N" not in fields:
            algorithm.append(prefix + "runsusie_study_N_required")
        if method in {"mr_wald", "mr_ivw"} and not {"beta", "se"} <= fields:
            algorithm.append(prefix + "beta_SE_required")
        if trait.get("sample_size_source") == "LD_reference":
            scientific.append(prefix + "reference_count_is_not_study_N")
        if trait.get("imputed_required_fields"):
            scientific.append(prefix + "arbitrary_required_field_imputation")

    region = plan.get("region", {})
    if not isinstance(region, dict):
        region = {}
    if region.get("variant_identity_qualified") is not True:
        scientific.append("variant_identity_unqualified")
    if method in {"coloc_abf_beta", "coloc_abf_p", "coloc_susie"}:
        if region.get("dense_shared_eligible_region") is not True:
            scientific.append("dense_shared_region_unqualified")
        if region.get("significance_filtered") is not False:
            scientific.append("significance_filtered_or_unknown_region")
        if region.get("scope_frozen") is not True:
            scientific.append("regional_scope_not_frozen")
    if method in {"coloc_abf_beta", "coloc_abf_p"} and region.get("LD_only_subset") is not False:
        scientific.append("ABF_cannot_inherit_LD_only_coverage")

    ld_required = method == "coloc_susie" or (method == "mr_ivw" and plan.get("instruments_independent") is not True)
    if ld_required:
        ld = plan.get("LD", {})
        if not isinstance(ld, dict):
            ld = {}
        if ld.get("kind") != "signed_r":
            algorithm.append("signed_correlation_LD_required")
        for field in ("variant_order_verified", "effect_alleles_aligned", "numeric_integrity_verified", "PSD_verified"):
            if ld.get(field) is not True:
                algorithm.append("LD_" + field + "_required")
        if ld.get("study_compatibility_qualified") is not True:
            scientific.append("study_LD_compatibility_unqualified")
        if ld.get("singular") is True and ld.get("rank_handling_qualified") is not True:
            scientific.append("singular_LD_handling_unqualified")

    if plan.get("source_trust") != "qualified":
        scientific.append("source_trust_unqualified")
    for field in ("assay_mapping_qualified", "study_context_qualified", "analysis_plan_frozen"):
        if plan.get(field) is not True:
            scientific.append(field + "_required")
    if plan.get("overlap_review") not in {"disjoint_documented", "bounded_sensitivity_qualified"}:
        scientific.append("overlap_not_qualified")
    if method in {"mr_wald", "mr_ivw"}:
        for field in ("instrument_plan_frozen", "identification_assumptions_reviewed", "strength_uncertainty_reviewed"):
            if plan.get(field) is not True:
                scientific.append(field + "_required")
    if method in {"coloc_abf_beta", "coloc_abf_p"} and plan.get("single_causal_model_reviewed") is not True:
        scientific.append("single_causal_model_not_reviewed")
    if method == "coloc_susie" and plan.get("multisignal_diagnostics_plan") is not True:
        scientific.append("multisignal_diagnostics_plan_required")
    if plan.get("exposure_kind") == "gene_transcript" and plan.get("claim_scope") not in {"transcript", "locus_association"}:
        scientific.append("RNA_cannot_be_relabelled_protein_or_drug_action")
    if plan.get("drug_action") is not None:
        scientific.append("drug_action_outside_genetics_method_guard")

    if plan.get("historical_use") is True:
        origin = _instant(plan.get("origin_at"))
        if origin is None:
            historical.append("qualified_origin_required")
        lineage = plan.get("lineage")
        if plan.get("complete_lineage_qualified") is not True or not isinstance(lineage, list) or not lineage:
            historical.append("complete_information_lineage_required")
        if isinstance(lineage, list):
            source_hashes: dict[str, str] = {}
            for index, ancestor in enumerate(lineage):
                ancestor = ancestor if isinstance(ancestor, dict) else {}
                source_id = ancestor.get("source_id", ancestor.get("source"))
                source_id = source_id.strip() if isinstance(source_id, str) else ""
                if not source_id:
                    historical.append(f"ancestor_{index}:source_identity_required")
                sha256 = ancestor.get("sha256")
                if not isinstance(sha256, str) or re.fullmatch(r"[0-9a-fA-F]{64}", sha256) is None:
                    historical.append(f"ancestor_{index}:sha256_required")
                elif source_id:
                    digest = sha256.lower()
                    if source_id in source_hashes and source_hashes[source_id] != digest:
                        historical.append(f"ancestor_{index}:conflicting_source_hash")
                    source_hashes[source_id] = digest
                role = ancestor.get("role")
                if not isinstance(role, str) or role not in HISTORICAL_INPUT_ROLES:
                    historical.append(f"ancestor_{index}:historical_input_role_unqualified")
                bound = _instant(ancestor.get("available_by"))
                if bound is None:
                    historical.append(f"ancestor_{index}:availability_unverified")
                elif origin is not None and bound > origin:
                    historical.append(f"ancestor_{index}:availability_after_origin")

    if plan.get("independent_numeric_validation_passed") is not True:
        admission.append("independent_numeric_validation_required")
    if plan.get("source_and_scientific_review_evidence_verified") is not True:
        admission.append("review_assertions_require_retained_verified_evidence")
    admission.append("plan_guard_never_admits_predictive_features")
    return {
        "method": method,
        "algorithm_plan_ready": not algorithm,
        "scientific_plan_ready": not scientific,
        "historical_plan_ready": not historical if plan.get("historical_use") is True else None,
        "ready_for_independent_review": not (algorithm or scientific or historical),
        "algorithm_holds": algorithm,
        "scientific_holds": scientific,
        "historical_holds": historical,
        "admission_holds": admission,
        "feature_admitted": False,
        "genetics_computation_performed": False,
    }
