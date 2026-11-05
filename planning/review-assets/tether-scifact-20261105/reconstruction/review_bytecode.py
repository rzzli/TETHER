"""Bounded peer qualification of cache freshness on three invented modules only."""
import argparse
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import py_compile
import sys
import tempfile
import types
from unittest.mock import patch


def sha(raw): return hashlib.sha256(raw).hexdigest()


def main(output):
    root = Path(__file__).resolve().parents[4]
    helper = root / "planning/review-assets/tether-scifact-20261105/verify_bytecode.py"
    helper_raw = helper.read_bytes()
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
    (output / "reviewed-verify_bytecode.py").write_bytes(helper_raw)
    spec = importlib.util.spec_from_file_location("fictional_bytecode_review", helper)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    results = []
    with tempfile.TemporaryDirectory(dir=root / "data/cache/scifact-scoring-test-temp") as temporary:
        for case in ("current_timestamp", "stale_timestamp", "forged_current_timestamp"):
            workspace = Path(temporary) / case
            source = workspace / "experiments/scifact/fictional_cache.py"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"fictional_value = 1\n")
            cache = Path(importlib.util.cache_from_source(str(source)))
            py_compile.compile(str(source), cfile=str(cache), doraise=True,
                               invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
            previous = source.stat()
            if case != "current_timestamp":
                source.write_bytes(b"fictional_value = 2\n")
                os.utime(source, (previous.st_atime, previous.st_mtime + (5 if case == "stale_timestamp" else 0)))
            cache_raw, source_raw = cache.read_bytes(), source.read_bytes()
            # Ask Python's own loader which code it would use, without executing it.
            with patch.object(sys, "dont_write_bytecode", True):
                loaded = importlib.machinery.SourceFileLoader("fictional_cache", str(source)).get_code("fictional_cache")
            expected = compile(source_raw, str(source), "exec", dont_inherit=True, optimize=0)
            loader_matches_source = loaded == expected
            module.ROOT = workspace
            module.sys = types.SimpleNamespace(prefix=str(workspace / "fake-environment"),
                                               flags=types.SimpleNamespace(optimize=0), version=sys.version)
            capture = io.StringIO(); error = None
            destination = output / (case + ".json")
            with patch.object(sys, "argv", [str(helper), "--output", str(destination)]), contextlib.redirect_stdout(capture):
                try: module.main()
                except AssertionError as caught: error = str(caught)
            (output / (case + ".stdout.txt")).write_text(capture.getvalue(), encoding="utf-8")
            retained = json.loads(destination.read_bytes()) if destination.exists() else None
            expected_rejection = case == "forged_current_timestamp"
            passed = bool(error) == expected_rejection and loader_matches_source == (not expected_rejection)
            if retained is not None:
                row = retained["cache_files"][0]
                passed = passed and len(retained["cache_files"]) == 1
                passed = passed and row["usable_by_default_interpreter"] == (case == "current_timestamp")
                passed = passed and row["code_matches_compiled_source"] == (case == "current_timestamp")
            results.append({"case": case, "status": "PASS" if passed else "FAIL",
                            "helper_rejected": bool(error), "helper_error": error,
                            "python_loader_code_matches_current_source": loader_matches_source,
                            "source_sha256": sha(source_raw), "cache_sha256": sha(cache_raw),
                            "cache_unchanged": cache.read_bytes() == cache_raw,
                            "module_code_executed": False})
    unchanged = helper.read_bytes() == helper_raw
    status = "PASS" if unchanged and all(x["status"] == "PASS" and x["cache_unchanged"] for x in results) else "FAIL"
    report = {"status": status, "helper_sha256": sha(helper_raw), "helper_unchanged": unchanged, "cases": results,
              "scope": "Three fictional timestamp caches; native/project caches unchanged; no module bytecode executed.",
              "limitations": ["Hash-based caches are reviewed by inspection here, not exercised by these three fixtures.",
                              "The helper assumes Python's default hash-cache validation mode and normal (non-optimized) assertion checking."]}
    (output / "REVIEW.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "cases": len(results), "output": str(output)}))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); raise SystemExit(main(args.output))
