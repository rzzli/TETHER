"""Exactly-once, answer-key-free native LitQA2 candidate generation.

The public entrypoint supervises one contained worker and seals an all-scheduled
ledger even after a bounded failure. No correctness scoring or reference-view
loading occurs here. Model/source qualification and scientific accuracy remain
separate; a partial sealed run is not successful benchmark completion.
"""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
from datetime import datetime,timezone
import hashlib
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from asof.agents import Usage
from asof.atomic import publish_bytes
from asof.journal import RunJournal,read_chain
from asof.serde import ContractError,canonical,decode,encode,fingerprint,freeze,parse_json,safe_child
from asof.study import native
from asof.study.session import StudySession,verify_study
from asof.workflow import Budget
from tether._process import ProcessLimits,supervise_command,validate_success_report
from experiments.labbench import model
from experiments.labbench.data_views import load_queries
from experiments.labbench.native_contract import validate_query
from experiments.labbench.runtime import contain_process_tree,empty_import_cache,ProcessSamples,process_sample,InputAudit
from experiments.labbench.tether_adapter import capture_context,verify_candidate

KIND="labbench_generation"
DEFAULT_LIMITS=freeze(dict(stage_seconds=10800,query_seconds=120,source_seconds=120,
    startup_seconds=180,cleanup_reserve_seconds=45,process_output_bytes=8*1024**2,
    maximum_output_bytes=512*1024**2,port=55616,threads=8,gpu_layers=99))
ALIAS="tether-litqa2-qwen14b-v1"
ZERO=freeze(dict(input_tokens=0,output_tokens=0,cost_usd=0.0))


def need(condition,message):
    if not condition:raise ContractError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def read(path,limit=64*1024**2):
    path=Path(path)
    need(path.is_file() and not path.is_symlink(),"Missing or aliased run artifact")
    with path.open("rb") as stream:raw=stream.read(limit+1)
    need(len(raw)<=limit,"Run artifact exceeds byte limit")
    return raw


def write(path,value):publish_bytes(Path(path),canonical(value)+b"\n")


def proof(path,root=None):
    path=Path(path);raw=read(path,512*1024**2)
    return dict(path=str(path.relative_to(root)).replace("\\","/") if root else str(path.resolve()),
                sha256=sha(raw),bytes=len(raw))


def checked_json(path,expected_sha,limit=64*1024**2):
    raw=read(path,limit);need(sha(raw)==expected_sha,"Anchored artifact hash differs")
    return parse_json(raw)


def source_pins():
    return {str(path.relative_to(ROOT)).replace("\\","/"):sha(read(path,2*1024**2))
            for path in sorted(Path(__file__).parent.glob("*.py"))}


def validate_limits(value):
    value=encode(value)
    need(isinstance(value,dict) and set(value)==set(DEFAULT_LIMITS),"Exact generation limits required")
    for key in value:
        need(type(value[key]) is int and value[key]>0,"Invalid generation limit: "+key)
    need(value["stage_seconds"]<=10800 and value["query_seconds"]<=120 and value["source_seconds"]<=120,
         "Generation limits exceed provisional protocol")
    need(value["cleanup_reserve_seconds"]<value["stage_seconds"] and 1<=value["port"]<=65535
         and value["threads"]<=64 and value["gpu_layers"]<=999,"Invalid process configuration")
    return freeze(value)


def disposition(query,producer_status="unexecuted",check_status="not_run",prediction=None,reason="not dispatched"):
    return dict(id=query["id"],producer_status=producer_status,check_status=check_status,
                prediction=prediction,reason=reason)


def _load_inputs(recipe,*,verify_sources=False,deadline=None):
    queries=load_queries(recipe["queries"]["path"],recipe["queries"]["sha256"])
    for query in queries:validate_query(query)
    need(len(queries)==recipe["expected_count"] and
         (recipe["mode"]=="fictional" or recipe["mode"]=="benchmark" and len(queries)==199),
         "Actual benchmark requires the complete frozen 199-question schedule")
    collection=recipe["collection"]
    if verify_sources:
        from experiments.labbench.collect import verify_collection
        manifest=verify_collection(collection["path"],collection["manifest_sha256"],deadline=deadline,allow_partial=True)
    else:
        manifest=checked_json(Path(collection["path"])/"manifest.json",collection["manifest_sha256"])
    ids=[q["id"] for q in queries]
    need(manifest["kind"]=="labbench_collection" and manifest["schema_version"]==1
         and list(manifest["schedule"])==ids,"Collection schedule differs from query-only grant")
    need(manifest["queries"]["sha256"]==recipe["queries"]["sha256"]
         and len(manifest["cases"])==len(ids),"Collection query grant or denominator differs")
    cutoff=decode(datetime,manifest["cutoff"])
    need(cutoff.tzinfo is not None and cutoff<=datetime.now(timezone.utc),"Invalid/future source cutoff")
    for index,(query,case) in enumerate(zip(queries,manifest["cases"])):
        need(case["id"]==query["id"] and case["ordinal"]==index and case["query_sha256"]==fingerprint(query),
             "Collection case identity differs")
    return freeze(queries),freeze(manifest)


def case_accounting(case_root):
    """Reconstruct charged/reserved use from the original generic study journal."""
    case_root=Path(case_root)
    result=dict(generation_attempts=0,tokenizer_attempts=0,measured_usage=dict(ZERO),estimated_usage=dict(ZERO),
                unresolved_generation=False,basis="no generation dispatch")
    token_path=case_root/"tokenization/request.json"
    # Request retention precedes HTTP: this is a conservative possible attempt,
    # not a claim that the tokenizer/server received it.
    result["tokenizer_attempts"]=int(token_path.exists())
    journal=case_root/"session/journal.jsonl"
    if not journal.exists():return result
    events=read_chain(journal,allow_incomplete_tail=True)
    dispatch=[e for e in events if e["event"]=="study_dispatch"]
    accounts=[e for e in events if e["event"]=="study_accounted"]
    need(len(dispatch)<=1 and len(accounts)<=1 and (not accounts or dispatch),"Duplicate/inconsistent model accounting")
    if not dispatch:return result
    result["generation_attempts"]=1
    reserved=decode(Usage,encode(dispatch[0]["details"]["reserved"]));reserved.validate()
    if accounts:
        item=accounts[0]["details"]
        usage=decode(Usage,encode(item["usage"]));usage.validate()
        need(item["basis"] in ("adapter_reported","conservative_quote"),"Unknown model accounting basis")
        result["measured_usage" if item["basis"]=="adapter_reported" else "estimated_usage"]=encode(usage)
        result["basis"]=item["basis"]
    else:
        result["estimated_usage"]=encode(reserved)
        result["unresolved_generation"]=True
        result["basis"]="durable dispatch without terminal accounting; conservative reservation"
    return result


def _native_return_complete(case_root,request,payload,alias):
    raw_path=Path(case_root)/"session/raw-response.bin"
    if not raw_path.exists():return False
    try:native._native(read(raw_path,1024**2),request,payload,alias)
    except Exception:return False
    return True


def run_case(query,case,*,ordinal,collection_root,cutoff,owner,model_provenance,configuration,
             alias,output,journal,deadline,limits):
    """Execute one fresh case, or retain an explicit nonexecution disposition.

    Returns a terminal record and whether the caller must stop further dispatch.
    Potentially incomplete model calls stop the stage; positively completed but
    malformed answer JSON may continue. No path retries a call.
    """
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    started,cpu=time.monotonic(),time.process_time()
    row=disposition(query);stage="source_context";stop=False;context=request=payload=None
    journal.append("case_reserved",id=query["id"],ordinal=ordinal,path=str(output.name))
    try:
        if case["status"]!="completed":
            row=disposition(query,"input_unavailable",reason="source collection "+case["status"]+": "+str(case.get("reason")))
        else:
            need(time.monotonic()<deadline-limits["cleanup_reserve_seconds"],"Stage budget exhausted before source preparation")
            retrieval=case["retrieval"]
            context=capture_context(query,safe_child(collection_root,retrieval["path"]),retrieval["manifest_sha256"],
                cutoff,model_provenance,configuration,deadline=min(deadline-limits["cleanup_reserve_seconds"],
                                                                time.monotonic()+limits["source_seconds"]))
            expected_sources=case["task_sources"]
            selected=checked_json(safe_child(collection_root,expected_sources["path"]),expected_sources["sha256"])
            need(canonical(context.sources)==canonical(selected),"Consumed sources differ from collection grant")
            request,payload=model.make_request(query,context.sources,model_provenance,configuration)
            need(canonical(request)==canonical(context.request),"Source capture and actual model request differ")
            for name,value in (("context.json",context.report),("request.json",request),("payload.json",payload),("sources.json",context.sources)):
                write(output/name,value)
            stage="tokenization"
            call_deadline=min(deadline-limits["cleanup_reserve_seconds"],time.monotonic()+limits["query_seconds"])
            quote=model.tokenize_once(owner,payload,output=output/"tokenization",journal=journal,deadline=call_deadline)
            transport=output/"transport";transport.mkdir()
            backend=model.LocalMCQBackend(owner=owner,request=request,payload=payload,tokenization=quote,
                output=transport,deadline=call_deadline,model_alias=alias)
            verifier=model.MCQVerifier(model_alias=alias)
            stage="generation"
            with StudySession(output/"session",resources={},required_resources=(),
                configuration=dict(task_id=query["id"],source_context_sha256=context.sha256,query_seconds=limits["query_seconds"]),
                budget=Budget(max_calls=1,max_retries=0,max_input_tokens=16384,max_output_tokens=256,
                              max_seconds=max(.001,call_deadline-time.monotonic()))) as session:
                prediction=session.call_once(request=request,payload=payload,backend=backend,verifier=verifier)
                session.finish()
            need(time.monotonic()<call_deadline,"Original shared query deadline exceeded")
            # This exact accepted native result is sealed before the policy gate.
            write(output/"candidate.json",prediction)
            stage="policy"
            decision=verify_candidate(context,request,prediction,journal=journal)
            write(output/"decision.json",decision)
            row=disposition(query,"produced","accepted" if decision["accepted"] else "rejected",
                            encode(prediction),None if decision["accepted"] else decision["reason"])
            stage="case_finalization"
    except BaseException as error:
        if stage=="policy" and (output/"candidate.json").exists():
            row=disposition(query,"produced","error",parse_json(read(output/"candidate.json")),type(error).__name__+": "+str(error))
        else:
            status="interrupted" if isinstance(error,KeyboardInterrupt) else "timeout" if isinstance(error,TimeoutError) else "error"
            if stage=="source_context":status="input_unavailable" if not isinstance(error,KeyboardInterrupt) else "interrupted"
            if stage=="generation" and isinstance(error,ContractError) and request is not None and _native_return_complete(output,request,payload,alias):
                # Only codec failure is parse_failure. Resource/proof/seal errors
                # remain operational errors even if some output text exists.
                try:model.MCQVerifier(model_alias=alias).validate_response(request,read(output/"session/raw-response.bin",1024**2))
                except ContractError:status="parse_failure"
            row=disposition(query,status,reason=stage+": "+type(error).__name__+": "+str(error))
        stop=isinstance(error,(KeyboardInterrupt,OSError)) or stage in ("tokenization","generation","case_finalization")
        if row["producer_status"]=="parse_failure":stop=False
        journal.append("case_failure",id=query["id"],ordinal=ordinal,stage=stage,error_class=type(error).__name__,stop_remaining=stop)
    record=dict(id=query["id"],ordinal=ordinal,disposition=row,accounting=case_accounting(output),
                resources=dict(wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
                               worker_process_sample=process_sample(os.getpid())),stage=stage,stop_remaining=stop)
    write(output/"status.json",record)
    journal.append("case_terminal",id=query["id"],ordinal=ordinal,status_sha256=sha(read(output/"status.json")))
    return freeze(record),stop


def _worker(recipe_path,expected_recipe_sha256,output):
    recipe=checked_json(recipe_path,expected_recipe_sha256,1024**2)
    need(source_pins()==recipe["code_pins"],"Generation worker code differs from freeze")
    limits=validate_limits(recipe["limits"]);config=model.configuration(recipe["configuration"])
    empty_import_cache(expected=recipe["worker_import_cache"],cache_root=ROOT/"data/cache")
    journal=RunJournal(Path(output),kind="build");output=journal.output
    started,cpu=time.monotonic(),time.process_time();deadline=started+limits["stage_seconds"]-5
    owner=None;sampler=None;audit=None;handle=None;status="partial";reason=None;stage="containment"
    try:
        handle=contain_process_tree()
        journal.append("worker_contained",kill_on_job_close=True,handle_inheritable=False)
        stage="source_collection_verification"
        queries,collection=_load_inputs(recipe,verify_sources=True,deadline=deadline-limits["cleanup_reserve_seconds"])
        stage="asset_preparation"
        spec,bindings,provenance=model.make_server_spec(recipe["model_receipt"]["path"],recipe["model_receipt"]["sha256"],
            port=limits["port"],alias=recipe["alias"],startup_seconds=limits["startup_seconds"],
            context_tokens=config["context_tokens"],threads=limits["threads"],gpu_layers=limits["gpu_layers"])
        collection_root=Path(recipe["collection"]["path"])
        # Collection is source-only, externally anchored and verified above. The
        # exact verified inventory grants no preparation/reference container.
        grants=[Path(recipe_path),Path(recipe["queries"]["path"]),*bindings.values()]
        grants.extend(safe_child(collection_root,key) for key in collection["outputs"])
        grants.extend(collection_root/key for key in ("manifest.json","journal.jsonl","SEALED.json",
            "COMPLETE.json" if collection["status"]=="completed" else "PARTIAL.json"))
        audit=InputAudit(inputs=grants,output=output,code_roots=(Path(sys.prefix),Path(sys.base_prefix),
            Path(__file__).parent,Path(recipe["worker_import_cache"])))
        audit.activate()
        server_output=output/"server";server_output.mkdir()
        owner=model.owned_server(spec,bindings,output=server_output,journal=journal,parent_deadline=deadline)
        stage="model_startup";setup=time.monotonic()
        with owner:
            journal.append("worker_model_ready",setup_including_asset_verification_seconds=time.monotonic()-setup,
                           model_provenance=provenance)
            with ProcessSamples(owner.terminal_record["pid"]) as sampler:
                stage="cases";stop_reason=None
                for ordinal,(query,case) in enumerate(zip(queries,collection["cases"])):
                    case_root=output/"cases"/f"{ordinal:03d}"
                    if stop_reason is not None or time.monotonic()>=deadline-limits["cleanup_reserve_seconds"]:
                        stop_reason=stop_reason or "global generation budget exhausted"
                        journal.append("case_unexecuted",id=query["id"],ordinal=ordinal,reason=stop_reason)
                        continue
                    terminal,stop=run_case(query,case,ordinal=ordinal,collection_root=collection_root,cutoff=collection["cutoff"],
                        owner=owner,model_provenance=provenance,configuration=config,alias=recipe["alias"],
                        output=case_root,journal=journal,deadline=deadline,limits=limits)
                    if stop:stop_reason=terminal["disposition"]["reason"] or "unresolved operation; no further dispatch"
                reason=stop_reason
                status="completed" if stop_reason is None else "partial"
            stage="model_cleanup"
        need(owner.terminal_record["server_stopped"] is True,"Model cleanup is unverified")
        empty_import_cache(expected=recipe["worker_import_cache"],cache_root=ROOT/"data/cache")
        need(source_pins()==recipe["code_pins"],"Generation code changed during worker")
        if audit:audit.flush();need(audit.denials==0,"Generation attempted forbidden file access")
        journal.append("worker_terminal",status=status,reason=reason,server_terminal=owner.terminal_record)
        write(output/"TERMINAL.json",dict(status=status,reason=reason,cleanup="normal_verified",server_terminal=owner.terminal_record,
            model_samples=sampler.values if sampler else [],model_sampling_seconds=.5,
            worker_wall_seconds=time.monotonic()-started,worker_cpu_seconds=time.process_time()-cpu,
            memory_scope="CPU working set sampled after model readiness; GPU memory/energy unmeasured",
            audit=dict(opens=audit.opens,denials=audit.denials) if audit else None,
            journal_terminal_sha256=journal.events[-1]["sha256"]))
    except BaseException as error:
        try:
            journal.fail(error,stage)
            write(output/"FAILURE.json",dict(status="partial",stage=stage,error_class=type(error).__name__,message=str(error),
                server_terminal=owner.terminal_record if owner else None,automatic_retry=False,
                cleanup="normal_verified" if owner and owner.terminal_record.get("server_stopped") is True else "unverified_or_job_forced"))
        except BaseException as secondary:error.add_note("Worker failure capture: "+type(secondary).__name__)
        raise
    finally:
        if audit:audit.flush()
        journal.close();_=handle


def recover_cases(root,queries,*,failure_reason=None):
    """Read durable case outcomes/accounting; never resume or call a model."""
    root=Path(root);worker=root/"worker";journal=worker/"journal.jsonl"
    events=read_chain(journal,allow_incomplete_tail=True) if journal.exists() else ()
    terminals={};reserved=set();unexecuted={}
    ids=[q["id"] for q in queries]
    for event in events:
        if event["event"] not in ("case_reserved","case_terminal","case_unexecuted"):continue
        details=event["details"];ordinal=details["ordinal"]
        need(type(ordinal) is int and 0<=ordinal<len(ids) and details["id"]==ids[ordinal],"Case journal schedule differs")
        if event["event"]=="case_reserved":
            need(ordinal not in reserved,"Duplicate case reservation");reserved.add(ordinal)
        elif event["event"]=="case_terminal":
            need(ordinal in reserved and ordinal not in terminals,"Duplicate/unreserved case terminal")
            path=worker/"cases"/f"{ordinal:03d}"/"status.json"
            terminal=checked_json(path,details["status_sha256"])
            need(terminal["id"]==ids[ordinal] and terminal["ordinal"]==ordinal,"Case terminal identity differs")
            terminals[ordinal]=terminal
        else:
            need(ordinal not in reserved and ordinal not in unexecuted,"Unexecuted case was already reserved")
            unexecuted[ordinal]=details["reason"]
    index=[]
    for ordinal,query in enumerate(queries):
        case_root=worker/"cases"/f"{ordinal:03d}"
        accounting=case_accounting(case_root)
        need(not (accounting["generation_attempts"] or accounting["tokenizer_attempts"]) or ordinal in reserved,
             "Model/tokenizer accounting exists without a scheduled case reservation")
        if ordinal in terminals:
            terminal=terminals[ordinal]
            need(canonical(terminal["accounting"])==canonical(accounting),"Terminal model accounting differs from journal")
            row=terminal["disposition"];basis="worker_terminal"
            resources=terminal["resources"]
        else:
            status="error" if ordinal in reserved else "unexecuted"
            row=disposition(query,status,reason=unexecuted.get(ordinal) or failure_reason or
                            ("reserved case has no durable terminal" if ordinal in reserved else "not dispatched"))
            resources=None;basis="parent_recovered_no_replay"
        need(row["id"]==query["id"],"Recovered disposition identity differs")
        artifacts={}
        names={"context":"context.json","request":"request.json","payload":"payload.json","sources":"sources.json",
               "candidate":"candidate.json","decision":"decision.json","status":"status.json",
               "session_receipt":"session/receipt.json","session_report":"session/report.json",
               "session_journal":"session/journal.jsonl","raw_response":"session/raw-response.bin",
               "session_response":"session/response.json","session_configuration":"session/configuration.json",
               "tokenization":"tokenization/result.json","tokenization_body":"tokenization/body.bin",
               "native_failure":"transport/native-failure-wrapper.json"}
        for key,name in names.items():
            path=case_root/name
            if path.exists():artifacts[key]=proof(path,root)
        index.append(dict(id=query["id"],ordinal=ordinal,path=f"worker/cases/{ordinal:03d}",disposition=row,
                          artifacts=artifacts,accounting=accounting,resources=resources,terminal_basis=basis))
    return freeze(index)


def totals(index):
    result=dict(scheduled=len(index),generation_attempts=0,tokenizer_attempts=0,unresolved_generation=0,
                measured_usage=dict(ZERO),estimated_usage=dict(ZERO),producer_statuses={},check_statuses={})
    result["producer_statuses"]=dict(Counter(c["disposition"]["producer_status"] for c in index))
    result["check_statuses"]=dict(Counter(c["disposition"]["check_status"] for c in index))
    for case in index:
        account=case["accounting"]
        for key in ("generation_attempts","tokenizer_attempts","unresolved_generation"):result[key]+=account[key]
        for basis in ("measured_usage","estimated_usage"):
            for key in ZERO:result[basis][key]+=account[basis][key]
    return result


def _inventory(root,maximum):
    records={};total=0
    for path in sorted(Path(root).rglob("*")):
        need(not path.is_symlink(),"Aliased generation output")
        if not path.is_file() or path==Path(root)/"SEALED.json":continue
        item=proof(path,root);total+=item["bytes"]
        need(total<=maximum and len(records)<30000,"Generation artifact limit exceeded")
        records[item["path"]]={"sha256":item["sha256"],"bytes":item["bytes"]}
    return records


def _seal(root,recipe,queries,journal,*,failure_reason,parent_resources,supervision):
    root=Path(root)
    index=recover_cases(root,queries,failure_reason=failure_reason)
    dispositions=[case["disposition"] for case in index]
    write(root/"dispositions.json",dispositions);write(root/"case-index.json",index)
    terminal_path=root/"worker/TERMINAL.json"
    terminal=parse_json(read(terminal_path)) if terminal_path.exists() else None
    if terminal:
        need(terminal["journal_terminal_sha256"]==read_chain(root/"worker/journal.jsonl")[-1]["sha256"],
             "Worker terminal record is not journal-bound")
    normal=bool(terminal and terminal["cleanup"]=="normal_verified" and terminal["server_terminal"]["server_stopped"] is True)
    complete=bool(failure_reason is None and normal and terminal["status"]=="completed"
                  and all(c["terminal_basis"]=="worker_terminal" for c in index))
    status="completed" if complete else "partial"
    aggregate=totals(index)
    manifest=dict(schema_version=1,kind=KIND,status=status,mode=recipe["mode"],schedule=[q["id"] for q in queries],
        queries=proof(root/"queries.json",root),collection=recipe["collection"],model_receipt=recipe["model_receipt"],
        alias=recipe["alias"],configuration=recipe["configuration"],limits=recipe["limits"],code_pins=recipe["code_pins"],
        recipe=proof(root/"recipe.json",root),dispositions=proof(root/"dispositions.json",root),case_index=proof(root/"case-index.json",root),
        totals=aggregate,cleanup="normal_verified" if normal else "unverified_or_job_forced",failure_reason=failure_reason,
        parent_resources=parent_resources,supervision=supervision,worker_terminal=proof(terminal_path,root) if terminal else None,
        provider_cost_usd=0,reference_access="not_performed",answer_correctness="not_evaluated",
        automatic_retries=False,created_at_utc=datetime.now(timezone.utc).isoformat())
    write(root/"manifest.json",manifest)
    marker=dict(status=status,manifest_sha256=sha(read(root/"manifest.json")),cleanup=manifest["cleanup"])
    write(root/("COMPLETE.json" if complete else "PARTIAL.json"),marker)
    journal.append("generation_sealed",status=status,manifest_sha256=marker["manifest_sha256"],
                   scheduled=len(queries),totals=aggregate)
    journal.close()
    outputs=_inventory(root,recipe["limits"]["maximum_output_bytes"])
    seal=dict(schema_version=1,kind=KIND,status=status,manifest_sha256=marker["manifest_sha256"],
              outputs=outputs,journal_terminal_sha256=journal.events[-1]["sha256"])
    write(root/"SEALED.json",seal)
    return freeze(manifest)


def run_stage(*,queries_path,queries_sha256,collection_root,collection_manifest_sha256,
              model_receipt_path,model_receipt_sha256,output,expected_code_pins,configuration=None,
              limits=DEFAULT_LIMITS,alias=ALIAS,mode="benchmark"):
    """Supervise one new generation worker; never infer permission to retry."""
    limits=validate_limits(limits);configuration=model.configuration(configuration)
    need(source_pins()==expected_code_pins,"Caller-supplied generation code freeze differs")
    parent_cache=empty_import_cache(cache_root=ROOT/"data/cache")
    queries=load_queries(queries_path,queries_sha256)
    need(mode in ("benchmark","fictional") and (mode=="fictional" or len(queries)==199),"Wrong generation population")
    root=Path(output).resolve()
    need(root.is_relative_to(ROOT/"data"),"Generation output must be a new ignored project data path")
    journal=RunJournal(root,kind="build")
    started,cpu=time.monotonic(),time.process_time();result=None;failure=None;manifest=None
    try:
        publish_bytes(root/"queries.json",read(queries_path))
        need(sha(read(root/"queries.json"))==queries_sha256,"Consumed/copied query bytes differ")
        worker_cache=root/"worker-import-cache";worker_cache.mkdir()
        recipe=dict(schema_version=1,kind=KIND,mode=mode,expected_count=len(queries),
            queries=proof(root/"queries.json"),collection=dict(path=str(Path(collection_root).resolve()),manifest_sha256=collection_manifest_sha256),
            model_receipt=dict(path=str(Path(model_receipt_path).resolve()),sha256=model_receipt_sha256),
            configuration=configuration,limits=limits,alias=alias,code_pins=expected_code_pins,
            worker_import_cache=str(worker_cache),parent_import_cache=str(parent_cache))
        write(root/"recipe.json",recipe)
        _load_inputs(recipe)
        command=[sys.executable,"-I","-B","-X","pycache_prefix="+str(worker_cache),str(Path(__file__).resolve()),
                 "--worker","--recipe",str(root/"recipe.json"),"--recipe-sha256",sha(read(root/"recipe.json")),"--output",str(root/"worker")]
        process_limits=ProcessLimits(timeout_seconds=limits["stage_seconds"],max_output_bytes=limits["process_output_bytes"])
        journal.append("generation_worker_dispatch",command=command,limits=process_limits.payload(),recipe_sha256=sha(read(root/"recipe.json")))
        try:
            result=supervise_command(command,limits=process_limits)
        except BaseException as error:
            result=getattr(error,"tether_engine_result",None)
            raise
        finally:
            if result is not None:
                publish_bytes(root/"worker.stdout",result.stdout);publish_bytes(root/"worker.stderr",result.stderr)
                write(root/"SUPERVISION.json",dict(returncode=result.returncode,supervision=result.supervision))
                journal.append("generation_worker_returned",returncode=result.returncode,supervision=result.supervision)
        need(result is not None and result.returncode==0,"Generation worker failed")
        validate_success_report(result.supervision,process_limits,len(result.stdout),len(result.stderr))
        need(source_pins()==expected_code_pins,"Generation code changed during execution")
        empty_import_cache(expected=parent_cache,cache_root=ROOT/"data/cache")
        need(not any(worker_cache.iterdir()),"Generation worker import cache is not empty")
    except BaseException as error:
        failure=type(error).__name__+": "+str(error)
        try:
            journal.fail(error,"parent_generation")
            write(root/"FAILURE.json",dict(error_class=type(error).__name__,reason=failure,automatic_retry=False))
        except BaseException as secondary:error.add_note("Parent failure retention: "+type(secondary).__name__)
        # A trusted schedule exists: attempt a partial all-case seal without any
        # acquisition/model replay. Catastrophic storage failures may still stop
        # sealing and leave only the readable journal prefix.
    try:
        need((root/"recipe.json").is_file(),"Preflight failed before a frozen recipe; no generation seal")
        manifest=_seal(root,recipe,queries,journal,failure_reason=failure,
            parent_resources=dict(wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
                                  process_sample=process_sample(os.getpid())),
            supervision=None if result is None else dict(returncode=result.returncode,report=result.supervision))
    finally:
        journal.close()
    return manifest


def verify_generation(root,expected_sealed_sha256):
    """Byte and schedule/accounting reconciliation; no gold or scientific score."""
    root=Path(root).resolve();seal=checked_json(root/"SEALED.json",expected_sealed_sha256)
    need(seal["schema_version"]==1 and seal["kind"]==KIND,"Unknown generation seal")
    manifest=checked_json(root/"manifest.json",seal["manifest_sha256"])
    need(manifest["schema_version"]==1 and manifest["kind"]==KIND and manifest["status"]==seal["status"]
         and manifest["status"] in ("completed","partial"),"Generation status mismatch")
    need(canonical(_inventory(root,manifest["limits"]["maximum_output_bytes"]))==canonical(seal["outputs"]),"Generation byte inventory differs")
    recipe=checked_json(safe_child(root,manifest["recipe"]["path"]),manifest["recipe"]["sha256"])
    queries=load_queries(safe_child(root,manifest["queries"]["path"]),manifest["queries"]["sha256"])
    for query in queries:validate_query(query)
    need(manifest["schedule"]==[q["id"] for q in queries] and recipe["expected_count"]==len(queries),"Generation schedule mismatch")
    for key in ("collection","model_receipt","configuration","limits","alias","mode","code_pins"):
        need(canonical(manifest[key])==canonical(recipe[key]),"Generation recipe/manifest mismatch: "+key)
    validate_limits(manifest["limits"]);model.configuration(manifest["configuration"])
    need(manifest["mode"]=="fictional" or manifest["mode"]=="benchmark" and len(queries)==199,"False complete benchmark population")
    events=read_chain(root/"journal.jsonl")
    need(events[-1]["event"]=="generation_sealed" and events[-1]["sha256"]==seal["journal_terminal_sha256"]
         and events[-1]["details"]["manifest_sha256"]==seal["manifest_sha256"],"Generation journal is not sealed")
    index=checked_json(safe_child(root,manifest["case_index"]["path"]),manifest["case_index"]["sha256"])
    rows=checked_json(safe_child(root,manifest["dispositions"]["path"]),manifest["dispositions"]["sha256"])
    reconstructed=recover_cases(root,queries,failure_reason=manifest["failure_reason"])
    need(canonical(index)==canonical(reconstructed) and canonical(rows)==canonical([c["disposition"] for c in index]),
         "Generation case ledger differs from retained originals")
    need(canonical(totals(index))==canonical(manifest["totals"])
         and canonical(events[-1]["details"]["totals"])==canonical(manifest["totals"]),"Generation aggregate accounting differs")
    from experiments.labbench.evaluate import PRODUCER_STATUSES,CHECK_STATUSES
    for row,case in zip(rows,index):
        need(set(row)=={"id","producer_status","check_status","prediction","reason"}
             and row["producer_status"] in PRODUCER_STATUSES and row["check_status"] in CHECK_STATUSES,"Invalid generation disposition")
        if row["producer_status"]=="produced":
            need({"candidate","request","payload","context","sources","session_receipt"}<=set(case["artifacts"]),"Produced candidate missing proofs")
            candidate=checked_json(safe_child(root,case["artifacts"]["candidate"]["path"]),case["artifacts"]["candidate"]["sha256"])
            need(canonical(candidate)==canonical(row["prediction"]),"Disposition differs from frozen candidate")
            need(row["reason"] is None if row["check_status"]=="accepted" else bool(row["reason"]),"Invalid policy disposition reason")
        else:
            need(row["prediction"] is None and row["check_status"]=="not_run" and bool(row["reason"]),"Failure was promoted to a native answer")
    flag="COMPLETE.json" if manifest["status"]=="completed" else "PARTIAL.json"
    marker=parse_json(read(root/flag))
    need(marker==dict(status=manifest["status"],manifest_sha256=seal["manifest_sha256"],cleanup=manifest["cleanup"]),"Generation marker differs")
    if manifest["status"]=="completed":
        need(manifest["cleanup"]=="normal_verified" and manifest["failure_reason"] is None
             and all(c["terminal_basis"]=="worker_terminal" for c in index),"False generation completion")
        supervision=manifest["supervision"]
        need(supervision["returncode"]==0,"Completed generation has nonzero worker exit")
        validate_success_report(supervision["report"],ProcessLimits(timeout_seconds=manifest["limits"]["stage_seconds"],
            max_output_bytes=manifest["limits"]["process_output_bytes"]),len(read(root/"worker.stdout")),len(read(root/"worker.stderr")))
    need(manifest["automatic_retries"] is False and manifest["provider_cost_usd"]==0
         and manifest["reference_access"]=="not_performed","Generation scope declaration differs")
    return freeze(manifest)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--worker",action="store_true");parser.add_argument("--execute",action="store_true")
    parser.add_argument("--recipe");parser.add_argument("--recipe-sha256");parser.add_argument("--output")
    args=parser.parse_args()
    need(args.recipe and args.recipe_sha256 and args.output,"Exact recipe anchor and fresh output required")
    if args.worker:_worker(args.recipe,args.recipe_sha256,args.output)
    elif args.execute:
        recipe=checked_json(args.recipe,args.recipe_sha256,1024**2)
        run_stage(queries_path=recipe["queries"]["path"],queries_sha256=recipe["queries"]["sha256"],
            collection_root=recipe["collection"]["path"],collection_manifest_sha256=recipe["collection"]["manifest_sha256"],
            model_receipt_path=recipe["model_receipt"]["path"],model_receipt_sha256=recipe["model_receipt"]["sha256"],
            output=args.output,expected_code_pins=recipe["code_pins"],configuration=recipe["configuration"],
            limits=recipe["limits"],alias=recipe["alias"],mode=recipe["mode"])
    else:raise ContractError("Explicit --execute required; inspection never resumes generation")


if __name__=="__main__":main()
