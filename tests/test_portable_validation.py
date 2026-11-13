"""Portable validation must account for every selected test and protect outputs."""
from contextlib import redirect_stderr, redirect_stdout
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import portable_validate as gate


class PortableValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def suite(self, outcome="pass"):
        class Example(unittest.TestCase):
            def test_one(self):
                if outcome == "failure":
                    self.fail("fictional assertion")
                if outcome == "error":
                    raise ValueError("fictional error")
                if outcome == "skip":
                    self.skipTest("fictional absent prerequisite")
                if outcome == "subtest":
                    with self.subTest(item=1):
                        self.fail("fictional subtest")
        return unittest.defaultTestLoader.loadTestsFromTestCase(Example)

    def execute(self, suite, name="output"):
        with patch.object(gate, "collect_suite", return_value=(suite, [])), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = gate.main(["--output", str(self.root / name)])
        return status, json.loads((self.root / name / "report.json").read_text())

    def test_pass_requires_discovered_and_executed_identity_match(self):
        status, report = self.execute(self.suite())
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["counts"]["discovered"], 1)
        self.assertEqual(report["counts"]["executed"], 1)
        self.assertEqual(report["discovered_test_ids"], report["executed_test_ids"])
        self.assertEqual(report["counts"]["passed"], 1)
        self.assertIn("packages.tether.tests.test_frontdoor", report["excluded_gates"])
        self.assertNotIn("packages.tether.tests.test_frontdoor", gate.TEST_MODULES)

    def test_failure_error_skip_and_subtest_cannot_pass(self):
        for outcome in ("failure", "error", "skip", "subtest"):
            with self.subTest(outcome=outcome):
                status, report = self.execute(self.suite(outcome), outcome)
                self.assertEqual(status, 1)
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["counts"]["passed"], 0)

    def test_empty_duplicate_and_unexecuted_suites_cannot_pass(self):
        first = self.suite()
        duplicated = unittest.TestSuite([first, self.suite()])
        class DropsTests(unittest.TestSuite):
            def run(self, result, debug=False):
                return result
        for name, suite in (("empty", unittest.TestSuite()), ("duplicate", duplicated),
                            ("dropped", DropsTests(self.suite()))):
            with self.subTest(name=name):
                status, report = self.execute(suite, name)
                self.assertEqual(status, 1)
                self.assertNotEqual(report["status"], "passed")

    def test_import_failure_and_missing_file_fail_discovery(self):
        (self.root / "missing.py").write_text("raise RuntimeError('fictional import')\n")
        for modules in (("not_present",), ("missing",)):
            with self.subTest(modules=modules), self.assertRaises(gate.ValidationError):
                gate.collect_suite(self.root, modules)

    def test_discovery_error_leaves_failure_report(self):
        with patch.object(gate, "collect_suite", side_effect=gate.ValidationError("fixture import")), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = gate.main(["--output", str(self.root / "discovery")])
        report = json.loads((self.root / "discovery/report.json").read_text())
        self.assertEqual(status, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["counts"]["executed"], 0)
        self.assertEqual(report["exception_type"], "ValidationError")

    def test_late_import_error_preserves_partial_discovery(self):
        (self.root / "first.py").write_text("# fictional module\n")
        module = SimpleNamespace(__file__=str(self.root / "first.py"))
        with patch.object(gate.importlib, "import_module", return_value=module), \
             patch.object(unittest.TestLoader, "loadTestsFromModule", return_value=self.suite()), \
             self.assertRaises(gate.ValidationError) as caught:
            gate.collect_suite(self.root, ("first", "missing"))
        self.assertEqual(len(caught.exception.discovered), 1)
        self.assertEqual(caught.exception.inventory[0]["module"], "first")
        with patch.object(gate, "collect_suite", side_effect=caught.exception), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(gate.main(["--output", str(self.root / "partial")]), 1)
        report = json.loads((self.root / "partial/report.json").read_text())
        self.assertEqual(report["counts"]["discovered"], 1)
        self.assertEqual(report["counts"]["executed"], 0)

    def test_interruption_retains_started_test_accounting(self):
        class Interrupted(unittest.TestCase):
            def test_interrupted(self):
                raise KeyboardInterrupt()
        status, report = self.execute(unittest.defaultTestLoader.loadTestsFromTestCase(Interrupted), "interrupted")
        self.assertEqual(status, 1)
        self.assertEqual(report["exception_type"], "KeyboardInterrupt")
        self.assertEqual(report["counts"]["executed"], 1)
        self.assertEqual(report["counts"]["passed"], 0)

    def test_output_is_exclusive_and_protected_source_paths_rejected(self):
        output = self.root / "exists"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_text("preserve")
        with self.assertRaises(gate.ValidationError):
            gate.reserve_output(output)
        self.assertEqual(sentinel.read_text(), "preserve")
        for directory in (gate.ROOT, gate.ROOT / "src/new-output", gate.ROOT / "tests/new-output"):
            with self.subTest(directory=directory), self.assertRaises(gate.ValidationError):
                gate.reserve_output(directory)

    def test_temp_environment_restored_and_work_removed(self):
        old_tempdir, old_cwd = tempfile.tempdir, Path.cwd()
        old_environment = {key: os.environ.get(key) for key in gate.ENV_KEYS}
        output = self.root / "temporary"
        output.mkdir()
        with gate.isolated_workspace(output) as work:
            self.assertEqual(Path(tempfile.gettempdir()), work)
            self.assertTrue(work.is_dir())
            self.assertEqual(os.environ["TMPDIR"], str(work))
            self.assertIn(str(gate.ROOT / "src"), os.environ["PYTHONPATH"])
        self.assertFalse(work.exists())
        self.assertEqual(tempfile.tempdir, old_tempdir)
        self.assertEqual(Path.cwd(), old_cwd)
        self.assertEqual({key: os.environ.get(key) for key in gate.ENV_KEYS}, old_environment)

    def test_concurrent_output_reservation_has_exactly_one_owner(self):
        destination = self.root / "concurrent"
        def reserve():
            try:
                gate.reserve_output(destination)
                return "reserved"
            except gate.ValidationError:
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: reserve(), range(2)))
        self.assertCountEqual(outcomes, ["reserved", "rejected"])

    def test_link_or_reparse_output_ancestor_rejected(self):
        original = Path.lstat
        for mode, attributes in ((stat.S_IFLNK, 0), (stat.S_IFDIR, 0x400)):
            with self.subTest(mode=mode, attributes=attributes):
                def injected(path, *args, **kwargs):
                    if path == self.root:
                        return SimpleNamespace(st_mode=mode, st_file_attributes=attributes)
                    return original(path, *args, **kwargs)
                with patch.object(Path, "lstat", injected), self.assertRaises(gate.ValidationError):
                    gate.reserve_output(self.root / "linked")
                self.assertFalse((self.root / "linked").exists())

    def test_unexpected_success_and_expected_failure_cannot_pass(self):
        class Expected(unittest.TestCase):
            @unittest.expectedFailure
            def test_one(self):
                self.fail("fictional expected failure")
        class Unexpected(unittest.TestCase):
            @unittest.expectedFailure
            def test_one(self):
                pass
        for case in (Expected, Unexpected):
            with self.subTest(case=case.__name__):
                status, report = self.execute(unittest.defaultTestLoader.loadTestsFromTestCase(case), case.__name__)
                self.assertEqual(status, 1)
                self.assertEqual(report["counts"]["passed"], 0)

    def test_report_is_not_published_before_test_log_is_closed(self):
        status, report = self.execute(self.suite(), "durable")
        self.assertEqual(status, 0)
        self.assertEqual(report["test_log_sha256"], gate.sha256(self.root / "durable/tests.log"))
        self.assertFalse(any(p.name.startswith("work-") for p in (self.root / "durable").iterdir()))


if __name__ == "__main__":
    unittest.main()
