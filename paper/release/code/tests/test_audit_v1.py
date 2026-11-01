"""Invented originals exercise the independent auditor; no actual study data."""
from __future__ import annotations

import ast
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
import asof
import asof_p05_replay

import pyarrow as pa
import pyarrow.parquet as pq

from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.serde import encode
from asof.study.source_fact_sources import compile_reference
from asof.study.source_fact_evaluation import score_cell
from asof_p05_replay import audit_v1 as audit


def task_for(case, groups):
    """Test-authored neutral query, independent of the auditor's Task builder."""
    records, fields, right = [], [], []
    for family in ("gwas_credible_sets", "credible_set"):
        for index, row in enumerate(groups[family]):
            key = ("gwas" if family == "gwas_credible_sets" else "credible") + f"-{index:04d}"
            values = row["values"]
            identity = ({"targetId": values["targetId"], "diseaseId": values["diseaseId"]}
                        if family == "gwas_credible_sets" else {})
            identity["studyLocusId"] = values["studyLocusId"]
            identity.update({k: values[k] for k in ("id", "studyId", "variantId") if values.get(k) not in (None, "")})
            records.append(dict(record_key=key, source_id=row["source_id"], locator=row["locator"], identity=identity))
            names = (("id", "targetId", "diseaseId", "studyLocusId", "studyId", "variantId", "datasourceId", "datatypeId")
                     if family == "gwas_credible_sets" else
                     ("studyLocusId", "studyId", "variantId", "beta", "standardError", "pValueMantissa", "pValueExponent"))
            if family == "credible_set":
                right.append(key)
            for name in names:
                measurement = name in ("beta", "standardError", "pValueMantissa", "pValueExponent")
                fields.append(dict(record_key=key, field=name, family="reported_measurement" if measurement else "identity_linkage",
                    group=("measurement:" if measurement else "identity:") + key, unit_field=None, empty_policy="unknown"))
    return dict(schema_version=1, task_id="p05-" + case["case_id"] + "-native-locus-v1",
        scope=dict(target_id=case["targetId"], indication_id=case["diseaseId"], target_namespace_version="unknown",
                   indication_namespace_version="unknown", action=None, modality=None, tissue=None),
        cutoff=audit.CUTOFF, profile="contemporary_assessment", primary_families=["reported_measurement"], records=records, fields=fields,
        joins=[dict(join_id="locus:" + r["record_key"], left_record=r["record_key"], left_field="studyLocusId",
                    right_records=right, right_field="studyLocusId", cardinality="one_to_many", inventory_status="complete")
               for r in records if r["record_key"].startswith("gwas")],
        collection=dict(status="selected_records", reason="All eligible selected physical rows in the pinned original frame only; source-locus reporting, no biological absence claim."))


def native_fixture(root):
    cases = [dict(case_id=f"p05-{i+1:02d}", targetId=f"T{i}", diseaseId=f"D{i}", studyLocusId=f"L{i}", release_id="25.09") for i in range(12)]
    for case in cases:
        case["unit_hash"] = hashlib.sha256(("preprint-p05-deterministic-v1|25.09|" + "|".join(case[k] for k in ("targetId", "diseaseId", "studyLocusId"))).encode()).hexdigest()
    values = {
        "gwas_credible_sets": [dict(id=f"E{i}", targetId=f"T{i}", diseaseId=f"D{i}", diseaseFromSourceMappedId=f"D{i}",
            variantId=None, studyId=None, studyLocusId=f"L{i}", datasourceId="gwas_credible_sets", datatypeId="genetic_association") for i in range(12)],
        "credible_set": [dict(studyLocusId=f"L{i}", studyId=f"S{i}", variantId=f"V{i}", beta=None if i == 0 else i + 0.125,
            standardError=None if i < 7 else 0.25, pValueMantissa=2.0, pValueExponent=-6, chromosome="1", position=i+1, sampleSize=None) for i in range(12)],
        "target": [dict(id=f"T{i}", approvedSymbol=f"GENE{i}") for i in range(12)],
        "disease": [dict(id=f"D{i}", name=f"Fictional disease {i}") for i in range(12)],
        "hgnc": [dict(hgnc_id=f"HGNC:{i}", symbol=f"GENE{i}", ensembl_gene_id=f"T{i}", status="Approved") for i in range(12)]}
    inventory, nodes = [], []
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for number, family in enumerate(sorted(values)):
        name = family + (".tsv" if family == "hgnc" else ".parquet")
        path = root / name
        if family == "hgnc":
            names = list(values[family][0])
            path.write_text("\t".join(names) + "\n" + "".join("\t".join(row[n] for n in names) + "\n" for row in values[family]), encoding="utf-8")
        else:
            table = pa.Table.from_pylist(values[family])
            names = table.schema.names
            pq.write_table(table, path, row_group_size=4)
        raw = path.read_bytes()
        descriptor = dict(source_id=f"original-{number:03d}", family=family, dataset_id=family, release_id="25.09", relative_path=name,
            sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), fields=names, rows=12,
            source_url="https://example.invalid/" + name, role="reference" if family == "hgnc" else "agent_evidence")
        receipt = dict(status="completed", dataset_id=family, release_id="25.09", relative_path=name, sha256=descriptor["sha256"],
            bytes=len(raw), url=descriptor["source_url"], completed_at_utc=observed.isoformat())
        receipt_raw = audit.wire(receipt) + b"\n"
        (root / (name + ".receipt.json")).write_bytes(receipt_raw)
        descriptor["receipt"] = dict(relative_path=name + ".receipt.json", sha256=hashlib.sha256(receipt_raw).hexdigest(), bytes=len(receipt_raw))
        inventory.append(descriptor)
        avail = Availability(None, None, None, None, observed.date(), "public_download_receipt",
            "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown", observed, descriptor["receipt"]["sha256"])
        nodes.append(SourceNode(descriptor["source_id"], family, "25.09", name, descriptor["sha256"], descriptor["role"], avail,
            TemporalClass.CONTEMPORARY, descriptor["source_url"], receipt_path=name + ".receipt.json", receipt_sha256=descriptor["receipt"]["sha256"]))
    snapshot = Snapshot(2, "p05-stage2-originals-v1", Profile.CONTEMPORARY, datetime.fromisoformat(audit.CUTOFF).date(), False, (), tuple(nodes), None,
        {"scope": "selected_original_frame_only", "historical_eligibility": "not_verified"}, datetime.fromisoformat(audit.CUTOFF))
    groups = {}
    for i, case in enumerate(cases):
        groups[case["case_id"]] = {family: [dict(source_id=next(x["source_id"] for x in inventory if x["family"] == family), family=family,
            locator=dict(format="parquet", row_group=i//4, row=i%4), physical_row_0based=i, values=values[family][i])]
            for family in ("gwas_credible_sets", "credible_set")}
    policy = dict(schema_version=1, method="p09.source_policy.v1", cutoff=audit.CUTOFF, inventory=inventory,
        expected_frame={x["family"]: dict(files=1, bytes=x["bytes"], rows=12) for x in inventory},
        catalog=dict(schema_version=1, datasets=[dict(dataset_id=x["family"], roles=[x["role"]]) for x in inventory]),
        snapshot=encode(snapshot), cases=cases, tasks={case["case_id"]: task_for(case, groups[case["case_id"]]) for case in cases},
        exposed_symbols=sorted(audit.EXPOSED), limits={})
    return policy, groups


def full_native_fixture(root):
    """137 separately anchored invented files preserve the actual family shape."""
    small, groups = native_fixture(root)
    inventory, nodes = [], []
    counts = dict(gwas_credible_sets=100, credible_set=25, target=10, disease=1, hgnc=1)
    observed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    original_by_family = {x["family"]: x for x in small["inventory"]}
    first = {}
    for family in sorted(counts):
        original = original_by_family[family]
        if family != "hgnc":
            table = pq.read_table(root / original["relative_path"])
        folder = root / family
        folder.mkdir()
        for partition in range(counts[family]):
            relative = family + f"/part-{partition:03d}" + (".tsv" if family == "hgnc" else ".parquet")
            path = root / relative
            if family == "hgnc":
                path.write_bytes((root / original["relative_path"]).read_bytes())
            else:
                pq.write_table(table if partition == 0 else table.slice(0, 0), path, row_group_size=4)
            payload = path.read_bytes()
            sid = f"original-{len(inventory):03d}"
            item = dict(original, source_id=sid, relative_path=relative, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                        rows=12 if partition == 0 else 0, source_url="https://example.invalid/" + relative)
            receipt = dict(status="completed", dataset_id=family, release_id="25.09", relative_path=relative,
                sha256=item["sha256"], bytes=len(payload), url=item["source_url"], completed_at_utc=observed.isoformat())
            receipt_raw = audit.wire(receipt) + b"\n"
            (root / (relative + ".receipt.json")).write_bytes(receipt_raw)
            item["receipt"] = dict(relative_path=relative + ".receipt.json", sha256=hashlib.sha256(receipt_raw).hexdigest(), bytes=len(receipt_raw))
            inventory.append(item)
            if partition == 0:
                first[family] = item
            availability = Availability(None, None, None, None, observed.date(), "public_download_receipt",
                "contemporary receipt-bound original; publication/availableAt and historical eligibility unknown", observed, item["receipt"]["sha256"])
            nodes.append(SourceNode(sid, family, "25.09", relative, item["sha256"], item["role"], availability, TemporalClass.CONTEMPORARY,
                item["source_url"], receipt_path=item["receipt"]["relative_path"], receipt_sha256=item["receipt"]["sha256"]))
    for case_groups in groups.values():
        for family, rows in case_groups.items():
            rows[0]["source_id"] = first[family]["source_id"]
    snapshot = decode_snapshot(small["snapshot"])
    small.update(inventory=inventory, snapshot=encode(replace(snapshot, sources=tuple(nodes))),
        expected_frame={family: dict(files=counts[family], bytes=sum(x["bytes"] for x in inventory if x["family"] == family), rows=12) for family in counts},
        tasks={case["case_id"]: task_for(case, groups[case["case_id"]]) for case in small["cases"]})
    return small, groups, first


class NativeAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy, self.groups = native_fixture(self.root)

    def context(self):
        return audit.Audit(time.monotonic() + 30)

    def test_direct_projection_matches_genuine_core_and_native_unknowns(self):
        context = self.context()
        with audit.native_projection(self.policy, self.root, context, full_frame=False) as projected:
            self.assertEqual(projected["coverage"]["mapping_rows"], {"hgnc": 12, "target": 12, "disease": 12})
            self.assertEqual(context.report["native_physical_row_counts"], {"credible_set": 12, "gwas_credible_sets": 12})
            for cid, expected in projected["references"].items():
                genuine = compile_reference(self.policy["tasks"][cid], projected["snapshot"], self.root, self.policy["catalog"], deadline=context.deadline)
                self.assertEqual(audit.wire(expected), audit.wire(genuine.document))
            facts = projected["references"]["p05-01"]["facts"]
            beta = next(f for f in facts if f["field"] == "beta")
            self.assertIsNone(beta["value"])
            self.assertEqual(beta["unknown_reason"], "null_source_value")
            self.assertTrue(all(f["unit"] is None for f in facts))
            self.assertEqual(sum(f["value"] is not None and f["family"] == "reported_measurement" for ref in projected["references"].values() for f in ref["facts"]), 40)

    def test_public_entry_frame_cannot_be_downgraded_to_five_files(self):
        with self.assertRaises(audit.AuditFailure):
            with audit.native_projection(self.policy, self.root, self.context()):
                self.fail("Actual audit must require all 137 originals")

    def test_payload_tamper_fails_before_source_row_scan(self):
        item = self.policy["inventory"][0]
        with (self.root / item["relative_path"]).open("ab") as stream:
            stream.write(b"changed")
        context = self.context()
        with self.assertRaises(audit.AuditFailure):
            with audit.native_projection(self.policy, self.root, context, full_frame=False):
                pass
        self.assertEqual(context.report["resources"]["original_row_passes"], 0)

    def test_evaluator_role_cannot_be_laundered_by_catalog(self):
        self.policy["inventory"][0]["role"] = "evaluation_only"
        with self.assertRaises(audit.AuditFailure):
            with audit.native_projection(self.policy, self.root, self.context(), full_frame=False):
                pass

    def test_future_receipt_cannot_be_newly_pinned_as_eligible(self):
        item = self.policy["inventory"][0]
        path = self.root / item["receipt"]["relative_path"]
        receipt = json.loads(path.read_bytes())
        receipt["completed_at_utc"] = "2026-11-02T00:00:00+00:00"
        payload = audit.wire(receipt)
        path.write_bytes(payload)
        item["receipt"].update(sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
        with self.assertRaises(audit.AuditFailure):
            with audit.native_projection(self.policy, self.root, self.context(), full_frame=False):
                pass

    def test_catalog_only_projection_is_narrow(self):
        with audit.native_projection(self.policy, self.root, self.context(), full_frame=False) as p:
            ref = p["references"]["p05-01"]
            changed = json.loads(audit.wire(ref))
            changed["method"]["catalog_sha256"] = "f" * 64
            self.assertEqual(audit.projection_digest(ref), audit.projection_digest(changed))
            changed["method"]["source_snapshot_sha256"] = "e" * 64
            self.assertNotEqual(audit.projection_digest(ref), audit.projection_digest(changed))


class ControlAuditTests(unittest.TestCase):
    def one(self, key):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        case, documents, sources, receipts, generation, evaluation, anchors, catalog = audit._control_source_documents(key)
        for name in documents:
            (root / (name + ".json")).write_bytes(sources[name])
            (root / (name + ".receipt.json")).write_bytes(receipts[name])
        groups = audit.json_groups(case, documents, declared_subset=key == "F04")
        task = task_for(case, groups)
        nodes = {n.source_id: n for n in evaluation.sources}
        rows = {record["record_key"]: row["values"] for record, row in zip(task["records"], groups["gwas_credible_sets"] + groups["credible_set"])}
        facts, _ = audit.projected_facts(task, rows, nodes, permit_boolean_measurement=True)
        raw = audit.candidate_bytes(task, facts, key)
        spec = dict(scenario_id=key, case=case, task=task, generation_snapshot=encode(generation), evaluation_snapshot=encode(evaluation), catalog=catalog, original_source_anchors=anchors)
        return spec, root, raw

    def test_all_fourteen_source_derived_guard_contrasts(self):
        admissions = {p: 0 for p in audit.POLICIES}
        rejected_valid = {p: 0 for p in audit.POLICIES}
        for key in audit.SCENARIOS:
            with self.subTest(key=key):
                spec, root, raw = self.one(key)
                result = audit.audit_control(spec, root, raw, audit.Audit(time.monotonic() + 30))
                for policy, decision in result["decisions"].items():
                    admissions[policy] += key.startswith("F") and decision["verdict"] == "admitted"
                    rejected_valid[policy] += key.startswith("C") and decision["verdict"] == "rejected"
                if result["reference"] is not None:
                    snapshot = replace(decode_snapshot(spec["evaluation_snapshot"]), raw_root=str(root))
                    genuine = compile_reference(spec["task"], snapshot, root, spec["catalog"], deadline=time.monotonic() + 30)
                    self.assertEqual(audit.wire(genuine.document), audit.wire(result["reference"]))
                    self.assertEqual(audit.wire(score_cell(genuine, raw, cell_id="S-" + key)), audit.wire(result["core_score"]))
        self.assertEqual(admissions, {"FULL": 0, "WITHOUT_WRAPPER": 2, "WIRE_ONLY": 7})
        self.assertEqual(rejected_valid, dict.fromkeys(audit.POLICIES, 0))

    def test_unknown_output_reason_and_duplicate_key_are_not_repaired(self):
        for key in ("F07", "F08", "F10"):
            spec, root, raw = self.one(key)
            result = audit.audit_control(spec, root, raw, audit.Audit(time.monotonic() + 30))
            self.assertEqual(result["states"]["G4"], "rejected")

    def test_control_source_mutation_is_independent_of_declared_guard(self):
        spec, root, raw = self.one("C01")
        with (root / "credible.json").open("ab") as stream:
            stream.write(b" ")
        with self.assertRaises(audit.AuditFailure):
            audit.audit_control(spec, root, raw, audit.Audit(time.monotonic() + 30))

    def test_zero_answerable_group_and_negative_standard_error_keep_limits(self):
        for key in ("C03", "C04"):
            spec, root, raw = self.one(key)
            result = audit.audit_control(spec, root, raw, audit.Audit(time.monotonic() + 30))
            self.assertTrue(result["strict_exact_report"])
            if key == "C04":
                self.assertIsNone(result["core_score"]["primary"]["coverage"])
                self.assertFalse(result["core_score"]["completion"])

    def test_auditor_has_no_producer_or_dynamic_old_tool_import(self):
        source = Path(audit.__file__).read_text()
        tree = ast.parse(source)
        names = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        names |= {x.name for n in ast.walk(tree) if isinstance(n, ast.Import) for x in n.names}
        self.assertFalse(any("policy_v1" in n or "baseline_v1" in n or "controls_v1" in n or n.startswith("tools") or n.startswith("importlib") for n in names))
        called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertNotIn("compile_reference", called)
        self.assertNotIn("score_cell", called)


def decode_snapshot(value):
    from asof.serde import decode
    return decode(Snapshot, value)


class TransactionAuditTests(unittest.TestCase):
    def transaction(self, *, comparison_before_seal=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "raw").mkdir()
        (root / "raw/example.json").write_bytes(b"invented output\n")
        events = []
        def event(name, **details):
            value = dict(sequence=len(events), previous_sha256=events[-1]["sha256"] if events else None,
                         event=name, details=details)
            value["sha256"] = hashlib.sha256(audit.wire(value)).hexdigest()
            events.append(value)
        def anchors(paths):
            return {p: dict(sha256=hashlib.sha256((root / p).read_bytes()).hexdigest(), bytes=(root / p).stat().st_size) for p in paths}
        event("preseal")
        if comparison_before_seal:
            event("comparison_started", comparison_sha256="c" * 64)
        seal = dict(schema_version=1, method="p09.reconstructed_output_seal.v1", protocol_sha256="a" * 64,
                    journal_prefix_sha256=events[-1]["sha256"], files=anchors(["raw/example.json"]),
                    comparison_inputs_parsed=False, model_calls=0, scientific_validation="not_established")
        seal_raw = audit.wire(seal) + b"\n"
        (root / "output-seal.json").write_bytes(seal_raw)
        seal_hash = hashlib.sha256(seal_raw).hexdigest()
        event("outputs_sealed", output_seal_sha256=seal_hash)
        if not comparison_before_seal:
            event("comparison_started", comparison_sha256="c" * 64)
        report = dict(schema_version=1, method="p09.source_inclusive_reconstruction.v1", status="COMPLETED_PENDING_AUDIT",
                      protocol_sha256="a" * 64, output_seal_sha256=seal_hash, source_coverage_path="source-coverage.json",
                      historical_output_comparison="all_38_exact_byte_hashes_and_all_90_decisions",
                      historical_archive_integrity="not_provided_by_public_reconstruction", scientific_validation="not_established",
                      model_calls=0, network_calls=0, new_downloads=0, provider_spending_usd=0)
        (root / "reconstruction.json").write_bytes(audit.wire(report) + b"\n")
        event("reconstruction_completed", report_sha256=hashlib.sha256((root / "reconstruction.json").read_bytes()).hexdigest())
        (root / "journal.jsonl").write_bytes(b"".join(audit.wire(x) + b"\n" for x in events))
        receipt = dict(schema_version=1, method="p09.reconstruction_receipt.v1", operation="reconstruct", status="SEALED_SUCCESS", protocol_sha256="a" * 64, output_seal_sha256=seal_hash,
                       reconstruction_sha256=hashlib.sha256((root / "reconstruction.json").read_bytes()).hexdigest(),
                       files=anchors(["raw/example.json", "output-seal.json", "journal.jsonl", "reconstruction.json"]))
        (root / "receipt.json").write_bytes(audit.wire(receipt) + b"\n")
        return root

    def reseal_receipt(self, root):
        receipt = json.loads((root / "receipt.json").read_bytes())
        receipt["reconstruction_sha256"] = hashlib.sha256((root / "reconstruction.json").read_bytes()).hexdigest()
        receipt["output_seal_sha256"] = hashlib.sha256((root / "output-seal.json").read_bytes()).hexdigest()
        receipt["files"] = {p.relative_to(root).as_posix(): dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)
                            for p in root.rglob("*") if p.is_file() and p.name != "receipt.json"}
        (root / "receipt.json").write_bytes(audit.wire(receipt) + b"\n")

    def rechain(self, root, events):
        previous = None
        for number, event in enumerate(events):
            event.update(sequence=number, previous_sha256=previous)
            event["sha256"] = hashlib.sha256(audit.wire({k: v for k, v in event.items() if k != "sha256"})).hexdigest()
            previous = event["sha256"]
        (root / "journal.jsonl").write_bytes(b"".join(audit.wire(x) + b"\n" for x in events))

    def synchronize_byte_bindings(self, root):
        seal_hash = hashlib.sha256((root / "output-seal.json").read_bytes()).hexdigest()
        report = json.loads((root / "reconstruction.json").read_bytes())
        report["output_seal_sha256"] = seal_hash
        (root / "reconstruction.json").write_bytes(audit.wire(report) + b"\n")
        events = [json.loads(line) for line in (root / "journal.jsonl").read_bytes().splitlines()]
        next(x for x in events if x["event"] == "outputs_sealed")["details"]["output_seal_sha256"] = seal_hash
        events[-1]["details"]["report_sha256"] = hashlib.sha256((root / "reconstruction.json").read_bytes()).hexdigest()
        self.rechain(root, events)
        self.reseal_receipt(root)

    def test_receipt_uses_exact_bytes_and_journal_orders_bridge_after_seal(self):
        root = self.transaction()
        context = audit.Audit(time.monotonic() + 30)
        audit._journal_and_receipt(root, "a" * 64, context, comparison_sha256="c" * 64)
        self.assertEqual(context.report["subject"]["receipt_sha256"], hashlib.sha256((root / "receipt.json").read_bytes()).hexdigest())

    def test_rechained_comparison_before_output_seal_is_rejected(self):
        root = self.transaction(comparison_before_seal=True)
        with self.assertRaises(audit.AuditFailure):
            audit._journal_and_receipt(root, "a" * 64, audit.Audit(time.monotonic() + 30), comparison_sha256="c" * 64)

    def test_extra_file_and_output_mutation_cannot_hide_behind_receipt(self):
        for mutation in ("extra", "changed"):
            root = self.transaction()
            if mutation == "extra":
                (root / "unlisted.json").write_bytes(b"{}")
            else:
                (root / "raw/example.json").write_bytes(b"changed")
            with self.assertRaises(audit.AuditFailure):
                audit._journal_and_receipt(root, "a" * 64, audit.Audit(time.monotonic() + 30), comparison_sha256="c" * 64)

    def test_rechained_resealed_journal_must_bind_exact_report_and_comparator(self):
        for event_name, field in (("reconstruction_completed", "report_sha256"), ("comparison_started", "comparison_sha256")):
            for mutation in ("changed", "missing"):
                with self.subTest(event=event_name, mutation=mutation):
                    root = self.transaction()
                    events = [json.loads(line) for line in (root / "journal.jsonl").read_bytes().splitlines()]
                    details = next(x for x in events if x["event"] == event_name)["details"]
                    if mutation == "changed": details[field] = "f" * 64
                    else: del details[field]
                    self.rechain(root, events)
                    self.reseal_receipt(root)
                    with self.assertRaises(audit.AuditFailure):
                        audit._journal_and_receipt(root, "a" * 64, audit.Audit(time.monotonic() + 30), comparison_sha256="c" * 64)

    def test_resealed_scope_claims_and_schema_types_are_mandatory(self):
        mutations = [(name, "schema_version", True) for name in ("receipt.json", "output-seal.json", "reconstruction.json")]
        mutations += [("output-seal.json", key, value) for key, value in (("comparison_inputs_parsed", True), ("model_calls", False), ("scientific_validation", "established"))]
        mutations += [("reconstruction.json", key, value) for key, value in (("historical_output_comparison", "partial"),
            ("historical_archive_integrity", "verified"), ("scientific_validation", "established"), ("source_coverage_path", "other.json"),
            ("model_calls", False), ("network_calls", 1), ("new_downloads", 1), ("provider_spending_usd", 0.0))]
        for name, key, value in mutations:
            with self.subTest(file=name, key=key, value=value):
                root = self.transaction()
                document = json.loads((root / name).read_bytes()); document[key] = value
                (root / name).write_bytes(audit.wire(document) + b"\n")
                self.synchronize_byte_bindings(root)
                with self.assertRaises(audit.AuditFailure):
                    audit._journal_and_receipt(root, "a" * 64, audit.Audit(time.monotonic() + 30), comparison_sha256="c" * 64)

    def test_external_protocol_pin_is_exact_bytes_not_json_fingerprint(self):
        raw = b'{"status":"READY"}\n'
        wrong = dict(document=json.loads(raw), raw_bytes=raw, byte_sha256=hashlib.sha256(raw.rstrip()).hexdigest())
        report = audit.audit_reconstruction(wrong, ".", ".", ".", time.monotonic() + 30)
        self.assertEqual(report["status"], "FAIL_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT")
        self.assertIn("external_protocol_exact_byte_hash", report["unresolved_findings"])
        self.assertFalse(report["source_inclusive"])

    def test_draft_wrong_version_and_nonboolean_authorization_fail_before_sources(self):
        allowed = dict(schema_version=1, method="p09.public_reconstruction_protocol.v1", status="READY", actual_reconstruction_authorized=True)
        denied = [("schema_version", True), ("schema_version", 2), ("method", "unapproved.protocol"),
                  ("status", "DRAFT"), ("actual_reconstruction_authorized", False), ("actual_reconstruction_authorized", 1)]
        for key, value in denied:
            with self.subTest(key=key, value=value):
                document = dict(allowed, **{key: value})
                raw = audit.wire(document) + b"\n"
                authority = dict(document=document, raw_bytes=raw, byte_sha256=hashlib.sha256(raw).hexdigest())
                report = audit.audit_reconstruction(authority, ".", ".", ".", time.monotonic() + 30)
                self.assertEqual(report["status"], "FAIL_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT")
                self.assertIn("root_authorized_public_protocol", report["unresolved_findings"])
                self.assertFalse(report["source_inclusive"])
                self.assertEqual(report["resources"]["logical_original_compressed_bytes_scanned"], 0)
        raw = audit.wire(allowed) + b"\n"
        report = audit.audit_reconstruction(dict(document=allowed, raw_bytes=raw, byte_sha256=hashlib.sha256(raw).hexdigest()),
                                            ".", ".", ".", time.monotonic() + 30)
        self.assertIn(dict(check="root_authorized_public_protocol", **{"pass": True}), report["checks"])
        self.assertFalse(report["source_inclusive"])  # Other mandatory inputs were deliberately not supplied.

    def test_summary_uses_all_scheduled_cells_and_preserves_unknown_slots(self):
        literal = dict(cell_id="N-L-p05-01", case_id="p05-01", arm="L", stratum="native", terminal="returned",
            full_verified_exact=True, core_score=dict(critical_errors=[], primary=dict(passes={"60": True, "80": True, "100": True})),
            fact_accounting=dict(families={"identity_linkage": dict(requested=11, answerable=9, expected_unknown_by_reason={"null_source_value": 2}),
                "reported_measurement": dict(requested=4, answerable=3, expected_unknown_by_reason={"null_source_value": 1})}))
        abstain = dict(cell_id="N-A-p05-01", case_id="p05-01", arm="A", stratum="native", terminal="returned",
            core_score=dict(completion=False, emitted_facts=0, critical_errors=[]))
        counts = audit.analysis_counts([literal, abstain], [])
        self.assertEqual(counts["planned_output_cells"], 2)
        self.assertEqual(counts["native_availability"], dict(identity_requested=11, identity_answerable=9, measurement_requested=4,
            measurement_answerable=3, native_nulls=3, absent=0, empty=0))
        self.assertEqual(counts["native_abstain"]["cases"], 1)


class BridgeAuditTests(unittest.TestCase):
    """Value-free metadata contract checks need no original-source reads."""
    def fixture(self):
        outputs, planned = audit.fixed_schedule()
        outputs = [dict(row, core_score=None) for row in outputs]
        statuses = dict.fromkeys(audit.STAGES, "pass")
        guards = {row["cell_id"]: {s: dict(status="pass", **({"schema_status": "pass"} if s == "G4" else {})) for s in audit.STAGES} for row in outputs}
        decisions = [dict(row, **audit.policy_decision(statuses, "pass", row["policy"])) for row in planned]
        native = {"references": {cid: dict(task_sha256="t" * 64, method=dict(catalog_sha256="c" * 64),
            facts=[dict(family="reported_measurement", value=1.0, record_key="invented", group="measurement:invented")]) for cid in audit.CASES}}
        bridge = dict(method="p09.p05_comparison_bridge.v1", role="evaluation_only", agent_visible=False,
            source_policy_sha256="s" * 64, scientific_validation="not_established", outputs=json.loads(audit.wire(outputs)),
            guards=json.loads(audit.wire(guards)), decisions=[{k: v for k, v in row.items() if k != "output_cell_id"} for row in decisions],
            native={cid: dict(projection_method="remove_only_method_catalog_sha256.v1", task_sha256=ref["task_sha256"],
                reference_projection_sha256=audit.projection_digest(ref), historical_reference_sha256="h" * 64,
                counts=dict(requested_facts=1, measurement_answerable_facts=1, measurement_answerable_groups=1,
                    case_id=cid, disposition="compiled", task_sha256=ref["task_sha256"], reference_sha256="h" * 64)) for cid, ref in native["references"].items()})
        return bridge, dict(guards=guards), native, outputs, decisions

    def compare(self, bridge, reconstruction, native, outputs, decisions):
        audit._bridge_comparison(bridge, "s" * 64, reconstruction, native, outputs, decisions, audit.Audit(time.monotonic() + 30))

    def test_complete_typed_bridge_contract_passes(self):
        self.compare(*self.fixture())

    def test_missing_extra_or_empty_historical_decision_is_rejected(self):
        for mutation in ("empty", "missing", "extra", "optional_binding_extra"):
            with self.subTest(mutation=mutation):
                args = self.fixture(); row = args[0]["decisions"][0]
                if mutation == "empty": row.clear()
                elif mutation == "missing": del row["verdict"]
                elif mutation == "extra": row["invented"] = True
                else: row["output_cell_id"] = args[-1][0]["output_cell_id"]
                with self.assertRaises(audit.AuditFailure): self.compare(*args)

    def test_guard_inventory_cannot_silently_include_extra_output(self):
        args = self.fixture(); args[0]["guards"]["invented-extra"] = args[0]["guards"][args[3][0]["cell_id"]]
        with self.assertRaises(audit.AuditFailure): self.compare(*args)

    def test_native_group_and_fact_counts_cannot_substitute_boolean_or_float(self):
        for field in ("requested_facts", "measurement_answerable_facts", "measurement_answerable_groups"):
            for value in (True, 1.0):
                with self.subTest(field=field, value=value):
                    args = self.fixture(); args[0]["native"]["p05-01"]["counts"][field] = value
                    with self.assertRaises(audit.AuditFailure): self.compare(*args)


class FullSyntheticAuditTests(unittest.TestCase):
    """A complete invented subject reaches the public audit entry point."""
    def test_complete137_originals38_outputs90_decisions_and_resealed_score_tamper(self):
        from asof.study.source_fact_adapters import adapt_output
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        originals, bundle, run = [base / n for n in ("originals", "bundle", "run")]
        for p in (originals, bundle, run):
            p.mkdir()
        policy, groups, first = full_native_fixture(originals)
        deadline = time.monotonic() + 180
        snapshot = replace(decode_snapshot(policy["snapshot"]), raw_root=str(originals))
        refs, old_refs, outputs, decisions, guards, native_descriptors, native_bridge = {}, {}, [], [], {}, {}, {}
        old_catalog = json.loads(audit.wire(policy["catalog"]))
        old_catalog["datasets"].append(dict(dataset_id="historical_unused_fixture", roles=["reference"]))
        (run / "raw").mkdir()
        (run / "references").mkdir()

        def raw_report(task, facts, abstain=False):
            return audit.wire(dict(schema_version=1, task_id=task["task_id"], task_sha256=hashlib.sha256(audit.wire(task)).hexdigest(),
                status="abstained" if abstain else "answered", facts=[] if abstain else [{k: f[k] for k in ("fact_id", "value", "unit", "source", "unknown_reason")} for f in facts],
                collection_status="selected_records", reason="Deliberate no-assertion baseline." if abstain else None))

        def add_output(cell, case, arm, stratum, raw, reference, statuses):
            score = encode(score_cell(reference, raw, cell_id=cell)) if reference is not None else None
            schema = adapt_output(raw, wire_format="typed_facts_v1", task_id=(reference.document["task_id"] if reference else control_specs[case]["task"]["task_id"]),
                task_sha256=(reference.document["task_sha256"] if reference else hashlib.sha256(audit.wire(control_specs[case]["task"])).hexdigest()))["status"]
            exact = bool(score and score["terminal"] == "returned" and score["adapter_status"] == "scorable" and not score["critical_errors"] and score["answer_status"] == "answered" and score["emitted_facts"] == len(reference.document["facts"]))
            statuses["G4"] = "pass" if exact else "rejected" if reference else "unexecuted"
            guard = {k: dict(status=v) for k, v in statuses.items()}
            guard["G4"]["schema_status"] = "pass" if schema == "scorable" else "rejected"
            guards[cell] = guard
            accounting = audit.independent_score(encode(reference.document), raw, cell)[2] if reference else None
            path = "raw/" + cell + ".json"
            (run / path).write_bytes(raw)
            outputs.append(dict(cell_id=cell, case_id=case, arm=arm, stratum=stratum, raw_path=path,
                raw_sha256=hashlib.sha256(raw).hexdigest(), raw_bytes=len(raw), terminal="returned" if schema == "scorable" else "malformed",
                received_terminal="returned", core_score=score, fact_accounting=accounting, strict_exact_report=exact if reference else None,
                full_source_admitted=all(statuses[k] == "pass" for k in ("G0", "G1", "G2", "G3")), full_verified_exact=all(v == "pass" for v in statuses.values())))
            for name in (audit.POLICIES if arm != "A" else ("FULL",)):
                required = ["G0", "G4_schema_only"] if name == "WIRE_ONLY" else ["G0", "G1", "G3", "G4"] if name == "WITHOUT_WRAPPER" else list(audit.STAGES)
                observed = [(s, guard["G4"]["schema_status"] if s == "G4_schema_only" else statuses[s]) for s in required]
                failure = next(("G4" if s == "G4_schema_only" else s for s, value in observed if value == "rejected"), None)
                decisions.append(dict(decision_id="D-" + cell + "-" + name, output_cell_id=cell, policy=name, verdict="rejected" if failure else "admitted",
                    first_failure_stage=failure, terminal="returned", required_stages=required))

        for case in policy["cases"]:
            cid = case["case_id"]
            reference = compile_reference(policy["tasks"][cid], snapshot, originals, policy["catalog"], deadline=deadline)
            old = compile_reference(policy["tasks"][cid], snapshot, originals, old_catalog, deadline=deadline)
            refs[cid], old_refs[cid] = reference, old
            fields = reference.document["facts"]
            measurement = [x for x in fields if x["family"] == "reported_measurement" and x["value"] is not None]
            counts = dict(requested_facts=len(fields), measurement_answerable_facts=len(measurement), measurement_answerable_groups=len({(x["record_key"], x["group"]) for x in measurement}))
            ref_path = "references/" + cid + ".json"
            (run / ref_path).write_bytes(audit.wire(reference.document) + b"\n")
            projection = json.loads(audit.wire(old.document))
            del projection["method"]["catalog_sha256"]
            projected_hash = hashlib.sha256(audit.wire(projection)).hexdigest()
            native_descriptors[cid] = dict(path=ref_path, fingerprint=reference.fingerprint, projection_sha256=projected_hash, task_sha256=reference.document["task_sha256"], counts=counts)
            native_bridge[cid] = dict(task_sha256=old.document["task_sha256"], historical_reference_sha256=old.fingerprint,
                reference_projection_sha256=projected_hash, projection_method="remove_only_method_catalog_sha256.v1",
                counts=dict(counts, case_id=cid, disposition="compiled", reference_sha256=old.fingerprint, task_sha256=old.document["task_sha256"]))
            for arm in ("L", "A"):
                raw = raw_report(policy["tasks"][cid], fields, abstain=arm == "A")
                add_output("N-" + arm + "-" + cid, cid, arm, "native", raw, reference, dict.fromkeys(audit.STAGES, "pass"))

        control_specs = {}
        for key in audit.SCENARIOS:
            path = run / "fictional" / key / "originals"
            path.mkdir(parents=True)
            case, documents, sources, receipts, generation, evaluation, anchors, catalog = audit._control_source_documents(key)
            for name in documents:
                (path / (name + ".json")).write_bytes(sources[name])
                (path / (name + ".receipt.json")).write_bytes(receipts[name])
            declared = audit.json_groups(case, documents, declared_subset=key == "F04")
            task = task_for(case, declared)
            control_specs[key] = dict(scenario_id=key, case=case, task=task, snapshot=encode(evaluation), catalog=catalog,
                originals_root="fictional/" + key + "/originals", original_source_anchors=anchors)
            rows = {r["record_key"]: x["values"] for r, x in zip(task["records"], declared["gwas_credible_sets"] + declared["credible_set"])}
            facts, _ = audit.projected_facts(task, rows, {n.source_id: n for n in evaluation.sources}, permit_boolean_measurement=True)
            raw = raw_report(task, facts)
            if key in ("F05", "F06", "F07"):
                document = json.loads(raw)
                fact = next(x for x in document["facts"] if x["source"]["field"] == "beta")
                if key == "F05": fact["value"] = 2.25
                elif key == "F06": fact["source"]["locator"] = dict(format="json", pointer="/rows/999")
                else: fact["unknown_reason"] = "field_not_in_schema"
                raw = audit.wire(document)
            if key == "F08": raw = raw[:-1] + b',"status":"answered"}'
            if key == "F10": raw += b" " * (262145-len(raw))
            states = dict.fromkeys(audit.STAGES, "unexecuted")
            states["G0"] = "rejected" if any(hashlib.sha256(sources[n]).hexdigest() != next(a["sha256"] for a in anchors if a["path"] == n + ".json") for n in documents) else "pass"
            reference = None
            if states["G0"] == "pass":
                states["G1"] = "pass" if all(n.role != "evaluation_only" and not n.parents for n in evaluation.sources) else "rejected"
            if states["G1"] == "pass":
                states["G2"] = "rejected" if documents["gwas"]["rows"][0].get("releaseDate", "") > "2026-11-01" or len(declared["credible_set"]) != len(documents["credible"]["rows"]) else "pass"
                try:
                    reference = compile_reference(task, replace(evaluation, raw_root=str(path)), path, catalog, deadline=deadline)
                    states["G3"] = "pass"
                except Exception:
                    states["G3"] = "rejected"
            add_output("S-" + key, key, "fixture", "fictional_json_core", raw, reference, states)

        # Subject coverage is independently assembled from invented fixture rows.
        dispositions = {}
        for i, case in enumerate(policy["cases"]):
            cid = case["case_id"]
            def mapping_record(family, values):
                item = first[family]
                locator = dict(source_relative_path=item["relative_path"], source_sha256=item["sha256"])
                locator.update(dict(data_record_0based=i, locator_basis="TSV parsed data record, header excluded; not a text line number") if family == "hgnc" else
                    dict(row_group_0based=i//4, row_in_group_0based=i%4, physical_row_0based=i))
                return dict(values=values, locator=locator)
            mapping = dict(method="fresh exact original canonical target/HGNC/disease replay", target_id_from_raw_GWAS=case["targetId"], indication_id_from_raw_GWAS=case["diseaseId"], no_alias_or_variant_inference=True,
                target_original=mapping_record("target", dict(id=f"T{i}", approvedSymbol=f"GENE{i}")),
                disease_original=mapping_record("disease", dict(id=f"D{i}", name=f"Fictional disease {i}")),
                hgnc_original=mapping_record("hgnc", dict(hgnc_id=f"HGNC:{i}", symbol=f"GENE{i}", ensembl_gene_id=f"T{i}", status="Approved")),
                upstream_namespace_versions=dict(target="unknown", indication="unknown"), other_exposure="UNKNOWN")
            dispositions[cid] = dict(status="ready_for_base_compile", blocked_reason=None,
                eligible_inventory={f: [dict(source_id=x["source_id"], locator=x["locator"]) for x in v] for f, v in groups[cid].items()}, excluded_inventory=[],
                neutral_task_sha256=hashlib.sha256(audit.wire(policy["tasks"][cid])).hexdigest(), normalization_sha256=hashlib.sha256(audit.wire(mapping)).hexdigest())
        coverage = dict(source_proofs=encode(refs["p05-01"].document["source_proofs"]),
            coverage=dict(original_files=137, selected_cases=12, mapping_rows=dict(target=12, disease=12, hgnc=12),
                cases={c: dict(eligible=dict(gwas_credible_sets=1, credible_set=1), excluded=0) for c in audit.CASES}),
            dispositions=dispositions, resources=dict(logical_original_compressed_bytes_scanned=sum(x["bytes"] for x in policy["inventory"]),
                logical_bytes_hashed=sum(x["bytes"]+x["receipt"]["bytes"] for x in policy["inventory"])))
        controls = control_specs
        (run / "control-descriptors.json").write_bytes(audit.wire(controls)+b"\n")
        (run / "source-coverage.json").write_bytes(audit.wire(coverage)+b"\n")
        source_raw = audit.wire(policy)+b"\n"
        bridge_outputs = []
        for row in outputs:
            item = json.loads(audit.wire(row)); del item["raw_path"]
            if item["core_score"] is not None: del item["core_score"]["reference_sha256"]
            bridge_outputs.append(item)
        bridge = dict(method="p09.p05_comparison_bridge.v1", role="evaluation_only", agent_visible=False,
            source_policy_sha256=hashlib.sha256(source_raw).hexdigest(), scientific_validation="not_established", native=native_bridge,
            outputs=bridge_outputs, guards=guards, decisions=[{k: v for k, v in x.items() if k != "output_cell_id"} for x in decisions])
        for relative, payload in (("config/source-policy.json", source_raw), ("config/controls.json", audit.wire(controls)+b"\n"), ("evaluation/comparison.json", audit.wire(bridge)+b"\n")):
            p=bundle/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(payload)
        def file_map(folder):
            return {p.relative_to(folder).as_posix(): dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size) for p in folder.rglob("*") if p.is_file()}
        files = file_map(bundle)
        def package_map(folder):
            return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob("*") if p.is_file() and p.suffix in (".py", ".json")}
        protocol = dict(schema_version=1, method="p09.public_reconstruction_protocol.v1", status="READY", actual_reconstruction_authorized=True, files=files,
            source_policy=dict(path="config/source-policy.json", **files["config/source-policy.json"]), controls=dict(path="config/controls.json", **files["config/controls.json"]),
            comparison=dict(path="evaluation/comparison.json", **files["evaluation/comparison.json"]),
            core_files=package_map(Path(asof.__file__).parent), replay_files=package_map(Path(asof_p05_replay.__file__).parent),
            environment=dict(python=__import__("platform").python_version(), pyarrow=pa.__version__, platform=__import__("sys").platform))
        protocol_raw=audit.wire(protocol)+b"\n";protocol_hash=hashlib.sha256(protocol_raw).hexdigest()
        authority=dict(document=protocol,raw_bytes=protocol_raw,byte_sha256=protocol_hash)
        (bundle/"protocol.json").write_bytes(protocol_raw)
        events=[]
        def event(name,**details):
            item=dict(sequence=len(events),previous_sha256=events[-1]["sha256"] if events else None,event=name,details=details)
            item["sha256"]=hashlib.sha256(audit.wire(item)).hexdigest();events.append(item)
        event("preseal")
        seal=dict(schema_version=1,method="p09.reconstructed_output_seal.v1",protocol_sha256=protocol_hash,files=file_map(run),journal_prefix_sha256=events[-1]["sha256"],
            comparison_inputs_parsed=False,model_calls=0,scientific_validation="not_established")
        seal_raw=audit.wire(seal)+b"\n";(run/"output-seal.json").write_bytes(seal_raw);seal_hash=hashlib.sha256(seal_raw).hexdigest()
        event("outputs_sealed",output_seal_sha256=seal_hash);event("comparison_started",comparison_sha256=files["evaluation/comparison.json"]["sha256"])
        report=dict(schema_version=1,method="p09.source_inclusive_reconstruction.v1",status="COMPLETED_PENDING_AUDIT",protocol_sha256=protocol_hash,output_seal_sha256=seal_hash,
            output_cells=outputs,decision_cells=[{k:v for k,v in x.items() if k!="output_cell_id"} for x in decisions],guards=guards,native_references=native_descriptors,source_coverage_path="source-coverage.json",analysis_counts=audit.analysis_counts(outputs,decisions),resources={},
            historical_output_comparison="all_38_exact_byte_hashes_and_all_90_decisions",historical_archive_integrity="not_provided_by_public_reconstruction",
            scientific_validation="not_established",model_calls=0,network_calls=0,new_downloads=0,provider_spending_usd=0)
        def reseal():
            (run/"reconstruction.json").write_bytes(audit.wire(report)+b"\n")
            if events[-1]["event"]=="reconstruction_completed": events.pop()
            event("reconstruction_completed",report_sha256=hashlib.sha256((run/"reconstruction.json").read_bytes()).hexdigest())
            (run/"journal.jsonl").write_bytes(b"".join(audit.wire(x)+b"\n" for x in events))
            receipt=dict(schema_version=1,method="p09.reconstruction_receipt.v1",operation="reconstruct",status="SEALED_SUCCESS",protocol_sha256=protocol_hash,output_seal_sha256=seal_hash,
                reconstruction_sha256=hashlib.sha256((run/"reconstruction.json").read_bytes()).hexdigest(),files={k:v for k,v in file_map(run).items() if k!="receipt.json"})
            (run/"receipt.json").write_bytes(audit.wire(receipt)+b"\n")
        reseal()
        result=audit.audit_reconstruction(authority,bundle,originals,run,deadline)
        self.assertEqual(result["status"],"PASS_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT",result["unresolved_findings"])
        self.assertEqual(result["originals_verified"],137)
        self.assertEqual(result["analysis_counts"]["planned_output_cells"],38)
        self.assertEqual(result["analysis_counts"]["planned_decisions"],90)
        report["output_cells"][0]["core_score"]["primary"]["passes"]["80"]=False
        reseal()
        failed=audit.audit_reconstruction(authority,bundle,originals,run,deadline)
        self.assertEqual(failed["status"],"FAIL_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT")
        self.assertTrue(any("independent_output_N-L-p05-01_core_score" in x for x in failed["unresolved_findings"]))


if __name__ == "__main__":
    unittest.main()
