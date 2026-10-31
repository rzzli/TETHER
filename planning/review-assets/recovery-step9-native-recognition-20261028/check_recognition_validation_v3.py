"""Synthetic strict-wire/parser tests. Pack bytes are data; no native/model API."""
import copy
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import time
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'recognition_validation_v3.py'
REPORT=HERE/'RECOGNITION-VALIDATION-PURE-PROOF-v3.json'
CONTRACT=HERE/'RECOGNITION-EXECUTION-CONTRACT-v1.json'
MANIFEST=HERE/'RECOGNITION-EXPECTED-PACK-METADATA-v1.json'
WIRE=HERE/'RECOGNITION-CHILD-WIRE-v2.json'
DENIED=[]
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        DENIED.append(event);raise AssertionError('No native operation in synthetic parser checks')
    if event=='open' and args and isinstance(args[0],(str,bytes)) and str(args[0]).lower().endswith(('.gguf','.dll','.pyd')):
        DENIED.append('payload_open');raise AssertionError('No CPU/GGUF/binary payload')
sys.addaudithook(guard)
def load(name,path):
    spec=util.spec_from_file_location(name,path);module=util.module_from_spec(spec);spec.loader.exec_module(module);return module
h=load('pure_recognition_result_validator',SOURCE)
policy=load('pure_recognition_phase_matcher',HERE/'recognition_module_policy_v1.py')
contract=json.loads(CONTRACT.read_text(encoding='utf-8'));manifest=json.loads(MANIFEST.read_text(encoding='utf-8'));wire=json.loads(WIRE.read_text(encoding='utf-8'))
PACK_RAW=Path(manifest['pack']['path']).read_bytes()  # Already qualified small fixture pack; never a model or human/outcome artifact.
DOCUMENTS=h.decode_pack(PACK_RAW,manifest)
CONTEXT=dict(expected_self=r'D:\qualified\recognition\bridge.exe',expected_runtime=r'D:\qualified\recognition\runtime')

def modeled_rows():
    """Independent byte-token model, never claimed to be the real tokenizer/native output."""
    caps=contract['native_call_policy']['per_API_caps'];counts={k:dict(attempted=0,returned=0) for k in caps}
    rows=[];case=-1;computed=written=prefix_seen=prefix_written=token_work=0;groups=[0,0,0];writes=[0,0,0];nv=512;eog=[511]
    EOG_examined=0;last_tokenize=last_piece=0;last_apply_kind=0
    def bump(name,n=1):counts[name]['attempted']+=n;counts[name]['returned']+=n
    def native_modules(phase):
        names=policy.SEMANTICS['phases'][phase]['required_native_names']
        return [dict(name='bridge.exe',path=CONTEXT['expected_self']),*[dict(name=n,path=CONTEXT['expected_runtime']+'\\'+n) for n in names],dict(name='apphelp.dll',path=r'C:\Windows\System32\apphelp.dll')]
    def module_fields(phase):return dict(module_policy_id=policy.POLICY_ID,module_policy_sha256=policy.POLICY_SHA256,module_policy_phase=phase,modules=native_modules(phase))
    def emit(event,**body):
        state={}
        for key,kind in wire['native_state_fields'].items():
            state[key]=False if kind=='bool' else [0,0,0] if kind.startswith('three ') else None if kind=='API name|null' else 0
        n=sum(v['returned'] for v in counts.values());applied=counts['llama_sampler_apply']['returned']>0
        state.update(total_attempted=n,total_returned=n,last_attempt='llama_sampler_free' if counts['llama_sampler_free']['returned'] else 'llama_version' if n else None,
            last_return='llama_sampler_free' if counts['llama_sampler_free']['returned'] else 'llama_version' if n else None,last_return_kind=1 if n else 0,
            last_tokenize_return=last_tokenize,last_piece_return=last_piece,last_apply_return_observed=applied,last_apply_shape_valid=applied,
            last_apply_logit_kind=last_apply_kind,last_EOG_id=nv-1 if EOG_examined else -1,last_EOG_returned=EOG_examined>0,last_EOG_value=EOG_examined>0,
            cpu_load_return_observed=counts['ggml_backend_load']['returned']==1,cpu_registry_nonnull=counts['ggml_backend_load']['returned']==1,
            backend_init_return_observed=counts['llama_backend_init']['returned']==1,backend_owned=counts['llama_backend_init']['returned']==1 and not counts['llama_backend_free']['attempted'],
            model_load_return_observed=counts['llama_model_load_from_splits']['returned']==1,model_return_nonnull=counts['llama_model_load_from_splits']['returned']==1,
            model_owned=counts['llama_model_load_from_splits']['returned']==1 and not counts['llama_model_free']['attempted'],
            model_free_attempted=bool(counts['llama_model_free']['attempted']),model_free_return_observed=bool(counts['llama_model_free']['returned']),
            backend_free_attempted=bool(counts['llama_backend_free']['attempted']),backend_free_return_observed=bool(counts['llama_backend_free']['returned']),
            sampler_nonnull_returns=counts['llama_sampler_init_grammar']['returned'],sampler_free_returned_nonnull=counts['llama_sampler_free']['returned'],
            token_work_reserved=token_work,cases_computed=computed,case_results_written=written,prefix_slots_seen=prefix_seen,prefix_results_written=prefix_written,
            EOG_ids_examined=EOG_examined,current_case_index=case,current_prefix_slot=prefix_seen-1,group_computed=list(groups),group_results_written=list(writes))
        rows.append(dict(event=event,**body,native_call_contract_sha256=h.CONTRACT_SHA,native_call_counters=copy.deepcopy(counts),
            native_call_scope='explicit_bridge_export_calls_only',unrecorded_killed_tail='unknown_since_last_acknowledged_snapshot',native_state=state))
    def observation(member):
        return dict(status='native_member' if member else 'native_eog_rejection',all_input_tokens_admitted=True,
            first_rejected_token_index=None,completion_EOG=[dict(id=i,admitted=member) for i in eog],first_rejected_byte_start=None,first_rejected_byte_end=None)
    emit('before_explicit_required_OpenMP_dependency_load',dependency_native_initialization_possible=True)
    emit('exact_core_modules_loaded_exports_resolved',layouts=contract['expected_layouts'],**module_fields('pre_cpu'))
    bump('llama_version');bump('llama_model_default_params')
    emit('typed_version_and_defaults_observed',version='0.7.0-dev',defaults=contract['expected_defaults'],no_backend_or_model_call_so_far=True)
    emit('pack_verified_before_backend_or_model',pack_sha256=manifest['pack']['sha256'],cases=189,prefixes=6)
    for index,shard in enumerate(contract['ordered_shard_descriptors']):
        emit('before_exact_shard_hash',index=index,path=shard['path'],expected_bytes=shard['bytes'])
        emit('exact_shard_hash_returned',index=index,bytes=shard['bytes'],sha256=shard['sha256'])
    emit('three_exact_shards_hash_verified_and_read_leased',weight_file_hash_reads=True,tensor_weight_allocation_claim=False)
    for api in ('ggml_backend_load','ggml_backend_reg_count','ggml_backend_reg_get','ggml_backend_reg_name','ggml_backend_dev_count','ggml_backend_dev_get','ggml_backend_dev_type','ggml_backend_dev_name'):bump(api)
    bump('ggml_backend_reg_dev_count',2);bump('ggml_backend_reg_dev_get',2)
    emit('cpu_registry_verified_before_llama_backend_init',registry_count=1,device_count=1,registry_name='CPU',device_name='CPU',**module_fields('post_cpu'))
    bump('llama_backend_init')
    for api in caps:
        if api.startswith('ggml_') and api!='ggml_backend_load':counts[api]=dict(attempted=caps[api],returned=caps[api])
    emit('backend_init_returned_exact_CPU_identity_rechecked',**module_fields('post_cpu'))
    emit('before_model_load_from_three_explicit_splits',effective_params=contract['effective_params'],empty_devices_array_nonnull=True,cooperative_deadline_not_interruptible_native_call=True)
    for api in ('llama_model_load_from_splits','llama_model_get_vocab','llama_vocab_n_tokens'):bump(api)
    bump('llama_vocab_is_eog',nv);EOG_examined=nv
    emit('all_vocabulary_ids_EOG_enumerated',vocabulary_count=nv,EOG_ids=eog,EOG_JSON_sha256=hashlib.sha256(json.dumps(eog,separators=(',',':')).encode()).hexdigest(),**module_fields('post_cpu'))
    for index,expected in enumerate(manifest['cases']):
        case=index;raw=DOCUMENTS[index];kind=expected['expected_kind'];group=expected['source_group']
        emit('before_case',case_index=index,id=expected['id'],document_sha256=expected['sha256'])
        tokens=0 if kind>=2 else len(raw)
        if kind<2:
            bump('llama_tokenize',1 if tokens<=1 else 2);last_tokenize=tokens
            bump('llama_token_to_piece',tokens);last_piece=1 if tokens else last_piece
            bump('llama_sampler_init_grammar');bump('llama_sampler_accept',tokens);bump('llama_sampler_apply',tokens+len(eog));bump('llama_sampler_free')
            last_apply_kind=2 if kind==1 else 1
        token_work+=tokens;computed+=1;groups[group]+=1
        fields=dict(status='harness_utf8_rejection' if kind==2 else 'harness_raw_nul_rejection',native_membership=None,completion_EOG=None) if kind>=2 else observation(kind==1)
        emit('case_result',case_index=index,source_group=group,id=expected['id'],bytes=len(raw),document_sha256=expected['sha256'],tokens=tokens,
            used_piece_NUL_seen=False,first_NUL_piece_index=None,first_NUL_offset_in_piece=None,expected_kind=kind,expected_native_membership=expected['expected_native_membership'],matches_expected=True,**fields)
        written+=1;writes[group]+=1
        for prefix in manifest['prefixes']:
            if prefix['base_case_index']!=index:continue
            prefix_seen+=1;cut=prefix['cut']
            if prefix['kind']:
                for cut in range(1,len(raw)):
                    if raw[cut]&0xc0!=0x80:continue
                    start=cut
                    while start>0 and raw[start]&0xc0==0x80:start-=1
                    width=2 if raw[start]<0xe0 else 3 if raw[start]<0xf0 else 4
                    if width in ((2,3) if prefix['kind']==1 else (4,)):break
                else:raise AssertionError('Frozen natural prefix unavailable in synthetic byte-token model')
            count=cut
            if prefix['kind']==0:
                bump('llama_tokenize',1 if count<=1 else 2);last_tokenize=count
                bump('llama_token_to_piece',count);last_piece=1 if count else last_piece
            bump('llama_sampler_init_grammar');bump('llama_sampler_accept',count);bump('llama_sampler_apply',count+len(eog));bump('llama_sampler_free');last_apply_kind=1
            token_work+=count
            emit('prefix_result',id=prefix['id'],base_id=expected['id'],prefix_kind=prefix['kind'],byte_cut=cut,token_count=count,
                prefix_sha256=hashlib.sha256(raw[:cut]).hexdigest(),partial_UTF8_at_cut=0<cut<len(raw) and raw[cut]&0xc0==0x80,
                last_piece_complete_codepoints_before_partial=False,matches_expected=True,**observation(False))
            prefix_written+=1
    bump('llama_model_free');bump('llama_backend_free')
    emit('recognition_batch_returned',pack_format_version=2,cases_completed=189,source_group_completed=dict(primary_frozen_wire=167,new_serialization_of_retained_authored_abstention=18,harness_byte_guards=4),
        primary_native_results=166,primary_harness_dispositions=1,new_authored_native_results=18,independent_guard_dispositions=4,prefix_slots=6,
        total_token_budget_used=token_work,tokenize_calls=counts['llama_tokenize']['returned'],piece_calls=counts['llama_token_to_piece']['returned'],
        apply_calls=counts['llama_sampler_apply']['returned'],accept_calls=counts['llama_sampler_accept']['returned'],EOG_accept_calls=0,
        samplers_freed_before_model=True,model_freed=True,backend_free_returned=True,scientific_validation='not_established',**module_fields('post_cpu'))
    emit('child_normal_completion',mode='--recognize',elapsed_ms=10,parent_qualification_required=True)
    return rows

BASE=modeled_rows()
def validate(rows):return h.validate_rows(rows,contract=contract,manifest=manifest,documents=DOCUMENTS,wire=wire,match_modules=policy.match_modules,**CONTEXT)
def first(event):return next(i for i,row in enumerate(BASE) if row['event']==event)
MUTATIONS=[]
def rejected(label,rows):
    try:validate(rows)
    except h.RecognitionValidationError as error:MUTATIONS.append(dict(id=label,error=str(error),coverage=error.coverage));return error
    raise AssertionError('Parser accepted '+label)

class Checks(unittest.TestCase):
    def test_rejected_rows_do_not_commit_native_or_harness_layer_coverage(self):
        for native,key in [(True,'native_case_results_validated'),(False,'harness_dispositions_validated')]:
            rows=copy.deepcopy(BASE)
            row=next(r for r in rows if r['event']=='case_result' and (r['expected_kind']<2 if native else r['expected_kind']>=2))
            row['id']='wrong-id-with-valid-accounting'
            error=rejected('uncommitted-layer-'+key,rows);self.assertEqual(error.coverage[key],0)
    def test_self_consistent_early_CPU_backend_model_calls_violate_fixed_stage(self):
        flags={'ggml_backend_load':('cpu_load_return_observed','cpu_registry_nonnull'),
            'llama_backend_init':('backend_init_return_observed','backend_owned'),
            'llama_model_load_from_splits':('model_load_return_observed','model_return_nonnull','model_owned')}
        ends={'ggml_backend_load':'cpu_registry_verified_before_llama_backend_init',
            'llama_backend_init':'backend_init_returned_exact_CPU_identity_rechecked','llama_model_load_from_splits':'all_vocabulary_ids_EOG_enumerated'}
        for api,end in ends.items():
            rows=copy.deepcopy(BASE)
            for row in rows[first('typed_version_and_defaults_observed'):first(end)]:
                row['native_call_counters'][api]['attempted']+=1;row['native_call_counters'][api]['returned']+=1
                row['native_state']['total_attempted']+=1;row['native_state']['total_returned']+=1
                for key in flags[api]:row['native_state'][key]=True
            error=rejected('early-stage-'+api,rows);self.assertIn('stage schedule',str(error))
    def test_rejected_case_frame_never_advances_last_observed_computation_claim(self):
        i=first('case_result')
        for mode in ('missing_snapshot','pending_snapshot','wrong_event'):
            rows=copy.deepcopy(BASE)
            if mode=='missing_snapshot':del rows[i]['native_state']
            elif mode=='pending_snapshot':rows[i]['native_call_counters']['llama_tokenize']['attempted']+=1
            else:rows[i]['event']='wrong_event_with_tokens'
            error=rejected('last-observed-'+mode,rows)
            self.assertEqual(error.coverage['case_results_validated'],0)
            self.assertEqual(error.coverage['last_observed_cases_computed_claim'],0)
            self.assertEqual(error.coverage['last_observed_case_results_written_claim'],0)
        error=rejected('no-accounting-frame',[])
        self.assertIsNone(error.coverage['last_observed_cases_computed_claim'])
    def test_independent_pack_decode_preserves_all_original_groups_and_NUL(self):
        self.assertEqual(len(DOCUMENTS),189);self.assertEqual(DOCUMENTS[161].find(b'\0'),169)
        self.assertEqual([len([c for c in manifest['cases'] if c['source_group']==g]) for g in range(3)],[167,18,4])
        self.assertEqual(manifest['cases'][161]['expected_kind'],3);self.assertIsNone(manifest['cases'][161]['expected_native_membership'])
    def test_all401_synthetic_frames_pass_without_native_claim(self):
        self.assertEqual(len(BASE),401);result=validate(BASE)
        self.assertEqual([result[k] for k in ('case_results','primary_native_results','primary_harness_dispositions','new_authored_native_results','independent_guard_dispositions','prefix_results')],[189,166,1,18,4,6])
        self.assertFalse(result['full_vocabulary_mask_qualified']);self.assertEqual(result['scientific_validation'],'not_established')
    def test_phase_missing_CPU_wrong_directory_and_forged_flags_reject(self):
        for event in ('exact_core_modules_loaded_exports_resolved','cpu_registry_verified_before_llama_backend_init'):
            rows=copy.deepcopy(BASE);rows[first(event)]['module_policy_phase']='post_cpu' if event.startswith('exact') else 'pre_cpu';rejected('wrongphase-'+event,rows)
        i=first('cpu_registry_verified_before_llama_backend_init')
        for mode in ('missing','wrongdir','verifiedflag','duplicate'):
            rows=copy.deepcopy(BASE);mods=rows[i]['modules'];cpu=next(m for m in mods if m['name']=='ggml-cpu-x64.dll')
            if mode=='missing':mods.remove(cpu)
            elif mode=='wrongdir':cpu['path']=r'C:\Windows\System32\ggml-cpu-x64.dll'
            elif mode=='verifiedflag':cpu['verified']=True
            else:mods.append(copy.deepcopy(cpu))
            rejected('CPU-'+mode,rows)
    def test_missing_duplicate_and_unavailable_coverage_is_unqualified(self):
        for event in ('case_result','prefix_result'):
            i=first(event);rows=copy.deepcopy(BASE);del rows[i];error=rejected('missing-'+event,rows)
            self.assertFalse(error.coverage['complete'])
            rows=copy.deepcopy(BASE);rows.insert(i,copy.deepcopy(rows[i]));rejected('duplicate-'+event,rows)
        rows=copy.deepcopy(BASE);rows[first('prefix_result')]['status']='coverage_unavailable';rejected('prefix-unavailable',rows)
        rows=copy.deepcopy(BASE[:first('case_result')]);error=rejected('partial-tail',rows);self.assertGreater(error.coverage['missing_case_results'],0)
    def test_counter_caps_pending_types_monotonic_and_ownership_cannot_pass(self):
        i=first('case_result')
        for name in ('pending','bool','decrease','owner','exceptions'):
            rows=copy.deepcopy(BASE)
            if name=='pending':rows[i]['native_call_counters']['llama_tokenize']['attempted']+=1
            elif name=='bool':rows[i]['native_call_counters']['llama_tokenize']['returned']=True
            elif name=='decrease':rows[i]['native_call_counters']['llama_version']=dict(attempted=0,returned=0)
            elif name=='owner':rows[i]['native_state']['model_owned']=False
            else:rows[i]['native_state']['exceptions']=1
            rejected('counter-'+name,rows)
    def test_EOG_completeness_identity_types_and_native_guard_layers(self):
        i=first('all_vocabulary_ids_EOG_enumerated')
        for value in ([],[511,511],[True],[512]):
            rows=copy.deepcopy(BASE);rows[i]['EOG_ids']=value;rejected('EOG-'+repr(value),rows)
        rows=copy.deepcopy(BASE);rows[first('case_result')]['completion_EOG']=[];rejected('missing-terminal-EOG',rows)
        i=next(i for i,r in enumerate(BASE) if r['event']=='case_result' and r['case_index']==161)
        rows=copy.deepcopy(BASE);rows[i]['expected_native_membership']=False;rejected('NUL-not-native-negative',rows)
    def test_prefix_bytes_and_ordinary_token_admission_are_checked(self):
        i=first('prefix_result')
        for name in ('cut','sha','tokens','native-token-reject'):
            rows=copy.deepcopy(BASE)
            if name=='cut':rows[i]['byte_cut']+=1
            elif name=='sha':rows[i]['prefix_sha256']='0'*64
            elif name=='tokens':rows[i]['all_input_tokens_admitted']=False
            else:rows[i].update(status='native_token_rejection',all_input_tokens_admitted=False,completion_EOG=None,first_rejected_token_index=0,first_rejected_byte_start=0,first_rejected_byte_end=1)
            rejected('prefix-'+name,rows)
    def test_semantic_apply_contribution_tamper_with_repaired_totals_rejects(self):
        rows=copy.deepcopy(BASE);start=first('recognition_batch_returned')
        for row in rows[start:]:
            pair=row['native_call_counters']['llama_sampler_apply'];pair['attempted']+=1;pair['returned']+=1
            row['native_state']['total_attempted']+=1;row['native_state']['total_returned']+=1
            if row['event']=='recognition_batch_returned':row['apply_calls']+=1
        error=rejected('selfconsistent-extra-apply',rows);self.assertIn('contributions',str(error))
    def test_model_defaults_hash_order_and_strict_JSON(self):
        for event,key,value in [('before_model_load_from_three_explicit_splits','empty_devices_array_nonnull',False),
            ('exact_shard_hash_returned','bytes',1),('typed_version_and_defaults_observed','version','wrong')]:
            rows=copy.deepcopy(BASE);rows[first(event)][key]=value;rejected('stage-'+key,rows)
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}'):
            with self.assertRaises(h.RecognitionValidationError):h.json_value(raw)
        with self.assertRaises(UnicodeError):h.json_value('{"a":1}'.encode('utf-16'))

def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
    assert not REPORT.exists();original=pin(SOURCE);started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks));assert pin(SOURCE)==original
    value=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[dict(test=str(c),trace=t) for c,t in result.errors],source=original,checker=pin(Path(__file__)),
        contract=pin(CONTRACT),manifest=pin(MANIFEST),wire=pin(WIRE),module_policy=pin(HERE/'recognition_module_policy_v1.py'),
        before_regression=pin(HERE/'RECOGNITION-COVERAGE-REGRESSION-BEFORE-v2.json'),
        stage_layer_before_regression=pin(HERE/'RECOGNITION-STAGE-LAYER-REGRESSION-BEFORE-v3b.json'),
        frozen_pack=manifest['pack'],synthetic_frames=len(BASE),mutation_cases=MUTATIONS,elapsed_seconds=time.monotonic()-started,
        activity=dict(CPU_binary_reads=0,GGUF_reads=0,SDK_constructors=0,native_calls=0,children=0,compiler_calls=0,qualified_small_pack_data_reads=1),
        denied_real_operations=DENIED,scope='Synthetic byte-token modeled wire and strict deterministic consistency only; never actual tokenizer/native vocabulary, model quality or scientific validation')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(REPORT),mutations=len(MUTATIONS))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
