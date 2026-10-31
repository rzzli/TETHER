"""One root-authorized literal correction; never imports or calls the core."""
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def pin(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def write(name,value):
    with (HERE/name).open('xb') as out:
        out.write((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8'))

old_schema=HERE/'ADOPTION-FIXTURE-SCHEMA-v2.json'
old_data=HERE/'RAW-ADOPTION-FIXTURES-v2.json'
assert pin(old_schema)['sha256']=='b4b6670c71d08133670af0af357088447c452f0e973f179c07e69702f900ade5'
assert pin(old_data)['sha256']=='09f79b6a5f7bca50a3da63f3d95a6041e8bc2acf84ec85f1db5d96a4e7c1d5f6'
schema=json.loads(old_schema.read_bytes()); old=json.loads(old_data.read_bytes())
schema['schema_version']=3
schema['status']='CLOSED_LITERAL_SCHEMA_WITH_ROOT_AUTHORIZED_UNUSED_BUFFER_CLARIFICATION'
schema['expected_buffer_universe_rule']='Snapshot buffers list EVERY buffer registered by this same owner, including an unused preallocated buffer after a rejected reservation. retained means the owner holds the object; reusable is derived separately from pending/failed call references. No rejected call may erase an existing buffer.'
write('ADOPTION-FIXTURE-SCHEMA-v3.json',schema)
new=copy.deepcopy(old)
case=next(c for c in new['cases'] if c['id']=='conflicting_reserve_keeps_original')
assert case['expected']['buffers']==[]
assert case['initial']['buffers']==[dict(id='buf0',capacity=3,generation=0,hex='616263')]
case['expected']['buffers']=[dict(id='buf0',generation=0,hex='616263',retained=True,reusable=True)]
# Validate the literal delta independently of any source output.
reverse=copy.deepcopy(new['cases'])
next(c for c in reverse if c['id']=='conflicting_reserve_keeps_original')['expected']['buffers']=[]
assert reverse==old['cases']
assert all(a['steps']==b['steps'] and a['checkpoints']==b['checkpoints'] and a['expected']['counters']==b['expected']['counters'] for a,b in zip(old['cases'],new['cases']))
new['schema_version']=3
new['status']='ROOT_AUTHORIZED_ONE_FIELD_LITERAL_CORRECTION_AFTER_PRESERVED_SOURCE_BEFORE_PROOF'
new['schema']=pin(HERE/'ADOPTION-FIXTURE-SCHEMA-v3.json')
new['author']=pin(Path(__file__).resolve())
new['preserved_v2']=dict(schema=pin(old_schema),fixture=pin(old_data),freeze=pin(HERE/'RAW-ADOPTION-FIXTURE-FREEZE-v2.json'),before_proof=pin(HERE/'RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v1.json'))
new['exact_v3_delta']='Only conflicting_reserve_keeps_original.expected.buffers adds its existing unused owner-registered buf0. No step/checkpoint/raw-record/counter/handoff/deadline expectation changes.'
new['expectation_provenance']='Root-authorized source-format correction from the already declared initial buffer, not an expectation inferred from under-test output. All prior authored expectations remain unchanged.'
new['successor_implementation_exists']=True
write('RAW-ADOPTION-FIXTURES-v3.json',new)
proof=dict(schema_version=1,status='passed',scope='Literal correction and encoding only, no under-test source import or execution.',author=pin(Path(__file__).resolve()),schema=pin(HERE/'ADOPTION-FIXTURE-SCHEMA-v3.json'),fixture=pin(HERE/'RAW-ADOPTION-FIXTURES-v3.json'),preserved=new['preserved_v2'],changed_case=case['id'],changed_path='expected.buffers',before=[],after=case['expected']['buffers'],all32_steps_checkpoints_counters_unchanged=True,all_other_cases_unchanged=True,reverse_delta_exact=True,cases=len(new['cases']),checkpoints=sum(len(c['checkpoints']) for c in new['cases']),literal_steps=sum(len(c['steps']) for c in new['cases']),actual_API_calls=0,under_test_calls=0,runtime_authorized=False,production_owner_bound=False,profile_qualified=False)
write('RAW-ADOPTION-LITERAL-CORRECTION-PROOF-v3.json',proof)
freeze=dict(schema_version=3,status='CORRECTED_LITERAL_PREPARATION_FROZEN_FOR_EXACT_DELTA_PEER',schema=proof['schema'],fixture=proof['fixture'],author=proof['author'],correction_proof=pin(HERE/'RAW-ADOPTION-LITERAL-CORRECTION-PROOF-v3.json'),preserved_v2=proof['preserved'],cases=32,literal_steps=256,checkpoints=9,exact_delta=new['exact_v3_delta'],actual_API_calls=0,FFI_registration_proven=False,production_owner_bound=False,profile_qualified=False,runtime_authorized=False)
write('RAW-ADOPTION-FIXTURE-FREEZE-v3.json',freeze)
print(json.dumps(dict(schema=proof['schema'],fixture=proof['fixture'],proof=pin(HERE/'RAW-ADOPTION-LITERAL-CORRECTION-PROOF-v3.json'),freeze=pin(HERE/'RAW-ADOPTION-FIXTURE-FREEZE-v3.json'))))
