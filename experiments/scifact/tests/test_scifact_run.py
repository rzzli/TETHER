"""Fictional controller tests. Worker/model-policy boundaries are explicit stubs.

Actual worker, native policy and scorer have separate qualification suites. No
production claim, reference label, model fitting or benchmark score is used here.
"""
import copy
import hashlib
import json
import platform
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools.history import read_checkpoint

from tether_engine.journal import read_chain
from tether_engine.serde import ContractError, canonical, fingerprint, freeze
from tether._process import EngineResult, EngineDeadlineExceeded, supervise_command
from experiments.scifact.data_views import prepare_release, load_product
from experiments.scifact.evaluate import EVALUATOR_SHA256
from experiments.scifact.tether_adapter import NativeSession, make_request
from experiments.scifact.run import (Stage, GRID, DEFAULT_LIMITS, failure_dispositions,
                                    select_configuration, session_cells, file_proof, read, write, capture_runtime)
from test_scifact_data_views import write_tar, acquisition

ROOT = Path(__file__).resolve().parents[3]
EVALUATOR_ARCHIVE = (
    "planning/review-assets/tether-scifact-20261105/scoring/qualification-attempt01/"
    "source_snapshots/data/reference/scifact-evaluator-66feffc5/evaluator/eval.py"
)


def resources(**changes):
    result = dict(wall_seconds=.001,cpu_seconds=.001,peak_memory_bytes=None,memory_method="fictional_unavailable",
                  input_bytes=1,output_bytes=1,examples=1,model_input_tokens=None,model_output_tokens=None,
                  tokenizer_identity=None,provider_usage=None,token_usage_reason="not_applicable_non_llm",provider_cost_usd=0)
    return result | changes


def supervision(limits, *, reason="exited"):
    return {"schema_version":1,"method":"tether.process_envelope.v1","limits":limits.payload(),
            "termination_reason":reason,"execution_elapsed_seconds":.01,"total_elapsed_seconds":.02,
            "retained_stdout_bytes":0,"retained_stderr_bytes":0,"observed_stdout_bytes":0,"observed_stderr_bytes":0,
            "observed_counts_are_lower_bounds":False,"pipe_eof":{"stdout":True,"stderr":True},
            "process_started":True,"process_reaped":True,"cleanup_errors":[]}


def fictional_preparation(root):
    corpus=[];train=[]
    for group in range(1,31):
        for doc in (group,1000+group):
            corpus.append({"doc_id":doc,"title":f"Document {doc}","abstract":["Measured finding.","Unrelated setting."],"structured":False})
        for offset,label in ((0,"SUPPORT"),(1,"CONTRADICT")):
            train.append({"id":2*group+offset,"claim":f"Statement {group} variant {offset}","cited_doc_ids":[group,1000+group],
                          "evidence":{str(group):[{"label":label,"sentences":[0]}]}})
    corpus.append({"doc_id":9999,"title":"Independent public task","abstract":["Unrelated document."],"structured":False})
    dev=[{"id":10000,"claim":"A held-out fictional query.","cited_doc_ids":[9999],"evidence":{}}]
    test=[{"id":20000,"claim":"Unused test query."}]
    archive=write_tar(root/"scifact-data.tar.gz",(corpus,train,dev,test))
    source=acquisition(root,archive);output=root/"preparation"
    # A fictional successful transport event is required by the real admission
    # bridge; this is generated fixture provenance, not a claim of a download.
    receipt=archive.with_suffix(".receipt.json");receipt_value=read(receipt);receipt_value["http_status"]=200
    receipt.write_bytes(canonical(receipt_value)+b"\n")
    acquisition_value=read(source);acquisition_value["originals"][0]["receipt_sha256"]=file_proof(receipt)["sha256"]
    source.write_bytes(canonical(acquisition_value)+b"\n")
    report=prepare_release(source,output)
    return output,report["manifest_sha256"]


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        # Exact upstream code only; no local acquisition, dataset or model is used.
        raw = read_checkpoint(EVALUATOR_ARCHIVE)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EVALUATOR_SHA256)
        self.evaluator = self.root / "eval.py"
        self.evaluator.write_bytes(raw)

    def stage(self, **kwargs):
        return Stage(self.root/"unused-prep","0"*64,self.root/"stage",sys.executable,self.evaluator,self.root/"environment.json",**kwargs)

    def test_tuning_ties_follow_both_metrics_and_then_size_threshold(self):
        rows=[{"configuration":dict(c),"status":"completed","metrics":{"abstract_rationalized_f1":.2,"sentence_label_f1":.1}} for c in GRID]
        self.assertEqual(select_configuration(rows)["configuration"],{"k":5,"rationale_threshold":.75})
        rows[3]["metrics"]["sentence_label_f1"]=.9
        self.assertEqual(select_configuration(rows)["configuration"],GRID[3])
        rows[8]["metrics"]["abstract_rationalized_f1"]=.8
        self.assertEqual(select_configuration(rows)["configuration"],GRID[8])

    def test_missing_duplicate_failed_or_nonfinite_tuning_result_rejected(self):
        rows=[{"configuration":dict(c),"status":"completed","metrics":{"abstract_rationalized_f1":0,"sentence_label_f1":0}} for c in GRID]
        bad=[rows[:-1],rows[:-1]+[rows[0]]]
        failed=copy.deepcopy(rows);failed[0]["status"]="failed";bad.append(failed)
        nonfinite=copy.deepcopy(rows);nonfinite[0]["metrics"]["abstract_rationalized_f1"]=float("nan");bad.append(nonfinite)
        for value in bad:
            with self.assertRaises(ContractError):select_configuration(value)

    def test_failure_ledger_preserves_every_scheduled_case_without_nei_placeholder(self):
        records={"1":{"status":"completed","result":{"prediction":{"id":1,"evidence":{}}}},
                 "2":{"status":"timeout","result":{}}}
        rows=failure_dispositions([1,2,3],records,"stopped")
        self.assertEqual([row["producer_status"] for row in rows],["produced","timeout","unexecuted"])
        self.assertIsNone(rows[1]["prediction"]);self.assertIsNone(rows[2]["prediction"])
        self.assertEqual(rows[0]["check_status"],"not_run")

    def test_output_reservation_is_exclusive(self):
        stage=self.stage()
        try:
            with self.assertRaises(FileExistsError):self.stage()
        finally:stage.journal.close()

    def test_qualified_runtime_alias_is_explicitly_resolved_without_relaxing_artifact_paths(self):
        # Invented executable-identity fixture; not a scientific/runtime qualification.
        qualification=self.root/"invented-executable-identity.json"
        expected={"executable":str(Path(sys.executable).absolute()),
                  "base_executable":str(Path(getattr(sys,"_base_executable",sys.executable)).absolute()),
                  "version":platform.python_version()}
        for key in ("executable","base_executable"):
            expected[key+"_sha256"]=hashlib.sha256(Path(expected[key]).read_bytes()).hexdigest()
        write(qualification,{"status":"PASS","python":expected,"installed":{}})
        result=capture_runtime(qualification)
        expected=read(qualification)["python"]
        base=result["executables"]["base_executable"]
        self.assertEqual(base["qualified_path"],expected["base_executable"])
        self.assertEqual(base["path"],str(Path(expected["base_executable"]).resolve()))
        self.assertEqual(base["sha256"],expected["base_executable_sha256"])
        if Path(expected["base_executable"]).absolute()!=Path(expected["base_executable"]).resolve():
            with self.assertRaises(ContractError):file_proof(expected["base_executable"])

    def test_invalid_limits_and_interpreter_fail_before_reservation(self):
        for value in (float("inf"),float("nan"),-1):
            with self.assertRaises(ContractError):self.stage(limits=DEFAULT_LIMITS|{"stage_seconds":value})
        with self.assertRaises(ContractError):
            Stage("a","0"*64,self.root/"no-output",self.root/"wrong-python",self.evaluator,"q")
        self.assertFalse((self.root/"stage").exists())

    def test_code_change_fails_before_worker_dispatch(self):
        calls=[];stage=self.stage(launcher=lambda *args,**kwargs:calls.append(args))
        stage.runtime={"identity":"before"}
        try:
            with patch("experiments.scifact.run.capture_runtime",return_value={"identity":"after"}):
                with self.assertRaisesRegex(ContractError,"changed"):
                    stage.dispatch("fit",{"limits":{"phase_seconds":1},"schedule":[],"mode":"fit"})
            self.assertEqual(calls,[])
            self.assertFalse((stage.output/"recipes").exists())
        finally:stage.journal.close()

    def test_source_bracket_cannot_dispatch_after_consuming_remaining_budget(self):
        stage=self.stage(limits=DEFAULT_LIMITS|{"stage_seconds":10});stage.started=0;stage.runtime={"stable":True}
        clock=[0]
        def bracket(_):clock[0]=20;return {"stable":True}
        try:
            with patch("experiments.scifact.run.time.perf_counter",side_effect=lambda:clock[0]),patch("experiments.scifact.run.capture_runtime",side_effect=bracket):
                with self.assertRaisesRegex(ContractError,"budget"):stage.boundary()
        finally:stage.journal.close()

    def test_worker_session_must_bind_submitted_configuration_inputs_and_queries(self):
        for alteration in ("configuration","inputs","query"):
            with self.subTest(alteration=alteration):
                root=self.root/alteration;root.mkdir()
                query_path=root/"queries.jsonl";query_path.write_bytes(canonical({"id":1,"claim":"Fictional query"})+b"\n")
                recipe={"schema_version":1,"mode":"predict","inputs":{"queries":file_proof(query_path)},
                        "configuration":{"k":5,"rationale_threshold":.25},"schedule":[1],
                        "limits":{"phase_seconds":60,"memory_bytes":1000000,"query_seconds":60}}
                def launch(command,*,limits):
                    job=Path(command[command.index("--output")+1]);job.mkdir(parents=True)
                    write(job/"recipe.json",recipe)
                    config=recipe["configuration"] if alteration!="configuration" else {"k":20,"rationale_threshold":.75}
                    with NativeSession(job/"session",["setup","1"],config,max_wall_seconds=60) as session:
                        session.begin("setup",{"mode":"predict","inputs":{} if alteration=="inputs" else recipe["inputs"]})
                        session.finish("setup",{"kind":"native_model_loaded"},resources())
                        query={"id":1,"claim":"Different text" if alteration=="query" else "Fictional query"}
                        session.begin("1",{"query":query,"configuration":recipe["configuration"]})
                        session.finish("1",{"prediction":{"id":1,"evidence":{}}},resources())
                        receipt=session.finalize()
                    write(job/"COMPLETE.json",{"status":"completed","session_receipt_sha256":receipt["sha256"]})
                    (job/"io-audit.jsonl").write_bytes(canonical({"allowed":True,"path":str(query_path)})+b"\n")
                    return EngineResult(0,b"",b"",supervision(limits))
                stage=Stage("unused","0"*64,root/"stage",sys.executable,self.evaluator,"unused",launcher=launch)
                try:
                    with self.assertRaises(ContractError):stage.dispatch("altered",recipe)
                finally:stage.journal.close()

    def test_parent_timeout_retains_transport_and_all_missing_cases_once(self):
        calls=[]
        def launch(command,*,limits):
            calls.append(command)
            error=EngineDeadlineExceeded("injected deadline")
            error.tether_engine_result=EngineResult(-1,b"",b"",supervision(limits,reason="deadline"))
            raise error
        stage=self.stage(launcher=launch)
        def initialize():stage.schedule=[1,2,3]
        def fit():
            stage.phase="fit"
            stage.dispatch("fit",{"schema_version":1,"mode":"fit","inputs":{},"configuration":{},"schedule":[],
                                  "limits":{"phase_seconds":1,"memory_bytes":1,"query_seconds":1}})
        with patch.object(stage,"initialize",initialize),patch.object(stage,"fit",fit):
            with self.assertRaises(EngineDeadlineExceeded):stage.execute()
        self.assertEqual(len(calls),1)
        self.assertTrue((stage.output/"transport/fit.json").exists())
        rows=read(stage.output/"FAILED-DISPOSITIONS.json")
        self.assertEqual(len(rows),3)
        self.assertTrue(all(row["producer_status"]=="unexecuted" for row in rows))
        self.assertEqual(read_chain(stage.output/"journal.jsonl")[-1]["event"],"build_failed")

    def test_full_controller_uses_sanitized_recipes_and_freezes_before_dev(self):
        preparation,anchor=fictional_preparation(self.root)
        calls=[];recipes=[]
        stage=Stage(preparation,anchor,self.root/"stage",sys.executable,self.evaluator,self.root/"environment.json")
        def launch(command,*,limits):
            recipe=read(command[command.index("--recipe")+1]);job=Path(command[command.index("--output")+1])
            if "score_worker.py" in command[3]:return supervise_command(command,limits=limits)
            if "check_worker.py" in command[3]:
                job.mkdir();write(job/"recipe.json",recipe);dispositions=[]
                with NativeSession(job/"session",[str(key) for key in stage.schedule],stage.selected,max_wall_seconds=60) as session:
                    for key in stage.schedule:
                        request=make_request(stage.context,key,stage.selected);produced=stage.dev_records[str(key)];value=produced["result"]
                        envelope={"request_sha256":fingerprint(request),"prediction_sha256":fingerprint(value["prediction"]),
                                  "retrieved":value["retrieved"],"source_bindings":value["source_bindings"],
                                  "producer_code_sha256":stage.context.model["producer_code"]["sha256"],"resources":produced["resources"]}
                        result={"kind":"accepted_candidate","request":request,"prediction":value["prediction"],"envelope":envelope}
                        session.begin(str(key),request);session.finish(str(key),result,resources(),status="accepted")
                        dispositions.append({"id":key,"producer_status":"produced","check_status":"accepted","prediction":value["prediction"],"reason":None})
                    receipt=session.finalize()
                write(job/"dispositions.json",dispositions);write(job/"COMPLETE.json",{"status":"completed","session_receipt_sha256":receipt["sha256"],
                      "candidate_input_sha256":recipe["candidates"]["sha256"],"policy_sha256":stage.context.policy_sha256})
                return EngineResult(0,b"",b"",supervision(limits))
            calls.append(job.name);recipes.append(recipe)
            self.assertEqual(set(recipe),{"schema_version","mode","inputs","configuration","schedule","limits"})
            # The source-view paths do contain the preparation directory name;
            # what is forbidden is a full preparation/control manifest or references.
            if job.name=="dev":self.assertTrue((stage.output/"DEV-FROZEN.json").exists())
            job.mkdir(parents=True,exist_ok=False);write(job/"recipe.json",recipe)
            schedule=["fit"] if recipe["mode"]=="fit" else ["setup",*map(str,recipe["schedule"])]
            with NativeSession(job/"session",schedule,recipe["configuration"],max_wall_seconds=60) as session:
                if recipe["mode"]=="fit":
                    (job/"model").mkdir()
                    for name,raw in (("model.json",b'{"fictional_mock":true}'),("arrays.npz",b'fictional')):(job/"model"/name).write_bytes(raw)
                    files=[{k:v for k,v in file_proof(p).items() if k!="path"}|{"path":p.name} for p in sorted((job/"model").iterdir())]
                    session.begin("fit",{"mode":"fit","inputs":recipe["inputs"]})
                    session.finish("fit",{"kind":"fitted_native_model","files":files,"metadata":{"fictional_mock":True}},resources())
                else:
                    session.begin("setup",{"mode":"predict","inputs":recipe["inputs"]});session.finish("setup",{"kind":"native_model_loaded"},resources())
                    queries=[json.loads(line) for line in Path(recipe["inputs"]["queries"]["path"]).read_bytes().splitlines()]
                    for query in queries:
                        key=query["id"]
                        session.begin(str(key),{"query":query,"configuration":recipe["configuration"]})
                        session.finish(str(key),{"prediction":{"id":key,"evidence":{}},"retrieved":[],"source_bindings":[],"pair_scores":[]},resources())
                receipt=session.finalize()
            write(job/"COMPLETE.json",{"status":"completed","session_receipt_sha256":receipt["sha256"]})
            (job/"io-audit.jsonl").write_bytes(b"".join(canonical({"path":proof["path"],"allowed":True})+b"\n" for proof in recipe["inputs"].values()))
            return EngineResult(0,b"",b"",supervision(limits))
        stage.launcher=launch
        def context(*args,**kwargs):
            corpus={row["doc_id"]:row for row in load_product(preparation,stage.manifest,"corpus","predict")}
            queries={row["id"]:row for row in load_product(preparation,stage.manifest,"queries_dev","predict")}
            return SimpleNamespace(policy_sha256="f"*64,model=read(stage.model_root/"model-manifest.json"),manifest=stage.manifest,
                                   model_manifest_sha256=stage.model_sha,corpus=corpus,queries=queries,container_admission={"fictional":True})
        # These are explicit integration boundaries, separately qualified by their suites.
        with patch("experiments.scifact.run.capture_runtime",return_value={"packages":{},"fictional_runtime":True}),\
             patch("experiments.scifact.run.build_context",side_effect=context),\
             patch("experiments.scifact.run.verify_session",return_value={"status":"fictional_policy_boundary_stub"}):
            result=stage.execute()
        self.assertEqual(calls,["fit",*[f"tune-{i:02d}" for i in range(1,10)],"dev"])
        self.assertEqual(result["scheduled"],1)
        self.assertEqual(read(stage.output/"DEV-FROZEN.json")["configuration"],{"k":5,"rationale_threshold":.75})
        self.assertTrue((stage.output/"RECEIPT.json").is_file())
        for recipe in recipes:
            inputs=recipe["inputs"]
            self.assertEqual(set(inputs),{"corpus","queries_fit","fit_pairs"} if recipe["mode"]=="fit" else {"model_json","model_arrays","queries"})
            self.assertFalse(any("references_" in proof["path"] or "manifest.json" in proof["path"] for proof in inputs.values()))


if __name__=="__main__":unittest.main()
