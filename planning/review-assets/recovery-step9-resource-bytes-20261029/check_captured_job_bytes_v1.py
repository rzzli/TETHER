"""Finite data-only checks against pre-implementation literal Job fixtures."""
import ast
import copy
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "captured_job_bytes_v1.py"
CONTRACT = HERE / "CAPTURED-JOB-BYTES-CONTRACT-v2.json"
FIXTURES = HERE / "CAPTURED-JOB-BYTES-FIXTURES-v1.json"
FREEZE = HERE / "CAPTURED-JOB-BYTES-FIXTURE-FREEZE-v1.json"
PROOF = HERE / "CAPTURED-JOB-BYTES-PURE-PROOF-v1.json"


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def subset(test, got, expected):
    if type(expected) is dict:
        test.assertIs(type(got), dict)
        for key, value in expected.items():
            test.assertIn(key, got)
            subset(test, got[key], value)
    else:
        test.assertIs(type(got), type(expected))
        test.assertEqual(got, expected)


def main():
    started = time.monotonic()
    if PROOF.exists():
        raise FileExistsError(PROOF)
    before = {key: pin(path) for key, path in dict(source=SOURCE, contract=CONTRACT, fixtures=FIXTURES, freeze=FREEZE).items()}
    frozen = json.loads(FREEZE.read_bytes())
    assert frozen["source_decoder_implemented"] is False
    assert frozen["fixtures"]["sha256"] == before["fixtures"]["sha256"]
    assert frozen["contract"]["sha256"] == before["contract"]["sha256"]
    corpus = json.loads(FIXTURES.read_bytes())
    spec = importlib.util.spec_from_file_location("captured_job_bytes_checked_v1", SOURCE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    cases = {item["id"]: item for item in corpus["captures"]}
    checks = dict(literal_captures=0, literal_phases=0, API_controls=0, mutation_vectors=0)

    class Checks(unittest.TestCase):
        def fresh(self, identity="assigned_return16"):
            return copy.deepcopy(cases[identity]["snapshot"])

        def test_frozen_literal_capture_and_phase_projections(self):
            for item in corpus["captures"]:
                with self.subTest(item=item["id"]):
                    original = copy.deepcopy(item["snapshot"])
                    result = mod.decode_job_snapshot(item["snapshot"])
                    self.assertIs(type(result), mod.DecodedJobSnapshot)
                    subset(self, result.to_dict(), item["expected_projection"])
                    self.assertEqual(original, item["snapshot"])
                    checks["literal_captures"] += 1
                    for phase in item["phase_checks"]:
                        row = mod.check_snapshot_phase(result, phase["expected_phase"], phase["own_pid"]).to_dict()
                        subset(self, row, {key: value for key, value in phase.items() if key != "own_pid"})
                        checks["literal_phases"] += 1

        def test_frozen_API_negative_controls(self):
            for item in corpus["api_controls"]:
                with self.subTest(item=item["id"]):
                    exc = {"ValueError": ValueError, "TypeError": TypeError}[item["expected_exception"]]
                    with self.assertRaises(exc) as caught:
                        if item["operation"] == "decode_job_snapshot":
                            mod.decode_job_snapshot(item["input"])
                        else:
                            arg = (mod.decode_job_snapshot(cases[item["fixture_id"]]["snapshot"])
                                   if "fixture_id" in item else item["input"])
                            mod.check_snapshot_phase(arg, item["expected_phase"], item["own_pid"])
                    if "expected_message" in item:
                        self.assertEqual(str(caught.exception), item["expected_message"])
                    checks["API_controls"] += 1

        def test_source_views_never_bool_or_repaired(self):
            for channel, field in (("accounting", "TotalPageFaultCount"), ("accounting", "TotalProcesses"),
                                   ("pid_list", "assigned_count"), ("pid_list", "listed_count"), ("pid_list", "pids")):
                with self.subTest(channel=channel, field=field):
                    raw = self.fresh()
                    if channel == "accounting": raw[channel]["decoded"][field] = True
                    else: raw[channel][field] = [True] if field == "pids" else True
                    result = mod.decode_job_snapshot(raw)
                    self.assertTrue(result.raw_complete)
                    self.assertIs(result.source_views_consistent, False)
                    self.assertEqual(mod.check_snapshot_phase(result, "assigned", 1234).status, "unresolved")
                    checks["mutation_vectors"] += 1

        def test_metadata_bounds_and_independent_channel_retention(self):
            vectors = [("ok", 1), ("ok", None), ("error", True), ("error", -1), ("error", 2**32),
                       ("returned_bytes", False), ("returned_bytes", -1), ("returned_bytes", 2**32),
                       ("raw_hex", "ff" * 100000), ("raw_hex", "A0" * 48), ("raw_hex", "00 " * 48)]
            for key, value in vectors:
                with self.subTest(key=key, value_type=type(value).__name__):
                    raw = self.fresh(); raw["accounting"][key] = value
                    result = mod.decode_job_snapshot(raw)
                    self.assertFalse(result.raw_complete)
                    self.assertEqual(result.accounting.status, "malformed")
                    self.assertEqual(result.pid_list.status, "decoded")
                    self.assertIsNone(result.accounting.to_dict()[key])
                    self.assertLess(len(json.dumps(result.to_dict())), 2000)
                    checks["mutation_vectors"] += 1
            raw = self.fresh(); raw["accounting"]["error"] = 5
            self.assertEqual(mod.decode_job_snapshot(raw).accounting.status, "malformed")
            for channel in ("accounting", "pid_list"):
                raw = self.fresh(); raw[channel]["ok"] = False
                self.assertEqual(mod.decode_job_snapshot(raw).to_dict()[channel]["status"], "undefined")
                self.assertIsNone(mod.decode_job_snapshot(raw).to_dict()[channel]["fields"])
                checks["mutation_vectors"] += 1

        def test_PID_frame_capacity_lengths_and_tail(self):
            raw = self.fresh()
            ids = tuple(0xFFFFFFFF00000000 + index for index in range(16))
            raw["pid_list"].update(raw_hex=struct.pack("<II16Q", 16, 16, *ids).hex(),
                                   returned_bytes=136, assigned_count=16, listed_count=16, pids=list(ids))
            result = mod.decode_job_snapshot(raw)
            self.assertEqual(result.pid_list.to_dict()["fields"]["pids"], list(ids))
            self.assertTrue(result.raw_complete)
            self.assertEqual(mod.check_snapshot_phase(result, "assigned", 1234).status, "counter_or_PID_mismatch")
            for assigned, listed, returned in ((17, 16, 136), (16, 17, 136), (1, 0, 8), (1, 1, 7), (1, 1, 137)):
                with self.subTest(assigned=assigned, listed=listed, returned=returned):
                    vector = self.fresh()
                    vector["pid_list"].update(raw_hex=struct.pack("<II16Q", assigned, listed, *range(16)).hex(), returned_bytes=returned)
                    got = mod.decode_job_snapshot(vector)
                    self.assertEqual(got.pid_list.status, "malformed")
                    self.assertIsNone(got.pid_list.fields)
                    checks["mutation_vectors"] += 1
            vector = self.fresh("unused_PID_tail_not_members"); vector["pid_list"]["returned_bytes"] = 136
            self.assertEqual(mod.decode_job_snapshot(vector).pid_list.to_dict()["fields"]["pids"], [])

        def test_window_and_API_schema(self):
            for start, end in ((True, 100), (100, False), (-1, 100), (101, 100), (None, 100), ("100", 100)):
                raw = self.fresh(); raw.update(query_started_monotonic_ns=start, query_finished_monotonic_ns=end)
                got = mod.decode_job_snapshot(raw)
                self.assertFalse(got.query_window_valid)
                self.assertFalse(got.raw_complete)
                self.assertEqual(got.accounting.status, "decoded")
                self.assertEqual(got.pid_list.status, "decoded")
                checks["mutation_vectors"] += 1
            for raw in ([], True, {}, {"ready": True}):
                with self.assertRaisesRegex(ValueError, "snapshot_schema"):
                    mod.decode_job_snapshot(raw)
            result = mod.decode_job_snapshot(self.fresh())
            for pid in (True, -1, 2**32, 0, None):
                with self.assertRaisesRegex(ValueError, "own_pid"):
                    mod.check_snapshot_phase(result, "assigned", pid)
            for pid in (True, 1, -1):
                with self.assertRaisesRegex(ValueError, "own_pid"):
                    mod.check_snapshot_phase(result, "empty", pid)
            with self.assertRaisesRegex(ValueError, "expected_phase"):
                mod.check_snapshot_phase(result, "qualified", 1234)
            class Derived(mod.DecodedJobSnapshot): pass
            derived = Derived(True, True, result.accounting, result.pid_list, ())
            with self.assertRaisesRegex(TypeError, "decoder_result_type"):
                mod.check_snapshot_phase(derived, "assigned", 1234)

        def test_ordinary_immutability_and_fresh_serialization(self):
            raw = self.fresh(); result = mod.decode_job_snapshot(raw)
            with self.assertRaises(dataclasses.FrozenInstanceError): result.capture_present = False
            with self.assertRaises(dataclasses.FrozenInstanceError): result.accounting.status = "qualified"
            exported = result.to_dict(); exported["accounting"]["fields"]["TotalProcesses"] = 77
            exported["pid_list"]["fields"]["pids"].append(999)
            exported["accounting"]["issues"].append("fabricated")
            raw["pid_list"]["pids"].append(999)
            self.assertEqual(result.to_dict()["accounting"]["fields"]["TotalProcesses"], 1)
            self.assertEqual(result.to_dict()["pid_list"]["fields"]["pids"], [1234])
            phase = mod.check_snapshot_phase(result, "assigned", 1234)
            data = phase.to_dict(); data["observed_state"]["pids"].clear()
            self.assertEqual(phase.to_dict()["observed_state"]["pids"], [1234])
            self.assertFalse(phase.resource_qualified)
            self.assertFalse(result.resource_qualified)
            self.assertFalse(result.atomic_snapshot)

        def test_scope_source_imports_and_no_qualification_flags(self):
            tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
            imports = [node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
                       for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
            self.assertEqual(imports, ["dataclasses", "re", "struct"])
            forbidden_calls = {"open", "eval", "exec", "compile", "__import__"}
            self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in forbidden_calls
                                 for n in ast.walk(tree)))

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    elapsed = time.monotonic() - started
    after = {key: pin(Path(value["path"])) for key, value in before.items()}
    stable = before == after
    proof = dict(schema_version=1, status="passed" if result.wasSuccessful() and stable and elapsed < 20 else "failed",
                 source=before["source"], contract=before["contract"], fixtures=before["fixtures"], freeze=before["freeze"],
                 checker=pin(Path(__file__).resolve()), methods=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                 failure_details=[dict(test=str(case), traceback=trace) for case, trace in result.failures + result.errors],
                 counts=checks, elapsed_seconds=elapsed, maximum_seconds=20, source_pins_stable=stable,
                 scope="pure captured-buffer decode and selected source-phase consistency only",
                 full_resource_qualification=False, SDK_OS_native_calls=0, CPU_GGUF_oldpack_operations=0,
                 original_source_qualification=False, hostile_Python_security_claim=False)
    with PROOF.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(proof, out, indent=2); out.write("\n")
    print(json.dumps(dict(status=proof["status"], methods=proof["methods"], counts=checks, elapsed_seconds=elapsed,
                          proof_sha256=pin(PROOF)["sha256"])))
    return 0 if proof["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
