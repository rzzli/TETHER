"""Compare two externally anchored source diagnostics; no production imports."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path

helper=Path(__file__).with_name('audit.py')
if hashlib.sha256(helper.read_bytes()).hexdigest()!='700ab30f03c9c61f7c8dc4dd7b39c75bb956de350d2ec10f9314025c52e5b392':raise ValueError('Independent helper changed')
spec=importlib.util.spec_from_file_location('source_comparison_io',helper)
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
AUDIT_SHA='d8bba9effebaf5d1292ea61a57b61501f8f67ed43e1bccd4d9e371a42fcf11d7'
SEAL_SHA='118711b7e7552750e441380b7abf8f60b68096ae98ef3163cf96754e7423fa6f'


def run():
    raw=A.read(Path(__file__).with_name('SOURCE-DOI-02.json'));A.need(A.sha(raw)==AUDIT_SHA,'Independent DOI audit anchor differs')
    independent=A.parse(raw)
    root=A.ROOT/'data/benchmark/labbench/evaluation-20261106T011303Z-attempt01'
    seal_raw=A.read(root/'SEALED.json');A.need(A.sha(seal_raw)==SEAL_SHA,'Primary evaluation seal anchor differs');seal=A.parse(seal_raw)
    A.need(seal['kind']=='labbench_native_evaluation' and seal['status']=='completed'
        and seal['input_anchors']['external_sealed_sha256']==independent['anchors']['generation_sealed_sha256'],
        'Compared analyses did not use the same sealed generation')
    primary=A.parse(A.read_proof(root,seal['outputs']['source-alignment.json']))
    A.need(A.sha(A.read(root/'journal.jsonl'))==seal['journal_sha256'],'Primary sealed journal differs')
    original={row['id']:row for row in independent['cases']}
    A.need(len(original)==199,'Independent DOI audit omitted questions')
    comparison={}
    for arm,method in (('retained_fulltext','retained_metadata'),('selected_for_prompt','selected_metadata')):
        actual=primary[arm];expected=independent['metrics'][method]
        A.need(actual['doi_identifier']['annotated_doi_count']==expected['annotated_doi_pairs']
            and actual['doi_identifier']['hit_doi_count']==expected['hit_doi_pairs']
            and actual['doi_identifier']['recall']==expected['doi_identifier_recall'],'Primary DOI denominator/numerator differs')
        A.need(actual['primary']['scheduled_count']==expected['scheduled_questions']
            and actual['primary']['observed_annotated_source_hit_questions']==expected['hit_questions']
            and actual['primary']['observed_annotated_source_hit_per_scheduled']==expected['doi_hit_per_all_scheduled'],
            'Primary all-scheduled source-hit denominator/numerator differs')
        cases=actual['case_results'];A.need(len(cases)==len(original) and {row['id'] for row in cases}==set(original),'Primary case identity differs')
        for row in cases:
            baseline=original[row['id']]
            A.need(row['annotated_doi_count']==baseline['annotated_doi_count'] and row['hit_doi_count']==baseline[method+'_hit_count']
                and row['annotated_source_hit'] is (baseline[method+'_hit_count']>0),'Per-case DOI/question hit differs')
        comparison[arm]={'matched_cases':len(cases),'doi_pairs':{'matched':expected['hit_doi_pairs'],'denominator':expected['annotated_doi_pairs']},
            'questions':{'matched':expected['hit_questions'],'denominator':expected['scheduled_questions']},
            'conditional_resolved_paper_reported_by_primary_only':actual['conditional_resolved_paper'],
            'resolution_reported_by_primary_only':actual['resolution'],'primary_semantic_support':actual['semantic_support']}
    return {'schema_version':1,'status':'PASS','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'comparison_code_sha256':A.sha(A.read(__file__)),'independent_doi_audit_sha256':AUDIT_SHA,'primary_evaluation_seal_sha256':SEAL_SHA,
        'primary_source_alignment_sha256':seal['outputs']['source-alignment.json']['sha256'],
        'comparison':comparison,'reference_reread':False,'network_calls':0,'model_calls':0,
        'interpretation':['Exact aggregate and all199 per-case agreement for DOI-pair and question-hit counts in both source arms',
            'Conditional resolved-paper recall is conditioned on available metadata and is not overall annotated-source recall',
            'The independent parser does not reproduce the production alias graph; conditional paper counts are copied with that scope explicitly labeled',
            'Agreement establishes source-identity counting consistency, not entailment, answer correctness or literature completeness']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();value=run()
    with Path(args.output).open('xb') as stream:stream.write(A.canonical(value)+b'\n')
    print(json.dumps({'status':value['status'],'comparison':value['comparison']}))
