"""Executable fictional policy frames in self-contained temporary workspaces."""
from contextlib import redirect_stdout, redirect_stderr
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages/tether/src"))
from tether_engine.serde import ContractError, canonical, fingerprint
from tether_engine.derivations import registry_entry
from tether_engine.journal import read_chain
from tether import _catalog_policy as policy, _catalog_binding as binding, _presentation as layer, _cli as cli


if __package__:
    from .catalog_fixtures import argv, make_fixture, write
else:
    from catalog_fixtures import argv, make_fixture, write


class CatalogBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="binding-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.f = make_fixture(self.root)
        self.output = self.root / "outer"

    def test_archived_policy_roots_cannot_grant_external_access(self):
        self.output.mkdir()
        descriptor = binding.prepare_policy_run(self.output, self.f['request'])
        with self.assertRaisesRegex(ContractError, 'source-root'):
            binding.verify_policy_run(self.output, descriptor, check_engine=False)
        answer = binding.verify_policy_run(self.output, descriptor, check_engine=False, source_roots=(self.root,))
        self.assertEqual(answer['status'], 'artifact_policy_consistency_verified')

    def test_real_policy_run_preserves_nested_inputs_and_verifies(self):
        stream = io.StringIO()
        with redirect_stdout(stream), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(argv(self.f, self.output)), 0)
        receipt = json.loads(stream.getvalue())
        verified = layer.verify_outer(self.output, receipt["receipt_sha256"], source_roots=(self.root,))
        self.assertEqual(verified["artifact_policy"]["checked_inputs"], 3)
        self.assertEqual(verified["artifact_policy"]["status"], "artifact_policy_consistency_verified")
        self.assertTrue((self.output / "catalog-policy/inputs/references/mapping.json").is_file())
        self.assertTrue((self.output / "catalog-policy/inputs/packets/evidence.json").is_file())
        inputs = json.loads((self.output / "engine/inputs.json").read_text())
        self.assertEqual(inputs["snapshot_base"], str((self.output / "catalog-policy/inputs").resolve()))
        roles = {r["dataset_id"]: r["roles"] for r in inputs["catalog_policy"]["datasets"]}
        self.assertEqual(roles["fictional_answers"], ["evaluation_only"])

    def test_mutating_original_controls_after_preparation_does_not_change_execution(self):
        def engine(arguments):
            for path in (self.f["paths"]["case"], self.f["paths"]["snapshot"],
                         self.f["paths"]["policy"], self.f["paths"]["source_catalog"], self.f["paths"]["roots"],
                         self.root / "reports/fictional.json", self.f["normalized"] / "packets/evidence.json",
                         self.f["normalized"] / "references/mapping.json"):
                path.write_bytes(b'{"changed":true}')
            return layer.invoke_engine(arguments)
        result = layer.create_outer(self.output, argv(self.f, self.output), engine=engine, policy_request=self.f["request"], source_roots=(self.root,))
        verified = layer.verify_outer(self.output, result["receipt_sha256"], source_roots=(self.root,))
        self.assertEqual(verified["artifact_policy"]["status"], "artifact_policy_consistency_verified")

    def test_invalid_policy_source_catalog_and_frame_fail_before_dispatch(self):
        for kind in ("policy", "catalog", "frame"):
            with self.subTest(kind=kind):
                f = self.f
                request = copy.copy(f["request"])
                original_policy = f["paths"]["policy"].read_bytes()
                original_catalog = f["paths"]["source_catalog"].read_bytes()
                if kind == "policy":
                    changed = copy.deepcopy(f["policy"]); changed["uses"][0].update(status="blocked", blockers=["fictional blocked"])
                    write(f["paths"]["policy"], changed)
                elif kind == "catalog":
                    write(f["paths"]["source_catalog"], original_catalog + b"\n")
                else:
                    from dataclasses import replace
                    request = replace(request, frame_sha256="0" * 64)
                output = self.root / ("outer-" + kind)
                with patch.object(layer, "invoke_engine") as child, self.assertRaises(ContractError):
                    layer.create_outer(output, argv(f, output), policy_request=request, source_roots=(self.root,))
                child.assert_not_called()
                self.assertNotIn("engine_dispatch", [e["event"] for e in read_chain(output / layer.JOURNAL)])
                self.assertEqual(layer.inspect_outer(output)["failure"]["stage"], "artifact_policy_preflight")
                write(f["paths"]["policy"], original_policy); write(f["paths"]["source_catalog"], original_catalog)

    def test_receipt_mutation_before_child_is_rejected_without_backend_dispatch(self):
        original = self.f["raw_root"] / self.f["snapshot"]["sources"][0]["receipt_path"]
        before = original.read_bytes()
        def engine(arguments):
            original.write_bytes(before + b"\n")
            return layer.invoke_engine(arguments)
        with self.assertRaises(layer.EngineFailure):
            layer.create_outer(self.output, argv(self.f, self.output), engine=engine, policy_request=self.f["request"], source_roots=(self.root,))
        events = read_chain(self.output / "engine/journal.jsonl")
        self.assertNotIn("dispatch", [e["event"] for e in events])
        self.assertEqual(next((self.output / "catalog-policy/receipts").iterdir()).read_bytes(), before)
        self.assertFalse((self.output / layer.RECEIPT).exists())

    def test_extra_unused_source_is_checked_before_packet_read_or_dispatch(self):
        snapshot = copy.deepcopy(self.f["snapshot"])
        extra = copy.deepcopy(snapshot["sources"][0]); extra.update(source_id="unused", dataset_id="fictional_answers")
        snapshot["sources"].append(extra)
        document = copy.deepcopy(self.f["policy"]); document["uses"][0]["snapshot_fingerprint"] = fingerprint(snapshot)
        write(self.f["paths"]["snapshot"], snapshot); write(self.f["paths"]["policy"], document)
        # The packet is deliberately invalid: metadata rejection must come first.
        (self.f["normalized"] / "packets/evidence.json").write_bytes(b"not JSON")
        with patch.object(layer, "invoke_engine") as child, self.assertRaisesRegex(ContractError, "undeclared"):
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"], source_roots=(self.root,))
        child.assert_not_called()

    def test_projection_mutation_rejected_independently_of_engine(self):
        self.output.mkdir()
        descriptor = binding.prepare_policy_run(self.output, self.f["request"])
        path = self.output / "catalog-policy/projection.json"
        projection = json.loads(path.read_text()); projection["datasets"][0]["roles"] = ["reference"]
        write(path, projection)
        seal_path = self.output / descriptor["path"]
        seal = json.loads(seal_path.read_text())
        seal["controls"]["projection"] = binding._descriptor("catalog-policy/projection.json", path.read_bytes())
        write(seal_path, seal)
        descriptor = binding._descriptor(descriptor["path"], seal_path.read_bytes())
        with self.assertRaisesRegex(ContractError, "projection differs"):
            binding.verify_policy_run(self.output, descriptor, check_engine=False, source_roots=(self.root,))

    def test_wrong_receipt_identity_fails_even_with_updated_receipt_hash(self):
        node = self.f["snapshot"]["sources"][0]
        path = self.f["raw_root"] / node["receipt_path"]
        receipt = json.loads(path.read_text()); receipt["receipt_id"] = "wrong-id"
        write(path, receipt)
        node["receipt_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        document = self.f["policy"]
        document["artifacts"][0]["provenance"]["receipt"]["sha256"] = node["receipt_sha256"]
        document["uses"][0]["snapshot_fingerprint"] = fingerprint(self.f["snapshot"])
        write(self.f["paths"]["snapshot"], self.f["snapshot"]); write(self.f["paths"]["policy"], document)
        with patch.object(layer, "invoke_engine") as child, self.assertRaisesRegex(ContractError, "receipt receipt_id"):
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"], source_roots=(self.root,))
        child.assert_not_called()

    def test_unsupported_policy_combinations_never_dispatch(self):
        with redirect_stderr(io.StringIO()), patch.object(layer, "invoke_engine") as child:
            for option in ("--scorer", "--replay", "--local-model"):
                self.assertEqual(cli.main(argv(self.f, self.output) + [option, "fictional.json"]), 2)
            with self.assertRaises(SystemExit):
                cli.main(["demo", "--output", str(self.output), "--catalog-policy", str(self.f["paths"]["policy"])])
            self.assertEqual(cli.main(["run", "--case", str(self.f["paths"]["case"]), "--snapshot", str(self.f["paths"]["snapshot"]),
                                      "--output", str(self.output), "--policy-use", "fictional-use"]), 2)
        child.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_conflicting_archive_copy_never_overwrites(self):
        self.output.mkdir()
        original = self.output / "catalog-policy/policy.json"
        write(original, b"retained existing bytes")
        with self.assertRaises(FileExistsError):
            binding.prepare_policy_run(self.output, self.f["request"])
        self.assertEqual(original.read_bytes(), b"retained existing bytes")

    def test_provenance_bytes_must_be_checked_and_copied(self):
        (self.root / "reports/fictional.json").write_bytes(b"changed provenance")
        with patch.object(layer, "invoke_engine") as child, self.assertRaisesRegex(ContractError, "provenance hash"):
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"], source_roots=(self.root,))
        child.assert_not_called()

    def test_synthetic_demo_profile_cannot_silently_bypass_projection(self):
        snapshot = self.f["snapshot"]
        snapshot["profile"] = "synthetic_demo"
        self.f["policy"]["uses"][0].update(profile="synthetic_demo", snapshot_fingerprint=fingerprint(snapshot))
        write(self.f["paths"]["snapshot"], snapshot); write(self.f["paths"]["policy"], self.f["policy"])
        with patch.object(layer, "invoke_engine") as child, self.assertRaisesRegex(ContractError, "Synthetic demo profile"):
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"], source_roots=(self.root,))
        child.assert_not_called()

    def test_policy_output_reservation_is_exclusive_under_concurrency(self):
        calls = []
        def child(arguments):
            calls.append(arguments)
            return layer.EngineResult(3)
        def attempt(_):
            try:
                layer.create_outer(self.output, argv(self.f, self.output), engine=child, policy_request=self.f["request"], source_roots=(self.root,))
            except Exception as error:
                return type(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertCountEqual(results, [FileExistsError, layer.EngineFailure])
        self.assertEqual(len(calls), 1)
        self.assertIsNotNone(layer.inspect_outer(self.output)["failure"]["artifact_policy"])

    def test_policy_copy_write_failure_is_retained_without_dispatch(self):
        with patch.object(binding, "publish_bytes", side_effect=OSError("fictional write failure")), \
             patch.object(layer, "invoke_engine") as child, self.assertRaises(OSError):
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"], source_roots=(self.root,))
        child.assert_not_called()
        self.assertEqual(layer.inspect_outer(self.output)["failure"]["stage"], "artifact_policy_preflight")
        self.assertFalse((self.output / layer.RECEIPT).exists())

    def test_future_publication_still_excluded_during_pre_dispatch_admission(self):
        path = self.f["normalized"] / "packets/evidence.json"
        packet = json.loads(path.read_text())
        record = packet["observations"][0]
        record.update(publication_date="2024-01-01", publication_year=2024)
        write(path, packet)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        self.f["snapshot"]["artifacts"][0]["sha256"] = sha
        art = self.f["policy"]["artifacts"][-1]
        old = art["artifact_id"]
        art.update(sha256=sha, bytes=path.stat().st_size)
        art["artifact_id"] = policy.artifact_id(art)
        use = self.f["policy"]["uses"][0]
        for grant in use["grants"]:
            if grant["artifact_id"] == old:
                grant["artifact_id"] = art["artifact_id"]
        use["snapshot_fingerprint"] = fingerprint(self.f["snapshot"])
        write(self.f["paths"]["policy"], self.f["policy"]); write(self.f["paths"]["snapshot"], self.f["snapshot"])
        self.output.mkdir()
        with patch.object(layer, "invoke_engine") as child:
            binding.prepare_policy_run(self.output, self.f["request"])
        child.assert_not_called()
        from tether_engine.chrono import load_snapshot
        from tether_engine.contracts import Case
        from tether_engine.serde import decode
        store = load_snapshot(self.output / "catalog-policy/inputs/snapshot.json", decode(Case, self.f["case"]),
                              self.output / "catalog-policy/projection.json")
        self.assertTrue(any(item.item_id == record["observation_id"] and item.reason == "publication_after_origin"
                            for item in store.exclusions))


if __name__ == "__main__":
    unittest.main()
