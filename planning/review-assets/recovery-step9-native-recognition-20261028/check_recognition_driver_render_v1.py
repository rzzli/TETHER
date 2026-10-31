"""Three pure render checks; no driver/parent import, protocol or final driver."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "render_recognition_once_driver_v1.py"
SOURCE_SHA = "e1c46ac5f727d2f0d76e218c427db49841ab576baa1114a04693d94bed26409a"
TEMPLATE = HERE / "execute_recognition_once_draft_v1.py"
TEMPLATE_SHA = "a9e115317b9a3851dddf832c5c3042f511acfd9bbe91f32a5b97a4e7e8d6f092"
PROOF = HERE / "RECOGNITION-DRIVER-RENDER-PURE-PROOF-v1.json"
RAW = SOURCE.read_bytes()
TEMPLATE_RAW = TEMPLATE.read_bytes()
assert hashlib.sha256(RAW).hexdigest() == SOURCE_SHA
assert hashlib.sha256(TEMPLATE_RAW).hexdigest() == TEMPLATE_SHA
DENIALS = []
CASES = []


def guard(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.dlopen", "os.system")):
        DENIALS.append(event)
        raise RuntimeError("Pure render checker forbids process/native/network")
    if event == "open" and isinstance(args[0], (str, bytes)):
        value = str(args[0]).lower()
        if value.endswith((".gguf", ".dll", "recognition.pack")):
            DENIALS.append("payload_open")
            raise RuntimeError("Pure render checker forbids payload access")


sys.addaudithook(guard)
NAMESPACE = {}
exec(compile(RAW, str(SOURCE), "exec"), NAMESPACE)
RENDER = NAMESPACE["render_driver"]
PHASE = NAMESPACE["PHASE"]
FAKE = dict(helper_path=PHASE + r"\run_recognition_observation_v999.py", helper_sha256="b" * 64,
            protocol_path=PHASE + r"\RECOGNITION-EXECUTION-PROTOCOL-v999.json", protocol_sha256="c" * 64,
            decision_path=PHASE + r"\RECOGNITION-EXECUTION-ROOT-DECISION-v999.json")


class Cases(unittest.TestCase):
    def test_exact_literal_only_render_preserves_every_function(self):
        rendered = RENDER(TEMPLATE_RAW, FAKE)
        before, after = ast.parse(TEMPLATE_RAW), ast.parse(rendered)
        functions = lambda tree: {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(functions(before), functions(after))
        changed = [(left, right) for left, right in zip(TEMPLATE_RAW.decode().splitlines(), rendered.decode().splitlines()) if left != right]
        self.assertEqual(len(changed), 6)
        self.assertTrue(all(left.split(" = ")[0] in NAMESPACE["ASSIGNMENTS"] for left, right in changed))
        constants = {node.targets[0].id: node.value for node in after.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
        self.assertIs(ast.literal_eval(constants["BOUND"]), True)
        self.assertEqual(ast.literal_eval(constants["HELPER"].args[0]), FAKE["helper_path"])
        self.assertEqual(ast.literal_eval(constants["PROTOCOL"].args[0]), FAKE["protocol_path"])
        self.assertEqual(ast.literal_eval(constants["DECISION"].args[0]), FAKE["decision_path"])
        self.assertEqual(NAMESPACE["_normalized"](after, before), ast.dump(before, include_attributes=False))
        CASES.append(dict(name="six_literal_bindings_in_memory", changed_assignments=6, unchanged_functions=len(functions(before)),
                          rendered_sha256=hashlib.sha256(rendered).hexdigest(), rendered_bytes=len(rendered), written=False, executed=False))

    def test_bad_template_or_bindings_reject_before_render(self):
        for name in ("template", "extra_key", "missing_key", "CPU_path", "outside_phase", "traversal", "protocol_as_helper", "upper_hash", "boolean_hash"):
            value = copy.deepcopy(FAKE)
            raw = TEMPLATE_RAW
            if name == "template": raw += b"\n# unreviewed source change\n"
            elif name == "extra_key": value["maximum_attempts"] = 2
            elif name == "missing_key": value.pop("decision_path")
            elif name == "CPU_path": value["helper_path"] = PHASE + r"\ggml-cpu-x64.dll"
            elif name == "outside_phase": value["helper_path"] = r"E:\run_recognition_observation_v999.py"
            elif name == "traversal": value["protocol_path"] = PHASE + r"\..\RECOGNITION-EXECUTION-PROTOCOL-v999.json"
            elif name == "protocol_as_helper": value["helper_path"] = value["protocol_path"]
            elif name == "upper_hash": value["helper_sha256"] = "B" * 64
            else: value["protocol_sha256"] = True
            with self.assertRaises(RuntimeError, msg=name): RENDER(raw, value)
            CASES.append(dict(name="rejected_" + name, written=False, executed=False))

    def test_no_authoring_io_cli_or_actual_binding(self):
        tree = ast.parse(RAW)
        self.assertFalse(any(isinstance(node, ast.If) and isinstance(node.test, ast.Compare) for node in tree.body))
        attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        self.assertFalse(attributes & {"open", "stat", "lstat", "read_bytes", "write_bytes", "execute", "Popen", "WinDLL"})
        self.assertEqual(hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(), TEMPLATE_SHA)
        self.assertIn(b"BOUND = False\n", TEMPLATE_RAW)
        self.assertTrue(all(b"\n" + name + b" = None\n" in TEMPLATE_RAW for name in (b"HELPER", b"HELPER_SHA", b"PROTOCOL", b"PROTOCOL_SHA", b"DECISION")))
        CASES.append(dict(name="original_unbound_no_filesystem_or_dispatch_capability", written=False, executed=False))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    proof = dict(schema_version=1, status="passed" if result.wasSuccessful() else "failed",
                 helper_sha256=SOURCE_SHA, template_sha256=TEMPLATE_SHA,
                 checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), tests=result.testsRun,
                 failures=[str(item) for item in result.failures], errors=[str(item) for item in result.errors],
                 scenarios=CASES, audit_denials=DENIALS, actual_parent_imports=0, actual_driver_executions=0,
                 actual_SDK_constructions=0, child_dispatches=0, CPU_GGUF_pack_operations=0,
                 final_driver_created=False, protocol_or_binding_preparation=False,
                 scope="Fake literals rendered to memory only; neither actual future paths nor source execution authorized")
    with PROOF.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(proof, output, indent=2)
        output.write("\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
