"""Independent current-document QA; only explicitly authorized QA-status edits."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
REPORT = BASE / 'SOURCE5-CURRENT-DOCS-QA-v1.json'
QA_NAME = REPORT.name
ASSESSMENT = 'planning/Project Progress Reassessment 2026-10-31 - Component Guards.md'
LOG = 'memory/research-log-2026-10-31-component-guards.md'
INDEX = 'planning/Project Progress Reassessments.md'
CHECKS = []


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def check(name, passed, detail=None):
    CHECKS.append(dict(name=name, passed=bool(passed), detail=detail))


def verify(item):
    path = Path(item['path'])
    if not path.is_absolute():
        path = ROOT / path
    actual = pin(path)
    return actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256']


author_path = BASE / 'SOURCE5-CURRENT-DOCS-AUTHORING-v2.json'
author = json.loads(author_path.read_bytes())
prior_author = json.loads((BASE / 'SOURCE5-CURRENT-DOCS-AUTHORING-v1.json').read_bytes())
check('exact_author_v2', pin(author_path)['sha256'] == '879f2f8f718b23778742f43b690756c2a881207bc4032685df63b1b7646099aa')
docs = list(author['documents_final'])
check('exact_ten_current_docs', len(docs) == len(set(docs)) == 10 and docs[:8] == [
    'README.md', 'TODO.md', 'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
    'planning/Recovery Status and Next Gates 2026-10-26.md', INDEX,
    'planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md',
    'memory/MEMORY.md', 'memory/project-goals.md'] and docs[8:] == [ASSESSMENT, LOG])
before = {name: (ROOT / name).read_bytes() for name in docs}
texts = {name: raw.decode('utf-8') for name, raw in before.items()}
for name, item in author['documents_final'].items():
    check('author_pin/' + name, verify(item))
    check('utf8/' + name, '\ufffd' not in texts[name] and not texts[name].startswith('\ufeff'))
hold_path = BASE / 'SOURCE5-CURRENT-DOCS-STATIC-HOLD-v1.json'
hold = json.loads(hold_path.read_bytes())
check('preserved_first_HOLD', pin(hold_path)['sha256'] == 'ea587291d6efff65d21f860380483eea1564fd5477e5dc653a40f33b375a63fc'
      and hold['status'] == 'HOLD_CURRENT_SOURCE5_DOCS_STALE_CURRENT_INDEX'
      and hold['authorized_QA_status_edits_applied'] is False)
current_pointer = next(line for line in texts['memory/MEMORY.md'].splitlines() if line.startswith('- [[project-goals]]'))
check('stale_current_index_fixed', '43' in current_pointer and 'four' in current_pointer
      and 'static' in current_pointer.lower() and 'unexecuted' not in current_pointer
      and 'authoring-only' not in current_pointer and 'two kind failures' not in current_pointer)

# Reconstruct all eight pre-edit tracked documents from narrow permitted changes.
baseline = {}
for name in docs[:8]:
    result = subprocess.run(['git', 'show', 'eecc087:' + name], cwd=ROOT, capture_output=True, check=True)
    raw = result.stdout
    expected = prior_author['documents_before'][name]
    check('baseline/' + name, len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'])
    baseline[name] = raw.decode('utf-8')
for name in docs[:8]:
    current = texts[name]
    old = baseline[name]
    if name in docs[:6]:
        new_line = next(line for line in current.splitlines() if line.startswith('Current checkpoint, 31 October UTC:'))
        old_line = next(line for line in old.splitlines() if line.startswith('Current checkpoint, 30 October UTC:'))
        current = current.replace(new_line, old_line, 1)
        new_line = next(line for line in current.splitlines() if line.startswith('Next: close the four native-bank design joins'))
        old_line = next(line for line in old.splitlines() if line.startswith('Next: correct only the two remaining native25'))
        current = current.replace(new_line, old_line, 1)
    if name == 'TODO.md':
        new_line = next(line for line in current.splitlines() if line.startswith('- [ ] Implement and validate the complete entry/operations/file-view route.'))
        old_line = next(line for line in old.splitlines() if line.startswith('- [ ] Implement and validate the complete entry/operations/file-view route.'))
        current = current.replace(new_line, old_line, 1)
        suffix = '\n' + '\n'.join(current.splitlines()[-2:]) + '\n'
        check('two_exact_new_TODO_entries', current.endswith(suffix)
              and suffix.startswith('\n- [x] Correct and independently validate only Source5 API/axis-kind guards:')
              and '\n- [ ] Reassess all R01–R16/HR1–HR4 after Source5 guards ' in suffix)
        current = current[:-len(suffix)]
    elif name == INDEX:
        suffix = '\n' + current.splitlines()[-1] + '\n'
        check('one_new_assessment_index_row', current.endswith(suffix) and suffix.startswith('\n| R09 Source5 API/axis-kind guard accepted |'))
        current = current[:-len(suffix)]
    elif name == 'planning/Recovery Status and Next Gates 2026-10-26.md':
        current = current.replace('Updated 31 October 2026 UTC.', 'Updated 30 October 2026 UTC.', 1)
    elif name == 'planning/Project Recovery and Evaluation Plan 2026-10-26.md':
        current = current.replace('**Status updated:** 31 October UTC / 30 October Los Angeles.',
                                  '**Status updated:** 30 October UTC / 29 October Los Angeles.', 1)
    elif name == 'memory/MEMORY.md':
        entry = next(line for line in current.splitlines() if line.startswith('- [[research-log-2026-10-31-component-guards]]'))
        current = current.replace(entry + '\n\n', '', 1)
        old_pointer = next(line for line in old.splitlines() if line.startswith('- [[project-goals]]'))
        current = current.replace(current_pointer, old_pointer, 1)
    elif name == 'memory/project-goals.md':
        start = 'Current checkpoint: [[Project Progress Reassessment 2026-10-31 - Component Guards]].'
        end = 'Prior checkpoint: [[Project Progress Reassessment 2026-10-30 - C Return Capture]].'
        left = current.index(start)
        right = current.index(end, left) + len(end)
        current = current[:left] + 'Current checkpoint: [[Project Progress Reassessment 2026-10-30 - C Return Capture]].' + current[right:]
        current = current.replace('updated: 2026-10-31', 'updated: 2026-10-30', 1)
    check('exact_limited_authoring_diff/' + name, current == old)
for name in (ASSESSMENT, LOG):
    item = prior_author['documents_before'][name]
    check('new_doc_unchanged_since_authoring/' + name,
          len(before[name]) == item['bytes'] and hashlib.sha256(before[name]).hexdigest() == item['sha256'])

accept_path = BASE / 'SOURCE5-ROOT-ACCEPTANCE-v1.json'
accept = json.loads(accept_path.read_bytes())
check('exact_Root_acceptance', pin(accept_path)['sha256'] == 'ec290b979a08ed76558b52b7239d5f844cd9a580e97a068adc8d1288455e01dc'
      and accept['status'] == 'ACCEPTED_SOURCE5_API_AXIS_KIND_GUARD_SOURCE_SYNTHETIC_ONLY')
for name, item in accept['evidence'].items():
    check('acceptance_evidence/' + name, verify(item))
check('acceptance_counts', accept['counts'] == dict(COMPONENT_PASS=43, DEFERRED_NOT_EXECUTED=4, STATIC_DECLARATION_ONLY=1))
check('acceptance_metrics', accept['independent_retained_data_checks'] == 1493 and accept['worlds'] == 20
      and accept['data_objects'] == 26 and accept['snapshots'] == 30
      and accept['artifacts'] == dict(files=188, bytes=578134)
      and accept['retained_execution'] == dict(files=190, bytes=819271)
      and accept['elapsed_seconds'] == 0.25 and accept['call_gate'] == dict(attempts=493, returns=451, checks=1582))
check('acceptance_limits', not any(accept['qualification'].values()) and accept['provider_spend_usd'] == 0
      and accept['downloader_or_monitor_changed'] is False)
for name in docs[:6]:
    current = next(line for line in texts[name].splitlines() if line.startswith('Current checkpoint, 31 October UTC:'))
    check('current_scope/' + name, all(term in current for term in ('43', 'four DEFERRED', 'one STATIC',
          '21 source-runtime / 22 data', 'ec290b97', '69d14742', '1,493', '188', '0.250',
          'Full native25', 'remain open')))
for name in ('memory/MEMORY.md', 'memory/project-goals.md', LOG):
    current = texts[name].split('### Prior C-return checkpoint', 1)[0]
    check('memory_current_scope/' + name, all(term in current for term in ('43', 'DEFERRED', 'STATIC', 'ec290b97', '69d14742'))
          and ('remain open' in current or 'stay open' in current or 'stay open' in texts[name]))
assessment = texts[ASSESSMENT]
expected_rows = {
    'R01': ('Accepted', 'scope'), 'R02': ('Accepted', 'checkpoint'),
    'R03': ('Accepted', 'restoration remains separate'), 'R04': ('Accepted', 'correctness'),
    'R05': ('Accepted', 'scientific sufficiency unresolved'), 'R06': ('Accepted', 'slice'),
    'R07': ('closed negative', 'human scientific assessment pending'),
    'R08': ('Partial', 'no scientifically qualified fresh case'),
    'R09': ('43', 'four deferrals', 'one static', 'remain open'),
    'R10': ('human', 'pending'), 'R11': ('power', 'preregistration', 'pending'),
    'R12': ('Locked', 'pending'), 'R13': ('conditional', 'unqualified'),
    'R14': ('conditional', 'unqualified'), 'R15': ('conditional', 'pending'),
    'R16': ('T2', 'H6', 'pending'), 'HR1': ('Human', 'pending'),
    'HR2': ('Two independent', 'pending'), 'HR3': ('source-only', 'pending'),
    'HR4': ('independent adjudication', 'pending')}
rows = dict(re.findall(r'^\|\s*((?:R\d{2}|HR[1-4]))\s*\|\s*(.*?)\s*\|\s*$', assessment, re.M))
check('exact20_R_HR_status_rows', set(rows) == set(expected_rows) and len(rows) == 20)
for name, terms in expected_rows.items():
    check('status/' + name, all(term in rows.get(name, '') for term in terms))
stages = re.findall(r'^([1-5])\. \*\*(.*?)\*\*', assessment, re.M)
wanted = ['Close the bridge contract and independent test expectations.',
          'Implement and qualify the compiled fake bridge, then the tiny original7 route.',
          'Close the actual new84 roster and joint physical budgets.',
          'Qualify positive native authority and the distinct prospective protocol.',
          'Return to scientific readiness and locked evaluation.']
check('five_ordered_next_stages', stages == [(str(i + 1), name) for i, name in enumerate(wanted)])
for name, terms in {
    'metrics': ('43 PASS = 21 SOURCE_RUNTIME + 22 DATA', '0.250', '20 / 26 / 30', '188 files / 578,134',
                '190 files / 819,271', '493 / 451 / 1,582', '1,493 / 1,493'),
    'bytes_lineage': ('112 binary', '600 nonmalformed axes', '180 snapshot rows / 46,080',
                      '36 query witnesses / 98,616', '313-byte', '244 top-level'),
    'history': ('31-PASS/12-FAIL', '38-PASS/5-FAIL', '41-PASS/2-FAIL', 'Source4', 'E08/122', 'C79', 'not rerun'),
    'science': ('65 missing inputs', '36 unqualified endpoint labels', '17/32', '0/12',
                'Features remain empty', 'probabilities null', 'Human reviews are still pending'),
    'application': ('327', '0.3.11/default v2', '1,774-test', 'No application tests were rerun', 'no default application integration'),
    'resources': ('19,079', '13,482', '5,597', '16,384', '40,139,776', 'owner300/child120/work117'),
    'four_joins': ('Canonical input handle', 'Buffer generation', 'Native observation', 'Mutation surface'),
    'limits': ('do not test a C extension', 'physical producer ACK/durability', 'not a new compiled test',
               'FAILED', 'INCOMPLETE_TIMEOUT', 'no restart requirement', 'downloader', 'stopped periodic monitor'),
}.items():
    check('assessment/' + name, all(term.lower() in assessment.lower() for term in terms))
commit_lines = subprocess.run(['git', 'show', '-s', '--format=%H%n%cI%n%s', '42c6950'], cwd=ROOT,
                              capture_output=True, check=True, text=True).stdout.splitlines()
check('first_commit_timestamp_typo_accurate', commit_lines[1] == '2026-10-30T22:12:06-07:00'
      and '05:22Z' in commit_lines[2] and '05:12:06 UTC' in assessment and 'rather than rewriting existing history' in assessment)
for commit, actual in [('575d441', '2026-10-30T22:13:38-07:00'), ('eecc087', '2026-10-30T22:14:57-07:00')]:
    value = subprocess.run(['git', 'show', '-s', '--format=%cI', commit], cwd=ROOT,
                           capture_output=True, check=True, text=True).stdout.strip()
    check('commit_chronology/' + commit, value == actual)

# Form only the seven explicitly authorized closeout edits; do not apply on HOLD.
edits = []
def replace_one(name, old, new):
    check('closeout_unique/' + name + '/' + str(len(edits)), texts[name].count(old) == 1)
    if texts[name].count(old) == 1:
        texts[name] = texts[name].replace(old, new, 1)
        edits.append(dict(path=name, old=old, new=new))

replace_one(ASSESSMENT, 'status: accepted-source-component-documentation-qa-pending',
            'status: accepted-source-component-documentation-qa-passed')
old = ('The current Source5 assessment, TODO, navigation and memory updates require a separate documentation QA before the reassessment checkbox is completed. '
       'That QA will check current claims, all twenty status rows, the five ordered stages, local links and final document hashes. '
       'It does not rerun the suite or complete the broader project.')
new = ('The current Source5 assessment, TODO, navigation and memory updates pass separate documentation QA in `' + QA_NAME + '`. '
       'That QA checks current claims, all twenty status rows, the five ordered stages, local links and final document hashes. '
       'Only this reassessment checkbox is completed; it does not rerun the suite or complete the broader project.')
replace_one(ASSESSMENT, old, new)
todo_line = next(line for line in texts['TODO.md'].splitlines() if line.startswith('- [ ] Reassess all R01–R16/HR1–HR4 after Source5 guards'))
replace_one('TODO.md', todo_line, todo_line.replace('- [ ]', '- [x]', 1).replace('documentation QA pending.', 'independent documentation QA PASS: ' + QA_NAME + '.'))
for name in ('memory/MEMORY.md', 'memory/project-goals.md'):
    replace_one(name, 'Current documentation QA pending.', 'Independent current documentation QA PASS: `' + QA_NAME + '`.')
replace_one(LOG, 'Current Source5 documentation QA is pending.', 'Independent current Source5 documentation QA PASS: `' + QA_NAME + '`.')
index_line = next(line for line in texts[INDEX].splitlines() if line.startswith('| R09 Source5 API/axis-kind guard accepted |'))
replace_one(INDEX, index_line, index_line.replace('Current documentation QA pending.', 'Independent current documentation QA PASS: `' + QA_NAME + '`.'))
check('seven_authorized_closeout_edits', len(edits) == 7)
for name in docs:
    reversed_text = texts[name]
    for edit in reversed(edits):
        if edit['path'] == name:
            reversed_text = reversed_text.replace(edit['new'], edit['old'], 1)
    check('reverse_QA_only_diff/' + name, reversed_text.encode('utf-8') == before[name])

# Existence only: never open linked originals, outcomes or model payloads.
listed = subprocess.run(['rg', '--files', 'memory', 'planning', 'docs', '-g', '*.md'], cwd=ROOT,
                        capture_output=True, check=True, text=True).stdout.splitlines()
note_index = {}
for name in listed + ['README.md', 'TODO.md']:
    path = (ROOT / name).resolve()
    note_index.setdefault(path.stem.lower(), []).append(path)
links = []
broken = []
outside = []
for name, text in texts.items():
    values = [(value, False) for value in re.findall(r'(?<!!)\[[^\]\n]+\]\((<[^>]+>|[^)\n]+)\)', text)]
    values += [(value, True) for value in re.findall(r'\[\[([^\]\n]+)\]\]', text)]
    for value, wiki in values:
        target = unquote(value.strip().strip('<>'))
        if not wiki and re.match(r'^(?:https?|mailto|app|plugin|codex):', target, re.I):
            continue
        target = target.split('|', 1)[0].split('#', 1)[0]
        if not target:
            candidates = [ROOT / name]
        else:
            if wiki and not target.lower().endswith('.md'):
                target += '.md'
            path = Path(target)
            candidates = [path.resolve()] if path.is_absolute() else [((ROOT / name).parent / path).resolve(), (ROOT / path).resolve()]
            if wiki:
                candidates += [(ROOT / 'memory' / path).resolve(), (ROOT / 'planning' / path).resolve()]
                matches = note_index.get(Path(target).stem.lower(), [])
                if len(matches) == 1:
                    candidates += matches
        resolved = None
        for candidate in candidates:
            if not candidate.is_relative_to(ROOT):
                outside.append(dict(document=name, target=target))
                continue
            if candidate.exists():
                resolved = candidate
                break
        row = dict(document=name, target=target, kind='wiki' if wiki else 'markdown',
                   resolved=None if resolved is None else resolved.relative_to(ROOT).as_posix())
        links.append(row)
        if resolved is None:
            broken.append(row)
check('all_local_links_exist', not broken and not outside, dict(broken=broken, outside=outside))
check('no_source_edited_since_acceptance', all(verify(item) for item in accept['evidence'].values()))
passed = all(item['passed'] for item in CHECKS)
if passed:
    for name, raw in before.items():
        if (ROOT / name).read_bytes() != raw:
            raise RuntimeError('Concurrent current-document drift: ' + name)
    for name in {edit['path'] for edit in edits}:
        (ROOT / name).write_bytes(texts[name].encode('utf-8'))
    for name in docs:
        if (ROOT / name).read_bytes() != texts[name].encode('utf-8'):
            raise RuntimeError('Post-edit current-document mismatch: ' + name)
result = dict(schema_version=1, status='PASS_TEN_CURRENT_DOCS_SOURCE5_COMPONENT_GUARDS' if passed else 'HOLD_CURRENT_SOURCE5_DOC_CHECKS',
              at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), checker=pin(__file__),
              evidence=dict(authoring=pin(author_path), first_HOLD=pin(hold_path), Root_acceptance=pin(accept_path)),
              documents_before={name: dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()) for name, raw in before.items()},
              documents_final={name: pin(ROOT / name) for name in docs},
              counts=dict(documents=len(docs), checks=len(CHECKS), passed=sum(c['passed'] for c in CHECKS),
                          failed=sum(not c['passed'] for c in CHECKS), status_rows=len(rows), ordered_next_stages=len(stages),
                          local_links=len(links), markdown_links=sum(l['kind'] == 'markdown' for l in links),
                          wikilinks=sum(l['kind'] == 'wiki' for l in links)),
              checks=CHECKS, status_rows=rows, next_stages=stages, links=links, broken_links=broken,
              authorized_edits=edits if passed else [],
              edit_limits='Only new Source5 reassessment checkbox, current QA phrases/frontmatter/new Source5 index and memory entries; no other TODO state, old dated document, source, runtime or original-target operation.',
              qualification='Documentation-only. Source5 guard/43 source-synthetic controls accepted; native25 four deferrals and one static row, actual bank/bridge/Win32/leases/physical/resources/model/science/humans remain open.',
              activity=dict(subject_imports=0, subject_runs=0, native_dispatches=0, compiler_calls=0,
                            application_tests=0, original_payload_reads=0))
with REPORT.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], report=pin(REPORT), counts=result['counts'],
                      failures=[c for c in CHECKS if not c['passed']]), indent=2))
