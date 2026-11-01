"""Original-only inputs for the separately named source-fact reporting study.

This module never imports the reference compiler, opens evaluator artifacts, or
constructs application EvidencePackets.  Its source ancestry is closed to the
explicitly pinned original inventory and the neutral input plan.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, time as day_time, timezone
from pathlib import Path
import time

from asof.contracts import Snapshot, SourceNode
from asof.provenance import InputGraph, catalog_index
from asof.serde import ContractError, canonical, decode, encode, fingerprint, parse_json
from .stable_read import checked_path, deadline_check, hash_file, read_file, stable_files


EVIDENCE_FIELDS = ("id", "targetId", "diseaseId", "datasourceId", "datatypeId",
                   "publicationDate", "evidenceDate", "cellType")
REQUESTED_FIELDS = ("id", "publicationDate", "evidenceDate", "cellType")
FAMILIES = {"id": "identity_linkage", "publicationDate": "reported_context",
            "evidenceDate": "reported_context", "cellType": "reported_context"}
METHOD = "source-fact-generation-input-v1"
MAX_MATCHING_ROWS = 100000
V4_PLAN_SHA256 = "815f23b10f15bb6e68967aaed05e532c35b286160c5f89f65b9105a98b10b761"


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _utc(value):
    _need(type(value) is str and "T" in value, "Exact UTC timestamp required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("Invalid UTC timestamp") from error
    _need(result.tzinfo is not None and result.utcoffset().total_seconds() == 0,
          "Exact UTC timestamp required")
    return result


def _plan_contract(plan, cutoff):
    """Reject a changed task/condition/selector contract before original values."""
    _need(cutoff == plan["created_at_utc"], "Cutoff differs from frozen neutral plan")
    wanted = [dict(case_id="cd276-nsclc-development", target_symbol="CD276", target_id=None,
                   indication_id="EFO_0003060", action="delivery_antigen", modality="ADC", tissue=None),
              dict(case_id="osmr-uc-development", target_symbol="OSMR", target_id=None,
                   indication_id="EFO_0000729", action="inhibit", modality="antibody", tissue=None)]
    _need(plan["cases"] == wanted, "Frozen case scope differs")
    _need(plan["conditions"] == [
        dict(id="cd276-clean", case="cd276-nsclc-development", kind="real_selected_sources"),
        dict(id="osmr-clean", case="osmr-uc-development", kind="real_selected_sources"),
        dict(id="cd276-controlled-missing", case="cd276-nsclc-development", kind="synthetic_input_withholding",
             records_available=0, collection_status="incomplete", biological_absence=False)], "Frozen conditions differ")
    _need(plan["source_policy"]["record_selector"] ==
          "per exact targetId/diseaseId choose first two distinct native record IDs in lexical order; tie locator source_id,row_group,row; conflicting duplicate IDs block affected case without favorable substitution",
          "Frozen lexical record selector differs")
    _need(plan["source_policy"]["primary_families"] == ["identity_linkage", "reported_context"],
          "Frozen primary reporting families differ")


def selected_inventory(plan, inspection, catalog, *, plan_sha256=None):
    """Select metadata only; reject unregistered, derived or evaluator ancestors."""
    policy = plan["source_policy"]
    _need(policy["release"] == "25.09" and policy["partition"] == "europepmc",
          "Only declared Open Targets 25.09 EuropePMC inventory is supported")
    _need(policy["requested_fields"] == list(REQUESTED_FIELDS), "Requested field plan changed")
    _need(policy["max_selected_records_per_case"] == 2, "Fixed two-record selection required")
    full_inventory = (policy["declared_evidence_files"] == 100 and
                      policy["declared_evidence_bytes"] == 8123685179 and
                      policy["declared_mapping_reference_bytes"] == 92541726)
    supersedes = plan.get("supersedes", {})
    previous_path = supersedes.get("path", "").replace("\\", "/")
    _need(0 < policy["max_source_bytes"] <= 10 * 1024**3, "Source byte cap exceeds 10 GiB")
    if policy["max_source_bytes"] > 5 * 1024**3:
        _need(full_inventory and previous_path.endswith(("DEVELOPMENT-INPUT-PLAN-v2.json", "DEVELOPMENT-INPUT-PLAN-v3.json")),
              "Expanded cap requires exact v3 full-inventory metadata declaration")
    wall = policy["selection_wall_seconds"]
    _need(0 < wall <= 600, "Preparation deadline exceeds 600 seconds")
    if wall > 120:
        _need(full_inventory and plan_sha256 == V4_PLAN_SHA256 and
              previous_path.endswith("DEVELOPMENT-INPUT-PLAN-v3.json") and
              supersedes.get("sha256") == "b6afc39926f50cfa3396daff0c786568f0c35d1a8776d4b4a15ee4edbbadb467",
              "Expanded preparation deadline requires exact approved v4 plan and complete inventory")
    index = catalog_index(catalog)
    selected = []
    for item in inspection["files"]:
        node = item["source"]
        dataset, path = node["dataset_id"], node["path"]
        allowed = (dataset == "hgnc_symbols" or
                   dataset == "ot_target" and node["release_id"] == policy["release"] or
                   dataset == "ot_evidence" and node["release_id"] == policy["release"] and
                   ("/evidence/sourceId=europepmc/" in path or
                    "/supplemental-20261017T064802Z/europepmc/" in path))
        if not allowed:
            continue
        _need(node.get("computed_at") is None and not node.get("parents") and
              node.get("method_id") is None and node.get("method_version") is None,
              "Original-only lineage excludes derived/reference/response ancestry")
        _need(dataset in index and node["role"] in index[dataset].get("roles", ()) and
              node["role"] in ("agent_evidence", "reference") and
              "evaluation_only" not in index[dataset].get("roles", ()),
              "Catalog/role denies original input")
        _need(node.get("receipt_path", "").startswith("manifests/receipt-archive/") and
              node.get("receipt_sha256"), "Archived original receipt required")
        _need(item["schema_sha256"] == fingerprint(item["columns"]),
              "Inspection column fingerprint differs")
        selected.append(item)
    ids = [item["source"]["source_id"] for item in selected]
    paths = [item["source"]["path"] for item in selected]
    _need(len(ids) == len(set(ids)) and len(paths) == len(set(paths)), "Duplicate inventory source/path")
    counts = {key: sum(i["source"]["dataset_id"] == key for i in selected)
              for key in ("ot_evidence", "ot_target", "hgnc_symbols")}
    _need(counts == {"ot_evidence": policy["declared_evidence_files"],
                    "ot_target": 10, "hgnc_symbols": 1}, "Pinned inventory counts differ")
    _need(counts["ot_evidence"] <= policy["max_existing_evidence_files"] <= 100,
          "Evidence file count cap exceeded")
    evidence_bytes = sum(i["bytes"] for i in selected if i["source"]["dataset_id"] == "ot_evidence")
    mapping_bytes = sum(i["bytes"] for i in selected if i["source"]["dataset_id"] != "ot_evidence")
    _need(evidence_bytes == policy["declared_evidence_bytes"] and
          mapping_bytes == policy["declared_mapping_reference_bytes"], "Pinned inventory bytes differ")
    _need(evidence_bytes + mapping_bytes <= policy["max_source_bytes"], "Source byte cap exceeded")
    return sorted(selected, key=lambda item: item["source"]["source_id"])


def _receipt(item, path, receipt_path, deadline):
    node = item["source"]
    original = hash_file(path, deadline)
    _need(original["sha256"] == node["sha256"] and original["bytes"] == item["bytes"],
          "Original hash/bytes differ: " + node["source_id"])
    receipt_hash = hash_file(receipt_path, deadline)
    _need(receipt_hash["sha256"] == node["receipt_sha256"], "Archived receipt hash differs")
    receipt = parse_json(read_file(receipt_path, deadline, 1024 * 1024))
    _need(receipt.get("status") == "completed" and
          receipt.get("dataset_id") == node["dataset_id"] and
          receipt.get("release_id") == node["release_id"] and
          receipt.get("sha256") == node["sha256"] and
          receipt.get("bytes") == original["bytes"] and
          receipt.get("relative_path", "").replace("\\", "/") == node["path"] and
          receipt.get("url") == node["source_url"], "Archived receipt identity/status differs")
    availability = node["availability"]
    _need(availability["basis"] == "public_download_receipt" and
          availability["evidence_ref"] == node["receipt_sha256"],
          "Original availability receipt binding differs")
    # Offset timestamps in original receipts are legitimate; compare instants.
    observed = datetime.fromisoformat(receipt["completed_at_utc"].replace("Z", "+00:00"))
    known = datetime.fromisoformat(availability["known_public_by"].replace("Z", "+00:00"))
    _need(observed.tzinfo is not None and known.tzinfo is not None and known >= observed,
          "Original receipt availability bound differs")
    return dict(source_id=node["source_id"], dataset_id=node["dataset_id"],
                release_id=node["release_id"], path=node["path"], sha256=node["sha256"],
                bytes=original["bytes"], role=node["role"], parents=[],
                receipt_path=node["receipt_path"], receipt_sha256=node["receipt_sha256"],
                receipt_bytes=receipt_hash["bytes"], schema_sha256=item["schema_sha256"],
                availability=availability, temporal_classification=node["temporal_classification"])


def _schema(item, path, pq):
    if item["source"]["dataset_id"] == "hgnc_symbols":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            columns = next(csv.reader(stream, delimiter="\t"))
    else:
        parquet = pq.ParquetFile(path)
        columns = parquet.schema_arrow.names
        _need(parquet.metadata.num_rows == item["rows"], "Original row count differs")
    _need(columns == item["columns"] and fingerprint(columns) == item["schema_sha256"],
          "Original schema differs")


def _parquet_filtered(item, path, projection, predicate, deadline, pa, pc, pq):
    """Filter Arrow arrays first; Python sees only matching projected rows."""
    parquet = pq.ParquetFile(path)
    columns = [name for name in projection if name in parquet.schema_arrow.names]
    for group in range(parquet.num_row_groups):
        offset = 0
        for batch in parquet.iter_batches(row_groups=[group], columns=columns, batch_size=4096):
            deadline_check(deadline)
            mask = pc.fill_null(predicate(batch), False)
            indices = pc.indices_nonzero(mask).to_pylist()
            rows = batch.filter(mask).to_pylist()
            for index, row in zip(indices, rows):
                yield dict(source_id=item["source"]["source_id"],
                           locator=dict(format="parquet", row_group=group, row=offset + index), row=row)
            offset += batch.num_rows


def resolve_cases(cases, hgnc_rows, target_rows):
    """Resolve exact approved HGNC symbol/Ensembl and matching target records."""
    resolved, blocked = {}, {}
    for case in cases:
        key, symbol = case["case_id"], case["target_symbol"]
        hg = [r for r in hgnc_rows if r["row"].get("symbol") == symbol and
              r["row"].get("status") == "Approved"]
        ot = [r for r in target_rows if r["row"].get("approvedSymbol") == symbol]
        if len(hg) != 1 or len(ot) != 1 or not hg[0]["row"].get("ensembl_gene_id") or \
                hg[0]["row"]["ensembl_gene_id"] != ot[0]["row"].get("id") or \
                case.get("target_id") not in (None, ot[0]["row"].get("id")):
            blocked[key] = "missing_or_conflicting_approved_canonical_mapping"
        else:
            resolved[key] = dict(target_id=ot[0]["row"]["id"], mappings=[hg[0], ot[0]])
    return resolved, blocked


def select_records(rows, maximum=2):
    """First distinct IDs lexically; an inconsistent duplicate blocks the case."""
    _need(maximum == 2, "Fixed two-record selection required")
    by_id = {}
    count = 0
    for candidate in rows:
        _need(set(candidate["row"]).issubset(EVIDENCE_FIELDS), "Undeclared evidence projection")
        identifier = candidate["row"].get("id")
        _need(type(identifier) is str and identifier, "Native evidence ID is required")
        _need(candidate["row"].get("datasourceId") == "europepmc" and
              candidate["row"].get("datatypeId") == "literature", "Evidence provider/type differs from pinned partition")
        count += 1
        _need(count <= MAX_MATCHING_ROWS, "Matching-row resource cap exceeded")
        old = by_id.get(identifier)
        if old is not None:
            _need(canonical(old["row"]) == canonical(candidate["row"]),
                  "Conflicting duplicate native evidence ID blocks case")
        locator_key = lambda r: (r["source_id"], r["locator"]["row_group"], r["locator"]["row"])
        if old is None or locator_key(candidate) < locator_key(old):
            by_id[identifier] = candidate
    return [by_id[key] for key in sorted(by_id)[:maximum]], dict(matching_rows=count, distinct_ids=len(by_id))


def _publication(row, cutoff):
    for field in ("publicationDate", "evidenceDate"):
        value = row.get(field)
        if value in (None, ""):
            continue
        _need(type(value) is str, "Native publication/evidence date must be an ISO string")
        try:
            observed = (datetime.combine(date.fromisoformat(value), day_time.max, timezone.utc)
                        if len(value) == 10 else _utc(value))
        except ValueError as error:
            raise ContractError("Native publication/evidence date is invalid") from error
        _need(observed <= cutoff, "Native publication/evidence date is after cutoff")


def make_packet(case, condition, resolution, selected, nodes, proofs, *, cutoff, plan_sha256):
    """Build a neutral task, original rows and value-free literal binding slots."""
    missing = condition["kind"] == "synthetic_input_withholding"
    _need(not missing or condition.get("records_available") == 0 and
          condition.get("collection_status") == "incomplete" and
          condition.get("biological_absence") is False, "Invalid controlled withholding condition")
    selected = [] if missing else selected
    target_mapping = resolution["mappings"][1]
    target_node = nodes[target_mapping["source_id"]]
    scope = dict(target_id=resolution["target_id"], indication_id=case["indication_id"],
                 target_namespace_version="OpenTargets-25.09:target:" + target_node["sha256"],
                 indication_namespace_version="OpenTargets-25.09:diseaseId:EFO:upstream-version-unknown",
                 action=case["action"], modality=case["modality"], tissue=case["tissue"])
    records, fields, source_rows = [], [], []
    for index, item in enumerate(selected):
        _need(set(item["row"]).issubset(EVIDENCE_FIELDS), "Undeclared evidence projection")
        _need(item["row"].get("targetId") == scope["target_id"] and
              item["row"].get("diseaseId") == scope["indication_id"], "Selected pair differs")
        _need(item["row"].get("datasourceId") == "europepmc" and item["row"].get("datatypeId") == "literature",
              "Evidence provider/type differs from pinned partition")
        _publication(item["row"], _utc(cutoff))
        key = "record-" + str(index + 1)
        records.append(dict(record_key=key, source_id=item["source_id"], locator=item["locator"],
                            identity={k: item["row"][k] for k in ("id", "targetId", "diseaseId")}))
        source_rows.append(dict(record_key=key, **item))
        for name in REQUESTED_FIELDS:
            group = "identity" if name == "id" else "cell-context" if name == "cellType" else "reported-dates"
            fields.append(dict(record_key=key, field=name, family=FAMILIES[name], group=key + ":" + group,
                               unit_field=None, empty_policy="unknown"))
    collection = dict(status="incomplete" if missing else "selected_records" if records else "zero_matches_selected_collection",
                      reason=(f"Synthetic withholding: all {case['target_symbol']} evidence records are unavailable in this condition; "
                              "collection is incomplete and makes no claim of biological absence."
                              if missing else "Only the pinned selected EuropePMC file inventory and first two distinct lexical IDs per exact pair; no whole-release or biological-absence claim."))
    task = dict(schema_version=1, task_id="p04-source-facts:" + condition["id"], scope=scope, cutoff=cutoff,
                profile="contemporary_assessment", primary_families=["identity_linkage", "reported_context"],
                records=records, fields=fields, joins=[], collection=collection)
    task_hash = fingerprint(task)
    slots = []
    for field in fields:
        record = next(r for r in records if r["record_key"] == field["record_key"])
        node = nodes[record["source_id"]]
        source = dict(source_id=node["source_id"], sha256=node["sha256"], release_id=node["release_id"],
                      locator=record["locator"], field=field["field"])
        identity = dict(task_sha256=task_hash, scope=scope, record_key=record["record_key"], source=source)
        slots.append(dict(fact_id="fact:" + fingerprint(identity), record_key=record["record_key"],
                          field=field["field"], source=source))
    _need(len({slot["fact_id"] for slot in slots}) == len(slots), "Duplicate fact slots")
    visible_nodes = {item["source_id"] for item in selected}
    if not missing:
        visible_nodes.update(item["source_id"] for item in resolution["mappings"])
    return dict(schema_version=1, packet_type=METHOD, role="agent_evidence", agent_visible=True,
                condition_id=condition["id"], case_id=case["case_id"], neutral_task=task,
                task_sha256=task_hash, source_records=source_rows, fact_skeleton=slots,
                mapping_records=[] if missing else resolution["mappings"],
                source_proofs=[p for p in proofs if p["source_id"] in visible_nodes],
                source_nodes=[nodes[key] for key in sorted(visible_nodes)],
                selection_inventory_sha256=fingerprint(dict(nodes=nodes, proofs=proofs)),
                namespace_provenance=dict(target_id_system="Ensembl", target_upstream_version="unknown",
                                          indication_id_system="EFO", indication_upstream_version="unknown",
                                          mapping_policy="Exact approved HGNC symbol/Ensembl plus matching Open Targets target record; no disease metadata mapping was read."),
                condition=dict(kind=condition["kind"], synthetic=missing, independent_biomedical_context=False if missing else True,
                               biological_absence_claim=False),
                instruction="Report only requested literal fields from supplied original source records using typed_facts_v1. Preserve exact source bindings, native null/empty/absent distinctions, and the collection scope. Do not infer biological effects or absence.",
                output_contract=dict(wire_format="typed_facts_v1",
                                     top_level_keys=["schema_version", "task_id", "task_sha256", "status", "facts", "collection_status", "reason"],
                                     fact_keys=["fact_id", "value", "unit", "source", "unknown_reason"],
                                     status_values=["answered", "partial", "abstained", "insufficient_input"]),
                lineage=dict(parents=[dict(kind="eligible_original", source_id=key, sha256=nodes[key]["sha256"]) for key in sorted(nodes)] +
                                     [dict(kind="neutral_input_plan", sha256=plan_sha256)],
                             method=METHOD, reference_inputs=[], generation_authority=False))


def prepare_generation_inputs(plan_path, inspection_path, catalog_path, *, expected_plan_sha256,
                              workspace_root, approved_raw_root, cutoff, deadline, progress=None):
    """Finite preparation, with all inventory authentication before value scans.

    Returns serializable packets and replay metadata. Writing/sealing is the
    caller's responsibility. Caller supplies the original root and exact plan
    hash as trusted authority; metadata cannot grant an additional source root.
    """
    started = time.monotonic()
    def emit(event, **details):
        if progress is not None:
            progress(event, **details)
        deadline_check(deadline)
    deadline_check(deadline)
    emit("build_stage", stage="metadata_validation")
    _need(Path(workspace_root).is_absolute() and Path(approved_raw_root).is_absolute(), "Explicit absolute roots required")
    metadata_paths = [Path(plan_path), Path(inspection_path), Path(catalog_path)]
    with stable_files(metadata_paths, deadline=deadline):
        plan_hash = hash_file(plan_path, deadline)["sha256"]
        _need(plan_hash == expected_plan_sha256, "Neutral plan hash differs")
        plan = parse_json(read_file(plan_path, deadline, 1024 * 1024))
        _plan_contract(plan, cutoff)
        policy = plan["source_policy"]
        _need(deadline - started <= policy["selection_wall_seconds"] + 0.01, "Caller deadline exceeds preparation bound")
        _need(hash_file(inspection_path, deadline)["sha256"] == policy["inspection_sha256"], "Pinned inspection hash differs")
        _need(hash_file(catalog_path, deadline)["sha256"] == policy["catalog_sha256"], "Pinned catalog hash differs")
        inspection = parse_json(read_file(inspection_path, deadline, 32 * 1024 * 1024))
        catalog = parse_json(read_file(catalog_path, deadline, 8 * 1024 * 1024))
        inventory = selected_inventory(plan, inspection, catalog, plan_sha256=plan_hash)
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
        _need(pa.__version__ == "21.0.0", "Generation input preparation requires Arrow 21.0.0")
        nodes = {item["source"]["source_id"]: item["source"] for item in inventory}
        paths = {key: checked_path(Path(approved_raw_root), node["path"]) for key, node in nodes.items()}
        receipts = {key: checked_path(Path(approved_raw_root), node["receipt_path"]) for key, node in nodes.items()}
        timestamp = _utc(cutoff)
        snapshot = Snapshot(2, "p04-original-inputs:" + plan_hash, "contemporary_assessment", timestamp.date(), False, (),
                            tuple(decode(SourceNode, node) for node in nodes.values()), str(approved_raw_root), {}, timestamp)
        graph = InputGraph(snapshot, Path(workspace_root), catalog_index(catalog))
        from types import SimpleNamespace
        _need(graph.exclusion(tuple(nodes), SimpleNamespace(cutoff=timestamp)) is None,
              "Original inventory is not temporally eligible")
        with stable_files(tuple(paths.values()) + tuple(receipts.values()), deadline=deadline):
            emit("build_stage", stage="verify_original_inventory")
            proofs = []
            # No original value scan is permitted until this whole loop succeeds.
            for item in inventory:
                deadline_check(deadline)
                key = item["source"]["source_id"]
                proof = _receipt(item, paths[key], receipts[key], deadline)
                _schema(item, paths[key], pq)
                proofs.append(proof)
                emit("build_progress", stage="verify_original_inventory", source_id=key,
                     verified_sources=len(proofs), total_sources=len(inventory),
                     verified_source_bytes=sum(p["bytes"] for p in proofs))
            emit("build_stage", stage="resolve_identifiers")
            symbols = [case["target_symbol"] for case in plan["cases"]]
            hgnc_rows, target_rows = [], []
            for item in inventory:
                key, dataset = item["source"]["source_id"], item["source"]["dataset_id"]
                if dataset == "hgnc_symbols":
                    with paths[key].open(encoding="utf-8-sig", newline="") as stream:
                        for index, row in enumerate(csv.DictReader(stream, delimiter="\t")):
                            deadline_check(deadline)
                            if row.get("symbol") in symbols:
                                projected = {name: row[name] for name in ("hgnc_id", "symbol", "status", "ensembl_gene_id") if name in row}
                                hgnc_rows.append(dict(source_id=key, locator=dict(format="tsv", row=index), row=projected))
                elif dataset == "ot_target":
                    target_rows.extend(_parquet_filtered(item, paths[key], ("id", "approvedSymbol"),
                        lambda batch: pc.is_in(batch.column("approvedSymbol"), value_set=pa.array(symbols)), deadline, pa, pc, pq))
            resolutions, blocked = resolve_cases(plan["cases"], hgnc_rows, target_rows)
            emit("build_stage", stage="scan_evidence")
            matches = {key: [] for key in resolutions}
            scanned_files, scanned_bytes = 0, 0
            for item in inventory:
                if item["source"]["dataset_id"] != "ot_evidence":
                    continue
                _need(all(name in item["columns"] for name in ("id", "targetId", "diseaseId")),
                      "Evidence identity fields are missing")
                def predicate(batch):
                    masks = [pc.and_(pc.equal(batch.column("targetId"), resolutions[case["case_id"]]["target_id"]),
                                     pc.equal(batch.column("diseaseId"), case["indication_id"]))
                             for case in plan["cases"] if case["case_id"] in resolutions]
                    mask = pa.array([False] * batch.num_rows) if not masks else masks[0]
                    for extra in masks[1:]:
                        mask = pc.or_(mask, extra)
                    return mask
                for candidate in _parquet_filtered(item, paths[item["source"]["source_id"]], EVIDENCE_FIELDS,
                                                     predicate, deadline, pa, pc, pq):
                    for case in plan["cases"]:
                        case_id = case["case_id"]
                        if case_id in resolutions and candidate["row"].get("targetId") == resolutions[case_id]["target_id"] and candidate["row"].get("diseaseId") == case["indication_id"]:
                            _need(len(matches[case_id]) < MAX_MATCHING_ROWS, "Matching-row resource cap exceeded")
                            matches[case_id].append(candidate)
                scanned_files += 1
                scanned_bytes += item["bytes"]
                emit("build_progress", stage="scan_evidence", source_id=item["source"]["source_id"],
                     scanned_evidence_files=scanned_files, scanned_evidence_bytes=scanned_bytes,
                     matching_rows=sum(len(rows) for rows in matches.values()))
            emit("build_stage", stage="assemble_packets")
            chosen, selection = {}, {}
            for case_id, rows in matches.items():
                try:
                    chosen[case_id], selection[case_id] = select_records(rows)
                except ContractError as error:
                    blocked[case_id] = str(error)
            packets = {}
            for condition in plan["conditions"]:
                case = next(c for c in plan["cases"] if c["case_id"] == condition["case"])
                key = case["case_id"]
                if key not in blocked:
                    packets[condition["id"]] = make_packet(case, condition, resolutions[key], chosen[key], nodes, proofs,
                                                           cutoff=cutoff, plan_sha256=plan_hash)
            deadline_check(deadline)
            emit("build_stage", stage="inputs_prepared")
    return dict(schema_version=1, method=METHOD, role="agent_evidence", agent_visible=True,
                plan_sha256=plan_hash, inspection_sha256=policy["inspection_sha256"], catalog_sha256=policy["catalog_sha256"],
                packets=packets, source_snapshot=encode(snapshot), inventory_proofs=proofs,
                blocked_cases=blocked, selection=selection,
                inventory_summary=dict(files=len(inventory), source_bytes=sum(i["bytes"] for i in inventory)),
                elapsed_seconds=time.monotonic() - started, reference_inputs=[], model_calls=0,
                generation_authority=False)
