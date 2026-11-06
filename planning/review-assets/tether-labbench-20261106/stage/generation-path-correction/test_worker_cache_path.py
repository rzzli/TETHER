"""Real interpreter/path regression; no data collection or model dispatch.

Extract the two worker cache-check expressions from an explicitly pinned source,
then execute those exact expressions using the real empty_import_cache function.
The production module and its imports are never mutated. Tests use exclusively
reserved fictional paths under data/benchmark, matching the production parent.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[5]
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
    source = Path(args.source).resolve()
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
    source: Path
    output: Path

    def invoke(self, name, *, mismatch=False, populated=False):
        stage = self.output / name
        stage.mkdir(exist_ok=False)
        prefix = stage / "worker-import-cache"
        prefix.mkdir()
        if populated:
            (prefix / "sentinel.txt").write_bytes(b"fictional nonempty cache")
        expected = stage / "different-cache" if mismatch else prefix
        command = [sys.executable, "-I", "-B", "-X", "pycache_prefix=" + str(prefix),
                   str(Path(__file__).resolve()), "--child", "--source", str(self.source),
                   "--source-sha256", hashlib.sha256(self.source.read_bytes()).hexdigest(),
                   "--expected", str(expected), "--worker-output", str(stage / "worker")]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=30, check=False)
        (stage / "stdout.json").write_bytes(result.stdout)
        (stage / "stderr.txt").write_bytes(result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-sha256")
    parser.add_argument("--expected")
    parser.add_argument("--worker-output")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.child:
        child(args)
        return
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if not output.is_relative_to(ROOT / "data/benchmark"):
        raise AssertionError("Qualification output must match the intended data/benchmark placement")
    output.mkdir(parents=True, exist_ok=False)
    WorkerCachePathTests.source, WorkerCachePathTests.output = source, output
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WorkerCachePathTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
