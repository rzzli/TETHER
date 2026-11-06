"""Authored fictional checks; no real SciFact predictions/references are opened."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import ast

SPEC = importlib.util.spec_from_file_location("independent_reconstruct", Path(__file__).with_name("reconstruct.py"))
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def corpus():
    return {17: {"doc_id": 17, "title": "Invented study", "abstract": ["one", "two", "three", "four", "five"]}}


def prediction(i=1, label="SUPPORT", sentences=None):
    return {"id": i, "evidence": {"17": {"label": label, "sentences": [0] if sentences is None else sentences}}}


def disposition(i, p, status="accepted", failure=None):
    return {"id": i, "producer_status": failure or "produced", "check_status": "not_run" if failure else status,
            "prediction": p, "reason": "fictional failure" if failure or status != "accepted" else None}


def resource(**kw):
    value = dict(wall_seconds=1.0, cpu_seconds=.5, peak_memory_bytes=100,
                 memory_method="fictional", input_bytes=12, output_bytes=23, examples=1,
                 model_input_tokens=None, model_output_tokens=None, tokenizer_identity=None,
                 provider_usage=None, token_usage_reason="not_applicable_non_llm", provider_cost_usd=0)
    value.update(kw)
    return value


def fictional_session(root, *, total_delta=0, budget=100):
    root = Path(root)
    (root / "cells").mkdir()
    events = []
    def event(name, details):
        row = {"sequence": len(events), "event": name, "details": details,
               "previous_sha256": events[-1]["sha256"] if events else None}
        row["sha256"] = r.digest(row)
        events.append(row)
    config = {"fictional": True}
    event("run_reserved", {"run_id": "fictional-session"})
    event("native_configured", {"schedule": ["1"], "configuration": config,
                               "budgets": {"max_calls": 1, "max_wall_seconds": budget, "max_output_bytes": 100}})
    request = {"query": "invented"}
    event("native_dispatch", {"cell_id": "1", "request": request, "request_sha256": r.digest(request)})
    value = {"schema_version": 1, "cell_id": "1", "status": "completed", "result": {"fictional": True},
             "resources": resource(), "session_elapsed_seconds": 2}
    relative = "cells/" + r.sha(b"1") + ".json"
    payload = r.canonical(value) + b"\n"
    (root / relative).write_bytes(payload)
    event("native_terminal", {"cell_id": "1", "status": "completed", "path": relative,
                              "record_sha256": r.sha(payload), "record_fingerprint": r.digest(value), "resources": value["resources"]})
    totals = {"wall_seconds": 1.0 + total_delta, "cpu_seconds": .5, "input_bytes": 12, "output_bytes": 23, "examples": 1,
              "unknown_measurements": {"wall_seconds": 0, "cpu_seconds": 0, "input_bytes": 0, "output_bytes": 0, "examples": 0},
              "provider_cost_usd": 0, "model_input_tokens": None, "model_output_tokens": None}
    event("native_finalized", {"terminal_cells": 1, "totals": totals})
    (root / "journal.jsonl").write_bytes(b"".join(r.canonical(e) + b"\n" for e in events))
    receipt = {"schema_version": 1, "kind": "scifact_native_session", "schedule": ["1"], "configuration": config,
               "terminal_cells": 1, "totals": totals,
               "outputs": {p.relative_to(root).as_posix(): r.sha(p.read_bytes()) for p in root.rglob("*") if p.is_file()}}
    payload = r.canonical(receipt) + b"\n"
    (root / "receipt.json").write_bytes(payload)
    return r.sha(payload)


class ReconstructionTests(unittest.TestCase):
    def test_strict_native_rationale_cap_and_alternatives(self):
        gold = {"id": 1, "evidence": {"17": [{"label": "SUPPORT", "sentences": [3]},
                                                {"label": "SUPPORT", "sentences": [0, 1, 2]}]}}
        self.assertFalse(r.strict_correct(gold, prediction(sentences=[0, 1, 4, 3])))
        self.assertTrue(r.strict_correct(gold, prediction(sentences=[0, 1, 2, 3])))
        long = {"id": 1, "evidence": {"17": [{"label": "SUPPORT", "sentences": [0, 1, 2, 3]}]}}
        self.assertTrue(r.strict_correct(long, prediction(sentences=[0, 1, 2, 3])))
        self.assertFalse(r.strict_correct(long, prediction(label="CONTRADICT", sentences=[0, 1, 2, 3])))

    def test_failure_empty_and_successful_nei_have_different_denominators(self):
        golds = [{"id": i, "evidence": {}} for i in [1, 2, 3]]
        rows = [disposition(1, {"id": 1, "evidence": {}}), disposition(2, None, failure="timeout"),
                disposition(3, {"id": 3, "evidence": {}}, "rejected")]
        out = r.aggregate([1, 2, 3], golds, rows, corpus())
        self.assertEqual(out["counts"]["produced"], 2)
        self.assertEqual(out["counts"]["correct_raw"], 2)
        self.assertEqual(out["counts"]["correct_and_admitted"], 1)
        self.assertEqual(out["counts"]["correct_but_policy_rejected"], 1)
        self.assertEqual(out["rates"]["correct_and_admitted_per_scheduled"], 1 / 3)
        self.assertIsNone(out["case_results"][1]["raw_strict_correct"])
        self.assertEqual(out["raw_predictions"], out["checked_predictions"])

    def test_schedule_cannot_drop_duplicate_or_reorder(self):
        gold = [{"id": 1, "evidence": {}}, {"id": 2, "evidence": {}}]
        rows = [disposition(i, {"id": i, "evidence": {}}) for i in [1, 2]]
        for schedule, altered in [([], []), ([1, 1], rows), ([1, 2], rows[:1]), ([1, 2], rows[::-1])]:
            with self.subTest(schedule=schedule, altered=altered), self.assertRaises(r.AuditError):
                r.aggregate(schedule, gold, altered, corpus())

    def test_native_prediction_contract(self):
        for p in [dict(prediction(), extra=True), prediction(sentences=[0, 0]), prediction(sentences=[5]),
                  prediction(label="NEI"), {"id": 1, "evidence": {"017": {"label": "SUPPORT", "sentences": [0]}}}]:
            with self.subTest(p=p), self.assertRaises(r.AuditError):
                r.native_prediction(p, corpus(), 1)
        self.assertEqual(r.native_prediction({"id": 1, "evidence": {}}, corpus(), 1)["evidence"], {})
        self.assertEqual(r.native_prediction(prediction(sentences=[]), corpus(), 1)["evidence"]["17"]["sentences"], [])

    def test_source_binding_uses_original_sentence_bytes(self):
        result = {"prediction": prediction(), "retrieved": [{"doc_id": 17, "rank": 1, "score": .3,
                  "document_sha256": r.digest(corpus()[17])}],
                  "source_bindings": [{"doc_id": 17, "sentence_id": 0, "text_sha256": r.sha(b"one")}]}
        self.assertEqual(r.source_bindings(result, corpus(), 1), {"retrieved_documents": 1, "returned_sentences": 1})
        result["source_bindings"][0]["text_sha256"] = r.sha(b"two")
        with self.assertRaises(r.AuditError): r.source_bindings(result, corpus(), 1)

    def test_source_binding_exact_coverage_and_unretrieved_doc(self):
        result = {"prediction": prediction(), "retrieved": [], "source_bindings": []}
        with self.assertRaises(r.AuditError): r.source_bindings(result, corpus(), 1)
        result["prediction"] = {"id": 1, "evidence": {}}
        self.assertEqual(r.source_bindings(result, corpus(), 1)["returned_sentences"], 0)

    def test_resource_totals_keep_unknown_and_peak_not_sum(self):
        values = [{"resources": resource()}, {"resources": resource(wall_seconds=None, peak_memory_bytes=150)}]
        totals = r.resource_totals(values)
        self.assertEqual(totals["wall_seconds"], 1)
        self.assertEqual(totals["unknown_measurements"]["wall_seconds"], 1)
        panel = r.resource_panel(values)
        self.assertEqual(panel["peak_memory_bytes_max"], 150)
        self.assertEqual(panel["logical_input_bytes"], 24)
        self.assertEqual(panel["primary_product_output_bytes"], 46)
        with self.assertRaises(r.AuditError): r.resource_totals([{"resources": resource(input_bytes=-1)}])

    def test_exact_comparison_rejects_denominator_and_extra_fields(self):
        r.same({"a": 1}, {"a": 1}, "fixture")
        for altered in [{"a": 2}, {"a": 1, "hidden": 2}]:
            with self.assertRaises(r.AuditError): r.same({"a": 1}, altered, "fixture")

    def test_json_duplicate_keys_rejected(self):
        with self.assertRaises(r.AuditError): r.parse(b'{"id":1,"id":2}')
        with self.assertRaises(r.AuditError): r.parse(b'{"score":NaN}')

    def test_receipt_tampering_and_extra_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "x.json").write_bytes(b'{}\n')
            receipt = {"outputs": {"x.json": r.sha(b'{}\n')}}
            raw = r.canonical(receipt) + b"\n"
            (root / "receipt.json").write_bytes(raw)
            self.assertEqual(r.inventory(root, "receipt.json", r.sha(raw)), receipt)
            (root / "surplus").write_bytes(b"x")
            with self.assertRaises(r.AuditError): r.inventory(root, "receipt.json", r.sha(raw))
            (root / "surplus").unlink()
            (root / "x.json").write_bytes(b'{"changed":true}\n')
            with self.assertRaises(r.AuditError): r.inventory(root, "receipt.json", r.sha(raw))

    def test_path_escape_and_empty_schedule_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in ["../escape", "/absolute", "x\\y", "C:/escape", "./alias"]:
                with self.subTest(path=path), self.assertRaises(r.AuditError): r.child(Path(tmp), path)
        with self.assertRaises(r.AuditError): r.schedule_ids([])

    def test_grid_tie_break_is_declared_not_lexicographic(self):
        rows = [{"configuration": {"k": k, "rationale_threshold": t}, "status": "completed",
                 "metrics": {"abstract_rationalized_f1": .4, "sentence_label_f1": .5}}
                for k in [5, 10, 20] for t in [.25, .5, .75]]
        self.assertEqual(r.select(rows)["configuration"], {"k": 5, "rationale_threshold": .75})
        rows[5]["metrics"]["sentence_label_f1"] = .6
        self.assertEqual(r.select(rows)["configuration"], {"k": 10, "rationale_threshold": .75})
        with self.assertRaises(r.AuditError): r.select(rows[:-1])

    def test_session_rebuild_rejects_rehashed_accounting_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = fictional_session(tmp)
            records, requests = r.session(tmp, receipt, ["1"], {"fictional": True})
            self.assertEqual(records["1"]["resources"]["examples"], 1)
            self.assertEqual(requests["1"], {"query": "invented"})
        with tempfile.TemporaryDirectory() as tmp:
            receipt = fictional_session(tmp, total_delta=10)
            with self.assertRaisesRegex(r.AuditError, "resource totals"):
                r.session(tmp, receipt, ["1"], {"fictional": True})

    def test_session_rejects_rehashed_budget_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = fictional_session(tmp, budget=1)
            with self.assertRaisesRegex(r.AuditError, "Budget/status"):
                r.session(tmp, receipt, ["1"], {"fictional": True})

    def test_official_cli_runs_unchanged_only_on_invented_rows(self):
        root = Path(__file__).resolve().parents[4]
        evaluator = (root / "data/reference/scifact-evaluator-66feffc5/evaluator/eval.py").read_bytes()
        golds = [{"id": 1, "evidence": {"17": [{"label": "SUPPORT", "sentences": [0]}]}}, {"id": 2, "evidence": {}}]
        predictions = [prediction(), {"id": 2, "evidence": {}}]
        with tempfile.TemporaryDirectory() as tmp:
            metrics = r.official(golds, predictions, evaluator, Path(tmp) / "official")
            self.assertEqual(len(metrics), 12)
            self.assertTrue(all(value == 1 for value in metrics.values()))
            self.assertEqual((Path(tmp) / "official/eval.py").read_bytes(), evaluator)

    def test_reconstruction_imports_no_project_or_producer_helpers(self):
        tree = ast.parse(Path(__file__).with_name("reconstruct.py").read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.extend(n.name for n in node.names)
            if isinstance(node, ast.ImportFrom): imports.append(node.module)
        self.assertTrue(set(imports) <= {"__future__", "argparse", "collections", "datetime", "hashlib", "io", "json", "math", "pathlib", "subprocess", "sys", "tarfile", "unicodedata"})

    def test_source_components_and_reference_strata_are_independent(self):
        train = {10: {"id": 10, "claim": "Fictional shared source", "cited_doc_ids": [17], "evidence": {}},
                 11: {"id": 11, "claim": " EXACT   claim ", "cited_doc_ids": [99], "evidence": {}}}
        dev = {1: {"id": 1, "claim": "Different words", "cited_doc_ids": [17, 17],
                   "evidence": {"17": [{"label": "SUPPORT", "sentences": [0]}]}},
               2: {"id": 2, "claim": "exact claim", "cited_doc_ids": [], "evidence": {}}}
        first, second = r.digest([1, 10]), r.digest([2, 11])
        split = {"group_by_claim": {"1": first, "10": first, "2": second, "11": second},
                 "groups": [{"group_id": first, "claim_ids": [1, 10]}, {"group_id": second, "claim_ids": [2, 11]}]}
        rows = r.aggregate([1, 2], list(dev.values()), [disposition(1, prediction()), disposition(2, None, failure="timeout")], corpus())
        result = r.component_strata({"train": train, "dev": dev}, list(dev.values()), rows["case_results"], split)
        self.assertEqual(result["by_native_reference_status"]["SUPPORT"]["strict_correct_and_admitted"], 1)
        self.assertEqual(result["by_native_reference_status"]["NEI"]["strict_correct_and_admitted"], 0)
        self.assertEqual(result["per_case"][1]["source_component_id"], second)
        self.assertEqual(result["per_case"][0]["cited_document_ids"], [17, 17])
        split["group_by_claim"]["2"] = first
        with self.assertRaises(r.AuditError): r.component_strata({"train": train, "dev": dev}, list(dev.values()), rows["case_results"], split)

    def test_retrieval_coverage_keeps_missed_gold_and_nei_denominators_distinct(self):
        references = [{"id": 1, "evidence": {"17": [{"label": "SUPPORT", "sentences": [0]}],
                                               "18": [{"label": "SUPPORT", "sentences": [1]}]}},
                      {"id": 2, "evidence": {}}]
        result = r.retrieval_coverage(references, {1: [17, 99], 2: [17]})
        self.assertEqual(result["annotated_claim_document_pairs"], 2)
        self.assertEqual(result["retrieved_annotated_claim_document_pairs"], 1)
        self.assertEqual(result["annotated_pair_recall"], .5)
        self.assertEqual(result["nonempty_gold_claims"], 1)
        self.assertEqual(result["complete_gold_claim_recall"], 0)
        self.assertIsNone(result["per_case"][1]["annotated_pair_recall"])
        self.assertIsNone(result["per_case"][1]["complete_gold_set_retrieved"])
        empty = r.retrieval_coverage([references[1]], {2: []})
        self.assertIsNone(empty["annotated_pair_recall"])
        self.assertIsNone(empty["complete_gold_claim_recall"])
        with self.assertRaises(r.AuditError): r.retrieval_coverage(references, {1: [17]})


if __name__ == "__main__": unittest.main(verbosity=2)
