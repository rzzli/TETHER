"""Fictional Windows/PowerShell transport report publication regressions."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/data/Test-DownloadBatch.ps1"
PWSH = shutil.which("pwsh")


@unittest.skipUnless(PWSH and os.name == "nt", "PowerShell 7 required for utility integration")
class DownloadReportPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw/example.csv"
        self.raw.parent.mkdir()
        self.raw.write_bytes(b"fictional,value\n1,2\n")
        self.row = dict(receipt_id="fictional", dataset_id="fictional", release_id="v1",
                        relative_path="raw/example.csv", url="https://example.invalid/data",
                        expected_bytes=self.raw.stat().st_size, planning_upper_bytes=100,
                        format="csv", required_header="fictional,value")
        self.queue = self.root / "queue.json"
        self.queue.write_text(json.dumps(dict(batch_id="fictional", files=[self.row])), encoding="utf-8")
        self.receipt = self.root / "manifests/receipts/fictional.json"
        self.receipt.parent.mkdir(parents=True)
        self.receipt.write_text(json.dumps(dict(**self.row, status="completed",
            bytes=self.raw.stat().st_size, sha256=hashlib.sha256(self.raw.read_bytes()).hexdigest())),
            encoding="utf-8")
        self.original = {p: p.read_bytes() for p in (self.raw, self.queue, self.receipt)}

    def command(self, output=None):
        command = [PWSH, "-NoProfile", "-File", str(SCRIPT), "-QueuePath", str(self.queue),
                   "-DataRoot", str(self.root)]
        return command + (["-OutputPath", str(output)] if output is not None else [])

    def run_tool(self, output=None):
        return subprocess.run(self.command(output), capture_output=True, text=True, timeout=30)

    def assert_inputs_unchanged(self):
        for path, raw in self.original.items():
            self.assertEqual(path.read_bytes(), raw, str(path))

    def assert_rejected(self, output):
        result = self.run_tool(output)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_inputs_unchanged()
        return result

    def test_report_cannot_replace_receipt(self):
        self.assert_rejected(self.receipt)

    def test_equivalent_and_case_paths_cannot_replace_receipt(self):
        for output in (self.receipt.parent / ".." / "receipts" / self.receipt.name,
                       str(self.receipt).upper()):
            with self.subTest(output=str(output)):
                self.assert_rejected(output)

    def test_report_cannot_replace_queue_or_raw_original(self):
        for output in (self.queue, self.raw):
            with self.subTest(output=str(output)):
                self.assert_rejected(output)

    def test_existing_unrelated_report_is_preserved(self):
        output = self.root / "existing.json"
        output.write_bytes(b"prior report evidence\n")
        self.assert_rejected(output)
        self.assertEqual(output.read_bytes(), b"prior report evidence\n")

    def test_missing_source_destinations_are_not_created_as_reports(self):
        for path in (self.raw, self.receipt):
            with self.subTest(path=str(path)):
                before = path.read_bytes()
                path.unlink()
                result = self.run_tool(path)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(path.exists(), "Report masqueraded as a missing source")
                path.write_bytes(before)
                self.assert_inputs_unchanged()

    def test_hard_link_alias_preserves_receipt(self):
        alias = self.root / "hardlink-report.json"
        os.link(self.receipt, alias)
        self.assert_rejected(alias)
        self.assertEqual(alias.read_bytes(), self.original[self.receipt])

    def test_junction_parent_cannot_redirect_output(self):
        alias = self.root / "junction"
        command = "$null=New-Item -ItemType Junction -Path $env:TETHER_TEST_LINK -Target $env:TETHER_TEST_TARGET"
        environment = dict(os.environ, TETHER_TEST_LINK=str(alias), TETHER_TEST_TARGET=str(self.receipt.parent))
        setup = subprocess.run([PWSH, "-NoProfile", "-Command", command],
                               capture_output=True, text=True, env=environment)
        self.assertEqual(setup.returncode, 0, setup.stderr)
        self.assert_rejected(alias / self.receipt.name)
        result = self.assert_rejected(alias / "fresh-report.json")
        self.assertIn("reparse", result.stderr.lower())
        self.assertFalse((self.receipt.parent / "fresh-report.json").exists())

    def test_fresh_report_succeeds_without_modifying_inputs(self):
        output = self.root / "reports/fresh.json"
        result = self.run_tool(output)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(output.read_text(encoding="utf-8-sig"))
        self.assertTrue(report["complete"])
        self.assertEqual(report["verified_files"], 1)
        self.assertEqual(json.loads(result.stdout), report)
        self.assert_inputs_unchanged()
        self.assertEqual(list(output.parent.glob(".verify-report-*.tmp")), [])

    def test_failed_validation_still_publishes_complete_failure_report(self):
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["dataset_id"] = "different-dataset"
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        self.original[self.receipt] = self.receipt.read_bytes()
        output = self.root / "failure.json"
        result = self.run_tool(output)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        report = json.loads(output.read_text(encoding="utf-8-sig"))
        self.assertFalse(report["complete"])
        self.assertEqual(report["failed_files"], 1)
        self.assertIn("identity mismatch", report["failures"][0]["problem"])
        self.assert_inputs_unchanged()

    def test_unwritable_parent_fails_without_modifying_inputs(self):
        parent = self.root / "parent-is-a-file"
        parent.write_bytes(b"keep")
        self.assert_rejected(parent / "report.json")
        self.assertEqual(parent.read_bytes(), b"keep")

    def test_stdout_only_remains_supported(self):
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["complete"])
        self.assert_inputs_unchanged()

    def test_concurrent_publication_has_exactly_one_winner(self):
        output = self.root / "race.json"
        children = [subprocess.Popen(self.command(output), stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True) for _ in range(2)]
        try:
            outcomes = [(child.communicate(timeout=30), child.returncode) for child in children]
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.wait()
        self.assertEqual(sum(code == 0 for _, code in outcomes), 1, repr(outcomes))
        self.assertTrue(json.loads(output.read_text(encoding="utf-8-sig"))["complete"])
        self.assert_inputs_unchanged()
        self.assertEqual(list(self.root.glob(".verify-report-*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
