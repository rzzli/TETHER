"""Independent finite P04 source fidelity audit; no author pipeline imports.

Run with the repository virtualenv and repository cwd. Reads only pinned P04
bundles, the v4 plan, pinned implementation bytes, catalogs, and seven selected
original files with their archived receipts. Never prints native source values.
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import date, datetime, time, timezone
import hashlib
import json
from pathlib import Path
import sys
import time as monotonic_time

import pyarrow
import pyarrow.parquet as pq

ROOT = Path(r"D:\Projects\drug_target_agents")
ASSETS = ROOT / "planning/review-assets/preprint-p04-20261031"
OUT = ASSETS / "INPUT-REFERENCE-AUDIT-v1.json"
START = monotonic_time.monotonic()
CHECKS = Counter()
DEFECTS = []


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"sha256": h.hexdigest(), "bytes": path.stat().st_size}


def check(test, label, category):
    CHECKS[category] += 1
    if not test:
        DEFECTS.append({"check": label, "category": category})


def utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def chain(path):
    payload = path.read_bytes()
    check(payload.endswith(b"\n"), "journal has complete terminal line", "journal")
    events = [json.loads(line) for line in payload.splitlines()]
    prior = None
    for index, event in enumerate(events):
        unsigned = {k: v for k, v in event.items() if k != "sha256"}
        check(event["sequence"] == index and event["previous_sha256"] == prior
              and event["sha256"] == fingerprint(unsigned),
              "journal sequence/link/hash", "journal")
        prior = event["sha256"]
    check(events[0]["event"] == "build_reserved"
          and events[-1]["event"] == "build_completed"
          and not any(e["event"] in ("build_failed", "build_interrupted") for e in events),
          "successful terminal journal", "journal")
    return events


def safe_raw(raw_root, relative):
    path = (raw_root / relative).resolve()
    check(path.is_relative_to(raw_root.resolve()), "selected original stays in approved root", "original")
    return path


def main():
    if Path.cwd().resolve() != ROOT or Path(sys.executable).resolve() != ROOT / ".venv/Scripts/python.exe":
        raise RuntimeError("Explicit repository cwd and absolute repository interpreter required")
    check(pyarrow.__version__ == "21.0.0", "Arrow version 21.0.0", "environment")
    gen_manifest_path = ASSETS / "GENERATION-INPUTS-v1.json"
    ref_manifest_path = ASSETS / "REFERENCES-v1.json"
    gman, rman = read(gen_manifest_path), read(ref_manifest_path)
    gen = ROOT / gman["original_value_output"]
    ref = ROOT / rman["output"]
    plan_path = ASSETS / "DEVELOPMENT-INPUT-PLAN-v4.json"
    plan = read(plan_path)
    gseal, rseal = read(gen / "SEAL.json"), read(ref / "SEAL.json")
    pins = read(ref / "input-pins.json")
    check(pins == rman["pins"], "public/private reference pins identical", "pin")
    plan_hash = digest(plan_path)["sha256"]
    check(plan_hash == gman["plan_sha256"] == rman["pins"]["plan_sha256"]
          == gseal["plan_sha256"] == rseal["plan_sha256"], "v4 plan pin", "pin")
    check(digest(gen_manifest_path)["sha256"] == pins["generation_manifest_sha256"],
          "generation manifest pin", "pin")
    check(digest(gen / "SEAL.json") == gman["seal"] == pins["generation_seal"],
          "generation seal hash/size", "pin")
    check(digest(ref / "SEAL.json") == rman["seal"], "reference seal hash/size", "pin")
    for base, seal in ((gen, gseal), (ref, rseal)):
        for name, proof in seal["files"].items():
            check(digest(base / name) == {k: proof[k] for k in ("sha256", "bytes")},
                  "sealed artifact hash/size:" + name, "sealed_file")
    expected_conditions = {"cd276-clean", "osmr-clean", "cd276-controlled-missing"}
    check(set(gman["conditions"]) == set(rman["conditions"]) == expected_conditions,
          "three prospective conditions", "pin")
    check(set(gseal["files"]) == {c+s for c in expected_conditions for s in (".packet.json", ".task.json")}
          | {"source-inventory.json", "preparation-summary.json"}, "exact eight generation assets", "pin")
    check(gseal["files"] == pins["generation_files"], "all eight generation file pins", "pin")
    code_pins = dict(pins["generation_implementation_hashes"])
    code_pins.update(pins["reference_implementation_hashes"])
    for name, wanted in code_pins.items():
        check(digest(ROOT / name)["sha256"] == wanted, "implementation hash:" + name, "code_pin")
    check(gman["implementation_hashes"] == gseal["implementation_hashes"]
          == pins["generation_implementation_hashes"], "generation implementation pin agreement", "pin")
    check(rseal["reference_implementation_hashes"] == pins["reference_implementation_hashes"],
          "reference implementation pin agreement", "pin")
    gevents, revents = chain(gen / "journal.jsonl"), chain(ref / "journal.jsonl")
    check(digest(gen / "journal.jsonl")["sha256"] == pins["generation_journal_sha256"],
          "generation journal file pin", "pin")
    check(gevents[-1]["sha256"] == pins["generation_journal_terminal"]
          and gevents[-1]["details"]["seal_sha256"] == gman["seal"]["sha256"],
          "generation terminal seal/pin", "journal")
    check(revents[-1]["sha256"] == rman["journal_terminal_sha256"]
          and revents[-1]["details"]["seal_sha256"] == rman["seal"]["sha256"]
          and revents[-2]["sha256"] == rseal["journal_prefix_sha256"],
          "reference terminal and preseal prefix", "journal")
    check(utc(gseal["sealed_at_utc"]) < utc(revents[0]["details"]["created_at_utc"])
          < utc(rseal["sealed_at_utc"]), "generation seal precedes reference reservation", "boundary")
    check(rseal["generation_seal_sha256"] == gman["seal"]["sha256"],
          "reference seal pins generation seal", "boundary")
    for doc in (gman, gseal):
        check(doc["model_calls"] == 0 and doc["reference_inputs"] == []
              and doc["generation_authority"] is False, "generation excludes evaluator parents/model authority", "boundary")
    inventory = read(gen / "source-inventory.json")
    snap = inventory["source_snapshot"]
    nodes = {n["source_id"]: n for n in snap["sources"]}
    proofs = {p["source_id"]: p for p in inventory["inventory_proofs"]}
    catalog_path = Path(pins["current_catalog_path"])
    archived_catalog_path = Path(pins["archived_catalog_path"])
    check(digest(catalog_path)["sha256"] == digest(archived_catalog_path)["sha256"]
          == pins["catalog_sha256"] == gman["catalog_sha256"]
          == plan["source_policy"]["catalog_sha256"], "current/exact archived catalog pin", "pin")
    catalog = read(archived_catalog_path)
    catalog_index = {d["dataset_id"]: d for d in catalog["datasets"]}
    wrapped_catalog = read(ref / "catalog.json")
    check(wrapped_catalog["catalog"] == catalog, "evaluation catalog wrapper preserves original", "pin")
    check(read(ref / "source-snapshot.json")["source_snapshot"] == snap
          and fingerprint(snap) == pins["source_snapshot_sha256"], "snapshot identity and pin", "pin")
    check(snap["origin_at"] == gman["cutoff"] == rman["cutoff"] == plan["created_at_utc"]
          and snap["raw_root"] == pins["approved_raw_root"]
          and snap["profile"] == "contemporary_assessment" and snap["schema_version"] == 2
          and not snap["artifacts"] and snap["allow_reconstructed"] is False,
          "snapshot cutoff/scope/root", "boundary")
    check(len(nodes) == len(proofs) == 111 and set(nodes) == set(proofs), "111 unique metadata nodes/proofs", "inventory_metadata")
    check(sum(p["bytes"] for p in proofs.values()) == 8216226905,
          "declared inventory byte sum", "inventory_metadata")
    check(Counter(n["dataset_id"] for n in nodes.values())
          == {"ot_evidence": 100, "ot_target": 10, "hgnc_symbols": 1},
          "declared inventory dataset counts", "inventory_metadata")
    cutoff = utc(gman["cutoff"])
    for sid, node in nodes.items():
        dataset = catalog_index[node["dataset_id"]]
        check(node["computed_at"] is None and node["parents"] == []
              and node["method_id"] is None and node["method_version"] is None
              and node["role"] in ("agent_evidence", "reference")
              and node["role"] in dataset["roles"] and "evaluation_only" not in dataset["roles"],
              "original-only catalog-approved ancestry", "lineage")
        for key in ("sha256", "dataset_id", "release_id", "path", "receipt_path", "receipt_sha256", "availability"):
            check(node[key] == proofs[sid][key], "source node/proof metadata binding", "lineage")
        check(node["availability"]["basis"] == "public_download_receipt"
              and utc(node["availability"]["known_public_by"]) <= cutoff
              and node["availability"]["evidence_ref"] == node["receipt_sha256"],
              "receipt-based contemporary availability", "lineage")
    check(inventory["reference_inputs"] == [] and inventory["plan_sha256"] == plan_hash,
          "inventory original-only lineage", "lineage")
    raw_root = Path(pins["approved_raw_root"])
    packets = {cid: read(gen / (cid + ".packet.json")) for cid in gman["conditions"]}
    selected_ids = {row["source_id"] for p in packets.values()
                    for row in p["source_records"] + p["mapping_records"]}
    selected_hashes = []
    for sid in sorted(selected_ids):
        node, proof = nodes[sid], proofs[sid]
        path, receipt_path = safe_raw(raw_root, node["path"]), safe_raw(raw_root, node["receipt_path"])
        actual, receipt_actual = digest(path), digest(receipt_path)
        receipt = read(receipt_path)
        check(actual == {"sha256": node["sha256"], "bytes": proof["bytes"]},
              "selected original full file hash/size", "original")
        check(receipt_actual == {"sha256": node["receipt_sha256"], "bytes": proof["receipt_bytes"]},
              "selected archived receipt hash/size", "receipt")
        check(receipt["status"] == "completed" and receipt["sha256"] == node["sha256"]
              and receipt["bytes"] == proof["bytes"] and receipt["dataset_id"] == node["dataset_id"]
              and receipt["release_id"] == node["release_id"] and receipt["url"] == node["source_url"]
              and receipt["relative_path"].replace("\\", "/") == node["path"]
              and utc(receipt["completed_at_utc"]) <= utc(node["availability"]["known_public_by"]),
              "selected receipt identity/path/time", "receipt")
        if node["dataset_id"] != "hgnc_symbols":
            columns = pq.ParquetFile(path).schema_arrow.names
        else:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                columns = next(csv.reader(stream, delimiter="\t"))
        check(fingerprint(columns) == proof["schema_sha256"], "selected original schema pin", "original")
        selected_hashes.append({"source_id": sid, "dataset_id": node["dataset_id"], **actual,
                                "receipt_sha256": receipt_actual["sha256"], "receipt_bytes": receipt_actual["bytes"]})

    def native_selected(item, fields):
        node = nodes[item["source_id"]]
        path = safe_raw(raw_root, node["path"])
        loc = item["locator"]
        if loc["format"] == "parquet":
            parquet = pq.ParquetFile(path)
            projection = [f for f in fields if f in parquet.schema_arrow.names]
            # Independent direct pyarrow row-group read and exact positional slice.
            table = parquet.read_row_group(loc["row_group"], columns=projection)
            check(loc["row"] < table.num_rows, "exact row-group locator in bounds", "direct_row")
            return table.slice(loc["row"], 1).to_pylist()[0]
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for index, row in enumerate(csv.DictReader(stream, delimiter="\t")):
                if index == loc["row"]:
                    return {f: row[f] for f in fields if f in row}
        raise RuntimeError("Selected TSV locator is absent")

    family_map = {"id": "identity_linkage", "publicationDate": "reported_context",
                  "evidenceDate": "reported_context", "cellType": "reported_context"}
    evidence_fields = ["id", "targetId", "diseaseId", "datasourceId", "datatypeId",
                       "publicationDate", "evidenceDate", "cellType"]
    cases = {c["case_id"]: c for c in plan["cases"]}
    expected_parents = [{"kind": "eligible_original", "source_id": sid, "sha256": nodes[sid]["sha256"]}
                        for sid in sorted(nodes)] + [{"kind": "neutral_input_plan", "sha256": plan_hash}]
    conditions = {}
    evidence_count, hgnc_count, target_count = 0, 0, 0
    native_states = Counter()
    for cid, packet in packets.items():
        task = read(gen / (cid + ".task.json"))
        reference = read(ref / (cid + ".reference.json"))
        task_hash = fingerprint(task)
        check(task == packet["neutral_task"] == reference["method"]["task"]
              and task_hash == packet["task_sha256"] == reference["task_sha256"]
              == gman["conditions"][cid]["task_sha256"] == pins["task_sha256"][cid],
              "task and canonical task pins across both bundles", "task")
        check(reference["scope"] == task["scope"] and reference["collection"] == task["collection"]
              and reference["cutoff"] == task["cutoff"] == gman["cutoff"],
              "reference task scope/collection/cutoff", "task")
        policy_snapshot = dict(snap, raw_root=None)
        check(reference["method"]["catalog_sha256"] == fingerprint(catalog_index)
              and reference["method"]["source_snapshot_sha256"] == fingerprint(policy_snapshot)
              and reference["method"]["scientific_validation"] == "not_established"
              and reference["method"]["transform"] == "literal_field.v1", "reference compiler metadata pins", "pin")
        check(reference["role"] == "evaluation_only" and reference["agent_visible"] is False
              and len(reference["source_proofs"]) == 111, "reference exposure/full proof metadata", "boundary")
        ref_proofs = {p["artifact_id"]: p for p in reference["source_proofs"]}
        check(set(ref_proofs) == set(nodes), "reference proof source set", "lineage")
        for sid, proof in proofs.items():
            expected_proof = {k: v for k, v in proof.items() if k not in ("source_id", "schema_sha256")}
            expected_proof.update(artifact_id=sid, path_scope="raw")
            check(ref_proofs[sid] == expected_proof, "reference proof equals pinned original metadata", "lineage")
        check(packet["role"] == "agent_evidence" and packet["agent_visible"] is True
              and packet["lineage"]["parents"] == expected_parents
              and packet["lineage"]["reference_inputs"] == []
              and packet["lineage"]["generation_authority"] is False,
              "packet source-only ancestry and exposure", "lineage")
        check(all(set(slot) == {"fact_id", "record_key", "field", "source"}
                  for slot in packet["fact_skeleton"]), "skeleton contains bindings only, no expected answers", "boundary")
        check(task["joins"] == [] and task["primary_families"] == ["identity_linkage", "reported_context"]
              and all(f["field"] in family_map for f in task["fields"]),
              "four-field allowlist excludes clinical/status/outcomes", "task")
        check(packet["namespace_provenance"]["target_upstream_version"] == "unknown"
              and packet["namespace_provenance"]["indication_upstream_version"] == "unknown"
              and "upstream-version-unknown" in task["scope"]["indication_namespace_version"],
              "unknown upstream namespaces explicitly retained", "namespace")
        visible = {x["source_id"] for x in packet["source_records"] + packet["mapping_records"]}
        check(packet["source_nodes"] == [nodes[sid] for sid in sorted(visible)]
              and packet["source_proofs"] == [p for p in inventory["inventory_proofs"] if p["source_id"] in visible],
              "packet visible sources/proofs exactly its selected original rows", "lineage")
        check(packet["selection_inventory_sha256"] == fingerprint({"nodes": nodes, "proofs": inventory["inventory_proofs"]}),
              "packet complete selection inventory metadata pin", "pin")
        native_rows = {}
        case = cases[packet["case_id"]]
        if packet["condition"]["synthetic"]:
            check(not packet["source_records"] and not packet["mapping_records"]
                  and not packet["fact_skeleton"] and not packet["source_nodes"] and not packet["source_proofs"]
                  and not task["records"] and not task["fields"] and not reference["facts"]
                  and packet["condition"]["kind"] == "synthetic_input_withholding"
                  and packet["condition"]["independent_biomedical_context"] is False
                  and packet["condition"]["biological_absence_claim"] is False
                  and task["collection"]["status"] == "incomplete",
                  "controlled missing withholds all source rows/values and has zero facts", "missing")
        else:
            check(len(packet["source_records"]) == 2 and len(packet["mapping_records"]) == 2
                  and len(task["records"]) == 2 and len(task["fields"]) == 8
                  and len(reference["facts"]) == 8, "clean case finite counts", "task")
            for item in packet["source_records"]:
                row = native_selected(item, evidence_fields)
                evidence_count += 1
                check(row == item["row"] and set(row).issubset(evidence_fields),
                      "native selected original evidence equals packet projection", "direct_row")
                record = next(x for x in task["records"] if x["record_key"] == item["record_key"])
                check(item["source_id"] == record["source_id"] and item["locator"] == record["locator"]
                      and record["identity"] == {f: row[f] for f in ("id", "targetId", "diseaseId")}
                      and row["targetId"] == task["scope"]["target_id"]
                      and row["diseaseId"] == task["scope"]["indication_id"] == case["indication_id"]
                      and row["datasourceId"] == "europepmc" and row["datatypeId"] == "literature",
                      "native identity/provider/case bindings", "direct_row")
                for f in ("publicationDate", "evidenceDate"):
                    value = row.get(f)
                    if value:
                        observed = datetime.combine(date.fromisoformat(value), time.max, timezone.utc) if len(value) == 10 else utc(value)
                        check(observed <= cutoff, "native selected date precedes cutoff", "direct_row")
                native_rows[item["record_key"]] = row
            hg, target = packet["mapping_records"]
            hg_row = native_selected(hg, ["hgnc_id", "symbol", "status", "ensembl_gene_id"])
            target_row = native_selected(target, ["id", "approvedSymbol"])
            hgnc_count += 1
            target_count += 1
            check(hg_row == hg["row"] and target_row == target["row"]
                  and hg_row["symbol"] == target_row["approvedSymbol"] == case["target_symbol"]
                  and hg_row["status"] == "Approved"
                  and hg_row["ensembl_gene_id"] == target_row["id"] == task["scope"]["target_id"],
                  "exact native HGNC and target row mapping", "mapping")
            check(task["scope"]["target_namespace_version"] == "OpenTargets-25.09:target:" + nodes[target["source_id"]]["sha256"],
                  "namespace token binds actual target artifact", "namespace")
        check(len(packet["fact_skeleton"]) == len(reference["facts"]) == len(task["fields"]),
              "task/skeleton/reference fact counts", "fact")
        for field, slot, fact in zip(task["fields"], packet["fact_skeleton"], reference["facts"]):
            record = next(x for x in task["records"] if x["record_key"] == field["record_key"])
            node, row, name = nodes[record["source_id"]], native_rows[field["record_key"]], field["field"]
            binding = {"source_id": node["source_id"], "sha256": node["sha256"],
                       "release_id": node["release_id"], "locator": record["locator"], "field": name}
            neutral_id = "fact:" + fingerprint({"task_sha256": task_hash, "scope": task["scope"],
                                                "record_key": field["record_key"], "source": binding})
            value = row.get(name)
            empty = value == "" if isinstance(value, str) else isinstance(value, (list, dict)) and len(value) == 0
            reason = "field_not_in_schema" if name not in row else "null_source_value" if value is None else "empty_source_value" if empty else None
            native_states[reason or "present_nonempty"] += 1
            expected = {"fact_id": neutral_id, "record_key": field["record_key"], "field": name,
                        "family": family_map[name], "group": field["record_key"] + ":" +
                        ("identity" if name == "id" else "cell-context" if name == "cellType" else "reported-dates"),
                        "value": None if reason else value,
                        "unit": None, "source": binding, "unknown_reason": reason}
            check(fact == expected and slot == {k: expected[k] for k in ("fact_id", "record_key", "field", "source")}
                  and field["family"] == family_map[name] and field["empty_policy"] == "unknown"
                  and field["group"] == expected["group"] and field["unit_field"] is None,
                  "independent literal/native-state/family/group/binding/neutral fact ID", "fact")
        family_counts = {}
        for family in ("identity_linkage", "reported_context", "reported_measurement", "provider_metric"):
            ff = [f for f in reference["facts"] if f["family"] == family]
            aa = [f for f in ff if f["unknown_reason"] is None]
            family_counts[family] = {"facts": len(ff), "answerable_facts": len(aa),
                                     "unknown_facts": len(ff)-len(aa), "groups": len({f["group"] for f in ff}),
                                     "answerable_groups": len({f["group"] for f in aa})}
        unknowns = dict(Counter(f["unknown_reason"] for f in reference["facts"] if f["unknown_reason"]))
        check(family_counts == rman["conditions"][cid]["families"]
              and unknowns == rman["conditions"][cid]["unknown_reasons"],
              "public reference answerability summary", "summary")
        conditions[cid] = {"records": len(task["records"]), "facts": len(reference["facts"]),
                           "task_sha256": task_hash, "reference_sha256": digest(ref / (cid + ".reference.json"))["sha256"],
                           "families": family_counts, "unknown_reasons": unknowns,
                           "collection_status": task["collection"]["status"], "native_selected_rows_match": True}
    for name, proof in rseal["files"].items():
        check(proof["role"] == "evaluation_only" and proof["agent_visible"] is False,
              "all reference-sealed assets evaluator-only", "boundary")
        if name != "catalog-original.json":
            document = read(ref / name)
            check(document["role"] == "evaluation_only" and document["agent_visible"] is False,
                  "reference document exposure", "boundary")
    report = {
        "schema_version": 1,
        "status": "passed_finite_source_fidelity_audit" if not DEFECTS else "defects_found",
        "audit_kind": "independent finite source fidelity; not candidate grading or scientific validation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_values_in_report": False,
        "inputs": {"generation_manifest": digest(gen_manifest_path), "references_manifest": digest(ref_manifest_path),
                   "plan_sha256": plan_hash, "catalog_sha256": pins["catalog_sha256"],
                   "source_snapshot_sha256": pins["source_snapshot_sha256"],
                   "generation_seal": digest(gen / "SEAL.json"), "reference_seal": digest(ref / "SEAL.json"),
                   "implementation_hashes": code_pins},
        "journals": {"generation": {**digest(gen / "journal.jsonl"), "events": len(gevents), "terminal_sha256": gevents[-1]["sha256"]},
                     "references": {**digest(ref / "journal.jsonl"), "events": len(revents), "terminal_sha256": revents[-1]["sha256"]},
                     "all_links_and_event_hashes_recomputed": True,
                     "generation_sealed_before_reference_reservation": True},
        "check_counts": dict(CHECKS), "checks_total": sum(CHECKS.values()), "defects": DEFECTS,
        "direct_original_checks": {"evidence_rows": evidence_count, "hgnc_tsv_rows": hgnc_count,
                                   "target_rows": target_count, "unique_original_files_hashed": len(selected_hashes),
                                   "archived_receipts_hashed": len(selected_hashes),
                                   "selected_original_hash_bytes": sum(x["bytes"] for x in selected_hashes),
                                   "native_state_fact_counts": dict(native_states), "selected_file_pins": selected_hashes,
                                   "row_method": "Direct pyarrow.ParquetFile.read_row_group with allowlisted columns then exact positional slice; TSV DictReader positional locators. No author pipeline/compiler/projection invoked."},
        "conditions": conditions,
        "scope_and_exposure": {"independent_biomedical_contexts": 2, "condition_units": 3,
                               "evaluator_references_read": True, "generator_eligibility_after_this_audit": False,
                               "original_selected_source_values_read": True, "old_experts_responses_candidates_read": False,
                               "clinical_outcomes_or_model_outputs_read": False, "model_calls": 0,
                               "network_download_server_worker_actions": 0,
                               "packet_skeleton_expected_answers": False, "references_evaluation_only": True,
                               "controlled_missing": "Artificial all-record withholding within an existing case: zero source rows, mappings, slots and facts; incomplete collection, no biological absence or independent third case.",
                               "namespace_and_truth": "Artifact/release identifier bindings verified; true upstream Ensembl/EFO versions remain unknown. Literal source fidelity does not establish scientific truth."},
        "limitations": [
            "All 111 inventory nodes/proofs checked as sealed metadata; only seven selected original files and their seven archived receipts rehashed/read. The other 104 originals and receipts were not independently reopened or rehashed.",
            "Global first-two lexical selection and 188/5 matching/distinct-row counts remain author-algorithm/history claims. No full 100-file evidence rescan was performed; no global minimality or duplicate-conflict exclusion independently established.",
            "Selected HGNC/target rows and equality were checked at exact locators; global symbol uniqueness across all mapping originals was not independently rescanned.",
            "Null, empty and absent rules were independently implemented, but these 16 selected facts exercise 12 present/nonempty and four null values, with zero empty and zero absent selected fields.",
            "Journal hashes and ordering authenticate retained artifacts and declared build history; they cannot prove undisclosed process reads or ancestry outside the retained provenance.",
            "Pinned inspection hash was checked for agreement through retained plan/manifests, without reopening its separate historical inspection file.",
            "Reference compiler replay and full-inventory hash passes were historical author actions; this audit did not invoke the compiler or repeat those full passes.",
            "No candidates were generated or graded, and no biomedical effect, absence, clinical outcome, publisher checksum authority, or scientific validity was inferred."
        ],
        "resources": {"elapsed_seconds": monotonic_time.monotonic()-START,
                      "full_inventory_rescan": False, "full_inventory_rehash": False,
                      "peak_rss_measured": False, "physical_io_measured": False},
        "checker_sha256": digest(Path(__file__))["sha256"],
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks_total": report["checks_total"],
                      "defects": DEFECTS, "direct_rows": evidence_count+hgnc_count+target_count,
                      "selected_files": len(selected_hashes), "report_sha256": digest(OUT)["sha256"]}))
    return 1 if DEFECTS else 0


if __name__ == "__main__":
    raise SystemExit(main())
