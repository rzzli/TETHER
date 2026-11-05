"""Runtime-witness launcher safety; paired-validator outcomes are not consulted."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from experiments.equal_policy.runtime_witnesses import tree_hashes

ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT = ROOT / "data/cache/tether-051-installed-qualification-attempt02/environment"
PYTHON = ENVIRONMENT / "Scripts/python.exe"
SCRIPT = ROOT / "experiments/equal_policy/runtime_witnesses.py"


class RuntimeWitnessLauncherTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / "data/cache/equal-policy-runtime-witness-tests"
        cache.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def invoke(self, output, runtime=ENVIRONMENT):
        self.assertTrue(PYTHON.is_file(), "Qualified installed interpreter is required, not silently skipped")
        env = dict(os.environ, TMP=str(self.root), TEMP=str(self.root))
        return subprocess.run([str(PYTHON), "-I", "-B", str(SCRIPT), "--output", str(output),
                               "--expected-runtime-root", str(runtime)], capture_output=True, timeout=30, env=env)

    def test_existing_output_is_not_mutated_even_by_failure_reporting(self):
        output = self.root / "existing"
        output.mkdir()
        (output / "sentinel.json").write_bytes(b'{"fictional":"preserve"}\n')
        before = tree_hashes(output)
        process = self.invoke(output)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"FileExistsError", process.stderr)
        self.assertEqual(tree_hashes(output), before)

    def test_wrong_installed_root_rejects_before_fixture_or_runtime_work(self):
        output = self.root / "new"
        process = self.invoke(output, self.root / "wrong-runtime")
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(b"expected installed environment", process.stderr)
        self.assertEqual(tree_hashes(output), {})

    def test_tree_inventory_detects_nested_change(self):
        child = self.root / "nested"
        child.mkdir()
        path = child / "fixture.json"
        path.write_bytes(b"one")
        before = tree_hashes(self.root)
        path.write_bytes(b"two")
        self.assertNotEqual(tree_hashes(self.root), before)


if __name__ == "__main__":
    unittest.main()
