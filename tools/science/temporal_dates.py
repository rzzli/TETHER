"""Aggregate eight OT25.09 columns in reported calendar coordinates only.

No identifiers, clinical outcomes, examples or unknown source strings are emitted.
This is a descriptive current-release audit, never historical evidence admission.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import re
import stat
import time

from tether_engine.atomic import publish_bytes
from tether_engine.ingest import arrow, peak_memory_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, canonical, fingerprint, freeze, parse_json, sha256_file
from tether_engine.study.proofs import _identity, _no_links
from tools.science import temporal_inventory as inventory


POLICY = freeze({
    "policy_id": "ot25.09-reported-calendar-profile.v1", "release": "25.09",
    "scope_sha256": "922e499faf9e61fb7d1e991b8941d2b98fdce9667b90f2fc58daa276606963da",
    "datatype_config_sha256": "eb01fcd16794ed30ebc24507c9b5362c8e5a775459a18956e4cdafa0e2c6448a",
    "sources": {"chembl": "known_drug", "gwas_credible_sets": "genetic_association",
                "gene_burden": "genetic_association", "uniprot_literature": "genetic_association"},
    "columns": ("datasourceId", "datatypeId", "publicationYear", "publicationDate",
                "evidenceDate", "releaseDate", "releaseVersion", "studyStartDate"),
    "date_fields": ("publicationYear", "publicationDate", "evidenceDate", "releaseDate", "studyStartDate"),
    "cutoffs": ("2024-01-01", "2025-01-01"), "batch_rows": 8192, "maximum_date_characters": 64,
    "grammar": "integer_year_or_exact_ISO_year_month_day_datetime; fractional_seconds_1_to_9_digits",
    "comparison": "reported_calendar_intervals; no_UTC_availability_ordering",
    "precision_basis": "strings_lexical; native_datetime_Python_value_fraction_only; declared_Arrow_resolution_retained_in_inventory_schema",
})
POLICY_SHA256 = fingerprint(POLICY)
_DATE_RE = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?", re.ASCII)
_TIME_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,9}))?)?(Z|[+-]\d{2}:\d{2})?", re.ASCII)
_STATES = ("valid", "null", "empty", "malformed", "unsupported", "missing_column")
_PRECISIONS = ("year", "month", "day", "datetime_minute", "datetime_second", "datetime_fraction")
_RELATIONS = ("entirely_before", "at_or_after", "crossing", "not_comparable")


class _ProfileError(ContractError):
    def __init__(self, code):
        self.code = code
        super().__init__("Date profile rejected: " + code)


def _need(condition, code):
    if not condition:
        raise _ProfileError(code)


def calendar_interval(value):
    """Return a bounded calendar interval; never retain the supplied value."""
    if value is None:
        return {"status": "null"}
    if type(value) is bool:
        return {"status": "unsupported"}
    zone, precision = "not_applicable", None
    try:
        if type(value) is datetime:
            day = value.date()
            precision = "datetime_fraction" if value.microsecond else "datetime_second"
            zone = "present" if value.tzinfo is not None and value.utcoffset() is not None else "absent"
            lower, upper = day.toordinal(), day.toordinal() + 1
        elif type(value) is date:
            lower, upper, precision = value.toordinal(), value.toordinal() + 1, "day"
        else:
            if type(value) is int:
                if not 1 <= value <= 9999:
                    return {"status": "malformed"}
                year, month, day = value, None, None
            elif type(value) is str:
                if not value.strip():
                    return {"status": "empty"}
                if len(value) > POLICY["maximum_date_characters"]:
                    return {"status": "unsupported"}
                match = _DATE_RE.fullmatch(value)
                stamp = _TIME_RE.fullmatch(value)
                if stamp:
                    year, month, day, hour, minute = map(int, stamp.groups()[:5])
                    second, fraction, offset = stamp.groups()[5:]
                    if hour > 23 or minute > 59 or second is not None and int(second) > 59:
                        return {"status": "malformed"}
                    if offset and offset != "Z" and (int(offset[1:3]) > 23 or int(offset[4:6]) > 59):
                        return {"status": "malformed"}
                    calendar_day = date(year, month, day)
                    lower, upper = calendar_day.toordinal(), calendar_day.toordinal() + 1
                    precision = "datetime_fraction" if fraction else "datetime_second" if second else "datetime_minute"
                    zone = "present" if offset else "absent"
                elif match:
                    year = int(match[1])
                    month = int(match[2]) if match[2] is not None else None
                    day = int(match[3]) if match[3] is not None else None
                else:
                    return {"status": "malformed"}
            else:
                return {"status": "unsupported"}
            if precision is None:
                lower = date(year, month if month is not None else 1, day if day is not None else 1).toordinal()
                if month is None:
                    upper, precision = (date(year + 1, 1, 1).toordinal() if year < 9999 else date.max.toordinal() + 1), "year"
                elif day is None:
                    upper = (date(year, month + 1, 1).toordinal() if month < 12 else
                             date(year + 1, 1, 1).toordinal() if year < 9999 else date.max.toordinal() + 1)
                    precision = "month"
                else:
                    upper, precision = lower + 1, "day"
        return {"status": "valid", "lower": lower, "upper": upper, "precision": precision, "timezone": zone}
    except (ValueError, OverflowError, TypeError):
        return {"status": "malformed"}


def compare_calendar(interval, cutoff):
    if interval["status"] != "valid":
        return "not_comparable"
    boundary = date.fromisoformat(cutoff).toordinal()
    if interval["upper"] <= boundary:
        return "entirely_before"
    if interval["lower"] >= boundary:
        return "at_or_after"
    return "crossing"


def _journal(payload, report_sha, files):
    """Validate the exact captured chain bytes, without rereading a path."""
    _need(payload.endswith(b"\n"), "inventory_journal_incomplete")
    events, previous = [], None
    for sequence, line in enumerate(payload.splitlines()):
        event = parse_json(line)
        _need(type(event) is dict and "sha256" in event, "inventory_journal_structure")
        digest = event.pop("sha256")
        _need(event.get("sequence") == sequence and event.get("previous_sha256") == previous and
              fingerprint(event) == digest, "inventory_journal_chain")
        previous = digest
        events.append(event)
    _need(len(events) >= 2 and events[0]["event"] == "build_reserved" and events[-1]["event"] == "build_completed" and
          events[-1]["details"].get("report_sha256") == report_sha and
          sum(e["event"] == "build_completed" for e in events) == 1 and
          not any(e["event"] in ("build_failed", "build_interrupted") for e in events), "inventory_journal_terminal")
    inspected = [event["details"] for event in events if event["event"] == "file_inspected"]
    _need(len(inspected) == len(files), "inventory_journal_file_count")
    for number, (details, row) in enumerate(zip(inspected, files), 1):
        _need(details.get("verified_files") == number and all(details.get(key) == row[key] for key in
              ("relative_path", "bytes", "sha256", "schema_sha256", "footer_rows", "footer_row_groups")),
              "inventory_journal_file_identity")
    return previous


def _prepare(inventory_dir, expected_report_sha256, output_dir):
    root, pins = inventory._absolute(str(inventory_dir)), {}
    _need(not os.path.lexists(root / "failure.json"), "inventory_failure_marker")
    report_path = root / "report.json"
    report_bytes = inventory._read(report_path, expected_report_sha256, pins)
    report = parse_json(report_bytes)
    _need(type(report) is dict and report.get("schema_version") == 1 and
          report.get("status") == "technical_inventory_passed" and report.get("role") == "evaluation_only" and
          report.get("agent_visible") is False and report.get("release_id") == POLICY["release"], "inventory_report_boundary")
    output, manifest_bytes, manifest, roots, raw, partition, extra = inventory._preflight(
        root / "inputs/manifest.json", report["manifest_sha256"], output_dir)
    _need(not output.is_relative_to(root), "output_inside_input_inventory")
    _need(report["dataset_id"] == manifest["dataset_id"] == "ot_evidence" and
          report["release_id"] == manifest["release_id"] == POLICY["release"] and
          report["partition"] == manifest["partition"], "inventory_manifest_identity")
    prefix = "raw/open_targets_platform/25.09/output/evidence/sourceId="
    _need(manifest["partition"].startswith(prefix), "unsupported_source_partition")
    source = manifest["partition"][len(prefix):]
    _need(source in POLICY["sources"], "unsupported_or_incomplete_source_partition")
    pins.update(extra)
    files = report["files"]
    _need(type(files) is list and len(files) == report["file_count"] == len(manifest["files"]) and
          0 < len(files) <= inventory.MAX_FILES, "inventory_file_count")
    expected = {inventory._relative(row["relative_path"]): row for row in manifest["files"]}
    _need(len(expected) == len(files) and [row["relative_path"] for row in files] == sorted(expected), "inventory_file_membership")
    for row in files:
        entry = expected[row["relative_path"]]
        _need(all(row[key] == entry[key] for key in ("bytes", "sha256", "receipt_sha256")) and
              row.get("role") == "evaluation_only" and row.get("agent_visible") is False and
              type(row["footer_rows"]) is int and row["footer_rows"] >= 0, "inventory_file_pin")
    _need(sum(row["bytes"] for row in files) == report["bytes"] and
          sum(row["footer_rows"] for row in files) == report["footer_rows"], "inventory_totals")
    membership = report["membership"]
    _need(all(membership[key] == sorted(expected) for key in ("manifest", "queue", "publisher", "disk")) and
          all(not values for kind in ("missing", "unexpected") for values in membership[kind].values()),
          "inventory_membership_incomplete")
    _need(inventory._disk_members(partition, raw) == sorted(expected), "current_partition_membership_changed")
    journal_path = root / "journal.jsonl"
    journal_bytes = inventory._read(journal_path, sha256_file(journal_path), pins)
    journal_head = _journal(journal_bytes, expected_report_sha256, files)
    return {"root": root, "report": report, "report_bytes": report_bytes, "journal_bytes": journal_bytes,
            "journal_head": journal_head, "manifest": manifest, "manifest_bytes": manifest_bytes,
            "roots": roots, "raw": raw, "partition": partition, "source": source, "pins": pins, "output": output}


def _verify_parents(prepared):
    """Check both original and retained receipt bytes; raw hashing follows in-stream."""
    manifest, report = prepared["manifest"], prepared["report"]
    raw, roots, pins, root = prepared["raw"], prepared["roots"], prepared["pins"], prepared["root"]
    raw_paths, expected, captures = {}, {}, {}
    for item in manifest["files"]:
        source = inventory._child(raw, item["relative_path"])
        receipt = inventory._child(raw, item["receipt_path"])
        raw_paths[source] = (item["sha256"], item["bytes"])
        expected[source] = item["sha256"]
        expected[receipt] = item["receipt_sha256"]
        captures[root / "inputs/receipts" / (item["receipt_sha256"] + ".json")] = item["receipt_sha256"]
    queue = manifest["queue"]
    expected[inventory._approved(queue["path"], roots)] = queue["sha256"]
    captures[root / "inputs/queue.json"] = queue["sha256"]
    for name, capture in (("publisher_listing", "publisher-integrity.txt"),
                          ("publisher_listing_checksum", "publisher-integrity.sha1")):
        item = manifest[name]
        expected[inventory._approved(item["path"], roots)] = item["sha256"]
        expected[inventory._approved(item["receipt_path"], roots)] = item["receipt_sha256"]
        captures[root / "inputs" / capture] = item["sha256"]
        captures[root / "inputs/receipts" / (item["receipt_sha256"] + ".json")] = item["receipt_sha256"]
    supplied = {}
    for pin in report["input_pins"]:
        path = inventory._approved(pin["path"], roots)
        _need(path not in supplied, "duplicate_inventory_parent")
        supplied[path] = pin
    original_manifest = set(supplied) - set(expected)
    _need(len(original_manifest) == 1, "inventory_parent_membership")
    original_path = original_manifest.pop()
    expected[original_path] = report["manifest_sha256"]
    _need(set(supplied) == set(expected), "inventory_parent_membership")
    for path, digest in expected.items():
        pin = supplied[path]
        _need(pin["sha256"] == digest and type(pin["bytes"]) is int and pin["bytes"] >= 0, "inventory_parent_identity")
        if path in raw_paths:
            _need((digest, pin["bytes"]) == raw_paths[path], "inventory_raw_parent_identity")
        else:
            limit = inventory.MAX_RECEIPT_BYTES if path.suffix == ".json" and "receipt" in path.name else inventory.MAX_METADATA_BYTES
            payload = inventory._read(path, digest, pins, limit=limit)
            _need(len(payload) == pin["bytes"], "inventory_parent_size")
    for path, digest in captures.items():
        inventory._read(path, digest, pins,
                        limit=inventory.MAX_RECEIPT_BYTES if path.parent.name == "receipts" else inventory.MAX_METADATA_BYTES)


def _new_state():
    fields = {name: {"semantics": "unqualified_descriptive_only", "states": dict.fromkeys(_STATES, 0),
                     "precision": dict.fromkeys(_PRECISIONS, 0),
                     "timezone_presence": dict.fromkeys(("present", "absent", "not_applicable"), 0),
                     "cutoffs": {cutoff: dict.fromkeys(_RELATIONS, 0) for cutoff in POLICY["cutoffs"]}}
              for name in POLICY["date_fields"]}
    return {"files_selected": 0, "files_hash_verified": 0, "files_scanned_complete": 0,
            "bytes_verified": 0, "footer_rows": 0, "rows_decoded": 0, "rows_aggregated": 0,
            "selected_column_bytes": 0, "fields": fields,
            "source_declarations": dict.fromkeys(("matched", "null", "empty", "missing_column", "conflicting"), 0),
            "datatype_declarations": dict.fromkeys(("expected", "null", "empty", "missing_column", "unexpected_string", "unsupported_type"), 0),
            "release_version_type_presence": dict.fromkeys(("missing_column", "null", "empty_string", "string", "boolean", "integer",
                                                            "number", "date", "datetime", "sequence", "mapping", "other"), 0),
            "pairs": {left + "|" + right: dict.fromkeys(("comparable", "not_comparable", "disjoint", "overlapping"), 0)
                      for left, right in combinations(POLICY["date_fields"], 2)}, "files": []}


def _presence(row, key):
    if key not in row:
        return "missing_column"
    if row[key] is None:
        return "null"
    if type(row[key]) is str and not row[key].strip():
        return "empty"
    return "present"


def _add_row(state, row, source):
    presence = _presence(row, "datasourceId")
    if presence == "present":
        presence = "matched" if type(row["datasourceId"]) is str and row["datasourceId"] == source else "conflicting"
    state["source_declarations"][presence] += 1
    _need(presence != "conflicting", "source_declaration_mismatch")
    presence = _presence(row, "datatypeId")
    if presence == "present":
        value = row["datatypeId"]
        presence = ("expected" if value == POLICY["sources"][source] else "unexpected_string") if type(value) is str else "unsupported_type"
    state["datatype_declarations"][presence] += 1
    presence = _presence(row, "releaseVersion")
    if presence == "present":
        value = row["releaseVersion"]
        presence = {str: "string", bool: "boolean", int: "integer", float: "number", date: "date",
                    datetime: "datetime", list: "sequence", tuple: "sequence", dict: "mapping"}.get(type(value), "other")
    elif presence == "empty":
        presence = "empty_string"
    state["release_version_type_presence"][presence] += 1
    intervals = {}
    for name in POLICY["date_fields"]:
        item = calendar_interval(row[name]) if name in row else {"status": "missing_column"}
        intervals[name] = item
        field = state["fields"][name]
        field["states"][item["status"]] += 1
        if item["status"] == "valid":
            field["precision"][item["precision"]] += 1
            field["timezone_presence"][item["timezone"]] += 1
        for cutoff in POLICY["cutoffs"]:
            field["cutoffs"][cutoff][compare_calendar(item, cutoff)] += 1
    for left, right in combinations(POLICY["date_fields"], 2):
        a, b, counts = intervals[left], intervals[right], state["pairs"][left + "|" + right]
        if a["status"] == b["status"] == "valid":
            counts["comparable"] += 1
            counts["disjoint" if a["upper"] <= b["lower"] or b["upper"] <= a["lower"] else "overlapping"] += 1
        else:
            counts["not_comparable"] += 1
    state["rows_aggregated"] += 1


def _scan(prepared, row, pq, state, journal):
    path = inventory._child(prepared["raw"], row["relative_path"])
    before = path.stat()
    _need(stat.S_ISREG(before.st_mode) and before.st_size == row["bytes"], "raw_size_changed")
    sha256, sha1, size = hashlib.sha256(), hashlib.sha1(), 0
    with path.open("rb") as stream:
        _need(_identity(before) == _identity(os.fstat(stream.fileno())), "raw_identity_changed_before_read")
        while chunk := stream.read(inventory.HASH_CHUNK_BYTES):
            size += len(chunk)
            _need(size <= before.st_size, "raw_grew_during_hash")
            sha256.update(chunk)
            sha1.update(chunk)
        _need(size == row["bytes"] and sha256.hexdigest() == row["sha256"] and sha1.hexdigest() == row["publisher_sha1"], "raw_checksum_changed")
        state["files_hash_verified"] += 1
        state["bytes_verified"] += size
        stream.seek(0)
        parquet = pq.ParquetFile(stream, pre_buffer=False, thrift_string_size_limit=inventory.MAX_METADATA_BYTES,
                                 thrift_container_size_limit=1000000)
        fields = inventory._schema_fields(parquet.schema_arrow)
        _need(fingerprint(fields) == row["schema_sha256"] and parquet.metadata.num_rows == row["footer_rows"] and
              parquet.num_row_groups == row["footer_row_groups"], "raw_footer_changed")
        names = [field["name"] for field in fields]
        _need(len(set(names)) == len(names), "ambiguous_schema_names")
        selected = [name for name in POLICY["columns"] if name in names]
        count = 0
        for batch in parquet.iter_batches(columns=selected, batch_size=POLICY["batch_rows"]):
            _need(list(batch.schema.names) == selected and type(batch.num_rows) is int and
                  0 <= batch.num_rows <= POLICY["batch_rows"], "unapproved_batch_projection")
            values = batch.to_pylist()
            _need(len(values) == batch.num_rows and all(type(value) is dict and set(value) == set(selected) for value in values),
                  "unapproved_decoded_projection")
            state["rows_decoded"] += batch.num_rows
            state["selected_column_bytes"] += batch.nbytes
            count += batch.num_rows
            _need(count <= row["footer_rows"], "decoded_rows_exceed_footer")
            for value in values:
                _add_row(state, value, prepared["source"])
            journal.append("date_batch_processed", files_scanned_complete=state["files_scanned_complete"],
                           rows_decoded=state["rows_decoded"], rows_aggregated=state["rows_aggregated"])
        _need(count == row["footer_rows"], "decoded_rows_differ_from_footer")
        after = os.fstat(stream.fileno())
    _no_links(path)
    _need(_identity(before) == _identity(after) == _identity(path.stat()), "raw_identity_changed_during_decode")
    prepared["pins"][path] = {"sha256": row["sha256"], "bytes": size, "identity": _identity(before)}
    state["files_scanned_complete"] += 1
    state["files"].append({"relative_path": row["relative_path"], "sha256": row["sha256"], "rows_decoded": count,
                           "selected_columns": selected, "missing_columns": [name for name in POLICY["columns"] if name not in names]})


def _reconcile(state):
    count = state["rows_aggregated"]
    _need(count == state["rows_decoded"] == state["footer_rows"] and
          state["files_scanned_complete"] == state["files_selected"] == state["files_hash_verified"], "profile_totals_differ")
    for counts in (state["source_declarations"], state["datatype_declarations"], state["release_version_type_presence"]):
        _need(sum(counts.values()) == count, "declaration_denominator_differs")
    for field in state["fields"].values():
        _need(sum(field["states"].values()) == count and sum(field["precision"].values()) == field["states"]["valid"] and
              sum(field["timezone_presence"].values()) == field["states"]["valid"] and
              all(sum(values.values()) == count for values in field["cutoffs"].values()), "field_denominator_differs")
    for pair in state["pairs"].values():
        _need(pair["comparable"] + pair["not_comparable"] == count and pair["disjoint"] + pair["overlapping"] == pair["comparable"],
              "pair_denominator_differs")


def profile_dates(inventory_dir, expected_report_sha256, output_dir):
    """Profile qualified complete source partitions; no real-data call is implicit."""
    started = time.monotonic()
    prepared = _prepare(inventory_dir, expected_report_sha256, output_dir)
    output, journal = prepared["output"], RunJournal(prepared["output"], kind="build")
    state, stage = _new_state(), "input_proofs"
    state["files_selected"] = prepared["report"]["file_count"]
    state["footer_rows"] = prepared["report"]["footer_rows"]
    try:
        _verify_parents(prepared)
        for name, payload in (("inventory-report.json", prepared["report_bytes"]),
                              ("inventory-journal.jsonl", prepared["journal_bytes"]),
                              ("inventory-manifest.json", prepared["manifest_bytes"]),
                              ("policy.json", canonical(POLICY) + b"\n")):
            inventory._capture(output, "inputs/" + name, payload)
        code = []
        from tether_engine import serde, journal as journal_module, ingest
        from tether_engine.study import proofs
        for module_path in (Path(__file__), Path(inventory.__file__), Path(serde.__file__),
                            Path(journal_module.__file__), Path(ingest.__file__), Path(proofs.__file__)):
            digest = sha256_file(module_path)
            payload = inventory._read(module_path, digest, prepared["pins"])
            code.append({"path": str(module_path.resolve()), "sha256": digest})
        journal.append("date_profile_policy", policy_sha256=POLICY_SHA256, inventory_report_sha256=expected_report_sha256,
                       source=prepared["source"], selected_columns=list(POLICY["columns"]))
        stage, pq = "selected_column_scan", arrow()
        for row in prepared["report"]["files"]:
            _scan(prepared, row, pq, state, journal)
        stage = "final_reconciliation"
        _reconcile(state)
        _need(state["bytes_verified"] == prepared["report"]["bytes"], "verified_byte_total_differs")
        _need(inventory._disk_members(prepared["partition"], prepared["raw"]) == prepared["report"]["membership"]["disk"],
              "partition_membership_changed")
        for path, pin in prepared["pins"].items():
            _no_links(path)
            _need(_identity(path.stat()) == pin["identity"], "input_changed_before_profile_finalization")
        _need(not os.path.lexists(prepared["root"] / "failure.json"), "inventory_failure_marker")
        report = {"schema_version": 1, "status": "aggregate_date_profile_completed", "role": "evaluation_only", "agent_visible": False,
                  "source": prepared["source"], "release_id": POLICY["release"], "complete_partition": True,
                  "policy": dict(POLICY), "policy_sha256": POLICY_SHA256, "inventory_report_sha256": expected_report_sha256,
                  "inventory_journal_head": prepared["journal_head"], "inventory_manifest_sha256": prepared["report"]["manifest_sha256"],
                  "input_pins": [{"path": str(path), "sha256": pin["sha256"], "bytes": pin["bytes"]}
                                 for path, pin in sorted(prepared["pins"].items(), key=lambda item: str(item[0]))],
                  "code_pins": code, "comparison_basis": POLICY["comparison"], "precision_basis": POLICY["precision_basis"],
                  "pairwise_interpretation": "disjoint_reported_calendar_intervals; not_adjudicated_source_errors",
                  "decoded_projection": list(POLICY["columns"]), "clinical_identifiers_selected": False,
                  "clinical_outcomes_selected": False, "labels_qualified": False, "historical_evidence_qualified": False,
                  "excluded_sources": {"europepmc": "incomplete_collection; no_subset_substitution_or_absence_inference"},
                  "selected_column_bytes_basis": "sum_of_decoded_Arrow_batch_nbytes; not_compressed_transfer_or_physical_IO",
                  "elapsed_seconds": time.monotonic() - started, "peak_memory_bytes": peak_memory_bytes(), **state}
        stage = "publication"
        payload = canonical(report) + b"\n"
        journal.append("build_completed", report_sha256=hashlib.sha256(payload).hexdigest(), rows_decoded=state["rows_decoded"])
        publish_bytes(output / "report.json", payload)
        return parse_json(payload)
    except BaseException as error:
        code = error.code if isinstance(error, _ProfileError) else "input_or_execution_failure"
        safe_error = KeyboardInterrupt() if isinstance(error, KeyboardInterrupt) else ContractError("Date profile failed: " + stage + "; " + code)
        failure = {"schema_version": 1, "status": "aggregate_date_profile_failed", "role": "evaluation_only", "agent_visible": False,
                   "stage": stage, "error_code": code, "labels_qualified": False, "historical_evidence_qualified": False,
                   "decoded_projection": list(POLICY["columns"]), "policy_sha256": POLICY_SHA256, **state}
        try:
            journal.fail(safe_error, stage)
        except OSError:
            pass
        try:
            publish_bytes(output / "failure.json", canonical(failure) + b"\n")
        except OSError:
            pass
        raise safe_error from None
    finally:
        journal.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--report-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = profile_dates(args.inventory, args.report_sha256, args.output)
    print(json.dumps({key: report[key] for key in ("status", "source", "files_scanned_complete", "rows_decoded")}))


if __name__ == "__main__":
    main()
