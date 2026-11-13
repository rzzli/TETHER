from __future__ import annotations

import json
import io
import shutil
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tether_engine.agents import ExtractiveBackend, ReplayBackend, Selection, Usage
from tether_engine.artifacts import verify_run, write_run
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case, Category, EvidencePacket, Profile, validate_observation
from tether_engine.evaluation import Outcome, Outcomes, add_months, evaluate
from tether_engine.ledger import EvidenceLedger
from tether_engine.scorer import ScorerArtifact
from tether_engine.serde import ContractError, decode, encode, parse_json, read_json, sha256_file, write_json
from tether_engine.workflow import BackendFailure, Budget, run_workflow


FIXTURES = Path(__file__).resolve().parents[1] / "src" / "tether_engine" / "demo" / "v2"


class RecordingBackend(ExtractiveBackend):
    def __init__(self, wrong_first=False, quoted_cost=0, actual_cost=0, failure=False):
        self.requests = []
        self.wrong_first = wrong_first
        self.quoted_cost = quoted_cost
        self.actual_cost = actual_cost
        self.failure = failure

    def quote(self, request):
        return Usage(0, 0, self.quoted_cost)

    def select(self, request):
        self.requests.append(request)
        if self.failure:
            raise BackendFailure("fixture failure", Usage(0, 0, self.actual_cost))
        if self.wrong_first and len(self.requests) == 1:
            return Selection(("unapproved-future-id",), Usage(0, 0, self.actual_cost))
        return Selection(tuple(item.observation_id for item in request.evidence),
                         Usage(0, 0, self.actual_cost))


class FrameworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fixture = self.root / "fixture"
        shutil.copytree(FIXTURES, self.fixture)
        self.case = decode(Case, read_json(self.fixture / "case.json"))
        self.model = decode(ScorerArtifact, read_json(self.fixture / "scorer.json"))

    def tearDown(self):
        self.temp.cleanup()

    def store(self, catalog=None):
        return load_snapshot(self.fixture / "snapshot.json", self.case, catalog)

    def edit_snapshot(self, change):
        document = read_json(self.fixture / "snapshot.json")
        change(document)
        write_json(self.fixture / "snapshot.json", document)

    def edit_packet(self, change):
        document = read_json(self.fixture / "evidence.json")
        change(document)
        write_json(self.fixture / "evidence.json", document)
        digest = sha256_file(self.fixture / "evidence.json")
        self.edit_snapshot(lambda doc: doc["artifacts"][0].update(sha256=digest))

    def historical_catalog(self, roles=("agent_evidence",)):
        path = self.fixture / "catalog.json"
        write_json(path, {"schema_version": 1,
                          "datasets": [{"dataset_id": "synthetic_fixture", "roles": roles}]})
        self.edit_snapshot(lambda doc: doc.update(profile="historical_benchmark"))
        snapshot = read_json(self.fixture / "snapshot.json")
        for node in snapshot["sources"]:
            source = self.fixture / node["path"]
            receipt_path = self.fixture / (node["source_id"] + "-receipt.json")
            write_json(receipt_path, {"status": "completed", "sha256": node["sha256"],
                      "dataset_id": node["dataset_id"], "release_id": node["release_id"],
                      "relative_path": node["path"], "bytes": source.stat().st_size,
                      "completed_at_utc": "2022-01-01T00:00:00+00:00"})
            node["receipt_path"] = receipt_path.name
            node["receipt_sha256"] = sha256_file(receipt_path)
        write_json(self.fixture / "snapshot.json", snapshot)
        return path

    def run_case(self, **kwargs):
        return run_workflow(self.case, self.store(), kwargs.pop("backend", ExtractiveBackend()),
                            kwargs.pop("model", self.model), **kwargs)

    def test_complete_offline_run_and_replay_are_equivalent(self):
        default = self.run_case()
        replayed = self.run_case(backend=ReplayBackend(self.fixture / "replay.json"))
        self.assertEqual(default.status, "completed")
        self.assertEqual(len(default.claims), 9)
        self.assertEqual(default.calls, 8)
        self.assertEqual(default.features, replayed.features)
        self.assertEqual(default.prediction, replayed.prediction)
        self.assertTrue(default.prediction.synthetic)
        self.assertAlmostEqual(default.prediction.probability, 0.48250714233361036)

    def test_future_canaries_are_not_in_any_backend_request_or_claim(self):
        backend = RecordingBackend()
        store = self.store()
        result = run_workflow(self.case, store, backend, self.model)
        requests = json.dumps(encode(backend.requests))
        self.assertNotIn("FUTURE_CANARY_SECRET", requests)
        self.assertNotIn("FUTURE_ARTIFACT_SECRET", requests)
        self.assertNotIn("FUTURE_CANARY_SECRET", json.dumps(encode(result)))
        self.assertEqual({entry.item_id for entry in store.exclusions},
                         {"demo-future", "demo-future-record"})

    def test_rejected_future_artifact_is_never_opened(self):
        (self.fixture / "future.json").unlink()
        self.assertEqual(len(self.store().source_proofs), 2)

    def test_later_annotation_of_old_observation_is_excluded(self):
        self.edit_packet(lambda doc: doc["observations"][0]["availability"].update(annotation_public_at="2025-01-01"))
        self.assertEqual(self.store().query(self.case, Category.GENETICS), ())

    def test_unknown_record_availability_is_excluded(self):
        self.edit_packet(lambda doc: doc["observations"][0]["availability"].update(record_public_at=None))
        self.assertEqual(self.store().query(self.case, Category.GENETICS), ())

    def test_year_precision_date_uses_conservative_upper_bound(self):
        self.edit_packet(lambda doc: doc["observations"][0]["availability"].update(record_public_at="2023-12-31"))
        self.assertEqual(self.store().query(self.case, Category.GENETICS), ())

    def test_retrieval_date_is_not_used_as_historical_availability(self):
        self.assertGreater(self.store().snapshot.artifacts[0].availability.retrieved_at, self.case.origin)
        self.assertEqual(len(self.store().query(self.case, Category.GENETICS)), 1)

    def test_contemporary_release_cannot_fill_historical_gap(self):
        catalog = self.historical_catalog()
        self.edit_snapshot(lambda doc: doc["sources"][0].update(temporal_classification="contemporary_only"))
        self.assertEqual(self.store(catalog).query(self.case, Category.GENETICS), ())

    def test_reconstructed_history_requires_explicit_approval(self):
        catalog = self.historical_catalog()
        self.edit_snapshot(lambda doc: doc["sources"][0].update(temporal_classification="reconstructed"))
        self.assertFalse(self.store(catalog).source_proofs)
        self.edit_snapshot(lambda doc: doc.update(allow_reconstructed=True))
        self.assertEqual(len(self.store(catalog).source_proofs), 2)

    def test_catalog_label_role_cannot_be_relabeled_agent_evidence(self):
        catalog = self.historical_catalog(("reference", "evaluation_only"))
        with self.assertRaisesRegex(ContractError, "Catalog denies"):
            self.store(catalog)

    def test_manifest_label_role_is_denied(self):
        self.edit_snapshot(lambda doc: doc["artifacts"][0].update(role="evaluation_only"))
        with self.assertRaisesRegex(ContractError, "artifact denied"):
            self.store()

    def test_real_snapshot_requires_catalog(self):
        self.historical_catalog()
        with self.assertRaisesRegex(ContractError, "require.*catalog"):
            self.store()

    def test_access_denied_preserves_explicit_exclusion(self):
        self.edit_snapshot(lambda doc: doc["artifacts"][0].update(access_approved=False))
        self.assertIn("access_denied", [entry.reason for entry in self.store().exclusions])

    def test_artifact_checksum_mismatch_fails(self):
        with (self.fixture / "evidence.json").open("a", encoding="utf-8") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(ContractError, "checksum mismatch"):
            self.store()

    def test_path_traversal_absolute_paths_and_ads_are_denied(self):
        original = read_json(self.fixture / "snapshot.json")
        for path in ("../outside.json", "D:/labels.json", "\\\\server\\share\\labels.json",
                     "evidence.json:secret", "./evidence.json"):
            with self.subTest(path=path):
                write_json(self.fixture / "snapshot.json", original)
                self.edit_snapshot(lambda doc: doc["artifacts"][0].update(path=path))
                with self.assertRaises(ContractError):
                    self.store()

    def test_duplicate_artifact_and_observation_ids_are_denied(self):
        self.edit_packet(lambda doc: doc["observations"][1].update(observation_id=doc["observations"][0]["observation_id"]))
        with self.assertRaisesRegex(ContractError, "Duplicate observation"):
            self.store()

    def test_wrong_target_and_program_are_not_retrieved(self):
        store = self.store()
        case = replace(self.case, hypothesis=replace(self.case.hypothesis, target_id="DEMO:OTHER"))
        self.assertFalse(store.query(case, Category.GENETICS))
        case = replace(self.case, program=replace(self.case.program, program_id="DEMO:OTHER"))
        self.assertFalse(store.query(case, Category.CLINICAL))

    def test_program_phase_eligibility_and_mapping_are_validated(self):
        for program in (replace(self.case.program, phase_at_origin=1),
                        replace(self.case.program, eligible_since=date(2024, 1, 1)),
                        replace(self.case.program, status_at_origin="unknown"),
                        replace(self.case.program, mapping_confidence=0)):
            with self.subTest(program=program):
                with self.assertRaises(ContractError):
                    replace(self.case, program=program).validate()

    def test_late_hypothesis_annotation_and_program_state_are_denied(self):
        for case in (replace(self.case, hypothesis=replace(self.case.hypothesis,
                         availability=replace(self.case.hypothesis.availability, annotation_public_at=date(2024, 1, 1)))),
                     replace(self.case, program=replace(self.case.program,
                         availability=replace(self.case.program.availability, record_public_at=date(2024, 1, 1))))):
            with self.subTest(case=case):
                with self.assertRaises(ContractError):
                    case.validate()

    def test_t6_audit_does_not_produce_clinical_probability(self):
        case = replace(self.case, task="T6", endpoint=None, program=None)
        result = run_workflow(case, self.store(), ExtractiveBackend(), self.model)
        self.assertEqual(result.prediction.status, "audit_only")
        self.assertIsNone(result.prediction.probability)

    def test_unknown_json_fields_bool_numbers_nan_and_duplicate_keys_are_denied(self):
        case = read_json(self.fixture / "case.json")
        case["outcome"] = 1
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            decode(Case, case)
        for payload in ('{"x": NaN}', '{"x": 1, "x": 2}'):
            with self.assertRaises(ContractError):
                parse_json(payload)
        with self.assertRaises(ContractError):
            decode(float, True)

    def test_clinical_features_cannot_leak_into_scoring(self):
        self.edit_packet(lambda doc: doc["observations"][5].update(features={"literature_support": 1.0}))
        with self.assertRaisesRegex(ContractError, "Clinical/known-drug"):
            self.store()

    def test_unobserved_and_failed_qc_cannot_create_features(self):
        for status in ("not_measured", "failed_qc", "access_denied", "outside_applicability", "absent"):
            packet = decode(EvidencePacket, read_json(self.fixture / "evidence.json"))
            observation = replace(packet.observations[0], status=type(packet.observations[0].status)(status))
            with self.subTest(status=status):
                with self.assertRaisesRegex(ContractError, "Unobserved"):
                    validate_observation(observation)

    def test_nonobserved_records_are_coverage_and_not_claims(self):
        result = self.run_case()
        self.assertEqual(result.coverage["perturbation"]["nonobserved"][0]["status"], "not_measured")
        self.assertNotIn("demo-perturbation-unmeasured", [claim.evidence.observation.observation_id for claim in result.claims])

    def test_write_time_ledger_denies_wrong_specialist_and_duplicates(self):
        ledger = EvidenceLedger(self.case, self.store())
        with self.assertRaises(ContractError):
            ledger.append(Category.CLINICAL, "demo-genetics-1")
        ledger.append(Category.GENETICS, "demo-genetics-1")
        with self.assertRaises(ContractError):
            ledger.append(Category.GENETICS, "demo-genetics-1")

    def test_dependency_group_deduplication_and_conflict(self):
        result = self.run_case()
        literature = result.features.values["literature_support"]
        self.assertEqual(literature.dependency_groups, 1)
        self.assertEqual(len(literature.observation_ids), 2)
        self.edit_packet(lambda doc: doc["observations"][8]["features"].update(literature_support=-0.4))
        feature = self.run_case().features.values["literature_support"]
        self.assertIsNone(feature.value)
        self.assertEqual(feature.status, "conflicting")
        self.assertEqual(feature.excluded_groups, ("demo-cohort-literature",))

    def test_shared_cohort_or_study_overrides_different_dependency_labels(self):
        self.edit_packet(lambda doc: doc["observations"][8].update(dependency_group="a-different-label"))
        result = self.run_case()
        self.assertEqual(result.features.values["literature_support"].dependency_groups, 1)
        self.edit_packet(lambda doc: doc["observations"][8].update(study_id="DIFFERENT:STUDY"))
        result = self.run_case()
        self.assertEqual(result.features.values["literature_support"].dependency_groups, 1)

    def test_missing_feature_is_null_and_triggers_abstention(self):
        result = self.run_case(disabled=(Category.GENETICS,))
        self.assertIsNone(result.features.values["genetic_support"].value)
        self.assertEqual(result.prediction.reason, "required_features_missing")

    def test_critic_retries_unsupported_selection_without_committing_it(self):
        backend = RecordingBackend(wrong_first=True)
        result = self.run_case(backend=backend)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.calls, 9)
        self.assertTrue(backend.requests[1].feedback)
        self.assertNotIn("unapproved-future-id", [claim.evidence.observation.observation_id for claim in result.claims])

    def test_no_review_ablation_preserves_grounding_gate(self):
        result = self.run_case(backend=RecordingBackend(wrong_first=True), review_enabled=False)
        self.assertEqual(result.status, "partial")
        self.assertIsNone(result.prediction.probability)
        self.assertEqual(result.coverage["genetics"]["status"], "failed")

    def test_budget_exhaustion_is_visible_and_probability_is_withheld(self):
        result = self.run_case(budget=Budget(max_calls=1))
        self.assertEqual(result.calls, 1)
        self.assertEqual(result.status, "budget_exhausted")
        self.assertEqual(result.prediction.reason, "run_incomplete")

    def test_cost_quote_denied_before_call_and_usage_overrun_detected(self):
        backend = RecordingBackend(quoted_cost=1, actual_cost=1)
        result = self.run_case(backend=backend)
        self.assertFalse(backend.requests)
        self.assertEqual(result.calls, 0)
        self.assertEqual(result.status, "budget_exhausted")
        result = self.run_case(backend=RecordingBackend(actual_cost=1))
        self.assertEqual(result.status, "budget_exhausted")
        self.assertEqual(result.usage.cost_usd, 1)

    def test_failed_adapter_usage_is_not_refunded(self):
        result = self.run_case(backend=RecordingBackend(quoted_cost=1, actual_cost=0.5, failure=True),
                               budget=Budget(max_cost_usd=1))
        self.assertGreater(result.usage.cost_usd, 0)
        self.assertIsNone(result.prediction.probability)

    def test_failed_call_with_usage_above_quote_stops_the_run(self):
        result = self.run_case(backend=RecordingBackend(quoted_cost=0, actual_cost=1, failure=True))
        self.assertEqual(result.status, "budget_exhausted")
        self.assertEqual(result.calls, 1)
        self.assertEqual(result.usage.cost_usd, 1)

    def test_negative_budget_and_out_of_range_imputation_are_rejected(self):
        with self.assertRaises(ContractError):
            self.run_case(budget=Budget(max_calls=-1))
        with self.assertRaises(ContractError):
            self.run_case(model=replace(self.model, missing_values={"safety_liability": -1}))

    def test_provider_request_has_no_paths_and_default_backend_has_no_network(self):
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            backend = RecordingBackend()
            result = self.run_case(backend=backend)
        self.assertEqual(result.status, "completed")
        self.assertNotIn(str(self.fixture), json.dumps(encode(backend.requests)))

    def test_no_scorer_means_no_invented_probability(self):
        result = self.run_case(model=None)
        self.assertEqual(result.prediction.reason, "no_frozen_scorer_configured")
        self.assertTrue(result.prediction.synthetic)

    def test_cli_replay_run_and_overwrite_rejection(self):
        from tether_engine.cli import main
        output = self.root / "cli-run"
        arguments = ["run", "--case", str(self.fixture / "case.json"),
                     "--snapshot", str(self.fixture / "snapshot.json"),
                     "--replay", str(self.fixture / "replay.json"), "--output", str(output)]
        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            self.assertEqual(main(arguments), 0)
            self.assertEqual(main(arguments), 2)
        prediction = read_json(output / "prediction.json")
        self.assertIsNone(prediction["probability"])
        self.assertTrue(prediction["synthetic"])

    def test_future_training_and_calibration_are_rejected(self):
        for model in (replace(self.model, training_label_available_max=self.case.origin),
                      replace(self.model, calibration="held_out_logistic", calibration_label_available_max=date(2024, 1, 1))):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ContractError, "Training/calibration"):
                    self.run_case(model=model)

    def test_demo_weights_are_denied_on_real_snapshot(self):
        catalog = self.historical_catalog()
        store = self.store(catalog)
        with self.assertRaisesRegex(ContractError, "Synthetic weights"):
            run_workflow(self.case, store, ExtractiveBackend(), self.model)

    def test_scorer_applicability_and_explicit_imputation(self):
        self.assertEqual(self.run_case(model=replace(self.model, modalities=("antibody",))).prediction.reason,
                         "outside_scorer_applicability")
        model = replace(self.model, missing_values={"literature_support": 0.25})
        result = self.run_case(model=model, disabled=(Category.LITERATURE,))
        contribution = result.prediction.contributions["literature_support"]
        self.assertTrue(contribution.imputed)
        self.assertEqual(contribution.value, 0.25)
        self.assertEqual(contribution.observation_ids, ())

    def test_actual_score_contribution_changes_when_evidence_is_removed(self):
        full = self.run_case()
        model = replace(self.model, missing_values={"literature_support": 0})
        ablated = self.run_case(model=model, disabled=(Category.LITERATURE,))
        self.assertLess(ablated.prediction.probability, full.prediction.probability)

    def test_run_receipt_integrity_and_external_anchor(self):
        store = self.store()
        result = run_workflow(self.case, store, ExtractiveBackend(), self.model)
        output = self.root / "run"
        digest = write_run(output, result, store, self.model)
        check = verify_run(output, digest)
        self.assertEqual(check["outputs"], 8)
        self.assertTrue(check["external_anchor_checked"])
        with self.assertRaises(FileExistsError):
            write_run(output, result, store, self.model)
        (output / "prediction.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "integrity failure"):
            verify_run(output, digest)

    def test_source_tampering_is_detected_and_outputs_only_is_explicit(self):
        store = self.store()
        output = self.root / "run"
        write_run(output, run_workflow(self.case, store, ExtractiveBackend(), self.model), store, self.model)
        (self.fixture / "evidence.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "Source integrity"):
            verify_run(output)
        self.assertEqual(verify_run(output, verify_sources=False)["source_artifacts_checked"], 0)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        case = decode(Case, read_json(FIXTURES / "case.json"))
        store = load_snapshot(FIXTURES / "snapshot.json", case)
        model = decode(ScorerArtifact, read_json(FIXTURES / "scorer.json"))
        self.base = run_workflow(case, store, ExtractiveBackend(), model).prediction
        self.freeze = date(2026, 1, 1)

    def pair(self, values=(0.1, 0.9)):
        predictions = tuple(replace(self.base, case_id=f"case-{i}", probability=value) for i, value in enumerate(values))
        rows = tuple(Outcome(f"case-{i}", date(2023, 1, 1), "phase_2_to_3", 24, "resolved", i,
                             date(2024, 1, 1) if i else None, date(2025, 1, 1), date(2025, 2, 1), f"cluster-{i}")
                     for i in range(2))
        return predictions, Outcomes(1, self.freeze, rows)

    def test_descriptive_metrics_and_ties(self):
        predictions, labels = self.pair()
        result = evaluate(predictions, labels, True)
        self.assertEqual(result["auroc"], 1)
        self.assertEqual(result["average_precision"], 1)
        self.assertAlmostEqual(result["brier"], 0.01)
        predictions, labels = self.pair((0.5, 0.5))
        result = evaluate(predictions, labels, True)
        self.assertEqual(result["auroc"], 0.5)
        self.assertEqual(result["average_precision"], 0.5)

    def test_unresolved_and_abstained_cases_report_coverage(self):
        predictions, labels = self.pair()
        labels = replace(labels, outcomes=(replace(labels.outcomes[0], status="censored", value=None), labels.outcomes[1]))
        result = evaluate(predictions, labels, True)
        self.assertEqual(result["coverage"], 0.5)
        self.assertIsNone(result["auroc"])
        predictions = (predictions[0], replace(predictions[1], status="abstained", probability=None))
        self.assertEqual(evaluate(predictions, labels, True)["coverage"], 0)

    def test_negative_labels_need_full_followup_and_censoring_cannot_be_failure(self):
        predictions, labels = self.pair()
        for row in (replace(labels.outcomes[0], observed_until=date(2024, 1, 1)),
                    replace(labels.outcomes[0], status="censored"),
                    replace(labels.outcomes[0], label_available_at=date(2024, 1, 1))):
            with self.subTest(row=row):
                with self.assertRaises(ContractError):
                    evaluate(predictions, replace(labels, outcomes=(row, labels.outcomes[1])), True)

    def test_label_freeze_future_positive_and_endpoint_mismatch_are_rejected(self):
        predictions, labels = self.pair()
        for row in (replace(labels.outcomes[1], event_at=date(2026, 1, 1)),
                    replace(labels.outcomes[1], event_at=None),
                    replace(labels.outcomes[1], label_available_at=date(2027, 1, 1)),
                    replace(labels.outcomes[1], endpoint="phase_1_to_2")):
            with self.subTest(row=row):
                with self.assertRaises(ContractError):
                    evaluate(predictions, replace(labels, outcomes=(labels.outcomes[0], row)), True)

    def test_missing_cases_duplicates_and_synthetic_without_opt_in_are_rejected(self):
        predictions, labels = self.pair()
        with self.assertRaises(ContractError):
            evaluate(predictions, labels)
        with self.assertRaises(ContractError):
            evaluate(predictions[:1], labels, True)
        with self.assertRaises(ContractError):
            evaluate((predictions[0], predictions[0]), labels, True)

    def test_horizon_calendar_arithmetic(self):
        self.assertEqual(add_months(date(2024, 1, 31), 1), date(2024, 2, 29))
        self.assertEqual(add_months(date(2024, 2, 29), 12), date(2025, 2, 28))

    def test_cli_raw_evaluator_round_trip_is_explicitly_unverified(self):
        from tether_engine.cli import main
        predictions, labels = self.pair()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i, prediction in enumerate(predictions):
                write_json(root / f"prediction-{i}.json", prediction)
            write_json(root / "outcomes.json", labels)
            arguments = ["evaluate-raw", "--predictions", str(root / "prediction-0.json"),
                         str(root / "prediction-1.json"), "--labels", str(root / "outcomes.json"),
                         "--output", str(root / "metrics.json"), "--allow-synthetic"]
            with patch("sys.stdout", io.StringIO()):
                self.assertEqual(main(arguments), 0)
            self.assertEqual(read_json(root / "metrics.json")["auroc"], 1)
            self.assertEqual(read_json(root / "metrics.json")["prediction_provenance"],
                             "not_checked_by_metrics_function")

    def test_production_evaluator_rejects_bare_unbound_predictions(self):
        from tether_engine.cli import main
        predictions, labels = self.pair()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i, prediction in enumerate(predictions):
                write_json(root / f"prediction-{i}.json", prediction)
            write_json(root / "outcomes.json", labels)
            arguments = ["evaluate", "--predictions", str(root / "prediction-0.json"),
                         str(root / "prediction-1.json"), "--labels", str(root / "outcomes.json"),
                         "--output", str(root / "metrics.json"), "--allow-synthetic"]
            with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
                with self.assertRaises(SystemExit) as rejected:
                    main(arguments)
            self.assertEqual(rejected.exception.code, 2)
            self.assertFalse((root / "metrics.json").exists())


if __name__ == "__main__":
    unittest.main()

