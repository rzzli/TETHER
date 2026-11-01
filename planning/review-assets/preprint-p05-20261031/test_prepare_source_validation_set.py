"""Fictional-only P05 builder checks; never opens the real E: originals."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib.util
import math
from pathlib import Path
import sqlite3
import tempfile
from threading import Barrier
import time
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("p05_source_builder", ROOT / "tools/science/prepare_source_validation_set.py")
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)
from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, parse_json


def wrapped(values):
    return {"values": values, "locator": {"fictional": True}}


def small_records():
    return {"target": [wrapped({"id": "ENSG_SYNTH_A", "approvedSymbol": "SYNTH_A"}),
                       wrapped({"id": "ENSG_SYNTH_B", "approvedSymbol": "SYNTH_B"})],
            "disease": [wrapped({"id": "SYNTH_D_A", "name": "Fictional condition A"})],
            "hgnc": [wrapped({"hgnc_id": "HGNC:SYNTH_A", "ensembl_gene_id": "ENSG_SYNTH_A", "symbol": "SYNTH_A", "status": "Approved"}),
                     wrapped({"hgnc_id": "HGNC:SYNTH_B", "ensembl_gene_id": "ENSG_SYNTH_B", "symbol": "SYNTH_B", "status": "Approved"})]}


def evidence(target="ENSG_SYNTH_A", locus="SYNTH_L_A", **updates):
    row = {"id": "SYNTH_EVIDENCE", "targetId": target, "diseaseId": "SYNTH_D_A",
           "diseaseFromSourceMappedId": "SYNTH_D_A", "variantId": "SYNTH_VARIANT", "studyId": "SYNTH_STUDY",
           "studyLocusId": locus, "datasourceId": "gwas_credible_sets", "datatypeId": "genetic_association"}
    return {**row, **updates}


def credible(locus="SYNTH_L_A", **updates):
    row = {"studyLocusId": locus, "studyId": "SYNTH_STUDY", "variantId": "SYNTH_VARIANT", "chromosome": "SYNTH_CHR",
           "position": 100, "beta": 0.3, "standardError": 0.1, "pValueMantissa": 2.5,
           "pValueExponent": -8, "sampleSize": 1000, "zScore": 3.0}
    return {**row, **updates}


class Fixture(unittest.TestCase):
    def setUp(self):
        cache = ROOT / "data/cache"
        cache.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="p05-fictional-", dir=cache)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw-root"
        self.raw.mkdir()
        self.out = self.root / "products"
        self.out.mkdir()
        self.bounds = b.Bounds(self.out)
        self.indexes = b.mapping_index(small_records())

    def source(self, family, rows, filename=None, row_group_size=2):
        path = self.raw / (filename or family + ".parquet")
        if family == "hgnc":
            keys = list(rows[0])
            path.write_text("\t".join(keys) + "\n" + "\n".join("\t".join(str(row.get(k, "")) for k in keys) for row in rows) + "\n", encoding="utf-8")
            fields, count = keys, None
        else:
            table = pa.Table.from_pylist(rows)
            pq.write_table(table, path, row_group_size=row_group_size)
            fields, count = table.schema.names, table.num_rows
        dataset = {"hgnc": "hgnc_symbols", "target": "ot_target", "disease": "ot_disease",
                   "gwas_credible_sets": "ot_evidence", "credible_set": "ot_credible_set"}[family]
        release = "snapshot_synthetic" if family == "hgnc" else "25.09"
        content = path.read_bytes()
        receipt = {"status": "completed", "dataset_id": dataset, "release_id": release,
                   "relative_path": path.relative_to(self.raw).as_posix(), "sha256": b.digest_bytes(content),
                   "bytes": len(content), "url": "https://invalid.example/synthetic/" + path.name,
                   "completed_at_utc": "2025-01-01T00:00:00+00:00"}
        receipt_path = self.raw / (path.name + ".receipt.json")
        receipt_bytes = canonical(receipt) + b"\n"
        receipt_path.write_bytes(receipt_bytes)
        record = {"family": family, "dataset_id": dataset, "release_id": release, "path": str(path),
                  "relative_path": receipt["relative_path"], "source_url": receipt["url"],
                  "bytes": len(content), "sha256": receipt["sha256"], "rows": count, "fields": fields,
                  "receipt": {"path": str(receipt_path), "sha256": b.digest_bytes(receipt_bytes), "bytes": len(receipt_bytes)}}
        return record

    def registry(self, rows):
        connection = b.open_registry(self.out / "candidate-registry.sqlite", b.LIMITS["registry_bytes"])
        self.addCleanup(connection.close)
        record = {"relative_path": "synthetic-gwas.parquet", "sha256": "a" * 64, "release_id": "25.09"}
        b.register_batch(connection, record, rows, {"row_group": 0, "row_in_group_start": 0, "physical_row_start": 0}, self.indexes)
        return connection

    def catalog(self):
        return {"schema_version": 1, "datasets": [
            {"dataset_id": key, "roles": ["reference"] if key == "hgnc_symbols" else ["agent_evidence"]}
            for key in ("hgnc_symbols", "ot_target", "ot_disease", "ot_evidence", "ot_credible_set", "asof_normalized_packets")]}

    def full_inventory(self):
        small = small_records()
        records = [self.source(family, [r["values"] for r in small[family]], filename=family + (".tsv" if family == "hgnc" else ".parquet"))
                   for family in ("target", "disease", "hgnc")]
        rows = [evidence(publicationDate="2020-01-01"), evidence(id="SYNTH_DUPLICATE", publicationDate="2020-01-01"),
                evidence(id="SYNTH_EXCLUDED_DUPLICATE", publicationDate="2099-01-01"),
                evidence(target="ENSG_SYNTH_B", locus="SYNTH_L_MISSING", id="SYNTH_SECOND", publicationDate="2020-01-01")]
        records += [self.source("gwas_credible_sets", [{**r, "literature": ["SYNTH_REF"], "clinicalStatus": "DO_NOT_PROJECT"} for r in rows])]
        records += [self.source("credible_set", [credible(beta=math.nan)], filename="credible-a.parquet"),
                    self.source("credible_set", [credible(beta=0.6, studyId="SYNTH_CONFLICT")], filename="credible-b.parquet")]
        return records


class IdentityAndSelectionTests(Fixture):
    def test_exact_hash_formula_and_delimiter_rejection(self):
        key = ("ENSG_SYNTH_A", "SYNTH_D_A", "SYNTH_L_A")
        expected = b.digest_bytes((b.SEED + "|25.09|" + "|".join(key)).encode())
        self.assertEqual(b.unit_hash("25.09", key), expected)
        with self.assertRaises(ContractError):
            b.unit_hash("25.09", ("A|B", "D", "L"))

    def test_registry_preserves_duplicates_and_excluded_rows(self):
        rows = [evidence(), evidence(), evidence(datasourceId="wrong")]
        db = self.registry(rows)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM physical_rows").fetchone()[0], 3)
        self.assertEqual(db.execute("SELECT SUM(eligible) FROM physical_rows").fetchone()[0], 2)
        selected = b.choose_units(db, 1)
        self.assertEqual(selected[0]["eligible_physical_rows"], 2)
        self.assertEqual(db.execute("SELECT physical_row FROM physical_rows ORDER BY physical_id").fetchall(), [(0,), (1,), (2,)])

    def test_unique_units_rank_by_hash_without_numeric_inputs(self):
        db = self.registry([evidence(), evidence(), evidence(target="ENSG_SYNTH_B", locus="SYNTH_L_B")])
        selected = b.choose_units(db, 2)
        self.assertEqual([x["unit_hash"] for x in selected], sorted(x["unit_hash"] for x in selected))
        self.assertEqual(len({x["studyLocusId"] for x in selected}), 2)
        self.assertEqual(len(b.choose_units(db, 12)), 2)

    def test_case_cap_accepts_one_and_zero_fails_with_full_registry_retained(self):
        db = self.registry([evidence(), evidence(publicationDate="2099-01-01", id="SYNTH_FUTURE")])
        cases = b.choose_units(db, 12)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["eligible_physical_rows"], 1)
        db.execute("UPDATE gwas_rows SET eligible=0")
        db.commit()
        with self.assertRaisesRegex(ContractError, "Zero eligible"):
            b.choose_units(db, 12)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM physical_rows").fetchone()[0], 2)
        for invalid in (0, 13, True):
            with self.assertRaises(ContractError):
                b.choose_units(db, invalid)

    def test_no_alias_casefold_or_status_repair(self):
        records = small_records()
        records["hgnc"][0]["values"]["symbol"] = "synth_a"
        records["hgnc"][0]["values"]["status"] = "approved"
        reasons = b.eligibility(evidence(), b.mapping_index(records))["exclusion_reasons"]
        self.assertIn("hgnc_exact_symbol_status_or_id_invalid", reasons)

    def test_duplicate_target_and_hgnc_do_not_first_row_resolve(self):
        for family in ("target", "hgnc"):
            records = small_records()
            records[family].append(records[family][0])
            self.assertFalse(b.eligibility(evidence(), b.mapping_index(records))["eligible"])

    def test_duplicate_symbols_and_hgnc_id_exclude(self):
        records = small_records()
        records["target"][1]["values"]["approvedSymbol"] = "SYNTH_A"
        self.assertIn("target_symbol_missing_or_nonunique", b.eligibility(evidence(), b.mapping_index(records))["exclusion_reasons"])
        records = small_records()
        records["hgnc"][1]["values"]["hgnc_id"] = "HGNC:SYNTH_A"
        self.assertIn("hgnc_symbol_or_id_nonunique", b.eligibility(evidence(), b.mapping_index(records))["exclusion_reasons"])

    def test_all_known_exposed_symbols_are_excluded_and_others_unknown(self):
        self.assertEqual(b.eligibility(evidence(), self.indexes)["exposure_status"], "UNKNOWN")
        for symbol in b.EXPOSED:
            records = small_records()
            records["target"][0]["values"]["approvedSymbol"] = symbol
            records["hgnc"][0]["values"]["symbol"] = symbol
            self.assertIn("known_exposed_symbol", b.eligibility(evidence(), b.mapping_index(records))["exclusion_reasons"])

    def test_disease_missing_duplicate_or_disagreement_excludes(self):
        self.assertFalse(b.eligibility(evidence(diseaseId="UNKNOWN_SYNTH"), self.indexes)["eligible"])
        self.assertIn("disease_mapped_id_disagreement", b.eligibility(evidence(diseaseFromSourceMappedId="OTHER_SYNTH"), self.indexes)["exclusion_reasons"])
        records = small_records()
        records["disease"].append(records["disease"][0])
        self.assertFalse(b.eligibility(evidence(), b.mapping_index(records))["eligible"])

    def test_raw_datasource_and_datatype_are_both_exact(self):
        for field, value in (("datasourceId", "GWAS_CREDIBLE_SETS"), ("datatypeId", "gwas_credible_sets")):
            self.assertFalse(b.eligibility(evidence(**{field: value}), self.indexes)["eligible"])

    def test_native_date_precision_and_future_or_malformed_dates_exclude(self):
        cutoff = datetime(2025, 6, 1, tzinfo=timezone.utc)
        self.assertEqual(b.source_date_bound("2024-02", "evidenceDate")[0].day, 29)
        self.assertEqual(b.source_date_bound(2024, "publicationYear")[1], "year")
        valid = b.eligibility(evidence(publicationDate="2024-12-31", publicationYear=2024, releaseVersion="native_source_label"), self.indexes, cutoff=cutoff)
        self.assertTrue(valid["eligible"])
        self.assertEqual(valid["date_guard"]["fields"]["releaseVersion"]["native"], "native_source_label")
        for field, value, reason in (("publicationDate", "2030-01-01", "publication_explicit_future"),
                                     ("evidenceDate", "2024-13-01", "evidenceDate_invalid_explicit_date"),
                                     ("releaseDate", "2025-06-01", "releaseDate_date_precision_unverified"),
                                     ("publicationYear", 2025, "publication_date_precision_unverified")):
            decision = b.eligibility(evidence(**{field: value}), self.indexes, cutoff=cutoff)
            self.assertIn(reason, decision["exclusion_reasons"])

    def test_unknown_publication_is_not_fabricated_and_naive_timestamps_invalid(self):
        decision = b.eligibility(evidence(publicationDate=None, evidenceDate="", releaseDate="2024-01-01T00:00:00"), self.indexes)
        self.assertEqual(decision["date_guard"]["fields"]["publicationDate"]["status"], "unknown")
        self.assertEqual(decision["date_guard"]["fields"]["evidenceDate"]["status"], "unknown")
        self.assertIn("releaseDate_invalid_explicit_date", decision["exclusion_reasons"])
        self.assertEqual(decision["date_guard"]["fields"]["publicationYear"]["status"], "schema_absent")

    def test_future_rows_stay_registered_but_do_not_determine_selected_units(self):
        rows = [evidence(publicationDate="2030-01-01"), evidence(target="ENSG_SYNTH_B", locus="SYNTH_L_B", publicationDate="2020-01-01")]
        db = self.registry(rows)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM physical_rows").fetchone()[0], 2)
        self.assertEqual(b.choose_units(db, 1)[0]["targetId"], "ENSG_SYNTH_B")
        excluded = db.execute("SELECT exclusion_reasons,identity_json FROM physical_rows WHERE eligible=0").fetchone()
        self.assertIn("publication_explicit_future", parse_json(excluded[0]))
        self.assertEqual(parse_json(excluded[1])["publicationDate"], "2030-01-01")

    def test_publication_day_and_matching_year_intersect_before_cutoff(self):
        cutoff = datetime(2025, 6, 1, tzinfo=timezone.utc)
        decision = b.eligibility(evidence(publicationDate="2025-04-15", publicationYear=2025), self.indexes, cutoff=cutoff)
        self.assertTrue(decision["eligible"])
        self.assertEqual(decision["date_guard"]["publication_event"]["status"], "within_cutoff")
        self.assertEqual(decision["date_guard"]["fields"]["publicationYear"]["status"], "date_precision_unverified")
        conflict = b.eligibility(evidence(publicationDate="2024-04-15", publicationYear=2025), self.indexes, cutoff=cutoff)
        self.assertIn("publication_date_conflict", conflict["exclusion_reasons"])
        partial = b.eligibility(evidence(publicationYear=2025), self.indexes, cutoff=cutoff)
        self.assertIn("publication_date_precision_unverified", partial["exclusion_reasons"])
        self.assertNotIn("publication_explicit_future", partial["exclusion_reasons"])


class ArrowAndProductTests(Fixture):
    def test_projection_ignores_wide_columns_and_optional_is_explicit(self):
        source = self.source("gwas_credible_sets", [{**evidence(), "literature": ["SYNTH_REF"], "clinicalStatus": "DO_NOT_PROJECT"}])
        batch, _ = next(b.parquet_batches(source, self.bounds))
        self.assertEqual(batch.schema.names, list(b.GWAS))
        self.assertNotIn("clinicalStatus", batch.schema.names)
        self.assertNotIn("literature", batch.schema.names)
        self.assertIn("literature", b.projection(source, optional=True))
        source["fields"].remove("studyLocusId")
        with self.assertRaises(ContractError):
            b.projection(source)

    def test_guard_columns_are_explicitly_projected_without_scientific_expansion(self):
        source = self.source("gwas_credible_sets", [{**evidence(), "publicationDate": "2024-01-01", "evidenceDate": None,
            "publicationYear": 2024, "releaseDate": None, "releaseVersion": "source_native", "beta": 9999.0}])
        batch, _ = next(b.parquet_batches(source, self.bounds))
        self.assertEqual(batch.schema.names, list(b.GWAS + b.GUARD_FIELDS))
        self.assertNotIn("beta", batch.schema.names)

    def test_all_physical_offsets_across_groups_and_8192_batches(self):
        source = self.source("gwas_credible_sets", [evidence(id=f"SYNTH_{i}") for i in range(8210)], row_group_size=8200)
        locations = []
        sizes = []
        for batch, offset in b.parquet_batches(source, self.bounds):
            sizes.append(batch.num_rows)
            locations.extend(b.locator(source, offset, index) for index in range(batch.num_rows))
        self.assertEqual(sizes, [8192, 8, 10])
        self.assertEqual([p["physical_row_0based"] for p in locations], list(range(8210)))
        self.assertEqual(locations[8200]["row_group_0based"], 1)
        self.assertEqual(locations[8200]["row_in_group_0based"], 0)

    def test_arrow_filter_happens_before_selected_values_convert(self):
        table = pa.Table.from_pylist([evidence(locus="OTHER_SYNTH"), evidence(), evidence()])
        selected, indices = b.filtered_rows(table.to_batches()[0], [{"targetId": "ENSG_SYNTH_A", "diseaseId": "SYNTH_D_A", "studyLocusId": "SYNTH_L_A"}], family="gwas_credible_sets")
        self.assertEqual(indices, [1, 2])
        self.assertEqual(selected.num_rows, 2)

    def test_conflicts_missing_no_replacement_and_nan_are_all_retained(self):
        inventory = self.full_inventory()
        db = self.registry([evidence(), evidence(target="ENSG_SYNTH_B", locus="SYNTH_L_MISSING")])
        cases = b.choose_units(db, 2)
        products = b.CaseProducts(self.out, self.bounds, cases)
        counts, coverage = b.capture_selected(inventory, cases, self.indexes, self.bounds, products)
        products.close()
        case = next(x for x in cases if x["studyLocusId"] == "SYNTH_L_A")
        rows = [parse_json(x) for x in (self.out / "selected-originals" / (case["case_id"] + ".jsonl")).read_bytes().splitlines()]
        evidence_rows = [x for x in rows if x["record_type"] == "gwas_credible_sets_original"]
        credible_rows = [x for x in rows if x["record_type"] == "credible_set_original"]
        self.assertEqual(len(evidence_rows), 3)
        self.assertEqual(len(credible_rows), 2)
        self.assertTrue(any(not x["eligibility"]["eligible"] for x in evidence_rows))
        future = next(x for x in evidence_rows if x["values"]["publicationDate"] == "2099-01-01")
        self.assertIn("publication_explicit_future", future["eligibility"]["exclusion_reasons"])
        self.assertTrue(all(x["role"] == "evaluation_only" and not x["agent_visible"] and
                            x["qualification"] == "UNQUALIFIED/AUDIT_ONLY" for x in rows))
        self.assertTrue(any(x["values"]["beta"] == {"type": "invalid_native_number", "native_type": "float", "kind": "nan"} for x in credible_rows))
        self.assertNotIn(b"DO_NOT_PROJECT", canonical(rows))
        missing = next(x for x in cases if x["studyLocusId"] == "SYNTH_L_MISSING")
        self.assertEqual(coverage[missing["case_id"]]["credible_set"]["status"], "missing_retained_no_replacement")
        self.assertEqual(coverage[case["case_id"]]["credible_set"]["distinct_projected_rows"], 2)

    def test_nan_and_both_infinities_remain_typed_invalid(self):
        values = b.source_value([math.nan, math.inf, -math.inf, None, 0.0])
        self.assertEqual([x["kind"] for x in values[:3]], ["nan", "positive_infinity", "negative_infinity"])
        self.assertEqual(parse_json(canonical(values))[3:], [None, 0.0])

    def test_optional_hgnc_absence_is_recorded_not_filled(self):
        records = small_records()
        inventory = [self.source("hgnc", [x["values"] for x in records["hgnc"]], filename="hgnc.tsv")]
        loaded, schemas = b.load_small(inventory, self.bounds)
        self.assertEqual(loaded["hgnc"][0]["values"]["status"], "Approved")
        self.assertEqual(schemas[0]["optional_fields"], {"gene_group": "schema_absent", "gene_group_id": "schema_absent"})

    def test_case_cap_and_constructor_failure_close_streams(self):
        bounds = b.Bounds(self.out, limits={**b.LIMITS, "case_product_bytes": 1})
        with self.assertRaises(ContractError):
            b.CaseProducts(self.out, bounds, [{"case_id": "p05-01"}])
        # Windows would reject this rename if constructor left its file handle open.
        path = self.out / "selected-originals/p05-01.jsonl"
        path.rename(path.with_suffix(".closed"))

    def test_registry_and_output_caps_and_cooperative_deadline(self):
        with self.assertRaises(sqlite3.DatabaseError):
            db = b.open_registry(self.out / "tiny.sqlite", 4096)
            db.close()
        bounds = b.Bounds(self.out, limits={**b.LIMITS, "output_bytes": 1})
        with self.assertRaises(ContractError):
            bounds.publish("too-large.json", {"data": "synthetic"})
        with self.assertRaises(TimeoutError):
            b.Bounds(self.out, deadline=time.monotonic() - 1).check()

    def test_process_peak_memory_is_distinct_from_sampled_rss_and_unknown_is_explicit(self):
        self.bounds.peak_process_rss_bytes = 100
        with patch.object(b, "peak_memory_bytes", return_value=123456):
            report = self.bounds.report()
        self.assertEqual(report["process_peak_working_set_bytes"], 123456)
        self.assertEqual(report["process_peak_working_set_status"], "measured")
        self.assertEqual(report["peak_sampled_process_rss_bytes"], 100)
        self.assertIn("overall Python process lifetime", report["process_peak_working_set_basis"])
        with patch.object(b, "peak_memory_bytes", return_value=None):
            report = self.bounds.report()
        self.assertIsNone(report["process_peak_working_set_bytes"])
        self.assertEqual(report["process_peak_working_set_status"], "os_query_unavailable")
        with patch.object(b, "peak_memory_bytes", side_effect=OSError("fictional OS failure")):
            report = self.bounds.report()
        self.assertIsNone(report["process_peak_working_set_bytes"])
        self.assertEqual(report["process_peak_working_set_status"], "os_query_failed:OSError")


class IntegrityAndGuardTests(Fixture):
    def ready_pair(self):
        plan = {"status": "DRAFT", "code_sha256": {"builder": "a" * 64}, "environment": {"python": "synthetic"},
                "limits": b.LIMITS, "frame": b.EXPECTED, "selection_seed": b.SEED, "selected_units": 12,
                "row_guard_cutoff_utc": "2025-01-01T00:00:00+00:00"}
        payload = canonical(plan) + b"\n"
        ready = {"schema_version": 1, "status": "READY", "scope": "p05_source_only_stage1", "frozen_by": "root",
                 "plan_sha256": b.digest_bytes(payload), "code_sha256": plan["code_sha256"], "environment": plan["environment"],
                 "row_guard_cutoff_utc": "2025-01-01T00:00:00+00:00"}
        return plan, payload, ready

    def test_ready_hash_code_environment_and_scope_guards(self):
        plan, payload, ready = self.ready_pair()
        b.validate_freeze(plan, payload, ready, current_code=plan["code_sha256"], current_environment=plan["environment"])
        for altered in ({**ready, "status": "DRAFT"}, {**ready, "plan_sha256": "0" * 64},
                        {**ready, "scope": "all_work"}, {**ready, "frozen_by": "owner"},
                        {**ready, "code_sha256": {}}, {**ready, "environment": {}}):
            with self.assertRaises(ContractError):
                b.validate_freeze(plan, payload, altered, current_code=plan["code_sha256"], current_environment=plan["environment"])
        with self.assertRaises(ContractError):
            b.validate_freeze(plan, payload, ready, current_code={"builder": "changed"}, current_environment=plan["environment"])

    def test_ready_cutoff_is_explicit_utc_between_frame_and_execution(self):
        plan, payload, ready = self.ready_pair()
        for value in (None, "2024-12-31T00:00:00+00:00", "2099-01-01T00:00:00+00:00", "2025-01-01T00:00:00", "2025-01-01T00:00:00-01:00"):
            with self.assertRaises(ContractError):
                b.freeze_cutoff(plan, {**ready, "row_guard_cutoff_utc": value})
        actual = b.freeze_cutoff(plan, {**ready, "row_guard_cutoff_utc": "2025-01-02T00:00:00Z"})
        self.assertEqual(actual, datetime(2025, 1, 2, tzinfo=timezone.utc))

    def test_transitive_framework_dependency_is_pinned_and_change_detected(self):
        self.assertIn("src/asof/study/proofs.py", b.code_pins())
        dependency = self.root / "fake_dependency.py"
        dependency.write_bytes(b"SYNTHETIC_CONSTANT = 1\n")
        with patch.object(b, "framework_paths", return_value=[dependency]):
            before = b.code_pins()
            dependency.write_bytes(b"SYNTHETIC_CONSTANT = 2\n")
            self.assertNotEqual(before, b.code_pins())

    def test_all_payloads_hash_before_receipt_interpretation_and_exact_archives(self):
        inventory = [self.source("credible_set", [credible()], filename="a.parquet"),
                     self.source("credible_set", [credible(locus="SYNTH_L_B")], filename="b.parquet")]
        events = []
        actual_hash, actual_read = b.hash_file, b.read_file
        def hashing(path, deadline):
            events.append(("payload", Path(path).name))
            return actual_hash(path, deadline)
        def reading(path, deadline, maximum):
            events.append(("receipt", Path(path).name))
            return actual_read(path, deadline, maximum)
        with patch.object(b, "RAW_ROOT", self.raw), patch.object(b, "hash_file", hashing), patch.object(b, "read_file", reading):
            proofs = b.verify_originals(inventory, self.out, self.bounds)
        self.assertEqual([x[0] for x in events], ["payload", "payload", "receipt", "receipt"])
        for proof in proofs:
            self.assertEqual((self.out / proof["receipt_archive"]).read_bytes(), Path(proof["receipt"]["path"]).read_bytes())

    def test_corrupt_payload_stops_before_receipts_or_values(self):
        record = self.source("credible_set", [credible()])
        record["sha256"] = "0" * 64
        with patch.object(b, "RAW_ROOT", self.raw), patch.object(b, "read_file") as reader:
            with self.assertRaises(ContractError):
                b.verify_originals([record], self.out, self.bounds)
            reader.assert_not_called()

    def test_role_and_future_receipt_denied_before_values(self):
        records = [self.source("credible_set", [credible()])]
        with patch.object(b, "RAW_ROOT", self.raw):
            proofs = b.verify_originals(records, self.out, self.bounds)
            catalog = self.catalog()
            catalog["datasets"][4]["roles"] = ["evaluation_only"]
            with self.assertRaises(ContractError):
                b.admit_originals(proofs, self.out, catalog, datetime.now(timezone.utc))
            proofs[0]["completed_at_utc"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            with self.assertRaises(ContractError):
                b.admit_originals(proofs, self.out, self.catalog(), datetime.now(timezone.utc))

    def test_exclusive_concurrent_output_and_hash_chained_failure(self):
        path = self.root / "exclusive"
        barrier = Barrier(2)
        def reserve():
            barrier.wait()
            try:
                journal = RunJournal(path, kind="build")
            except FileExistsError:
                return "denied"
            journal.fail(ContractError("synthetic failure"), "synthetic-stage")
            journal.close()
            return "reserved"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: reserve(), range(2)))
        self.assertEqual(sorted(outcomes), ["denied", "reserved"])
        self.assertEqual(read_chain(path / "journal.jsonl")[-1]["event"], "build_failed")

    def test_failure_seal_retains_hashes_and_expired_hashes_are_explicit(self):
        (self.out / "partial.json").write_bytes(b"synthetic")
        b.failure_seal(self.out, "synthetic", RuntimeError(), time.monotonic() + 20)
        seal = parse_json((self.out / "failure-seal.json").read_bytes())
        self.assertEqual(seal["status"], "failed_stage1_partial_not_usable")
        self.assertEqual(seal["retained_artifacts"][0]["sha256"], b.digest_bytes(b"synthetic"))
        other = self.root / "expired"
        other.mkdir()
        (other / "partial.json").write_bytes(b"synthetic")
        b.failure_seal(other, "expired", TimeoutError(), time.monotonic() - 1)
        self.assertEqual(parse_json((other / "failure-seal.json").read_bytes())["retained_artifacts"][0]["hash_status"], "deadline_expired_not_hashed")

    def test_execute_fictional_success_and_failure_never_read_actual_originals(self):
        inventory = self.full_inventory()
        derived = self.root / "derived"
        plan = {"selected_units": 12, "row_guard_cutoff_utc": "2025-01-01T23:59:59.999999+00:00"}
        plan_path, ready_path = self.root / "plan.json", self.root / "ready.json"
        plan_path.write_bytes(canonical(plan))
        ready_path.write_bytes(b"{}")
        expected = {**b.EXPECTED, "gwas_credible_sets": {"files": 1, "bytes": 0, "rows": 4}}
        @contextmanager
        def fixture_stable(paths, *, deadline):
            # Trusted test seam only; serialized inputs cannot select alternate locking.
            self.assertTrue(all(Path(p).is_absolute() for p in paths))
            yield
        patches = [patch.object(b, "RAW_ROOT", self.raw), patch.object(b, "OUTPUT_ROOT", derived),
                   patch.object(b, "PLAN_PATH", plan_path), patch.object(b, "READY_PATH", ready_path),
                   patch.object(b, "EXPECTED", expected), patch.object(b, "load_guard", return_value=(plan, inventory, self.catalog())),
                   patch.object(b, "stable_files", fixture_stable), patch.object(b, "checked_path", side_effect=lambda root, relative: Path(root) / relative)]
        from contextlib import ExitStack
        with ExitStack() as stack:
            for item in patches:
                stack.enter_context(item)
            output = derived / "preprint-p05-source-validation-20250101T000000Z"
            seal = b.execute(output)
            self.assertEqual(seal["status"], "completed_source_only_stage1")
            self.assertEqual(seal["selected_unit_cap"], 12)
            self.assertEqual(seal["actual_selected_units"], 2)
            events = read_chain(output / "journal.jsonl")
            self.assertLess(next(i for i, x in enumerate(events) if x["event"] == "original_lineage_admitted_before_values"),
                            next(i for i, x in enumerate(events) if x["event"] == "build_stage" and x["details"]["stage"] == "canonical_normalization"))
            self.assertEqual(events[-1]["event"], "build_completed")
            lineage = parse_json((output / "lineage.json").read_bytes())
            self.assertEqual(len(lineage["verified_originals"]), len(inventory))
            self.assertIn("neutral-plan", lineage["derived_products"]["parents"])
            artifacts = {x["artifact_id"]: x for x in lineage["artifact_lineage"]}
            captures = [x for key, x in artifacts.items() if key.startswith("audit-selected-original-")]
            self.assertEqual(len(captures), 2)
            self.assertTrue(all(x["role"] == "evaluation_only" and not x["agent_visible"] for x in captures))
            original_ids = {x["source_id"] for x in lineage["source_nodes"]}
            for neutral in ("neutral-registry", "neutral-case-plan"):
                self.assertEqual(set(artifacts[neutral]["parents"]), original_ids | {"neutral-plan"})
                self.assertTrue(all(not x.startswith("audit-") for x in artifacts[neutral]["parents"]))
            case_plan_bytes = (output / "selected-case-plan.json").read_bytes()
            self.assertNotIn(b"2099-01-01", case_plan_bytes)
            case_plan = parse_json(case_plan_bytes)
            self.assertEqual(case_plan["actual_selected_units"], 2)
            self.assertEqual(case_plan["selected_unit_cap"], 12)
            failed = derived / "preprint-p05-source-validation-20250101T000001Z"
            with patch.object(b, "load_small", side_effect=RuntimeError("fictional failure")):
                with self.assertRaises(RuntimeError):
                    b.execute(failed)
            self.assertEqual(read_chain(failed / "journal.jsonl")[-1]["event"], "build_failed")
            self.assertFalse((failed / "seal.json").exists())
            self.assertEqual(parse_json((failed / "failure-seal.json").read_bytes())["stage"], "canonical_normalization")
            close_failed = derived / "preprint-p05-source-validation-20250101T000002Z"
            actual_close = b.RunJournal.close
            def close_then_raise(journal):
                actual_close(journal)
                raise OSError("fictional journal-close fault")
            with patch.object(b.RunJournal, "close", close_then_raise):
                with self.assertRaises(OSError):
                    b.execute(close_failed)
            self.assertFalse((close_failed / "seal.json").exists())
            self.assertTrue((close_failed / "failure-seal.json").is_file())
            exit_failed = derived / "preprint-p05-source-validation-20250101T000003Z"
            @contextmanager
            def exit_failure(paths, *, deadline):
                yield
                raise OSError("fictional stable-lock exit fault")
            with patch.object(b, "stable_files", exit_failure):
                with self.assertRaises(OSError):
                    b.execute(exit_failed)
            self.assertFalse((exit_failed / "seal.json").exists())
            self.assertTrue((exit_failed / "failure-seal.json").is_file())
            fail_append = derived / "preprint-p05-source-validation-20250101T000004Z"
            with patch.object(b, "load_small", side_effect=RuntimeError("fictional failure")), patch.object(b.RunJournal, "fail", side_effect=OSError("fictional failure append")):
                with self.assertRaises(RuntimeError):
                    b.execute(fail_append)
            self.assertTrue((fail_append / "failure-seal.json").is_file())
            zero_inventory = [r for r in inventory if r["family"] != "gwas_credible_sets"] + [self.source(
                "gwas_credible_sets", [evidence(datasourceId="SYNTH_EXCLUDED", id=f"SYNTH_{i}") for i in range(4)], filename="zero-eligible.parquet")]
            zero = derived / "preprint-p05-source-validation-20250101T000005Z"
            with patch.object(b, "load_guard", return_value=(plan, zero_inventory, self.catalog())):
                with self.assertRaisesRegex(ContractError, "Zero eligible"):
                    b.execute(zero)
            self.assertFalse((zero / "seal.json").exists())
            self.assertEqual(parse_json((zero / "failure-seal.json").read_bytes())["stage"], "deterministic_selection")
            with sqlite3.connect(zero / "candidate-registry.sqlite") as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM physical_rows").fetchone()[0], 4)
                self.assertEqual(db.execute("SELECT SUM(eligible) FROM physical_rows").fetchone()[0], 0)
            db.close()


if __name__ == "__main__":
    unittest.main()
