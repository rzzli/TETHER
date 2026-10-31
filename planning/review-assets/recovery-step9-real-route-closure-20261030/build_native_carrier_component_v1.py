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
        remaining = 60 - (time.monotonic() - start)
        if remaining <= 0:
            raise TimeoutError("Build deadline before " + label)
        emit("dispatch_reserved", label=label, argv=argv)
        process = subprocess.Popen(argv, cwd=out, env=environment,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=False)
        error = None
        try:
            stdout, stderr = process.communicate(timeout=remaining)
        except BaseException as caught:
            error = caught
            process.kill()
            stdout, stderr = process.communicate()
        (out / (label + ".stdout")).write_bytes(stdout)
        (out / (label + ".stderr")).write_bytes(stderr)
        row = dict(label=label, argv=argv, pid=process.pid,
                   returncode=process.returncode, stdout_bytes=len(stdout),
                   stderr_bytes=len(stderr), error_type=type(error).__name__ if error else None,
                   reaped_main_process=process.returncode is not None)
        results.append(row)
        emit("dispatch_returned_or_failed", **row)
        if error:
            raise error
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
        emit("build_complete_no_execution")
    except BaseException as caught:
        failure = dict(type=type(caught).__name__, message=str(caught))
        try:
            emit("build_failure", error=failure)
        except BaseException as journal_error:
            failure["journal_error"] = type(journal_error).__name__
    artifacts = []
    for path in sorted(out.iterdir()):
        if path.is_file():
            raw = path.read_bytes()
            artifacts.append(dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=digest(raw)))
    report = dict(schema_version=1, status=terminal, elapsed_seconds=time.monotonic() - start,
                  binding_sha256=digest(BINDING.read_bytes()), events=len(events),
                  journal_final_hash=previous, commands=results, artifacts=artifacts,
                  failure=failure, executable_dispatches=0, original_payload_reads=0,
                  qualification="Build only; no ABI execution, same-Core binding, file lifetime, physical profile or resource fit",
                  process_scope="Known subprocesses killed/reaped on failure; no OS-wide descendant attestation",
                  clock_scope="The60-second timer starts after input pin checks and exclusive output reservation; interpreter startup/preflight and final report write are excluded",
                  persistence_scope="Ordinary harness writes, not flush/crash durability; report write outside measured elapsed")
    (out / "build-result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status=terminal, result=str(out / "build-result.json"), failure=failure)))
    return 0 if terminal == "BUILT_NOT_EXECUTED" else 1


if __name__ == "__main__":
    sys.exit(main())
