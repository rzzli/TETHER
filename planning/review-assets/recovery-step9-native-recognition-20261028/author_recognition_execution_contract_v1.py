"""Freeze prospective call/accounting/role contract from retained descriptors only."""
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DECISION=HERE/'RECOGNITION-SOURCE-ROOT-DECISION-v1.json'
assert hashlib.sha256(DECISION.read_bytes()).hexdigest()=='20ea58d6626b82dd55c7b823ed1bd729134ecac15470fcc6c4c1ad69d92a5399'
CONTRACT=HERE/'RECOGNITION-EXECUTION-CONTRACT-v1.json'
MANIFEST=HERE/'RECOGNITION-EXPECTED-PACK-METADATA-v1.json'
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(path,value):
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
old=json.loads((HERE/'TRUSTED-SYSTEM32-ABI-CONTRACT-v2.json').read_text(encoding='utf-8'))
policy=json.loads((HERE/'RECOGNITION-MODULE-POLICY-v1.json').read_text(encoding='utf-8'))
report_path=ROOT/'data/cache/r09-native-recognition-pack-v2-20261028T183647Z/preparation-report.json'
assert pin(report_path)['sha256']=='1ff800d4e2a01137eb47acb7d3d7051d64e35b71a0b0bca077f914acdaf60f7e'
report=json.loads(report_path.read_text(encoding='utf-8'))
assert len(report['cases'])==189 and len(report['grammars'])==4 and len(report['prefixes'])==6
expected=dict(schema_version=1,status='frozen_pack_metadata_expectations_not_native_observations',
    original_preparation_report=pin(report_path),independent_pack_verification=pin(HERE/'PACK-V2-RESULT-VERIFICATION.json'),pack=report['pack'],
    grammars=report['grammars'],cases=[{k:row[k] for k in ('id','bytes','expected_kind','expected_native_membership','grammar_index','sha256','source_group','pure_membership_expected')} for row in report['cases']],
    prefixes=[{k:row[k] for k in ('base_case_index','cut','id','kind','sha256')} for row in report['prefixes']],
    original_input_descriptors=report['inputs'],preserve_groups=True,execution_authorized=False)
write(MANIFEST,expected)
header=ROOT/'data/cache/r09-trusted-platform-bridge-preparation-v2-20261029T024601Z/recognizer_runtime_pins.hpp'
text=header.read_text(encoding='utf-8')
shards=[]
for path,sha,size in re.findall(r'\{L"([^"\n]+\.gguf)", "([a-f0-9]{64})", ([0-9]+)ull\}',text):
    shards.append(dict(path=path.replace('\\\\','\\'),bytes=int(size),sha256=sha))
assert len(shards)==3 and sum(r['bytes'] for r in shards)==8988110496
cpu_match=re.search(r'\{L"ggml-cpu-x64.dll", "([a-f0-9]{64})", ([0-9]+)ull\}',text)
assert cpu_match
cpu=dict(path=str(ROOT/'data/cache/approved-native-mirror-20261028T004531Z/runtime/ggml-cpu-x64.dll'),bytes=int(cpu_match[2]),sha256=cpu_match[1])
caps={name:1 for name in ('llama_version','llama_model_default_params','llama_backend_init','llama_backend_free',
    'llama_model_load_from_splits','llama_model_free','llama_model_get_vocab','llama_vocab_n_tokens','ggml_backend_load')}
caps.update(llama_vocab_is_eog=262144,llama_tokenize=412,llama_token_to_piece=2000000,
    llama_sampler_init_grammar=206,llama_sampler_free=206,llama_sampler_apply=1013184,llama_sampler_accept=1000000,
    ggml_backend_reg_count=2,ggml_backend_reg_get=2,ggml_backend_reg_name=2,
    ggml_backend_reg_dev_count=3,ggml_backend_reg_dev_get=3,ggml_backend_dev_count=2,
    ggml_backend_dev_get=2,ggml_backend_dev_type=2,ggml_backend_dev_name=2)
assert len(caps)==25
value=dict(schema_version=1,status='prospective_recognition_source_contract_not_execution_authority',
    root_source_decision=pin(DECISION),fixed_ABI_acceptance=pin(HERE/'TRUSTED-PLATFORM-ABI-ACCEPTANCE-v1.json'),
    observed_version='0.7.0-dev',future_verified_executable=None,future_verified_build=None,
    module_policy=pin(HERE/'RECOGNITION-MODULE-POLICY-v1.json'),module_policy_id=policy['module_policy_id'],
    module_policy_sha256=policy['module_policy_sha256'],expected_pack_manifest=pin(MANIFEST),
    descriptor_basis_header=pin(header),CPU_descriptor=cpu,ordered_shard_descriptors=shards,
    source_only_asset_access='Descriptors are copied from retained qualified metadata; no CPU/GGUF stat, open, hash or load is permitted by this source contract',
    role=dict(mode='--recognize',argc=9,argv=['EXACT_EXE','--recognize','EXACT_RUNTIME','EXCLUSIVE_CHILD_OUTPUT','EXACT_PACK','ggml-cpu-x64.dll','EXACT_SHARD_1','EXACT_SHARD_2','EXACT_SHARD_3'],maximum_attempts=1,automatic_retry=False,
        initializer_side_effects_not_instrumented=True,full_vocabulary_mask=False,inference=False,server=False),
    expected_defaults=old['expected_defaults'],expected_layouts=old['expected_layouts'],
    effective_params=dict(devices_null=False,tensor_buft_overrides_null=True,n_gpu_layers=0,split_mode=0,load_mode=0,
        lazy_mode=0,main_gpu=-1,tensor_split_null=True,progress_callback_null=True,progress_userdata_null=True,
        kv_overrides_null=True,vocab_only=True,check_tensors=False,use_extra_bufts=False,no_host=False,no_alloc=True,load_mtp=False),
    limits=dict(parent_seconds=300,child_seconds_including_cleanup=120,child_cleanup_reserved_seconds=2,parent_finalization_reserved_seconds=5,
        cooperative_work_ms=117000,process_and_job_commit_bytes=268435456,active_processes=1,maximum_children=1,
        stream_bytes=65536,row_bytes=65536,child_JSONL_bytes=8388608,attempt_bytes=4096,
        small_software_file_bytes=134217728,model_files='Only the exact three descriptors at their exact recorded byte sizes/hashes; no general large-file allowance',
        document_bytes=65536,document_tokens=65536,piece_bytes=65536,grammar_bytes=65536,
        vocabulary_ids=262144,EOG_ids=64,cases=200,prefixes=6,grammars=20,counted_token_work=1000000,pack_bytes=20971520),
    native_call_policy=dict(scope='Conservative reservations and observed returns for exactly25 bridge-issued public export calls; excludes internal library, OS/DLL initializer and parent calls',
        counters_exact_fields=['attempted','returned'],per_API_caps=caps,aggregate_attempt_cap=sum(caps.values()),
        attempted='Increment/reserve before API entry and before any potentially throwing publication; a reservation alone does not prove entry',
        returned='Increment immediately when return is observed; register returned ownership/side-effect state before deadline checks, logging or validation',
        unknown='attempted minus returned is retained as unknown; never infer no side effect or automatically repeat a potentially entered call',
        cleanup='Cleanup calls have the same fixed per-API/aggregate caps; no repeat of a returned free/init/load after a post-return exception',
        complete='All attempted==returned; vocab_is_eog returns==actual vocabulary size; exactly190 sampler init/free returns for184 native cases+6 prefixes; EOG accept operations0',
        bounds_basis='T=1000000,C=200,P=6,E=64,V=262144. tokenize<=2(C+P),piece<=2T,apply<=T+E(C+P),accept<=T,sampler init/free<=C+P; scalar setup/identity limits from frozen two CPU checks'),
    clock_policy=dict(owner_start='Trusted driver monotonic start before helper import, validation or runtime hash; not a serialized readiness flag',
        all_runtime_hash_validation_included=True,deadline_aware_streaming=True,parent_hash_calls_before_recorded_start=0,
        child_hashing_included_in_child_clock=True,external_independent_verification_timed_separately=True,
        scientific_case_budget_unchanged_seconds=300),
    frozen_groups=dict(primary_documents=167,pure_members=44,pure_nonmembers=123,primary_native_byte_front=166,
        primary_native_member_expectations=44,primary_native_nonmember_expectations=122,primary_harness_NUL=1,
        new_authored_serializations=18,independent_byte_guards=4,all_packed_cases=189,grammars=4,prefix_slots=6,
        positive_complete_native_cases=184,positive_complete_harness_dispositions=5,positive_complete_sampler_states=190),
    missing_coverage='Any required natural UTF8 prefix unavailable leaves the gate unpassed; no replacement, edited wire or favorable rerun',
    strict_parser='Exact event order, per-case IDs/hashes/groups/expected kinds, all actual EOG IDs, layer distinctions, native counters, result caps, no authoritative failure marker and complete terminal seals required',
    protocol_separation='Source-only contract/header descriptor design cannot grant asset access, compilation, SDK construction or execution; all later gates require separately reviewed exact inputs and root decisions',
    execution_authorized=False,activity=dict(CPU_binary_reads=0,GGUF_reads=0,SDK_constructors=0,children=0,compiler_calls=0))
write(CONTRACT,value)
print(json.dumps(dict(contract=pin(CONTRACT),expected_pack_manifest=pin(MANIFEST),aggregate_call_attempt_cap=sum(caps.values()),asset_payload_reads=0)))
