"""Negative current-package admission probe; no original data or archived code."""
import json
import os
from pathlib import Path
import sys
import time
from asof.serde import ContractError, fingerprint
from asof.study.retrieval_preparation import qualify_universe

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
old = json.loads((HERE.parent/'recovery-step9-token-aware-20261026/REAL-PREPARATION.json').read_bytes())
parent = Path(old['output'])/'source'
request = json.loads((parent/'request.json').read_bytes())
rows = request['source_request']['evidence']
authority = dict(schema_version=1, kind='real_source_preparation',
    parent=dict(root_id='project', relative_path=parent.relative_to(ROOT).as_posix()),
    parent_receipt_sha256=old['source_receipt_sha256'], source_authority_sha256=old['source_authority_sha256'],
    candidate_ids=sorted(r['observation_id'] for r in rows),
    grounded_fingerprints={r['observation_id']:r['admitted_sha256'] for r in rows},
    category=rows[0]['scientific_record']['category'], request_sha256=old['request_sha256'])
attempts = dict(original_data=[], dispatch=[])


def guard(event, args):
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if path.startswith(os.path.normcase('E:\\')):
            attempts['original_data'].append(path)
            raise PermissionError('Original data unavailable to negative version probe')
    if event in ('subprocess.Popen','socket.connect'):
        attempts['dispatch'].append(event)
        raise PermissionError('No frozen-verifier fallback or dispatch permitted')


sys.addaudithook(guard)
try:
    qualify_universe(authority, fingerprint(authority),
        roots={'project':ROOT,'raw':Path(r'E:\projects_data\drug_target_agents_data')},
        deadline=time.monotonic()+30)
except ContractError as error:
    assert str(error) == 'Package proof mismatch', str(error)
    assert not any(attempts.values())
    result = dict(schema_version=1, status='old_parent_rejected_before_original_source_access',
                  old_parent_version='0.3.4', current_version='0.3.5',
                  error_class=type(error).__name__, reason=str(error), guards=attempts,
                  negative_probe_only=True, real_universe_expansion=False, model_calls=0)
    with (HERE/'OLD-PARENT-REJECTION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
else:
    raise AssertionError('Old package source receipt was incorrectly admitted')
