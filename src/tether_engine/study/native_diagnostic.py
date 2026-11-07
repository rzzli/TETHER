"""Fixed R07 exposed/synthetic technical diagnostic, never a scientific acceptance.

Preparation is offline. Execution uses only an explicitly frozen local asset set,
one owned server and six declared once-only cells. No retry or response repair.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import http.client
import json
import math
from pathlib import Path
import re
import time

from tether_engine.agents import Usage
from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import (
    ContractError,
    canonical,
    decode,
    encode,
    fingerprint,
    freeze,
    parse_json,
    safe_child,
)
from tether_engine.workflow import Budget, add_usage

from .diagnostic import REQUIRED_RESOURCES, prepare_payload, request_from_payload
from .native import (
    LocalBackend,
    NativeVerifier,
    bounded_health_probe,
    windows_listener_owner,
)
from .process import OwnedServer, ServerSpec
from .proofs import capture_file, capture_package_proof, verify_package_proof
from .session import StudySession, inspect_study, need, verify_study

CASE_IDS = ("exposed-il6r-genetics", "synthetic-orientation", "synthetic-context")
INTERFACES = ("current", "simplified")
ALIAS = "tether-r07-native-diagnostic"
RESOURCES = {name: "study/" + name for name in REQUIRED_RESOURCES}


def pin(path):
    path = Path(path).absolute()
    proof = capture_file(path, "data-file")
    return dict(path=str(path), sha256=proof["sha256"], bytes=proof["bytes"])


def _approved(path, roots):
    path = Path(path).absolute()
    need(
        any(path.resolve().is_relative_to(Path(root).resolve()) for root in roots),
        "Input outside caller-approved roots",
    )
    return path


def check(proof, roots):
    path = _approved(proof["path"], roots)
    need(pin(path) == encode(proof), "Frozen input bytes changed: " + str(path))
    return path


def document(proof, roots, limit=4 * 1024 * 1024):
    path = check(proof, roots)
    need(proof["bytes"] <= limit, "Input JSON exceeds diagnostic bound")
    raw = path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == proof["sha256"], "JSON changed during read")
    return parse_json(raw)


def put(path, value):
    publish_bytes(Path(path), canonical(value) + b"\n")


def _capture_package(output):
    proof = capture_package_proof(RESOURCES, REQUIRED_RESOURCES)
    package = Path(__file__).resolve().parents[1]
    copies = []
    for item in proof["code"]:
        relative = Path(item["logical_id"]).relative_to("tether_engine")
        target = output / "executing-package" / relative
        publish_bytes(target, (package / relative).read_bytes())
        captured = pin(target)
        need(
            captured["sha256"] == item["sha256"] and captured["bytes"] == item["bytes"],
            "Copied package code differs",
        )
        copies.append(captured)
    for item in proof["resources"].values():
        relative = item["relative_path"]
        target = output / "executing-package" / relative
        publish_bytes(target, (package / relative).read_bytes())
        captured = pin(target)
        need(
            captured["sha256"] == item["proof"]["sha256"]
            and captured["bytes"] == item["proof"]["bytes"],
            "Copied package resource differs",
        )
        copies.append(captured)
    verify_package_proof(proof, required_resources=REQUIRED_RESOURCES)
    return proof, copies


def _launch(inventory, port):
    assets = inventory["assets"]
    servers = [a for a in assets if Path(a["path"]).name == "llama-server.exe"]
    weights = sorted(
        [a for a in assets if a["path"].endswith(".gguf")],
        key=lambda item: item["path"],
    )
    need(
        len(servers) == 1
        and len(weights) == 3
        and type(port) is int
        and 1 <= port <= 65535,
        "Pinned server/shard set or port is incomplete",
    )
    server = {key: servers[0][key] for key in ("path", "sha256", "bytes")}
    argv = [
        server["path"],
        "--model",
        weights[0]["path"],
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--ctx-size",
        "16384",
        "--parallel",
        "1",
        "--n-gpu-layers",
        "99",
        "--threads",
        "8",
        "--alias",
        ALIAS,
        "--no-webui",
        "--offline",
        "-lv",
        "4",
    ]
    return server, weights, argv


def prepare(
    output,
    *,
    r05_path,
    inventory_path,
    source_gate_path,
    compiler_archive_path,
    approved_roots,
    port=55591,
):
    """Copy exact prepared inputs and freeze all launch/code/source identities."""
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    journal = RunJournal(output / "preparation", kind="build")
    try:
        need(
            type(port) is int and 1 <= port <= 65535 and approved_roots,
            "Invalid explicit port/roots",
        )
        r05_pin, inventory_pin = pin(r05_path), pin(inventory_path)
        gate_pin, compiler_pin = pin(source_gate_path), pin(compiler_archive_path)
        r05, inventory = (
            document(r05_pin, approved_roots),
            document(inventory_pin, approved_roots),
        )
        gate, compiler = (
            document(gate_pin, approved_roots),
            document(compiler_pin, approved_roots),
        )
        need(
            gate["status"] == "passed"
            and gate["all_six_payloads_unchanged"] is True
            and gate["evaluator_answers_read"]
            is gate["clinical_outcome_contents_read"]
            is False,
            "Source gate is not qualified",
        )
        need(
            compiler["source_gate"] == gate_pin
            and compiler["archived_code_executed"] is False
            and len(compiler["files"]) == len(gate["source_compiler_code_proofs"]),
            "Compiler data archive differs",
        )
        originals = {p["path"]: p for p in gate["source_compiler_code_proofs"]}
        compiler_copies = []
        need(
            originals and len(originals) == len(gate["source_compiler_code_proofs"]),
            "Missing compiler code proofs",
        )
        need(
            {m["original"]["path"] for m in compiler["files"]} == set(originals),
            "Compiler code inventory incomplete",
        )
        for index, member in enumerate(compiler["files"]):
            need(
                member["original"] == originals[member["original"]["path"]]
                and member["archive"]["sha256"] == member["original"]["sha256"],
                "Compiler code bytes differ",
            )
            target = output / "source-compiler-data" / f"{index:03}.py"
            publish_bytes(target, check(member["archive"], approved_roots).read_bytes())
            copied = pin(target)
            need(
                copied["sha256"] == member["original"]["sha256"],
                "Archived compiler copy differs",
            )
            compiler_copies.append(copied)
        for proof in gate["authoritative_input_proofs"]:
            check(proof, approved_roots)
        assets = inventory["assets"]
        for item in assets:
            check(
                {key: item[key] for key in ("path", "sha256", "bytes")}, approved_roots
            )
        server, weights, argv = _launch(inventory, port)
        cells = []
        need(
            [case["case_id"] for case in r05["cases"]] == list(CASE_IDS),
            "Diagnostic case pack changed",
        )
        for case in r05["cases"]:
            need(len(case["arms"]) == 2, "Prepared case must declare exactly two arms")
            request = document(case["request"], approved_roots)
            if case["case_id"] == CASE_IDS[0]:
                need(
                    fingerprint(request)
                    == gate["expected_request_sha256"]
                    == gate["request_sha256"],
                    "Real source request differs",
                )
            case_reservation = Usage(0, 0, 0.0)
            for interface, arm in zip(INTERFACES, case["arms"]):
                payload = document(arm["http_payload"], approved_roots)
                need(
                    fingerprint(prepare_payload(request, interface))
                    == fingerprint(payload)
                    and fingerprint(request_from_payload(payload, interface))
                    == fingerprint(request),
                    "Prepared payload/source differs",
                )
                cell_id = case["case_id"] + "-" + interface
                folder = output / "inputs" / cell_id
                publish_bytes(
                    folder / "request.json",
                    check(case["request"], approved_roots).read_bytes(),
                )
                publish_bytes(
                    folder / "payload.json",
                    check(arm["http_payload"], approved_roots).read_bytes(),
                )
                quote = Usage(len(payload["prompt"].encode()) + 32, 2048, 0.0)
                case_reservation = add_usage(case_reservation, quote)
                cells.append(
                    dict(
                        cell_id=cell_id,
                        case_id=case["case_id"],
                        interface=interface,
                        request=pin(folder / "request.json"),
                        payload=pin(folder / "payload.json"),
                        quote=encode(quote),
                        source_kind=case["basis"],
                    )
                )
            need(
                case_reservation.input_tokens <= 32000
                and case_reservation.output_tokens <= 8000,
                "Shared case reservation exceeded",
            )
        package_proof, package_copies = _capture_package(output)
        plan = dict(
            schema_version=1,
            kind="r07_native_technical_plan",
            root=str(output),
            port=port,
            r05=r05_pin,
            inventory=inventory_pin,
            source_gate=gate_pin,
            compiler_archive=compiler_pin,
            source_inputs=gate["authoritative_input_proofs"],
            assets=[{k: a[k] for k in ("path", "sha256", "bytes")} for a in assets],
            server=server,
            argv=argv,
            alias=ALIAS,
            cells=cells,
            package_proof=encode(package_proof),
            package_archive=package_copies,
            compiler_data_archive=compiler_copies,
            model_provenance=dict(
                weights_sha256={Path(a["path"]).name: a["sha256"] for a in weights},
                runtime_sha256=server["sha256"],
                asset_manifest_sha256=inventory_pin["sha256"],
            ),
            max_calls=6,
            seconds_per_cell=150,
            seconds_per_case=300,
            seconds_total=1200,
            response_original_byte_cap=524288,
            automatic_retries=False,
            provider_spend_usd=0,
            fresh_holdout=False,
            human_scientific_review="pending",
            capacity_comparison="unavailable_stronger_control",
            generation_failure_policy="continue predeclared cells after contract/transport failure; stop on storage, ownership, interruption or global budget failure",
        )
        put(output / "run-plan.json", plan)
        journal.append("build_completed", plan=pin(output / "run-plan.json"))
        return pin(output / "run-plan.json")
    except BaseException as error:
        journal.fail(error, "native_diagnostic_preparation")
        put(
            output / "preparation-failure.json",
            dict(error_class=type(error).__name__, model_calls=0),
        )
        raise
    finally:
        journal.close()


def _validate(plan, roots):
    need(
        plan["kind"] == "r07_native_technical_plan"
        and plan["schema_version"] == 1
        and plan["max_calls"] == 6
        and plan["seconds_per_cell"] == 150
        and plan["seconds_per_case"] == 300
        and plan["seconds_total"] == 1200
        and plan["automatic_retries"] is False
        and plan["provider_spend_usd"] == 0,
        "Frozen native diagnostic policy differs",
    )
    need(
        [(c["case_id"], c["interface"]) for c in plan["cells"]]
        == [(case, interface) for case in CASE_IDS for interface in INTERFACES],
        "Fixed cell order differs",
    )
    verify_package_proof(plan["package_proof"], required_resources=REQUIRED_RESOURCES)
    for proof in (
        [plan[k] for k in ("r05", "inventory", "source_gate", "compiler_archive")]
        + plan["source_inputs"]
        + plan["assets"]
    ):
        check(proof, roots)
    gate = document(plan["source_gate"], roots)
    need(
        gate["status"] == "passed"
        and gate["evaluator_answers_read"] is False
        and gate["clinical_outcome_contents_read"] is False
        and plan["source_inputs"] == gate["authoritative_input_proofs"],
        "Source proof inventory differs",
    )
    inventory = document(plan["inventory"], roots)
    assets = [
        {k: a[k] for k in ("path", "sha256", "bytes")} for a in inventory["assets"]
    ]
    server, weights, argv = _launch(inventory, plan["port"])
    need(
        plan["assets"] == assets
        and plan["server"] == server
        and plan["argv"] == argv
        and plan["alias"] == ALIAS,
        "Launch assets/arguments differ from pinned inventory",
    )
    need(
        plan["model_provenance"]
        == dict(
            weights_sha256={Path(a["path"]).name: a["sha256"] for a in weights},
            runtime_sha256=server["sha256"],
            asset_manifest_sha256=plan["inventory"]["sha256"],
        ),
        "Declared model provenance differs",
    )
    for proof in plan["package_archive"] + plan["compiler_data_archive"]:
        check(proof, roots)
    output = Path(plan["root"])
    package_expected = []
    for member in plan["package_proof"]["code"]:
        path = (
            output
            / "executing-package"
            / Path(member["logical_id"]).relative_to("tether_engine")
        )
        package_expected.append(
            dict(path=str(path), sha256=member["sha256"], bytes=member["bytes"])
        )
    for member in plan["package_proof"]["resources"].values():
        path = output / "executing-package" / member["relative_path"]
        package_expected.append(
            dict(
                path=str(path),
                sha256=member["proof"]["sha256"],
                bytes=member["proof"]["bytes"],
            )
        )
    need(
        plan["package_archive"] == package_expected,
        "Complete archived package proof differs",
    )
    compiler = document(plan["compiler_archive"], roots)
    need(
        compiler["source_gate"] == plan["source_gate"]
        and compiler["archived_code_executed"] is False,
        "Compiler archive source binding differs",
    )
    compiler_expected = [
        dict(
            path=str(output / "source-compiler-data" / f"{index:03}.py"),
            sha256=member["original"]["sha256"],
            bytes=member["original"]["bytes"],
        )
        for index, member in enumerate(compiler["files"])
    ]
    need(
        plan["compiler_data_archive"] == compiler_expected,
        "Complete archived compiler proof differs",
    )
    r05 = document(plan["r05"], roots)
    expected = [
        (case, interface, arm)
        for case in r05["cases"]
        for interface, arm in zip(INTERFACES, case["arms"])
    ]
    need(len(expected) == len(plan["cells"]) == 6, "Prepared input inventory differs")
    for cell, (case, interface, arm) in zip(plan["cells"], expected):
        request, payload = (
            document(cell["request"], roots),
            document(cell["payload"], roots),
        )
        need(
            cell["cell_id"] == case["case_id"] + "-" + interface
            and cell["source_kind"] == case["basis"]
            and cell["request"]["sha256"]
            == case["request"]["sha256"]
            == fingerprint(request)
            and cell["payload"]["sha256"]
            == arm["http_payload"]["sha256"]
            == fingerprint(payload),
            "Prepared source/payload bindings differ",
        )
        need(
            fingerprint(prepare_payload(request, cell["interface"]))
            == fingerprint(payload),
            "Frozen cell payload differs",
        )
        need(
            cell["quote"]
            == encode(Usage(len(payload["prompt"].encode()) + 32, 2048, 0.0)),
            "Frozen reservation differs",
        )


def _memory(owner):
    """Observed owned-process peak working set, never GPU memory attribution."""

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ]

    try:
        counter = Counters()
        counter.cb = ctypes.sizeof(counter)
        fn = ctypes.windll.psapi.GetProcessMemoryInfo
        fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
        fn.restype = ctypes.c_int
        need(
            fn(int(owner._process._handle), ctypes.byref(counter), counter.cb) != 0,
            "Memory observation unavailable",
        )
        return dict(
            peak_working_set_bytes=counter.PeakWorkingSetSize,
            gpu_memory_bytes=None,
            gpu_reason="Not attributed by process memory API",
        )
    except Exception as error:
        return dict(
            peak_working_set_bytes=None,
            reason=type(error).__name__,
            gpu_memory_bytes=None,
        )


def execute(plan_path, expected_sha256, approved_roots):
    plan_proof = pin(plan_path)
    need(plan_proof["sha256"] == expected_sha256, "Wrong external plan anchor")
    plan = document(plan_proof, approved_roots)
    output = Path(plan["root"])
    need(Path(plan_path).resolve() == output / "run-plan.json", "Moved diagnostic plan")
    journal = RunJournal(output / "execution", kind="build")
    started = time.monotonic()
    results = [
        dict(
            cell_id=c["cell_id"],
            case_id=c["case_id"],
            interface=c["interface"],
            status="undispatched",
        )
        for c in plan["cells"]
    ]
    owner, primary = None, None
    try:
        _validate(plan, approved_roots)
        asset_proofs = [
            dict(logical_id=f"asset-{i}", sha256=a["sha256"], bytes=a["bytes"])
            for i, a in enumerate(plan["assets"])
        ]
        bindings = {
            p["logical_id"]: Path(a["path"])
            for p, a in zip(asset_proofs, plan["assets"])
        }
        server_index = next(
            i
            for i, a in enumerate(plan["assets"])
            if a["path"] == plan["server"]["path"]
        )
        spec = ServerSpec(
            tuple(plan["argv"]),
            asset_proofs[server_index],
            tuple(p for i, p in enumerate(asset_proofs) if i != server_index),
            "127.0.0.1",
            plan["port"],
            180,
            30,
            10,
        )
        owner = OwnedServer(
            spec,
            bindings=bindings,
            output=output,
            journal=journal,
            listener_owner=windows_listener_owner,
            health_probe=bounded_health_probe,
        )
        with owner:
            startup = (output / "server.stderr.log").read_text(
                encoding="utf-8", errors="replace"
            )
            need(
                re.search(r"n_slots\s*=\s*1,\s*n_ctx_slot\s*=\s*16384", startup)
                is not None,
                "Actual single-slot context not qualified from owned startup",
            )
            journal.append(
                "native_context_qualified",
                context=16384,
                slots=1,
                memory=_memory(owner),
            )
            case_started = {}
            case_usage = {}
            case_calls = {}
            for cell, result in zip(plan["cells"], results):
                case_start = case_started.setdefault(cell["case_id"], time.monotonic())
                remaining = min(
                    150.0,
                    300 - (time.monotonic() - case_start),
                    1200 - (time.monotonic() - started),
                )
                need(remaining > 0, "Diagnostic aggregate wall budget exhausted")
                used = case_usage.get(cell["case_id"], Usage(0, 0, 0.0))
                next_total = add_usage(used, decode(Usage, cell["quote"]))
                need(
                    next_total.input_tokens <= 32000
                    and next_total.output_tokens <= 8000
                    and case_calls.get(cell["case_id"], 0) < 2,
                    "Shared case usage cannot admit next cell",
                )
                owner.assert_ready()
                request, payload = (
                    document(cell["request"], approved_roots),
                    document(cell["payload"], approved_roots),
                )
                folder = output / "cells" / cell["cell_id"]
                verifier = NativeVerifier(cell["interface"], plan["alias"])
                budget = Budget(
                    max_calls=1,
                    max_input_tokens=cell["quote"]["input_tokens"],
                    max_output_tokens=2048,
                    max_cost_usd=0.0,
                    max_seconds=remaining,
                    max_retries=0,
                )
                error = None
                cell_started = time.monotonic()
                try:
                    with StudySession(
                        folder,
                        budget=budget,
                        configuration=dict(
                            plan_sha256=expected_sha256,
                            cell_id=cell["cell_id"],
                            source_kind=cell["source_kind"],
                            human_review="pending",
                        ),
                        resources=RESOURCES,
                        required_resources=REQUIRED_RESOURCES,
                    ) as session:
                        backend = LocalBackend(
                            f"http://127.0.0.1:{plan['port']}",
                            cell["interface"],
                            plan["model_provenance"],
                            plan["alias"],
                            owner,
                            folder,
                        )
                        session.call_once(
                            request=request,
                            payload=payload,
                            backend=backend,
                            verifier=verifier,
                        )
                        session.finish()
                    proof = pin(folder / "receipt.json")
                    verify_study(
                        folder,
                        expected_receipt_sha256=proof["sha256"],
                        verifier=verifier,
                    )
                    result.update(
                        status="contract_verified_not_scientific_validation",
                        receipt=proof,
                    )
                except BaseException as issue:
                    error = issue
                    result.update(status="failed", error_class=type(issue).__name__)
                if (folder / "journal.jsonl").is_file():
                    result["inspection"] = encode(inspect_study(folder))
                    usage = add_usage(
                        decode(Usage, result["inspection"]["measured_usage"]),
                        decode(Usage, result["inspection"]["estimated_usage"]),
                    )
                    case_usage[cell["case_id"]] = add_usage(used, usage)
                    case_calls[cell["case_id"]] = (
                        case_calls.get(cell["case_id"], 0)
                        + result["inspection"]["calls"]
                    )
                result["memory"] = _memory(owner)
                result["elapsed_seconds"] = time.monotonic() - cell_started
                journal.append("native_cell_terminal", **result)
                print(
                    json.dumps(
                        dict(
                            cell_id=cell["cell_id"],
                            status=result["status"],
                            calls=result.get("inspection", {}).get("calls", 0),
                        )
                    ),
                    flush=True,
                )
                used_now = case_usage.get(cell["case_id"], Usage(0, 0, 0.0))
                need(
                    used_now.input_tokens <= 32000
                    and used_now.output_tokens <= 8000
                    and case_calls.get(cell["case_id"], 0) <= 2,
                    "Actual shared case usage exceeded its ceiling",
                )
                if error is not None and not isinstance(
                    error,
                    (
                        ConnectionError,
                        TimeoutError,
                        ContractError,
                        http.client.HTTPException,
                    ),
                ):
                    # OSError is not generally recoverable: storage failures must
                    # not trigger another generation under a transport label.
                    raise error
        for proof in plan["source_inputs"]:
            check(proof, approved_roots)
    except BaseException as error:
        primary = error
        try:
            journal.fail(error, "native_diagnostic_execution")
        except BaseException as secondary:
            primary.add_note("Parent failure journal: " + type(secondary).__name__)
    finally:
        terminal = (
            encode(owner.terminal_record)
            if owner is not None
            else dict(started=False, server_stopped=None)
        )
        if primary is None and (
            terminal.get("server_stopped") is not True
            or time.monotonic() - started >= 1200
        ):
            primary = RuntimeError("Owned termination or total deadline not qualified")
        for result in results:
            if result["status"] == "undispatched":
                result["reason"] = "No dispatch after " + (
                    type(primary).__name__ if primary else "terminal boundary"
                )
        report = dict(
            schema_version=1,
            kind="r07_native_technical_report",
            plan=plan_proof,
            cells=results,
            status="technical_terminal_pending_human_review"
            if primary is None
            else "incomplete_execution",
            error_class=type(primary).__name__ if primary else None,
            server=terminal,
            elapsed_seconds=time.monotonic() - started,
            provider_spend_usd=0,
            human_scientific_review="pending",
            scientific_acceptance="not_established",
            features={},
            clinical_probability=None,
        )
        terminal_error = None
        try:
            put(output / "execution-report.json", report)
            journal.append(
                "native_diagnostic_terminal",
                report=pin(output / "execution-report.json"),
            )
        except BaseException as issue:
            terminal_error = issue
        try:
            journal.close()
        except BaseException as issue:
            if terminal_error is None:
                terminal_error = issue
            else:
                terminal_error.add_note("Journal close: " + type(issue).__name__)
        if terminal_error is None:
            try:
                files = {
                    p.relative_to(output).as_posix(): pin(p)
                    for p in sorted(output.rglob("*"))
                    if p.is_file()
                }
                put(
                    output / "terminal-seal.json",
                    dict(
                        schema_version=1,
                        kind="r07_technical_terminal_seal",
                        plan=plan_proof,
                        files=files,
                        human_scientific_review="pending",
                        qualification="Byte/mechanical record, not scientific acceptance",
                    ),
                )
            except BaseException as issue:
                terminal_error = issue
        if terminal_error is not None:
            if primary is not None:
                primary.add_note("Terminal storage: " + type(terminal_error).__name__)
            else:
                primary = terminal_error
            try:
                put(
                    output / "terminal-storage-failure.json",
                    dict(
                        error_class=type(primary).__name__,
                        secondary_error_class=type(terminal_error).__name__,
                        success_seal=False,
                    ),
                )
            except BaseException as issue:
                primary.add_note("Failure snapshot: " + type(issue).__name__)
            raise primary
    return pin(output / "terminal-seal.json")


def verify(output, expected_sha256, approved_roots):
    output = Path(output).resolve()
    seal_proof = pin(output / "terminal-seal.json")
    need(seal_proof["sha256"] == expected_sha256, "Wrong external terminal anchor")
    seal = document(seal_proof, approved_roots, limit=8 * 1024 * 1024)
    need(
        type(seal.get("schema_version")) is int
        and seal["schema_version"] == 1
        and seal.get("kind") == "r07_technical_terminal_seal"
        and seal.get("human_scientific_review") == "pending",
        "Unsupported terminal seal",
    )
    actual_files = {
        p.relative_to(output).as_posix()
        for p in output.rglob("*")
        if p.is_file() and p.name != "terminal-seal.json"
    }
    need(
        set(seal.get("files", {})) == actual_files
        and {
            "run-plan.json",
            "preparation/journal.jsonl",
            "execution/journal.jsonl",
            "execution-report.json",
        }
        <= actual_files,
        "Incomplete parent file inventory",
    )
    for relative, proof in seal["files"].items():
        need(
            safe_child(output, relative) == Path(proof["path"]).resolve(),
            "Sealed member outside diagnostic",
        )
        check(proof, approved_roots)
    plan, report = (
        document(seal["plan"], approved_roots),
        document(pin(output / "execution-report.json"), approved_roots),
    )
    need(
        seal["plan"] == pin(output / "run-plan.json")
        and plan["root"] == str(output)
        and report.get("plan") == seal["plan"],
        "Parent plan identity differs",
    )
    need(
        type(report.get("schema_version")) is int
        and report["schema_version"] == 1
        and report.get("kind") == "r07_native_technical_report"
        and report.get("status")
        in ("technical_terminal_pending_human_review", "incomplete_execution")
        and report.get("scientific_acceptance") == "not_established"
        and report.get("provider_spend_usd") == 0,
        "Unsupported parent report scope",
    )
    need(
        type(report.get("elapsed_seconds")) in (int, float)
        and math.isfinite(report["elapsed_seconds"])
        and report["elapsed_seconds"] >= 0,
        "Invalid parent elapsed time",
    )
    _validate(plan, approved_roots)
    events = read_chain(output / "execution/journal.jsonl")
    need(
        events[-1]["event"] == "native_diagnostic_terminal"
        and events[-1]["details"]["report"] == pin(output / "execution-report.json"),
        "Terminal report differs",
    )
    need(
        [r["cell_id"] for r in report["cells"]]
        == [c["cell_id"] for c in plan["cells"]],
        "Cell denominators differ",
    )
    calls = 0
    cell_events = [e["details"] for e in events if e["event"] == "native_cell_terminal"]
    expected_events = [
        {k: v for k, v in result.items() if k != "reason"}
        for result in report["cells"]
        if result["status"] != "undispatched"
    ]
    need(
        fingerprint(cell_events) == fingerprint(expected_events),
        "Parent cell journal differs from report",
    )
    server_events = [e["details"] for e in events if e["event"] == "server_terminal"]
    need(
        len(server_events) <= 1
        and (
            fingerprint(server_events[0]) == fingerprint(report["server"])
            if server_events
            else report["server"].get("started") is False
        ),
        "Owned terminal record differs",
    )
    if report["status"] == "technical_terminal_pending_human_review":
        started_events = [
            e["details"] for e in events if e["event"] == "server_started"
        ]
        ready_events = [e["details"] for e in events if e["event"] == "server_ready"]
        context_events = [e for e in events if e["event"] == "native_context_qualified"]
        need(
            report["server"].get("started") is True
            and report["server"].get("server_stopped") is True
            and report["error_class"] is None
            and report["elapsed_seconds"] < 1200
            and len(started_events) == len(ready_events) == len(context_events) == 1
            and len(cell_events) == 6
            and all(c["status"] != "undispatched" for c in report["cells"])
            and started_events[0]["pid"]
            == ready_events[0]["pid"]
            == report["server"].get("pid"),
            "Qualified technical terminal has no owned stop/budget proof",
        )
    for cell, result in zip(plan["cells"], report["cells"]):
        folder = output / "cells" / cell["cell_id"]
        need(
            result["case_id"] == cell["case_id"]
            and result["interface"] == cell["interface"]
            and result["status"]
            in (
                "undispatched",
                "failed",
                "contract_verified_not_scientific_validation",
            ),
            "Cell identity/status differs",
        )
        if result["status"] == "undispatched":
            need(
                not (folder / "journal.jsonl").exists(),
                "Undispatched cell has execution",
            )
            continue
        inspected = inspect_study(folder)
        need(encode(inspected) == result["inspection"], "Cell accounting differs")
        calls += inspected["calls"]
        if result["status"] == "failed":
            need(
                inspected["status"] == "failed_or_incomplete"
                and not (folder / "receipt.json").exists(),
                "Failed cell has a success receipt",
            )
        if inspected["calls"]:
            config = document(pin(folder / "configuration.json"), approved_roots)
            need(
                config["caller_configuration"]["plan_sha256"] == seal["plan"]["sha256"]
                and config["caller_configuration"]["cell_id"] == cell["cell_id"]
                and config["adapter_provenance"]["owner_pid"]
                == report["server"].get("pid")
                and config["adapter_provenance"]["endpoint"]
                == f"http://127.0.0.1:{plan['port']}",
                "Cell launch ownership/parent binding differs",
            )
        if result["status"] == "contract_verified_not_scientific_validation":
            verify_study(
                folder,
                expected_receipt_sha256=result["receipt"]["sha256"],
                verifier=NativeVerifier(cell["interface"], plan["alias"]),
            )
    need(
        calls <= 6
        and report["features"] == {}
        and report["clinical_probability"] is None
        and report["human_scientific_review"] == "pending",
        "Technical/scientific scope differs",
    )
    return freeze(
        dict(
            status="verified_r07_technical_terminal",
            cell_dispatch_reservations=calls,
            planned_cells=6,
            scientific_acceptance="not_established",
            human_scientific_review="pending",
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--output", required=True, type=Path)
    for name in ("r05", "inventory", "source-gate", "compiler-archive"):
        prep.add_argument("--" + name, required=True, type=Path)
    prep.add_argument("--port", type=int, default=55591)
    for name in ("execute", "verify"):
        sub = commands.add_parser(name)
        sub.add_argument("--path", required=True, type=Path)
        sub.add_argument("--sha256", required=True)
    for sub in commands.choices.values():
        sub.add_argument("--approved-root", action="append", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(
            args.output,
            r05_path=args.r05,
            inventory_path=args.inventory,
            source_gate_path=args.source_gate,
            compiler_archive_path=args.compiler_archive,
            approved_roots=args.approved_root,
            port=args.port,
        )
    elif args.command == "execute":
        result = execute(args.path, args.sha256, args.approved_root)
    else:
        result = verify(args.path, args.sha256, args.approved_root)
    print(json.dumps(encode(result), indent=2))


if __name__ == "__main__":
    main()
