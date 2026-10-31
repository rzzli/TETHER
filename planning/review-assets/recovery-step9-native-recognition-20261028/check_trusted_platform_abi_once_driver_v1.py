"""Six AST-extracted driver admission/fake-call tests; no parent import or OS call."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "execute_trusted_platform_abi_once_v1.py"
EXPECTED_SOURCE_SHA = "507211b3cdfb728c3ffb6a238f313905f4594434da22277eb57f87219a85732c"
PROOF = HERE / "TRUSTED-PLATFORM-ABI-ONCE-DRIVER-PURE-PROOF-v1.json"
SCENARIOS = []
RAW = SOURCE.read_bytes()
assert hashlib.sha256(RAW).hexdigest() == EXPECTED_SOURCE_SHA
TREE = ast.parse(RAW)
MAIN = next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "main")


def literal(name):
    return next(ast.literal_eval(node.value) for node in TREE.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))


class FakeBoundary:
    def __init__(self, *, consumed=False, terminal=None, error=None):
        self.calls = []
        self.consumed, self.terminal, self.error = consumed, literal("SUCCESS_STATUS") if terminal is None else terminal, error
        self.config = dict(output="D:\\own-fake-output", limits={"maximum_children": 1},
                           mode="--abi", explicit_target_calls=["llama_version", "llama_model_default_params"],
                           recognition_enabled=False, no_model_or_CPU_paths_supplied=True, inputs=[dict(path="fake-input.json", bytes=3, sha256="c" * 64)])
        self.pins = {str(SOURCE): dict(path=str(SOURCE), bytes=len(RAW), sha256=EXPECTED_SOURCE_SHA),
                     "fake-helper.py": dict(path="fake-helper.py", bytes=5, sha256=literal("HELPER_SHA")),
                     "fake-protocol.json": dict(path="fake-protocol.json", bytes=7, sha256=literal("PROTOCOL_SHA")),
                     "fake-decision.json": dict(path="fake-decision.json", bytes=11, sha256="a" * 64),
                     "fake-input.json": copy.deepcopy(self.config["inputs"][0])}
        self.decision = dict(status="root_authorizes_one_exact_trusted_platform_ABI_observation", success_status=literal("SUCCESS_STATUS"),
                             driver=copy.deepcopy(self.pins[str(SOURCE)]), helper=copy.deepcopy(self.pins["fake-helper.py"]),
                             protocol=copy.deepcopy(self.pins["fake-protocol.json"]), maximum_attempts=1,
                             automatic_retry=False, output=self.config["output"], limits=copy.deepcopy(self.config["limits"]))
        owner = self

        class FakePath:
            def __init__(self, value): self.value = str(value)
            def __str__(self): return self.value
            def exists(self):
                owner.calls.append("exists")
                return owner.consumed
            def read_text(self, **kwargs):
                return json.dumps(owner.decision if self.value == "fake-decision.json" else owner.config)

        def validate_role(config):
            self.calls.append("validate_role")
            if config != self.config: raise RuntimeError("Fake role differs")

        def execute(config, expected):
            self.calls.append("execute")
            if self.error: raise self.error
            return dict(status=self.terminal)

        self.helper = SimpleNamespace(validate_role=validate_role, execute=execute)
        loader = SimpleNamespace(exec_module=lambda module: self.calls.append("fake_import"))
        util = SimpleNamespace(spec_from_file_location=lambda *args: SimpleNamespace(loader=loader),
                               module_from_spec=lambda spec: self.helper)
        self.namespace = dict(__file__=str(SOURCE), pin=lambda path: copy.deepcopy(self.pins[str(path)]),
                              DECISION=FakePath("fake-decision.json"), HELPER="fake-helper.py",
                              HELPER_SHA=literal("HELPER_SHA"), PROTOCOL=FakePath("fake-protocol.json"),
                              PROTOCOL_SHA=literal("PROTOCOL_SHA"), SUCCESS_STATUS=literal("SUCCESS_STATUS"), Path=FakePath, json=json, util=util,
                              print=lambda *args, **kwargs: self.calls.append("print"))
        exec(compile(ast.Module(body=[MAIN], type_ignores=[]), str(SOURCE), "exec"), self.namespace)

    def run(self, expected="a" * 64):
        return self.namespace["main"](["--execute-once", expected])

    def retain(self, name):
        SCENARIOS.append(dict(name=name, calls=self.calls[:], execute_calls=self.calls.count("execute"),
                              fake_imports=self.calls.count("fake_import")))


class Cases(unittest.TestCase):
    def test_wrong_decision_hash_blocks_import_and_call(self):
        case = FakeBoundary()
        with self.assertRaisesRegex(RuntimeError, "decision bytes"):
            case.run("b" * 64)
        self.assertNotIn("fake_import", case.calls)
        self.assertNotIn("execute", case.calls)
        case.retain("wrong_decision_hash")

    def test_wrong_helper_protocol_and_role_block(self):
        for field in ("driver", "helper", "protocol", "status", "maximum_attempts_bool", "limits_bool", "automatic_retry", "mode",
                      "success_status", "calls", "recognition", "CPU_flags"):
            case = FakeBoundary()
            if field in ("driver", "helper", "protocol"): case.decision[field]["sha256"] = "d" * 64
            elif field == "maximum_attempts_bool": case.decision["maximum_attempts"] = True
            elif field == "limits_bool": case.decision["limits"]["maximum_children"] = True
            elif field == "automatic_retry": case.decision[field] = True
            elif field == "mode": case.config[field] = "--module-census"
            elif field == "success_status": case.decision[field] = "genuine_native_qualification_claim_not_allowed"
            elif field == "calls": case.config["explicit_target_calls"].append("llama_backend_init")
            elif field == "recognition": case.config["recognition_enabled"] = True
            elif field == "CPU_flags": case.config["no_model_or_CPU_paths_supplied"] = False
            else: case.decision[field] = "unapproved"
            try:
                with self.assertRaises(RuntimeError, msg=field): case.run()
                self.assertNotIn("execute", case.calls, field)
            finally:
                case.retain("wrong_" + field)

    def test_preconsumed_output_zero_dispatch(self):
        case = FakeBoundary(consumed=True)
        with self.assertRaisesRegex(RuntimeError, "consumed"):
            case.run()
        self.assertNotIn("fake_import", case.calls)
        self.assertNotIn("execute", case.calls)
        case.retain("preconsumed_output")

    def test_success_exactly_one_call(self):
        case = FakeBoundary()
        self.assertFalse(hasattr(case.helper, "STATUS"))
        self.assertEqual(literal("SUCCESS_STATUS"), "ABI_observations_retained_independent_qualification_pending")
        self.assertEqual(case.run(), 0)
        self.assertEqual(case.calls.count("execute"), 1)
        case.retain("success")

    def test_failed_execution_no_retry(self):
        for terminal, error in (("failed", None), ("wrong_success_status", None), (None, RuntimeError("Synthetic execute failure"))):
            case = FakeBoundary(terminal=terminal, error=error)
            if error:
                with self.assertRaises(RuntimeError): case.run()
            else:
                self.assertEqual(case.run(), 1)
            self.assertEqual(case.calls.count("execute"), 1)
            case.retain("failed_execution_" + str(terminal))

    def test_interrupted_execution_no_retry(self):
        for error in (KeyboardInterrupt(), SystemExit(7)):
            case = FakeBoundary(error=error)
            with self.assertRaises(type(error)): case.run()
            self.assertEqual(case.calls.count("execute"), 1)
            case.retain(type(error).__name__)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    proof = dict(schema_version=1, status="passed" if result.wasSuccessful() else "failed",
                 source_sha256=EXPECTED_SOURCE_SHA, checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 source_unchanged=hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SOURCE_SHA,
                 tests=result.testsRun, failures=[str(item) for item in result.failures], errors=[str(item) for item in result.errors],
                 scenarios=SCENARIOS, actual_parent_imports=0, actual_SDK_constructions=0, actual_child_dispatches=0,
                 scope="Only AST-extracted driver main with authored fake pins/files/import boundary/helper; no real parent import or native execution")
    with PROOF.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(proof, output, indent=2)
        output.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
