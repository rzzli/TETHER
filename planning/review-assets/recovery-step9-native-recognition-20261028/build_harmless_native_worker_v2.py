"""Prepare/build the own harmless worker only; never execute its result.

The frozen bridge helper supplies unmodified tool/audit/PE/environment functions.
No Windows Job, target DLL, model, downloaded code or compiled result is invoked.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASIS = HERE / "build_public_c_bridge.py"
BASIS_SHA = "733a47bb8c047e129560c0c68dd63d97cf09c95c23b3cabd105df7791927c09c"
OLD_PROTOCOL = HERE / "BUILD-PROTOCOL.json"
OLD_PROTOCOL_SHA = "5c6086e48ca9fb3b3f1f61a2eea780e64f1392bbdc819216e37b09935acc345e"
SOURCE = HERE / "harmless_launch_worker_native_v2.cpp"
SOURCE_SHA = "c22e5b781a2beb1fb82c70382b036b608582dad19f60b36540f1bc51832d1f60"
DESIGN = HERE / "HARMLESS-NATIVE-WORKER-DESIGN-v2.md"
DESIGN_SHA = "ba0f6940a4e0fed57501d94fb5bf8253c4e86b95721a2e4e6e747b9f5d4f5d88"
PRESERVED = {
    HERE / "harmless_launch_worker_native_v1.cpp": "d9bd78c7fdd2c9fc7d70ade21fa06d76b5d5c25251f06f68ff9b03734d254f25",
    HERE / "HARMLESS-NATIVE-WORKER-DESIGN-v1.md": "377c29e0144fa3be989db2c78719513f4694f41763131180b4b8e3eb1aeda3f4"}
SOURCE_REVIEWS = {
    HERE / "HARMLESS-NATIVE-WORKER-SOURCE-PEER-v1.json": "4484919b60800cc9df2c1269a98e244e6ff780aae9d6bad99120e45418e4b9c7",
    HERE / "HARMLESS-NATIVE-WORKER-SOURCE-PEER-v1.md": "af3ddf4929b9eb06b63d4d8b7c3db67ed3eac7b96fc5d739c5ad6a92f7aef088",
    HERE / "HARMLESS-NATIVE-WORKER-SOURCE-PEER-v2.json": "bc9c8740c05ca0af16bb4b20841878d908a6d233cd6ecf39cdc79a4ebd694763",
    HERE / "HARMLESS-NATIVE-WORKER-SOURCE-PEER-v2.md": "3d23a594412815cc7fbf06e5e3c6ddfd9e62be9d1a68e8c5fff7f34b1c1f25d5"}
PRESERVED_BUILD_V1 = {
    HERE / "build_harmless_native_worker_v1.py": "fb096d3d33adf6eba89d416eb4a6bf2a6b427bdd3ea47f492edd571e76708459",
    HERE / "HARMLESS-NATIVE-BUILD-PROTOCOL-v1.json": "73b8bfcff0b7d49e7510d46403886640148942e59292fa8eec22f278856510ac",
    HERE / "HARMLESS-NATIVE-BUILD-PREPARATION-v1.json": "621c4ea0c9f95ec393264ea847d8422bdb276691a0c8701081ae6e87089c8677",
    HERE / "check_harmless_native_build_v1.py": "92e70f48d3c873218ff2c58941974c4c29db9599362bf531fa6c9cab34af6b16",
    HERE / "HARMLESS-NATIVE-BUILD-PURE-CHECKS-v1.json": "fcb298d7c4deb5394a8334472a6515f10050830c27fc79ab6d7fe6795d05d7ee"}
PROTOCOL = HERE / "HARMLESS-NATIVE-BUILD-PROTOCOL-v2.json"
PREPARATION = HERE / "HARMLESS-NATIVE-BUILD-PREPARATION-v2.json"
PREPARATION_FAILURE = HERE / "HARMLESS-NATIVE-BUILD-PREPARATION-FAILURE-v2.json"
PURE = HERE / "HARMLESS-NATIVE-BUILD-PURE-CHECKS-v2.json"
PURE_CHECKER = HERE / "check_harmless_native_build_v2.py"
INITIAL_ENV = dict(os.environ)
LIMITS = dict(total_seconds=60, compile_seconds=45, link_seconds=10,
    finalization_reserve_seconds=5, stdout_bytes=262144, stderr_bytes=262144,
    maximum_children=2, execute_result=False)
STATUS = "own_harmless_native_worker_built_not_executed"


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def basis():
    need(sha(BASIS) == BASIS_SHA, "Frozen build helper changed")
    spec = util.spec_from_file_location("frozen_bridge_build_for_harmless_worker", BASIS)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    need(module.LIMITS == LIMITS, "Existing finite build limits changed")
    return module


def accepted(frozen):
    need(os.name == "nt" and sys.flags.isolated and sys.dont_write_bytecode,
         "Accepted isolated Windows interpreter required")
    need(metadata.version("asof-target-agents") == "0.3.11" and util.find_spec("pyarrow") is None,
         "Accepted dependency-free 0.3.11 required")
    source_checks()
    pure = json.loads(PURE.read_bytes())
    need(pure["status"] == "passed" and pure["helper_sha256"] == sha(__file__)
         and pure["checker_sha256"] == sha(PURE_CHECKER) and pure["actual_children"] == 0
         and pure["actual_compiler_dispatches"] == 0, "Focused pure checks missing or changed")
    old = json.loads(OLD_PROTOCOL.read_bytes())
    need(len(old["inputs"]) == 193 and old["accepted_software_sha256"] == frozen.ACCEPTANCE_SHA
         and old["execute_result"] is False, "Original 193-pin build basis differs")
    need(Path(sys.executable) in [Path(row["path"]) for row in old["inputs"]]
         and sha(frozen.ACCEPTANCE) == frozen.ACCEPTANCE_SHA, "Accepted environment anchor missing")
    for item in old["inputs"]:
        frozen.safe_input(item["path"])
    return old


def source_checks():
    need(sha(OLD_PROTOCOL) == OLD_PROTOCOL_SHA and sha(SOURCE) == SOURCE_SHA
         and sha(DESIGN) == DESIGN_SHA, "Frozen source/design/build basis changed")
    need(all(sha(path) == digest for path, digest in PRESERVED.items()), "Preserved version-one source changed")
    need(all(sha(path) == digest for path, digest in SOURCE_REVIEWS.items()), "Independent source review changed")
    need(all(sha(path) == digest for path, digest in PRESERVED_BUILD_V1.items()), "Preserved build version one changed")


def commands(frozen, prepared, output):
    tool = frozen.TOOLROOT / "bin/Hostx64/x64"
    return [dict(stage="compile", seconds=45, argv=[str(tool / "cl.exe"), "/nologo", "/Bv",
        "/std:c++17", "/MD", "/O2", "/DNDEBUG", "/D_ITERATOR_DEBUG_LEVEL=0", "/EHsc",
        "/Zp8", "/Gd", "/W4", "/WX", "/utf-8", "/c",
        str(prepared / "harmless_launch_worker.cpp"), "/Fo" + str(output / "worker.obj"),
        "/Fd" + str(output / "compiler.pdb")]),
        dict(stage="link", seconds=10, argv=[str(tool / "link.exe"), "/NOLOGO", "/MACHINE:X64",
        "/SUBSYSTEM:CONSOLE", "/INCREMENTAL:NO", "/MANIFEST:NO", "/DYNAMICBASE", "/NXCOMPAT",
        "/HIGHENTROPYVA", "/OUT:" + str(output / "harmless_launch_worker.exe"), str(output / "worker.obj"),
        str(frozen.SDKROOT / f"Lib/{frozen.SDKVER}/um/x64/bcrypt.lib"),
        str(frozen.SDKROOT / f"Lib/{frozen.SDKVER}/um/x64/kernel32.lib")])]


def pe_policy(ordinary, delayed):
    need(not delayed, "Unexpected delayed import")
    allowed = {"kernel32.dll", "bcrypt.dll", "msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"}
    need(all(name.casefold() in allowed or name.casefold().startswith("api-ms-win-crt-")
             for name in ordinary), "Unexpected target/network/system DLL import")
    names = {name for group in ordinary.values() for name in group}
    process = {name for name in names if name.startswith(("CreateProcess", "TerminateProcess", "ShellExecute",
               "WinExec", "_spawn", "_wspawn", "_execl", "_execv", "_wexecl", "_wexecv"))
               or name in ("system", "_wsystem")}
    need(process == {"CreateProcessW", "TerminateProcess"}, "Unexpected/missing explicit process imports")
    need(not any(any(tag in name.casefold() for tag in ("winhttp", "internetopen", "wsastartup", "shellexecute"))
                 for name in names), "Network/shell function import forbidden")


def verify_pins(frozen, records, deadline):
    for item in records:
        frozen.safe_input(item["path"])
        need(frozen.encode(frozen.hash_file(item["path"], deadline)) ==
             {key: item[key] for key in ("bytes", "sha256")}, "Pinned input changed: " + item["path"])


def finalize(frozen, output, result, state, journal, leases, deadline, started, expected):
    """Seal after unconditional context-manager cleanup; every failure vetoes."""
    errors = []
    def error_record(error, phase):
        errors.append(dict(phase=phase, error_class=type(error).__name__, error=str(error)[:2048]))
        result["status"] = "failed"
    cleanup = dict(schema_version=1, close_attempted=False, close_returned=False, close_error=None,
        scope="ExitStack.close/stable_files context-manager outcome only; no individual-handle close attestation")
    try:
        result.update(guards={key: state[key] for key in ("dispatches", "denied")},
                      elapsed_seconds_before_finalization=time.monotonic() - started)
        try:
            journal.append("own_harmless_build_terminal", status=result["status"], dispatches=state["dispatches"])
        except BaseException as error:
            error_record(error, "terminal_journal_append")
        finally:
            try:
                journal.close()
            except BaseException as error:
                error_record(error, "terminal_journal_close")
        frozen.write_new(output / "build-report.json", result)
        frozen.deadline_check(deadline)
        early = {}
        for index, path in enumerate(output.rglob("*")):
            need(index < 128, "Generated entry count cap")
            frozen.deadline_check(deadline)
            frozen.safe(path, output)
            if path.is_file():
                need(path.stat().st_size <= 128 * 1024**2, "Generated artifact cap")
                early[path.relative_to(output).as_posix()] = frozen.encode(frozen.hash_file(path, deadline))
        chain = frozen.read_chain(output / "journal.jsonl")
        frozen.write_new(output / "receipt.json", dict(schema_version=1, status=result["status"], outputs=early,
            journal_tip_sha256=chain[-1]["sha256"], protocol_sha256=expected,
            required_terminal_seal="terminal-seal.json", status_provisional_until_post_lease_seal=True,
            failure_veto="Any failure marker, failed or missing terminal seal overrides this receipt"))
    except BaseException as error:
        error_record(error, "pre_cleanup_finalization")
    finally:
        cleanup["close_attempted"] = True
        try:
            leases.close(); cleanup["close_returned"] = True
        except BaseException as error:
            cleanup["close_error"] = dict(error_class=type(error).__name__, error=str(error)[:2048])
            error_record(error, "context_manager_cleanup")
    cleanup.update(elapsed_seconds_after_cleanup=time.monotonic() - started,
                   deadline_expired=time.monotonic() > deadline)
    for field, name in (("prior_primary_failure", "failure.json"), ("prior_receipt", "receipt.json")):
        cleanup[field] = None
        try:
            if (output / name).is_file():
                cleanup[field] = frozen.pin(output / name)
        except BaseException as error:
            error_record(error, "post_cleanup_prior_anchor_" + field)
    if cleanup["deadline_expired"]:
        error_record(TimeoutError("Global deadline exceeded after context-manager cleanup"), "post_cleanup_deadline")
    cleanup["status"] = "failed" if errors else "context_manager_returned"
    try:
        frozen.write_new(output / "post-lease-cleanup.json", cleanup)
    except BaseException as error:
        error_record(error, "post_cleanup_record")
    if errors:
        try:
            frozen.write_new(output / "late-failure.json", dict(authoritative=True, automatic_retry=False,
                failures=errors, prior_primary_failure=cleanup["prior_primary_failure"], prior_receipt=cleanup["prior_receipt"]))
        except BaseException as error:
            error_record(error, "late_failure_record")
    outputs, complete = {}, True
    try:
        for index, path in enumerate(output.rglob("*")):
            need(index < 128, "Post-cleanup entry count cap")
            frozen.deadline_check(deadline)
            frozen.safe(path, output)
            if path.is_file():
                need(path.stat().st_size <= 128 * 1024**2, "Post-cleanup artifact cap")
                outputs[path.relative_to(output).as_posix()] = frozen.encode(frozen.hash_file(path, deadline))
        frozen.deadline_check(deadline)
    except BaseException as error:
        complete = False; error_record(error, "post_cleanup_inventory")
    if errors and not (output / "late-failure.json").exists():
        try:
            frozen.write_new(output / "late-failure.json", dict(authoritative=True, automatic_retry=False,
                failures=errors, prior_primary_failure=cleanup["prior_primary_failure"], prior_receipt=cleanup["prior_receipt"]))
            outputs["late-failure.json"] = {key: frozen.pin(output / "late-failure.json")[key]
                                           for key in ("bytes", "sha256")}
        except BaseException as error:
            error_record(error, "inventory_failure_record")
    markers = ("failure.json", "late-failure.json", "post-seal-failure.json")
    veto = bool(errors) or result["status"] != STATUS or any((output / name).exists() for name in markers)
    seal = dict(schema_version=1, status="failed" if veto or not complete else STATUS,
        protocol_sha256=expected, outputs=outputs, complete_output_universe=complete,
        finalization_errors=errors, elapsed_seconds_before_seal=time.monotonic() - started,
        cleanup_scope=cleanup["scope"], executable_executions=0,
        failure_veto="failure.json, late-failure.json or post-seal-failure.json overrides every earlier status")
    try:
        frozen.write_new(output / "terminal-seal.json", seal)
        frozen.deadline_check(deadline)
    except BaseException as error:
        error_record(error, "terminal_seal_or_post_seal_deadline")
        try:
            frozen.write_new(output / "post-seal-failure.json", dict(authoritative=True, automatic_retry=False,
                failures=errors, terminal_seal=frozen.pin(output / "terminal-seal.json")
                if (output / "terminal-seal.json").is_file() else None))
        except BaseException:
            pass  # Missing/failed seal and the nonzero return still prohibit acceptance.
    return not errors and seal["status"] == STATUS and complete and (output / "terminal-seal.json").is_file() \
        and not any((output / name).exists() for name in markers)


def prepare():
    need(not any(path.exists() for path in (PROTOCOL, PREPARATION, PREPARATION_FAILURE)),
         "Preparation already reserved; no retry")
    frozen = basis()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prepared = frozen.safe(ROOT / "data/cache" / ("r09-harmless-native-preparation-v2-" + stamp))
    output = frozen.safe(ROOT / "data/cache" / ("r09-harmless-native-build-v2-" + stamp))
    need(not prepared.exists() and not output.exists(), "Exclusive output exists")
    state = dict(active=None, environment=None, dispatches=0, denied=[], write_roots=[prepared],
                 write_files={PROTOCOL, PREPARATION, PREPARATION_FAILURE})
    frozen.audit(state)
    old = accepted(frozen)
    previous = json.loads((HERE / "HARMLESS-NATIVE-BUILD-PROTOCOL-v1.json").read_bytes())
    need(len(previous["inputs"]) == 206 and not Path(previous["output"]).exists(), "Prior preparation changed or was executed")
    inputs = previous["inputs"] + [frozen.pin(path) for path in
        (OLD_PROTOCOL, BASIS, SOURCE, DESIGN, __file__, PURE, PURE_CHECKER, *PRESERVED, *SOURCE_REVIEWS, *PRESERVED_BUILD_V1)]
    inputs = list({os.path.normcase(item["path"]): item for item in inputs}.values())
    deadline = time.monotonic() + 60
    try:
        with ExitStack() as leases:
            leases.enter_context(frozen.stable_files([Path(row["path"]) for row in inputs], deadline=deadline))
            verify_pins(frozen, inputs, deadline)
            prepared.mkdir()
            copied = prepared / "harmless_launch_worker.cpp"
            with copied.open("xb") as stream:
                stream.write(SOURCE.read_bytes()); stream.flush(); os.fsync(stream.fileno())
            need(sha(copied) == SOURCE_SHA, "Copied author source differs")
            inputs.append(frozen.pin(copied))
            leases.enter_context(frozen.stable_files([copied], deadline=deadline))
            verify_pins(frozen, inputs, deadline)
            environment = frozen.build_environment(old["environment"], output)
            value = dict(schema_version=1, kind="own_harmless_native_worker_build_v2", helper=frozen.pin(__file__),
                source=frozen.pin(SOURCE), source_copy=frozen.pin(copied), design=frozen.pin(DESIGN),
                frozen_build_helper=frozen.pin(BASIS), original_build_protocol=frozen.pin(OLD_PROTOCOL),
                accepted_software_sha256=frozen.ACCEPTANCE_SHA, prepared=str(prepared), output=str(output),
                commands=commands(frozen, prepared, output), environment=environment, limits=LIMITS, inputs=inputs,
                inherited_inputs=193, execute_result=False, build_authorized_by_preparation=False,
                prior_unexecuted_build_preparation=frozen.pin(HERE / "HARMLESS-NATIVE-BUILD-PREPARATION-v1.json"),
                preserved_previous_inputs=206, change="Precise exec-family classifier; _execute_onexit_table is not process execution",
                process_scope="Launched compiler/linker handles only; descendants not independently attested",
                toolchain_scope="Inherited pinned tools/direct SDK-STL leaves/libs; not a complete transitive closure",
                source_compile_scope="Own harmless source and system/CRT headers only; no fetched project implementation",
                pe_policy="No delayed imports; finite system/CRT import names; explicit process imports only CreateProcessW/TerminateProcess",
                parent_qualification="Separate future exact-role review; no ABI or harmless-launch gate cleared by build",
                activity=dict(children=0, compiles=0, links=0, result_executions=0, target_loads=0, model_reads=0, network_requests=0))
            frozen.write_new(PROTOCOL, value)
        frozen.deadline_check(deadline)
        need(state["dispatches"] == 0 and not state["denied"] and dict(os.environ) == INITIAL_ENV,
             "Preparation performed forbidden activity/environment change")
        frozen.write_new(PREPARATION, dict(schema_version=1, status="prepared_not_built_or_executed",
            protocol=frozen.pin(PROTOCOL), helper=frozen.pin(__file__), source=frozen.pin(SOURCE), design=frozen.pin(DESIGN),
            inputs=len(inputs), inherited_inputs=193, output_absent=not output.exists(), limits=LIMITS,
            activity=value["activity"], global_environment_unchanged=True))
    except BaseException as error:
        if not PREPARATION_FAILURE.exists():
            frozen.write_new(PREPARATION_FAILURE, dict(authoritative=True, automatic_retry=False,
                error_class=type(error).__name__, error=str(error)[:2048]))
        raise
    print(json.dumps(dict(status="prepared_not_built_or_executed", protocol_sha256=sha(PROTOCOL),
        helper_sha256=sha(__file__), inputs=len(inputs), prepared=str(prepared), output=str(output))))


def build(expected):
    frozen = basis()
    need(len(expected) == 64 and sha(PROTOCOL) == expected and not PREPARATION_FAILURE.exists(),
         "Exact separately reviewed protocol required")
    config = json.loads(PROTOCOL.read_bytes())
    need(config["kind"] == "own_harmless_native_worker_build_v2" and config["helper"] == frozen.pin(__file__)
         and config["source"] == frozen.pin(SOURCE) and config["design"] == frozen.pin(DESIGN)
         and config["limits"] == LIMITS and config["execute_result"] is False, "Build scope changed")
    output = frozen.safe(config["output"], ROOT / "data/cache")
    prepared = frozen.safe(config["prepared"], ROOT / "data/cache")
    need(not output.exists(), "Build already reserved; no restart")
    started = time.monotonic(); deadline = started + 60
    journal = frozen.RunJournal(output, kind="build")
    state = dict(active=None, environment=config["environment"], dispatches=0, denied=[], write_roots=[output], write_files=set())
    frozen.audit(state, output)
    leases = ExitStack(); failure = None; sealed = False
    result = dict(schema_version=1, status="failed", protocol_sha256=expected, commands=[],
        executable_executions=0, target_dll_loads=0, model_reads=0, network_requests=0,
        compiler_process_scope=config["process_scope"])
    def fail(error, phase):
        nonlocal failure
        failure = dict(error_class=type(error).__name__, message=str(error)[:2048], phase=phase)
        result.update(status="failed", failure=failure)
        try:
            if not (output / "failure.json").exists():
                frozen.write_new(output / "failure.json", dict(authoritative=True, **failure, automatic_retry=False))
        except BaseException as marker_error:
            result["failure_marker_error_class"] = type(marker_error).__name__
    try:
        old = accepted(frozen)
        need(config["commands"] == commands(frozen, prepared, output)
             and config["environment"] == frozen.build_environment(old["environment"], output), "Command/environment changed")
        frozen.write_new(output / "effective-protocol.json", config)
        inputs = config["inputs"] + [frozen.pin(PROTOCOL)]
        leases.enter_context(frozen.stable_files([Path(row["path"]) for row in inputs], deadline=deadline))
        verify_pins(frozen, inputs, deadline)
        for step in config["commands"]:
            frozen.run_tool(step, output, config["environment"], journal, state, deadline, result["commands"])
        exe = frozen.safe(output / "harmless_launch_worker.exe", output)
        obj = frozen.safe(output / "worker.obj", output)
        need(0 < exe.stat().st_size <= 16 * 1024**2 and 0 < obj.stat().st_size <= 128 * 1024**2,
             "Generated executable/object cap")
        leases.enter_context(frozen.stable_files([exe, obj], deadline=deadline))
        binary = frozen.PE(exe.read_bytes()); ordinary, delayed = binary.imports(), binary.imports(True)
        pe_policy(ordinary, delayed)
        verify_pins(frozen, inputs, deadline)
        need(state["dispatches"] == 2 and not state["denied"] and dict(os.environ) == INITIAL_ENV,
             "Build dispatch/guard/environment mismatch")
        result.update(status=STATUS, executable=frozen.pin(exe), object=frozen.pin(obj), ordinary_imports=ordinary,
            delay_imports=delayed, generated_outputs_read_leased_during_static_checks=True,
            global_environment_unchanged=True)
    except BaseException as error:
        fail(error, "build_or_static_qualification")
    finally:
        sealed = finalize(frozen, output, result, state, journal, leases, deadline, started, expected)
    print(json.dumps(dict(status=result["status"], output=str(output),
        authoritative_failure=(output / "failure.json").exists(), elapsed_seconds=time.monotonic() - started)))
    return 0 if sealed and failure is None and result["status"] == STATUS else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--prepare"]:
        prepare()
    elif len(sys.argv) == 3 and sys.argv[1] == "--build":
        raise SystemExit(build(sys.argv[2]))
    else:
        raise SystemExit("--prepare only; --build PROTOCOL_SHA256 requires separate exact-hash authorization")
