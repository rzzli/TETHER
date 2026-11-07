"""Fictional source-inclusive recovery admission; no network or model calls."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import socket
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, encode
from experiments.litqa_comparison import transport
from experiments.litqa_recovery import admission as a, collection as c, plan as p
from experiments.litqa_recovery import test_plan as fixtures
from experiments.litqa_recovery.test_plan import journal, write
from experiments.litqa_supplied import admission as v1, resolver


class RecoveredAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.no_network = patch.object(socket, "create_connection", side_effect=AssertionError("No HTTP/model calls"))
        self.no_network.start(); self.addCleanup(self.no_network.stop)
        self.f = fixtures.RecoveryPlanTests("runTest"); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.top = self.f.top
        self.original_source = self.f.phase / "products/0000"
        original_with_article = self.top / "invented-original-article"
        with patch.object(resolver.legacy, "fetch_http", side_effect=self.fetch_one):
            resolver.acquire(resolver.plan(self.f.dois[0]), original_with_article, deadline=time.monotonic()+60)
        # Only fixture bytes are replaced, before its independent audit/authority.
        shutil.copytree(original_with_article, self.original_source, dirs_exist_ok=True)
        slot_path = self.f.phase / "slots/0000.json"
        slot = json.loads(slot_path.read_bytes())
        slot["product"].update(receipt=p._proof(self.original_source/"RECEIPT.json"),
                               manifest=p._proof(self.original_source/"MANIFEST.json"))
        write(slot_path, slot)
        self.f.stage_pairs[3][1]["slot_sha256"] = p._proof(slot_path)["sha256"]
        journal(self.f.phase/"journal.jsonl", self.f.stage_pairs)
        self.f.hints[0]["dois"] = [self.f.dois[0], self.f.dois[1]]
        self.f.hints[2]["dois"] = [self.f.dois[2], self.f.dois[0]]
        self.rebind_original()
        authority = self.f.reserve()
        qualification = c.publish(self.top/"QUALIFICATION.json", dict(schema_version=2,
            kind="sc04_recovery_collection_qualification_v2", status="PASS", tests=1,
            failures=0, errors=0, skipped=0, code_pins=c.source_pins(),
            scope="Invented unit fixture only; no production qualification"))
        self.output = self.top/"recovered"
        frame = c.make_frame(authority["frame"], authority["authority"], qualification, self.output, 600)
        frame_proof = c.publish(self.top/"EXECUTION.json", frame)
        with patch.object(resolver.legacy, "fetch_http", side_effect=self.fetch_three):
            result = c.execute(frame_proof["path"], frame_proof["sha256"], output=self.output)
        self.receipt_sha = result["receipt"]["sha256"]
        self.prepared = a.prepare(self.output, self.receipt_sha, self.top)
        self.cutoff = datetime.now(timezone.utc)+timedelta(seconds=1)
        self.model = dict(weights_sha256={"fictional.gguf":"a"*64}, runtime_sha256="b"*64,
                          asset_manifest_sha256="c"*64, model_id="invented", revision="pinned")

    @staticmethod
    def response(url, doi, pmcid, text):
        if "/search?" in url:
            body = canonical(dict(hitCount=1,resultList=dict(result=[dict(doi=doi,pmcid=pmcid,
                title="Invented source",isOpenAccess="Y",license="cc by",firstPublicationDate="2020-01-01")])))
        else:
            body = (f'<article><front><article-meta><article-id pub-id-type="pmcid">{pmcid}</article-id>'
                f'<article-id pub-id-type="doi">{doi}</article-id><permissions><license>'
                '<license-p>Creative Commons Attribution License.</license-p></license></permissions>'
                f'</article-meta></front><body><p>{text}</p></body></article>').encode()
        return dict(status=200,body=body,final_url=url,headers={})

    def fetch_one(self, url, **limits):
        return self.response(url,self.f.dois[0],"PMC7000001","Invented question 1 and question 3: cobalt uptake increased.")

    def fetch_three(self, url, **limits):
        return self.response(url,self.f.dois[2],"PMC7000003","Invented question 3: calcium uptake decreased.")

    def rebind_original(self):
        hint_path = Path(self.f.frame["products"]["hints"]["path"])
        write(hint_path,self.f.hints)
        self.f.frame["products"]["hints"] = p._proof(hint_path)
        self.f.frame["question_doi_pairs"] = sum(len(h["dois"]) for h in self.f.hints)
        write(self.f.frame_path,self.f.frame);write(self.f.root/"FRAME.json",self.f.frame)
        self.f.frame_sha = p._proof(self.f.frame_path)["sha256"]
        job_path=self.f.root/"collect/JOB.json";job=json.loads(job_path.read_bytes())
        job["frame_sha256"]=self.f.frame_sha;write(job_path,job)
        command_path=self.f.root/"collect/COMMAND.json";command=json.loads(command_path.read_bytes())
        for flag,value in (("--frame-sha256",self.f.frame_sha),("--job-sha256",p._proof(job_path)["sha256"])):
            command["command"][command["command"].index(flag)+1]=value
        write(command_path,command)
        write(self.f.root/"collect/worker/CONFIG.json",dict(frame_sha256=self.f.frame_sha,job=job,purpose="fictional_qualification"))
        registry=json.loads(self.f.registry_policy_path.read_bytes())
        registry["parent_identity"]=p.digest(p.canonical(dict(original_frame_sha256=self.f.frame_sha,
            original_root_reservation_sha256=p._journal(self.f.root/"journal.jsonl")[0]["sha256"])))
        write(self.f.registry_policy_path,registry)
        self.f.registry_policy_sha=p._proof(self.f.registry_policy_path)["sha256"]
        self.f.anchor()

    def capture(self,index=0,**kwargs):
        return a.capture(self.f.queries[index],self.f.hints[index],self.prepared,
                         kwargs.pop("cutoff",self.cutoff),self.model,**kwargs)

    def test_resolved_only_exact_v1_request_source_order_and_multiple_original_roots(self):
        context=self.capture(2)
        descriptors={d:self.prepared._rows[d]["resolution"] for d in self.f.hints[2]["dois"]}
        original=v1.capture(self.f.queries[2],self.f.hints[2],descriptors,self.top,self.cutoff,self.model)
        self.assertEqual(canonical(context.request),canonical(original.request))
        self.assertEqual(context.sources,original.sources)
        self.assertEqual(context.report["pool"],original.report["pool"])
        self.assertEqual(context.report["source_proofs"],original.report["source_proofs"])
        self.assertEqual(list(context.report["resolved_source_descriptors"]),self.f.hints[2]["dois"])
        self.assertEqual(len({r["root"] for r in descriptors.values()}),2)
        self.assertEqual(context.report["coverage"]["retained_articles"],2)

    def test_uncertain_only_is_exact_empty_request_with_null_unavailability(self):
        context=self.capture(1)
        empty,_=transport.make_answer_request(self.f.queries[1],(),self.model)
        self.assertEqual(canonical(context.request),canonical(empty))
        self.assertEqual(context.sources,())
        self.assertEqual(context.report["source_proofs"],())
        self.assertEqual(context.report["resolved_source_descriptors"],{})
        missing=context.report["coverage"]["sources"][0]
        self.assertIsNone(missing["source"])
        self.assertIsNone(missing["coverage"]["article_retained"])
        self.assertEqual(missing["source_availability"],"unknown")
        operation=context.report["operational_provenance"][0]
        self.assertFalse(operation["citable"])
        self.assertIsNone(operation["parent_proofs"]["response_proof"])
        self.assertEqual(operation["accounting"]["safety_accounted_bytes"],1048576)
        self.assertTrue(a.check(context,dict(answer_index=1,evidence_ids=[]),context.request)["accepted"])
        self.assertFalse(a.check(context,dict(answer_index=0,evidence_ids=[]),context.request)["accepted"])

    def test_mixed_sources_preserve_full_hint_and_uncitable_operational_context(self):
        context=self.capture(0)
        subset=dict(self.f.hints[0],dois=[self.f.dois[0]])
        descriptor={self.f.dois[0]:self.prepared._rows[self.f.dois[0]]["resolution"]}
        original=v1.capture(self.f.queries[0],subset,descriptor,self.top,self.cutoff,self.model)
        self.assertEqual(context.request,original.request)
        self.assertEqual(encode(context.report["full_hint"]),self.f.hints[0])
        self.assertEqual([r["doi"] for r in context.report["coverage"]["sources"]],self.f.hints[0]["dois"])
        self.assertEqual(context.report["coverage"]["inherited_uncertain_inputs"],(self.f.dois[1],))
        valid=context.sources[0]["source_id"]
        self.assertTrue(a.check(context,dict(answer_index=0,evidence_ids=[valid]),context.request)["accepted"])
        operational=context.report["operational_provenance"][1]["parent_proofs"]["plan"]["sha256"]
        self.assertFalse(a.check(context,dict(answer_index=0,evidence_ids=[operational]),context.request)["accepted"])

    def test_raw_dict_and_direct_construction_cannot_be_admitted(self):
        with self.assertRaises(TypeError):a.PreparedCollection(self.prepared.manifest)
        for raw in (encode(self.prepared.manifest),dict(status="independently_reconstructed")):
            with self.subTest(raw=tuple(raw)),self.assertRaisesRegex(ValueError,"capability"):
                a.capture(self.f.queries[0],self.f.hints[0],raw,self.cutoff,self.model)

    def test_actual_query_choices_and_identity_are_not_looked_up_then_ignored(self):
        for change in ("id","choices","question","reference"):
            q=deepcopy(self.f.queries[0])
            if change=="id":q["id"]="00000000-0000-0000-0000-000000000099"
            elif change=="choices":q["choices"][0]="(A) Changed"
            elif change=="question":q["question"]="Changed question?"
            else:q["correct_index"]=0
            with self.subTest(change=change),self.assertRaises(ValueError):
                a.capture(q,self.f.hints[0],self.prepared,self.cutoff,self.model)

    def test_hint_unknown_extra_missing_or_reordered_doi_and_evaluator_fields_reject(self):
        for change in ("unknown","extra","missing","reverse","key","role"):
            h=deepcopy(self.f.hints[0])
            if change=="unknown":h["dois"][0]="10.1234/unknown"
            elif change=="extra":h["dois"].append(self.f.dois[2])
            elif change=="missing":h["dois"].pop()
            elif change=="reverse":h["dois"].reverse()
            elif change=="key":h["key_passage"]="No evaluator answer"
            else:h["role"]="evaluator_only"
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,"hint"):
                a.capture(self.f.queries[0],h,self.prepared,self.cutoff,self.model)

    def test_resolved_source_future_cutoff_and_evaluator_role_reject(self):
        with self.assertRaisesRegex(ValueError,"cutoff"):
            self.capture(2,cutoff=self.cutoff-timedelta(days=1))
        catalog=encode(v1.DEFAULT_CATALOG);catalog["datasets"][0]["roles"]=["evaluator_only"]
        with self.assertRaises(ValueError):self.capture(2,catalog=catalog)

    def test_uncertain_plan_and_journal_tampering_reject_per_question(self):
        row=self.prepared._rows[self.f.dois[1]]
        for name in ("plan","journal"):
            path=Path(row["parent_proofs"][name]["path"]);before=path.read_bytes()
            try:
                path.write_bytes(before+b" ")
                with self.subTest(name=name),self.assertRaises(ValueError):self.capture(1)
            finally:path.write_bytes(before)

    def test_missing_uncertain_proof_rejects_without_source_fabrication(self):
        path=Path(self.prepared._rows[self.f.dois[1]]["parent_proofs"]["journal"]["path"])
        path.unlink()
        with self.assertRaises((ValueError,OSError)):self.capture(1)

    def test_source_body_tampering_revalidated_even_with_prepared_state(self):
        path=self.original_source/"responses/001.body"
        path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaises(ValueError):self.capture(0)

    def test_changed_collection_receipt_rejects_before_capture(self):
        path=self.output/"RECEIPT.json";path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaises(ValueError):self.capture(1)

    def test_deep_mutations_through_prepared_and_context_are_denied(self):
        context=self.capture(0)
        operations=(lambda:self.prepared.manifest["records"][1]["parent_proofs"]["reservation"].__setitem__("byte_reservation",0),
                    lambda:self.prepared.queries[0]["choices"].__setitem__(0,"changed"),
                    lambda:context.report["coverage"]["sources"][1]["coverage"].__setitem__("article_retained",True),
                    lambda:context.request["model_provenance"]["weights_sha256"].__setitem__("fictional.gguf","f"*64),
                    lambda:setattr(self.prepared,"_state",{}))
        before=canonical(context.report)
        for operation in operations:
            with self.assertRaises((AttributeError,TypeError)):operation()
        self.assertEqual(canonical(self.capture(0).report),before)
        caller_hint=deepcopy(self.f.hints[0]);caller_model=deepcopy(self.model)
        original_capture=v1.capture
        def mutate_caller(*args,**kwargs):
            caller_hint["dois"].reverse()
            caller_model["weights_sha256"]["fictional.gguf"]="f"*64
            return original_capture(*args,**kwargs)
        with patch.object(v1,"capture",side_effect=mutate_caller):
            stable=a.capture(self.f.queries[0],caller_hint,self.prepared,self.cutoff,caller_model)
        self.assertEqual(canonical(stable.report),before)
        self.assertEqual(canonical(stable.request),canonical(context.request))

    def test_prepare_copies_replay_data_instead_of_retaining_caller_backing_maps(self):
        result=c.replay(self.output,self.receipt_sha)
        with patch.object(c,"replay",return_value=result):prepared=a.prepare(self.output,self.receipt_sha,self.top)
        result["manifest"]["records"][1]["coverage"]["source_availability"]="invented"
        self.assertEqual(prepared.manifest["records"][1]["coverage"]["source_availability"],"unknown")

    def test_full_replay_is_once_per_operation_boundary_not_per_question(self):
        with patch.object(c,"replay",side_effect=AssertionError("No full replay per question")):
            self.capture(0);self.capture(1);self.capture(2)
        with patch.object(c,"replay",wraps=c.replay) as replay:
            result=a.revalidate(self.prepared)
            self.assertEqual(replay.call_count,1)
        self.assertEqual(result["status"],"independently_revalidated")

    def test_final_replay_rejects_changed_unqueried_source(self):
        self.capture(1)
        path=self.output/"products/0002/responses/001.body";path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaises(ValueError):a.revalidate(self.prepared)

    def test_bad_anchor_common_root_and_expired_deadline_fail(self):
        with self.assertRaises(ValueError):a.prepare(self.output,"0"*64,self.top)
        with self.assertRaises(ValueError):a.prepare(self.output,self.receipt_sha,self.output)
        with patch.object(c,"replay",side_effect=AssertionError("Expired prepare cannot replay")):
            with self.assertRaisesRegex(ValueError,"deadline"):a.prepare(self.output,self.receipt_sha,self.top,deadline=0)
        with self.assertRaisesRegex(ValueError,"deadline"):self.capture(1,deadline=0)


if __name__=="__main__":unittest.main()
