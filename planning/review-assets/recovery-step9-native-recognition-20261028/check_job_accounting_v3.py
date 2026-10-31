"""Pure guard/module-path fixtures; no ctypes import/load or Windows API call."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HELPER = HERE / "probe_job_accounting_v3.py"
HELPER_SHA = "d5f23f471adc9d4ee293d2bee27a3d85443b578a4a116e50ce53ccd235920e49"
assert sys.flags.isolated and sys.dont_write_bytecode
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA
actual_denied = []


def actual_guard(event, args):
    if event in ("ctypes.dlopen", "subprocess.Popen", "os.system", "socket.__new__",
                 "socket.getaddrinfo", "socket.connect"):
        actual_denied.append(event)
        raise RuntimeError("Pure checks cannot load, dispatch or network")


sys.addaudithook(actual_guard)
spec = importlib.util.spec_from_file_location("owned_job_accounting_v3_pure", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
output = ROOT / "data/cache" / ("r09-job-accounting-v3-pure-checks-" + str(time.time_ns()))
output.mkdir(exist_ok=False)
cases = []


def captured_hook(preparing=False, worker=False):
    hooks = []
    original = sys.addaudithook
    sys.addaudithook = hooks.append
    try:
        helper.guard(dict(denied=[], dispatches=0, active_argv=None),
                     preparing=preparing, worker=worker)
    finally:
        sys.addaudithook = original
    assert len(hooks) == 1
    return hooks[0]


full = str(Path(os.environ["SystemRoot"]) / "System32/kernel32.dll")
other = str(output / "kernel32.dll")
parent = captured_hook()
for label, name, allowed in (("parent_current_process", None, True),
                             ("parent_exact_literal", "kernel32", True),
                             ("parent_exact_system_path", full, True),
                             ("parent_other_basename", "user32.dll", False),
                             ("parent_target_basename", "llama.dll", False),
                             ("parent_suffix_alias", "kernel32.dll", False),
                             ("parent_case_alias", "KERNEL32", False),
                             ("parent_other_full_path", other, False)):
    rejected = False
    try:
        parent("ctypes.dlopen", (name,))
    except RuntimeError:
        rejected = True
    assert rejected is not allowed, label
    cases.append(dict(name=label, passed=True, expected_allowed=allowed))
for role in ("preparation", "worker"):
    hook = captured_hook(preparing=role == "preparation", worker=role == "worker")
    for label, name in (("none", None), ("literal", "kernel32"), ("full", full)):
        try:
            hook("ctypes.dlopen", (name,))
        except RuntimeError:
            pass
        else:
            raise AssertionError(role + " must reject " + label)
        cases.append(dict(name=role + "_rejects_" + label, passed=True))

system = output / "mock-System32"
system.mkdir()
expected = system / "kernel32.dll"
wrong = output / "wrong-kernel32.dll"
expected.write_text("Pure fixture text, never loaded.", encoding="utf-8")
wrong.write_text("Pure mismatch fixture text, never loaded.", encoding="utf-8")


def reader(value, length=None):
    def read(capacity):
        assert capacity == 32768
        return len(value.encode("utf-16-le"))//2 if length is None else length, value
    return read


result = helper.verify_kernel_module_path(reader(str(expected)), expected)
assert result["verified_cached_module"] and Path(result["resolved_path"]) == expected
cases.append(dict(name="mock_exact_module_path_accepted", passed=True))
for label, read in (("mock_other_module_rejected", reader(str(wrong))),
                    ("mock_zero_length_rejected", reader("", 0)),
                    ("mock_truncation_rejected", reader("x" * 32768, 32768)),
                    ("mock_inconsistent_length_rejected", reader("abc", 4)),
                    ("mock_relative_path_rejected", reader("kernel32.dll"))):
    try:
        helper.verify_kernel_module_path(read, expected)
    except RuntimeError:
        pass
    else:
        raise AssertionError(label)
    cases.append(dict(name=label, passed=True))

v2 = HERE / "probe_job_accounting_v2.py"
def functions(path):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}
old, new = functions(v2), functions(HELPER)
for name in ("drain_capture", "publish_marker", "worker", "safe", "environment"):
    assert old[name] == new[name], name
trees = [ast.parse(path.read_text()) for path in (v2, HELPER)]
for name in ("LIMITS", "STAGES"):
    values = [next(ast.dump(node.value, include_attributes=False) for node in tree.body
                   if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name
                   for t in node.targets)) for tree in trees]
    assert values[0] == values[1], name
prior = HERE / "JOB-ACCOUNTING-V2-FAULT-CHECKS.json"
prior_value = json.loads(prior.read_bytes())
assert len(prior_value["cases"]) == 6 and prior_value["actual_children"] == 0
assert actual_denied == []
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA
report = dict(schema_version=1, status="passed_exact_parent_bootstrap_and_module_path_pure_fixtures",
              helper_sha256=HELPER_SHA, fixture_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              cases=cases, output=str(output), actual_children=0, network_requests=0,
              windows_api_calls=0, actual_ctypes_loads=0, actual_forbidden_events=actual_denied,
              captured_audit_closures_invoked_directly=True,
              unchanged_v2_functions=["drain_capture", "publish_marker", "worker", "safe", "environment"],
              unchanged_limits_and_stages=True,
              prior_six_pure_checks_sha256=hashlib.sha256(prior.read_bytes()).hexdigest(),
              scope="Direct calls to captured audit-hook closures and mocked path-reader callbacks; never import ctypes or load fixture files.")
with (HERE / "JOB-ACCOUNTING-V3-FAULT-CHECKS.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")
print(json.dumps(dict(status=report["status"], cases=len(cases), actual_children=0,
                     windows_api_calls=0, actual_ctypes_loads=0)))
