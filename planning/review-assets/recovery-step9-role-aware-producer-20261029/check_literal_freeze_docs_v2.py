"""Validate current fixture checkpoint documents; no subject imports or original targets."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = 'Project Progress Reassessment 2026-10-29 - Producer Literal Freeze.md'
ASSESSMENT = 'planning/' + NAME
DOCS = ('README.md', 'TODO.md', ASSESSMENT,
        'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
        'planning/Recovery Status and Next Gates 2026-10-26.md',
        'planning/Project Progress Reassessments.md',
        'planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md',
        'memory/MEMORY.md', 'memory/project-goals.md',
        'memory/research-log-2026-10-29-producer-literal-freeze.md')
texts = {name: (ROOT / name).read_bytes().decode('utf-8', 'strict') for name in DOCS}
text = texts[ASSESSMENT]
rows = re.findall(r'^\| (R\d\d|HR\d) \|', text, re.M)
assert rows == [f'R{i:02d}' for i in range(1, 17)] + [f'HR{i}' for i in range(1, 5)]
assert re.findall(r'^([1-5])\. ', text, re.M) == list('12345')
links = []
for wrapped, bare in re.findall(r'\]\((?:<([^>]+)>|([^\s)]+))\)', text):
    target = wrapped or bare
    if target.startswith(('https://', 'http://', '#')):
        continue
    p = ((ROOT / ASSESSMENT).parent / unquote(target.split('#', 1)[0])).resolve()
    assert p.is_relative_to(ROOT) and p.is_file(), target
    links.append(str(p.relative_to(ROOT)))
for name in DOCS[:7]:
    if name != ASSESSMENT:
        assert NAME in texts[name], name
for name in DOCS:
    assert '8f1020bd' in texts[name] and '3e1ac225' in texts[name], name
for token in ('40 base values', '225 byte-negative expansions', '134 anchors',
              '320 section frames', '26 evidence pins', '9,017,363,601', '209 bytes',
              '10,095', '127,809,034', '19079', '256 MiB', 'INCOMPLETE_TIMEOUT',
              '1,774 passing full tests', '327 source/resource pins', '65 missing inputs',
              '0/12', 'probabilities null', 'human reviews pending', 'The project remains unfinished'):
    assert token in text, token
todo = texts['TODO.md']
assert '- [x] Freeze independent role-aware format literals/tests before source:' in todo
assert '- [ ] Implement and qualify the concrete codec and genuine role-aware producer integration' in todo
assert '[ ] R09 Implement' in todo and all(f'[ ] HR{i}' in todo for i in range(1, 5))
pending = f'- [ ] Reassess all R01-R16/HR1-HR4 after the independent literal freeze; retain {NAME} and current-document QA.'
assert todo.count(pending) == 1
pins = {
    'ROLE-AWARE-FORMAT-LITERAL-ACCEPTANCE-v2.json': '8f1020bd0b5a1c97c26080bbaaa263395cd3cfa354c6fa64afb6929eae9f090d',
    'ROLE-AWARE-FORMAT-LITERAL-FREEZE-v2.json': 'e0d636af4501544f3fd8aba77b061633a5052be81f06f8fa0ab8fded41cb4e53',
    'ROLE-AWARE-FORMAT-LITERAL-INDEPENDENT-REVIEW-v2.json': '3e1ac2257e59aa415d2494cac7d6aa8bc6b74179234629d2c0ba0141aca48549',
    'ROLE-AWARE-PRODUCER-SOURCE-SCOPE-v1.json': '9e202d81d5d2f18bf2eb7b3552c86782ceda2b0f2a6cf56a711f70ee4f1053e5',
}
for name, digest in pins.items():
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
acceptance = json.loads((HERE / 'ROLE-AWARE-FORMAT-LITERAL-ACCEPTANCE-v2.json').read_bytes())
assert acceptance['root_verification']['evidence_pins_matched'] == 26
assert acceptance['subject_imports'] == acceptance['subject_runs'] == 0
assert not any(acceptance['qualification'].values())
(ROOT / 'TODO.md').write_text(todo.replace(pending, pending.replace('- [ ]', '- [x]', 1), 1), encoding='utf-8', newline='\n')
documents = {}
for name in DOCS:
    raw = (ROOT / name).read_bytes()
    documents[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
report = dict(schema_version=1, status='PASS', recorded_at_utc=datetime.now(timezone.utc).isoformat(),
              scope='Current UTF8 documents,20status rows,five next gates,local links and exact fixture/source-scope boundaries only.',
              documents=documents, status_rows=rows, ordered_next_gates=5, assessment_local_links=links,
              evidence_pins=pins, retained_application_tests=1774, retained_application_source_pins=327,
              application_tests_rerun=False, subject_imports=0, subject_runs=0, original_target_or_native_operations=0,
              checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
output = HERE / 'ROLE-AWARE-LITERAL-CURRENT-DOCS-QA-v2.json'
with output.open('x', encoding='utf-8', newline='\n') as out:
    json.dump(report, out, sort_keys=True, indent=2)
    out.write('\n')
print(json.dumps(dict(status='PASS', documents=len(DOCS), rows=len(rows), links=len(links), sha256=hashlib.sha256(output.read_bytes()).hexdigest())))
