"""All-case scientific summaries of independently reconstructed SC04 records."""
from collections import Counter

from .native_records import canonical, need
from .scoring import score_arm, paper_metrics, factorial, ordered
from .metrics import ARMS, contrasts


def summarize(primary, supplied, inputs, *, expected_count=199, replicates=10000, seed=20261106):
    queries=inputs['queries']; refs=inputs['references']; ids=[q['id'] for q in queries]
    need(len(ids)==expected_count and primary['queries']==supplied['queries']==queries, 'Original identical complete question schedule')
    need(set(primary['records'])==set(ARMS) and set(supplied['records'])=={'supplied'}, 'Four primary arms plus diagnostic')
    for run in (primary,supplied):
        need(run['status']=='independently_reconstructed' and run['source_lineage_checked'] is True and
             run['native_calls_checked'] is True and run['cross_stage_products_checked'] is True, 'Reconstruction required before scoring')
    metrics={}; source_metrics={}; accounting={}; cases={}
    for run in (primary,supplied):
        for arm, rows in run['records'].items():
            metrics[arm]=score_arm(queries,refs,rows,run['evidence_ids'][arm])
            metrics[arm]['provenance_validated']=True
            source_cases=run['source_cases'][arm];ordered(source_cases,ids,'source cases')
            cases[arm]=source_cases
            source_metrics[arm]={level:paper_metrics(ids,inputs['annotations'],{r['id']:r[level+'_dois'] for r in source_cases})
                                 for level in ('retained','pool','selected')}
            usage={key:sum(r['logical_model_usage'][key] for r in source_cases) for key in source_cases[0]['logical_model_usage']}
            accounting[arm]=dict(logical_model_usage=usage, selected_text_bytes=sum(r['selected_bytes'] for r in source_cases),
                selected_passages=sum(r['selected_passages'] for r in source_cases),
                native_status_counts=dict(Counter(r['native_status'] for r in source_cases)),
                no_selected_passage_cases=sum(r['selected_passages']==0 for r in source_cases),
                warning='Shared expansion/collection resources are charged to multiple logical arms; do not sum as physical cost.')
            accounting[arm]['logical_http_usage']={key:sum(r['logical_http_usage'][key] for r in source_cases)
                                                   for key in source_cases[0]['logical_http_usage']}
            for field in ('retained_original_bytes','extracted_paragraph_bytes','candidate_pool_bytes'):
                accounting[arm][field]=sum(r[field] for r in source_cases)
            if arm!='supplied':
                accounting[arm]['expansion_status_counts']=dict(Counter(r['expansion_status'] for r in source_cases))
                accounting[arm]['ranking_status_counts']=dict(Counter(r['ranking_status'] for r in source_cases))
                for field in ('expansion_native_status','ranking_native_status','expansion_failure_reason','ranking_failure_reason'):
                    accounting[arm][field+'_counts']=dict(Counter(r[field] for r in source_cases if r[field] is not None))
    changed={}
    for branch in ('L','E'):
        before=primary['evidence_ids'][branch+'/O'];after=primary['evidence_ids'][branch+'/R']
        changed[branch]=dict(membership_changed=sum(set(before[i])!=set(after[i]) for i in ids),
            order_changed_with_same_membership=sum(set(before[i])==set(after[i]) and before[i]!=after[i] for i in ids),
            identical_selection=sum(before[i]==after[i] for i in ids))
        need(sum(changed[branch].values())==expected_count,'All selection transitions accounted')
    available={r['id'] for r in cases['supplied'] if r['source_coverage']['retained_articles']>0}
    all_available={r['id'] for r in cases['supplied'] if not r['source_coverage']['unknown_or_unavailable_inputs']}
    subsets={}
    for label,subset in (('any_annotated_source_eligible',available),('all_annotated_sources_eligible',all_available)):
        if subset:
            subsets[label]=score_arm([q for q in queries if q['id'] in subset],[r for r in refs if r['id'] in subset],
                [r for r in supplied['records']['supplied'] if r['id'] in subset],{k:v for k,v in supplied['evidence_ids']['supplied'].items() if k in subset})
            subsets[label]['provenance_validated']=True
        else:subsets[label]=dict(scheduled_count=0,metrics=None,reason='No eligible source subset; full cohort remains in primary report.')
    availability={}
    e={r['id'] for r in cases['E/O'] if r['expansion_native_status']=='completed'}
    l={r['id'] for r in cases['L/R'] if r['ranking_native_status']=='completed'}
    r={r['id'] for r in cases['E/R'] if r['ranking_native_status']=='completed'}
    for label,subset in (('expansion_available',e),('lexical_branch_ranking_available',l),
                         ('expanded_branch_ranking_available',r),('all_interventions_available',e&l&r)):
        selected={}
        if subset:
            for arm in ARMS:
                selected[arm]=score_arm([q for q in queries if q['id'] in subset],[ref for ref in refs if ref['id'] in subset],
                    [record for record in primary['records'][arm] if record['id'] in subset],
                    {k:v for k,v in primary['evidence_ids'][arm].items() if k in subset})
                selected[arm]['provenance_validated']=True
        availability[label]=dict(scheduled_count=len(subset),ids=[i for i in ids if i in subset],arms=selected,
            raw_accuracy_contrasts=contrasts({a:s['raw_metrics']['accuracy'] for a,s in selected.items()}) if subset else None,
            scope='Secondary intervention-availability subset; conditioned on execution success, not a replacement for full-cohort contrasts.')
    return dict(kind='sc04_all_scheduled_scientific_summary_v1',scheduled_count=expected_count,arms=metrics,
        source_metrics=source_metrics,paired=factorial({a:metrics[a] for a in ARMS},inputs['groups'],replicates=replicates,seed=seed),
        ranking_selection_changes=changed,logical_arm_accounting=accounting,
        physical_accounting=dict(primary=primary['resources'],supplied=supplied['resources']),
        supplied_source_subsets=subsets,available_intervention_subsets=availability,diagnostic_resolutions=supplied['diagnostic_resolutions'],
        source_cases=cases,model_provider_spend_usd=0,
        limits=['Repeatedly exposed public development set, not an untouched holdout.',
                'Paper identity matching is not decisive-passage recall or semantic support.',
                'Source admission is not evidence entailment or scientific validation.',
                'Archived baseline differs in acquisition time, prompt and allocation.',
                'Physical provider spend is zero; energy, labour and GPU memory are not measured.'])


def native_agreement(summary, primary, supplied, inputs, scorer):
    """Run the separately pinned native scorer; caller verifies its code first."""
    checked=[]
    keys=('scheduled_count','counts','raw_metrics','checked_metrics','raw_precision_defined','checked_precision_defined',
          'producer_status_counts','check_status_counts','case_results')
    for run in (primary,supplied):
        for arm,records in run['records'].items():
            native=scorer(inputs['queries'],inputs['references'],records,evidence_ids_by_query=run['evidence_ids'][arm])
            # Native freeze() returns tuple/mapping wrappers. Convert without importing its serializer.
            def plain(value):
                if hasattr(value,'items'):return {k:plain(v) for k,v in value.items()}
                if isinstance(value,(list,tuple)):return [plain(v) for v in value]
                return value
            native=plain(native)
            for key in keys:need(canonical(native[key])==canonical(summary['arms'][arm][key]),'Independent/native score mismatch: '+arm+' '+key)
            checked.append(dict(arm=arm,checks=list(keys),native=native))
    return dict(status='PASS',arms_checked=5,comparisons=checked)
