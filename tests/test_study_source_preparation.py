import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from dataclasses import replace

from tether_engine.study.source_preparation import (
    PROFILE,
    RECIPE,
    validate_authority,
    compile_request,
    prepare_source_request,
    verify_source_preparation,
)
from tether_engine.study.source_rows import reconstruct_observation
from tether_engine.study.diagnostic import load_synthetic_request
from tether_engine.contracts import Case, Citation, GroundedObservation, Profile
from tether_engine.serde import ContractError, canonical, decode, encode, fingerprint, freeze


def authority():
    return dict(
        schema_version=1,
        profile=PROFILE,
        recipe=RECIPE,
        files={
            name: dict(
                root_id="project",
                relative_path=name + ".json",
                sha256="a" * 64,
                bytes=1,
            )
            for name in ("case", "snapshot", "catalog", "identifiers")
        },
        inputs={n: n for n in ("case", "snapshot", "catalog", "identifiers")},
        selection=dict(
            family="genetic-study-report.v1",
            max_claims=2,
            max_observations=256,
            observation_ids=["obs1"],
        ),
        expected_request_sha256=None,
    )


class SourceAuthorityTests(unittest.TestCase):
    def test_unanchored_shape_and_foreign_profile_rejected(self):
        for value in [{}, {"schema_version": 1, "profile": "evaluation_only"}]:
            with self.assertRaises(ContractError):
                validate_authority(value)

    def test_strict_authority_and_deep_immutability(self):
        a = validate_authority(authority())
        with self.assertRaises(TypeError):
            a["selection"]["max_claims"] = 9
        for change in [
            ("recipe", "unknown"),
            ("expected_request_sha256", "x"),
            ("schema_version", True),
        ]:
            x = authority()
            x[change[0]] = change[1]
            with self.assertRaises(ContractError):
                validate_authority(x)
        for ids in [[], ["a", "a"], [""]]:
            x = authority()
            x["selection"]["observation_ids"] = ids
            with self.assertRaises(ContractError):
                validate_authority(x)

    def test_no_foreign_fields_or_input_refs(self):
        x = authority()
        x["evaluator_answers"] = {}
        with self.assertRaises(ContractError):
            validate_authority(x)
        x = authority()
        x["inputs"]["case"] = "missing"
        with self.assertRaises(ContractError):
            validate_authority(x)


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.case = decode(
            Case,
            encode(load_synthetic_request("synthetic-context"))["source_request"][
                "case"
            ],
        )
        h = self.case.hypothesis
        obs = reconstruct_observation(
            dict(
                id="1",
                targetId=h.target_id,
                diseaseId=h.indication_id,
                datasourceId="europepmc",
                datatypeId="literature",
                score=0.4,
            ),
            symbol="X",
            disease_name="Y",
            locator=dict(source_id="raw", row_group=0, row=0),
            mapping_refs=("map",),
            availability=h.availability,
            cutoff=self.case.cutoff,
        )
        self.record = GroundedObservation(
            obs,
            Citation(
                "packet",
                "ot_evidence",
                "25.09",
                "b" * 64,
                "https://example.test/source",
            ),
        )
        self.selection = dict(
            family="genetic-study-report.v1",
            max_claims=2,
            max_observations=256,
            observation_ids=[obs.observation_id],
        )

    def store(self, record=None):
        record = record or self.record
        return SimpleNamespace(
            snapshot=SimpleNamespace(
                profile=Profile.CONTEMPORARY,
                snapshot_id="invented",
                coverage={"missing_input_count": 65},
            ),
            admitted_fingerprints={
                record.observation.observation_id: fingerprint(record)
            },
            query=lambda case, category: (record,)
            if category == record.observation.category
            else (),
        )

    def test_grounded_fingerprint_fields_and_coverage(self):
        request, selected = compile_request(self.case, self.store(), self.selection)
        row = request["source_request"]["evidence"][0]
        self.assertEqual(row["admitted_sha256"], fingerprint(self.record))
        self.assertNotEqual(
            row["admitted_sha256"], fingerprint(self.record.observation)
        )
        self.assertEqual(
            canonical(row["scientific_record"]), canonical(self.record.observation)
        )
        self.assertEqual(
            request["source_request"]["coverage"]["missing_input_count"], 65
        )
        self.assertFalse(request["source_request"]["coverage"]["absence_claim"])
        with self.assertRaises(TypeError):
            row["scientific_record"]["source_metrics"]["score"] = 99

    def test_nonempty_features_and_forged_admission_rejected(self):
        bad = replace(
            self.record,
            observation=replace(self.record.observation, features={"unvalidated": 1.0}),
        )
        with self.assertRaises(ContractError):
            compile_request(self.case, self.store(bad), self.selection)
        s = self.store()
        s.admitted_fingerprints[self.record.observation.observation_id] = fingerprint(
            self.record.observation
        )
        with self.assertRaises(ContractError):
            compile_request(self.case, s, self.selection)
        with self.assertRaises(ContractError):
            compile_request(
                self.case,
                self.store(),
                dict(self.selection, observation_ids=["foreign"]),
            )


class PublicationTests(unittest.TestCase):
    def fixture(self, root):
        path = root / "authority.json"
        raw = canonical(authority())
        path.write_bytes(raw)
        result = freeze(
            dict(
                request={"source": "invented"},
                source_audit={"whole_record_equal": True},
                source_proofs=[],
                request_sha256=fingerprint({"source": "invented"}),
                scientific_validation="not_performed",
                model_calls=0,
            )
        )
        return path, hashlib.sha256(raw).hexdigest(), result

    def test_publication_replay_anchor_tamper_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, anchor, result = self.fixture(root)
            out = root / "new"
            with patch("tether_engine.study.source_preparation._build", return_value=result):
                receipt = prepare_source_request(
                    a, anchor, {}, out, deadline=time.monotonic() + 299
                )
                checked = verify_source_preparation(
                    out,
                    receipt["receipt_sha256"],
                    anchor,
                    {},
                    deadline=time.monotonic() + 299,
                )
                self.assertEqual(checked["status"], "verified")
                with self.assertRaises(FileExistsError):
                    prepare_source_request(
                        a, anchor, {}, out, deadline=time.monotonic() + 299
                    )
                with self.assertRaises(ContractError):
                    verify_source_preparation(
                        out, "0" * 64, anchor, {}, deadline=time.monotonic() + 299
                    )
                (out / "request.json").write_text("{}")
                with self.assertRaises(ContractError):
                    verify_source_preparation(
                        out,
                        receipt["receipt_sha256"],
                        anchor,
                        {},
                        deadline=time.monotonic() + 299,
                    )

    def test_failed_anchor_and_interruption_are_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, anchor, result = self.fixture(root)
            with patch("tether_engine.study.source_preparation._build") as build:
                with self.assertRaises(ContractError):
                    prepare_source_request(
                        a, "0" * 64, {}, root / "bad", deadline=time.monotonic() + 299
                    )
                build.assert_not_called()
            self.assertTrue((root / "bad/failure.json").is_file())
            with patch(
                "tether_engine.study.source_preparation._build", side_effect=KeyboardInterrupt
            ):
                with self.assertRaises(KeyboardInterrupt):
                    prepare_source_request(
                        a,
                        anchor,
                        {},
                        root / "interrupt",
                        deadline=time.monotonic() + 299,
                    )
            self.assertEqual(
                json.loads((root / "interrupt/failure.json").read_bytes())[
                    "error_class"
                ],
                "KeyboardInterrupt",
            )
            self.assertFalse((root / "interrupt/receipt.json").exists())

    def test_concurrent_reservation_one_failure_record_no_clobber(self):
        from concurrent.futures import ThreadPoolExecutor

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, anchor, result = self.fixture(root)
            out = root / "concurrent"

            def attempt():
                try:
                    prepare_source_request(
                        a, "0" * 64, {}, out, deadline=time.monotonic() + 299
                    )
                except BaseException as error:
                    return type(error).__name__

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(lambda _: attempt(), range(2)))
            self.assertCountEqual(outcomes, ["ContractError", "FileExistsError"])
            original = (out / "failure.json").read_bytes()
            with self.assertRaises(FileExistsError):
                prepare_source_request(
                    a, anchor, {}, out, deadline=time.monotonic() + 299
                )
            self.assertEqual((out / "failure.json").read_bytes(), original)

    def test_publication_write_failure_keeps_primary_error(self):
        from tether_engine.atomic import publish_bytes

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, anchor, result = self.fixture(root)
            out = root / "write-failure"

            def fail_request(path, data):
                if Path(path).name == "request.json":
                    raise OSError("injected write failure")
                return publish_bytes(path, data)

            with (
                patch("tether_engine.study.source_preparation._build", return_value=result),
                patch(
                    "tether_engine.study.source_preparation.publish_bytes",
                    side_effect=fail_request,
                ),
            ):
                with self.assertRaisesRegex(OSError, "injected write failure"):
                    prepare_source_request(
                        a, anchor, {}, out, deadline=time.monotonic() + 299
                    )
            self.assertTrue((out / "failure.json").exists())
            self.assertFalse((out / "receipt.json").exists())


class PreReadBoundaryTests(unittest.TestCase):
    def test_protected_primary_path_is_rejected_before_read_or_lock(self):
        from tether_engine.study.source_preparation import _build

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = authority()
            for name in a["files"]:
                (root / (name + ".json")).write_text("{}")
            protected = root / "gold_evidence"
            protected.mkdir()
            (protected / "case.json").write_text("DO NOT READ")
            a["files"]["case"]["relative_path"] = "gold_evidence/case.json"
            with (
                patch("tether_engine.study.stable_read.stable_files") as locks,
                patch("tether_engine.study.stable_read.hash_file") as hashes,
            ):
                with self.assertRaises(ContractError):
                    _build(
                        validate_authority(a), {"project": root}, time.monotonic() + 299
                    )
                locks.assert_not_called()
                hashes.assert_not_called()

    def test_future_graph_node_never_hashed(self):
        from tether_engine.study.source_preparation import _build
        from contextlib import nullcontext

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = authority()
            for name in list(a["files"]) + ["raw"]:
                path = root / (name + ".json")
                path.write_text("{}")
                a["files"][name] = dict(
                    root_id="project",
                    relative_path=path.name,
                    sha256=hashlib.sha256(b"{}").hexdigest(),
                    bytes=2,
                )
            case = SimpleNamespace(task="T6", validate=lambda: None)
            node = SimpleNamespace(source_id="raw", receipt_path=None)
            snapshot = SimpleNamespace(
                profile=Profile.CONTEMPORARY,
                sources=(node,),
                artifacts=(),
                raw_root=str(root),
            )
            graph = SimpleNamespace(
                exclusion=lambda refs, case: "available_after_origin",
                path=lambda node: root / "raw.json",
            )
            from tether_engine.study.stable_read import hash_file

            with (
                patch(
                    "tether_engine.study.stable_read.stable_files",
                    side_effect=lambda *a, **kw: nullcontext(),
                ),
                patch(
                    "tether_engine.study.source_preparation.decode", side_effect=[case, snapshot]
                ),
                patch("tether_engine.study.source_preparation.catalog_index", return_value={}),
                patch("tether_engine.study.source_preparation.InputGraph", return_value=graph),
                patch("tether_engine.study.stable_read.hash_file", wraps=hash_file) as hashing,
            ):
                with self.assertRaisesRegex(ContractError, "Ineligible source"):
                    _build(
                        validate_authority(a), {"project": root}, time.monotonic() + 299
                    )
                self.assertNotIn(
                    root / "raw.json", [call.args[0] for call in hashing.call_args_list]
                )

    def test_hgnc_reference_directory_not_blanket_denied(self):
        from tether_engine.study.source_preparation import _source_path_guard

        _source_path_guard(Path("data/reference/hgnc_symbols/source.txt"))
        for name in [
            "data/benchmark/labels/outcomes.json",
            "data/cache/normalized-outcomes.json",
            "runs/x/raw-response.bin",
        ]:
            with self.assertRaises(ContractError):
                _source_path_guard(Path(name))
