"""Independent token-capacity boundaries using only invented tokenizer fixtures."""

from dataclasses import FrozenInstanceError, replace
import hashlib
import time
import unittest
from unittest.mock import patch

from tether_engine.agents import Usage
from tether_engine.serde import ContractError
from tether_engine.study import session as study
from tether_engine.study import tokenization as tok
from tether_engine.workflow import Budget
from tests import test_study_token_capacity as fixtures


class TokenCapacityPeerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.TokenCapacityTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.TokenCapacityTests.tearDownClass()

    setUp = fixtures.TokenCapacityTests.setUp
    session = fixtures.TokenCapacityTests.session

    def _accepted(self):
        cell = self.session(capacity_policy=self.policy)
        self.addCleanup(lambda: cell.journal.close() if not cell.closed else None)
        cell.call_once(
            request=self.request,
            payload=self.payload,
            backend=self.backend,
            verifier=self.verifier,
        )
        return cell

    def test_capacity_descriptor_is_deeply_immutable_and_locator_free(self):
        descriptor = self.policy.describe()
        self.assertNotIn("path", descriptor)
        with self.assertRaises(TypeError):
            descriptor["implementation"]["sha256"] = "0" * 64
        with self.assertRaises(FrozenInstanceError):
            self.policy.receipt_sha256 = "0" * 64
        self.assertEqual(descriptor, self.policy.describe())

    def test_exact_capacity_and_budget_do_not_accept_smaller_or_larger_quotes(self):
        quote = self.backend.quote(self.request, self.payload)
        for altered in (
            Usage(quote.input_tokens - 1, quote.output_tokens, 0.0),
            Usage(quote.input_tokens + 1, quote.output_tokens, 0.0),
            Usage(quote.input_tokens, quote.output_tokens + 1, 0.0),
        ):
            with self.subTest(quote=altered), self.assertRaises(ContractError):
                self.policy.verify(
                    self.request,
                    self.payload,
                    self.backend.capabilities,
                    altered,
                    Budget(),
                    deadline=self.deadline,
                )
        for budget in (
            replace(Budget(), max_input_tokens=quote.input_tokens - 1),
            replace(Budget(), max_output_tokens=quote.output_tokens - 1),
            replace(Budget(), max_cost_usd=1.0),
        ):
            with self.subTest(budget=budget), self.assertRaises(ContractError):
                self.policy.verify(
                    self.request,
                    self.payload,
                    self.backend.capabilities,
                    quote,
                    budget,
                    deadline=self.deadline,
                )

    def test_wrong_external_anchor_and_tokenizer_fail_without_dispatch(self):
        bad = replace(self.policy, receipt_sha256="0" * 64)
        with self.assertRaises(ContractError):
            bad.reservation(
                self.request,
                self.payload,
                self.backend.capabilities,
                deadline=self.deadline,
            )
        caps = replace(self.backend.capabilities, tokenizer_identity="0" * 64)
        with patch.object(
            tok, "verify_tokenization", side_effect=AssertionError("No proof read")
        ):
            with self.assertRaises(ContractError):
                self.policy.reservation(
                    self.request, self.payload, caps, deadline=self.deadline
                )
        self.assertFalse(self.backend.used)

    def test_expiry_during_quote_does_not_consume_and_success_is_one_use(self):
        now = [time.monotonic()]
        verified = tok.verify_tokenization

        def slow_verified(*args, **kwargs):
            result = verified(*args, **kwargs)
            now[0] = self.deadline + 1
            return result

        with (
            patch.object(time, "monotonic", side_effect=lambda: now[0]),
            patch.object(tok, "verify_tokenization", side_effect=slow_verified),
        ):
            with self.assertRaises(TimeoutError):
                self.backend.generate(self.request, self.payload, timeout_seconds=10)
        self.assertFalse(self.backend.used)
        self.backend.generate(self.request, self.payload, timeout_seconds=10)
        self.assertTrue(self.backend.used)
        with self.assertRaises(ContractError):
            self.backend.generate(self.request, self.payload, timeout_seconds=10)

    def test_expired_replay_fails_before_receipt_read(self):
        with patch.object(study, "_read", side_effect=AssertionError("No file read")):
            with self.assertRaises(TimeoutError):
                study.verify_study(
                    self.root / "absent",
                    expected_receipt_sha256="0" * 64,
                    verifier=self.verifier,
                    capacity_policy=self.policy,
                    deadline=time.monotonic() - 1,
                )

    def test_shorter_caller_timeout_expires_before_recorded_consumption(self):
        now = [time.monotonic()]
        verified = tok.verify_tokenization

        def slow_verified(*args, **kwargs):
            result = verified(*args, **kwargs)
            now[0] += 2
            return result

        with (
            patch.object(time, "monotonic", side_effect=lambda: now[0]),
            patch.object(tok, "verify_tokenization", side_effect=slow_verified),
        ):
            with self.assertRaises(TimeoutError):
                self.backend.generate(self.request, self.payload, timeout_seconds=1)
        self.assertFalse(self.backend.used)

    def test_expiry_during_final_output_hashing_cannot_publish_success(self):
        cell = self._accepted()
        now = [time.monotonic()]
        original = study.capture_file

        def slow_capture(*args, **kwargs):
            result = original(*args, **kwargs)
            now[0] = cell.started + cell.budget.max_seconds + 1
            return result

        with (
            patch.object(study.time, "monotonic", side_effect=lambda: now[0]),
            patch.object(study, "capture_file", side_effect=slow_capture),
        ):
            with self.assertRaises((TimeoutError, ContractError)):
                cell.finish()
        self.assertFalse((cell.output / "receipt.json").exists())
        self.assertTrue((cell.output / "failure.json").exists())
        self.assertTrue(self.backend.used)

    def test_expiry_during_receipt_publication_withdraws_only_own_receipt(self):
        cell = self._accepted()
        now = [time.monotonic()]
        original = study._write

        def slow_write(root, name, value):
            result = original(root, name, value)
            if name == "receipt.json":
                now[0] = cell.started + cell.budget.max_seconds + 1
            return result

        with (
            patch.object(study.time, "monotonic", side_effect=lambda: now[0]),
            patch.object(study, "_write", side_effect=slow_write),
        ):
            with self.assertRaises((TimeoutError, ContractError)):
                cell.finish()
        self.assertFalse((cell.output / "receipt.json").exists())
        self.assertTrue((cell.output / "raw-response.bin").is_file())
        self.assertTrue((cell.output / "failure.json").is_file())

    def test_token_schema_replay_needs_exact_explicit_authority(self):
        cell = self._accepted()
        cell.finish()
        anchor = hashlib.sha256((cell.output / "receipt.json").read_bytes()).hexdigest()
        for policy in (None, replace(self.policy, spec_sha256="0" * 64)):
            with self.subTest(policy=policy), self.assertRaises(ContractError):
                study.verify_study(
                    cell.output,
                    expected_receipt_sha256=anchor,
                    verifier=self.verifier,
                    capacity_policy=policy,
                    deadline=time.monotonic() + 30,
                )


if __name__ == "__main__":
    unittest.main()
