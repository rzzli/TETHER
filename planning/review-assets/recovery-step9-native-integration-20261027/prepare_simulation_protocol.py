"""Declare one engineering simulation only after immutable full-code validation."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=ROOT/'data/cache/recovery-step9-native-validation-20261028'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


full=json.loads((CACHE/'full-validation.json').read_bytes())
code=json.loads((CACHE/'code-validation.json').read_bytes())
assert full['status']==code['status']=='passed'
assert full['tests']==dict(run=1724,failures=0,errors=0,skipped=[])
assert full['required_probes_exit_code']==0 and code['unchanged_code'] and code['protected_unchanged']
assert len(code['source_pins'])==324 and all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
mirror=json.loads((HERE/'NATIVE-MODEL-MIRROR.json').read_bytes())
assert mirror['status']=='verified_identical_local_native_mirror' and len(mirror['items'])==36
authority=HERE.parent/'recovery-step9-real-retrieval-20261027/SOURCE-AUTHORITY-v1.json'
assert sha(authority)=='84ff16c264c48daf995dc9533bb42227c7c53964edd4c039eae468286b3d6520'
protocol=dict(schema_version=1,role='prospective_real_input_simulated_native_qualification',
    created_at_utc=datetime.now(timezone.utc).isoformat(),version='0.3.9',
    helper_sha256=sha(HERE/'qualify_simulated.py'),
    code_validation=dict(path=(CACHE/'code-validation.json').relative_to(ROOT).as_posix(),sha256=sha(CACHE/'code-validation.json')),
    source_authority=dict(path=authority.relative_to(ROOT).as_posix(),sha256=sha(authority)),
    raw_root=r'E:\projects_data\drug_target_agents_data',model_root=mirror['target'],
    inventory_path='planning/review-assets/recovery-step5-20261026/inventory.json',
    model_mirror_sha256=sha(HERE/'NATIVE-MODEL-MIRROR.json'),
    execution_scope='simulated_native_transport',maximum_tokenizer_children=6,
    maximum_simulated_posts=6,maximum_simulated_servers=1,actual_model_calls=0,actual_native_servers=0,
    actual_network_requests=0,provider_cost_usd=0,automatic_retries=False,
    budget=dict(max_calls=16,max_input_tokens=32000,max_output_tokens=8000,max_cost_usd=0,max_seconds=300,max_retries=1),
    case='existing_exposed_IL6R_RA_inhibit_antibody',fresh_case=False,declared_candidate_count=5,
    original_source_files=27,selected_strategy='literal_case_overlap_then_id_v1',features={},clinical_probability=None,
    scientific_validation='not_attempted',human_reviews='pending',new_downloads=0,
    interpretation='Exact source reports through fake process and HTTP; actual approved tokenizer only. No model result, grammar qualification or native R07 restart.')
with (HERE/'SIMULATION-PROTOCOL.json').open('x',encoding='utf-8') as stream:json.dump(protocol,stream,indent=2)
print(json.dumps(dict(status='prospective_simulation_declared',helper_sha256=protocol['helper_sha256'])))
