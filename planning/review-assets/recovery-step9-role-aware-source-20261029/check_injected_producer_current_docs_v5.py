"""Current-document QA only; no subjects, original targets or experiments.

All checks finish before the sole authorized TODO checkbox edit. Earlier QA
records are untouched. Link targets receive existence checks, not body reads.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASSESSMENT = 'planning/Project Progress Reassessment 2026-10-29 - Injected Producer.md'
NAME = Path(ASSESSMENT).name
DOCS = ('README.md', 'TODO.md',
        'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
        'planning/Recovery Status and Next Gates 2026-10-26.md',
        'planning/Project Progress Reassessments.md',
        'planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md',
        'memory/MEMORY.md', 'memory/project-goals.md', ASSESSMENT,
        'memory/research-log-2026-10-29-injected-producer.md')
OUTPUT = HERE / 'ROLE-AWARE-INJECTED-PRODUCER-CURRENT-DOCS-QA-v5.json'
PENDING = ('- [ ] Reassess all R01-R16/HR1-HR4 after the injected producer small gate; '
           'retain Project Progress Reassessment 2026-10-29 - Injected Producer.md and current-document QA.')
PINS = {
    'ROLE-AWARE-PRODUCER-SMALL-GATE-ACCEPTANCE-v4.json': '096f5781b0c5d92208fcbd6a0da21528939f668be62ccd573c433ae7517b7445',
    'ROLE-AWARE-PRODUCER-SMALL-GATE-INDEPENDENT-PEER-v4.json': 'ad941fe04c7373bb33cd37dadec1088f3bb6afe2d1c7069f885e9f27f26d2567',
    'ROLE-AWARE-INDEPENDENT-LEGACY48_FIRST-PROOF-v8.json': 'f53e3db06b69337d2a8ce4b34fe851dab1338806bfe9aba0bba7b89261f22c6f',
    'ROLE-AWARE-EXTENSIONS-EXTENSIONS_FIRST-PROOF-v5.json': 'cd0caf2efce5e8899c6275d1f82df7c0a63b4f7713e4e5235f48e2ee0bf125ae',
    'ROLE-AWARE-INDEPENDENT-CODEC_FIRST-PROOF-v6.json': '8cb7b87d3e2dc8dd931fd7a2dd7c9957446a09eae1180f59ca3f587b57af2b3b',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def compact(value):
    return re.sub(r'[\s,]', '', value).lower()


def main():
    if OUTPUT.exists():
        raise RuntimeError('New QA report already exists; no overwrite or replay')
    failures = []
    checks = []

    def check(label, ok):
        checks.append(dict(check=label, passed=bool(ok)))
        if not ok:
            failures.append(label)

    raw_docs = {n: (ROOT / n).read_bytes() for n in DOCS}
    texts = {n: b.decode('utf-8', 'strict') for n, b in raw_docs.items()}
    for name, text in texts.items():
        check(name + ': current root and peer attribution', '096f5781' in text.lower() and 'ad941fe0' in text.lower())
    for name in DOCS[:6]:
        lines = [x for x in texts[name].splitlines() if x.startswith('Current checkpoint:')]
        check(name + ': one current assessment pointer', len(lines) == 1 and NAME in unquote(lines[0]))
        check(name + ': whole R09 remains open', bool(lines) and 'does not complete R09' in lines[0])
        doc_lines = texts[name].splitlines()
        current_index = next(i for i, line in enumerate(doc_lines) if line.startswith('Current checkpoint:'))
        nxt = doc_lines[current_index + 2:current_index + 3]
        check(name + ': finite next preparation and unqualified resources', len(nxt) == 1 and nxt[0].startswith('Next:') and all(x in compact(nxt[0]) for x in ('216', 'preparationonly', 'unqualified', '9d6f0240')))
    goals = texts['memory/project-goals.md']
    check('memory goals current pointer', NAME in unquote(next(x for x in goals.splitlines() if x.startswith('Current checkpoint:'))))
    check('memory index and new log connected', '[[research-log-2026-10-29-injected-producer]]' in texts['memory/MEMORY.md'] and 'name: research-log-2026-10-29-injected-producer' in texts[DOCS[-1]])

    assessment = texts[ASSESSMENT]
    rows = re.findall(r'^\| (R\d\d|HR\d) \| (.+) \|$', assessment, re.M)
    expected = [f'R{i:02d}' for i in range(1, 17)] + [f'HR{i}' for i in range(1, 5)]
    check('all20 ordered R/HR status rows', [r[0] for r in rows] == expected)
    status = dict(rows)
    for n in expected[:6]:
        check(n + ': accepted stated engineering scope', 'accepted' in status.get(n, '').lower())
    check('R07 negative and independent humans pending', 'negative' in status.get('R07', '').lower() and 'pending' in status.get('R07', '').lower())
    check('R08 remains partial and no fresh case', 'partial' in status.get('R08', '').lower() and 'no scientifically qualified fresh case' in status.get('R08', '').lower())
    check('R09 remains unfinished beyond small producer', 'remain unfinished' in status.get('R09', '').lower())
    for n in expected[9:]:
        check(n + ': pending or conditional', any(x in status.get(n, '').lower() for x in ('pending', 'conditional')))
    tail = assessment.split('## Critical next step', 1)[1]
    gates = re.findall(r'^([1-5])\. (.+)$', tail, re.M)
    check('five next gates ordered', [x[0] for x in gates] == list('12345'))
    predicates = (('216', 'original', 'separate', 'once'), ('new84', 'roster', 'entry', 'physicalpack'),
                  ('19079', '16384', '14', 'readback'), ('inference', 'ram', 'vram', 'kv', '256'),
                  ('r08', 'hr1', 'r10', 'r11', 'r12', 'hr4'))
    for i, terms in enumerate(predicates):
        check('next gate ' + str(i + 1) + ': existing required scope', len(gates) == 5 and all(x in compact(gates[i][1]) for x in terms))
    body = compact(assessment)
    check('original300-second owner budget explicit in resource paragraph', 'originalentry-anchored300-secondownerbudget' in body)
    for token in ('0.3.11/defaultv2', '1774passingfulltests', '327source/resourcepins', 'tenpreserved-version',
                  '65missinginputs', '36unqualifiedendpointlabels', '17/32', '0/12', 'featuresremainempty',
                  'probabilitiesnull', 'humanreviewspending', '$0', 'stoppedperiodicmonitor',
                  'failed', 'incomplete_timeout', 'not16384originalcalls', 'carriedwithoutreplay'):
        check('retained boundary: ' + token, token in body)

    links = []
    for name, text in texts.items():
        text = re.sub(r'(?ms)^```[^\n]*\n.*?^```[^\n]*$', '', text)
        for wrapped, bare in re.findall(r'\]\((?:<([^>]+)>|([^\s)]+))\)', text):
            target = wrapped or bare
            if target.startswith(('https:', 'http:', 'mailto:', '#')):
                continue
            resolved = ((ROOT / name).parent / unquote(target.split('#', 1)[0])).resolve()
            safe = resolved.is_relative_to(ROOT)
            exists = safe and resolved.exists()
            links.append(dict(document=name, target=target, exists=exists))
            check(name + ': local link ' + target, exists)

    evidence = {}
    for name, expected_sha in PINS.items():
        raw = (HERE / name).read_bytes()
        check('exact current evidence pin: ' + name, digest(raw) == expected_sha)
        evidence[name] = json.loads(raw)
    acceptance = evidence['ROLE-AWARE-PRODUCER-SMALL-GATE-ACCEPTANCE-v4.json']
    check('acceptance small scope only', acceptance['status'] == 'ACCEPTED_SOURCE_PURE_SMALL_PRODUCER_GATE_ONLY' and not acceptance['application_changed'])
    check('all real/resource/science qualifiers false', acceptance['qualification']['small_source_pure'] is True and all(v is False for k, v in acceptance['qualification'].items() if k != 'small_source_pure'))
    check('separate group counts', [acceptance['separate_test_groups'][k]['methods'] for k in ('pure_codec', 'genuine_legacy', 'genuine_extensions')] == [4, 9, 13])
    peer = evidence['ROLE-AWARE-PRODUCER-SMALL-GATE-INDEPENDENT-PEER-v4.json']
    check('independent peer bounded clear', peer['status'] == 'CLEAR_SOURCE_PURE_SMALL_GATE_ONLY' and peer['material_blockers'] == [])
    legacy = evidence['ROLE-AWARE-INDEPENDENT-LEGACY48_FIRST-PROOF-v8.json']
    ext = evidence['ROLE-AWARE-EXTENSIONS-EXTENSIONS_FIRST-PROOF-v5.json']
    codec = evidence['ROLE-AWARE-INDEPENDENT-CODEC_FIRST-PROOF-v6.json']
    check('actual Legacy counts', (legacy['status'], legacy['methods'], legacy['histories_executed'], legacy['histories_matched'], legacy['legacy_snapshot_count'], legacy['actual_legacy_fake_dispatches'], legacy['actual_marker_module_execs']) == ('PASS', 9, 48, 48, 372, 518, 34))
    check('actual extensions13 methods', ext['status'] == 'PASS' and ext['methods'] == 13 and len(ext['method_outcomes']) == 13 and all(x['status'] == 'PASS' for x in ext['method_outcomes']))
    check('carried codec exact scoped counts', codec['status'] == 'PASS' and codec['methods'] == 4 and codec['codec']['counts']['encode_calls'] + codec['codec']['counts']['decode_calls'] == 387 and codec['codec']['counts']['callback_exception_cases'] == 66)
    check('actual source/harness remain unchanged and audit clean', all(not r['audit_denials'] and all(r['source_unchanged'].values()) and all(r['harness_unchanged'].values()) for r in (legacy, ext)))
    check('first failures and original failed experiment retained in narrative', all(x in body for x in ('first', 'setter', 'reservation', 'packet', 'afterfinalization', 'failed', 'incomplete_timeout', 'neitherwasrepeated')))

    todo = texts['TODO.md']
    check('exact reassessment TODO pending once', todo.count(PENDING) == 1)
    check('full producer TODO remains pending', '- [ ] Finish the full-profile producer qualification:' in todo)
    check('R09 and HR work remain pending', '[ ] R09 Implement' in todo and all(f'[ ] HR{i}' in todo for i in range(1, 5)))
    changed = False
    if not failures:
        current = (ROOT / 'TODO.md').read_bytes()
        check('TODO unchanged during checks', current == raw_docs['TODO.md'])
        if not failures:
            done = PENDING.replace('- [ ]', '- [x]', 1)
            updated = current.replace(PENDING.encode(), done.encode(), 1)
            check('sole TODO edit is the selected checkbox', updated != current and len(updated) == len(current))
            if not failures:
                (ROOT / 'TODO.md').write_bytes(updated)
                changed = True
    docs = {}
    for name in DOCS:
        raw = (ROOT / name).read_bytes()
        docs[name] = dict(bytes=len(raw), sha256=digest(raw))
        if name != 'TODO.md':
            check(name + ': document unchanged by QA', raw == raw_docs[name])
    report = dict(schema_version=1, status='PASS' if not failures else 'FAIL',
                  recorded_at_utc=datetime.now(timezone.utc).isoformat(), documents=docs,
                  document_count=len(DOCS), checks=checks, failures=failures,
                  status_rows=[dict(item=k, text=v) for k, v in rows], ordered_next_gates=5,
                  local_links=links, local_link_count=len(links), assessment_local_link_count=sum(x['document'] == ASSESSMENT for x in links),
                  evidence_pins=PINS, reassessment_todo_completed=changed,
                  todo_before_sha256=digest(raw_docs['TODO.md']), todo_after_sha256=docs['TODO.md']['sha256'],
                  mutation_scope='Only the selected reassessment checkbox; no other TODO/document/source/test/pause edits.',
                  checkpoint_chronology='This assessment records the small gate. Later separately scoped reference preparation does not invalidate its at-checkpoint wording; no large-run update is made here.',
                  prior_failed_qa_sha256='f524ca700769218fab4dbd276403ff223eb089d9435bf64fed7871dbc4da6590',
                  predicate_correction='Current-next adjacency,300s budget context,features-remain-empty wording,and after-finalization wording only; all original requirements retained.',
                  helper_setup_note='An earlier ad-hoc listing used the Windows default codec and failed. This named helper always decodes exact UTF8 explicitly; that listing did not alter a file or execute a subject.',
                  application_tests_rerun=False, subject_imports=0, subject_runs=0,
                  large_helper_preparation_or_run=0, original_payload_or_native_operations=0,
                  checker_sha256=digest(Path(__file__).read_bytes()))
    with OUTPUT.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(report, out, sort_keys=True, indent=2)
        out.write('\n')
    print(json.dumps(dict(status=report['status'], documents=len(DOCS), rows=len(rows), gates=len(gates), links=len(links), todo_completed=changed, failures=failures, report_sha256=digest(OUTPUT.read_bytes()))))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
