"""Prepare/build the own recognition-enabled bridge; result/payload access remain unauthorized.

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
PREVIOUS_BUILDER = HERE / "build_trusted_platform_bridge_v2.py"
PREVIOUS_BUILDER_SHA = "22bf933308ddf5b35a17db9d4c9d5c46d33ba04f6b01f0fa74a2261052b92515"
SOURCE = HERE / 'typed_public_c_recognizer_recognition_v2.cpp'
SOURCE_SHA = 'e683cf9b307e8e5d8943dc7f859c1f1a6e20f24dcd40faca19ab32841a9fe2ae'
DESIGN = HERE / 'RECOGNITION-MODULE-POLICY-v1.json'
DESIGN_SHA = '1f918760526adf368910096a3fc9f60c4cbd78fba5737907b332396d3f6ea37a'
VECTORS = HERE / 'RECOGNITION-MODULE-VECTORS-v1.json'
VECTORS_SHA = '3602f46516165149ae34b74db0abbdc2b6f0d88e75edca5f026ebbc752ef0475'
MATCHER = HERE / 'recognition_module_policy_v1.py'
MATCHER_SHA = '5031f2e3d1672684ef0d0dee1aa8370184cd8bc4df05042bfc135c1451f48f12'
MATCHER_PROOF = HERE / 'RECOGNITION-MODULE-POLICY-PURE-PROOF-v1.json'
MATCHER_PROOF_SHA = 'be9a1742109a2c7f8eaa2df1ce400b00f616e9b4fa5c178cd5ae1efe30dc297d'
MATCHER_CHECKER = HERE / 'check_recognition_module_policy_v1.py'
MATCHER_CHECKER_SHA = 'df07176b41acf18b3cf841b477f958d05430d4f38723ebb471c9b2fc1a788ac0'
CHILD_CHECKER = HERE / 'check_recognition_child_v2.py'
CHILD_CHECKER_SHA = '47e90c52a7d6b4c0ba35efa795152f262eaeb695f14eebfd49a4473b07fcd2bd'
CHILD_PROOF = HERE / 'RECOGNITION-CHILD-SOURCE-PURE-PROOF-v2.json'
CHILD_PROOF_SHA = 'f5bd0d8088981530c8bbeffe3390d51d3e813bd408e67eb6754b121849d8d14a'
SOURCE_PEER = HERE / 'RECOGNITION-CHILD-SOURCE-PEER-REVIEW-v2.json'
SOURCE_PEER_SHA = '17c6e6b4faadfe6dee4724e292ae434fed8ebcc8ec63953955a71dd2c9adc39f'
ROOT_POLICY = HERE / 'RECOGNITION-SOURCE-ROOT-DECISION-v1.json'
ROOT_POLICY_SHA = '20ea58d6626b82dd55c7b823ed1bd729134ecac15470fcc6c4c1ad69d92a5399'
EXECUTION_CONTRACT = HERE / 'RECOGNITION-EXECUTION-CONTRACT-v1.json'
EXECUTION_CONTRACT_SHA = '30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861'
WIRE = HERE / 'RECOGNITION-CHILD-WIRE-v2.json'
WIRE_SHA = 'd578bc2179e55f7866dd7b2df3ec3169fdc3bcb0dee58629c2a31b8d366d0d01'
DESCRIPTOR = HERE / 'RECOGNITION-RUNTIME-PIN-DESCRIPTOR-v1.json'
DESCRIPTOR_SHA = 'e42cfda8a76c0784883c5d3dd1f695fd6e10c4d60b9c85685bfc2aba2a89922c'
DESCRIPTOR_CHECKER = HERE / 'check_recognition_descriptors_v1.py'
DESCRIPTOR_CHECKER_SHA = '648c43d00d660957abef56bdea3ec558ccfe1a47d3123540e08839e0c388af66'
DESCRIPTOR_PROOF = HERE / 'RECOGNITION-DESCRIPTOR-PURE-PROOF-v1.json'
DESCRIPTOR_PROOF_SHA = '40f998b32f6acba26a8af7cb411109d26769cd8b4b8fa36436e470472fadff21'
HEADER = HERE / 'recognition_runtime_pins_v1.hpp'
HEADER_SHA = '0a049358a1d8f2a8fd1bcc734a7c3995535f6e1829ec1bf0de8b39df1f86b3e6'
BUILD_PREP_DECISION = HERE / 'RECOGNITION-BUILD-PREPARATION-ROOT-DECISION-v1.json'
BUILD_PREP_DECISION_SHA = 'a90c8d1c8e99f803dcde99c3256de226324a7d8b119315329a965b1f09bd3e48'
PACK_METADATA = HERE / 'RECOGNITION-EXPECTED-PACK-METADATA-v1.json'
PACK_METADATA_SHA = '096e1234e239d04c3b276295e7176f5886f139a4064c3fc5f207745f8938f64d'
ABI_ACCEPTANCE = HERE / 'TRUSTED-PLATFORM-ABI-ACCEPTANCE-v1.json'
ABI_ACCEPTANCE_SHA = '024e053664ba45dbda59096ea3a11ab4351fc52fc6f06300af045bc152d2991b'
POLICY_ID = "trusted-System32-recognition-v1"
POLICY_SHA = "4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713"
EXCEPTION_HEADER = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.51.36231\include\exception")
EXCEPTION_HEADER_SHA = "49c3ebe69f8fd1947c6a05f7de89dd17fc962e4c229b8bf1a5b0d040e5dcb0cb"
PROTOCOL = HERE / "RECOGNITION-BUILD-PROTOCOL-v1.json"
PREPARATION = HERE / "RECOGNITION-BUILD-PREPARATION-v1.json"
PREPARATION_FAILURE = HERE / "RECOGNITION-BUILD-PREPARATION-FAILURE-v1.json"
PURE = HERE / "RECOGNITION-BUILD-PURE-CHECKS-v1.json"
PURE_CHECKER = HERE / "check_recognition_build_v1.py"
INITIAL_ENV = dict(os.environ)
ACCEPTED_PARENT = ROOT / "data/cache/recovery-step9-generation-wheel-20261028/environment/Scripts/python.exe"
LIMITS = dict(total_seconds=60, compile_seconds=45, link_seconds=10,
    finalization_reserve_seconds=5, stdout_bytes=262144, stderr_bytes=262144,
    maximum_children=2, execute_result=False)
STATUS = "recognition_enabled_bridge_built_not_executed_or_runtime_qualified"
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
    spec = util.spec_from_file_location("frozen_build_tools_for_bridge_v5", BASIS)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    need(module.LIMITS == LIMITS, "Frozen finite tool limits changed")
    return module


def previous_builder():
    need(sha(PREVIOUS_BUILDER) == PREVIOUS_BUILDER_SHA, "Frozen trusted-platform build basis changed")
    spec = util.spec_from_file_location("frozen_platform_basis_for_recognition_build", PREVIOUS_BUILDER)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_checks():
    previous = previous_builder()
    rows = previous.source_checks()  # Preserve qualified ABI/owner/software basis.
    for path, expected in ((SOURCE, SOURCE_SHA),
                           (DESIGN, DESIGN_SHA),
                           (VECTORS, VECTORS_SHA),
                           (MATCHER, MATCHER_SHA),
                           (MATCHER_PROOF, MATCHER_PROOF_SHA),
                           (MATCHER_CHECKER, MATCHER_CHECKER_SHA),
                           (CHILD_CHECKER, CHILD_CHECKER_SHA),
                           (CHILD_PROOF, CHILD_PROOF_SHA),
                           (SOURCE_PEER, SOURCE_PEER_SHA),
                           (ROOT_POLICY, ROOT_POLICY_SHA),
                           (EXECUTION_CONTRACT, EXECUTION_CONTRACT_SHA),
                           (WIRE, WIRE_SHA),
                           (DESCRIPTOR, DESCRIPTOR_SHA),
                           (DESCRIPTOR_CHECKER, DESCRIPTOR_CHECKER_SHA),
                           (DESCRIPTOR_PROOF, DESCRIPTOR_PROOF_SHA),
                           (HEADER, HEADER_SHA),
                           (BUILD_PREP_DECISION, BUILD_PREP_DECISION_SHA),
                           (PACK_METADATA, PACK_METADATA_SHA),
                           (ABI_ACCEPTANCE, ABI_ACCEPTANCE_SHA), (EXCEPTION_HEADER, EXCEPTION_HEADER_SHA)):
        need(sha(path) == expected, "Pinned recognition source/proof/header changed: " + path.name)
    child = json.loads(CHILD_PROOF.read_bytes())
    need(child["status"] == "passed" and child["tests"] == 15 and child["shared_vectors"] == 100
         and child["source_sha256"] == SOURCE_SHA and child["source_unchanged"] is True
         and child["checker_sha256"] == CHILD_CHECKER_SHA and child["execution_contract_sha256"] == EXECUTION_CONTRACT_SHA
         and child["phase_policy_sha256"] == DESIGN_SHA and child["descriptor_sha256"] == DESCRIPTOR_SHA
         and child["failures"] == child["errors"] == [] and all(value == 0 for value in child["activity"].values()),
         "Exact recognition intended-model/static proof differs")
    header_proof = json.loads(DESCRIPTOR_PROOF.read_bytes())
    need(header_proof["status"] == "passed" and header_proof["tests"] == 5
         and header_proof["failures"] == header_proof["errors"] == [] and header_proof["checker_sha256"] == DESCRIPTOR_CHECKER_SHA
         and header_proof["descriptor_sha256"] == DESCRIPTOR_SHA and header_proof["header_sha256"] == HEADER_SHA
         and header_proof["contract_sha256"] == EXECUTION_CONTRACT_SHA
         and all(header_proof[key] == 0 for key in ("CPU_GGUF_pack_payload_stat_open_hash", "compiler_calls", "SDK_constructors", "children")),
         "Exact metadata-only descriptor proof differs")
    phase = json.loads(MATCHER_PROOF.read_bytes()); policy = json.loads(DESIGN.read_bytes())
    semantic_sha = hashlib.sha256(json.dumps(policy["semantic_policy"], sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
    need(phase["status"] == "passed" and phase["tests"] == 5 and phase["vector_count"] == 100
         and phase["failures"] == phase["errors"] == phase["denied_real_operations"] == []
         and phase["source"]["sha256"] == MATCHER_SHA and phase["checker"]["sha256"] == MATCHER_CHECKER_SHA
         and phase["vectors"]["sha256"] == VECTORS_SHA and phase["module_policy_sha256"] == POLICY_SHA == semantic_sha
         and all(value == 0 for value in phase["activity"].values()), "Exact recognition phase proof differs")
    validate_header_data(HEADER.read_text(encoding="utf-8"), json.loads(DESCRIPTOR.read_bytes()), json.loads(EXECUTION_CONTRACT.read_bytes()))
    text = SOURCE.read_text(encoding="utf-8"); prior = previous.SOURCE.read_text(encoding="utf-8")
    begin, end = "template<class T> static T symbol", "struct Reader {"
    need(text[text.index(begin):text.index(end)] == prior[prior.index(begin):prior.index(end)],
         "Existing25 export owners/public defaults/layouts changed")
    need(re.findall(r"^#include .+$", text, re.M) == re.findall(r"^#include .+$", prior, re.M), "Verified direct include sequence changed")
    need('COOPERATIVE_MS = 117000;' in text and 'NATIVE_TOTAL_CAP = 4276181;' in text
         and 'RECOGNITION_POLICY_SHA256 = "' + POLICY_SHA + '";' in text, "Recognition source profile differs")
    return rows


def validate_header_data(text, descriptor, contract):
    """Metadata-only: never stat/open/hash a described CPU/GGUF/pack file."""
    need(descriptor["header"]["sha256"] == HEADER_SHA and descriptor["observed_version"] == contract["observed_version"] == "0.7.0-dev"
         and descriptor["module_policy_sha256"] == POLICY_SHA and descriptor["cooperative_work_ms"] == 117000
         and all(value is False for value in descriptor["authority"].values()) and not any(descriptor["activity"].values()),
         "Prospective header cannot grant payload/runtime authority")
    need('R09_RECOGNITION_ENABLED = true;' in text and 'R09_EXPECTED_LLAMA_VERSION[] = "0.7.0-dev";' in text
         and 'R09_COOPERATIVE_WORK_MS = 117000ull;' in text, "Recognition-enabled version/clock header differs")
    entries = re.findall(r'\{L"((?:[^"\\]|\\.)*)", "([0-9a-f]{64})", ([0-9]+)ull\}', text)
    parsed = [dict(path=json.loads('"' + path + '"'), sha256=checksum, bytes=int(size)) for path, checksum, size in entries]
    need(parsed[-3:] == contract["ordered_shard_descriptors"], "Exact ordered3 shard metadata differs")
    need([dict(path=row["path_or_name"], bytes=row["bytes"], sha256=row["sha256"]) for row in descriptor["ordered_shard_descriptors"]]
         == contract["ordered_shard_descriptors"], "Descriptor shard order/identity differs")
    cpu = next(row for row in parsed if row["path"] == "ggml-cpu-x64.dll")
    need(cpu["bytes"] == contract["CPU_descriptor"]["bytes"] and cpu["sha256"] == contract["CPU_descriptor"]["sha256"]
         and descriptor["CPU_descriptor"]["bytes"] == cpu["bytes"] and descriptor["CPU_descriptor"]["sha256"] == cpu["sha256"],
         "CPU metadata differs")
    need(next(row for row in parsed if row["path"] == descriptor["pack"]["path"]) == descriptor["pack"]
         and descriptor["pack"]["sha256"] == "f75ab9937c57b5f03c2234643a8a9c91cda852ca0cca0de0478369f793e57e5f",
         "Frozen pack metadata differs")


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


def validate_parent_interpreter():
    need(Path(sys.executable).resolve() == ACCEPTED_PARENT.resolve(), "Pinned accepted parent interpreter required")


def accepted(frozen, *, require_pure=True):
    need(os.name == "nt" and sys.flags.isolated and sys.dont_write_bytecode,
         "Isolated Windows accepted parent required")
    validate_parent_interpreter()
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


def extra_input_paths():
    previous = previous_builder()
    paths = previous.extra_input_paths() + [PREVIOUS_BUILDER, SOURCE, DESIGN, VECTORS, MATCHER, MATCHER_PROOF, MATCHER_CHECKER,
        CHILD_CHECKER, CHILD_PROOF, SOURCE_PEER, ROOT_POLICY, EXECUTION_CONTRACT, WIRE, DESCRIPTOR, DESCRIPTOR_CHECKER,
        DESCRIPTOR_PROOF, HEADER, BUILD_PREP_DECISION, PACK_METADATA, ABI_ACCEPTANCE, EXCEPTION_HEADER, Path(__file__), PURE, PURE_CHECKER]
    paths += [HERE / name for name in (
        "typed_public_c_recognizer_recognition_v1.cpp", "check_recognition_child_v1.py", "RECOGNITION-CHILD-SOURCE-PURE-PROOF-v1.json",
        "RECOGNITION-UNKNOWN-CREATION-REGRESSIONS-BEFORE-v1.json", "RECOGNITION-HEADER-DESCRIPTOR-PREPARATION-FAILURE-v1.json",
        "RECOGNITION-CHILD-WIRE-v1.json", "PACK-V2-RESULT-VERIFICATION.json", "TRUSTED-PLATFORM-ABI-RESULT-VERIFICATION-v1.json")]
    return list(dict.fromkeys(paths))


def validate_input_roles(records, frozen, old, prepared):
    selected, _ = filtered_basis_inputs(old, frozen)
    originals = {os.path.normcase(item["path"]): item for item in selected}
    expected = set(originals) | {os.path.normcase(str(path)) for path in extra_input_paths()}
    expected.update(os.path.normcase(str(prepared / name)) for name in
                    ("typed_public_c_recognizer.cpp", "recognizer_runtime_pins.hpp"))
    expected.update(os.path.normcase(str(prepared / "headers" / Path(row["copied"]["path"]).name))
                    for row in old["headers"])
    seen = set()
    for item in records:
        path = Path(item["path"]); key = os.path.normcase(str(path))
        need(path.is_absolute() and path.name.casefold() != "ggml-cpu-x64.dll"
             and path.suffix.casefold() != ".gguf" and key in expected and key not in seen,
             "Input outside exact recognition software/metadata-only build role")
        need(key not in originals or item == originals[key], "Filtered original input pin changed")
        seen.add(key)
    need(seen == expected, "Exact build input path universe differs")


def collect_inputs(frozen, old):
    selected, excluded = filtered_basis_inputs(old, frozen)
    records = selected + [frozen.pin(path) for path in extra_input_paths()]
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
            journal.append("typed_ABI_bridge_v5_build_terminal", status=result["status"], dispatches=state["dispatches"])
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
    prepared = frozen.safe(ROOT / "data/cache" / ("r09-recognition-bridge-preparation-v1-" + stamp))
    output = frozen.safe(ROOT / "data/cache" / ("r09-recognition-bridge-build-v1-" + stamp))
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
            need(sha(prepared / "recognizer_runtime_pins.hpp") == HEADER_SHA, "Recognition data header copy changed")
            validate_header_data((prepared / "recognizer_runtime_pins.hpp").read_text(encoding="utf-8"),
                                 json.loads(DESCRIPTOR.read_bytes()), json.loads(EXECUTION_CONTRACT.read_bytes()))
            validate_input_roles(inputs, frozen, old, prepared)
            leases.enter_context(frozen.stable_files([copied for _, copied in copies], deadline=deadline))
            verify_pins(frozen, inputs, deadline)
            value = dict(schema_version=1, kind="recognition_bridge_v1_build_runtime_unqualified", helper=frozen.pin(__file__),
                source=frozen.pin(SOURCE), design=frozen.pin(DESIGN), prepared=str(prepared), output=str(output),
                commands=commands(frozen, prepared, output, old), environment=frozen.build_environment(old["environment"], output),
                limits=LIMITS, inputs=inputs, filtered_basis_count=len(old["inputs"]), excluded_basis_inputs=excluded,
                input_count=len(inputs), header=frozen.pin(prepared / "recognizer_runtime_pins.hpp"),
                old_header=frozen.pin(HEADER), static_owner_basis_proof=frozen.pin(previous_builder().previous_builder().previous_builder().OWNER_PROOF),
                platform_source_proof=frozen.pin(CHILD_PROOF), policy_contract=frozen.pin(DESIGN),
                shared_vectors=frozen.pin(VECTORS), pure_matcher=frozen.pin(MATCHER), pure_matcher_proof=frozen.pin(MATCHER_PROOF),
                root_policy_decision=frozen.pin(ROOT_POLICY), execution_contract=frozen.pin(EXECUTION_CONTRACT),
                header_descriptor=frozen.pin(DESCRIPTOR), descriptor_proof=frozen.pin(DESCRIPTOR_PROOF),
                wire=frozen.pin(WIRE), pack_metadata=frozen.pin(PACK_METADATA), ABI_acceptance=frozen.pin(ABI_ACCEPTANCE),
                build_preparation_decision=frozen.pin(BUILD_PREP_DECISION),
                module_policy_id=POLICY_ID, module_policy_sha256=POLICY_SHA, exception_header=frozen.pin(EXCEPTION_HEADER),
                source_peer_review=frozen.pin(SOURCE_PEER),
                module_policy_route="trusted_System32_recognition_pre_post_CPU", reported_platform_path_filesystem_operations=0,
                platform_image_authentication="not_established",
                recognition_enabled=True, expected_version="0.7.0-dev", runtime_execution_authorized=False, CPU_GGUF_payload_access_authorized=False, execute_result=False, build_authorized_by_preparation=False,
                accepted_software_sha256=frozen.ACCEPTANCE_SHA,
                process_scope="Launched compiler/linker handles only; descendants not independently attested",
                toolchain_scope="Pinned prior direct SDK/STL/tool leaves and libraries; not a complete transitive toolchain closure",
                source_compile_scope="Own reviewed bridge and seven public declarations; no fetched project implementation",
                header_scope="New recognition-enabled metadata-only header embeds retained CPU/GGUF/pack descriptors; compilation and runtime/payload access separately gated",
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
    need(config["kind"] == "recognition_bridge_v1_build_runtime_unqualified"
         and config["helper"] == frozen.pin(__file__) and config["source"] == frozen.pin(SOURCE)
         and config["design"] == frozen.pin(DESIGN) and config["limits"] == LIMITS
         and config["recognition_enabled"] is True and config["expected_version"] == "0.7.0-dev"
         and config["runtime_execution_authorized"] is False and config["CPU_GGUF_payload_access_authorized"] is False
         and config["module_policy_route"] == "trusted_System32_recognition_pre_post_CPU"
         and type(config["reported_platform_path_filesystem_operations"]) is int and config["reported_platform_path_filesystem_operations"] == 0
         and config["platform_image_authentication"] == "not_established"
         and config["platform_source_proof"] == frozen.pin(CHILD_PROOF) and config["policy_contract"] == frozen.pin(DESIGN)
         and config["shared_vectors"] == frozen.pin(VECTORS) and config["pure_matcher"] == frozen.pin(MATCHER)
         and config["pure_matcher_proof"] == frozen.pin(MATCHER_PROOF)
         and config["root_policy_decision"] == frozen.pin(ROOT_POLICY) and config["execution_contract"] == frozen.pin(EXECUTION_CONTRACT)
         and config["header_descriptor"] == frozen.pin(DESCRIPTOR) and config["descriptor_proof"] == frozen.pin(DESCRIPTOR_PROOF)
         and config["wire"] == frozen.pin(WIRE) and config["pack_metadata"] == frozen.pin(PACK_METADATA)
         and config["ABI_acceptance"] == frozen.pin(ABI_ACCEPTANCE) and config["build_preparation_decision"] == frozen.pin(BUILD_PREP_DECISION)
         and config["module_policy_id"] == POLICY_ID and config["module_policy_sha256"] == POLICY_SHA
         and config["exception_header"] == frozen.pin(EXCEPTION_HEADER)
         and config["execute_result"] is False and config["header"]["sha256"] == HEADER_SHA,
         "Exact recognition-enabled compile-only/runtime-unqualified scope changed")
    need(config["commands"] == commands(frozen, prepared, output, old)
         and config["environment"] == frozen.build_environment(old["environment"], output), "Commands/environment changed")
    validate_input_roles(config["inputs"], frozen, old, prepared)
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
                      recognition_enabled=True, expected_version="0.7.0-dev", runtime_execution_authorized=False, CPU_GGUF_payload_access_authorized=False, global_environment_unchanged=True)
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
