"""Source-inclusive, evaluator-only literal reporting references.

The token protects against accidental construction, not a hostile Python caller.
Catalogs and explicit deny lists are trusted provenance inputs; this module does
not detect undisclosed response ancestry by inspecting biomedical text.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import math
from pathlib import Path
import re
from types import SimpleNamespace

from tether_engine.contracts import Profile, Snapshot
from tether_engine.provenance import InputGraph, catalog_index
from tether_engine.serde import ContractError, canonical, encode, fingerprint, freeze, parse_json
from tether_engine.wire import same_json
from .source_rows import parquet_row
from .stable_read import checked_path, deadline_check, hash_file, read_file, stable_files


FAMILIES = ("identity_linkage", "reported_context", "reported_measurement", "provider_metric")
FIELD_FAMILIES = {
    **dict.fromkeys((
        "id", "targetId", "target_id", "diseaseId", "indication_id", "datasourceId",
        "datatypeId", "literature", "pmcIds", "studyId", "studyLocusId", "cohortId",
        "variantId", "variantRsId", "variantFromSourceId", "variantHgvsId",
        "variantFunctionalConsequenceId", "ancestryId", "biologicalModelId",
        "targetInModelEnsemblId", "targetInModelMgiId",
    ), "identity_linkage"),
    **dict.fromkeys((
        "publicationDate", "publicationYear", "evidenceDate", "annotationDate",
        "ancestry", "cellType", "biosamplesFromSource", "alleleOrigins",
        "allelicRequirements", "diseaseCellLines", "sex", "studyCases",
        "studyCasesWithQualifyingVariants", "studySampleSize", "sampleSize",
        "targetModulation", "variantEffect", "directionOnTrait", "chromosome", "position",
    ), "reported_context"),
    **dict.fromkeys((
        "beta", "standardError", "zScore", "betaConfidenceIntervalLower",
        "betaConfidenceIntervalUpper", "oddsRatio", "oddsRatioConfidenceIntervalLower",
        "oddsRatioConfidenceIntervalUpper", "pValueMantissa", "pValueExponent",
        "pValue", "adjustedPValue", "log2FoldChangeValue",
    ), "reported_measurement"),
    **dict.fromkeys(("score", "resourceScore", "log2FoldChangePercentileRank"), "provider_metric"),
}
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_TASK_BYTES = 1024 * 1024
_TOKEN = object()
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_FIELD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_DATE_FIELDS = ("publicationDate", "evidenceDate", "annotationDate")


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _text(value, label):
    _need(type(value) is str and bool(value.strip()) and len(value.encode("utf-8")) <= 8192,
          "Invalid " + label)
    return value


def _json(value):
    if isinstance(value, Mapping):
        _need(all(type(k) is str for k in value), "JSON object keys must be strings")
        for item in value.values():
            _json(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _json(item)
    else:
        _need(value is None or type(value) in (str, bool, int, float), "Non-JSON native value")
        _need(type(value) is not float or math.isfinite(value), "Nonfinite native value")


def _exact(value, keys, label):
    _need(isinstance(value, Mapping) and set(value) == set(keys), "Invalid " + label + " fields")


def _timestamp(value):
    _text(value, "UTC cutoff")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("Invalid UTC cutoff") from error
    _need("T" in value and parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
          "Cutoff must be an exact timezone-aware UTC timestamp")
    return parsed.astimezone(timezone.utc)


def _pointer_tokens(pointer):
    _need(type(pointer) is str and len(pointer.encode("utf-8")) <= 8192,
          "Invalid JSON pointer")
    _need(pointer == "" or pointer.startswith("/"), "JSON pointer must follow RFC6901")
    tokens = pointer.split("/")[1:] if pointer else []
    _need(len(tokens) <= 128, "JSON pointer exceeds depth bound")
    for token in tokens:
        _need(not re.search(r"~(?![01])", token), "Invalid JSON pointer escape")
    return [token.replace("~1", "/").replace("~0", "~") for token in tokens]


def _field(value):
    _text(value, "literal field")
    _need(_FIELD.fullmatch(value) is not None, "Only literal original top-level fields are supported")


def _anchors(task):
    scope = task["scope"]
    result = set()
    for record in task["records"]:
        identity = record["identity"]
        if (any(identity.get(k) == scope["target_id"] for k in ("targetId", "target_id"))
                and any(identity.get(k) == scope["indication_id"] for k in ("diseaseId", "indication_id"))):
            result.add(record["record_key"])
    return result


def validate_task(task):
    """Validate the frozen finite reporting task; never read a source."""
    try:
        _json(task)
        _need(len(canonical(task)) <= MAX_TASK_BYTES, "Reporting task exceeds byte bound")
        task = encode(task)
        _exact(task, ("schema_version", "task_id", "scope", "cutoff", "profile", "primary_families",
                      "records", "fields", "joins", "collection"), "task")
        _need(type(task["schema_version"]) is int and task["schema_version"] == 1, "Invalid task version")
        _text(task["task_id"], "task identity")
        _need(len(task["task_id"]) <= 512, "Task identity exceeds common wire bound")
        _exact(task["scope"], ("target_id", "indication_id", "target_namespace_version",
                               "indication_namespace_version", "action", "modality", "tissue"), "scope")
        for key in ("target_id", "indication_id", "target_namespace_version", "indication_namespace_version"):
            _text(task["scope"][key], key)
        for key in ("action", "modality", "tissue"):
            if task["scope"][key] is not None:
                _text(task["scope"][key], key)
        _timestamp(task["cutoff"])
        _need(task["profile"] in tuple(p.value for p in Profile), "Invalid task profile")
        primary = task["primary_families"]
        _need(isinstance(primary, list) and primary and all(type(x) is str and x in FAMILIES for x in primary)
              and len(set(primary)) == len(primary), "Invalid primary families")
        for key, maximum in (("records", 64), ("fields", 512), ("joins", 32)):
            _need(isinstance(task[key], list) and len(task[key]) <= maximum, "Invalid bounded " + key)
        _exact(task["collection"], ("status", "reason"), "collection")
        _need(task["collection"]["status"] in ("selected_records", "zero_matches_selected_collection", "incomplete", "failed_qc"),
              "Invalid collection status")
        _text(task["collection"]["reason"], "collection scope statement")
        records = {}
        for record in task["records"]:
            _exact(record, ("record_key", "source_id", "locator", "identity"), "record")
            key = _text(record["record_key"], "record key")
            _need(key not in records, "Duplicate record key")
            records[key] = record
            _text(record["source_id"], "source ID")
            _need(len(record["source_id"]) <= 512, "Source identity exceeds common wire bound")
            locator = record["locator"]
            _need(isinstance(locator, dict), "Invalid record locator")
            if locator.get("format") == "json":
                _exact(locator, ("format", "pointer"), "JSON locator")
                _pointer_tokens(locator["pointer"])
            else:
                _exact(locator, ("format", "row_group", "row"), "Parquet locator")
                _need(locator["format"] == "parquet" and all(type(locator[k]) is int and locator[k] >= 0
                      for k in ("row_group", "row")), "Invalid Parquet locator")
            identity = record["identity"]
            _need(isinstance(identity, dict) and bool(identity), "Literal record identity is required")
            for name in identity:
                _field(name)
        fields, groups = set(), {}
        for field in task["fields"]:
            _exact(field, ("record_key", "field", "family", "group", "unit_field", "empty_policy"), "field request")
            _need(field["record_key"] in records, "Field references unknown record")
            _field(field["field"])
            _need(FIELD_FAMILIES.get(field["field"]) == field["family"], "Field family differs from known-field map")
            pair = (field["record_key"], field["field"])
            _need(pair not in fields, "Duplicate requested field")
            fields.add(pair)
            group = _text(field["group"], "fact group")
            group_identity = (field["record_key"], field["family"])
            _need(group not in groups or groups[group] == group_identity, "Group crosses records or families")
            groups[group] = group_identity
            if field["unit_field"] is not None:
                _field(field["unit_field"])
            _need(field["empty_policy"] in ("unknown", "value"), "Invalid empty policy")
        join_ids = set()
        for join in task["joins"]:
            _exact(join, ("join_id", "left_record", "left_field", "right_records", "right_field",
                          "cardinality", "inventory_status"), "join")
            identity = _text(join["join_id"], "join identity")
            _need(identity not in join_ids, "Duplicate join identity")
            join_ids.add(identity)
            _need(join["left_record"] in records, "Unknown join left record")
            _field(join["left_field"])
            _field(join["right_field"])
            right = join["right_records"]
            _need(isinstance(right, list) and len(right) <= 64 and all(type(x) is str and x in records for x in right)
                  and len(set(right)) == len(right) and join["left_record"] not in right, "Invalid join candidate records")
            _need(join["cardinality"] in ("one_to_one", "one_to_many"), "Invalid join cardinality")
            _need(join["inventory_status"] in ("partial", "complete"), "Invalid join inventory status")
        if records:
            _need(task["collection"]["status"] != "zero_matches_selected_collection", "Zero-match collection cannot contain selected records")
            reachable = _anchors(task)
            _need(bool(reachable), "At least one record must literally anchor target and indication")
            while True:
                expanded = reachable | {r for j in task["joins"] if j["left_record"] in reachable for r in j["right_records"]}
                if expanded == reachable:
                    break
                reachable = expanded
            _need(reachable == set(records), "Every other record needs a declared exact-key path from scope")
        else:
            _need(not task["fields"] and not task["joins"] and task["collection"]["status"] != "selected_records",
                  "Empty references require explicit bounded missing-input collection")
        return freeze(task)
    except (KeyError, TypeError, RecursionError, OverflowError) as error:
        raise ContractError("Malformed reporting task") from error


@dataclass(frozen=True, init=False)
class VerifiedReference:
    document: Mapping
    fingerprint: str

    def __init__(self, document, *, _token=None):
        _need(_token is _TOKEN, "Reference must be compiled or source-verified")
        frozen = freeze(document)
        object.__setattr__(self, "document", frozen)
        object.__setattr__(self, "fingerprint", fingerprint(frozen))


def _selected_json(path, pointer, deadline):
    try:
        value = parse_json(read_file(path, deadline, MAX_JSON_BYTES))
        _json(value)
        for token in _pointer_tokens(pointer):
            deadline_check(deadline)
            if isinstance(value, dict):
                _need(token in value, "JSON pointer member is absent")
                value = value[token]
            elif isinstance(value, list):
                _need(re.fullmatch(r"0|[1-9][0-9]*", token) is not None, "Noncanonical JSON array index")
                index = int(token)
                _need(index < len(value), "JSON pointer array index is absent")
                value = value[index]
            else:
                raise ContractError("JSON pointer traverses a scalar")
        _need(isinstance(value, dict), "Selected source record must be an object")
        return value
    except (RecursionError, OverflowError) as error:
        raise ContractError("Source JSON exceeds native parsing bounds") from error


def _publication(record, cutoff):
    for field in _DATE_FIELDS:
        value = record.get(field)
        if value is None or value == "":
            continue
        _need(type(value) is str, "Publication/annotation date must be a literal ISO string")
        try:
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                observed = datetime.combine(date.fromisoformat(value), time.max, timezone.utc)
            else:
                observed = _timestamp(value)
        except ValueError as error:
            raise ContractError("Invalid publication/annotation date") from error
        _need(observed <= cutoff, "Publication/annotation date is after reporting cutoff")
    year = record.get("publicationYear")
    if year is not None:
        _need(type(year) is int and 1 <= year <= cutoff.year, "Invalid or future publication year")


def _binding(record, node, field):
    return dict(source_id=node.source_id, sha256=node.sha256, release_id=node.release_id,
                locator=encode(record["locator"]), field=field)


def _empty(value):
    return (type(value) is str and value == "") or (isinstance(value, (list, tuple, dict)) and not value)


def _join_reports(task, rows, nodes):
    reports, restrictions = [], {}
    requests = {r["record_key"]: r for r in task["records"]}
    fields = {key: [f for f in task["fields"] if f["record_key"] == key] for key in requests}

    def requested_signature(key):
        row = rows[key]
        return {field["field"]: dict(present=field["field"] in row, value=row.get(field["field"]),
                                     unit_field=field["unit_field"],
                                     unit_present=field["unit_field"] is not None and field["unit_field"] in row,
                                     unit_value=row.get(field["unit_field"]), empty_policy=field["empty_policy"])
                for field in fields[key]}
    for join in task["joins"]:
        left = rows[join["left_record"]]
        value = left.get(join["left_field"])
        key_available = join["left_field"] in left and value is not None and not _empty(value)
        matched = [r for r in join["right_records"] if key_available and join["right_field"] in rows[r]
                   and rows[r][join["right_field"]] is not None and not _empty(rows[r][join["right_field"]])
                   and same_json(value, rows[r][join["right_field"]])]
        status = "matched"
        if not key_available:
            status = "unavailable_key"
        elif not matched:
            status = ("missing_input_in_partial_collection" if join["inventory_status"] == "partial"
                      else "zero_matches_selected_collection")
        elif join["cardinality"] == "one_to_one" and len(matched) > 1:
            signatures = [requested_signature(r) for r in matched]
            status = ("unresolved_multiplicity" if all(same_json(s, signatures[0]) for s in signatures[1:])
                      else "conflicting_values")
        report = {key: encode(join[key]) for key in ("join_id", "left_record", "right_records", "cardinality", "inventory_status")}
        report.update(status=status, matched_records=matched,
                      matched_sources=[_binding(requests[r], nodes[requests[r]["source_id"]], join["right_field"]) for r in matched])
        reports.append(report)
        for right in join["right_records"]:
            reason = None if status == "matched" and right in matched else (
                "conflicting_join" if status == "conflicting_values" else "unavailable_join")
            restrictions.setdefault(right, []).append((join["left_record"], reason))
    # Anchors retain direct scope authority. Every declared incoming join for a
    # linked record must resolve; a chain cannot bypass an unresolved ancestor.
    anchors, state = _anchors(task), {}

    def reason(key, active):
        if key in anchors:
            return None
        if key in state:
            return state[key]
        if key in active:
            return "unavailable_join"
        failures = [r or reason(left, active | {key}) for left, r in restrictions.get(key, ())]
        result = ("conflicting_join" if "conflicting_join" in failures else
                  "unavailable_join" if any(failures) or not failures else None)
        state[key] = result
        return result

    return reports, {key: reason(key, set()) for key in requests}


def compile_reference(task, snapshot, root, catalog, *, deadline,
                      denied_source_ids=(), denied_dataset_ids=(), denied_sha256=(), approved_raw_root=None):
    """Replay finite selected records after whole-graph provenance admission.

    ``deadline`` is cooperative, not a hard OS deadline. Existing InputGraph
    checksum calls finish before the next checkpoint; stable hash/read helpers
    additionally check the deadline between bounded chunks.
    """
    task = validate_task(task)
    deadline_check(deadline)
    _need(isinstance(snapshot, Snapshot), "A v2 Snapshot object is required")
    cutoff = _timestamp(task["cutoff"])
    _need(snapshot.schema_version == 2 and snapshot.profile == task["profile"] and snapshot.origin_at is not None
          and snapshot.origin_at.tzinfo is not None and snapshot.origin_at == cutoff and snapshot.origin == cutoff.date(),
          "Task/snapshot cutoff or profile differs")
    approved_root = Path(root)
    _need(approved_root.is_absolute(), "An absolute approved source root is required")
    raw_root = Path(snapshot.raw_root or approved_root)
    _need(raw_root.is_absolute(), "Snapshot raw root must be absolute")
    if approved_raw_root is None:
        _need(raw_root.absolute() == approved_root.absolute(), "A different raw root requires explicit approval")
    else:
        explicit_raw_root = Path(approved_raw_root)
        _need(explicit_raw_root.is_absolute() and explicit_raw_root.absolute() == raw_root.absolute(),
              "Explicit approved raw root differs from snapshot raw root")
    _need(isinstance(catalog, Mapping), "An explicit trusted source catalog is required")
    index = catalog_index(catalog) if "datasets" in catalog else catalog
    deny_sets = []
    for values, hashes in ((denied_source_ids, False), (denied_dataset_ids, False), (denied_sha256, True)):
        _need(not isinstance(values, (str, bytes)), "Deny lists must be explicit sequences")
        values = tuple(values)
        for value in values:
            _text(value, "denied source identity")
            _need(not hashes or _SHA.fullmatch(value) is not None, "Invalid denied source hash")
        deny_sets.append(set(values))
    for node in snapshot.sources:
        _need(node.source_id not in deny_sets[0] and node.dataset_id not in deny_sets[1] and node.sha256 not in deny_sets[2],
              "Denied response/evaluator source ancestry")
    nodes, proofs, rows = {}, [], {}
    if snapshot.sources:
        graph = InputGraph(snapshot, approved_root, index)
        refs = tuple(graph.nodes)
        # These checks, including every ancestor's role, precede all byte reads.
        _need(graph.exclusion(refs, SimpleNamespace(cutoff=cutoff)) is None,
              "Source graph is not temporally eligible at reporting cutoff")
        paths, receipts = {}, {}
        for key, node in graph.nodes.items():
            base = approved_root if node.computed_at is not None else Path(snapshot.raw_root or approved_root)
            paths[key] = checked_path(base, node.path)
            _need(paths[key] == graph.path(node), "Source path alias differs")
            if node.receipt_path:
                receipts[key] = checked_path(Path(snapshot.raw_root or approved_root), node.receipt_path)
        for record in task["records"]:
            _need(record["source_id"] in graph.nodes, "Selected source is missing from graph")
            _need(len(graph.nodes[record["source_id"]].release_id) <= 512,
                  "Selected source release exceeds common wire bound")
        records_by_key = {record["record_key"]: record for record in task["records"]}
        for join in task["joins"]:
            left_source = graph.nodes[records_by_key[join["left_record"]]["source_id"]]
            _need(all(graph.nodes[records_by_key[key]["source_id"]].release_id == left_source.release_id
                      for key in join["right_records"]), "Exact selected-row joins require the same source release")
        all_paths = tuple(paths.values()) + tuple(receipts.values())
        with stable_files(all_paths, deadline=deadline):
            deadline_check(deadline)
            verified = graph.verify(refs, {})
            deadline_check(deadline)
            for proof in verified:
                key = proof["artifact_id"]
                node = graph.nodes[key]
                source_hash = hash_file(paths[key], deadline)
                _need(source_hash["sha256"] == node.sha256, "Stable original checksum differs")
                item = dict(encode(proof), bytes=source_hash["bytes"], availability=encode(node.availability),
                            temporal_classification=node.temporal_classification.value)
                # Bind logical paths while roots remain explicit runtime authority.
                item["path"] = node.path
                item["path_scope"] = "derived" if node.computed_at is not None else "raw"
                if key in receipts:
                    receipt_hash = hash_file(receipts[key], deadline)
                    _need(receipt_hash["sha256"] == node.receipt_sha256, "Stable receipt checksum differs")
                    item["receipt_bytes"] = receipt_hash["bytes"]
                    item["receipt_path"] = node.receipt_path
                proofs.append(item)
            for record in task["records"]:
                key, source_id, locator = record["record_key"], record["source_id"], record["locator"]
                node, path = graph.nodes[source_id], paths[source_id]
                if locator["format"] == "json":
                    row = _selected_json(path, locator["pointer"], deadline)
                else:
                    import pyarrow as pa
                    import pyarrow.parquet as pq
                    _need(pa.__version__ == "21.0.0", "Parquet reporting replay requires Arrow 21.0.0")
                    deadline_check(deadline)
                    available = pq.ParquetFile(path).schema_arrow.names
                    needed = set(record["identity"]) | set(_DATE_FIELDS) | {"publicationYear", "targetId", "target_id", "diseaseId", "indication_id"}
                    for field in task["fields"]:
                        if field["record_key"] == key:
                            needed.add(field["field"])
                            if field["unit_field"] is not None:
                                needed.add(field["unit_field"])
                    for join in task["joins"]:
                        if join["left_record"] == key:
                            needed.add(join["left_field"])
                        if key in join["right_records"]:
                            needed.add(join["right_field"])
                    projection = tuple(name for name in available if name in needed)
                    _need(bool(projection), "No identity fields are present in Parquet schema")
                    row = parquet_row(path, {"row_group": locator["row_group"], "row": locator["row"]},
                                      projection, deadline_check=lambda: deadline_check(deadline))
                _json(row)
                for name, value in record["identity"].items():
                    _need(name in row and same_json(row[name], value), "Original record identity differs")
                for name, scope_key in (("targetId", "target_id"), ("target_id", "target_id"),
                                        ("diseaseId", "indication_id"), ("indication_id", "indication_id")):
                    if name in row and row[name] is not None:
                        _need(same_json(row[name], task["scope"][scope_key]), "Original record reporting scope differs")
                _publication(row, cutoff)
                rows[key] = row
            nodes = graph.nodes
            deadline_check(deadline)
    else:
        _need(not task["records"], "Selected source graph cannot be empty")
    joins, blocked = _join_reports(task, rows, nodes)
    requests = {record["record_key"]: record for record in task["records"]}
    facts = []
    for field in task["fields"]:
        record = requests[field["record_key"]]
        row, node = rows[field["record_key"]], nodes[record["source_id"]]
        name, reason = field["field"], blocked[field["record_key"]]
        value, unit = row.get(name), None
        if field["unit_field"] is not None:
            unit = row.get(field["unit_field"])
            _need(unit is None or (type(unit) is str and bool(unit.strip())), "Native unit must be a nonblank string or null")
        if task["collection"]["status"] == "failed_qc":
            reason = "failed_qc"
        if reason is None:
            reason = ("field_not_in_schema" if name not in row else "null_source_value" if value is None else
                      "empty_source_value" if _empty(value) and field["empty_policy"] == "unknown" else None)
        if reason is None and field["family"] == "reported_measurement":
            _need(type(value) in (int, float) and (type(value) is not float or math.isfinite(value)),
                  "Native measurement failed QC: a finite number excluding Boolean is required")
            _need(name != "pValueExponent" or type(value) is int,
                  "Native measurement failed QC: pValueExponent must be an integer")
        if reason is not None:
            value = None
        binding = _binding(record, node, name)
        identity = dict(task_sha256=fingerprint(task), scope=encode(task["scope"]), record_key=field["record_key"], source=binding)
        facts.append(dict(fact_id="fact:" + fingerprint(identity), record_key=field["record_key"], field=name,
                          family=field["family"], group=field["group"], value=value, unit=unit,
                          source=binding, unknown_reason=reason))
    document = dict(schema_version=1, task_id=task["task_id"], task_sha256=fingerprint(task), role="evaluation_only",
                    agent_visible=False, scope=encode(task["scope"]), cutoff=task["cutoff"], profile=task["profile"],
                    primary_families=encode(task["primary_families"]), collection=encode(task["collection"]), facts=facts,
                    joins=joins, source_proofs=proofs,
                    method=dict(code_id="tether_engine.study.source_fact_sources", version="1", transform="literal_field.v1",
                                task=encode(task), json_read_max_bytes=MAX_JSON_BYTES,
                                field_family_map_sha256=fingerprint(FIELD_FAMILIES),
                                scientific_validation="not_established", linked_measurement_scope="source_locus_only"))
    snapshot_policy = encode(snapshot)
    snapshot_policy["raw_root"] = None
    document["method"].update(catalog_sha256=fingerprint(index),
                              source_snapshot_sha256=fingerprint(snapshot_policy),
                              deny_policy=dict(source_ids=sorted(deny_sets[0]), dataset_ids=sorted(deny_sets[1]),
                                               sha256=sorted(deny_sets[2])))
    # Close the compiler/adapter boundary: a reference must be exactly expressible
    # in the same finite wire used by every arm. This in-memory projection is a
    # structural check, not a generated answer or an empirical model result.
    from .source_fact_adapters import adapt_output
    projection = dict(schema_version=1, task_id=task["task_id"], task_sha256=fingerprint(task),
                      status="answered" if facts else "insufficient_input",
                      facts=[{key: fact[key] for key in ("fact_id", "value", "unit", "source", "unknown_reason")}
                             for fact in facts], collection_status=task["collection"]["status"],
                      reason=None if facts else "No selected facts; collection-bounded missing input.")
    adapted = adapt_output(canonical(projection), wire_format="typed_facts_v1", task_id=task["task_id"],
                           task_sha256=fingerprint(task))
    _need(adapted["status"] == "scorable", "Reference exceeds common wire representation: " + str(adapted["error"]))
    document["method"]["projection_wire_verified"] = True
    deadline_check(deadline)
    return VerifiedReference(document, _token=_TOKEN)


def verify_reference(document, expected_sha256, task, snapshot, root, catalog, *, deadline,
                     denied_source_ids=(), denied_dataset_ids=(), denied_sha256=(), approved_raw_root=None):
    """Authenticate a retained document, then reconstruct it from admitted bytes."""
    _need(type(expected_sha256) is str and _SHA.fullmatch(expected_sha256) is not None,
          "An independent exact reference hash is required")
    _need(fingerprint(document) == expected_sha256, "Retained reference hash differs")
    verified = compile_reference(task, snapshot, root, catalog, deadline=deadline,
                                 denied_source_ids=denied_source_ids, denied_dataset_ids=denied_dataset_ids,
                                 denied_sha256=denied_sha256, approved_raw_root=approved_raw_root)
    _need(canonical(document) == canonical(verified.document), "Reference differs from source-inclusive replay")
    return verified
