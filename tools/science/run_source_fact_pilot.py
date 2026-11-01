"""Prospectively pinned P04 source-reporting pilot; no implicit execution.

The generation phase receives only authenticated source packets. Evaluator values
are opened only after generation has ended and the owned server has been stopped.
This controller deliberately does not inherit any native-v2 qualification path.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from contextlib import ExitStack
import hashlib
from importlib import metadata
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import urllib.request

from asof.contracts import Snapshot
from asof.journal import RunJournal, read_chain
from asof.provenance import InputGraph, catalog_index
from asof.serde import ContractError, canonical, decode, encode, fingerprint, freeze, parse_json
from asof.study.process import OwnedServer, ServerSpec
from asof.study.source_fact_cell import ARMS, run_reporting_cell
from asof.study.source_fact_evaluation import TERMINALS, aggregate_cells, score_cell
from asof.study.source_fact_reporting import reporting_view
from asof.study.source_fact_sources import verify_reference
from asof.study.source_fact_transport import (
    MAX_NETSTAT_BYTES, TypedReportingClient, parse_netstat_listener,
)
from asof.study.stable_read import checked_path, read_file, stable_files
from asof.workflow import Budget


ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = Path(r"E:\projects_data\drug_target_agents_data")
GENERATION_ROOT = ROOT / "data/derived/preprint-p04-inputs-20261101T043317717926Z"
REFERENCE_ROOT = ROOT / "data/benchmark/gold_evidence/preprint-p04-references-20261101T044012853811Z"
OUTPUT_PARENT = ROOT / "runs"
CONDITIONS = ("cd276-clean", "osmr-clean", "cd276-controlled-missing")
ASSETS = "planning/review-assets/preprint-p04-20261031/"
PINNED_COMPONENTS = {
    "model": "dfba9f924a01d7ff8b7ab7845b481af482e29d0dbed9eb280bc3bb142598342e",
    "server": "2143076f29b6af862d138ea1a605919ab0eefb91c39f9b8d4f282ce76662b8e3",
    "scheduled_cells": "3c00d34a3d84adde467c847812337b686b5063ccef6f5872e14026ee58e0ca0b",
    "budgets_per_arm_cell": "97793c3be999701cb3af8c753ca57a2ad62bf3cc50c2753efb5123ac7935285c",
}
MANIFEST_PINS = {
    "generation_manifest": ("GENERATION-INPUTS-v1.json", "c7c2fdf706b8f96759816e618f35cee8f6926d49ee6fae95d1fe75981aa766f1", 3274),
    "reference_manifest": ("REFERENCES-v1.json", "32321dab80f05c51cf482adeac8e51e54bb14903066589d3f9806b795774ddad", 9143),
    "input_plan": ("DEVELOPMENT-INPUT-PLAN-v4.json", "815f23b10f15bb6e68967aaed05e532c35b286160c5f89f65b9105a98b10b761", 5742),
}
SEALS = {
    "generation_seal_sha256": "b4aa4bd2fa27f9489f13ff9a2c71f34d89dda4400b097a3c1279114f7222767e",
    "reference_seal_sha256": "6487625483b5bb06ed6338aeedbf893bcc6b4525affdae14f19f1dd8725a4612",
}
HASH = re.compile(r"[0-9a-f]{64}\Z")
ZERO = dict(input_tokens=0, output_tokens=0, cost_usd=0.0)


def need(condition, message):
    if not condition:
        raise ContractError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_bytes(path, raw):
    """Exclusive durable publication; never replace a previous run's evidence."""
    need(type(raw) is bytes, "Exact byte publication required")
    path = Path(path)
    with path.open("xb", buffering=0) as stream:
        remaining = memoryview(raw)
        while remaining:
            written = stream.write(remaining)
            if not written:
                raise OSError("Pilot evidence write failed")
            remaining = remaining[written:]
        os.fsync(stream.fileno())
    return dict(sha256=digest(raw), bytes=len(raw))


def capture_environment():
    """Runtime facts for independent prospective freezing, without network IO."""
    return dict(python_executable=str(Path(sys.executable).resolve()),
                python_version=platform.python_version(),
                python_implementation=platform.python_implementation(),
                platform=platform.platform(),
                dependencies={name: metadata.version(name)
                              for name in ("asof-target-agents", "pyarrow")})


def code_inventory():
    paths = list((ROOT / "src/asof").rglob("*.py"))
    paths.extend(ROOT / name for name in (
        "tools/science/run_source_fact_pilot.py",
        ASSETS + "prepare_generation_inputs.py", ASSETS + "prepare_references.py"))
    return tuple(sorted(path.relative_to(ROOT).as_posix() for path in paths))


def validate_protocol(raw, expected_sha256):
    """Validate authority and literal prospective bounds before any reservation."""
    need(type(expected_sha256) is str and HASH.fullmatch(expected_sha256),
         "An independent protocol SHA-256 is required")
    need(type(raw) is bytes and digest(raw) == expected_sha256, "Protocol hash differs")
    protocol = parse_json(raw)
    need(isinstance(protocol, Mapping) and protocol.get("status") == "READY",
         "Only an independently frozen READY protocol is executable; DRAFT is denied")
    need(type(protocol.get("schema_version")) is int and protocol["schema_version"] == 1
         and protocol.get("development_only") is True
         and protocol.get("study_id") == "preprint-p04-typed-report-postvalidation-v1",
         "Unknown development protocol")
    for key, pin in PINNED_COMPONENTS.items():
        need(fingerprint(protocol.get(key)) == pin, "Frozen protocol component differs: " + key)
    need(len(protocol["scheduled_cells"]) == 12
         and {cell["arm"] for cell in protocol["scheduled_cells"]} == set(ARMS),
         "The complete twelve-cell schedule is required")
    for key, (name, pin, size) in MANIFEST_PINS.items():
        proof = protocol.get(key)
        need(isinstance(proof, Mapping) and set(proof) == {"path", "sha256", "bytes"}
             and proof["path"].replace("\\", "/") == ASSETS + name
             and proof["sha256"] == pin and proof["bytes"] == size,
             "Independent manifest pin differs: " + key)
    need(all(protocol.get(key) == pin for key, pin in SEALS.items()), "Seal pin differs")
    expected_roots = dict(workspace=str(ROOT), approved_raw_root=str(RAW_ROOT),
                          generation=str(GENERATION_ROOT), reference=str(REFERENCE_ROOT),
                          output_parent=str(OUTPUT_PARENT))
    need(protocol.get("roots") == expected_roots, "Explicit approved roots differ")
    need(all(type(protocol.get(key)) is int and protocol[key] == value for key, value in (
             ("evaluation_seconds", 3600), ("maximum_output_tokens_per_call", 2048),
             ("maximum_prompt_bytes", 14304), ("seed", 0))),
         "Literal execution caps differ")
    for phase in ("source", "reference"):
        for suffix in ("journal_sha256", "journal_terminal_sha256"):
            need(type(protocol.get(phase + "_" + suffix)) is str
                 and HASH.fullmatch(protocol[phase + "_" + suffix]),
                 "Independent terminal-journal pins required")
    code = protocol.get("code_bundle")
    need(isinstance(code, Mapping) and set(code) == set(code_inventory()),
         "Complete executing code inventory required")
    for proof in code.values():
        need(isinstance(proof, Mapping) and set(proof) == {"sha256", "bytes"}
             and type(proof["bytes"]) is int and 0 <= proof["bytes"] <= 2 * 1024 * 1024
             and type(proof["sha256"]) is str and HASH.fullmatch(proof["sha256"]),
             "Invalid code pin")
    need(isinstance(protocol.get("environment"), Mapping), "Frozen environment required")
    return freeze(protocol)


def _verified_bytes(path, proof, deadline, maximum=4 * 1024 * 1024):
    raw = read_file(path, deadline, maximum)
    need(len(raw) == proof["bytes"] and digest(raw) == proof["sha256"], "Pinned input bytes differ")
    return raw


def _verify_code_environment(protocol, output, deadline):
    need(capture_environment() == dict(protocol["environment"]), "Executing environment differs")
    need(protocol["environment"]["dependencies"]["pyarrow"] == "21.0.0",
         "Reference replay requires pinned Arrow 21.0.0")
    archive = output / "code"
    archive.mkdir()
    for name, proof in protocol["code_bundle"].items():
        source = checked_path(ROOT, name)
        raw = _verified_bytes(source, proof, deadline, 2 * 1024 * 1024)
        destination = archive / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_bytes(destination, raw)
    write_bytes(output / "environment.json", canonical(capture_environment()))


def _terminal_seal(root, protocol, phase, seal_pin, deadline):
    with stable_files((root / "SEAL.json", root / "journal.jsonl"), deadline=deadline):
        raw = read_file(root / "SEAL.json", deadline, 1024 * 1024)
        need(digest(raw) == seal_pin, "Preparation seal hash differs")
        seal = parse_json(raw)
        journal_raw = read_file(root / "journal.jsonl", deadline, 4 * 1024 * 1024)
        need(digest(journal_raw) == protocol[phase + "_journal_sha256"], "Preparation journal hash differs")
        events = read_chain(root / "journal.jsonl")
    need(events[0]["event"] == "build_reserved" and events[-1]["event"] == "build_completed"
         and not any(e["event"] in ("build_failed", "build_interrupted") for e in events)
         and events[-1]["sha256"] == protocol[phase + "_journal_terminal_sha256"]
         and events[-1]["details"]["seal_sha256"] == seal_pin,
         "Preparation journal is not the independently pinned successful terminal chain")
    need(seal.get("model_calls") == 0, "Preparation unexpectedly generated model output")
    return seal, raw, journal_raw


def _admit_source_packets(packets, tasks, manifest, plan, inventory, catalog):
    """Check the whole original ancestry, then the pure generation projection."""
    need(inventory.get("role") == "agent_evidence" and inventory.get("agent_visible") is True
         and inventory.get("reference_inputs") == [] and inventory.get("plan_sha256") == manifest["plan_sha256"],
         "Evaluator or unsupported source inventory denied")
    snapshot = decode(Snapshot, inventory["source_snapshot"])
    need(snapshot.raw_root == str(RAW_ROOT) and snapshot.profile == "contemporary_assessment"
         and not snapshot.artifacts and snapshot.allow_reconstructed is False
         and inventory["source_snapshot"]["origin_at"] == manifest["cutoff"],
         "Original snapshot scope differs")
    nodes = {node.source_id: node for node in snapshot.sources}
    proofs = {proof["source_id"]: proof for proof in inventory["inventory_proofs"]}
    need(len(nodes) == len(snapshot.sources) == len(proofs) == 111 and set(nodes) == set(proofs),
         "Complete original 111-node inventory required")
    need(sum(proof["bytes"] for proof in proofs.values()) == manifest["inventory"]["source_bytes"] == 8216226905,
         "Original byte inventory differs")
    for key, node in nodes.items():
        need(node.role in ("agent_evidence", "reference") and node.computed_at is None and not node.parents
             and node.dataset_id in ("ot_evidence", "ot_target", "hgnc_symbols")
             and node.receipt_path and node.receipt_sha256,
             "Derived or evaluator-only source ancestor denied")
        for field in ("sha256", "dataset_id", "release_id", "path", "receipt_path", "receipt_sha256"):
            need(encode(getattr(node, field)) == proofs[key][field], "Original source proof differs")
    graph = InputGraph(snapshot, ROOT, catalog_index(catalog))
    from types import SimpleNamespace
    need(graph.exclusion(tuple(nodes), SimpleNamespace(cutoff=snapshot.origin_at)) is None,
         "Original inventory is not temporally eligible")
    parents = [dict(kind="eligible_original", source_id=key, sha256=nodes[key].sha256) for key in sorted(nodes)]
    parents.append(dict(kind="neutral_input_plan", sha256=manifest["plan_sha256"]))
    for condition in CONDITIONS:
        packet, task = packets[condition], tasks[condition]
        view = reporting_view(packet)
        need(packet["condition_id"] == condition and canonical(packet["neutral_task"]) == canonical(task)
             and fingerprint(task) == manifest["conditions"][condition]["task_sha256"]
             and canonical(packet["lineage"]["parents"]) == canonical(parents)
             and packet["lineage"]["generation_authority"] is False
             and task["cutoff"] == manifest["cutoff"] and task["scope"]["tissue"] is None
             and canonical(task["primary_families"]) == canonical(plan["source_policy"]["primary_families"]),
             "Source packet, neutral task or original-only lineage differs")
        need(all(canonical(node) == canonical(encode(nodes[node["source_id"]]))
                 for node in packet["source_nodes"]), "Packet original metadata differs")
        need(len(view["fact_skeleton"]) == manifest["conditions"][condition]["fact_slots"],
             "Value-free binding inventory differs")
    return snapshot


def _admit_inputs(protocol, output, deadline):
    manifests, raw_manifests = {}, {}
    for key in MANIFEST_PINS:
        proof = protocol[key]
        raw = _verified_bytes(checked_path(ROOT, proof["path"].replace("\\", "/")), proof, deadline)
        raw_manifests[key], manifests[key] = raw, parse_json(raw)
        write_bytes(output / (key + ".json"), raw)
    generation, reference, plan = (manifests[key] for key in MANIFEST_PINS)
    need(generation["status"] == "sealed_source_inputs" and generation["role"] == "agent_evidence"
         and generation["agent_visible"] is True and not generation["blocked_cases"]
         and generation["reference_inputs"] == [] and generation["evaluator_artifacts_read"] is False
         and generation["generation_authority"] is False and generation["model_calls"] == 0
         and generation["original_value_output"].replace("\\", "/") == GENERATION_ROOT.relative_to(ROOT).as_posix(),
         "Source-only generation manifest denied")
    need(reference["status"] == "sealed_source_only_references" and reference["role"] == "evaluation_only"
         and reference["agent_visible"] is False
         and reference["output"].replace("\\", "/") == REFERENCE_ROOT.relative_to(ROOT).as_posix()
         and reference["pins"]["approved_raw_root"] == str(RAW_ROOT), "Reference metadata boundary differs")
    seal, seal_raw, source_journal = _terminal_seal(GENERATION_ROOT, protocol, "source",
                                                  protocol["generation_seal_sha256"], deadline)
    ref_seal, ref_raw, ref_journal = _terminal_seal(REFERENCE_ROOT, protocol, "reference",
                                                  protocol["reference_seal_sha256"], deadline)
    need(seal["phase"] == "generation_inputs_sealed_before_evaluator_reference_creation"
         and seal["reference_inputs"] == [] and seal["generation_authority"] is False
         and seal["plan_sha256"] == protocol["input_plan"]["sha256"], "Source seal boundary differs")
    need(ref_seal["phase"] == "source_only_evaluator_references_sealed_before_model_calls"
         and ref_seal["role"] == "evaluation_only" and ref_seal["agent_visible"] is False
         and ref_seal["generation_seal_sha256"] == protocol["generation_seal_sha256"]
         and ref_seal["reference_count"] == 3 and ref_seal["source_inclusive_replays_per_reference"] == 1,
         "Reference preparation seal differs")
    expected = {condition + suffix for condition in CONDITIONS for suffix in (".packet.json", ".task.json")}
    expected |= {"source-inventory.json", "preparation-summary.json"}
    need(set(seal["files"]) == expected, "Exact eight-file generation seal required")
    payloads, archive = {}, output / "generation-inputs"
    archive.mkdir()
    for name, proof in seal["files"].items():
        raw = _verified_bytes(checked_path(GENERATION_ROOT, name), proof, deadline)
        payloads[name] = parse_json(raw)
        write_bytes(archive / name, raw)
    for name, raw in (("source-SEAL.json", seal_raw), ("reference-SEAL.json", ref_raw),
                      ("source-journal.jsonl", source_journal), ("reference-journal.jsonl", ref_journal)):
        write_bytes(output / name, raw)
    summary = payloads["preparation-summary.json"]
    need(summary["evaluator_artifacts_read"] is False and summary["reference_inputs"] == []
         and summary["blocked_cases"] == {}, "Source preparation boundary differs")
    catalog_path = ROOT / "data/catalog/sources.json"
    catalog_raw = read_file(catalog_path, deadline, 4 * 1024 * 1024)
    need(digest(catalog_raw) == generation["catalog_sha256"] == reference["pins"]["catalog_sha256"]
         == plan["source_policy"]["catalog_sha256"], "Original catalog pin differs")
    write_bytes(output / "generation-catalog.json", catalog_raw)
    tasks = {condition: payloads[condition + ".task.json"] for condition in CONDITIONS}
    packets = {condition: payloads[condition + ".packet.json"] for condition in CONDITIONS}
    _admit_source_packets(packets, tasks, generation, plan, payloads["source-inventory.json"], parse_json(catalog_raw))
    for cell in protocol["scheduled_cells"]:
        need(cell["task_sha256"] == generation["conditions"][cell["condition"]]["task_sha256"]
             == reference["conditions"][cell["condition"]]["task_sha256"]
             and cell["reference_sha256"] == reference["conditions"][cell["condition"]]["reference_sha256"],
             "Scheduled source/reference binding differs")
    # Evaluator member payloads have not been opened or hashed at this point.
    return freeze(dict(packets=packets, tasks=tasks, generation=generation, reference=reference,
                       reference_seal=ref_seal, preparation=summary))


def _server_spec(protocol):
    model, config = protocol["model"], protocol["server"]
    asset_root = Path(model["asset_root"])
    proofs, bindings = [], {}
    for item in model["weights"]:
        logical = "weights/" + item["name"]
        proofs.append(dict(logical_id=logical, sha256=item["sha256"], bytes=item["bytes"]))
        bindings[logical] = asset_root / item["name"]
    for item in model["runtime_files"]:
        logical = item["path"].replace("\\", "/")
        proofs.append(dict(logical_id=logical, sha256=item["sha256"], bytes=item["bytes"]))
        bindings[logical] = asset_root / logical
    need(len(proofs) == 55 and len(bindings) == 55, "Exactly three weights and 52 runtime inputs required")
    executable = next(proof for proof in proofs if proof["logical_id"] == "runtime/llama-server.exe")
    argv = (str(bindings[executable["logical_id"]]), "--model", str(bindings[proofs[0]["logical_id"]]),
            "--host", config["host"], "--port", str(config["port"]),
            "--ctx-size", str(config["context_tokens"]), "--parallel", str(config["parallel"]),
            "--n-gpu-layers", str(config["gpu_layers"]), "--threads", str(config["threads"]),
            "--alias", config["alias"], "--no-webui")
    spec = ServerSpec(argv, executable, tuple(proof for proof in proofs if proof is not executable),
                      config["host"], config["port"], config["startup_seconds"],
                      config["terminate_seconds"], config["kill_seconds"])
    return spec, bindings


class _RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ContractError("Owned health redirects are forbidden")


class ListenerEvidence:
    """Explicit bounded netstat evidence, checked with the retained live handle."""
    def __init__(self, output, journal, setup_deadline):
        self.output, self.journal, self.setup_deadline = output, journal, setup_deadline
        self.process = None
        self.ready = False
        self.count = 0
        self.output.mkdir()

    def _setup_bound(self):
        if not self.ready and time.monotonic() >= self.setup_deadline:
            raise TimeoutError("Separate asset/server setup budget exhausted")

    def owner(self, pid, host, port):
        self._setup_bound()
        need(self.process is not None and self.process.pid == pid and self.process.poll() is None,
             "Retained owned process is not live")
        need(host == "127.0.0.1" and port == 55591 and self.count < 8192,
             "Unexpected listener or ownership-evidence cap exceeded")
        self.count += 1
        try:
            result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True,
                                    timeout=2, check=False, shell=False,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
        except BaseException as error:
            try:
                partial = getattr(error, "stdout", None)
                partial = partial if type(partial) is bytes else b""
                proof = write_bytes(self.output / f"netstat-{self.count:04d}-failed.bin", partial[:65536])
                self.journal.append("listener_snapshot_failed", expected_pid=pid, host=host, port=port,
                                    error_class=type(error).__name__, partial_bytes=len(partial),
                                    partial_sha256=digest(partial), retained=proof, timeout_seconds=2)
            except BaseException as secondary:
                error.add_note("Secondary listener diagnostic retention failure: " + type(secondary).__name__)
            raise
        raw = result.stdout
        need(type(raw) is bytes and type(result.stderr) is bytes, "Netstat must return raw bytes")
        # Retain a bounded diagnostic prefix as well as full bounded-output hashes.
        name = f"netstat-{self.count:04d}.bin"
        retained = raw[:65536]
        proof = write_bytes(self.output / name, retained)
        self.journal.append("listener_snapshot", expected_pid=pid, host=host, port=port,
                            returncode=result.returncode, stdout_bytes=len(raw), stdout_sha256=digest(raw),
                            stderr_bytes=len(result.stderr), stderr_sha256=digest(result.stderr),
                            retained=dict(path="ownership/" + name, **proof), prefix_only=len(raw) > len(retained))
        need(result.returncode == 0 and len(raw) <= MAX_NETSTAT_BYTES and len(result.stderr) <= 65536,
             "Netstat failed or exceeded bounded capture")
        owner = parse_netstat_listener(raw, port)
        need(owner in (None, pid), "Listener belongs to another process")
        if self.ready:
            need(owner == pid, "Owned listener disappeared")
        return owner == pid

    def health(self, host, port, timeout):
        self._setup_bound()
        need(host == "127.0.0.1" and port == 55591 and self.process is not None,
             "Explicit owned health endpoint required")
        if self.owner(self.process.pid, host, port) is not True:
            return False
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _RejectRedirect())
        url = f"http://127.0.0.1:{port}/health"
        with opener.open(urllib.request.Request(url, method="GET"), timeout=min(1, timeout)) as response:
            need(response.geturl() == url, "Owned health URL differs")
            raw = response.read(4097)
            need(type(raw) is bytes and len(raw) <= 4096, "Owned health body exceeds cap")
            self.journal.append("owned_health", status=response.status, body_bytes=len(raw), body_sha256=digest(raw))
            return response.status == 200 and parse_json(raw).get("status") == "ok"


def _evaluate(protocol, admitted, cells, output, journal):
    """The only phase that reads private evaluator member payloads."""
    started = time.monotonic()
    deadline = started + protocol["evaluation_seconds"]
    seal, manifest = admitted["reference_seal"], admitted["reference"]
    archive, payloads = output / "evaluation-only", {}
    archive.mkdir()
    for name, proof in seal["files"].items():
        need(proof["role"] == "evaluation_only" and proof["agent_visible"] is False,
             "Evaluator file exposure differs")
        raw = _verified_bytes(checked_path(REFERENCE_ROOT, name), proof, deadline, 8 * 1024 * 1024)
        payloads[name] = parse_json(raw)
        write_bytes(archive / name, raw)
    snapshot_doc = payloads["source-snapshot.json"]["source_snapshot"]
    need(fingerprint(snapshot_doc) == manifest["pins"]["source_snapshot_sha256"], "Evaluator snapshot pin differs")
    snapshot = decode(Snapshot, snapshot_doc)
    catalog_raw = (archive / "catalog-original.json").read_bytes()
    need(digest(catalog_raw) == manifest["pins"]["catalog_sha256"], "Evaluator original catalog differs")
    catalog = parse_json(catalog_raw)
    references = {}
    for condition in CONDITIONS:
        pin = manifest["conditions"][condition]
        document = payloads[pin["reference_path"]]
        phase_start = time.monotonic()
        references[condition] = verify_reference(document, pin["reference_sha256"], admitted["tasks"][condition],
                                                snapshot, ROOT, catalog, deadline=deadline, approved_raw_root=RAW_ROOT)
        journal.append("reference_replayed", condition=condition, reference_sha256=pin["reference_sha256"],
                       elapsed_seconds=time.monotonic() - phase_start, source_graph_nodes=111)
    scored = [score_cell(references[cell["condition"]], cells[cell["cell_id"]]["raw_final"],
                         cell_id=cell["cell_id"], terminal=cells[cell["cell_id"]]["terminal"])
              for cell in protocol["scheduled_cells"]]
    planned = [{key: cell[key] for key in ("cell_id", "task_id", "task_sha256", "reference_sha256")}
               for cell in protocol["scheduled_cells"]]
    aggregate = aggregate_cells(planned, scored)
    write_bytes(output / "scores.json", canonical(aggregate))
    return aggregate, dict(elapsed_seconds=time.monotonic() - started, cap_seconds=3600,
                           source_graph_nodes_per_replay=111, reference_replays=3,
                           estimated_logical_source_hash_bytes=2 * 3 * admitted["generation"]["inventory"]["source_bytes"],
                           physical_io_bytes=None, peak_native_rss_bytes=None)


def _message(error):
    return type(error).__name__ + ": " + str(error).encode("utf-8", "backslashreplace").decode("utf-8")[:240]


def _cell_from_journal(journal, cell_id, error):
    retained = getattr(error, "reporting_cell_result", None)
    if isinstance(retained, Mapping):
        result = dict(retained)
        result.update(terminal="interrupted" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "failed",
                      reason=_message(error))
        return result
    for event in reversed(journal.events):
        if event["event"] == "cell_terminal" and event["details"]["cell_id"] == cell_id:
            details = dict(event["details"])
            details["raw_final"] = None
            # A terminal write or cleanup failure must never become a completion.
            details["terminal"] = "interrupted" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "failed"
            details["reason"] = _message(error)
            return details
    measured, estimated, dispatched = dict(ZERO), dict(ZERO), 0
    for event in journal.events:
        details = event["details"]
        if event["event"] == "attempt_accounted" and details.get("cell_id") == cell_id:
            dispatched += details["dispatched"] is True
            total = measured if details["basis"] == "adapter_reported" else estimated
            for key in ZERO:
                total[key] += details["usage"][key]
    return dict(raw_final=None, terminal="interrupted" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "failed",
                reason=_message(error), dispatches=dispatched, measured_usage=measured, estimated_usage=estimated,
                stage_records=[], elapsed_seconds=None)


def run_pilot(protocol_path, protocol_sha256, output, *, execute=False,
              server_factory=OwnedServer, cell_runner=run_reporting_cell,
              client_class=TypedReportingClient):
    """Execute once; return a retained partial report after any bounded failure.

    Trusted Python injection is solely for fictional tests; protocol data cannot
    name callbacks or select archived executable code.
    """
    raw_protocol = Path(protocol_path).read_bytes()
    protocol = validate_protocol(raw_protocol, protocol_sha256)
    need(execute is True, "Execution requires the explicit --execute flag")
    output = Path(output).absolute()
    need(output.parent.resolve() == OUTPUT_PARENT.resolve() and output.name not in ("", ".", "..")
         and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", output.name),
         "Output must be a new direct child of the approved runs root")
    journal = RunJournal(output)
    code_locks = ExitStack()
    started, stage, errors, admitted, server = time.monotonic(), "reserve", [], None, None
    cells = {cell["cell_id"]: dict(raw_final=None, terminal="unexecuted", reason="Generation did not reach this planned cell",
              dispatches=0, measured_usage=dict(ZERO), estimated_usage=dict(ZERO), stage_records=[], elapsed_seconds=None)
             for cell in protocol["scheduled_cells"]}
    aggregate, evaluation_resources, server_record, generation_ended = None, None, None, False
    setup_resources = dict(cap_seconds=900, elapsed_seconds=None, native_peak_rss_bytes=None, physical_io_bytes=None)
    report = None
    try:
        journal.append("schedule_reserved", planned_cells=protocol["scheduled_cells"],
                       protocol_sha256=protocol_sha256, retry_policy="none")
        write_bytes(output / "protocol.json", raw_protocol)
        setup_start = time.monotonic()
        setup_deadline = setup_start + 900
        stage = "code_environment"
        code_locks.enter_context(stable_files(tuple(checked_path(ROOT, name) for name in protocol["code_bundle"]),
                                             deadline=started + 900 + 12 * 300 + 3600 + 40))
        _verify_code_environment(protocol, output, setup_deadline)
        stage = "source_admission"
        admitted = _admit_inputs(protocol, output, setup_deadline)
        journal.append("generation_inputs_frozen", source_seal_sha256=protocol["generation_seal_sha256"],
                       evaluator_payloads_opened=False, all_cells_reserved=12)

        def execute_cell(cell, client_factory):
            identifier = cell["cell_id"]
            try:
                result = cell_runner(admitted["packets"][cell["condition"]], cell["arm"], cell_id=identifier,
                                     output=output / identifier, journal=journal, client_factory=client_factory,
                                     budget=Budget(max_retries=0))
                need(result["terminal"] in TERMINALS, "Cell runner returned unknown terminal")
                cells[identifier] = dict(result)
            except BaseException as error:
                cells[identifier] = _cell_from_journal(journal, identifier, error)
                raise

        def no_client(*args):
            raise ContractError("Deterministic arm attempted model dispatch")

        stage = "deterministic_generation"
        for cell in protocol["scheduled_cells"][:6]:
            execute_cell(cell, no_client)
        stage = "owned_server_setup"
        spec, bindings = _server_spec(protocol)
        # Verify the pinned acquisition metadata, without adopting its old root.
        acquisition = _verified_bytes(checked_path(ROOT, protocol["model"]["acquisition"]["path"].replace("\\", "/")),
                                      protocol["model"]["acquisition"], setup_deadline)
        write_bytes(output / "model-acquisition.json", acquisition)
        evidence = ListenerEvidence(output / "ownership", journal, setup_deadline)

        def spawn(argv, **kwargs):
            evidence._setup_bound()
            process = subprocess.Popen(argv, **kwargs)
            evidence.process = process
            return process

        session_deadline = setup_deadline + 6 * 300 + 40
        with ExitStack() as stack:
            stack.enter_context(stable_files(tuple(bindings.values()), deadline=session_deadline))
            server = server_factory(spec, bindings=bindings, output=output, journal=journal,
                                    listener_owner=evidence.owner, health_probe=evidence.health,
                                    process_factory=spawn, parent_deadline=session_deadline)
            try:
                stack.enter_context(server)
                evidence._setup_bound()
                evidence.ready = True
                setup_resources["elapsed_seconds"] = time.monotonic() - setup_start
                stage = "model_generation"

                def fresh_client(stage_name, retain):
                    server.assert_ready()
                    process = evidence.process
                    need(process is not None and process.poll() is None, "Owned process handle missing")
                    return client_class(f"http://127.0.0.1:{spec.port}", expected_pid=process.pid,
                                        ownership_check=evidence.owner, retain=retain)

                for cell in protocol["scheduled_cells"][6:]:
                    execute_cell(cell, fresh_client)
            finally:
                # ExitStack owns server cleanup before evaluation can begin.
                pass
        server_record = server.terminal_record
    except BaseException as error:
        errors.append(dict(stage=stage, error=_message(error)))
        try:
            journal.fail(error, stage)
        except BaseException as secondary:
            errors.append(dict(stage="failure_journal", error=_message(secondary)))
    finally:
        generation_ended = True
        if server is not None:
            server_record = server.terminal_record
        if setup_resources["elapsed_seconds"] is None:
            setup_resources["elapsed_seconds"] = time.monotonic() - started
        try:
            journal.append("generation_ceased", evaluator_payloads_opened=False,
                           terminals={name: sum(cell["terminal"] == name for cell in cells.values()) for name in TERMINALS},
                           cells=[dict(cell_id=identifier, terminal=result["terminal"], reason=result["reason"],
                                       dispatches=result["dispatches"], measured_usage=result["measured_usage"],
                                       estimated_usage=result["estimated_usage"],
                                       raw_final_sha256=digest(result["raw_final"]) if result["raw_final"] is not None else None)
                                  for identifier, result in cells.items()])
        except BaseException as error:
            errors.append(dict(stage="generation_terminal_journal", error=_message(error)))

    # No dispatch path is reachable below this boundary, including after failure.
    cleanup_affirmed = (server_record is None or server_record.get("started") is False
                        or server_record.get("server_stopped") is True)
    if admitted is not None and generation_ended and cleanup_affirmed:
        try:
            aggregate, evaluation_resources = _evaluate(protocol, admitted, cells, output, journal)
        except BaseException as error:
            errors.append(dict(stage="source_verified_evaluation", error=_message(error)))
    elif admitted is not None and not cleanup_affirmed:
        errors.append(dict(stage="source_verified_evaluation",
                           error="Evaluator payloads remain closed because owned-server cleanup was not affirmed"))
    try:
        metadata_cells = []
        for cell in protocol["scheduled_cells"]:
            result = dict(cells[cell["cell_id"]])
            raw = result.pop("raw_final", None)
            result.update(cell_id=cell["cell_id"], condition=cell["condition"], arm=cell["arm"],
                          raw_final_sha256=digest(raw) if raw is not None else None,
                          raw_final_bytes=len(raw) if raw is not None else None)
            metadata_cells.append(result)
        measured, estimated = dict(ZERO), dict(ZERO)
        for cell in metadata_cells:
            for key in ZERO:
                measured[key] += cell["measured_usage"][key]
                estimated[key] += cell["estimated_usage"][key]
        # Completion means execution/retention/evaluation finished, not superiority.
        status = "completed" if not errors and aggregate is not None else "partial_or_failed"
        if all(cell["terminal"] in ("failed", "timeout", "interrupted", "unexecuted") for cell in metadata_cells):
            status = "partial_or_failed"
        report = dict(schema_version=1, study_id=protocol["study_id"], status=status,
                      protocol_sha256=protocol_sha256, planned_cells=12, cells=metadata_cells,
                      terminal_counts={name: sum(cell["terminal"] == name for cell in metadata_cells) for name in TERMINALS},
                      actual_calls=sum(cell["dispatches"] for cell in metadata_cells),
                      measured_usage=measured, estimated_upper_usage=estimated,
                      setup_resources=setup_resources, evaluation_resources=evaluation_resources,
                      all_cell_wall_seconds=time.monotonic() - started, server=server_record,
                      source_preparation=None if admitted is None else admitted["preparation"],
                      reference_preparation=None if admitted is None else admitted["reference"]["resources"],
                      scores=aggregate, errors=errors, final_probability_features=None,
                      scientific_validation="not_established", measurement_endpoint="not_studied",
                      interpretation="Exposed development source/reporting feasibility only; source fidelity is not biological validity.",
                      retry_policy="none", physical_io_bytes=None, peak_native_rss_bytes=None)
        proof = write_bytes(output / "report.json", canonical(report))
        text = ("P04 source/reporting pilot: " + status + "\n"
                + "Planned cells: 12; actual model calls: " + str(report["actual_calls"]) + "\n"
                + "Terminal counts: " + str(report["terminal_counts"]) + "\n"
                + "Source/reporting feasibility only; biological validity is not established.\n"
                + "\n".join(item["stage"] + ": " + item["error"] for item in errors) + "\n")
        write_bytes(output / "REPORT.txt", text.encode("utf-8"))
        journal.append("run_completed" if status == "completed" else "run_partial", report=proof,
                       planned_cells=12, actual_calls=report["actual_calls"])
        receipt = dict(schema_version=1, status=status, protocol_sha256=protocol_sha256, report=proof,
                       journal_terminal_sha256=journal.events[-1]["sha256"],
                       journal_sha256=digest(journal.path.read_bytes()), planned_cells=12)
        code_locks.close()
        journal.close()
        write_bytes(output / "receipt.json", canonical(receipt))
    except BaseException as error:
        errors.append(dict(stage="final_publication", error=_message(error)))
        if report is not None:
            report["status"] = "partial_or_failed"
        try:
            journal.fail(error, "final_publication")
        except BaseException:
            pass
        try:
            write_bytes(output / "failure-receipt.json", canonical(dict(status="partial_or_failed", errors=errors,
                        protocol_sha256=protocol_sha256, planned_cells=12,
                        terminal_counts={name: sum(cell["terminal"] == name for cell in cells.values()) for name in TERMINALS},
                        journal_terminal_sha256=journal.events[-1]["sha256"])))
        except BaseException:
            pass  # Existing durable events remain the recovery record.
    finally:
        try:
            code_locks.close()
        except BaseException as error:
            errors.append(dict(stage="code_lock_cleanup", error=_message(error)))
            if report is not None:
                report["status"] = "partial_or_failed"
        try:
            journal.close()
        except BaseException as error:
            errors.append(dict(stage="journal_close", error=_message(error)))
            if report is not None:
                report["status"] = "partial_or_failed"
    return report or dict(status="partial_or_failed", errors=errors, planned_cells=12)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        protocol = validate_protocol(args.protocol.read_bytes(), args.protocol_sha256)
        print("READY protocol structure validated; no output reservation, asset hashing, server or HTTP. "
              + protocol["study_id"])
        return 0
    report = run_pilot(args.protocol, args.protocol_sha256, args.output, execute=True)
    print(canonical(dict(status=report["status"], output=str(args.output.resolve()),
                         planned_cells=report["planned_cells"], errors=report["errors"])).decode("utf-8"))
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
