"""SC05 all-scheduled stage journal with exclusive reservation and no resume."""
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID,uuid4
import math
import time

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal,read_chain
from tether_engine.serde import canonical,encode,freeze,parse_json,safe_child
from tether_engine.study.stable_read import checked_path,deadline_check,hash_file,read_file,stable_files
from . import contracts

PHASES=('critic','refinement_collect','pair_prepare','repair','removal')
PARENTS=dict(critic=(),refinement_collect=('critic',),pair_prepare=('critic','refinement_collect'),
             repair=('pair_prepare',),removal=('pair_prepare',))
ALLOWED={'critic':('completed','capacity','codec_failure'),'refinement_collect':('completed','unavailable'),
         'pair_prepare':('completed',),'repair':('completed','capacity','codec_failure'),'removal':('completed','capacity','codec_failure')}
ACCOUNT_FIELDS=('generation_calls','measured_input_tokens','measured_output_tokens','reserved_input_tokens',
                'reserved_output_tokens','source_http_requests','measured_response_bytes','safety_accounted_bytes')


def slots(ids,phase,*,purpose,execution_namespace):
    ids=tuple(ids)
    contracts.need(phase in PHASES and purpose in ('production','fictional_qualification'),'Explicit SC05 phase/purpose')
    contracts.need(len(ids)==(199 if purpose=='production' else 2) and len(set(ids))==len(ids),'Full SC05 schedule required')
    contracts.need(all(isinstance(i,str) and str(UUID(i))==i for i in ids),'Canonical scheduled identities')
    contracts.need(isinstance(execution_namespace,str) and str(UUID(execution_namespace))==execution_namespace,'Canonical execution namespace')
    return freeze([dict(ordinal=n,id=ident,phase=phase,execution_id=f'{execution_namespace}-{phase}-{n:04d}') for n,ident in enumerate(ids)])


def limits(phase):
    contracts.need(phase in PHASES,'Unknown phase')
    model=phase in ('critic','repair','removal');source=phase=='refinement_collect'
    return freeze(dict(generation_calls=int(model),reserved_input_tokens=16128 if model else 0,
        reserved_output_tokens=256 if model else 0,source_http_requests=5 if source else 0,
        safety_accounted_bytes=8*1024**2 if source else 0,provider_cost_usd=0))


def accounting(value,phase,*,status=None):
    contracts.need(isinstance(value,Mapping) and set(value)==set(ACCOUNT_FIELDS)|{'provider_cost_usd'},'Explicit per-cell accounting')
    contracts.need(all(type(value[k]) is int and value[k]>=0 for k in ACCOUNT_FIELDS),'Nonnegative integral cell accounting')
    contracts.need(type(value['provider_cost_usd']) in (int,float) and value['provider_cost_usd']==0,'Provider spending is zero')
    caps=limits(phase)
    for key in ('generation_calls','reserved_input_tokens','reserved_output_tokens','source_http_requests','safety_accounted_bytes'):
        contracts.need(value[key]<=caps[key],'Cell budget exceeded: '+key)
    contracts.need(value['measured_input_tokens']<=value['reserved_input_tokens'] and
        value['measured_output_tokens']<=value['reserved_output_tokens'] and
        value['measured_response_bytes']<=value['safety_accounted_bytes'],'Measured usage exceeds conservative reservation')
    if value['generation_calls']==0:
        contracts.need(not any(value[k] for k in ('measured_input_tokens','measured_output_tokens','reserved_input_tokens','reserved_output_tokens')),
                       'Nongeneration cannot claim model tokens')
    if status is not None:
        contracts.need(status in ALLOWED[phase],'Phase-specific accounting disposition')
        if phase in ('critic','repair','removal'):
            contracts.need(value['generation_calls']==int(status!='capacity'),'Native status/generation accounting differs')
            if status!='capacity':contracts.need(value['reserved_output_tokens']==256,'Native output reservation differs')
        if phase=='refinement_collect':
            if status=='unavailable':contracts.need(not any(value[k] for k in ACCOUNT_FIELDS),'Unavailable source collection cannot claim work')
            else:contracts.need(2<=value['source_http_requests']<=5,'Complete source collection requires both metadata slots')
    return freeze(value)


def zero_accounting():return freeze(dict(**{key:0 for key in ACCOUNT_FIELDS},provider_cost_usd=0))


def _inventory(root,end):
    result={};total=0
    for path in sorted(root.rglob('*')):
        deadline_check(end)
        if path.is_dir():continue
        name=path.relative_to(root).as_posix();checked_path(root,name)
        if name=='STAGE-RECEIPT.json':continue
        proof=hash_file(path,end);total+=proof['bytes']
        contracts.need(len(result)<20000 and proof['bytes']<=128*1024**2 and total<=8*1024**3,'Bounded stage file inventory')
        result[name]=proof
    return freeze(result)


def _summary(rows,config,elapsed):
    known=[r['accounting'] for r in rows if r['accounting'] is not None]
    uncertain=[r['id'] for r in rows if r['status'] in ('failed','interrupted','entered')]
    return freeze(dict(kind='tether_refinement_stage_report_v1',phase=config['phase'],purpose=config['purpose'],
        status='complete' if all(r['status'] in ('completed','capacity','codec_failure','unavailable') for r in rows) and elapsed<config['seconds'] else 'incomplete',
        scheduled=len(rows),entered=sum(r['status']!='unexecuted' for r in rows),unexecuted=sum(r['status']=='unexecuted' for r in rows),
        rows=rows,wall_seconds=elapsed,
        accounting=dict(known_totals={k:sum(a[k] for a in known) for k in ACCOUNT_FIELDS},provider_cost_usd=0,
            uncertain_cells=uncertain,measurements_complete=not uncertain,
            uncertain_per_cell_ceiling=config['cell_limits'],historical_work_included=False),automatic_retry=False))


class Stage:
    def __init__(self,ids,phase,output,*,purpose,seconds,clock=time.monotonic):
        contracts.need(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,'Finite stage deadline')
        self.clock=clock;self.started=clock();self.deadline=self.started+seconds
        namespace=str(uuid4());ordered=slots(ids,phase,purpose=purpose,execution_namespace=namespace)
        self.config=freeze(dict(kind='tether_refinement_stage_v1',phase=phase,purpose=purpose,ids=tuple(ids),
            execution_namespace=namespace,schedule=ordered,seconds=seconds,cell_limits=limits(phase)))
        self.journal=RunJournal(Path(output),kind='build');self.root=self.journal.output
        self.rows=[dict(**slot,status='unexecuted',reason=None,product=None,accounting=None) for slot in ordered]
        self.cursor=0;self.failed=False;self.closed=False
        publish_bytes(self.root/'CONFIG.json',canonical(self.config))
        self.journal.append('refinement_stage_configured',config_sha256=contracts.codecs.digest(canonical(self.config)))

    def call(self,operation):
        contracts.need(not self.closed and not self.failed and self.cursor<len(self.rows),'Stage closed/failed/exhausted; no retry')
        contracts.need(self.clock()<self.deadline,'Stage deadline before slot reservation')
        row=self.rows[self.cursor];slot=self.config['schedule'][self.cursor]
        self.journal.append('refinement_slot_reserved',slot=slot,limits=self.config['cell_limits'])
        self.cursor+=1;row['status']='entered'
        try:
            result=operation(slot,self.deadline)
            contracts.need(isinstance(result,Mapping) and set(result)=={'status','reason','product','accounting'},'Exact stage operation result')
            contracts.need(result['status'] in ALLOWED[self.config['phase']],'Explicit phase disposition')
            checked=accounting(result['accounting'],self.config['phase'],status=result['status'])
            contracts.need(self.clock()<self.deadline,'Stage deadline after operation')
            row.update(encode(result));row['accounting']=encode(checked)
            name=f'slots/{slot["ordinal"]:04d}.json';publish_bytes(self.root/name,canonical(row))
            self.journal.append('refinement_slot_terminal',ordinal=slot['ordinal'],path=name,
                slot_sha256=contracts.codecs.digest(canonical(row)),status=row['status'])
            return freeze(row)
        except BaseException as error:
            self.failed=True;row.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                reason=type(error).__name__,product=None,accounting=None)
            try:
                name=f'failures/{slot["ordinal"]:04d}.json';publish_bytes(self.root/name,canonical(row))
                self.journal.append('refinement_slot_failed',ordinal=slot['ordinal'],path=name,
                    slot_sha256=contracts.codecs.digest(canonical(row)),status=row['status'],reason=row['reason'])
            except BaseException as failure:error.add_note('Failed-slot persistence: '+type(failure).__name__)
            raise

    def finish(self):
        contracts.need(not self.closed,'Stage already finalized')
        elapsed=self.clock()-self.started
        contracts.need(math.isfinite(elapsed) and elapsed>=0,'Nonnegative elapsed duration')
        report=_summary(self.rows,self.config,elapsed)
        try:
            publish_bytes(self.root/'REPORT.json',canonical(report))
            self.journal.append('refinement_stage_finalized',status=report['status'],report_sha256=contracts.codecs.digest(canonical(report)))
            self.journal.close()
            # Failed attempts still receive a readable receipt. This separate
            # bounded persistence window never authorizes another call.
            inventory=_inventory(self.root,time.monotonic()+120)
            seal_elapsed=self.clock()-self.started
            receipt=dict(kind='tether_refinement_stage_receipt_v1',status=report['status'],files=inventory,
                         seal_elapsed_seconds=seal_elapsed,automatic_retry=False)
            publish_bytes(self.root/'STAGE-RECEIPT.json',canonical(receipt))
            if report['status']=='complete' and not 0<=seal_elapsed<self.config['seconds']:
                publish_bytes(self.root/'FINALIZATION-FAILED.json',canonical(dict(reason='stage_deadline_during_sealing')))
                raise TimeoutError('Stage deadline during sealing')
            return report
        finally:self.closed=True;self.journal.close()


def verify(root,receipt_sha256,*,expected_ids=None,expected_phase=None,purpose=None,deadline=None):
    root=Path(root).absolute();end=time.monotonic()+120 if deadline is None else deadline
    receipt_path=checked_path(root,'STAGE-RECEIPT.json')
    with stable_files((receipt_path,),deadline=end):
        raw=read_file(receipt_path,end,8*1024**2)
        contracts.need(contracts.codecs.digest(raw)==receipt_sha256,'Stage external receipt anchor')
        receipt=parse_json(raw)
        contracts.need(set(receipt)=={'kind','status','files','seal_elapsed_seconds','automatic_retry'} and
            receipt['kind']=='tether_refinement_stage_receipt_v1' and receipt['automatic_retry'] is False,'Stage receipt fields')
        paths=tuple(checked_path(root,n) for n in receipt['files'])
        with stable_files(paths,deadline=end):
            contracts.need(canonical(_inventory(root,end))==canonical(receipt['files']),'Exact stage byte inventory')
            config=parse_json(read_file(root/'CONFIG.json',end,1024**2));report=parse_json(read_file(root/'REPORT.json',end,64*1024**2))
            ordered=slots(config['ids'],config['phase'],purpose=config['purpose'],execution_namespace=config['execution_namespace'])
            contracts.need(config['kind']=='tether_refinement_stage_v1' and canonical(config['schedule'])==canonical(ordered)
                and config['cell_limits']==encode(limits(config['phase'])),'Stage fixed schedule/configuration')
            if expected_ids is not None:contracts.need(tuple(config['ids'])==tuple(expected_ids),'Required complete parent schedule')
            if expected_phase is not None:contracts.need(config['phase']==expected_phase,'Parent phase differs')
            if purpose is not None:contracts.need(config['purpose']==purpose,'Parent purpose differs')
            contracts.need(type(config['seconds']) in (int,float) and math.isfinite(config['seconds']) and config['seconds']>0,'Stage time budget')
            elapsed=report['wall_seconds'];seal=receipt['seal_elapsed_seconds']
            contracts.need(type(elapsed) in (int,float) and type(seal) in (int,float) and
                math.isfinite(elapsed) and math.isfinite(seal) and 0<=elapsed<=seal,'Stage nonnegative elapsed accounting')
            rows=report['rows'];contracts.need(len(rows)==len(ordered),'All scheduled rows retained')
            events=read_chain(root/'journal.jsonl')
            contracts.need(events[0]['event']=='build_reserved' and events[1]['event']=='refinement_stage_configured'
                and events[1]['details']==dict(config_sha256=contracts.codecs.digest(canonical(config))),'Stage journal configuration')
            cursor=2;stopped=False
            for slot,row in zip(ordered,rows):
                contracts.need(set(row)==set(slot)|{'status','reason','product','accounting'} and
                    all(row[k]==v for k,v in slot.items()),'Scheduled row identity')
                if row['status']=='unexecuted':
                    stopped=True;contracts.need(row['product'] is None and row['accounting'] is None and row['reason'] is None,'Unexecuted row state');continue
                contracts.need(not stopped and events[cursor]['event']=='refinement_slot_reserved'
                    and events[cursor]['details']==dict(slot=encode(slot),limits=config['cell_limits']),'Exclusive sequential slot reservation')
                cursor+=1
                failed=row['status'] in ('failed','interrupted')
                if failed:
                    stopped=True;contracts.need(row['accounting'] is None and row['product'] is None,'Uncertain failure cannot claim known accounting')
                else:
                    contracts.need(row['status'] in ALLOWED[config['phase']],'Phase-specific terminal disposition')
                    accounting(row['accounting'],config['phase'],status=row['status'])
                name=f'{"failures" if failed else "slots"}/{slot["ordinal"]:04d}.json'
                actual=parse_json(read_file(checked_path(root,name),end,32*1024**2))
                contracts.need(actual==row,'Journal/row artifact agreement')
                detail=dict(ordinal=slot['ordinal'],path=name,slot_sha256=contracts.codecs.digest(canonical(row)),status=row['status'])
                if failed:detail['reason']=row['reason']
                contracts.need(events[cursor]['event']==('refinement_slot_failed' if failed else 'refinement_slot_terminal')
                    and events[cursor]['details']==detail,'Terminal row accounting journal');cursor+=1
            rebuilt=_summary(rows,config,elapsed)
            contracts.need(canonical(rebuilt)==canonical(report) and receipt['status']==report['status'],'Reconstructed stage counts/accounting')
            contracts.need(len(events)==cursor+1 and events[cursor]['event']=='refinement_stage_finalized'
                and events[cursor]['details']==dict(status=report['status'],report_sha256=contracts.codecs.digest(canonical(report))),
                'Exact stage journal terminal')
            if report['status']=='complete':
                contracts.need(seal<config['seconds'],'Complete stage exceeds deadline')
                contracts.need(not any(Path(n).name in ('FAILURE.json','FINALIZATION-FAILED.json','DEADLINE.json') for n in receipt['files']),
                               'Failure marker in complete stage')
            return freeze(dict(config=config,report=report,root=str(root),receipt_sha256=receipt_sha256))
