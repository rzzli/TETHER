"""Actual-format fictional policy/baseline tests; no project source values."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.serde import ContractError, canonical, encode, fingerprint, parse_json
from asof.study.source_fact_evaluation import score_cell
from asof.study.source_fact_sources import compile_reference, verify_reference
from asof_p05_replay import policy_v1 as policy
from asof_p05_replay.baseline_v1 import literal_report


def sha(data):
    return hashlib.sha256(data).hexdigest()


def gwas(**changes):
    row = dict(id="fictional-evidence", targetId="T", diseaseId="D", diseaseFromSourceMappedId="D",
               variantId="fictional-GWAS-variant", studyId="fictional-GWAS-study", studyLocusId="L",
               datasourceId="gwas_credible_sets", datatypeId="genetic_association", publicationDate=None,
               publicationYear=None, annotationDate=None, releaseVersion="native-version-unknown")
    row.update(changes)
    return row


def credible(**changes):
    row = dict(studyLocusId="L", studyId="fictional-credible-study", variantId="fictional-credible-variant",
               beta=0.25, standardError=None, pValueMantissa=2.5, pValueExponent=-5,
               chromosome="1", position=101, sampleSize=None, publicationDate=None,
               publicationYear=None, annotationDate=None, releaseVersion="native-version-unknown")
    row.update(changes)
    return row


def fixture(root, *, gwas_rows=None, credible_rows=None, target_rows=None, hgnc_rows=None,
            eligible_gwas=None, eligible_credible=None, windows_receipts=False, omit_credible_field=None):
    """Build all five complete fictional families and exact immutable receipts."""
    root.mkdir(parents=True)
    grows = gwas_rows if gwas_rows is not None else [gwas()]
    crows = credible_rows if credible_rows is not None else [credible()]
    if omit_credible_field:
        crows = [{key: value for key, value in row.items() if key != omit_credible_field} for row in crows]
    targets = target_rows if target_rows is not None else [dict(id="T", approvedSymbol="FAKEGENE")]
    hgnc = hgnc_rows if hgnc_rows is not None else [dict(hgnc_id="HGNC:FAKE", symbol="FAKEGENE", ensembl_gene_id="T", status="Approved", gene_group="fictional", gene_group_id="0")]
    records = {"credible_set": crows, "disease": [dict(id="D", name="Fictional disease")],
               "gwas_credible_sets": grows, "target": targets}
    inventory = []
    for family in sorted([*records, "hgnc"]):
        relative = "payload/" + family + (".tsv" if family == "hgnc" else ".parquet")
        path = root / relative
        path.parent.mkdir(exist_ok=True)
        if family == "hgnc":
            fields = list(hgnc[0])
            path.write_text("\t".join(fields) + "\n" + "".join("\t".join(row[key] for key in fields) + "\n" for row in hgnc), encoding="utf-8")
            rows = None
        else:
            table = pa.Table.from_pylist(records[family])
            # Fixed row groups and single-row scan batches exercise physical locators.
            pq.write_table(table, path, row_group_size=2)
            fields, rows = table.schema.names, table.num_rows
        source_id = f"original-{len(inventory):03d}"
        url = "https://example.invalid/fictional/" + family
        payload = path.read_bytes()
        receipt = dict(status="completed", dataset_id="fictional." + family, release_id="25.09",
                       sha256=sha(payload), bytes=len(payload), url=url,
                       relative_path=relative.replace("/", "\\") if windows_receipts else relative,
                       completed_at_utc="2026-10-10T00:00:00+00:00")
        receipt_path = "receipts/" + family + ".json"
        receipt_bytes = canonical(receipt) + b"\n"
        (root / "receipts").mkdir(exist_ok=True)
        (root / receipt_path).write_bytes(receipt_bytes)
        inventory.append(dict(source_id=source_id, family=family, dataset_id=receipt["dataset_id"], release_id="25.09",
            relative_path=relative, sha256=sha(payload), bytes=len(payload), fields=fields, rows=rows, source_url=url,
            role="reference" if family == "hgnc" else "agent_evidence",
            receipt=dict(relative_path=receipt_path, sha256=sha(receipt_bytes), bytes=len(receipt_bytes))))
    cutoff = policy.utc(policy.CUTOFF)
    observed = datetime(2026, 10, 10, tzinfo=timezone.utc)
    nodes = []
    for item in inventory:
        availability = Availability(None, None, None, None, observed.date(), "public_download_receipt",
            "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown", observed, item["receipt"]["sha256"])
        nodes.append(SourceNode(item["source_id"], item["dataset_id"], "25.09", item["relative_path"], item["sha256"], item["role"],
            availability, TemporalClass.CONTEMPORARY, item["source_url"], receipt_path=item["receipt"]["relative_path"], receipt_sha256=item["receipt"]["sha256"]))
    snapshot = Snapshot(2, "p05-stage2-originals-v1", Profile.CONTEMPORARY, cutoff.date(), False, (), tuple(nodes), None,
                        {"scope": "selected_original_frame_only", "historical_eligibility": "not_verified"}, cutoff)
    case = dict(case_id="p05-01", targetId="T", diseaseId="D", studyLocusId="L", release_id="25.09",
                unit_hash=policy.unit_hash("25.09", ("T", "D", "L")))
    groups = {"gwas_credible_sets": [], "credible_set": []}
    for family, source_rows, indices in [("gwas_credible_sets", grows, eligible_gwas), ("credible_set", crows, eligible_credible)]:
        item = next(item for item in inventory if item["family"] == family)
        for number in range(len(source_rows)) if indices is None else indices:
            groups[family].append(dict(source_id=item["source_id"], family=family,
                locator=dict(format="parquet", row_group=number // 2, row=number % 2), physical_row_0based=number,
                values=source_rows[number]))
    task = policy.build_task(case, groups)
    expected_frame = {family: dict(files=1, bytes=next(i["bytes"] for i in inventory if i["family"] == family),
                         rows=next(i["rows"] for i in inventory if i["family"] == family)) for family in [*records, "hgnc"]}
    config = dict(schema_version=1, method=policy.METHOD, cutoff=policy.CUTOFF, inventory=inventory,
        expected_frame=expected_frame, catalog=dict(schema_version=1, datasets=[dict(dataset_id=i["dataset_id"], roles=[i["role"]]) for i in inventory]),
        snapshot=encode(snapshot), cases=[case], tasks={"p05-01": task}, exposed_symbols=sorted(policy.EXPOSED), limits={**policy.LIMITS, "batch_rows": 1})
    return config, groups


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.gettempdir()) / "asof-p05-replay-policy-tests"
        self.parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-", dir=self.parent)
        self.root = Path(self.temp.name)
        self.assertTrue(self.root.resolve().is_relative_to(self.parent.resolve()))

    def tearDown(self):
        self.temp.cleanup()

    def session(self, config, root):
        return policy.policy_session(config, root, time.monotonic() + 60)

    def test_real_originals_receipts_core_replay_and_exact_literal(self):
        config, _ = fixture(self.root / "raw", windows_receipts=True)
        with self.session(config, self.root / "raw") as admitted:
            self.assertEqual(admitted["dispositions"]["p05-01"]["status"], "ready_for_base_compile")
            task = admitted["tasks"]["p05-01"]
            ref = compile_reference(task, admitted["snapshot"], self.root, admitted["catalog"],
                                    approved_raw_root=self.root / "raw", deadline=time.monotonic() + 60)
            literal = literal_report(task, admitted["snapshot"], admitted["groups"]["p05-01"])
            scored = score_cell(ref, literal, cell_id="fictional-native")
            self.assertTrue(scored["completion"])
            self.assertEqual(scored["measurement_answerable_facts"], 3)
            output = parse_json(literal)
            self.assertEqual(len(output["facts"]), 15)
            self.assertEqual([f["unknown_reason"] for f in output["facts"] if f["source"]["field"] == "standardError"], ["null_source_value"])
            self.assertEqual(admitted["coverage"]["mapping_rows"], {"target": 1, "disease": 1, "hgnc": 1})

    def test_relocation_keeps_exact_reference_fact_and_output_identity(self):
        config, _ = fixture(self.root / "first")
        with self.session(config, self.root / "first") as admitted:
            ref = compile_reference(admitted["tasks"]["p05-01"], admitted["snapshot"], self.root, admitted["catalog"], approved_raw_root=self.root / "first", deadline=time.monotonic() + 60)
            raw = literal_report(admitted["tasks"]["p05-01"], admitted["snapshot"], admitted["groups"]["p05-01"])
        shutil.copytree(self.root / "first", self.root / "second")
        with self.session(config, self.root / "second") as admitted:
            replayed = verify_reference(ref.document, ref.fingerprint, admitted["tasks"]["p05-01"], admitted["snapshot"], self.root, admitted["catalog"], approved_raw_root=self.root / "second", deadline=time.monotonic() + 60)
            self.assertEqual(replayed.fingerprint, ref.fingerprint)
            self.assertEqual(literal_report(admitted["tasks"]["p05-01"], admitted["snapshot"], admitted["groups"]["p05-01"]), raw)
            self.assertTrue(all(not proof["path"].startswith(str(self.root)) for proof in admitted["source_proofs"]))

    def test_public_catalog_delta_changes_genuine_reference_only_at_named_projection(self):
        config, _ = fixture(self.root / "raw")
        with self.session(config, self.root / "raw") as admitted:
            first = compile_reference(admitted["tasks"]["p05-01"], admitted["snapshot"], self.root, admitted["catalog"], approved_raw_root=self.root / "raw", deadline=time.monotonic() + 60)
        changed = deepcopy(config)
        changed["catalog"]["datasets"][0]["purpose"] = "new public catalog metadata"
        with self.session(changed, self.root / "raw") as admitted:
            second = compile_reference(admitted["tasks"]["p05-01"], admitted["snapshot"], self.root, admitted["catalog"], approved_raw_root=self.root / "raw", deadline=time.monotonic() + 60)
        self.assertNotEqual(first.fingerprint, second.fingerprint)
        left, right = encode(first.document), encode(second.document)
        del left["method"]["catalog_sha256"]; del right["method"]["catalog_sha256"]
        self.assertEqual(canonical(left), canonical(right))

    def test_all_hashes_and_receipts_precede_first_arrow_source_open(self):
        config, _ = fixture(self.root / "raw")
        events = []
        original = pq.ParquetFile
        def inspected(*args, **kwargs):
            self.assertEqual(events.count("original_payload_verified"), 5)
            self.assertEqual(events.count("original_receipt_verified"), 5)
            return original(*args, **kwargs)
        with patch.object(pq, "ParquetFile", side_effect=inspected):
            with policy.policy_session(config, self.root / "raw", time.monotonic() + 60, lambda event, **details: events.append(event)):
                pass

    def test_changed_last_payload_rejected_before_any_source_parse(self):
        config, _ = fixture(self.root / "raw")
        (self.root / "raw" / config["inventory"][-1]["relative_path"]).write_bytes(b"fictional mutation")
        with patch.object(pq, "ParquetFile", side_effect=AssertionError("values parsed")):
            with self.assertRaisesRegex(ContractError, "checksum/size"):
                with self.session(config, self.root / "raw"):
                    pass

    def test_changed_receipt_identity_rejected_before_any_source_parse(self):
        config, _ = fixture(self.root / "raw")
        item = config["inventory"][0]
        receipt_path = self.root / "raw" / item["receipt"]["relative_path"]
        doc = parse_json(receipt_path.read_bytes()); doc["relative_path"] = "payload/changed.parquet"
        data = canonical(doc) + b"\n"; receipt_path.write_bytes(data)
        item["receipt"].update(sha256=sha(data), bytes=len(data))
        # Bind the changed receipt digest in declared metadata, proving the
        # identity predicate itself rejects it, rather than just a stale hash.
        config["snapshot"]["sources"][0]["receipt_sha256"] = sha(data)
        config["snapshot"]["sources"][0]["availability"]["evidence_ref"] = sha(data)
        with patch.object(pq, "ParquetFile", side_effect=AssertionError("values parsed")):
            with self.assertRaisesRegex(ContractError, "relative path"):
                with self.session(config, self.root / "raw"):
                    pass

    def test_evaluator_catalog_role_rejected_before_payload_hash(self):
        config, _ = fixture(self.root / "raw")
        config["catalog"]["datasets"][0]["roles"].append("evaluation_only")
        with patch.object(policy, "hash_file", side_effect=AssertionError("payload opened")):
            with self.assertRaises(ContractError):
                with self.session(config, self.root / "raw"):
                    pass

    def test_receipt_derived_snapshot_rejects_invented_availability_before_rows(self):
        config, _ = fixture(self.root / "raw")
        config["snapshot"]["sources"][0]["availability"]["known_public_by"] = "2026-10-09T00:00:00+00:00"
        with patch.object(pq, "ParquetFile", side_effect=AssertionError("values parsed")):
            with self.assertRaisesRegex(ContractError, "Receipt-derived"):
                with self.session(config, self.root / "raw"):
                    pass

    def test_outer_session_prevents_mutation_through_caller_replay(self):
        config, _ = fixture(self.root / "raw")
        path = self.root / "raw" / config["inventory"][0]["relative_path"]
        before = path.read_bytes()
        with self.session(config, self.root / "raw"):
            with self.assertRaises(OSError):
                path.write_bytes(b"blocked while caller holds session")
        self.assertEqual(path.read_bytes(), before)

    def test_all_matches_and_future_duplicate_locators_preserved(self):
        rows = [credible(), credible(annotationDate="2027-01-01"), credible(beta=0.75)]
        config, _ = fixture(self.root / "raw", credible_rows=rows, eligible_credible=[0, 2])
        with self.session(config, self.root / "raw") as admitted:
            records = admitted["groups"]["p05-01"]["credible_set"]
            self.assertEqual([r["physical_row_0based"] for r in records], [0, 2])
            self.assertEqual([encode(r["locator"]) for r in records], [dict(format="parquet", row_group=0, row=0), dict(format="parquet", row_group=1, row=0)])
            excluded = admitted["dispositions"]["p05-01"]["excluded_inventory"]
            self.assertEqual(len(excluded), 1)
            self.assertIn("annotationDate_explicit_future", excluded[0]["exclusion_reasons"])
            self.assertNotIn("values", excluded[0])
            self.assertEqual(admitted["dispositions"]["p05-01"]["status"], "ready_for_base_compile")
            self.assertEqual(len(parse_json(literal_report(admitted["tasks"]["p05-01"], admitted["snapshot"], admitted["groups"]["p05-01"]))["facts"]), 22)

    def test_incomplete_neutral_inventory_blocks_case_without_dropping_matches(self):
        config, _ = fixture(self.root / "raw", credible_rows=[credible(), credible(beta=0.75)], eligible_credible=[0])
        with self.session(config, self.root / "raw") as admitted:
            self.assertEqual(len(admitted["groups"]["p05-01"]["credible_set"]), 2)
            self.assertEqual(admitted["dispositions"]["p05-01"]["status"], "blocked")
            self.assertIn("fixed neutral task", admitted["dispositions"]["p05-01"]["blocked_reason"])
            self.assertEqual(len(admitted["cases"]), 1)

    def test_duplicate_mapping_blocks_without_replacement(self):
        config, _ = fixture(self.root / "raw", target_rows=[dict(id="T", approvedSymbol="FAKEGENE"), dict(id="OTHER", approvedSymbol="FAKEGENE")])
        with self.session(config, self.root / "raw") as admitted:
            self.assertEqual(admitted["dispositions"]["p05-01"]["status"], "blocked")
            self.assertEqual(len(admitted["groups"]["p05-01"]["gwas_credible_sets"]), 0)
            self.assertIn("target_symbol_missing_or_nonunique", admitted["dispositions"]["p05-01"]["excluded_inventory"][0]["exclusion_reasons"])

    def test_matching_row_bound_fails_without_yield_or_truncation(self):
        config, _ = fixture(self.root / "raw", credible_rows=[credible(), credible(beta=0.75)])
        config["limits"]["matching_rows_per_case"] = 1
        yielded = False
        with self.assertRaisesRegex(ContractError, "no truncation"):
            with self.session(config, self.root / "raw"):
                yielded = True
        self.assertFalse(yielded)

    def test_core_record_bound_retains_blocked_case_and_every_matching_row(self):
        config, _ = fixture(self.root / "raw", credible_rows=[credible(beta=float(i)) for i in range(64)], eligible_credible=[0])
        with self.session(config, self.root / "raw") as admitted:
            self.assertEqual(admitted["dispositions"]["p05-01"]["status"], "blocked")
            self.assertEqual(len(admitted["groups"]["p05-01"]["credible_set"]), 64)
            self.assertIn("bounded records", admitted["dispositions"]["p05-01"]["blocked_reason"])

    def test_native_absent_measurement_column_rejected_not_c02_acceptance(self):
        config, _ = fixture(self.root / "raw", omit_credible_field="standardError")
        with self.assertRaisesRegex(ContractError, "required columns"):
            with self.session(config, self.root / "raw"):
                pass

    def test_invalid_native_numbers_are_blocked_not_coerced(self):
        for label, row in [("boolean", credible(beta=True)), ("nan", credible(beta=float("nan"))), ("float_exponent", credible(pValueExponent=-5.0))]:
            with self.subTest(label=label):
                raw_root = self.root / label
                config, _ = fixture(raw_root, credible_rows=[row])
                with self.session(config, raw_root) as admitted:
                    self.assertEqual(admitted["dispositions"]["p05-01"]["status"], "blocked")
                    self.assertEqual(len(admitted["groups"]["p05-01"]["credible_set"]), 1)

    def test_finite_negative_standard_error_is_literal_technical_data(self):
        config, _ = fixture(self.root / "raw", credible_rows=[credible(standardError=-0.25)])
        with self.session(config, self.root / "raw") as admitted:
            self.assertEqual(admitted["dispositions"]["p05-01"]["status"], "ready_for_base_compile")

    def test_schema_footer_mismatch_and_selected_row_extract_rejected(self):
        config, _ = fixture(self.root / "raw", credible_rows=[credible(), credible(beta=0.75)])
        item = next(i for i in config["inventory"] if i["family"] == "credible_set")
        wrong = deepcopy(config); target = next(i for i in wrong["inventory"] if i["family"] == "credible_set")
        target["rows"] += 1; wrong["expected_frame"]["credible_set"]["rows"] += 1
        with self.assertRaisesRegex(ContractError, "schema/footer"):
            with self.session(wrong, self.root / "raw"):
                pass
        path = self.root / "raw" / item["relative_path"]
        pq.write_table(pa.Table.from_pylist([credible()]), path)
        with self.assertRaisesRegex(ContractError, "checksum/size"):
            with self.session(config, self.root / "raw"):
                pass

    def test_explicit_date_precision_and_conflict_semantics(self):
        cutoff = policy.utc(policy.CUTOFF)
        self.assertIn("publication_date_conflict", policy.date_guard(dict(publicationDate="2026-10-01", publicationYear=2025), cutoff)["exclusion_reasons"])
        self.assertEqual(policy.date_guard(dict(publicationDate="2026-10-01", publicationYear=2026), cutoff)["exclusion_reasons"], [])
        self.assertIn("publication_date_precision_unverified", policy.date_guard(dict(publicationYear=2026), cutoff)["exclusion_reasons"])
        self.assertEqual(policy.date_guard(dict(releaseVersion="not-an-OT-release-assertion"), cutoff)["exclusion_reasons"], [])
        lower, upper, precision = policy.source_date_interval("2026-10-01", "annotationDate")
        self.assertEqual(precision, "day"); self.assertLess(lower, upper)

    def test_deadline_and_caller_exit_failure_propagate(self):
        config, _ = fixture(self.root / "raw")
        with self.assertRaises(TimeoutError):
            with policy.policy_session(config, self.root / "raw", time.monotonic() - 1):
                pass
        def failing_progress(event, **details):
            if event == "source_policy_caller_completed":
                raise OSError("fictional caller-exit failure")
        with self.assertRaisesRegex(OSError, "caller-exit"):
            with policy.policy_session(config, self.root / "raw", time.monotonic() + 60, failing_progress):
                pass

    def test_declared_session_time_cap_is_not_overridden_by_later_caller_deadline(self):
        config, _ = fixture(self.root / "raw")
        config["limits"]["seconds"] = 1
        with self.assertRaises(TimeoutError):
            with self.session(config, self.root / "raw"):
                time.sleep(1.05)

    def test_baseline_pure_no_file_or_reference_lookup_and_abstain_reason(self):
        config, _ = fixture(self.root / "raw")
        with self.session(config, self.root / "raw") as admitted:
            task, snapshot, groups = admitted["tasks"]["p05-01"], admitted["snapshot"], admitted["groups"]["p05-01"]
            with patch("builtins.open", side_effect=AssertionError("baseline file lookup")), patch("asof.study.source_fact_sources.compile_reference", side_effect=AssertionError("reference lookup")):
                raw = literal_report(task, snapshot, groups, always_abstain=True)
            output = parse_json(raw)
            self.assertEqual(output["status"], "abstained")
            self.assertEqual(output["facts"], [])
            self.assertEqual(output["reason"], "Deliberate no-assertion baseline.")
            with self.assertRaises(TypeError):
                literal_report(task, snapshot, groups, expected_reference={})

    def test_pure_json_control_absent_field_and_locator_validation(self):
        config, groups = fixture(self.root / "raw")
        task = deepcopy(config["tasks"]["p05-01"])
        for request, record in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"]):
            request["locator"] = dict(format="json", pointer="/rows/0")
            record["locator"] = dict(format="json", pointer="/rows/0")
        del groups["credible_set"][0]["values"]["standardError"]
        from asof.serde import decode
        snapshot = decode(Snapshot, config["snapshot"])
        output = parse_json(literal_report(task, snapshot, groups))
        self.assertEqual([f["unknown_reason"] for f in output["facts"] if f["source"]["field"] == "standardError"], ["field_not_in_schema"])
        groups["credible_set"][0]["locator"] = dict(format="json", pointer="/rows/1")
        with self.assertRaisesRegex(ContractError, "locator"):
            literal_report(task, snapshot, groups)


if __name__ == "__main__":
    unittest.main()
