"""Independent retrieval-boundary probes; invented inputs, no model or real data."""

from pathlib import Path
from contextlib import nullcontext
import hashlib
import json
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, encode, fingerprint
from tether_engine.study import retrieval_preparation as rp
from tether_engine.study.diagnostic_codec import bind_question
from tests import test_study_retrieval_preparation as own_fixtures

TEMP = Path(__file__).resolve().parents[1] / "data/cache"


def fixture():
    authority = rp.fixture_authority()
    anchor = rp.authority_anchor(authority)
    universe = rp.qualify_universe(authority, anchor, deadline=time.monotonic() + 299)
    policy = rp.policy_for("id_order_v1")
    result = rp.retrieve(universe, policy, anchor, deadline=time.monotonic() + 299)
    return anchor, universe, result


class RetrievalPeerTests(unittest.TestCase):
    def test_qualification_does_not_return_mutated_caller_authority(self):
        authority = encode(rp.fixture_authority())
        anchor = fingerprint(authority)
        original = rp._synthetic

        def mutate_after_validating(value):
            result = original(value)
            authority["fixture"] = "invented-empty-v1"
            return result

        with patch.object(rp, "_synthetic", side_effect=mutate_after_validating):
            try:
                universe = rp.qualify_universe(
                    authority, anchor, deadline=time.monotonic() + 299
                )
            except ContractError:
                return
        self.assertEqual(fingerprint(universe["authority"]), anchor)

    def test_retrieval_does_not_return_policy_changed_after_selection(self):
        anchor, universe, _ = fixture()
        policy = encode(rp.policy_for("id_order_v1"))
        original_policy = canonical(policy)
        original = rp._select

        def mutate_after_selection(*args):
            value = original(*args)
            policy["max_records"] = 99
            return value

        with patch.object(rp, "_select", side_effect=mutate_after_selection):
            try:
                result = rp.retrieve(
                    universe, policy, anchor, deadline=time.monotonic() + 299
                )
            except ContractError:
                return
        self.assertEqual(canonical(result["policy"]), original_policy)

    def test_sorted_real_authority_membership_preserves_reversed_parent_order(self):
        """Mock only trusted parent gate; this does not establish real admission."""
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            root = Path(tmp)
            authority, request = own_fixtures.RealParentRecoveryUnitTests().make_parent(
                root
            )
            source = request["source_request"]
            source["evidence"].reverse()
            request = bind_question(source, request["question"]["question_id"])
            raw = canonical(request)
            folder = root / "parent"
            (folder / "request.json").write_bytes(raw)
            receipt = json.loads((folder / "receipt.json").read_bytes())
            receipt["files"]["request.json"].update(
                sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)
            )
            raw_receipt = canonical(receipt)
            (folder / "receipt.json").write_bytes(raw_receipt)
            authority["parent_receipt_sha256"] = hashlib.sha256(raw_receipt).hexdigest()
            authority["request_sha256"] = fingerprint(request)
            authority["candidate_ids"] = sorted(authority["candidate_ids"])
            anchor = fingerprint(authority)
            with (
                patch.object(rp, "verify_source_preparation"),
                patch.object(
                    rp, "stable_files", side_effect=lambda *a, **kw: nullcontext()
                ),
            ):
                universe = rp.qualify_universe(
                    authority,
                    anchor,
                    roots={"project": root},
                    deadline=time.monotonic() + 299,
                )
                result = rp.retrieve(
                    universe,
                    rp.policy_for("id_order_v1"),
                    anchor,
                    roots={"project": root},
                    deadline=time.monotonic() + 299,
                )
                compiled = rp.compile_retrieved(
                    universe,
                    result,
                    anchor,
                    roots={"project": root},
                    deadline=time.monotonic() + 299,
                )
            self.assertEqual(
                [
                    r["observation_id"]
                    for r in compiled["request"]["source_request"]["evidence"]
                ],
                ["id02", "id01"],
            )
            self.assertEqual(compiled["coverage"]["parent_observations_available"], 99)

    def test_compiler_uses_authenticated_snapshot_not_changed_caller_mapping(self):
        anchor, universe, result = fixture()
        mutable = encode(universe)
        expected = mutable["request"]["source_request"]["evidence"][0]["statement"]
        original = rp.retrieve

        def change_after_authentication(*args, **kwargs):
            value = original(*args, **kwargs)
            row = mutable["request"]["source_request"]["evidence"][0]
            row["statement"] = "Changed after authentication; not in original source."
            row["scientific_record"]["statement"] = row["statement"]
            return value

        with patch.object(rp, "retrieve", side_effect=change_after_authentication):
            try:
                compiled = rp.compile_retrieved(
                    mutable, result, anchor, deadline=time.monotonic() + 299
                )
            except ContractError:
                return  # Rejecting the concurrent change is also safe.
        self.assertEqual(
            compiled["request"]["source_request"]["evidence"][0]["statement"], expected
        )

    def test_protected_parent_path_fails_before_parent_verifier_reads(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            root = Path(tmp)
            (root / "labels/pretend-parent").mkdir(parents=True)
            authority = dict(
                schema_version=1,
                kind="real_source_preparation",
                parent=dict(root_id="test", relative_path="labels/pretend-parent"),
                parent_receipt_sha256="a" * 64,
                source_authority_sha256="b" * 64,
                candidate_ids=["invented"],
                grounded_fingerprints={"invented": "c" * 64},
                category="literature",
                request_sha256="d" * 64,
            )
            with patch.object(
                rp,
                "verify_source_preparation",
                side_effect=AssertionError("protected parent reader reached"),
            ) as reader:
                with self.assertRaises(ContractError):
                    rp.qualify_universe(
                        authority,
                        fingerprint(authority),
                        roots={"test": root},
                        deadline=time.monotonic() + 299,
                    )
                reader.assert_not_called()


class RetrievalSmokePeerTests(unittest.TestCase):
    def test_second_policy_never_dispatches_after_shared_deadline_expires(self):
        from tether_engine.study import retrieval_smoke as smoke

        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            output = Path(tmp) / "expired-second"
            clock = [0.0]
            append = smoke.RunJournal.append
            generate = smoke.DeadlineRecordedBackend.generate

            def expire_after_first_accept(journal, event, **details):
                result = append(journal, event, **details)
                if event == "cell_accepted":
                    clock[0] = 301.0
                return result

            with (
                patch.object(smoke.time, "monotonic", side_effect=lambda: clock[0]),
                patch.object(smoke.RunJournal, "append", new=expire_after_first_accept),
                patch.object(
                    smoke.DeadlineRecordedBackend,
                    "generate",
                    autospec=True,
                    side_effect=generate,
                ) as dispatch,
            ):
                with self.assertRaises(ContractError):
                    smoke.smoke(output)
            self.assertEqual(dispatch.call_count, 1)
            self.assertFalse(
                (output / "cells/literal_case_overlap_then_id_v1").exists()
            )
            self.assertFalse((output / "receipt.json").exists())
            self.assertEqual(
                json.loads((output / "failure.json").read_bytes())["accepted_cells"],
                ["id_order_v1"],
            )

    def test_final_artifact_capture_cannot_publish_after_shared_deadline(self):
        from tether_engine.study import retrieval_smoke as smoke

        with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
            output = Path(tmp) / "late-seal"
            clock = [0.0]
            original = smoke.capture_file

            def late_capture(path, logical_id):
                result = original(path, logical_id)
                if Path(path) == output / "summary.json":
                    clock[0] = 301.0
                return result

            with (
                patch.object(smoke.time, "monotonic", side_effect=lambda: clock[0]),
                patch.object(smoke, "capture_file", side_effect=late_capture),
            ):
                with self.assertRaises(ContractError):
                    smoke.smoke(output)
            self.assertFalse((output / "receipt.json").exists())
            self.assertTrue((output / "failure.json").exists())
