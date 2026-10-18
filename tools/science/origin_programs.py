"""Seal a new 2025 origin-only registry universe; never accepts outcome sources.

Trial/arm scopes remain separate until scientific equivalence is established.
The seal freezes selection, not clinical qualification or target truth.
"""
from __future__ import annotations

import argparse
import calendar
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import unicodedata

ORIGIN = '2025-01-01T00:00:00Z'
VERSION = 'science-origin-programs-20250101-v1'
ACTIVE = {'RECRUITING', 'ACTIVENOTRECRUITING', 'ENROLLINGBYINVITATION'}
TABLES = ('conditions', 'interventions', 'intervention_other_names', 'design_groups',
          'design_group_interventions', 'sponsors', 'brief_summaries', 'eligibilities', 'designs')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')
        f.flush(); os.fsync(f.fileno())


def read_bound_json(path):
    """Bind the exact bytes parsed, rather than a later read of their pathname."""
    path=Path(path).resolve(); raw=path.read_bytes()
    return json.loads(raw),{'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


def verify_pins(pins):
    for item in pins:
        path=Path(item['path'])
        if (('bytes' in item and path.stat().st_size!=item['bytes']) or sha(path)!=item['sha256']):
            raise ValueError('Changed bound ancestor: '+str(path))


def origin_ancestor_pins(freeze, parent_pin):
    """Include restore receipts as well as the direct origin-selection artifacts."""
    pins=[dict(parent_pin)]
    for item in [*freeze['files'],*freeze.get('source_receipts',[])]:
        pin=dict(item)
        if 'bytes' not in pin:pin['bytes']=Path(pin['path']).stat().st_size
        pins.append(pin)
    verify_pins(pins)
    return pins


def norm(value):
    return ' '.join(unicodedata.normalize('NFKC', value or '').casefold().split())


def cat(value):
    return re.sub('[^A-Z0-9]', '', (value or '').upper())


def stable(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def start_bounds(raw):
    """No imputed AACT date can refine the source's original date precision."""
    raw = (raw or '').strip()
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
            return date.fromisoformat(raw).isoformat(), date.fromisoformat(raw).isoformat(), 'day'
        if re.fullmatch(r'\d{4}-\d{2}', raw):
            y, m = map(int, raw.split('-'))
            return date(y,m,1).isoformat(), date(y,m,calendar.monthrange(y,m)[1]).isoformat(), 'month'
        if re.fullmatch(r'\d{4}', raw):
            y = int(raw); return date(y,1,1).isoformat(), date(y,12,31).isoformat(), 'year'
        for fmt in ('%B %d, %Y', '%b %d, %Y', '%B %Y', '%b %Y'):
            try: d = datetime.strptime(raw, fmt)
            except ValueError: continue
            if '%d' in fmt: return d.date().isoformat(), d.date().isoformat(), 'day'
            return date(d.year,d.month,1).isoformat(), date(d.year,d.month,calendar.monthrange(d.year,d.month)[1]).isoformat(), 'month'
    except ValueError:
        pass
    return None, None, 'unknown'


def query():
    fields = ["'study',json_build_object(" + ','.join("'%s',s.%s" % (c,c) for c in (
        'nct_id','brief_title','official_title','study_type','phase','overall_status',
        'start_date','start_month_year','start_date_type','study_first_posted_date','last_update_posted_date')) + ')']
    joins = []
    for table in TABLES:
        fields.append("'%s',coalesce(%s_bundle.rows,'[]'::json)" % (table, table))
        joins.append('LEFT JOIN (SELECT t.nct_id,json_agg(to_json(t) ORDER BY t.id) rows FROM ctgov.%s t JOIN selected a ON a.nct_id=t.nct_id GROUP BY t.nct_id) %s_bundle ON %s_bundle.nct_id=s.nct_id' % (table,table,table))
    return ("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\n"
        "WITH selected AS MATERIALIZED (SELECT s.* FROM ctgov.studies s WHERE upper(s.study_type)='INTERVENTIONAL' "
        "AND regexp_replace(upper(coalesce(s.phase,'')),'[^A-Z0-9]','','g') IN "
        "('EARLYPHASE1','PHASE1','PHASE1PHASE2','PHASE2','PHASE2PHASE3','PHASE3','PHASE4')) "
        'SELECT json_build_object(' + ','.join(fields) + ') FROM selected s ' + ' '.join(joins) + ' ORDER BY s.nct_id;\nROLLBACK;\n')


def validate(row):
    s = row['study']; nct = s['nct_id']
    if not re.fullmatch(r'NCT\d{8}',nct): raise ValueError('Invalid source NCT')
    for key in ('study_first_posted_date','last_update_posted_date'):
        if not s.get(key) or s[key] >= ORIGIN[:10]: raise ValueError('Unqualified origin posting date')
    for table in TABLES:
        ids = [c['id'] for c in row[table]]
        if len(ids) != len(set(ids)): raise ValueError('Duplicate source child ID')
        if any(c['nct_id'] != nct for c in row[table]): raise ValueError('Cross-trial child')
    arms = {r['id'] for r in row['design_groups']}; interventions = {r['id'] for r in row['interventions']}
    for r in row['design_group_interventions']:
        if r['design_group_id'] not in arms or r['intervention_id'] not in interventions:
            raise ValueError('Broken arm/intervention source linkage')
    if any(r['intervention_id'] not in interventions for r in row['intervention_other_names']):
        raise ValueError('Broken intervention alias linkage')
    return nct


def trial_facts(row):
    s=row['study']; lo,hi,precision=start_bounds(s.get('start_month_year'))
    phase={'PHASE1':1,'PHASE2':2,'PHASE3':3,'PHASE4':4}.get(cat(s['phase']))
    reasons=[]
    if cat(s['overall_status']) not in ACTIVE: reasons.append('not_active_at_origin')
    if phase not in (1,2): reasons.append('phase_not_unambiguous_phase1_or_phase2')
    if cat(s.get('start_date_type')) != 'ACTUAL': reasons.append('start_not_actual')
    if not hi or hi >= ORIGIN[:10]: reasons.append('actual_start_interval_not_wholly_pre_origin')
    return {'phase':phase,'start_interval':{'lower_date':lo,'upper_date':hi,'precision':precision,
        'date_semantics':'UTC day interval [00:00,next-day 00:00); whole interval must end <= origin'},
        'reasons':reasons}


def arm_records(row):
    s=row['study']; facts=trial_facts(row); products={p['id']:p for p in row['interventions']}
    conditions=sorted({norm(c['name']) for c in row['conditions'] if norm(c['name'])}) or ['']
    for arm in row['design_groups']:
        if cat(arm['group_type']) != 'EXPERIMENTAL': continue
        links=sorted({r['intervention_id'] for r in row['design_group_interventions'] if r['design_group_id']==arm['id']})
        slots=[products[i] for i in links]
        active=[p for p in slots if cat(p['intervention_type']) in {'DRUG','BIOLOGICAL'} and not re.search(r'\b(placebo|sham|vehicle)\b',norm(p['name']))]
        reasons=list(facts['reasons'])
        if not active: reasons.append('no_linked_active_drug_or_biological')
        for condition in conditions:
            excluded=list(reasons)
            if not condition: excluded.append('missing_condition')
            holds=['historical_drug_target_mapping_unqualified','same_program_scope_not_established',
                   'snapshot_exact_public_availability_unverified','arm_population_not_explicitly_qualified',
                   'prior_higher_phase_alias_completeness_unqualified']
            if len(conditions)>1: holds.append('multiple_conditions_arm_assignment_unqualified')
            if len(active)>1: holds.append('combination_regimen_roles_unqualified')
            if any(cat(p['intervention_type']) not in {'DRUG','BIOLOGICAL'} for p in slots): holds.append('other_linked_intervention_roles_unqualified')
            if not row['eligibilities']: holds.append('study_eligibility_missing')
            names=sorted({norm(p['name']) for p in active})
            yield {'program_id':'origin-scope:'+stable([s['nct_id'],arm['id'],condition])[:24],
                'nct_id':s['nct_id'],'arm_id':arm['id'],'condition_verbatim_normalized':condition,
                'origin_phase':facts['phase'],'phase_raw':s['phase'],'status_raw':s['overall_status'],
                'start_interval':facts['start_interval'],'regimen_source_intervention_ids':links,
                'active_product_names':names,'drug_ids':[],'target_ids':[],
                'mapping_status':'unknown_pending_historical_qualification',
                'scope_status':'excluded' if excluded else 'conditional_origin_candidate',
                'exclusions':sorted(set(excluded)),'qualification_holds':sorted(set(holds)),
                'source_arm':arm,'source_products':slots,'population_source':row['eligibilities'],
                'design_source':row['designs'],'lead_sponsors':sorted({p['name'] for p in row['sponsors'] if cat(p.get('lead_or_collaborator'))=='LEAD' and p.get('name')}),
                'dependence_keys':{'trial':s['nct_id'],'regimen_verbatim':'regimen:'+stable(names)[:24] if names else None,
                    'product_verbatim':['product:'+stable(n)[:24] for n in names],
                    'sponsor_verbatim':['sponsor:'+stable(norm(p['name']))[:24] for p in row['sponsors'] if p.get('name')],
                    'target':[],'qualification':'verbatim keys flag possible dependence; no biological identity assertion'},
                'clinical_outcome':None,'clinical_ready':False,'role':'evaluation_only'}


def seal_frame(frame, output, source_receipts):
    """Freeze the source-only candidate universe before any later endpoint access."""
    output=Path(output); frame=Path(frame)
    if any((output/name).exists() for name in ('origin-freeze.json','origin-prior-index.sqlite','origin-programs.jsonl')):
        raise FileExistsError('Never modify or reuse a prior origin build')
    db=sqlite3.connect(output/'origin-prior-index.sqlite')
    db.execute('CREATE TABLE prior(product TEXT,condition TEXT,phase INTEGER,nct TEXT,start_upper TEXT,start_kind TEXT,phase_raw TEXT)')
    counts=Counter(); proofs=[]; previous=None; offset=0; first_digest=hashlib.sha256()
    with frame.open('rb') as source, (output/'trial-dispositions.jsonl').open('x',encoding='utf-8',newline='\n') as trials:
        for line,raw in enumerate(source,1):
            first_digest.update(raw)
            row=json.loads(raw); nct=validate(row)
            if previous and nct<=previous: raise ValueError('Source order/uniqueness violation')
            previous=nct; s=row['study']; facts=trial_facts(row)
            proof={'nct_id':nct,'line':line,'byte_offset':offset,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            offset+=len(raw); counts['source_trials']+=1
            counts['trial_eligible' if not facts['reasons'] else 'trial_excluded']+=1
            trials.write(json.dumps({'nct_id':nct,**facts,'source_proof':proof})+'\n')
            if len(proofs)<30 or line%5000==0: proofs.append(proof)
            # Prior-stage risk includes comparator and unresolved roles conservatively.
            for p in row['interventions']:
                if cat(p['intervention_type']) not in {'DRUG','BIOLOGICAL'}: continue
                names={norm(p['name'])}|{norm(a['name']) for a in row['intervention_other_names'] if a['intervention_id']==p['id']}
                for name in names- {''}:
                    for c in {norm(c['name']) for c in row['conditions']} - {''}:
                        db.execute('INSERT INTO prior VALUES(?,?,?,?,?,?,?)',(name,c,facts['phase'],nct,facts['start_interval']['upper_date'],cat(s.get('start_date_type')),cat(s['phase'])))
            if line%2000==0: db.commit()
    db.commit(); db.execute('CREATE INDEX prior_key ON prior(product,condition)'); db.commit()
    second_digest=hashlib.sha256()
    with frame.open('rb') as source, (output/'origin-programs.jsonl').open('x',encoding='utf-8',newline='\n') as out:
        offset=0
        for line,raw in enumerate(source,1):
            second_digest.update(raw)
            row=json.loads(raw)
            for rec in arm_records(row):
                if rec['scope_status']=='excluded': counts['excluded_arm_condition_scopes']+=1; continue
                alerts=[]
                for name in rec['active_product_names']:
                    for hit in db.execute('SELECT DISTINCT nct,phase,phase_raw,start_upper,start_kind FROM prior WHERE product=? AND condition=? AND nct<>?',(name,rec['condition_verbatim_normalized'],rec['nct_id'])):
                        nct,phase,phase_raw,upper,kind=hit
                        higher=(phase and phase>rec['origin_phase']) or phase_raw=='PHASE2PHASE3' or (rec['origin_phase']==1 and phase_raw=='PHASE1PHASE2')
                        if higher and kind=='ACTUAL' and upper and upper<ORIGIN[:10]:
                            alerts.append({'nct_id':nct,'phase':phase,'phase_raw':phase_raw,'product_verbatim':name,'start_upper':upper})
                rec['prior_higher_phase_verbatim_alerts']=alerts
                if alerts: rec['qualification_holds'].append('possible_prior_higher_phase_source_review_required')
                rec['source_proof']={'path':str(frame.resolve()),'line':line,'byte_offset':offset,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                out.write(json.dumps(rec,ensure_ascii=False)+'\n'); counts['conditional_origin_candidates']+=1
                if alerts: counts['candidates_with_prior_higher_phase_alerts']+=1
            offset+=len(raw)
    db.close()
    if first_digest.hexdigest()!=second_digest.hexdigest() or sha(frame)!=first_digest.hexdigest():
        raise ValueError('Origin frame changed during source-only selection')
    audit=[]
    with frame.open('rb') as f:
        for proof in proofs:
            f.seek(proof['byte_offset']); raw=f.read(proof['bytes'])
            if hashlib.sha256(raw).hexdigest()!=proof['sha256'] or json.loads(raw)['study']['nct_id']!=proof['nct_id']:
                raise ValueError('Retained original-row audit failed')
            audit.append(proof)
    write(output/'origin-source-audit.json',{'checks':len(audit),'status':'passed','source_rows':audit,
        'limit':'byte/relational/source fidelity, not independent clinical adjudication'})
    write(output/'origin-summary.json',{'counts':dict(counts),'qualified_programs':0,'clinical_outcomes_read':0,
        'mapping_status':'pending_historical_qualification','scientific_scope_equivalence':'not_established'})
    assets=[frame,output/'origin-programs.jsonl',output/'trial-dispositions.jsonl',output/'origin-source-audit.json',output/'origin-summary.json',output/'origin-prior-index.sqlite',output/'origin-query.sql',output/'origin-contract.json',output/'executed-origin-programs.py']
    write(output/'origin-freeze.json',{'schema_version':1,'protocol_id':VERSION,'sealed_at_utc':datetime.now(timezone.utc).isoformat(),
        'origin_at':ORIGIN,'horizon_at':'2026-01-01T00:00:00Z','selection_sealed':True,
        'selection_basis':'January2025 origin-only; no endpoint source queried or joined',
        'clinical_ready':False,'snapshot_date':'2025-01-01','status':'sealed_conditional_candidate_universe',
        'endpoint_rows_queried':0,'mapping_qualified':False,'origin_date_qualified':False,
        'revision_type':'origin_trial_regimen_universe_with_unknown_historical_mapping',
        'mapping_qualified_revision_required_before_endpoint_joins':True,
        'files':[{'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size} for p in assets],
        'source_receipts':source_receipts,'counts':dict(counts),'provider_spend_usd':0})
    return dict(counts)


def extract(restore, pg_bin, output, port=55439):
    restore=Path(restore).resolve(); pg_bin=Path(pg_bin).resolve(); output=Path(output).resolve()
    if restore.name!='followup-20250101-20261017T051834Z': raise ValueError('Only approved January2025 restore accepted')
    if not 1024<=port<=65535: raise ValueError('Invalid owned local port')
    verification=json.loads((restore/'verification.json').read_text())
    if verification['studies']!=520688 or verification['status']!='technical_checks_passed': raise ValueError('Wrong origin inventory')
    toc=(restore/'dump-toc-pg17.txt').read_text()
    if '; Archive created at 2025-01-01 ' not in toc: raise ValueError('Wrong origin dump date')
    output.mkdir(parents=True,exist_ok=False)
    receipts=[{'path':str((restore/name).resolve()),'sha256':sha(restore/name)} for name in ('verification.json','archive-inspection.json','dump-toc-pg17.txt','technical-audit.json','schema-pg17.sql')]
    (output/'executed-origin-programs.py').write_bytes(Path(__file__).read_bytes())
    write(output/'origin-contract.json',{'protocol_id':VERSION,'origin_at':ORIGIN,'endpoint_access_before_seal':False,
        'all_fields_same_origin_snapshot':True,'mixed_phase':'held; never rounded down','active_statuses':sorted(ACTIVE),
        'source_public_availability':'dump Jan1 05:22:15 timezone unknown; exact public release unverified; conditional historical reconstruction',
        'posting_qualification':'both posting dates strictly before Jan1 UTC; date-only upper bound next midnight',
        'start_qualification':'ACTUAL and whole source-precision interval before origin; AACT imputed dates never refine precision',
        'scope':'one trial/experimental-arm/condition; no cross-trial collapse; combo roles, arm-population and historical identity conditional',
        'missingness':'unknown identifiers/targets/populations never invented; no outcome labels','source_receipts':receipts})
    (output/'origin-query.sql').write_text(query(),encoding='utf-8',newline='\n')
    def run(name,args,env=None,allowed=(0,),timeout=120):
        with (output/(name+'.stdout.log')).open('xb') as out,(output/(name+'.stderr.log')).open('xb') as err:
            p=subprocess.run(args,stdout=out,stderr=err,env=env,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if p.returncode not in allowed: raise RuntimeError(name+' failed; inspect retained sanitized logs')
        return p.returncode
    if run('status-before',[str(pg_bin/'pg_ctl.exe'),'-D',str(restore/'pgdata'),'status'],allowed=(0,3))==0:
        raise RuntimeError('Origin server already running; ownership not acquired')
    started=False
    try:
        # Native hidden Start-Process is required for this Windows background helper.
        ctl=str(pg_bin/'pg_ctl.exe').replace("'","''")
        args=['-D',str(restore/'pgdata'),'-l',str(output/'origin-server.log'),'-o',f'-p {port} -c default_transaction_read_only=on','-w','-t','45','start']
        # Quote every argument for Start-Process's command line assembly.
        arglist=','.join("'\""+a.replace("'","''")+"\"'" for a in args)
        command=f"$p=Start-Process -FilePath '{ctl}' -ArgumentList @({arglist}) -WindowStyle Hidden -PassThru; $p.WaitForExit(); exit $p.ExitCode"
        started=True
        run('start',['powershell.exe','-NoProfile','-NonInteractive','-Command',command])
        env=os.environ.copy(); env.update(PGHOST='127.0.0.1',PGPORT=str(port),PGUSER='aact_restore_admin',PGDATABASE='aact_snapshot',PGCLIENTENCODING='UTF8',
            PGPASSWORD=(restore/'.local-postgres-secrets/password.txt').read_text(),PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=1800000 -c enable_nestloop=off -c enable_mergejoin=off -c jit=off')
        sql="SELECT json_build_object('studies',(SELECT count(*) FROM ctgov.studies),'data_directory',current_setting('data_directory'),'read_only',current_setting('transaction_read_only'),'port',current_setting('port'),'server_version',current_setting('server_version'));"
        run('metadata',[str(pg_bin/'psql.exe'),'-XAtq','-v','ON_ERROR_STOP=1','-c',sql],env)
        meta=json.loads((output/'metadata.stdout.log').read_text())
        if meta['studies']!=520688 or Path(meta['data_directory']).resolve()!=restore/'pgdata' or meta['read_only']!='on' or meta['port']!=str(port): raise ValueError('Wrong source connection')
        print(json.dumps({'stage':'origin_query_started','output':str(output)}),flush=True)
        run('origin-frame',[str(pg_bin/'psql.exe'),'-XAtq','-v','ON_ERROR_STOP=1','-f',str(output/'origin-query.sql')],env,timeout=1900)
    finally:
        if started and (restore/'pgdata/postmaster.pid').exists():
            run('stop',[str(pg_bin/'pg_ctl.exe'),'-D',str(restore/'pgdata'),'-m','fast','-w','-t','45','stop'])
            run('status-after',[str(pg_bin/'pg_ctl.exe'),'-D',str(restore/'pgdata'),'status'],allowed=(3,))
            write(output/'origin-server-stopped.json',{'stopped':True,'port':port,'at_utc':datetime.now(timezone.utc).isoformat()})
    counts=seal_frame(output/'origin-frame.stdout.log',output,receipts)
    print(json.dumps({'stage':'origin_sealed','output':str(output),'counts':counts}),flush=True)


def mapping_revision(parent, manifest_path, output, rules_proof):
    """Attach historical annotation candidates without changing frozen membership."""
    parent=Path(parent).resolve(); manifest_path=Path(manifest_path).resolve(); output=Path(output).resolve()
    freeze,parent_pin=read_bound_json(parent)
    manifest,manifest_pin=read_bound_json(manifest_path)
    rules=Path(rules_proof).resolve()
    rules_pin={'path':str(rules),'sha256':sha(rules),'bytes':rules.stat().st_size}
    if freeze.get('origin_at')!=ORIGIN or not freeze.get('selection_sealed') or freeze.get('endpoint_rows_queried')!=0:
        raise ValueError('Origin selection seal must precede mapping')
    if manifest.get('status')!='qualified_mapping_projections_only' or manifest.get('release_id')!='24.09' or manifest.get('origin_at')!=ORIGIN or manifest.get('future_fallback') is not False:
        raise ValueError('Wrong historical mapping qualification')
    available=datetime.fromisoformat(manifest['available_by'].replace('Z','+00:00'))
    origin=datetime.fromisoformat(ORIGIN.replace('Z','+00:00'))
    if available.tzinfo is None or available.utcoffset().total_seconds()!=0 or available>=origin:
        raise ValueError('Historical mapping availability not pre-origin UTC')
    origin_pins=origin_ancestor_pins(freeze,parent_pin)
    # Qualification covers the complete raw/receipt/schema closure, not just
    # declarations in a rehashed projection manifest.
    from tools.science.historical_inputs import verify_manifest
    closure_before=verify_manifest(manifest_path,audit_original_rows=False,
        expected_manifest_sha256=manifest_pin['sha256'])
    historical_pins=closure_before['ancestor_pins']
    programs=next(Path(f['path']) for f in freeze['files'] if Path(f['path']).name=='origin-programs.jsonl')
    products={p['product']:p for p in manifest['products']}
    if set(products)!={'molecule','mechanismOfAction','targets','diseases'}: raise ValueError('Incomplete mapping projections')
    raw_proofs={Path(p['path']).name:p['sha256'] for p in manifest['files']}
    aliases={}; molecules={}; mechanisms={}; targets={}; diseases={}; disease_aliases={}
    forbidden={'maximumClinicalTrialPhase','hasBeenWithdrawn','isApproved','indications','linkedDiseases','linkedTargets','clinicalTrials'}
    for name,product in products.items():
        path=Path(product['path'])
        if sha(path)!=product['sha256']: raise ValueError('Changed historical projection')
        count=0
        with path.open(encoding='utf-8') as f:
            for raw in f:
                item=json.loads(raw);r=item['record'];proof=item['source'];count+=1
                if forbidden & set(r) or set(r)-set(product['approved_columns']): raise ValueError('Unapproved historical annotation field')
                if raw_proofs.get(Path(proof['path']).name)!=proof['sha256']: raise ValueError('Unbound historical source-row proof')
                if name=='molecule':
                    if r['id'] in molecules: raise ValueError('Duplicate molecule ID')
                    molecules[r['id']]=proof
                    for term in (r.get('name'),r['id'],*(r.get('synonyms') or []),*(r.get('tradeNames') or [])):
                        if norm(term):aliases.setdefault(norm(term),set()).add(r['id'])
                elif name=='mechanismOfAction':
                    for did in r.get('chemblIds') or []:
                        mechanisms.setdefault(did,[]).append({'target_ids':sorted(set(r.get('targets') or [])),
                            'action_type':r.get('actionType'),'target_type':r.get('targetType'),'target_name':r.get('targetName'),
                            'mechanism':r.get('mechanismOfAction'),'source':proof})
                elif name=='targets':targets[r['id']]=proof
                else:
                    diseases[r['id']]=proof
                    syn=r.get('synonyms') or {}
                    for term in (r.get('name'),*((syn.get('hasExactSynonym') or []) if isinstance(syn,dict) else [])):
                        if norm(term):disease_aliases.setdefault(norm(term),set()).add(r['id'])
        if count!=product['rows']: raise ValueError('Historical projection row count differs')
    output.mkdir(parents=True,exist_ok=False)
    (output/'executed-mapping-revision.py').write_bytes(Path(__file__).read_bytes())
    counts=Counter(); parent_count=0
    with programs.open(encoding='utf-8') as source,(output/'origin-programs.jsonl').open('x',encoding='utf-8',newline='\n') as out:
        for raw in source:
            rec=json.loads(raw); parent_count+=1; slots=[]; resolved=set(); candidate_targets=set(); mapping_proofs=[]
            for p in rec['source_products']:
                if cat(p['intervention_type']) not in {'DRUG','BIOLOGICAL'} or re.search(r'\b(placebo|sham|vehicle)\b',norm(p['name'])): continue
                # Alias strings come only from this source record. No fuzzy/current fallback.
                terms=[p['name']]
                proof=rec['source_proof']
                with Path(proof['path']).open('rb') as original:
                    original.seek(proof['byte_offset']);source_raw=original.read(proof['bytes'])
                if hashlib.sha256(source_raw).hexdigest()!=proof['sha256']: raise ValueError('Changed original source row')
                row=json.loads(source_raw)
                terms += [a['name'] for a in row['intervention_other_names'] if a['intervention_id']==p['id']]
                matches=set().union(*(aliases.get(norm(t),set()) for t in terms))
                slots.append({'source_intervention_id':p['id'],'source_terms':terms,'candidate_drug_ids':sorted(matches),
                    'status':'unique_exact_historical_alias' if len(matches)==1 else 'unmapped' if not matches else 'ambiguous_historical_alias'})
                if len(matches)==1:
                    did=next(iter(matches));resolved.add(did)
                    for mech in mechanisms.get(did,[]): candidate_targets.update(mech['target_ids'])
                    mapping_proofs.append({'drug_id':did,'molecule_source':molecules[did],'mechanisms':mechanisms.get(did,[])})
            fully_resolved=bool(slots) and all(s['status']=='unique_exact_historical_alias' for s in slots)
            rec['historical_mapping_slots']=slots;rec['drug_ids']=sorted(resolved) if fully_resolved else []
            rec['target_ids']=sorted(t for t in candidate_targets if t in targets) if fully_resolved else []
            rec['historical_mapping_proofs']=mapping_proofs
            rec['target_mapping_status']='historical_resource_annotation_candidates_only'
            rec['unrecognized_historical_target_ids']=sorted(candidate_targets-set(targets))
            disease_ids=sorted(disease_aliases.get(rec['condition_verbatim_normalized'],set()))
            rec['condition_candidate_ids']=disease_ids
            rec['condition_mapping_status']='unique_exact_historical_alias' if len(disease_ids)==1 else 'unmapped' if not disease_ids else 'ambiguous_historical_alias'
            rec['mapping_status']='unique_exact_historical_drug_aliases' if fully_resolved else 'unknown_or_ambiguous_historical_drug_aliases'
            rec['mapping_inputs_qualified']=True
            rec['qualification_holds']=[h for h in rec['qualification_holds'] if h!='historical_drug_target_mapping_unqualified']
            rec['qualification_holds'].append('historical_annotation_does_not_establish_therapeutic_target_or_scope')
            if not fully_resolved:rec['qualification_holds'].append('drug_identity_unmapped_or_ambiguous')
            if not rec['target_ids']:rec['qualification_holds'].append('no_qualified_target_annotation_link')
            rec['dependence_keys']['target']=['target:'+t for t in rec['target_ids']]
            rec['dependence_keys']['historical_drug']=['drug:'+d for d in rec['drug_ids']]
            rec['reconstructed_origin_information_eligible']=True
            # No re-selection: every parent program is retained with its exact program ID.
            out.write(json.dumps(rec,ensure_ascii=False)+'\n');counts[rec['mapping_status']]+=1
            counts['programs_with_target_annotation' if rec['target_ids'] else 'programs_without_target_annotation']+=1
    if parent_count!=freeze['counts']['conditional_origin_candidates']:raise ValueError('Membership count changed')
    write(output/'origin-mapping-summary.json',{'programs':parent_count,'counts':dict(counts),'selection_changed':False,
        'clinical_ready':False,'qualified_scientific_programs':0,'endpoint_rows_queried':0,
        'limits':['Historical annotation candidates are not experimentally verified therapeutic mechanisms.',
                  'Clinical arm/population/regimen equivalence and prior-phase completeness remain conditional.',
                  'Strict complete origin/dataset availability and locked evaluation are not established.']})
    assets=[output/'origin-programs.jsonl',output/'origin-mapping-summary.json',output/'executed-mapping-revision.py']
    for name in ('origin-public-provenance-receipts.json','origin-nlm-posting-semantics.html','origin-aact-provenance.html'):
        if (parent.parent/name).exists():assets.append(parent.parent/name)
    # No qualified seal is emitted unless every original ancestor still matches
    # the exact bytes validated before projection records were consumed.
    closure_after=verify_manifest(manifest_path,audit_original_rows=False,
        expected_manifest_sha256=manifest_pin['sha256'])
    if closure_after['ancestor_pins']!=historical_pins:
        raise ValueError('Historical ancestor closure changed during mapping')
    verify_pins([*origin_pins,manifest_pin,rules_pin,*historical_pins])
    write(output/'origin-freeze.json',{'schema_version':1,'protocol_id':VERSION+'-mapping-r1',
        'sealed_at_utc':datetime.now(timezone.utc).isoformat(),'origin_at':ORIGIN,'horizon_at':freeze['horizon_at'],
        'snapshot_date':'2025-01-01','status':'sealed_mapping_qualified_reconstructed_exploratory',
        'selection_sealed':True,'parent_origin_seal':parent_pin,
        'historical_mapping_manifest':{**manifest_pin,'release_id':'24.09','available_by':manifest['available_by']},
        'integrity_policy':'exact parsed-byte binding; complete ancestor closure checked before projection consumption and before seal',
        'origin_ancestor_pins':origin_pins,'historical_ancestor_pins':historical_pins,
        'mapping_qualified':True,'mapping_qualification_scope':'complete release-pinned input projections and exact alias candidates; not clinical equivalence',
        'reconstructed_origin_information_eligible':True,'origin_date_qualified':False,'strict_dataset_availability_qualified':False,
        'registry_completeness_qualified':False,'clinical_locked':False,'clinical_ready':False,'endpoint_rows_queried':0,
        'reconstruction_rules_proof':rules_pin,'programs':parent_count,
        'files':[{'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size} for p in assets],
        'provider_spend_usd':0})
    return {'programs':parent_count,'counts':dict(counts),'seal':str(output/'origin-freeze.json'),'sha256':sha(output/'origin-freeze.json')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--restore',type=Path,required=True);p.add_argument('--pg-bin',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--port',type=int,default=55439)
    a=p.parse_args();extract(a.restore,a.pg_bin,a.output,a.port)
