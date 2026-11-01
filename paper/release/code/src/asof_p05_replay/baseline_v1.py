"""Pure P05 literal/abstain reconstruction from admitted source-only arguments.

No filesystem, reference, comparison bridge or expected hash is available here.
Provenance admission belongs to policy_session and the separately trusted caller.
"""
from collections.abc import Mapping

from asof.contracts import Snapshot
from asof.serde import ContractError, canonical, encode, fingerprint
from asof.study.source_fact_adapters import adapt_output
from asof.study.source_fact_sources import validate_task
from asof.wire import same_json


def need(condition, message):
    if not condition:
        raise ContractError(message)


def literal_report(task, snapshot, groups, always_abstain=False):
    """Return the exact frozen P05 wire; JSON controls retain absent fields.

    The declared original view is checked but does not grant temporal/role source
    authority. Deliberately untrusted controls are evaluated by separate guards.
    """
    need(type(always_abstain) is bool and isinstance(snapshot, Snapshot), "Invalid baseline arguments")
    task = encode(validate_task(task))
    need(snapshot.schema_version == 2 and snapshot.origin_at is not None and
         snapshot.origin_at.isoformat() == task["cutoff"] and snapshot.profile.value == task["profile"], "Task/source snapshot cutoff or profile differs")
    need(task["primary_families"] == ["reported_measurement"] and
         all(task["scope"][key] is None for key in ("action", "modality", "tissue")) and
         all(task["scope"][key] == "unknown" for key in ("target_namespace_version", "indication_namespace_version")), "Unsupported P05 reporting scope")
    need(all(field["unit_field"] is None and field["empty_policy"] == "unknown" for field in task["fields"]), "Only native null-unit requests supported")
    need(isinstance(groups, Mapping) and set(groups) == {"gwas_credible_sets", "credible_set"}, "Complete source-family groups required")
    originals = list(groups["gwas_credible_sets"]) + list(groups["credible_set"])
    need(len(originals) == len(task["records"]), "Complete packet record inventory differs")
    nodes = {node.source_id: node for node in snapshot.sources}
    need(len(nodes) == len(snapshot.sources), "Duplicate source node")
    rows, anchors, restrictions = {}, set(), {}
    for request, original in zip(task["records"], originals):
        key = request["record_key"]
        need(isinstance(original, Mapping) and isinstance(original.get("values"), Mapping) and
             original["source_id"] == request["source_id"] and same_json(original["locator"], request["locator"]) and
             request["source_id"] in nodes, "Source row/locator inventory differs")
        node = nodes[request["source_id"]]
        need(node.role in ("agent_evidence", "reference") and not node.parents and node.computed_at is None, "Selected generation node is not a declared original")
        need(all(name in original["values"] and same_json(original["values"][name], value) for name, value in request["identity"].items()), "Native record identity differs")
        rows[key] = original["values"]
        restrictions[key] = []
        if request["identity"].get("targetId") == task["scope"]["target_id"] and request["identity"].get("diseaseId") == task["scope"]["indication_id"]:
            anchors.add(key)
    records = {record["record_key"]: record for record in task["records"]}
    for join in task["joins"]:
        need(join["cardinality"] == "one_to_many" and join["inventory_status"] == "complete" and
             join["left_record"] in anchors and join["left_field"] == join["right_field"] == "studyLocusId", "Unsupported P05 join shape")
        left = rows[join["left_record"]].get("studyLocusId")
        for right in join["right_records"]:
            right_value = rows[right].get("studyLocusId")
            restrictions[right].append(left not in (None, "") and right_value not in (None, "") and same_json(left, right_value))
            need(nodes[records[right]["source_id"]].release_id == nodes[records[join["left_record"]]["source_id"]].release_id, "P05 joins require same release")
    facts = []
    if not always_abstain:
        for field in task["fields"]:
            record = records[field["record_key"]]
            node = nodes[record["source_id"]]
            source = {"source_id": node.source_id, "sha256": node.sha256, "release_id": node.release_id,
                      "locator": record["locator"], "field": field["field"]}
            identity = {"task_sha256": fingerprint(task), "scope": task["scope"], "record_key": record["record_key"], "source": source}
            row, key, name = rows[record["record_key"]], record["record_key"], field["field"]
            value = row.get(name)
            empty = (type(value) is str and value == "") or isinstance(value, (list, tuple, Mapping)) and not value
            reason = ("unavailable_join" if key not in anchors and (not restrictions[key] or not all(restrictions[key])) else
                      "failed_qc" if task["collection"]["status"] == "failed_qc" else
                      "field_not_in_schema" if name not in row else "null_source_value" if value is None else
                      "empty_source_value" if empty else None)
            facts.append({"fact_id": "fact:" + fingerprint(identity), "value": None if reason else value, "unit": None,
                          "source": source, "unknown_reason": reason})
    result = {"schema_version": 1, "task_id": task["task_id"], "task_sha256": fingerprint(task),
              "status": "abstained" if always_abstain else "answered" if facts else "insufficient_input",
              "facts": facts, "collection_status": task["collection"]["status"],
              "reason": "Deliberate no-assertion baseline." if always_abstain else None if facts else "No requested records in the declared bounded collection."}
    raw = canonical(result)
    need(adapt_output(raw, wire_format="typed_facts_v1", task_id=task["task_id"], task_sha256=fingerprint(task))["status"] == "scorable", "Literal output exceeds unchanged common wire; no truncation")
    return raw
