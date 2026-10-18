"""Independent terminal acceptance of an empty-cohort technical AACT restore.

Reads retained files and probes only the owned loopback port. Never starts/stops a
server, opens a database connection, or queries clinical rows.
"""
from __future__ import annotations

import argparse
from datetime import date
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import socket
import time
import zipfile
import zlib

from asof.journal import RunJournal
from asof.serde import ContractError, fingerprint, parse_json, safe_child, sha256_file
from tools.science.ascertainment_inputs import DEFAULT_LIMITS, actual_date, safe_members, save
from tools.science.endpoint_restore import validate_gate, verify_origin_closure

EMPTY_SQL = b"SELECT '[]'::text;\n"
EMPTY_SQL_ENCODINGS = (EMPTY_SQL, b"SELECT '[]'::text;\r\n")
STAGES = ("archive_check", "toc", "setup", "import", "analyze", "audit", "cohort", "stop")
EXCLUDED = {"pgdata", "extracted", ".local-postgres-secrets", "__pycache__"}


def require(condition, message):
    if not condition:
        raise ContractError(message)


def zero(value):
    return type(value) is int and value == 0


def port_listening(port):
    with socket.socket() as connection:
        connection.settimeout(2)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def chain(payload, *, outer):
    require(payload.endswith(b"\n"), "Incomplete journal tail")
    rows, previous = [], None
    for line in payload.splitlines():
        row = parse_json(line); digest = row.pop("sha256")
        require(row.get("previous_sha256") == previous, "Journal predecessor mismatch")
        if outer:
            require(row.get("sequence") == len(rows), "Outer journal sequence mismatch")
            actual = fingerprint(row)
        else:
            actual = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        require(actual == digest, "Journal checksum mismatch")
        rows.append(row); previous = digest
    require(bool(rows), "Empty journal")
    return rows, previous


def toc_objects(toc):
    """Read flat ctgov object identities from pg_restore's retained --list output."""
    constraints, indexes = [], []
    for line in toc.splitlines():
        if re.search(r"\bCONSTRAINT ctgov\b", line):
            match = re.fullmatch(r"\d+;\s+\d+\s+\d+\s+(?:FK\s+)?CONSTRAINT\s+(ctgov)\s+(\S+)\s+(\S+)\s+\S+\s*", line)
            require(match is not None, "Unrecognized ctgov constraint TOC format")
            constraints.append(match.groups())
        elif re.search(r"\bINDEX ctgov\b", line):
            match = re.fullmatch(r"\d+;\s+\d+\s+\d+\s+INDEX\s+(ctgov)\s+(\S+)\s+\S+\s*", line)
            require(match is not None, "Unrecognized ctgov index TOC format")
            indexes.append(match.groups())
    require(len(constraints) == len(set(constraints)), "Duplicate constraint identity in TOC")
    require(len(indexes) == len(set(indexes)), "Duplicate index identity in TOC")
    return set(constraints), set(indexes)


def strict_technical(audit, toc, requested):
    require(audit.get("status") == "completed", "Technical audit not completed")
    actual_date(toc, requested)
    expected = set(re.findall(r"TABLE ctgov (\w+) ", toc))
    tables = audit["tables"]
    require(all(item.get("schema") == "ctgov" for item in tables), "Unexpected technical table schema")
    names = [item["table"] for item in tables if item["schema"] == "ctgov"]
    require(bool(expected) and len(names) == len(set(names)) and set(names) == expected,
            "Technical table coverage differs from dump TOC")
    for item in tables:
        require(type(item.get("rows")) is int and item["rows"] >= 0, "Invalid technical row counter")
        for key in ("null_nct_ids", "malformed_nct_ids", "orphan_nct_ids"):
            require(key not in item or zero(item[key]), "Technical identifier exception")
    ids = audit["study_id_check"]
    require(type(ids.get("rows")) is int and ids["rows"] > 0 and
            type(ids.get("distinct_nct_ids")) is int and ids["rows"] == ids["distinct_nct_ids"]
            and zero(ids.get("null_nct_ids")), "Technical study identifier counters conflict")
    studies = [item for item in tables if item["schema"] == "ctgov" and item["table"] == "studies"]
    require(len(studies) == 1 and studies[0]["rows"] == ids["rows"], "Study table and identifier totals conflict")
    expected_constraints, explicit_indexes = toc_objects(toc)
    constraints, indexes = audit["constraints"], audit["indexes"]
    constraint_keys = [(item["schema"], item["table_name"], item["conname"]) for item in constraints]
    require(len(constraint_keys) == len(set(constraint_keys)) and set(constraint_keys) == expected_constraints,
            "Technical constraints omit, duplicate or differ from TOC identities")
    require(all(item.get("convalidated") is True for item in constraints), "Unvalidated constraint")
    index_keys = [(item["schema"], item["index_name"]) for item in indexes]
    require(len(index_keys) == len(set(index_keys)), "Duplicate technical index identity")
    require(all(item["schema"] in ("ctgov", "pg_toast") for item in indexes), "Unexpected technical index schema")
    backing = {(item["schema"], item["conname"]) for item in constraints if item.get("contype") in ("p", "u", "x")}
    actual_ctgov = {key for key in index_keys if key[0] == "ctgov"}
    require(actual_ctgov == explicit_indexes | backing, "Technical indexes omit or differ from TOC/backing identities")
    index_by_key = dict(zip(index_keys, indexes))
    for item in constraints:
        if item.get("contype") in ("p", "u", "x"):
            require(index_by_key[(item["schema"], item["conname"])].get("table_name") == item["table_name"],
                    "Constraint backing index belongs to a different table")
    require(all(item.get("indisvalid") is True and item.get("indisready") is True for item in indexes),
            "Invalid or unready index")
    posting_columns = {"study_first_posted_date", "last_update_posted_date", "results_first_posted_date"}
    recorded_columns = [item["column"] for item in audit["study_date_ranges"]]
    require(len(recorded_columns) == len(set(recorded_columns)) and posting_columns <= set(recorded_columns),
            "Technical audit omits or duplicates posting-date checks")
    for item in audit["study_date_ranges"]:
        require(type(item.get("after_candidate_date")) is int and item["after_candidate_date"] >= 0,
                "Invalid posting-date counter")
        if item["column"] in posting_columns:
            require(zero(item["after_candidate_date"]), "Posting date exceeds snapshot date")
            require(item.get("max") is None or date.fromisoformat(item["max"]) <= date.fromisoformat(requested),
                    "Posting-date maximum conflicts with zero late-date count")
    return {"snapshot_date": requested, "tables": len(names), "studies": ids["rows"],
        "total_rows": sum(item["rows"] for item in tables), "identifier_exceptions": [],
        "constraints": len(audit["constraints"]), "indexes_including_toast": len(audit["indexes"]),
        "scientific_validation": "not_established"}


def verify_restore(restore_root, output, *, origin_path, decision_path, requested_date,
                   owned_port, expected_report_sha256=None, port_probe=None):
    """Reserve a fresh verification directory and return a pinned terminal report.

    All actual files in the worker's evidence scope must be listed, not merely the
    subset a manifest happens to declare. April also requires complete qualification
    proof coverage. The input tree is never modified by this verifier.
    """
    restore_root, output = Path(restore_root).resolve(), Path(output).resolve()
    journal = RunJournal(output, kind="build")
    started, stage, pins = time.monotonic(), "terminal_artifacts", {}
    try:
        require(requested_date in ("2026-01-01", "2026-04-01"), "Unsupported technical snapshot")
        require(type(owned_port) is int and 1 <= owned_port <= 65535, "Invalid owned port")
        with (output / "executed-verifier.py").open("xb") as stream:
            stream.write(Path(__file__).read_bytes())

        def pin(path, expected=None, size=None):
            path = Path(path).resolve(); digest = sha256_file(path)
            require(expected is None or digest == expected, "Changed restore ancestor: " + str(path))
            require(size is None or path.stat().st_size == size, "Restore ancestor size differs")
            if path in pins:
                require(pins[path]["sha256"] == digest, "Conflicting restore ancestor identity")
            pins[path] = {"path": str(path), "sha256": digest, "bytes": path.stat().st_size}
            return digest

        def payload(path, expected=None):
            path = Path(path).resolve(); raw = path.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
            require(expected is None or digest == expected, "Changed parsed restore artifact")
            if path in pins:
                require(pins[path]["sha256"] == digest, "Parsed artifact changed during verification")
            pins[path] = {"path": str(path), "sha256": digest, "bytes": len(raw)}
            return raw

        def read(path, expected=None):
            return parse_json(payload(path, expected))

        def proof(item):
            return pin(item["path"], item["sha256"], item.get("bytes"))

        outer_raw = payload(restore_root / "report.json", expected_report_sha256)
        outer = parse_json(outer_raw); outer_hash = hashlib.sha256(outer_raw).hexdigest()
        require(outer.get("status") == "technical_restore_completed" and outer.get("role") == "evaluation_only",
                "Outer technical restore is not terminal")
        require(zero(outer.get("endpoint_cohort_rows_queried")) and outer.get("clinical_activation") is False
                and outer.get("ascertainment_qualified") is False, "Outer report claims clinical activation or queried rows")
        if "snapshot_date" in outer:
            require(outer["snapshot_date"] == requested_date, "Outer snapshot date conflict")
        if "snapshot_purpose" in outer:
            require(outer["snapshot_purpose"] == ("ascertainment" if requested_date == "2026-04-01" else "endpoint"),
                    "Outer snapshot purpose conflict")
        outer_rows, outer_head = chain(payload(restore_root / "journal.jsonl"), outer=True)
        require(outer_rows[-1]["event"] == "build_completed" and
                outer_rows[-1]["details"].get("report_sha256") == outer_hash, "Outer terminal report hash not bound")
        require(not any(r["event"] in ("build_failed", "build_interrupted") for r in outer_rows), "Failed outer journal")
        result = read(restore_root / "restore/result.json")
        require(result.get("status") == "completed" and len(result.get("snapshots", [])) == 1, "Child batch incomplete")
        row = result["snapshots"][0]
        root = restore_root / "restore" / requested_date
        require(Path(row["root"]).resolve() == root and row.get("status") == "completed" and
                row.get("server_stopped") is True, "Child snapshot status/root/stopped conflict")
        require(row.get("requested_date") == row.get("actual_snapshot_date") == requested_date,
                "Child snapshot date conflict")
        require(zero(row.get("cohort_records")), "Nonempty cohort counter")
        retained = read(root / "restore-result.json")
        require({"root", "status", "requested_date", "actual_snapshot_date", "server_stopped", "cohort_records", "technical_checks"}
                <= set(retained), "Retained child row omits required fields")
        require(all(key in row and row[key] == value for key, value in retained.items()), "Retained child row conflicts")
        require(retained.get("status") == "completed" and retained.get("server_stopped") is True and
                zero(retained.get("cohort_records")), "Retained child row incomplete")
        require(not (root / "pgdata/postmaster.pid").exists(), "Owned PostgreSQL PID remains")
        plan = read(restore_root / "plan.json")
        require(read(restore_root / "restore/plan.json") == plan, "Outer and worker restore plans differ")
        gate = read(restore_root / "gate.json")
        require(gate.get("origin_seal_sha256") == outer.get("origin_seal_sha256") and
                gate.get("decision_sha256") == outer.get("decision_sha256") and
                gate.get("mode") == "reconstructed_exploratory" and zero(gate.get("endpoint_cohort_rows_requested"))
                and gate.get("clinical_activation") is False, "Retained dispatch gate conflicts")
        pin(restore_root / "executed-endpoint-gate.py")
        pin(restore_root / "restore/executed-code.py")
        require(plan.get("first_port") == owned_port and len(plan.get("snapshots", [])) == 1 and
                plan["snapshots"][0].get("requested_date") == requested_date and plan.get("frozen_nct_ids") == [],
                "Restore plan date/port/cohort conflict")
        require(not (port_probe or port_listening)(owned_port), "Owned PostgreSQL port still listening")
        query_bytes = payload(root / "cohort-query.sql")
        require(query_bytes in EMPTY_SQL_ENCODINGS and read(root / "cohort-records.json") == [] and
                read(root / "cohort.stdout.log") == [], "Cohort query/result is not literal empty selection")
        query_path = Path(plan["frozen_cohort_query"]).resolve()
        require(query_path == restore_root / "empty-cohort.sql" and payload(query_path, plan["frozen_cohort_query_sha256"]) == query_bytes,
                "Frozen outer query differs")
        child_rows, child_head = chain(payload(restore_root / "restore/journal.jsonl"), outer=False)
        require(child_rows[-1].get("stage") == "batch_terminal" and child_rows[-1].get("status") == "completed",
                "Child terminal journal incomplete")
        require(not any(r.get("status") == "failed" or r.get("stage") == "batch_failed" for r in child_rows), "Failed child journal")
        require(all(r.get("requested_date", requested_date) == requested_date for r in child_rows), "Child journal date conflict")
        for name in STAGES:
            require(any(r.get("stage") == name and r.get("status") == "completed" and
                        r.get("requested_date") == requested_date for r in child_rows), "Missing child terminal stage: " + name)
            require(all(r.get("returncode", 0) == 0 for r in child_rows if r.get("stage") == name and r.get("status") == "completed"),
                    "Completed child stage has nonzero return code")
        stage = "technical_and_evidence_integrity"
        audit = read(root / "technical-audit.json")
        toc = payload(root / "dump-toc-pg17.txt").decode("utf-8")
        checks = strict_technical(audit, toc, requested_date)
        require(checks == row.get("technical_checks") == retained.get("technical_checks"), "Technical checks disagree")
        completed_snapshots = [r for r in child_rows if r.get("stage") == "snapshot_completed"]
        require(len(completed_snapshots) == 1 and completed_snapshots[0].get("actual_snapshot_date") == requested_date and
                completed_snapshots[0].get("studies") == checks["studies"] and
                completed_snapshots[0].get("evidence_manifest_sha256") == row.get("evidence_manifest_sha256"),
                "Snapshot completion counters/date/evidence hash conflict")
        evidence_path = root / "evidence-manifest.json"
        evidence = read(evidence_path, row["evidence_manifest_sha256"])
        listed = set()
        for item in evidence["files"]:
            path = safe_child(root, item["path"]).resolve()
            require(path not in listed and not any(p in EXCLUDED for p in path.relative_to(root).parts),
                    "Duplicate or out-of-scope evidence member")
            listed.add(path); pin(path, item["sha256"], item["bytes"])
        actual_files = {p.resolve() for p in root.rglob("*") if p.is_file() and p != evidence_path and
                        not any(part in EXCLUDED for part in p.relative_to(root).parts)}
        require(listed == actual_files, "Evidence manifest omits or invents files")
        retained_bytes = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
        require(type(row.get("retained_bytes")) is int and row["retained_bytes"] == retained_bytes,
                "Measured retained-byte counter conflicts with complete snapshot file inventory")
        stage = "source_archive_and_qualification"
        inspection = read(root / "archive-inspection.json")
        require(inspection.get("status") == "archive_integrity_passed", "Archive inspection is not complete")
        archive = Path(inspection["archive"]).resolve()
        archive_hash = pin(archive, inspection["archive_sha256"], inspection["archive_bytes"])
        require(Path(plan["snapshots"][0]["archive"]).resolve() == archive and plan.get("source_archive_sha256") == archive_hash,
                "Source archive and plan identities conflict")
        member_index = {}
        for item in inspection["members"]:
            require(item["name"] not in member_index and item.get("crc_check") == "passed_full_read", "Invalid member integrity record")
            member_index[item["name"]] = item
            pin(safe_child(root / "extracted", item["name"]), item["sha256"], item["bytes"])
        with zipfile.ZipFile(archive) as archive_zip:
            infos = archive_zip.infolist(); safe_members(infos, DEFAULT_LIMITS)
            require({info.filename for info in infos} == set(member_index), "Archive inspection omits ZIP members")
            for info in infos:
                hasher, count, crc = hashlib.sha256(), 0, 0
                with archive_zip.open(info) as source:
                    while block := source.read(8 * 1024**2):
                        count += len(block); hasher.update(block); crc = zlib.crc32(block, crc)
                item = member_index[info.filename]
                require(count == item["bytes"] == info.file_size and hasher.hexdigest() == item["sha256"]
                        and crc == info.CRC == item["crc32"], "Fresh ZIP CRC/member identity differs")
        qualification_hash = None
        if requested_date == "2026-04-01" or plan.get("archive_qualification"):
            qualification_proof = plan.get("archive_qualification")
            require(isinstance(qualification_proof, dict), "Missing archive qualification proof")
            q = read(qualification_proof["path"], qualification_proof["sha256"])
            qualification_hash = qualification_proof["sha256"]
            require(q.get("status") == "archive_qualification_passed" and q.get("requested_date") == q.get("actual_dump_date") == requested_date,
                    "Archive qualification status/date mismatch")
            require(q.get("database_restored") is False and zero(q.get("clinical_rows_queried")),
                    "Archive qualification claimed restore or clinical queries")
            require(q.get("archive") == {"path": str(archive), "sha256": archive_hash, "bytes": inspection["archive_bytes"]},
                    "Archive qualification source identity differs")
            required = q["members"] + [q["toc"], q["executed_code"], q["pg_restore"]]
            expected_paths = {Path(p["path"]).resolve() for p in required}
            declared_paths = [Path(p["path"]).resolve() for p in q.get("proofs", [])]
            require(len(declared_paths) == len(set(declared_paths)) and set(declared_paths) == expected_paths,
                    "Archive qualification omits or duplicates ancestor proofs")
            for item in required + q["proofs"]:
                proof(item)
            require(actual_date(payload(q["toc"]["path"], q["toc"]["sha256"]).decode("utf-8"), requested_date) == requested_date,
                    "Retained qualification TOC date differs")
            require({m["name"] for m in q["members"]} == set(member_index), "Qualification member set differs")
            for member in q["members"]:
                source = member_index[member["name"]]
                require(member["sha256"] == source["sha256"] and member["bytes"] == source["bytes"]
                        and member.get("crc_check") == "passed_full_read", "Qualification member identity differs")
        stage = "full_origin_closure"
        origin, origin_pins = verify_origin_closure(origin_path, outer["origin_seal_sha256"])
        decision = read(decision_path, outer["decision_sha256"]); validate_gate(origin, decision)
        require(decision.get("origin_seal_sha256") == outer["origin_seal_sha256"], "Decision does not bind origin")
        if requested_date == "2026-04-01":
            require(decision.get("technical_snapshot_date") == requested_date and decision.get("snapshot_purpose") == "ascertainment"
                    and decision.get("ascertainment_at") == "2026-04-01T00:00:00Z", "April decision changed analytic cutoff")
        for path, digest in origin_pins.items():
            pin(path, digest)
        require(result.get("peak_memory_bytes") is None and bool(result.get("peak_memory_reason")), "Unmeasured memory cannot be invented")
        stage = "final_closure"
        for item in list(pins.values()):
            proof(item)
        require(not (root / "pgdata/postmaster.pid").exists() and not (port_probe or port_listening)(owned_port),
                "Owned PostgreSQL became active during verification")
        require(sum(path.stat().st_size for path in root.rglob("*") if path.is_file()) == retained_bytes,
                "Retained snapshot file bytes changed during verification")
        verifier_proof = {"path": str(output / "executed-verifier.py"), "sha256": sha256_file(output / "executed-verifier.py"),
                          "bytes": (output / "executed-verifier.py").stat().st_size}
        report = {"schema_version": 1, "status": "independent_terminal_acceptance_passed", "role": "evaluation_only",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(), "restore_root": str(restore_root), "snapshot_date": requested_date,
            "endpoint_cohort_rows_queried": 0, "clinical_activation": False, "clinical_ready": False, "clinical_locked": False,
            "ascertainment_qualified": False, "reporting_allowance_qualified": False, "exact_first_public_availability": None,
            "dump_creation_timezone": None, "technical_checks": checks, "server_stopped": True, "owned_port_listening": False,
            "owned_port": owned_port, "source_archive_sha256": archive_hash, "source_archive_bytes": inspection["archive_bytes"],
            "archive_qualification_sha256": qualification_hash, "source_members_verified": len(member_index),
            "evidence_files_verified": len(listed), "ancestor_pins_reverified": len(origin_pins),
            "child_journal_head_sha256": child_head, "outer_journal_head_sha256": outer_head,
            "peak_memory_bytes": None, "peak_memory_reason": result["peak_memory_reason"],
            "restore_elapsed_seconds": result.get("elapsed_seconds"), "import_elapsed_seconds": row.get("import_elapsed_seconds"),
            "retained_bytes": retained_bytes,
            "acceptance_elapsed_seconds": time.monotonic() - started, "provider_spend_usd": 0,
            "executed_verifier": verifier_proof, "proofs": sorted(pins.values(), key=lambda p: p["path"])}
        save(output / "report.json", report)
        journal.append("build_completed", report_sha256=sha256_file(output / "report.json"))
        return report
    except BaseException as error:
        journal.fail(error, stage)
        save(output / "failure.json", {"status": "failed", "stage": stage, "error_class": type(error).__name__,
            "error": str(error), "recovery": "Inspect only; repeat verification in a fresh directory after resolving the cause"})
        raise
    finally:
        journal.close()


def main():
    parser = argparse.ArgumentParser()
    for name in ("restore-root", "output", "origin-path", "decision-path", "requested-date"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--owned-port", required=True, type=int)
    parser.add_argument("--expected-report-sha256")
    args = parser.parse_args(); options = vars(args); restore_root = options.pop("restore_root"); output = options.pop("output")
    result = verify_restore(restore_root, output, **options)
    print(json.dumps({"status": result["status"], "snapshot_date": result["snapshot_date"], "proofs": len(result["proofs"])}))


if __name__ == "__main__":
    main()
