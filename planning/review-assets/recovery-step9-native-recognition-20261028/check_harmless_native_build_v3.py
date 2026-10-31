"""Focused PURE build-finalization checks; no tools, Job APIs or worker run."""
from datetime import datetime, timezone
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HELPER = HERE / "build_harmless_native_worker_v3.py"
REPORT = HERE / "HARMLESS-NATIVE-BUILD-PURE-CHECKS-v3.json"
need_absent = not REPORT.exists()
if not need_absent:
    raise RuntimeError("Pure checks already retained; no overwrite")
spec = util.spec_from_file_location("own_build_pure_checks", HELPER)
helper = util.module_from_spec(spec); spec.loader.exec_module(helper)
frozen = helper.basis()
output = ROOT / "data/cache" / ("r09-harmless-native-build-pure-v3-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
output.mkdir()
dispatches = []
def guard(event, args):
    if event in ("subprocess.Popen", "os.system", "socket.__new__", "socket.connect", "socket.getaddrinfo"):
        dispatches.append(event); raise RuntimeError("Pure fixture dispatch/network forbidden")
sys.addaudithook(guard)

checks = []
def check(name, action):
    action(); checks.append(dict(name=name, passed=True))
def assert_true(value, message):
    if not value:
        raise AssertionError(message)
def rejects(action):
    try:
        action()
    except RuntimeError:
        return
    raise AssertionError("Required rejection did not occur")
class Lease:
    def __init__(self, error=False):
        self.error, self.attempts = error, 0
    def close(self):
        self.attempts += 1
        if self.error:
            raise OSError("Injected context-manager close failure")

def finalization_case(name, primary=False, close_error=False):
    folder = output / name
    journal = frozen.RunJournal(folder, kind="build")
    journal.append("synthetic_fixture_only", actual_children=0, actual_compiles=0)
    result = dict(schema_version=1, status="failed" if primary else helper.STATUS, pure_fixture=True, commands=[])
    if primary:
        frozen.write_new(folder / "failure.json", dict(authoritative=True, injected_primary=True))
    before = frozen.pin(folder / "failure.json") if primary else None
    lease = Lease(close_error)
    started = time.monotonic()
    success = helper.finalize(frozen, folder, result, dict(dispatches=0, denied=[]), journal,
        lease, started + 30, started, "0" * 64)
    seal = json.loads((folder / "terminal-seal.json").read_bytes())
    cleanup = json.loads((folder / "post-lease-cleanup.json").read_bytes())
    assert_true(lease.attempts == 1 and cleanup["close_attempted"], "Cleanup did not run exactly once")
    for relative, proof in seal["outputs"].items():
        actual = frozen.pin(folder / relative)
        assert_true({key: actual[key] for key in ("bytes", "sha256")} == proof, "Sealed file hash differs")
    if primary and close_error:
        late = json.loads((folder / "late-failure.json").read_bytes())
        assert_true(not success and seal["status"] == "failed", "Late cleanup falsely qualified")
        assert_true(frozen.pin(folder / "failure.json") == before, "Original primary overwritten")
        assert_true(cleanup["close_returned"] is False and cleanup["close_error"]["error_class"] == "OSError",
                    "Late close evidence missing")
        assert_true(late["prior_primary_failure"] == before and
                    any(row["phase"] == "context_manager_cleanup" for row in late["failures"]),
                    "Both primary and late error were not retained")
    else:
        assert_true(success and seal["status"] == helper.STATUS and cleanup["close_returned"], "Ordinary seal failed")
        universe = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
        assert_true(set(seal["outputs"]) == universe - {"terminal-seal.json"} and seal["complete_output_universe"],
                    "Post-cleanup complete universe not bound")

failure = None
try:
    check("ordinary_success_sealed_after_context_manager_return", lambda: finalization_case("ordinary"))
    check("primary_and_late_close_errors_both_retained_and_veto", lambda: finalization_case("late", True, True))
    real_sha = helper.sha
    def wrong_source():
        try:
            helper.sha = lambda path: "f" * 64 if Path(path) == helper.SOURCE else real_sha(path)
            rejects(helper.source_checks)
            assert_true(not dispatches, "Wrong source reached dispatch")
        finally:
            helper.sha = real_sha
    check("wrong_source_fails_before_any_dispatch", wrong_source)
    ordinary = {"KERNEL32.dll": ["CreateProcessW", "TerminateProcess"], "bcrypt.dll": ["BCryptHashData"]}
    check("selected_worker_imports_accepted", lambda: helper.pe_policy(ordinary, {}))
    check("nonprocess_CRT_execute_onexit_table_accepted", lambda: helper.pe_policy(
        {**ordinary, "api-ms-win-crt-runtime-l1-1-0.dll": ["_execute_onexit_table"]}, {}))
    for forbidden in ("CreateProcessA", "ShellExecuteW", "WinExec", "_wspawnve", "system", "_execve", "_wexeclp"):
        check("forbid_" + forbidden, lambda name=forbidden: rejects(lambda:
            helper.pe_policy({"KERNEL32.dll": ["CreateProcessW", "TerminateProcess", name]}, {})))
    check("target_dll_forbidden", lambda: rejects(lambda: helper.pe_policy({**ordinary, "llama.dll": []}, {})))
    check("network_dll_forbidden", lambda: rejects(lambda: helper.pe_policy({**ordinary, "ws2_32.dll": []}, {})))
    check("delayed_import_forbidden", lambda: rejects(lambda: helper.pe_policy(ordinary, {"bcrypt.dll": []})))
    steps = helper.commands(frozen, output / "prepared", output / "built")
    check("two_tools_separate_compile_link_MD_only", lambda: assert_true(
        [step["stage"] for step in steps] == ["compile", "link"] and "/MD" in steps[0]["argv"]
        and "/MT" not in steps[0]["argv"] and "/c" in steps[0]["argv"]
        and [step["seconds"] for step in steps] == [45, 10], "Command contract changed"))
except BaseException as error:
    failure = dict(error_class=type(error).__name__, error=str(error))
artifacts = {p.relative_to(output).as_posix(): frozen.pin(p) for p in output.rglob("*") if p.is_file()}
result = dict(schema_version=1, status="failed" if failure else "passed", helper_sha256=helper.sha(HELPER),
    checker_sha256=helper.sha(__file__), source_sha256=helper.sha(helper.SOURCE), frozen_helper_sha256=helper.sha(helper.BASIS),
    checks=checks, passed=len(checks), failure=failure, output=str(output), artifacts=artifacts,
    actual_children=0, actual_compiler_dispatches=0, attempted_forbidden_events=dispatches,
    scientific_validation="not_established", fixture_scope="Synthetic control flow only; no toolchain/worker/Job execution")
frozen.write_new(REPORT, result)
print(json.dumps(dict(status=result["status"], passed=len(checks), failure=failure, output=str(output))))
raise SystemExit(1 if failure or dispatches else 0)
