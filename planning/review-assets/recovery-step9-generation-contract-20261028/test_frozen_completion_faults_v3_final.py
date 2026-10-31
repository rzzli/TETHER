"""Focused in-memory fault fixtures for the operator helper, not archive replays.

All journal/files/leases/processes are stdlib stubs. No actual child, model,
dataset, target DLL or original archived helper is executed. Writes one new
fixture-result JSON only after all mock contexts have ended.
"""
from contextlib import ExitStack
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
HELPER = HERE / "verify_frozen_completion_v3.py"
RESULT = HERE / "FROZEN-COMPLETION-v3-FAULT-RESULTS-final.json"
spec = importlib.util.spec_from_file_location("completion_operator_fault_fixture", HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fake_pin(path):
    return dict(path=str(path), sha256="stub", bytes=0)


def fixtures():
    originals = []
    for version in module.REUSED + list(module.VERSIONS):
        originals.append(dict(version=version, python="invented-"+version+"-python", python_sha256="stub",
            helper="invented-"+version+"-helper", helper_sha256="stub", expected_status="passed", status="passed",
            args=["invented-base" if version=="038" else "old-report", "old-output"],
            report="invented-"+version+"-report", report_sha256="stub"))
    rows = []
    for original in originals[7:]:
        version = original["version"]
        args = list(original["args"])
        if version == "038":
            report = module.OUTPUT / "038/guarded-installed-verification.json"
            args[-1] = str(report)
        else:
            report = module.OUTPUT / (version+"-report.json")
            args[0], args[1] = str(report), str(module.OUTPUT/version)
        rows.append(dict(version=version, expected_version=module.VERSIONS[version], python=original["python"],
            python_sha256="stub", helper=original["helper"], helper_sha256="stub", expected_status="passed",
            args=args, primary_args=original["args"], report=str(report), replay_timeout_seconds=360))
    primary = dict(records=originals)
    protocol = dict(kind="remaining_three_matching_installed_verifiers_v1", preparation_revision=3,
        limits=module.LIMITS, helper=dict(sha256="stub"), reused_records=originals[:7],
        reused_versions=module.REUSED, remaining_versions=list(module.VERSIONS), records=rows,
        output=str(module.OUTPUT), combined_report=str(module.COMBINED), pinned_files=[])
    return primary, protocol


def finalization_fixture(name, fault_event=None, late_lease=False):
    primary, protocol = fixtures()
    state = dict(files={}, directories=set(), lease_closed=False, journal_closed=False,
                 stub_metadata=0, stub_replays=0, fault_injected=False, now=0.0)

    def write(path, value):
        key = str(path)
        assert key not in state["files"], "Stub refused replacement"
        state["files"][key] = copy.deepcopy(value)

    class Journal:
        def __init__(self, output, **kwargs):
            state["directories"].add(str(output))
        def append(self, event, **kwargs):
            if event == fault_event and not state["fault_injected"]:
                state["fault_injected"] = True
                raise OSError("Invented transient journal write failure")
        def fail(self, error, stage):
            state["journal_failed"] = type(error).__name__
        def close(self):
            state["journal_closed"] = True

    class Lease:
        def __enter__(self):
            return None
        def __exit__(self, *args):
            state["lease_closed"] = True
            if late_lease:
                state["now"] = 1201.0

    def check_deadline(deadline):
        if state["now"] >= deadline:
            raise TimeoutError("Invented aggregate deadline exceeded")

    def read(path):
        if path == module.PROTOCOL:
            return json.dumps(protocol).encode()
        return b'{"status":"passed","guards":{},"model_calls":0}'

    def child(row, stage, argv, cap, journal, deadline):
        state["stub_metadata" if stage=="metadata" else "stub_replays"] += 1
        row[stage] = dict(stub_only=True, returncode=0, reaped=True)

    with ExitStack() as mocks:
        substitutions = dict(authorities=lambda:(primary, dict(source_pins={}), {}), sha=lambda path:"stub",
            pin=fake_pin, write_new=write, RunJournal=Journal, retained_ok=lambda *args:None,
            hash_file=lambda *args:dict(sha256="stub",bytes=0), stable_files=lambda *args,**kwargs:Lease(),
            read_chain=lambda *args:(), run_child=child, deadline_check=check_deadline)
        for key, value in substitutions.items():
            mocks.enter_context(patch.object(module, key, value))
        mocks.enter_context(patch.object(module.time, "monotonic", lambda:state["now"]))
        mocks.enter_context(patch.object(Path, "exists", lambda path:str(path) in state["files"] or str(path) in state["directories"]))
        mocks.enter_context(patch.object(Path, "read_bytes", read))
        mocks.enter_context(patch.object(module.subprocess, "Popen", side_effect=AssertionError("No actual child authorized")))
        mocks.enter_context(patch("builtins.print"))
        code = module.execute("stub")
    marker = state["files"].get(str(module.OUTPUT/"failure.json"))
    combined = str(module.COMBINED) in state["files"]
    assert code == 1 and marker and marker["authoritative"]
    assert state["lease_closed"] and state["journal_closed"]
    if late_lease:
        assert combined and marker["status"] == "failed_lease_cleanup_or_global_deadline"
    else:
        assert not combined
    if fault_event == "completion_remaining_three_verified":
        assert state["files"][str(module.REPORT)]["status"] == "failed_body_exception"
    return dict(id=name,status="passed",actual_children=0,stub_metadata_operations=state["stub_metadata"],
        stub_replay_operations=state["stub_replays"],lease_closed=state["lease_closed"],
        journal_closed=state["journal_closed"],authoritative_failure=marker["status"] if "status" in marker else True,
        combined_record_present=combined,returncode=code)


def child_deadline_fixture():
    state = dict(now=0.0, waits=0, files={}, kills=0)
    class Buffer(io.BytesIO):
        def fileno(self):
            return 42
    class Process:
        pid = 4242
        stdin, stdout, stderr = Buffer(), Buffer(), Buffer()
        def poll(self):
            return 0
        def wait(self, **kwargs):
            state["waits"] += 1
            state["now"] = 0.25 if state["waits"] == 1 else 2.0
            return 0
        def kill(self):
            state["kills"] += 1
    class SynchronousThread:
        def __init__(self, target, args, **kwargs):
            self.target, self.args = target, args
        def start(self):
            self.target(*self.args)
        def join(self, **kwargs):
            pass
        def is_alive(self):
            return False
    class Journal:
        def append(self, *args, **kwargs):
            pass
    row = dict(version="invented")
    with ExitStack() as mocks:
        mocks.enter_context(patch.object(module.time,"monotonic",lambda:state["now"]))
        mocks.enter_context(patch.object(module,"deadline_check",lambda deadline:None))
        mocks.enter_context(patch.object(module.subprocess,"Popen",lambda *args,**kwargs:Process()))
        mocks.enter_context(patch.object(module,"Thread",SynchronousThread))
        mocks.enter_context(patch.object(module.os,"fsync",lambda descriptor:None))
        mocks.enter_context(patch.object(module,"pin",fake_pin))
        mocks.enter_context(patch.object(module,"write_new",lambda path,value:state["files"].update({str(path):copy.deepcopy(value)})))
        mocks.enter_context(patch.object(Path,"open",lambda *args,**kwargs:Buffer()))
        mocks.enter_context(patch.object(Path,"exists",lambda path:True))
        try:
            module.run_child(row,"replay",["invented-no-process"],1,Journal(),100)
        except RuntimeError as error:
            assert "Whole-process deadline exceeded" in str(error)
        else:
            raise AssertionError("Post-cleanup process overrun was accepted")
    assert row["replay"]["full_process_elapsed_seconds"] == 2.0
    assert row["replay"]["effective_seconds"] == 1.0 and row["replay"]["reaped"]
    return dict(id="post_capture_child_deadline",status="passed",actual_children=0,
        process_interface="stdlib stub only",measured_stub_seconds=2.0,effective_stub_seconds=1.0,
        success_rejected=True,stub_process_reaped=True)


def main():
    assert not RESULT.exists(), "Preserve existing fixture evidence"
    results = []
    status = "failed"
    failure = None
    try:
        results.append(finalization_fixture("transient_body_journal_failure","completion_remaining_three_verified"))
        results.append(finalization_fixture("terminal_journal_failure","completion_attempt_terminal"))
        results.append(finalization_fixture("post_lease_global_deadline",late_lease=True))
        results.append(child_deadline_fixture())
        status = "passed_four_in_memory_stub_fault_fixtures"
    except BaseException as error:
        failure = dict(error_class=type(error).__name__,message=str(error))
    report = dict(schema_version=1,status=status,helper_sha256=hashlib.sha256(HELPER.read_bytes()).hexdigest(),
        fixture_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope="in_memory_operator_failure_control_flow_only_not_actual_archive_replays",actual_children=0,
        actual_metadata_checks=0,actual_replays=0,model_calls=0,native_target_calls=0,results=results,failure=failure)
    with RESULT.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2)
        stream.write("\n")
    print(json.dumps(dict(status=status,fixtures=len(results),actual_children=0,failure=failure)))
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
