"""Durable once-only cells: real files and fake recorded generation only."""

import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from asof.agents import Usage
from asof.serde import ContractError, canonical, encode
from asof.study.__main__ import fixture, smoke
from asof.study.diagnostic import (
    REQUIRED_RESOURCES,
    load_synthetic_request,
    prepare_payload,
)
from asof.study.recorded import RecordedBackend, RecordedVerifier
from asof.study.session import GeneratedBytes, StudySession, inspect_study, verify_study
from asof.workflow import Budget


class InterruptBackend(RecordedBackend):
    def generate(self, request, payload, *, timeout_seconds):
        self.used = True
        raise KeyboardInterrupt("fixture interruption")


class EnvelopeBackend(RecordedBackend):
    def generate(self, request, payload, *, timeout_seconds):
        self.used = True
        return GeneratedBytes(None, Usage(7, 2, 0.0))


class StudySessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.request = load_synthetic_request("synthetic-orientation")
        self.payload = prepare_payload(self.request, "simplified")
        self.verifier = RecordedVerifier()
        self.resources = {name: "study/" + name for name in REQUIRED_RESOURCES}

    def session(self, name="cell", **kwargs):
        return StudySession(
            self.root / name,
            resources=self.resources,
            required_resources=REQUIRED_RESOURCES,
            **kwargs,
        )

    def backend(self, **kwargs):
        return RecordedBackend(fixture(self.request, self.payload, **kwargs))

    def call(self, cell, backend=None):
        return cell.call_once(
            request=self.request,
            payload=self.payload,
            backend=backend or self.backend(),
            verifier=self.verifier,
        )

    def verify(self, path):
        anchor = hashlib.sha256((path / "receipt.json").read_bytes()).hexdigest()
        return verify_study(
            path, expected_receipt_sha256=anchor, verifier=self.verifier
        )

    def test_recorded_success_seals_and_verifies(self):
        with self.session() as cell:
            response = self.call(cell)
            self.assertIsNone(response["clinical_probability"])
            report = cell.finish()
        self.assertEqual(report["calls"], 1)
        self.assertEqual(self.verify(cell.output)["mechanical_consistency"], "verified")

    def test_custom_backend_ids_do_not_select_verification_behavior(self):
        for index, identifier in enumerate(
            ("fixture-a", "unrelated-implementation-id")
        ):
            backend = RecordedBackend(
                fixture(self.request, self.payload), backend_id=identifier
            )
            with self.session(str(index)) as cell:
                self.call(cell, backend)
                cell.finish()
            self.assertEqual(self.verify(cell.output)["status"], "verified_study_cell")

    def test_timeout_is_once_conservatively_accounted_and_inspectable(self):
        backend = self.backend(timeout=True)
        with self.assertRaises(TimeoutError), self.session() as cell:
            self.call(cell, backend)
        report = inspect_study(cell.output)
        self.assertTrue(backend.used)
        self.assertEqual(report["calls"], 1)
        self.assertEqual(report["estimated_usage"]["output_tokens"], 2048)
        self.assertEqual(report["unresolved_attempts"], ())
        self.assertFalse((cell.output / "receipt.json").exists())
        with self.assertRaises(ContractError):
            self.call(cell, backend)

    def test_invalid_content_retains_measured_usage(self):
        document = fixture(self.request, self.payload, malformed=True)
        document["usage"] = encode(Usage(7, 2, 0.0))
        with self.assertRaises(ContractError), self.session() as cell:
            self.call(cell, RecordedBackend(document))
        report = inspect_study(cell.output)
        self.assertEqual(report["measured_usage"]["input_tokens"], 7)
        self.assertEqual(report["estimated_usage"]["input_tokens"], 0)
        self.assertEqual((cell.output / "raw-response.bin").read_bytes(), b"{}")

    def test_invalid_envelope_preserves_valid_measured_usage(self):
        with self.assertRaises(ContractError), self.session() as cell:
            self.call(cell, EnvelopeBackend(fixture(self.request, self.payload)))
        self.assertEqual(
            inspect_study(cell.output)["measured_usage"]["input_tokens"], 7
        )

    def test_interruption_retains_original_exception_and_conservative_usage(self):
        with self.assertRaises(KeyboardInterrupt), self.session() as cell:
            self.call(cell, InterruptBackend(fixture(self.request, self.payload)))
        report = inspect_study(cell.output)
        self.assertEqual(report["calls"], 1)
        self.assertGreater(report["estimated_usage"]["input_tokens"], 0)
        self.assertTrue(report["failure_marker_present"])

    def test_dispatch_write_failure_has_zero_generation(self):
        backend = self.backend()
        with self.assertRaises(OSError), self.session() as cell:
            original = cell.journal.append

            def append(event, **details):
                if event == "study_dispatch":
                    raise OSError("dispatch journal fixture")
                return original(event, **details)

            with patch.object(cell.journal, "append", append):
                self.call(cell, backend)
        self.assertFalse(backend.used)
        self.assertEqual(inspect_study(cell.output)["calls"], 0)

    def test_account_write_failure_leaves_unknown_reservation_without_retry(self):
        backend = self.backend()
        with self.assertRaises(OSError), self.session() as cell:
            original = cell.journal.append

            def append(event, **details):
                if event == "study_accounted":
                    raise OSError("accounting journal fixture")
                return original(event, **details)

            with patch.object(cell.journal, "append", append):
                self.call(cell, backend)
        report = inspect_study(cell.output)
        self.assertTrue(backend.used)
        self.assertEqual(report["unresolved_attempts"], ("cell",))
        self.assertEqual(report["measured_usage"]["input_tokens"], 0)
        self.assertGreater(report["estimated_usage"]["input_tokens"], 0)

    def test_budget_and_capability_failure_precedes_generation(self):
        backend = self.backend()
        backend.capabilities = replace(backend.capabilities, max_prompt_bytes=1)
        with self.assertRaises(ContractError), self.session() as cell:
            self.call(cell, backend)
        self.assertFalse(backend.used)
        self.assertEqual(inspect_study(cell.output)["calls"], 0)

    def test_changed_fixture_binding_fails_before_generation(self):
        document = fixture(self.request, self.payload)
        document["payload_sha256"] = "a" * 64
        backend = RecordedBackend(document)
        with self.assertRaises(ContractError), self.session() as cell:
            self.call(cell, backend)
        self.assertFalse(backend.used)

    def test_output_collision_and_paid_budget_reject(self):
        with self.assertRaises(ContractError), self.session():
            with self.assertRaises(FileExistsError):
                self.session()
        with self.assertRaises(ContractError):
            self.session("paid", budget=Budget(max_cost_usd=1.0))

    def test_unfinalized_success_is_not_a_receipt(self):
        with self.assertRaises(ContractError), self.session() as cell:
            self.call(cell)
        self.assertFalse((cell.output / "receipt.json").exists())
        self.assertEqual(inspect_study(cell.output)["status"], "failed_or_incomplete")

    def test_second_call_rejects_even_after_success(self):
        with self.session() as cell:
            self.call(cell)
            with self.assertRaises(ContractError):
                self.call(cell)
            cell.finish()

    def test_response_output_tampering_and_wrong_anchor_reject(self):
        with self.session() as cell:
            self.call(cell)
            cell.finish()
        with self.assertRaises(ContractError):
            verify_study(
                cell.output, expected_receipt_sha256="0" * 64, verifier=self.verifier
            )
        (cell.output / "response.json").write_bytes(canonical({"changed": True}))
        with self.assertRaises(ContractError):
            self.verify(cell.output)

    def test_final_receipt_write_failure_never_reports_sealed(self):
        with self.assertRaises(OSError), self.session() as cell:
            self.call(cell)
            original = cell._put

            def put(name, value):
                if name == "receipt.json":
                    raise OSError("receipt write fixture")
                return original(name, value)

            with patch.object(cell, "_put", put):
                cell.finish()
        self.assertFalse(cell.sealed)
        self.assertEqual(inspect_study(cell.output)["status"], "failed_or_incomplete")

    def test_smoke_retains_both_fixture_outcomes(self):
        report = smoke(self.root / "smoke")
        self.assertEqual(report["native_model_calls"], 0)
        self.assertEqual(report["failure"]["calls"], 1)
        self.assertEqual(report["success"]["consumer_contract"], "verified")


if __name__ == "__main__":
    unittest.main()
