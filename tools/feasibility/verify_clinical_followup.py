"""Verify retained AACT follow-up restoration and deterministic registry comparison."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from tools.feasibility.compare_clinical_snapshots import compare


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def verify(project, restore, comparison, origin):
    public = load(project/'data/manifests/public/2026-10-16-feasibility-pilots.json')
    anchor = next(x for x in public['evidence_manifests'] if Path(x['root']).resolve()==origin.resolve())
    manifest = origin/anchor['manifest']
    require(sha(manifest)==anchor['sha256'],'Origin evidence manifest changed')
    for entry in load(manifest)['files']:
        path=(origin/entry['path']).resolve()
        require(path.is_relative_to(origin.resolve()),'Origin proof escapes root')
        require(sha(path)==entry['sha256'],'Frozen origin artifact changed: '+entry['path'])
    restored=load(restore/'restore-result.json')
    require(restored['status']=='completed' and restored['server_stopped'],'Restore/audit/stop incomplete')
    audit=load(restore/'technical-audit.json')
    require(audit['status']=='completed','Technical audit incomplete')
    toc=set(re.findall(r'TABLE ctgov (\w+) ',(restore/'dump-toc-pg17.txt').read_text()))
    actual={x['table'] for x in audit['tables'] if x['schema']=='ctgov'}
    require(toc==actual,'TOC/restored table set differs')
    require(all(x['convalidated'] for x in audit['constraints']),'Unvalidated constraint')
    require(all(x['indisvalid'] and x['indisready'] for x in audit['indexes']),'Invalid index')
    require(audit['study_id_check']['rows']==audit['study_id_check']['distinct_nct_ids'],'Duplicate study IDs')
    require(not audit['study_id_check']['null_nct_ids'],'Null study ID')
    archive=load(restore/'archive-inspection.json')
    require(archive['status']=='archive_integrity_passed','Archive check incomplete')
    execution=load(comparison/'execution.json')
    require(execution['status']=='completed','Comparison incomplete')
    require(execution['source_sha256']==sha(comparison/'followup-records.json'),'Follow-up query bytes changed')
    require(execution['selected_sha256']==sha(origin/'selected.json'),'Selection changed')
    require(execution['protocol_sha256']==sha(origin/'protocol.json'),'Origin protocol changed')
    require(execution['code_sha256']==sha(project/'tools/feasibility/compare_clinical_snapshots.py'),'Comparison code differs')
    selected=load(origin/'selected.json');protocol=load(origin/'protocol.json')
    replay=compare(selected,load(comparison/'followup-records.json'),load(origin/'mapping-review.json'),
                   protocol['origin_date'],protocol['followup_date'])
    require(replay==load(comparison/'comparison.json'),'Comparison replay differs')
    page=(comparison/'Review.html').read_text(encoding='utf-8')
    require(page.count('<article>')==len(selected) and '<script' not in page,'Review HTML structure differs')
    date_flags=[x for x in audit['study_date_ranges'] if x['column'] in
                ('study_first_posted_date','last_update_posted_date','results_first_posted_date')]
    require(not any(x['after_candidate_date'] for x in date_flags),'Future posting dates in snapshot')
    exceptions=[x for x in audit['tables'] if any(x.get(k,0) for k in
                ('null_nct_ids','malformed_nct_ids','orphan_nct_ids'))]
    return {'schema_version':1,'status':'technical_checks_passed','tables':len(actual),
        'total_table_rows':sum(x['rows'] for x in audit['tables']),
        'studies':audit['study_id_check']['rows'],'constraints':len(audit['constraints']),
        'valid_indexes_including_toast':len(audit['indexes']),
        'application_indexes':sum(x['schema']=='ctgov' for x in audit['indexes']),
        'table_id_exceptions':exceptions,'posting_date_checks':date_flags,
        'comparison_trials':len(replay),'comparison_replay':'identical','origin_evidence_manifest':'unchanged',
        'clinical_labels_assigned':0,'scientific_validation':'not_established',
        'publisher_checksum_and_exact_public_availability':'unverified'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('project','restore','comparison','origin','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    result=verify(args.project,args.restore,args.comparison,args.origin)
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(result))
