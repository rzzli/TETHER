"""Independent status/late-failure vectors; AST-only component, fake closes."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
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
PROOF = HERE / "SELF-MODULE-CENSUS-SEALER-INDEPENDENT-PROOF-v1.json"
STATUS = "module_census_observations_retained_not_ABI_qualification"
OLD_ABI_STATUS = "ABI_observations_retained_independent_qualification_pending"
EXPECTED_SOURCE = "7794819e3b8013847f0f5e8912d8b8424edfea8c2a95a09354b0918409daf682"
EXPECTED_BASIS = "4cc94dd9ab5940f4f5e303d4c41ffbbb8d5032103eafb139113133d44cbb1dcb"
ROOT = HERE.parents[2] / "data/cache" / ("r09-census-independent-sealer-" + str(time.time_ns()))
DENIED, FIXTURES = [], []


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def guard(event, args):
    if event in ("ctypes.dlopen", "subprocess.Popen", "os.system") or event.startswith("socket."):
        DENIED.append(event)
        raise AssertionError("Independent sealer test permits no native dispatch")


def require(value, message):
    if not value:
        raise RuntimeError(message)


def factory_node(path):
    return next(node for node in ast.parse(Path(path).read_text(encoding="utf-8")).body
                if isinstance(node, ast.FunctionDef) and node.name == "make_sealer")


def fixture(name, *, late_close=False, seal_publication=False):
    root = ROOT / name
    root.mkdir()
    calls = []

    def safe(path, **unused):
        path = Path(path).absolute()
        require(path.is_relative_to(ROOT), "Synthetic fixture boundary")
        return path

    def write_new(path, value):
        path = safe(path)
        if seal_publication and path.name == "terminal-seal.json":
            raise OSError("Independent synthetic terminal publication failure")
        with path.open("xb") as stream:
            stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
            stream.flush()
            os.fsync(stream.fileno())

    # A deliberately misleading successful ABI-labelled early receipt must not
    # hide a later census close/publication failure.
    write_new(root / "receipt.json", dict(status=OLD_ABI_STATUS, synthetic=True))
    earlier = (root / "receipt.json").read_bytes()
    ns = dict(Path=Path, time=SimpleNamespace(monotonic=lambda: 100.0))
    exec(compile(ast.Module(body=[factory_node(SOURCE)], type_ignores=[]),
                 str(SOURCE) + "::<AST factory only>", "exec"), ns)
    sdk = SimpleNamespace(safe=safe, file_pin=pin, write_new=write_new, require=require)

    class FakeAPI:
        def close(self, handle):
            calls.append(handle)
            if late_close:
                raise OSError("Independent synthetic late lease close failure")

    leases = [dict(path="synthetic input metadata", handle=71, validation="passed",
                   closed=False, cleanup_errors=[])]
    return SimpleNamespace(root=root, calls=calls, leases=leases, earlier=earlier,
                           run=lambda: ns["make_sealer"](sdk)(root, FakeAPI(), leases, None,
                                                             OLD_ABI_STATUS, 99.0, 110.0))


def retain(f):
    FIXTURES.append(dict(case=f.root.name, output=str(f.root),
                         files=[pin(path) for path in sorted(f.root.rglob("*")) if path.is_file()]))


class IndependentSealer(unittest.TestCase):
    def test_whole_factory_has_exactly_one_status_literal_delta(self):
        self.assertEqual(pin(SOURCE)["sha256"], EXPECTED_SOURCE)
        self.assertEqual(pin(BASIS)["sha256"], EXPECTED_BASIS)
        current, previous = factory_node(SOURCE), factory_node(BASIS)
        normalised = copy.deepcopy(current)
        candidates = [node for node in ast.walk(previous)
                      if isinstance(node, ast.IfExp) and isinstance(node.orelse, ast.Constant)
                      and isinstance(node.orelse.value, str) and "harmless" in node.orelse.value]
        self.assertEqual(len(candidates), 1)
        changed = 0
        for node in ast.walk(normalised):
            if isinstance(node, ast.Constant) and node.value == STATUS:
                changed += 1
                node.value = candidates[0].orelse.value
        self.assertEqual(changed, 1)
        self.assertEqual(ast.dump(normalised, include_attributes=False),
                         ast.dump(previous, include_attributes=False))

    def test_forged_successful_early_receipt_late_close_remains_failed(self):
        f = fixture("forged-early-ABI-late-close", late_close=True)
        result = f.run()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(f.calls, [71])
        self.assertEqual((f.root / "receipt.json").read_bytes(), f.earlier)
        self.assertTrue((f.root / "late-failure.json").is_file())
        cleanup = json.loads((f.root / "post-lease-cleanup.json").read_bytes())
        self.assertTrue(cleanup["close_errors"])
        self.assertFalse(cleanup["outcomes"][0]["closed_after"])
        seal = json.loads((f.root / "terminal-seal.json").read_bytes())
        self.assertEqual(seal["status"], "failed")
        self.assertIn("late-failure.json", seal["outputs"])
        retain(f)

    def test_forged_successful_early_receipt_seal_publication_cannot_pass(self):
        f = fixture("forged-early-ABI-seal-publication", seal_publication=True)
        with self.assertRaisesRegex(OSError, "terminal publication"):
            f.run()
        self.assertEqual(f.calls, [71])
        self.assertEqual((f.root / "receipt.json").read_bytes(), f.earlier)
        self.assertFalse((f.root / "terminal-seal.json").exists())
        self.assertTrue((f.root / "late-failure.json").is_file())
        retain(f)


if __name__ == "__main__":
    require(not PROOF.exists(), "Preserve proof; no automatic repeat")
    sys.addaudithook(guard)
    ROOT.mkdir()
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(IndependentSealer))
    require(pin(SOURCE)["sha256"] == EXPECTED_SOURCE, "Source changed during pure check")
    record = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                  status="passed" if result.wasSuccessful() else "failed", tests=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors),
                  elapsed_seconds=time.monotonic()-started, source=pin(SOURCE), basis=pin(BASIS),
                  checker=pin(Path(__file__).resolve()), fixtures=FIXTURES, denied_real_operations=DENIED,
                  scope="Independent source-bound status and fabricated early-receipt vectors; AST factory with fake SDK/file outputs only, no launcher import",
                  activity=dict(actual_SDK_or_API_calls=0, children_or_compiler_or_DLL_loads=0,
                                unknown_image_or_GGUF_payload_reads=0))
    with PROOF.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(dict(proof=str(PROOF), sha256=pin(PROOF)["sha256"])))
    raise SystemExit(0 if result.wasSuccessful() else 1)
