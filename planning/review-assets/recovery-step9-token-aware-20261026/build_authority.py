"""Anchor the unchanged exposed R07 development inputs; never reads answers."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
RAW = Path(r'E:\projects_data\drug_target_agents_data')
PLAN = ROOT / 'runs/question-development-20261026T023832Z/run-plan.json'
EXPECTED_PLAN = '9a8645ab86563e0d37434c4d2ec32ab6539300689db68ede02cfad8e253108b9'
EXPECTED_REQUEST = '14b735ef940bde56c04ea964cf145f3f7d1e343b2fe1e35de157cc8a5af2d61a'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked(proof):
    path = Path(proof['path'])
    assert sha(path) == proof['sha256'] and path.stat().st_size == proof['bytes']
    return path


assert sha(PLAN) == EXPECTED_PLAN
plan = json.loads(PLAN.read_bytes())
task = next(t for t in plan['tasks'] if t['task_id'] == 'mr-discovery-replication')
assert task['family'] == 'genetic-study-report.v1' and task['request_sha256'] == EXPECTED_REQUEST
case, snapshot, catalog = (checked(plan[name]) for name in ('case', 'snapshot', 'catalog'))
identifiers = snapshot.parent / 'identifier-validation.json'
snap = json.loads(snapshot.read_bytes())
files = {}


def add(key, path, expected=None):
    path = path.absolute()
    root_id, root = ('raw', RAW) if path.is_relative_to(RAW) else ('project', ROOT)
    assert path.is_relative_to(root)
    assert not any(v.lower() in {'benchmark', 'gold_evidence', 'adjudication', 'completed-responses'} for v in path.parts)
    actual = sha(path)
    assert expected is None or expected == actual
    files[key] = dict(root_id=root_id, relative_path=path.relative_to(root).as_posix(),
                      sha256=actual, bytes=path.stat().st_size)


for name, path in (('case', case), ('snapshot', snapshot), ('catalog', catalog), ('identifiers', identifiers)):
    add(name, path)
for artifact in snap['artifacts']:
    add('artifact-' + artifact['artifact_id'], snapshot.parent / artifact['path'], artifact['sha256'])
for node in snap['sources']:
    base = snapshot.parent if node['computed_at'] is not None else Path(snap['raw_root'])
    add('source-' + node['source_id'], base / node['path'], node['sha256'])
    if node['receipt_path']:
        add('receipt-' + node['source_id'], Path(snap['raw_root']) / node['receipt_path'], node['receipt_sha256'])
authority = dict(schema_version=1, profile='contemporary-t6-opentargets25.09-normalization2.2',
                 recipe='asof.opentargets.normalize:2.2', files=files,
                 inputs={name: name for name in ('case', 'snapshot', 'catalog', 'identifiers')},
                 selection=dict(family=task['family'], max_claims=2, max_observations=256,
                                observation_ids=task['observation_ids']),
                 expected_request_sha256=EXPECTED_REQUEST)
target = HERE / 'SOURCE-AUTHORITY-v1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(authority, stream, indent=2)
record = dict(schema_version=1, role='planning_only', original_plan_sha256=EXPECTED_PLAN,
              authority_sha256=sha(target), files=len(files), bytes=sum(v['bytes'] for v in files.values()),
              original_request_expected=EXPECTED_REQUEST,
              status='authority_pins_prepared_not_source_admission',
              source_validation='pending_whole_row_replay', generation_calls=0, protected_contents_read=False)
with (HERE / 'SOURCE-AUTHORITY-PREPARATION.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
print(json.dumps(record))
