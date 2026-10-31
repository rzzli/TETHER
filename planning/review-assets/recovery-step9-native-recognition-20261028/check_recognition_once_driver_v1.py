"""Pure AST/fake checks for the exact bound driver; no parent import or dispatch."""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "execute_recognition_once_v1.py"
SOURCE_SHA = "71101d748da93dca8fcf3f888ecb3a57fad9b7619890948e492fae3b9b129681"
PROOF = HERE / "RECOGNITION-ONCE-DRIVER-PURE-PROOF-v1.json"
RAW = SOURCE.read_bytes()
assert hashlib.sha256(RAW).hexdigest() == SOURCE_SHA
TREE = ast.parse(RAW)
FUNCTIONS = {node.name: node for node in TREE.body if isinstance(node, ast.FunctionDef)}
LITERALS = {}
for node in TREE.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        try:
            LITERALS[node.targets[0].id] = ast.literal_eval(node.value)
        except ValueError:
            # Two dict(...) constants have only literal keywords.
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "dict":
                LITERALS[node.targets[0].id] = {kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords}
            elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "Path":
                LITERALS[node.targets[0].id] = ast.literal_eval(node.value.args[0])
SCENARIOS = []
DENIED = []


def guard(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.dlopen", "os.system")):
        DENIED.append(event)
        raise RuntimeError("Pure checker forbids process/network/native operation")
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = str(args[0]).lower()
        if path.endswith(".gguf") or path.endswith(".dll") or path.endswith("recognition.pack"):
            DENIED.append("payload_open")
            raise RuntimeError("Pure checker forbids payload opens")


sys.addaudithook(guard)


class Boundary:
    def __init__(self, *, consumed=False, terminal=None, error=None):
        self.calls = []
        self.now = 100.0
        self.started_passed = None
        self.consumed, self.error = consumed, error
        self.terminal = LITERALS["SUCCESS_STATUS"] if terminal is None else terminal
        self.read_delay = 0.0
        self.import_delay = 0.0
        self.execute_delay = 0.0
        pack = copy.deepcopy(LITERALS["FROZEN_PACK"])
        shards = copy.deepcopy(LITERALS["ORDERED_SHARDS"])
        self.config = dict(
            kind="detached_singleton_recognition_observation_v1", mode="--recognize",
            output="D:\\fake-owned-output", executable={"path": "D:\\fake-own.exe"},
            argv=["D:\\fake-own.exe", "--recognize", "D:\\fake-runtime", "D:\\fake-owned-output\\execution\\child",
                  pack["path"], "ggml-cpu-x64.dll", *shards],
            limits=copy.deepcopy(LITERALS["PROFILE"]), expected_pack_sha256=pack["sha256"],
            contract_sha256=LITERALS["CONTRACT_SHA"], module_policy_sha256=LITERALS["POLICY_SHA"],
            expected_version="0.7.0-dev", maximum_attempts=1, automatic_retry=False,
            full_vocabulary_mask=False, inference=False, original_SDK_general_gate=False,
            parent_seconds=300, child_seconds=120, cooperative_work_ms=117000,
            creation_flags=0x0008040C, hash_pass_policy={"driver_model_passes": 0},
            inputs=[{"path": "E:\\FORBIDDEN-PAYLOAD.gguf", "bytes": 4000000000, "sha256": "f" * 64}],
        )
        self.pins = {
            str(SOURCE): dict(path=str(SOURCE), bytes=len(RAW), sha256=SOURCE_SHA),
            "fake-helper.py": dict(path="fake-helper.py", bytes=7, sha256="b" * 64),
            "fake-protocol.json": dict(path="fake-protocol.json", bytes=9, sha256="c" * 64),
            "fake-decision.json": dict(path="fake-decision.json", bytes=11, sha256="a" * 64),
        }
        self.decision = dict(status=LITERALS["DECISION_STATUS"], success_status=LITERALS["SUCCESS_STATUS"],
                             driver=copy.deepcopy(self.pins[str(SOURCE)]), helper=copy.deepcopy(self.pins["fake-helper.py"]),
                             protocol=copy.deepcopy(self.pins["fake-protocol.json"]), maximum_attempts=1,
                             automatic_retry=False, output=self.config["output"], limits=copy.deepcopy(self.config["limits"]),
                             argv=copy.deepcopy(self.config["argv"]), frozen_pack=pack)
        owner = self

        class FakePath:
            def __init__(self, value): self.value = str(value)
            def exists(self):
                owner.calls.append("output_exists")
                return owner.consumed

        def clock():
            self.calls.append("clock")
            return self.now

        def technical_file(path, deadline):
            self.calls.append("read:" + str(path))
            self.now += self.read_delay
            self.namespace["check_clock"](deadline, "fake technical read")
            raw = json.dumps(self.decision if str(path) == "fake-decision.json" else self.config).encode()
            if str(path) == "fake-helper.py": raw = b"FAKE_HELPER_SOURCE"
            return copy.deepcopy(self.pins[str(path)]), raw

        def execute(config, expected, *, owner_started):
            self.calls.append("execute")
            self.started_passed = owner_started
            assert config == self.config and expected == "c" * 64
            self.now += self.execute_delay
            if self.error is not None: raise self.error
            return dict(status=self.terminal)

        def load_helper(raw, path, deadline):
            self.calls.append("fake_import")
            assert raw == b"FAKE_HELPER_SOURCE"
            self.now += self.import_delay
            self.namespace["check_clock"](deadline, "fake helper import")
            return SimpleNamespace(execute=execute)  # No validate_role/STATUS attribute.

        self.namespace = dict(LITERALS, __file__=str(SOURCE), BOUND=True, HELPER="fake-helper.py", HELPER_SHA="b" * 64,
                              PROTOCOL="fake-protocol.json", PROTOCOL_SHA="c" * 64, DECISION="fake-decision.json",
                              Path=FakePath, json=json, time=SimpleNamespace(monotonic=clock),
                              technical_file=technical_file, load_helper=load_helper,
                              print=lambda *args, **kwargs: self.calls.append("print"))
        nodes = [FUNCTIONS[name] for name in ("canonical", "check_clock", "main")]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), self.namespace)

    def run(self, expected="a" * 64):
        return self.namespace["main"](["--execute-once", expected])

    def retain(self, name):
        SCENARIOS.append(dict(name=name, calls=self.calls[:], execute_calls=self.calls.count("execute"),
                              fake_imports=self.calls.count("fake_import"), owner_started_passed=self.started_passed,
                              elapsed_seconds=self.now - 100.0))


class Cases(unittest.TestCase):
    def test_unbound_and_wrong_decision(self):
        for name in ("unbound", "wrong_hash"):
            case = Boundary()
            if name == "unbound": case.namespace["BOUND"] = False
            with self.assertRaises(RuntimeError): case.run("d" * 64 if name == "wrong_hash" else "a" * 64)
            self.assertEqual(case.calls[0], "clock")
            self.assertNotIn("fake_import", case.calls)
            self.assertNotIn("execute", case.calls)
            case.retain(name)

    def test_exact_authority_and_role_negatives(self):
        for field in ("driver", "helper", "protocol", "maximum_attempts", "success_status", "limits_bool",
                      "mode", "pack", "shard_order", "full_mask", "inference", "CPU_basename", "driver_hash_pass"):
            case = Boundary()
            if field in ("driver", "helper", "protocol"): case.decision[field]["sha256"] = "d" * 64
            elif field == "maximum_attempts": case.decision[field] = True
            elif field == "success_status": case.decision[field] = "ABI_observations_retained_independent_qualification_pending"
            elif field == "limits_bool": case.decision["limits"]["maximum_children"] = True
            elif field == "mode": case.config["mode"] = "--abi"
            elif field == "pack": case.config["argv"][4] = "D:\\favorable-subset.pack"
            elif field == "shard_order": case.config["argv"][6:] = list(reversed(case.config["argv"][6:]))
            elif field == "full_mask": case.config["full_vocabulary_mask"] = True
            elif field == "inference": case.config["inference"] = True
            elif field == "CPU_basename": case.config["argv"][5] = "ggml-cpu-other.dll"
            else: case.config["hash_pass_policy"]["driver_model_passes"] = True
            with self.assertRaises(RuntimeError, msg=field): case.run()
            self.assertNotIn("fake_import", case.calls, field)
            self.assertNotIn("execute", case.calls, field)
            case.retain("wrong_" + field)

    def test_consumed_output_zero_dispatch(self):
        case = Boundary(consumed=True)
        with self.assertRaisesRegex(RuntimeError, "consumed"): case.run()
        self.assertNotIn("fake_import", case.calls)
        self.assertNotIn("execute", case.calls)
        case.retain("consumed_output")

    def test_success_one_call_original_clock_and_no_payload_prehash(self):
        case = Boundary()
        case.read_delay = 0.5
        case.import_delay = 0.5
        self.assertEqual(case.run(), 0)
        self.assertEqual(case.calls[0], "clock")
        self.assertEqual(case.started_passed, 100.0)
        self.assertEqual(case.calls.count("execute"), 1)
        self.assertEqual([call[5:] for call in case.calls if call.startswith("read:")],
                         ["fake-decision.json", str(SOURCE), "fake-helper.py", "fake-protocol.json"])
        case.retain("success_same_start_no_payload_read")

    def test_deadlines_before_dispatch_and_after_seal(self):
        for stage in ("technical", "import", "execute"):
            case = Boundary()
            if stage == "technical": case.read_delay = 296
            elif stage == "import": case.import_delay = 296
            else: case.execute_delay = 301
            with self.assertRaises(TimeoutError): case.run()
            self.assertEqual(case.calls.count("execute"), 1 if stage == "execute" else 0)
            case.retain("deadline_" + stage)

    def test_failure_and_interruptions_never_retry(self):
        for name, terminal, error in (("failed", "failed", None), ("wrong_success", "ABI_observations_retained_independent_qualification_pending", None),
                                      ("exception", None, RuntimeError("Synthetic execute error")),
                                      ("KeyboardInterrupt", None, KeyboardInterrupt()), ("SystemExit", None, SystemExit(7))):
            case = Boundary(terminal=terminal, error=error)
            if error is None: self.assertEqual(case.run(), 1)
            else:
                with self.assertRaises(type(error)): case.run()
            self.assertEqual(case.calls.count("execute"), 1)
            case.retain(name)

    def test_bounded_technical_reader_uses_no_other_paths(self):
        for name, raw in (("bounded", b"metadata"), ("over_cap", b"123456789")):
            opened = []
            class MemoryPath:
                def __init__(self, path): self.path = path
                def __str__(self): return self.path
                def open(self, mode):
                    opened.append(self.path)
                    self_outer.assertEqual(mode, "rb")
                    return io.BytesIO(raw)
            self_outer = self
            namespace = dict(Path=MemoryPath, hashlib=hashlib, TECHNICAL_FILE_BYTES=8,
                             check_clock=lambda *args: None)
            exec(compile(ast.Module(body=[FUNCTIONS["technical_file"]], type_ignores=[]), str(SOURCE), "exec"), namespace)
            if name == "bounded":
                pin, result = namespace["technical_file"]("fixed-technical.json", 295)
                self.assertEqual(result, raw)
                self.assertEqual(pin["sha256"], hashlib.sha256(raw).hexdigest())
            else:
                with self.assertRaisesRegex(RuntimeError, "fixed cap"):
                    namespace["technical_file"]("fixed-technical.json", 295)
            self.assertEqual(opened, ["fixed-technical.json"])

    def test_source_scope_and_metadata_binding(self):
        main = FUNCTIONS["main"]
        self.assertIsInstance(main.body[0], ast.Assign)
        self.assertEqual(ast.unparse(main.body[0].value), "time.monotonic()")
        self.assertTrue(LITERALS["BOUND"])
        expected_paths = {"HELPER": "run_recognition_observation_v7.py", "PROTOCOL": "RECOGNITION-EXECUTION-PROTOCOL-v1.json",
                          "DECISION": "RECOGNITION-EXECUTION-ROOT-DECISION-v1.json"}
        for name, leaf in expected_paths.items(): self.assertEqual(LITERALS[name], str(HERE / leaf))
        self.assertEqual(LITERALS["HELPER_SHA"], "b2aafdd98b797f181d4d718b5edab75a4dad4e16a735cbf719baa5c58cb54b09")
        self.assertEqual(LITERALS["PROTOCOL_SHA"], "b690c63bbcc576dab0ea02b4f6359ed31b24edc39a850bc945789563bf99bbf2")
        template_raw = (HERE / "execute_recognition_once_draft_v1.py").read_bytes()
        self.assertEqual(hashlib.sha256(template_raw).hexdigest(), "a9e115317b9a3851dddf832c5c3042f511acfd9bbe91f32a5b97a4e7e8d6f092")
        template_tree = ast.parse(template_raw)
        values = {node.targets[0].id: node.value for node in template_tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
        normalized = copy.deepcopy(TREE)
        allowed = {"BOUND", "HELPER", "HELPER_SHA", "PROTOCOL", "PROTOCOL_SHA", "DECISION"}
        for node in normalized.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in allowed:
                node.value = copy.deepcopy(values[node.targets[0].id])
        self.assertEqual(ast.dump(normalized, include_attributes=False), ast.dump(template_tree, include_attributes=False))
        self.assertEqual(sum(a != b for a, b in zip(template_raw.splitlines(), RAW.splitlines())), 6)
        report_raw = (HERE.parents[2] / "data/cache/r09-recognition-preparation-v1-20261029.json").read_bytes()
        self.assertEqual(hashlib.sha256(report_raw).hexdigest(), "e0290900e15464ead2343eebb9f207709b329d258926f43a4fadb895ce489416")
        report = json.loads(report_raw)
        for name, key in (("HELPER", "helper"), ("PROTOCOL", "protocol")):
            self.assertEqual(LITERALS[name], report[key]["path"])
            actual_raw = Path(LITERALS[name]).read_bytes()
            self.assertEqual(len(actual_raw), report[key]["bytes"])
            self.assertEqual(hashlib.sha256(actual_raw).hexdigest(), report[key]["sha256"])
        self.assertFalse(report["execution_authorized"])
        self.assertNotIn("validate_role", {node.attr for node in ast.walk(main) if isinstance(node, ast.Attribute)})
        self.assertEqual(sum(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "execute" for node in ast.walk(main)), 1)
        contract = json.loads((HERE / "RECOGNITION-EXECUTION-CONTRACT-v1.json").read_bytes())
        metadata = json.loads((HERE / "RECOGNITION-EXPECTED-PACK-METADATA-v1.json").read_bytes())
        self.assertEqual(LITERALS["FROZEN_PACK"], metadata["pack"])
        self.assertEqual(LITERALS["ORDERED_SHARDS"], [record["path"] for record in contract["ordered_shard_descriptors"]])
        self.assertEqual(LITERALS["CONTRACT_SHA"], hashlib.sha256((HERE / "RECOGNITION-EXECUTION-CONTRACT-v1.json").read_bytes()).hexdigest())
        self.assertEqual(LITERALS["POLICY_SHA"], contract["module_policy_sha256"])


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    proof = dict(schema_version=1, status="passed" if result.wasSuccessful() else "failed",
                 source_sha256=SOURCE_SHA, checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 source_unchanged=hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA,
                 tests=result.testsRun, failures=[str(item) for item in result.failures], errors=[str(item) for item in result.errors],
                 scenarios=SCENARIOS, audit_denials=DENIED, source_bound=True,
                 template_sha256="a9e115317b9a3851dddf832c5c3042f511acfd9bbe91f32a5b97a4e7e8d6f092",
                 permitted_assignment_delta=6, normalized_whole_module_AST_equal=True,
                 preparation_report_sha256="e0290900e15464ead2343eebb9f207709b329d258926f43a4fadb895ce489416",
                 actual_parent_imports=0, actual_SDK_constructions=0, actual_child_dispatches=0,
                 CPU_GGUF_pack_payload_reads=0, preparation_or_protocol_created=False,
                 scope="AST-extracted driver functions with fake files/clock/helper; metadata-only descriptor comparison, no actual driver/parent invocation")
    with PROOF.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(proof, output, indent=2)
        output.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
