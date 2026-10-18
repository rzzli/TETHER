import hashlib
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, sha256_file
from tools.science.ascertainment_inputs import qualify, save
from tools.science.restore_verification import STAGES, strict_technical, verify_restore


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class RestoreVerificationTests(unittest.TestCase):
    def fixture(self, directory, requested="2026-04-01", newline=b"\n"):
        base = Path(directory); restore = base / "restore-run"; restore.mkdir()
        worker = restore / "restore"; worker.mkdir(); root = worker / requested; root.mkdir()
        extracted = root / "extracted"; extracted.mkdir()
        origin = {"status": "sealed_mapping_qualified_reconstructed_exploratory", "origin_at": "2025-01-01T00:00:00Z",
            "horizon_at": "2026-01-01T00:00:00Z", "selection_sealed": True, "mapping_qualified": True,
            "reconstructed_origin_information_eligible": True, "endpoint_rows_queried": 0,
            "clinical_ready": False, "clinical_locked": False, "strict_dataset_availability_qualified": False,
            "registry_completeness_qualified": False, "origin_date_qualified": False, "files": []}
        write(base / "origin.json", origin)
        decision = {"mode": "reconstructed_exploratory", "technical_restore_only": True,
            "endpoint_cohort_queries_allowed": False, "clinical_activation_allowed": False,
            "origin_seal_sha256": sha256_file(base / "origin.json"), "technical_snapshot_date": requested,
            "snapshot_purpose": "ascertainment", "ascertainment_at": "2026-04-01T00:00:00Z"}
        write(base / "decision.json", decision)
        archive = base / "source.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("postgres.dmp", b"fixture-dump"); z.writestr("schema.png", b"")
        executable = base / "pg_restore.fixture"; executable.write_bytes(b"fixture-executable")
        toc = "; Archive created at " + requested + " 01:02:03\n1; 0 0 TABLE ctgov studies owner\n"
        with redirect_stdout(io.StringIO()):
            q = qualify(archive, base / "qualification", executable, requested_date=requested,
                runner=lambda *args: {"returncode": 0, "output": toc.encode()})
        members = []
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                raw = z.read(info); (extracted / info.filename).write_bytes(raw)
                members.append({"name": info.filename, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                                "crc32": info.CRC, "crc_check": "passed_full_read"})
        inspection = {"status": "archive_integrity_passed", "archive": str(archive),
            "archive_sha256": sha256_file(archive), "archive_bytes": archive.stat().st_size, "members": members}
        write(root / "archive-inspection.json", inspection)
        audit = {"status": "completed", "tables": [{"schema": "ctgov", "table": "studies", "rows": 3,
            "null_nct_ids": 0, "malformed_nct_ids": 0, "orphan_nct_ids": 0}],
            "study_id_check": {"rows": 3, "distinct_nct_ids": 3, "null_nct_ids": 0},
            "constraints": [], "indexes": [], "study_date_ranges": [
                {"column": column, "max": requested, "after_candidate_date": 0}
                for column in ("study_first_posted_date", "last_update_posted_date", "results_first_posted_date")]}
        write(root / "technical-audit.json", audit); (root / "dump-toc-pg17.txt").write_text(toc)
        (root / "cohort-query.sql").write_bytes(b"SELECT '[]'::text;" + newline)
        (restore / "empty-cohort.sql").write_bytes(b"SELECT '[]'::text;" + newline)
        write(root / "cohort-records.json", []); write(root / "cohort.stdout.log", [])
        plan = {"first_port": 55438, "snapshots": [{"archive": str(archive), "requested_date": requested}],
            "frozen_nct_ids": [], "source_archive_sha256": sha256_file(archive),
            "frozen_cohort_query": str(restore / "empty-cohort.sql"),
            "frozen_cohort_query_sha256": sha256_file(restore / "empty-cohort.sql")}
        if requested == "2026-04-01":
            plan["archive_qualification"] = {"path": str(base / "qualification/qualification.json"),
                "sha256": sha256_file(base / "qualification/qualification.json")}
        write(restore / "plan.json", plan); write(worker / "plan.json", plan)
        (restore / "executed-endpoint-gate.py").write_text("fixture gate")
        (worker / "executed-code.py").write_text("fixture worker")
        gate = {"origin_seal_sha256": sha256_file(base / "origin.json"), "decision_sha256": sha256_file(base / "decision.json"),
                "mode": "reconstructed_exploratory", "endpoint_cohort_rows_requested": 0, "clinical_activation": False}
        write(restore / "gate.json", gate)
        row = {"root": str(root), "status": "completed", "requested_date": requested, "actual_snapshot_date": requested,
            "server_stopped": True, "cohort_records": 0, "technical_checks": strict_technical(audit, toc, requested),
            "import_elapsed_seconds": 1}
        write(root / "restore-result.json", row)
        evidence = {"files": [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha256_file(p)}
                              for p in sorted(root.iterdir()) if p.is_file()]}
        write(root / "evidence-manifest.json", evidence)
        row["evidence_manifest_sha256"] = sha256_file(root / "evidence-manifest.json")
        row["retained_bytes"] = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
        result = {"status": "completed", "snapshots": [row], "elapsed_seconds": 2,
            "peak_memory_bytes": None, "peak_memory_reason": "Not instrumented"}
        write(worker / "result.json", result)
        events = [{"stage": stage, "status": "completed", "requested_date": requested, "returncode": 0} for stage in STAGES]
        events += [{"stage": "snapshot_completed", "requested_date": requested, "actual_snapshot_date": requested,
            "studies": 3, "evidence_manifest_sha256": row["evidence_manifest_sha256"]},
            {"stage": "batch_terminal", "status": "completed"}]
        previous = None
        with (worker / "journal.jsonl").open("w") as stream:
            for event in events:
                event["previous_sha256"] = previous
                previous = hashlib.sha256(json.dumps(event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                stream.write(json.dumps(dict(event, sha256=previous)) + "\n")
        outer = {"status": "technical_restore_completed", "role": "evaluation_only", "endpoint_cohort_rows_queried": 0,
            "clinical_activation": False, "ascertainment_qualified": False,
            "origin_seal_sha256": gate["origin_seal_sha256"], "decision_sha256": gate["decision_sha256"]}
        write(restore / "report.json", outer)
        journal = RunJournal(base / "outer-journal", kind="build")
        journal.append("build_completed", report_sha256=sha256_file(restore / "report.json")); journal.close()
        (restore / "journal.jsonl").write_bytes((base / "outer-journal/journal.jsonl").read_bytes())
        return {"base": base, "restore": restore, "root": root, "requested": requested,
            "options": {"origin_path": base / "origin.json", "decision_path": base / "decision.json",
                "requested_date": requested, "owned_port": 55438, "port_probe": lambda port: False}}

    def verify(self, fixture):
        return verify_restore(fixture["restore"], fixture["base"] / "verification", **fixture["options"])

    def test_april_and_legacy_january_empty_restore_pass_with_no_database_calls(self):
        for requested in ("2026-01-01", "2026-04-01"):
            with self.subTest(requested=requested), tempfile.TemporaryDirectory() as directory:
                f = self.fixture(directory, requested); result = self.verify(f)
                self.assertEqual(result["status"], "independent_terminal_acceptance_passed")
                self.assertFalse(result["clinical_activation"]); self.assertFalse(result["ascertainment_qualified"])
                self.assertIsNone(result["peak_memory_bytes"]); self.assertEqual(result["endpoint_cohort_rows_queried"], 0)
                self.assertEqual(read_chain(f["base"] / "verification/journal.jsonl")[-1]["event"], "build_completed")
                self.assertEqual(sha256_file(Path(result["executed_verifier"]["path"])), result["executed_verifier"]["sha256"])
                self.assertEqual(result["retained_bytes"], sum(p.stat().st_size for p in f["root"].rglob("*") if p.is_file()))

    def test_actual_windows_crlf_sql_is_accepted_and_raw_copy_consistency_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            f = self.fixture(directory, newline=b"\r\n")
            result = self.verify(f)
            self.assertEqual(result["status"], "independent_terminal_acceptance_passed")
        for kind in ("extra_sql", "different_raw_copy"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                f = self.fixture(directory, newline=b"\r\n")
                if kind == "extra_sql":
                    (f["root"] / "cohort-query.sql").write_bytes(b"SELECT '[]'::text;\r\nSELECT 1;\r\n")
                else:
                    path = f["restore"] / "empty-cohort.sql"; path.write_bytes(b"SELECT '[]'::text;\n")
                    plan = json.loads((f["restore"] / "plan.json").read_text())
                    plan["frozen_cohort_query_sha256"] = sha256_file(path)
                    write(f["restore"] / "plan.json", plan); write(f["restore"] / "restore/plan.json", plan)
                with self.assertRaises(ContractError): self.verify(f)

    def test_corrupted_retained_byte_counter_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            f = self.fixture(directory); path = f["restore"] / "restore/result.json"
            result = json.loads(path.read_text()); result["snapshots"][0]["retained_bytes"] += 1; write(path, result)
            with self.assertRaisesRegex(ContractError, "retained-byte counter"):
                self.verify(f)

    def test_durable_evidence_tamper_and_unlisted_files_fail(self):
        for omitted in (False, True):
            with self.subTest(omitted=omitted), tempfile.TemporaryDirectory() as directory:
                f = self.fixture(directory)
                if omitted: (f["root"] / "unlisted-file.txt").write_text("unlisted")
                else: (f["root"] / "cohort-query.sql").write_text("SELECT nct_id FROM ctgov.studies;")
                with self.assertRaises(ContractError): self.verify(f)
                self.assertTrue((f["base"] / "verification/failure.json").exists())
                self.assertFalse((f["base"] / "verification/report.json").exists())

    def test_omitted_qualification_proof_is_rejected_even_when_plan_rehashed(self):
        with tempfile.TemporaryDirectory() as directory:
            f = self.fixture(directory); qpath = f["base"] / "qualification/qualification.json"
            q = json.loads(qpath.read_text()); q["proofs"].pop(); write(qpath, q)
            plan = json.loads((f["restore"] / "plan.json").read_text()); plan["archive_qualification"]["sha256"] = sha256_file(qpath)
            write(f["restore"] / "plan.json", plan); write(f["restore"] / "restore/plan.json", plan)
            with self.assertRaisesRegex(ContractError, "omits or duplicates"): self.verify(f)

    def test_date_cohort_counter_and_audit_conflicts_fail(self):
        for kind in ("date", "cohort", "audit", "memory", "retained"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                f = self.fixture(directory); result_path = f["restore"] / "restore/result.json"
                result = json.loads(result_path.read_text())
                if kind == "date": result["snapshots"][0]["actual_snapshot_date"] = "2026-04-02"
                if kind == "cohort": result["snapshots"][0]["cohort_records"] = 1
                if kind == "memory": result["peak_memory_bytes"] = 12345
                write(result_path, result)
                if kind == "audit":
                    path = f["root"] / "technical-audit.json"; audit = json.loads(path.read_text())
                    audit["study_id_check"]["distinct_nct_ids"] = 2; write(path, audit)
                if kind == "retained":
                    path = f["root"] / "restore-result.json"; row = json.loads(path.read_text()); row["technical_checks"]["studies"] = 9; write(path, row)
                with self.assertRaises(ContractError): self.verify(f)

    def test_alive_port_and_pid_fail_without_start_or_stop(self):
        for pid in (False, True):
            with self.subTest(pid=pid), tempfile.TemporaryDirectory() as directory:
                f = self.fixture(directory)
                if pid:
                    (f["root"] / "pgdata").mkdir(); (f["root"] / "pgdata/postmaster.pid").write_text("123")
                else: f["options"]["port_probe"] = lambda port: True
                with self.assertRaises(ContractError): self.verify(f)

    def test_terminal_journal_tampering_report_mismatch_and_output_reuse_fail(self):
        for kind in ("child", "outer", "report", "reuse"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                f = self.fixture(directory)
                if kind == "reuse": (f["base"] / "verification").mkdir()
                elif kind == "report":
                    path = f["restore"] / "report.json"; path.write_bytes(path.read_bytes() + b" ")
                else:
                    path = f["restore"] / ("restore/journal.jsonl" if kind == "child" else "journal.jsonl")
                    path.write_bytes(path.read_bytes()[:-1])
                with self.assertRaises((ContractError, FileExistsError)): self.verify(f)

    def test_transitive_origin_and_extracted_dump_changes_fail(self):
        for kind in ("origin", "dump"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                f = self.fixture(directory)
                path = f["base"] / "origin.json" if kind == "origin" else f["root"] / "extracted/postgres.dmp"
                path.write_bytes(path.read_bytes() + b" ")
                with self.assertRaises(ContractError): self.verify(f)

    def constraint_fixture(self):
        toc = ("; Archive created at 2026-04-01 01:02:03\n"
            "1; 0 0 TABLE ctgov studies owner\n"
            "2; 2606 100 CONSTRAINT ctgov studies studies_pkey owner\n"
            "3; 2606 101 FK CONSTRAINT ctgov studies studies_parent_fkey owner\n"
            "4; 1259 102 INDEX ctgov index_studies_on_status owner\n")
        audit = {"status": "completed", "tables": [{"schema": "ctgov", "table": "studies", "rows": 3}],
            "study_id_check": {"rows": 3, "distinct_nct_ids": 3, "null_nct_ids": 0},
            "study_date_ranges": [{"column": column, "after_candidate_date": 0, "max": "2026-04-01"}
                for column in ("study_first_posted_date", "last_update_posted_date", "results_first_posted_date")],
            "constraints": [{"schema": "ctgov", "table_name": "studies", "conname": name, "contype": kind, "convalidated": True}
                for name, kind in (("studies_pkey", "p"), ("studies_parent_fkey", "f"))],
            "indexes": [{"schema": schema, "table_name": table, "index_name": name, "indisvalid": True, "indisready": True}
                for schema, table, name in (("ctgov", "studies", "studies_pkey"),
                    ("ctgov", "studies", "index_studies_on_status"), ("pg_toast", "pg_toast_fixture", "pg_toast_fixture_index"))]}
        return audit, toc

    def test_source_toc_constraint_index_coverage_includes_backing_and_allows_toast(self):
        audit, toc = self.constraint_fixture()
        checks = strict_technical(audit, toc, "2026-04-01")
        self.assertEqual(checks["constraints"], 2); self.assertEqual(checks["indexes_including_toast"], 3)
        # A source TOC with no constraint/index objects legitimately permits empty arrays.
        audit["constraints"] = []; audit["indexes"] = []
        empty_toc = "; Archive created at 2026-04-01 01:02:03\n1; 0 0 TABLE ctgov studies owner\n"
        self.assertEqual(strict_technical(audit, empty_toc, "2026-04-01")["constraints"], 0)

    def test_omitted_constraints_indexes_duplicate_identities_and_foreign_schema_rejected(self):
        for kind in ("empty_constraints", "omit_constraint", "duplicate_constraint", "empty_indexes",
                     "omit_explicit_index", "omit_backing_index", "duplicate_index", "duplicate_toast_index",
                     "wrong_backing_table", "extra_index", "extra_table_schema", "duplicate_table"):
            with self.subTest(kind=kind):
                audit, toc = self.constraint_fixture()
                if kind == "empty_constraints": audit["constraints"] = []
                if kind == "omit_constraint": audit["constraints"].pop()
                if kind == "duplicate_constraint": audit["constraints"].append(deepcopy(audit["constraints"][0]))
                if kind == "empty_indexes": audit["indexes"] = []
                if kind == "omit_explicit_index": audit["indexes"].pop(1)
                if kind == "omit_backing_index": audit["indexes"].pop(0)
                if kind == "duplicate_index": audit["indexes"].append(deepcopy(audit["indexes"][0]))
                if kind == "duplicate_toast_index": audit["indexes"].append(deepcopy(audit["indexes"][-1]))
                if kind == "wrong_backing_table": audit["indexes"][0]["table_name"] = "other"
                if kind == "extra_index":
                    extra = deepcopy(audit["indexes"][0]); extra["index_name"] = "unlisted_index"; audit["indexes"].append(extra)
                if kind == "extra_table_schema": audit["tables"].append({"schema": "other", "table": "injected", "rows": 99})
                if kind == "duplicate_table": audit["tables"].append(deepcopy(audit["tables"][0]))
                with self.assertRaises(ContractError): strict_technical(audit, toc, "2026-04-01")

    def test_unique_and_exclusion_constraints_also_require_their_backing_indexes(self):
        for kind in ("u", "x"):
            with self.subTest(kind=kind):
                audit, toc = self.constraint_fixture(); audit["constraints"][0]["contype"] = kind
                strict_technical(audit, toc, "2026-04-01")
                audit["indexes"].pop(0)
                with self.assertRaises(ContractError): strict_technical(audit, toc, "2026-04-01")

    def test_source_index_identity_can_contain_a_literal_dot(self):
        audit, toc = self.constraint_fixture()
        toc = toc.replace("index_studies_on_status", "index_ctgov.studies_on_status")
        audit["indexes"][1]["index_name"] = "index_ctgov.studies_on_status"
        self.assertEqual(strict_technical(audit, toc, "2026-04-01")["indexes_including_toast"], 3)


if __name__ == "__main__":
    unittest.main()
