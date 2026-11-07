import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from tether_engine.agents import make_request
from tether_engine.contracts import Category
from tether_engine.serde import ContractError, canonical, encode, fingerprint
from tether_engine.study import retrieval_preparation as rp


def prepared(name="invented-six-v1"):
    authority = rp.fixture_authority(name)
    anchor = rp.authority_anchor(authority)
    return (
        authority,
        anchor,
        rp.qualify_universe(authority, anchor, deadline=time.monotonic() + 299),
    )


def reseal(root):
    receipt = json.loads((root / "receipt.json").read_bytes())
    for name in receipt["files"]:
        raw = (root / name).read_bytes()
        receipt["files"][name] = dict(
            logical_id=name, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)
        )
    (root / "receipt.json").write_bytes(canonical(receipt))
    return fingerprint(receipt)


class RetrievalContractTests(unittest.TestCase):
    def test_named_fixture_and_distinct_policies(self):
        a, h, u = prepared()
        self.assertEqual(a["fixture"], "invented-six-v1")
        choices = {
            s: list(
                rp.retrieve(u, rp.policy_for(s), h, deadline=time.monotonic() + 299)[
                    "selected_ids"
                ]
            )
            for s in ("id_order_v1", "literal_case_overlap_then_id_v1")
        }
        self.assertEqual(
            choices,
            {
                "id_order_v1": ["id01", "id02"],
                "literal_case_overlap_then_id_v1": ["id03", "id04"],
            },
        )

    def test_oversized_first_is_reported_and_not_clipped(self):
        a, h, u = prepared()
        r = rp.retrieve(
            u,
            rp.policy_for("literal_case_overlap_then_id_v1"),
            h,
            deadline=time.monotonic() + 299,
        )
        self.assertEqual(
            r["retrieval_audit"]["excluded"][0],
            {"observation_id": "id06", "reason": "whole_record_exceeds_byte_cap"},
        )
        compiled = rp.compile_retrieved(u, r, h, deadline=time.monotonic() + 299)
        self.assertEqual(compiled["coverage"]["declared_candidates"], 6)
        self.assertEqual(compiled["coverage"]["selected_count"], 2)
        self.assertFalse(compiled["coverage"]["absence_claim"])

    def test_original_fields_and_parent_denominators_preserved(self):
        a, h, u = prepared()
        r = rp.retrieve(
            u, rp.policy_for("id_order_v1"), h, deadline=time.monotonic() + 299
        )
        c = rp.compile_retrieved(u, r, h, deadline=time.monotonic() + 299)["request"]
        parent = encode(u["request"]["source_request"])
        expected = copy.deepcopy(parent)
        expected["evidence"] = parent["evidence"][:2]
        expected["coverage"]["observations_visible"] = 2
        self.assertEqual(encode(c["source_request"]), expected)
        self.assertEqual(c["source_request"]["coverage"]["observations_available"], 6)
        self.assertTrue(
            all(
                "feature_applicability" not in x["scientific_record"]
                for x in c["source_request"]["evidence"]
            )
        )
        with self.assertRaises(TypeError):
            c["source_request"]["evidence"][0]["scientific_record"]["features"]["x"] = 1

    def test_changed_excluded_record_and_forged_instance_rejected(self):
        a, h, u = prepared()
        bad = encode(u)
        bad["request"]["source_request"]["evidence"][-1]["scientific_record"][
            "statement"
        ] = "changed excluded source"
        with self.assertRaises(ContractError):
            rp.retrieve(
                bad, rp.policy_for("id_order_v1"), h, deadline=time.monotonic() + 299
            )
        with self.assertRaises(ContractError):
            rp.qualify_universe(
                dict(encode(a), kind="real_source_preparation"),
                h,
                deadline=time.monotonic() + 299,
            )
        with self.assertRaises(ContractError):
            rp.retrieve(
                u,
                rp.policy_for("id_order_v1"),
                "0" * 64,
                deadline=time.monotonic() + 299,
            )

    def test_result_policy_ids_and_source_changes_fail(self):
        a, h, u = prepared()
        r = rp.retrieve(
            u, rp.policy_for("id_order_v1"), h, deadline=time.monotonic() + 299
        )
        for field, value in [
            ("selected_ids", ["id06"]),
            ("source_request_sha256", "0" * 64),
            ("scientific_answer_status", "answered"),
        ]:
            bad = encode(r)
            bad[field] = value
            with self.assertRaises(ContractError):
                rp.compile_retrieved(u, bad, h, deadline=time.monotonic() + 299)
        with self.assertRaises(ContractError):
            rp.retrieve(
                u,
                dict(encode(rp.policy_for("id_order_v1")), max_records=3),
                h,
                deadline=time.monotonic() + 299,
            )

    def test_empty_and_all_overcap_are_distinct_declared_results(self):
        states = []
        for name in ["invented-empty-v1", "invented-overcap-v1"]:
            a, h, u = prepared(name)
            r = rp.retrieve(
                u, rp.policy_for("id_order_v1"), h, deadline=time.monotonic() + 299
            )
            c = rp.compile_retrieved(u, r, h, deadline=time.monotonic() + 299)
            self.assertIsNone(c["request"])
            states.append(c["coverage"]["status"])
        self.assertEqual(
            states, ["empty_declared_universe", "all_whole_records_excluded"]
        )
        with self.assertRaises(ContractError):
            rp.fixture_authority("arbitrary-empty")

    def test_reverse_ranking_input_preserves_ties_and_zero_overlap_rule(self):
        a, h, u = prepared()
        case, records = rp._records(u["request"])
        request = make_request(case, Category.LITERATURE, records)
        for strategy in ["id_order_v1", "literal_case_overlap_then_id_v1"]:
            left, _ = rp._select(request, rp.policy_for(strategy))
            right, _ = rp._select(
                replace(request, evidence=tuple(reversed(request.evidence))),
                rp.policy_for(strategy),
            )
            self.assertEqual(
                [x.observation_id for x in left.evidence],
                [x.observation_id for x in right.evidence],
            )
        zero = replace(
            request,
            evidence=tuple(
                replace(x, statement="zzz qqq vvv") for x in request.evidence[:2]
            ),
        )
        selected, _ = rp._select(zero, rp.policy_for("literal_case_overlap_then_id_v1"))
        self.assertEqual(len(selected.evidence), 2)

    def test_resource_tamper_and_deadline_rejected(self):
        with patch.dict(rp.RESOURCE_HASHES, {rp.CORPUS: "0" * 64}):
            with self.assertRaises(ContractError):
                rp.fixture_authority()
        a, h, u = prepared()
        with self.assertRaises(TimeoutError):
            rp.retrieve(
                u, rp.policy_for("id_order_v1"), h, deadline=time.monotonic() - 1
            )


class RetrievalPublicationTests(unittest.TestCase):
    def create(self, root):
        a = rp.fixture_authority()
        h = rp.authority_anchor(a)
        result = rp.prepare_retrieval(
            a, h, rp.policy_for("id_order_v1"), root, deadline=time.monotonic() + 299
        )
        return h, result

    def test_roundtrip_access_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            h, result = self.create(root)
            verified = rp.verify_retrieval_preparation(
                root, result["receipt_sha256"], h, deadline=time.monotonic() + 299
            )
            self.assertEqual(verified["status"], "verified")
            self.assertEqual(verified["model_calls"], 0)
            access = json.loads((root / "access-manifest.json").read_bytes())
            self.assertEqual(len({canonical(v) for v in access.values()}), 1)
            with self.assertRaises(FileExistsError):
                self.create(root)
            with self.assertRaises(ContractError):
                rp.verify_retrieval_preparation(
                    root, "0" * 64, h, deadline=time.monotonic() + 299
                )

    def test_resealed_coverage_and_resource_paths_fail_semantics(self):
        for member in ["coverage.json", "package-proof.json"]:
            with self.subTest(member=member), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                h, result = self.create(root)
                doc = json.loads((root / member).read_bytes())
                if member == "coverage.json":
                    doc["parent_observations_available"] = 2
                else:
                    names = list(doc["resources"])
                    doc["resources"][names[0]], doc["resources"][names[1]] = (
                        doc["resources"][names[1]],
                        doc["resources"][names[0]],
                    )
                (root / member).write_bytes(canonical(doc))
                anchor = reseal(root)
                with self.assertRaises(ContractError):
                    rp.verify_retrieval_preparation(
                        root, anchor, h, deadline=time.monotonic() + 299
                    )

    def test_extra_file_and_request_tamper_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            h, result = self.create(root)
            (root / "extra.json").write_text("{}")
            with self.assertRaises(ContractError):
                rp.verify_retrieval_preparation(
                    root, result["receipt_sha256"], h, deadline=time.monotonic() + 299
                )
            (root / "extra.json").unlink()
            doc = json.loads((root / "request.json").read_bytes())
            doc["source_request"]["evidence"][0]["scientific_record"]["statement"] = (
                "modified"
            )
            (root / "request.json").write_bytes(canonical(doc))
            with self.assertRaises(ContractError):
                rp.verify_retrieval_preparation(
                    root, reseal(root), h, deadline=time.monotonic() + 299
                )

    def test_interruption_and_concurrent_reservation_remain_readable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            with patch.object(rp, "qualify_universe", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    self.create(root)
            self.assertTrue((root / "failure.json").exists())
            self.assertFalse((root / "receipt.json").exists())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "same"
            a = rp.fixture_authority()

            def attempt():
                try:
                    rp.prepare_retrieval(
                        a,
                        "0" * 64,
                        rp.policy_for("id_order_v1"),
                        root,
                        deadline=time.monotonic() + 299,
                    )
                except BaseException as e:
                    return type(e).__name__

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(lambda _: attempt(), range(2)))
            self.assertCountEqual(outcomes, ["ContractError", "FileExistsError"])

    def test_expiry_during_sealing_cannot_publish_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            clock = [0.0]
            calls = [0]
            original = rp._package_check

            def check(proof):
                original(proof)
                calls[0] += 1
                if calls[0] == 2:
                    clock[0] = 301

            a = rp.fixture_authority()
            h = rp.authority_anchor(a)
            with (
                patch("time.monotonic", side_effect=lambda: clock[0]),
                patch.object(rp, "_package_check", side_effect=check),
            ):
                with self.assertRaises(TimeoutError):
                    rp.prepare_retrieval(
                        a, h, rp.policy_for("id_order_v1"), root, deadline=299
                    )
            self.assertFalse((root / "receipt.json").exists())
            self.assertTrue((root / "failure.json").exists())


class RealParentRecoveryUnitTests(unittest.TestCase):
    """Invented files and explicitly mocked trusted source gate, never real admission."""

    def make_parent(self, root):
        _, _, u = prepared()
        request = encode(u["request"])
        request["source_request"]["coverage"].update(
            observations_available=99,
            missing_input_count=65,
            missing_count_basis="snapshot_declaration",
        )
        case, records = rp._records(request)
        parent = root / "parent"
        parent.mkdir()
        audit = {
            "selected_rows": [
                dict(
                    observation_id=r.observation.observation_id,
                    whole_record_equal=True,
                    observation_sha256=fingerprint(r.observation),
                )
                for r in records
            ]
        }
        files = {}
        for name, value in [("request.json", request), ("source-audit.json", audit)]:
            raw = canonical(value)
            (parent / name).write_bytes(raw)
            files[name] = dict(
                logical_id=name, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)
            )
        receipt = dict(files=files)
        raw = canonical(receipt)
        (parent / "receipt.json").write_bytes(raw)
        authority = dict(
            schema_version=1,
            kind="real_source_preparation",
            parent=dict(root_id="project", relative_path="parent"),
            parent_receipt_sha256=hashlib.sha256(raw).hexdigest(),
            source_authority_sha256="a" * 64,
            candidate_ids=[r.observation.observation_id for r in records],
            grounded_fingerprints={
                r.observation.observation_id: fingerprint(r) for r in records
            },
            category="literature",
            request_sha256=fingerprint(request),
        )
        return authority, request

    def test_verified_parent_subset_preserves_full_available_and_missing_counts(self):
        from contextlib import nullcontext

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, parent = self.make_parent(root)
            h = fingerprint(a)
            with (
                patch.object(rp, "verify_source_preparation") as gate,
                patch.object(
                    rp, "stable_files", side_effect=lambda *a, **kw: nullcontext()
                ),
            ):
                u = rp.qualify_universe(
                    a, h, roots={"project": root}, deadline=time.monotonic() + 299
                )
                r = rp.retrieve(
                    u,
                    rp.policy_for("id_order_v1"),
                    h,
                    roots={"project": root},
                    deadline=time.monotonic() + 299,
                )
                c = rp.compile_retrieved(
                    u, r, h, roots={"project": root}, deadline=time.monotonic() + 299
                )["request"]
                self.assertGreaterEqual(gate.call_count, 3)
            expected = copy.deepcopy(parent["source_request"])
            expected["evidence"] = expected["evidence"][:2]
            expected["coverage"]["observations_visible"] = 2
            self.assertEqual(encode(c["source_request"]), expected)
            self.assertEqual(
                c["source_request"]["coverage"]["observations_available"], 99
            )
            self.assertEqual(c["source_request"]["coverage"]["missing_input_count"], 65)

    def test_parent_verifier_failure_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, _ = self.make_parent(root)
            with (
                patch.object(
                    rp,
                    "verify_source_preparation",
                    side_effect=ContractError("old package"),
                ),
                patch.object(rp, "read_file") as read,
            ):
                with self.assertRaisesRegex(ContractError, "old package"):
                    rp.qualify_universe(
                        a,
                        fingerprint(a),
                        roots={"project": root},
                        deadline=time.monotonic() + 299,
                    )
                read.assert_not_called()

    def test_missing_excluded_raw_audit_is_rejected(self):
        from contextlib import nullcontext

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, _ = self.make_parent(root)
            path = root / "parent/source-audit.json"
            doc = json.loads(path.read_bytes())
            doc["selected_rows"].pop()
            path.write_bytes(canonical(doc))
            receipt = json.loads((root / "parent/receipt.json").read_bytes())
            receipt["files"]["source-audit.json"].update(
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                bytes=path.stat().st_size,
            )
            raw = canonical(receipt)
            (root / "parent/receipt.json").write_bytes(raw)
            a["parent_receipt_sha256"] = hashlib.sha256(raw).hexdigest()
            with (
                patch.object(rp, "verify_source_preparation"),
                patch.object(
                    rp, "stable_files", side_effect=lambda *a, **kw: nullcontext()
                ),
            ):
                with self.assertRaisesRegex(ContractError, "All candidates"):
                    rp.qualify_universe(
                        a,
                        fingerprint(a),
                        roots={"project": root},
                        deadline=time.monotonic() + 299,
                    )
