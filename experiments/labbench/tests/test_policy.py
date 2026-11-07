"""Fictional downloaded bodies only: no real LitQA2 questions or answer keys."""
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, canonical, encode
from experiments.labbench import retrieval
from experiments.labbench.tether_adapter import capture_context, verify_candidate, DEFAULT_CATALOG

QUERY = {"id":"00000000-0000-4000-8000-000000000001", "question":"Which fictional blue result was observed?",
         "choices":["(A) blue", "(B) green", "(C) Insufficient information to answer the question"]}
MODEL = {"weights_sha256":{"fictional.gguf":"1"*64}, "runtime_sha256":"2"*64,
         "asset_manifest_sha256":"3"*64,"model_id":"fictional","revision":"fictional-v1"}
XML = b'''<article><front><article-meta><article-id pub-id-type="pmc">17</article-id><permissions>
<license><p>Creative Commons Attribution License</p></license></permissions></article-meta></front>
<abstract><p>Fictional blue result was observed.</p></abstract><body><p>The fictional green condition failed.</p></body></article>'''


def fake_fetch(url, **kwargs):
    if url.endswith("fullTextXML"):
        body=XML
    else:
        body=canonical({"resultList":{"result":[{"pmcid":"PMC17","license":"cc by","isOpenAccess":"Y",
            "firstPublicationDate":"2020-01-01","title":"Fictional result","doi":"10.000/fictional"}]}})
    return {"status":200,"body":body,"final_url":url,"headers":{}}


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/"source"
        with patch.object(retrieval,"fetch_http",fake_fetch):
            self.manifest=retrieval.retrieve(QUERY["question"],self.root)
        self.sha=hashlib.sha256((self.root/"manifest.json").read_bytes()).hexdigest()
        self.cutoff=datetime.now(timezone.utc)

    def tearDown(self): self.temp.cleanup()

    def context(self, **kw):
        return capture_context(QUERY,self.root,self.sha,kw.pop("cutoff",self.cutoff),MODEL,**kw)

    def test_real_core_lineage_and_source_binding(self):
        context=self.context()
        self.assertEqual(context.report["policy_kind"],"labbench_native_source_backed_v1")
        self.assertTrue(context.report["input_proofs"])
        self.assertTrue(context.report["snapshot"]["sources"])
        self.assertEqual(context.report["semantic_support"],"unevaluated")
        candidate={"answer_index":0,"evidence_ids":[context.sources[0]["source_id"]]}
        self.assertTrue(verify_candidate(context,context.request,candidate)["accepted"])
        # Native correctness is deliberately not part of the admission boundary.
        candidate["answer_index"]=1
        self.assertTrue(verify_candidate(context,context.request,candidate)["accepted"])

    def test_empty_source_substantive_rejected_unsure_admitted(self):
        context=self.context()
        self.assertFalse(verify_candidate(context,context.request,{"answer_index":0,"evidence_ids":[]})["accepted"])
        self.assertTrue(verify_candidate(context,context.request,{"answer_index":2,"evidence_ids":[]})["accepted"])

    def test_context_is_deeply_copied_and_frozen(self):
        context=self.context()
        with self.assertRaises(TypeError): context.sources[0]["text"]="replace"
        with self.assertRaises(TypeError): context.request["query"]["question"]="replace"
        with self.assertRaises(TypeError): context.report["snapshot"]["sources"][0]["role"]="evaluation_only"

    def test_substituted_request_and_duplicate_citation_rejected(self):
        context=self.context()
        altered=encode(context.request); altered["query"]["question"]="Changed question"
        selected=context.sources[0]["source_id"]
        self.assertFalse(verify_candidate(context,altered,{"answer_index":0,"evidence_ids":[selected]})["accepted"])
        self.assertFalse(verify_candidate(context,context.request,{"answer_index":0,"evidence_ids":[selected,selected]})["accepted"])

    def test_original_byte_change_blocks_capture(self):
        original=self.root/self.manifest["sources"][0]["original"]["path"]
        original.write_bytes(XML+b" ")
        with self.assertRaises(ContractError): self.context()

    def test_evaluator_only_parent_blocks_capture(self):
        catalog=encode(DEFAULT_CATALOG)
        catalog["datasets"][0]["roles"].append("evaluation_only")
        with self.assertRaises(ContractError): self.context(catalog=catalog)

    def test_future_receipt_blocks_all_input_admission(self):
        with self.assertRaises(ContractError): self.context(cutoff=datetime(2020,1,1,tzinfo=timezone.utc))

    def test_no_retained_source_context_admits_only_unsure(self):
        root=Path(self.temp.name)/"empty-source"
        def empty_fetch(url,**kw):
            return {"status":200,"body":canonical({"resultList":{"result":[]}}),"final_url":url,"headers":{}}
        with patch.object(retrieval,"fetch_http",empty_fetch): retrieval.retrieve(QUERY["question"],root)
        sha=hashlib.sha256((root/"manifest.json").read_bytes()).hexdigest()
        context=capture_context(QUERY,root,sha,datetime.now(timezone.utc),MODEL)
        self.assertTrue(context.report["no_sources"])
        self.assertEqual(context.sources,())
        self.assertTrue(verify_candidate(context,context.request,{"answer_index":2,"evidence_ids":[]})["accepted"])
        self.assertFalse(verify_candidate(context,context.request,{"answer_index":0,"evidence_ids":[]})["accepted"])

    def test_unknown_publication_does_not_become_historical_date(self):
        root=Path(self.temp.name)/"unknown-date"
        def unknown_fetch(url,**kw):
            value=fake_fetch(url,**kw)
            if not url.endswith("fullTextXML"):
                from tether_engine.serde import parse_json
                body=parse_json(value["body"]);body["resultList"]["result"][0]["firstPublicationDate"]=None
                value["body"]=canonical(body)
            return value
        with patch.object(retrieval,"fetch_http",unknown_fetch): retrieval.retrieve(QUERY["question"],root)
        sha=hashlib.sha256((root/"manifest.json").read_bytes()).hexdigest()
        context=capture_context(QUERY,root,sha,datetime.now(timezone.utc),MODEL)
        entry=context.report["publication_dates"]["PMC17"]
        self.assertIsNone(entry["reported_date"])
        self.assertTrue(entry["unknown_reason"])

    def test_decision_has_durable_generic_hash_chained_record(self):
        context=self.context()
        journal=RunJournal(Path(self.temp.name)/"check")
        try:
            decision=verify_candidate(context,context.request,{"answer_index":2,"evidence_ids":[]},journal=journal)
        finally: journal.close()
        event=read_chain(journal.path)[-1]
        self.assertEqual(event["event"],"labbench_candidate_checked")
        self.assertEqual(event["details"]["decision"],decision)


if __name__ == "__main__": unittest.main(verbosity=2)
