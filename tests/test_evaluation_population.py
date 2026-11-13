"""Fixed-horizon risk-set regressions; all examples are artificial contract tests."""

from dataclasses import replace
from datetime import date, datetime, timezone
import unittest

import tether_engine.evaluation as evaluation
from tether_engine.evaluation import Outcome, Outcomes, add_months, evaluate
from tether_engine.scorer import Prediction
from tether_engine.serde import ContractError


class EvaluationPopulationTests(unittest.TestCase):
    def row(self, key="case", *, value=0, status="resolved", p=0.2,
            origin=date(2023, 1, 1), months=24, event=None,
            observed=date(2025, 1, 1), available=date(2025, 1, 2)):
        if event is None and value == 1:
            event = date(2024, 1, 1)
        outcome = Outcome(key, origin, "phase_2_to_3", months, status, value, event,
                          observed, available, "cluster-" + key)
        prediction = Prediction(key, origin, "phase_2_to_3", months,
                                "abstained" if p is None else "scored", p,
                                None, "fixture", False, None, None, None, {})
        return prediction, outcome

    def run_rows(self, rows, *, freeze=date(2026, 1, 1), policy=None):
        predictions = tuple(row[0] for row in rows)
        labels = Outcomes(1, freeze, tuple(row[1] for row in rows))
        if policy is None:
            return evaluate(predictions, labels)
        return evaluate(predictions, labels, policy=policy)

    def policy(self, *, months=24, lag=0, endpoint="phase_2_to_3"):
        return evaluation.EvaluationPolicy(1, endpoint, months, lag)

    def test_early_positives_do_not_create_an_immature_cohort(self):
        rows = [self.row(str(i), value=1 if i < 3 else None,
                         status="resolved" if i < 3 else "censored", months=36,
                         event=date(2023, 6, 1) if i < 3 else None,
                         observed=date(2024, 1, 1), available=date(2024, 1, 1))
                for i in range(10)]
        result = self.run_rows(rows, freeze=date(2024, 1, 1))
        self.assertIsNone(result["brier"])
        self.assertIsNone(result["average_precision"])
        self.assertEqual(result["metric_status"], "no_mature_cases")
        self.assertEqual(result["denominators"]["registered"], 10)
        self.assertEqual(result["denominators"]["mature"], 0)
        self.assertEqual(result["denominators"]["registered_prediction_available"], 10)
        self.assertEqual(result["brier_completion_bounds"]["cases"], 0)
        self.assertIsNone(result["brier_completion_bounds"]["lower"])
        self.assertEqual(len(result["case_states"]), 10)

    def test_maturity_is_independent_of_the_observed_label(self):
        mature = self.row("old", value=0)
        early = self.row("young", value=1, origin=date(2024, 7, 1),
                         event=date(2024, 8, 1), observed=date(2025, 1, 1))
        unknown = (early[0], replace(early[1], value=None, status="censored", event_at=None))
        positive_result = self.run_rows([mature, early])
        unknown_result = self.run_rows([mature, unknown])
        self.assertAlmostEqual(positive_result["brier"], 0.04)
        self.assertEqual(positive_result["populations"]["mature_case_ids"], ["old"])
        self.assertEqual(positive_result["population_fingerprint"], unknown_result["population_fingerprint"])
        self.assertEqual(positive_result["brier"], unknown_result["brier"])

    def test_reporting_lag_boundary_is_applied_to_every_label(self):
        rows = [self.row("negative"), self.row("positive", value=1)]
        policy = self.policy(lag=30)
        before = self.run_rows(rows, freeze=date(2025, 1, 30), policy=policy)
        at = self.run_rows(rows, freeze=date(2025, 1, 31), policy=policy)
        self.assertEqual(before["denominators"]["mature"], 0)
        self.assertEqual(at["denominators"]["mature"], 2)
        self.assertEqual(at["metric_status"], "complete")
        self.assertEqual(at["policy_source"], "explicit")

    def test_mature_early_positive_need_not_be_observed_after_irreversible_event(self):
        result = self.run_rows([self.row(value=1, p=0.8, event=date(2023, 8, 1),
                                         observed=date(2023, 8, 1), available=date(2023, 8, 2))],
                               policy=self.policy(lag=90))
        self.assertEqual(result["metric_status"], "complete")
        self.assertAlmostEqual(result["brier"], 0.04)

    def test_unknown_labels_withhold_primary_and_preserve_independent_prediction_count(self):
        rows = [self.row("known", value=1, p=0.8),
                self.row("unknown", value=None, status="unresolved", p=0.2)]
        result = self.run_rows(rows)
        self.assertIsNone(result["brier"])
        self.assertIsNone(result["average_precision"])
        self.assertEqual(result["metric_status"], "incomplete_labels")
        self.assertEqual(result["denominators"]["resolved"], 1)
        self.assertEqual(result["denominators"]["prediction_available"], 2)
        self.assertEqual(result["populations"]["prediction_available_case_ids"], ["known", "unknown"])
        self.assertAlmostEqual(result["conditional_metrics"]["brier"], 0.04)
        bounds = result["brier_completion_bounds"]
        self.assertEqual(bounds["cases"], 2)
        self.assertAlmostEqual(bounds["lower"], 0.04)
        self.assertAlmostEqual(bounds["upper"], 0.34)

    def test_prediction_missingness_is_retained_in_the_common_universe(self):
        rows = [self.row("known", value=1, p=0.8), self.row("abstained", p=None),
                self.row("unknown", value=None, status="censored", p=None)]
        result = self.run_rows(rows)
        self.assertEqual(result["denominators"]["mature"], 3)
        self.assertEqual(result["denominators"]["missing_predictions"], 2)
        self.assertEqual(result["denominators"]["prediction_available"], 1)
        self.assertEqual(result["denominators"]["resolved"], 2)
        self.assertAlmostEqual(result["brier_completion_bounds"]["lower"], 0.04 / 3)
        self.assertAlmostEqual(result["brier_completion_bounds"]["upper"], 2.04 / 3)
        states = {row["case_id"]: row for row in result["case_states"]}
        self.assertEqual(set(states["unknown"]["exclusion_reasons"]),
                         {"censored", "prediction_abstained_or_failed"})

    def test_two_arms_cannot_hide_different_failed_cases(self):
        rows = [self.row("a", value=0), self.row("b", value=1)]
        first = [(replace(rows[0][0], status="abstained", probability=None), rows[0][1]), rows[1]]
        second = [rows[0], (replace(rows[1][0], status="abstained", probability=None), rows[1][1])]
        left, right = self.run_rows(first), self.run_rows(second)
        self.assertEqual(left["metric_status"], "incomplete_predictions")
        self.assertEqual(left["population_fingerprint"], right["population_fingerprint"])
        self.assertEqual(left["populations"]["mature_case_ids"], right["populations"]["mature_case_ids"])
        self.assertNotEqual(left["populations"]["scored_case_ids"], right["populations"]["scored_case_ids"])
        self.assertIsNone(left["brier"])
        self.assertIsNone(right["brier"])

    def test_duplicate_missing_and_extra_members_are_errors(self):
        a, b = self.row("a"), self.row("b")
        labels = Outcomes(1, date(2026, 1, 1), (a[1], b[1]))
        for predictions in ((a[0],), (a[0], a[0]), (a[0], b[0], replace(b[0], case_id="extra"))):
            with self.subTest(predictions=predictions), self.assertRaises(ContractError):
                evaluate(predictions, labels)
        with self.assertRaises(ContractError):
            evaluate((a[0],), replace(labels, outcomes=(a[1], a[1])))

    def test_invalid_negative_followup_and_contradictory_events_are_errors(self):
        p, row = self.row()
        for changed in (replace(row, observed_until=date(2024, 1, 1)),
                        replace(row, label_available_at=date(2024, 1, 1)),
                        replace(row, event_at=date(2024, 1, 1))):
            with self.subTest(row=changed), self.assertRaises(ContractError):
                self.run_rows([(p, changed)])

    def test_positive_event_boundaries_and_later_negative_event(self):
        p, row = self.row(value=1)
        for event in (row.origin, date(2025, 1, 2)):
            with self.subTest(event=event), self.assertRaises(ContractError):
                self.run_rows([(p, replace(row, event_at=event))])
        at = self.run_rows([(p, replace(row, event_at=date(2025, 1, 1)))])
        self.assertEqual(at["denominators"]["mature_positive"], 1)
        later = self.row(value=0, event=date(2025, 2, 1), observed=date(2025, 3, 1),
                         available=date(2025, 3, 1))
        self.assertEqual(self.run_rows([later])["denominators"]["mature_negative"], 1)

    def test_future_information_is_rejected_even_for_an_immature_case(self):
        p, row = self.row(months=36, value=None, status="censored",
                          observed=date(2024, 1, 1), available=date(2024, 1, 1))
        for changed in (replace(row, observed_until=date(2024, 1, 2)),
                        replace(row, label_available_at=date(2024, 1, 2))):
            with self.subTest(row=changed), self.assertRaises(ContractError):
                self.run_rows([(p, changed)], freeze=date(2024, 1, 1))

    def test_numeric_type_bypasses_are_rejected_before_maturity_filtering(self):
        p, row = self.row(months=36, value=None, status="censored",
                          observed=date(2024, 1, 1), available=date(2024, 1, 1))
        for probability in (True, False, float("nan"), float("inf"), -float("inf"), "0.5", -0.1, 1.1):
            with self.subTest(probability=probability), self.assertRaises(ContractError):
                self.run_rows([(replace(p, probability=probability), row)], freeze=date(2024, 1, 1))
        for value in (True, False, 0.0, 1.0, "1"):
            p, row = self.row(value=1)
            with self.subTest(value=value), self.assertRaises(ContractError):
                self.run_rows([(p, replace(row, value=value))])

    def test_prediction_status_probability_pairs_are_consistent(self):
        p, row = self.row()
        for status, probability in (("scored", None), ("abstained", 0.2),
                                    ("failed", 0.2), ("unknown", None)):
            with self.subTest(status=status, probability=probability), self.assertRaises(ContractError):
                self.run_rows([(replace(p, status=status, probability=probability), row)])

    def test_failure_reason_and_declared_abstention_remain_distinguishable(self):
        failed, abstained = self.row("failed", p=None), self.row("abstained", p=None)
        failed = (replace(failed[0], status="failed", reason="timeout"), failed[1])
        abstained = (replace(abstained[0], reason="insufficient_evidence"), abstained[1])
        result = self.run_rows([failed, abstained])
        states = {row["case_id"]: row for row in result["case_states"]}
        self.assertEqual(states["failed"]["prediction_status"], "failed")
        self.assertEqual(states["failed"]["prediction_reason"], "timeout")
        self.assertEqual(states["abstained"]["prediction_reason"], "insufficient_evidence")
        self.assertEqual(result["denominators"]["missing_predictions"], 2)

    def test_mixed_endpoint_or_horizon_is_not_one_analysis(self):
        first, second = self.row("a"), self.row("b")
        for field, value in (("endpoint", "phase_1_to_2"), ("horizon_months", 12)):
            changed = (replace(second[0], **{field: value}), replace(second[1], **{field: value}))
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.run_rows([first, changed])

    def test_policy_and_date_types_fail_closed(self):
        for months, lag in ((True, 0), (24.0, 0), (0, 0), (-1, 0),
                            (24, True), (24, -1), (24, 0.5), (24, 10**30)):
            with self.subTest(months=months, lag=lag), self.assertRaises(ContractError):
                self.run_rows([self.row()], policy=self.policy(months=months, lag=lag))
        p, row = self.row()
        for changed in (replace(row, origin="2023-01-01"),
                        replace(row, observed_until=datetime(2025, 1, 1, tzinfo=timezone.utc)),
                        replace(row, label_available_at=None), replace(row, cluster_id=" "),
                        replace(row, horizon_months=True)):
            with self.subTest(row=changed), self.assertRaises(ContractError):
                self.run_rows([(p, changed)])
        with self.assertRaises(ContractError):
            evaluate((p,), Outcomes(True, date(2026, 1, 1), (row,)))

    def test_calendar_arithmetic_is_exact_and_bounded(self):
        self.assertEqual(add_months(date(2024, 1, 31), 1), date(2024, 2, 29))
        self.assertEqual(add_months(date(2024, 2, 29), 12), date(2025, 2, 28))
        for months in (True, 1.0, "12", 0, -1, 10**30):
            with self.subTest(months=months), self.assertRaises(ContractError):
                add_months(date(2024, 1, 31), months)
        with self.assertRaises(ContractError):
            add_months(date(9999, 12, 31), 1)

    def test_tied_ranking_metrics_match_pairwise_reference_and_ignore_order(self):
        values = [(0, 0.2), (1, 0.5), (0, 0.5), (1, 0.5), (1, 0.9), (0, 0.9)]
        rows = [self.row(str(i), value=y, p=p) for i, (y, p) in enumerate(values)]
        result = self.run_rows(rows)
        reversed_result = self.run_rows(rows[::-1])
        positives = [p for y, p in values if y]
        negatives = [p for y, p in values if not y]
        expected_auc = sum((p > n) + 0.5 * (p == n) for p in positives for n in negatives) / 9
        expected_ap = (1 / 3) * (1 / 2) + (2 / 3) * (3 / 5)
        self.assertAlmostEqual(result["auroc"], expected_auc)
        self.assertAlmostEqual(result["average_precision"], expected_ap)
        self.assertEqual(result, reversed_result)

    def test_single_class_and_empty_populations_do_not_invent_auc(self):
        positives = self.run_rows([self.row(value=1)])
        negatives = self.run_rows([self.row(value=0)])
        self.assertIsNone(positives["auroc"])
        self.assertEqual(positives["average_precision"], 1)
        self.assertIsNone(negatives["auroc"])
        self.assertIsNone(negatives["average_precision"])
        empty = self.run_rows([], policy=self.policy())
        self.assertEqual(empty["metric_status"], "no_mature_cases")
        self.assertIsNone(empty["brier_completion_bounds"]["upper"])

    def test_population_identity_binds_freeze_policy_and_dependence_but_not_labels(self):
        row = self.row()
        first = self.run_rows([row], policy=self.policy())
        changed_label = (row[0], replace(row[1], status="unresolved", value=None))
        self.assertEqual(first["population_fingerprint"],
                         self.run_rows([changed_label], policy=self.policy())["population_fingerprint"])
        for result in (self.run_rows([row], freeze=date(2026, 1, 2), policy=self.policy()),
                       self.run_rows([row], policy=self.policy(lag=1)),
                       self.run_rows([(row[0], replace(row[1], cluster_id="other"))], policy=self.policy())):
            self.assertNotEqual(first["population_fingerprint"], result["population_fingerprint"])

    def test_raw_metrics_do_not_certify_prediction_provenance(self):
        result = self.run_rows([self.row()])
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["policy_source"], "inferred_legacy_zero_lag")
        self.assertEqual(result["prediction_provenance"], "not_checked_by_metrics_function")
        self.assertEqual(result["estimator"], "fixed_horizon_binary")

    def test_bounds_collapse_with_complete_labels_and_predictions(self):
        result = self.run_rows([self.row("a", p=0.3), self.row("b", value=1, p=0.7)])
        bounds = result["brier_completion_bounds"]
        self.assertEqual(bounds["lower"], result["brier"])
        self.assertEqual(bounds["upper"], result["brier"])

    def test_bounds_cover_all_missing_label_completions(self):
        rows = [self.row("a", value=None, status="unresolved", p=0.1),
                self.row("b", value=None, status="censored", p=0.9)]
        result = self.run_rows(rows)
        bounds = result["brier_completion_bounds"]
        for a in (0, 1):
            for b in (0, 1):
                loss = ((0.1 - a) ** 2 + (0.9 - b) ** 2) / 2
                self.assertGreaterEqual(loss + 1e-12, bounds["lower"])
                self.assertLessEqual(loss - 1e-12, bounds["upper"])
        self.assertAlmostEqual(bounds["lower"], 0.01)
        self.assertAlmostEqual(bounds["upper"], 0.81)


if __name__ == "__main__":
    unittest.main()
