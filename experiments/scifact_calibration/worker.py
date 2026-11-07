"""Owned calibration worker: exact inputs, durable attempts and no retries.

Managed-Python I/O auditing is not an OS sandbox. The separately pinned parent
supervisor additionally owns the process deadline and current code/environment.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
if __name__=='__main__':
    # Import only source code at startup; scientific files are opened after the
    # externally anchored recipe establishes exact actor grants.
    sys.path[:0]=[str(ROOT),str(ROOT/'src')]

from tether_engine.serde import canonical, encode, parse_json
from experiments.scifact_calibration.inputs import anchored, capture, digest, local_path, need

MAX_OUTPUT_BYTES=2*1024**3
_FINAL_LOCK=threading.RLock()


def _shape(proof, maximum):
    need(isinstance(proof,dict) and set(proof)=={'path','sha256','bytes'} and
         type(proof['bytes']) is int and 0<=proof['bytes']<=maximum and
         isinstance(proof['sha256'],str) and len(proof['sha256'])==64 and
         set(proof['sha256'])<=set('0123456789abcdef'),'Invalid granted file proof')
    return local_path(proof['path'])


def _configuration(recipe):
    fields={'schema_version','kind','purpose','mode','requests','schedule','model','code_files','runtime_roots',
            'device','pair_seconds','phase_seconds','output_bytes'}
    need(isinstance(recipe,dict) and set(recipe)==fields and type(recipe['schema_version']) is int and
         recipe['schema_version']==1 and recipe['kind']=='sc05_calibration_worker_v1' and
         recipe['purpose']=='calibrate','Explicit calibration worker authority required')
    need(recipe['mode'] in ('production','qualification') and recipe['device']=='cuda:0','Unsupported execution mode/device')
    ids=recipe['schedule']
    need(isinstance(ids,list) and ids and all(type(x) is int and x>=0 for x in ids) and ids==sorted(set(ids)),'Ordered unique schedule required')
    need(len(ids)==69 if recipe['mode']=='production' else 1<=len(ids)<=8,'Full production or bounded invented qualification schedule required')
    pair=recipe['pair_seconds'];phase=recipe['phase_seconds']
    need(type(pair) in (int,float) and math.isfinite(pair) and 0<pair<=120 and
         (recipe['mode']!='production' or pair==120),'Invalid hard pair deadline')
    need(type(phase) in (int,float) and math.isfinite(phase) and pair<=phase<=43200,'Invalid hard worker deadline')
    need(type(recipe['output_bytes']) is int and recipe['output_bytes']==MAX_OUTPUT_BYTES,'Worker output budget differs')
    request=_shape(recipe['requests'],64*1024**2)
    need(not {'restricted','labels','gold_evidence'}.intersection(p.casefold() for p in request.parts),'Restricted input cannot be a worker request grant')
    model=recipe['model']
    need(isinstance(model,dict) and set(model)=={'acquisition_root','receipt','assets'},'Exact model descriptor required')
    model_root=local_path(model['acquisition_root']);receipt=_shape(model['receipt'],8*1024**2)
    need(receipt==model_root/'RECEIPT.json' and isinstance(model['assets'],list) and model['assets'],'Exact model receipt/assets required')
    assets=[_shape(x,6*1024**3) for x in model['assets']]
    need(len(set(assets))==len(assets) and all(p.is_relative_to(model_root) and p!=receipt for p in assets),'Duplicate or escaped model asset')
    need(isinstance(recipe['code_files'],list) and recipe['code_files'],'Qualified exact code files required')
    code=[_shape(p,8*1024**2) for p in recipe['code_files']]
    roots=(ROOT/'src',ROOT/'experiments',ROOT/'packages/tether/src')
    need(len(code)==len(set(code)) and all(any(p.is_relative_to(r) for r in roots) and p.suffix in ('.py','.json') for p in code),
         'Code grant escapes maintained code roots')
    required={Path(__file__).resolve(),Path(__file__).with_name('inputs.py').resolve(),ROOT/'experiments/scifact_comparison/worker.py',
              ROOT/'experiments/scifact_comparison/inputs.py',ROOT/'experiments/scifact_multivers/inference.py'}
    need(required<=set(code),'Incomplete worker source closure')
    allowed_runtime={Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve()}
    if os.name=='nt': allowed_runtime.add(Path(os.environ.get('SystemRoot','C:/Windows')).resolve()/'System32')
    need(isinstance(recipe['runtime_roots'],list) and recipe['runtime_roots'],'Qualified runtime roots required')
    runtime=[local_path(p) for p in recipe['runtime_roots']]
    need(len(runtime)==len(set(runtime)) and set(runtime)<=allowed_runtime and
         not any(p==ROOT or ROOT.is_relative_to(p) for p in runtime),'Broad or non-runtime read grant')
    return {request,receipt,*assets,*code},tuple(runtime)


class InputAudit:
    """Audited exact data/code opens; stop the hook before terminal hashing."""
    def __init__(self, files, output, runtime):
        self.files={str(p).casefold() for p in files};self.output=output;self.runtime=runtime
        self.runtime_spellings=(Path(sys.prefix).absolute(),Path(sys.base_prefix).absolute(),*runtime)
        self.active=False;self.busy=threading.local();self.lock=threading.Lock()
        self.stream=(output/'io-audit.jsonl').open('xb',buffering=0)
        self.denials=0

    def hook(self,event,args):
        if not self.active or getattr(self.busy,'value',False):return
        if event not in ('open','socket.connect','socket.bind','subprocess.Popen','os.system'):return
        self.busy.value=True
        try:
            if event=='open':
                name,mode,flags=args
                if isinstance(name,int):
                    row=dict(event=event,path=None,descriptor=name,allowed=True,basis='existing_descriptor')
                else:
                    raw_path=Path(os.fsdecode(name))
                    opened=raw_path.absolute()
                    # Python's installed base may be a version alias (for
                    # example a package-manager junction). Resolve only these
                    # runtime spellings, then require the qualified physical
                    # root. Data/code proofs never gain this alias exemption.
                    if any(opened.is_relative_to(r) for r in self.runtime_spellings):
                        resolved=opened.resolve()
                        need(any(resolved.is_relative_to(r) for r in self.runtime),'Runtime alias escapes qualified roots')
                        path=local_path(resolved)
                    else:path=local_path(opened)
                    write=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
                    output=path.is_relative_to(self.output)
                    allowed=output or (not write and (str(path).casefold() in self.files or any(path.is_relative_to(r) for r in self.runtime)))
                    row=dict(event=event,path=str(path),opened_path=str(opened),mode=mode,flags=flags,allowed=allowed,
                             basis='output' if output else 'declared_file_or_runtime' if allowed else 'denied')
            else:row=dict(event=event,path=None,allowed=False,basis='network_or_child_process_denied')
            with self.lock:
                self.stream.write(canonical(row)+b'\n')
                if not row['allowed']:self.denials+=1;os.fsync(self.stream.fileno())
            if not row['allowed']:raise PermissionError('Calibration worker denies undeclared I/O: '+str(row['path'] or event))
        finally:self.busy.value=False

    def activate(self):self.active=True;sys.addaudithook(self.hook)

    def close(self):
        self.active=False
        with self.lock:self.stream.flush();os.fsync(self.stream.fileno());self.stream.close()


def _write(path,value):
    raw=canonical(encode(value))+b'\n'
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())


def _inventory(output):
    records={}
    for path in sorted(output.rglob('*')):
        local_path(path)
        if not path.is_file():continue
        h=hashlib.sha256();size=0
        with path.open('rb') as stream:
            while block:=stream.read(1024**2):h.update(block);size+=len(block)
        records[path.relative_to(output).as_posix()]=dict(path=str(path),bytes=size,sha256=h.hexdigest())
    return records


def _native_answer(answer,cid,document):
    need(isinstance(answer,dict) and answer.get('status')=='completed' and
         isinstance(answer.get('pair_predictions'),list) and len(answer['pair_predictions'])==1 and
         isinstance(answer.get('observations'),list) and len(answer['observations'])==1,'One native pair result required')
    pair=answer['pair_predictions'][0];did=document['doc_id']
    need(isinstance(pair,dict) and set(pair)=={'claim_id','abstract_id','predicted_label','predicted_rationale','label_probs','rationale_probs'}
         and type(pair['claim_id']) is int and type(pair['abstract_id']) is int and pair['claim_id']==cid and pair['abstract_id']==did,
         'Native prediction identity/schema differs')
    probabilities=pair['label_probs'];rationale=pair['rationale_probs']
    valid=lambda p:type(p) in (int,float) and math.isfinite(p) and 0<=p<=1
    need(isinstance(probabilities,list) and len(probabilities)==3 and all(valid(p) for p in probabilities)
         and abs(math.fsum(probabilities)-1)<=1e-5,'Invalid native label probabilities')
    labels=('CONTRADICT','NEI','SUPPORT')
    need(pair['predicted_label']==labels[max(range(3),key=lambda i:probabilities[i])],'Native first-argmax label differs')
    need(isinstance(rationale,list) and len(rationale)==len(document['abstract']) and all(valid(p) for p in rationale)
         and isinstance(pair['predicted_rationale'],list) and all(type(i) is int for i in pair['predicted_rationale'])
         and pair['predicted_rationale']==[i for i,p in enumerate(rationale) if p>=.5],'Native rationale threshold/span differs')
    return answer


class Tracker:
    def __init__(self):self.requests=None;self.events=[]

    def rows(self):
        if self.requests is None:return []
        rows=[]
        for request in self.requests:
            for doc in request['documents']:
                cid,did=request['id'],doc['doc_id']
                events=[(event,info) for event,info in self.events if info.get('claim_id')==cid and info.get('abstract_id')==did]
                reserved=any(e=='pair_attempt_reserved' for e,d in events)
                started=any(e=='pair_started' for e,d in events);returned=any(e=='pair_completed' for e,d in events)
                terminals=[d['status'] for e,d in events if e=='pair_committed']
                state=terminals[-1] if terminals else 'returned_uncommitted' if returned else 'attempt_entered_no_terminal' if reserved else 'untouched'
                rows.append(dict(claim_id=cid,abstract_id=did,state=state,native_started=started,native_returned=returned,attempt_reserved=reserved))
        return rows

    def counts(self):
        if self.requests is None:return None
        rows=self.rows();commits=[d for e,d in self.events if e=='claim_committed']
        return dict(scheduled_claims=len(self.requests),scheduled_pairs=len(rows),completed_claims=len(commits),
            complete_prediction_claims=sum(d['status']=='produced' for d in commits),
            completed_pairs=sum(r['state']=='completed' for r in rows),input_unavailable_pairs=sum(r['state']=='input_unavailable' for r in rows),
            overlength_pairs=sum(r['state']=='overlength' for r in rows),
            unexpected_failed_pairs=sum(r['state'] in ('returned_uncommitted','attempt_entered_no_terminal') for r in rows))


def run_calibration(recipe_path, recipe_sha256, output, *, _solver_factory=None, _memory_reader=None):
    """Reserve one fresh output, execute once, seal success or retain failure.

    Injection arguments are fictional unit-test seams, never CLI options. The
    production coordinator must separately pin this entrypoint and interpreter.
    """
    output=local_path(Path(output).absolute())
    need(output.is_relative_to(ROOT) and output!=ROOT,'Calibration output must remain in workspace')
    output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter();cpu=time.process_time();tracker=Tracker()
    state=dict(writer=None,audit=None,finished=False,report=None,load_seconds=None,deadline_fired=False)
    timers=[];old_cache=sys.pycache_prefix

    def finish(error=None, hard=False):
        with _FINAL_LOCK:
            if state['finished']:return state['report']
            state['finished']=True
            for timer in timers:timer.cancel()
            writer=state['writer'];audit=state['audit'];counts=tracker.counts()
            if writer is not None:
                try:writer.event('calibration_failed' if error else 'calibration_completed',counts=counts)
                except BaseException as failure:
                    if error is None:error=failure
                try:writer.close()
                except BaseException as failure:
                    if error is None:error=failure
            if audit is not None:
                try:audit.close()
                except BaseException as failure:
                    if error is None:error=failure
            if error is None and (state['deadline_fired'] or (output/'DEADLINE.json').exists()):
                error=TimeoutError('Hard deadline interrupted finalization')
            if error is None and audit is not None and audit.denials:
                error=PermissionError('Recorded I/O denial prevents successful completion')
            report=dict(schema_version=1,kind='sc05_calibration_worker_status_v1',status='failed' if error else 'completed',
                counts=counts,recipe_sha256=recipe_sha256,pair_states=tracker.rows(),wall_seconds=time.perf_counter()-started,
                cpu_seconds=time.process_time()-cpu,load_seconds=state['load_seconds'],provider_cost_usd=0,
                references_read=False,scientific_scoring_performed=False,automatic_retry=False,hard_deadline=hard,
                io_denials=audit.denials if audit else 0,error=None if error is None else dict(type=type(error).__name__,message=str(error)[:2000]))
            try:
                report['files']=_inventory(output);_write(output/'STATUS.json',report)
                files=_inventory(output)
                _write(output/'RECEIPT.json',dict(schema_version=1,kind='sc05_calibration_worker_receipt_v1',
                    status=report['status'],recipe_sha256=recipe_sha256,files=files))
            except BaseException as final_error:
                try:_write(output/'FINALIZATION-FAILED.json',dict(status='failed',error_type=type(final_error).__name__,automatic_retry=False))
                except BaseException:pass
                if error is None:raise
            state['report']=report
            return report

    def deadline(seconds,label):
        def expire():
            # Never wait for the normal finalizer lock, close model handles or
            # hash output payloads here. The owner inventories partial output
            # after this process exits. A terminal contradiction is a failure.
            state['deadline_fired']=True
            marker=dict(schema_version=1,status='failed',recipe_sha256=recipe_sha256,
                        reason=label+' hard deadline exceeded',automatic_retry=False)
            try:
                try:_write(output/'DEADLINE.json',marker)
                except BaseException:pass
                status=dict(schema_version=1,kind='sc05_calibration_worker_status_v1',status='failed',
                    counts=tracker.counts(),recipe_sha256=recipe_sha256,pair_states=tracker.rows(),
                    hard_deadline=True,automatic_retry=False,files=None,
                    inventory_status='parent_must_inventory_partial_output',error=dict(type='TimeoutError',message=marker['reason']))
                try:_write(output/'STATUS.json',status)
                except BaseException:pass
            finally:os._exit(124)
        timer=threading.Timer(seconds,expire);timer.daemon=True;timers.append(timer);timer.start();return timer

    try:
        recipe_raw,recipe_proof=anchored(recipe_path,recipe_sha256,2*1024**2);recipe=parse_json(recipe_raw)
        files,runtime=_configuration(recipe)
        need(not any(p.is_relative_to(output) for p in files),'Output overlaps a granted input')
        audit=InputAudit(files|{local_path(recipe_path)},output,runtime);state['audit']=audit;audit.activate()
        sys.pycache_prefix=str(output/'import-cache')
        phase_timer=deadline(recipe['phase_seconds'],'worker phase')
        for spec in recipe['code_files']:capture(spec,8*1024**2)
        from experiments.scifact_comparison.worker import Writer,process_requests
        from experiments.scifact_comparison.inputs import validate_requests

        class RecordingWriter(Writer):
            def event(self,event,**details):
                with _FINAL_LOCK:
                    need(not state['finished'] or event in ('calibration_completed','calibration_failed'),'Worker already terminal')
                    super().event(event,**details);tracker.events.append((event,encode(details)))
        writer=RecordingWriter(output,recipe['output_bytes']);state['writer']=writer
        writer.publish('recipe.json',recipe);writer.event('calibration_reserved',recipe_sha256=recipe_sha256,purpose='calibrate',mode=recipe['mode'])
        receipt=parse_json(capture(recipe['model']['receipt'],8*1024**2));model_root=local_path(recipe['model']['acquisition_root'])
        need(receipt.get('status')=='PASS' and isinstance(receipt.get('files'),list),'Incomplete model acquisition')
        expected=[]
        for asset in receipt['files']:
            need(asset.get('status')=='completed','Incomplete model asset')
            path=local_path(model_root/asset['relative_path'])
            need(path.is_relative_to(model_root) and str(path)==asset['path'],'Model asset locator differs')
            expected.append(dict(path=str(path),bytes=asset['bytes'],sha256=asset['sha256']))
        need(sorted(expected,key=lambda p:p['path'])==sorted(recipe['model']['assets'],key=lambda p:p['path']),'Exact model asset grants differ from receipt')
        raw=capture(recipe['requests']);requests=[parse_json(line) for line in raw.splitlines()]
        validate_requests(requests,expected_schedule=recipe['schedule'],expected_k=5)
        tracker.requests=requests
        writer.event('inputs_admitted',requests_sha256=recipe['requests']['sha256'],claims=len(requests),pairs=len(requests)*5,references_read=False)
        if _solver_factory is None:
            from experiments.scifact_multivers.inference import LoadedSolver
            _solver_factory=LoadedSolver
        writer.event('model_load_started')
        solver=_solver_factory(str(model_root),recipe['model']['receipt']['sha256'],device=recipe['device'])
        state['load_seconds']=solver.load_seconds
        writer.publish('MODEL.json',dict(metadata=solver.metadata,device=solver.device_info,load_seconds=solver.load_seconds))
        writer.event('model_load_completed')

        class BoundedSolver:
            def predict(self,claims,corpus,*,pair_deadline_seconds,event):
                cid=claims[0]['id'];did=corpus[0]['doc_id']
                writer.event('pair_attempt_reserved',claim_id=cid,abstract_id=did,seconds=pair_deadline_seconds)
                timer=deadline(pair_deadline_seconds,'pair '+str(cid)+'/'+str(did))
                try:
                    answer=solver.predict(claims,corpus,pair_deadline_seconds=pair_deadline_seconds,event=event)
                    return _native_answer(answer,cid,corpus[0])
                finally:timer.cancel()
        counts=process_requests(requests,BoundedSolver(),writer,'calibration',pair_seconds=recipe['pair_seconds'],expected_k=5)
        need(counts==tracker.counts(),'Worker/journal accounting differs')
        need(counts['completed_pairs']==len(requests)*5 and counts['complete_prediction_claims']==len(requests),
             'Incomplete calibration pairs cannot finalize as successful inference')
        if _memory_reader is None:
            from experiments.scifact_multivers.runtime import process_memory
            _memory_reader=process_memory
        writer.publish('RESOURCES.json',dict(memory=_memory_reader(),wall_seconds=time.perf_counter()-started,
            cpu_seconds=time.process_time()-cpu,load_seconds=solver.load_seconds,provider_cost_usd=0,
            model_input_tokens=None,model_output_tokens=None,token_usage_reason='not_applicable_non_llm',counts=counts))
        need(audit.denials==0,'Recorded I/O denial prevents successful inference')
        report=finish()
        need(report['status']=='completed','Worker failed during finalization')
        return report
    except BaseException as error:
        finish(error)
        raise
    finally:
        for timer in timers:timer.cancel()
        sys.pycache_prefix=old_cache


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--recipe',required=True);parser.add_argument('--recipe-sha256',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    report=run_calibration(args.recipe,args.recipe_sha256,args.output)
    print(json.dumps(dict(status=report['status'],counts=report['counts'])))
