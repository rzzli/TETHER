"""Independent contradiction/failure probes, using explicit synthetic fixtures only."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.agents import Usage
from tether_engine.serde import ContractError, canonical, encode, fingerprint, parse_json
from tether_engine.study.__main__ import fixture
from tether_engine.study.diagnostic import (
    REQUIRED_RESOURCES,
    load_synthetic_request,
    prepare_payload,
)
from tether_engine.study.proofs import capture_file
from tether_engine.study.recorded import RecordedBackend, RecordedVerifier
from tether_engine.study.session import GeneratedBytes, StudySession, inspect_study, verify_study


class StudySessionPeerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.counter = 0
        self.request = load_synthetic_request("synthetic-orientation")
        self.payload = prepare_payload(self.request, "simplified")
        self.verifier = RecordedVerifier()
        self.resources = {name: "study/" + name for name in REQUIRED_RESOURCES}

    def cell(self):
        self.counter += 1
        return StudySession(
            self.root / str(self.counter),
            resources=self.resources,
            required_resources=REQUIRED_RESOURCES,
            configuration={"source_kind": "synthetic_fixture_not_scientific_reference"},
        )

    def call(self, cell, backend=None):
        backend = backend or RecordedBackend(fixture(self.request, self.payload))
        return cell.call_once(
            request=self.request,
            payload=self.payload,
            backend=backend,
            verifier=self.verifier,
        )

    def success(self):
        with self.cell() as cell:
            self.call(cell)
            cell.finish()
        self.verify(cell.output)
        return cell.output

    def verify(self, output):
        return verify_study(
            output,
            expected_receipt_sha256=hashlib.sha256(
                (output / "receipt.json").read_bytes()
            ).hexdigest(),
            verifier=self.verifier,
        )

    def contradict(self, mutate):
        """Reseal byte-consistent artifacts so semantic checks, not old hashes, decide."""
        output = self.success()
        documents = {
            name: parse_json((output / name).read_bytes())
            for name in ("configuration.json", "report.json", "receipt.json")
        }
        events = [
            parse_json(line)
            for line in (output / "journal.jsonl").read_bytes().splitlines()
        ]
        mutate(documents, events)
        for event in events:
            if event["event"] == "study_prepared":
                event["details"]["configuration_sha256"] = fingerprint(
                    documents["configuration.json"]
                )
            if event["event"] == "study_completed":
                event["details"]["report_sha256"] = fingerprint(
                    documents["report.json"]
                )
        previous = None
        for sequence, event in enumerate(events):
            event.pop("sha256", None)
            event.update(sequence=sequence, previous_sha256=previous)
            event["sha256"] = fingerprint(event)
            previous = event["sha256"]
        (output / "journal.jsonl").write_bytes(
            b"".join(canonical(e) + b"\n" for e in events)
        )
        for name in ("configuration.json", "report.json"):
            (output / name).write_bytes(canonical(documents[name]) + b"\n")
        receipt = documents["receipt.json"]
        receipt["outputs"] = {
            name: encode(capture_file(output / name, name))
            for name in receipt["outputs"]
        }
        (output / "receipt.json").write_bytes(canonical(receipt) + b"\n")
        return output

    def test_sealed_capability_bounds_are_rechecked(self):
        for name in (
            "max_prompt_bytes",
            "max_payload_bytes",
            "max_response_bytes",
            "context_tokens",
            "max_output_tokens",
        ):
            with self.subTest(name=name):
                output = self.contradict(
                    lambda docs, events: docs["configuration.json"][
                        "backend_capabilities"
                    ].update({name: 1})
                )
                with self.assertRaises(ContractError):
                    self.verify(output)

    def test_sealed_budget_reservation_is_rechecked(self):
        for name in (
            "max_calls",
            "max_input_tokens",
            "max_output_tokens",
            "max_seconds",
        ):
            with self.subTest(name=name):
                output = self.contradict(
                    lambda docs, events: docs["configuration.json"]["budget"].update(
                        {name: 0}
                    )
                )
                with self.assertRaises(ContractError):
                    self.verify(output)

    def test_conservative_account_must_equal_full_reservation(self):
        def mutate(docs, events):
            account = next(e for e in events if e["event"] == "study_accounted")
            account["details"]["basis"] = "conservative_quote"
            # Fixture reports zero measured usage; treating it as zero conservative
            # usage contradicts the strictly positive dispatched reservation.
            docs["report.json"]["estimated_usage"] = encode(Usage(0, 0, 0.0))

        output = self.contradict(mutate)
        with self.assertRaises(ContractError):
            self.verify(output)

    def test_account_before_dispatch_is_rejected(self):
        def mutate(docs, events):
            account = next(e for e in events if e["event"] == "study_accounted")
            events.remove(account)
            events.insert(2, account)

        output = self.contradict(mutate)
        with self.assertRaises(ContractError):
            self.verify(output)

    def test_failure_event_cannot_be_hidden_before_completed(self):
        def mutate(docs, events):
            events.insert(
                -1,
                {
                    "event": "build_failed",
                    "details": {"stage": "execution", "error_class": "OSError"},
                },
            )

        output = self.contradict(mutate)
        with self.assertRaises(ContractError):
            self.verify(output)

    def test_raw_retained_byte_count_cannot_contradict_sealed_bytes(self):
        def mutate(docs, events):
            next(e for e in events if e["event"] == "study_response_captured")[
                "details"
            ]["retained_bytes"] = 0

        output = self.contradict(mutate)
        with self.assertRaises(ContractError):
            self.verify(output)

    def test_adapter_code_proof_cannot_be_arbitrary(self):
        def mutate(docs, events):
            docs["configuration.json"]["adapter_code"]["file"]["sha256"] = "0" * 64

        output = self.contradict(mutate)
        with self.assertRaises(ContractError):
            self.verify(output)

    def test_report_schema_and_status_are_validated(self):
        for changes in (
            {"schema_version": 999},
            {"status": "failed"},
            {"kind": "unrelated"},
        ):
            with self.subTest(changes=changes):
                output = self.contradict(
                    lambda docs, events: docs["report.json"].update(changes)
                )
                with self.assertRaises(ContractError):
                    self.verify(output)

    def test_failed_dispatch_write_never_invokes_backend(self):
        backend = RecordedBackend(fixture(self.request, self.payload))
        cell = self.cell()
        append = cell.journal.append
        error = OSError("dispatch fsync failed")

        def broken(event, **details):
            if event == "study_dispatch":
                raise error
            return append(event, **details)

        with patch.object(cell.journal, "append", side_effect=broken):
            with self.assertRaises(OSError) as caught:
                with cell:
                    self.call(cell, backend)
        self.assertIs(caught.exception, error)
        self.assertFalse(backend.used)
        self.assertEqual(inspect_study(cell.output)["calls"], 0)

    def test_changed_package_proof_fails_before_backend_call(self):
        cell = self.cell()
        stale = encode(cell.package_proof)
        stale["code"][0]["sha256"] = "0" * 64
        cell.package_proof = stale
        backend = RecordedBackend(fixture(self.request, self.payload))
        try:
            with self.assertRaises(ContractError):
                self.call(cell, backend)
            self.assertFalse(backend.used)
        finally:
            cell.journal.close()

    def test_finalization_rejects_changed_archived_inputs_or_response(self):
        for name in (
            "request.json",
            "payload.json",
            "configuration.json",
            "response.json",
        ):
            with self.subTest(name=name):
                cell = self.cell()
                try:
                    self.call(cell)
                    document = parse_json((cell.output / name).read_bytes())
                    document["unexpected_after_dispatch"] = "mutated on disk"
                    (cell.output / name).write_bytes(canonical(document) + b"\n")
                    with self.assertRaises(ContractError):
                        cell.finish()
                    self.assertFalse((cell.output / "receipt.json").exists())
                finally:
                    cell.journal.close()

    def test_failed_accounting_write_retains_unknown_reservation_and_blocks_repeat(
        self,
    ):
        backend = RecordedBackend(fixture(self.request, self.payload))
        cell = self.cell()
        append = cell.journal.append
        writes = []

        def broken(event, **details):
            if event == "study_accounted":
                writes.append(event)
                raise OSError("account fsync failed")
            return append(event, **details)

        with patch.object(cell.journal, "append", side_effect=broken):
            with self.assertRaises(OSError):
                with cell:
                    self.call(cell, backend)
        report = inspect_study(cell.output)
        self.assertEqual(report["calls"], 1)
        self.assertEqual(tuple(report["unresolved_attempts"]), ("cell",))
        self.assertGreater(report["estimated_usage"]["input_tokens"], 0)
        self.assertEqual(len(writes), 1)
        with self.assertRaises(ContractError):
            self.call(cell, RecordedBackend(fixture(self.request, self.payload)))

    def test_measured_usage_survives_invalid_envelope(self):
        cell = self.cell()
        backend = RecordedBackend(fixture(self.request, self.payload))
        with patch.object(
            backend, "generate", return_value=GeneratedBytes(None, Usage(7, 3, 0.0))
        ):
            with self.assertRaises(ContractError):
                with cell:
                    self.call(cell, backend)
        report = inspect_study(cell.output)
        self.assertEqual(report["measured_usage"], encode(Usage(7, 3, 0.0)))
        self.assertEqual(report["estimated_usage"], encode(Usage(0, 0, 0.0)))
        self.assertFalse((cell.output / "receipt.json").exists())

    def test_close_failure_prevents_success_receipt_and_preserves_primary(self):
        cell = self.cell()
        close = cell.journal.close
        error = OSError("close failed")

        def broken():
            close()
            raise error

        with self.assertRaises(OSError) as caught:
            with cell:
                self.call(cell)
                with patch.object(cell.journal, "close", side_effect=broken):
                    cell.finish()
        self.assertIs(caught.exception, error)
        self.assertFalse((cell.output / "receipt.json").exists())
        self.assertTrue((cell.output / "failure.json").exists())

    def test_second_call_rejected_after_success_without_invoking_second_backend(self):
        first, second = (
            RecordedBackend(fixture(self.request, self.payload)),
            RecordedBackend(fixture(self.request, self.payload)),
        )
        with self.cell() as cell:
            self.call(cell, first)
            with self.assertRaises(ContractError):
                self.call(cell, second)
            self.assertFalse(second.used)
            cell.finish()


if __name__ == "__main__":
    unittest.main()
