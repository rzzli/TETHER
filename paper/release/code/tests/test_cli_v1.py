"""Fictional CLI/authority integration; no real P05 values or source replay.

The full pipeline test uses genuine core objects and real source/path/journal
helpers. Its historical-comparison seam is explicit and is not actual release
qualification. Authority and finalization predicates are tested separately.
"""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import platform
from types import SimpleNamespace
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import asof
import asof_p05_replay
import pyarrow
from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, encode, parse_json
from asof.study.source_fact_evaluation import ScoredCell
from asof.study.source_fact_sources import VerifiedReference
from asof_p05_replay import authority_v1 as auth
from asof_p05_replay import cli
from asof_p05_replay import policy_v1
from test_audit_v1 import native_fixture

ROOT = Path(__file__).resolve().parents[4]


def schedules():
    cells = [f"N-{arm}-p05-{i:02d}" for i in range(1, 13) for arm in ("L", "A")]
    cells += ["S-" + key for key in [*(f"C{i:02d}" for i in range(1, 5)), *(f"F{i:02d}" for i in range(1, 11))]]
    decisions = ["D-" + cell + "-" + p for cell in cells for p in (("FULL",) if cell.startswith("N-A-") else ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY"))]
    return cells, decisions


def descriptor(root, name, payload):
    (root / name).write_bytes(payload)
    return dict(path=name, sha256=auth.sha(payload), bytes=len(payload))


class CliTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "tmp/p09-cli-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-", dir=parent)
        self.root = Path(self.temp.name)
        self.assertTrue(self.root.resolve().is_relative_to(parent.resolve()))
        self.bundle = self.root / "bundle"; self.bundle.mkdir()
        self.originals = self.root / "originals"; self.originals.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def metadata_authority(self, *, comparison=b"this comparator is deliberately not JSON"):
        files = {}
        for name, raw in [("source-policy.json", b"{}\n"), ("comparison.json", comparison), ("controls.json", b"{}\n")]:
            files[name] = descriptor(self.bundle, name, raw)
        document = dict(schema_version=1, method="p09.public_reconstruction_protocol.v1", status="READY",
            actual_reconstruction_authorized=True,
            source_policy=files["source-policy.json"], comparison=files["comparison.json"], controls=files["controls.json"], files=files,
            environment=dict(python=platform.python_version(), pyarrow=pyarrow.__version__, platform=sys.platform),
            core_files=auth.code_inventory(Path(asof.__file__).resolve().parent),
            replay_files=auth.code_inventory(Path(asof_p05_replay.__file__).resolve().parent),
            limits=dict(seconds=120, memory_bytes=2 * 1024**3, output_bytes=256 * 1024**2))
        raw = canonical(document) + b"\n"
        (self.bundle / "protocol.json").write_bytes(raw)
        return document, raw

    def fake_authority(self):
        return dict(document=dict(limits=dict(seconds=120, memory_bytes=2 * 1024**3, output_bytes=256 * 1024**2)), byte_sha256="a" * 64)

    def argv(self, output, operation="reconstruct"):
        result = [operation, "--protocol", str(self.bundle / "protocol.json"), "--protocol-sha256", "a" * 64,
                  "--bundle-root", str(self.bundle), "--originals-root", str(self.originals), "--output", str(output)]
        if operation == "audit":
            result += ["--reconstruction-root", str(self.root / "fictional-prior-reconstruction")]
        return result

    def invoke(self, args):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return cli.main(args)

    @staticmethod
    def small_reconstruction(authority, bundle, originals, output, journal, deadline):
        seal = cli.save(output, "output-seal.json", dict(method="fictional_finalization_only", model_calls=0))
        journal.append("outputs_sealed", output_seal_sha256=seal["sha256"])
        return dict(status="COMPLETED_PENDING_AUDIT", output_seal_sha256=seal["sha256"], fictional_lifecycle_probe=True)

    def full_context(self):
        source_policy, _ = native_fixture(self.originals)
        source_policy["limits"] = dict(policy_v1.LIMITS)
        source = descriptor(self.bundle, "source-policy.json", canonical(source_policy) + b"\n")
        scenarios = cli.prepare_controls(self.root / "neutral-control-preparation", time.monotonic() + 120)
        controls = descriptor(self.bundle, "controls.json", canonical({key: cli.control_descriptor(value) for key, value in scenarios.items()}) + b"\n")
        probe = b'{"fictional_comparison_probe":true}\n'
        comparison = descriptor(self.bundle, "comparison.json", probe)
        authority = dict(document=dict(source_policy=source, controls=controls, comparison=comparison,
            limits=dict(seconds=180, memory_bytes=2 * 1024**3, output_bytes=256 * 1024**2)), byte_sha256="a" * 64)
        return authority, probe

    def test_authority_hashes_but_does_not_parse_comparator_before_generation(self):
        _, raw = self.metadata_authority()
        admitted = auth.load_authority(self.bundle / "protocol.json", auth.sha(raw), self.bundle,
                                       time.monotonic() + 60, require_installed=False)
        self.assertEqual(admitted["byte_sha256"], auth.sha(raw))
        self.assertRaises(ContractError, parse_json, (self.bundle / "comparison.json").read_bytes())

    def test_authority_requires_exact_schema_and_explicit_true_before_source_access(self):
        document, _ = self.metadata_authority()
        for label in ("missing_authorization", "false_authorization", "integer_authorization", "boolean_schema"):
            with self.subTest(envelope=label):
                changed = deepcopy(document)
                if label == "missing_authorization":
                    del changed["actual_reconstruction_authorized"]
                elif label == "false_authorization":
                    changed["actual_reconstruction_authorized"] = False
                elif label == "integer_authorization":
                    changed["actual_reconstruction_authorized"] = 1
                else:
                    changed["schema_version"] = True
                raw = canonical(changed) + b"\n"
                (self.bundle / "protocol.json").write_bytes(raw)
                with patch.object(auth, "read_descriptor", side_effect=AssertionError("source/bundle accessed before authority")) as source_reads, \
                     patch.object(auth, "read_file", wraps=auth.read_file) as protocol_reads:
                    with self.assertRaisesRegex(ContractError, "authorized READY"):
                        auth.load_authority(self.bundle / "protocol.json", auth.sha(raw), self.bundle,
                                            time.monotonic() + 60, require_installed=False)
                    source_reads.assert_not_called()
                    self.assertEqual([Path(call.args[0]) for call in protocol_reads.call_args_list],
                                     [self.bundle / "protocol.json"])

    def test_authority_rejects_external_hash_and_code_inventory_mismatch(self):
        document, raw = self.metadata_authority()
        with self.assertRaisesRegex(ContractError, "External protocol"):
            auth.load_authority(self.bundle / "protocol.json", "0" * 64, self.bundle, time.monotonic() + 60, require_installed=False)
        name = next(iter(document["replay_files"]))
        document["replay_files"][name] = "0" * 64
        changed = canonical(document); (self.bundle / "protocol.json").write_bytes(changed)
        with self.assertRaisesRegex(ContractError, "installed source/resource"):
            auth.load_authority(self.bundle / "protocol.json", auth.sha(changed), self.bundle, time.monotonic() + 60, require_installed=False)

    def test_authority_rejects_checkout_or_other_outside_environment_import(self):
        _, raw = self.metadata_authority()
        outside = self.root / "outside-package"; outside.mkdir(); (outside / "__init__.py").write_bytes(b"")
        with patch.object(auth, "asof", SimpleNamespace(__file__=str(outside / "__init__.py"))):
            with self.assertRaisesRegex(ContractError, "installed environments"):
                auth.load_authority(self.bundle / "protocol.json", auth.sha(raw), self.bundle, time.monotonic() + 60)

    def test_authority_descriptor_mutation_and_nonready_protocol_rejected(self):
        document, _ = self.metadata_authority()
        (self.bundle / "controls.json").write_bytes(b"changed")
        raw = (self.bundle / "protocol.json").read_bytes()
        with self.assertRaisesRegex(ContractError, "descriptor bytes"):
            auth.load_authority(self.bundle / "protocol.json", auth.sha(raw), self.bundle, time.monotonic() + 60, require_installed=False)
        document["status"] = "DRAFT"; raw = canonical(document); (self.bundle / "protocol.json").write_bytes(raw)
        with self.assertRaisesRegex(ContractError, "READY"):
            auth.load_authority(self.bundle / "protocol.json", auth.sha(raw), self.bundle, time.monotonic() + 60, require_installed=False)

    def test_complete_fictional_pipeline_seals_all_outputs_before_comparator_and_uses_genuine_scores(self):
        authority, probe = self.full_context()
        output = self.root / "complete"
        real_parse, real_exact, real_compile = cli.parse_json, cli.report_exactness, cli.compile_reference
        native_objects = []
        comparisons = []
        def parse_observed(raw):
            if raw == probe:
                self.assertTrue((output / "output-seal.json").exists())
                self.assertEqual(len(list((output / "raw").glob("*.json"))), 38)
                self.assertEqual(len(list((output / "references").glob("*.json"))), 12)
                events = read_chain(output / "journal.jsonl")
                names = [event["event"] for event in events]
                self.assertLess(names.index("outputs_sealed"), names.index("comparison_started"))
                self.assertEqual(sum(name == "output_retained" for name in names), 38)
            return real_parse(raw)
        def exact_observed(reference, raw, **kwargs):
            self.assertIsInstance(reference, VerifiedReference)
            result = real_exact(reference, raw, **kwargs)
            self.assertIsInstance(result[1], ScoredCell)
            native_objects.append(result[1])
            return result
        def compile_observed(*args, **kwargs):
            self.assertEqual(len(list((output / "raw").glob("*.json"))), 38)
            return real_compile(*args, **kwargs)
        def compare_observed(bridge, policy_sha, outputs, decisions, guards, refs):
            self.assertEqual(bridge, {"fictional_comparison_probe": True})
            expected_outputs, expected_decisions = schedules()
            self.assertEqual([row["cell_id"] for row in outputs], expected_outputs)
            self.assertEqual([row["decision_id"] for row in decisions], expected_decisions)
            self.assertEqual(set(guards), set(expected_outputs))
            self.assertEqual(set(refs), {f"p05-{i:02d}" for i in range(1, 13)})
            comparisons.append(True)
        with patch.object(cli, "load_authority", return_value=authority), patch.object(cli, "parse_json", side_effect=parse_observed), \
             patch.object(cli, "report_exactness", side_effect=exact_observed), patch.object(cli, "compile_reference", side_effect=compile_observed), \
             patch.object(cli, "compare_bridge", side_effect=compare_observed):
            self.assertEqual(self.invoke(self.argv(output)), 0)
        self.assertEqual(len(native_objects), 24)
        self.assertEqual(comparisons, [True])
        report = parse_json((output / "reconstruction.json").read_bytes())
        counts = report["analysis_counts"]
        self.assertEqual(counts["planned_output_cells"], 38)
        self.assertEqual(counts["planned_decisions"], 90)
        self.assertEqual(counts["native_literal"]["verified_exact"], 12)
        self.assertEqual(counts["native_abstain"]["completion_80"], 0)
        self.assertEqual(counts["controls"]["invalid_admissions"], dict(FULL=0, WITHOUT_WRAPPER=2, WIRE_ONLY=7))
        receipt = parse_json((output / "receipt.json").read_bytes())
        self.assertEqual(receipt["status"], "SEALED_SUCCESS")
        self.assertEqual(receipt["files"]["journal.jsonl"]["sha256"], auth.sha((output / "journal.jsonl").read_bytes()))
        self.assertEqual(receipt["reconstruction_sha256"], auth.sha((output / "reconstruction.json").read_bytes()))
        self.assertEqual(read_chain(output / "journal.jsonl")[-1]["event"], "reconstruction_completed")

    def test_disk_corruption_after_generation_cannot_be_scored_as_retained_bytes(self):
        authority, _ = self.full_context()
        output = self.root / "corrupted"
        real_save = cli.save
        def corrupt_after_save(root, relative, value, **kwargs):
            result = real_save(root, relative, value, **kwargs)
            if relative == "raw/N-L-p05-01.json":
                (root / relative).write_bytes(b"fictional retained-byte corruption")
            return result
        with patch.object(cli, "load_authority", return_value=authority), patch.object(cli, "save", side_effect=corrupt_after_save), \
             patch.object(cli, "compare_bridge", side_effect=AssertionError("corrupted output reached comparison")):
            self.assertEqual(self.invoke(self.argv(output)), 1)
        self.assertTrue((output / "failure.json").exists())
        self.assertFalse((output / "receipt.json").exists())

    def test_success_receipt_is_published_only_after_journal_close(self):
        output = self.root / "close-order"
        seen = []
        class ObservedJournal(RunJournal):
            def close(self):
                super().close(); seen.append("closed")
        real_save = cli.save
        def observed_save(root, relative, value, **kwargs):
            if relative == "receipt.json":
                self.assertEqual(seen, ["closed"])
            return real_save(root, relative, value, **kwargs)
        with patch.object(cli, "RunJournal", ObservedJournal), patch.object(cli, "load_authority", return_value=self.fake_authority()), \
             patch.object(cli, "reconstruct", side_effect=self.small_reconstruction), patch.object(cli, "save", side_effect=observed_save):
            self.assertEqual(self.invoke(self.argv(output)), 0)

    def test_journal_close_fault_retains_failure_without_success_receipt(self):
        for when in ("before", "after"):
            with self.subTest(when=when):
                output = self.root / ("close-fault-" + when)
                class BrokenClose(RunJournal):
                    def close(self):
                        if not getattr(self, "injected", False):
                            self.injected = True
                            if when == "before":
                                raise OSError("fictional close before")
                            super().close()
                            raise OSError("fictional close after")
                        # The final best-effort attempt closes a descriptor
                        # left open by the before-close fault.
                        super().close()
                with patch.object(cli, "RunJournal", BrokenClose), patch.object(cli, "load_authority", return_value=self.fake_authority()), \
                     patch.object(cli, "reconstruct", side_effect=self.small_reconstruction):
                    self.assertEqual(self.invoke(self.argv(output)), 1)
                self.assertTrue((output / "failure.json").exists())
                self.assertFalse((output / "receipt.json").exists())

    def test_failure_append_fault_does_not_suppress_primary_failure_evidence(self):
        output = self.root / "append-fault"
        class BrokenFailureAppend(RunJournal):
            def fail(self, error, stage):
                raise OSError("fictional fail-append fault")
        with patch.object(cli, "RunJournal", BrokenFailureAppend), patch.object(cli, "load_authority", return_value=self.fake_authority()), \
             patch.object(cli, "reconstruct", side_effect=ValueError("fictional primary defect")):
            self.assertEqual(self.invoke(self.argv(output)), 1)
        failure = parse_json((output / "failure.json").read_bytes())
        self.assertEqual(failure["error_class"], "ValueError")
        self.assertIn("OSError", failure["journal_failure_recording_errors"])
        self.assertFalse((output / "receipt.json").exists())

    def test_terminal_append_fault_cannot_publish_success_receipt(self):
        output = self.root / "terminal-append-fault"
        class BrokenTerminal(RunJournal):
            def append(self, event, **details):
                if event == "reconstruction_completed":
                    raise OSError("fictional terminal append failure")
                return super().append(event, **details)
        with patch.object(cli, "RunJournal", BrokenTerminal), patch.object(cli, "load_authority", return_value=self.fake_authority()), \
             patch.object(cli, "reconstruct", side_effect=self.small_reconstruction):
            self.assertEqual(self.invoke(self.argv(output)), 1)
        self.assertTrue((output / "failure.json").exists())
        self.assertEqual(read_chain(output / "journal.jsonl")[-1]["event"], "build_failed")
        self.assertFalse((output / "receipt.json").exists())

    def test_failure_file_write_fault_keeps_durable_primary_journal_failure(self):
        output = self.root / "failure-file-fault"
        real_save = cli.save
        def fail_failure_file(root, relative, value, **kwargs):
            if relative == "failure.json":
                raise OSError("fictional failure-file write fault")
            return real_save(root, relative, value, **kwargs)
        with patch.object(cli, "load_authority", return_value=self.fake_authority()), patch.object(cli, "reconstruct", side_effect=ValueError("primary")), \
             patch.object(cli, "save", side_effect=fail_failure_file):
            self.assertEqual(self.invoke(self.argv(output)), 1)
        event = read_chain(output / "journal.jsonl")[-1]
        self.assertEqual(event["event"], "build_failed")
        self.assertEqual(event["details"]["error_class"], "ValueError")
        self.assertFalse((output / "receipt.json").exists())

    def test_interruption_retains_failure_and_does_not_publish_success(self):
        output = self.root / "interrupted"
        with patch.object(cli, "load_authority", return_value=self.fake_authority()), patch.object(cli, "reconstruct", side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                self.invoke(self.argv(output))
        self.assertEqual(parse_json((output / "failure.json").read_bytes())["error_class"], "KeyboardInterrupt")
        self.assertEqual(read_chain(output / "journal.jsonl")[-1]["event"], "build_interrupted")
        self.assertFalse((output / "receipt.json").exists())

    def test_receipt_write_fault_retains_failure_after_closed_journal(self):
        output = self.root / "receipt-fault"
        real_save = cli.save
        def fail_receipt(root, relative, value, **kwargs):
            if relative == "receipt.json":
                raise OSError("fictional receipt write fault")
            return real_save(root, relative, value, **kwargs)
        with patch.object(cli, "load_authority", return_value=self.fake_authority()), patch.object(cli, "reconstruct", side_effect=self.small_reconstruction), \
             patch.object(cli, "save", side_effect=fail_receipt):
            self.assertEqual(self.invoke(self.argv(output)), 1)
        self.assertTrue((output / "failure.json").exists())
        self.assertFalse((output / "receipt.json").exists())

    def test_existing_and_input_nested_output_paths_are_not_modified(self):
        output = self.root / "existing"; output.mkdir(); (output / "marker").write_bytes(b"prior reviewed bytes")
        with patch.object(cli, "load_authority", side_effect=AssertionError("reserved output must precede authority")):
            with self.assertRaises(FileExistsError):
                self.invoke(self.argv(output))
        self.assertEqual((output / "marker").read_bytes(), b"prior reviewed bytes")
        for parent in (self.bundle, self.originals):
            nested = parent / "forbidden-output"
            with self.assertRaises(ContractError):
                self.invoke(self.argv(nested))
            self.assertFalse(nested.exists())

    def test_negative_independent_audit_returns_failure_status_and_receipt(self):
        from asof_p05_replay import audit_v1
        output = self.root / "negative-audit"
        with patch.object(cli, "load_authority", return_value=self.fake_authority()), \
             patch.object(audit_v1, "audit_reconstruction", return_value=dict(status="FAIL_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT", issues=["fictional defect"])):
            self.assertEqual(self.invoke(self.argv(output, operation="audit")), 1)
        self.assertEqual(parse_json((output / "receipt.json").read_bytes())["status"], "SEALED_FAILED_AUDIT")
        self.assertEqual(read_chain(output / "journal.jsonl")[-1]["event"], "audit_failed")

    def test_declared_memory_and_output_caps_reject_before_generation(self):
        authority, _ = self.full_context()
        for name in ("memory", "output"):
            with self.subTest(bound=name):
                output = self.root / ("bound-" + name)
                current = deepcopy(authority)
                peak = 3 * 1024**3 if name == "memory" else 0
                if name == "output":
                    current["document"]["limits"]["output_bytes"] = 1
                with patch.object(cli, "load_authority", return_value=current), patch.object(cli, "peak_memory_bytes", return_value=peak):
                    self.assertEqual(self.invoke(self.argv(output)), 1)
                self.assertTrue((output / "failure.json").exists())
                self.assertFalse((output / "raw").exists())
                self.assertFalse((output / "receipt.json").exists())

    def test_projection_excludes_only_catalog_digest(self):
        source = dict(method=dict(catalog_sha256="a" * 64, source_snapshot_sha256="b" * 64), facts=[dict(value=0.125)])
        catalog = deepcopy(source); catalog["method"]["catalog_sha256"] = "c" * 64
        changed_snapshot = deepcopy(source); changed_snapshot["method"]["source_snapshot_sha256"] = "c" * 64
        changed_value = deepcopy(source); changed_value["facts"][0]["value"] = 0.25
        self.assertEqual(cli.reference_projection(source), cli.reference_projection(catalog))
        self.assertNotEqual(cli.reference_projection(source), cli.reference_projection(changed_snapshot))
        self.assertNotEqual(cli.reference_projection(source), cli.reference_projection(changed_value))

    def test_contradictory_duplicate_schedules_cannot_pass_matching_bridge(self):
        output_ids, decision_ids = schedules()
        outputs = [dict(cell_id=cid, core_score=None) for cid in output_ids]
        decisions = [dict(decision_id=did) for did in decision_ids]
        bridge = dict(method="p09.p05_comparison_bridge.v1", role="evaluation_only", agent_visible=False,
                      source_policy_sha256="a" * 64, outputs=deepcopy(outputs), decisions=deepcopy(decisions), guards={}, native={})
        outputs[-1] = deepcopy(outputs[-2]); bridge["outputs"][-1] = deepcopy(outputs[-2])
        with self.assertRaisesRegex(ContractError, "output schedule"):
            cli.compare_bridge(bridge, "a" * 64, outputs, decisions, {}, {})
        outputs = [dict(cell_id=cid, core_score=None) for cid in output_ids]; bridge["outputs"] = deepcopy(outputs)
        decisions[-1] = deepcopy(decisions[-2]); bridge["decisions"] = deepcopy(decisions)
        with self.assertRaisesRegex(ContractError, "decision schedule"):
            cli.compare_bridge(bridge, "a" * 64, outputs, decisions, {}, {})


if __name__ == "__main__":
    unittest.main()
