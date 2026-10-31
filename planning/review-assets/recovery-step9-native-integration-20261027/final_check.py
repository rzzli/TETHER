"""Final hash/link/JSON consistency checks; protected payloads are hashed only."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


acceptance=json.loads((HERE/'acceptance.json').read_bytes())
assert sha(HERE/'acceptance.json')=='8a77c2eaba83dece672330b72c518a8f16f1417c9a14498b54686ac990b7815b'
assert acceptance['status']=='accepted_native_adapter_controller_integration_engineering_only'
assert all(sha(ROOT/p['path'])==p['sha256'] for p in acceptance['evidence'])
code=json.loads((HERE/'code-validation.json').read_bytes())
assert all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
assert all(sha(ROOT/n)==h for n,h in code['protected_hashes'].items())  # Hash only.
assert sha(ROOT/acceptance['preserved_wheel']['path'])==acceptance['wheel']['sha256']
docs=[ROOT/p for p in ('README.md','CHANGELOG.md','TODO.md','docs/NATIVE_INTERPRETATION.md',
    'docs/INTERPRETATION_INTERFACE.md','docs/AUTHORITY_FOUR_ARM_COMPARISON.md','docs/STUDY_RUNTIME.md',
    'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
    'planning/Recovery Status and Next Gates 2026-10-26.md','memory/MEMORY.md','memory/project-goals.md',
    'memory/research-log-2026-10-28-r09-native-integration.md')]
docs+=list(HERE.glob('*.md'))
missing=[];links=0
for path in docs:
    for target in re.findall(r'\[[^\]]*\]\(([^\n]+?)\)',path.read_text(encoding='utf-8')):
        target=unquote(target.strip().strip('<>')).split('#')[0]
        if not target or re.match(r'^[a-z]+://|^mailto:',target):continue
        destination=Path(target) if Path(target).is_absolute() else path.parent/target
        links+=1
        if not destination.exists():missing.append(dict(document=str(path),target=target))
assert not missing,missing
json_paths=list(HERE.glob('*.json'))
for path in json_paths:json.loads(path.read_bytes())
report=dict(schema_version=1,status='passed',acceptance_sha256=sha(HERE/'acceptance.json'),
    source_pins_rechecked=len(code['source_pins']),evidence_hashes_rechecked=len(acceptance['evidence']),
    protected_hashes_only=len(code['protected_hashes']),documents_checked=len(docs),local_links_checked=links,
    missing_links=missing,json_reports_parsed=len(json_paths),actual_model_calls=0,provider_spend_usd=0,
    scientific_validation='not_established',human_reviews='pending',native_grammar='unverified')
with (HERE/'FINAL-CHECK.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
