"""Adversarial synthetic comparison mechanics; no model or scientific gold."""

import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from asof.journal import RunJournal
from asof.serde import ContractError, canonical, encode, fingerprint
from asof.study import fixed_evidence as stages
from asof.study import fixed_evidence_smoke as comparison
from asof.study.session import StudySession
from asof.workflow import Budget


class FixedEvidenceBoundaryPeerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "comparison"

    def test_wrong_predecessor_identity_fails_before_recursive_verifier(self):
        journal = RunJournal(self.root, kind="build")
        self.addCleanup(journal.close)
        run_id = journal.events[0]["details"]["run_id"]
        fixture, arm = "synthetic-context", stages.ARMS[1]
        request = encode(stages.prepare_stage(self.root, run_id, fixture, arm, 0))
        request["stage_index"] = 1
        folder = self.root / stages.cell_path(fixture, arm, 0)
        folder.mkdir(parents=True)
        for name in comparison.CELL_FILES:
            (folder / name).write_bytes(
                canonical(request if name == "request.json" else {})
            )
        anchor = hashlib.sha256((folder / "receipt.json").read_bytes()).hexdigest()
        with patch.object(
            stages,
            "verify_study",
            side_effect=AssertionError(
                "Invalid identity reached recursive verification"
            ),
        ):
            with self.assertRaises(ContractError):
                stages.verify_stage(self.root, run_id, fixture, arm, 0, anchor)

    def test_parent_expiry_during_document_preparation_prevents_dispatch(self):
        clock = SimpleNamespace(now=0.0)
        original_document = comparison._recorded_document
        original_generate = stages.DeadlineRecordedBackend.generate
        dispatched = []

        def delayed_document(request, payload):
            result = original_document(request, payload)
            clock.now = 301.0
            return result

        def count_dispatch(backend, *args, **kwargs):
            dispatched.append(True)
            return original_generate(backend, *args, **kwargs)

        with (
            patch.object(comparison.time, "monotonic", side_effect=lambda: clock.now),
            patch.object(
                comparison, "_recorded_document", side_effect=delayed_document
            ),
            patch.object(
                stages.DeadlineRecordedBackend, "generate", new=count_dispatch
            ),
        ):
            with self.assertRaises(ContractError):
                comparison.smoke(self.root)
        self.assertEqual(
            dispatched, [], "A recorded call started after the shared deadline"
        )
        marker = json.loads((self.root / "failure.json").read_bytes())
        self.assertEqual(marker["actual_model_calls"], 0)

    def parent(self, suffix=""):
        root = self.root.with_name(self.root.name + suffix)
        journal = RunJournal(root, kind="build")
        self.addCleanup(journal.close)
        return root, journal.events[0]["details"]["run_id"]

    def test_final_recorded_consumption_guard_after_quote_delay(self):
        root, run_id = self.parent()
        request = stages.prepare_stage(
            root, run_id, "synthetic-context", stages.ARMS[0], 0
        )
        payload = stages.prepare_payload(request)
        document = stages.recorded_document(request, payload)
        backend = stages.DeadlineRecordedBackend(document, case_end=300.0)
        clock = SimpleNamespace(now=0.0)
        original_quote = backend.quote

        def slow_quote(*args, **kwargs):
            result = original_quote(*args, **kwargs)
            clock.now = 301.0
            return result

        with (
            patch.object(stages.time, "monotonic", side_effect=lambda: clock.now),
            patch.object(backend, "quote", side_effect=slow_quote),
        ):
            with self.assertRaises(ContractError):
                backend.generate(request, payload, timeout_seconds=300.0)
        self.assertFalse(backend.used, "Expired fixture was consumed")

    def test_outer_run_metadata_does_not_change_measured_prompt(self):
        first_root, first_id = self.parent("-first")
        second_root, second_id = self.parent("-second")
        first = stages.prepare_stage(
            first_root, first_id, "synthetic-context", stages.ARMS[0], 0
        )
        second = stages.prepare_stage(
            second_root, second_id, "synthetic-context", stages.ARMS[0], 0
        )
        self.assertNotEqual(first_id, second_id)
        self.assertNotEqual(fingerprint(first), fingerprint(second))
        self.assertEqual(
            canonical(stages.prepare_payload(first)),
            canonical(stages.prepare_payload(second)),
        )
        self.assertEqual(
            stages.preflight("synthetic-context")["input_reservation"], 31715
        )
        self.assertEqual(
            stages.preflight("synthetic-orientation")["input_reservation"], 28503
        )

    def test_evaluator_metadata_cannot_enter_rehashed_stage_source(self):
        root, run_id = self.parent()
        original = stages.prepare_stage(
            root, run_id, "synthetic-context", stages.ARMS[0], 0
        )
        for mutation in ("source", "history"):
            with self.subTest(mutation=mutation):
                bad = encode(original)
                if mutation == "source":
                    row = bad["original_request"]["source_request"]["evidence"][0]
                    row["scientific_record"]["source_metrics"]["evaluator_answer"] = (
                        "FORBIDDEN"
                    )
                    row["admitted_sha256"] = fingerprint(row["scientific_record"])
                    bad["original_request"]["source_scope"]["observations"][0][
                        "scientific_record_sha256"
                    ] = row["admitted_sha256"]
                    bad["original_request_sha256"] = fingerprint(
                        bad["original_request"]
                    )
                    bad["source_scope_sha256"] = fingerprint(
                        bad["original_request"]["source_scope"]
                    )
                else:
                    bad["history_projection"] = [
                        {"stage": "human_reference", "source_ids": ["E0"]}
                    ]
                    bad["prior_stage_proofs"] = [{"role": "evaluation_only"}]
                    bad["history_projection_sha256"] = fingerprint(
                        bad["history_projection"]
                    )
                with self.assertRaises(ContractError):
                    stages.prepare_payload(bad)

    def test_authored_text_is_not_repaired_when_materializing_source_quotes(self):
        root, run_id = self.parent()
        stage = stages.prepare_stage(
            root, run_id, "synthetic-context", stages.ARMS[0], 0
        )
        payload = stages.prepare_payload(stage)
        document = json.loads(stages.recorded_document(stage, payload)["content_utf8"])
        authored = "Invented caution <tag>&\nCombining e\u0301 and café remain literal."
        document["claims"][1]["text"] = authored
        validated = stages.RoleRecordedVerifier(root, run_id).validate_response(
            stage, canonical(document)
        )
        view = comparison._interpretation_view(stage, validated, "Candidate A")
        self.assertEqual(view["claims"][1]["authored_claim"]["text"], authored)
        source = stage["original_request"]["source_request"]["evidence"][0]["statement"]
        self.assertEqual(view["claims"][1]["literal_quotes"][0]["text"], source)
        self.assertNotEqual(authored, source)
        self.assertEqual(view["scientific_validation"], "not_attempted")

    def test_linked_parent_rejected_before_journal_read(self):
        root, run_id = self.parent()
        real_lstat = Path.lstat

        def linked(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            if path == root:
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return info

        with (
            patch.object(Path, "lstat", new=linked),
            patch.object(
                stages, "read_chain", side_effect=AssertionError("Linked journal read")
            ),
        ):
            with self.assertRaises(ContractError):
                stages.prepare_stage(
                    root, run_id, "synthetic-context", stages.ARMS[0], 0
                )

    def stage_setup(self):
        journal = RunJournal(self.root, kind="build")
        self.addCleanup(journal.close)
        run_id = journal.events[0]["details"]["run_id"]
        start = time.monotonic()
        end = start + 300.0
        fixture, arm = "synthetic-context", stages.ARMS[1]
        journal.append(
            "fixture_started",
            fixture=fixture,
            budget=encode(Budget()),
            start_monotonic=start,
            case_end_monotonic=end,
        )
        verifier = stages.RoleRecordedVerifier(self.root, run_id)
        request = verifier.prepare_stage(fixture, arm, 0)
        payload = stages.prepare_payload(request)
        document = stages.recorded_document(request, payload)
        folder = self.root / stages.cell_path(fixture, arm, 0)
        return verifier, request, payload, document, folder, end

    def test_successful_unregistered_predecessor_is_not_accepted_history(self):
        verifier, request, payload, document, folder, end = self.stage_setup()
        with StudySession(
            folder,
            resources={name: "study/" + name for name in stages.REQUIRED_RESOURCES},
            required_resources=stages.REQUIRED_RESOURCES,
        ) as session:
            session.call_once(
                request=request,
                payload=payload,
                backend=stages.DeadlineRecordedBackend(document, case_end=end),
                verifier=verifier,
            )
            session.finish()
        anchor = hashlib.sha256((folder / "receipt.json").read_bytes()).hexdigest()
        verifier.verify_stage("synthetic-context", stages.ARMS[1], 0, anchor)
        with self.assertRaisesRegex(ContractError, "not accepted"):
            verifier.prepare_stage("synthetic-context", stages.ARMS[1], 1)

    def test_other_valid_scripted_response_cannot_become_approved_transport(self):
        verifier, request, payload, document, folder, end = self.stage_setup()
        changed = encode(document)
        response = json.loads(changed["content_utf8"])
        response["claims"][1]["text"] = "Alternative invented selection commentary."
        changed["content_utf8"] = canonical(response).decode()
        # It satisfies the response schema; the fixed fixture authorization is separate.
        verifier.validate_response(request, canonical(response))
        with self.assertRaisesRegex(ContractError, "fixed synthetic transport fixture"):
            with StudySession(
                folder,
                resources={name: "study/" + name for name in stages.REQUIRED_RESOURCES},
                required_resources=stages.REQUIRED_RESOURCES,
            ) as session:
                session.call_once(
                    request=request,
                    payload=payload,
                    backend=stages.DeadlineRecordedBackend(changed, case_end=end),
                    verifier=verifier,
                )
        self.assertFalse((folder / "receipt.json").exists())

    def test_resealed_stage_elapsed_cannot_overlap_next_allocation(self):
        comparison.smoke(self.root)
        journal_path = self.root / "journal.jsonl"
        events = [json.loads(line) for line in journal_path.read_bytes().splitlines()]
        fixture = "synthetic-context"
        reserved = [
            e["details"]
            for e in events
            if e["event"] == "stage_reserved" and e["details"]["fixture"] == fixture
        ]
        first, second = reserved[:2]
        gap = (
            first["allocated_budget"]["max_seconds"]
            - second["allocated_budget"]["max_seconds"]
        )
        folder = self.root / first["cell_id"]
        report_path = folder / "report.json"
        report = json.loads(report_path.read_bytes())
        report["elapsed_seconds"] = gap + 1.0
        self.assertLess(
            report["elapsed_seconds"], first["allocated_budget"]["max_seconds"]
        )
        report_path.write_bytes(canonical(report) + b"\n")
        child_events = [
            json.loads(line)
            for line in (folder / "journal.jsonl").read_bytes().splitlines()
        ]
        child_events[-1]["details"]["report_sha256"] = fingerprint(report)
        self.rechain(folder / "journal.jsonl", child_events)
        receipt_path = folder / "receipt.json"
        receipt = json.loads(receipt_path.read_bytes())
        for name in ("report.json", "journal.jsonl"):
            raw = (folder / name).read_bytes()
            receipt["outputs"][name]["sha256"] = hashlib.sha256(raw).hexdigest()
            receipt["outputs"][name]["bytes"] = len(raw)
        receipt_path.write_bytes(canonical(receipt) + b"\n")
        anchor = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        for event in events:
            if (
                event["event"] == "stage_accepted"
                and event["details"]["cell_id"] == first["cell_id"]
            ):
                event["details"]["receipt_sha256"] = anchor
            if (
                event["event"] == "fixture_completed"
                and event["details"]["fixture"] == fixture
            ):
                event["details"]["elapsed_seconds"] = 200.0
        summary_path = self.root / "summary.json"
        summary = json.loads(summary_path.read_bytes())
        summary["fixtures"][0]["elapsed_seconds"] = 200.0
        summary_path.write_bytes(canonical(summary))
        events[-1]["details"]["summary_sha256"] = fingerprint(summary)
        self.rechain(journal_path, events)
        parent_path = self.root / "receipt.json"
        parent = json.loads(parent_path.read_bytes())
        for name, proof in parent["artifacts"].items():
            raw = (self.root / name).read_bytes()
            proof["sha256"] = hashlib.sha256(raw).hexdigest()
            proof["bytes"] = len(raw)
        parent_path.write_bytes(canonical(parent))
        # The child is individually consistent; only the shared schedule contradicts it.
        stages.verify_stage(
            self.root, summary["run_id"], fixture, stages.ARMS[0], 0, anchor
        )
        with self.assertRaises(ContractError):
            comparison.verify(
                self.root, hashlib.sha256(parent_path.read_bytes()).hexdigest()
            )

    @staticmethod
    def rechain(path, events):
        previous = None
        for index, event in enumerate(events):
            event.pop("sha256", None)
            event["sequence"] = index
            event["previous_sha256"] = previous
            event["sha256"] = fingerprint(event)
            previous = event["sha256"]
        path.write_bytes(b"".join(canonical(event) + b"\n" for event in events))


if __name__ == "__main__":
    unittest.main()
