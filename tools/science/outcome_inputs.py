"""Pure bounded SQL and row contracts for evaluator-only Science 4 inputs.

No database driver, service lifecycle, network access, labels or fitting. SQL emits
one JSON object per row; the runner owns source pins, transactions and provenance.
"""
from __future__ import annotations

import copy
import json
import re

from asof.serde import ContractError, fingerprint
from tools.science.ascertainment_policy import version_eligibility
from tools.science.origin_programs import start_bounds


DATES = ("2025-01-01", "2026-01-01", "2026-04-01")
BEGIN = "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;"
PRELUDE = BEGIN + "\nSET LOCAL standard_conforming_strings=on;\n"
ORIGIN_COLUMNS = ("nct_id", "brief_title", "official_title", "study_type", "phase", "overall_status",
    "start_date", "start_month_year", "start_date_type", "study_first_posted_date",
    "study_first_posted_date_type", "last_update_posted_date", "last_update_posted_date_type",
    "study_first_submitted_date", "last_update_submitted_date", "primary_completion_date",
    "primary_completion_month_year", "primary_completion_date_type", "completion_date",
    "completion_month_year", "completion_date_type", "enrollment", "enrollment_type", "number_of_arms")
FOLLOWUP_COLUMNS = ORIGIN_COLUMNS + ("results_first_posted_date", "results_first_posted_date_type", "why_stopped")
CHILD_COLUMNS = {
    "conditions": ("id", "nct_id", "name"),
    "interventions": ("id", "nct_id", "intervention_type", "name", "description"),
    "intervention_other_names": ("id", "nct_id", "intervention_id", "name"),
    "design_groups": ("id", "nct_id", "group_type", "title", "description"),
    "design_group_interventions": ("id", "nct_id", "design_group_id", "intervention_id"),
    "designs": ("id", "nct_id", "allocation", "intervention_model", "observational_model", "primary_purpose",
        "time_perspective", "masking", "masking_description", "intervention_model_description", "subject_masked",
        "caregiver_masked", "investigator_masked", "outcomes_assessor_masked"),
    "design_outcomes": ("id", "nct_id", "outcome_type", "measure", "time_frame", "population", "description"),
    "eligibilities": ("id", "nct_id", "sampling_method", "gender", "minimum_age", "maximum_age", "healthy_volunteers",
        "population", "criteria", "gender_description", "gender_based", "adult", "child", "older_adult"),
    "brief_summaries": ("id", "nct_id", "description"),
    "detailed_descriptions": ("id", "nct_id", "description"),
    "sponsors": ("id", "nct_id", "agency_class", "lead_or_collaborator", "name"),
    "id_information": ("id", "nct_id", "id_source", "id_value", "id_type", "id_type_description", "id_link"),
    "study_references": ("id", "nct_id", "pmid", "reference_type", "citation"),
    "documents": ("id", "nct_id", "document_id", "document_type", "url", "comment"),
    "provided_documents": ("id", "nct_id", "document_type", "has_protocol", "has_icf", "has_sap", "document_date", "url"),
}
ASCII_SPACE = " \t\n\r\f\v"


def _require(condition, message):
    if not condition:
        raise ContractError(message)


def _date(value):
    _require(value in DATES, "Only the approved January2025/January2026/April2026 snapshots are supported")


def _ids(values, maximum=200):
    _require(isinstance(values, (list, tuple)) and 0 < len(values) <= maximum, "NCT whitelist exceeds its explicit bound or is empty")
    _require(all(isinstance(v, str) and re.fullmatch(r"NCT[0-9]{8}", v) for v in values), "Malformed NCT whitelist")
    _require(len(set(values)) == len(values), "Duplicate NCT whitelist member")
    return sorted(values)


def normalized_alias(value):
    _require(isinstance(value, str) and value.isascii(), "Aliases require explicit ASCII text; no transliteration or fuzzy fallback")
    value = value.strip(ASCII_SPACE)
    _require(bool(value) and len(value) <= 512 and all(32 <= ord(c) < 127 for c in value), "Empty, oversized or control-bearing alias")
    return value.lower()


def _literal(value):
    return "'" + value.replace("'", "''") + "'"


def _norm_sql(expression):
    return ("translate(btrim(coalesce(" + expression + ",''),chr(32)||chr(9)||chr(10)||chr(13)||chr(12)||chr(11)),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')")


def schema_from_audit(audit):
    """Use only technical column metadata; no table rows are needed."""
    schema = {}
    for item in audit["columns"]:
        if item["table_schema"] != "ctgov":
            continue
        columns = schema.setdefault(item["table_name"], [])
        _require(item["column_name"] not in columns, "Duplicate technical schema column")
        columns.append(item["column_name"])
    return schema


def _seal(request):
    request["schema_version"] = 1
    request["role"] = "evaluation_only"
    request["clinical_labels_assigned"] = 0
    request["request_sha256"] = fingerprint(request)
    return request


def _check_request(request, kind, expected_sha256=None):
    core = {key: value for key, value in request.items() if key != "request_sha256"}
    _require(request.get("request_sha256") == fingerprint(core), "Extraction request changed after freeze")
    _require(expected_sha256 is None or expected_sha256 == request["request_sha256"], "Extraction request differs from its supplied anchor")
    _require(request.get("kind") == kind and request.get("role") == "evaluation_only", "Wrong extraction request role or kind")


def study_query(nct_ids, snapshot_date, schema, *, max_ids=200, requested_columns=None, cutoff_at=None):
    """Explicit protocol metadata projection; never SELECT *, result rows or labels."""
    _date(snapshot_date)
    _require(type(max_ids) is int and 1 <= max_ids <= 200, "Invalid NCT extraction bound")
    ids = _ids(nct_ids, max_ids)
    approved_cutoff = "2025-01-01T00:00:00Z" if snapshot_date == DATES[0] else "2026-04-01T00:00:00Z"
    cutoff_at = approved_cutoff if cutoff_at is None else cutoff_at
    _require(cutoff_at == approved_cutoff, "Study eligibility cutoff differs from frozen chronology")
    allowed = {"studies": ORIGIN_COLUMNS if snapshot_date == DATES[0] else FOLLOWUP_COLUMNS, **CHILD_COLUMNS}
    selected = allowed if requested_columns is None else requested_columns
    _require(isinstance(selected, dict) and "studies" in selected, "Explicit study projection required")
    projection, missing = {}, {}
    for table, columns in selected.items():
        _require(table in allowed and isinstance(columns, (list, tuple)) and bool(columns), "Unknown or empty projected table")
        _require(all(isinstance(c, str) for c in columns) and len(set(columns)) == len(columns) and set(columns) <= set(allowed[table]), "Unapproved or duplicate projected column")
        keys = {"nct_id"} if table == "studies" else {"id", "nct_id"}
        if table == "intervention_other_names": keys.add("intervention_id")
        if table == "design_group_interventions": keys.update(("intervention_id", "design_group_id"))
        _require(keys <= set(columns), "Projected identifiers cannot be omitted")
        available = set(schema.get(table, ()))
        _require(table != "studies" or "nct_id" in available, "Source schema lacks study identity")
        _require(not available or keys <= available, "Existing source table lacks required identifiers")
        projection[table] = [c for c in columns if c in available]
        if set(columns) - available:
            missing[table] = [c for c in columns if c not in available]
    for table, parents in {"intervention_other_names": ("interventions",),
                           "design_group_interventions": ("interventions", "design_groups")}.items():
        if projection.get(table):
            _require(all(projection.get(parent) for parent in parents), "Projected child linkage requires its parent table")
    fields = []
    for table, columns in projection.items():
        alias = "s" if table == "studies" else "t"
        encoded = "json_build_object(" + ",".join(_literal(c) + "," + alias + "." + c for c in columns) + ")"
        if table == "studies":
            fields.append("'study'," + encoded)
        elif columns:
            fields.append(_literal(table) + ",coalesce((SELECT json_agg(" + encoded + " ORDER BY t.id) FROM ctgov." +
                          table + " t WHERE t.nct_id=s.nct_id),'[]'::json)")
        else:
            fields.append(_literal(table) + ",'[]'::json")
    sql = (PRELUDE + "SELECT json_build_object(" + ",".join(fields) + ") FROM ctgov.studies s WHERE s.nct_id IN (" +
           ",".join(_literal(i) for i in ids) + ") ORDER BY s.nct_id;\nROLLBACK;")
    return _seal({"kind": "study_metadata", "snapshot_date": snapshot_date, "nct_ids": ids,
        "max_ids": max_ids, "projection": projection, "missing_source_columns": missing, "sql": sql,
        "source_schema": copy.deepcopy(schema), "requested_projection": {t:list(c) for t,c in selected.items()},
        "cutoff_at": cutoff_at,
        "results_tables_included": False, "absence_claim": False})


def candidate_query(aliases_by_origin, snapshot_date, schema, *, per_origin_cap=20, total_cap=200):
    """All-phase exact identity leads. Caps fail in validation; SQL never truncates."""
    _date(snapshot_date)
    _require(isinstance(aliases_by_origin, dict), "Frozen origin alias dictionary required")
    origins = _ids(list(aliases_by_origin), 200)
    _require(type(per_origin_cap) is int and 1 <= per_origin_cap <= 5000 and
             type(total_cap) is int and 1 <= total_cap <= 20000, "Invalid candidate bounds")
    required = {"id", "nct_id", "intervention_type", "name"}
    _require(required <= set(schema.get("interventions", ())), "Candidate source lacks intervention identifiers/names")
    other = bool(schema.get("intervention_other_names"))
    _require(not other or {"intervention_id", "nct_id", "name"} <= set(schema["intervention_other_names"]), "Candidate aliases lack source linkage")
    aliases = {}
    for origin in origins:
        values = aliases_by_origin[origin]
        _require(isinstance(values, (list, tuple)) and 0 < len(values) <= 256, "Each origin requires bounded frozen aliases")
        normalized = [normalized_alias(value) for value in values]
        _require(len(set(normalized)) == len(normalized), "Duplicate normalized alias within an origin")
        aliases[origin] = sorted(normalized)
    _require(sum(map(len, aliases.values())) <= 2048, "Frozen alias dictionary exceeds its bound")
    values = ",".join("(" + _literal(origin) + "," + _literal(term) + ")" for origin in origins for term in aliases[origin])
    names = "SELECT i.name AS source_name"
    if other:
        names += " UNION ALL SELECT n.name FROM ctgov.intervention_other_names n WHERE n.intervention_id=i.id AND n.nct_id=i.nct_id"
    sql = (PRELUDE + "WITH aliases(origin_nct_id,term) AS (VALUES " + values + "), matches AS ("
        "SELECT DISTINCT a.origin_nct_id,i.nct_id,i.id AS intervention_id,i.intervention_type,names.source_name,a.term AS alias "
        "FROM ctgov.interventions i CROSS JOIN LATERAL (" + names + ") names JOIN aliases a ON " +
        _norm_sql("names.source_name") + "=a.term WHERE " + _norm_sql("i.intervention_type") + " IN ('drug','biological')) "
        "SELECT json_build_object('origin_nct_id',m.origin_nct_id,'nct_id',m.nct_id,'matches',"
        "json_agg(json_build_object('intervention_id',m.intervention_id,'intervention_type',m.intervention_type,"
        "'source_name',m.source_name,'alias',m.alias) ORDER BY m.intervention_id,m.source_name,m.alias)) "
        "FROM matches m GROUP BY m.origin_nct_id,m.nct_id ORDER BY m.origin_nct_id,m.nct_id;\nROLLBACK;")
    return _seal({"kind": "candidate_identity", "snapshot_date": snapshot_date, "aliases_by_origin": aliases,
        "per_origin_cap": per_origin_cap, "total_cap": total_cap, "sql": sql,
        "total_cap_unit": "distinct_nct_ids",
        "source_schema": copy.deepcopy(schema),
        "normalization": "ASCII lower and edge whitespace trim; punctuation/internal whitespace unchanged",
        "other_names_available": other, "phase_or_outcome_filter": False, "absence_claim": False})


def regenerate_request(request, *, expected_request_sha256=None):
    """Rebuild every generated field; a recomputed self-hash cannot bless free SQL."""
    kind = request.get("kind")
    _check_request(request, kind, expected_request_sha256)
    if kind == "study_metadata":
        rebuilt = study_query(request["nct_ids"], request["snapshot_date"], request["source_schema"],
            max_ids=request["max_ids"], requested_columns=request["requested_projection"], cutoff_at=request["cutoff_at"])
    elif kind == "candidate_identity":
        rebuilt = candidate_query(request["aliases_by_origin"], request["snapshot_date"], request["source_schema"],
            per_origin_cap=request["per_origin_cap"], total_cap=request["total_cap"])
    else:
        raise ContractError("Unknown generated extraction request")
    _require(rebuilt == request, "Extraction request differs from deterministic regeneration")
    return rebuilt


def parse_jsonl(text):
    """Decode only row JSON; reject duplicate keys, nonfinite numbers and noise."""
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "Duplicate JSON object key")
            result[key] = value
        return result
    def constant(value):
        raise ContractError("Nonfinite JSON value")
    _require(isinstance(text, str), "JSONL text required")
    rows = []
    for line in text.splitlines():
        if not line.strip(): continue
        try:
            row = json.loads(line, object_pairs_hook=pairs, parse_constant=constant)
        except (ValueError, TypeError) as error:
            raise ContractError("Malformed JSONL row") from error
        _require(isinstance(row, dict), "JSONL rows must be objects")
        rows.append(row)
    return rows


def validate_candidates(rows, request, *, expected_request_sha256=None):
    regenerate_request(request, expected_request_sha256=expected_request_sha256)
    _require(request["kind"] == "candidate_identity", "Wrong extraction request kind")
    aliases = request["aliases_by_origin"]
    _require(isinstance(rows, list), "Candidate JSONL must decode to a row list")
    pairs = []; counts = {origin: 0 for origin in aliases}
    for row in rows:
        _require(isinstance(row, dict) and set(row) == {"origin_nct_id", "nct_id", "matches"}, "Unexpected candidate fields")
        origin, nct = row["origin_nct_id"], row["nct_id"]
        _require(origin in aliases, "Candidate crossed the frozen origin set")
        _ids([nct]); pair = (origin, nct)
        _require(pair not in pairs, "Duplicate candidate pair")
        pairs.append(pair); counts[origin] += 1
        _require(isinstance(row["matches"], list) and row["matches"], "Candidate lacks a source match")
        signatures = set()
        for match in row["matches"]:
            _require(isinstance(match, dict) and set(match) == {"intervention_id", "intervention_type", "source_name", "alias"}, "Unknown candidate match field")
            _require(type(match["intervention_id"]) is int and match["intervention_id"] > 0, "Invalid candidate intervention ID")
            _require(normalized_alias(match["intervention_type"]) in ("drug", "biological") and
                     match["alias"] in aliases[origin] and normalized_alias(match["source_name"]) == match["alias"], "Candidate is not an exact frozen drug/biological alias match")
            signature = fingerprint(match)
            _require(signature not in signatures, "Duplicate candidate match")
            signatures.add(signature)
    _require(pairs == sorted(pairs), "Candidate rows must retain canonical origin/NCT order")
    _require(len({nct for _, nct in pairs}) <= request["total_cap"] and all(n <= request["per_origin_cap"] for n in counts.values()),
             "Candidate cap exceeded; no truncation, automatic expansion or partial success")
    return {"status": "candidate_rows_validated", "candidate_pairs": len(rows), "per_origin_counts": counts,
        "candidate_nct_ids": sorted({pair[1] for pair in pairs}), "quarantined_candidates": copy.deepcopy(rows),
        "total_distinct_trials": len({pair[1] for pair in pairs}),
        "clinical_label": None, "absence_claim": False, "origin_membership_changed": False}


def validate_study_rows(rows, request, *, cutoff_at=None, expected_request_sha256=None):
    regenerate_request(request, expected_request_sha256=expected_request_sha256)
    _require(request["kind"] == "study_metadata", "Wrong extraction request kind")
    _require(cutoff_at is None or cutoff_at == request["cutoff_at"], "Validator cutoff differs from frozen request")
    cutoff_at = request["cutoff_at"]
    _require(isinstance(rows, list) and len(rows) <= request["max_ids"], "Study row bound exceeded")
    projection = request["projection"]; ids = []; dispositions = []; eligible = []
    for record in rows:
        _require(isinstance(record, dict) and set(record) == ({"study"} | (set(projection) - {"studies"})), "Unexpected study envelope field")
        study = record["study"]
        _require(isinstance(study, dict) and set(study) == set(projection["studies"]), "Study fields differ from the frozen projection")
        nct = study["nct_id"]; _ids([nct])
        _require(nct in request["nct_ids"] and nct not in ids, "Unrequested or duplicate study")
        ids.append(nct)
        child_ids = {}
        for table, columns in projection.items():
            if table == "studies": continue
            children = record[table]
            _require(isinstance(children, list), "Child table must be a row array")
            seen = []
            for child in children:
                _require(isinstance(child, dict) and set(child) == set(columns), "Child fields differ from frozen projection")
                _require(type(child.get("id")) is int and child["id"] > 0 and child.get("nct_id") == nct,
                         "Invalid child identity or cross-trial child")
                _require(child["id"] not in seen, "Duplicate child ID")
                seen.append(child["id"])
            _require(seen == sorted(seen), "Child IDs must retain source ordering")
            child_ids[table] = set(seen)
        for alias in record.get("intervention_other_names", []):
            _require(alias["intervention_id"] in child_ids.get("interventions", ()), "Broken intervention alias linkage")
        for link in record.get("design_group_interventions", []):
            _require(link["intervention_id"] in child_ids.get("interventions", ()) and
                     link["design_group_id"] in child_ids.get("design_groups", ()), "Broken arm/intervention linkage")
        temporal = version_eligibility(last_update_posted_date=study.get("last_update_posted_date"),
            first_posted_date=study.get("study_first_posted_date"), cutoff_at=cutoff_at)
        missing = [field for field in projection["studies"] if study[field] is None]
        date_type = study.get("last_update_posted_date_type")
        if date_type is None or str(date_type).strip().upper() != "ACTUAL":
            temporal["status"] = "held_unqualified_posting_date_type"
        latest = study.get("last_update_posted_date")
        if isinstance(latest, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", latest) and latest > request["snapshot_date"]:
            temporal["status"] = "held_posting_date_after_source_snapshot"
        # Original precision remains authoritative; the parsed AACT date never
        # refines a missing/partial original start or completion interval.
        intervals = {}
        for name in ("start", "primary_completion", "completion"):
            low, high, precision = start_bounds(study.get(name + "_month_year"))
            intervals[name] = {"lower": low, "upper": high, "precision": precision,
                               "source_type": study.get(name + "_date_type"), "event_inferred": False}
        dispositions.append({"nct_id": nct, "version_eligibility": temporal, "missing_study_fields": missing,
            "source_date_intervals": intervals, "absence_claim": False, "clinical_label": None})
        if temporal["status"] == "eligible_reconstructed_date_bound": eligible.append(copy.deepcopy(record))
    _require(ids == sorted(ids), "Study rows must retain canonical NCT ordering")
    return {"status": "study_rows_validated", "quarantined_rows": copy.deepcopy(rows),
        "eligible_reconstructed_rows": eligible, "version_dispositions": dispositions,
        "missing_nct_ids": sorted(set(request["nct_ids"]) - set(ids)),
        "missing_source_columns": copy.deepcopy(request["missing_source_columns"]),
        "clinical_label": None, "absence_claim": False, "origin_membership_changed": False,
        "metadata_document_presence_is_endpoint_qualification": False}
