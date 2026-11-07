"""Fictional native-policy controls; no scientific benchmark answers are read."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import json
import copy
import platform
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, fingerprint
from experiments.scifact.tether_adapter import (
    admit_container, reverify_container, validate_resources,
    NativeSession, inspect_session, verify_session, authorize_products,
    build_context, make_request, verify_candidate, reverify_context,
    _validate_model,
)


NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)


class ContainerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive = self.root / "original.tar.gz"
        self.archive.write_bytes(b"fictional original container")
        self.receipt = self.root / "transport.json"
        self.transport = {"status": "downloaded_not_parsed", "url": "https://example.test/data.tar.gz",
                          "path": str(self.archive), "bytes": self.archive.stat().st_size,
                          "sha256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                          "finished_at_utc": NOW.isoformat(), "http_status": 200}
        self.receipt.write_bytes(canonical(self.transport))
        self.original = self.receipt.read_bytes()

    def tearDown(self):
        self.temp.cleanup()

    def admit(self, **kw):
        return admit_container(self.archive, self.receipt, self.root / "normalized.json",
                               workspace_root=self.root, cutoff=kw.pop("cutoff", NOW),
                               expected_archive_sha256=self.transport["sha256"],
                               expected_receipt_sha256=hashlib.sha256(self.original).hexdigest(), **kw)

    def test_original_event_is_admitted_without_rewriting_transport(self):
        proof = self.admit()
        self.assertEqual(self.receipt.read_bytes(), self.original)
        self.assertEqual(proof["allowed_purpose"], "preparation")
        self.assertEqual(reverify_container(proof, self.root)["status"], "verified")

    def test_future_original_rejected(self):
        with self.assertRaisesRegex(ContractError, "after_origin"):
            self.admit(cutoff=NOW-timedelta(seconds=1))

    def test_receipt_change_rejected(self):
        self.receipt.write_bytes(self.original+b" ")
        with self.assertRaisesRegex(ContractError, "receipt"):
            self.admit()

    def test_archive_change_rejected(self):
        self.archive.write_bytes(b"altered")
        with self.assertRaisesRegex(ContractError, "archive"):
            self.admit()

    def test_normalized_receipt_tamper_rejected(self):
        proof=self.admit()
        (self.root/"normalized.json").write_bytes(b"{}")
        with self.assertRaises(ContractError): reverify_container(proof,self.root)

    def test_normalization_cannot_clobber_original(self):
        with self.assertRaises((ContractError,FileExistsError)):
            admit_container(self.archive,self.receipt,self.receipt,workspace_root=self.root,
                            cutoff=NOW,expected_archive_sha256=self.transport["sha256"],
                            expected_receipt_sha256=hashlib.sha256(self.original).hexdigest())
        self.assertEqual(self.receipt.read_bytes(),self.original)


def resources(**updates):
    result=dict(wall_seconds=.1,cpu_seconds=.05,peak_memory_bytes=10000,
                memory_method="fictional_measurement",input_bytes=10,output_bytes=20,examples=1,
                model_input_tokens=None,model_output_tokens=None,tokenizer_identity=None,
                provider_usage=None,token_usage_reason="not_applicable_non_llm",provider_cost_usd=0)
    result.update(updates)
    return result


class NativeSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_resources_do_not_invent_llm_usage(self):
        value=validate_resources(resources())
        self.assertIsNone(value["model_input_tokens"])
        for field,bad in (("model_input_tokens",0),("provider_cost_usd",1),
                          ("wall_seconds",float("nan")),("examples",True)):
            with self.subTest(field=field),self.assertRaises(ContractError):
                validate_resources(resources(**{field:bad}))

    def test_complete_schedule_reconciles(self):
        with NativeSession(self.root/"run",["c1","c2"],{"study":"fictional"}) as session:
            for cell in ["c1","c2"]:
                session.begin(cell,{"cell":cell})
                session.finish(cell,{"value":1},resources())
            receipt=session.finalize()
        result=verify_session(self.root/"run",expected_receipt_sha256=receipt["sha256"])
        self.assertEqual(result["terminal_cells"],2)
        self.assertEqual(result["totals"]["examples"],2)

    def test_reservation_is_exclusive(self):
        with NativeSession(self.root/"run",["c1"],{}) as session:
            with self.assertRaises(FileExistsError):NativeSession(self.root/"run",["c1"],{})
        self.assertEqual(inspect_session(self.root/"run")["terminal_cells"],0)

    def test_duplicate_schedule_rejected_before_reservation(self):
        with self.assertRaises(ContractError):NativeSession(self.root/"run",["c1","c1"],{})
        self.assertFalse((self.root/"run").exists())

    def test_missing_case_cannot_finalize(self):
        with NativeSession(self.root/"run",["c1"],{}) as session:
            with self.assertRaises(ContractError):session.finalize()

    def test_duplicate_dispatch_rejected(self):
        with NativeSession(self.root/"run",["c1"],{}) as session:
            session.begin("c1",{})
            session.finish("c1",{},resources())
            with self.assertRaises(ContractError):session.begin("c1",{})

    def test_interruption_preserves_attempt_without_retry(self):
        with self.assertRaises(KeyboardInterrupt):
            with NativeSession(self.root/"run",["c1"],{}) as session:
                session.begin("c1",{})
                raise KeyboardInterrupt()
        state=inspect_session(self.root/"run")
        self.assertEqual(state["attempted_cells"],["c1"])
        self.assertEqual(state["recovery_action"],"inspect only; never automatically retry")
        self.assertEqual(state["last_event"],"native_interrupted")

    def test_write_failure_keeps_attempt_and_disables_later_work(self):
        with NativeSession(self.root/"run",["c1","c2"],{}) as session:
            session.begin("c1",{})
            with patch("experiments.scifact.tether_adapter.publish_bytes",side_effect=OSError("injected")):
                with self.assertRaises(OSError):session.finish("c1",{},resources())
            with self.assertRaises(ContractError):session.begin("c2",{})
        inspection=inspect_session(self.root/"run")
        self.assertEqual(inspection["attempted_cells"],["c1"])
        self.assertEqual(inspection["uncommitted_measured_resources"][0]["resources"]["output_bytes"],20)

    def test_call_budget_denial_keeps_unexecuted_schedule(self):
        with NativeSession(self.root/"run",["c1","c2"],{},max_calls=1) as session:
            session.begin("c1",{});session.finish("c1",{},resources())
            with self.assertRaises(ContractError):session.begin("c2",{})
            session.mark_not_run("c2","call_budget_exhausted");receipt=session.finalize()
        self.assertEqual(verify_session(self.root/"run",expected_receipt_sha256=receipt["sha256"])["terminal_cells"],2)

    def test_budget_breach_retains_resources_and_stops(self):
        with NativeSession(self.root/"run",["c1","c2"],{},max_output_bytes=10) as session:
            session.begin("c1",{})
            record=session.finish("c1",{},resources())
            self.assertEqual(record["status"],"budget_exceeded")
            self.assertEqual(record["resources"]["output_bytes"],20)
            with self.assertRaises(ContractError):session.begin("c2",{})
            session.mark_not_run("c2","prior_budget_exceeded")
            receipt=session.finalize()
        self.assertEqual(verify_session(self.root/"run",expected_receipt_sha256=receipt["sha256"])["terminal_cells"],2)

    def test_resealed_record_disagreeing_with_journal_rejected(self):
        with NativeSession(self.root/"run",["c1"],{}) as session:
            session.begin("c1",{});session.finish("c1",{},resources());session.finalize()
        path=next((self.root/"run"/"cells").glob("*.json"))
        value=json.loads(path.read_bytes());value["resources"]["examples"]=99
        path.write_bytes(canonical(value)+b"\n")
        receiptpath=self.root/"run"/"receipt.json"
        receipt=json.loads(receiptpath.read_bytes())
        receipt["outputs"][path.relative_to(self.root/"run").as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        receiptpath.write_bytes(canonical(receipt)+b"\n")
        with self.assertRaises(ContractError):verify_session(self.root/"run",expected_receipt_sha256=hashlib.sha256(receiptpath.read_bytes()).hexdigest())

    def test_resealed_contradictory_byte_and_time_budgets_rejected(self):
        for field,value in [("max_output_bytes",1),("max_wall_seconds",1e-12)]:
            with self.subTest(field=field):
                output=self.root/field
                with NativeSession(output,["c1"],{}) as session:
                    session.begin("c1",{});session.finish("c1",{},resources());session.finalize()
                lines=[json.loads(x) for x in (output/"journal.jsonl").read_bytes().splitlines()]
                lines[1]["details"]["budgets"][field]=value
                prior=None
                for event in lines:
                    event.pop("sha256");event["previous_sha256"]=prior;event["sha256"]=fingerprint(event);prior=event["sha256"]
                (output/"journal.jsonl").write_bytes(b"".join(canonical(x)+b"\n" for x in lines))
                rp=output/"receipt.json";receipt=json.loads(rp.read_bytes())
                receipt["outputs"]["journal.jsonl"]=hashlib.sha256((output/"journal.jsonl").read_bytes()).hexdigest()
                rp.write_bytes(canonical(receipt)+b"\n")
                with self.assertRaisesRegex(ContractError,"budget"):
                    verify_session(output,expected_receipt_sha256=hashlib.sha256(rp.read_bytes()).hexdigest())

    def test_verifier_rejects_selfconsistent_empty_schedule(self):
        output=self.root/"empty"
        with NativeSession(output,["c1"],{}) as session:
            session.begin("c1",{});session.finish("c1",{},resources());session.finalize()
        events=[json.loads(x) for x in (output/"journal.jsonl").read_bytes().splitlines()]
        events=[events[0],events[1],events[-1]]
        events[1]["details"]["schedule"]=[]
        totals={"wall_seconds":0,"cpu_seconds":0,"input_bytes":0,"output_bytes":0,"examples":0,
                "unknown_measurements":{"wall_seconds":0,"cpu_seconds":0,"input_bytes":0,"output_bytes":0,"examples":0},
                "provider_cost_usd":0,"model_input_tokens":None,"model_output_tokens":None}
        events[-1]["details"]={"terminal_cells":0,"totals":totals}
        prior=None
        for index,event in enumerate(events):
            event.pop("sha256");event["sequence"]=index;event["previous_sha256"]=prior
            event["sha256"]=fingerprint(event);prior=event["sha256"]
        (output/"journal.jsonl").write_bytes(b"".join(canonical(x)+b"\n" for x in events))
        cell=next((output/"cells").glob("*.json"));cell.unlink()
        receipt={"schema_version":1,"kind":"scifact_native_session","schedule":[],"configuration":{},
                 "terminal_cells":0,"totals":totals,"outputs":{"journal.jsonl":hashlib.sha256((output/"journal.jsonl").read_bytes()).hexdigest()}}
        rp=output/"receipt.json";rp.write_bytes(canonical(receipt)+b"\n")
        with self.assertRaisesRegex(ContractError,"schedule"):
            verify_session(output,expected_receipt_sha256=hashlib.sha256(rp.read_bytes()).hexdigest())


class CandidatePolicyTests(unittest.TestCase):
    """Policy-layer tests stub the separately qualified trusted projector only."""
    def setUp(self):
        ContainerTests.setUp(self)
        self.prep=self.root/"prep";self.prep.mkdir();self.modelroot=self.root/"model";self.modelroot.mkdir()
        products={}
        def product(key,rows,kind,purposes,parents):
            raw=b"".join(canonical(row)+b"\n" for row in rows)
            relative=key+".jsonl";(self.prep/relative).write_bytes(raw)
            products[key]={"path":relative,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),
                           "format":"jsonl","kind":kind,"purposes":purposes,"rows":len(rows),
                           "fields":list(rows[0]),"logical_parents":parents}
        product("corpus",[{"doc_id":10,"title":"Fictional","abstract":["First sentence.","Second sentence."]}],
                "public_corpus",["fit","predict"],["member:data/corpus.jsonl:doc_id,title,abstract"])
        product("queries_fit",[{"id":1,"claim":"Fitting question"}],"query_only",["fit"],["member:data/claims_train.jsonl:id,claim","split:membership"])
        product("queries_dev",[{"id":2,"claim":"Evaluation question"}],"query_only",["predict"],["member:data/claims_dev.jsonl:id,claim","split:membership"])
        product("references_fit",[{"id":1,"claim":"Fitting question","evidence":{},"cited_doc_ids":[10]}],
                "fit_supervision",["fit"],["member:data/claims_train.jsonl:id,claim,evidence,cited_doc_ids","split:membership"])
        product("fit_pairs",[{"claim_id":1,"doc_id":10,"label":"NEI"}],"fit_supervision",["fit"],["references_fit"])
        product("references_dev",[{"id":2,"claim":"Evaluation question","evidence":{},"cited_doc_ids":[10]}],
                "evaluation_reference",["evaluate"],["member:data/claims_dev.jsonl:id,claim,evidence,cited_doc_ids","split:membership"])
        self.manifest={"archive":{"path":str(self.archive),"receipt_path":str(self.receipt),
                                  "sha256":self.transport["sha256"],"receipt_sha256":hashlib.sha256(self.original).hexdigest()},"products":products}
        self.asset=self.modelroot/"numeric.json";self.asset.write_bytes(b'{"weights":[0.1]}')
        self.producer=self.root/"producer.py";self.producer.write_bytes(b'# fictional producer, never executed\n')
        self.model={"schema_version":1,"kind":"scifact_model","computed_at":"2027-01-01T00:00:00+00:00",
                    "fit_product_ids":["corpus","queries_fit","fit_pairs"],"index_input_product_ids":["corpus"],
                    "fit_claim_ids":[1],"configuration":{"k":1,"threshold":.5},
                    "files":[{"path":"numeric.json","sha256":hashlib.sha256(self.asset.read_bytes()).hexdigest(),"bytes":self.asset.stat().st_size}],
                    "producer_code":{"path":str(self.producer),"sha256":hashlib.sha256(self.producer.read_bytes()).hexdigest()},
                    "dependency_versions":{"python":platform.python_version()}}
        self.model["preparation_manifest_sha256"]="a"*64
        self.model["input_product_proofs"]={key:{name:products[key][name] for name in ("sha256","bytes")} for key in self.model["fit_product_ids"]}
        consumed={key:{"path":str(self.prep/products[key]["path"]),**proof} for key,proof in self.model["input_product_proofs"].items()}
        with NativeSession(self.root/"fit-execution",["fit"],{}) as session:
            session.begin("fit",{"inputs":consumed})
            session.finish("fit",{"files":self.model["files"]},resources())
            fitreceipt=session.finalize()
        self.model["fit_execution"]={"path":str(self.root/"fit-execution"),"receipt_sha256":fitreceipt["sha256"],"cell_id":"fit"}
        self.model["computed_at"]=datetime.now(timezone.utc).isoformat()
        self.patch=patch("experiments.scifact.data_views.verify_preparation",return_value=self.manifest)
        self.patch.start();self.addCleanup(self.patch.stop)
        self.context=self.build()

    def tearDown(self):ContainerTests.tearDown(self)

    def build(self):
        (self.prep/"manifest.json").write_bytes(canonical(self.manifest)+b"\n")
        self.modelpath=self.modelroot/"model-manifest.json";self.modelpath.write_bytes(canonical(self.model)+b"\n")
        dest=self.root/("proof-"+str(len(list(self.root.glob("proof-*")))))
        return build_context(self.prep,"a"*64,self.modelroot,hashlib.sha256(self.modelpath.read_bytes()).hexdigest(),NOW,dest,workspace_root=self.root)

    def candidate(self,label="SUPPORT"):
        request=make_request(self.context,2,self.model["configuration"])
        prediction={"id":2,"evidence":{"10":{"label":label,"sentences":[0]}}}
        envelope={"request_sha256":fingerprint(request),"prediction_sha256":fingerprint(prediction),
                  "retrieved":[{"doc_id":10,"rank":1,"score":.5,"document_sha256":self.context.document_hashes[10]}],
                  "source_bindings":[{"doc_id":10,"sentence_id":0,"text_sha256":self.context.sentence_hashes[(10,0)]}],
                  "producer_code_sha256":self.model["producer_code"]["sha256"],"resources":resources()}
        return request,prediction,envelope

    def test_new_computation_on_eligible_old_inputs_allowed(self):
        self.assertEqual(reverify_context(self.context).policy_sha256,self.context.policy_sha256)

    def test_source_valid_opposite_labels_are_not_semantically_judged(self):
        for label in ["SUPPORT","CONTRADICT"]:
            self.assertEqual(verify_candidate(self.context,*self.candidate(label))["scientific_validation"],"not_performed")

    def test_nested_accepted_state_immutable(self):
        request,prediction,envelope=self.candidate()
        result=verify_candidate(self.context,request,prediction,envelope)
        prediction["evidence"]["10"]["sentences"][0]=1
        self.assertEqual(result["prediction"]["evidence"]["10"]["sentences"],(0,))
        with self.assertRaises(TypeError):result["envelope"]["resources"]["examples"]=5

    def test_prediction_request_configuration_and_locator_tamper_rejected(self):
        for mode in ["prediction","request","configuration","document","sentence","unretrieved","producer"]:
            with self.subTest(mode=mode):
                request,prediction,envelope=self.candidate();request=dict(request)
                if mode=="prediction":prediction["evidence"]["10"]["label"]="CONTRADICT"
                elif mode=="request":envelope["request_sha256"]="f"*64
                elif mode=="configuration":request["configuration_sha256"]="f"*64;envelope["request_sha256"]=fingerprint(request)
                elif mode=="document":envelope["retrieved"][0]["document_sha256"]="f"*64
                elif mode=="sentence":envelope["source_bindings"][0]["text_sha256"]="f"*64
                elif mode=="unretrieved":envelope["retrieved"]=[]
                else:envelope["producer_code_sha256"]="f"*64
                with self.assertRaises(ContractError):verify_candidate(self.context,request,prediction,envelope)

    def test_evaluator_feature_injection_rejected(self):
        request,prediction,envelope=self.candidate();request=dict(request);request["cited_doc_ids"]=[10]
        envelope["request_sha256"]=fingerprint(request)
        with self.assertRaises(ContractError):verify_candidate(self.context,request,prediction,envelope)

    def test_model_fitting_reference_parent_denied(self):
        self.model["fit_product_ids"].append("references_dev")
        with self.assertRaises(ContractError):self.build()

    def test_transitive_reference_parent_denied_even_if_role_promoted(self):
        self.manifest["products"]["fit_pairs"]["logical_parents"]=["references_dev"]
        self.manifest["products"]["references_dev"]["purposes"].append("fit")
        with self.assertRaisesRegex(ContractError,"Held-out"):
            authorize_products(self.manifest,["fit_pairs"],"fit")

    def test_logical_cycle_rejected(self):
        self.manifest["products"]["fit_pairs"]["logical_parents"]=["fit_pairs"]
        with self.assertRaisesRegex(ContractError,"cycle"):authorize_products(self.manifest,["fit_pairs"],"fit")

    def test_bad_fit_membership_rejected(self):
        self.model["fit_claim_ids"]=[1,2]
        with self.assertRaisesRegex(ContractError,"membership"):self.build()

    def test_same_claim_ids_do_not_substitute_other_fit_label_bytes(self):
        self.manifest["products"]["fit_pairs"]["sha256"]="f"*64
        with self.assertRaisesRegex(ContractError,"input.*proof|parent"):
            _validate_model(self.model,self.modelroot,self.manifest,[{"id":1}])

    def test_changed_fit_receipt_anchor_rejected(self):
        self.model["fit_execution"]["receipt_sha256"]="f"*64
        with self.assertRaisesRegex(ContractError,"anchor"):self.build()

    def test_model_cannot_claim_computation_before_its_fit_attempt(self):
        self.model["computed_at"]="2020-01-01T00:00:00+00:00"
        with self.assertRaisesRegex(ContractError,"predates"):self.build()

    def test_other_numeric_assets_cannot_replace_fitting_outputs(self):
        self.asset.write_bytes(b'{"weights":[0.9]}')
        self.model["files"][0].update(sha256=hashlib.sha256(self.asset.read_bytes()).hexdigest(),bytes=self.asset.stat().st_size)
        with self.assertRaisesRegex(ContractError,"fitting result"):self.build()

    def test_changed_model_or_producer_rejected_on_source_replay(self):
        self.asset.write_bytes(b'{}')
        with self.assertRaisesRegex(ContractError,"asset"):reverify_context(self.context)

    def test_source_inclusive_accepted_session(self):
        request,prediction,envelope=self.candidate()
        result=verify_candidate(self.context,request,prediction,envelope)
        with NativeSession(self.root/"checked",["case-2"],{}) as session:
            session.begin("case-2",request);session.finish("case-2",result,resources(),status="accepted");receipt=session.finalize()
        self.assertEqual(verify_session(self.root/"checked",expected_receipt_sha256=receipt["sha256"],context=self.context)["terminal_cells"],1)
        with self.assertRaises(ContractError):verify_session(self.root/"checked",expected_receipt_sha256=receipt["sha256"])

    def test_journal_dispatch_must_match_accepted_request(self):
        request,prediction,envelope=self.candidate();result=verify_candidate(self.context,request,prediction,envelope)
        with NativeSession(self.root/"wrong-dispatch",["case-2"],{}) as session:
            session.begin("case-2",{"unrelated":"request"});session.finish("case-2",result,resources(),status="accepted");receipt=session.finalize()
        with self.assertRaisesRegex(ContractError,"dispatched request"):
            verify_session(self.root/"wrong-dispatch",expected_receipt_sha256=receipt["sha256"],context=self.context)


if __name__=="__main__":unittest.main()
