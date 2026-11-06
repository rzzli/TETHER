"""Full-cohort stage accounting, without implicit resume or redispatch.

This module has no network/model implementation. Controllers supply one call
per reserved slot and retain the slot's inputs/outputs separately. A failed
stage preserves all unexecuted slots instead of shrinking the denominator.
"""
import math
import hashlib
from collections.abc import Mapping
from pathlib import Path
import time

from asof.atomic import publish_bytes
from asof.journal import RunJournal,read_chain
from asof.serde import canonical,encode,freeze,parse_json
from .codecs import need,digest

ARMS=('L/O','E/O','L/R','E/R')
STAGES=('expand','collect','rank','answer','supplied')


def slots(ids,stage):
    need(isinstance(ids,(tuple,list)) and ids and len(set(ids))==len(ids) and
         all(isinstance(i,str) and i for i in ids),'Unique full task schedule required')
    need(stage in STAGES,'Unknown stage')
    branches=('L','E') if stage in ('collect','rank') else ARMS if stage=='answer' else ('shared',)
    return tuple(dict(ordinal=n,id=cid,branch=branch) for n,(cid,branch) in
                 enumerate((cid,b) for cid in ids for b in branches))


def journal_inventory(root):
    root=Path(root)
    result={}
    for p in root.rglob('*'):
        need(not p.is_symlink(),'Symlink in stage output')
        if not p.is_file() or p==root/'STAGE-RECEIPT.json':continue
        need(len(result)<40000 and p.stat().st_size<=128*1024**2,'Stage inventory count/file bound')
        with p.open('rb') as stream:hashed=hashlib.file_digest(stream,'sha256').hexdigest()
        result[p.relative_to(root).as_posix()]=dict(bytes=p.stat().st_size,sha256=hashed)
    return result


class Stage:
    """Durably reserve each slot before invoking a caller-supplied operation.

    No API resumes this object from disk. Reopening an existing output fails.
    Recovery is read-only and returns unfinished attempts as uncertain.
    """
    def __init__(self,ids,stage,output,*,seconds,clock=time.monotonic):
        self.schedule=slots(ids,stage)
        need(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,'Finite stage budget')
        self.clock=clock;self.started=clock();self.deadline=self.started+seconds
        self.root=Path(output);self.journal=RunJournal(self.root,kind='build')
        self.rows=[dict(**s,status='unexecuted',reason=None,product=None) for s in self.schedule]
        self.cursor=0;self.closed=False;self.failed=False
        self.config=freeze(dict(kind='sc04_stage_v1',stage=stage,ids=list(ids),schedule=self.schedule,seconds=seconds))
        publish_bytes(self.root/'CONFIG.json',canonical(self.config))
        self.journal.append('stage_configured',config_sha256=digest(canonical(self.config)))

    def call(self,operation):
        need(not self.closed and not self.failed,'Stage closed/failed; no retry')
        need(self.cursor<len(self.rows),'Schedule exhausted')
        need(self.clock()<self.deadline,'Stage deadline before dispatch')
        index=self.cursor;row=self.rows[index]
        # Reserve before anything potentially paid, including validation that
        # may be implemented inside operation. Once entered, this slot cannot
        # be called again regardless of its terminal response.
        self.journal.append('slot_reserved',**self.schedule[index])
        row['status']='entered';self.cursor+=1
        try:
            result=operation(freeze(self.schedule[index]),self.deadline)
            need(isinstance(result,Mapping) and set(result)=={'status','reason','product'} and
                 result['status'] in ('completed','fallback','not_applicable'),'Explicit stage operation disposition required')
            need(self.clock()<self.deadline,'Stage deadline after operation')
            row.update(encode(result))
            path=f'slots/{index:04d}.json'
            publish_bytes(self.root/path,canonical(row))
            self.journal.append('slot_terminal',ordinal=index,slot_sha256=digest(canonical(row)),path=path,status=row['status'])
            return freeze(row)
        except BaseException as error:
            self.failed=True
            row.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',reason=type(error).__name__,product=None)
            try:
                publish_bytes(self.root/f'failures/{index:04d}.json',canonical(row))
                self.journal.append('slot_failed',ordinal=index,status=row['status'],reason=row['reason'])
            except BaseException as secondary:error.add_note('Slot failure retention: '+type(secondary).__name__)
            raise

    def finish(self):
        need(not self.closed,'Stage already finalized')
        complete=not self.failed and self.cursor==len(self.schedule) and self.clock()<self.deadline
        report=freeze(dict(status='complete' if complete else 'partial',scheduled=len(self.schedule),
             entered=self.cursor,unexecuted=len(self.schedule)-self.cursor,rows=self.rows,wall_seconds=self.clock()-self.started))
        try:
            publish_bytes(self.root/'REPORT.json',canonical(report))
            self.journal.append('stage_finalized',status=report['status'],report_sha256=digest(canonical(report)))
            self.journal.close()
            publish_bytes(self.root/'STAGE-RECEIPT.json',canonical(dict(status=report['status'],files=journal_inventory(self.root))))
            if complete and self.clock()>=self.deadline:
                publish_bytes(self.root/'FINALIZATION-FAILED.json',canonical(dict(reason='stage_deadline_during_finalization')))
                raise TimeoutError('Stage finalization exceeded its deadline')
            return report
        finally:
            self.closed=True;self.journal.close()


def inspect(root):
    """Read-only recovery: missing terminal evidence means uncertainty, not retry."""
    root=Path(root);config=parse_json((root/'CONFIG.json').read_bytes())
    expected=slots(config['ids'],config['stage'])
    need(canonical(config['schedule'])==canonical(expected),'Stage schedule changed')
    events=read_chain(root/'journal.jsonl',allow_incomplete_tail=True)
    need(len(events)>=2 and events[0]['event']=='build_reserved' and events[1]['event']=='stage_configured'
         and events[1]['details']['config_sha256']==digest((root/'CONFIG.json').read_bytes()),'Stage configuration binding')
    states=[dict(**s,status='unexecuted',reason=None,product=None) for s in expected]
    cursor=0;active=None;terminal=False;failed=False
    for event in events[2:]:
        kind,details=event['event'],event['details']
        need(not terminal,'Extra event after stage finalization')
        if kind=='slot_reserved':
            need(not failed and active is None and cursor<len(expected) and encode(details)==expected[cursor],'Unexpected slot reservation')
            active=cursor;states[cursor]['status']='uncertain';cursor+=1
        elif kind=='slot_terminal':
            need(active is not None and details['ordinal']==active,'Unexpected slot terminal')
            path=f'slots/{active:04d}.json';need(details['path']==path,'Slot path substitution')
            raw=(root/path).read_bytes();row=parse_json(raw)
            need(digest(raw)==details['slot_sha256'] and row['status']==details['status'] and
                 row['status'] in ('completed','fallback','not_applicable'),'Slot terminal binding')
            need(all(row[k]==v for k,v in expected[active].items()),'Slot identity differs')
            states[active]=row;active=None
        elif kind=='slot_failed':
            need(active is not None and details['ordinal']==active and details['status'] in ('failed','interrupted'),'Unexpected slot failure')
            row=parse_json((root/f'failures/{active:04d}.json').read_bytes())
            need(all(row[k]==v for k,v in expected[active].items()) and row['status']==details['status']
                 and row['reason']==details['reason'] and row['product'] is None,'Failure record binding')
            states[active]=row;active=None;failed=True
        elif kind=='stage_finalized':
            need(active is None,'Finalized with uncertain dispatch')
            report=parse_json((root/'REPORT.json').read_bytes())
            need(details['report_sha256']==digest((root/'REPORT.json').read_bytes()) and details['status']==report['status'],'Stage report binding')
            need(report['scheduled']==len(expected) and report['entered']==cursor and report['unexecuted']==len(expected)-cursor,'Stage report accounting')
            need(canonical(report['rows'])==canonical(states),'Report/journal states differ')
            need(report['status'] in ('partial','complete') and
                 (report['status']=='partial' or (not failed and cursor==len(expected))),'False complete stage')
            need(type(report['wall_seconds']) in (int,float) and math.isfinite(report['wall_seconds']) and report['wall_seconds']>=0
                 and (report['status']=='partial' or report['wall_seconds']<config['seconds']),'Stage timing bounds')
            terminal=True
        else:raise ValueError('Unexpected stage journal event: '+kind)
    return freeze(dict(finalized=terminal,rows=states,scheduled=len(expected),entered=cursor,
                       recovery='Read only; uncertain slots are never automatically redispatched'))


def verify(root,expected_receipt_sha256):
    root=Path(root);raw=(root/'STAGE-RECEIPT.json').read_bytes()
    need(digest(raw)==expected_receipt_sha256,'Stage external receipt anchor')
    receipt=parse_json(raw)
    need(receipt['files']==journal_inventory(root),'Exact stage byte inventory')
    state=inspect(root)
    report=parse_json((root/'REPORT.json').read_bytes())
    need(state['finalized'] and receipt['status']==report['status'],'Stage completion status')
    return state
