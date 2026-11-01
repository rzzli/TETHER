"""Windows fixture/shape probes, explicitly not Linux or native qualification."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from asof.serde import ContractError
from asof.study import stable_read
from tests import test_study_source_fact_inputs as tests


def run_tests(mode):
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.InputTests)
    native = tests.inputs.stable_files
    if mode == "windows-native":
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    else:
        # Change only the test module's branch. Actual Windows filesystem and
        # production stable_read.os remain unchanged throughout the simulation.
        with patch.object(tests, "os", SimpleNamespace(name="posix")):
            assert stable_read.os.name == "nt"
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    assert tests.inputs.stable_files is native
    expected = result.testsRun == 12 and not result.errors and not result.failures and not result.skipped
    name = "SOURCE-FACT-INPUTS-POSIX-" + mode + "-after-v1.txt"
    payload = log.getvalue().encode()
    with (Path(__file__).resolve().parent / name).open("xb") as stream:
        stream.write(payload)
    return dict(mode=mode, status="PASS" if expected else "FAIL", tests=result.testsRun,
        errors=len(result.errors), failures=len(result.failures), skips=len(result.skipped),
        log=name, log_sha256=hashlib.sha256(payload).hexdigest())


def scope_checks():
    checks = []
    with tempfile.TemporaryDirectory(dir=ROOT / "data/cache") as temporary:
        base = Path(temporary).resolve()
        assert base.is_relative_to((ROOT / "data/cache").resolve())
        fixture = base / "fixture"
        fixture.mkdir()
        inside, outside = fixture / "invented.json", base / "outside.json"
        inside.write_bytes(b"{}")
        outside.write_bytes(b"{}")
        def admitted(paths, *, deadline=None):
            with tests._fictional_posix_locks(paths, deadline=time.monotonic() + 30 if deadline is None else deadline, fixture_root=fixture):
                pass
        admitted((inside,))
        checks.append("existing_inside_regular_file_admitted")
        for name, paths in (("missing_denied", (fixture / "missing.json",)), ("outside_denied", (outside,)),
                            ("empty_denied", ()), ("directory_denied", (fixture,)),
                            ("relative_denied", (Path("invented.json"),)),
                            ("traversal_denied", (fixture / ".." / "outside.json",))):
            try:
                admitted(paths)
            except (ContractError, FileNotFoundError):
                checks.append(name)
            else:
                raise AssertionError(name)
        real_lstat = Path.lstat
        for name, mode, attributes, links in (("symlink_shape_denied", stat.S_IFLNK, 0, 1),
                                              ("reparse_shape_denied", stat.S_IFREG, 0x400, 1),
                                              ("hardlink_shape_denied", stat.S_IFREG, 0, 2)):
            def linked(path, *args, **kwargs):
                return SimpleNamespace(st_mode=mode, st_file_attributes=attributes, st_nlink=links) if path == inside else real_lstat(path, *args, **kwargs)
            with patch.object(Path, "lstat", linked):
                try:
                    admitted((inside,))
                except ContractError:
                    checks.append(name)
                else:
                    raise AssertionError(name)
        nested = fixture / "nested"
        nested.mkdir()
        nested_file = nested / "invented.json"
        nested_file.write_bytes(b"{}")
        def parent_link(path, *args, **kwargs):
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400) if path == nested else real_lstat(path, *args, **kwargs)
        with patch.object(Path, "lstat", parent_link):
            try:
                admitted((nested_file,))
            except ContractError:
                checks.append("linked_parent_shape_denied")
            else:
                raise AssertionError("linked parent")
        try:
            admitted((inside,), deadline=time.monotonic() - 1)
        except TimeoutError:
            checks.append("expired_deadline_denied")
        else:
            raise AssertionError("expired deadline")
        native = stable_read.stable_files
        with patch.object(stable_read, "os", SimpleNamespace(name="posix")):
            try:
                with native((inside,), deadline=time.monotonic() + 30):
                    raise AssertionError("Native lock unexpectedly admitted POSIX")
            except ContractError as error:
                assert "require Windows sharing locks" in str(error)
                checks.append("native_unsupported_platform_remains_rejected")
    return checks


def main():
    if os.name != "nt":
        raise RuntimeError("This probe requires Windows and does not qualify Linux")
    import pyarrow
    if pyarrow.__version__ != "21.0.0":
        raise RuntimeError("Existing Arrow21 environment required; no installs")
    results = [run_tests(mode) for mode in ("windows-native", "simulated-posix-fixture")]
    report = dict(schema_version=1, method="p09.input_fixture_platform_boundary.v1",
        status="PASS" if all(result["status"] == "PASS" for result in results) else "FAIL", results=results,
        negative_shape_checks=scope_checks(), linux_qualification=False,
        simulation="Only the test module os binding and explicit lstat shapes are simulated; Windows OS and production source policy unchanged",
        native_source_read_guarantee="Windows actual tests use genuine stable_files; POSIX fixture seam claims no OS locking guarantee",
        test_sha256=hashlib.sha256(Path(tests.__file__).read_bytes()).hexdigest(),
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        actual_source_reads=False, model_calls=0, network_calls=0, runtime_source_changes=False)
    destination = Path(__file__).resolve().parent / "SOURCE-FACT-INPUTS-POSIX-after-v1.json"
    with destination.open("xb") as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
