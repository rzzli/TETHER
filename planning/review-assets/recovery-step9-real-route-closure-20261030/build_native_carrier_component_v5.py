"""Trusted build-only helper. Requires a separately reviewed exact Root binding.

Never executes the generated image. Does not import the subject or enumerate
original resources. This is not the production same-Core/native/file adapter.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
BINDING = BASE / "NATIVE-CARRIER-COMPONENT-BUILD-BINDING-v1.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(pin):
    path = Path(pin["path"])
    if not path.is_absolute():
        path = ROOT / path
    raw = path.read_bytes()
    if len(raw) != pin["bytes"] or digest(raw) != pin["sha256"]:
        raise ValueError("Pinned build input differs: " + str(path))
    return path.resolve(), raw


def main():
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    if binding.get("status") != "ROOT_BOUND_BUILD_ONLY":
        raise ValueError("No build-only authority")
    if binding.get("budget_seconds") != 60:
        raise ValueError("Expected the separately declared 60-second build budget")
    checked = {}
    for name, pin in binding["inputs"].items():
        checked[name] = verify(pin)
    if checked["driver"][0] != Path(__file__).resolve():
        raise ValueError("Binding does not name this exact driver")
    out = (ROOT / binding["output_relative"]).resolve()
    allowed_parent = (ROOT / "data/cache").resolve()
    if out.parent != allowed_parent or not out.name.startswith("r09-native-carrier-component-build-"):
        raise ValueError("Unapproved build output path")
    out.mkdir(exist_ok=False)
    start = time.monotonic()
    previous = "0" * 64
    events = []
    results = []
    secondary_errors = []
    primary_dispatch_error = None

    def emit(kind, **fields):
        nonlocal previous
        row = dict(sequence=len(events), previous_sha256=previous,
                   elapsed_seconds=time.monotonic() - start, kind=kind, **fields)
        raw = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        previous = digest(raw)
        with (out / "build-journal.jsonl").open("ab") as stream:
            stream.write(raw + b"\n")
        events.append(row)

    def run(label, argv):
        nonlocal primary_dispatch_error
        remaining = 60 - (time.monotonic() - start)
        if remaining <= 2:
            raise TimeoutError("Build work deadline before " + label)
        emit("dispatch_reserved", label=label, argv=argv)
        if 60 - (time.monotonic() - start) <= 2:
            raise TimeoutError("Build work deadline before process creation: " + label)
        process = subprocess.Popen(argv, cwd=out, env=environment,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=False)
        error = None
        cleanup_errors = []
        first_stdout = first_stderr = None
        stdout = stderr = None
        output_complete = False
        kill_attempted = kill_acknowledged = False
        try:
            # Reserve bounded cleanup time INSIDE the unchanged60-second cap.
            work_remaining = 60 - (time.monotonic() - start) - 2
            if work_remaining <= 0:
                raise TimeoutError("Build work deadline after process creation: " + label)
            stdout, stderr = process.communicate(timeout=work_remaining)
            output_complete = True
        except BaseException as caught:
            error = caught
            primary_dispatch_error = dict(type=type(caught).__name__, message=str(caught))
            first_stdout = getattr(caught, "output", None)
            first_stderr = getattr(caught, "stderr", None)
            stdout, stderr = first_stdout, first_stderr
            try:
                if process.poll() is None:
                    kill_attempted = True
                    process.kill()
                    kill_acknowledged = True
            except BaseException as cleanup_error:
                cleanup_errors.append(dict(stage="kill", type=type(cleanup_error).__name__,
                                           message=str(cleanup_error)))
            cleanup_remaining = min(2.0, max(0.0, 60 - (time.monotonic() - start)))
            if cleanup_remaining > 0:
                try:
                    stdout, stderr = process.communicate(timeout=cleanup_remaining)
                    output_complete = True
                except BaseException as cleanup_error:
                    cleanup_errors.append(dict(stage="bounded_reap", type=type(cleanup_error).__name__,
                                               message=str(cleanup_error)))
                    newer_stdout = getattr(cleanup_error, "output", None)
                    newer_stderr = getattr(cleanup_error, "stderr", None)
                    if newer_stdout is not None:
                        stdout = newer_stdout
                    if newer_stderr is not None:
                        stderr = newer_stderr
            else:
                cleanup_errors.append(dict(stage="bounded_reap", type="NOT_ATTEMPTED_DEADLINE",
                                           message="No cleanup time remains; exit/pipe completeness may be unknown"))
        for suffix, value in (("first-error.stdout", first_stdout), ("first-error.stderr", first_stderr)):
            if value is not None:
                (out / (label + "." + suffix)).write_bytes(value)
        # Keep each first-visible prefix even if a later cleanup disagrees.
        for channel, first, latest in (("stdout", first_stdout, stdout), ("stderr", first_stderr, stderr)):
            if first is not None and latest is not None and not latest.startswith(first):
                cleanup_errors.append(dict(stage="output_reconciliation", type="PREFIX_MISMATCH", channel=channel))
                output_complete = False
        (out / (label + ".stdout")).write_bytes(stdout if stdout is not None else b"")
        (out / (label + ".stderr")).write_bytes(stderr if stderr is not None else b"")
        row = dict(label=label, argv=argv, pid=process.pid,
                   returncode=process.returncode,
                   stdout_bytes=len(stdout) if stdout is not None else None,
                   stderr_bytes=len(stderr) if stderr is not None else None,
                   output_complete=output_complete,
                   primary_error=primary_dispatch_error if error else None,
                   cleanup_errors=cleanup_errors, kill_attempted=kill_attempted,
                   kill_acknowledged=kill_acknowledged,
                   main_exit_observed=process.returncode is not None)
        results.append(row)
        emit("dispatch_returned_or_failed", **row)
        if error:
            raise error  # The original error survives kill/reap failures.
        if process.returncode != 0:
            raise RuntimeError(label + " returned " + str(process.returncode))

    terminal = "BUILD_FAILED"
    failure = None
    try:
        emit("build_reserved", binding_sha256=digest(BINDING.read_bytes()),
             source_imports=0, executable_dispatches=0)
        probe = json.loads(checked["toolchain_probe"][1])
        scoped = json.loads(checked["build_environment"][1])
        compiler = str(checked["compiler"][0])
        linker = str(checked["linker"][0])
        if compiler != probe["compiler"] or linker != probe["linker"]:
            raise ValueError("Compiler/linker differ from the accepted toolchain probe")
        environment = {key: os.environ[key] for key in
                       ("SystemRoot", "WINDIR", "TEMP", "TMP") if key in os.environ}
        for key in ("INCLUDE", "LIB", "LIBPATH"):
            environment[key] = scoped[key]
        system_root = environment.get("SystemRoot", r"C:\Windows")
        environment["PATH"] = str(Path(compiler).parent) + os.pathsep + str(Path(system_root) / "System32")
        header_dir = str(checked["header"][0].parent)
        common = [compiler, "/nologo", "/c", "/TC", "/std:c11", "/O2", "/Ob0", "/Oi",
                  "/MT", "/W4", "/WX", "/GL-", "/D_WIN32_WINNT=0x0A00", "/I" + header_dir]
        run("compile-carrier", common + ["/GS-", "/FAcs", "/Fa" + str(out / "carrier.asm"),
            "/Fo" + str(out / "carrier.obj"), str(checked["source"][0])])
        run("compile-tests", common + ["/GS", "/Fo" + str(out / "tests.obj"),
            str(checked["tests"][0])])
        run("link-tests", [linker, "/NOLOGO", "/MACHINE:X64", "/INCREMENTAL:NO",
            "/SUBSYSTEM:CONSOLE", "/OUT:" + str(out / "native-carrier-fake-tests.exe"),
            str(out / "carrier.obj"), str(out / "tests.obj"), "kernel32.lib"])
        if time.monotonic() - start >= 60:
            raise TimeoutError("Final build deadline")
        terminal = "BUILT_NOT_EXECUTED"
        emit("build_commands_prepared_no_execution")
    except BaseException as caught:
        terminal = "BUILD_FAILED"
        failure = dict(type=type(caught).__name__, message=str(caught), original_dispatch_error=primary_dispatch_error)
        try:
            emit("build_failure", error=failure)
        except BaseException as journal_error:
            failure["journal_error"] = type(journal_error).__name__
    artifacts = []
    inventory_complete = False
    try:
        for path in sorted(out.iterdir()):
            if path.is_file():
                raw = path.read_bytes()
                artifacts.append(dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=digest(raw)))
        inventory_complete = True
    except BaseException as inventory_error:
        terminal = "BUILD_FAILED"
        observed = dict(stage="artifact_inventory", type=type(inventory_error).__name__, message=str(inventory_error))
        secondary_errors.append(observed)
        if failure is None:
            failure = dict(type=type(inventory_error).__name__, message=str(inventory_error), original_dispatch_error=primary_dispatch_error)
        try:
            emit("build_failure", stage="artifact_inventory", error=observed)
            journal_raw = (out / "build-journal.jsonl").read_bytes()
            for artifact in artifacts:
                if artifact["path"] == str((out / "build-journal.jsonl").relative_to(ROOT)):
                    artifact.update(bytes=len(journal_raw), sha256=digest(journal_raw))
        except BaseException as inventory_journal_error:
            secondary_errors.append(dict(stage="inventory_failure_journal", type=type(inventory_journal_error).__name__))
    eligibility_elapsed = time.monotonic() - start
    if terminal == "BUILT_NOT_EXECUTED" and eligibility_elapsed >= 60:
        terminal = "BUILD_FAILED"
        failure = dict(type="TimeoutError", message="Final build deadline after artifact inventory",
                       original_dispatch_error=primary_dispatch_error)
        try:
            emit("build_failure", error=failure)
            journal_raw = (out / "build-journal.jsonl").read_bytes()
            for artifact in artifacts:
                if artifact["path"] == str((out / "build-journal.jsonl").relative_to(ROOT)):
                    artifact.update(bytes=len(journal_raw), sha256=digest(journal_raw))
        except BaseException as journal_error:
            failure["journal_error"] = type(journal_error).__name__
    report = dict(schema_version=1, status=terminal, elapsed_seconds=eligibility_elapsed,
                  binding_sha256=digest(BINDING.read_bytes()), events=len(events),
                  journal_final_hash=previous, commands=results, artifacts=artifacts,
                  failure=failure, secondary_errors=secondary_errors, artifact_inventory_complete=inventory_complete,
                  executable_dispatches=0, original_payload_reads=0,
                  qualification="Build only; no ABI execution, same-Core binding, file lifetime, physical profile or resource fit",
                  process_scope="Known main process cleanup attempted within remaining cap; original and cleanup failures separate, incomplete pipes/exit explicit; no OS-wide descendant attestation",
                  clock_scope="The60-second timer starts after input pin checks/reservation and ends at post-inventory eligibility; final report construction/write and any failure-only diagnostic tail are excluded. No new command follows the veto.",
                  persistence_scope="Ordinary harness writes, not flush/crash durability; final report construction/write and failure-only diagnostic tail outside measured elapsed")
    try:
        (out / "build-result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except BaseException as report_error:
        reporting_failure = dict(type=type(report_error).__name__, message=str(report_error))
        try:
            emit("build_report_write_failure", status="BUILD_FAILED", error=reporting_failure)
        except BaseException as report_journal_error:
            reporting_failure["journal_error"] = type(report_journal_error).__name__
        print(json.dumps(dict(status="BUILD_FAILED", result=None, failure=failure, reporting_failure=reporting_failure)))
        return 1
    print(json.dumps(dict(status=terminal, result=str(out / "build-result.json"), failure=failure)))
    return 0 if terminal == "BUILT_NOT_EXECUTED" else 1


if __name__ == "__main__":
    sys.exit(main())
