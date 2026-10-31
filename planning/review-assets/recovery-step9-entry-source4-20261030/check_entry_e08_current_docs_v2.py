"""Ten-document metadata/link QA; only explicitly authorized status edits."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REPORT = HERE / 'ENTRY-E08-CURRENT-DOCS-QA-v2.json'
QA_NAME = REPORT.name
ASSESSMENT = 'planning/Project Progress Reassessment 2026-10-30 - E08 Policy.md'
DOCS = ['README.md', 'TODO.md',
        'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
        'planning/Recovery Status and Next Gates 2026-10-26.md',
        'planning/Project Progress Reassessments.md',
        'planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md',
        ASSESSMENT, 'memory/MEMORY.md', 'memory/project-goals.md',
        'memory/research-log-2026-10-30-e08-policy.md']


def pin(path):
    path = Path(path); raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)).replace('\\', '/'),
                bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def save(value):
    with REPORT.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode())


def exact(value):
    path = ROOT / value['path']; actual = pin(path)
    if actual['bytes'] != value['bytes'] or actual['sha256'] != value['sha256']:
        raise RuntimeError('changed evidence metadata: ' + value['path'])
    return actual


before = {name: (ROOT / name).read_bytes() for name in DOCS}
texts = {name: raw.decode('utf-8') for name, raw in before.items()}
before_pins = {name: pin(ROOT / name) for name in DOCS}
checks = []


def check(name, result, detail=None):
    checks.append(dict(name=name, passed=bool(result), detail=detail))


accept_path = HERE / 'ENTRY-E08-SUITE-ROOT-ACCEPTANCE-v1.json'
accept = json.loads(accept_path.read_bytes())
check('exact_root_acceptance', pin(accept_path)['sha256'] ==
      '43316e7aa8611aa9d9df5033778d37a7ebfc3f0d64577d2728bea3abe051f2ab')
evidence = {'acceptance': pin(accept_path)}
for key in ('actual_proof', 'independent_branch_review', 'independent_byte_review', 'author_accounting_review'):
    evidence[key] = exact(accept[key])
check('root122_metrics', accept['actual']['passed_dispatches'] == 122 and
      [accept['actual'][key] for key in ('corrections', 'policy_literals', 'genuine_integration_branches', 'prior_causal_assertions')] == [5, 52, 15, 50])
check('root_resource_scope_false', not any(accept['qualification'][key] for key in
      ('complete_entry_gate', 'native25_executed', 'real_first_entry', 'target_native_or_physical',
       'full_real_roster', 'resource_fit', 'scientific', 'R09_complete', 'project_complete')))

# Prepare only the expressly authorized current-C paragraph and QA-status
# changes. Nothing is written until the complete candidate check passes.
assessment = texts[ASSESSMENT]
c_lines = [line for line in assessment.splitlines() if line.startswith('Current unvalidated work is explicit:')]
check('one_current_C_paragraph', len(c_lines) == 1)
if len(c_lines) == 1:
    replacement = ('Post-checkpoint source-only update: the [source-authoring scope]'
        '(review-assets/recovery-step9-real-route-closure-20261030/NATIVE-CARRIER-SOURCE-AUTHORING-SCOPE-v1.json) '
        '`76064321` produced the preserved `preflight_file14_raw_v1.h` / `.c` and '
        '[source design](review-assets/recovery-step9-real-route-closure-20261030/NATIVE-CARRIER-SOURCE-DESIGN-v1.md). '
        'The [first static review](review-assets/recovery-step9-real-route-closure-20261030/NATIVE-CARRIER-INDEPENDENT-SOURCE-REVIEW-v1.json) '
        '`64e89ff6` retained one requested-zero initializer HOLD. The named `preflight_file14_raw_v2.c` '
        '(8,811 bytes, `ab117f5b`) adds only the 16-byte positive-request guard; '
        '[exact delta review](review-assets/recovery-step9-real-route-closure-20261030/NATIVE-CARRIER-INDEPENDENT-SOURCE-REVIEW-v2.json) '
        '`91fc029b` clears that source mismatch. This is static source evidence only: no C compiler/build, SDK, '
        'FFI or native execution, compiled ABI, genuine kernel ticket/bank/lifetime or physical qualification. '
        'Native25 preparation is not executed coverage. Source4 and accepted E08 evidence remain unchanged.')
    assessment = assessment.replace(c_lines[0], replacement, 1)
check('one_pending_assessment_frontmatter', assessment.count('status: accepted-component-documentation-qa-pending') == 1)
assessment = assessment.replace('status: accepted-component-documentation-qa-pending',
                                'status: accepted-component-documentation-qa-passed', 1)
old = ('Independent documentation QA of this reassessment is pending and must close its separate TODO item '
       'before the documentation checkpoint is marked complete.')
check('one_pending_assessment_final_status', assessment.count(old) == 1)
assessment = assessment.replace(old, 'Independent documentation QA passes in `' + QA_NAME +
                                '`; only its separate reassessment TODO is closed.', 1)
texts[ASSESSMENT] = assessment

pending = [line for line in texts['TODO.md'].splitlines()
           if line.startswith('- [ ] Reassess all ') and 'after E08 entry policy and validate current docs/memory.' in line]
check('one_pending_E08_reassessment_TODO', len(pending) == 1)
if len(pending) == 1:
    completed = pending[0].replace('- [ ]', '- [x]', 1).replace(
        'independent documentation QA pending.', 'independent documentation QA PASS: ' + QA_NAME + '.')
    texts['TODO.md'] = texts['TODO.md'].replace(pending[0], completed, 1)
check('one_pending_memory_index_notice', texts['memory/MEMORY.md'].count('independent documentation QA pending.') == 1)
texts['memory/MEMORY.md'] = texts['memory/MEMORY.md'].replace('independent documentation QA pending.',
    'independent documentation QA PASS: `' + QA_NAME + '`.', 1)
check('one_pending_goals_notice', texts['memory/project-goals.md'].count('Independent current-document QA pending.') == 1)
texts['memory/project-goals.md'] = texts['memory/project-goals.md'].replace('Independent current-document QA pending.',
    'Independent current-document QA PASS: `' + QA_NAME + '`.', 1)
log_name = 'memory/research-log-2026-10-30-e08-policy.md'
check('one_pending_current_log_notice', texts[log_name].count('independent current-document QA is pending.') == 1)
texts[log_name] = texts[log_name].replace('independent current-document QA is pending.',
    'independent current-document QA PASS: `' + QA_NAME + '`.', 1)

for name in DOCS:
    s = texts[name]
    check(name + '/strict_UTF8_no_replacement_character', '\ufffd' not in s and not s.startswith('\ufeff'))
    check(name + '/current_checkpoint', all(value in s for value in ('43316e7a', '01e92b72', '7ae5e826', '122', '13.359', 'native25')))
    compact = ' '.join(s.lower().split())
    check(name + '/unqualified_broader_scope', any(value in compact for value in ('remain open', 'remain pending', 'remain unqualified', 'still open')))
for name in DOCS[:6]:
    line = next((line for line in texts[name].splitlines() if line.startswith('Current checkpoint, 30 October UTC:')), '')
    check(name + '/current_accepted_counts_and_scope', all(value in line for value in
          ('43316e7a', '122', '13.359', '844', '20,134,324', '846', '34,330,393', 'complete entry gate', 'native25', 'remain open')))
for name in ('memory/MEMORY.md', 'memory/project-goals.md'):
    check(name + '/new_log_pointer', '[[research-log-2026-10-30-e08-policy]]' in texts[name])

expected_status = {
    'R01': ('Accepted', 'scope'), 'R02': ('Accepted', 'checkpoint'),
    'R03': ('Accepted', 'restoration remains separate'), 'R04': ('Accepted', 'correctness'),
    'R05': ('Accepted', 'scientific sufficiency unresolved'), 'R06': ('Accepted', 'slice'),
    'R07': ('closed negative', 'human assessment pending'), 'R08': ('Partial', 'no scientifically qualified'),
    'R09': ('E08', '122', 'Complete entry', 'native25', 'remain open', 'E16'),
    'R10': ('human', 'pending'), 'R11': ('power', 'preregistration', 'pending'),
    'R12': ('Locked', 'pending'), 'R13': ('conditional', 'unqualified'),
    'R14': ('conditional', 'unqualified'), 'R15': ('conditional', 'pending'),
    'R16': ('T2', 'H6', 'pending'), 'HR1': ('Human', 'pending'),
    'HR2': ('Two independent', 'pending'), 'HR3': ('source-only', 'pending'),
    'HR4': ('independent adjudication', 'pending')}
status_rows = {match[0]: match[1].strip() for match in re.findall(
    r'^\|\s*((?:R\d{2}|HR[1-4]))\s*\|\s*(.*?)\s*\|\s*$', assessment, re.M)}
check('exact20_status_rows', set(status_rows) == set(expected_status) and len(status_rows) == 20)
for label, terms in expected_status.items():
    check('status/' + label, all(term in status_rows.get(label, '') for term in terms))
gates = re.findall(r'^([1-5])\. \*\*(.*?)\*\*', assessment, re.M)
expected_gates = ['Close the selected source/import/consumer route.',
                  'Exercise the finite native25 component contract honestly.',
                  'Freeze the joint physical14 census, representation and reservations.',
                  'Qualify native carriers and physical operations under separate scopes.',
                  'Compose the new84 run and measure the complete case before application integration.']
check('five_exact_ordered_next_stages', gates == [(str(i + 1), text) for i, text in enumerate(expected_gates)])
for key, terms in {
    'prepared_issued_eligibility': ('119 / 72 / 70', 'Prepared-only reports', '396', '400'),
    'literal_not_entry_success': ('42 exact refusals', 'Six EXECUTION metadata reports', 'four AUTHORING'),
    'worlds_and_identity': ('128 / 123 / 119', '63 / 63 true'),
    'retained_files': ('844', '20,134,324', '846', '34,330,393', '3,121,169', '17,013,155'),
    'raw_snapshots_queries': ('4,562', '4,561', '74 immutable', '4,583', '18,332', '312 query', '854,672'),
    'real_stream_distinct_from_model': ('3,991,999,872', '3,992,098,940', '99,068', '3,812', '3,842', 'periodic data'),
    'no_RSS_or_physical_claim': ('not RSS', 'VRAM/KV', 'physical14', 'Final proof'),
    'old_history_preserved': ('50 PASS / three DEFERRED', 'historical E16', '2d4979a6', 'cf4d6aac', 'fe105a5b'),
    'old_native_failure_stays': ('189', 'timeout'),
    'application_and_science': ('0.3.11', '1,774', '327', '65', '36', '17/32', '0/12', 'probabilities', '$0'),
    'current_C_static_only': ('64e89ff6', 'ab117f5b', '91fc029b', 'no C compiler/build', 'genuine kernel ticket'),
    'physical_warning': ('19,079', '13,482', '5,597', '16,384', 'not a joint admission'),
}.items():
    check('assessment/' + key, all(term.casefold() in assessment.casefold() for term in terms))

# Resolve links by document-relative/root/vault paths. Dotted note names keep
# their complete stem. Only target existence is tested, never target contents.
listed = subprocess.run(['rg', '--files', 'memory', 'planning', 'docs', '-g', '*.md'], cwd=ROOT,
                        capture_output=True, text=True, check=True).stdout.splitlines()
note_index = {}
for item in listed + ['README.md', 'TODO.md']:
    path = (ROOT / item).resolve()
    note_index.setdefault(path.stem.casefold(), []).append(path)
links = []; broken = []; outside = []


def local_target(name, target, wiki):
    value = unquote(target.strip().strip('<>'))
    if not wiki and re.match(r'^(?:https?|mailto|app|plugin|codex):', value, re.I):
        return None
    value = value.split('|', 1)[0] if wiki else value
    value = value.split('#', 1)[0]
    if not value:
        return ROOT / name
    if wiki and not value.casefold().endswith('.md'):
        value += '.md'
    base = ROOT / name
    raw = Path(value)
    candidates = [raw.resolve()] if raw.is_absolute() else [(base.parent / raw).resolve(), (ROOT / raw).resolve()]
    if wiki:
        candidates += [(ROOT / 'memory' / raw).resolve(), (ROOT / 'planning' / raw).resolve()]
        matches = note_index.get(Path(value).stem.casefold(), [])
        if len(matches) == 1:
            candidates += matches
    for candidate in candidates:
        if not candidate.is_relative_to(ROOT):
            outside.append(dict(document=name, target=target))
            continue
        if candidate.exists():
            return candidate
    return False


for name, s in texts.items():
    items = [(v, False) for v in re.findall(r'(?<!!)\[[^\]\n]+\]\((<[^>]+>|[^)\n]+)\)', s)]
    items += [(v, True) for v in re.findall(r'\[\[([^\]\n]+)\]\]', s)]
    for target, wiki in items:
        path = local_target(name, target, wiki)
        if path is None:
            continue
        row = dict(document=name, target=target, kind='wiki' if wiki else 'markdown',
                   resolved=None if path is False else str(path.relative_to(ROOT)).replace('\\', '/'))
        links.append(row)
        if path is False:
            broken.append(row)
check('all_local_Markdown_and_wikilinks_exist', not broken and not outside,
      dict(markdown=sum(v['kind'] == 'markdown' for v in links), wiki=sum(v['kind'] == 'wiki' for v in links),
           broken=broken, outside_workspace_not_followed=outside))

check('single_TODO_line_only', len(pending) == 1 and texts['TODO.md'].replace(completed, pending[0], 1).encode() == before['TODO.md'])
allowed = {ASSESSMENT, 'TODO.md', 'memory/MEMORY.md', 'memory/project-goals.md', log_name}
for name in set(DOCS) - allowed:
    check(name + '/unchanged_by_QA', texts[name].encode() == before[name])
passed = all(v['passed'] for v in checks)
if passed:
    # Refuse concurrent updater drift before any authorized edit.
    for name, raw in before.items():
        if (ROOT / name).read_bytes() != raw:
            raise RuntimeError('document changed during QA: ' + name)
    for name in allowed:
        if texts[name].encode() != before[name]:
            (ROOT / name).write_bytes(texts[name].encode())
    for name in DOCS:
        if (ROOT / name).read_bytes() != texts[name].encode():
            raise RuntimeError('final document bytes did not match checked candidate')
report = dict(schema_version=1, status='PASS_TEN_CURRENT_DOCS_E08_CHECKPOINT' if passed else 'HOLD_DOC_CHECKS',
    checker=pin(__file__), scope='E08 ten current Markdown docs;20 R/HR states,five ordered next stages,local-link existence and narrow authorized status/C-note edits only.',
    evidence=evidence, documents_before=before_pins, documents_final={name: pin(ROOT / name) for name in DOCS},
    counts=dict(checks=len(checks), passed=sum(v['passed'] for v in checks), failed=sum(not v['passed'] for v in checks),
                status_rows=len(status_rows), following_gates=len(gates), local_links=len(links),
                markdown_links=sum(v['kind'] == 'markdown' for v in links), wikilinks=sum(v['kind'] == 'wiki' for v in links)),
    checks=checks, status_rows=status_rows, next_stages=gates, broken_links=broken, links=links,
    authorized_edits_applied=sorted(allowed) if passed else [],
    authorized_edit_limits='Only the E08 reassessment TODO checkbox; assessment frontmatter/final QA status and narrow dated C-status paragraph; QA-status phrases in current MEMORY/project-goals/log entries. No other TODO/content/source change.',
    link_method='Percent-decoded document/root-relative local Markdown links; Obsidian wiki aliases/headings stripped, unique vault basename fallback preserving dotted names. Existence only; no linked payload read, no render/Obsidian runtime claim.',
    activity=dict(subject_calls=0, source_import_or_execution=0, native_or_original_operations=0, payload_reads=0,
                  application_suite_rerun=0, source_or_test_artifact_mutations=0),
    qualification='Documentation reconciliation only. Source-only E08 accepted; complete entry/native25/physical/new84/resource/science/human gates stay open.')
report['preserved_first_helper_only_hold'] = pin(HERE / 'ENTRY-E08-CURRENT-DOCS-QA-v1.json')
report['first_checker_issue'] = 'Initial vault basename index omitted docs/, producing two false missing T6-note links. Both files already existed; no current-document edits were made on that HOLD.'
save(report)
print(json.dumps(dict(status=report['status'], report=pin(REPORT), counts=report['counts'],
                      failures=[v['name'] for v in checks if not v['passed']])))
