"""Strict data-only singleton recognition result validation; no native APIs.

Context, contracts, wire schema and pack bytes must come from the qualified
parent's exact original-path authority. Child fields never grant authority.
"""
import hashlib
import json
import struct

AUGMENT={'native_call_contract_sha256','native_call_counters','native_call_scope','unrecorded_killed_tail','native_state'}
CONTRACT_SHA='30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861'
POLICY_ID='trusted-System32-recognition-v1'
POLICY_SHA='4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713'

class RecognitionValidationError(ValueError):
    def __init__(self,message,coverage=None):
        super().__init__(message);self.coverage=coverage or dict(status='unqualified_unknown',complete=False)

def need(value,message):
    if not value:raise RecognitionValidationError(message)

def exact(actual,expected):
    if type(actual) is not type(expected):return False
    if type(expected) is dict:return set(actual)==set(expected) and all(exact(actual[k],v) for k,v in expected.items())
    if type(expected) is list:return len(actual)==len(expected) and all(exact(a,b) for a,b in zip(actual,expected))
    return actual==expected

def uint(value,maximum):return type(value) is int and 0<=value<=maximum

def json_value(raw):
    def pairs(items):
        out={}
        for key,value in items:need(key not in out,'Duplicate result JSON key');out[key]=value
        return out
    if type(raw) is bytes:raw=raw.decode('utf-8','strict')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(RecognitionValidationError('Nonfinite result JSON')))

def decode_pack(raw,manifest):
    """Independently decode bounded immutable pack; never repair/reserialize wires."""
    need(type(raw) is bytes and len(raw)==manifest['pack']['bytes'] and len(raw)<=20*1024**2,'Exact pack size')
    need(hashlib.sha256(raw).hexdigest()==manifest['pack']['sha256'],'Exact pack hash')
    at=0
    def take(n):
        nonlocal at
        need(type(n) is int and 0<=n<=len(raw)-at,'Pack truncated');out=raw[at:at+n];at+=n;return out
    def u32():return struct.unpack('<I',take(4))[0]
    def span(cap):
        n=u32();need(n<=cap,'Pack span cap');return take(n)
    def ident():
        value=span(256);need(value and all(32<=b<=126 for b in value),'Pack ASCII identifier');return value.decode('ascii')
    need(take(8)==b'R09NC02\0' and u32()==2,'Pack magic/version')
    ng,nc,np=u32(),u32(),u32();need((ng,nc,np)==(4,189,6),'Frozen pack counts')
    grammars=[]
    for expected in manifest['grammars']:
        name,sha,text=ident(),take(32).hex(),span(65536)
        need(exact(dict(id=name,sha256=sha),expected) and text and b'\0' not in text and hashlib.sha256(text).hexdigest()==sha,'Grammar bytes/identity')
        text.decode('utf-8','strict');grammars.append(text)
    documents=[]
    for expected in manifest['cases']:
        name,group,index,kind,sha,text=ident(),u32(),u32(),u32(),take(32).hex(),span(65536)
        need(exact([name,group,index,kind,sha,len(text)],[expected['id'],expected['source_group'],expected['grammar_index'],expected['expected_kind'],expected['sha256'],expected['bytes']]),'Case pack/metadata binding')
        need(hashlib.sha256(text).hexdigest()==sha,'Original document hash');documents.append(text)
    for expected in manifest['prefixes']:
        name,index,kind,cut,sha=ident(),u32(),u32(),u32(),take(32).hex()
        need(exact([name,index,kind,cut,sha],[expected['id'],expected['base_case_index'],expected['kind'],expected['cut'],expected['sha256']]),'Prefix pack/metadata binding')
    need(at==len(raw),'Trailing pack bytes')
    return documents

def counter_frame(row,contract,wire,previous=None,*,allow_pending=False):
    need(type(row) is dict and AUGMENT<=set(row),'Missing native accounting snapshot')
    need(row['native_call_contract_sha256']==CONTRACT_SHA and type(row['native_call_contract_sha256']) is str,'Native call contract fingerprint')
    need(row['native_call_scope']=='explicit_bridge_export_calls_only' and row['unrecorded_killed_tail']=='unknown_since_last_acknowledged_snapshot','Native call/tail scope')
    caps=contract['native_call_policy']['per_API_caps'];counters=row['native_call_counters'];state=row['native_state']
    need(type(counters) is dict and set(counters)==set(caps),'Exactly25 native API counters')
    for api,cap in caps.items():
        pair=counters[api];need(type(pair) is dict and set(pair)=={'attempted','returned'},'Exact attempted/returned shape')
        need(uint(pair['attempted'],cap) and uint(pair['returned'],pair['attempted']),'Native API cap/type')
        if not allow_pending:need(pair['attempted']==pair['returned'],'Unknown/unreturned native API cannot qualify')
        if previous:
            need(pair['attempted']>=previous[api]['attempted'] and pair['returned']>=previous[api]['returned'],'Native counters decreased')
    total=sum(v['attempted'] for v in counters.values());returned=sum(v['returned'] for v in counters.values())
    need(total<=contract['native_call_policy']['aggregate_attempt_cap'],'Aggregate native attempt cap')
    fields=wire['native_state_fields'];need(type(state) is dict and set(state)==set(fields),'Exact native state fields')
    for key,kind in fields.items():
        value=state[key]
        if kind=='bool':need(type(value) is bool,'Native bool type: '+key)
        elif kind=='nonnegative integer':need(uint(value,2**63-1),'Native nonnegative type: '+key)
        elif kind=='signed integer':need(type(value) is int and -2**63<=value<2**63,'Native signed type: '+key)
        elif kind=='API name|null':need(value is None or type(value) is str and value in caps,'Last API identity')
        elif kind.startswith('three '):need(type(value) is list and len(value)==3 and all(uint(v,200) for v in value),'Native group counters')
        elif key=='last_return_kind':need(uint(value,4),'Native return-kind enum')
        elif key=='last_apply_logit_kind':need(uint(value,3),'Native logit-kind enum')
        else:need(False,'Unknown trusted wire state type')
    need(state['total_attempted']==total and state['total_returned']==returned,'Native accounting totals differ')
    if not allow_pending:
        need(state['exceptions']==0 and not state['cleanup_failed'] and not state['model_release_unknown'] and not state['backend_release_unknown']
            and state['sampler_release_unknown']==0 and state['samplers_owned']==0,'Native exceptions/unknown ownership cannot qualify')
        need(not state['required_UTF8_prefix_unavailable'],'Required UTF8 prefix unavailable')
        applied=counters['llama_sampler_apply']['returned']>0
        need(state['last_apply_return_observed'] is applied,'Apply return observation/counter differs')
        if applied:need(state['last_apply_shape_valid'] and state['last_apply_logit_kind'] in (1,2),'Unexpected native candidate result')
        flags={'cpu_load_return_observed':'ggml_backend_load','backend_init_return_observed':'llama_backend_init',
            'model_load_return_observed':'llama_model_load_from_splits','model_free_attempted':'llama_model_free',
            'model_free_return_observed':'llama_model_free','backend_free_attempted':'llama_backend_free','backend_free_return_observed':'llama_backend_free'}
        for flag,api in flags.items():
            key='attempted' if flag.endswith('_attempted') else 'returned'
            need(state[flag] is (counters[api][key]==1),'Native ownership/call observation differs: '+flag)
        need(state['cpu_registry_nonnull'] is state['cpu_load_return_observed'] and state['model_return_nonnull'] is state['model_load_return_observed'],'Null native return cannot qualify')
        need(state['backend_owned'] is (state['backend_init_return_observed'] and not state['backend_free_attempted'])
            and state['model_owned'] is (state['model_load_return_observed'] and not state['model_free_attempted']),'Native actionable ownership differs')
    return counters,state

class Ledger:
    def __init__(self,rows,contract,manifest,documents,wire,match_modules,expected_self,expected_runtime,check):
        self.rows,self.contract,self.manifest,self.documents,self.wire=rows,contract,manifest,documents,wire
        self.matcher,self.self_path,self.runtime,self.check=match_modules,expected_self,expected_runtime,check
        self.at=0;self.previous=None;self.current_case=-1;self.computed=self.written=self.prefix_seen=self.prefix_written=0
        self.groups=[0,0,0];self.group_writes=[0,0,0];self.token_work=0;self.sampler_states=0;self.eog_examined=0
        self.eog=[];self.nv=None;self.native=0;self.harness=0;self.token_rejections=0;self.eog_states=0
        self.accepts=0;self.tokenize=0;self.piece_tokens=0;self.modules=[]
    def coverage(self):
        return dict(status='unqualified_incomplete_or_invalid',complete=False,frames_validated=self.at,
            expected_cases=189,cases_computed_claims_validated=self.computed,case_results_validated=self.written,
            case_group_results_validated=list(self.group_writes),prefix_results_validated=self.prefix_written,expected_prefixes=6,
            native_case_results_validated=self.native,harness_dispositions_validated=self.harness,
            missing_case_results=189-self.written,missing_prefix_results=6-self.prefix_written,
            unrecorded_tail='unknown_since_last_acknowledged_snapshot')
    def fail(self,message):raise RecognitionValidationError(message,self.coverage())
    def req(self,value,message):
        if not value:self.fail(message)
    def frame(self,event):
        self.check();self.req(self.at<len(self.rows),'Required result frame missing: '+event)
        row=self.rows[self.at];self.req(type(row) is dict and row.get('event')==event,'Exact recognition event order: '+event)
        try:counters,state=counter_frame(row,self.contract,self.wire,self.previous)
        except RecognitionValidationError as error:self.fail(str(error))
        self.req(exact([state['cases_computed'],state['case_results_written'],state['prefix_slots_seen'],state['prefix_results_written']],
            [self.computed,self.written,self.prefix_seen,self.prefix_written]),'Cross-frame progress/write acknowledgment differs')
        self.req(exact(state['group_computed'],self.groups) and exact(state['group_results_written'],self.group_writes),'Group progress differs')
        self.req(state['current_case_index']==self.current_case and state['current_prefix_slot']==self.prefix_seen-1,'Current case/prefix index differs')
        self.req(state['token_work_reserved']==self.token_work and self.token_work<=1000000,'Token-work ledger differs')
        self.req(state['EOG_ids_examined']==self.eog_examined,'Vocabulary enumeration progress differs')
        self.req(state['sampler_nonnull_returns']==state['sampler_free_returned_nonnull']==self.sampler_states,'Sampler ownership/progress differs')
        self.req(counters['llama_sampler_init_grammar']['returned']==counters['llama_sampler_free']['returned']==self.sampler_states,'Sampler return counters differ')
        self.previous=counters;self.at+=1;self.check()
        return {k:v for k,v in row.items() if k not in AUGMENT},state
    def equals(self,actual,expected,message):self.req(exact(actual,expected),message)
    def module(self,body,phase):
        self.req(body.get('module_policy_id')==POLICY_ID and body.get('module_policy_sha256')==POLICY_SHA
            and body.get('module_policy_phase')==phase,'Expected event selects module phase; child cannot select it')
        try:classified=self.matcher(body['modules'],expected_self=self.self_path,expected_runtime=self.runtime,phase=phase)
        except (ValueError,KeyError) as error:self.fail('Module report policy: '+str(error))
        self.modules.append(classified)
        return {k:v for k,v in body.items() if k not in {'module_policy_id','module_policy_sha256','module_policy_phase','modules'}}
    def EOG(self,value,admitted):
        self.req(type(value) is list and len(value)==len(self.eog),'Complete EOG vector required')
        self.equals(value,[dict(id=i,admitted=admitted) for i in self.eog],'EOG IDs/boolean results differ')
    def observation(self,body,tokens,byte_count,expected):
        keys={'status','all_input_tokens_admitted','first_rejected_token_index','completion_EOG','first_rejected_byte_start','first_rejected_byte_end'}
        self.req(keys<=set(body),'Native observation fields missing')
        self.req(type(body['all_input_tokens_admitted']) is bool,'Native token admission bool')
        if body['status']=='native_token_rejection':
            self.req(expected is False and body['all_input_tokens_admitted'] is False and body['completion_EOG'] is None,'Native token rejection scope')
            index=body['first_rejected_token_index'];start,end=body['first_rejected_byte_start'],body['first_rejected_byte_end']
            self.req(uint(index,tokens-1) and uint(start,byte_count) and uint(end,byte_count) and start<=end,'Rejected token/byte span')
            self.accepts+=index;self.token_rejections+=1
        else:
            self.req(body['all_input_tokens_admitted'] is True and body['first_rejected_token_index'] is None
                and body['first_rejected_byte_start'] is None and body['first_rejected_byte_end'] is None,'Complete-token native scope')
            self.req(body['status']==('native_member' if expected else 'native_eog_rejection'),'Native membership status differs')
            self.EOG(body['completion_EOG'],expected);self.accepts+=tokens;self.eog_states+=1
        return keys

def validate_rows(rows,*,contract,manifest,documents,wire,match_modules,expected_self,expected_runtime,check=lambda:None):
    need(type(rows) is list and len(rows)<=500,'Result frame count cap')
    need(type(documents) is list and len(documents)==189 and len(manifest['cases'])==189,'All original pack documents required')
    for raw,case in zip(documents,manifest['cases']):
        need(type(raw) is bytes and len(raw)==case['bytes'] and hashlib.sha256(raw).hexdigest()==case['sha256'],'Exact immutable original wire')
    l=Ledger(rows,contract,manifest,documents,wire,match_modules,expected_self,expected_runtime,check)
    try:
        body,_=l.frame('before_explicit_required_OpenMP_dependency_load');l.equals(body,dict(event='before_explicit_required_OpenMP_dependency_load',dependency_native_initialization_possible=True),'OpenMP stage')
        body,_=l.frame('exact_core_modules_loaded_exports_resolved');body=l.module(body,'pre_cpu')
        l.equals(body,dict(event='exact_core_modules_loaded_exports_resolved',layouts=contract['expected_layouts']),'Typed layout fields/types')
        body,_=l.frame('typed_version_and_defaults_observed')
        l.equals(body,dict(event='typed_version_and_defaults_observed',version=contract['observed_version'],defaults=contract['expected_defaults'],no_backend_or_model_call_so_far=True),'Pinned typed version/defaults')
        body,_=l.frame('pack_verified_before_backend_or_model')
        l.equals(body,dict(event='pack_verified_before_backend_or_model',pack_sha256=manifest['pack']['sha256'],cases=189,prefixes=6),'Exact frozen pack stage')
        for index,shard in enumerate(contract['ordered_shard_descriptors']):
            body,_=l.frame('before_exact_shard_hash');l.equals(body,dict(event='before_exact_shard_hash',index=index,path=shard['path'],expected_bytes=shard['bytes']),'Ordered shard reservation')
            body,_=l.frame('exact_shard_hash_returned');l.equals(body,dict(event='exact_shard_hash_returned',index=index,bytes=shard['bytes'],sha256=shard['sha256']),'Exact whole-shard hash return')
        body,_=l.frame('three_exact_shards_hash_verified_and_read_leased')
        l.equals(body,dict(event='three_exact_shards_hash_verified_and_read_leased',weight_file_hash_reads=True,tensor_weight_allocation_claim=False),'Hash vs tensor-computation distinction')
        body,_=l.frame('cpu_registry_verified_before_llama_backend_init');body=l.module(body,'post_cpu')
        l.equals(body,dict(event='cpu_registry_verified_before_llama_backend_init',registry_count=1,device_count=1,registry_name='CPU',device_name='CPU'),'Exact CPU identity stage')
        body,_=l.frame('backend_init_returned_exact_CPU_identity_rechecked');body=l.module(body,'post_cpu')
        l.equals(body,dict(event='backend_init_returned_exact_CPU_identity_rechecked'),'Backend identity recheck stage')
        body,_=l.frame('before_model_load_from_three_explicit_splits')
        l.equals(body,dict(event='before_model_load_from_three_explicit_splits',effective_params=contract['effective_params'],empty_devices_array_nonnull=True,cooperative_deadline_not_interruptible_native_call=True),'Exact vocabulary-only parameters')
        l.req(l.at<len(rows),'Missing vocabulary/EOG frame');next_row=rows[l.at]
        l.req(type(next_row) is dict and uint(next_row.get('vocabulary_count'),262144) and next_row['vocabulary_count']>0,'Vocabulary count cap')
        l.nv=next_row['vocabulary_count'];l.eog_examined=l.nv
        body,state=l.frame('all_vocabulary_ids_EOG_enumerated');body=l.module(body,'post_cpu');l.eog=body['EOG_ids']
        l.req(type(l.eog) is list and 1<=len(l.eog)<=64 and all(uint(v,l.nv-1) for v in l.eog) and l.eog==sorted(set(l.eog)),'Complete unique sorted EOG set')
        digest=hashlib.sha256(json.dumps(l.eog,separators=(',',':')).encode('ascii')).hexdigest()
        l.equals(body,dict(event='all_vocabulary_ids_EOG_enumerated',vocabulary_count=l.nv,EOG_ids=l.eog,EOG_JSON_sha256=digest),'EOG vector hash/fields')
        l.req(l.previous['llama_vocab_is_eog']['returned']==l.nv and state['last_EOG_id']==l.nv-1 and state['last_EOG_returned'] is True
            and state['last_EOG_value']==(l.nv-1 in l.eog),'Every vocabulary ID queried')
        for index,case in enumerate(manifest['cases']):
            l.current_case=index;body,_=l.frame('before_case')
            l.equals(body,dict(event='before_case',case_index=index,id=case['id'],document_sha256=case['sha256']),'Exact case order/reservation')
            l.req(l.at<len(rows),'Missing case result');candidate=rows[l.at];l.req(type(candidate) is dict and uint(candidate.get('tokens'),65536),'Case token count cap')
            tokens=candidate['tokens'];kind=case['expected_kind'];l.token_work+=tokens;l.computed+=1;l.groups[case['source_group']]+=1
            if kind in (0,1):l.sampler_states+=1
            body,_=l.frame('case_result')
            base=dict(event='case_result',case_index=index,source_group=case['source_group'],id=case['id'],bytes=case['bytes'],document_sha256=case['sha256'],
                tokens=tokens,used_piece_NUL_seen=False,first_NUL_piece_index=None,first_NUL_offset_in_piece=None,expected_kind=kind,
                expected_native_membership=case['expected_native_membership'],matches_expected=True)
            if kind in (2,3):
                l.req(tokens==0,'Raw byte guards must precede tokenization');l.harness+=1
                base.update(status='harness_utf8_rejection' if kind==2 else 'harness_raw_nul_rejection',native_membership=None,completion_EOG=None)
            else:
                l.req(tokens>0,'Nonempty eligible documents require counted token roundtrip');l.native+=1;l.piece_tokens+=tokens;l.tokenize+=1 if tokens<=1 else 2
                native_keys=l.observation(body,tokens,case['bytes'],kind==1)
                base.update({k:body[k] for k in native_keys})
            l.equals(body,base,'Case fields/layer/expected outcome differ')
            l.written+=1;l.group_writes[case['source_group']]+=1
            for prefix in manifest['prefixes']:
                if prefix['base_case_index']!=index:continue
                l.prefix_seen+=1;l.req(l.at<len(rows),'Required prefix missing');candidate=rows[l.at]
                l.req(type(candidate) is dict and candidate.get('status')!='coverage_unavailable','Required UTF8 prefix coverage unavailable')
                count,cut=candidate.get('token_count'),candidate.get('byte_cut')
                l.req(uint(count,65536) and uint(cut,case['bytes']-1),'Prefix token/cut cap')
                raw=documents[index];sha=hashlib.sha256(raw[:cut]).hexdigest();partial=0<cut<len(raw) and raw[cut]&0xc0==0x80
                if prefix['kind']==0:l.req(cut==prefix['cut'] and sha==prefix['sha256'],'Fixed prefix immutable byte cut/hash');l.tokenize+=1 if count<=1 else 2;l.piece_tokens+=count
                else:
                    l.req(partial and 0<count<tokens,'Required natural token-boundary prefix')
                    start=cut
                    while start>0 and raw[start]&0xc0==0x80:start-=1
                    width=2 if raw[start]<0xe0 else 3 if raw[start]<0xf0 else 4
                    l.req(width in ((2,3) if prefix['kind']==1 else (4,)),'Natural prefix scalar width')
                l.token_work+=count;l.sampler_states+=1;body,_=l.frame('prefix_result')
                l.req(body.get('status')=='native_eog_rejection' and body.get('all_input_tokens_admitted') is True,
                    'Incomplete prefixes require all ordinary tokens admitted and all EOG rejected')
                l.req(type(body.get('last_piece_complete_codepoints_before_partial')) is bool,'Prefix context bool')
                base=dict(event='prefix_result',id=prefix['id'],base_id=case['id'],prefix_kind=prefix['kind'],byte_cut=cut,token_count=count,
                    prefix_sha256=sha,partial_UTF8_at_cut=partial,last_piece_complete_codepoints_before_partial=body['last_piece_complete_codepoints_before_partial'],matches_expected=True)
                native_keys=l.observation(body,count,cut,False);base.update({k:body[k] for k in native_keys})
                l.equals(body,base,'Prefix fields/identity/EOG outcome differ');l.prefix_written+=1
        body,state=l.frame('recognition_batch_returned');body=l.module(body,'post_cpu')
        base=dict(event='recognition_batch_returned',pack_format_version=2,cases_completed=189,
            source_group_completed=dict(primary_frozen_wire=167,new_serialization_of_retained_authored_abstention=18,harness_byte_guards=4),
            primary_native_results=166,primary_harness_dispositions=1,new_authored_native_results=18,independent_guard_dispositions=4,
            prefix_slots=6,total_token_budget_used=l.token_work,tokenize_calls=l.previous['llama_tokenize']['returned'],piece_calls=l.previous['llama_token_to_piece']['returned'],
            apply_calls=l.previous['llama_sampler_apply']['returned'],accept_calls=l.previous['llama_sampler_accept']['returned'],EOG_accept_calls=0,
            samplers_freed_before_model=True,model_freed=True,backend_free_returned=True,scientific_validation='not_established')
        l.equals(body,base,'Final batch accounting/layers differ')
        l.req((l.native,l.harness,l.sampler_states,l.prefix_written)==(184,5,190,6),'Whole frozen-pack coverage incomplete')
        l.req(l.previous['llama_tokenize']['returned']==l.tokenize and l.piece_tokens<=l.previous['llama_token_to_piece']['returned']<=2*l.piece_tokens,'Tokenization/piece count derivation differs')
        l.req(l.previous['llama_sampler_accept']['returned']==l.accepts
            and l.previous['llama_sampler_apply']['returned']==l.accepts+l.token_rejections+len(l.eog)*l.eog_states,'Apply/accept/EOG contributions differ')
        variable={'llama_vocab_is_eog','llama_tokenize','llama_token_to_piece','llama_sampler_init_grammar','llama_sampler_free','llama_sampler_apply','llama_sampler_accept'}
        for api,cap in contract['native_call_policy']['per_API_caps'].items():
            if api not in variable:l.req(l.previous[api]['returned']==cap,'Final scalar/CPU identity calls incomplete: '+api)
        for flag in ('cpu_load_return_observed','cpu_registry_nonnull','backend_init_return_observed','model_load_return_observed','model_return_nonnull',
                     'model_free_attempted','model_free_return_observed','backend_free_attempted','backend_free_return_observed'):l.req(state[flag] is True,'Final native ownership return missing')
        l.req(not state['model_owned'] and not state['backend_owned'],'Native ownership not released')
        body,_=l.frame('child_normal_completion')
        l.req(set(body)=={'event','mode','elapsed_ms','parent_qualification_required'} and body['mode']=='--recognize'
            and uint(body['elapsed_ms'],119999) and body['parent_qualification_required'] is True,'Recognition child completion bounds')
        l.req(l.at==len(rows),'Unexpected trailing result frames')
        return dict(status='complete_singleton_source_bound_observations',complete=True,case_results=189,primary_native_results=166,
            primary_harness_dispositions=1,new_authored_native_results=18,independent_guard_dispositions=4,prefix_results=6,
            vocabulary_count=l.nv,EOG_ids=l.eog,module_classifications=l.modules,token_work=l.token_work,native_call_counters=l.previous,
            full_vocabulary_mask_qualified=False,scientific_validation='not_established',execution_authorized=False,
            observation_basis='Hash-bound reviewed native source, retained wire/counters and independent deterministic consistency checks; no repeated native execution')
    except RecognitionValidationError as error:
        if not error.coverage or error.coverage.get('status')=='unqualified_unknown':error.coverage=l.coverage()
        raise

def read_bounded(path,cap,check):
    check();need(path.is_file() and 0<path.stat().st_size<=cap,'Result artifact type/byte cap');out=[];count=0
    with path.open('rb') as stream:
        while True:
            check();block=stream.read(65536)
            if not block:break
            count+=len(block);need(count<=cap,'Result grew beyond cap');out.append(block);check()
    check();return b''.join(out)

def validate_artifacts(child,*,contract,manifest,wire,expected_self,expected_runtime,match_modules,pack_raw,safe,check=lambda:None):
    child=safe(child,output=True);need({p.name for p in child.iterdir()}=={'attempt.json','result.jsonl'},'Incomplete/unexpected recognition child artifacts')
    attempt=safe(child/'attempt.json',output=True);result=safe(child/'result.jsonl',output=True)
    claim=read_bounded(attempt,4096,check);need(exact(json_value(claim),dict(schema_version=1,mode='--recognize',status='claimed_before_native_load',draft=True)),'Recognition attempt claim')
    raw=read_bounded(result,8388608,check);need(raw.endswith(b'\n'),'Unterminated recognition JSONL')
    lines=raw.split(b'\n')[:-1];need(0<len(lines)<=500 and all(0<len(line)<=65536 for line in lines),'Result row cap')
    rows=[json_value(line) for line in lines];documents=decode_pack(pack_raw,manifest)
    return validate_rows(rows,contract=contract,manifest=manifest,documents=documents,wire=wire,match_modules=match_modules,
        expected_self=expected_self,expected_runtime=expected_runtime,check=check)
