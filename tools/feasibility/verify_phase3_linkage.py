"""Verify sealed linked-trial extraction and replay timing without a database."""
import argparse
import hashlib
import json
from pathlib import Path
from tools.feasibility.program_outcomes import load, sha, verify_manifest
from tools.feasibility.extract_phase3_followup import validate_extract, query
from tools.feasibility.assess_phase3_link import assess_timing


def verify(output, anchor):
    output=Path(output).resolve()
    count=verify_manifest(output/'evidence-manifest.json',anchor)
    retained=load(output/'verification.json')
    for parent in retained['parents']:
        verify_manifest(Path(parent['path']),parent['sha256'])
    plan=load(output/'plan.json')
    for parent in plan['parents']:
        verify_manifest(Path(parent['path']),parent['sha256'])
    payload=load(output/'extraction/records.json')
    if payload!=load(output/'extraction/extract.stdout.log') or payload!=load(output/'extraction/replay.stdout.log'):
        raise ValueError('Extract and repeated read differ')
    check=validate_extract(payload,plan)
    if (output/'extraction/query.sql').read_text(encoding='utf-8')!=query(plan['nct_ids']):
        raise ValueError('Query differs from bounded read-only recipe')
    prior=None;events=[]
    for line in (output/'extraction/journal.jsonl').read_text(encoding='utf-8').splitlines():
        event=json.loads(line);digest=event.pop('sha256')
        if event['previous']!=prior or hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest()!=digest:
            raise ValueError('Journal chain mismatch')
        prior=digest;events.append(event)
    if events[-1]['stage']!='completed' or not events[-1]['server_stopped']:
        raise ValueError('Extraction/shutdown incomplete')
    for name,code in [('start',0),('extract',0),('replay',0),('stop',0),('status_after',3)]:
        found=[e for e in events if e['stage']==name and e.get('status')=='finished']
        if len(found)!=1 or found[0]['returncode']!=code:raise ValueError('Ambiguous lifecycle or query result')
    for row in load(output/'source-checks.json'):
        proof=row['source'];path=Path(proof['path'])
        if sha(path)!=proof['sha256']:raise ValueError('Changed source proof')
        value=load(path)
        for key in proof['json_pointer'].strip('/').split('/'):
            value=value[int(key)] if isinstance(value,list) else value[key]
        if value!=row['observed_value']:raise ValueError('Source field differs from review')
    assessment=load(output/'assessment.json')
    for proof in assessment['source_proofs']:
        if sha(Path(proof['path']))!=proof['sha256']:raise ValueError('Changed report or record')
    study=next(r['study'] for r in payload['records'] if r['study']['nct_id']=='NCT06203210')
    timing=assess_timing(study,'2024-08-01',plan['origin'],plan['endpoint'])
    if timing!=load(output/'timing-assessment.json') or timing!=assessment['timing']:
        raise ValueError('Timing derivation differs')
    if assessment['strict_historical_event_certified'] or assessment['training_labels_added']!=0:
        raise ValueError('Unsupported scientific promotion')
    return {'byte_integrity':'passed','source_inclusive_checks':'passed','timing_replay':'passed',
            'journal_and_shutdown':'passed','files_verified':count,'source_fields_checked':len(load(output/'source-checks.json')),
            'query_validation':check,'scientific_validation':'not_established'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--expected-sha256',required=True)
    args=parser.parse_args();print(json.dumps(verify(args.output,args.expected_sha256)))
