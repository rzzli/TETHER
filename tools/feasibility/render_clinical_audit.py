"""Join retained review annotations and provenance into a readable local audit."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--data-root',type=Path,required=True)
    args=parser.parse_args();root=args.root
    def read(name):return json.loads((root/name).read_text(encoding='utf-8'))
    cases=read('selected.json');annotations=read('review-annotations.json')
    assessments={x['candidate_id']:x for x in annotations['assessments']}
    receipts={x['nct_id']:x for x in read('current-record-receipts.json')}
    availability={x['nct_id']:x for x in read('origin-result-availability.json')}
    hreceipt=json.loads((args.data_root/'manifests/receipts/hgnc-snapshot-2026-10-10.json').read_text())
    hgnc=args.data_root/'reference/hgnc_symbols/snapshot_2026-10-10/hgnc_complete_set.txt'
    assert hashlib.sha256(hgnc.read_bytes()).hexdigest()==hreceipt['sha256']
    with hgnc.open(encoding='utf-8') as f:
        genes={x['symbol']:x for x in csv.DictReader(f,delimiter='\t') if x['status']=='Approved'}
    result=[]
    for case in cases:
        row=case['origin_record'];nct=row['nct_id'];review=assessments[case['candidate_id']]
        current=read('current_records/'+nct+'.json')['protocolSection']['statusModule']
        gene=genes[case['target_anchor']]
        result.append({**review,'nct_id':nct,'target_symbol':case['target_anchor'],
            'target_hgnc_id':gene['hgnc_id'],'target_ensembl_id':gene['ensembl_gene_id'],
            'identifier_reference':'HGNC snapshot_2026-10-10; contemporary normalization only',
            'identifier_reference_sha256':hreceipt['sha256'],'drug_anchor':case['drug_anchor'],
            'origin_phase':row['phase'],'origin_status':row['overall_status'],
            'origin_conditions':row['conditions'],
            'origin_primary_endpoints':[x for x in (row['planned_endpoints'] or []) if x['type']=='primary'],
            'origin_results_first_posted':availability[nct]['results_first_posted_date'],
            'review_type':annotations['review_type'],
            'target_mapping_confidence':'contemporary identity supported; historical annotation not adjudicated',
            'program_mapping_confidence':'provisional; '+review['decision'],
            'disease_ontology_mapping':None,
            'ontology_mapping_missing_reason':'Verbatim indications retained; dated ontology mapping not adjudicated',
            'mechanism_source':annotations['mechanism_references'][case['drug_anchor']],
            'origin_proofs':{'source_file':'origin-records.json','nct_id':nct,
                'context_file':'origin-context.json','availability_file':'origin-result-availability.json'},
            'current_registry_observation':{'status':current.get('overallStatus'),
                'why_stopped':current.get('whyStopped'),'last_update_posted':current.get('lastUpdatePostDateStruct'),
                'reported_completion':current.get('completionDateStruct'),
                'results_first_posted':current.get('resultsFirstPostDateStruct'),
                'receipt':receipts[nct],'eligible_as_2025_snapshot':False},
            'event_date':None,'event_publication_date':None,'censoring_date':None,
            'therapeutic_success':None,'clinical_failure':None,
            'unresolved_reason':'No pinned 2025 follow-up snapshot or dated arm/program event adjudication. Current status is not a 2025 outcome label.'})
    summary={'schema_version':1,'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'origin_mapping_screen_completed_longitudinal_audit_pending',
        'cases_reviewed':len(result),'target_families':dict(Counter(x['target_symbol'] for x in result)),
        'decisions':dict(Counter(x['decision'] for x in result)),
        'current_status_descriptive_only':dict(Counter(x['current_registry_observation']['status'] for x in result)),
        'origin_results_already_available':sum(x['origin_results_first_posted'] is not None for x in result),
        'clinical_outcome_labels_assigned':0,'followup_snapshot_missing':'2025-01-01',
        'independent_adjudication':False,
        'coverage_limit':'SCN9A has no selected qualifying seed-matched trial; not evidence of biological absence'}
    for name,doc in [('mapping-review.json',result),('review-summary.json',summary)]:
        with (root/name).open('x',encoding='utf-8',newline='\n') as f:
            json.dump(doc,f,indent=2,ensure_ascii=False);f.write('\n')
    title='Clinical origin audit: 24 trial representatives'
    intro='Single-AI development screen. January 2023 selection was fixed before current records were fetched. All outcome, event and censoring labels remain null; these are not 24 independent adjudicated programs.'
    markdown=['# '+title,'',intro,'','| Case | Trial | Anchor | Decision |','| --- | --- | --- | --- |']
    cards=[]
    esc=html.escape
    for row in result:
        cid,nct=row['candidate_id'],row['nct_id'];url='https://clinicaltrials.gov/study/'+nct
        markdown.append(f"| {cid} | [{nct}]({url}) | {row['target_symbol']} / {row['drug_anchor']} | {row['decision']} |")
        current=row['current_registry_observation']
        observation=f"Current registry: {current['status']}; reported stop reason: {current['why_stopped'] or 'not reported'}. This is a present-day observation."
        cards.append(f'<article><h2>{cid} · {esc(row["drug_anchor"])} <small>{esc(row["target_symbol"])}</small></h2>'
            f'<p><a href="{url}">{nct}</a> · Origin: {esc(row["origin_phase"])} / {esc(row["origin_status"])}</p>'
            f'<p class="decision">{esc(row["decision"].replace("_"," "))}</p><p>{esc(row["review_note"])}</p>'
            f'<details><summary>Evidence, endpoint and unresolved follow-up</summary><p>{esc(observation)}</p>'
            f'<p>{esc(row["unresolved_reason"])}</p><p>Origin conditions: {esc("; ".join(row["origin_conditions"]))}</p>'
            f'<p>Origin primary endpoints: {esc("; ".join(x["measure"] for x in row["origin_primary_endpoints"]))}</p>'
            f'<p><a href="{esc(row["mechanism_source"],quote=True)}">Mechanism reference</a> (current/evaluation-only).</p></details></article>')
    for row in result:
        markdown+=['',f"## {row['candidate_id']} — {row['nct_id']}",'',row['review_note'],'',
            f"Origin: {row['origin_phase']}; {row['origin_status']}. Role: {row['intervention_role']}.",'',
            f"[Mechanism reference]({row['mechanism_source']}) (contemporary/evaluation-only).",'',row['unresolved_reason']]
    (root/'REVIEW.md').write_bytes(('\n'.join(markdown)+'\n').encode())
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>body{font:17px/1.55 system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:0 20px;background:#f4f6f8;color:#182534}h1{line-height:1.2}article{background:white;border:1px solid #d3dde5;border-radius:10px;padding:18px 24px;margin:18px 0}h2{font-size:21px;margin:0}small{color:#536779}a{color:#145d96}summary{cursor:pointer;font-weight:600}.decision{font-weight:700;color:#745000}header{border-left:5px solid #145d96;padding-left:18px}@media print{body{background:white}article{break-inside:avoid}details{display:block}}</style><header><h1>'+title+'</h1><p>'+intro+'</p><p><b>Next required input:</b> a pinned January 2025 follow-up snapshot. Current registry records are kept separate.</p></header>'+''.join(cards)+'</html>'
    (root/'Review.html').write_bytes(page.encode())
    print(json.dumps(summary))


if __name__=='__main__':main()
