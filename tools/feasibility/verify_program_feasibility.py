"""Source-inclusive replay of the evaluator-only program feasibility package."""
import argparse
import hashlib
import json
from pathlib import Path

from tools.feasibility.program_outcomes import load, sha, verify_manifest, validate_bundle
from tools.feasibility.build_program_feasibility import ROOT, derive


def verify(output, expected):
    files = verify_manifest(output/'evidence-manifest.json', expected)
    manifest = load(output/'evidence-manifest.json')
    for parent in manifest['parents']:
        verify_manifest(ROOT/parent['path']/'evidence-manifest.json', parent['sha256'])
    for name in ['build_program_feasibility.py', 'program_outcomes.py']:
        if sha(output/name) != sha(ROOT/'tools/feasibility'/name):
            raise ValueError('Replay code changed; use the archived code version')
    previous = None
    stages = []
    for line in (output/'build-journal.jsonl').read_text(encoding='utf-8').splitlines():
        event = json.loads(line)
        digest = event.pop('sha256')
        if event['previous'] != previous or digest != hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest():
            raise ValueError('Journal chain differs')
        previous = digest
        stages.append(event['stage'])
    if stages != ['started', 'parents_verified', 'completed']:
        raise ValueError('Build did not complete exactly once')
    if load(output/'build-reservation.json')['protocol_sha256'] != sha(output/'protocol.json'):
        raise ValueError('Protocol changed after reservation')
    selected, replay = derive()
    retained = {name: load(output/(name+'.json')) for name in replay}
    if retained != replay:
        raise ValueError('Source-derived tables differ from deterministic replay')
    checked = validate_bundle(retained, selected)
    flow = load(output/'cohort-flow.json')
    terminal = json.loads((output/'build-journal.jsonl').read_text(encoding='utf-8').splitlines()[-1])
    if terminal['detail']['flow'] != flow:
        raise ValueError('Flow does not match completed journal')
    return {'byte_integrity':'passed', 'source_inclusive_replay':'passed', 'journal':'passed',
            'files_verified':files, 'checks':checked, 'scientific_validation':'not_established'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.output, args.expected_sha256)))
