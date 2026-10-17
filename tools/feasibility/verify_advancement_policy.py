"""Verify frozen development policy, source bindings and deterministic application."""
import argparse
import json
from pathlib import Path
from tools.feasibility.program_outcomes import load,sha,verify_manifest
from tools.feasibility.apply_advancement_policy import derive,ROOT
from tools.feasibility.advancement_rules import validate_policy
from tools.feasibility.verify_phase3_linkage import verify as verify_linkage
from tools.feasibility.verify_program_feasibility import verify as verify_programs


def verify(output,anchor):
    output=Path(output).resolve();count=verify_manifest(output/'evidence-manifest.json',anchor)
    policy=load(output/'protocol.json');validate_policy(policy)
    fingerprint=sha(output/'protocol.json')
    if fingerprint!=load(output/'protocol-freeze.json')['protocol_sha256'] or fingerprint!=load(output/'application-reservation.json')['protocol_sha256']:
        raise ValueError('Policy changed between freezing and application')
    for filename in ['advancement_rules.py','apply_advancement_policy.py']:
        if sha(output/filename)!=sha(ROOT/'tools/feasibility'/filename):
            raise ValueError('Use the archived application code version')
    for index,parent in enumerate(policy['parents']):
        manifest=Path(parent['path']);verify_manifest(manifest,parent['sha256'])
        if index==0:verify_programs(manifest.parent,parent['sha256'])
        elif index==1:verify_linkage(manifest.parent,parent['sha256'])
    expected=derive(policy)
    for name,value in expected.items():
        if value!=load(output/(name+'.json')):raise ValueError('Application differs from replay: '+name)
    for row in load(output/'review-inputs.json'):
        p=row['proof'];path=Path(p['path'])
        if sha(path)!=p['sha256']:raise ValueError('Changed review input')
        value=load(path)
        for key in p['json_pointer'].strip('/').split('/'):
            value=value[int(key)] if isinstance(value,list) else value[key]
        if value!=row['value']:raise ValueError('Review pointer value mismatch')
    if load(output/'application-completed.json')['flow']!=expected['cohort-flow']:
        raise ValueError('Completion accounting differs')
    return {'byte_integrity':'passed','source_inclusive_replay':'passed','policy_binding':'passed',
        'cases_accounted':24,'files_verified':count,'qualified_primary_events':expected['cohort-flow']['qualified_unique_primary_events'],
        'scientific_validation':'not_established'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--expected-sha256',required=True)
    args=p.parse_args();print(json.dumps(verify(args.output,args.expected_sha256)))
