"""Read registry-scale evaluator frames from the existing five stopped restores.

Stream one source-qualified study per JSONL row. No import, network or model calls.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from asof.serde import sha256_file


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, obj):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')


def frame_query(snapshot, origin, endpoint):
    for d in [snapshot,origin,endpoint]:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',d):raise ValueError('ISO dates required')
    phase="regexp_replace(upper(coalesce(s.phase,'')), '[^A-Z0-9]', '', 'g')"
    phases="('PHASE1','PHASE1PHASE2','PHASE2','PHASE2PHASE3','PHASE3','PHASE4','EARLYPHASE1')"
    where=f"upper(s.study_type)='INTERVENTIONAL' AND {phase} IN {phases}"
    if snapshot!=origin:
        where+=f" AND {phase} IN ('PHASE1PHASE2','PHASE2','PHASE2PHASE3','PHASE3','PHASE4')"
        where+=f" AND (s.start_date IS NULL OR s.start_date<=DATE '{endpoint}') AND (s.start_date>DATE '{origin}' OR s.study_first_posted_date>DATE '{origin}' OR s.start_date IS NULL)"
    fields=["'study',json_build_object('nct_id',s.nct_id,'brief_title',s.brief_title,'official_title',s.official_title,'study_type',s.study_type,'phase',s.phase,'overall_status',s.overall_status,'start_date',s.start_date,'start_month_year',s.start_month_year,'start_date_type',s.start_date_type,'study_first_posted_date',s.study_first_posted_date,'last_update_posted_date',s.last_update_posted_date)"]
    joins=[]
    for table,columns in {
        'conditions':['id','nct_id','name'],
        'interventions':['id','nct_id','intervention_type','name','description'],
        'intervention_other_names':['id','nct_id','intervention_id','name'],
        'design_groups':['id','nct_id','group_type','title','description'],
        'design_group_interventions':['id','nct_id','design_group_id','intervention_id'],
        'sponsors':['id','nct_id','lead_or_collaborator','name'],
        'brief_summaries':['id','nct_id','description'],
    }.items():
        projection=','.join("'"+c+"',t."+c for c in columns)
        alias=table+'_bundle'
        fields.append(f"'{table}',coalesce({alias}.rows,'[]'::json)")
        joins.append(f"LEFT JOIN (SELECT t.nct_id,json_agg(json_build_object({projection}) ORDER BY t.id) AS rows FROM ctgov.{table} t JOIN selected anchor ON anchor.nct_id=t.nct_id GROUP BY t.nct_id) {alias} ON {alias}.nct_id=s.nct_id")
    return ("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\n"
        "WITH selected AS MATERIALIZED (SELECT s.* FROM ctgov.studies s WHERE "+where+") SELECT json_build_object("+','.join(fields)+") FROM selected s "+' '.join(joins)+" ORDER BY s.nct_id;\nROLLBACK;\n")


def metadata_query():
    return "SELECT json_build_object('database',current_database(),'data_directory',current_setting('data_directory'),'port',current_setting('port'),'transaction_read_only',current_setting('transaction_read_only'),'studies',(SELECT count(*) FROM ctgov.studies),'server_version',current_setting('server_version'));"


def validate_row(row, cutoff):
    study=row['study'];nct=study['nct_id']
    if not re.fullmatch(r'NCT\d{8}',nct):raise ValueError('Invalid NCT ID')
    for key in ['study_first_posted_date','last_update_posted_date']:
        value=study.get(key)
        if value and value>cutoff:raise ValueError('Posting after snapshot')
    for table,children in row.items():
        if table=='study':continue
        if any(c['nct_id']!=nct for c in children):raise ValueError('Cross-trial child')
    arms={a['id'] for a in row['design_groups']};drugs={d['id'] for d in row['interventions']}
    for link in row['design_group_interventions']:
        if link['design_group_id'] not in arms or link['intervention_id'] not in drugs:
            raise ValueError('Unresolved source arm link')
    return nct


def extract(protocol_path, output, resume_completed_from=None):
    root=Path.cwd();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    policy=load(protocol_path)
    if policy['protocol_id']!='registry-sizing-development-v0.4':raise ValueError('Wrong frozen protocol')
    freeze=load(root/'data/manifests/public/2026-10-17-registry-sizing-v04-freeze.json')
    if sha256_file(protocol_path)!=freeze['protocol']['sha256']:raise ValueError('Protocol differs from freeze')
    for proof in policy['input_anchors']:
        if sha256_file(root/proof['path'])!=proof['sha256']:raise ValueError('Changed input anchor')
    write(output/'execution-plan.json',{'protocol':str(Path(protocol_path).resolve()),'sha256':sha256_file(protocol_path),'role':'evaluation_only','mode':'read-only registry-scale frame extraction'})
    previous=None
    def event(stage, **kwargs):
        nonlocal previous
        obj={'at_utc':datetime.now(timezone.utc).isoformat(),'stage':stage,'previous':previous,**kwargs}
        digest=hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()
        with (output/'journal.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps({**obj,'sha256':digest})+'\n');f.flush();os.fsync(f.fileno())
        previous=digest
        print(json.dumps({'stage':stage,**kwargs}),flush=True)
    results=[]
    for index,snapshot in enumerate(policy['snapshots']):
        date=snapshot['date'];folder=output/date;folder.mkdir()
        if resume_completed_from:
            old=Path(resume_completed_from)/date;validation=old/'frame-validation.json'
            if validation.exists():
                prior=load(Path(resume_completed_from)/'execution-plan.json')
                row=load(validation)
                stopped=any(e.get('stage')=='server_stopped' and e.get('date')==date for e in map(json.loads,(Path(resume_completed_from)/'journal.jsonl').read_text().splitlines()))
                if prior['sha256']!=sha256_file(protocol_path) or not stopped or sha256_file(Path(row['path']))!=row['sha256']:
                    raise ValueError('Cannot reuse changed or incompletely stopped source frame')
                results.append(row);write(folder/'reused-frame.json',{'validation':str(validation.resolve()),'frame':row})
                event('completed_frame_reused',date=date,records=row['records'])
                continue
        restore=Path(snapshot['restore_root']);setup=(restore/'setup.py').read_text(encoding='utf-8')
        match=re.search(r"^BIN=Path\(r['\"]([^'\"]+)['\"]\)",setup,re.M)
        port=re.search(r"^PORT=['\"](\d+)['\"]",setup,re.M)
        if not match or not port:raise ValueError('Unrecognized retained setup recipe')
        pg=Path(match.group(1));port=port.group(1);started=False
        def command(name, args, env=None, allowed=(0,), timeout=120):
            with (folder/(name+'.stdout.log')).open('xb') as stdout,(folder/(name+'.stderr.log')).open('xb') as stderr:
                proc=subprocess.run(args,stdout=stdout,stderr=stderr,env=env,timeout=timeout,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if proc.returncode not in allowed:raise RuntimeError(name+' failed; inspect retained logs')
            return proc.returncode
        event('snapshot_started',date=date)
        try:
            status=command('status_before',[str(pg/'pg_ctl.exe'),'-D',str(restore/'pgdata'),'status'],allowed=(0,3))
            if status==0:raise RuntimeError('Server already running; not taking ownership')
            started=True
            command('start',[str(pg/'pg_ctl.exe'),'-D',str(restore/'pgdata'),'-l',str(folder/'server.log'),'-o','-c default_transaction_read_only=on','-w','-t','30','start'])
            env=os.environ.copy();env.update(PGHOST='127.0.0.1',PGPORT=port,PGUSER='aact_restore_admin',PGDATABASE='aact_snapshot',PGCLIENTENCODING='UTF8',
                PGPASSWORD=(restore/'.local-postgres-secrets/password.txt').read_text(),PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=1200000 -c enable_nestloop=off -c enable_mergejoin=off -c jit=off')
            command('metadata',[str(pg/'psql.exe'),'-XAtq','-v','ON_ERROR_STOP=1','-c',metadata_query()],env)
            meta=load(folder/'metadata.stdout.log')
            if meta['transaction_read_only']!='on' or Path(meta['data_directory']).resolve()!=(restore/'pgdata').resolve():
                raise ValueError('Wrong source database or read-only state')
            expected=[437548,457254,477238,499882,520688][index]
            if meta['studies']!=expected:raise ValueError('Source study inventory differs')
            sql=frame_query(date,policy['origin'],policy['occurrence_endpoint'])
            (folder/'frame.sql').write_text(sql,encoding='utf-8',newline='\n')
            event('query_started',date=date,source_studies=meta['studies'])
            begin=time.monotonic()
            command('frame',[str(pg/'psql.exe'),'-XAtq','-v','ON_ERROR_STOP=1','-f',str(folder/'frame.sql')],env,timeout=1300)
            event('query_finished',date=date,elapsed_seconds=time.monotonic()-begin)
            path=folder/'frame.stdout.log';count=0;last=None;h=hashlib.sha256()
            with path.open('rb') as f:
                for raw in f:
                    if len(raw)>8*1024*1024:raise ValueError('Source row exceeds 8 MiB')
                    row=json.loads(raw);nct=validate_row(row,date)
                    if last and nct<=last:raise ValueError('Duplicate/out-of-order frame rows')
                    last=nct;count+=1;h.update(raw)
            result={'snapshot_date':date,'records':count,'bytes':path.stat().st_size,'sha256':h.hexdigest(),'path':str(path),
                'source_studies':meta['studies'],'posting_and_child_checks':'passed','role':'evaluation_only'}
            write(folder/'frame-validation.json',result);results.append(result)
            event('frame_validated',date=date,records=count,bytes=path.stat().st_size)
        except BaseException as exc:
            event('failed',date=date,error_type=type(exc).__name__,error=str(exc))
            write(folder/'failure.json',{'type':type(exc).__name__,'error':str(exc),'automatic_retry':False})
            raise
        finally:
            if started:
                command('stop',[str(pg/'pg_ctl.exe'),'-D',str(restore/'pgdata'),'-m','fast','-w','-t','30','stop'])
                command('status_after',[str(pg/'pg_ctl.exe'),'-D',str(restore/'pgdata'),'status'],allowed=(3,))
                event('server_stopped',date=date)
    write(output/'frames.json',{'schema_version':1,'role':'evaluation_only','protocol_sha256':sha256_file(protocol_path),'snapshots':results})
    event('extraction_completed',snapshots=len(results),records=sum(x['records'] for x in results))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resume-completed-from',type=Path)
    a=p.parse_args();extract(a.protocol,a.output,a.resume_completed_from)
