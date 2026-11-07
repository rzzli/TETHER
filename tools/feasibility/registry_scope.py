"""Frozen evaluator-only condition/prior-risk/context audit of fixed v0.4 members."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

from tether_engine.serde import sha256_file
from tools.feasibility.registry_extract import load,write
from tools.feasibility.registry_cohort import norm,category,start_bounds,peak_memory_bytes


def ontology_index(rows):
    aliases=defaultdict(set);proofs=defaultdict(list);ancestors={};seen=set()
    for row in rows:
        did=row['id']
        if not did or did in seen:raise ValueError('Duplicate/missing disease ID')
        seen.add(did);ancestors[did]=set(row.get('ancestors') or [])
        terms=[('name',row.get('name'))]+[('hasExactSynonym',t) for t in (row.get('synonyms') or {}).get('hasExactSynonym',[]) or []]
        for kind,term in terms:
            if norm(term):
                aliases[norm(term)].add(did)
                item={'id':did,'field':kind,'original':term}
                if item not in proofs[norm(term)]:proofs[norm(term)].append(item)
    return aliases,proofs,ancestors


def relation(left,right,aliases,ancestors):
    a,b=aliases.get(norm(left),set()),aliases.get(norm(right),set())
    if len(a)==len(b)==1:
        x,y=next(iter(a)),next(iter(b))
        if x==y:return 'same_unique_ontology_id'
        if x in ancestors.get(y,set()) or y in ancestors.get(x,set()):return 'hierarchy_alert_only'
    if norm(left)==norm(right):return 'same_verbatim_unresolved_ontology'
    return None


FACETS={
 'route':{'oral':r'\boral(?:ly)?\b|\bby mouth\b|\bPO\b','intravenous':r'\bintravenous(?:ly)?\b|\bi\.?v\.?\b',
          'subcutaneous':r'\bsubcutaneous(?:ly)?\b|\bSC\b','intranasal':r'\bintranasal(?:ly)?\b|\bnasal powder\b'},
 'age_words':{'pediatric':r'\bpediatric\b|\bpaediatric\b|\bchildren\b','adult':r'\badults?\b','adolescent':r'\badolescents?\b'},
 'setting':{'adjuvant':r'\badjuvant\b','neoadjuvant':r'\bneoadjuvant\b','metastatic':r'\bmetastatic\b','advanced':r'\badvanced\b'},
 'prior_treatment':{'untreated':r'\buntreated\b|\btreatment.naive\b','previously_treated':r'\bpreviously treated\b|\bprior treatment\b',
                    'refractory':r'\brefractory\b','relapsed':r'\brelapsed\b|\brecurrent\b'},
 'design':{'extension':r'\bextension\b|\bcontinuation\b|\bfeeder stud','bridging':r'\bbridging\b|\bJapanese\b'},
 'regimen':{'additional_drug_narrative':r'\bin combination\b|\bin addition to\b|\bdrug cocktail\b|\bplus\b'}
}


def context(row,arm_ids):
    """Text signals, not complete eligibility, dose, species or intervention inference."""
    fields=[];linked=set();arm_ids=set(arm_ids)
    for arm in row['design_groups']:
        if arm['id'] in arm_ids:
            fields.extend((f"arm:{arm['id']}:{k}",arm.get(k)) for k in ['title','description'])
    for link in row['design_group_interventions']:
        if link['design_group_id'] in arm_ids:linked.add(link['intervention_id'])
    non_drug=[]
    for item in row['interventions']:
        if item['id'] not in linked:continue
        fields.extend((f"intervention:{item['id']}:{k}",item.get(k)) for k in ['name','description'])
        if category(item['intervention_type']) in {'PROCEDURE','RADIATION','DEVICE'}:
            non_drug.append({'id':item['id'],'type':item['intervention_type'],'name':item['name']})
    def scan(items):
        found=[]
        for locator,text in items:
            if not text:continue
            for facet,values in FACETS.items():
                for value,pattern in values.items():
                    for match in re.finditer(pattern,text,re.I):
                        prefix=text[max(0,match.start()-28):match.start()]
                        negated=bool(re.search(r'\b(no|not|without|non)[ -]?(?:\w+\s+){0,2}$',prefix,re.I))
                        found.append({'facet':facet,'value':value,'field':locator,'negated_or_qualified':negated,
                                      'excerpt':text[max(0,match.start()-35):min(len(text),match.end()+55)]})
        return found
    signals=scan(fields)
    return {'arm_signals':signals,'study_wide_signals':scan([('study:brief_title',row['study'].get('brief_title'))]),
        'non_drug_partners':non_drug,'missing_eligibility':True,'scope_equivalence':'not_established'}


def compare_context(origin,followup):
    def values(c,facet):return {s['value'] for s in c['arm_signals'] if s['facet']==facet and not s['negated_or_qualified']}
    flags=[];missing=[]
    for facet in ['route','age_words','setting','prior_treatment']:
        a,b=values(origin,facet),values(followup,facet)
        if not a or not b:missing.append(facet)
        elif a.isdisjoint(b):flags.append(facet+'_text_differs')
    if values(origin,'design') or values(followup,'design'):flags.append('extension_or_regional_context')
    if origin['non_drug_partners'] or followup['non_drug_partners']:flags.append('non_drug_regimen_partner')
    if values(origin,'regimen') or values(followup,'regimen'):flags.append('additional_drug_narrative')
    # Study-wide words provide additional review leads, never arm eligibility.
    for facet in ['route','age_words','setting','prior_treatment']:
        a={s['value'] for s in origin['study_wide_signals'] if s['facet']==facet and not s['negated_or_qualified']}
        b={s['value'] for s in followup['study_wide_signals'] if s['facet']==facet and not s['negated_or_qualified']}
        if a and b and a.isdisjoint(b):flags.append('study_wide_'+facet+'_text_differs')
    if any(s['facet']=='design' and not s['negated_or_qualified'] for c in [origin,followup] for s in c['study_wide_signals']):
        flags.append('study_wide_extension_or_regional_context')
    return {'alerts':flags,'unreported_facets':missing,'clinical_scope_equivalence':'not_established',
            'experimental_first_dosing':None,'training_label':None}


def verify_prior_row(alert,row):
    s=row['study']
    if (s['nct_id']!=alert['source_proof']['nct'] or category(s['phase'])!=category(alert['phase'])
            or s.get('start_month_year')!=alert['start'] or category(s.get('start_date_type'))!=alert['date_type']
            or alert['condition'] not in {norm(c['name']) for c in row['conditions']}
            or not any(a['id']==alert['source_arm_id'] and category(a['group_type'])=='EXPERIMENTAL' for a in row['design_groups'])):
        raise ValueError('Prior-risk projection disagrees with original row')


def checked_file(path,expected):
    if sha256_file(Path(path))!=expected:raise ValueError('Changed pinned file: '+str(path))


def read_disease_rows(path):
    import pyarrow.parquet as pq
    return pq.read_table(path,columns=['id','name','synonyms','ancestors']).to_pylist()


def run(protocol_path,freeze_path,output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();policy=load(protocol_path);freeze=load(freeze_path)
    if policy['protocol_id']!='registry-scope-development-v0.5' or policy['role']!='evaluation_only':raise ValueError('Wrong scope protocol')
    checked_file(protocol_path,freeze['protocol']['sha256'])
    write(output/'execution.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha256_file(protocol_path),
        'code_sha256':sha256_file(Path(__file__)),'role':'evaluation_only'})
    try:_run(policy,output,protocol_path)
    except BaseException as exc:
        write(output/'failure.json',{'type':type(exc).__name__,'error':str(exc),'automatic_retry':False});raise
    finally:write(output/'resources.json',{'elapsed_seconds':time.monotonic()-started,'peak_memory_bytes':peak_memory_bytes(),'provider_spend_usd':0})


def _run(policy,output,protocol_path):
    parent=policy['parent_anchor'];checked_file(parent['path'],parent['sha256']);anchor=load(parent['path'])
    sealpath=Path(anchor['canonical_manifest']['path']);checked_file(sealpath,anchor['canonical_manifest']['sha256']);seal=load(sealpath)
    root=sealpath.parent;seen=set()
    for item in seal['files']:
        p=(root/item['path']).resolve()
        if not p.is_relative_to(root.resolve()) or p in seen:raise ValueError('Unsafe/duplicate parent member')
        seen.add(p);checked_file(p,item['sha256'])
    inp=policy['disease_input'];checked_file(inp['path'],inp['sha256']);checked_file(inp['receipt_path'],inp['receipt_sha256'])
    receipt=load(inp['receipt_path'])
    if receipt['status']!='completed' or receipt['dataset_id']!='ot_disease' or receipt['release_id']!='25.09' or receipt['sha256']!=inp['sha256'] or receipt['bytes']!=Path(inp['path']).stat().st_size:
        raise ValueError('Disease receipt mismatch')
    rows=read_disease_rows(inp['path'])
    aliases,termproofs,ancestors=ontology_index(rows)
    dbpath=root/anchor['cohort']/'cohort.sqlite'
    wal=dbpath.with_name(dbpath.name+'-wal')
    if wal.exists() and wal.stat().st_size:raise ValueError('Parent index is not checkpointed')
    db=sqlite3.connect('file:'+dbpath.resolve().as_posix()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row
    programs=[json.loads(line) for line in (root/anchor['cohort']/'cohort.jsonl').read_text(encoding='utf-8').splitlines()]
    events=load(root/anchor['cohort']/'candidate-events.json')
    terms=[r[0] for r in db.execute('SELECT DISTINCT condition FROM arms ORDER BY condition')]
    termmap=[{'term':t,'candidate_ids':sorted(aliases.get(t,set())),'status':'unique_exact' if len(aliases.get(t,set()))==1 else 'ambiguous' if aliases.get(t) else 'unmapped',
        'matches':termproofs.get(t,[])} for t in terms]
    write(output/'condition-map.json',{'role':'evaluation_only','disease_sha256':inp['sha256'],'terms':termmap})
    write(output/'mapping-freeze.json',{'condition_map_sha256':sha256_file(output/'condition-map.json'),
        'at_utc':datetime.now(timezone.utc).isoformat(),'before_prior_and_event_joins':True})
    bydrug=defaultdict(list)
    for p in programs:bydrug[p['drug_id']].append(p)
    wanted=defaultdict(dict);risk=defaultdict(list)
    def want(proof):
        key=str(Path(proof['source']).resolve());line=proof['line']
        if line in wanted[key] and wanted[key][line]!=proof['row_sha']:raise ValueError('Conflicting row proof')
        wanted[key][line]=proof['row_sha']
    for p in programs:
        for proof in p['source_proofs']:want(proof)
    for e in events:want(e['source_proof'])
    origin=load(root/'frames.json')['snapshots'][0]['snapshot_date']
    sql='SELECT DISTINCT p.drug,p.condition,p.arm_id,p.resolved,p.reason,o.* FROM possible p JOIN observations o USING(snapshot,nct) WHERE p.snapshot=?'
    for row in db.execute(sql,(origin,)):
        possible=bydrug.get(row['drug'],[])
        if not possible:continue
        numeric=[int(x) for x in re.findall('[1-4]',category(row['phase_raw']))]
        maximum=max(numeric,default=0)
        if not maximum:continue
        lo,hi,precision=start_bounds(row['start'],row['start_raw'])
        if lo and lo>origin:continue
        for p in possible:
            if maximum<=p['origin_phase']:continue
            rel=relation(p['condition'],row['condition'],aliases,ancestors)
            if not rel:continue
            proof={k:row[k] for k in ['snapshot','nct','row_sha','line','source']};want(proof)
            risk[p['program_id']].append({'relation':rel,'condition':row['condition'],'phase':row['phase_raw'],
                'start':row['start_raw'],'date_type':row['start_kind'],'precision':precision,'source_arm_id':row['arm_id'],
                'actual_before_origin':bool(row['start_kind']=='ACTUAL' and hi and hi<=origin),
                'role_resolved':bool(row['resolved']),'role_holds':json.loads(row['reason']),'source_proof':proof,
                'interpretation':'prior-risk review alert; clinical equivalence not adjudicated'})
    # Hash every parent frame and verify the original bytes for every new proof.
    checks=defaultdict(list)
    for alerts in risk.values():
        for alert in alerts:
            p=alert['source_proof'];checks[(str(Path(p['source']).resolve()),p['line'])].append(alert)
    framepaths=set();proof_count=0
    for frame in load(root/'frames.json')['snapshots']:
        path=Path(frame['path']).resolve();framepaths.add(str(path));h=hashlib.sha256()
        with path.open('rb') as stream:
            for line,raw in enumerate(stream,1):
                h.update(raw)
                if line in wanted.get(str(path),{}):
                    if hashlib.sha256(raw).hexdigest()!=wanted[str(path)][line]:raise ValueError('Original proof changed')
                    for alert in checks[(str(path),line)]:verify_prior_row(alert,json.loads(raw))
                    proof_count+=1
        if h.hexdigest()!=frame['sha256']:raise ValueError('Frame hash changed')
    if not set(wanted).issubset(framepaths) or proof_count!=sum(len(v) for v in wanted.values()):raise ValueError('Incomplete source proofs')
    scope=[];non_disease=set(policy['clinical_scope']['non_disease_exact_terms']);broad=set(policy['clinical_scope']['broad_condition_exact_terms'])
    for p in programs:
        ids=aliases.get(p['condition'],set())
        scope.append({'program_id':p['program_id'],'drug_name':p['drug_name'],'condition':p['condition'],
            'ontology_ids':sorted(ids),'mapping_status':'unique_exact' if len(ids)==1 else 'ambiguous' if ids else 'unmapped',
            'clinical_scope':'outside_disease_focus' if p['condition'] in non_disease else 'broad_condition_requires_review' if p['condition'] in broad else 'requires_population_review',
            'prior_risk_alerts':risk[p['program_id']],'original_label_state':p['label_state'],'training_label':None})
    write(output/'program-scope.json',scope)
    cache={}
    def original(proof):
        key=(proof['snapshot'],proof['nct'])
        if key not in cache:
            r=db.execute('SELECT row_json,row_sha FROM observations WHERE snapshot=? AND nct=?',key).fetchone()
            if not r or r['row_sha']!=proof['row_sha']:raise ValueError('Index/source row proof mismatch')
            cache[key]=json.loads(r['row_json'])
        return cache[key]
    pindex={p['program_id']:p for p in programs};event_audits=[]
    for e in events:
        p=pindex[e['program_id']];origin_context=[]
        for nct in p['origin_active_trials']:
            proofs=[s for s in p['source_proofs'] if s['nct']==nct]
            proof={**proofs[0],'snapshot':origin};origin_context.append({'source_proof':proof,'context':context(original(proof),[s['arm_id'] for s in proofs])})
        # Event rows were already source-checked by the sealed v0.4 audit. Verify
        # this link also resolves to that admitted index row before parsing context.
        followup=context(original(e['source_proof']),[e['source_arm_id']])
        comparisons=[compare_context(o['context'],followup) for o in origin_context]
        event_audits.append({'program_id':p['program_id'],'event_id':e['event_id'],'nct_id':e['nct_id'],
            'original_status':e['status'],'origin_contexts':origin_context,'followup_context':followup,
            'source_proof':e['source_proof'],'comparisons':comparisons,'clinical_scope_equivalence':'not_established'})
    db.close();write(output/'event-scope.json',event_audits)
    report={'role':'evaluation_only','protocol_sha256':sha256_file(protocol_path),'programs':len(scope),'event_links':len(event_audits),
        'mapping_status':dict(Counter(p['mapping_status'] for p in scope)),
        'clinical_scope':dict(Counter(p['clinical_scope'] for p in scope)),
        'programs_with_prior_alerts':sum(bool(p['prior_risk_alerts']) for p in scope),
        'prior_relations':dict(Counter(a['relation'] for p in scope for a in p['prior_risk_alerts'])),
        'recorded_start_programs_with_prior_alerts':sum(bool(p['prior_risk_alerts']) and p['original_label_state']=='recorded_next_phase_start' for p in scope),
        'event_comparison_alerts':dict(Counter(f for e in event_audits for c in e['comparisons'] for f in c['alerts'])),
        'original_rows_rehashed_for_origin_and_prior_proofs':proof_count,'v04_parent_files_verified':len(seen),
        'scientifically_qualified_labels':None,'training_labels':0,'scientific_validation':'not_established',
        'limitations':['Fixed v0.4 population/links; no ontology-normalized event re-enumeration or recall estimate.',
            'Ontology includes phenotypes and measurements; exact alias identity is not clinical population identity.',
            'Hierarchy and text differences are review alerts, not proven exclusions or contradictions.',
            'Complete eligibility and experimental arm-specific first dosing are unavailable in selected frames.']}
    write(output/'summary.json',report);print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.protocol,args.freeze,args.output)
