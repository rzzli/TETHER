"""PREPARED ONLY: pin a post-copy protocol, then separately authorize one child.

Run with the accepted dependency-free installed0.3.10 Python and -I.
--prepare creates data-only protocol; --execute SHA consumes its one attempt.
No engine import, target DLL/model or corpus validation occurs in preparation.
"""
from contextlib import ExitStack
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
import time

from asof.journal import RunJournal, read_chain
from asof.serde import canonical, encode
from asof.study.stable_read import deadline_check, hash_file, stable_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD_PROTOCOL = HERE.parent / "recovery-step9-native-grammar-20261028/FINITE-CONVERTER-EXECUTION-PROTOCOL-v3.json"
OLD_PROTOCOL_SHA256 = "a4f09687d19bc2803a4b419c6c707044d6f0097515a0f5778770563f0f267ce0"
QUALIFICATION = HERE / "CACHED-REFERENCE-QUALIFICATION.json"
QUALIFICATION_SHA256 = "401047cbf5b240867192a0d8acc1324b98ecb68837b6f4fca8f6b87dcb513ea4"
CHILD = HERE / "run_cached_reference_batch.py"
ENV_ROOT = ROOT / "data/cache/r09-jsonschema-reference-environment-20261028"
ENV_RECEIPT = ENV_ROOT / "ENVIRONMENT-RECEIPT.json"
PROTOCOL = HERE / "REFERENCE-BATCH-EXECUTION-PROTOCOL.json"
OUTPUT = ROOT / "data/cache/r09-jsonschema-reference-parent-20261028"
CHILD_OUTPUT = ROOT / "data/cache/r09-jsonschema-reference-batch-20261028"
DATA = ROOT / "data/cache/r09-generation-corpus-extension-v1-20261028"
SEEDS = {
    DATA / "FROZEN-INPUTS.json": "1b80e365e42b28fe237c22fc35e215d1a0410729203a77255fc628309a9da414",
    DATA / "FUTURE-NATIVE-CORPUS-MANIFEST.json": "43aa4b18d3d9c7393198d0eaa93095999d1ef54f0d2757ffe6265c7d95a26e4a",
    DATA / "COMPARISON-RESULTS.json": "95c2c30fa8ef69dca5122e22ce32fe3b636e812d3a8f8f05c685b366e323316a",
    ROOT / "data/cache/r09-native-grammar-corpus-20261028/cases.json": "01286d35689c7005ea67fa817c4b4098cecd05c4233c3949e7ec744bc5f5d97a",
}
LIMITS = dict(max_children=1, parent_seconds=120, child_deadline_seconds=100,
              child_process_seconds=110, max_stdout_bytes=1048576, max_stderr_bytes=1048576)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(path):
    path = Path(path).absolute()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def write_new(path, payload):
    with Path(path).open("xb") as stream:
        stream.write(canonical(payload) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def installed_parent():
    require(sys.flags.isolated and metadata.version("asof-target-agents") == "0.3.10", "Use accepted isolated installed0.3.10 parent")
    require(sha(OLD_PROTOCOL) == OLD_PROTOCOL_SHA256 and sha(QUALIFICATION) == QUALIFICATION_SHA256, "Prior protocol/qualification changed")
    accepted = json.loads(OLD_PROTOCOL.read_bytes())["accepted_software"]
    require(os.path.normcase(str(Path(sys.executable).resolve())) == os.path.normcase(str(Path(accepted["installed_python"]).resolve())), "Wrong installed parent executable")
    return accepted


def prepare():
    accepted = installed_parent()
    require(not PROTOCOL.exists() and not OUTPUT.exists() and not CHILD_OUTPUT.exists(), "Existing protocol/attempt; no replacement or restart")
    receipt = json.loads(ENV_RECEIPT.read_bytes())
    require(receipt["status"] == "offline_reference_environment_materialized_not_import_qualified"
            and receipt["source_qualification_sha256"] == QUALIFICATION_SHA256
            and receipt["copied_files"] == 139 and receipt["copied_bytes"] == 1640116, "Unqualified environment copy")
    files = [pin(__file__), pin(CHILD), pin(ENV_RECEIPT), pin(QUALIFICATION), pin(OLD_PROTOCOL), pin(sys.executable),
             pin(receipt["python"]), pin(Path(receipt["environment"]) / "pyvenv.cfg")]
    files.extend(accepted["installed_files"])
    files.extend([accepted["wheel"], accepted["acceptance"]])
    for package in receipt["selected"]:
        for relative, item in package["files"].items():
            path = Path(receipt["environment"]) / "Lib/site-packages" / relative
            require(path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], "Installed package file changed")
            files.append(dict(path=str(path), **item))
    for path, expected in SEEDS.items():
        require(sha(path) == expected, "Corpus seed changed")
        files.append(pin(path))
    future = json.loads((DATA / "FUTURE-NATIVE-CORPUS-MANIFEST.json").read_bytes())
    for variant in future["variants"].values():
        item = variant["schema.json"]
        require(sha(ROOT / item["path"]) == item["sha256"], "Schema changed")
        files.append(pin(ROOT / item["path"]))
    for case in future["cases"]:
        if case["document_path"] is not None:
            require(sha(ROOT / case["document_path"]) == case["document_sha256"], "Extension document changed")
            files.append(pin(ROOT / case["document_path"]))
    by_path = {os.path.normcase(item["path"]): item for item in files}
    files = list(by_path.values())
    require(len(files) <= 400 and sum(item["bytes"] for item in files) <= 32 * 1024 * 1024, "Protocol inventory cap exceeded")
    deadline = time.monotonic() + 30
    with stable_files([Path(item["path"]) for item in files], deadline=deadline):
        for item in files:
            require(encode(hash_file(item["path"], deadline)) == {key: item[key] for key in ("sha256", "bytes")}, "Preparation pin changed")
        protocol = dict(schema_version=1, kind="once_only_cached_jsonschema_reference_v1", execution_authorized=False,
            parent=pin(__file__), child=pin(CHILD), accepted_parent_software=accepted,
            environment_receipt=pin(ENV_RECEIPT), input_and_code_files=files, limits=LIMITS,
            argv=[receipt["python"], "-I", "-B", str(CHILD), sha(ENV_RECEIPT)], cwd=str(ROOT),
            output=str(OUTPUT), child_output=str(CHILD_OUTPUT), original_cases=109, extension_cases=58,
            typed_schema_expectations=162, independent_parse_edge_cases=5, unicode_controls=16,
            scope="offline reference-tool validation only; no native target/tokenizer/model/scientific evaluation",
            child_imports_before_batch=0, restart_allowed=False)
        write_new(PROTOCOL, protocol)
    print(json.dumps(dict(status="prepared_no_dispatch", protocol=str(PROTOCOL), sha256=sha(PROTOCOL), pinned_files=len(files))))


def execute(expected):
    installed_parent()
    require(sha(PROTOCOL) == expected, "Protocol external expected hash mismatch")
    protocol = json.loads(PROTOCOL.read_bytes())
    require(protocol["kind"] == "once_only_cached_jsonschema_reference_v1" and protocol["limits"] == LIMITS,
            "Wrong protocol/limits")
    require(protocol["parent"]["sha256"] == sha(__file__) and protocol["child"]["sha256"] == sha(CHILD), "Helper changed")
    require(protocol["argv"] == [str(ENV_ROOT / "environment/Scripts/python.exe"), "-I", "-B", str(CHILD),
                                protocol["environment_receipt"]["sha256"]]
            and protocol["cwd"] == str(ROOT), "Only the exact reference-environment child may run")
    require(protocol["output"] == str(OUTPUT) and protocol["child_output"] == str(CHILD_OUTPUT)
            and not OUTPUT.exists() and not CHILD_OUTPUT.exists(), "Attempt consumed or output changed")
    journal = RunJournal(OUTPUT, kind="build")
    started = time.monotonic()
    deadline = started + LIMITS["parent_seconds"]
    record = dict(schema_version=1, status="failed_or_incomplete", protocol_sha256=expected,
                  argv=protocol["argv"], cwd=protocol["cwd"], pid=None, spawn_succeeded=False,
                  actual_children=0, reaped=False, timed_out=False, capture_overflow=False, streams={},
                  cleanup_errors=[], native_target_calls=0, model_calls=0, restart_allowed=False)
    process = None
    threads = []
    stop = Event()
    captures = ExitStack()
    try:
        write_new(OUTPUT / "effective-protocol.json", protocol)
        journal.append("reference_attempt_reserved", protocol_sha256=expected, limits=LIMITS,
                       environment_receipt_sha256=protocol["environment_receipt"]["sha256"])
        pinned = protocol["input_and_code_files"] + [pin(PROTOCOL)]
        with stable_files([Path(item["path"]) for item in pinned], deadline=deadline):
            for item in pinned:
                require(encode(hash_file(item["path"], deadline)) == {key: item[key] for key in ("sha256", "bytes")}, "Execution pin changed")
            sinks = {name: captures.enter_context((OUTPUT / (name + ".bin")).open("xb"))
                     for name in ("stdout", "stderr")}
            def drain(name, pipe):
                state = record["streams"][name]
                try:
                    while True:
                        data = pipe.read(65536)
                        if not data:
                            break
                        state["observed_bytes_at_least"] += len(data)
                        remaining = LIMITS["max_" + name + "_bytes"] - state["retained_bytes"]
                        if remaining:
                            sinks[name].write(data[:remaining])
                            state["retained_bytes"] += min(len(data), remaining)
                        if len(data) > remaining:
                            state["truncated"] = True
                            stop.set()
                            break
                except BaseException as error:
                    state["error_class"] = type(error).__name__
                    stop.set()
                finally:
                    try:
                        sinks[name].flush()
                        os.fsync(sinks[name].fileno())
                    except BaseException as error:
                        state["error_class"] = type(error).__name__
                        stop.set()
            journal.append("reference_dispatch_intent", argv=protocol["argv"], cwd=protocol["cwd"])
            system = Path(os.environ["SystemRoot"])
            environment = dict(SystemRoot=str(system), WINDIR=str(system), SystemDrive=system.drive,
                               PATH=str(system / "System32"), TEMP=str(OUTPUT), TMP=str(OUTPUT))
            process = subprocess.Popen(protocol["argv"], cwd=protocol["cwd"], env=environment,
                shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
            record.update(pid=process.pid, spawn_succeeded=True, actual_children=1)
            process.stdin.close()  # Owned EOF pipe: no NUL device or path exception.
            journal.append("reference_child_started", pid=process.pid)
            child_end = min(time.monotonic() + LIMITS["child_process_seconds"], deadline - 8)
            for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
                record["streams"][name] = dict(retained_bytes=0, observed_bytes_at_least=0, truncated=False, error_class=None)
                thread = Thread(target=drain, args=(name, pipe), daemon=True)
                thread.start()
                threads.append(thread)
            while process.poll() is None:
                if stop.is_set() or time.monotonic() >= child_end:
                    record["timed_out"] = time.monotonic() >= child_end
                    process.kill()
                    break
                time.sleep(0.02)
            process.wait(timeout=max(0.1, min(3, deadline - time.monotonic())))
            record["reaped"] = True
            for thread in threads:
                thread.join(timeout=max(0.1, min(3, deadline - time.monotonic())))
            require(not any(thread.is_alive() for thread in threads), "Capture thread unresolved")
            record["capture_overflow"] = any(state["truncated"] for state in record["streams"].values())
            record["exit_code"] = process.returncode
            require(not record["timed_out"] and not record["capture_overflow"]
                    and not any(state["error_class"] for state in record["streams"].values()), "Child/capture deadline failure")
            require(process.returncode == 0, "Reference batch failed; retain child result")
            captures.close()
            require((OUTPUT / "stderr.bin").stat().st_size == 0, "Reference tool reported stderr diagnostics")
            deadline_check(deadline)
            require((CHILD_OUTPUT / "REFERENCE-BATCH-RESULT.json").stat().st_size <= 4 * 1024 * 1024, "Child result cap exceeded")
            child_result = json.loads((CHILD_OUTPUT / "REFERENCE-BATCH-RESULT.json").read_bytes())
            require(child_result["status"] == "passed_reference_schema_expectations"
                    and child_result["typed_schema_cases"] == 162 and child_result["explicit_parse_edge_cases"] == 5
                    and child_result["unicode_controls"] == 16 and not child_result["guard_attempts"], "Child qualification incomplete")
            for item in pinned:
                deadline_check(deadline)
                require(encode(hash_file(item["path"], deadline)) == {key: item[key] for key in ("sha256", "bytes")}, "Final input/code pin changed")
            journal.append("reference_batch_qualified", child_result=pin(CHILD_OUTPUT / "REFERENCE-BATCH-RESULT.json"))
            record.update(status="passed_reference_batch_once", child_result=pin(CHILD_OUTPUT / "REFERENCE-BATCH-RESULT.json"))
    except BaseException as error:
        record.update(status="failed_no_automatic_retry", error_class=type(error).__name__, message=str(error))
        journal.fail(error, "reference_batch")
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=max(0.1, min(3, deadline - time.monotonic())))
                record.update(reaped=True, exit_code=process.poll())
            except BaseException as error:
                record["cleanup_errors"].append(type(error).__name__)
            for thread in threads:
                thread.join(timeout=max(0.1, min(2, deadline - time.monotonic())))
            if any(thread.is_alive() for thread in threads):
                record["cleanup_errors"].append("CaptureThreadUnresolved")
            for pipe in (process.stdout, process.stderr):
                if pipe is not None and not any(thread.is_alive() for thread in threads):
                    pipe.close()
        try:
            captures.close()
        except BaseException as error:
            record["cleanup_errors"].append(type(error).__name__)
        record["elapsed_seconds_before_sealing"] = time.monotonic() - started
        if record["cleanup_errors"] or time.monotonic() >= deadline:
            record["status"] = "failed_cleanup_or_global_deadline"
        try:
            try:
                journal.append("reference_attempt_terminal", **record)
            finally:
                journal.close()
            if record["status"] != "passed_reference_batch_once":
                write_new(OUTPUT / "failure.json", dict(authoritative=True, **record))
            write_new(OUTPUT / "parent-attempt.json", record)
            read_chain(OUTPUT / "journal.jsonl")
            if time.monotonic() >= deadline and not (OUTPUT / "failure.json").exists():
                write_new(OUTPUT / "failure.json", dict(authoritative=True, status="failed_postseal_global_deadline", restart_allowed=False))
            if not (OUTPUT / "failure.json").exists():
                deadline_check(deadline)
                inventory = {}
                for name in ("journal.jsonl", "parent-attempt.json", "stdout.bin", "stderr.bin", "effective-protocol.json"):
                    deadline_check(deadline)
                    proof = encode(hash_file(OUTPUT / name, deadline))
                    inventory[name] = dict(path=str(OUTPUT / name), **proof)
                write_new(OUTPUT / "receipt.json", dict(schema_version=1, status=record["status"], protocol_sha256=expected,
                    outputs=inventory, child_result=record["child_result"], authority_rule="failure.json overrides any receipt"))
                if time.monotonic() >= deadline:
                    write_new(OUTPUT / "failure.json", dict(authoritative=True, status="failed_postreceipt_global_deadline", restart_allowed=False))
        except BaseException as error:
            record.update(status="failed_finalization", sealing_error_class=type(error).__name__, sealing_error_message=str(error))
            if not (OUTPUT / "failure.json").exists():
                write_new(OUTPUT / "failure.json", dict(authoritative=True, status=record["status"],
                    error_class=type(error).__name__, message=str(error), elapsed_seconds=time.monotonic()-started,
                    restart_allowed=False, authority_rule="This marker overrides any earlier receipt or terminal status"))
    print(json.dumps(dict(status=record["status"], parent_output=str(OUTPUT),
        authoritative_failure=(OUTPUT / "failure.json").exists(), elapsed_seconds=time.monotonic() - started)))
    return 0 if record["status"] == "passed_reference_batch_once" and not (OUTPUT / "failure.json").exists() else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--prepare"]:
        prepare()
    elif len(sys.argv) == 3 and sys.argv[1] == "--execute":
        raise SystemExit(execute(sys.argv[2]))
    else:
        raise SystemExit("Use --prepare, then independently review protocol before --execute SHA256")
