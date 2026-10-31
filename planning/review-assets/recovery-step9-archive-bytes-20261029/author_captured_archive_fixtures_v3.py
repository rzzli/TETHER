"""Author literal source-shaped byte graphs; no archive checker or live reads.

Only this new review directory's contract/framing files are read. All run paths,
software/payload declarations and runtime observations below are invented data.
"""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "CAPTURED-NATIVE-ARCHIVE-CONTRACT-v3.json"
CONTRACT_FREEZE = HERE / "CAPTURED-NATIVE-ARCHIVE-CONTRACT-FREEZE-v3.json"
FRAMING = HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FRAMING-v1.json"
TARGET = HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json"
FREEZE = HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FREEZE-v3.json"
ROOT = r"D:\synthetic\run"
TECH = r"D:\synthetic\technical"
RUNTIME = r"D:\synthetic\runtime"
POLICY = "trusted-System32-recognition-v1"
POLICY_SHA = "4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713"
STATUS = "recognition_observations_retained_independent_qualification_pending"
OWNER = 1234
STAMP = "2026-10-29T00:00:00.000001+00:00"


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def document(value):
    return canonical(value) + b"\n"


def raw_pin(path, raw):
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def declared(path, label):
    # Authored descriptor-only leaf: there is deliberately no original content.
    return dict(path=path, bytes=17, sha256=hashlib.sha256(label.encode("ascii")).hexdigest())


def absolute(locator):
    return ROOT + "\\" + locator.replace("/", "\\")


def map_bytes(files):
    return {key: {field: value for field, value in raw_pin(absolute(key), raw).items() if field != "path"}
            for key, raw in sorted(files.items())}


def journal_row(sequence, event, details, previous=None):
    row = dict(sequence=sequence, event=event, details=details, previous_sha256=previous)
    row["sha256"] = hashlib.sha256(canonical(row)).hexdigest()
    return row


def metadata(fault=None):
    names = dict(executable=TECH + r"\recognizer.exe", verified_build=TECH + r"\build-proof.json",
                 source=TECH + r"\child.cpp", compiled_source_copy=TECH + r"\copied-child.cpp",
                 runtime_pin_header=TECH + r"\pins.hpp", execution_contract=TECH + r"\contract.json",
                 expected_pack_metadata=TECH + r"\pack-metadata.json")
    static = [declared(path, key) for key, path in names.items()]
    static += [declared(RUNTIME + "\\" + name, name) for name in ("libomp.dll", "ggml-base.dll", "ggml.dll", "llama.dll")]
    by_path = {row["path"]: row for row in static}
    by_path[names["execution_contract"]]["sha256"] = "30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861"
    by_path[names["compiled_source_copy"]]["sha256"] = by_path[names["source"]]["sha256"]
    payloads = [declared(RUNTIME + r"\ggml-cpu-x64.dll", "CPU")]
    payloads += [declared(r"D:\synthetic\payload\part" + str(index) + ".gguf", "model" + str(index)) for index in (1, 2, 3)]
    payloads += [declared(r"D:\synthetic\payload\recognition.pack", "pack")]
    helper = declared(TECH + r"\parent.py", "parent")
    authority_path = TECH + r"\authority.json"
    dynamic_tail = [declared(TECH + r"\binding-checker.py", "checker"), declared(TECH + r"\binding-proof.json", "proof")]
    authority = dict(schema_version=1, status="verified_build_software_and_descriptor_basis_not_execution_permission",
        mode="--recognize", execution_authorized=False, runtime_qualified=False,
        **{key: by_path[path] for key, path in names.items()}, module_policy_id=POLICY, module_policy_sha256=POLICY_SHA,
        software_inputs=copy.deepcopy(static), payload_descriptors=copy.deepcopy(payloads),
        closure_scope="Synthetic finite descriptor-only fixture; no original source authority.",
        dynamic_dependencies=["current_parent", "current_authority", "current_binding_checker", "current_binding_proof"])
    if fault == "static_dynamic_collision":
        authority["software_inputs"].append(copy.deepcopy(helper))
    authority_raw = document(authority)
    authority_pin = raw_pin(authority_path, authority_raw)
    dynamics = [helper, authority_pin, *dynamic_tail]
    software = copy.deepcopy(static + dynamics)
    limits = dict(parent_seconds=300, child_seconds=120, child_cleanup_reserved_seconds=2,
                  finalization_reserved_seconds=5, process_and_job_commit_bytes=268435456,
                  active_processes=1, maximum_children=1, stream_bytes=65536,
                  maximum_job_snapshots=40, job_pid_capacity=16, attempt_bytes=4096,
                  result_bytes=8388608, row_bytes=65536)
    argv = [names["executable"], "--recognize", RUNTIME, ROOT + r"\execution\child", payloads[4]["path"],
            "ggml-cpu-x64.dll", *[row["path"] for row in payloads[1:4]]]
    if fault and fault.startswith("argv_"):
        index = int(fault.split("_")[1]); argv[index] = "--abi" if index == 1 else r"D:\synthetic\wrong"
    config = dict(schema_version=1, kind="detached_singleton_recognition_observation_v1", mode="--recognize",
        helper=copy.deepcopy(helper), executable=copy.deepcopy(by_path[names["executable"]]),
        software_inputs=software, payload_inputs=copy.deepcopy(payloads), inputs=copy.deepcopy(software + payloads),
        output=ROOT, argv=argv, command_line=" ".join(argv),
        environment=dict(SystemRoot=r"C:\Windows", WINDIR=r"C:\Windows", SystemDrive="C:",
                         PATH=r"C:\Windows\System32", TEMP=ROOT, TMP=ROOT, OMP_NUM_THREADS="1", OMP_THREAD_LIMIT="1"),
        limits=limits, creation_flags=0x0008040C, maximum_attempts=1, automatic_retry=False,
        module_policy_id=POLICY, module_policy_sha256=POLICY_SHA, expected_version="0.7.0-dev",
        expected_pack_sha256=payloads[4]["sha256"], contract_sha256="30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861",
        parent_seconds=300, child_seconds=120, cooperative_work_ms=117000, full_vocabulary_mask=False, inference=False,
        scientific_validation="not_established", execution_authorized_by_preparation=False,
        hash_pass_policy=dict(driver_model_passes=0, parent_initial=1, child=1, parent_final=1, external_verifier_separately_timed=True),
        periodic_job_seconds=3.5, original_SDK_general_gate=False)
    if fault == "bool_descriptor_bytes": config["inputs"][0]["bytes"] = True
    protocol_raw = document(config)
    protocol_pin = raw_pin(TECH + r"\protocol.json", protocol_raw)
    bindings = dict(policy_id="captured-native-recognition-v7-archive-v1", run_root=ROOT,
        protocol_pin=protocol_pin, authority_pin=authority_pin, helper_pin=copy.deepcopy(helper),
        static_software_pins=copy.deepcopy(static),
        dynamic_pins=[dict(role=role, pin=copy.deepcopy(row)) for role, row in zip(authority["dynamic_dependencies"], dynamics)],
        payload_descriptors=copy.deepcopy(payloads))
    return config, protocol_raw, authority_raw, bindings


def graph(branch="positive", fault=None):
    config, protocol, authority, bindings = metadata(fault)
    primary = (dict(error_class="OSError", error="synthetic constructor stop") if branch == "early_initialization"
               else dict(error_class="RuntimeError", error="synthetic retained negative"))
    negative_early = branch in ("child_negative", "retry_after_close_failure", "early_initialization", "malformed_root_marker")
    early_status = "failed" if negative_early else STATUS
    reservation = dict(owner_pid=OWNER, created_at_utc=STAMP, status="reserved_before_journal_or_native_API")
    if fault == "reservation_owner": reservation["owner_pid"] += 1
    first = journal_row(0, "build_reserved" if fault != "wrong_first_kind" else "run_reserved",
                        dict(run_id="12345678-1234-4234-8234-123456789abc", owner_pid=OWNER, created_at_utc=STAMP))
    header = dict(protocol_sha256=bindings["protocol_pin"]["sha256"], limits=copy.deepcopy(config["limits"]))
    if fault == "second_header_limits": header["limits"]["active_processes"] = True
    second = journal_row(1, "detached_recognition_attempt_reserved", header, first["sha256"])
    report = dict(schema_version=1, status=early_status, automatic_retry=False,
                  call_return_observed=branch != "early_initialization", returncode=2 if negative_early else 0,
                  reaped=branch != "early_initialization", finalization_errors=[])
    if negative_early: report["failure"] = copy.deepcopy(primary)
    if branch == "early_initialization":
        report.pop("returncode")
        report.pop("reaped")
    files = {"parent-reservation.json": document(reservation), "effective-protocol.json": protocol,
             "execution/journal.jsonl": document(first) + document(second), "stdout.bin": b"", "stderr.bin": b""}
    files["execution/child/attempt.json"] = b'{"schema_version":1,"mode":"--recognize","status":"claimed_before_native_load","draft":true}\n'
    if branch in ("child_negative", "malformed_root_marker"):
        files["execution/child/failure.json"] = document(dict(schema_version=1, status="failed", message="synthetic child negative"))
        files["execution/child/result.partial.jsonl"] = b'{"event":"synthetic_partial_only"}\n'
    else:
        files["execution/child/result.jsonl"] = b'{"event":"synthetic_opaque_result_not_semantic_success"}\n'
    if branch == "child_final_conflict":
        files["execution/child/failure.json"] = b'{"schema_version":1,"status":"failed"}\n'
    if negative_early:
        files["failure.json"] = document(dict(authoritative=True, automatic_retry=False, **primary))
    if branch == "malformed_root_marker":
        files["failure.json"] = b'{"authoritative":false,"authoritative":true}\n'
    if branch == "early_initialization":
        files = {key: value for key, value in files.items() if key in ("parent-reservation.json", "failure.json")}
        files["failure.json"] = document(dict(authoritative=True, automatic_retry=False,
            phase="parent_reservation_or_journal_initialization", error_class="OSError", error="synthetic constructor stop"))
    if fault == "root_journal_locator": files["journal.jsonl"] = files.pop("execution/journal.jsonl")
    if fault == "missing_parent_reservation": files.pop("parent-reservation.json")
    if fault == "traversal_locator": files["../result.jsonl"] = files.pop("execution/child/result.jsonl")
    files["parent-report.json"] = document(report)
    receipt = dict(schema_version=1, status=early_status, outputs=map_bytes(files),
                   protocol_sha256=bindings["protocol_pin"]["sha256"],
                   failure_veto="Every authoritative failure marker or missing/failed terminal seal vetoes")
    if fault == "receipt_future_edge":
        receipt["outputs"]["post-lease-cleanup.json"] = dict(bytes=17, sha256="0" * 64)
    files["receipt.json"] = document(receipt)
    failure = copy.deepcopy(primary) if negative_early else None
    sealer_earlier_status = early_status
    if branch == "publication_after_receipt":
        failure = dict(phase="terminal_publication", error_class="TimeoutError", error="synthetic post-receipt stop")
        sealer_earlier_status = "failed"
        files["failure.json"] = document(dict(authoritative=True, automatic_retry=False, **failure))
        files["terminal-publication-error.json"] = document(dict(authoritative=True, automatic_retry=False,
            publication_error=failure, primary_failure=failure, finalization_errors=[failure]))
    prior_errors = [dict(phase="final_input_recheck_close", error_class="OSError", error="synthetic first close failure")] if branch == "retry_after_close_failure" else []
    outcome = dict(path=bindings["static_software_pins"][0]["path"], handle=41, validation="passed",
        closed_before=False, prior_cleanup_errors=prior_errors, primary_validation_error=None,
        close_attempted=True, close_return_observed=True, close_success=True, close_error=None, closed_after=True)
    close_errors = []
    if branch == "normal_late":
        error = dict(error_class="OSError", error="synthetic current close failure")
        outcome.update(close_return_observed=False, close_success=False, close_error=error, closed_after=False)
        close_errors = [dict(path=outcome["path"], handle=41, **error)]
    root_marker = raw_pin(absolute("failure.json"), files["failure.json"]) if "failure.json" in files else None
    receipt_pin = raw_pin(absolute("receipt.json"), files["receipt.json"])
    cleanup = dict(schema_version=1, status="failed" if close_errors else "close_outcomes_retained",
        earlier_status=sealer_earlier_status, primary_failure=failure, primary_failure_marker=root_marker,
        earlier_receipt=receipt_pin, parent_elapsed_after_leases_seconds=1.25, parent_deadline_exceeded=False,
        close_errors=close_errors, outcomes=[] if branch == "early_initialization" else [outcome])
    files["post-lease-cleanup.json"] = document(cleanup)
    cleanup_pin = raw_pin(absolute("post-lease-cleanup.json"), files["post-lease-cleanup.json"])
    if branch == "normal_late":
        files["late-failure.json"] = document(dict(schema_version=1, authoritative=True, automatic_retry=False,
            phase="post_receipt_lease_cleanup", error_class="LeaseCleanupOrParentDeadline", primary_failure=failure,
            primary_failure_marker=root_marker, cleanup_artifact=cleanup_pin, close_errors=close_errors,
            parent_deadline_exceeded=False))
    failed = bool(failure or root_marker or branch == "normal_late")
    terminal = dict(schema_version=1, status="failed" if failed else STATUS, required=True,
        earlier_receipt=receipt_pin, cleanup_artifact=cleanup_pin, primary_failure_marker=root_marker,
        late_failure_marker=raw_pin(absolute("late-failure.json"), files["late-failure.json"]) if "late-failure.json" in files else None,
        outputs=map_bytes(files), parent_elapsed_before_terminal_seal_seconds=1.5,
        failure_veto="failure.json, late-failure.json or after-seal-failure.json override any seal; missing terminal-seal.json is incomplete")
    if fault == "cross_root_pin": terminal["cleanup_artifact"]["path"] = r"D:\other\post-lease-cleanup.json"
    if fault == "terminal_self_edge": terminal["outputs"]["terminal-seal.json"] = dict(bytes=17, sha256="0" * 64)
    files["terminal-seal.json"] = document(terminal)
    if branch == "after_seal":
        files["after-seal-failure.json"] = document(dict(authoritative=True, automatic_retry=False,
            error_class="ParentDeadlineAfterTerminalSeal", terminal_seal=raw_pin(absolute("terminal-seal.json"), files["terminal-seal.json"])))
    if branch == "exception_after_terminal":
        files["late-failure.json"] = document(dict(authoritative=True, automatic_retry=False,
            phase="post_lease_cleanup_or_terminal_sealing", error_class="OSError", error="synthetic after-seal publication failure",
            primary_failure=failure, primary_failure_marker=root_marker, close_outcomes=[outcome]))
    if branch == "missing_terminal": files.pop("terminal-seal.json")
    if fault == "digest_corruption": files["stdout.bin"] = b"later captured byte differing from old maps"
    return dict(protocol_hex=protocol.hex(), authority_hex=authority.hex(),
                run_files=[dict(locator=key, raw_hex=value.hex()) for key, value in sorted(files.items())]), bindings


def expectation(graph_status="consistent_captured_graph", disposition="source_positive_observations_pending"):
    return dict(captured_graph_status=graph_status, source_terminal_disposition=disposition,
                profile_qualified=False, originals_authenticated=False, actual_directory_complete=False, source_qualified=False)


def main():
    assert not TARGET.exists() and not FREEZE.exists()
    frozen = json.loads(CONTRACT_FREEZE.read_bytes())
    assert frozen["contract"]["sha256"] == hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    cases = []
    def add(identity, purpose, branch="positive", fault=None, status="consistent_captured_graph", disposition="source_positive_observations_pending"):
        captured, bindings = graph(branch, fault)
        cases.append(dict(id=identity, purpose=purpose, captured=captured, bindings=bindings,
                          expected_projection=expectation(status, disposition)))
    add("complete_positive_captured_graph", "Source-shaped local graph only; opaque child bytes establish no profile success.")
    for branch in ("child_negative", "publication_after_receipt", "after_seal", "retry_after_close_failure", "normal_late"):
        add(branch, "Consistent negative graph retains distinct source phase/marker semantics.", branch=branch, disposition="source_negative")
    add("exception_after_terminal", "Post-terminal exception supplement absent from older map, negative/incomplete.",
        branch="exception_after_terminal", status="incomplete_captured_graph", disposition="source_negative")
    add("missing_terminal", "Early receipt/cleanup cannot replace a missing terminal.", branch="missing_terminal",
        status="incomplete_captured_graph", disposition="unresolved")
    add("early_initialization", "Negative receipt/seal cannot manufacture missing journal/protocol or launched child.",
        branch="early_initialization", status="incomplete_captured_graph", disposition="source_negative")
    for fault in ("root_journal_locator", "traversal_locator", "cross_root_pin", "terminal_self_edge", "receipt_future_edge", "digest_corruption",
                  "bool_descriptor_bytes", "static_dynamic_collision", "reservation_owner", "wrong_first_kind", "second_header_limits"):
        add(fault, "Bounded authored inner format/reference attack; graph is not accepted by a positive status.", fault=fault,
            status="inconsistent_captured_graph", disposition="unresolved")
    add("missing_parent_reservation", "Missing source reservation cannot be defaulted to a known owner.", fault="missing_parent_reservation",
        status="incomplete_captured_graph", disposition="unresolved")
    add("malformed_root_marker", "Duplicate-key marker veto is determined by filename even when document parse fails.",
        branch="malformed_root_marker", status="inconsistent_captured_graph", disposition="source_negative")
    add("child_final_conflict", "Child failure marker coexists with dishonest finalized result/positive parent label.",
        branch="child_final_conflict", status="inconsistent_captured_graph", disposition="source_negative")
    for index in range(9):
        add("argv_" + str(index), "Exact authored mutation of one of all nine argv derivations; protocol bytes/pins remain coherent.",
            fault="argv_" + str(index), status="inconsistent_captured_graph", disposition="unresolved")
    assert len(cases) == 32
    root = dict(schema_version=1, status="literal_actual_format_synthetic_captures_before_archive_checker",
        contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(), framing_sha256=hashlib.sha256(FRAMING.read_bytes()).hexdigest(),
        cases=cases, actual_old_runs_replayed=0, originals_opened=0, SDK_OS_native_calls=0,
        source_checker_implemented=False, profile_qualified=False,
        payload_and_source_paths="Invented descriptor strings only; no corresponding bytes/files read or created.")
    raw = document(root)
    with TARGET.open("xb") as out: out.write(raw)
    record = dict(schema_version=1, status="literal_archive_fixtures_frozen_before_checker_implementation",
        contract=raw_pin(str(CONTRACT), CONTRACT.read_bytes()), contract_freeze=raw_pin(str(CONTRACT_FREEZE), CONTRACT_FREEZE.read_bytes()),
        framing=raw_pin(str(FRAMING), FRAMING.read_bytes()), author=raw_pin(str(Path(__file__).resolve()), Path(__file__).read_bytes()),
        fixtures=raw_pin(str(TARGET), raw), counts=dict(cases=len(cases), argv_derivations=9,
            maximum_run_files=max(len(item["captured"]["run_files"]) for item in cases)),
        predecessor_fixtures=raw_pin(str(HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v2.json"), (HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v2.json").read_bytes()),
        independent_fixture_findings=raw_pin(str(HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-PEER-FINDINGS-v2.json"), (HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-PEER-FINDINGS-v2.json").read_bytes()),
        fixture_finding=raw_pin(str(HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FINDING-v1.json"), (HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FINDING-v1.json").read_bytes()),
        checker_implemented=False, checker_authorized=False, old_run_replay=0, SDK_native_payload_operations=0)
    with FREEZE.open("xb") as out: out.write(document(record))
    print(json.dumps(dict(status=record["status"], fixtures_sha256=record["fixtures"]["sha256"],
                          bytes=len(raw), counts=record["counts"])))


if __name__ == "__main__":
    main()
