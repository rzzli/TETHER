"""Fictional generation orchestration; no model, benchmark answers or source HTTP."""
import copy
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest import TestCase,main
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))

from asof.journal import RunJournal
from asof.serde import ContractError,canonical,encode,fingerprint,freeze,parse_json
from experiments.labbench import run as r
from experiments.labbench.tests import test_model as fixtures
from experiments.labbench.tether_adapter import CapturedContext


class RunTests(TestCase):
    def setUp(self):
        self.fixture=fixtures.ModelTests("runTest");self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root/"run";self.parent=RunJournal(self.root,kind="build")
        self.addCleanup(self.parent.close)
        self.worker=RunJournal(self.root/"worker",kind="build");self.addCleanup(self.worker.close)
        self.query=self.fixture.request["query"]
        self.collection=self.fixture.root/"collection";self.collection.mkdir()
        r.write(self.collection/"sources.json",self.fixture.request["sources"])
        self.case=dict(id=self.query["id"],ordinal=0,query_sha256=fingerprint(self.query),status="completed",
                       retrieval=dict(path="retrieval",manifest_sha256="a"*64),
                       task_sources=r.proof(self.collection/"sources.json",self.collection))
        report=dict(request_sha256=fingerprint(self.fixture.request),query_sha256=fingerprint(self.query),
                    sources_sha256=fingerprint(self.fixture.request["sources"]))
        self.context=CapturedContext(self.query,self.fixture.request["sources"],(),self.fixture.request,report)
        self.case_root=self.root/"worker/cases/000"

    def execute_case(self,body=None,*,case=None,context=None):
        responses=[fixtures.Response(canonical(dict(tokens=list(range(50))))),
                   fixtures.Response(self.fixture.native_body() if body is None else body)]
        calls=self.fixture.calls
        with patch.object(r,"capture_context",return_value=context or self.context), \
             patch.object(r.model.http.client,"HTTPConnection",side_effect=lambda *a,**k:fixtures.Connection(responses.pop(0),calls)), \
             patch.object(r.model.native,"_watchdog",return_value=fixtures.Timer()):
            return r.run_case(self.query,self.case if case is None else case,ordinal=0,collection_root=self.collection,
                 cutoff="2026-11-06T00:00:00+00:00",owner=self.fixture.owner,model_provenance=self.fixture.model,
                 configuration=self.fixture.request["configuration"],alias="fictional-mcq",output=self.case_root,
                 journal=self.worker,deadline=time.monotonic()+200,limits=r.DEFAULT_LIMITS)

    def query2(self):
        query=encode(self.query);query["id"]="00000000-0000-0000-0000-000000000002"
        return freeze(query)

    def seal_partial(self,queries):
        self.worker.close()
        r.write(self.root/"queries.json",queries)
        recipe=dict(mode="fictional",expected_count=len(queries),collection=dict(path=str(self.collection),manifest_sha256="a"*64),
                    model_receipt=dict(path=str(self.fixture.receipt),sha256=r.sha(self.fixture.receipt.read_bytes())),
                    configuration=self.fixture.request["configuration"],limits=r.DEFAULT_LIMITS,alias="fictional-mcq",
                    code_pins=r.source_pins(),queries=r.proof(self.root/"queries.json"))
        r.write(self.root/"recipe.json",recipe)
        r._seal(self.root,recipe,queries,self.parent,failure_reason="fictional stopped worker",
                parent_resources={},supervision=None)
        return r.sha((self.root/"SEALED.json").read_bytes())

    def test_one_native_candidate_same_bytes_policy_and_accounting(self):
        record,stop=self.execute_case()
        self.assertFalse(stop)
        self.assertEqual(record["disposition"]["producer_status"],"produced")
        self.assertEqual(record["disposition"]["check_status"],"accepted")
        self.assertEqual(record["accounting"]["generation_attempts"],1)
        self.assertEqual(record["accounting"]["tokenizer_attempts"],1)
        self.assertEqual(record["accounting"]["measured_usage"]["input_tokens"],50)
        candidate=parse_json((self.case_root/"candidate.json").read_bytes())
        session=parse_json((self.case_root/"session/response.json").read_bytes())
        decision=parse_json((self.case_root/"decision.json").read_bytes())
        self.assertEqual(candidate,session)
        self.assertEqual(candidate,decision["prediction"])
        self.assertEqual(len(self.fixture.calls),2)
        digest=self.seal_partial([self.query,self.query2()])
        manifest=r.verify_generation(self.root,digest)
        self.assertEqual(manifest["totals"]["scheduled"],2)
        self.assertEqual(manifest["totals"]["producer_statuses"],{"produced":1,"unexecuted":1})

    def test_completed_malformed_reply_is_parse_failure_without_retry(self):
        record,stop=self.execute_case(self.fixture.native_body(content='{"answer_index":true,"evidence_ids":[]}'))
        self.assertFalse(stop)
        self.assertEqual(record["disposition"]["producer_status"],"parse_failure")
        self.assertIsNone(record["disposition"]["prediction"])
        self.assertEqual(record["accounting"]["generation_attempts"],1)
        self.assertEqual(len(self.fixture.calls),2)

    def test_source_failure_never_calls_model(self):
        case=dict(self.case,status="failed",reason="fictional unavailable original")
        record,stop=self.execute_case(case=case)
        self.assertFalse(stop)
        self.assertEqual(record["disposition"]["producer_status"],"input_unavailable")
        self.assertEqual(record["accounting"]["generation_attempts"],0)
        self.assertFalse(self.fixture.calls)

    def test_input_source_packet_substitution_fails_before_call(self):
        sources=encode(self.fixture.request["sources"]);sources[0]["text"]="changed"
        (self.collection/"sources.json").write_bytes(canonical(sources))
        record,stop=self.execute_case()
        self.assertEqual(record["disposition"]["producer_status"],"input_unavailable")
        self.assertFalse(self.fixture.calls)

    def test_interrupt_after_dispatch_accounts_conservatively_and_stops(self):
        responses=[fixtures.Response(canonical(dict(tokens=list(range(50))))),fixtures.Response(b"partial",interrupt=True)]
        with patch.object(r,"capture_context",return_value=self.context), \
             patch.object(r.model.http.client,"HTTPConnection",side_effect=lambda *a,**k:fixtures.Connection(responses.pop(0),self.fixture.calls)), \
             patch.object(r.model.native,"_watchdog",return_value=fixtures.Timer()):
            record,stop=r.run_case(self.query,self.case,ordinal=0,collection_root=self.collection,
                 cutoff="2026-11-06T00:00:00+00:00",owner=self.fixture.owner,model_provenance=self.fixture.model,
                 configuration=self.fixture.request["configuration"],alias="fictional-mcq",output=self.case_root,
                 journal=self.worker,deadline=time.monotonic()+200,limits=r.DEFAULT_LIMITS)
        self.assertTrue(stop)
        self.assertEqual(record["disposition"]["producer_status"],"interrupted")
        self.assertEqual(record["accounting"]["generation_attempts"],1)
        self.assertGreater(record["accounting"]["estimated_usage"]["input_tokens"],0)
        digest=self.seal_partial([self.query,self.query2()])
        manifest=r.verify_generation(self.root,digest)
        self.assertEqual(manifest["totals"]["generation_attempts"],1)
        self.assertEqual(manifest["totals"]["producer_statuses"],{"interrupted":1,"unexecuted":1})

    def test_exclusive_case_output_cannot_repeat_dispatch(self):
        self.execute_case()
        original=(self.case_root/"candidate.json").read_bytes()
        with self.assertRaises(FileExistsError):self.execute_case()
        self.assertEqual((self.case_root/"candidate.json").read_bytes(),original)
        self.assertEqual(len(self.fixture.calls),2)

    def test_parent_recovery_preserves_unresolved_dispatch_and_all_schedule(self):
        self.case_root.mkdir(parents=True)
        self.worker.append("case_reserved",id=self.query["id"],ordinal=0,path="000")
        session=RunJournal(self.case_root/"session",kind="build")
        session.append("study_dispatch",attempt_id="cell",request_sha256="a"*64,payload_sha256="b"*64,
                       reserved=dict(input_tokens=1000,output_tokens=256,cost_usd=0.0));session.close()
        rows=r.recover_cases(self.root,[self.query,self.query2()],failure_reason="forced timeout")
        self.assertEqual(len(rows),2)
        self.assertTrue(rows[0]["accounting"]["unresolved_generation"])
        self.assertEqual(rows[0]["accounting"]["estimated_usage"]["input_tokens"],1000)
        self.assertEqual(rows[1]["disposition"]["producer_status"],"unexecuted")

    def test_duplicate_or_unreserved_dispatch_is_rejected(self):
        self.case_root.mkdir(parents=True)
        session=RunJournal(self.case_root/"session",kind="build")
        session.append("study_dispatch",reserved=dict(input_tokens=1000,output_tokens=256,cost_usd=0.0));session.close()
        with self.assertRaises(ContractError):r.recover_cases(self.root,[self.query])

    def test_self_consistent_inventory_cannot_hide_changed_disposition(self):
        self.execute_case();self.seal_partial([self.query])
        path=self.root/"dispositions.json"
        rows=parse_json(path.read_bytes());rows[0]["prediction"]["answer_index"]=2
        path.write_bytes(canonical(rows)+b"\n")
        manifest=parse_json((self.root/"manifest.json").read_bytes())
        manifest["dispositions"]=r.proof(path,self.root)
        (self.root/"manifest.json").write_bytes(canonical(manifest)+b"\n")
        seal=parse_json((self.root/"SEALED.json").read_bytes())
        seal["manifest_sha256"]=r.sha((self.root/"manifest.json").read_bytes())
        seal["outputs"]=r._inventory(self.root,r.DEFAULT_LIMITS["maximum_output_bytes"])
        (self.root/"SEALED.json").write_bytes(canonical(seal)+b"\n")
        with self.assertRaises(ContractError):r.verify_generation(self.root,r.sha((self.root/"SEALED.json").read_bytes()))

    def test_worker_reuses_one_owned_server_for_two_distinct_cells(self):
        queries=[self.query,self.query2()]
        cases=[dict(self.case,id=q["id"],ordinal=i,query_sha256=fingerprint(q)) for i,q in enumerate(queries)]
        collection=dict(cases=cases,cutoff="2026-11-06T00:00:00+00:00",outputs={"sources.json":{}},status="completed")
        limits=encode(r.DEFAULT_LIMITS);limits["port"]=55598
        recipe=dict(code_pins={"fictional":"frozen"},limits=limits,configuration=self.fixture.request["configuration"],
            worker_import_cache=str(self.fixture.root/"cache"),model_receipt=dict(path=str(self.fixture.receipt),sha256=r.sha(self.fixture.receipt.read_bytes())),
            queries=dict(path=str(self.collection/"queries.json")),collection=dict(path=str(self.collection)),alias="fictional-mcq")
        recipe_path=self.root/"worker-recipe.json";r.write(recipe_path,recipe)
        enters=[];calls=[]
        fixture=self.fixture
        class Owner:
            spec=fixture.spec;bindings=fixture.bindings
            terminal_record={"pid":12345,"server_stopped":False}
            def assert_ready(self):pass
            def __enter__(self):enters.append(True);return self
            def __exit__(self,*unused):self.terminal_record["server_stopped"]=True
        class Sampler:
            values=[]
            def __enter__(self):return self
            def __exit__(self,*unused):pass
        class DynamicConnection(fixtures.Connection):
            def __init__(self,*args,**kwargs):super().__init__(None,calls)
            def request(self,method,path,**kwargs):
                super().request(method,path,**kwargs)
                payload=parse_json(kwargs["body"])
                self.response=fixtures.Response(canonical(dict(tokens=list(range(50)))) if path=="/tokenize" else
                    fixture.native_body(prompt=payload["prompt"],generation_settings=payload))
        def context(query,*args,**kwargs):
            request,_=r.model.make_request(query,fixture.request["sources"],fixture.model,fixture.request["configuration"])
            report=dict(request_sha256=fingerprint(request),query_sha256=fingerprint(query),sources_sha256=fingerprint(fixture.request["sources"]))
            return CapturedContext(query,fixture.request["sources"],(),request,report)
        audit=SimpleNamespace(activate=lambda:None,flush=lambda:None,opens=1,denials=0)
        out=self.root/"loop-worker"
        with patch.object(r,"source_pins",return_value=recipe["code_pins"]), \
             patch.object(r,"empty_import_cache",return_value=self.fixture.root/"cache"), \
             patch.object(r,"contain_process_tree",return_value=123), \
             patch.object(r,"_load_inputs",return_value=(queries,collection)), \
             patch.object(r,"InputAudit",return_value=audit), \
             patch.object(r.model,"owned_server",return_value=Owner()), \
             patch.object(r,"ProcessSamples",return_value=Sampler()), \
             patch.object(r,"capture_context",side_effect=context), \
             patch.object(r.model.http.client,"HTTPConnection",side_effect=DynamicConnection), \
             patch.object(r.model.native,"_watchdog",return_value=fixtures.Timer()):
            r._worker(recipe_path,r.sha(recipe_path.read_bytes()),out)
        self.assertEqual(len(enters),1)
        self.assertEqual([item["path"] for item in calls],["/tokenize","/completion","/tokenize","/completion"])
        terminal=parse_json((out/"TERMINAL.json").read_bytes())
        self.assertEqual(terminal["status"],"completed")
        self.assertEqual(terminal["cleanup"],"normal_verified")
        for i in range(2):
            self.assertTrue((out/f"cases/{i:03d}/session/receipt.json").is_file())
            self.assertEqual(parse_json((out/f"cases/{i:03d}/status.json").read_bytes())["disposition"]["producer_status"],"produced")


if __name__=="__main__":main()
