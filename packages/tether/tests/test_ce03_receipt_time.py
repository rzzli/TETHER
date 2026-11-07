"""All granted raw inputs must reconcile public-download availability evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages/tether/src"))
sys.path.insert(0, str(Path(__file__).parent))

from tether_engine.serde import ContractError, fingerprint
from tether_engine.journal import read_chain
from tether import _catalog_binding as binding, _catalog_policy as policy, _presentation as layer
from test_catalog_binding import argv, make_fixture, write


def add_raw(fixture, *, used=False, completed="2022-01-01T00:00:00+00:00",
            known="2022-01-01T00:00:00+00:00", basis="public_download_receipt",
            evidence_ref=None, receipt_url=None):
    """Append a distinct, explicitly granted raw source, used or unused."""
    node = copy.deepcopy(fixture["snapshot"]["sources"][0])
    payload = b'{"fictional_ce03":true}\n'
    node.update(source_id="ce03-extra", path="originals/ce03.json",
                sha256=hashlib.sha256(payload).hexdigest(), receipt_path="receipt-archive/ce03.json")
    write(fixture["raw_root"] / node["path"], payload)
    receipt = dict(receipt_id="ce03-extra", dataset_id=node["dataset_id"], release_id=node["release_id"],
                   relative_path=node["path"], sha256=node["sha256"], bytes=len(payload),
                   url=receipt_url or node["source_url"], status="completed", completed_at_utc=completed)
    receipt_path = fixture["raw_root"] / node["receipt_path"]
    write(receipt_path, receipt)
    node["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    node["availability"] = dict(first_public_at="2020-01-01", release_public_at="2020-01-01",
        record_public_at="2020-01-01", annotation_public_at="2020-01-01", retrieved_at="2026-01-01",
        basis=basis, uncertainty="Fictional regression input; no real historical claim",
        known_public_by=known, evidence_ref=evidence_ref or node["receipt_sha256"])
    fixture["snapshot"]["sources"].append(node)
    record = policy.artifact_record(dataset_id=node["dataset_id"], release_id=node["release_id"],
        root_alias="raw", relative_path=node["path"], sha256=node["sha256"], bytes=len(payload), kind="raw",
        parents=[], availability=node["availability"], temporal_classification=node["temporal_classification"],
        source_url=node["source_url"], scope="CE03 fictional regression", scientific_validation="not_established",
        provenance=dict(kind="download_receipt",
            evidence=copy.deepcopy(fixture["policy"]["artifacts"][0]["provenance"]["evidence"]),
            receipt=dict(root_alias="raw", relative_path=node["receipt_path"], sha256=node["receipt_sha256"],
                         receipt_id=receipt["receipt_id"], url=node["source_url"])))
    fixture["policy"]["artifacts"].append(record)
    fixture["policy"]["uses"][0]["grants"].append(dict(artifact_id=record["artifact_id"], role=node["role"]))
    if used:
        fixture["snapshot"]["sources"][1]["parents"].append(node["source_id"])
        fixture["policy"]["artifacts"][1]["parents"].append(record["artifact_id"])
    fixture["policy"]["uses"][0]["snapshot_fingerprint"] = fingerprint(fixture["snapshot"])
    write(fixture["paths"]["policy"], fixture["policy"])
    write(fixture["paths"]["snapshot"], fixture["snapshot"])
    return node, record


def reseal_extra_availability(output, descriptor, changes):
    """Recompute byte seals after maliciously registering contradictory metadata.

    This isolates the semantic relation from ordinary byte-integrity checks. No
    publisher signature is forged; all inputs are explicitly fictional.
    """
    seal_path = output / descriptor["path"]
    seal = json.loads(seal_path.read_bytes())
    controls = {name: json.loads((output / ref["path"]).read_bytes())
                for name, ref in seal["controls"].items()}
    snapshot = controls["snapshot"]
    node = next(row for row in snapshot["sources"] if row["source_id"] == "ce03-extra")
    node["availability"].update(changes)
    record = next(row for row in controls["policy"]["artifacts"] if row["relative_path"] == node["path"])
    record["availability"] = copy.deepcopy(node["availability"])
    controls["policy"]["uses"][0]["snapshot_fingerprint"] = fingerprint(snapshot)
    controls["execution_snapshot"] = copy.deepcopy(snapshot)
    decision = binding._decision(controls["policy"], snapshot, controls["case"], controls["roots"]["roots"],
                                 seal["use_id"], seal["frame_sha256"])
    controls["projection"], controls["decision"] = decision["projection"], decision["binding"]
    # Preserve exact unchanged bytes, particularly the source-catalog anchor.
    for name in ("policy", "snapshot", "execution_snapshot", "projection", "decision"):
        document = controls[name]
        relative = seal["controls"][name]["path"]
        write(output / relative, document)
        seal["controls"][name] = binding._descriptor(relative, (output / relative).read_bytes())
    write(seal_path, seal)
    return binding._descriptor(descriptor["path"], seal_path.read_bytes())


class ReceiptAvailabilityTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / "data/cache/tether-ce03-tests"
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="receipt-", dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, name, **kwargs):
        root = self.root / name
        root.mkdir()
        fixture = make_fixture(root)
        add_raw(fixture, **kwargs)
        return fixture, root / "outer"

    def assert_preflight_rejects(self, fixture, output, pattern):
        with patch.object(layer, "invoke_engine", side_effect=ContractError("unexpected dispatch reached")) as child, \
                self.assertRaisesRegex(ContractError, pattern):
            layer.create_outer(output, argv(fixture, output), policy_request=fixture["request"])
        child.assert_not_called()
        events = read_chain(output / layer.JOURNAL)
        self.assertNotIn("engine_dispatch", [row["event"] for row in events])
        self.assertEqual(layer.inspect_outer(output)["failure"]["stage"], "artifact_policy_preflight")
        self.assertFalse((output / layer.RECEIPT).exists())

    def test_used_and_unused_receipt_time_contradictions_fail_before_dispatch(self):
        for used in (False, True):
            with self.subTest(used=used):
                fixture, output = self.fixture(str(used), used=used, completed="2024-01-01T00:00:00+00:00")
                self.assert_preflight_rejects(fixture, output, "availability bound.*receipt")

    def test_used_and_unused_wrong_availability_evidence_refs_fail(self):
        for used in (False, True):
            with self.subTest(used=used):
                fixture, output = self.fixture(str(used), used=used, evidence_ref="0" * 64)
                self.assert_preflight_rejects(fixture, output, "availability bound.*receipt")

    def test_missing_public_download_bound_is_not_replaced_by_unrelated_dates(self):
        for used in (False, True):
            with self.subTest(used=used):
                fixture, output = self.fixture(str(used), used=used, known=None)
                self.assert_preflight_rejects(fixture, output, "availability bound.*receipt")

    def test_receipt_url_mismatch_rejects_used_and_unused_inputs(self):
        for used in (False, True):
            with self.subTest(used=used):
                fixture, output = self.fixture(str(used), used=used, receipt_url="https://example.invalid/wrong")
                self.assert_preflight_rejects(fixture, output, "receipt url differs")

    def test_future_raw_bound_rejects_even_when_unused(self):
        fixture, output = self.fixture("future", completed="2024-01-01T00:00:00+00:00",
                                       known="2024-01-01T00:00:00+00:00")
        self.assert_preflight_rejects(fixture, output, "raw information unavailable at origin")

    def test_valid_exact_and_conservative_bounds_preserve_all_proofs(self):
        for index, (used, known) in enumerate(((False, "2022-01-01T00:00:00+00:00"),
                    (True, "2022-01-01T00:00:00+00:00"), (False, "2022-01-02T00:00:00+00:00"))):
            with self.subTest(used=used, known=known):
                fixture, output = self.fixture(str(index), used=used, known=known)
                output.mkdir()
                descriptor = binding.prepare_policy_run(output, fixture["request"])
                verified = binding.verify_policy_run(output, descriptor, check_engine=False)
                self.assertEqual(verified["checked_inputs"], 4)
                seal = json.loads((output / descriptor["path"]).read_bytes())
                self.assertEqual(len(seal["receipts"]), 2)
                self.assertEqual({row["source_id"] for row in seal["external_sources"]},
                                 {"demo-original-input", "ce03-extra"})
                self.assertEqual(verified["scientific_validation"], "not_established")

    def test_separate_historical_basis_is_not_misrepresented_as_download_time(self):
        for used in (False, True):
            with self.subTest(used=used):
                fixture, output = self.fixture(str(used), used=used, completed="2024-01-01T00:00:00+00:00",
                    basis="Fictional separately retained release dates", known=None,
                    evidence_ref="fictional-release-evidence")
                output.mkdir()
                descriptor = binding.prepare_policy_run(output, fixture["request"])
                self.assertEqual(binding.verify_policy_run(output, descriptor, check_engine=False)["checked_inputs"], 4)

    def test_verification_rejects_resealed_used_and_unused_time_contradictions(self):
        for used in (False, True):
            with self.subTest(used=used):
                fixture, output = self.fixture(str(used), used=used)
                output.mkdir()
                descriptor = binding.prepare_policy_run(output, fixture["request"])
                descriptor = reseal_extra_availability(output, descriptor, dict(known_public_by="2021-01-01T00:00:00+00:00"))
                with self.assertRaisesRegex(ContractError, "availability bound.*receipt"):
                    binding.verify_policy_run(output, descriptor, check_engine=False)

    def test_verification_rejects_resealed_unused_evidence_ref(self):
        fixture, output = self.fixture("wrong-ref")
        output.mkdir()
        descriptor = binding.prepare_policy_run(output, fixture["request"])
        descriptor = reseal_extra_availability(output, descriptor, dict(evidence_ref="0" * 64))
        with self.assertRaisesRegex(ContractError, "availability bound.*receipt"):
            binding.verify_policy_run(output, descriptor, check_engine=False)


if __name__ == "__main__":
    unittest.main()
