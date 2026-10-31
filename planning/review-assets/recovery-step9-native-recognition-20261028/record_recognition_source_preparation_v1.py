"""Retain an engineering source/pure evidence index; no runtime/payload operation."""
from datetime import datetime,timezone
import ast
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPORT=HERE/'RECOGNITION-PARENT-SOURCE-PREPARATION-v1.json'
def guard(event,args):
    if event in ('ctypes.dlopen','subprocess.Popen','os.system') or event.startswith('socket.'):
        raise RuntimeError('Source preparation only')
    if event=='open' and args and isinstance(args[0],(str,bytes)) and str(args[0]).lower().endswith(('.dll','.gguf','.pyd')):
        raise RuntimeError('No binary/model payload in source preparation')
sys.addaudithook(guard)
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
components=[
    ('phase_policy','recognition_module_policy_v1.py','RECOGNITION-MODULE-POLICY-PURE-PROOF-v1.json','source',5),
    ('exact_file_roles','recognition_runtime_roles_v2.py','RECOGNITION-RUNTIME-ROLES-PURE-PROOF-v2.json','source_sha256',10),
    ('strict_result_validator','recognition_validation_v3.py','RECOGNITION-VALIDATION-PURE-PROOF-v3.json','source',12),
    ('parent_role_clock','run_recognition_observation_v6.py','RECOGNITION-PARENT-ROLE-PURE-PROOF-v6.json','helper',10),
    ('parent_fake_lifecycle','run_recognition_observation_v6.py','RECOGNITION-PARENT-INTEGRATION-PURE-PROOF-v6.json','helper',7),
    ('status_only_sealer','recognition_status_seal_v1.py','RECOGNITION-SEALER-PURE-PROOF-v1.json','source',6),
]
verified=[]
for name,source,proof,key,count in components:
    proof_path=HERE/proof;value=json.loads(proof_path.read_text(encoding='utf-8'));source_pin=pin(HERE/source)
    assert value['status']=='passed' and value['tests']==count and not value['failures'] and not value['errors']
    actual=value[key] if key=='source_sha256' else value[key]['sha256']
    assert actual==source_pin['sha256']
    verified.append(dict(component=name,source=source_pin,proof=pin(proof_path),test_methods=count))
parent=HERE/'run_recognition_observation_v6.py';raw=parent.read_bytes();raw.decode('utf-8','strict');tree=ast.parse(raw)
assign={t.id:n.value for n in tree.body if isinstance(n,ast.Assign) for t in n.targets if isinstance(t,ast.Name)}
assert ast.literal_eval(assign['EXE']) is None and ast.literal_eval(assign['EXE_SHA']) is None
funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
assert isinstance(funcs['authority'].body[0],ast.Raise)
assert sum(r['test_methods'] for r in verified)==50
metadata_names=('RECOGNITION-SOURCE-ROOT-DECISION-v1.json','RECOGNITION-EXECUTION-CONTRACT-v1.json',
    'RECOGNITION-MODULE-POLICY-v1.json','RECOGNITION-MODULE-VECTORS-v1.json','RECOGNITION-EXPECTED-PACK-METADATA-v1.json',
    'RECOGNITION-CHILD-WIRE-v2.json','recognition_runtime_pins_v1.hpp','RECOGNITION-RUNTIME-PIN-DESCRIPTOR-v1.json')
regressions=[
    dict(finding='Canonical CPU/software role aliases',before='RECOGNITION-ROLE-COLLISION-REGRESSION-BEFORE-v2.json',scope='Four genuine pure-data before failures',corrected_by='recognition_runtime_roles_v2.py'),
    dict(finding='Expected computation counted without valid snapshot',before='RECOGNITION-COVERAGE-REGRESSION-BEFORE-v2.json',scope='Three genuine before failures',corrected_by='recognition_validation_v2.py and preserved in v3'),
    dict(finding='Wrong-ID rows prematurely counted as validated native/harness; early native setup calls admitted',before='RECOGNITION-STAGE-LAYER-REGRESSION-BEFORE-v3b.json',scope='Five genuine corrected-fixture before failures',corrected_by='recognition_validation_v3.py'),
    dict(finding='Inherited terminal seal replaces recognition status with ABI status',before='RECOGNITION-PARENT-INTEGRATION-PURE-PROOF-v2.json',scope='One genuine fake lifecycle failure; no actual child',corrected_by='recognition_status_seal_v1.py'),
    dict(finding='Derived reporting failure bypasses original leases/seal',before='RECOGNITION-REPORT-SEAL-REGRESSION-BEFORE-v5b.json',scope='Four genuine fake RuntimeError/KI × observed child0/2 failures',corrected_by='run_recognition_observation_v5.py and preserved in v6'),
    dict(finding='Returned report omits known publication failure despite correct disk retention/cleanup',before='RECOGNITION-PARENT-INTEGRATION-PURE-PROOF-v5.json',scope='Four subcase missing-key errors after cleanup/seal assertions passed',corrected_by='run_recognition_observation_v6.py'),
]
for row in regressions:row['before_pin']=pin(HERE/row['before'])
value=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    status='source_and_pure_components_prepared_pending_independent_review_not_execution_authority',
    review_type='Author engineering preparation; not independent scientist or native conformance review',
    components=verified,latest_component_test_methods=50,metadata=[pin(HERE/name) for name in metadata_names],
    frozen_parent=pin(parent),module_policy_id='trusted-System32-recognition-v1',
    module_policy_sha256='4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713',
    regressions=regressions,
    other_preserved_attempts=[dict(path='RECOGNITION-STAGE-LAYER-REGRESSION-BEFORE-v3.json',
        disposition='Initial native-row vector incorrectly expected zero after selecting later group1; preserved, superseded by first-native v3b. Other findings do not depend on that erroneous baseline.'),
        dict(path='RECOGNITION-REPORT-SEAL-REGRESSION-BEFORE-v5.json',
        disposition='Initial AST harness injected before ns existed, four harness errors before reaching source behavior; preserved, superseded by precise final-ns injection v5b.'),
        dict(path='check_recognition_module_policy_v1_before_syntax.py',disposition='Initial raw-string SyntaxError preserved; no policy source mutation or test result from that attempt.')],
    source_limits=dict(parent_seconds=300,child_seconds=120,cooperative_ms=117000,child_cleanup_seconds=2,parent_finalization_seconds=5,
        process_job_commit_bytes=268435456,active_processes=1,child_attempts=1,periodic_job_seconds=3.5),
    model_hash_plan=dict(source_only_preparation_passes=0,driver_passes=0,parent_initial=1,child=1,parent_final=1,
        logical_total_bytes=26964331488,external_verification_separately_timed=True,no_runtime_fit_established=True),
    artifact_scopes=dict(policy_vectors=100,synthetic_complete_rows=401,modeled_case_records=189,prefix_slots=6,
        parser_adversarial_mutations=40,fake_lifecycle_fixtures=15,original_primary_documents=167,raw_NUL_primary_native_result=None,
        no_actual_native_or_tokenizer_result=True),
    unchanged_sources=[pin(HERE/'detached_parent_launch_draft_v1.py'),pin(HERE/'abi_parent_launch_draft_v3.py'),
        pin(HERE/'detached_abi_terminal_observation_v3.py'),pin(HERE/'trusted_system32_module_policy_v1.py')],
    unbound=dict(executable=True,verified_build_runtime_authority=True,CPU_GGUF_asset_validation=True,collector=True,
        preparation_protocol=True,execution_authority=True),
    activity=dict(CPU_binary_opens_or_hashes=0,GGUF_opens_or_hashes=0,SDK_constructors=0,native_target_calls=0,
        actual_target_children=0,compiler_dispatches=0,downloads=0,new_census_or_OS_tracing=0),
    execution_authorized=False,full_vocabulary_mask_qualified=False,scientific_validation='not_established',
    remaining='Exact independent source review; separate metadata-only acyclic verified-build binding decision; later bounded asset/runtime permissions and native qualification remain separate')
with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(preparation=pin(REPORT),test_methods=50)))
