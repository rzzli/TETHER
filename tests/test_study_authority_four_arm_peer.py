"""Independent composition replay probes; every tokenizer process is invented."""

from pathlib import Path
import shutil
import time
import unittest
from unittest.mock import patch

from tether_engine.journal import read_chain
from tether_engine.serde import ContractError, canonical, encode, fingerprint, parse_json
from tether_engine.study import authority_four_arm as composition
from tether_engine.study.proofs import capture_file, capture_package_proof
from tests import test_study_authority_four_arm as fixtures


class AuthorityFourArmPeerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.CompositionLifecycleTests.setUpClass()
        cls.root = fixtures.CompositionLifecycleTests.root
        cls.result = fixtures.CompositionLifecycleTests.result

    @classmethod
    def tearDownClass(cls):
        fixtures.CompositionLifecycleTests.tearDownClass()

    def test_wrong_predecessor_identity_fails_before_recursive_replay(self):
        root = self.root / "peer-cycle"
        shutil.copytree(self.root / "good", root)
        # A malicious reseal changes only the predecessor's retained request.
        # It must fail identity before invoking recursive request validation.
        child = root / "cells/01"
        (child / "request.json").write_bytes(
            (root / "cells/02/request.json").read_bytes()
        )
        receipt = parse_json((child / "receipt.json").read_bytes())
        receipt["outputs"]["request.json"] = encode(
            capture_file(child / "request.json", "request.json")
        )
        (child / "receipt.json").write_bytes(canonical(receipt))
        events = encode(read_chain(root / "journal.jsonl"))
        previous = None
        for event in events:
            if event["event"] == "cell_accepted" and event["details"]["cell"] == 1:
                event["details"]["receipt_sha256"] = fingerprint(receipt)
            event.pop("sha256")
            event["previous_sha256"] = previous
            event["sha256"] = fingerprint(event)
            previous = event["sha256"]
        (root / "journal.jsonl").write_bytes(
            b"".join(canonical(e) + b"\n" for e in events)
        )
        verifier = composition.AuthorityRecordedVerifier(
            root, events[0]["details"]["run_id"], deadline=time.monotonic() + 120
        )
        original = composition.verify_study
        calls = []

        def bounded_verify(*args, **kwargs):
            calls.append(Path(args[0]))
            if len(calls) > 4:
                self.fail("Wrong predecessor identity entered recursive verification")
            return original(*args, **kwargs)

        with patch.object(composition, "verify_study", side_effect=bounded_verify):
            with self.assertRaises(ContractError):
                verifier.stage(2)

    def test_final_receipt_read_cannot_cross_replay_deadline(self):
        root = self.root / "good"
        now = [time.monotonic()]
        end = now[0] + 200
        original = composition._read
        reads = []

        def slow_last_read(directory, name):
            result = original(directory, name)
            if Path(directory) == root and name == "receipt.json":
                reads.append(name)
                if len(reads) == 2:
                    now[0] = end + 1
            return result

        with (
            patch.object(time, "monotonic", side_effect=lambda: now[0]),
            patch.object(composition, "_read", side_effect=slow_last_read),
        ):
            with self.assertRaises((TimeoutError, ContractError)):
                composition.verify(root, self.result["receipt_sha256"], deadline=end)
        self.assertEqual(len(reads), 2)

    def test_unexpected_outer_member_rejected_before_source_replay(self):
        root = self.root / "peer-extra"
        shutil.copytree(self.root / "good", root)
        (root / "caller-answer.json").write_bytes(b"{}")
        with patch.object(
            composition.AuthorityRecordedVerifier,
            "original",
            side_effect=AssertionError("No source replay"),
        ):
            with self.assertRaises(ContractError):
                composition.verify(root, self.result["receipt_sha256"])

    def test_resealed_child_resource_aliases_are_not_composition_authority(self):
        root = self.root / "peer-resource-alias"
        shutil.copytree(self.root / "good", root)
        child = root / "cells/05"
        config = parse_json((child / "configuration.json").read_bytes())
        resource_map = composition._resources()
        first, second = sorted(resource_map)[:2]
        resource_map[first], resource_map[second] = (
            resource_map[second],
            resource_map[first],
        )
        config["package_proof"] = encode(
            capture_package_proof(resource_map, composition.REQUIRED_RESOURCES)
        )
        (child / "configuration.json").write_bytes(canonical(config))
        events = encode(read_chain(child / "journal.jsonl"))
        previous = None
        for event in events:
            if event["event"] == "study_prepared":
                event["details"]["configuration_sha256"] = fingerprint(config)
            event.pop("sha256")
            event["previous_sha256"] = previous
            event["sha256"] = fingerprint(event)
            previous = event["sha256"]
        (child / "journal.jsonl").write_bytes(
            b"".join(canonical(e) + b"\n" for e in events)
        )
        receipt = parse_json((child / "receipt.json").read_bytes())
        for name in ("configuration.json", "journal.jsonl"):
            receipt["outputs"][name] = encode(capture_file(child / name, name))
        (child / "receipt.json").write_bytes(canonical(receipt))
        root_events = read_chain(root / "journal.jsonl")
        end = time.monotonic() + 200
        verifier = composition.AuthorityRecordedVerifier(
            root, root_events[0]["details"]["run_id"], deadline=end
        )
        stage = verifier.stage(5)
        policy = verifier.capacity(5, verifier.payload(stage))
        with self.assertRaises(ContractError):
            composition.verify_study(
                child,
                expected_receipt_sha256=fingerprint(receipt),
                verifier=verifier,
                capacity_policy=policy,
                deadline=end,
            )


if __name__ == "__main__":
    unittest.main()
