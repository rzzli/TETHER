"""Run the portable source-export gate with Python 3.11+, without Git or data.

This deliberately does not replace tools/validate.py's full-clone study, native,
ingestion, and wheel gates. All selected tests use fictional/local fixtures.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import traceback
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
TEST_MODULES = (
    "tests.test_framework",
    "tests.test_derivation_registry",
    "tests.test_derivation_execution",
    "tests.test_derivation_graph_limits",
    "tests.test_derivation_source_envelope",
    "tests.test_store_temporal_hardening",
    "tests.test_evaluation_population",
    "tests.test_evaluation_binding",
    "tests.test_evaluation_cli",
    "tests.test_portable_bundle",
    "tests.test_bundle_output_paths",
    "tests.test_dossier_rendering",
    "tests.test_portable_validation",
    "packages.tether.tests.test_namespace",
    "packages.tether.tests.test_semantics",
)
EXCLUDED_GATES = {
    "packages.tether.tests.test_frontdoor":
        "Installed-package launcher tests invoke isolated Python; retain the existing installed wrapper gate.",
    "tools/validate.py":
        "Full-clone, historical study, optional ingestion, native and wheel gates remain separate.",
}
ENV_KEYS = ("TMP", "TEMP", "TMPDIR", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE")


class ValidationError(ValueError):
    """The selected portable gate was not completely executed."""

    def __init__(self, message, *, inventory=(), discovered=()):
        super().__init__(message)
        self.inventory = list(inventory)
        self.discovered = list(discovered)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from test_ids(item)
        else:
            yield item.id()


def collect_suite(root=ROOT, modules=TEST_MODULES):
    """Import each exact required module; never treat import failure as absence."""
    loader = unittest.TestLoader()
    suite, inventory = unittest.TestSuite(), []
    def failure(message):
        return ValidationError(message, inventory=inventory, discovered=test_ids(suite))
    for name in modules:
        path = root.joinpath(*name.split(".")).with_suffix(".py")
        if not path.is_file():
            raise failure("Required test module is absent: " + name)
        try:
            module = importlib.import_module(name)
        except Exception as error:
            raise failure("Required test module could not import: " + name) from error
        if Path(module.__file__).resolve() != path.resolve():
            raise failure("Required test module resolved outside this export: " + name)
        selected = loader.loadTestsFromModule(module)
        ids = list(test_ids(selected))
        if loader.errors or not ids:
            raise failure("Required test module did not discover tests: " + name)
        inventory.append({"module": name, "path": path.relative_to(root).as_posix(),
                          "sha256": sha256(path), "discovered": len(ids)})
        suite.addTests(selected)
    return suite, inventory


class AccountedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_ids = []
        self.passed_ids = []

    def startTest(self, test):
        self.started_ids.append(test.id())
        super().startTest(test)

    def addSuccess(self, test):
        self.passed_ids.append(test.id())
        super().addSuccess(test)


def summarize(result, discovered):
    """Fixture/subtest errors remain visible even if they lack a startTest event."""
    executed = result.started_ids if result else []
    counts = {"discovered": len(discovered), "executed": result.testsRun if result else 0,
              "passed": len(result.passed_ids) if result else 0}
    for key in ("failures", "errors", "skipped", "expectedFailures", "unexpectedSuccesses"):
        counts[key] = len(getattr(result, key)) if result else 0
    complete = (bool(discovered) and len(discovered) == len(set(discovered))
                and executed == discovered and counts["executed"] == len(discovered))
    success = bool(result and complete and result.wasSuccessful()
                   and not result.skipped and not result.expectedFailures
                   and counts["passed"] == len(discovered))
    return counts, list(executed), complete, success


def reserve_output(path):
    path = Path(os.path.abspath(path))
    protected = (ROOT, *(ROOT / name for name in
                 ("src", "tests", "tools", "packages", "docs", ".git", ".github")))
    if path == ROOT or ROOT.is_relative_to(path) or any(
            path.is_relative_to(member) for member in protected[1:]):
        raise ValidationError("Output overlaps protected source paths")
    for member in (*reversed(path.parents), path):
        if not os.path.lexists(member):
            continue
        info = member.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValidationError("Output has a link/reparse component")
    if not path.parent.is_dir() or os.path.lexists(path):
        raise ValidationError("Output must be a fresh directory under an existing parent")
    try:
        path.mkdir()
    except FileExistsError as error:
        raise ValidationError("Output reservation was already taken") from error
    return path


@contextmanager
def isolated_workspace(output):
    previous = {key: os.environ.get(key) for key in ENV_KEYS}
    old_tempdir, old_cwd = tempfile.tempdir, Path.cwd()
    old_path, old_bytecode = list(sys.path), sys.dont_write_bytecode
    paths = [str(ROOT / "src"), str(ROOT / "packages/tether/src"), str(ROOT)]
    with tempfile.TemporaryDirectory(prefix="work-", dir=output) as temporary:
        work = Path(temporary)
        try:
            tempfile.tempdir = str(work)
            for key in ("TMP", "TEMP", "TMPDIR"):
                os.environ[key] = str(work)
            os.environ["PYTHONPATH"] = os.pathsep.join(paths)
            os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
            sys.dont_write_bytecode = True
            sys.path[:0] = paths
            os.chdir(ROOT)
            yield work
        finally:
            tempfile.tempdir = old_tempdir
            os.chdir(old_cwd)
            sys.path[:] = old_path
            sys.dont_write_bytecode = old_bytecode
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        help="fresh report directory; default is a unique system-temp directory")
    args = parser.parse_args(argv)
    destination = args.output or Path(tempfile.gettempdir()) / ("tether-portable-" + uuid.uuid4().hex)
    try:
        output = reserve_output(destination)
    except (ValidationError, OSError) as error:
        print("Portable validation output rejected: " + str(error), file=sys.stderr)
        return 1
    print("Portable validation report directory: " + str(output), flush=True)
    started = time.monotonic()
    result, inventory, discovered, exception_type = None, [], [], None
    log = output / "tests.log"
    with log.open("x", encoding="utf-8", newline="\n") as stream:
        try:
            with isolated_workspace(output):
                suite, inventory = collect_suite()
                discovered = list(test_ids(suite))
                if not discovered or len(discovered) != len(set(discovered)):
                    raise ValidationError("Required suite is empty or has duplicate test identities")
                def result_factory(*args, **kwargs):
                    nonlocal result
                    result = AccountedResult(*args, **kwargs)
                    return result
                runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=result_factory)
                runner.run(suite)
        except (Exception, KeyboardInterrupt) as error:
            exception_type = type(error).__name__
            if result is None and isinstance(error, ValidationError) and error.discovered:
                inventory, discovered = error.inventory, error.discovered
            traceback.print_exc(file=stream)
        stream.flush()
        os.fsync(stream.fileno())
    counts, executed, complete, success = summarize(result, discovered)
    success = success and exception_type is None
    report = {"schema_version": 1, "kind": "portable_source_export_validation",
              "status": "passed" if success else "failed", "counts": counts,
              "discovery_complete": complete, "modules": inventory,
              "excluded_gates": EXCLUDED_GATES,
              "discovered_test_ids": discovered, "executed_test_ids": executed,
              "exception_type": exception_type, "test_log_sha256": sha256(log),
              "elapsed_seconds": round(time.monotonic() - started, 6),
              "failures": [{"test_id": test.id(), "traceback": detail} for test, detail in result.failures] if result else [],
              "errors": [{"test_id": test.id(), "traceback": detail} for test, detail in result.errors] if result else [],
              "python": sys.version, "git_required": False,
              "scope": "Selected source-export core and public-interface tests; not the full-clone, native, ingestion, wheel, or scientific qualification gates."}
    with (output / "report.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": report["status"], "counts": counts, "report": str(output / "report.json")}))
    if not success:
        for entry in (*report["failures"], *report["errors"]):
            print(entry["traceback"], file=sys.stderr)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
