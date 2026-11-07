"""Scientific leakage and no-fit regressions, using synthetic plan declarations."""
from copy import deepcopy
import unittest

from tools.science.scoring_qualification import review_scoring_plan


def pin(identity):
    return {"artifact_id": identity, "sha256": "a" * 64}


def ancestor(identity, kind, available="2022-01-01T00:00:00Z"):
    return dict(pin(identity), kind=kind, role="reference", available_by=available,
                current_fallback=False)


def qualified_declaration():
    plan = {
        "endpoint_id": "clinical_success", "test_origin_at": "2025-01-01T00:00:00Z",
        "output_mode": "probability", "test_outcomes_accessed": False,
        "predictor_bundle_qualified": True, "uses_genetics": False,
        "genetics_method_qualified": False,
        "feature_schema": dict(pin("schema-v1"), columns=["historical_evidence_count"],
            frozen_before_test_outcomes=True, selection_used_test_outcomes=False,
            scientific_model_roles=[]),
        "derivation": dict(pin("recipe-v1"), deterministic=True,
            same_recipe_all_partitions=True, no_later_information=True,
            computed_at="2026-10-20T00:00:00Z"),
        "split_manifest": dict(pin("split-v1"), frozen_before_fitting=True,
            dependence_graph_qualified=True),
        "preprocessing": dict(pin("preprocess-v1"), fit_partitions=["train"],
            selection_and_transforms_train_only=True),
        "scorer_spec": dict(pin("scorer-spec-v1"), estimator_id="prespecified_estimator",
            hyperparameters_frozen=True, selection_used_test_outcomes=False),
        "calibration": dict(pin("calibration-v1"), fit_partitions=["calibration"], method_frozen=True),
        "scientific_design": {"training_cohort_qualified": True, "sample_adequacy_qualified": True,
            "dependence_qualified": True, "discrimination_power_qualified": True,
            "calibration_precision_qualified": True},
        "independent_payload_and_design_review_passed": True, "rows": [],
    }
    for partition, year in (("train", 2023), ("calibration", 2024), ("test", 2025)):
        for index in (0, 1):
            identity = f"{partition}-{index}"
            row = {"row_id": identity, "program_id": identity,
                "dependence_component_id": identity, "partition": partition,
                "origin_at": f"{year}-01-01T00:00:00Z", "features_qualified": True,
                "complete_feature_lineage": True,
                "ancestors": [ancestor("old-source-v1", "source"), ancestor("old-mapping-v1", "mapping")],
                "models": [], "label": None}
            if partition != "test":
                row["label"] = dict(pin(identity + "-label"), status="qualified_binary", value=index,
                    purpose="training_label" if partition == "train" else "calibration_label",
                    source_role="evaluation_only", endpoint_id="clinical_success",
                    ascertainment_qualified=True, horizon_at=f"{year}-10-01T00:00:00Z",
                    available_by=f"{year}-12-01T00:00:00Z", complete_label_lineage=True,
                    sources=[dict(pin(identity + "-outcome-source"), role="evaluation_only",
                                  available_by=f"{year}-12-01T00:00:00Z")])
            plan["rows"].append(row)
    return plan


def qwen_model(released="2024-09-19T00:00:00Z"):
    return dict(pin("Qwen2.5-exact-release"), scientific_role="feature_generator",
        revision="b" * 40, released_by=released,
        assets=[dict(ancestor("qwen-" + kind, kind, released), kind=kind) for kind in ("weights", "tokenizer", "config")]
               + [dict(pin("qwen-runtime"), kind="runtime", role="execution_runtime",
                       information_bearing=False, scientific_adaptation=False,
                       available_by="2026-10-20T00:00:00Z")],
        complete_adaptation_lineage=True, adaptations=[])


class ScoringQualificationTests(unittest.TestCase):
    def test_evaluator_only_bytes_cannot_reappear_as_predictor_under_same_identity(self):
        plan = qualified_declaration()
        plan['rows'][0]['label']['sources'][0].update(
            artifact_id='old-source-v1', available_by='2022-01-01T00:00:00Z')
        self.assertFalse(review_scoring_plan(plan)['ready_for_independent_review'])

    def test_extra_role_key_cannot_shadow_evaluator_only_label_source_role(self):
        plan = qualified_declaration()
        plan['rows'][0]['label'].update(artifact_id='old-source-v1', role='reference')
        self.assertFalse(review_scoring_plan(plan)['ready_for_independent_review'])

    def test_extra_information_bearing_model_asset_kind_cannot_escape_chronology(self):
        plan = qualified_declaration()
        plan['feature_schema']['scientific_model_roles'] = ['feature_generator']
        for row in plan['rows']:
            model = qwen_model()
            model['released_by'] = '2022-01-01T00:00:00Z'
            for asset in model['assets']:
                if asset['kind'] != 'runtime':
                    asset['available_by'] = '2022-01-01T00:00:00Z'
            row['models'] = [model]
        self.assertTrue(review_scoring_plan(plan)['ready_for_independent_review'])
        plan['rows'][0]['models'][0]['assets'].append(
            ancestor('future-prompt', 'prompt', '2026-01-01T00:00:00Z'))
        self.assertFalse(review_scoring_plan(plan)['ready_for_independent_review'])

    def test_qualified_declarations_allow_review_never_training_or_probability(self):
        result = review_scoring_plan(qualified_declaration())
        self.assertTrue(result["ready_for_independent_review"], result["holds"])
        self.assertFalse(result["fit_allowed"])
        self.assertEqual(0, result["trained_models"] + result["calibrated_models"] + result["probabilities_emitted"])

    def test_genetics_is_optional_for_non_genetic_route(self):
        plan = qualified_declaration()
        self.assertTrue(review_scoring_plan(plan)["ready_for_independent_review"])
        plan["uses_genetics"] = True
        self.assertIn("genetics_gate_required_only_when_genetics_used", review_scoring_plan(plan)["holds"]["science"])

    def test_missing_bundle_and_unknown_training_inventory_produce_no_fit(self):
        plan = qualified_declaration()
        plan["predictor_bundle_qualified"] = False
        plan["rows"] = []
        result = review_scoring_plan(plan)
        self.assertEqual("no_fit", result["decision"])
        self.assertIn("qualified_training_calibration_test_rows_not_supplied", result["holds"]["scope"])

    def test_later_deterministic_computation_is_permitted_later_knowledge_is_not(self):
        plan = qualified_declaration()
        self.assertTrue(review_scoring_plan(plan)["ready_for_independent_review"])
        plan["rows"][0]["ancestors"][1]["available_by"] = "2026-01-01T00:00:00Z"
        self.assertIn("row_0:ancestor_1:knowledge_after_row_origin", review_scoring_plan(plan)["holds"]["chronology"])
        plan = qualified_declaration()
        plan["derivation"]["no_later_information"] = False
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])

    def test_Qwen_Sep2024_is_too_late_for_2023_but_can_qualify_for_Jan2025(self):
        plan = qualified_declaration()
        plan["feature_schema"]["scientific_model_roles"] = ["feature_generator"]
        for row in plan["rows"]:
            row["models"] = [qwen_model()]
        result = review_scoring_plan(plan)
        self.assertIn("row_0:model_0:model_release_not_qualified_at_row_origin", result["holds"]["models"])
        self.assertFalse(any(reason.startswith("row_4:") for reason in result["holds"]["models"]))

    def test_all_scientific_model_roles_assets_and_adaptations_must_qualify(self):
        plan = qualified_declaration()
        plan["feature_schema"]["scientific_model_roles"] = ["feature_generator"]
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])
        for row in plan["rows"]:
            model = qwen_model("2022-01-01T00:00:00Z")
            row["models"] = [model]
        self.assertTrue(review_scoring_plan(plan)["ready_for_independent_review"])
        plan["rows"][0]["models"][0]["adaptations"] = [ancestor("future-adapter", "adaptation", "2026-01-01T00:00:00Z")]
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])
        plan = qualified_declaration()
        model = qwen_model(); model["assets"].pop(); model["revision"] = "main"
        plan["rows"][4]["models"] = [model]
        holds = review_scoring_plan(plan)["holds"]["models"]
        self.assertIn("row_4:model_0:complete_model_assets_required", holds)
        self.assertIn("row_4:model_0:immutable_revision_required", holds)

    def test_old_model_release_cannot_hide_new_or_evaluator_only_weights_tokenizer_config(self):
        for kind in ("weights", "tokenizer", "config"):
            for field, value in (("available_by", "2026-01-01T00:00:00Z"),
                                 ("role", "evaluation_only"), ("available_by", None),
                                 ("current_fallback", True)):
                plan = qualified_declaration()
                plan["feature_schema"]["scientific_model_roles"] = ["feature_generator"]
                for row in plan["rows"]:
                    row["models"] = [qwen_model("2022-01-01T00:00:00Z")]
                asset = next(a for a in plan["rows"][0]["models"][0]["assets"] if a["kind"] == kind)
                asset[field] = value
                self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"], (kind, field))

    def test_late_non_scientific_runtime_and_late_deterministic_weight_conversion_are_permitted(self):
        plan = qualified_declaration()
        plan["feature_schema"]["scientific_model_roles"] = ["feature_generator"]
        for row in plan["rows"]:
            row["models"] = [qwen_model("2022-01-01T00:00:00Z")]
            row["models"][0]["assets"][0]["converted_at"] = "2026-10-20T00:00:00Z"
        self.assertTrue(review_scoring_plan(plan)["ready_for_independent_review"])
        runtime = plan["rows"][0]["models"][0]["assets"][-1]
        runtime["scientific_adaptation"] = True
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])
        runtime["scientific_adaptation"] = False
        runtime["role"] = "evaluation_only"
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])

    def test_feature_identity_hash_role_mapping_and_unknown_availability_fail_closed(self):
        for key in ("artifact_id", "sha256", "role", "available_by"):
            plan = qualified_declaration()
            del plan["rows"][0]["ancestors"][0][key]
            self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"], key)
        plan = qualified_declaration()
        plan["rows"][0]["ancestors"] = plan["rows"][0]["ancestors"][:1]
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])

    def test_evaluator_interpretation_is_not_a_feature_but_mature_labels_can_be(self):
        plan = qualified_declaration()
        self.assertTrue(review_scoring_plan(plan)["ready_for_independent_review"])
        plan["rows"][0]["ancestors"][0]["role"] = "evaluation_only"
        self.assertIn("row_0:ancestor_0:predictor_role_required", review_scoring_plan(plan)["holds"]["features"])

    def test_old_event_with_later_public_label_cannot_train_Jan2025_model(self):
        plan = qualified_declaration()
        plan["rows"][0]["label"]["available_by"] = "2026-01-01T00:00:00Z"
        self.assertIn("row_0:label_not_available_before_test_origin", review_scoring_plan(plan)["holds"]["chronology"])
        plan["rows"][0]["label"]["available_by"] = plan["test_origin_at"]
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])

    def test_unresolved_labels_never_become_negative_or_qualified_classes(self):
        plan = qualified_declaration()
        for row in plan["rows"]:
            if row["label"] is not None:
                row["label"].update(status="unresolved", value=None)
        result = review_scoring_plan(plan)
        self.assertEqual({"negative": 0, "positive": 0}, result["declared_class_counts"]["train"])
        self.assertEqual("no_fit", result["decision"])
        plan["rows"][0]["label"].update(status="qualified_binary", value=False)
        self.assertIn("row_0:qualified_binary_label_required", review_scoring_plan(plan)["holds"]["labels"])

    def test_endpoint_label_identity_and_maturity_are_not_assumed(self):
        for mutation in ({"endpoint_id": "registry_next_phase_actual_start"}, {"sha256": None},
                         {"purpose": "predictor"}, {"source_role": "reference"},
                         {"ascertainment_qualified": False}, {"horizon_at": "2024-12-02T00:00:00Z"}):
            plan = qualified_declaration()
            plan["rows"][2]["label"].update(mutation)
            self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"], mutation)

    def test_label_source_lineage_cannot_hide_later_knowledge_behind_old_label_date(self):
        plan = qualified_declaration()
        plan["rows"][0]["label"]["sources"][0]["available_by"] = "2026-01-01T00:00:00Z"
        holds = review_scoring_plan(plan)["holds"]["chronology"]
        self.assertIn("row_0:label_source_0:source_not_available_before_test_origin", holds)
        self.assertIn("row_0:label_source_0:source_after_declared_label_availability", holds)
        for key in ("artifact_id", "sha256", "role", "available_by"):
            plan = qualified_declaration()
            del plan["rows"][0]["label"]["sources"][0][key]
            self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"], key)

    def test_program_and_dependence_leakage_detected_even_when_flags_say_qualified(self):
        for field in ("program_id", "dependence_component_id"):
            plan = qualified_declaration()
            plan["rows"][2][field] = plan["rows"][0][field]
            self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])
        plan = qualified_declaration()
        plan["rows"][1]["row_id"] = plan["rows"][0]["row_id"]
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])

    def test_train_only_preprocessing_and_separate_calibration_are_required(self):
        plan = qualified_declaration()
        plan["preprocessing"]["fit_partitions"] = ["train", "test"]
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])
        plan = qualified_declaration()
        plan["calibration"]["fit_partitions"] = ["train", "calibration"]
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])
        plan = qualified_declaration()
        plan["scorer_spec"]["selection_used_test_outcomes"] = True
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])

    def test_discrimination_design_does_not_certify_calibration_precision(self):
        plan = qualified_declaration()
        plan["scientific_design"]["calibration_precision_qualified"] = False
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])
        plan["output_mode"] = "rank_only"
        self.assertTrue(review_scoring_plan(plan)["ready_for_independent_review"])

    def test_test_outcomes_cannot_select_schema_or_enter_development(self):
        for field in ("test_outcomes_accessed",):
            plan = qualified_declaration(); plan[field] = True
            self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])
        plan = qualified_declaration(); plan["rows"][4]["label"] = deepcopy(plan["rows"][0]["label"])
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])
        plan = qualified_declaration(); plan["feature_schema"]["selection_used_test_outcomes"] = True
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])

    def test_conflicting_source_hash_and_current_mapping_fallback_are_held(self):
        plan = qualified_declaration()
        plan["rows"][1]["ancestors"][0]["sha256"] = "b" * 64
        self.assertIn("row_1:ancestor_0:conflicting_identity_hash", review_scoring_plan(plan)["holds"]["features"])
        plan = qualified_declaration()
        plan["rows"][0]["ancestors"][1]["current_fallback"] = True
        self.assertFalse(review_scoring_plan(plan)["ready_for_independent_review"])


if __name__ == "__main__":
    unittest.main()
