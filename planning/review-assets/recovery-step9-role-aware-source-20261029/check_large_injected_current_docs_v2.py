"""Ten current docs only; metadata QA and one conditional TODO checkbox edit.

No subject/source import, producer or experiment execution. Link checks inspect
existence only; exact evidence checks read named new metadata records only.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASSESSMENT = 'planning/Project Progress Reassessment 2026-10-29 - Large Injected Producer.md'
LOG = 'memory/research-log-2026-10-29-large-injected-producer.md'
DOCS = ('README.md', 'TODO.md',
        'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
        'planning/Recovery Status and Next Gates 2026-10-26.md',
        'planning/Project Progress Reassessments.md',
        'planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md',
        'memory/MEMORY.md', 'memory/project-goals.md', ASSESSMENT, LOG)
OUTPUT = HERE / 'ROLE-AWARE-LARGE-INJECTED-CURRENT-DOCS-QA-v2.json'
PINS = {
    'ROLE-AWARE-LARGE-INJECTED-ROOT-ACCEPTANCE-v3.json': '93eeaef97a34bc07d99e00dc4c0cb84b24cee4fd8a19cde7342301579e7872e0',
    'ROLE-AWARE-LARGE-INJECTED-PROOF-v3.json': '7cefbe0e5dc71f950a3537be9f30790d0c7501ca7c5c3446c3c331567a98cedf',
    'ROLE-AWARE-LARGE-INJECTED-INDEPENDENT-ACTUAL-PEER-v2.json': 'fa6b4375559d310587cd7ea53a0679bd1434182a78c8984e1723337ecbb0f2a5',
    'ROLE-AWARE-LARGE-ACTUAL-ACCOUNTING-RESOURCE-REVIEW-v3.json': '674cdf3471c133153882752a948b8515ce8518efee0472bb2834607cad1edd24',
    'ROLE-AWARE-LARGE-REFERENCE-PROOF-v1.json': '1a3e47ec28b1f96c4ac0d5c9c9eb7c2f13288cf5a6df4e3c4f6853d07a56aa03',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def compact(value):
    return re.sub(r'[\s,]', '', value).lower()


def main():
    if OUTPUT.exists():
        raise RuntimeError('Retain the first QA result; no overwrite')
    checks = []
    failures = []

    def check(label, ok):
        checks.append(dict(check=label, passed=bool(ok)))
        if not ok:
            failures.append(label)

    raw_docs = {name: (ROOT / name).read_bytes() for name in DOCS}
    texts = {name: raw.decode('utf-8', 'strict') for name, raw in raw_docs.items()}
    title = Path(ASSESSMENT).name
    for name, text in texts.items():
        check(name + ': accepted current scope attributed', '93eeaef9' in text.lower() and 'fa6b4375' in text.lower())
    for name in DOCS[:6]:
        lines = texts[name].splitlines()
        current = [i for i, line in enumerate(lines) if line.startswith('Current checkpoint:')]
        check(name + ': one current assessment pointer', len(current) == 1 and title in unquote(lines[current[0]]))
        if current:
            check(name + ': R09 completion not claimed', 'does not complete R09' in lines[current[0]] or 'not R09 or production qualification' in lines[current[0]])
            next_lines = [line for line in lines[current[0]+1:current[0]+5] if line.startswith('Next:')]
            check(name + ': next real roster/entry/physical composition', len(next_lines) == 1 and all(x in compact(next_lines[0]).replace('-','') for x in ('roster', 'entry', 'physical', 'new84')))
    goals_current = texts['memory/project-goals.md'].split('Prior checkpoint:',1)[0]
    check('memory goals current pointer and scoped next', title in unquote(goals_current) and all(x in compact(goals_current).replace('-','') for x in ('nextis','new84','roster','origin','class','physical','gatesremainopen')))
    check('memory current large log indexed', '[[research-log-2026-10-29-large-injected-producer]]' in texts['memory/MEMORY.md'])
    check('large log frontmatter', 'name: research-log-2026-10-29-large-injected-producer' in texts[LOG])
    assessment = texts[ASSESSMENT]
    body = compact(assessment)
    check('assessment final acceptance rather than draft', '**DRAFT' not in assessment and 'acceptance is pending' not in assessment and '93eeaef9' in body)
    rows = re.findall(r'^\| (R\d\d|HR\d) \| (.+) \|$', assessment, re.M)
    expected = [f'R{i:02d}' for i in range(1,17)] + [f'HR{i}' for i in range(1,5)]
    check('all20 ordered R/HR statuses', [key for key, _ in rows] == expected)
    status = dict(rows)
    for key in expected[:6]:
        check(key + ': accepted engineering scope', 'accepted' in status.get(key, '').lower())
    check('R07 negative / humans pending', all(x in status.get('R07','').lower() for x in ('negative','pending')))
    check('R08 partial / no scientific fresh case', 'partial' in status.get('R08','').lower() and 'no scientifically qualified fresh case' in status.get('R08','').lower())
    check('R09 large narrow acceptance / unfinished remainder', all(x in status.get('R09','').lower() for x in ('accepted','216-input','generated','unfinished')))
    for key in expected[9:]:
        check(key + ': pending or conditional', any(x in status.get(key,'').lower() for x in ('pending','conditional')))
    gate_tail = assessment.split('## Next major stage:',1)[-1]
    gates = re.findall(r'^([1-5])\. (.+)$', gate_tail, re.M)
    check('five critical next gates in order', [n for n,_ in gates] == list('12345'))
    required_gate_terms = (
        ('roster','consumer','712415','8989020320','role'),
        ('core4','5232640','unresolved','024e0536'),
        ('entry','origin','nonce','before','import','class'),
        ('19079','13482','5597','16384','14','readback'),
        ('84','78','68','37766','genuine','child','pipe','clock'))
    for i, terms in enumerate(required_gate_terms):
        check('gate ' + str(i+1) + ': existing bounded critical path', len(gates) == 5 and all(x in compact(gates[i][1]) for x in terms))
    for term in ('9017363601','8799','10095','216','209','1331','9879','19974','10.094','0.359','4373152','4428448','1775088','11575490','8980699','14410009','23390708','15',
                 '0.3.11/defaultv2','1774passingfulltests','327source/resourcepins','tenpreserved-version','65missinginputs','36unqualifiedendpointlabels','17/32','0/12','featuresareempty','probabilitiesnull','humanreviewspending','$0','stoppedperiodicmonitor','failed','incomplete_timeout'):
        check('retained assessment fact: ' + term, term in body)
    check('resource observations not RSS/fit', 'peakrsswasnotestablished' in body and 'notprocessrss' in body and '256' in body)
    check('earlier report-phase prefix is intentional', all(x in body for x in ('8803608','1330','8980699','1331','earlier')))
    check('reference separate / 198 checkpoints', all(x in body for x in ('1.578','198','3991999872','separately')))
    check('reviewer setup failure is not producer failure or replay', 'reviewer-helper' in body and 'notaproducerfailureorreplay' in body)
    check('all authority flags remain false', 'qualificationflagsremainfalse' in body and 'synthetic' in body and 'scientific' in body)
    links = []
    for name, text in texts.items():
        text = re.sub(r'(?ms)^```[^\n]*\n.*?^```[^\n]*$', '', text)
        for wrapped, bare in re.findall(r'\]\((?:<([^>]+)>|([^\s)]+))\)', text):
            target = wrapped or bare
            if target.startswith(('https:','http:','mailto:','#')):
                continue
            resolved = ((ROOT / name).parent / unquote(target.split('#',1)[0])).resolve()
            safe = resolved.is_relative_to(ROOT)
            exists = safe and resolved.exists()
            links.append(dict(document=name,target=target,exists=exists))
            check(name + ': local link ' + target, exists)
    evidence = {}
    for name, expected_sha in PINS.items():
        raw = (HERE / name).read_bytes()
        check('exact evidence pin: ' + name, sha(raw) == expected_sha)
        evidence[name] = json.loads(raw)
    acceptance = evidence['ROLE-AWARE-LARGE-INJECTED-ROOT-ACCEPTANCE-v3.json']
    check('root accepted only generated source/pure', acceptance['status'] == 'ACCEPTED_LARGE_GENERATED_SOURCE_PURE_ONLY' and not acceptance['application_changed'] and not acceptance['project_complete'] and acceptance['actual_experiments'] == 1)
    check('all root authority/fit flags false', all(v is False for v in acceptance['qualification'].values()) and acceptance['actual_peak_RSS'] is None and acceptance['provider_spend_usd'] == 0)
    check('exact storage categories', (acceptance['retained_files'],acceptance['source_generated_disk_bytes'],acceptance['harness_evidence_disk_bytes'],acceptance['retained_disk_bytes']) == (15,8980699,14410009,23390708))
    check('timing categories distinct', round(acceptance['source_unwind_seconds'],3) == 10.094 and round(acceptance['separate_evidence_persistence_seconds'],3) == 0.359)
    proof = evidence['ROLE-AWARE-LARGE-INJECTED-PROOF-v3.json']
    check('actual proof narrow PASS and immutable/source-audit clean', proof['status'] == 'PASS_SOURCE_PURE_LARGE_GENERATED_ONLY' and all(proof['source_and_harness_unchanged'].values()) and proof['first_exception'] is None and proof['evidence_publication_error'] is None and not proof['audit_denials'] and not proof['monitor_violations'])
    check('proof exact raw/dispatch/read/close/capture/hash counts', (proof['canonical_raw_sidecar']['rows_written'],proof['actual_original_dispatches'],proof['actual_read_dispatch_attempts'],proof['actual_close_attempts'],proof['canonical_known_successful_close_returns'],proof['positive_verification']['byte_totals']['hashed_bytes'],proof['positive_verification']['byte_totals']['captured_bytes']) == (10095,10095,8799,216,216,9017363601,209))
    peer = evidence['ROLE-AWARE-LARGE-INJECTED-INDEPENDENT-ACTUAL-PEER-v2.json']
    check('independent actual peer finite clear', peer['status'] == 'CLEAR_SOURCE_PURE_LARGE_GENERATED_RESULT_ONLY' and peer['material_blockers'] == [] and peer['activity']['producer_runs'] == 0)
    resource = evidence['ROLE-AWARE-LARGE-ACTUAL-ACCOUNTING-RESOURCE-REVIEW-v3.json']
    check('resource accounting clear / physical fit unknown', resource['status'] == 'CLEAR_ACTUAL_ACCOUNTING_EVIDENCE_SOURCE_PURE_ONLY_RESOURCE_FIT_UNKNOWN' and resource['all_evidence_disk_bytes'] == 23390708)
    ref = evidence['ROLE-AWARE-LARGE-REFERENCE-PROOF-v1.json']
    check('reference separately complete, not producer calls', ref['status'] == 'REFERENCE_COMPLETE' and ref['unique_checkpoint_count'] == 198 and ref['reference_bytes_hashed'] == 3991999872 and ref['actual_reference_owner_or_subject_calls'] == 0)
    todo = texts['TODO.md']
    pending = [line for line in todo.splitlines() if line.startswith('- [ ] Reassess all R01-R16/HR1-HR4 after the selected large injected producer')]
    check('one exact large reassessment checkbox pending', len(pending) == 1)
    check('broad R09 / humans remain pending', '[ ] R09 Implement' in todo and all(f'[ ] HR{i}' in todo for i in range(1,5)))
    check('full producer qualification remains pending', any(line.startswith('- [ ] Complete broader role-aware producer qualification') and all(x in line for x in ('new-84','entry/Origin','real FFI','physical writer/readback','integrated resource/native','does not close this item')) for line in todo.splitlines()))
    changed = False
    if not failures:
        current = (ROOT / 'TODO.md').read_bytes()
        check('TODO unchanged during all checks', current == raw_docs['TODO.md'])
        if not failures:
            updated = current.replace(pending[0].encode(),pending[0].replace('- [ ]','- [x]',1).encode(),1)
            check('only one checkbox byte changes', len(updated)==len(current) and sum(a!=b for a,b in zip(updated,current))==1)
            if not failures:
                (ROOT/'TODO.md').write_bytes(updated)
                changed = True
    docs = {}
    for name in DOCS:
        raw = (ROOT/name).read_bytes()
        docs[name] = dict(bytes=len(raw),sha256=sha(raw))
        if name != 'TODO.md':
            check(name + ': unchanged by QA', raw == raw_docs[name])
    report = dict(schema_version=1,status='PASS' if not failures else 'FAIL',recorded_at_utc=datetime.now(timezone.utc).isoformat(),documents=docs,document_count=len(DOCS),checks=checks,failures=failures,status_rows=[dict(item=k,text=v) for k,v in rows],ordered_next_gates=5,local_links=links,local_link_count=len(links),assessment_local_link_count=sum(x['document']==ASSESSMENT for x in links),evidence_pins=PINS,reassessment_todo_completed=changed,todo_before_sha256=sha(raw_docs['TODO.md']),todo_after_sha256=docs['TODO.md']['sha256'],mutation_scope='Only the pending large reassessment checkbox after successful QA; no other document/TODO/source/test/pause changes.',subject_imports=0,subject_runs=0,producer_replay=0,original_payload_or_native_operations=0,application_tests_rerun=False,checker_sha256=sha(Path(__file__).read_bytes()),preserved_first_qa_sha256='909331d2629b30ac6dfbf16ad5c9a9744b1de64d03912893cb7b3f2be1d87f2d',predicate_correction='Only two wording-equivalent predicates: selected216-input generated R09 acceptance and explicitly pending broader role-aware producer TODO. No document or requirement correction.')
    with OUTPUT.open('x',encoding='utf-8',newline='\n') as out:
        json.dump(report,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(status=report['status'],checks=len(checks),documents=len(DOCS),rows=len(rows),gates=len(gates),links=len(links),todo_completed=changed,failures=failures,report_sha256=sha(OUTPUT.read_bytes()))))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
