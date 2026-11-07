"""Executable fictional policy frames; all generated files stay in project cache."""
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
from tether_engine.journal import read_chain
from tether import _catalog_policy as policy, _catalog_binding as binding, _presentation as layer, _cli as cli


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else canonical(value) + b"\n")


def make_fixture(root):
    """Complete synthetic engine contracts plus exact policy grants and receipts."""
    root = Path(root).absolute()
    normalized, raw_root = root / "normalized", root / "raw"
    normalized.mkdir(); raw_root.mkdir()
    base = ROOT / "src/tether_engine/demo/v2"
    case = json.loads((base / "case.json").read_text())
    snapshot = json.loads((base / "snapshot.json").read_text())
    snapshot["profile"] = "contemporary_assessment"
    snapshot["sources"] = snapshot["sources"][:1]
    snapshot["artifacts"] = snapshot["artifacts"][:1]
    snapshot["raw_root"] = str(raw_root)
    raw = (base / "raw-inputs.json").read_bytes()
    node = snapshot["sources"][0]
    node["path"] = "originals/raw-inputs.json"
    write(raw_root / node["path"], raw)
    receipt = dict(receipt_id="fictional-original", dataset_id=node["dataset_id"], release_id=node["release_id"],
                   relative_path=node["path"].replace("/", "\\"), sha256=node["sha256"], bytes=len(raw), url=node["source_url"],
                   status="completed", completed_at_utc="2022-01-01T00:00:00+00:00")
    receipt_bytes = canonical(receipt) + b"\n"
    node.update(receipt_path="receipt-archive/original.json", receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest())
    write(raw_root / node["receipt_path"], receipt_bytes)
    mapping = dict(source_id="fictional-mapping", dataset_id="synthetic_reference", release_id="fixture-v1",
        path="references/mapping.json", sha256=hashlib.sha256(b'{"fictional":true}\n').hexdigest(), role="reference",
        availability=copy.deepcopy(node["availability"]), temporal_classification=node["temporal_classification"],
        source_url="https://example.invalid/mapping", parents=[node["source_id"]],
        computed_at="2026-01-01T00:00:00+00:00", method_id="fictional-normalization", method_version="1")
    snapshot["sources"].append(mapping)
    write(normalized / mapping["path"], b'{"fictional":true}\n')
    artifact = snapshot["artifacts"][0]
    artifact.update(path="packets/evidence.json", input_refs=[mapping["source_id"]])
    write(normalized / artifact["path"], (base / "evidence.json").read_bytes())
    source_bytes = canonical(dict(schema_version=1, providers=[dict(provider_id="fictional")], datasets=[
        dict(dataset_id=key, provider_id="fictional", roles=roles, dependencies=[], collection_status="planned",
             parse_status="not_run", validation_status="not_run")
        for key, roles in (("synthetic_fixture", ["agent_evidence"]), ("synthetic_reference", ["reference"]),
                           ("fictional_answers", ["evaluation_only", "reference"]))]))
    document = policy.migrate_catalog(source_bytes, source_path="data/catalog/sources.json",
                                      policy_id="fictional-policy", created_at_utc="2026-11-02T00:00:00Z")
    for product in document["products"][:2]:
        product["dependency_review_status"] = "reviewed_for_selected_frame"
    records, by_node = [], {}
    proof_bytes = b'{"kind":"fictional provenance"}\n'
    write(root / "reports/fictional.json", proof_bytes)
    for entry, kind, alias in ((node, "raw", "raw"), (mapping, "derived", "snapshot"), (artifact, "packet", "snapshot")):
        path = (raw_root if kind == "raw" else normalized) / entry["path"]
        parents = entry.get("parents", entry.get("input_refs", []))
        provenance = dict(kind="download_receipt" if kind == "raw" else "generated",
            evidence=[dict(path="reports/fictional.json", sha256=hashlib.sha256(proof_bytes).hexdigest())],
            receipt=(dict(root_alias="raw", relative_path=node["receipt_path"], sha256=node["receipt_sha256"],
                          receipt_id=receipt["receipt_id"], url=node["source_url"]) if kind == "raw" else None))
        record = policy.artifact_record(dataset_id=entry["dataset_id"], release_id=entry["release_id"],
            root_alias=alias, relative_path=entry["path"], sha256=entry["sha256"], bytes=path.stat().st_size,
            kind=kind, parents=[by_node[p]["artifact_id"] for p in parents], availability=entry["availability"],
            temporal_classification=entry["temporal_classification"], source_url=entry["source_url"],
            provenance=provenance, scope="Fictional integration fixture", scientific_validation="not_established")
        by_node[entry.get("source_id", entry.get("artifact_id"))] = record
        records.append(record)
    document["artifacts"] = records
    document["uses"] = [dict(use_id="fictional-use", kind="contemporary_evidence", status="allowed",
        profile=snapshot["profile"], origin_at=case["origin_at"], frame_sha256="f" * 64,
        case_fingerprint=fingerprint(case), snapshot_fingerprint=fingerprint(snapshot),
        raw_root_alias="raw", snapshot_root_alias="snapshot",
        grants=[dict(artifact_id=r["artifact_id"], role="reference" if r["kind"] == "derived" else "agent_evidence")
                for r in records], blockers=[])]
    roots = dict(schema_version=1, roots=dict(raw=str(raw_root), snapshot=str(normalized), metadata=str(root)))
    paths = dict(policy=root / "policy.json", roots=root / "roots.json", case=root / "case.json",
                 snapshot=normalized / "snapshot.json", source_catalog=root / "data/catalog/sources.json")
    for key, value in (("policy", document), ("roots", roots), ("case", case), ("snapshot", snapshot), ("source_catalog", source_bytes)):
        write(paths[key], value)
    request = binding.PolicyRequest(paths["policy"], paths["roots"], paths["case"], paths["snapshot"],
                                    paths["source_catalog"], "fictional-use", "f" * 64)
    return dict(request=request, policy=document, roots=roots, case=case, snapshot=snapshot, paths=paths,
                raw_root=raw_root, normalized=normalized)


def argv(fixture, output):
    p = fixture["paths"]
    return ["run", "--output", str(output), "--case", str(p["case"]), "--snapshot", str(p["snapshot"]),
            "--catalog", str(p["source_catalog"]), "--catalog-policy", str(p["policy"]),
            "--policy-roots", str(p["roots"]), "--policy-use", "fictional-use", "--policy-frame-sha256", "f" * 64]


class CatalogBindingTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / "data/cache/tether-q02-tests"
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="binding-", dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.f = make_fixture(self.root)
        self.output = self.root / "outer"

    def test_real_policy_run_preserves_nested_inputs_and_verifies(self):
        stream = io.StringIO()
        with redirect_stdout(stream), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(argv(self.f, self.output)), 0)
        receipt = json.loads(stream.getvalue())
        verified = layer.verify_outer(self.output, receipt["receipt_sha256"])
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
        result = layer.create_outer(self.output, argv(self.f, self.output), engine=engine, policy_request=self.f["request"])
        verified = layer.verify_outer(self.output, result["receipt_sha256"])
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
                    layer.create_outer(output, argv(f, output), policy_request=request)
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
            layer.create_outer(self.output, argv(self.f, self.output), engine=engine, policy_request=self.f["request"])
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
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"])
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
            binding.verify_policy_run(self.output, descriptor, check_engine=False)

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
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"])
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
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"])
        child.assert_not_called()

    def test_synthetic_demo_profile_cannot_silently_bypass_projection(self):
        snapshot = self.f["snapshot"]
        snapshot["profile"] = "synthetic_demo"
        self.f["policy"]["uses"][0].update(profile="synthetic_demo", snapshot_fingerprint=fingerprint(snapshot))
        write(self.f["paths"]["snapshot"], snapshot); write(self.f["paths"]["policy"], self.f["policy"])
        with patch.object(layer, "invoke_engine") as child, self.assertRaisesRegex(ContractError, "Synthetic demo profile"):
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"])
        child.assert_not_called()

    def test_policy_output_reservation_is_exclusive_under_concurrency(self):
        calls = []
        def child(arguments):
            calls.append(arguments)
            return layer.EngineResult(3)
        def attempt(_):
            try:
                layer.create_outer(self.output, argv(self.f, self.output), engine=child, policy_request=self.f["request"])
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
            layer.create_outer(self.output, argv(self.f, self.output), policy_request=self.f["request"])
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
