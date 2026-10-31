"""Independent ten-current-document QA and narrowly authorized QA-status closeout."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPORT = HERE / 'C-RETURN-CURRENT-DOCS-QA-v1.json'
QA_NAME = REPORT.name
ASSESSMENT = 'planning/Project Progress Reassessment 2026-10-30 - C Return Capture.md'
LOG = 'memory/research-log-2026-10-30-c-return-capture.md'
INDEX = 'planning/Project Progress Reassessments.md'
AUTHOR = HERE / 'C-RETURN-CURRENT-DOCS-AUTHORING-v2.json'
author = json.loads(AUTHOR.read_bytes())
DOCS = [p['path'] for p in author['after_document_pins']]
checks = []


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)).replace('\\', '/'), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def check(label, ok, detail=None):
    checks.append(dict(name=label, passed=bool(ok), detail=detail))


def exact(item):
    actual = pin(ROOT / item['path'])
    check('evidence_pin/'+item['path'], actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256'])
    return actual


check('exact_authoring_v2', pin(AUTHOR)['sha256'] == 'c88ee505a45f963a5125b9e37f32a2ce0fbb1a99a064670a9fdb368e3f68a1da')
check('exact_ten_doc_set', len(DOCS) == 10 and len(set(DOCS)) == 10 and ASSESSMENT in DOCS and LOG in DOCS)
before = {name:(ROOT/name).read_bytes() for name in DOCS}
texts = {name:raw.decode('utf-8') for name,raw in before.items()}
for item in author['after_document_pins']:
    exact(item)
accept_path = HERE / 'NATIVE-CARRIER-ROOT-ACCEPTANCE-v1.json'
accept = json.loads(accept_path.read_bytes())
evidence = dict(authoring=pin(AUTHOR), acceptance=pin(accept_path))
check('root_acceptance_pin', evidence['acceptance']['sha256'] == 'ad4c9f0ece7296ac658ecec175caee028883562fd1905da4b58a4fc9952972e1')
for name,item in accept['references'].items():
    evidence[name] = exact(item)
check('fourteen_root_references', len(accept['references']) == 14)
expected_actual = dict(builds=1, build_commands=3, build_exits=[0,0,0], generated_image_dispatches=1,
    fake_controls_passed=79, C_assertions_passed=29310, initializer_attempts=79, wrapper_attempts=116,
    fake_target_calls=47, last_error_entries=17, last_error_normal_returns=16,
    partial_boundary_copies=17, primary_cell_copies=79, raw_cell_payload_bytes=24576,
    build_journal_acknowledgments=8, run_journal_acknowledgments=4, artifact_review_checks=129,
    actual_review_checks=399, build_inventory_files=11, build_inventory_bytes=339767,
    run_files_including_result=4, run_bytes_including_result=121790)
for key,value in expected_actual.items():
    check('accepted_actual/'+key, accept['actual'].get(key) == value)
check('accepted_timing', round(accept['actual']['build_elapsed_seconds'],3) == 1.047 and round(accept['actual']['run_elapsed_seconds'],3) == 0.172)
check('compiled_fake_only_qualification', accept['qualification']['compiled_layout_and_fake_target_behavior'] is True and
      not any(value for key,value in accept['qualification'].items() if key != 'compiled_layout_and_fake_target_behavior'))
check('preserved_app_spend_monitor', accept['provider_spend_usd'] == 0 and accept['application_defaults_changed'] is False and accept['downloader_or_stopped_monitor_changed'] is False)
native_dir = ROOT / 'planning/review-assets/recovery-step9-native25-component-20261030'
control_path = native_dir / 'NATIVE25-COMPONENT-PROOF-v4.json'
native_peer_path = native_dir / 'NATIVE25-COMPONENT-INDEPENDENT-ACTUAL-CONTROL-v4.json'
evidence['current_native25_actual'] = pin(control_path)
evidence['current_native25_actual_peer'] = pin(native_peer_path)
check('native25_control_hash', evidence['current_native25_actual']['sha256'] == 'dfe90829f1f8ac9e05aaaa7ce31304422150bb286c3cecb300ac7651f61ff63d')
check('native25_peer_hash', evidence['current_native25_actual_peer']['sha256'] == '27e061831086d70364bb6f8e00e5c49fa0bf7f281b2e70d00d432542f7e584ac')
native = json.loads(control_path.read_bytes())
check('native25_current_counts', native['counts'] == dict(COMPONENT_PASS=41, FAIL=2, DEFERRED_NOT_EXECUTED=4, STATIC_DECLARATION_ONLY=1))
check('native25_current_retention_clean', native['setup_error'] is None and native['evidence_error'] is None and not native['audit_denials'] and not native['changed_pins'] and not native['cooperative_deadline_late'])
for version,prefix in ((2,'2519c0b1'),(3,'bca943d0')):
    item = pin(native_dir/('NATIVE25-COMPONENT-PROOF-v%d.json'%version))
    evidence['preserved_native25_control%d'%version] = item
    check('native25_history_pin%d'%version, item['sha256'].startswith(prefix))
source5_pause_path = ROOT / 'planning/review-assets/recovery-step9-entry-source5-20261030/ENTRY-SOURCE-PAUSE-v5.json'
evidence['source5_unexecuted_pause'] = pin(source5_pause_path)
check('source5_prepared_pin', evidence['source5_unexecuted_pause']['sha256'] == '27d70c5388c9fb66855945c2c2bcad31871032ed7243d368d32fad886d35816f')
check('source5_no_result_claim', not (source5_pause_path.parent/'NATIVE25-COMPONENT-PROOF-v5.json').exists())

# Prepare candidates only; write them after every semantic/link check passes.
edits = []
def replace_one(name, old, new, label):
    check(label, texts[name].count(old) == 1)
    if texts[name].count(old) == 1:
        texts[name] = texts[name].replace(old,new,1)
        edits.append(dict(path=name, old=old, new=new))

replace_one(ASSESSMENT, 'status: accepted-component-documentation-qa-pending', 'status: accepted-component-documentation-qa-passed', 'one_assessment_frontmatter_status')
replace_one(ASSESSMENT, 'The separate reassessment/current-document QA item remains **unticked pending independent peer QA**.',
            'The separate reassessment/current-document QA passes in `'+QA_NAME+'`; only its own TODO item is checked.', 'one_assessment_final_QA_status')
todo_old = [line for line in texts['TODO.md'].splitlines() if line.startswith('- [ ] Reassess all ') and 'after C return capture and pass independent current-document/memory QA.' in line]
check('one_C_return_pending_checkbox', len(todo_old) == 1)
todo_new = None
if len(todo_old) == 1:
    todo_new = todo_old[0].replace('- [ ]','- [x]',1).replace('documentation QA pending, do not tick before the independent peer.', 'independent documentation QA PASS: '+QA_NAME+'.')
    replace_one('TODO.md',todo_old[0],todo_new,'one_TODO_QA_status')
replace_one('memory/MEMORY.md','independent current-doc QA pending.','independent current-doc QA PASS: `'+QA_NAME+'`.','one_current_MEMORY_status')
replace_one('memory/project-goals.md','Independent documentation QA remains pending and unticked.','Independent documentation QA PASS: `'+QA_NAME+'`.','one_current_goals_status')
replace_one(LOG,'independent reassessment\nand current-document QA remain pending and unticked.','independent reassessment\nand current-document QA PASS: `'+QA_NAME+'`.','one_current_log_status')
index_old = [line for line in texts[INDEX].splitlines() if line.startswith('| R09 compiled raw-carrier layout and C79 fake component accepted |')]
check('one_current_C_index_row',len(index_old)==1)
if len(index_old)==1:
    index_new=index_old[0].replace('independent documentation QA pending.','independent documentation QA PASS: `'+QA_NAME+'`.')
    replace_one(INDEX,index_old[0],index_new,'one_current_C_index_QA_status')

assessment=texts[ASSESSMENT]
for name in DOCS:
    check(name+'/UTF8', '\ufffd' not in texts[name] and not texts[name].startswith('\ufeff'))
    check(name+'/accepted_C_metrics',all(term in texts[name] for term in ('ad4c9f0e','5796bcc6','1b10326d','79','29,310','129','399','121,790')))
    current = texts[name] if name in (ASSESSMENT,LOG,'memory/MEMORY.md') else '\n'.join(texts[name].splitlines()[:45]) if name=='memory/project-goals.md' else next((line for line in texts[name].splitlines() if line.startswith('Current checkpoint, 30 October UTC:')),'')
    check(name+'/native25_current_not_complete', all(term in current for term in ('41 PASS','Source5','unexecuted')) and ('two FAIL' in current or 'two FAIL' in texts[name]))
for name in DOCS[:6]:
    line=next((line for line in texts[name].splitlines() if line.startswith('Current checkpoint, 30 October UTC:')),'')
    check(name+'/current_scope',all(term in line for term in ('47 fake','17 error entries / 16 returns','0.172','122','Python conversion bridge','remain open')))
    next_line=next((line for line in texts[name].splitlines() if line.startswith('Next: correct only the two remaining native25')),'')
    check(name+'/next_and_history',all(term in next_line for term in ('Source5','31/12','38/5','separate execution binding','19,079','1,774','327','$0')))
for name in ('memory/MEMORY.md','memory/project-goals.md'):
    check(name+'/current_log_link','[[research-log-2026-10-30-c-return-capture]]' in texts[name])

expected_status = {
    'R01':('Accepted','scope'), 'R02':('Accepted','checkpoint'), 'R03':('Accepted','restoration remains separate'),
    'R04':('Accepted','correctness'), 'R05':('Accepted','scientific sufficiency unresolved'), 'R06':('Accepted','slice'),
    'R07':('closed negative','human assessment pending'), 'R08':('Partial','no scientifically qualified'),
    'R09':('C79','Source4','122','Native25','remain open'), 'R10':('human','pending'),
    'R11':('power','preregistration','pending'), 'R12':('Locked','pending'), 'R13':('conditional','unqualified'),
    'R14':('conditional','unqualified'), 'R15':('conditional','pending'), 'R16':('T2','H6','pending'),
    'HR1':('Human','pending'), 'HR2':('Two independent','pending'), 'HR3':('source-only','pending'), 'HR4':('independent adjudication','pending')}
status_rows={key:value.strip() for key,value in re.findall(r'^\|\s*((?:R\d{2}|HR[1-4]))\s*\|\s*(.*?)\s*\|\s*$',assessment,re.M)}
check('exact_twenty_status_rows',set(status_rows)==set(expected_status) and len(status_rows)==20)
for key,terms in expected_status.items():
    check('status/'+key,all(term in status_rows.get(key,'') for term in terms))
gates=re.findall(r'^([1-5])\. \*\*(.*?)\*\*',assessment,re.M)
expected_gates=['Correct the two remaining native25 API/axis-kind guards.',
    'Close the actual new84 source/import/consumer and bridge design.',
    'Qualify the same-Core native bridge and bounded original7 boundary.',
    'Freeze and qualify joint physical14 operations and genuine held leases.',
    'Compose and measure the complete new84 route before application/scientific advancement.']
check('five_exact_ordered_next_stages',gates==[(str(i+1),name) for i,name in enumerate(expected_gates)])
for label,terms in {
    'C_acceptance_vs_runtime':('three commands','1.047','79 PASS / 29,310','399 / 399','0.172','not 79 real Win32'),
    'raw_layout_and_counts':('128-byte header','32-byte axes','256-byte cell','79 / 116','47 / 17 / 16','24,576','3,524','163,328'),
    'retained_build_and_run_bytes':('339,767','7,136','346,903','57,264','1,365','58,629','63,161','121,790'),
    'qualification_limits':('not measure','RSS','VRAM/KV','physical producer ACK','Python conversion','same-Core native bank','not a built/ABI-qualified extension'),
    'native25_history_and_specific_errata':('2519c0b1','31 PASS / 12 FAIL','bca943d0','38 PASS / five FAIL','dfe90829','41 PASS / two FAIL','RAW_RETURN_UNKNOWN','READ_PROGRESS_INCOMPLETE','READ_COUNT_UNKNOWN'),
    'Source5_not_accepted':('Source5 guard authoring','unexecuted','Independent source/harness review','separate runtime binding'),
    'preserved_failures_and_no_hidden_replay':('HOLDs','V3 nonlocal-binding defect','5bd681cb','no hidden failed image attempt','FAILED','INCOMPLETE_TIMEOUT'),
    'application_science_humans':('0.3.11/default v2','1,774','327','ten preserved versions','65 missing','36 unqualified','17/32','0/12','Features remain empty','probabilities null','human reviews pending','$0'),
    'physical_and_execution_boundaries':('19,079','13,482','5,597','16,384','not a fitted profile','planned/null','300/child120/work117','256 MiB','189','new84'),
}.items():
    check('assessment/'+label,all(term.casefold() in assessment.casefold() for term in terms))

# Only local target existence is tested. Linked payload/source contents are not opened.
listed=subprocess.run(['rg','--files','memory','planning','docs','-g','*.md'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.splitlines()
note_index={}
for item in listed+['README.md','TODO.md']:
    path=(ROOT/item).resolve()
    note_index.setdefault(path.stem.casefold(),[]).append(path)
links=[];broken=[];outside=[]
def target(name,value,wiki):
    value=unquote(value.strip().strip('<>'))
    if not wiki and re.match(r'^(?:https?|mailto|app|plugin|codex):',value,re.I):return None
    if wiki:value=value.split('|',1)[0]
    value=value.split('#',1)[0]
    if not value:return ROOT/name
    if wiki and not value.casefold().endswith('.md'):value+='.md'
    raw=Path(value)
    candidates=[raw.resolve()] if raw.is_absolute() else [((ROOT/name).parent/raw).resolve(),(ROOT/raw).resolve()]
    if wiki:
        candidates += [(ROOT/'memory'/raw).resolve(),(ROOT/'planning'/raw).resolve()]
        matches=note_index.get(Path(value).stem.casefold(),[])
        if len(matches)==1:candidates+=matches
    for candidate in candidates:
        if not candidate.is_relative_to(ROOT):
            outside.append(dict(document=name,target=value));continue
        if candidate.exists():return candidate
    return False
for name,text in texts.items():
    values=[(v,False) for v in re.findall(r'(?<!!)\[[^\]\n]+\]\((<[^>]+>|[^)\n]+)\)',text)]
    values += [(v,True) for v in re.findall(r'\[\[([^\]\n]+)\]\]',text)]
    for value,wiki in values:
        resolved=target(name,value,wiki)
        if resolved is None:continue
        row=dict(document=name,target=value,kind='wiki' if wiki else 'markdown',resolved=None if resolved is False else str(resolved.relative_to(ROOT)).replace('\\','/'))
        links.append(row)
        if resolved is False:broken.append(row)
check('all_local_Markdown_and_wikilinks',not broken and not outside,dict(broken=broken,outside_not_followed=outside))
allowed={ASSESSMENT,LOG,INDEX,'TODO.md','memory/MEMORY.md','memory/project-goals.md'}
check('only_single_checkbox_TODO_changed',len(todo_old)==1 and texts['TODO.md'].replace(todo_new,todo_old[0],1).encode('utf-8')==before['TODO.md'])
for name in set(DOCS)-allowed:
    check(name+'/unchanged_by_QA',texts[name].encode('utf-8')==before[name])
passed=all(row['passed'] for row in checks)
if passed:
    for name,raw in before.items():
        if (ROOT/name).read_bytes()!=raw:raise RuntimeError('Concurrent document drift: '+name)
    for name in allowed:
        (ROOT/name).write_bytes(texts[name].encode('utf-8'))
    for name in DOCS:
        if (ROOT/name).read_bytes()!=texts[name].encode('utf-8'):raise RuntimeError('Post-edit candidate mismatch: '+name)
result=dict(schema_version=1,status='PASS_TEN_CURRENT_DOCS_C_RETURN_CAPTURE' if passed else 'HOLD_CURRENT_DOC_CHECKS',
    checker=pin(__file__),evidence=evidence,
    scope='Ten current docs at C-return checkpoint,20R/HR states,five ordered next stages,local Markdown/wiki link existence and authorized QA-status closeout only.',
    documents_before={name:dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for name,raw in before.items()},
    documents_final={name:pin(ROOT/name) for name in DOCS},
    counts=dict(documents=len(DOCS),checks=len(checks),passed=sum(r['passed'] for r in checks),failed=sum(not r['passed'] for r in checks),
                status_rows=len(status_rows),ordered_next_stages=len(gates),local_links=len(links),markdown_links=sum(r['kind']=='markdown' for r in links),wikilinks=sum(r['kind']=='wiki' for r in links)),
    checks=checks,status_rows=status_rows,next_stages=gates,links=links,broken_links=broken,
    authorized_edits=edits if passed else [],
    edit_limits='Only the C-return reassessment checkbox and current QA-status phrases/frontmatter in this assessment, C-return index row, MEMORY/project-goals/new C-return log. No other TODO/history/source change.',
    local_link_method='Percent-decoded document/root paths and unique Obsidian vault basename fallback;aliases/headings stripped. Existence only, no render or linked payload-content read.',
    activity=dict(subject_calls=0,source_imports=0,application_tests=0,builds=0,native_dispatches=0,original_model_payload_reads=0),
    qualification='Documentation-only reconciliation. Accepted compiled C79 fake behavior and Source4 E08 stay scoped; Source5 unexecuted, native25 two failures plus deferred branches, real/native/physical/resources/science/humans open.')
with REPORT.open('xb') as stream:
    stream.write((json.dumps(result,indent=2,sort_keys=True,ensure_ascii=True)+'\n').encode('utf-8'))
print(json.dumps(dict(status=result['status'],report=pin(REPORT),counts=result['counts'],failures=[r for r in checks if not r['passed']]),indent=2))
