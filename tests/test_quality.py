"""Quality gates reject stale installations and incomplete/failed measurements."""

import copy
from pathlib import Path
import tempfile
import unittest

from tools.coverage_gate import check_report
from tools.quality import check_lock_versions, runtime_sources


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.counts = dict(covered_lines=8, num_statements=10, covered_branches=3, num_branches=4)
        self.document = dict(
            meta=dict(version="7.17.3", branch_coverage=True),
            files={"installed/tether_engine/a.py": dict(summary=self.counts)},
            totals=self.counts.copy(),
        )
        self.validation = dict(
            status="passed",
            mode="full",
            test_scope=dict(profile="maintained"),
            required_probes_exit_code=0,
            tests=dict(run=2, failures=0, errors=0, skipped=[]),
        )
        self.baseline = dict(minimum_tests=2, minimum_line_percent=80, minimum_branch_percent=75)
        self.expected = {"tether_engine/a.py"}

    def check(self, document=None, validation=None, expected=None):
        return check_report(
            document if document is not None else self.document,
            validation if validation is not None else self.validation,
            self.baseline,
            expected if expected is not None else self.expected,
        )

    def test_exact_baseline_passes(self):
        self.assertEqual(self.check(), self.counts)

    def test_reduced_or_fabricated_counts_fail(self):
        for edit in (
            {"covered_lines": 7},
            {"covered_branches": 2},
            {"covered_lines": True},
            {"num_statements": 0},
            {"covered_branches": 5},
        ):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                document = copy.deepcopy(self.document)
                document["files"]["installed/tether_engine/a.py"]["summary"].update(edit)
                document["totals"].update(edit)
                self.check(document)

    def test_omissions_duplicates_and_unreconciled_totals_fail(self):
        with self.assertRaisesRegex(ValueError, "omitted"):
            self.check(expected=self.expected | {"tether_engine/missing.py"})
        document = copy.deepcopy(self.document)
        document["files"]["elsewhere/tether_engine/a.py"] = document["files"][
            "installed/tether_engine/a.py"
        ]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check(document)
        document = copy.deepcopy(self.document)
        document["totals"]["covered_lines"] = 9
        with self.assertRaisesRegex(ValueError, "reconcile"):
            self.check(document)

    def test_failed_or_reduced_test_gate_cannot_qualify_coverage(self):
        for edit in ({"run": 1}, {"errors": 1}, {"failures": 1}, {"skipped": ["fixture"]}):
            validation = copy.deepcopy(self.validation)
            validation["tests"].update(edit)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.check(validation=validation)
        with self.assertRaises(ValueError):
            self.check(validation=dict(self.validation, required_probes_exit_code=1))

    def test_line_only_or_wrong_version_measurement_fails(self):
        for edit in ({"version": "unknown"}, {"branch_coverage": False}):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.check(dict(self.document, meta=dict(self.document["meta"], **edit)))

    def test_current_lockfiles_and_runtime_inventory(self):
        check_lock_versions()
        names = runtime_sources()
        self.assertIn("tether_engine/temporal.py", names)
        self.assertIn("tether/_cli.py", names)
        self.assertEqual(
            {name for name in names if "/study/" in name},
            {
                "tether_engine/study/" + name + ".py"
                for name in ("__init__", "proofs", "stable_read")
            },
        )

    def test_stale_wrapper_or_engine_lock_fails(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            clone = Path(directory)
            for folder in (".", "packages/tether"):
                (clone / folder).mkdir(parents=True, exist_ok=True)
                for name in ("pyproject.toml", "uv.lock"):
                    (clone / folder / name).write_bytes((root / folder / name).read_bytes())
            for folder in (".", "packages/tether"):
                lock = clone / folder / "uv.lock"
                original = lock.read_bytes()
                lock.write_bytes(original.replace(b'version = "0.6.0.dev1"', b'version = "0.0.0"'))
                with self.subTest(folder=folder), self.assertRaisesRegex(ValueError, "Stale"):
                    check_lock_versions(clone)
                lock.write_bytes(original)
