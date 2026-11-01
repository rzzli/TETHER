"""Fictional original-only controls; no retained study values or candidates."""
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from unittest.mock import patch

from asof.serde import ContractError, canonical, fingerprint
from asof.study import source_fact_inputs as inputs


ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = ROOT / "data" / "cache" / "test-source-fact-inputs"
CUTOFF = "2026-10-31T23:00:00+00:00"
requires_parquet = unittest.skipUnless(importlib.util.find_spec("pyarrow") is not None,
    "install the ingest extra for adapter tests")


@contextmanager
def _fictional_posix_locks(paths, *, deadline, fixture_root):
    """Only existing regular files beneath this invented fixture may enter."""
    inputs.deadline_check(deadline)
    root = Path(fixture_root)
    if not root.is_absolute():
        raise ContractError("Explicit fictional fixture root required")
    observed = root.lstat()
    if not stat.S_ISDIR(observed.st_mode) or stat.S_ISLNK(observed.st_mode) or \
            getattr(observed, "st_file_attributes", 0) & 0x400 or root.resolve() != root:
        raise ContractError("Linked fictional fixture root denied")
    paths = tuple(Path(path) for path in paths)
    if not paths:
        raise ContractError("Fictional fixture file inventory cannot be empty")
    for path in paths:
        if not path.is_absolute() or not path.is_relative_to(root):
            raise ContractError("Fictional lock path escapes its fixture")
        relative = path.relative_to(root)
        if any(part in (".", "..") for part in relative.parts):
            raise ContractError("Aliased fictional fixture path denied")
        current = root
        for part in relative.parts:
            current /= part
            observed = current.lstat()
            if stat.S_ISLNK(observed.st_mode) or getattr(observed, "st_file_attributes", 0) & 0x400:
                raise ContractError("Linked fictional fixture path denied")
        if not stat.S_ISREG(observed.st_mode) or getattr(observed, "st_nlink", 1) != 1 or path.resolve() != path:
            raise ContractError("Fictional locks require unlinked regular fixture files")
    yield
    inputs.deadline_check(deadline)


@contextmanager
def _fixture_lock_boundary(fixture_root):
    # This Python-only seam exercises invented Parquet/metadata logic on POSIX.
    # Windows tests retain real sharing locks; production remains fail closed.
    if os.name == "nt":
        yield
    else:
        def scoped(paths, *, deadline):
            return _fictional_posix_locks(paths, deadline=deadline, fixture_root=fixture_root)
        with patch.object(inputs, "stable_files", scoped):
            yield


def row(identifier="a", *, source="source-a", offset=0, **extra):
    return dict(source_id=source, locator=dict(format="parquet", row_group=0, row=offset),
                row=dict(id=identifier, targetId="ENSG_FAKE_A", diseaseId="EFO_0003060",
                         datasourceId="europepmc", datatypeId="literature", **extra))


def fixture(root):
    import pyarrow as pa
    if pa.__version__ != "21.0.0":
        raise ContractError("Parquet fixture requires pinned pyarrow 21.0.0; installed version differs")
    import pyarrow.parquet as pq
    raw = root / "originals"
    files = []
    def original(dataset, relative, table=None, text=None):
        path = raw / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if text is not None:
            path.write_text(text, encoding="utf-8")
            columns, rows = text.splitlines()[0].split("\t"), None
        else:
            pq.write_table(table, path)
            columns, rows = table.schema.names, table.num_rows
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        release = "snapshot_fake" if dataset == "hgnc_symbols" else "25.09"
        url = "https://example.invalid/" + relative
        receipt = dict(status="completed", dataset_id=dataset, release_id=release,
                       sha256=digest, bytes=path.stat().st_size, relative_path=relative,
                       completed_at_utc="2026-10-01T00:00:00+00:00", url=url)
        receipt_bytes = canonical(receipt)
        receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
        receipt_path = "manifests/receipt-archive/" + receipt_sha + ".json"
        (raw / receipt_path).parent.mkdir(parents=True, exist_ok=True)
        (raw / receipt_path).write_bytes(receipt_bytes)
        node = dict(source_id="raw-" + str(len(files)), dataset_id=dataset, release_id=release,
                    path=relative, sha256=digest, role="reference" if dataset == "hgnc_symbols" else "agent_evidence",
                    availability=dict(first_public_at=None, release_public_at=None, record_public_at=None,
                                      annotation_public_at=None, retrieved_at="2026-10-01", basis="public_download_receipt",
                                      uncertainty="Fictional control", known_public_by="2026-10-01T00:00:00+00:00", evidence_ref=receipt_sha),
                    temporal_classification="contemporary_only", source_url=url, parents=[], computed_at=None,
                    method_id=None, method_version=None, receipt_path=receipt_path, receipt_sha256=receipt_sha)
        files.append(dict(source=node, columns=columns, rows=rows, bytes=path.stat().st_size,
                          schema_sha256=fingerprint(columns)))
    for index in range(10):
        values = [dict(id="ENSG_FAKE_A", approvedSymbol="CD276"), dict(id="ENSG_FAKE_B", approvedSymbol="OSMR")] if index == 0 else []
        original("ot_target", f"raw/open_targets_platform/25.09/output/target/part-{index}.parquet",
                 pa.Table.from_pylist(values, schema=pa.schema([("id", pa.string()), ("approvedSymbol", pa.string())])))
    original("hgnc_symbols", "reference/hgnc/fake.tsv", text="hgnc_id\tsymbol\tstatus\tensembl_gene_id\nHGNC:FAKE_A\tCD276\tApproved\tENSG_FAKE_A\nHGNC:FAKE_B\tOSMR\tApproved\tENSG_FAKE_B\n")
    evidence = [row("c", cellType="cell-c")["row"], row("a", publicationDate="2025-01-01", cellType=None)["row"],
                row("b", evidenceDate="2025-03-01", cellType=[])["row"],
                dict(id="other", targetId="UNRELATED", diseaseId="OTHER", clinicalStatus="never_project"),
                dict(id="b1", targetId="ENSG_FAKE_B", diseaseId="EFO_0000729", datasourceId="europepmc", datatypeId="literature")]
    # Schema includes a forbidden distractor, while literal selected nulls remain null.
    schema = pa.schema([(name, pa.list_(pa.string()) if name == "cellType" else pa.string())
                        for name in inputs.EVIDENCE_FIELDS] + [("clinicalStatus", pa.string())])
    evidence[0]["cellType"] = ["cell-c"]
    original("ot_evidence", "raw/open_targets_platform/25.09/output/evidence/sourceId=europepmc/part-0.parquet",
             pa.Table.from_pylist(evidence, schema=schema))
    catalog = dict(schema_version=1, datasets=[dict(dataset_id=key, roles=["agent_evidence", "reference"])
                   for key in ("ot_target", "ot_evidence", "hgnc_symbols")])
    inspection = dict(schema_version=2, files=files)
    inspection_path, catalog_path, plan_path = root / "inspection.json", root / "catalog.json", root / "plan.json"
    inspection_path.write_bytes(canonical(inspection))
    catalog_path.write_bytes(canonical(catalog))
    cases = [dict(case_id="cd276-nsclc-development", target_symbol="CD276", target_id=None, indication_id="EFO_0003060", action="delivery_antigen", modality="ADC", tissue=None),
             dict(case_id="osmr-uc-development", target_symbol="OSMR", target_id=None, indication_id="EFO_0000729", action="inhibit", modality="antibody", tissue=None)]
    plan = dict(created_at_utc=CUTOFF, cases=cases, source_policy=dict(release="25.09", partition="europepmc", requested_fields=list(inputs.REQUESTED_FIELDS),
                record_selector="per exact targetId/diseaseId choose first two distinct native record IDs in lexical order; tie locator source_id,row_group,row; conflicting duplicate IDs block affected case without favorable substitution",
                primary_families=["identity_linkage", "reported_context"],
                max_selected_records_per_case=2, max_source_bytes=5 * 1024**3, selection_wall_seconds=120,
                declared_evidence_files=1, max_existing_evidence_files=100,
                declared_evidence_bytes=sum(f["bytes"] for f in files if f["source"]["dataset_id"] == "ot_evidence"),
                declared_mapping_reference_bytes=sum(f["bytes"] for f in files if f["source"]["dataset_id"] != "ot_evidence"),
                inspection_sha256=hashlib.sha256(inspection_path.read_bytes()).hexdigest(),
                catalog_sha256=hashlib.sha256(catalog_path.read_bytes()).hexdigest()),
                conditions=[dict(id="cd276-clean", case="cd276-nsclc-development", kind="real_selected_sources"),
                            dict(id="osmr-clean", case="osmr-uc-development", kind="real_selected_sources"),
                            dict(id="cd276-controlled-missing", case="cd276-nsclc-development", kind="synthetic_input_withholding", records_available=0,
                                 collection_status="incomplete", biological_absence=False)])
    plan_path.write_bytes(canonical(plan))
    return dict(plan=plan, inspection=inspection, catalog=catalog, files=files, raw=raw,
                plan_path=plan_path, inspection_path=inspection_path, catalog_path=catalog_path)


class InputTests(unittest.TestCase):
    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.root = Path(self.temp.name)
        self.fixture_locks = ExitStack()
        self.addCleanup(self.fixture_locks.close)
        self.fixture_locks.enter_context(_fixture_lock_boundary(self.root))

    def tearDown(self):
        self.temp.cleanup()

    def test_lexical_ids_and_physical_tie_without_value_selection(self):
        first = row("a", source="source-z", offset=3, cellType=None)
        tie = row("a", source="source-a", offset=7, cellType=None)
        selected, summary = inputs.select_records([row("z", cellType="rich"), first, row("b"), tie])
        self.assertEqual([r["row"]["id"] for r in selected], ["a", "b"])
        self.assertEqual(selected[0]["source_id"], "source-a")
        self.assertEqual(summary, dict(matching_rows=4, distinct_ids=3))
        self.assertIsNone(selected[0]["row"]["cellType"])
        self.assertNotIn("cellType", selected[1]["row"])

    def test_conflicting_duplicates_block_even_if_not_selected(self):
        with self.assertRaisesRegex(ContractError, "Conflicting duplicate"):
            inputs.select_records([row("a"), row("b"), row("z", cellType=None), row("z")])
        with self.assertRaisesRegex(ContractError, "projection"):
            inputs.select_records([row("a", clinicalStatus="forbidden")])
        with patch.object(inputs, "MAX_MATCHING_ROWS", 1):
            with self.assertRaisesRegex(ContractError, "resource cap"):
                inputs.select_records([row("a"), row("b")])

    def test_mapping_conflict_never_substitutes(self):
        cases = [dict(case_id="case", target_symbol="FAKE_A", target_id=None)]
        hg = [dict(source_id="hg", row=dict(symbol="FAKE_A", status="Approved", ensembl_gene_id="ENSG_A"))]
        ot = [dict(source_id="ot", row=dict(approvedSymbol="FAKE_A", id="ENSG_B"))]
        resolved, blocked = inputs.resolve_cases(cases, hg, ot)
        self.assertEqual(resolved, {})
        self.assertIn("case", blocked)
        ot[0]["row"]["id"] = "ENSG_A"
        self.assertIn("case", inputs.resolve_cases(cases, hg, ot + ot)[1])

    def test_packet_preserves_absent_schema_and_scope_null(self):
        case = dict(case_id="fictional", target_symbol="FAKE_A", indication_id="EFO_0003060",
                    action="delivery_antigen", modality="ADC", tissue=None)
        resolution = dict(target_id="ENSG_FAKE_A", mappings=[dict(source_id="hg"), dict(source_id="target")])
        nodes = {key: dict(source_id=key, sha256=("a" if key == "source-a" else "b") * 64,
                           release_id="25.09") for key in ("source-a", "hg", "target")}
        packet = inputs.make_packet(case, dict(id="fictional-clean", kind="real_selected_sources"),
                                    resolution, [row()], nodes, [], cutoff=CUTOFF, plan_sha256="c" * 64)
        self.assertNotIn("publicationDate", packet["source_records"][0]["row"])
        self.assertNotIn("cellType", packet["source_records"][0]["row"])
        self.assertIsNone(packet["neutral_task"]["scope"]["tissue"])
        self.assertEqual(len(packet["fact_skeleton"]), 4)
        self.assertTrue(all(set(slot).isdisjoint({"value", "unit", "unknown_reason", "expected"})
                            for slot in packet["fact_skeleton"]))

    @requires_parquet
    def test_metadata_role_lineage_and_caps_fail_before_scan(self):
        f = fixture(self.root)
        for change in (lambda: f["files"][0]["source"].update(role="evaluation_only"),
                       lambda: f["files"][0]["source"].update(computed_at="2026-10-01T00:00:00+00:00", parents=["response-derived"]),
                       lambda: f["plan"]["source_policy"].update(max_source_bytes=1)):
            # Restore fixture metadata independently for every exclusion.
            f = fixture(self.root)
            change()
            with self.assertRaises(ContractError):
                inputs.selected_inventory(f["plan"], f["inspection"], f["catalog"])

    def run_preparation(self, f, *, progress=None, cutoff=CUTOFF):
        return inputs.prepare_generation_inputs(f["plan_path"], f["inspection_path"], f["catalog_path"],
                    expected_plan_sha256=hashlib.sha256(f["plan_path"].read_bytes()).hexdigest(),
                    workspace_root=self.root, approved_raw_root=f["raw"], cutoff=cutoff,
                    deadline=time.monotonic() + 120, progress=progress)

    @requires_parquet
    def test_wrong_provider_type_and_frozen_scope_cutoff_fail_closed(self):
        for field in ("datasourceId", "datatypeId"):
            candidate = row()
            candidate["row"][field] = "fictional_wrong_value"
            with self.assertRaisesRegex(ContractError, "provider/type"):
                inputs.select_records([candidate])
        f = fixture(self.root)
        with patch.object(inputs, "_receipt", side_effect=AssertionError("original verification reached")):
            with self.assertRaisesRegex(ContractError, "Cutoff differs"):
                self.run_preparation(f, cutoff="2026-10-31T22:00:00+00:00")
        f["plan"]["cases"][0]["modality"] = "changed"
        f["plan_path"].write_bytes(canonical(f["plan"]))
        with patch.object(inputs, "_receipt", side_effect=AssertionError("original verification reached")):
            with self.assertRaisesRegex(ContractError, "case scope"):
                self.run_preparation(f)

    @requires_parquet
    def test_inventory_declaration_mismatch_and_unapproved_expanded_cap_precede_values(self):
        f = fixture(self.root)
        f["plan"]["source_policy"]["declared_evidence_files"] = 2
        f["plan_path"].write_bytes(canonical(f["plan"]))
        with patch.object(inputs, "_receipt", side_effect=AssertionError("original verification reached")):
            with self.assertRaisesRegex(ContractError, "inventory counts"):
                self.run_preparation(f)
        f["plan"]["source_policy"]["max_source_bytes"] = 10 * 1024**3
        f["plan_path"].write_bytes(canonical(f["plan"]))
        with patch.object(inputs, "_receipt", side_effect=AssertionError("original verification reached")):
            with self.assertRaisesRegex(ContractError, "exact v3 full-inventory"):
                self.run_preparation(f)

    @requires_parquet
    def test_unapproved_arbitrary_deadline_precedes_original_access(self):
        f = fixture(self.root)
        f["plan"]["source_policy"]["selection_wall_seconds"] = 600
        f["plan_path"].write_bytes(canonical(f["plan"]))
        with patch.object(inputs, "_receipt", side_effect=AssertionError("original verification reached")):
            with self.assertRaisesRegex(ContractError, "exact approved v4"):
                self.run_preparation(f)

    @requires_parquet
    def test_progress_journal_and_callback_write_failure_stop_source_work(self):
        from asof.journal import RunJournal, read_chain
        f = fixture(self.root)
        journal = RunJournal(self.root / "success-journal", kind="build")
        try:
            self.run_preparation(f, progress=journal.append)
        finally:
            journal.close()
        events = read_chain(self.root / "success-journal/journal.jsonl")
        verified = [event for event in events if event["details"].get("stage") == "verify_original_inventory" and event["event"] == "build_progress"]
        scans = [event for event in events if event["details"].get("stage") == "scan_evidence" and event["event"] == "build_progress"]
        self.assertEqual(len(verified), 12)
        self.assertEqual(verified[-1]["details"]["verified_sources"], 12)
        self.assertEqual(len(scans), 1)
        self.assertNotIn("ENSG_FAKE", (self.root / "success-journal/journal.jsonl").read_text())
        callback_events = []
        def write_failure(event, **details):
            callback_events.append((event, details))
            if event == "build_progress":
                raise OSError("fictional journal write failure")
        with patch.object(inputs, "_receipt", wraps=inputs._receipt) as receipt_calls:
            with patch.object(inputs, "_parquet_filtered", side_effect=AssertionError("value scan reached")):
                with self.assertRaisesRegex(OSError, "journal write failure"):
                    self.run_preparation(f, progress=write_failure)
        self.assertEqual(receipt_calls.call_count, 1)
        self.assertEqual(sum(event == "build_progress" for event, _ in callback_events), 1)

    @requires_parquet
    def test_fictional_preparation_source_only_and_slot_closure(self):
        f = fixture(self.root)
        import builtins
        normal_import = builtins.__import__
        def restricted_import(name, *args, **kwargs):
            if "source_fact_sources" in name or "source_fact_evaluation" in name:
                raise AssertionError("Evaluator import reached generation preparation")
            return normal_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=restricted_import):
            prepared = self.run_preparation(f)
        self.assertEqual(prepared["blocked_cases"], {})
        packet = prepared["packets"]["cd276-clean"]
        self.assertEqual(packet["role"], "agent_evidence")
        self.assertTrue(packet["agent_visible"])
        self.assertEqual([r["row"]["id"] for r in packet["source_records"]], ["a", "b"])
        self.assertNotIn("clinicalStatus", json.dumps(packet))
        self.assertEqual(len(packet["fact_skeleton"]), 8)
        self.assertEqual(packet["task_sha256"], fingerprint(packet["neutral_task"]))
        for slot in packet["fact_skeleton"]:
            self.assertEqual(set(slot), {"fact_id", "record_key", "field", "source"})
            identity = dict(task_sha256=packet["task_sha256"], scope=packet["neutral_task"]["scope"],
                            record_key=slot["record_key"], source=slot["source"])
            self.assertEqual(slot["fact_id"], "fact:" + fingerprint(identity))
        # Original schema has these fields, and native null is not backfilled.
        self.assertIsNone(packet["source_records"][0]["row"]["evidenceDate"])
        self.assertEqual(packet["source_records"][1]["row"]["cellType"], [])
        self.assertEqual(prepared["reference_inputs"], [])
        missing = prepared["packets"]["cd276-controlled-missing"]
        self.assertEqual(missing["source_records"], [])
        self.assertEqual(missing["mapping_records"], [])
        self.assertEqual(missing["neutral_task"]["records"], [])
        self.assertEqual(missing["neutral_task"]["fields"], [])
        self.assertEqual(missing["fact_skeleton"], [])
        self.assertEqual(missing["neutral_task"]["collection"]["status"], "incomplete")
        self.assertTrue(missing["condition"]["synthetic"])
        self.assertFalse(missing["condition"]["independent_biomedical_context"])
        self.assertFalse(missing["condition"]["biological_absence_claim"])

    @requires_parquet
    def test_source_tamper_precedes_any_original_value_scan(self):
        f = fixture(self.root)
        victim = f["raw"] / f["files"][-1]["source"]["path"]
        victim.write_bytes(victim.read_bytes() + b"tampered")
        with patch.object(inputs, "_parquet_filtered", side_effect=AssertionError("scan reached")):
            with self.assertRaisesRegex(ContractError, "Original hash/bytes"):
                self.run_preparation(f)

    @requires_parquet
    def test_receipt_tamper_and_deadline(self):
        f = fixture(self.root)
        receipt = f["raw"] / f["files"][0]["source"]["receipt_path"]
        receipt.write_bytes(b"{}")
        with self.assertRaisesRegex(ContractError, "receipt hash"):
            self.run_preparation(f)
        with self.assertRaises(TimeoutError):
            inputs.prepare_generation_inputs(f["plan_path"], f["inspection_path"], f["catalog_path"],
                expected_plan_sha256="0" * 64, workspace_root=self.root, approved_raw_root=f["raw"],
                cutoff=CUTOFF, deadline=time.monotonic() - 1)


if __name__ == "__main__":
    unittest.main()
