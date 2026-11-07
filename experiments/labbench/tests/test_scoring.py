"""Invented native MCQ cases; no benchmark answer rows are opened."""
import unittest

from tether_engine.serde import ContractError
from experiments.labbench.native_contract import parse_prediction, validate_prediction, validate_query
from experiments.labbench.evaluate import evaluate_schedule, source_annotation_metrics


def key(n): return f"00000000-0000-4000-8000-{n:012d}"
def query(n=1): return {"id": key(n), "question": "Which fictional result was observed?",
                       "choices": ["(A) blue", "(B) green", "(C) Insufficient information to answer the question"]}
def prediction(index=0, ids=None): return {"answer_index": index, "evidence_ids": ["PMC17:p0001"] if ids is None else ids}


class NativeTests(unittest.TestCase):
    def test_native_shape_bounds_and_bool(self):
        self.assertEqual(validate_prediction(prediction(), query(), ["PMC17:p0001"])["answer_index"], 0)
        for value in [None, prediction(True), prediction(-1), prediction(3), prediction(ids=["unknown"]),
                      prediction(ids=["PMC17:p0001", "PMC17:p0001"]), dict(prediction(), hidden=True)]:
            with self.subTest(value=value), self.assertRaises(ContractError):
                validate_prediction(value, query(), ["PMC17:p0001"])

    def test_empty_evidence_is_structurally_valid_not_native_failure(self):
        self.assertEqual(validate_prediction(prediction(2, []), query(), [])["evidence_ids"], ())
        self.assertEqual(validate_prediction(prediction(0, []), query(), [])["answer_index"], 0)

    def test_strict_json_and_deep_immutable_copy(self):
        for raw in [b'{"answer_index":0,"answer_index":1,"evidence_ids":[]}', b'{"answer_index":NaN,"evidence_ids":[]}']:
            with self.assertRaises(ContractError): parse_prediction(raw, query(), [])
        mutable = prediction()
        frozen = validate_prediction(mutable, query(), ["PMC17:p0001"])
        mutable["evidence_ids"].append("changed")
        self.assertEqual(frozen["evidence_ids"], ("PMC17:p0001",))
        with self.assertRaises(TypeError): frozen["answer_index"] = 2

    def test_query_has_no_reference_fields_and_exact_labels(self):
        for value in [dict(query(), answer_index=0), dict(query(), id="not-a-uuid"),
                      dict(query(), choices=["(A) blue", "(A) green"])]:
            with self.subTest(value=value), self.assertRaises(ContractError): validate_query(value)

    def test_native_duplicate_distractor_text_preserves_indexed_slots(self):
        q=query()
        q["choices"]=["(A) blue","(B) green","(C) green","(D) Insufficient information to answer the question"]
        frozen=validate_query(q)
        self.assertEqual(len(frozen["choices"]),4)
        for index in (1,2):
            self.assertEqual(validate_prediction(prediction(index,[]),q,[])["answer_index"],index)
        q["choices"][2]="(C) Insufficient information to answer the question"
        with self.assertRaises(ContractError): validate_query(q)


class ScoringTests(unittest.TestCase):
    def fixtures(self):
        queries = [query(i) for i in range(1, 7)]
        references = [{"id": key(i), "answer_index": 0, "unsure_index": 2} for i in range(1, 7)]
        outcomes = [(0,"accepted",None),(1,"accepted",None),(0,"rejected","no source"),
                    (2,"accepted",None),(None,"not_run","timeout"),(2,"rejected","future source")]
        records = [{"id": key(i), "producer_status": "timeout" if index is None else "produced", "check_status": status,
                    "prediction": None if index is None else prediction(index), "reason": reason}
                   for i,(index,status,reason) in enumerate(outcomes,1)]
        sources = {key(i): ["PMC17:p0001"] for i in range(1,7)}
        return queries,references,records,sources

    def test_native_metrics_all_schedule_and_failure_vs_unsure(self):
        queries,refs,records,sources = self.fixtures()
        value = evaluate_schedule(queries,refs,records,evidence_ids_by_query=sources)
        self.assertEqual(value["scheduled_count"],6)
        self.assertEqual(dict(value["raw_metrics"]),{"accuracy":2/6,"precision":2/3,"coverage":3/6})
        self.assertEqual(dict(value["checked_metrics"]),{"accuracy":1/6,"precision":1/2,"coverage":2/6})
        self.assertEqual(value["counts"]["correct_but_rejected"],1)
        self.assertEqual(value["counts"]["native_unsure"],2)
        self.assertEqual(value["counts"]["producer_failures"],1)
        self.assertEqual(value["counts"]["incorrect_and_admitted"],2)
        self.assertEqual(value["counts"]["incorrect_substantive_and_admitted"],1)
        self.assertIsNone(value["case_results"][4]["native_unsure"])
        self.assertFalse(value["case_results"][3]["raw_correct"])

    def test_missing_duplicate_and_reordered_cases_fail(self):
        q,g,r,s = self.fixtures()
        for altered in [r[:-1],r[::-1],r[:-1]+[r[0]]]:
            with self.assertRaises(ContractError): evaluate_schedule(q,g,altered,evidence_ids_by_query=s)
        with self.assertRaises(ContractError): evaluate_schedule([],[],[],evidence_ids_by_query={})

    def test_reference_errors_and_claimed_success_on_failure_fail(self):
        q,g,r,s = self.fixtures()
        g[0]["unsure_index"] = 0
        with self.assertRaises(ContractError): evaluate_schedule(q,g,r,evidence_ids_by_query=s)
        q,g,r,s = self.fixtures(); r[4]["prediction"] = prediction()
        with self.assertRaises(ContractError): evaluate_schedule(q,g,r,evidence_ids_by_query=s)

    def test_all_unsure_precision_convention_is_explicit(self):
        q,g,r,s = self.fixtures()
        for row in r: row.update(producer_status="produced",check_status="accepted",prediction=prediction(2,[]),reason=None)
        value=evaluate_schedule(q,g,r,evidence_ids_by_query=s)
        self.assertEqual(value["raw_metrics"]["precision"],0)
        self.assertEqual(value["counts"]["raw_answered"],0)
        self.assertFalse(value["raw_precision_defined"])

    def test_literal_null_ideal_retains_original_native_semantics(self):
        q=query();q["choices"][0]="(A) null"
        refs=[{"id":q["id"],"answer_index":0,"unsure_index":2}]
        for choice,correct in ((0,True),(2,False)):
            row={"id":q["id"],"producer_status":"produced","check_status":"accepted",
                 "prediction":prediction(choice,[]),"reason":None}
            result=evaluate_schedule([q],refs,[row],evidence_ids_by_query={q["id"]:[]})
            self.assertEqual(result["case_results"][0]["raw_correct"],correct)

    def test_each_operational_failure_is_not_native_unsure(self):
        for status in ("parse_failure","timeout","error","interrupted","unexecuted","input_unavailable"):
            q=query(); row={"id":q["id"],"producer_status":status,"check_status":"not_run","prediction":None,"reason":status}
            value=evaluate_schedule([q],[{"id":q["id"],"answer_index":0,"unsure_index":2}],[row],
                                    evidence_ids_by_query={q["id"]:[]})
            self.assertEqual(value["counts"]["producer_failures"],1)
            self.assertEqual(value["counts"]["native_unsure"],0)
            self.assertEqual(value["raw_metrics"]["coverage"],0)

    def test_parsefailure_projection_and_all_nonadmission_loss_explicit(self):
        q,g,r,s=self.fixtures()
        r[4]["producer_status"]="parse_failure"
        r[2]["check_status"]="error"
        value=evaluate_schedule(q,g,r,evidence_ids_by_query=s)
        self.assertEqual(value["counts"]["parse_failures"],1)
        self.assertEqual(value["counts"]["produced_or_parse_failure"],6)
        self.assertEqual(value["counts"]["correct_not_admitted"],1)
        self.assertEqual(value["counts"]["correct_but_rejected"],0)
        self.assertEqual(value["raw_metrics"]["precision"],2/3)
        # Original arbitrary non-unsure malformed-string scoring would use
        # 2/4 here; our operational failure projection is a declared difference.
        self.assertNotEqual(value["raw_metrics"]["precision"],2/4)
        self.assertIn("strict JSON",value["metric_conventions"]["upstream_difference"])

    def test_source_identity_hit_is_not_semantic_support(self):
        schedule=[key(1),key(2)]
        value=source_annotation_metrics(schedule,{key(1):["doi:a","doi:b"],key(2):[]},
                                        {key(1):["doi:a","doi:other"],key(2):["doi:z"]})
        self.assertEqual(value["annotated_source_recall"],.5)
        self.assertEqual(value["questions_with_any_annotated_source_hit"],1)
        self.assertIsNone(value["case_results"][1]["annotated_source_recall"])
        self.assertEqual(value["semantic_support"],"unevaluated")


if __name__ == "__main__": unittest.main(verbosity=2)
