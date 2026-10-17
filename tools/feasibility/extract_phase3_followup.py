"""Read a bounded linked-trial set from an existing stopped AACT restore.

No import, source edit, credentials in receipts, or clinical label assignment.
The temporary server uses read-only transactions and is stopped in finally.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from tools.feasibility.program_outcomes import load, sha, verify_manifest
from tools.feasibility.restore_intermediate_aact import sha as stream_sha


TABLES = ['conditions','interventions','intervention_other_names','design_groups',
          'design_group_interventions','design_outcomes','eligibilities',
          'brief_summaries','detailed_descriptions','sponsors','id_information','study_references']


def query(ids):
    if not ids or len(ids)>10 or len(set(ids))!=len(ids) or any(not re.fullmatch(r'NCT[0-9]{8}',x) for x in ids):
        raise ValueError('One to ten distinct valid NCT IDs required')
    fields=["'study',row_to_json(s)"]
    for table in TABLES:
        fields.append(f"'{table}',(SELECT coalesce(json_agg(row_to_json(t) ORDER BY t.id),'[]'::json) FROM ctgov.{table} t WHERE t.nct_id=s.nct_id)")
    return ("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\n"
            "SELECT json_build_object('database',current_database(),'server_version',current_setting('server_version'),"
            "'transaction_read_only',current_setting('transaction_read_only'),'port',current_setting('port'),"
            "'data_directory',current_setting('data_directory'),'studies_count',(SELECT count(*) FROM ctgov.studies),"
            "'records',coalesce((SELECT json_agg(q.record ORDER BY q.nct_id) FROM (SELECT s.nct_id,json_build_object("+
            ','.join(fields)+") AS record FROM ctgov.studies s WHERE s.nct_id IN ("+
            ','.join("'"+i+"'" for i in ids)+")) q),'[]'::json));\nROLLBACK;\n")


def validate_extract(payload, plan):
    if payload['transaction_read_only']!='on' or payload['database']!='aact_snapshot':
        raise ValueError('Wrong database or non-read-only session')
    if Path(payload['data_directory']).resolve()!=Path(plan['restore_root'],'pgdata').resolve():
        raise ValueError('Unexpected restore directory')
    if payload['studies_count']!=plan['expected_studies'] or int(payload['port'])!=plan['port']:
        raise ValueError('Unexpected database inventory/port')
    records=payload['records'];ids=[r['study']['nct_id'] for r in records]
    if len(ids)!=len(set(ids)) or set(ids)!=set(plan['nct_ids']):
        raise ValueError('Missing/duplicate/unrequested linked trial')
    for record in records:
        study=record['study'];nct=study['nct_id']
        for field in ['study_first_posted_date','last_update_posted_date','results_first_posted_date']:
            value=study.get(field)
            if value and value>plan['snapshot_date']:raise ValueError('Post-cutoff posted information')
        for table in TABLES:
            if any(r['nct_id']!=nct for r in record[table]):raise ValueError('Cross-trial child leakage')
        arms={r['id'] for r in record['design_groups']};interventions={r['id'] for r in record['interventions']}
        for link in record['design_group_interventions']:
            if link['design_group_id'] not in arms or link['intervention_id'] not in interventions:
                raise ValueError('Unresolved arm/intervention foreign key')
    return {'status':'passed','records':len(records),'read_only':True,'posting_dates_within_snapshot':True}


def extract(plan, output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    def write(name,data):
        with (output/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(data,f,indent=2);f.write('\n')
    write('extraction-plan.json',plan)
    shutil.copyfile(__file__,output/'extract_phase3_followup.py')
    (output/'query.sql').write_text(query(plan['nct_ids']),encoding='utf-8',newline='\n')
    previous=None
    def event(stage,**detail):
        nonlocal previous
        row={'time_utc':datetime.now(timezone.utc).isoformat(),'stage':stage,'previous':previous,**detail}
        digest=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
        with (output/'journal.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({**row,'sha256':digest})+'\n');f.flush();os.fsync(f.fileno())
        previous=digest
    pg=Path(plan['pg_bin']);root=Path(plan['restore_root']);started=False;stopped=False
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    def command(name,args,env=None,timeout=60,allowed=(0,)):
        event(name,status='started')
        with (output/(name+'.stdout.log')).open('xb') as out,(output/(name+'.stderr.log')).open('xb') as err:
            proc=subprocess.run(args,stdout=out,stderr=err,env=env,timeout=timeout,creationflags=flags)
        event(name,status='finished',returncode=proc.returncode)
        if proc.returncode not in allowed:raise RuntimeError(name+' failed; inspect retained logs')
        return proc.returncode
    begin=time.monotonic()
    try:
        event('parent_verification',status='started')
        checks=[]
        for parent in plan['parents']:
            checks.append({'path':parent['path'],'sha256':parent['sha256'],
                           'files':verify_manifest(Path(parent['path']),parent['sha256'])})
        dump=root/'extracted/postgres.dmp'
        if stream_sha(dump)!=plan['dump_sha256']:raise ValueError('Restored source dump differs from pinned original')
        write('input-verification.json',{'parents':checks,'dump_sha256':plan['dump_sha256'],'dump_bytes':dump.stat().st_size})
        event('parent_verification',status='passed')
        status=command('status_before',[str(pg/'pg_ctl.exe'),'-D',str(root/'pgdata'),'status'],allowed=(0,3))
        if status==0:raise RuntimeError('Server already running; refusing to change its lifecycle')
        started=True # Startup may partially succeed; finally must check/stop our instance.
        command('start',[str(pg/'pg_ctl.exe'),'-D',str(root/'pgdata'),'-l',str(output/'server.log'),
                         '-o','-c default_transaction_read_only=on','-w','-t','30','start'])
        env=os.environ.copy();env.update(PGHOST='127.0.0.1',PGPORT=str(plan['port']),PGUSER='aact_restore_admin',
            PGDATABASE='aact_snapshot',PGPASSWORD=(root/'.local-postgres-secrets/password.txt').read_text(),
            PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=30000',PGCLIENTENCODING='UTF8')
        for name in ['extract','replay']:
            command(name,[str(pg/'psql.exe'),'-XAtq','-v','ON_ERROR_STOP=1','-f',str(output/'query.sql')],env)
        first=load(output/'extract.stdout.log');second=load(output/'replay.stdout.log')
        checks=validate_extract(first,plan)
        if first!=second:raise ValueError('Repeated read differs')
        write('records.json',first)
        write('query-validation.json',{**checks,'repeat_read':'identical','records_sha256':sha(output/'records.json')})
        event('extraction',status='completed',records=len(first['records']))
    except BaseException as exc:
        event('failure',type=type(exc).__name__,message=str(exc))
        write('failure.json',{'type':type(exc).__name__,'message':str(exc),'automatic_retry':False})
        raise
    finally:
        if started:
            command('stop',[str(pg/'pg_ctl.exe'),'-D',str(root/'pgdata'),'-m','fast','-w','-t','30','stop'])
            stopped=command('status_after',[str(pg/'pg_ctl.exe'),'-D',str(root/'pgdata'),'status'],allowed=(3,))==3
        write('execution.json',{'server_started_by_this_run':started,'server_stopped':stopped,
            'elapsed_seconds':time.monotonic()-begin,'provider_spend_usd':0,'snapshot_date':plan['snapshot_date'],
            'clinical_label':None,'role':'evaluation_only'})
    event('completed',server_stopped=stopped)
    files=[{'path':p.relative_to(output).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(output.rglob('*')) if p.is_file()]
    write('evidence-manifest.json',{'schema_version':1,'role':'evaluation_only','files':files})
    print(json.dumps({'output':str(output),'evidence_manifest_sha256':sha(output/'evidence-manifest.json'),'server_stopped':stopped}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();extract(load(args.plan),args.output)
