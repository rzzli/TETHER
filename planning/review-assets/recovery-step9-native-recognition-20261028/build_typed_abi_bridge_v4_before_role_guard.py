"""Prepare/build a typed ABI bridge; recognition disabled, result never executed.

The frozen tool runner/audit/environment/import parser are reused unchanged.
Only compiler/linker handles are controlled; descendants are not attested.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import re
import struct
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASIS = HERE / "build_public_c_bridge.py"
BASIS_SHA = "733a47bb8c047e129560c0c68dd63d97cf09c95c23b3cabd105df7791927c09c"
FINALIZER_BASIS = HERE / "build_harmless_native_worker_v3.py"
FINALIZER_BASIS_SHA = "f292b65c6a86a9a70a41a1fb5286e20266281b6749c1583579e64193524af5ae"
OLD_PROTOCOL = HERE / "BUILD-PROTOCOL.json"
OLD_PROTOCOL_SHA = "5c6086e48ca9fb3b3f1f61a2eea780e64f1392bbdc819216e37b09935acc345e"
OLD_PREPARED = ROOT / "data/cache/r09-public-c-bridge-preparation-20261028T175036Z"
SOURCE = HERE / "typed_public_c_recognizer_v4.cpp"
SOURCE_SHA = "2f34035545c6d7bd742b8932a95449aeb76ebc48084e8dc170cbea6b740794ae"
DESIGN = HERE / "BRIDGE-DRAFT-DESIGN-v4.md"
DESIGN_SHA = "f91c93036e195de83416e75f37d35d4be35617c5f9343dc9191442cd9e01d13b"
OWNER_CHECKER = HERE / "check_bridge_symbol_owners_v4.py"
OWNER_CHECKER_SHA = "cb4196f2a3d0d39c44f9b0c1ab581cdd0a25314c8fedb61bee2529d3ea502ef9"
OWNER_PROOF = HERE / "BRIDGE-SYMBOL-OWNERS-PURE-PROOF-v4.json"
OWNER_PROOF_SHA = "cae0ad9da16ca1a95a29abe8ee99ba89c2edbf75dc1a4690afe15777d0a726eb"
HEADER = OLD_PREPARED / "recognizer_runtime_pins.hpp"
HEADER_SHA = "dee857596074375218a3c3f8d11130f4066fbfb07b7ae08e454f1f12306a1784"
PROTOCOL = HERE / "TYPED-ABI-BUILD-PROTOCOL-v4.json"
PREPARATION = HERE / "TYPED-ABI-BUILD-PREPARATION-v4.json"
PREPARATION_FAILURE = HERE / "TYPED-ABI-BUILD-PREPARATION-FAILURE-v4.json"
PURE = HERE / "TYPED-ABI-BUILD-PURE-CHECKS-v4.json"
PURE_CHECKER = HERE / "check_typed_abi_build_v4.py"
INITIAL_ENV = dict(os.environ)
LIMITS = dict(total_seconds=60, compile_seconds=45, link_seconds=10,
    finalization_reserve_seconds=5, stdout_bytes=262144, stderr_bytes=262144,
    maximum_children=2, execute_result=False)
STATUS = "typed_ABI_bridge_built_recognition_disabled_not_executed"
CORE_NAMES = {"libomp.dll", "ggml-base.dll", "ggml.dll", "llama.dll"}
EXPECTED_GROUPS = {
    "LLAMA_APIS": ("llama.dll", "llama", ["llama_version", "llama_model_default_params", "llama_backend_init",
        "llama_backend_free", "llama_model_load_from_splits", "llama_model_free", "llama_model_get_vocab",
        "llama_vocab_n_tokens", "llama_vocab_is_eog", "llama_tokenize", "llama_token_to_piece",
        "llama_sampler_init_grammar", "llama_sampler_apply", "llama_sampler_accept", "llama_sampler_free"]),
    "GGML_APIS": ("ggml.dll", "ggml", ["ggml_backend_load", "ggml_backend_reg_count", "ggml_backend_reg_get",
        "ggml_backend_dev_count", "ggml_backend_dev_get"]),
    "GGML_BASE_APIS": ("ggml-base.dll", "base", ["ggml_backend_reg_name", "ggml_backend_reg_dev_count",
        "ggml_backend_reg_dev_get", "ggml_backend_dev_name", "ggml_backend_dev_type"])}


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def basis():
    need(sha(BASIS) == BASIS_SHA and sha(FINALIZER_BASIS) == FINALIZER_BASIS_SHA,
         "Frozen tool/finalizer basis changed")
    spec = util.spec_from_file_location("frozen_build_tools_for_bridge_v4", BASIS)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    need(module.LIMITS == LIMITS, "Frozen finite tool limits changed")
    return module


def source_checks():
    for path, expected in ((SOURCE, SOURCE_SHA), (DESIGN, DESIGN_SHA),
                           (OWNER_CHECKER, OWNER_CHECKER_SHA), (OWNER_PROOF, OWNER_PROOF_SHA),
                           (OLD_PROTOCOL, OLD_PROTOCOL_SHA), (HEADER, HEADER_SHA)):
        need(sha(path) == expected, "Pinned source/ownership/header basis changed: " + path.name)
    header = HEADER.read_text(encoding="utf-8")
    need('R09_RECOGNITION_ENABLED = false;' in header and 'R09_EXPECTED_LLAMA_VERSION[] = "";' in header,
         "Existing header is no longer recognition-disabled/unknown-version")
    proof = json.loads(OWNER_PROOF.read_bytes())
    need(proof["status"] == "passed_static_symbol_owner_regressions" and proof["tests_run"] == 7
         and proof["failures"] == proof["errors"] == 0 and proof["source"]["sha256"] == SOURCE_SHA
         and proof["helper"]["sha256"] == OWNER_CHECKER_SHA, "Static owner regression proof differs")
    text = SOURCE.read_text(encoding="utf-8")
    rows = []
    for group, (owner, handle, names) in EXPECTED_GROUPS.items():
        match = re.search(r"^#define " + group + r"\(X\) (.+)$", text, re.M)
        need(match is not None and re.findall(r"X\((\w+)\)", match.group(1)) == names,
             "Exact typed export group differs")
        rows.extend(dict(symbol=name, owner=owner, handle=handle, group=group) for name in names)
    need(rows == proof["complete_symbol_mapping"] and len({row["symbol"] for row in rows}) == 25,
         "Typed owner mapping changed or duplicated")
    need('Api api(llama, ggml, base);' in text
         and 'std::string("required_export_missing:") + owner + ":" + name' in text,
         "Exact base handle or bounded owner/name diagnostics missing")
    return rows


def named_exports(raw):
    """Bounded x64 PE named exports, never an OS loader or function call."""
    need(type(raw) is bytes and 0 < len(raw) <= 128 * 1024**2 and raw[:2] == b"MZ", "PE input cap/signature")
    def number(offset, form):
        size = struct.calcsize(form)
        need(0 <= offset <= len(raw)-size, "PE field out of bounds")
        return struct.unpack_from(form, raw, offset)[0]
    pe = number(0x3c, "<I")
    need(raw[pe:pe+4] == b"PE\0\0" and number(pe+4, "<H") == 0x8664, "x64 PE required")
    opt = pe + 24
    count, opt_size = number(pe+6, "<H"), number(pe+20, "<H")
    need(number(opt, "<H") == 0x20b and 0 < count <= 96 and opt_size >= 120, "PE64 layout")
    sections = []
    for i in range(count):
        at = opt + opt_size + i*40
        sections.append((number(at+12, "<I"), number(at+20, "<I"), number(at+16, "<I")))
    def offset(rva, size=1):
        for virtual, start, length in sections:
            if virtual <= rva and rva-virtual+size <= length:
                result = start+rva-virtual
                need(0 <= result and result+size <= len(raw), "PE section exceeds file")
                return result
        raise RuntimeError("Unmapped PE export RVA")
    def string(rva):
        at = offset(rva)
        end = raw.find(b"\0", at, min(len(raw), at+65536))
        need(end >= at, "Unterminated PE export name")
        return raw[at:end].decode("ascii")
    export_rva, export_size = number(opt+112, "<I"), number(opt+116, "<I")
    need(export_rva and export_size >= 40, "No bounded export directory")
    directory = offset(export_rva, 40)
    functions, names = number(directory+20, "<I"), number(directory+24, "<I")
    need(0 < functions <= 65536 and 0 <= names <= 65536, "Export table count cap")
    ft, nt, ot = (number(directory+x, "<I") for x in (28, 32, 36))
    result = {}
    for i in range(names):
        name = string(number(offset(nt+4*i, 4), "<I"))
        ordinal = number(offset(ot+2*i, 2), "<H")
        need(ordinal < functions and name not in result, "Export ordinal/duplicate name")
        rva = number(offset(ft+4*ordinal, 4), "<I")
        result[name] = dict(rva=rva, forwarder=string(rva) if export_rva <= rva < export_rva+export_size else None)
    return result


def verify_export_mapping(rows, tables):
    need(len(rows) == 25 and len({row["symbol"] for row in rows}) == 25, "Complete unique owner map required")
    for row in rows:
        item = tables.get(row["owner"], {}).get(row["symbol"])
        need(item is not None and item["rva"] > 0 and item["forwarder"] is None,
             "Missing/non-direct exact owner export: " + row["owner"] + ":" + row["symbol"])


def filtered_basis_inputs(old, frozen):
    """Select before any path read: CPU/model/pack binaries are never opened."""
    accepted_root = ROOT / "data/cache/recovery-step9-generation-wheel-20261028"
    public = {row["source"]["path"] for row in old["headers"]}
    public.update(row["copied"]["path"] for row in old["headers"])
    metadata_names = {"acceptance.json", "WHEEL-ENVIRONMENTS.json", "TOOLCHAIN-LOCAL-PROBE-v2.json",
                      "filtered-build-environment.json", "HEADER-CLOSURE-FOLLOWUP.json"}
    selected, excluded = [], []
    for item in old["inputs"]:
        path = Path(item["path"])
        keep = (path.is_relative_to(accepted_root) or str(path) in public or path.name in metadata_names
                or path.is_relative_to(frozen.TOOLROOT) or path.is_relative_to(frozen.SDKROOT)
                or path.parent == frozen.SYSTEM or path == frozen.PYBASE
                or path.name in ("vswhere.exe", "VsDevCmd.bat")
                or (path.parent == frozen.RUNTIME and path.name in CORE_NAMES))
        need(path.suffix.casefold() != ".gguf", "Old metadata unexpectedly lists a model payload")
        if path.name == "ggml-cpu-x64.dll": keep = False
        (selected if keep else excluded).append(item)
    need(not any(Path(row["path"]).name == "ggml-cpu-x64.dll" for row in selected), "CPU binary selected")
    return selected, excluded


def accepted(frozen, *, require_pure=True):
    need(os.name == "nt" and sys.flags.isolated and sys.dont_write_bytecode,
         "Isolated Windows accepted parent required")
    need(metadata.version("asof-target-agents") == "0.3.11" and util.find_spec("pyarrow") is None,
         "Accepted dependency-free0.3.11 required")
    source_checks()
    old = json.loads(OLD_PROTOCOL.read_bytes())
    need(old["accepted_software_sha256"] == frozen.ACCEPTANCE_SHA and old["execute_result"] is False,
         "Old build authority differs")
    need(sha(frozen.ACCEPTANCE) == frozen.ACCEPTANCE_SHA, "Accepted software identity differs")
    if require_pure:
        proof = json.loads(PURE.read_bytes())
        need(proof["status"] == "passed" and proof["helper_sha256"] == sha(__file__)
             and proof["checker_sha256"] == sha(PURE_CHECKER)
             and proof["actual_compiler_dispatches"] == proof["actual_children"] == 0, "Fresh focused pure proof required")
    return old


def collect_inputs(frozen, old):
    selected, excluded = filtered_basis_inputs(old, frozen)
    files = [BASIS, FINALIZER_BASIS, OLD_PROTOCOL, SOURCE, DESIGN, OWNER_CHECKER, OWNER_PROOF,
             HEADER, Path(__file__), PURE, PURE_CHECKER, HERE / "ABI-EXPORT-STATIC-CROSSCHECK-v1.json",
             HERE / "ABI-EXPORT-AND-NEGATIVE-EXIT-REVIEW-v1.json",
             HERE / "DETACHED-ABI-V1-RESULT-VERIFICATION.json"]
    records = selected + [frozen.pin(path) for path in files]
    unique = {os.path.normcase(item["path"]): item for item in records}
    need(len(unique) == len({item["path"].casefold() for item in records}), "Ambiguous input spelling")
    return list(unique.values()), excluded


def verify_pins(frozen, records, deadline):
    for item in records:
        frozen.safe_input(item["path"])
        need(frozen.encode(frozen.hash_file(item["path"], deadline)) ==
             {key: item[key] for key in ("bytes", "sha256")}, "Pinned input changed: " + item["path"])


def export_tables(old):
    result = {}
    for row in old["runtime_pins"]:
        if row["name"] in CORE_NAMES:
            item = row["pin"]
            need(sha(item["path"]) == item["sha256"] and Path(item["path"]).stat().st_size == item["bytes"],
                 "Exact core PE bytes changed")
            result[row["name"]] = named_exports(Path(item["path"]).read_bytes())
    need(set(result) == CORE_NAMES, "Exact four-core static read set required")
    return result


def pe_policy(ordinary, delayed):
    need(not delayed and not any(any(tag in name.casefold() for tag in
         ("llama", "ggml", "ws2_32", "winhttp", "wininet", "urlmon")) for name in ordinary),
         "Target/network static imports forbidden")
    forbidden = ("CreateProcess", "ShellExecute", "WinHttp", "InternetOpen", "WSAStartup")
    need(not any(any(tag in name for tag in forbidden) for names in ordinary.values() for name in names),
         "Process/network static function import forbidden")


def commands(frozen, prepared, output, old):
    return frozen.commands(prepared, output, dict(compiler=old["commands"][0]["argv"][0],
                                                linker=old["commands"][1]["argv"][0]))


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
            journal.append("typed_ABI_bridge_v4_build_terminal", status=result["status"], dispatches=state["dispatches"])
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
    need(not any(path.exists() for path in (PROTOCOL, PREPARATION, PREPARATION_FAILURE)), "Preparation consumed; no retry")
    frozen = basis(); old = accepted(frozen)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prepared = frozen.safe(ROOT / "data/cache" / ("r09-typed-ABI-preparation-v4-" + stamp))
    output = frozen.safe(ROOT / "data/cache" / ("r09-typed-ABI-build-v4-" + stamp))
    need(not prepared.exists() and not output.exists(), "Exclusive preparation/build output exists")
    inputs, excluded = collect_inputs(frozen, old)
    state = dict(active=None, environment=None, dispatches=0, denied=[], write_roots=[prepared],
                 write_files={PROTOCOL, PREPARATION, PREPARATION_FAILURE})
    frozen.audit(state)
    deadline = time.monotonic() + 60
    try:
        with ExitStack() as leases:
            leases.enter_context(frozen.stable_files([Path(row["path"]) for row in inputs], deadline=deadline))
            verify_pins(frozen, inputs, deadline)
            verify_export_mapping(source_checks(), export_tables(old))
            prepared.mkdir(); (prepared / "headers").mkdir()
            copies = [(SOURCE, prepared / "typed_public_c_recognizer.cpp"), (HEADER, prepared / "recognizer_runtime_pins.hpp")]
            copies += [(Path(row["copied"]["path"]), prepared / "headers" / Path(row["copied"]["path"]).name)
                       for row in old["headers"]]
            need(len(old["headers"]) == 7, "Seven public header files required")
            for original, copied in copies:
                with copied.open("xb") as stream:
                    stream.write(original.read_bytes()); stream.flush(); os.fsync(stream.fileno())
                need(sha(original) == sha(copied), "Copied source/header differs")
                inputs.append(frozen.pin(copied))
            need(sha(prepared / "recognizer_runtime_pins.hpp") == HEADER_SHA, "Existing header bytes changed")
            leases.enter_context(frozen.stable_files([copied for _, copied in copies], deadline=deadline))
            verify_pins(frozen, inputs, deadline)
            value = dict(schema_version=1, kind="typed_ABI_bridge_v4_build_recognition_disabled", helper=frozen.pin(__file__),
                source=frozen.pin(SOURCE), design=frozen.pin(DESIGN), prepared=str(prepared), output=str(output),
                commands=commands(frozen, prepared, output, old), environment=frozen.build_environment(old["environment"], output),
                limits=LIMITS, inputs=inputs, filtered_basis_count=len(old["inputs"]), excluded_basis_inputs=excluded,
                input_count=len(inputs), header=frozen.pin(prepared / "recognizer_runtime_pins.hpp"),
                old_header=frozen.pin(HEADER), static_owner_proof=frozen.pin(OWNER_PROOF),
                recognition_enabled=False, expected_version="", execute_result=False, build_authorized_by_preparation=False,
                accepted_software_sha256=frozen.ACCEPTANCE_SHA,
                process_scope="Launched compiler/linker handles only; descendants not independently attested",
                toolchain_scope="Pinned prior direct SDK/STL/tool leaves and libraries; not a complete transitive toolchain closure",
                source_compile_scope="Own reviewed bridge and seven public declarations; no fetched project implementation",
                header_scope="Unchanged ABI data header contains unused CPU/GGUF names; no payload reads",
                activity=dict(compiler_dispatches=0, children=0, result_executions=0, target_DLL_loads=0, CPU_binary_reads=0,
                              GGUF_model_reads=0, network_requests=0, accepted_file_lease_API_used=True))
            frozen.write_new(PROTOCOL, value)
        frozen.deadline_check(deadline)
        need(state["dispatches"] == 0 and not state["denied"] and dict(os.environ) == INITIAL_ENV,
             "Preparation dispatched or changed environment")
        frozen.write_new(PREPARATION, dict(schema_version=1, status="prepared_compile_link_only_not_dispatched",
            helper=frozen.pin(__file__), protocol=frozen.pin(PROTOCOL), input_count=len(inputs),
            excluded_basis_count=len(excluded), output_absent=not output.exists(), limits=LIMITS, activity=value["activity"]))
    except BaseException as error:
        if not PREPARATION_FAILURE.exists():
            frozen.write_new(PREPARATION_FAILURE, dict(authoritative=True, automatic_retry=False,
                error_class=type(error).__name__, error=str(error)[:2048]))
        raise
    print(json.dumps(dict(status="prepared_compile_link_only_not_dispatched", helper_sha256=sha(__file__),
        protocol_sha256=sha(PROTOCOL), inputs=len(inputs), excluded=len(excluded), output=str(output))))


def validate_config(config, frozen, old):
    output = frozen.safe(config["output"], ROOT / "data/cache")
    prepared = frozen.safe(config["prepared"], ROOT / "data/cache")
    need(config["kind"] == "typed_ABI_bridge_v4_build_recognition_disabled"
         and config["helper"] == frozen.pin(__file__) and config["source"] == frozen.pin(SOURCE)
         and config["design"] == frozen.pin(DESIGN) and config["limits"] == LIMITS
         and config["recognition_enabled"] is False and config["expected_version"] == ""
         and config["execute_result"] is False and config["header"]["sha256"] == HEADER_SHA,
         "Exact compile-only recognition-disabled scope changed")
    need(config["commands"] == commands(frozen, prepared, output, old)
         and config["environment"] == frozen.build_environment(old["environment"], output), "Commands/environment changed")
    need(not output.exists(), "Build attempt already consumed; no retry")
    return prepared, output


def build(expected):
    frozen = basis()
    need(len(expected) == 64 and sha(PROTOCOL) == expected and not PREPARATION_FAILURE.exists(),
         "Exact separately reviewed protocol required")
    old = accepted(frozen); config = json.loads(PROTOCOL.read_bytes())
    prepared, output = validate_config(config, frozen, old)
    started = time.monotonic(); deadline = started + 60
    journal = frozen.RunJournal(output, kind="build")
    state = dict(active=None, environment=config["environment"], dispatches=0, denied=[], write_roots=[output], write_files=set())
    frozen.audit(state, output); leases = ExitStack(); failure = None; sealed = False
    result = dict(schema_version=1, status="failed", protocol_sha256=expected, commands=[], executable_executions=0,
        target_DLL_loads=0, CPU_binary_reads=0, GGUF_model_reads=0, network_requests=0,
        compiler_process_scope=config["process_scope"])
    try:
        frozen.write_new(output / "effective-protocol.json", config)
        inputs = config["inputs"] + [frozen.pin(PROTOCOL)]
        leases.enter_context(frozen.stable_files([Path(row["path"]) for row in inputs], deadline=deadline))
        verify_pins(frozen, inputs, deadline)
        verify_export_mapping(source_checks(), export_tables(old))
        for step in config["commands"]:
            frozen.run_tool(step, output, config["environment"], journal, state, deadline, result["commands"])
        exe, obj = output / "typed_public_c_recognizer_abi.exe", output / "bridge.obj"
        need(0 < exe.stat().st_size <= 16 * 1024**2 and 0 < obj.stat().st_size <= 128 * 1024**2, "Generated output cap")
        leases.enter_context(frozen.stable_files([exe, obj], deadline=deadline))
        binary = frozen.PE(exe.read_bytes()); ordinary, delayed = binary.imports(), binary.imports(True)
        pe_policy(ordinary, delayed); verify_pins(frozen, inputs, deadline)
        need(state["dispatches"] == 2 and not state["denied"] and dict(os.environ) == INITIAL_ENV,
             "Build dispatch/guard/environment mismatch")
        result.update(status=STATUS, executable=frozen.pin(exe), object=frozen.pin(obj), ordinary_imports=ordinary,
                      delay_imports=delayed, generated_outputs_read_leased_during_static_checks=True,
                      recognition_enabled=False, expected_version="", global_environment_unchanged=True)
    except BaseException as error:
        failure = dict(error_class=type(error).__name__, message=str(error)[:2048], phase="build_or_static_checks")
        result.update(status="failed", failure=failure)
        try:
            if not (output / "failure.json").exists():
                frozen.write_new(output / "failure.json", dict(authoritative=True, automatic_retry=False, **failure))
        except BaseException as marker:
            result["failure_marker_error_class"] = type(marker).__name__
    finally:
        sealed = finalize(frozen, output, result, state, journal, leases, deadline, started, expected)
    print(json.dumps(dict(status=result["status"], output=str(output), elapsed_seconds=time.monotonic()-started)))
    return 0 if sealed and failure is None and result["status"] == STATUS else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--prepare"]:
        prepare()
    elif len(sys.argv) == 3 and sys.argv[1] == "--build":
        raise SystemExit(build(sys.argv[2]))
    else:
        raise SystemExit("Prepare, obtain exact independent root decision, then --build SHA256; never execute result")
