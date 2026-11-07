"""Owned read-only execution of frozen evaluator queries, never automatic retry.

The query generator and scientific review policy are separate. This runner accepts
only byte-pinned generated SQL and restores explicitly named in a frozen plan.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, read_json, sha256_file, write_json
from tools.science.reference_panel import read_bound_json

PACK_SHA256='5a4842f9b1751d3e0b2e50c166c5bf1786e3639741072b38b8ad264b4b8da56d'
POLICY_SHA256='5fe2f3c49b85a4b36bb145df36e229b9e8785adef90e1e113a05d8d1f1ab3da6'
APPROVED_BASE=Path('E:/projects_data/drug_target_agents_data/derived/aact_restore')
APPROVED_RESTORES={
    '2025-01-01':'followup-20250101-20261017T051834Z',
    '2026-01-01':'science-endpoint-20260101-20261018T174448Z/restore/2026-01-01',
    '2026-04-01':'science-ascertainment-20260401-20261018T205200Z/restore/2026-04-01',
}


def validate_binding(plan):
    """Tie the request to the actual approved pilot and restored source identities."""
    if plan['phase']=='origin_screening':
        from tools.science.origin_maturity import validate_origin_binding
        return validate_origin_binding(plan)
    if plan['phase']=='endpoint_followup':
        from tools.science.endpoint_followup import validate_endpoint_binding
        return validate_endpoint_binding(plan)
    policy=plan['review_policy']
    if policy['sha256']!=POLICY_SHA256:
        raise ContractError('Wrong scientific review policy')
    read_bound_json(Path(policy['path']),POLICY_SHA256)
    selection=plan['selection']
    if selection['sha256']!=PACK_SHA256:
        raise ContractError('Wrong sealed origin pilot')
    pack,_=read_bound_json(Path(selection['path']),PACK_SHA256)
    if pack['clinical_labels_assigned']!=0 or pack['selected_distinct_trials']!=12:
        raise ContractError('Origin pilot is not unmodified pre-follow-up selection')
    check_pins(pack['files'])
    results_phase=plan['phase']=='selected_results'
    results_policy=None
    if results_phase:
        policy_pin=plan['results_policy']
        approved=Path(__file__).resolve().parents[2]/'planning/protocols/clinical-label-readiness-v0.1.json'
        if Path(policy_pin['path']).resolve()!=approved.resolve():
            raise ContractError('Unapproved reported-results policy path')
        results_policy,_=read_bound_json(approved,policy_pin['sha256'])
        from tools.science.outcome_results import RESULT_FIELDS
        if (results_policy.get('protocol_id')!='clinical-label-readiness-v0.1' or
                results_policy.get('role')!='evaluation_only' or
                results_policy.get('parent_origin_pack_sha256')!=PACK_SHA256 or
                results_policy.get('parent_review_policy_sha256')!=POLICY_SHA256 or
                results_policy.get('max_rows_per_trial')!=100000 or
                results_policy.get('max_result_output_bytes_per_snapshot')!=128*1024*1024 or
                results_policy.get('source_snapshots')!=[j['snapshot_date'] for j in plan['jobs']] or
                results_policy.get('reported_tables')!=list(RESULT_FIELDS) or
                any(results_policy.get(k)!=plan[k] for k in ('origin_at','horizon_at','ascertainment_at')) or
                results_policy.get('automatic_label_assignment') is not False or
                results_policy.get('clinical_activation') is not False):
            raise ContractError('Reported-results policy differs from bounded no-label scope')
        if not any(Path(p['path']).resolve()==approved.resolve() and p['sha256']==policy_pin['sha256'] for p in plan['parents']):
            raise ContractError('Reported-results policy missing from parent closure')
    members=[]
    for pin in pack['files']:
        path=Path(pin['path'])
        if path.parent.name=='packets':
            packet,_=read_bound_json(path,pin['sha256'])
            members.append(packet['origin_scope']['nct_id'])
    if len(members)!=12 or sorted(members)!=sorted(plan['nct_ids']):
        raise ContractError('Extraction membership differs from actual sealed pilot')
    alias_pin=plan['alias_dictionary']
    alias_data,_=read_bound_json(Path(alias_pin['path']),alias_pin['sha256'])
    if (alias_data['origin_pack_sha256']!=PACK_SHA256 or alias_data['followup_sources_read'] is not False
            or sorted(alias_data['aliases_by_origin'])!=sorted(members)):
        raise ContractError('Alias dictionary differs from the sealed pre-follow-up origin universe')
    amendment_pin=plan['cap_amendment']
    amendment,_=read_bound_json(Path(amendment_pin['path']),amendment_pin['sha256'])
    if amendment['parent_protocol_sha256']!=POLICY_SHA256 or amendment['endpoint_cohort_queries_performed']!=0:
        raise ContractError('Candidate cap amendment lacks its pre-query policy binding')
    expected_base=APPROVED_BASE.resolve()
    for job in plan['jobs']:
        root=Path(job['restore_root']).resolve()
        if root!=(expected_base/APPROVED_RESTORES[job['snapshot_date']]).resolve():
            raise ContractError('Unapproved restored cluster path')
        pins={Path(p['path']).resolve():p for p in job['pins']}
        required=['extracted/postgres.dmp','archive-inspection.json','dump-toc-pg17.txt',
                  'technical-audit.json','setup.py']
        if job['snapshot_date']=='2025-01-01':required.append('schema-pg17.sql')
        for name in required:
            if root/name not in pins:
                raise ContractError('Incomplete restored-source proof inventory')
        check_pins(job['pins'])
        inspection,_=read_bound_json(root/'archive-inspection.json',pins[root/'archive-inspection.json']['sha256'])
        member=next(m for m in inspection['members'] if m['name']=='postgres.dmp')
        if member['sha256']!=pins[root/'extracted/postgres.dmp']['sha256']:
            raise ContractError('Dump bytes contradict archive member qualification')
        audit,_=read_bound_json(root/'technical-audit.json',pins[root/'technical-audit.json']['sha256'])
        if audit['status']!='completed' or audit['study_id_check']['rows']!=job['expected_studies']:
            raise ContractError('Restored source audit contradicts expected inventory')
        names=[q['name'] for q in job['queries']]
        expected_names={'results'} if results_phase else {'studies','candidates'}
        if len(names)!=len(set(names)) or set(names)!=expected_names:
                raise ContractError('Frozen query names differ from the approved extraction phase')
        from tools.science.outcome_inputs import regenerate_request, schema_from_audit, study_query
        for query in job['queries']:
            request=query['request']
            if results_phase:
                from tools.science.outcome_results import regenerate_results
                rebuilt=regenerate_results(request)
            else:rebuilt=regenerate_request(request)
            if rebuilt!=request or request['sql']!=Path(query['path']).read_text(encoding='utf-8'):
                raise ContractError('Query differs from deterministic approved generator recipe')
            if request['snapshot_date']!=job['snapshot_date'] or request['source_schema']!=schema_from_audit(audit):
                raise ContractError('Request schema/snapshot differs from its pinned actual source')
            if results_phase:
                from tools.science.outcome_results import results_query
                expected_results=results_query(members,job['snapshot_date'],schema_from_audit(audit),
                    max_rows_per_trial=results_policy['max_rows_per_trial'])
                if request!=expected_results:
                    raise ContractError('Result query does not retain exact pilot membership and projection')
            elif query['name']=='studies':
                expected_studies=study_query(members,job['snapshot_date'],schema_from_audit(audit),max_ids=12)
                if request!=expected_studies:
                    raise ContractError('Study query does not retain the actual twelve members')
            elif (request['kind']!='candidate_identity' or request['aliases_by_origin']!=alias_data['aliases_by_origin']
                    or request['per_origin_cap']!=amendment['new_caps']['per_origin_trial']
                    or request['total_cap']!=amendment['new_caps']['total_distinct_trials']):
                raise ContractError('Candidate query differs from frozen aliases or explicit caps')


@contextmanager
def source_lease(restore_root):
    """Serialize this tool's ownership of each existing local cluster."""
    import hashlib
    folder=Path(__file__).resolve().parents[2]/'data/cache/science-source-locks'
    folder.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256(str(Path(restore_root).resolve()).casefold().encode()).hexdigest()
    lock=folder/(key+'.lock')
    with lock.open('x',encoding='utf-8') as stream:
        stream.write(json.dumps({'pid':os.getpid(),'restore_root':str(restore_root)}))
    try:
        yield
    finally:
        lock.unlink()


def check_pins(pins):
    seen={}
    for pin in pins:
        path=Path(pin['path']).resolve()
        if path in seen and seen[path]!=pin['sha256']:
            raise ContractError('Conflicting extraction input identity')
        if sha256_file(path)!=pin['sha256'] or ('bytes' in pin and path.stat().st_size!=pin['bytes']):
            raise ContractError('Changed extraction ancestor: '+str(path))
        seen[path]=pin['sha256']


def validate_plan(plan):
    origin_screening=plan.get('phase')=='origin_screening'
    expected_protocol=('endpoint-origin-screen-inputs-v1' if origin_screening else
        'endpoint-followup-inputs-v1' if plan.get('phase')=='endpoint_followup' else 'science4-outcome-inputs-v1')
    if (plan.get('schema_version')!=1 or plan.get('protocol_id')!=expected_protocol
            or plan.get('role')!='evaluation_only' or plan.get('provider_spend_usd')!=0
            or plan.get('clinical_activation') is not False):
        raise ContractError('Unapproved evaluator extraction protocol')
    if (plan.get('origin_at'),plan.get('horizon_at'),plan.get('ascertainment_at'))!=(
            '2025-01-01T00:00:00Z','2026-01-01T00:00:00Z','2026-04-01T00:00:00Z'):
        raise ContractError('Extraction chronology differs from frozen design')
    ids=plan.get('nct_ids',[])
    count=128 if origin_screening else 12
    if len(ids)!=count or len(set(ids))!=count or any(not isinstance(x,str) or not re.fullmatch(r'NCT[0-9]{8}',x) for x in ids):
        raise ContractError('Extraction must retain all twelve sealed pilot members')
    if plan.get('phase') not in ('origin_design','followup_design','selected_results','origin_screening','endpoint_followup'):
        raise ContractError('Unknown evaluator phase')
    jobs=plan.get('jobs',[])
    expected=['2025-01-01'] if plan['phase'] in ('origin_design','origin_screening') else ['2026-01-01','2026-04-01']
    if [j.get('snapshot_date') for j in jobs]!=expected:
        raise ContractError('Wrong or reordered source snapshots')
    for job in jobs:
        if (not 1024<=job.get('port',0)<=65535 or
                job.get('expected_studies')!={'2025-01-01':520688,'2026-01-01':563840,'2026-04-01':578527}[job['snapshot_date']]):
            raise ContractError('Wrong source inventory or loopback port')
        if not job.get('pins') or not job.get('queries'):
            raise ContractError('Source proofs and frozen query files required')
        for query in job['queries']:
            sql=Path(query['path']).read_text(encoding='utf-8')
            # Not a general SQL security parser: the reviewed generator and exact bytes
            # are pinned separately. Reject accidentally supplied free-form mutations.
            if not sql.startswith('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;') or not sql.rstrip().endswith('ROLLBACK;'):
                raise ContractError('Only frozen read-only generated transactions accepted')
            if not re.fullmatch('[a-z][a-z0-9_-]{0,40}',query.get('name','')):
                raise ContractError('Unsafe extraction query name')


def extract(plan_path, expected_sha256, output):
    output=Path(output).resolve()
    journal=RunJournal(output,kind='build')
    started_at=time.monotonic()
    stage='plan'
    try:
        plan,_=read_bound_json(Path(plan_path),expected_sha256)
        validate_plan(plan)
        if not any(Path(p['path']).resolve()==Path(__file__).resolve() for p in plan['executed_code']):
            raise ContractError('Missing executing-runner code commitment')
        check_pins(plan['parents']+plan['executed_code'])
        project=Path(__file__).resolve().parents[2]
        codepaths={Path(p['path']).resolve() for p in plan['executed_code']}
        required_code={'tools/science/outcome_extract.py','tools/science/outcome_inputs.py',
            'tools/science/ascertainment_policy.py','tools/science/origin_programs.py',
            'tools/science/reference_panel.py','src/tether_engine/serde.py','src/tether_engine/journal.py'}
        if plan['phase']=='selected_results':required_code.add('tools/science/outcome_results.py')
        if plan['phase']=='endpoint_followup':required_code.update(('tools/science/endpoint_followup.py','tools/science/outcome_results.py'))
        if plan['phase']=='origin_screening':required_code.update(('tools/science/origin_maturity.py','tools/science/origin_review.py'))
        if not {project/p for p in required_code}<=codepaths:
            raise ContractError('Incomplete executing query/temporal/serialization code closure')
        validate_binding(plan)
        write_json(output/'effective-plan.json',plan)
        (output/'executed-runner.py').write_bytes(Path(__file__).read_bytes())
        archived_code=[]
        for proof in plan['executed_code']:
            source=Path(proof['path']).resolve()
            if not source.is_relative_to(project):raise ContractError('Executing code outside project')
            archived=output/'executed-code'/source.relative_to(project)
            archived.parent.mkdir(parents=True,exist_ok=True)
            with archived.open('xb') as stream:stream.write(source.read_bytes())
            if sha256_file(archived)!=proof['sha256']:raise ContractError('Executing code changed while archiving')
            archived_code.append({'source':proof,'archive_path':str(archived),'sha256':proof['sha256']})
        write_json(output/'executed-code-proofs.json',archived_code)
        results=[]
        for job in plan['jobs']:
            date=job['snapshot_date'];stage=date
            folder=output/date;folder.mkdir()
            root=Path(job['restore_root']).resolve();pg=Path(plan['pg_bin']).resolve()
            check_pins(job['pins']+job['queries'])
            if not any(Path(p['path']).resolve()==root/'extracted/postgres.dmp' for p in job['pins']):
                raise ContractError('Missing original dump commitment')
            toc=(root/'dump-toc-pg17.txt').read_text(encoding='utf-8')
            if '; Archive created at '+date+' ' not in toc:
                raise ContractError('Wrong actual dump date')
            acquired=False;stopped=False;failed=None
            lease=source_lease(root)
            lease.__enter__()
            def command(name,args,env=None,allowed=(0,),timeout=90):
                journal.append('build_progress',stage=stage,command=name,status='started')
                with (folder/(name+'.stdout.log')).open('xb') as stdout,(folder/(name+'.stderr.log')).open('xb') as stderr:
                    proc=subprocess.run(args,env=env,stdout=stdout,stderr=stderr,timeout=timeout,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                journal.append('build_progress',stage=stage,command=name,status='finished',returncode=proc.returncode)
                if proc.returncode not in allowed:raise RuntimeError(name+' failed; inspect retained logs')
                return proc.returncode
            try:
                status=command('status-before',[str(pg/'pg_ctl.exe'),'-D',str(root/'pgdata'),'status'],allowed=(0,3))
                if status==0:raise ContractError('Existing server running; ownership refused')
                with socket.socket() as probe:
                    if probe.connect_ex(('127.0.0.1',job['port']))==0:
                        raise ContractError('Requested port already occupied')
                # A unique PostgreSQL-created PID file proves this startup owns the
                # server, including a partial pg_ctl timeout. Port equality alone
                # cannot distinguish a concurrent manual startup.
                ownership_file=folder/'owned-postmaster.pid'
                if any(c.isspace() or c in "'\"" for c in ownership_file.as_posix()):
                    raise ContractError('Ownership PID path needs a simple local path')
                acquired=True
                ctl=str(pg/'pg_ctl.exe').replace("'","''")
                args=['-D',str(root/'pgdata'),'-l',str(folder/'server.log'),'-o',
                      f"-p {job['port']} -c default_transaction_read_only=on -c external_pid_file={ownership_file.as_posix()}",'-w','-t','45','start']
                arglist=','.join("'\""+a.replace("'","''")+"\"'" for a in args)
                command('start',['powershell.exe','-NoProfile','-NonInteractive','-Command',
                    f"$p=Start-Process -FilePath '{ctl}' -ArgumentList @({arglist}) -WindowStyle Hidden -PassThru; $p.WaitForExit(); exit $p.ExitCode"])
                env=os.environ.copy()
                env.update(PGHOST='127.0.0.1',PGPORT=str(job['port']),PGUSER='aact_restore_admin',
                    PGDATABASE='aact_snapshot',PGCLIENTENCODING='UTF8',
                    PGPASSWORD=(root/'.local-postgres-secrets/password.txt').read_text(encoding='utf-8'),
                    PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=300000 -c jit=off')
                metadata="SELECT json_build_object('database',current_database(),'studies',(SELECT count(*) FROM ctgov.studies),'directory',current_setting('data_directory'),'port',current_setting('port'),'read_only',current_setting('transaction_read_only'));"
                command('metadata',[str(pg/'psql.exe'),'-XAtq','-v','ON_ERROR_STOP=1','-c',metadata],env)
                meta=read_json(folder/'metadata.stdout.log')
                if (meta['database']!='aact_snapshot' or meta['studies']!=job['expected_studies']
                        or Path(meta['directory']).resolve()!=root/'pgdata'
                        or meta['read_only']!='on' or meta['port']!=str(job['port'])):
                    raise ContractError('Wrong source database identity/read-only state')
                queries=[]
                for query in job['queries']:
                    # Recheck the exact generated SQL immediately before dispatch.
                    check_pins([query])
                    name=query['name']
                    for suffix in ('first','repeat'):
                        command(name+'-'+suffix,[str(pg/'psql.exe'),'-XAtq','-v','ON_ERROR_STOP=1','-f',query['path']],env,timeout=330)
                    first=folder/(name+'-first.stdout.log');repeat=folder/(name+'-repeat.stdout.log')
                    byte_limit=(128*1024*1024 if plan['phase'] in ('origin_screening','endpoint_followup') else query['request'].get('max_output_bytes'))
                    if byte_limit is not None and max(first.stat().st_size,repeat.stat().st_size)>byte_limit:
                        raise ContractError('Reported results exceed explicit output-byte bound')
                    if first.read_bytes()!=repeat.read_bytes():raise ContractError('Repeat source reads differ')
                    from tools.science.outcome_inputs import parse_jsonl, validate_study_rows, validate_candidates
                    rows=parse_jsonl(first.read_text(encoding='utf-8'))
                    if name=='results':
                        from tools.science.outcome_results import validate_result_rows
                        validation=validate_result_rows(rows,query['request'])
                    else:
                        validation=(validate_study_rows(rows,query['request']) if name=='studies'
                                    else validate_candidates(rows,query['request']))
                    write_json(folder/(name+'-validation.json'),validation)
                    queries.append({'name':name,'path':str(first),'sha256':sha256_file(first),
                                    'bytes':first.stat().st_size,'repeat_identical':True})
                check_pins(job['pins']+job['queries'])
                results.append({'snapshot_date':date,'queries':queries,'metadata':meta})
            except BaseException as exc:
                failed=exc
                raise
            finally:
                try:
                    if acquired:
                        try:
                            if (root/'pgdata/postmaster.pid').exists():
                                pid_lines=(root/'pgdata/postmaster.pid').read_text(encoding='utf-8').splitlines()
                                if (len(pid_lines)<4 or pid_lines[3]!=str(job['port']) or
                                        not ownership_file.is_file() or
                                        ownership_file.read_text(encoding='utf-8').strip()!=pid_lines[0]):
                                    raise ContractError('Server startup ownership unproven; refusing shutdown')
                                journal.append('build_progress',stage=stage,status='owned_server_cleanup',
                                               server_pid=pid_lines[0],server_started_epoch=pid_lines[2])
                                command('stop',[str(pg/'pg_ctl.exe'),'-D',str(root/'pgdata'),'-m','fast','-w','-t','45','stop'])
                            stopped=command('status-after',[str(pg/'pg_ctl.exe'),'-D',str(root/'pgdata'),'status'],allowed=(3,))==3
                            with socket.socket() as probe:
                                if probe.connect_ex(('127.0.0.1',job['port']))==0:
                                    raise ContractError('Owned local port remains open')
                        except BaseException as cleanup_error:
                            journal.append('build_cleanup_failed',stage=stage,error_class=type(cleanup_error).__name__)
                            if failed is None:raise
                finally:
                    try:
                        write_json(folder/'lifecycle.json',{'ownership_acquired':acquired,'server_stopped':stopped,
                            'port':job['port'],'automatic_retry':False})
                    finally:
                        lease.__exit__(None,None,None)
            journal.append('build_progress',stage=stage,status='source_reads_complete',server_stopped=stopped)
        check_pins(plan['parents']+plan['executed_code'])
        report={'schema_version':1,'status':'source_reads_complete_pending_scientific_validation','role':'evaluation_only',
            'created_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':expected_sha256,
            'phase':plan['phase'],'snapshots':results,'elapsed_seconds':time.monotonic()-started_at,
            'clinical_labels_assigned':0,'provider_spend_usd':0,'clinical_activation':False}
        write_json(output/'report.json',report)
        journal.append('build_completed',report_sha256=sha256_file(output/'report.json'))
    except BaseException as exc:
        journal.fail(exc,stage)
        write_json(output/'failure.json',{'stage':stage,'error_class':type(exc).__name__,'message':str(exc),'automatic_retry':False})
        raise
    finally:
        journal.close()
    read_chain(output/'journal.jsonl')
    print(json.dumps({'status':report['status'],'output':str(output),'elapsed_seconds':report['elapsed_seconds']}),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--expected-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    extract(args.plan,args.expected_sha256,args.output)
