"""Check the accepted correction and living-document consistency, without rerunning tests."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


assert sha(HERE/'acceptance.json')=='27f33a36fd01d48b79e1492ad6b4b185a60e4bd662bb1ee0d955e5a284079cdc'
accepted=json.loads((HERE/'acceptance.json').read_bytes())
assert all(sha(ROOT/r['path'])==r['sha256'] for r in accepted['evidence'])
code=json.loads((HERE/'code-validation.json').read_bytes())
assert all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
assert all(sha(ROOT/n)==h for n,h in code['protected_hashes'].items())  # Hash only.
assert sha(ROOT/accepted['preserved_wheel']['path'])==accepted['wheel']['sha256']
qa=json.loads((HERE/'PROGRESS-REASSESSMENT-DOC-QA.json').read_bytes())
assert sha(ROOT/qa['document'])==qa['document_sha256']
assert qa['accepted_version']=='0.3.10' and len(qa['numbered_steps_present'])==16 and len(qa['human_gates_present'])==4
docs=[ROOT/p for p in ('README.md','CHANGELOG.md','TODO.md','docs/NATIVE_INTERPRETATION.md',
    'docs/INTERPRETATION_INTERFACE.md','docs/AUTHORITY_FOUR_ARM_COMPARISON.md','docs/STUDY_RUNTIME.md',
    'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
    'planning/Recovery Status and Next Gates 2026-10-26.md','planning/Project Progress Reassessments.md',
    'planning/Project Progress Reassessment 2026-10-28 - R09 Integration.md',
    'planning/Project Progress Reassessment 2026-10-28 - R09 Duration.md',
    'memory/MEMORY.md','memory/project-goals.md','memory/research-log-2026-10-28-r09-duration.md')]
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
    source_pins_rechecked=len(code['source_pins']),evidence_hashes_rechecked=len(accepted['evidence']),
    protected_hashes_only=len(code['protected_hashes']),documents_checked=len(docs),local_links_checked=links,
    missing_links=missing,json_reports_parsed=len(json_paths),full_tests=accepted['full_tests'],
    major_completion_reassessment=dict(path=qa['document'],sha256=qa['document_sha256']),
    actual_native_case_feasibility='not_established',observed_time_margin_seconds=accepted['observed_time_margin_seconds'],
    human_reviews='pending',native_grammar='not_tested',model_calls=0,provider_spend_usd=0)
with (HERE/'FINAL-CHECK.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
