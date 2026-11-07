"""Independent adversarial preparation probes; no real model or source assets."""

import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, canonical, encode, fingerprint
from tether_engine.study import source_preparation as source
from tether_engine.study import tokenization as tok
from tether_engine.study.proofs import capture_file, capture_package_proof
from tether_engine.study.source_rows import verify_observation
from tether_engine.study.preparation_payloads import prepare_payloads
from tether_engine.study.diagnostic import load_synthetic_request
from tether_engine.study.diagnostic_codec import bind_question
from tether_engine.study.stable_read import read_file
from tests import test_study_source_preparation as source_fixtures
from tests import test_study_tokenization as token_fixtures

TEMP = Path(__file__).resolve().parents[1] / "data/cache"


class SourcePeerTests(unittest.TestCase):
    def test_deadline_exhausted_during_sealing_cannot_publish_success(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            root = Path(tmp)
            authority, anchor, result = source_fixtures.PublicationTests().fixture(root)
            output = root / "late-seal"
            clock = [0.0]

            def expensive_sealing(_proof):
                clock[0] = 301.0

            with (
                patch.object(source.time, "monotonic", side_effect=lambda: clock[0]),
                patch.object(source, "_build", return_value=result),
                patch.object(source, "_verify_package", side_effect=expensive_sealing),
            ):
                with self.assertRaises(TimeoutError):
                    source.prepare_source_request(
                        authority, anchor, {}, output, deadline=299
                    )
            self.assertFalse((output / "receipt.json").exists())
            self.assertTrue((output / "failure.json").exists())

    def test_resealed_resource_name_cannot_point_to_another_package_asset(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            root = Path(tmp)
            authority, anchor, result = source_fixtures.PublicationTests().fixture(root)
            output = root / "prepared"
            with patch.object(source, "_build", return_value=result):
                original = source.prepare_source_request(
                    authority, anchor, {}, output, deadline=time.monotonic() + 299
                )
                source.verify_source_preparation(
                    output,
                    original["receipt_sha256"],
                    anchor,
                    {},
                    deadline=time.monotonic() + 299,
                )
                resources = {
                    name: "study/" + name for name in source.REQUIRED_RESOURCES
                }
                names = list(resources)
                resources[names[0]], resources[names[1]] = (
                    resources[names[1]],
                    resources[names[0]],
                )
                proof = capture_package_proof(resources, source.REQUIRED_RESOURCES)
                (output / "package-proof.json").write_bytes(canonical(proof))
                receipt = json.loads((output / "receipt.json").read_bytes())
                receipt["files"]["package-proof.json"] = encode(
                    capture_file(output / "package-proof.json", "package-proof.json")
                )
                raw = canonical(receipt)
                (output / "receipt.json").write_bytes(raw)
                with self.assertRaises(ContractError):
                    source.verify_source_preparation(
                        output,
                        hashlib.sha256(raw).hexdigest(),
                        anchor,
                        {},
                        deadline=time.monotonic() + 299,
                    )

    def test_whole_record_replay_rejects_metadata_outside_selected_metrics(self):
        fixture = source_fixtures.CompilerTests()
        fixture.setUp()
        observation = encode(fixture.record.observation)
        row = dict(
            id="1",
            targetId=fixture.case.hypothesis.target_id,
            diseaseId=fixture.case.hypothesis.indication_id,
            datasourceId="europepmc",
            datatypeId="literature",
            score=0.4,
        )
        arguments = dict(
            symbol="X",
            disease_name="Y",
            locator=dict(source_id="raw", row_group=0, row=0),
            mapping_refs=("map",),
            availability=fixture.case.hypothesis.availability,
            cutoff=fixture.case.cutoff,
        )
        verify_observation(observation, row, **arguments)
        for field, value in (
            ("source_kind", "computed"),
            ("missingness", {}),
            ("publication_year", 2019),
        ):
            with self.subTest(field=field), self.assertRaises(ContractError):
                verify_observation(
                    dict(observation, **{field: value}), row, **arguments
                )
        changed = json.loads(canonical(observation))
        changed["method"]["notes"] = ["invented scientific endorsement"]
        with self.assertRaises(ContractError):
            verify_observation(changed, row, **arguments)


class TokenPeerTests(unittest.TestCase):
    def test_offline_replay_rechecks_artifacts_after_initial_hash_pass(self):
        fixture = token_fixtures.TokenizationArtifactTests
        fixture.setUpClass()
        try:
            fixture().verify()
            original = tok._member_hashes
            calls = [0]

            def mutate_after_hash(root, deadline):
                value = original(root, deadline)
                calls[0] += 1
                if calls[0] == 1:
                    (root / "stderr.bin").write_bytes(b"changed after verification")
                return value

            with patch.object(tok, "_member_hashes", side_effect=mutate_after_hash):
                with self.assertRaises(ContractError):
                    fixture().verify()
        finally:
            fixture.tearDownClass()

    def test_fallible_cleanup_clock_does_not_replace_primary_interruption(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            output = Path(tmp) / "attempt"
            journal = RunJournal(output, kind="build")
            try:
                with patch.object(
                    tok.time,
                    "monotonic",
                    side_effect=[0, 0, 0, OSError("clock failed")],
                ):
                    with self.assertRaises(KeyboardInterrupt):
                        tok._run_child(
                            ["invented.exe"],
                            b"x",
                            10,
                            output,
                            journal,
                            process_factory=lambda *a, **kw: (_ for _ in ()).throw(
                                KeyboardInterrupt()
                            ),
                        )
                self.assertTrue((output / "child.json").is_file())
            finally:
                journal.close()

    def test_token_resource_alias_rejected_even_with_new_consistent_seal(self):
        fixture = token_fixtures.TokenizationArtifactTests
        fixture.setUpClass()
        try:
            output = fixture.bundle
            fixture().verify()
            proof = capture_package_proof(
                {tok.RESOURCE: "study/resources/fixed-evidence-plan-v1.json"},
                tok.REQUIRED_RESOURCES,
            )
            (output / "package-proof.json").write_bytes(canonical(proof))
            receipt = json.loads((output / "receipt.json").read_bytes())
            receipt["files"]["package-proof.json"] = encode(
                tok.hash_file(output / "package-proof.json", time.monotonic() + 10)
            )
            raw = canonical(receipt)
            (output / "receipt.json").write_bytes(raw)
            with patch.object(
                tok.subprocess,
                "Popen",
                side_effect=AssertionError("offline replay dispatched"),
            ):
                with self.assertRaises(ContractError):
                    tok.verify_tokenization(
                        output,
                        hashlib.sha256(raw).hexdigest(),
                        hashlib.sha256(fixture.prompt.encode()).hexdigest(),
                        fingerprint(fixture.spec),
                        expected_payload_sha256="a" * 64,
                    )
        finally:
            fixture.tearDownClass()


class PayloadAndReadPeerTests(unittest.TestCase):
    def test_full_source_two_claim_payloads_preserve_fields_and_are_not_execution(self):
        original = encode(load_synthetic_request("synthetic-context"))["source_request"]
        original["bounds"]["max_claims"] = 2
        request = bind_question(original, "genetic-study-report.v1")
        before = canonical(request)
        cells = prepare_payloads(request)
        self.assertEqual(len(cells), 6)
        for cell in cells:
            self.assertEqual(
                canonical(cell["semantic_data"]["original_request"]), before
            )
            self.assertIn("Active limits: 2 claims;", cell["payload"]["prompt"])
            self.assertEqual(
                cell["payload"]["json_schema"]["properties"]["claims"]["maxItems"], 2
            )
            self.assertFalse(cell["execution_authorized"])
            self.assertEqual(
                cell["history_scope"], "exact_hypothetical_only_not_a_token_maximum"
            )
        self.assertEqual(canonical(request), before)

    def test_declared_size_limit_rejects_before_payload_open(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            path = Path(tmp) / "large.json"
            path.write_bytes(b"x" * 17)
            with patch.object(
                Path, "open", side_effect=AssertionError("oversized file opened")
            ):
                with self.assertRaises(ContractError):
                    read_file(path, time.monotonic() + 10, 16)
