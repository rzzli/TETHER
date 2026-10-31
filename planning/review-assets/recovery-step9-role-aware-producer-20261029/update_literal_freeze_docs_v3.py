"""Update current status pointers only; retain historical assessments and proposals."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = 'Project Progress Reassessment 2026-10-29 - Producer Literal Freeze.md'
docs = ('README.md', 'TODO.md',
        'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
        'planning/Recovery Status and Next Gates 2026-10-26.md',
        'planning/Project Progress Reassessments.md',
        'planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md')
next_line = ('Next: complete the concrete codec plus genuine role-aware producer integration. '
             'Independent literals are frozen (e0d636af), peer-cleared (3e1ac225) and root-accepted (8f1020bd): '
             '40 bases, 225 byte negatives, 134 anchors, six passing fixture checks and 26 matching pins. '
             'Source authoring is underway under9e202d81; no subject has been imported/tested at this checkpoint. '
             'Full-roster, first-entry/FFI, physical/native, integrated-resource and scientific/human gates remain open. '
             'AsOf0.3.11/defaultv2 retains1,774 tests/327pins; $0 and unchanged application defaults.')
for name in docs:
    p = ROOT / name
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    a = [i for i, line in enumerate(lines) if line.startswith('Current checkpoint:')]
    b = [i for i, line in enumerate(lines) if line.startswith('Next:') and a and i == a[0] + 2]
    assert len(a) == len(b) == 1, name
    target = ('planning/' if '/' not in name else '') + NAME
    lines[a[0]] = (f'Current checkpoint: [independent producer literals](<{target}>) are accepted '
                   '(root8f1020bd, peer3e1ac225). OriginalV1 and its5/6 fixture failure remain preserved. '
                   'Concrete four-module source authoring and a separate genuine-producer test harness have started; '
                   'fixture acceptance establishes no codec behavior or live provenance.')
    lines[b[0]] = next_line
    text = '\n'.join(lines) + '\n'
    if name == 'README.md':
        old = 'See the [current full-project reassessment](<planning/Project Progress Reassessment 2026-10-29 - Producer Format Schema.md>)'
        assert text.count(old) == 1
        text = text.replace(old, f'See the [current full-project reassessment](<planning/{NAME}>)', 1)
    if name == 'TODO.md':
        duplicate = '- [ ] Implement and validate the concrete role-aware codec/owner/ports/controller against frozen format cases and genuine ownership/legacy/streaming controls. Source authoring started; no codec-only completion or decoded provenance substitute.\n'
        assert text.count(duplicate) == 1
        text = text.replace(duplicate, '', 1)
        old = '- [ ] Freeze independent literal corpus/test source, then implement and qualify the concrete codec and genuine role-aware producer integration (old48 identity plus new role/fault/full-profile controls).'
        assert text.count(old) == 1
        text = text.replace(old, '- [ ] Implement and qualify the concrete codec and genuine role-aware producer integration against frozen literals (old48 identity plus new role/fault/full-profile controls). Source authoring underway; no subject execution yet.', 1)
        text += f'- [ ] Reassess all R01-R16/HR1-HR4 after the independent literal freeze; retain {NAME} and current-document QA.\n'
    if name == 'planning/Project Progress Reassessments.md':
        text += f'\n| R09 independent producer literals accepted | [29 October UTC literal snapshot](<{NAME}>) | Root8f1020bd/peer3e1ac225;40 bases/225 negatives/134 anchors,6 fixture checks and26 pins pass. Concrete source authoring underway; no producer/runtime/scientific acceptance. |\n'
    p.write_text(text, encoding='utf-8', newline='\n')
p = ROOT / 'memory/MEMORY.md'
text = p.read_text(encoding='utf-8')
assert 'research-log-2026-10-29-producer-literal-freeze' not in text
lines = text.splitlines()
lines.insert(2, '- [[research-log-2026-10-29-producer-literal-freeze]] - Root8f1020bd/peer3e1ac225 accepts40bases/225negatives/134anchors;6fixture checks/26pins pass. Concrete4module source and independent harness underway; no subject run, live provenance or scientific completion.')
p.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
p = ROOT / 'memory/project-goals.md'
text = p.read_text(encoding='utf-8')
marker = '## Current recovery execution\n\n'
assert text.count(marker) == 1
note = (f'Current checkpoint: [independent producer literals](../planning/{NAME.replace(" ", "%20")}).\n'
        'Root8f1020bd/peer3e1ac225 accepts freezee0d636af,40bases/225negatives/134anchors;\n'
        '6fixture methods/26pins pass. First5/6 failure preserved. Concrete4modules\n'
        'and independent actual runner/legacy48adapter are authoring under9e202d81.\n'
        'No subject imports/tests at this checkpoint; coherent freeze and separate\n'
        'execution scope precede them. See [[research-log-2026-10-29-producer-literal-freeze]].\n\n')
text = text.replace(marker, marker + note, 1)
text = text.replace('Current source-only checkpoint: [producer format schema]', 'Prior source-only checkpoint: [producer format schema]', 1)
p.write_text(text, encoding='utf-8', newline='\n')
print('Updated eight current status documents; historical assessments/proposals preserved.')
