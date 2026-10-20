"""Scientific-misuse regressions for the conditional genetics plan guard."""
from copy import deepcopy
import unittest

from tools.science.genetics_qualification import review_method_plan


def abf_plan():
    return {
        "method": "coloc_abf_beta",
        "traits": [
            {"type": "quant", "fields": ["beta", "varbeta", "sdY"], "scale_qualified": True},
            {"type": "cc", "fields": ["beta", "varbeta"]},
        ],
        "region": {"variant_identity_qualified": True, "dense_shared_eligible_region": True,
                   "significance_filtered": False, "LD_only_subset": False, "scope_frozen": True},
        "source_trust": "qualified",
        "assay_mapping_qualified": True,
        "study_context_qualified": True,
        "analysis_plan_frozen": True,
        "overlap_review": "disjoint_documented",
        "single_causal_model_reviewed": True,
        "exposure_kind": "gene_transcript",
        "claim_scope": "transcript",
        "historical_use": False,
    }


def historical_ancestor(source="GCST90132223", available_by="2024-12-31T23:00:00Z"):
    # Synthetic declaration fixture, not a source-payload verification receipt.
    return {"source": source, "sha256": "a" * 64, "role": "agent_evidence",
            "available_by": available_by}


def historical_plan():
    plan = abf_plan()
    plan.update(historical_use=True, origin_at="2025-01-01T00:00:00Z",
                complete_lineage_qualified=True, lineage=[historical_ancestor()])
    return plan


class GeneticsMethodGuardTests(unittest.TestCase):
    def test_beta_variance_abf_does_not_invent_unused_N_EAF_LD_or_case_fraction(self):
        result = review_method_plan(abf_plan())
        self.assertTrue(result["algorithm_plan_ready"])
        self.assertTrue(result["scientific_plan_ready"])
        self.assertFalse(result["feature_admitted"])
        self.assertIn("independent_numeric_validation_required", result["admission_holds"])

    def test_2979_LD_intersection_is_not_dense_ABF_by_assertion(self):
        plan = abf_plan()
        plan["region"]["LD_only_subset"] = True
        result = review_method_plan(plan)
        self.assertTrue(result["algorithm_plan_ready"])
        self.assertFalse(result["scientific_plan_ready"])
        self.assertIn("ABF_cannot_inherit_LD_only_coverage", result["scientific_holds"])

    def test_significant_hits_do_not_substitute_for_complete_region(self):
        plan = abf_plan()
        plan["region"]["significance_filtered"] = True
        self.assertFalse(review_method_plan(plan)["scientific_plan_ready"])

    def test_unknown_quantitative_scale_needs_real_estimation_inputs(self):
        plan = abf_plan()
        plan["traits"][0]["fields"].remove("sdY")
        self.assertIn("trait_0:sdY_or_N_MAF_required", review_method_plan(plan)["algorithm_holds"])
        plan["traits"][0]["fields"] += ["N", "MAF"]
        self.assertTrue(review_method_plan(plan)["algorithm_plan_ready"])
        plan["traits"][0]["imputed_required_fields"] = ["N"]
        self.assertFalse(review_method_plan(plan)["scientific_plan_ready"])

    def test_sdY_one_requires_scale_evidence(self):
        plan = abf_plan()
        plan["traits"][0]["scale_qualified"] = False
        self.assertIn("trait_0:sdY_scale_unqualified", review_method_plan(plan)["scientific_holds"])

    def test_p_approximation_does_need_N_MAF_and_case_fraction(self):
        plan = abf_plan()
        plan["method"] = "coloc_abf_p"
        self.assertFalse(review_method_plan(plan)["algorithm_plan_ready"])
        for trait in plan["traits"]:
            trait["fields"] = ["pvalues", "MAF", "N"]
        self.assertIn("trait_1:case_fraction_required", review_method_plan(plan)["algorithm_holds"])
        plan["traits"][1]["fields"].append("s")
        self.assertTrue(review_method_plan(plan)["algorithm_plan_ready"])

    def test_susie_needs_signed_aligned_LD_and_study_N(self):
        plan = abf_plan()
        plan["method"] = "coloc_susie"
        plan["multisignal_diagnostics_plan"] = True
        result = review_method_plan(plan)
        self.assertIn("trait_1:runsusie_study_N_required", result["algorithm_holds"])
        for trait in plan["traits"]:
            trait["fields"].append("N")
        plan["LD"] = {"kind": "signed_r", "variant_order_verified": True,
                      "effect_alleles_aligned": True, "numeric_integrity_verified": True,
                      "PSD_verified": True, "study_compatibility_qualified": True}
        self.assertTrue(review_method_plan(plan)["algorithm_plan_ready"])
        for fault in ("variant_order_verified", "effect_alleles_aligned"):
            broken = deepcopy(plan)
            broken["LD"][fault] = False
            self.assertFalse(review_method_plan(broken)["algorithm_plan_ready"])
        plan["LD"]["kind"] = "r_squared"
        self.assertIn("signed_correlation_LD_required", review_method_plan(plan)["algorithm_holds"])

    def test_external_LD_reproducibility_does_not_qualify_study_matching_or_N(self):
        plan = abf_plan()
        plan["method"] = "coloc_susie"
        plan["multisignal_diagnostics_plan"] = True
        for trait in plan["traits"]:
            trait["fields"].append("N")
            trait["sample_size_source"] = "LD_reference"
        plan["LD"] = {"kind": "signed_r", "variant_order_verified": True,
                      "effect_alleles_aligned": True, "numeric_integrity_verified": True,
                      "PSD_verified": True, "study_compatibility_qualified": False,
                      "singular": True}
        result = review_method_plan(plan)
        self.assertTrue(result["algorithm_plan_ready"])
        self.assertIn("study_LD_compatibility_unqualified", result["scientific_holds"])
        self.assertIn("singular_LD_handling_unqualified", result["scientific_holds"])
        self.assertIn("trait_0:reference_count_is_not_study_N", result["scientific_holds"])

    def test_RNA_sign_cannot_set_protein_or_drug_claim(self):
        for claim in ("protein", "drug_direction"):
            plan = abf_plan()
            plan["claim_scope"] = claim
            self.assertIn("RNA_cannot_be_relabelled_protein_or_drug_action",
                          review_method_plan(plan)["scientific_holds"])
        plan = abf_plan()
        plan["drug_action"] = "inhibit"
        self.assertFalse(review_method_plan(plan)["scientific_plan_ready"])

    def test_source_discrepancy_and_unknown_overlap_are_scientific_not_missing_algorithm_fields(self):
        plan = abf_plan()
        plan["source_trust"] = "quarantined"
        plan["overlap_review"] = "unknown"
        result = review_method_plan(plan)
        self.assertTrue(result["algorithm_plan_ready"])
        self.assertIn("source_trust_unqualified", result["scientific_holds"])
        self.assertIn("overlap_not_qualified", result["scientific_holds"])

    def test_historical_unknown_and_post_origin_ancestor_do_not_qualify_Jan2025(self):
        plan = historical_plan()
        plan["lineage"][0]["available_by"] = None
        self.assertFalse(review_method_plan(plan)["historical_plan_ready"])
        plan["lineage"][0]["available_by"] = "2025-01-02T00:00:00Z"
        self.assertIn("ancestor_0:availability_after_origin", review_method_plan(plan)["historical_holds"])
        plan["lineage"][0]["available_by"] = "2024-12-31T23:00:00Z"
        self.assertTrue(review_method_plan(plan)["historical_plan_ready"])
        plan["lineage"].append(historical_ancestor("assay_map", "2026-01-01"))
        self.assertFalse(review_method_plan(plan)["historical_plan_ready"])

    def test_old_evaluator_content_cannot_become_historical_predictor_input(self):
        for role in ("evaluator_only", "evaluation_only", "unknown", ""):
            plan = historical_plan()
            plan["lineage"][0]["role"] = role
            result = review_method_plan(plan)
            self.assertFalse(result["historical_plan_ready"])
            self.assertFalse(result["ready_for_independent_review"])
            self.assertIn("ancestor_0:historical_input_role_unqualified", result["historical_holds"])
        plan["lineage"][0]["role"] = "reference"
        self.assertTrue(review_method_plan(plan)["historical_plan_ready"])

    def test_bare_date_and_missing_or_malformed_ancestor_identity_hash_role_hold(self):
        plan = historical_plan()
        plan["lineage"] = [{"available_by": "2024-12-31T23:00:00Z"}]
        result = review_method_plan(plan)
        for reason in ("source_identity_required", "sha256_required", "historical_input_role_unqualified"):
            self.assertIn("ancestor_0:" + reason, result["historical_holds"])
        for field, value in (("source", None), ("source", "  "), ("sha256", None),
                             ("sha256", "z" * 64), ("sha256", "a" * 63), ("role", None)):
            broken = historical_plan()
            broken["lineage"][0][field] = value
            self.assertFalse(review_method_plan(broken)["historical_plan_ready"])

    def test_conflicting_duplicate_source_hashes_do_not_qualify_lineage(self):
        plan = historical_plan()
        plan["lineage"].append(deepcopy(plan["lineage"][0]))
        self.assertTrue(review_method_plan(plan)["historical_plan_ready"])
        plan["lineage"][1]["sha256"] = "b" * 64
        result = review_method_plan(plan)
        self.assertFalse(result["historical_plan_ready"])
        self.assertIn("ancestor_1:conflicting_source_hash", result["historical_holds"])

    def test_explicit_source_id_and_at_origin_bound_remain_valid_declarations(self):
        plan = historical_plan()
        ancestor = plan["lineage"][0]
        ancestor["source_id"] = ancestor.pop("source")
        ancestor["available_by"] = plan["origin_at"]
        result = review_method_plan(plan)
        self.assertTrue(result["historical_plan_ready"])
        self.assertFalse(result["feature_admitted"])

    def test_MR_arithmetic_inputs_do_not_require_N_EAF_but_identification_still_does(self):
        plan = abf_plan()
        plan["method"] = "mr_wald"
        for trait in plan["traits"]:
            trait["fields"] = ["beta", "se"]
        result = review_method_plan(plan)
        self.assertTrue(result["algorithm_plan_ready"])
        self.assertIn("identification_assumptions_reviewed_required", result["scientific_holds"])

    def test_correlated_IVW_never_silently_treats_cis_SNPs_as_independent(self):
        plan = abf_plan()
        plan["method"] = "mr_ivw"
        for trait in plan["traits"]:
            trait["fields"] = ["beta", "se"]
        self.assertIn("signed_correlation_LD_required", review_method_plan(plan)["algorithm_holds"])
        plan["instruments_independent"] = True
        self.assertTrue(review_method_plan(plan)["algorithm_plan_ready"])

    def test_even_passed_plan_assertions_do_not_admit_feature_or_run_analysis(self):
        plan = abf_plan()
        plan.update(independent_numeric_validation_passed=True,
                    source_and_scientific_review_evidence_verified=True)
        result = review_method_plan(plan)
        self.assertTrue(result["ready_for_independent_review"])
        self.assertFalse(result["feature_admitted"])
        self.assertFalse(result["genetics_computation_performed"])


if __name__ == "__main__":
    unittest.main()
