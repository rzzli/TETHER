"""Bounded evaluator-only reported results, distinct from planned trial outcomes.

Only the original twelve frozen trials are queried. Source rows are observations,
not success/failure labels; dates and hypotheses require separate adjudication.
"""
from __future__ import annotations

import copy
import re

from tether_engine.serde import ContractError, fingerprint
from tools.science.ascertainment_policy import version_eligibility
from tools.science.outcome_inputs import PRELUDE, _literal, _seal

STUDY_FIELDS = ('nct_id', 'last_update_posted_date', 'last_update_posted_date_type',
    'study_first_posted_date', 'results_first_posted_date', 'results_first_posted_date_type')
RESULT_FIELDS = {
    'outcomes': ('id','nct_id','outcome_type','title','description','time_frame','population',
        'units','units_analyzed','dispersion_type','param_type'),
    'result_groups': ('id','nct_id','ctgov_group_code','result_type','title','description','outcome_id'),
    'outcome_analyses': ('id','nct_id','outcome_id','non_inferiority_type','non_inferiority_description',
        'param_type','param_value','dispersion_type','dispersion_value','p_value_modifier','p_value',
        'ci_n_sides','ci_percent','ci_lower_limit','ci_upper_limit','ci_upper_limit_na_comment',
        'p_value_description','method','method_description','estimate_description','groups_description',
        'other_analysis_description','ci_upper_limit_raw','ci_lower_limit_raw','p_value_raw'),
    'outcome_analysis_groups': ('id','nct_id','outcome_analysis_id','result_group_id','ctgov_group_code'),
    'outcome_counts': ('id','nct_id','outcome_id','result_group_id','ctgov_group_code','scope','units','count'),
    'outcome_measurements': ('id','nct_id','outcome_id','result_group_id','ctgov_group_code',
        'classification','category','title','description','units','param_type','param_value','param_value_num',
        'dispersion_type','dispersion_value','dispersion_value_num','dispersion_lower_limit','dispersion_upper_limit',
        'explanation_of_na','dispersion_upper_limit_raw','dispersion_lower_limit_raw'),
}
REQUIRED = {
    'outcomes': {'id','nct_id'}, 'result_groups': {'id','nct_id'},
    'outcome_analyses': {'id','nct_id','outcome_id'},
    'outcome_analysis_groups': {'id','nct_id','outcome_analysis_id','result_group_id'},
    'outcome_counts': {'id','nct_id','outcome_id','result_group_id'},
    'outcome_measurements': {'id','nct_id','outcome_id','result_group_id'},
}


def require(condition, message):
    if not condition:raise ContractError(message)


def results_query(nct_ids, snapshot_date, schema, *, max_rows_per_trial=100000):
    require(snapshot_date in ('2026-01-01','2026-04-01'), 'Results require approved follow-up snapshot')
    require(isinstance(nct_ids,(list,tuple)) and len(nct_ids)==len(set(nct_ids))==12 and
        all(isinstance(n,str) and re.fullmatch(r'NCT\d{8}',n) for n in nct_ids), 'Exactly twelve unique frozen trial IDs required')
    require(type(max_rows_per_trial) is int and 1<=max_rows_per_trial<=100000, 'Invalid explicit result-row bound')
    ids=sorted(nct_ids)
    require({'nct_id','last_update_posted_date','last_update_posted_date_type','study_first_posted_date'}<=
        set(schema.get('studies',[])), 'Source lacks version eligibility fields')
    projection={'studies':[c for c in STUDY_FIELDS if c in schema['studies']]};missing={}
    missing['studies']=[c for c in STUDY_FIELDS if c not in schema['studies']]
    fields=[];counts=[]
    for table,allowed in RESULT_FIELDS.items():
        available=set(schema.get(table,[]))
        require(not available or REQUIRED[table]<=available, 'Result table lacks mandatory linkage: '+table)
        projection[table]=[c for c in allowed if c in available]
        missing[table]=[c for c in allowed if c not in available]
    for table,parents in {'outcome_analyses':('outcomes',),
        'outcome_analysis_groups':('outcome_analyses','result_groups'),
        'outcome_counts':('outcomes','result_groups'),
        'outcome_measurements':('outcomes','result_groups')}.items():
        require(not projection[table] or all(projection[p] for p in parents),'Result linkage parent table missing')
    def object_sql(columns,alias):
        return 'json_build_object('+','.join(_literal(c)+','+alias+'.'+c for c in columns)+')'
    fields.append("'study',"+object_sql(projection['studies'],'s'))
    for table in RESULT_FIELDS:
        cols=projection[table]
        if cols:
            fields.append(_literal(table)+',coalesce((SELECT json_agg('+object_sql(cols,'t')+
                ' ORDER BY t.id) FROM ctgov.'+table+" t WHERE t.nct_id=s.nct_id),'[]'::json)")
            counts.append('(SELECT count(*) FROM ctgov.'+table+' t WHERE t.nct_id=s.nct_id)')
        else:fields.append(_literal(table)+",'[]'::json")
    count='('+('+'.join(counts) or '0')+')'
    sql=(PRELUDE+'SELECT CASE WHEN '+count+'>'+str(max_rows_per_trial)+
        " THEN json_build_object('overflow',true,'nct_id',s.nct_id,'result_rows',"+count+
        ') ELSE json_build_object('+','.join(fields)+') END FROM ctgov.studies s WHERE s.nct_id IN ('+
        ','.join(_literal(n) for n in ids)+') ORDER BY s.nct_id;\nROLLBACK;')
    return _seal({'kind':'reported_results','snapshot_date':snapshot_date,'nct_ids':ids,
        'source_schema':copy.deepcopy(schema),'projection':projection,
        'missing_source_columns':{t:c for t,c in missing.items() if c},'sql':sql,
        'max_rows_per_trial':max_rows_per_trial,'max_output_bytes':128*1024*1024,
        'cutoff_at':'2026-04-01T00:00:00Z','absence_claim':False,'automatic_labels':False,
        'selection':'Original frozen trial membership only; no result/status/significance filter'})


def regenerate_results(request):
    require(isinstance(request,dict) and request.get('kind')=='reported_results','Wrong result request kind')
    rebuilt=results_query(request['nct_ids'],request['snapshot_date'],request['source_schema'],
        max_rows_per_trial=request['max_rows_per_trial'])
    require(rebuilt==request,'Result request differs from deterministic explicit generator')
    return rebuilt


def validate_result_rows(rows,request):
    regenerate_results(request)
    require(isinstance(rows,list) and len(rows)<=12,'Result envelope exceeds membership bound')
    seen=[];eligible=[];dispositions=[];totals={t:0 for t in RESULT_FIELDS}
    for record in rows:
        require(isinstance(record,dict) and not record.get('overflow'),'Explicit result-row cap exceeded')
        require(set(record)=={'study',*RESULT_FIELDS},'Unexpected result envelope fields')
        study=record['study']
        require(isinstance(study,dict) and set(study)==set(request['projection']['studies']),'Study fields differ from frozen result projection')
        nct=study['nct_id'];require(nct in request['nct_ids'] and nct not in seen,'Cross-trial or duplicate result envelope')
        seen.append(nct);keys={};total=0
        for table in RESULT_FIELDS:
            children=record[table];require(isinstance(children,list),'Result table must be an array')
            ids=[]
            for child in children:
                require(isinstance(child,dict) and set(child)==set(request['projection'][table]),'Unexpected projected result fields')
                require(type(child.get('id')) is int and child['id']>0 and child.get('nct_id')==nct,'Invalid result identity or cross-trial row')
                require(child['id'] not in ids,'Duplicate result primary key');ids.append(child['id'])
            require(ids==sorted(ids),'Result rows lost canonical source order')
            keys[table]=set(ids);total+=len(children);totals[table]+=len(children)
        require(total<=request['max_rows_per_trial'],'Explicit result-row cap exceeded')
        for table,parent,field in (('outcome_analyses','outcomes','outcome_id'),
            ('outcome_analysis_groups','outcome_analyses','outcome_analysis_id'),
            ('outcome_analysis_groups','result_groups','result_group_id'),
            ('outcome_counts','outcomes','outcome_id'),('outcome_counts','result_groups','result_group_id'),
            ('outcome_measurements','outcomes','outcome_id'),('outcome_measurements','result_groups','result_group_id')):
            require(all(type(c[field]) is int and c[field]>0 and c[field] in keys[parent] for c in record[table]),
                'Broken within-trial result linkage: '+table+'.'+field)
        groups={c['id']:c for c in record['result_groups']}
        analyses={c['id']:c for c in record['outcome_analyses']}
        for group in groups.values():
            require(group.get('outcome_id') is None or (type(group['outcome_id']) is int and group['outcome_id'] in keys['outcomes']),
                'Result group references missing outcome')
        for table in ('outcome_counts','outcome_measurements','outcome_analysis_groups'):
            for child in record[table]:
                group_outcome=groups[child['result_group_id']].get('outcome_id')
                outcome=analyses[child['outcome_analysis_id']]['outcome_id'] if table=='outcome_analysis_groups' else child['outcome_id']
                require(group_outcome is None or group_outcome==outcome,'Result group/outcome scope differs')
                source_code=child.get('ctgov_group_code');group_code=groups[child['result_group_id']].get('ctgov_group_code')
                require(source_code is None or group_code is None or source_code==group_code,'Result group code contradicts referenced group')
        temporal=version_eligibility(last_update_posted_date=study.get('last_update_posted_date'),
            first_posted_date=study.get('study_first_posted_date'),cutoff_at=request['cutoff_at'])
        if str(study.get('last_update_posted_date_type','')).upper()!='ACTUAL':temporal['status']='held_unqualified_posting_date_type'
        latest=study.get('last_update_posted_date')
        if isinstance(latest,str) and latest>request['snapshot_date']:temporal['status']='held_posting_date_after_source_snapshot'
        first_results=study.get('results_first_posted_date')
        if first_results is not None:
            from tools.science.ascertainment_policy import publication_bounds
            bounds=publication_bounds(first_results)
            if bounds['status']=='reconstructed' and (first_results>request['snapshot_date'] or
                    (latest is not None and first_results>latest)):
                temporal['status']='held_inconsistent_results_posting_date'
        counts={t:len(record[t]) for t in RESULT_FIELDS}
        dispositions.append({'nct_id':nct,'version_eligibility':temporal,'result_rows':total,
            'table_counts':counts,'reported_results_present':bool(record['outcomes']),
            'clinical_label':None,'absence_claim':False,
            'interpretation':'Presence, p values and registry dates do not establish a clinical success/failure event.'})
        if temporal['status']=='eligible_reconstructed_date_bound':eligible.append(copy.deepcopy(record))
    require(seen==sorted(seen),'Trial result envelopes must retain source order')
    return {'status':'reported_result_rows_validated','role':'evaluation_only',
        'quarantined_rows':copy.deepcopy(rows),'eligible_reconstructed_rows':eligible,
        'version_dispositions':dispositions,'missing_nct_ids':sorted(set(request['nct_ids'])-set(seen)),
        'missing_source_columns':copy.deepcopy(request['missing_source_columns']),'table_counts':totals,
        'clinical_label':None,'clinical_activation':False,'absence_claim':False,
        'origin_membership_changed':False,'prespecified_success_rule_checked':False}
