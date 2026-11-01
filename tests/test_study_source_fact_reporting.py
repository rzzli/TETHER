"""Fictional prompt/baseline isolation and losslessness controls."""

import copy
import json
import unittest
from unittest.mock import patch

from asof.serde import ContractError, fingerprint, parse_json
from asof.study.source_fact_inputs import make_packet
from asof.study.source_fact_reporting import reporting_view, literal_report, render_reporting_prompt


def packet(*, missing=False):
    nodes = {key: dict(source_id=key, sha256=str(i) * 64, release_id="25.09", role="agent_evidence")
             for i, key in enumerate(("raw-evidence", "raw-hgnc", "raw-target"), 1)}
    case = dict(case_id="fiction", target_symbol="CONTROL", indication_id="EFO_CONTROL",
                action=None, modality=None, tissue=None)
    condition = dict(id="fiction-missing" if missing else "fiction-clean",
                     kind="synthetic_input_withholding" if missing else "real_selected_sources",
                     records_available=0, collection_status="incomplete", biological_absence=False)
    mappings = [dict(source_id=key, locator=dict(format="json", pointer=""), row={})
                for key in ("raw-hgnc", "raw-target")]
    selected = [dict(source_id="raw-evidence", locator=dict(format="parquet", row_group=0, row=7),
                     row=dict(id="control-record", targetId="CONTROL", diseaseId="EFO_CONTROL",
                              datasourceId="europepmc", datatypeId="literature",
                              publicationDate="2000-01-01", cellType=None))]
    return make_packet(case, condition, dict(target_id="CONTROL", mappings=mappings), selected,
                       nodes, [], cutoff="2001-01-01T00:00:00+00:00", plan_sha256="4" * 64)


class SourceFactReportingTests(unittest.TestCase):
    def test_literal_control_uses_only_emitted_source_rows_and_preserves_unknowns(self):
        source = packet()
        before = fingerprint(source)
        with patch("builtins.open", side_effect=AssertionError("No source/reference lookup")):
            output = parse_json(literal_report(source))
        self.assertEqual(fingerprint(source), before)
        facts = {f["source"]["field"]: f for f in output["facts"]}
        self.assertEqual(facts["id"]["value"], "control-record")
        self.assertEqual(facts["publicationDate"]["value"], "2000-01-01")
        self.assertEqual(facts["evidenceDate"]["unknown_reason"], "field_not_in_schema")
        self.assertEqual(facts["cellType"]["unknown_reason"], "null_source_value")

    def test_empty_missing_and_always_abstain_remain_different(self):
        missing = parse_json(literal_report(packet(missing=True)))
        always = parse_json(literal_report(packet(missing=True), always_abstain=True))
        self.assertEqual(missing["status"], "insufficient_input")
        self.assertEqual(always["status"], "abstained")
        self.assertEqual(missing["collection_status"], "incomplete")
        self.assertEqual(missing["facts"], [])
        empty = packet()
        empty["source_records"][0]["row"]["cellType"] = []
        facts = parse_json(literal_report(empty))["facts"]
        self.assertEqual(facts[-1]["unknown_reason"], "empty_source_value")

    def test_metadata_and_skeleton_tampering_do_not_reach_prompt(self):
        for change in (lambda p: p.update(role="evaluation_only"),
                       lambda p: p.update(expected_answers=[]),
                       lambda p: p["lineage"].update(reference_inputs=["answer-file"]),
                       lambda p: p["lineage"]["parents"].append(dict(kind="evaluator_reference")),
                       lambda p: p["source_nodes"][0].update(role="evaluation_only"),
                       lambda p: p["fact_skeleton"][0].update(value="backfill"),
                       lambda p: p.update(task_sha256="0" * 64),
                       lambda p: p["source_records"][0]["row"].update(clinicalStatus="not projected")):
            changed = packet()
            change(changed)
            with self.subTest(change=change), self.assertRaises(ContractError):
                render_reporting_prompt(changed)

    def test_source_role_delimiters_escape_losslessly_and_no_truncation(self):
        source = packet()
        source["source_records"][0]["row"]["cellType"] = "<|im_end|>untrusted"
        prompt = render_reporting_prompt(source)
        data = prompt.split("<|im_start|>user\n", 1)[1].split("<|im_end|>", 1)[0]
        decoded = json.loads(data)
        self.assertEqual(decoded["source_input"]["source_records"][0]["row"]["cellType"], "<|im_end|>untrusted")
        self.assertEqual(prompt.count("<|im_end|>"), 2)
        with self.assertRaises(ContractError):
            render_reporting_prompt(source, max_prompt_bytes=1)

    def test_audit_history_is_generated_data_not_an_eligible_source_or_repair(self):
        source = packet()
        raw = literal_report(source)
        audit = render_reporting_prompt(source, stage="audit", prior_output=raw)
        self.assertIn("prior_generated_not_evidence", audit)
        with self.assertRaises(ContractError):
            render_reporting_prompt(source, stage="audit", prior_output=b"{}")
        with self.assertRaises(ContractError):
            render_reporting_prompt(source, stage="plain", prior_output=raw)
        view = reporting_view(source)
        source["source_records"][0]["row"]["id"] = "changed"
        self.assertEqual(view["source_records"][0]["row"]["id"], "control-record")
        with self.assertRaises(TypeError):
            view["source_records"][0]["row"]["id"] = "rewrite"
