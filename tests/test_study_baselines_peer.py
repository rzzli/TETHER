"""Independent public-boundary probes; invented fixtures are not scientific gold."""

import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from asof.serde import ContractError, canonical, encode, fingerprint
from asof.study.baselines import reviewer_view, run_baseline, verify_baseline
from asof.study.diagnostic import load_synthetic_request
from asof.study import diagnostic_resources
from asof.study import baseline_smoke


def limits(**changes):
    return {
        "schema_version": 1,
        "method": "extractive",
        "query": None,
        "max_excerpts": 3,
        "max_quote_bytes": 8192,
        "max_request_bytes": 65536,
        "max_result_bytes": 65536,
        **changes,
    }


class BaselinePeerTests(unittest.TestCase):
    def setUp(self):
        self.request = load_synthetic_request("synthetic-context")

    def test_rehashed_evaluator_annotation_cannot_become_fixture(self):
        request = encode(self.request)
        row = request["source_request"]["evidence"][0]
        row["scientific_record"]["source_metrics"]["evaluation"] = {
            "role": "evaluation_only",
            "expected_answer": "Invented forbidden evaluator annotation",
        }
        row["admitted_sha256"] = fingerprint(row["scientific_record"])
        request["source_scope"]["observations"][0]["scientific_record_sha256"] = row[
            "admitted_sha256"
        ]
        with self.assertRaises(ContractError):
            run_baseline(request, limits())

    def test_known_source_and_agent_role_are_not_admission(self):
        for source_ref in (
            {"kind": "known_source"},
            {"kind": "synthetic_fixture_not_admitted", "role": "agent_evidence"},
            {
                "kind": "synthetic_fixture_not_admitted",
                "parents": [{"role": "evaluation_only"}],
            },
        ):
            with self.subTest(source_ref=source_ref):
                request = encode(self.request)
                request["source_request"]["evidence"][0]["source_ref"] = source_ref
                with self.assertRaises(ContractError):
                    run_baseline(request, limits())

    def test_packet_hash_consistency_does_not_authorize_new_source_order(self):
        request = encode(self.request)
        request["source_request"]["evidence"].reverse()
        request["source_scope"]["observations"].reverse()
        with self.assertRaises(ContractError):
            run_baseline(request, limits())

    def test_request_limit_precedes_fixture_resource_access(self):
        cap = len(canonical(self.request)) - 1
        with patch(
            "asof.study.baselines.load_synthetic_request",
            side_effect=AssertionError("Must not load after failing byte preflight"),
        ):
            with self.assertRaises(ContractError):
                run_baseline(self.request, limits(max_request_bytes=cap))

    def test_corrupted_packaged_resource_fails_even_with_good_caller_request(self):
        # A parseable altered package resource must fail its external code-pinned hash.
        changed = encode(self.request)
        changed["role"] = "evaluation_only"
        resource = Mock()
        resource.joinpath.return_value = resource
        resource.read_bytes.return_value = json.dumps(changed).encode()
        with patch.object(diagnostic_resources, "files", return_value=resource):
            with self.assertRaises(ContractError):
                run_baseline(self.request, limits())

    def test_oversized_statement_retains_omission_without_clipping(self):
        rows = self.request["source_request"]["evidence"]
        sizes = {
            row["observation_id"]: len(row["statement"].encode("utf-8")) for row in rows
        }
        self.assertNotEqual(min(sizes.values()), max(sizes.values()))
        result = run_baseline(self.request, limits(max_quote_bytes=min(sizes.values())))
        selected = {q["observation_id"]: q for q in result["excerpts"]}
        self.assertEqual(len(result["selection_trace"]), len(rows))
        for row in rows:
            ident = row["observation_id"]
            if sizes[ident] == min(sizes.values()):
                self.assertEqual(selected[ident]["text"], row["statement"])
                self.assertEqual(
                    selected[ident]["text_sha256"],
                    hashlib.sha256(row["statement"].encode("utf-8")).hexdigest(),
                )
            else:
                self.assertNotIn(ident, selected)
                trace = next(
                    item
                    for item in result["selection_trace"]
                    if item["observation_id"] == ident
                )
                self.assertEqual(trace["disposition"], "too_large")
        self.assertEqual(result["extraction_state"], "partial")
        self.assertEqual(result["scientific_answer_status"], "not_attempted")

    def test_external_policy_anchor_rejects_self_consistent_replacement(self):
        expected = limits()
        replacement = limits(method="lexical", query="nonexistentword")
        independently_valid = run_baseline(self.request, replacement)
        with self.assertRaises(ContractError):
            verify_baseline(self.request, expected, independently_valid)

    def test_projection_rejects_forged_science_and_denominators(self):
        original = run_baseline(self.request, limits())
        changes = (
            ("scientific_answer_status", "answered"),
            ("generated_interpretations", ["Invented inference"]),
            ("clinical_probability", 0.9),
            ("features", {"literature_support": 1}),
            ("offered_statement_count", 1),
            ("extraction_incomplete", True),
            (
                "measured_model_usage",
                {"input_tokens": 1, "output_tokens": 0, "cost_usd": 0.0},
            ),
        )
        for field, value in changes:
            with self.subTest(field=field):
                changed = encode(original)
                changed[field] = value
                with self.assertRaises(ContractError):
                    reviewer_view(changed, "Candidate A")

    def test_pure_baselines_cannot_dispatch_network_or_process(self):
        with (
            patch("socket.socket", side_effect=AssertionError("Network forbidden")),
            patch("subprocess.Popen", side_effect=AssertionError("Process forbidden")),
        ):
            for policy in (limits(), limits(method="lexical", query="human")):
                result = run_baseline(self.request, policy)
                verify_baseline(self.request, policy, result)
                reviewer_view(result, "Candidate A")
                self.assertEqual(result["model_calls"], 0)

    def test_neutral_label_cannot_spell_actual_arm_identity(self):
        result = run_baseline(self.request, limits())
        for name in ("Candidate ASOF", "Candidate BASELINE", "Candidate LEXICAL"):
            with self.subTest(name=name), self.assertRaises(ContractError):
                reviewer_view(result, name)


class BaselineSmokePeerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "smoke"

    def reseal(self, updates):
        receipt_path = self.output / "receipt.json"
        receipt = json.loads(receipt_path.read_bytes())
        for name, document in updates.items():
            raw = canonical(document)
            (self.output / name).write_bytes(raw)
            receipt["artifacts"][name]["sha256"] = hashlib.sha256(raw).hexdigest()
            receipt["artifacts"][name]["bytes"] = len(raw)
        raw = canonical(receipt)
        receipt_path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def test_reparse_ancestor_rejected_before_parent_creation(self):
        # Model Windows reparse metadata without requiring privileged link creation.
        real_lstat = Path.lstat

        def reparse_metadata(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            if path == self.root:
                return SimpleNamespace(
                    st_mode=info.st_mode,
                    st_file_attributes=getattr(info, "st_file_attributes", 0) | 0x400,
                )
            return info

        missing = self.root / "must-not-create"
        with patch.object(Path, "lstat", new=reparse_metadata):
            with self.assertRaises(ContractError):
                baseline_smoke.smoke(missing / "smoke")
        self.assertFalse(missing.exists(), "Rejected path mutated before validation")

    def test_resealed_resource_name_swap_is_not_consumer_compatible(self):
        baseline_smoke.smoke(self.output)
        package = json.loads((self.output / "package-proof.json").read_bytes())
        names = sorted(package["resources"])
        first, second = names[0], names[1]
        package["resources"][first], package["resources"][second] = (
            package["resources"][second],
            package["resources"][first],
        )
        anchor = self.reseal({"package-proof.json": package})
        with self.assertRaises(ContractError):
            baseline_smoke.verify(self.output, anchor)

    def test_resealed_valid_alternative_policy_is_not_frozen_cell(self):
        baseline_smoke.smoke(self.output)
        request = json.loads((self.output / "cell-01-request.json").read_bytes())
        policy = limits(method="lexical", query="human")
        result = run_baseline(request, policy)
        view = reviewer_view(result, "Candidate A")
        anchor = self.reseal(
            {
                "cell-01-policy.json": policy,
                "cell-01-result.json": result,
                "cell-01-reviewer.json": view,
            }
        )
        with self.assertRaises(ContractError):
            baseline_smoke.verify(self.output, anchor)

    def test_zero_accounting_cannot_hide_missing_algorithm_invocations(self):
        baseline_smoke.smoke(self.output)
        accounting = json.loads((self.output / "accounting.json").read_bytes())
        accounting["algorithm_invocations"] = 0
        anchor = self.reseal({"accounting.json": accounting})
        with self.assertRaises(ContractError):
            baseline_smoke.verify(self.output, anchor)

    def test_failed_reservation_cannot_repeat_computation(self):
        with patch.object(
            baseline_smoke,
            "run_baseline",
            side_effect=KeyboardInterrupt("fixture stop"),
        ) as algorithm:
            with self.assertRaises(KeyboardInterrupt):
                baseline_smoke.smoke(self.output)
            self.assertEqual(algorithm.call_count, 1)
            with self.assertRaises(FileExistsError):
                baseline_smoke.smoke(self.output)
            self.assertEqual(algorithm.call_count, 1)
        marker = json.loads((self.output / "failure.json").read_bytes())
        self.assertEqual(marker["error_class"], "KeyboardInterrupt")
        self.assertEqual(marker["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
