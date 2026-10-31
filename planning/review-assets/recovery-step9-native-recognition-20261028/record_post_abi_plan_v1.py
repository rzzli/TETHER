"""Record source-only planning evidence/links; no model, CPU, API or child operation."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DOC=HERE/'POST-ABI-RECOGNITION-PREREQUISITES-v1.md'
REPORT=HERE/'POST-ABI-RECOGNITION-PREREQUISITES-v1.json'
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        raise RuntimeError('Source-only plan cannot construct/connect/dispatch')
    if event=='open' and args and isinstance(args[0],(str,bytes)):
        path=str(args[0]).lower()
        if path.endswith(('.gguf','.dll','.pyd')):raise RuntimeError('No binary/model payload in planning')
sys.addaudithook(guard)
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

text=DOC.read_text(encoding='utf-8')
assert '\ufffd' not in text and text.encode('utf-8').decode('utf-8')==text
links=[]
for target in re.findall(r'\]\(([^)]+)\)',text):
    assert '://' not in target,'Only retained local references intended'
    path=(DOC.parent/target).resolve()
    assert path.is_file(),str(path)
    links.append(dict(target=target,exists=True))
names=('SOURCE-QUALIFICATION.json','EXPLICIT-CPU-REVIEW.json','VOCAB-TOKEN-REVIEW.json',
    'DELEGATED-LOADER-REVIEW.json','PACK-V2-RESULT-VERIFICATION.json','RESOURCE-PATH-REVIEW.json',
    'TRUSTED-SYSTEM32-MODULE-POLICY-v1.json','trusted_system32_module_policy_v1.py',
    'typed_public_c_recognizer_platform_v1.cpp','TRUSTED-PLATFORM-ABI-RESULT-VERIFICATION-v1.json',
    'TRUSTED-SYSTEM32-ABI-CONTRACT-v2.json','run_platform_abi_observation_v2.py',
    'TRUSTED-PLATFORM-ABI-EXECUTION-PROTOCOL-v1.json')
inputs=[pin(HERE/name) for name in names]
abi=next(r for r in inputs if Path(r['path']).name=='TRUSTED-PLATFORM-ABI-RESULT-VERIFICATION-v1.json')
assert abi['sha256']=='6f6d3be451853b7de80d00712e3ef96caa26a1e198bd341385daf3e7f1ff92c2'
header=ROOT/'data/cache/r09-trusted-platform-bridge-preparation-v2-20261029T024601Z/recognizer_runtime_pins.hpp'
inputs.append(pin(header))
value=dict(schema_version=1,status='source_only_next_gate_plan_not_execution_authority',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    document=pin(DOC),recorder=pin(Path(__file__)),inputs=inputs,
    latest_ABI=dict(independent_actual_verification=abi,observed_version='0.7.0-dev',
        qualification_scope='Fixed typed version/defaults/layout boundary only; no CPU/model/tokenizer/grammar conformance',separate_acceptance_required=True),
    prospective_findings=[dict(id='recognition_policy_mode_gap',severity='required_prospective_change',
        source='typed_public_c_recognizer_platform_v1.cpp',lines=[245,253,257,533,544,555],
        finding='ABI-only core4 classifier rejects protected CPU even after runtime.recognition is enabled; recognition requires coordinated new mode policy/fingerprint/parent/header/build'),
        dict(id='header_and_role_unqualified',finding='Current header disables recognition/version/pack; existing parent admits four-argument ABI only and five result rows'),
        dict(id='cooperative_vs_hard_deadline',finding='Child120s tick cannot replace external owner; current ABI30/60s role does not authorize recognition120s'),
        dict(id='harness_native_separation',finding='Preserve167primary pure44/123;166native byte-front44/122+one NUL harness;18authored+4guards separate;6prefix slots'),
        dict(id='singleton_not_fullmask',finding='Finite singleton membership/EOG gate cannot qualify production full-vocabulary mask or cost'),
        dict(id='whole_shard_identity_cost',finding='Three descriptors total8988110496B; vocabulary-only computation still performs whole-file identity hashing; no fresh payload reads in this review')],
    current_source_caps=dict(document_bytes=65536,document_tokens=65536,piece_bytes=65536,grammar_bytes=65536,
        vocabulary=262144,EOG=64,cases=200,prefixes=6,grammars=20,total_token_work=1000000,pack_bytes=20*1024**2,
        JSONL_bytes=8*1024**2,row_bytes=65536,child_cooperative_ms=120000),
    current_ABI_parent_caps=dict(child_seconds=30,parent_seconds=60,child_cleanup_reserve_seconds=2,parent_finalization_reserve_seconds=5,
        process_job_commit_bytes=256*1024**2,active_processes=1,children=1),
    scientific_case_budget_seconds=300,descriptor_shard_bytes=8988110496,
    unchanged_framework_resource_warning=dict(observed_simulation_seconds=295.922,limit_seconds=300,headroom_seconds=4.078,
        actual_inference_in_that_simulation=False,logical_model_hash_passes=16,logical_hash_input_bytes=143809767936,
        physical_IO_or_causal_hash_timing_established=False),
    ordered_gates=['bind accepted exact ABI report','mode-specific policy/source-only regressions','exact header/build/runtime closure with independent build proof',
        'bounded CPU/vocabulary/EOG load qualification','unchanged documents/harness/prefix membership conformance','separate full-mask conformance then bounded profiling/integration'],
    QA=dict(UTF8=True,local_links_checked=len(links),links=links,doc_word_count=len(text.split()),
        historical_sources_preserved=True,all_input_paths_are_retained_engineering_metadata_or_source=True),
    activity=dict(native_calls=0,SDK_constructors=0,actual_target_children=0,compiler_calls=0,CPU_binary_reads=0,GGUF_payload_reads=0,
        downloads=0,scientific_or_human_payload_reads=0,new_census_or_tracing=0),
    execution_authorized=False,scientific_validation='not_established',review_type='AI engineering planning review; not independent scientist review')
with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(document=pin(DOC),report=pin(REPORT),links=len(links),words=len(text.split()),activity=value['activity'])))
