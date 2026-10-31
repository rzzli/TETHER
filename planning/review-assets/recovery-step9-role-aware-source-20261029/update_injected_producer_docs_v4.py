"""Advance current status pointers; preserve dated historical assessments."""
from pathlib import Path

H = Path(__file__).resolve().parent
ROOT = H.parents[2]
NAME = 'Project Progress Reassessment 2026-10-29 - Injected Producer.md'
DOCS = ('README.md', 'TODO.md',
        'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
        'planning/Recovery Status and Next Gates 2026-10-26.md',
        'planning/Project Progress Reassessments.md',
        'planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md')
for name in DOCS:
    p = ROOT / name
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    checkpoints = [i for i, s in enumerate(lines) if s.startswith('Current checkpoint:')]
    assert len(checkpoints) == 1, name
    i = checkpoints[0]
    assert lines[i + 2].startswith('Next:'), name
    target = ('planning/' if '/' not in name else '') + NAME
    lines[i] = (f'Current checkpoint: [injected producer](<{target}>) passes the small SOURCE/PURE gate '
                '(root096f5781, peerad941fe0). Exact codec interoperability, genuine48/48 legacy histories '
                'plus focused controls, and13/13 extension methods pass. Source4 preserves raw/error/identity '
                'facts and hashes2,097,378 fictional bytes with209B capture. This does not complete R09.')
    lines[i + 2] = ('Next: freeze independent216-input generated-stream references/helpers and qualify one original-clock '
                    'large producer control after allocation review. Actual source audit9d6f0240 clears preparation only; '
                    'heap/RSS/timing remain unqualified. Complete roster/entry/14APIphysical/new84/native/integrated '
                    'and scientific/human gates remain open. App0.3.11/defaultv2 retains1,774 tests/327pins; '
                    '$0, unchanged application defaults and untouched downloader/stopped monitor.')
    text = '\n'.join(lines) + '\n'
    if name == 'README.md':
        a = 'See the [current full-project reassessment](<planning/Project Progress Reassessment 2026-10-29 - Producer Literal Freeze.md>)'
        assert text.count(a) == 1
        text = text.replace(a, f'See the [current full-project reassessment](<planning/{NAME}>)', 1)
    if name == 'TODO.md':
        a = '- [ ] Implement and qualify the concrete codec and genuine role-aware producer integration against frozen literals (old48 identity plus new role/fault/full-profile controls). Source authoring underway; no subject execution yet.'
        assert text.count(a) == 1
        text = text.replace(a, '- [ ] Finish the full-profile producer qualification: independent216-file reference/preparation, one actual large generated stream and retained complete evidence. Small injected gate passes; real entry/roster/physical/native/science remain separate.', 1)
        text += ('- [x] Implement and validate the concrete small injected codec/owner/ports/controller: '
                 'root096f5781/peerad941fe0; codec4methods carried by exact byte identity, actual48/48+SAME8 '
                 'and13/13 indexed/new producer methods; small2,097,378B stream/209B capture. Preserve all first failures; '
                 'no production or science qualification.\n')
        text += f'- [ ] Reassess all R01-R16/HR1-HR4 after the injected producer small gate; retain {NAME} and current-document QA.\n'
    if name == 'planning/Project Progress Reassessments.md':
        text += (f'\n| R09 small injected producer accepted | [29 October UTC producer snapshot](<{NAME}>) | '
                 'Root096f5781/peerad941fe0; actual48/48+same8 and13/13 producer methods, exact codec carry. '
                 'Large control/real route/resources/science pending; failure chronology and actual allocation audit retained. |\n')
    p.write_text(text, encoding='utf-8', newline='\n')
p = ROOT / 'memory/MEMORY.md'
text = p.read_text(encoding='utf-8')
assert 'research-log-2026-10-29-injected-producer' not in text
lines = text.splitlines()
lines.insert(2, '- [[research-log-2026-10-29-injected-producer]] - Small source4 gate096f5781/ad941fe0 passes actual48/48+same8,13/13 extensions and pure codec carry;2,097,378B hash/209B capture. Audit9d6f permits large preparation only. Real route/resources/science/humans pending; all first failures preserved.')
p.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
p = ROOT / 'memory/project-goals.md'
text = p.read_text(encoding='utf-8')
marker = '## Current recovery execution\n\n'
assert text.count(marker) == 1
note = (f'Current checkpoint: [small injected producer](../planning/{NAME.replace(" ", "%20")}).\n'
        'Root096f5781/peerad941fe0 accepts source4a746: actualLegacy48/48+same8(9methods),\n'
        'extensions13/13(old6+new7), purecodec4methods carried by exactbytes. Smallstream\n'
        'hashes2,097,378B/captures209B with6reads/30fakecalls/4closes; no bulkbody.\n'
        'Actualallocationaudit9d6f0240 clears independent216-file fixture preparation\n'
        'only. Large9,017,363,601B control/entry/FFI/physical/roster/new84/resources/science\n'
        'remain open. All first source/oracle/harness failures retained; no oldnative\n'
        'experiment replay. See [[research-log-2026-10-29-injected-producer]].\n\n')
text = text.replace('Current checkpoint: [independent producer literals]', 'Prior checkpoint: [independent producer literals]', 1)
text = text.replace(marker, marker + note, 1)
p.write_text(text, encoding='utf-8', newline='\n')
print('Updated eight current status documents; historical proposals and checkpoints retained.')
