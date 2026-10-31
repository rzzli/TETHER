"""Status-only sealer AST and fake cleanup/publication faults; no SDK/API/child."""
import ast
import hashlib
from importlib import util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "module_census_status_seal_v1.py"
BASIS = HERE / "harmless_launch_seal_v2.py"
REPORT = HERE / "SELF-MODULE-CENSUS-SEALER-PURE-PROOF-v1.json"
STATUS = "module_census_observations_retained_not_ABI_qualification"
TEST_ROOT = HERE.parents[2] / "data/cache" / ("r09-census-sealer-pure-" + str(time.time_ns()))
TEST_ROOT.mkdir()
DENIED, FIXTURES = [], []


def guard(event, args):
    if event in ("subprocess.Popen", "os.system", "ctypes.dlopen") or event.startswith("socket."):
        DENIED.append(event)
        raise RuntimeError("Sealer checks are fake/file-only")


sys.addaudithook(guard)
spec = util.spec_from_file_location("own_census_status_sealer", SOURCE)
module = util.module_from_spec(spec)
spec.loader.exec_module(module)


def pin(path):
    p = Path(path)
    raw = p.read_bytes()
    return dict(path=str(p), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def require(value, message):
    if not value:
        raise RuntimeError(message)


def fixture(name, *, primary=False, close_error=None, write_failure=None, after_seal=False):
    root = TEST_ROOT / name
    root.mkdir()
    clock = SimpleNamespace(value=100.0)
    def write_new(path, value):
        path = Path(path)
        if path.name == write_failure:
            raise OSError("Synthetic publication fault: " + path.name)
        with path.open("xb") as stream:
            stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()+b"\n")
            stream.flush(); os.fsync(stream.fileno())
        if after_seal and path.name == "terminal-seal.json":
            clock.value = 111.0
    def safe(path, **kwargs):
        p = Path(path).absolute()
        require(p.is_relative_to(TEST_ROOT), "Only own synthetic outputs")
        return p
    sdk = SimpleNamespace(safe=safe, file_pin=pin, write_new=write_new, require=require)
    marker = dict(error_class="SyntheticPrimary", error="keep original primary") if primary else None
    write_new(root / "receipt.json", dict(status="failed" if primary else STATUS, own_fixture=True))
    if primary:
        write_new(root / "failure.json", dict(authoritative=True, **marker))
    old_receipt = (root / "receipt.json").read_bytes()
    old_primary = (root / "failure.json").read_bytes() if primary else None
    class API:
        calls = 0
        def close(self, handle):
            self.calls += 1
            if close_error:
                raise close_error("Synthetic close fault")
    api = API()
    leases = [dict(path="own synthetic pinned file", handle=123, validation="passed", closed=False, cleanup_errors=[])]
    def run(deadline=110.0):
        original = module.time
        module.time = SimpleNamespace(monotonic=lambda: clock.value)
        try:
            return module.make_sealer(sdk)(root, api, leases, marker, "failed" if primary else STATUS, 99.0, deadline)
        finally:
            module.time = original
            FIXTURES.append(dict(case=name, output=str(root), files=[pin(p) for p in sorted(root.rglob("*")) if p.is_file()]))
    return root, api, leases, run, old_receipt, old_primary


class Checks(unittest.TestCase):
    def test_whole_function_AST_diff_is_one_success_literal(self):
        self.assertEqual(pin(BASIS)["sha256"], "4cc94dd9ab5940f4f5e303d4c41ffbbb8d5032103eafb139113133d44cbb1dcb")
        def function(path):
            return next(n for n in ast.parse(path.read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == "make_sealer")
        new = function(SOURCE)
        changed = 0
        for n in ast.walk(new):
            if isinstance(n, ast.Constant) and n.value == STATUS:
                n.value = "harmless_launch_qualification_passed"; changed += 1
        self.assertEqual(changed, 1)
        self.assertEqual(ast.dump(new, include_attributes=False), ast.dump(function(BASIS), include_attributes=False))

    def test_success_is_census_observation_only(self):
        root, api, leases, run, old_receipt, _ = fixture("success")
        self.assertEqual(run()["status"], STATUS)
        self.assertEqual(api.calls, 1); self.assertTrue(leases[0]["closed"])
        self.assertEqual((root / "receipt.json").read_bytes(), old_receipt)
        self.assertEqual(json.loads((root / "terminal-seal.json").read_text())["status"], STATUS)

    def test_primary_and_late_close_failure_preserve_both(self):
        root, api, leases, run, old_receipt, old_primary = fixture("primary-close", primary=True, close_error=OSError)
        self.assertEqual(run()["status"], "failed")
        self.assertEqual((root / "failure.json").read_bytes(), old_primary)
        self.assertEqual((root / "receipt.json").read_bytes(), old_receipt)
        self.assertTrue((root / "late-failure.json").is_file())
        cleanup = json.loads((root / "post-lease-cleanup.json").read_text())
        self.assertEqual(cleanup["close_errors"][0]["error_class"], "OSError")

    def test_interrupted_close_is_authoritative_failure(self):
        root, api, leases, run, _, _ = fixture("interrupt-close", close_error=KeyboardInterrupt)
        self.assertEqual(run()["status"], "failed")
        self.assertEqual(json.loads((root / "post-lease-cleanup.json").read_text())["close_errors"][0]["error_class"], "KeyboardInterrupt")

    def test_cleanup_publication_failure_cannot_publish_success(self):
        root, api, leases, run, _, old_primary = fixture("cleanup-publication", primary=True, write_failure="post-lease-cleanup.json")
        with self.assertRaises(OSError): run()
        self.assertEqual((root / "failure.json").read_bytes(), old_primary)
        self.assertTrue((root / "late-failure.json").is_file())
        self.assertFalse((root / "terminal-seal.json").exists())

    def test_missing_seal_and_after_seal_deadline_veto(self):
        root, api, leases, run, _, _ = fixture("seal-publication", write_failure="terminal-seal.json")
        with self.assertRaises(OSError): run()
        self.assertFalse((root / "terminal-seal.json").exists())
        self.assertTrue((root / "late-failure.json").exists())
        root, api, leases, run, _, _ = fixture("after-seal", after_seal=True)
        self.assertEqual(run()["status"], "failed")
        self.assertEqual(json.loads((root / "terminal-seal.json").read_text())["status"], STATUS)
        self.assertTrue((root / "after-seal-failure.json").exists())


if __name__ == "__main__":
    require(not REPORT.exists(), "Proof already exists")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    value = dict(schema_version=1, status="passed" if result.wasSuccessful() else "failed", tests=result.testsRun,
                 failures=[str(c) for c, _ in result.failures], errors=[str(c) for c, _ in result.errors],
                 source=pin(SOURCE), basis=pin(BASIS), checker=pin(Path(__file__)),
                 whole_function_AST_equal_after_one_literal=True if result.wasSuccessful() else None,
                 actual_SDK_or_child_or_target_calls=0, denied_real_operations=DENIED, fixtures=FIXTURES,
                 scope="Status-only sealer source/AST and synthetic filesystem cleanup/publication evidence")
    with REPORT.open("x", encoding="utf-8") as f:
        json.dump(value, f, sort_keys=True, indent=2); f.write("\n")
    print(json.dumps(dict(proof=str(REPORT), sha256=pin(REPORT)["sha256"])))
    raise SystemExit(0 if result.wasSuccessful() else 1)
