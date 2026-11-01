"""Fictional grouped-score and all-cell controls, not biomedical observations."""

import copy
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.serde import ContractError, canonical, encode
from asof.study.source_fact_sources import compile_reference
from asof.study.source_fact_evaluation import score_cell, aggregate_cells


class SourceFactEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        if os.name != "nt":
            self.guard = patch("asof.study.source_fact_sources.stable_files",
                               side_effect=lambda *a, **k: nullcontext())
            self.guard.start()
            self.addCleanup(self.guard.stop)
        self.rows = [
            dict(id="fiction-0", targetId="CONTROL", diseaseId="CONTROL_DISEASE",
                 beta=-0.0, pValueMantissa=2.0, pValueExponent=-4,
                 standardError=1.0, unit="native-control-unit", studyLocusId="locus-0"),
            dict(id="fiction-1", targetId="CONTROL", diseaseId="CONTROL_DISEASE",
                 beta=1.0, unit="native-control-unit", studyLocusId="locus-1"),
        ]
        raw = canonical(self.rows)
        (self.root / "original.json").write_bytes(raw)
        when = date(2000, 1, 1)
        availability = Availability(when, when, when, when, when, "fictional_control", None)
        self.cutoff = datetime(2001, 1, 1, tzinfo=timezone.utc)
        node = SourceNode("raw-control", "control", "fiction-v1", "original.json",
                          hashlib.sha256(raw).hexdigest(), "agent_evidence", availability,
                          TemporalClass.HISTORICAL, "https://example.invalid/control")
        self.snapshot = Snapshot(2, "control", Profile.DEMO, self.cutoff.date(), False,
                                 (), (node,), str(self.root), {}, self.cutoff)
        fields = [dict(record_key="r0", field=field, family="reported_measurement",
                       group="r0-estimate", unit_field="unit" if field == "beta" else None,
                       empty_policy="unknown")
                  for field in ("beta", "pValueMantissa", "pValueExponent", "standardError")]
        fields += [dict(record_key="r1", field="beta", family="reported_measurement",
                        group="r1-estimate", unit_field="unit", empty_policy="unknown"),
                   dict(record_key="r1", field="studyLocusId", family="identity_linkage",
                        group="linkage", unit_field=None, empty_policy="unknown")]
        self.task = dict(
            schema_version=1, task_id="fictional-group-control",
            scope=dict(target_id="CONTROL", indication_id="CONTROL_DISEASE",
                       target_namespace_version="control-v1", indication_namespace_version="control-v1",
                       action=None, modality=None, tissue=None),
            cutoff=self.cutoff.isoformat(), profile="synthetic_demo",
            primary_families=["reported_measurement", "identity_linkage"],
            records=[dict(record_key=f"r{i}", source_id="raw-control",
                          locator=dict(format="json", pointer=f"/{i}"),
                          identity=dict(id=row["id"], targetId="CONTROL", diseaseId="CONTROL_DISEASE"))
                     for i, row in enumerate(self.rows)], fields=fields, joins=[],
            collection=dict(status="selected_records", reason="Only two fictional selected records."))
        self.reference = compile_reference(self.task, self.snapshot, self.root,
                                            {"control": {"roles": ["agent_evidence"]}},
                                            deadline=time.monotonic() + 20)

    def output(self, *, omit=(), status="answered", reason=None):
        document = self.reference.document
        facts = [{key: encode(fact[key]) for key in
                  ("fact_id", "value", "unit", "source", "unknown_reason")}
                 for fact in document["facts"] if fact["fact_id"] not in omit]
        return dict(schema_version=1, task_id=document["task_id"],
                    task_sha256=document["task_sha256"], status=status, facts=facts,
                    collection_status=document["collection"]["status"], reason=reason)

    def plan(self, cell_id):
        return dict(cell_id=cell_id, task_id=self.reference.document["task_id"],
                    task_sha256=self.reference.document["task_sha256"],
                    reference_sha256=self.reference.fingerprint)

    def test_group_means_prevent_component_rich_record_dominance(self):
        omitted = [f["fact_id"] for f in self.reference.document["facts"]
                   if f["record_key"] == "r1" and f["field"] == "beta"]
        result = score_cell(self.reference, canonical(self.output(omit=omitted)), cell_id="cell")
        self.assertEqual(result["family_scores"]["reported_measurement"]["coverage"], .5)
        self.assertEqual(result["primary"]["coverage"], 2 / 3)
        self.assertFalse(result["completion"])
        self.assertTrue(result["primary"]["passes"]["60"])
        self.assertFalse(result["primary"]["passes"]["80"])

    def test_wrong_native_types_sign_units_or_source_are_critical(self):
        original = self.output()
        beta = next(i for i, f in enumerate(self.reference.document["facts"])
                    if f["record_key"] == "r0" and f["field"] == "beta")
        for field, value in (("value", 0.0), ("value", 0), ("value", False),
                             ("unit", "invented-unit"), ("source", {**original["facts"][beta]["source"],
                                                                     "release_id": "wrong"})):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(original)
                changed["facts"][beta][field] = value
                result = score_cell(self.reference, canonical(changed), cell_id="cell")
                self.assertTrue(result["critical_errors"])
                self.assertFalse(result["completion"])

    def test_no_rescue_of_failed_or_malformed_cells_and_complete_schedule(self):
        good = score_cell(self.reference, canonical(self.output()), cell_id="ok")
        timeout = score_cell(self.reference, canonical(self.output()), cell_id="late", terminal="timeout")
        missing = score_cell(self.reference, None, cell_id="not-run", terminal="unexecuted")
        malformed = score_cell(self.reference, b"{}", cell_id="malformed")
        summary = aggregate_cells([self.plan(i) for i in ("ok", "late", "not-run", "malformed")],
                                  [good, timeout, missing, malformed])
        self.assertEqual(summary["planned_cells"], 4)
        self.assertEqual(summary["completion_count"], 1)
        self.assertEqual(summary["completion_rate"], .25)
        self.assertEqual(malformed["terminal"], "malformed")
        self.assertEqual(malformed["received_terminal"], "returned")
        for result in (timeout, missing, malformed):
            self.assertIsNone(result["primary"]["coverage"])
            self.assertFalse(result["completion"])
        for results in ([good], [good, good], [good, missing]):
            with self.assertRaises(ContractError):
                aggregate_cells([self.plan("ok"), self.plan("late")], results)

    def test_reference_and_scored_cells_cannot_be_substituted_by_serialized_dicts(self):
        raw = canonical(self.output())
        with self.assertRaises(ContractError):
            score_cell(encode(self.reference.document), raw, cell_id="cell")
        result = score_cell(self.reference, raw, cell_id="cell")
        with self.assertRaises(ContractError):
            aggregate_cells([self.plan("cell")], [encode(result)])
        with self.assertRaises(TypeError):
            result["primary"]["coverage"] = .25
        with self.assertRaises(TypeError):
            self.reference.document["facts"][0]["source"]["release_id"] = "rewrite"


if __name__ == "__main__":
    unittest.main()
