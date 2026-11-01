"""Source-only P04 reference construction after the generation-input seal.

No packet row values are consulted. Expected values are constructed exclusively
by the public source-inclusive compiler, then replayed once from originals.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(r"D:\Projects\drug_target_agents")
sys.path.insert(0, str(ROOT / "src"))

from asof.contracts import Snapshot
from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, decode, encode, fingerprint, parse_json
from asof.study.source_fact_sources import (
    FAMILIES, compile_reference, validate_task, verify_reference,
)
from asof.study.stable_read import deadline_check, read_file, stable_files


ASSETS = ROOT / "planning/review-assets/preprint-p04-20261031"
PLAN = ASSETS / "DEVELOPMENT-INPUT-PLAN-v4.json"
MANIFEST = ASSETS / "GENERATION-INPUTS-v1.json"
BUNDLE = ROOT / "data/derived/preprint-p04-inputs-20261101T043317717926Z"
RAW_ROOT = Path(r"E:\projects_data\drug_target_agents_data")
LIMIT_SECONDS = 3600
CONDITIONS = ("cd276-clean", "osmr-clean", "cd276-controlled-missing")
CODE = (
    "planning/review-assets/preprint-p04-20261031/prepare_references.py",
    "src/asof/study/source_fact_sources.py",
    "src/asof/study/source_fact_adapters.py",
    "src/asof/study/source_rows.py",
    "src/asof/study/stable_read.py",
    "src/asof/study/proofs.py",
    "src/asof/provenance.py",
    "src/asof/contracts.py",
    "src/asof/serde.py",
    "src/asof/wire.py",
    "src/asof/journal.py",
)


def need(condition, message):
    if not condition:
        raise ContractError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def exclusive(path, document):
    return exclusive_payload(path, canonical(document))


def exclusive_payload(path, payload):
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    return {"sha256": digest(payload), "bytes": len(payload)}


def restricted(document):
    return dict(document, role="evaluation_only", agent_visible=False)


def skeleton(facts):
    return [{key: encode(fact[key]) for key in
             ("fact_id", "record_key", "field", "source")} for fact in facts]


def answerability(document):
    facts = document["facts"]
    families = {}
    for family in FAMILIES:
        selected = [fact for fact in facts if fact["family"] == family]
        answerable = [fact for fact in selected if fact["unknown_reason"] is None]
        families[family] = dict(
            facts=len(selected), answerable_facts=len(answerable),
            unknown_facts=len(selected) - len(answerable),
            groups=len({fact["group"] for fact in selected}),
            answerable_groups=len({fact["group"] for fact in answerable}),
        )
    return dict(facts=len(facts), families=families,
                unknown_reasons=dict(Counter(fact["unknown_reason"] for fact in facts
                                             if fact["unknown_reason"] is not None)))


def build(current_catalog):
    started = time.monotonic()
    deadline = started + LIMIT_SECONDS
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "data/benchmark/gold_evidence" / ("preprint-p04-references-" + stamp)
    ignored = subprocess.run(["git", "check-ignore", "--quiet", str(output / "probe")],
                             cwd=ROOT, check=False, capture_output=True)
    need(ignored.returncode == 0, "Reference output must already be ignored")
    journal = RunJournal(output, kind="build")
    stage = "verify_generation_boundary"
    journal.append("build_stage", stage=stage, role="evaluation_only", agent_visible=False,
                   whole_phase_seconds=LIMIT_SECONDS, cooperative_deadline=True,
                   hard_kill_claim=False, model_calls=0)
    timings = []
    verified_references = []
    report = restricted(dict(schema_version=1, status="building", model_calls=0))
    try:
        need(Path.cwd().resolve() == ROOT, "Explicit repository working directory required")
        need(not (ASSETS / "REFERENCES-v1.json").exists(), "Sanitized report already exists")
        manifest_bytes = MANIFEST.read_bytes()
        manifest = parse_json(manifest_bytes)
        seal_payload = (BUNDLE / "SEAL.json").read_bytes()
        seal = parse_json(seal_payload)
        need(digest(seal_payload) == manifest["seal"]["sha256"] and
             len(seal_payload) == manifest["seal"]["bytes"], "Generation seal pin differs")
        expected_names = {condition + suffix for condition in CONDITIONS
                          for suffix in (".packet.json", ".task.json")} | {
                              "preparation-summary.json", "source-inventory.json"}
        need(set(seal["files"]) == expected_names, "Eight-file generation seal differs")
        pinned_paths = [PLAN, MANIFEST, BUNDLE / "SEAL.json", BUNDLE / "journal.jsonl",
                        current_catalog]
        pinned_paths.extend(BUNDLE / name for name in expected_names)
        pinned_paths.extend(ROOT / name for name in CODE)
        pinned_paths.extend(ROOT / name for name in seal["implementation_hashes"])
        with stable_files(pinned_paths, deadline=deadline):
            # Re-read the independently pinned metadata while sharing locks hold.
            need(MANIFEST.read_bytes() == manifest_bytes and
                 (BUNDLE / "SEAL.json").read_bytes() == seal_payload,
                 "Generation metadata changed before stable admission")
            plan_bytes = read_file(PLAN, deadline, 1024 * 1024)
            plan = parse_json(plan_bytes)
            need(digest(plan_bytes) == manifest["plan_sha256"] == seal["plan_sha256"],
                 "Frozen input-plan hash differs")
            payloads = {}
            for name, proof in seal["files"].items():
                payload = read_file(BUNDLE / name, deadline, 2 * 1024 * 1024)
                need(digest(payload) == proof["sha256"] and len(payload) == proof["bytes"],
                     "Sealed generation-input file differs")
                payloads[name] = payload
            for name, pin in seal["implementation_hashes"].items():
                need(digest(read_file(ROOT / name, deadline, 2 * 1024 * 1024)) == pin,
                     "Generation implementation hash differs")
            events = read_chain(BUNDLE / "journal.jsonl")
            need(events[0]["event"] == "build_reserved" and
                 events[-1]["event"] == "build_completed" and
                 not any(event["event"] in ("build_failed", "build_interrupted") for event in events),
                 "Generation preparation journal is not successfully terminal")
            need(events[-1]["details"]["seal_sha256"] == digest(seal_payload),
                 "Generation terminal journal seal differs")
            need(seal["model_calls"] == manifest["model_calls"] == 0 and
                 seal["reference_inputs"] == manifest["reference_inputs"] == [] and
                 seal["generation_authority"] is False and
                 seal["phase"] == "generation_inputs_sealed_before_evaluator_reference_creation",
                 "Generation source-only boundary differs")
            summary = parse_json(payloads["preparation-summary.json"])
            need(summary["evaluator_artifacts_read"] is False and
                 summary["reference_inputs"] == [] and summary["blocked_cases"] == {},
                 "Generation preparation source-only status differs")
            catalog_bytes = read_file(current_catalog, deadline, 4 * 1024 * 1024)
            need(digest(catalog_bytes) == manifest["catalog_sha256"] ==
                 plan["source_policy"]["catalog_sha256"], "Trusted catalog pin differs")
            catalog = parse_json(catalog_bytes)
            inventory = parse_json(payloads["source-inventory.json"])
            snapshot_doc = inventory["source_snapshot"]
            snapshot = decode(Snapshot, snapshot_doc)
            need(inventory["plan_sha256"] == digest(plan_bytes) and
                 inventory["reference_inputs"] == [], "Inventory lineage differs")
            nodes = {node.source_id: node for node in snapshot.sources}
            proofs = {proof["source_id"]: proof for proof in inventory["inventory_proofs"]}
            need(len(nodes) == len(snapshot.sources) == len(proofs) == 111 and
                 set(nodes) == set(proofs), "Full original 111-node inventory differs")
            need(sum(proof["bytes"] for proof in proofs.values()) ==
                 manifest["inventory"]["source_bytes"] == 8216226905,
                 "Full original byte inventory differs")
            need(snapshot.raw_root == str(RAW_ROOT) and
                 snapshot_doc["origin_at"] == manifest["cutoff"] == plan["created_at_utc"] and
                 snapshot_doc["profile"] == "contemporary_assessment" and
                 not snapshot.artifacts and snapshot.allow_reconstructed is False,
                 "Original snapshot scope or cutoff differs")
            for source_id, node in nodes.items():
                proof = proofs[source_id]
                need(node.computed_at is None and not node.parents and
                     node.role in ("agent_evidence", "reference") and node.receipt_path and
                     node.receipt_sha256 and node.dataset_id in ("ot_evidence", "ot_target", "hgnc_symbols"),
                     "Non-original or disallowed source ancestor")
                for key in ("sha256", "dataset_id", "release_id", "path", "receipt_path", "receipt_sha256"):
                    need(encode(getattr(node, key)) == proof[key], "Original source proof binding differs")
            tasks, skeletons = {}, {}
            for condition in CONDITIONS:
                condition_pin = manifest["conditions"][condition]
                task = parse_json(payloads[condition_pin["task_path"]])
                validate_task(task)
                packet = parse_json(payloads[condition_pin["packet_path"]])
                # Only neutral tasks, lineage, source metadata and value-free slots
                # are used. source_records and mapping_records are never accessed.
                need(fingerprint(task) == condition_pin["task_sha256"] == packet["task_sha256"],
                     "Neutral task hash differs")
                need(canonical(packet["neutral_task"]) == canonical(task) and
                     task["cutoff"] == manifest["cutoff"] and
                     task["scope"]["tissue"] is None and
                     task["primary_families"] == plan["source_policy"]["primary_families"],
                     "Packet/task scope or cutoff differs")
                need(packet["role"] == "agent_evidence" and packet["agent_visible"] is True and
                     packet["lineage"]["reference_inputs"] == [] and
                     packet["lineage"]["generation_authority"] is False,
                     "Generation packet lineage differs")
                parents = packet["lineage"]["parents"]
                expected_parents = [{"kind": "eligible_original", "source_id": key,
                                     "sha256": nodes[key].sha256} for key in sorted(nodes)]
                expected_parents.append({"kind": "neutral_input_plan", "sha256": digest(plan_bytes)})
                need(canonical(parents) == canonical(expected_parents), "Packet original-only lineage differs")
                for slot in packet["fact_skeleton"]:
                    need(set(slot) == {"fact_id", "record_key", "field", "source"},
                         "Generation skeleton is not value-free")
                need(len(packet["fact_skeleton"]) == condition_pin["fact_slots"],
                     "Generation skeleton slot count differs")
                tasks[condition], skeletons[condition] = task, packet["fact_skeleton"]
            code_hashes = {name: digest(read_file(ROOT / name, deadline, 2 * 1024 * 1024)) for name in CODE}
            pins = restricted(dict(
                schema_version=1, plan_sha256=digest(plan_bytes),
                generation_manifest_sha256=digest(manifest_bytes),
                generation_seal=manifest["seal"], generation_files=seal["files"],
                generation_journal_sha256=digest((BUNDLE / "journal.jsonl").read_bytes()),
                generation_journal_terminal=events[-1]["sha256"],
                generation_implementation_hashes=seal["implementation_hashes"],
                reference_implementation_hashes=code_hashes,
                catalog_sha256=manifest["catalog_sha256"],
                archived_catalog_path=str(output / "catalog-original.json"),
                current_catalog_path=str(current_catalog),
                approved_raw_root=str(RAW_ROOT), source_snapshot_sha256=fingerprint(snapshot_doc),
                task_sha256={key: fingerprint(task) for key, task in tasks.items()},
            ))
            files = {"input-pins.json": exclusive(output / "input-pins.json", pins),
                     "source-snapshot.json": exclusive(output / "source-snapshot.json",
                         restricted(dict(schema_version=1, source_snapshot=snapshot_doc))),
                     "catalog.json": exclusive(output / "catalog.json",
                         restricted(dict(schema_version=1, catalog=catalog))),
                     # Retain the exact original catalog bytes; its evaluator-only
                     # exposure restriction is assigned by the surrounding seal.
                     "catalog-original.json": exclusive_payload(output / "catalog-original.json", catalog_bytes)}
            need(files["catalog-original.json"]["sha256"] == manifest["catalog_sha256"],
                 "Archived exact catalog bytes differ")
            journal.append("build_progress", generation_files_verified=8, generation_journal_events=len(events),
                           original_source_count=len(nodes), source_bytes=8216226905,
                           implementation_sha256=fingerprint(code_hashes),
                           implementation_hashes=code_hashes, whole_phase_seconds=LIMIT_SECONDS,
                           fixed_compiler_passes=6,
                           estimated_logical_source_hash_bytes=12*8216226905,
                           estimated_prior_throughput_seconds=(12*8216226905 /
                               plan["source_policy"]["preparation_budget_basis"]["approximate_bytes_per_second"]),
                           cap_basis="Prospective setup allocation before first compile; no per-case model-budget change")
            conditions = {}
            # Six full-graph compiler passes: initial construction plus one
            # independent retained-document replay per reference. Each public
            # compiler pass hashes every original twice (InputGraph + stable hash).
            graph_hash_bytes_per_pass = 2 * 8216226905
            receipt_hash_bytes_per_pass = 2 * sum(p["receipt_bytes"] for p in proofs.values())
            for condition in CONDITIONS:
                task = tasks[condition]
                phase_started = time.monotonic()
                stage = "compile_reference:" + condition
                journal.append("build_stage", stage=stage, full_source_graph_nodes=111,
                               estimated_logical_source_hash_bytes=graph_hash_bytes_per_pass)
                compiled = compile_reference(task, snapshot, ROOT, catalog, deadline=deadline,
                                             approved_raw_root=RAW_ROOT)
                compile_seconds = time.monotonic() - phase_started
                need(skeleton(compiled.document["facts"]) == skeletons[condition],
                     "Reference and sealed generation skeleton binding mismatch")
                need(compiled.document["role"] == "evaluation_only" and
                     compiled.document["agent_visible"] is False and
                     len(compiled.document["source_proofs"]) == 111,
                     "Reference exposure or full-source proof mismatch")
                filename = condition + ".reference.json"
                files[filename] = exclusive(output / filename, compiled.document)
                need(files[filename]["sha256"] == compiled.fingerprint, "Canonical reference pin differs")
                # Pin bytes independently before the source-inclusive replay.
                journal.append("build_progress", condition_id=condition, reference_sha256=compiled.fingerprint,
                               reference_bytes=files[filename]["bytes"], compile_seconds=compile_seconds)
                stage = "verify_reference:" + condition
                journal.append("build_stage", stage=stage, source_inclusive_replay=True,
                               full_source_graph_nodes=111,
                               estimated_logical_source_hash_bytes=graph_hash_bytes_per_pass)
                replay_started = time.monotonic()
                retained = parse_json(read_file(output / filename, deadline, 4 * 1024 * 1024))
                verified = verify_reference(retained, compiled.fingerprint, task, snapshot, ROOT, catalog,
                                            deadline=deadline, approved_raw_root=RAW_ROOT)
                replay_seconds = time.monotonic() - replay_started
                need(verified.fingerprint == compiled.fingerprint and
                     skeleton(verified.document["facts"]) == skeletons[condition],
                     "Retained replay or generation binding differs")
                verified_references.append(verified)
                conditions[condition] = dict(
                    reference_path=filename, reference_sha256=verified.fingerprint,
                    task_sha256=fingerprint(task), collection_status=task["collection"]["status"],
                    records=len(task["records"]), source_proofs=111,
                    skeleton_bindings_match=True, source_inclusive_replays=1,
                    **answerability(verified.document),
                )
                timings.append(dict(condition_id=condition, compile_seconds=compile_seconds,
                                    verification_replay_seconds=replay_seconds,
                                    compiler_passes=2,
                                    estimated_logical_source_hash_bytes=2 * graph_hash_bytes_per_pass,
                                    estimated_logical_receipt_hash_bytes=2 * receipt_hash_bytes_per_pass))
                journal.append("build_progress", condition_id=condition, source_replay_verified=True,
                               replay_seconds=replay_seconds, reference_sha256=verified.fingerprint)
            stage = "seal_references"
            journal.append("build_stage", stage=stage, verified_reference_capabilities=len(verified_references))
            deadline_check(deadline)
            report = restricted(dict(
                schema_version=1, status="sealed_source_only_references", model_calls=0,
                reference_method="mechanical public literal_field.v1 compiler; not AI gold or adjudication",
                output=str(output.relative_to(ROOT)).replace("\\", "/"), cutoff=manifest["cutoff"],
                conditions=conditions, pins=pins,
                exposure=dict(generation_inputs_sealed_first=True, generation_inputs_modified=False,
                              packet_row_values_used_for_expected_facts=False,
                              expected_facts_from_original_source_replay=True,
                              old_references_candidates_experts_memory_benchmarks_read=False,
                              generated_p04_outputs_read=False, source_only_mechanical_build=True,
                              expected_values_in_public_report=False),
                resources=dict(whole_phase_seconds=LIMIT_SECONDS, cooperative_deadline=True,
                               cap_basis="Prospective 3600s whole-build allocation before first compile, based on twelve full original hash reads (~98.6GB); per-case model budgets unchanged.",
                               hard_kill_claim=False, elapsed_seconds=time.monotonic()-started,
                               phases=timings, compiler_passes=6,
                               source_graph_nodes_per_pass=111,
                               source_bytes=8216226905,
                               estimated_logical_source_hash_bytes=6*graph_hash_bytes_per_pass,
                               estimated_logical_receipt_hash_bytes=6*receipt_hash_bytes_per_pass,
                               physical_io_bytes=None,
                               io_estimate_note="Logical hash read bytes only; excludes row parsing and receipt JSON reads; physical IO not measured. Public compiler hashes originals twice per pass.",
                               peak_working_set_bytes=None, peak_rss_measured=False,
                               rss_note="Not measured for this build; generation-preparation RSS is not reference-build RSS.",
                               cache_state="Potentially warm from prior generation preparation; cache residency not measured.",
                               prior_generation_preparation_seconds=summary["preparation_elapsed_seconds"],
                               prior_failed_preparation=dict(elapsed_seconds=plan["source_policy"]["preparation_budget_basis"]["observed_seconds"],
                                   verified_bytes=plan["source_policy"]["preparation_budget_basis"]["observed_verified_bytes"],
                                   source="Pinned v4 plan; not reread or included in this phase elapsed time")),
            ))
            files["build-report.json"] = exclusive(output / "build-report.json", report)
            reference_seal = restricted(dict(
                schema_version=1, sealed_at_utc=datetime.now(timezone.utc).isoformat(),
                phase="source_only_evaluator_references_sealed_before_model_calls",
                files={name:dict(proof, role="evaluation_only", agent_visible=False)
                       for name,proof in files.items()},
                generation_seal_sha256=manifest["seal"]["sha256"], plan_sha256=digest(plan_bytes),
                reference_implementation_hashes=code_hashes,
                journal_prefix_sha256=journal.events[-1]["sha256"], model_calls=0,
                reference_count=len(verified_references), source_inclusive_replays_per_reference=1,
            ))
            seal_pin = exclusive(output / "SEAL.json", reference_seal)
            deadline_check(deadline)
            journal.append("build_completed", references=3, source_inclusive_replays=3,
                           elapsed_seconds=time.monotonic()-started, seal_sha256=seal_pin["sha256"],
                           model_calls=0, role="evaluation_only", agent_visible=False)
            public_report = dict(report, seal=seal_pin,
                                 journal_terminal_sha256=journal.events[-1]["sha256"],
                                 total_elapsed_seconds=time.monotonic()-started)
            exclusive(ASSETS / "REFERENCES-v1.json", public_report)
            # VerifiedReference objects never cross a serialized or agent-visible boundary.
            verified_references.clear()
            print(json.dumps(dict(status=public_report["status"], references=3,
                                  output=public_report["output"], seal=seal_pin,
                                  elapsed_seconds=public_report["total_elapsed_seconds"])))
            return 0
    except BaseException as error:
        journal.append("build_interrupted" if isinstance(error, KeyboardInterrupt) else "build_failed",
                       stage=stage, error_class=type(error).__name__,
                       failure_reason=str(error), elapsed_seconds=time.monotonic()-started,
                       model_calls=0, role="evaluation_only", agent_visible=False)
        failure = restricted(dict(schema_version=1, status="failed", stage=stage,
                                  error_class=type(error).__name__, failure_reason=str(error),
                                  elapsed_seconds=time.monotonic()-started, model_calls=0,
                                  no_alternate_cases_or_references=True))
        exclusive(output / "failure-report.json", failure)
        print(json.dumps(dict(status="failed", stage=stage, error_class=type(error).__name__,
                              failure_reason=str(error), output=str(output))))
        return 1
    finally:
        journal.close()


if __name__ == "__main__":
    need(len(sys.argv) == 2, "Pass exact pinned current catalog path")
    raise SystemExit(build(Path(sys.argv[1])))
