"""Full-schedule durable stages for the separate six/199-case condition.

Accounting rules remain shared with the established bounded model calls. The
schedule and stage identity are new; no old reservation or answer is adopted.
"""
from pathlib import Path
from uuid import UUID, uuid4
import math
import time
from collections.abc import Mapping

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import canonical, encode, freeze, parse_json
from tether_engine.study.stable_read import checked_path, deadline_check, hash_file, read_file, stable_files
from experiments.litqa_refinement import contracts
from experiments.litqa_refinement.schedule import ACCOUNT_FIELDS, accounting, zero_accounting
from . import contracts as scope

PHASES = scope.PHASES
ALLOWED = {phase: scope.TERMINAL_STATUSES for phase in PHASES}


def slots(ids, phase, *, purpose, execution_namespace):
    ids = scope.schedule(ids, purpose)
    scope.need(phase in PHASES, 'Evidence-first paired phase required')
    scope.need(isinstance(execution_namespace, str) and str(UUID(execution_namespace)) == execution_namespace,
               'Canonical execution namespace')
    return freeze([dict(ordinal=i, id=key, phase=phase, execution_id=f'{execution_namespace}-{phase}-{i:04d}')
                   for i, key in enumerate(ids)])


def limits(phase):
    scope.need(phase in PHASES, 'Unknown evidence-first phase')
    return scope.CELL_LIMITS

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
    return freeze(dict(kind='sc05_evidence_first_stage_report_v1',phase=config['phase'],purpose=config['purpose'],
        status='complete' if all(r['status'] in ('completed','capacity','codec_failure','unavailable') for r in rows) and elapsed<config['seconds'] else 'incomplete',
        scheduled=len(rows),entered=sum(r['status']!='unexecuted' for r in rows),unexecuted=sum(r['status']=='unexecuted' for r in rows),
        rows=rows,wall_seconds=elapsed,
        accounting=dict(known_totals={k:sum(a[k] for a in known) for k in ACCOUNT_FIELDS},provider_cost_usd=0,
            uncertain_cells=uncertain,measurements_complete=not uncertain,
            uncertain_per_cell_ceiling=config['cell_limits'],historical_work_included=False),automatic_retry=False))


class Stage:
    def __init__(self,ids,phase,output,*,purpose,seconds,clock=time.monotonic):
        contracts.need(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,'Finite stage deadline')
        scope.need(phase in PHASES, 'Paired phase required')
        ceiling = scope.budgets(purpose)['phase_seconds'][phase]
        if phase == 'repair': ceiling = min(ceiling, scope.budgets(purpose)['repair_stage_seconds'])
        scope.need(seconds <= ceiling, 'Stage cannot enlarge the approved phase allowance')
        self.clock=clock;self.started=clock();self.deadline=self.started+seconds
        namespace=str(uuid4());ordered=slots(ids,phase,purpose=purpose,execution_namespace=namespace)
        self.config=freeze(dict(kind='sc05_evidence_first_stage_v1',phase=phase,purpose=purpose,ids=tuple(ids),
            execution_namespace=namespace,schedule=ordered,seconds=seconds,cell_limits=limits(phase)))
        self.journal=RunJournal(Path(output),kind='build');self.root=self.journal.output
        self.rows=[dict(**slot,status='unexecuted',reason=None,product=None,accounting=None) for slot in ordered]
        self.cursor=0;self.failed=False;self.closed=False
        publish_bytes(self.root/'CONFIG.json',canonical(self.config))
        self.journal.append('evidence_first_stage_configured',config_sha256=contracts.codecs.digest(canonical(self.config)))

    def call(self,operation):
        contracts.need(not self.closed and not self.failed and self.cursor<len(self.rows),'Stage closed/failed/exhausted; no retry')
        contracts.need(self.clock()<self.deadline,'Stage deadline before slot reservation')
        row=self.rows[self.cursor];slot=self.config['schedule'][self.cursor]
        self.journal.append('evidence_first_slot_reserved',slot=slot,limits=self.config['cell_limits'])
        self.cursor+=1;row['status']='entered'
        try:
            result=operation(slot,self.deadline)
            contracts.need(isinstance(result,Mapping) and set(result)=={'status','reason','product','accounting'},'Exact stage operation result')
            contracts.need(result['status'] in ALLOWED[self.config['phase']],'Explicit phase disposition')
            checked=accounting(result['accounting'],self.config['phase'],status=result['status'])
            contracts.need(self.clock()<self.deadline,'Stage deadline after operation')
            row.update(encode(result));row['accounting']=encode(checked)
            name=f'slots/{slot["ordinal"]:04d}.json';publish_bytes(self.root/name,canonical(row))
            self.journal.append('evidence_first_slot_terminal',ordinal=slot['ordinal'],path=name,
                slot_sha256=contracts.codecs.digest(canonical(row)),status=row['status'])
            return freeze(row)
        except BaseException as error:
            self.failed=True;row.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                reason=type(error).__name__,product=None,accounting=None)
            try:
                name=f'failures/{slot["ordinal"]:04d}.json';publish_bytes(self.root/name,canonical(row))
                self.journal.append('evidence_first_slot_failed',ordinal=slot['ordinal'],path=name,
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
            self.journal.append('evidence_first_stage_finalized',status=report['status'],report_sha256=contracts.codecs.digest(canonical(report)))
            self.journal.close()
            # Failed attempts still receive a readable receipt. This separate
            # bounded persistence window never authorizes another call.
            inventory=_inventory(self.root,time.monotonic()+120)
            seal_elapsed=self.clock()-self.started
            receipt=dict(kind='sc05_evidence_first_stage_receipt_v1',status=report['status'],files=inventory,
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
            receipt['kind']=='sc05_evidence_first_stage_receipt_v1' and receipt['automatic_retry'] is False,'Stage receipt fields')
        paths=tuple(checked_path(root,n) for n in receipt['files'])
        with stable_files(paths,deadline=end):
            contracts.need(canonical(_inventory(root,end))==canonical(receipt['files']),'Exact stage byte inventory')
            config=parse_json(read_file(root/'CONFIG.json',end,1024**2));report=parse_json(read_file(root/'REPORT.json',end,64*1024**2))
            ordered=slots(config['ids'],config['phase'],purpose=config['purpose'],execution_namespace=config['execution_namespace'])
            contracts.need(config['kind']=='sc05_evidence_first_stage_v1' and canonical(config['schedule'])==canonical(ordered)
                and config['cell_limits']==encode(limits(config['phase'])),'Stage fixed schedule/configuration')
            if expected_ids is not None:contracts.need(tuple(config['ids'])==tuple(expected_ids),'Required complete parent schedule')
            if expected_phase is not None:contracts.need(config['phase']==expected_phase,'Parent phase differs')
            if purpose is not None:contracts.need(config['purpose']==purpose,'Parent purpose differs')
            contracts.need(type(config['seconds']) in (int,float) and math.isfinite(config['seconds']) and config['seconds']>0,'Stage time budget')
            ceiling = scope.budgets(config['purpose'])['phase_seconds'][config['phase']]
            if config['phase'] == 'repair': ceiling = min(ceiling, scope.budgets(config['purpose'])['repair_stage_seconds'])
            scope.need(config['seconds'] <= ceiling, 'Stage exceeds prospective allowance')
            elapsed=report['wall_seconds'];seal=receipt['seal_elapsed_seconds']
            contracts.need(type(elapsed) in (int,float) and type(seal) in (int,float) and
                math.isfinite(elapsed) and math.isfinite(seal) and 0<=elapsed<=seal,'Stage nonnegative elapsed accounting')
            rows=report['rows'];contracts.need(len(rows)==len(ordered),'All scheduled rows retained')
            events=read_chain(root/'journal.jsonl')
            contracts.need(events[0]['event']=='build_reserved' and events[1]['event']=='evidence_first_stage_configured'
                and events[1]['details']==dict(config_sha256=contracts.codecs.digest(canonical(config))),'Stage journal configuration')
            cursor=2;stopped=False
            for slot,row in zip(ordered,rows):
                contracts.need(set(row)==set(slot)|{'status','reason','product','accounting'} and
                    all(row[k]==v for k,v in slot.items()),'Scheduled row identity')
                if row['status']=='unexecuted':
                    stopped=True;contracts.need(row['product'] is None and row['accounting'] is None and row['reason'] is None,'Unexecuted row state');continue
                contracts.need(not stopped and events[cursor]['event']=='evidence_first_slot_reserved'
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
                contracts.need(events[cursor]['event']==('evidence_first_slot_failed' if failed else 'evidence_first_slot_terminal')
                    and events[cursor]['details']==detail,'Terminal row accounting journal');cursor+=1
            rebuilt=_summary(rows,config,elapsed)
            contracts.need(canonical(rebuilt)==canonical(report) and receipt['status']==report['status'],'Reconstructed stage counts/accounting')
            contracts.need(len(events)==cursor+1 and events[cursor]['event']=='evidence_first_stage_finalized'
                and events[cursor]['details']==dict(status=report['status'],report_sha256=contracts.codecs.digest(canonical(report))),
                'Exact stage journal terminal')
            if report['status']=='complete':
                contracts.need(seal<config['seconds'],'Complete stage exceeds deadline')
                contracts.need(not any(Path(n).name in ('FAILURE.json','FINALIZATION-FAILED.json','DEADLINE.json') for n in receipt['files']),
                               'Failure marker in complete stage')
            return freeze(dict(config=config,report=report,root=str(root),receipt_sha256=receipt_sha256))
