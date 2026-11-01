"""Fictional-only stage-2 input-builder checks; never opens real originals."""
from contextlib import ExitStack, contextmanager, nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("p05_inputs", ROOT / "tools/science/prepare_source_validation_inputs.py")
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


def fictional_directory():
    cache = ROOT / "data/cache"
    cache.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix="p05-input-fictional-", dir=cache)


def case():
    result = dict(case_id="p05-01", targetId="ENSG_FAKE_1", diseaseId="EFO_FAKE_2", studyLocusId="locus-fiction", release_id="25.09")
    result["unit_hash"] = b.stage1.unit_hash("25.09", b.stage1.unit_key(result))
    return result


def gwas(**changes):
    result = dict(id="evidence-fiction", targetId="ENSG_FAKE_1", diseaseId="EFO_FAKE_2", studyLocusId="locus-fiction",
                  studyId="GWAS_NATIVE", variantId="GWAS_VARIANT", datasourceId="gwas_credible_sets", datatypeId="genetic_association")
    result.update(changes)
    return result


def credible(**changes):
    result = dict(studyLocusId="locus-fiction", studyId="CREDIBLE_NATIVE", variantId="CREDIBLE_VARIANT", beta=0.125,
                  standardError=0.25, pValueMantissa=1.5, pValueExponent=-8, chromosome="1", position=42, sampleSize=123)
    result.update(changes)
    return result


def record(row, family="credible_set", index=0):
    return dict(source_id="original-000" if family == "gwas_credible_sets" else "original-001", family=family,
                locator=dict(format="parquet", row_group=0, row=index), physical_row_0based=index, values=row)


def groups(rows=None):
    return {"gwas_credible_sets": [record(gwas(), "gwas_credible_sets")],
            "credible_set": [record(row, index=i) for i, row in enumerate([credible()] if rows is None else rows)]}


def indexes():
    def item(values, family):
        return dict(values=values, locator=dict(source_relative_path="fiction/" + family, source_sha256="a" * 64, row_group_0based=0, row_in_group_0based=0, physical_row_0based=0))
    return b.stage1.mapping_index({"target": [item(dict(id="ENSG_FAKE_1", approvedSymbol="FAKEGENE"), "target")],
        "disease": [item(dict(id="EFO_FAKE_2", name="Fictional phenotype"), "disease")],
        "hgnc": [item(dict(hgnc_id="HGNC:FAKE", symbol="FAKEGENE", ensembl_gene_id="ENSG_FAKE_1", status="Approved"), "hgnc")]})


def nodes():
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    availability = b.Availability(None, None, None, None, observed.date(), "public_download_receipt", "fictional", observed, "f" * 64)
    return SimpleNamespace(sources=tuple(b.SourceNode("original-" + f"{i:03d}", "fiction", "25.09", f"fiction/{i}.parquet",
        ("a" if i == 0 else "b") * 64, "agent_evidence", availability, b.TemporalClass.CONTEMPORARY,
        "https://example.invalid/fiction", receipt_path=f"fiction/{i}.receipt.json", receipt_sha256="f" * 64) for i in range(2)))


@contextmanager
def fictional_build():
    """Five real original files/receipts, real locks/journal; metadata authority is fictional."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    with fictional_directory() as folder, ExitStack() as stack:
        workspace = Path(folder)
        output_root = workspace / "data/derived"
        output_root.mkdir(parents=True)
        raw_root = workspace / "originals"
        raw_root.mkdir()
        inventory, datasets = [], []
        families = [("gwas_credible_sets", [{**gwas(), "diseaseFromSourceMappedId": None}]), ("credible_set", [credible()]),
            ("target", [dict(id="ENSG_FAKE_1", approvedSymbol="FAKEGENE")]),
            ("disease", [dict(id="EFO_FAKE_2", name="Fictional phenotype")]),
            ("hgnc", [dict(hgnc_id="HGNC:FAKE", symbol="FAKEGENE", ensembl_gene_id="ENSG_FAKE_1", status="Approved")])]
        for number, (family, rows) in enumerate(families):
            path = raw_root / (family + (".tsv" if family == "hgnc" else ".parquet"))
            if family == "hgnc":
                fields = list(rows[0])
                path.write_text("\t".join(fields) + "\n" + "\t".join(rows[0][k] for k in fields) + "\n", encoding="utf-8")
            else:
                table = pa.Table.from_pylist(rows)
                fields = table.schema.names
                pq.write_table(table, path)
            payload = path.read_bytes()
            receipt_path = raw_root / (family + ".receipt.json")
            dataset = "fiction_" + family
            receipt = dict(status="completed", dataset_id=dataset, release_id="25.09", relative_path=path.name,
                sha256=b.digest(payload), bytes=len(payload), url="https://example.invalid/" + family, completed_at_utc="2026-01-01T00:00:00+00:00")
            receipt_bytes = b.canonical(receipt) + b"\n"
            receipt_path.write_bytes(receipt_bytes)
            inventory.append(dict(family=family, dataset_id=dataset, release_id="25.09", path=str(path), relative_path=path.name,
                sha256=b.digest(payload), bytes=len(payload), source_url=receipt["url"], fields=fields, rows=len(rows),
                receipt=dict(path=str(receipt_path), sha256=b.digest(receipt_bytes), bytes=len(receipt_bytes))))
            datasets.append(dict(dataset_id=dataset, roles=["reference" if family == "hgnc" else "agent_evidence"]))
        catalog = dict(schema_version=1, datasets=datasets)
        metadata = workspace / "fiction-neutral-routing.json"
        routing_bytes = b.canonical(dict(cases=[case()], role="neutral_metadata")) + b"\n"
        metadata.write_bytes(routing_bytes)
        code = workspace / "fiction-builder.py"
        code.write_bytes(b"# fictional immutable dependency\n")
        pins = {code.name: b.digest(code.read_bytes())}
        limits = {**b.LIMITS, "files": 5}
        auth = dict(stage1_case_plan_sha256=b.digest(routing_bytes))
        environment = b.stage1.environment()
        plan = dict(status="DRAFT", actual_build_authorized=False, code_sha256=pins, environment=environment,
            limits=limits, row_guard_cutoff_utc=b.CUTOFF, authentication=auth, denied_inputs=["fictional_forbidden_evaluator"])
        plan_path, ready_path = workspace / "plan.json", workspace / "ready.json"
        plan_bytes = b.canonical(plan) + b"\n"
        plan_path.write_bytes(plan_bytes)
        ready = dict(schema_version=1, status="READY", scope="p05_source_only_stage2_inputs", frozen_by="root", actual_build_authorized=True,
            plan_sha256=b.digest(plan_bytes), code_sha256=pins, environment=environment, row_guard_cutoff_utc=b.CUTOFF,
            stage1_case_plan_sha256=auth["stage1_case_plan_sha256"])
        ready_bytes = b.canonical(ready) + b"\n"
        ready_path.write_bytes(ready_bytes)
        replacements = dict(WORKSPACE=workspace, OUTPUT_ROOT=output_root, RAW_ROOT=raw_root, PLAN_PATH=plan_path, READY_PATH=ready_path,
            LIMITS=limits)
        for name, value in replacements.items():
            stack.enter_context(patch.object(b, name, value))
        stack.enter_context(patch.object(b, "metadata_paths", return_value=[metadata]))
        stack.enter_context(patch.object(b, "code_paths", return_value=[code]))
        stack.enter_context(patch.object(b, "code_pins", return_value=pins))
        stack.enter_context(patch.object(b, "make_plan", return_value=plan))
        stack.enter_context(patch.object(b, "neutral_documents", return_value=({"catalog": catalog}, inventory, [case()], auth, routing_bytes)))
        stack.enter_context(patch.object(b.subprocess, "run", return_value=SimpleNamespace(returncode=0)))
        yield SimpleNamespace(output=output_root / "preprint-p05-source-inputs-20990101T000002Z", ready_sha256=b.digest(ready_bytes),
            inventory=inventory, raw_root=raw_root)


class RoutingAndFreezeTests(unittest.TestCase):
    def route(self):
        return dict(schema_version=1, role="neutral_metadata", product_kind="neutral_selected_case_plan", agent_visible=False,
            plan_sha256="a" * 64, row_guard_cutoff_utc=b.CUTOFF, no_replacement=True, numeric_availability_used=False,
            model_performance_used=False, selection_seed=b.stage1.SEED, cases=[case()], actual_selected_units=1)

    def test_route_retains_only_neutral_identities(self):
        route = self.route()
        route["cases"][0]["eligible_physical_rows"] = 999999
        self.assertEqual(b.route_contract(route, stage1_plan_sha256="a" * 64), [case()])

    def test_evaluation_parent_cannot_be_relabelled_by_product_kind(self):
        route = self.route()
        route["role"] = "evaluation_only"
        with self.assertRaises(b.ContractError):
            b.route_contract(route, stage1_plan_sha256="a" * 64)

    def test_routing_hash_and_count_fail_closed(self):
        for mutate in (lambda x: x["cases"][0].update(unit_hash="f" * 64), lambda x: x.update(actual_selected_units=2),
                       lambda x: x.update(numeric_availability_used=True), lambda x: x.update(no_replacement=False)):
            route = self.route()
            mutate(route)
            with self.assertRaises(b.ContractError):
                b.route_contract(route, stage1_plan_sha256="a" * 64)

    def test_duplicate_route_is_rejected(self):
        route = self.route()
        route.update(cases=[case(), case()], actual_selected_units=2)
        with self.assertRaises(b.ContractError):
            b.route_contract(route, stage1_plan_sha256="a" * 64)

    def test_build_requires_external_exact_root_ready_hash(self):
        plan = dict(status="DRAFT", actual_build_authorized=False, code_sha256={"fiction.py": "a" * 64},
            environment={"fiction": True}, limits=b.LIMITS, row_guard_cutoff_utc=b.CUTOFF,
            authentication=dict(stage1_case_plan_sha256="b" * 64))
        payload = b.canonical(plan)
        ready = dict(schema_version=1, status="READY", scope="p05_source_only_stage2_inputs", frozen_by="root",
            actual_build_authorized=True, plan_sha256=b.digest(payload), code_sha256=plan["code_sha256"], environment=plan["environment"],
            row_guard_cutoff_utc=b.CUTOFF, stage1_case_plan_sha256="b" * 64)
        frozen = b.canonical(ready)
        b.validate_freeze(plan, payload, ready, b.digest(frozen), frozen, current_code=plan["code_sha256"], current_environment=plan["environment"])
        for key, value in (("frozen_by", "child"), ("actual_build_authorized", False), ("row_guard_cutoff_utc", "2026-11-02T00:00:00Z")):
            changed = {**ready, key: value}
            raw = b.canonical(changed)
            with self.assertRaises(b.ContractError):
                b.validate_freeze(plan, payload, changed, b.digest(raw), raw, current_code=plan["code_sha256"], current_environment=plan["environment"])
        with self.assertRaises(b.ContractError):
            b.validate_freeze(plan, payload, ready, "0" * 64, frozen, current_code=plan["code_sha256"], current_environment=plan["environment"])

    def test_code_changes_after_freeze_fail(self):
        plan = dict(status="DRAFT", actual_build_authorized=False, code_sha256={}, environment={}, limits=b.LIMITS,
                    row_guard_cutoff_utc=b.CUTOFF, authentication=dict(stage1_case_plan_sha256="b" * 64))
        raw = b.canonical(plan)
        ready = dict(schema_version=1, status="READY", scope="p05_source_only_stage2_inputs", frozen_by="root", actual_build_authorized=True,
            plan_sha256=b.digest(raw), code_sha256={}, environment={}, row_guard_cutoff_utc=b.CUTOFF, stage1_case_plan_sha256="b" * 64)
        frozen = b.canonical(ready)
        with self.assertRaisesRegex(b.ContractError, "implementation"):
            b.validate_freeze(plan, raw, ready, b.digest(frozen), frozen, current_code={"changed": "c" * 64}, current_environment={})


class LiteralTaskTests(unittest.TestCase):
    def test_all_physical_credible_duplicates_and_conflicts_remain(self):
        inventory = groups([credible(), credible(), credible(beta=-0.5, studyId="OTHER_STUDY")])
        task = b.build_task(case(), inventory)
        self.assertEqual(len(task["records"]), 4)
        self.assertEqual(task["joins"][0]["cardinality"], "one_to_many")
        self.assertEqual(task["joins"][0]["right_records"], ["credible-0000", "credible-0001", "credible-0002"])
        self.assertEqual(len([f for f in task["fields"] if f["family"] == "reported_measurement"]), 12)
        self.assertEqual(len({f["group"] for f in task["fields"] if f["family"] == "reported_measurement"}), 3)
        self.assertEqual(task["records"][1]["identity"]["studyId"], "CREDIBLE_NATIVE")
        self.assertEqual(task["records"][0]["identity"]["studyId"], "GWAS_NATIVE")

    def test_duplicate_gwas_anchors_each_get_full_locus_join(self):
        inventory = groups()
        inventory["gwas_credible_sets"].append(record(gwas(id="second"), "gwas_credible_sets", 1))
        task = b.build_task(case(), inventory)
        self.assertEqual(len(task["joins"]), 2)
        self.assertTrue(all(j["right_records"] == ["credible-0000"] for j in task["joins"]))

    def test_missing_native_identity_is_requested_separately(self):
        inventory = groups([credible(studyId=None, variantId="")])
        task = b.build_task(case(), inventory)
        self.assertNotIn("studyId", task["records"][1]["identity"])
        names = [f["field"] for f in task["fields"] if f["record_key"] == "credible-0000"]
        self.assertIn("studyId", names)
        self.assertIn("variantId", names)
        self.assertTrue(all(f["empty_policy"] == "unknown" and f["unit_field"] is None for f in task["fields"]))

    def test_zero_credible_rows_does_not_invent_measurement_slots(self):
        task = b.build_task(case(), groups([]))
        self.assertEqual(task["joins"][0]["right_records"], [])
        self.assertEqual(task["joins"][0]["inventory_status"], "complete")
        self.assertEqual([f for f in task["fields"] if f["family"] == "reported_measurement"], [])

    def test_scope_unknowns_are_explicit_and_no_intervention_inferred(self):
        task = b.build_task(case(), groups())
        self.assertEqual([task["scope"][k] for k in ("action", "modality", "tissue")], [None, None, None])
        self.assertEqual(task["scope"]["target_namespace_version"], "unknown")
        self.assertIn("not inferred", b.UNKNOWN_CONTEXT["genome_build"])

    def test_core_limit_is_not_changed_or_truncated(self):
        inventory = groups([credible() for _ in range(64)])
        before = deepcopy(inventory)
        with self.assertRaisesRegex(b.ContractError, "records"):
            b.build_task(case(), inventory)
        self.assertEqual(inventory, before)

    def test_native_numeric_types_fail_without_coercion(self):
        for field, value in (("beta", True), ("standardError", "0.25"), ("beta", float("nan")), ("pValueExponent", -8.0)):
            with self.subTest(field=field, value=value), self.assertRaises(b.ContractError):
                b.native_representability(record(credible(**{field: value})))
        b.native_representability(record(credible(beta=None, standardError=None)))

    def test_precision_eligible_native_date_can_be_core_unrepresentable(self):
        row = credible(publicationDate="2025-02")
        self.assertEqual(b.stage1.date_guard(row, b.utc(b.CUTOFF))["exclusion_reasons"], [])
        with self.assertRaises(b.ContractError):
            b.native_representability(record(row))
        with self.assertRaises(b.ContractError):
            b.native_representability(record(credible(publicationYear="2025")))

    def test_timezone_offset_not_rewritten_for_core(self):
        row = credible(evidenceDate="2025-01-01T01:00:00+01:00")
        self.assertEqual(b.stage1.date_guard(row, b.utc(b.CUTOFF))["exclusion_reasons"], [])
        with self.assertRaises(b.ContractError):
            b.native_representability(record(row))

    def test_native_automatic_scope_mismatch_blocks_without_coercion(self):
        with self.assertRaises(b.ContractError):
            b.native_representability(record(credible(targetId="OTHER_TARGET")), case())

    def test_complete_packet_preserves_originals_and_slots_have_no_answers(self):
        inventory = groups([credible(beta=None, standardError=0.25)])
        before = deepcopy(inventory)
        mapping = b.normalization_proof(case(), inventory["gwas_credible_sets"], indexes())
        packet = b.make_packet(case(), inventory, mapping, nodes(), [], "c" * 64,
            computed_at="2026-11-01T08:00:00+00:00", routing_sha256="d" * 64)
        self.assertEqual(inventory, before)
        self.assertEqual(packet["source_records"][1]["values"]["beta"], None)
        self.assertEqual(packet["source_records"][1]["values"]["standardError"], 0.25)
        self.assertTrue(all(set(slot) == {"fact_id", "record_key", "field", "source"} for slot in packet["fact_skeleton"]))
        self.assertEqual(packet["lineage"]["reference_inputs"], [])
        self.assertEqual(packet["lineage"]["input_refs"][-1]["kind"], "neutral_selected_case_plan")

    def test_aggregate_common_wire_size_blocks_without_dropping_rows(self):
        inventory = groups([credible(studyId="s" * 8192, variantId="v" * 8192) for _ in range(20)])
        before = deepcopy(inventory)
        mapping = b.normalization_proof(case(), inventory["gwas_credible_sets"], indexes())
        with self.assertRaisesRegex(b.ContractError, "serialized-size"):
            b.make_packet(case(), inventory, mapping, nodes(), [], "c" * 64,
                computed_at="2026-11-01T08:00:00+00:00", routing_sha256="d" * 64)
        self.assertEqual(inventory, before)

    def test_original_mapping_rechecked_and_conflicts_fail(self):
        ix = indexes()
        proof = b.normalization_proof(case(), groups()["gwas_credible_sets"], ix)
        self.assertEqual(proof["target_id_from_raw_GWAS"], "ENSG_FAKE_1")
        ix["hgnc"]["ENSG_FAKE_1"][0]["values"]["symbol"] = "WRONG"
        with self.assertRaises(b.ContractError):
            b.normalization_proof(case(), groups()["gwas_credible_sets"], ix)


class OriginalBoundaryTests(unittest.TestCase):
    def test_future_duplicate_excluded_before_any_value_retention(self):
        ix = indexes()
        rows = [("p05-01", record(gwas(), "gwas_credible_sets")),
                ("p05-01", record(gwas(beta=987654, evidenceDate="2027-01-01"), "gwas_credible_sets", 1)),
                ("p05-01", record(credible()))]
        proofs = [dict(family="gwas_credible_sets"), dict(family="credible_set")]
        def matches(item, *_):
            return iter([r for r in rows if r[1]["family"] == item["family"]])
        with fictional_directory() as folder, patch.object(b, "matching_rows", side_effect=matches):
            selected, excluded = b.select_eligible([case()], proofs, ix, b.Bounds(Path(folder)))
        self.assertEqual(len(selected["p05-01"]["gwas_credible_sets"]), 1)
        self.assertEqual(len(excluded["p05-01"]), 1)
        self.assertNotIn("987654", b.canonical(excluded).decode())
        self.assertNotIn("values", excluded["p05-01"][0])

    def test_credible_future_date_excluded_with_only_reason_and_locator(self):
        rows = [("p05-01", record(credible(publicationDate="2027-01-01", beta=987654)))]
        with fictional_directory() as folder, patch.object(b, "matching_rows", return_value=iter(rows)):
            selected, excluded = b.select_eligible([case()], [dict(family="credible_set")], indexes(), b.Bounds(Path(folder)))
        self.assertEqual(selected["p05-01"]["credible_set"], [])
        self.assertNotIn("987654", b.canonical(excluded).decode())

    def test_future_annotation_duplicate_is_excluded_before_case_assembly(self):
        rows = [("p05-01", record(credible())), ("p05-01", record(credible(annotationDate="2027-01-01", beta=987654), index=1))]
        with fictional_directory() as folder, patch.object(b, "matching_rows", return_value=iter(rows)):
            selected, excluded = b.select_eligible([case()], [dict(family="credible_set")], indexes(), b.Bounds(Path(folder)))
        self.assertEqual(len(selected["p05-01"]["credible_set"]), 1)
        self.assertEqual(excluded["p05-01"][0]["exclusion_reasons"], ["annotationDate_explicit_future"])
        self.assertNotIn("987654", b.canonical(excluded).decode())

    def test_publication_precision_conflict_is_excluded(self):
        guard = b.stage1.date_guard(gwas(publicationDate="2024-01-01", publicationYear=2025), b.utc(b.CUTOFF))
        self.assertIn("publication_date_conflict", guard["exclusion_reasons"])

    def test_windows_receipt_separator_identity_is_exact_otherwise(self):
        item = dict(dataset_id="fiction", release_id="25.09", sha256="a" * 64, bytes=17, source_url="https://example.invalid/original",
                    relative_path="fiction/release/payload.parquet")
        receipt = dict(status="completed", dataset_id="fiction", release_id="25.09", sha256="a" * 64, bytes=17,
                       url=item["source_url"], relative_path="fiction\\release\\payload.parquet")
        self.assertTrue(b.stage1.check_receipt_identity(receipt, item)["relative_path_separator_normalized"])
        receipt["url"] += "wrong"
        with self.assertRaises(b.ContractError):
            b.stage1.check_receipt_identity(receipt, item)

    def test_all_payload_hashes_precede_receipt_parse(self):
        with fictional_directory() as folder:
            root = Path(folder)
            inventory = [dict(path=str(root / f"{i}.parquet"), relative_path=f"{i}.parquet", dataset_id="fiction", family="credible_set",
                sha256="a" * 64, bytes=1) for i in range(2)]
            catalog = dict(schema_version=1, datasets=[dict(dataset_id="fiction", roles=["agent_evidence"])])
            changed = {**b.LIMITS, "files": 2}
            with patch.object(b, "LIMITS", changed), patch.object(b, "checked_path", side_effect=lambda raw, rel: raw / rel), \
                 patch.object(b, "hash_file", side_effect=[dict(sha256="a" * 64, bytes=1), dict(sha256="b" * 64, bytes=1)]), \
                 patch.object(b, "read_file", side_effect=AssertionError("receipt read too early")) as read:
                with self.assertRaisesRegex(b.ContractError, "hash/size"):
                    b.verify_originals(inventory, b.Bounds(root), catalog, raw_root=root)
                read.assert_not_called()

    def test_catalog_evaluation_role_is_rejected_before_hash(self):
        inventory = [dict(path="fiction", relative_path="fiction", dataset_id="fiction", family="credible_set", bytes=1)]
        catalog = dict(schema_version=1, datasets=[dict(dataset_id="fiction", roles=["evaluation_only"])])
        with fictional_directory() as folder, patch.object(b, "LIMITS", {**b.LIMITS, "files": 1}), patch.object(b, "hash_file") as hashed:
            with self.assertRaises(b.ContractError):
                b.verify_originals(inventory, b.Bounds(Path(folder)), catalog)
            hashed.assert_not_called()

    def test_actual_path_guard_rejects_parent_and_alias_spelling(self):
        with fictional_directory() as folder:
            for relative in ("../escape", "a/../b", "a\\b"):
                with self.subTest(relative=relative), self.assertRaises(b.ContractError):
                    b.checked_path(Path(folder), relative)

    def test_real_parquet_row_group_locators_and_filter(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        with fictional_directory() as folder:
            path = Path(folder) / "fiction.parquet"
            table = pa.Table.from_pylist([credible(studyLocusId="elsewhere"), credible(beta=0.25), credible(beta=0.5)])
            pq.write_table(table, path, row_group_size=2)
            item = dict(path=str(path), family="credible_set", source_id="original-001", fields=table.schema.names, rows=3, bytes=path.stat().st_size)
            rows = list(b.matching_rows(item, [case()], b.Bounds(Path(folder))))
        self.assertEqual([r[1]["locator"] for r in rows], [dict(format="parquet", row_group=0, row=1), dict(format="parquet", row_group=1, row=0)])
        self.assertEqual([r[1]["physical_row_0based"] for r in rows], [1, 2])


class LifecycleTests(unittest.TestCase):
    def test_full_fictional_execute_success_with_real_locks_and_seal(self):
        with fictional_build() as fixture:
            before = {p: p.read_bytes() for p in fixture.raw_root.iterdir()}
            seal = b.execute(fixture.output, expected_ready_sha256=fixture.ready_sha256)
            self.assertEqual(seal["status"], "completed_source_only_stage2_inputs")
            self.assertEqual(seal["packet_count"], 1)
            self.assertEqual(seal["blocked_case_count"], 0)
            self.assertFalse((fixture.output / "failure-seal.json").exists())
            self.assertEqual(before, {p: p.read_bytes() for p in fixture.raw_root.iterdir()})
            packet = b.parse_json((fixture.output / "packets/p05-01.json").read_bytes())
            self.assertEqual(packet["source_records"][1]["values"]["beta"], 0.125)
            self.assertEqual(packet["lineage"]["reference_inputs"], [])

    def test_real_lock_exit_failure_prevents_success_seal(self):
        real = b.stable_files
        with fictional_build() as fixture:
            @contextmanager
            def injected(paths, *, deadline):
                paths = list(paths)
                with real(paths, deadline=deadline):
                    yield
                if Path(fixture.inventory[0]["path"]) in paths:
                    raise OSError("fictional original lock cleanup fault")
            with patch.object(b, "stable_files", side_effect=injected), self.assertRaisesRegex(OSError, "lock cleanup"):
                b.execute(fixture.output, expected_ready_sha256=fixture.ready_sha256)
            self.assertTrue((fixture.output / "failure-seal.json").exists())
            self.assertFalse((fixture.output / "seal.json").exists())

    def test_real_journal_close_failure_prevents_success_seal(self):
        real = b.RunJournal.close
        with fictional_build() as fixture:
            state = {"raised": False}
            def injected(journal):
                real(journal)
                if not state["raised"]:
                    state["raised"] = True
                    raise OSError("fictional journal close fault")
            with patch.object(b.RunJournal, "close", new=injected), self.assertRaisesRegex(OSError, "journal close"):
                b.execute(fixture.output, expected_ready_sha256=fixture.ready_sha256)
            self.assertTrue((fixture.output / "failure-seal.json").exists())
            self.assertFalse((fixture.output / "seal.json").exists())

    def test_exclusive_reservation_rejects_existing_directory(self):
        with fictional_directory() as folder:
            output = Path(folder)
            with self.assertRaises(FileExistsError):
                b.RunJournal(output, kind="build")

    def test_output_path_outside_approved_root_is_rejected(self):
        with fictional_directory() as folder, self.assertRaises(b.ContractError):
            b.validate_output_location(Path(folder) / "preprint-p05-source-inputs-20261101T000000Z")

    def test_fresh_entry_uses_real_parent_leaf_journal_and_stable_locks(self):
        with fictional_directory() as folder:
            workspace = Path(folder)
            approved = workspace / "data/derived"
            approved.mkdir(parents=True)
            output = approved / "preprint-p05-source-inputs-20990101T000000Z"
            with patch.object(b, "WORKSPACE", workspace), patch.object(b, "OUTPUT_ROOT", approved), \
                 patch.object(b.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
                self.assertEqual(b.validate_output_location(output), output)
                self.assertFalse(output.exists())
                journal = b.RunJournal(output, kind="build")
                try:
                    self.assertEqual(b.checked_path(workspace, output.relative_to(workspace).as_posix()), output)
                    metadata = workspace / "fiction-metadata.json"
                    metadata.write_bytes(b"{}")
                    with b.stable_files([metadata], deadline=b.time.monotonic() + 30):
                        self.assertTrue((output / "journal.jsonl").is_file())
                finally:
                    journal.close()
                with self.assertRaises(b.ContractError):
                    b.validate_output_location(output)

    def test_execute_passes_real_entry_and_locks_before_fictional_auth_failure(self):
        with fictional_directory() as folder:
            workspace = Path(folder)
            approved = workspace / "data/derived"
            approved.mkdir(parents=True)
            output = approved / "preprint-p05-source-inputs-20990101T000001Z"
            metadata = workspace / "metadata.json"
            metadata.write_bytes(b"{}")
            with patch.object(b, "WORKSPACE", workspace), patch.object(b, "OUTPUT_ROOT", approved), \
                 patch.object(b.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                 patch.object(b, "metadata_paths", return_value=[metadata]), patch.object(b, "code_paths", return_value=[]), \
                 patch.object(b, "PLAN_PATH", metadata), patch.object(b, "READY_PATH", metadata), patch.object(b, "verify_originals") as originals:
                with self.assertRaisesRegex(b.ContractError, "READY hash"):
                    b.execute(output, expected_ready_sha256="a" * 64)
                originals.assert_not_called()
            self.assertTrue((output / "failure-seal.json").is_file())

    def test_authorization_failure_seals_without_original_reads(self):
        with fictional_directory() as folder:
            output = Path(folder) / "fresh"
            with patch.object(b, "validate_output_location", return_value=output), patch.object(b, "stable_files", return_value=nullcontext()), \
                 patch.object(b, "read_file", side_effect=b.ContractError("fictional authorization rejection")), patch.object(b, "verify_originals") as read_originals:
                with self.assertRaises(b.ContractError):
                    b.execute(output, expected_ready_sha256="a" * 64)
                read_originals.assert_not_called()
            failure = b.parse_json((output / "failure-seal.json").read_bytes())
            self.assertEqual(failure["status"], "failed_stage2_partial_not_usable")
            self.assertFalse((output / "seal.json").exists())

    def test_failure_seal_does_not_replace_previous_bytes(self):
        with fictional_directory() as folder:
            output = Path(folder)
            b.failure_seal(output, "fiction", ValueError())
            first = (output / "failure-seal.json").read_bytes()
            with self.assertRaises((FileExistsError, b.ContractError)):
                b.failure_seal(output, "changed", TypeError())
            self.assertEqual((output / "failure-seal.json").read_bytes(), first)

    def test_failure_seal_retains_terminal_status_if_partial_hash_fails(self):
        with fictional_directory() as folder:
            output = Path(folder)
            (output / "partial.json").write_bytes(b"{}")
            with patch.object(b, "hash_file", side_effect=TimeoutError("fictional hash deadline")):
                b.failure_seal(output, "fiction", ValueError())
            seal = b.parse_json((output / "failure-seal.json").read_bytes())
            self.assertEqual(seal["status"], "failed_stage2_partial_not_usable")
            self.assertEqual(seal["retained_artifacts"][0]["hash_status"], "unavailable:TimeoutError")

    def test_failure_seal_attempted_when_journal_fail_append_errors(self):
        with fictional_directory() as folder:
            output = Path(folder) / "fresh"
            with patch.object(b, "validate_output_location", return_value=output), patch.object(b, "stable_files", return_value=nullcontext()), \
                 patch.object(b, "read_file", side_effect=b.ContractError("fictional authorization rejection")), \
                 patch.object(b.RunJournal, "fail", side_effect=OSError("fictional journal fault")):
                with self.assertRaisesRegex(b.ContractError, "fictional authorization"):
                    b.execute(output, expected_ready_sha256="a" * 64)
            self.assertTrue((output / "failure-seal.json").is_file())

    def test_no_reference_or_model_call_in_builder_ast(self):
        import ast
        tree = ast.parse(Path(b.__file__).read_text(encoding="utf-8"))
        calls = {node.func.id if isinstance(node.func, ast.Name) else node.func.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))}
        self.assertTrue(calls.isdisjoint({"compile_reference", "verify_reference", "adapt_output", "score_cell", "execute_stage1", "open_registry", "capture_selected"}))


if __name__ == "__main__":
    unittest.main()
