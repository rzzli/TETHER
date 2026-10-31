"""Data-only reconstruction of the retained failed singleton experiment.

No pack/CPU/model path is inspected. This records negative evidence, never a
replacement success validator or a route to repeat the frozen experiment.
"""
import collections
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUTPUT=ROOT/'data/cache/r09-recognition-observation-v1-20261029T051950Z'
CHILD=OUTPUT/'execution/child'
REPORT=HERE/'RECOGNITION-NEGATIVE-COVERAGE-RECONSTRUCTION-v1.json'
NOTE=HERE/'RECOGNITION-NEGATIVE-COVERAGE-RECONSTRUCTION-v1.md'
START=time.monotonic();DEADLINE=START+60
ACTIVITY=[]
def tick():
    if time.monotonic()>=DEADLINE:raise TimeoutError('Bounded data-only coverage review')
def need(value,message):
    if not value:raise AssertionError(message)
def read(path,cap=2*1024**2):
    tick();path=Path(path);raw=path.read_bytes();need(len(raw)<=cap,'Metadata cap');tick();return raw
def pin(path):
    raw=read(path,8*1024**2);return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def parsed(path):return json.loads(read(path))
contract=parsed(HERE/'RECOGNITION-EXECUTION-CONTRACT-v1.json')
manifest=parsed(HERE/'RECOGNITION-EXPECTED-PACK-METADATA-v1.json')
wire=parsed(HERE/'RECOGNITION-CHILD-WIRE-v2.json')
PAYLOAD_KEYS={str(r['path']).replace('/','\\').lower() for r in [contract['CPU_descriptor'],*contract['ordered_shard_descriptors'],manifest['pack']]}
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        ACTIVITY.append(event);raise AssertionError('Data-only audit cannot execute native/process/network')
    if event=='open' and args and isinstance(args[0],(str,bytes)) and str(args[0]).replace('/','\\').lower() in PAYLOAD_KEYS:
        ACTIVITY.append('payload_open');raise AssertionError('No CPU/model/pack content read')
sys.addaudithook(guard)
for name in ('stat','lstat','resolve','open'):
    original=getattr(Path,name)
    def wrapper(path,*args,_name=name,_original=original,**kwargs):
        if str(path).replace('/','\\').lower() in PAYLOAD_KEYS:
            ACTIVITY.append(_name);raise AssertionError('No CPU/model/pack path inspection')
        return _original(path,*args,**kwargs)
    setattr(Path,name,wrapper)
VALIDATOR=HERE/'recognition_validation_v3.py'
need(pin(VALIDATOR)['sha256']=='bbd98b162bf47ff035a945cca29b97c5290113b39c8b1efb7770abc89f0ca229','Frozen pure validator changed')
spec=util.spec_from_file_location('negative_recognition_data_validator',VALIDATOR)
v=util.module_from_spec(spec);spec.loader.exec_module(v)
raw=read(CHILD/'result.partial.jsonl',8*1024**2)
rows=[v.json_value(line) for line in raw.splitlines()]
need(len(rows)==400 and all(type(r) is dict for r in rows),'Exact retained partial row count')
failure=v.json_value(read(CHILD/'failure.json'))
need(rows[-1]==failure and failure['message']=='required_partial_UTF8_prefix_coverage_unavailable','Failure marker/last-row binding')
need(not (CHILD/'result.jsonl').exists(),'Failed partial cannot have a finalized result')
counter=None;progress=dict(computed=0,written=0,prefix_seen=0,prefix_written=0,groups=[0,0,0],group_written=[0,0,0])
cases=[];prefixes=[];groups=collections.defaultdict(collections.Counter);all_case_bodies=[]
setup=[r for r in rows if r.get('event')=='all_vocabulary_ids_EOG_enumerated']
need(len(setup)==1,'One EOG enumeration frame');eog=setup[0]['EOG_ids'];nv=setup[0]['vocabulary_count']
need(eog==sorted(set(eog)) and len(eog)==6 and 0<min(eog)<=max(eog)<nv,'Bounded unique observed EOG IDs')
need(hashlib.sha256(json.dumps(eog,separators=(',',':')).encode('ascii')).hexdigest()==setup[0]['EOG_JSON_sha256'],'Observed EOG vector digest')
for ordinal,row in enumerate(rows):
    tick();counter,state=v.counter_frame(row,contract,wire,counter,allow_pending=True)
    event=row.get('event')
    if event=='before_case':
        index=len(cases);case=manifest['cases'][index]
        need(row['case_index']==index and row['id']==case['id'] and row['document_sha256']==case['sha256'],'Ordered before-case identity')
    elif event=='case_result':
        index=len(cases);case=manifest['cases'][index];kind=case['expected_kind']
        expected=dict(event='case_result',case_index=index,source_group=case['source_group'],id=case['id'],bytes=case['bytes'],
            document_sha256=case['sha256'],tokens=row['tokens'],used_piece_NUL_seen=False,first_NUL_piece_index=None,
            first_NUL_offset_in_piece=None,expected_kind=kind,expected_native_membership=(kind==1 if kind<=1 else None),matches_expected=True)
        need(type(row['tokens']) is int and 0<=row['tokens']<=65536,'Case token cap')
        if kind in (2,3):
            need(row['tokens']==0,'Harness rejects before native tokenization')
            expected.update(status='harness_utf8_rejection' if kind==2 else 'harness_raw_nul_rejection',native_membership=None,completion_EOG=None)
        elif kind==1:
            need(row['tokens']>0,'Native case token count')
            expected.update(status='native_member',all_input_tokens_admitted=True,first_rejected_token_index=None,
                completion_EOG=[dict(id=i,admitted=True) for i in eog],first_rejected_byte_start=None,first_rejected_byte_end=None)
        else:
            need(row['status']=='native_token_rejection' and type(row['first_rejected_token_index']) is int
                and 0<=row['first_rejected_token_index']<row['tokens'],'Actual negative token rejection bound')
            start,end=row['first_rejected_byte_start'],row['first_rejected_byte_end']
            need(type(start) is int and type(end) is int and 0<=start<=end<=case['bytes'],'Actual rejected byte-span bound')
            expected.update(status='native_token_rejection',all_input_tokens_admitted=False,first_rejected_token_index=row['first_rejected_token_index'],
                completion_EOG=None,first_rejected_byte_start=start,first_rejected_byte_end=end)
        body={k:value for k,value in row.items() if k not in v.AUGMENT}
        need(v.exact(body,expected),'Complete case body/types/manifest/outcome differs: '+case['id'])
        cases.append(case);progress['computed']+=1;progress['groups'][case['source_group']]+=1
        groups[case['source_group']][row['status']]+=1
        all_case_bodies.append(dict(id=case['id'],index=index,group=case['source_group'],document_sha256=case['sha256'],
            bytes=case['bytes'],expected_kind=kind,status=row['status'],independent_metadata_body_check=True,
            original_bytes_rehashed_in_this_review=False,native_execution_repeated=False))
    elif event=='prefix_result':
        found=[p for p in manifest['prefixes'] if p['id']==row['id']];need(len(found)==1,'Frozen prefix ID')
        p=found[0];base=manifest['cases'][p['base_case_index']]
        need(cases and cases[-1]['id']==base['id'],'Prefix source/base-case order')
        progress['prefix_seen']+=1
        if p['kind']:
            need(v.exact({k:value for k,value in row.items() if k not in v.AUGMENT},
                dict(event='prefix_result',id=p['id'],status='coverage_unavailable',matches_expected=None)),'Unavailable natural-prefix row')
            need(state['required_UTF8_prefix_unavailable'] is True,'Unavailable source flag retained')
            prefixes.append(dict(id=p['id'],base_id=base['id'],base_document_sha256=base['sha256'],kind=p['kind'],status='coverage_unavailable',
                native_EOG_checks_for_this_slot=0,required_coverage_established=False))
        else:
            expected=dict(event='prefix_result',id=p['id'],base_id=base['id'],prefix_kind=0,byte_cut=p['cut'],token_count=row['token_count'],
                prefix_sha256=p['sha256'],partial_UTF8_at_cut=False,last_piece_complete_codepoints_before_partial=False,matches_expected=True,
                status='native_eog_rejection',all_input_tokens_admitted=True,first_rejected_token_index=None,
                completion_EOG=[dict(id=i,admitted=False) for i in eog],first_rejected_byte_start=None,first_rejected_byte_end=None)
            need(type(row['token_count']) is int and 0<=row['token_count']<=65536,'Fixed prefix token cap')
            need(v.exact({k:value for k,value in row.items() if k not in v.AUGMENT},expected),'Fixed prefix byte/hash/EOG body')
            prefixes.append(dict(id=p['id'],base_id=base['id'],base_document_sha256=base['sha256'],kind=0,byte_cut=p['cut'],prefix_sha256=p['sha256'],
                status='reported_all_ordinary_tokens_admitted_and_all_EOG_rejected',partial_UTF8_at_cut=False,required_coverage_established=True))
    need(v.exact([state['cases_computed'],state['case_results_written'],state['prefix_slots_seen'],state['prefix_results_written']],
        [progress['computed'],progress['written'],progress['prefix_seen'],progress['prefix_written']]),'Per-row compute/write acknowledgment schedule')
    need(v.exact(state['group_computed'],progress['groups']) and v.exact(state['group_results_written'],progress['group_written']),
        'Per-group computation/write schedule')
    if event=='case_result':progress['written']+=1;progress['group_written'][row['source_group']]+=1
    elif event=='prefix_result':progress['prefix_written']+=1
need(len(cases)==189 and len(prefixes)==6 and progress['groups']==[167,18,4],'Whole retained case/prefix inventory')
need(len({c['id'] for c in cases})==189 and len({p['id'] for p in prefixes})==6,'No repeated case/prefix')
need(sum(groups[0].values())==167 and groups[0]==dict(native_member=44,native_token_rejection=122,harness_raw_nul_rejection=1),'Frozen primary layer counts')
need(groups[1]==dict(native_member=18) and groups[2]==dict(harness_utf8_rejection=2,harness_raw_nul_rejection=2),'Separate authored/guard layers')
need(all(pair['attempted']==pair['returned'] for pair in counter.values()),'No reported explicit outstanding native call')
state=failure['native_state'];need(state['total_attempted']==state['total_returned']==442668,'Reported explicit aggregate')
need(state['samplers_owned']==state['sampler_release_unknown']==0 and state['sampler_nonnull_returns']==state['sampler_free_returned_nonnull']==188,
    'Reported sampler cleanup')
need(not state['model_owned'] and not state['backend_owned'] and not state['model_release_unknown'] and not state['backend_release_unknown']
    and state['model_free_return_observed'] and state['backend_free_return_observed'] and not state['cleanup_failed'],'Reported model/backend cleanup')
parent=parsed(OUTPUT/'parent-report.json')
need(parent['status']=='failed' and parent['returncode']==2 and parent['reaped'] is True,'Parent negative observed exit')
need(parent['partial_coverage']['status']=='not_inspected_unknown','Original parent partial-coverage uncertainty preserved')
need(not any(r.get('event') in ('recognition_batch_returned','child_normal_completion') for r in rows),'No full completion')
first_unavailable=next(i for i,r in enumerate(rows) if r.get('status')=='coverage_unavailable')
need(first_unavailable==239,'First required missing prefix position')
result=dict(schema_version=1,status='negative_coverage_reconstructed_NOT_qualified',review_type='AI data-only independent row/counter reconstruction; not native replay or scientist review',
    inputs={name:pin(path) for name,path in [('partial_result',CHILD/'result.partial.jsonl'),('child_failure',CHILD/'failure.json'),('parent_report',OUTPUT/'parent-report.json'),
        ('manifest',HERE/'RECOGNITION-EXPECTED-PACK-METADATA-v1.json'),('contract',HERE/'RECOGNITION-EXECUTION-CONTRACT-v1.json'),('wire',HERE/'RECOGNITION-CHILD-WIRE-v2.json'),
        ('validator',VALIDATOR),('child_source',HERE/'typed_public_c_recognizer_recognition_v2.cpp')]},
    helper=pin(Path(__file__)),partial_rows=len(rows),event_counts=dict(collections.Counter(r.get('event','<failure_frame>') for r in rows)),
    individual_case_body_checks=dict(count=189,groups={str(k):dict(value) for k,value in groups.items()},basis='Whole-body strict type/field comparison to frozen metadata and observed EOG vector; bounded rejection spans; source acknowledgment schedule. Original document content was not reread here.',
        cases=all_case_bodies),prefix_checks=prefixes,observed_vocabulary_count=nv,observed_EOG_ids=eog,
    strict_success_validator=dict(executed_in_this_review=False,reason='The independent actual-result verifier owns the one separately authorized pack read. This report does not duplicate it.',
        source_derived_first_required_unavailable_row_index=first_unavailable,expected_stop_after_case='primary/110',
        distinction='Strict sequential acceptance cannot reach later rows after the first unavailable prefix. The189 individual body checks above are separate bounded negative evidence, not189 success-validator accepted results.'),
    source_reported_final_progress=state,source_reported_explicit_API_counts=counter,
    missing_native_prefix_experiments=2,positive_profile_requires_samplers=190,source_reported_samplers=188,
    source_failure_order=dict(after_all_cases_and_slots=True,source_lines='typed_public_c_recognizer_recognition_v2.cpp:673-681',
        unavailable_branch_sets_flag_and_continues=True,final_unavailable_guard_throws=True,
        normal_batch_and_completion_absent=True,RAII_cleanup_runs_on_unwind_before_failure_publication=True),
    parent_observations=dict(status=parent['status'],returncode=parent['returncode'],reaped=parent['reaped'],
        child_full_process_elapsed_seconds=parent['child_full_process_elapsed_seconds'],elapsed_before_early_receipt_seconds=parent['elapsed_before_early_receipt_seconds'],
        partial_coverage=parent['partial_coverage'],terminal_observation_complete=parent['terminal_observation']['complete'],captures=parent['captures']),
    limits=['No original token-piece sequence, per-token offsets or token-merging histogram was retained, so exact unavailable-boundary cause and availability in other documents are unknown.',
        'All25 counter pairs are bounded/monotone and report no outstanding explicit call at the final snapshot. This is source-instrumented bridge accounting, not proof about uninstrumented library internals or all OS effects.',
        'The killed-tail scope remains unknown_since_last_acknowledged_snapshot; a truthful final recorded return snapshot does not change that frozen policy.',
        'Four successful fixed prefixes all report partial_UTF8_at_cut=false; they do not replace either unavailable natural partial-UTF8 experiment.',
        'No batch/completion/footer or independent full conformance exists. The failed experiment stays failed; no repeat, repaired corpus or substitute prefix is authorized.'],
    singleton_conformance=False,full_vocabulary_mask_conformance=False,scientific_validation='not_established',execution_authorized=False,
    activity=dict(native_API_calls=0,CPU_GGUF_pack_path_operations=0,original_artifact_edits=0,denied_operations=ACTIVITY),
    elapsed_seconds=time.monotonic()-START)
need(not REPORT.exists() and not NOTE.exists(),'Preserve previous audit')
with REPORT.open('x',encoding='utf-8') as out:json.dump(result,out,sort_keys=True,indent=2);out.write('\n')
text=f'''# Failed singleton recognition: retained coverage reconstruction

This is an AI engineering data review, not a new native run or a scientist review. The [retained JSON audit]({REPORT.name}) records its exact metadata, source and child artifact hashes. No CPU, model or frozen pack path was inspected.

The experiment remains **failed**: `required_partial_UTF8_prefix_coverage_unavailable`. Its partial file contains400rows:15setup/stage rows,189before-case rows,189case results,6prefix results and1failure frame. There is no `recognition_batch_returned`, normal completion or finalized result.

All189retained case bodies independently match their frozen metadata identities, declared layer/outcome and exact expected observed-body shape: primary167 =44native members +122token rejections +1raw-NUL harness disposition; authored18 =18members; guard4 =2UTF8 +2NUL harness rejections. This is bounded source-linked negative evidence; it does not mean the strict success validator accepted189results. Original document contents were not rehashed in this review.

Four fixed prefixes report all ordinary tokens admitted and all6EOG IDs rejected. All four report `partial_UTF8_at_cut=false`. The required natural astral slot (`primary/110`) and natural BMP slot (`primary/127`) report **coverage unavailable**, with null membership. The source continues after each unavailable slot and throws only after all189cases and6slots have been visited. It does not replace the missing experiment with a nearby boundary.

The strict success-validator source stops at the first unavailable row, ordinal239 after `primary/110`; its exact accepted subset is independently reported by the actual-result verifier, which owns the pack read. Later individually checked bodies remain a separate evidence class. Missing token-piece/offset traces prevent a claim about exact merges or availability elsewhere.

All400accounting frames pass strict types, cap, total and monotonic checks in negative-observation mode. The compute/write acknowledgment schedule reconstructs189case results and6prefix rows. The final source snapshot reports442,668explicit attempts and returns,188samplers created/freed, zero owned or unknown samplers, and returned model/backend cleanup. The positive profile would need190samplers:2natural-prefix experiments never ran. These are bounded bridge instrumentation claims, with the original unknown-tail policy unchanged.

The original parent records exit2/reaped, child full-process{parent['child_full_process_elapsed_seconds']:.3f}s, early-receipt elapsed{parent['elapsed_before_early_receipt_seconds']:.3f}s, complete negative terminal observations and both capture EOFs. Its own partial-coverage status remains `not_inspected_unknown`; this new audit does not rewrite it.

No singleton/full-mask conformance, biological validity, numerical feature or clinical probability is established. No rerun, corpus repair, new prefix or asset access is authorized by this review.
'''
with NOTE.open('x',encoding='utf-8',newline='\n') as out:out.write(text)
print(json.dumps(dict(status=result['status'],report=pin(REPORT),note=pin(NOTE),individual_case_body_checks=189,prefixes_available=4,prefixes_unavailable=2,payload_path_operations=0)))
