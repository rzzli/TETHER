"""Generation cache-path regression under real isolated Python interpreters.

No source acquisition, benchmark questions, model startup or inference. The test
executes the current worker's two exact cache-check expressions using the actual
runtime guard; it does not mock that guard or mutate the production module.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = next(path for path in Path(__file__).resolve().parents
            if (path / "experiments/labbench/run.py").is_file())
sys.path.insert(0, str(ROOT))


def expressions(source):
    tree = ast.parse(source.read_text(encoding="utf-8"))
    worker = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_worker")
    checks = [node for node in ast.walk(worker) if isinstance(node, ast.Call)
              and isinstance(node.func, ast.Name) and node.func.id == "empty_import_cache"]
    if len(checks) != 2:
        raise AssertionError("Expected the worker's entry and final cache checks")
    return sorted(checks, key=lambda node: node.lineno)


def child(args):
    from experiments.labbench.runtime import empty_import_cache
    source = ROOT / "experiments/labbench/run.py"
    if hashlib.sha256(source.read_bytes()).hexdigest() != args.source_sha256:
        raise AssertionError("Regression source pin differs")
    namespace = {"empty_import_cache": empty_import_cache, "ROOT": ROOT, "Path": Path,
                 "recipe": {"worker_import_cache": args.expected}, "output": Path(args.worker_output)}
    results = []
    for expression in expressions(source):
        try:
            path = eval(compile(ast.Expression(expression), str(source), "eval"), namespace)
            results.append({"line": expression.lineno, "accepted": True, "path": str(path)})
        except Exception as exc:
            results.append({"line": expression.lineno, "accepted": False,
                            "error_type": type(exc).__name__, "reason": str(exc)})
    print(json.dumps({"isolated": sys.flags.isolated, "dont_write_bytecode": sys.dont_write_bytecode,
                      "prefix": sys.pycache_prefix, "checks": results}, sort_keys=True))


class WorkerCachePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ROOT / "experiments/labbench/run.py"
        fixture_parent = ROOT / "data/benchmark"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        cls.output = Path(tempfile.mkdtemp(prefix="labbench-cache-path-test-", dir=fixture_parent))

    @classmethod
    def tearDownClass(cls):
        # Small fixture proofs stay in ignored data, including red-control evidence.
        print("Retained cache-path fixtures: " + str(cls.output), file=sys.stderr)

    def invoke(self, name, *, mismatch=False, populated=False):
        stage = self.output / name
        stage.mkdir(exist_ok=False)
        prefix = stage / "worker-import-cache"
        prefix.mkdir()
        if populated:
            (prefix / "sentinel.txt").write_bytes(b"fictional nonempty cache")
        expected = stage / "different-cache" if mismatch else prefix
        source_sha256 = hashlib.sha256(self.source.read_bytes()).hexdigest()
        command = [sys.executable, "-I", "-B", "-X", "pycache_prefix=" + str(prefix),
                   str(Path(__file__).resolve()), "--child", "--source-sha256", source_sha256,
                   "--expected", str(expected), "--worker-output", str(stage / "worker")]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=30, check=False)
        (stage / "stdout.json").write_bytes(result.stdout)
        (stage / "stderr.txt").write_bytes(result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), source_sha256)
        proof = json.loads(result.stdout)
        self.assertEqual(proof["isolated"], 1)
        self.assertTrue(proof["dont_write_bytecode"])
        self.assertEqual(sorted(path.name for path in prefix.iterdir()), ["sentinel.txt"] if populated else [])
        return proof["checks"]

    def test_exclusive_generation_cache_passes_entry_and_final_check(self):
        checks = self.invoke("valid")
        self.assertEqual([row["accepted"] for row in checks], [True, True], checks)

    def test_wrong_expected_prefix_is_rejected_by_both_checks(self):
        checks = self.invoke("mismatch", mismatch=True)
        self.assertEqual([row["accepted"] for row in checks], [False, False], checks)

    def test_nonempty_prefix_is_rejected_without_removing_contents(self):
        checks = self.invoke("populated", populated=True)
        self.assertEqual([row["accepted"] for row in checks], [False, False], checks)


if __name__ == "__main__":
    if "--child" in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument("--child", action="store_true")
        parser.add_argument("--source-sha256", required=True)
        parser.add_argument("--expected", required=True)
        parser.add_argument("--worker-output", required=True)
        child(parser.parse_args())
    else:
        unittest.main()
