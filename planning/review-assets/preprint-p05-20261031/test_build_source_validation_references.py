"""Fictional P05 reference tests. Real core, Windows locks and output parent.

No fixture reads an actual original, generation packet, capture or answer file.
Only trusted metadata configuration is substituted in the full-execute fixture;
path validation, exclusive reservation, stable locks and core APIs stay active.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("p05_references", ROOT / "tools/science/build_source_validation_references.py")
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


def case():
    value = dict(case_id="p05-01", targetId="ENSG_FAKE_1", diseaseId="EFO_FAKE_1", studyLocusId="FAKE_LOCUS", release_id="25.09")
    value["unit_hash"] = b.stage1.unit_hash("25.09", b.stage1.unit_key(value))
    return value


def gwas(**changes):
    value = dict(id="FAKE_EVIDENCE", targetId="ENSG_FAKE_1", diseaseId="EFO_FAKE_1", studyLocusId="FAKE_LOCUS",
        studyId="GWAS_STUDY", variantId="GWAS_VARIANT", diseaseFromSourceMappedId=None,
        datasourceId="gwas_credible_sets", datatypeId="genetic_association")
    return {**value, **changes}


def credible(**changes):
    return {**dict(studyLocusId="FAKE_LOCUS", studyId="CREDIBLE_STUDY", variantId="CREDIBLE_VARIANT", beta=0.125,
        standardError=0.25, pValueMantissa=1.5, pValueExponent=-8, chromosome="1", position=42, sampleSize=123), **changes}


@contextmanager
def fixture(*, credible_rows=None, selected_indices=None, gwas_rows=None, target_symbol="FAKEGENE", reserve=True):
    import pyarrow as pa
    import pyarrow.parquet as pq
    cache = ROOT / "data/cache"
    cache.mkdir(parents=True, exist_ok=True)
    b.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p05-reference-fictional-", dir=cache) as temp:
        raw = Path(temp) / "originals"
        raw.mkdir()
        (raw / "payloads").mkdir()
        originals = [credible()] if credible_rows is None else credible_rows
        anchors = [gwas()] if gwas_rows is None else gwas_rows
        families = [("credible_set", originals), ("gwas_credible_sets", anchors),
            ("target", [dict(id="ENSG_FAKE_1", approvedSymbol=target_symbol)]),
            ("disease", [dict(id="EFO_FAKE_1", name="Fictional phenotype")]),
            ("hgnc", [dict(hgnc_id="HGNC:FAKE", symbol=target_symbol, ensembl_gene_id="ENSG_FAKE_1", status="Approved")])]
        inventory, datasets = [], []
        for number, (family, rows) in enumerate(families):
            path = raw / "payloads" / (family + (".tsv" if family == "hgnc" else ".parquet"))
            if family == "hgnc":
                fields = list(rows[0])
                path.write_text("\t".join(fields) + "\n" + "\t".join(rows[0][k] for k in fields) + "\n", encoding="utf-8")
            else:
                # Empty credible inventory retains the declared schema.
                table = pa.Table.from_pylist(rows if rows else [credible()])
                if not rows:
                    table = table.slice(0, 0)
                fields = table.schema.names
                pq.write_table(table, path, row_group_size=1)
            payload = path.read_bytes()
            receipt_path = raw / (family + ".receipt.json")
            dataset = "fiction_" + family
            relative = path.relative_to(raw).as_posix()
            receipt = dict(status="completed", dataset_id=dataset, release_id="25.09", relative_path=relative.replace("/", "\\"),
                sha256=b.digest(payload), bytes=len(payload), url="https://example.invalid/" + family,
                completed_at_utc="2026-01-01T00:00:00+00:00")
            receipt_payload = b.canonical(receipt) + b"\n"
            receipt_path.write_bytes(receipt_payload)
            inventory.append(dict(family=family, dataset_id=dataset, release_id="25.09", relative_path=relative,
                path=str(path), bytes=len(payload), sha256=b.digest(payload), source_url=receipt["url"], fields=fields,
                rows=len(rows), receipt=dict(path=str(receipt_path), bytes=len(receipt_payload), sha256=b.digest(receipt_payload))))
            datasets.append(dict(dataset_id=dataset, roles=["reference" if family == "hgnc" else "agent_evidence"]))
        catalog = dict(schema_version=1, datasets=datasets)
        proofs = [{**item, "source_id": f"original-{i:03d}", "completed_at_utc":"2026-01-01T00:00:00+00:00",
            "receipt_relative_path": Path(item["receipt"]["path"]).name} for i, item in enumerate(inventory)]
        suffix = str(int(uuid.uuid4().hex[:8], 16) % 1000000).zfill(6)
        output = b.OUTPUT_ROOT / (b.OUTPUT_PREFIX + "20990101T" + suffix + "Z")
        b.validate_output_location(output)
        journal = b.RunJournal(output, kind="build") if reserve else None
        bounds = b.Bounds(output)
        snapshot = b.source_inputs.original_snapshot(proofs, catalog, output, raw_root=raw)
        def record(row, source_id, row_index, family):
            return dict(source_id=source_id, family=family, locator=dict(format="parquet", row_group=row_index, row=0), values=row)
        indices = list(range(len(originals))) if selected_indices is None else selected_indices
        groups = {"gwas_credible_sets": [record(row, "original-001", i, "gwas_credible_sets") for i, row in enumerate(anchors)],
                  "credible_set": [record(originals[i], "original-000", i, "credible_set") for i in indices]}
        task = b.source_inputs.build_task(case(), groups)
        routing = dict(schema_version=1,role="neutral_metadata",product_kind="neutral_selected_case_plan",agent_visible=False,
            plan_sha256="a"*64,row_guard_cutoff_utc=b.CUTOFF,no_replacement=True,numeric_availability_used=False,
            model_performance_used=False,selection_seed=b.stage1.SEED,cases=[case()],actual_selected_units=1)
        retained = {"p05-01.task.json":b.canonical(task)+b"\n", "source-snapshot.json":b.canonical(b.encode(snapshot))+b"\n",
                    "selected-case-plan.json":b.canonical(routing)+b"\n"}
        metadata_bytes = {"catalog":b.canonical(catalog)+b"\n"}
        seal_bytes = b.canonical(dict(status="SEALED_NEUTRAL_TASK_DEFINITIONS_ONLY",source_row_values_copied=False,
            measurement_expected_values=False,items=[dict(path=name,sha256=b.digest(data)) for name,data in retained.items()]))+b"\n"
        authentication = dict(neutral_seal_sha256=b.digest(seal_bytes),frame_descriptor_sha256=b.fingerprint(inventory),
            neutral_files_sha256={name:b.digest(data) for name,data in retained.items()},
            metadata_sha256={name:b.digest(data) for name,data in metadata_bytes.items()})
        bundle = SimpleNamespace(docs={"catalog":catalog}, inventory=inventory, cases=[case()], tasks={"p05-01":task},
            snapshot_document=b.encode(snapshot),authentication=authentication,retained=retained,
            metadata_bytes=metadata_bytes,neutral_seal_bytes=seal_bytes)
        f = SimpleNamespace(raw=raw, output=output, bounds=bounds, journal=journal, bundle=bundle,
                            inventory=inventory, snapshot=snapshot, task=task)
        try:
            yield f
        finally:
            if journal:
                journal.close()
            resolved = output.resolve()
            if resolved.exists():
                assert resolved.parent == b.OUTPUT_ROOT.resolve() and resolved.name.startswith(b.OUTPUT_PREFIX + "2099")
                shutil.rmtree(resolved)


def replay(f):
    paths = [Path(i["path"]) for i in f.inventory] + [Path(i["receipt"]["path"]) for i in f.inventory]
    with b.stable_files(paths, deadline=f.bounds.deadline):
        return b.replay_sources(f.bundle, f.bounds, raw_root=f.raw)


def compile_manifest(f):
    snapshot, details, proofs = replay(f)
    results = b.compile_p05_references(f.bundle, snapshot, details, f.output, f.bundle.docs["catalog"],
        deadline=f.bounds.deadline, approved_raw_root=f.raw)
    plan = dict(status="DRAFT",actual_build_authorized=False,code_sha256=b.code_pins(),environment=b.stage1.environment(),
        limits=b.LIMITS,authentication=f.bundle.authentication,row_guard_cutoff_utc=b.CUTOFF,raw_root=str(f.raw),output_root=str(b.OUTPUT_ROOT),
        actual_selected_units=len(f.bundle.cases))
    plan_bytes = b.canonical(plan) + b"\n"
    ready = dict(schema_version=1,status="READY",frozen_by="root",scope="p05_independent_source_references",actual_build_authorized=True,
        plan_sha256=b.digest(plan_bytes),code_sha256=plan["code_sha256"],environment=plan["environment"],
        authentication=plan["authentication"],row_guard_cutoff_utc=b.CUTOFF)
    ready_bytes = b.canonical(ready) + b"\n"
    f.ready_sha256 = b.digest(ready_bytes)
    manifest = dict(method=b.METHOD, role="evaluation_only", agent_visible=False, adjudicated_gold=False,
        authentication=f.bundle.authentication, information_cutoff=b.CUTOFF,
        ready_sha256=f.ready_sha256,
        actual_selected_units=len(f.bundle.cases),unknown_context=b.source_inputs.UNKNOWN_CONTEXT,
        scientific_validation=b.SCIENTIFIC_VALIDATION,computed_at=datetime.now(timezone.utc).isoformat(),
        recipe=[],recipe_policy=b.RECIPE_POLICY,
        original_inputs=[{k:p[k] for k in ("source_id","relative_path","sha256","receipt")} for p in proofs],
        authorization=b.retained_context(plan_bytes,ready_bytes,f.bundle),
        cases={key:dict(disposition=value["disposition"], reference=b.encode(value["reference"].document) if value["reference"] else None)
               for key,value in results.items()})
    return manifest


class OriginalReferenceTests(unittest.TestCase):
    @contextmanager
    def execution_config(self, f):
        """Substitute fictional trusted config only; production I/O stays real."""
        metadata = f.raw.parent / "neutral-config.json"
        metadata.write_bytes(b.canonical({"routing_only":True}) + b"\n")
        plan_path, ready_path = f.raw.parent / "plan.json", f.raw.parent / "ready.json"
        with patch.object(b,"RAW_ROOT",f.raw), patch.object(b,"PLAN_PATH",plan_path), patch.object(b,"READY_PATH",ready_path), \
             patch.object(b,"metadata_paths",return_value=[metadata]), patch.object(b,"neutral_documents",return_value=f.bundle):
            plan = b.make_plan()
            plan_bytes = b.canonical(plan) + b"\n"
            plan_path.write_bytes(plan_bytes)
            ready = dict(schema_version=1,status="READY",frozen_by="root",scope="p05_independent_source_references",
                actual_build_authorized=True,plan_sha256=b.digest(plan_bytes),code_sha256=plan["code_sha256"],
                environment=plan["environment"],authentication=plan["authentication"],row_guard_cutoff_utc=b.CUTOFF)
            ready_bytes = b.canonical(ready) + b"\n"
            ready_path.write_bytes(ready_bytes)
            yield b.digest(ready_bytes)

    def test_full_execute_real_production_paths_and_locks(self):
        with fixture(reserve=False) as f, self.execution_config(f) as ready_hash:
            result = b.execute(f.output,expected_ready_sha256=ready_hash)
            self.assertEqual(result["cases"]["p05-01"]["disposition"]["status"],"compiled")
            seal = b.parse_json((f.output / "seal.json").read_bytes())
            self.assertEqual(seal["status"],"sealed_verified_source_references")
            self.assertFalse(seal["agent_visible"])
            self.assertFalse(seal["adjudicated_gold"])
            resources = b.parse_json((f.output / "build-report.json").read_bytes())["resources"]
            self.assertGreater(resources["logical_base_completed_hash_bytes"],0)
            self.assertIsNone(resources["physical_io_bytes"])
            from asof.journal import read_chain
            self.assertEqual(read_chain(f.output / "journal.jsonl")[-1]["event"],"build_completed")

    def test_wrong_root_ready_hash_fails_before_original_replay_and_journals(self):
        with fixture(reserve=False) as f, self.execution_config(f):
            with patch.object(b,"replay_sources",side_effect=AssertionError("original value read before authorization")):
                with self.assertRaises(b.ContractError):
                    b.execute(f.output,expected_ready_sha256="0"*64)
            from asof.journal import read_chain
            self.assertEqual(read_chain(f.output / "journal.jsonl")[-1]["event"],"build_failed")
            self.assertTrue((f.output / "failure-seal.json").is_file())

    def test_real_lock_cleanup_failure_is_terminal_and_journaled(self):
        with fixture(reserve=False) as f, self.execution_config(f) as ready_hash:
            original_close = b.ExitStack.close
            first = [True]
            def cleanup(stack):
                original_close(stack)
                if first[0]:
                    first[0] = False
                    raise OSError("fictional cleanup failure after real handles closed")
            with patch.object(b.ExitStack,"close",cleanup):
                with self.assertRaises(OSError):
                    b.execute(f.output,expected_ready_sha256=ready_hash)
            from asof.journal import read_chain
            self.assertEqual(read_chain(f.output / "journal.jsonl")[-1]["event"],"build_failed")
            self.assertFalse((f.output / "seal.json").exists())
            self.assertTrue((f.output / "failure-seal.json").exists())
            failure = b.parse_json((f.output / "failure-seal.json").read_bytes())
            self.assertGreater(failure["resources"]["wall_seconds"],0)

    def test_journal_close_failure_cannot_leave_success_seal(self):
        for after_close in (False,True):
            with self.subTest(after_close=after_close),fixture(reserve=False) as f,self.execution_config(f) as ready_hash:
                original_close = b.RunJournal.close
                first = [True]
                def close(journal):
                    if after_close:
                        original_close(journal)
                    if first[0]:
                        first[0] = False
                        raise OSError("fictional journal close failure")
                    original_close(journal)
                with patch.object(b.RunJournal,"close",close):
                    with self.assertRaises(OSError):
                        b.execute(f.output,expected_ready_sha256=ready_hash)
                self.assertFalse((f.output / "seal.json").exists())
                self.assertTrue((f.output / "failure-seal.json").exists())
                from asof.journal import read_chain
                events = read_chain(f.output / "journal.jsonl")
                if not after_close:
                    self.assertEqual(events[-1]["event"],"build_failed")

    def test_common_wire_string_limit_blocks_without_truncation(self):
        with fixture(credible_rows=[credible(variantId="v"*9000)]) as f:
            detail = replay(f)[1]["p05-01"]
            self.assertEqual(detail["status"],"blocked")
            self.assertIn("fact value string",detail["blocked_reason"])

    def test_record_cap_retains_complete_inventory_as_blocked(self):
        with fixture(credible_rows=[credible() for _ in range(64)],selected_indices=[0]) as f:
            detail = replay(f)[1]["p05-01"]
            self.assertEqual(len(detail["eligible_inventory"]["credible_set"]),64)
            self.assertEqual(detail["status"],"blocked")
            self.assertIn("bounded records",detail["blocked_reason"])

    def test_standalone_verifier_requires_independent_root_ready_hash(self):
        with fixture() as f:
            manifest = compile_manifest(f)
            with self.assertRaises(b.ContractError):
                b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                    approved_raw_root=f.raw,expected_ready_sha256="0"*64)

    def test_standalone_holds_real_code_locks_during_context_and_replay(self):
        with fixture() as f:
            manifest = compile_manifest(f)
            original_stable_files = b.stable_files
            original_context = b.validate_context
            active = []
            @contextmanager
            def locks(paths,**kwargs):
                with original_stable_files(paths,**kwargs):
                    active.append(set(Path(p) for p in paths))
                    try:
                        yield
                    finally:
                        active.pop()
            def context(*args,**kwargs):
                self.assertTrue(set(b.code_paths()) <= set().union(*active))
                return original_context(*args,**kwargs)
            with patch.object(b,"stable_files",locks),patch.object(b,"validate_context",context):
                verified = b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                    approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)
            self.assertEqual(set(verified),{"p05-01"})

    def test_standalone_archived_catalog_tamper_fails_before_values(self):
        with fixture() as f:
            manifest = compile_manifest(f)
            manifest["authorization"]["metadata_files_json"]["catalog"] += " "
            with patch.object(b,"replay_sources",side_effect=AssertionError("values accepted before context")):
                with self.assertRaises(b.ContractError):
                    b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                        approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)

    def test_standalone_task_snapshot_plan_tamper_fails_before_values(self):
        for name in ("p05-01.task.json","source-snapshot.json","selected-case-plan.json"):
            with self.subTest(name=name), fixture() as f:
                manifest = compile_manifest(f)
                manifest["authorization"]["neutral_files_json"][name] += " "
                with patch.object(b,"replay_sources",side_effect=AssertionError("values accepted before context")):
                    with self.assertRaises(b.ContractError):
                        b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                            approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)

    def test_standalone_archived_code_policy_mismatch_fails_before_values(self):
        with fixture() as f:
            manifest = compile_manifest(f)
            context = manifest["authorization"]
            plan = b.parse_json(context["draft_json"].encode("utf-8"))
            first = next(iter(plan["code_sha256"]))
            plan["code_sha256"][first] = "0"*64
            plan_bytes = b.canonical(plan)+b"\n"
            ready = b.parse_json(context["ready_json"].encode("utf-8"))
            ready.update(code_sha256=plan["code_sha256"],plan_sha256=b.digest(plan_bytes))
            ready_bytes = b.canonical(ready)+b"\n"
            context.update(draft_json=plan_bytes.decode("utf-8"),ready_json=ready_bytes.decode("utf-8"))
            manifest["ready_sha256"] = b.digest(ready_bytes)
            with patch.object(b,"replay_sources",side_effect=AssertionError("values accepted before code policy")):
                with self.assertRaisesRegex(b.ContractError,"active code changed"):
                    b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                        approved_raw_root=f.raw,expected_ready_sha256=b.digest(ready_bytes))

    def test_standalone_archived_environment_mismatch_fails_before_values(self):
        with fixture() as f:
            manifest = compile_manifest(f)
            context = manifest["authorization"]
            plan = b.parse_json(context["draft_json"].encode("utf-8"))
            plan["environment"]["python"] = "0.0.0-fiction"
            plan_bytes = b.canonical(plan)+b"\n"
            ready = b.parse_json(context["ready_json"].encode("utf-8"))
            ready.update(environment=plan["environment"],plan_sha256=b.digest(plan_bytes))
            ready_bytes = b.canonical(ready)+b"\n"
            context.update(draft_json=plan_bytes.decode("utf-8"),ready_json=ready_bytes.decode("utf-8"))
            manifest["ready_sha256"] = b.digest(ready_bytes)
            with patch.object(b,"replay_sources",side_effect=AssertionError("values accepted before environment policy")):
                with self.assertRaisesRegex(b.ContractError,"environment changed"):
                    b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                        approved_raw_root=f.raw,expected_ready_sha256=b.digest(ready_bytes))

    def test_declared_ready_and_original_provenance_mismatch_fail_before_values(self):
        for field in ("ready_sha256","original_inputs"):
            with self.subTest(field=field),fixture() as f:
                manifest = compile_manifest(f)
                if field == "ready_sha256":
                    manifest[field] = "0"*64
                else:
                    manifest[field][0]["sha256"] = "0"*64
                with patch.object(b,"replay_sources",side_effect=AssertionError("values accepted before provenance")):
                    with self.assertRaises(b.ContractError):
                        b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                            approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)

    def test_redundant_unit_scope_recipe_time_bindings_fail_before_values(self):
        changes = dict(actual_selected_units=2,unknown_context={},scientific_validation="clinically_validated",
                       computed_at="2026-01-01",recipe_policy="authenticated_by_source_replay",cases={})
        for field,value in changes.items():
            with self.subTest(field=field),fixture() as f:
                manifest = compile_manifest(f)
                manifest[field] = value
                with patch.object(b,"replay_sources",side_effect=AssertionError("values accepted before declared context")):
                    with self.assertRaises(b.ContractError):
                        b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                            approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)

    def test_build_time_cannot_precede_cutoff_or_follow_replay_time(self):
        for timestamp in ("2026-01-01T00:00:00+00:00","2099-01-01T00:00:00+00:00"):
            with self.subTest(timestamp=timestamp),fixture() as f:
                manifest = compile_manifest(f)
                manifest["computed_at"] = timestamp
                with patch.object(b,"replay_sources",side_effect=AssertionError("values accepted before build-time guard")):
                    with self.assertRaises(b.ContractError):
                        b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                            approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)

    def test_standalone_mutable_runtime_catalog_mismatch_fails_before_values(self):
        with fixture() as f:
            manifest = compile_manifest(f)
            f.bundle.docs["catalog"]["datasets"][0]["roles"] = ["evaluation_only"]
            with patch.object(b,"replay_sources",side_effect=AssertionError("values accepted before catalog policy")):
                with self.assertRaisesRegex(b.ContractError,"Archived catalog/frame"):
                    b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                        approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)

    def test_genuine_windows_separator_receipt_is_byte_preserved(self):
        with fixture() as f:
            original = Path(f.inventory[0]["receipt"]["path"]).read_bytes()
            self.assertIn(b"payloads\\\\credible_set.parquet",original)
            paths = [Path(i["path"]) for i in f.inventory] + [Path(i["receipt"]["path"]) for i in f.inventory]
            with b.stable_files(paths,deadline=f.bounds.deadline):
                proofs = b.verify_originals(f.inventory,f.bounds,f.bundle.docs["catalog"],raw_root=f.raw,archive_receipts=True)
            archived = f.output / "_private/receipts" / (proofs[0]["receipt"]["sha256"] + ".json")
            self.assertEqual(archived.read_bytes(),original)

    def test_actual_core_compile_and_wrapper_verify(self):
        with fixture() as f:
            manifest = compile_manifest(f)
            verified = b.verify_p05_references(manifest, b.fingerprint(manifest), f.bundle, f.bounds,
                approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)
            self.assertEqual(set(verified), {"p05-01"})
            self.assertEqual(manifest["cases"]["p05-01"]["reference"]["role"], "evaluation_only")

    def test_native_study_variant_identities_are_separate(self):
        with fixture() as f:
            facts = compile_manifest(f)["cases"]["p05-01"]["reference"]["facts"]
            studies = {x["record_key"]:x["value"] for x in facts if x["field"] == "studyId"}
            self.assertEqual(studies, {"gwas-0000":"GWAS_STUDY", "credible-0000":"CREDIBLE_STUDY"})

    def test_all_physical_matches_and_conflicting_beta_retained(self):
        with fixture(credible_rows=[credible(), credible(beta=-0.5, studyId="OTHER")]) as f:
            ref = compile_manifest(f)["cases"]["p05-01"]["reference"]
            self.assertEqual([x["value"] for x in ref["facts"] if x["field"] == "beta"], [0.125, -0.5])
            self.assertEqual(ref["joins"][0]["cardinality"], "one_to_many")
            self.assertEqual(len(ref["joins"][0]["matched_records"]), 2)

    def test_identical_duplicate_physical_rows_are_not_deduplicated(self):
        with fixture(credible_rows=[credible(),credible()]) as f:
            ref = compile_manifest(f)["cases"]["p05-01"]["reference"]
            self.assertEqual(len([x for x in ref["facts"] if x["field"] == "beta"]), 2)

    def test_future_duplicate_excluded_before_compile(self):
        with fixture(credible_rows=[credible(annotationDate="2027-01-01"), credible()], selected_indices=[1]) as f:
            manifest = compile_manifest(f)
            self.assertEqual(manifest["cases"]["p05-01"]["disposition"]["excluded_inventory"][0]["locator"]["row_group"], 0)
            self.assertIsNotNone(manifest["cases"]["p05-01"]["reference"])

    def test_precision_future_month_duplicate_excluded(self):
        with fixture(credible_rows=[credible(publicationDate="2026-11"), credible()], selected_indices=[1]) as f:
            detail = replay(f)[1]["p05-01"]
            self.assertIn("publication_date_precision_unverified", detail["excluded_inventory"][0]["exclusion_reasons"])

    def test_publication_precision_intersection_not_coerced_for_core(self):
        with fixture(credible_rows=[credible(publicationDate="2025-01", publicationYear=2025)]) as f:
            detail = replay(f)[1]["p05-01"]
            self.assertEqual(detail["status"], "blocked")
            self.assertIsNotNone(detail["blocked_reason"])

    def test_publication_date_year_conflict_excluded(self):
        with fixture(credible_rows=[credible(publicationDate="2025-01-01", publicationYear=2024),credible()], selected_indices=[1]) as f:
            self.assertIn("publication_date_conflict", replay(f)[1]["p05-01"]["excluded_inventory"][0]["exclusion_reasons"])

    def test_null_and_missing_measurements_have_explicit_unknowns(self):
        row = credible(beta=None)
        del row["standardError"]
        # Presence is an acquisition schema requirement; null remains representable.
        row["standardError"] = None
        with fixture(credible_rows=[row]) as f:
            facts = compile_manifest(f)["cases"]["p05-01"]["reference"]["facts"]
            self.assertEqual(next(x for x in facts if x["field"] == "beta")["unknown_reason"], "null_source_value")

    def test_zero_credible_inventory_retains_case_without_measurement_slots(self):
        with fixture(credible_rows=[]) as f:
            value = compile_manifest(f)["cases"]["p05-01"]
            self.assertEqual(value["reference"]["joins"][0]["status"], "zero_matches_selected_collection")
            self.assertFalse(any(x["family"] == "reported_measurement" for x in value["reference"]["facts"]))

    def test_boolean_measurement_blocks_without_numeric_coercion(self):
        with fixture(credible_rows=[credible(beta=True)]) as f:
            self.assertEqual(compile_manifest(f)["cases"]["p05-01"]["disposition"]["status"], "blocked")

    def test_noninteger_exponent_blocks(self):
        with fixture(credible_rows=[credible(pValueExponent=-8.5)]) as f:
            self.assertIn("requires int", replay(f)[1]["p05-01"]["blocked_reason"])

    def test_nonfinite_numeric_blocks(self):
        with fixture(credible_rows=[credible(beta=float("inf"))]) as f:
            self.assertEqual(replay(f)[1]["p05-01"]["status"], "blocked")

    def test_scope_disagreement_blocks_case(self):
        with fixture(credible_rows=[credible(targetId="WRONG_TARGET")]) as f:
            self.assertIn("scope field disagrees", replay(f)[1]["p05-01"]["blocked_reason"])

    def test_canonical_exposed_mapping_excludes_anchor(self):
        with fixture(target_symbol="PCSK9") as f:
            detail = replay(f)[1]["p05-01"]
            self.assertEqual(detail["status"], "blocked")
            self.assertTrue(any("known_exposed_symbol" in x["exclusion_reasons"] for x in detail["excluded_inventory"]))

    def test_evaluator_original_role_rejected_before_values(self):
        with fixture() as f:
            f.bundle.docs["catalog"]["datasets"][0]["roles"] = ["evaluation_only"]
            with self.assertRaises(b.ContractError):
                replay(f)

    def test_disclosed_derived_ancestor_rejected(self):
        with fixture() as f:
            f.inventory[0]["parents"] = ["private-gold"]
            with self.assertRaises(b.ContractError):
                replay(f)

    def test_native_date_replay_binds_excluded_inventory(self):
        with fixture(credible_rows=[credible(annotationDate="2027-01-01"),credible()],selected_indices=[1]) as f:
            manifest = compile_manifest(f)
            manifest["cases"]["p05-01"]["disposition"]["excluded_inventory"] = []
            with self.assertRaises(b.ContractError):
                b.verify_p05_references(manifest,b.fingerprint(manifest),f.bundle,f.bounds,
                    approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)

    def test_task_inventory_tampering_blocks(self):
        with fixture() as f:
            f.task["records"][1]["identity"]["studyId"] = "TAMPERED"
            self.assertIn("task/inventory differs", replay(f)[1]["p05-01"]["blocked_reason"])

    def test_wrapper_hash_tamper_rejected(self):
        with fixture() as f:
            manifest = compile_manifest(f)
            with self.assertRaises(b.ContractError):
                b.verify_p05_references(manifest,"0"*64,f.bundle,f.bounds,
                    approved_raw_root=f.raw,expected_ready_sha256=f.ready_sha256)

    def test_no_generation_output_read(self):
        with fixture() as f:
            real_read = Path.read_bytes
            def read(path):
                self.assertFalse("packets" in path.parts or path.name == "answer.json")
                return real_read(path)
            with patch.object(Path,"read_bytes",read):
                compile_manifest(f)

    def test_real_production_parent_is_exclusive(self):
        with fixture() as f:
            with self.assertRaises(b.ContractError):
                b.validate_output_location(f.output)
            with self.assertRaises(b.ContractError):
                b.validate_output_location(f.output.parent.parent / f.output.name)

    def test_real_stable_lock_denies_write(self):
        with fixture() as f:
            path = Path(f.inventory[0]["path"])
            with b.stable_files([path],deadline=f.bounds.deadline):
                with self.assertRaises(PermissionError):
                    path.write_bytes(b"tampering")

    def test_default_cli_requires_explicit_build_and_ready_hash(self):
        with self.assertRaises(SystemExit):
            b.main([])
        with self.assertRaises(b.ContractError):
            b.main(["--build","--output",str(b.OUTPUT_ROOT / "preprint-p05-references-20990101T000001Z")])


if __name__ == "__main__":
    unittest.main()
