"""Fictional controls; non-Windows injection exercises pure logic, not locking."""
from contextlib import nullcontext
from dataclasses import replace
from datetime import date, datetime, timezone
import hashlib
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.serde import ContractError, canonical, encode, fingerprint
from asof.study import source_fact_sources as sources
from asof.study.stable_read import stable_files as platform_stable_files


class SourceFactSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".source-fact-test-", dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cutoff = datetime(2026, 10, 31, 23, 59, 59, 999999, timezone.utc)
        day = date(2020, 1, 1)
        self.availability = Availability(day, day, day, day, day, "fictional_control", None)
        self.catalog = {"fictional": {"roles": ["agent_evidence"]}}
        if os.name != "nt":
            # Fictional pure-logic controls only. Production replay keeps its
            # Windows-only lock boundary, separately checked below.
            injected = patch.object(sources, "stable_files", lambda paths, *, deadline: nullcontext())
            injected.start()
            self.addCleanup(injected.stop)

    def test_unpatched_stable_read_fails_closed_outside_windows(self):
        path = self.root / "fictional.json"
        deadline = time.monotonic() + 30
        # The primitive rejects this platform flag before any Path/file calls.
        # All other Windows controls continue using real, uninjected locks.
        with patch("asof.study.stable_read.os.name", "posix"):
            with self.assertRaises(ContractError):
                with platform_stable_files((path,), deadline=deadline):
                    self.fail("Unpatched non-Windows stable read unexpectedly admitted input")

    def source(self, key, value, *, parents=(), computed=False):
        path = self.root / (key + ".json")
        path.write_bytes(canonical(value))
        return SourceNode(key, "fictional", "v1", path.name, hashlib.sha256(path.read_bytes()).hexdigest(),
                          "agent_evidence", self.availability, TemporalClass.CONTEMPORARY,
                          "https://example.invalid/fictional", parents,
                          datetime(2026, 11, 1, tzinfo=timezone.utc) if computed else None,
                          "fictional_projection" if computed else None, "1" if computed else None)

    def snapshot(self, *nodes):
        return Snapshot(2, "fictional", Profile.DEMO, self.cutoff.date(), False, (), nodes,
                        str(self.root), origin_at=self.cutoff)

    def record(self, key="r", source="s", identity=None, pointer=""):
        return {"record_key": key, "source_id": source,
                "locator": {"format": "json", "pointer": pointer},
                "identity": identity or {"targetId": "T", "diseaseId": "D"}}

    def field(self, name="beta", record="r", family="reported_measurement", group=None, unit_field=None, empty_policy="unknown"):
        return {"record_key": record, "field": name, "family": family,
                "group": group or record + ":" + family, "unit_field": unit_field, "empty_policy": empty_policy}

    def task(self, records=None, fields=None, joins=None):
        return {"schema_version": 1, "task_id": "fictional-task",
                "scope": {"target_id": "T", "indication_id": "D", "target_namespace_version": "fictional:1",
                          "indication_namespace_version": "fictional:1", "action": None, "modality": None, "tissue": None},
                "cutoff": self.cutoff.isoformat(), "profile": "synthetic_demo",
                "primary_families": ["reported_measurement"],
                "records": records if records is not None else [self.record()],
                "fields": fields if fields is not None else [self.field()],
                "joins": joins or [], "collection": {"status": "selected_records", "reason": "Fictional selected records only"}}

    def compile(self, task, snapshot, **kwargs):
        return sources.compile_reference(task, snapshot, self.root, self.catalog,
                                         deadline=time.monotonic() + 30, **kwargs)

    def test_literal_replay_binding_frozen_reference_and_hash(self):
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": -0.0, "unit": "native-unit"})
        task = self.task(fields=[self.field(unit_field="unit")])
        result = self.compile(task, self.snapshot(node))
        fact = result.document["facts"][0]
        self.assertEqual(canonical(fact["value"]), b"-0.0")
        self.assertEqual(fact["unit"], "native-unit")
        self.assertEqual(set(fact["source"]), {"source_id", "sha256", "release_id", "locator", "field"})
        self.assertEqual(fact["source"]["sha256"], node.sha256)
        self.assertIsNone(result.document["scope"]["action"])
        self.assertEqual(result.fingerprint, fingerprint(result.document))
        with self.assertRaises(TypeError):
            result.document["facts"][0]["value"] = 99
        with self.assertRaises(ContractError):
            sources.VerifiedReference(result.document)
        task["scope"]["action"] = "invented"
        self.assertIsNone(result.document["scope"]["action"])

    def test_replay_rejects_document_and_original_tampering(self):
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": 1.0})
        task, snap = self.task(), self.snapshot(node)
        original = self.compile(task, snap)
        tampered = encode(original.document)
        tampered["facts"][0]["value"] = 2.0
        with self.assertRaises(ContractError):
            sources.verify_reference(tampered, original.fingerprint, task, snap, self.root,
                                     self.catalog, deadline=time.monotonic() + 30)
        with self.assertRaises(ContractError):
            sources.verify_reference(tampered, fingerprint(tampered), task, snap, self.root,
                                     self.catalog, deadline=time.monotonic() + 30)
        (self.root / node.path).write_bytes(canonical({"targetId": "T", "diseaseId": "D", "beta": 2.0}))
        with self.assertRaises(ContractError):
            sources.verify_reference(original.document, original.fingerprint, task, snap, self.root,
                                     self.catalog, deadline=time.monotonic() + 30)

    def test_absent_null_empty_and_explicit_empty_value(self):
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": None, "ancestry": [], "sex": ""})
        task = self.task(fields=[self.field(), self.field("standardError"),
                                self.field("ancestry", family="reported_context"),
                                self.field("sex", family="reported_context", empty_policy="value")])
        facts = {f["field"]: f for f in self.compile(task, self.snapshot(node)).document["facts"]}
        self.assertEqual(facts["beta"]["unknown_reason"], "null_source_value")
        self.assertEqual(facts["standardError"]["unknown_reason"], "field_not_in_schema")
        self.assertEqual(facts["ancestry"]["unknown_reason"], "empty_source_value")
        self.assertEqual(facts["sex"]["value"], "")
        self.assertIsNone(facts["sex"]["unknown_reason"])

    def test_family_map_group_boundaries_and_finite_task_validation(self):
        for name in ("studyLocusId", "variantId", "score", "sampleSize"):
            with self.subTest(name=name), self.assertRaises(ContractError):
                sources.validate_task(self.task(fields=[self.field(name)]))
        with self.assertRaises(ContractError):
            sources.validate_task(self.task(fields=[self.field(), self.field()]))
        task = self.task(fields=[self.field(), self.field("sampleSize", family="reported_context", group="r:reported_measurement")])
        with self.assertRaises(ContractError):
            sources.validate_task(task)
        task = self.task()
        task["records"][0]["identity"]["beta"] = float("inf")
        with self.assertRaises(ContractError):
            sources.validate_task(task)

    def test_measurements_require_native_finite_numbers_and_integer_exponent(self):
        for field, value in (("beta", True), ("beta", "1.5"), ("standardError", {"value": 1.0}),
                             ("pValueExponent", 3.0), ("pValueExponent", False)):
            node = self.source("s", {"targetId": "T", "diseaseId": "D", field: value})
            with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                self.compile(self.task(fields=[self.field(field)]), self.snapshot(node))
        for field, value in (("beta", 1), ("beta", 1.0), ("beta", -0.0), ("pValueExponent", -10)):
            node = self.source("s", {"targetId": "T", "diseaseId": "D", field: value})
            fact = self.compile(self.task(fields=[self.field(field)]), self.snapshot(node)).document["facts"][0]
            self.assertEqual(canonical(fact["value"]), canonical(value))
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": ""})
        fact = self.compile(self.task(), self.snapshot(node)).document["facts"][0]
        self.assertEqual(fact["unknown_reason"], "empty_source_value")
        with self.assertRaises(ContractError):
            self.compile(self.task(fields=[self.field(empty_policy="value")]), self.snapshot(node))

    def test_selected_joins_require_same_release_before_byte_access(self):
        task, snap = self.join_task()
        snap = replace(snap, sources=(snap.sources[0], replace(snap.sources[1], release_id="v2")))
        with patch.object(sources, "stable_files", side_effect=AssertionError("bytes accessed")):
            with self.assertRaises(ContractError):
                self.compile(task, snap)

    def test_strict_pointer_identity_scope_and_dates(self):
        node = self.source("s", {"a/b": {"~": [{"targetId": "T", "diseaseId": "D", "beta": 1.0}]}})
        task = self.task(records=[self.record(pointer="/a~1b/~0/0")])
        self.assertEqual(self.compile(task, self.snapshot(node)).document["facts"][0]["value"], 1.0)
        for pointer in ("a", "/a~2b", "/a~1b/~0/00", "/a~1b/~0/-"):
            task["records"][0]["locator"]["pointer"] = pointer
            with self.subTest(pointer=pointer), self.assertRaises(ContractError):
                self.compile(task, self.snapshot(node))
        for row in ({"targetId": "OTHER", "diseaseId": "D", "beta": 1.0},
                    {"targetId": "T", "diseaseId": "D", "publicationDate": "2030-01-01"},
                    {"targetId": "T", "diseaseId": "D", "publicationYear": True},
                    {"targetId": "T", "diseaseId": "D", "evidenceDate": "2020"}):
            with self.subTest(row=row), self.assertRaises(ContractError):
                self.compile(self.task(), self.snapshot(self.source("s", row)))

    def test_entire_graph_roles_dates_and_denies_precede_byte_access(self):
        parent = self.source("p", {"mapping": "fictional"})
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": 1.0}, parents=("p",), computed=True)
        for kwargs in ({"denied_source_ids": ("p",)}, {"denied_dataset_ids": ("fictional",)},
                       {"denied_sha256": (parent.sha256,)}):
            with self.subTest(kwargs=kwargs), patch.object(sources, "stable_files", side_effect=AssertionError("bytes accessed")):
                with self.assertRaises(ContractError):
                    self.compile(self.task(), self.snapshot(node, parent), **kwargs)
        future = [replace(parent, availability=replace(parent.availability, **{name: date(2030, 1, 1)}))
                  for name in ("first_public_at", "release_public_at", "record_public_at", "annotation_public_at")]
        for changed in (replace(parent, role="evaluation_only"), *future,
                        replace(parent, temporal_classification=TemporalClass.UNVERIFIED)):
            with patch.object(sources, "stable_files", side_effect=AssertionError("bytes accessed")):
                with self.assertRaises(ContractError):
                    self.compile(self.task(), self.snapshot(node, changed))
        # Later computation from earlier eligible sources is permitted.
        self.assertEqual(self.compile(self.task(), self.snapshot(node, parent)).document["facts"][0]["value"], 1.0)

    def test_missing_ancestors_cycles_profile_and_cutoff_mismatch(self):
        p = self.source("p", {}, parents=("s",), computed=True)
        s = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": 1.0}, parents=("p",), computed=True)
        with self.assertRaises(ContractError):
            self.compile(self.task(), self.snapshot(s, p))
        with self.assertRaises(ContractError):
            self.compile(self.task(), self.snapshot(s))
        node = self.source("s", {"targetId": "T", "diseaseId": "D"})
        with self.assertRaises(ContractError):
            self.compile(self.task(), replace(self.snapshot(node), origin_at=datetime(2020, 1, 1, tzinfo=timezone.utc)))
        task = self.task()
        task["profile"] = "contemporary_assessment"
        with self.assertRaises(ContractError):
            self.compile(task, self.snapshot(node))

    def test_duplicate_provider_ids_remain_distinct_across_files(self):
        a = self.source("s", {"id": "same", "targetId": "T", "diseaseId": "D", "beta": 1.0})
        b = self.source("b", {"id": "same", "targetId": "T", "diseaseId": "D", "beta": 1.0})
        task = self.task(records=[self.record(), self.record("other", "b")],
                         fields=[self.field(), self.field(record="other")])
        facts = self.compile(task, self.snapshot(a, b)).document["facts"]
        self.assertNotEqual(facts[0]["fact_id"], facts[1]["fact_id"])

    def join_task(self, cardinality="one_to_one", inventory="complete", candidate_values=(1.0,)):
        left = self.source("s", {"targetId": "T", "diseaseId": "D", "studyLocusId": "L"})
        nodes, records, fields = [left], [self.record()], []
        for i, value in enumerate(candidate_values):
            key = "candidate" + str(i)
            nodes.append(self.source(key, {"studyLocusId": "L", "beta": value}))
            records.append(self.record(key, key, {"studyLocusId": "L"}))
            fields.append(self.field(record=key))
        join = {"join_id": "locus", "left_record": "r", "left_field": "studyLocusId",
                "right_records": [r["record_key"] for r in records[1:]], "right_field": "studyLocusId",
                "cardinality": cardinality, "inventory_status": inventory}
        return self.task(records, fields, [join]), self.snapshot(*nodes)

    def test_exact_joins_zero_one_multiple_and_conflict(self):
        for inventory, expected in (("partial", "missing_input_in_partial_collection"),
                                    ("complete", "zero_matches_selected_collection")):
            task, snap = self.join_task(inventory=inventory, candidate_values=())
            self.assertEqual(self.compile(task, snap).document["joins"][0]["status"], expected)
        task, snap = self.join_task()
        self.assertEqual(self.compile(task, snap).document["facts"][0]["value"], 1.0)
        for values, expected, reason in (((1.0, 1.0), "unresolved_multiplicity", "unavailable_join"),
                                         ((1.0, 2.0), "conflicting_values", "conflicting_join")):
            task, snap = self.join_task(candidate_values=values)
            result = self.compile(task, snap).document
            self.assertEqual(result["joins"][0]["status"], expected)
            self.assertEqual(len(result["joins"][0]["matched_sources"]), 2)
            self.assertTrue(all(f["value"] is None and f["unknown_reason"] == reason for f in result["facts"]))
        task, snap = self.join_task(cardinality="one_to_many", candidate_values=(1.0, 2.0))
        self.assertEqual([f["value"] for f in self.compile(task, snap).document["facts"]], [1.0, 2.0])

    def test_unknown_join_chain_cannot_reauthorize_linked_facts(self):
        task, snap = self.join_task(candidate_values=(1.0, 2.0))
        extra = self.source("extra", {"studyLocusId": "L", "beta": 3.0})
        task["records"].append(self.record("extra", "extra", {"studyLocusId": "L"}))
        task["fields"].append(self.field(record="extra"))
        task["joins"].append({"join_id": "downstream", "left_record": "candidate0", "left_field": "studyLocusId",
                              "right_records": ["extra"], "right_field": "studyLocusId",
                              "cardinality": "one_to_one", "inventory_status": "complete"})
        result = self.compile(task, replace(snap, sources=snap.sources + (extra,))).document
        self.assertEqual(result["facts"][-1]["unknown_reason"], "conflicting_join")

    def test_native_units_and_empty_missing_reference(self):
        for unit in (1, [], ""):
            node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": 1.0, "unit": unit})
            with self.subTest(unit=unit), self.assertRaises(ContractError):
                self.compile(self.task(fields=[self.field(unit_field="unit")]), self.snapshot(node))
        task = self.task(records=[], fields=[])
        task["collection"] = {"status": "incomplete", "reason": "Fictional missing selected input; no biological absence"}
        result = self.compile(task, self.snapshot())
        self.assertEqual(result.document["facts"], ())
        self.assertEqual(result.document["collection"]["status"], "incomplete")
        with self.assertRaises(ContractError):
            self.compile(self.task(records=[], fields=[]), self.snapshot())

    def test_deadline_and_receipt_required_for_real_profile(self):
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": 1.0})
        with self.assertRaises(TimeoutError):
            sources.compile_reference(self.task(), self.snapshot(node), self.root, self.catalog,
                                      deadline=time.monotonic() - 1)
        task = self.task()
        task["profile"] = "contemporary_assessment"
        with self.assertRaises(ContractError):
            self.compile(task, replace(self.snapshot(node), profile=Profile.CONTEMPORARY))

    def test_receipt_bound_contemporary_replay_and_tampering(self):
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": 1.0})
        receipt = {"status": "completed", "sha256": node.sha256,
                   "bytes": (self.root / node.path).stat().st_size,
                   "dataset_id": node.dataset_id, "release_id": node.release_id,
                   "relative_path": node.path, "url": node.source_url,
                   "completed_at_utc": "2020-01-01T12:00:00+00:00"}
        receipt_path = self.root / "receipt.json"
        receipt_path.write_bytes(canonical(receipt))
        receipt_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        availability = replace(node.availability, basis="public_download_receipt",
                               known_public_by=datetime(2020, 1, 1, 12, tzinfo=timezone.utc),
                               evidence_ref=receipt_hash)
        node = replace(node, receipt_path=receipt_path.name, receipt_sha256=receipt_hash,
                       availability=availability)
        task = self.task()
        task["profile"] = "contemporary_assessment"
        snap = replace(self.snapshot(node), profile=Profile.CONTEMPORARY)
        result = self.compile(task, snap)
        self.assertEqual(result.document["source_proofs"][0]["receipt_sha256"], receipt_hash)
        receipt["bytes"] += 1
        receipt_path.write_bytes(canonical(receipt))
        with self.assertRaises(ContractError):
            self.compile(task, snap)
        # A newly pinned bad receipt still cannot assert the wrong byte count.
        changed_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        changed = replace(node, receipt_sha256=changed_hash,
                          availability=replace(availability, evidence_ref=changed_hash))
        with self.assertRaises(ContractError):
            self.compile(task, replace(snap, sources=(changed,)))

    def test_fictional_parquet_selected_row_and_absent_schema(self):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("install the ingest extra for source-audit tests")
        if pa.__version__ != "21.0.0":
            self.skipTest("Source-fact Parquet replay requires optional Arrow 21.0.0")
        node = self.source("s", {})
        parquet_path = self.root / "fictional.parquet"
        pq.write_table(pa.table({"targetId": ["T", "T"], "diseaseId": ["D", "D"],
                                 "beta": [0.5, -0.0]}), parquet_path, row_group_size=1)
        node = replace(node, path=parquet_path.name,
                       sha256=hashlib.sha256(parquet_path.read_bytes()).hexdigest())
        task = self.task(fields=[self.field(), self.field("standardError")])
        task["records"][0]["locator"] = {"format": "parquet", "row_group": 1, "row": 0}
        facts = self.compile(task, self.snapshot(node)).document["facts"]
        self.assertEqual(canonical(facts[0]["value"]), b"-0.0")
        self.assertEqual(facts[1]["unknown_reason"], "field_not_in_schema")
        task["records"][0]["locator"]["row"] = 1
        with self.assertRaises(ContractError):
            self.compile(task, self.snapshot(node))

    def test_compiled_reference_exact_projection_must_fit_common_wire(self):
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": 1.0, "originalUnit": "u" * 513})
        with self.assertRaises(ContractError):
            self.compile(self.task(fields=[self.field(unit_field="originalUnit")]), self.snapshot(node))
        deep = "native"
        for _ in range(17):
            deep = [deep]
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "ancestry": deep})
        with self.assertRaises(ContractError):
            self.compile(self.task(fields=[self.field("ancestry", family="reported_context")]), self.snapshot(node))
        task = self.task()
        task["task_id"] = "t" * 513
        with patch.object(sources, "stable_files", side_effect=AssertionError("bytes accessed")):
            with self.assertRaises(ContractError):
                self.compile(task, self.snapshot(node))

    def test_snapshot_cannot_grant_an_additional_raw_root(self):
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": 1.0})
        with tempfile.TemporaryDirectory(prefix=".source-fact-other-root-", dir=Path.cwd()) as folder:
            other_root = Path(folder)
            (other_root / node.path).write_bytes((self.root / node.path).read_bytes())
            snap = replace(self.snapshot(node), raw_root=str(other_root))
            with patch.object(sources, "stable_files", side_effect=AssertionError("bytes accessed")):
                with self.assertRaises(ContractError):
                    self.compile(self.task(), snap)
            result = self.compile(self.task(), snap, approved_raw_root=other_root)
            self.assertEqual(result.document["facts"][0]["value"], 1.0)
            replayed = sources.verify_reference(result.document, result.fingerprint, self.task(), snap,
                                                 self.root, self.catalog, deadline=time.monotonic() + 30,
                                                 approved_raw_root=other_root)
            self.assertEqual(replayed.fingerprint, result.fingerprint)

    def test_reference_relocates_but_catalog_deny_and_snapshot_policy_remain_bound(self):
        node = self.source("s", {"targetId": "T", "diseaseId": "D", "beta": 1.0})
        task, snap = self.task(), self.snapshot(node)
        result = self.compile(task, snap)
        self.assertEqual(result.document["source_proofs"][0]["path"], node.path)
        self.assertTrue(result.document["method"]["projection_wire_verified"])
        with tempfile.TemporaryDirectory(prefix=".source-fact-relocated-", dir=Path.cwd()) as folder:
            relocated = Path(folder)
            (relocated / node.path).write_bytes((self.root / node.path).read_bytes())
            replayed = sources.verify_reference(result.document, result.fingerprint, task,
                                                 replace(snap, raw_root=str(relocated)), relocated,
                                                 self.catalog, deadline=time.monotonic() + 30)
            self.assertEqual(replayed.fingerprint, result.fingerprint)
        with self.assertRaises(ContractError):
            sources.verify_reference(result.document, result.fingerprint, task, snap, self.root,
                                     self.catalog, deadline=time.monotonic() + 30,
                                     denied_source_ids=("new-unrelated-deny",))
        with self.assertRaises(ContractError):
            sources.verify_reference(result.document, result.fingerprint, task, snap, self.root,
                                     {"fictional": {"roles": ["agent_evidence"], "version": "changed"}},
                                     deadline=time.monotonic() + 30)

    def test_one_to_one_conflict_includes_native_units_and_schema_presence(self):
        task, snap = self.join_task(candidate_values=(1.0, 1.0))
        changed = []
        for i, node in enumerate(snap.sources[1:]):
            path = self.root / node.path
            path.write_bytes(canonical({"studyLocusId": "L", "beta": 1.0, "unit": "u" + str(i)}))
            changed.append(replace(node, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            task["fields"][i]["unit_field"] = "unit"
        result = self.compile(task, replace(snap, sources=(snap.sources[0], *changed))).document
        self.assertEqual(result["joins"][0]["status"], "conflicting_values")
        self.assertTrue(all(f["unknown_reason"] == "conflicting_join" for f in result["facts"]))


if __name__ == "__main__":
    unittest.main()
