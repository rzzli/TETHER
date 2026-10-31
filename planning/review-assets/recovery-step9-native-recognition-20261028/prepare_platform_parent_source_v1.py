"""Author a prospective unbound parent; only own-source/data transformation."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE/'run_detached_abi_observation_v6.py'
old_bytes=OLD.read_bytes()
assert hashlib.sha256(old_bytes).hexdigest()=='ec985415358e547db31bf988a5027099b2992a06d096f3067136ffa03f858aff'
raw=old_bytes.decode('utf-8')
tree=ast.parse(raw)
functions={n.name:ast.get_source_segment(raw,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
old_contract=json.loads((HERE/'DETACHED-ABI-EXECUTION-CONTRACT-v6.json').read_text(encoding='utf-8'))
policy=json.loads((HERE/'TRUSTED-SYSTEM32-MODULE-POLICY-v1.json').read_text(encoding='utf-8'))
contract=dict(schema_version=1,status='prospective_unbound_trusted_platform_ABI_source_contract_only',
    execution_authorized=False,verified_bridge_executable=None,verified_build_proof=None,
    binding_requirements='Future separately versioned exact acyclic runtime authority/protocol/root decision; this source contract cannot authorize dispatch',
    module_policy_id=policy['module_policy_id'],module_policy_sha256=policy['module_policy_sha256'],
    policy_contract=dict(path=str(HERE/'TRUSTED-SYSTEM32-MODULE-POLICY-v1.json'),sha256=hashlib.sha256((HERE/'TRUSTED-SYSTEM32-MODULE-POLICY-v1.json').read_bytes()).hexdigest()),
    semantic_policy=policy['semantic_policy'],
    expected_defaults=old_contract['expected_defaults'],expected_layouts=old_contract['expected_layouts'],
    child_artifacts=old_contract['child_artifacts'],
    version_policy=old_contract['version_policy'],
    permitted_explicit_load_order=old_contract['permitted_explicit_load_order'],
    explicit_target_calls=['llama_version','llama_model_default_params'],
    module_policy_wire=dict(event_index=1,required_outer_fields=['module_policy_id','module_policy_sha256'],module_rows_exact_fields=['name','path']),
    maximum_module_reports=64,platform_report_filesystem_operations=0,
    trust_scope='Canonical platform directory reports are trusted host context; not authenticated images or loader/initializer/lifetime attestation',
    CPU_enabled=False,model_enabled=False,recognition_enabled=False,
    no_old_failure_reinterpretation=True,no_new_census_or_tracing=True)
contract_path=HERE/'TRUSTED-SYSTEM32-ABI-CONTRACT-v1.json'
with contract_path.open('x',encoding='utf-8') as out:json.dump(contract,out,sort_keys=True,indent=2);out.write('\n')
contract_sha=hashlib.sha256(contract_path.read_bytes()).hexdigest()
prefix=raw[:raw.index('EXE=ROOT/')]
prefix=prefix.replace('Fixed diagnostic ABI observation, source revision6 / proposed attempt3.','Prospective trusted-platform ABI parent v1; source/pure only, build-unbound.')
prefix=prefix.replace('Actual dispatch requires new exact protocol, independent peer and root decision.','Authority, configuration, collection and preparation reject until a separately versioned binding.\nThe preserved execute body is unreachable through this draft. No dispatch permission is created.')
prefix+='''EXE=None  # Deliberately no future executable/build binding.
EXE_SHA=None
RUNTIME=ROOT/"data/cache/approved-native-mirror-20261028T004531Z/runtime"
PROTOCOL=None
EXECUTION_AUTHORIZED=False
'''
prefix+=f'CONTRACT=HERE/"{contract_path.name}"\nCONTRACT_SHA="{contract_sha}"\n'
prefix+='''TERMINAL_SOURCE=HERE/"detached_abi_terminal_observation_v3.py"
TERMINAL_SHA="4ea2c429a8e4d512d42ae449fc3764550421ae8cf6491e3866c8322880d5c96c"
POLICY_SOURCE=HERE/"trusted_system32_module_policy_v1.py"
POLICY_SOURCE_SHA="77e39b3bb82fb83049aba9956da0251b4a8d914f167dc6d6512d554ad7bfb3a8"
POLICY_ID="trusted-System32-platform-v1"
POLICY_SHA="807995f6061d7a2c85144c58668fc2e4ecb79a4fb51d462e43d0a8dfc586d589"
'''
prefix+=raw[raw.index('TERMINAL_POLICY='):raw.index('if sha(BUILD_PROTOCOL)')]
blocks=['''def authority():
    raise RuntimeError("Unbound trusted-platform ABI source: no verified future build/executable/runtime authority")


def policy_matcher():
    require(sha(POLICY_SOURCE)==POLICY_SOURCE_SHA,"Frozen mathematical module policy changed")
    spec=util.spec_from_file_location("trusted_platform_ABI_pure_policy_v1",POLICY_SOURCE)
    module=util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.POLICY_ID==POLICY_ID and module.POLICY_SHA256==POLICY_SHA,"Policy semantic fingerprint differs")
    return module
''']
for name in ('terminal_observer','api_class','exact','json_value','runtime_pins'):
    blocks.append(functions[name])
blocks.append('''def validate_modules(rows):
    require(EXE is not None,"Unbound ABI context is not an approved self executable")
    return policy_matcher().match_modules(rows,expected_self=str(EXE),expected_runtime=str(RUNTIME))
''')
# All authoritative wire checks are pure and operate only on reported strings.
old=functions['validate_child_artifacts']
body=old[old.index('    require([row.get("event")'):old.index('\n    return dict(version=')]
body=body.replace('set(rows[1])=={"event","modules","layouts"}',
    'set(rows[1])=={"event","modules","layouts","module_policy_id","module_policy_sha256"}')
body=body.replace('    validate_modules(rows[1]["modules"])',
    '    require(type(rows[1]["module_policy_id"]) is str and rows[1]["module_policy_id"]==POLICY_ID\n'
    '            and type(rows[1]["module_policy_sha256"]) is str and rows[1]["module_policy_sha256"]==POLICY_SHA,\n'
    '            "Compiled module policy identifier/fingerprint differs")\n'
    '    classified=policy_matcher().match_modules(rows[1]["modules"],expected_self=expected_self,expected_runtime=expected_runtime)')
pure='''def validate_child_rows(rows,*,contract,expected_self,expected_runtime):
    """Pure complete-wire validation using externally prevalidated fixed native context.

    Context identity must come from live original-path native leases in a future
    qualified parent, never from child-supplied verified flags or platform paths.
    """
    require(type(rows) is list and len(rows)==5,"ABI row count differs")
'''+body+'''
    return dict(version=version,version_expected_previously_known=False,defaults=observed["defaults"],
        layouts=rows[1]["layouts"],raw_modules=rows[1]["modules"],module_classification=classified,result_rows=5,
        module_policy_id=POLICY_ID,module_policy_sha256=POLICY_SHA,
        independent_ABI_acceptance="pending",scientific_validation="not_established",
        module_inventory_scope="Reported before explicit version/default calls; trusted platform context, not image authentication or lifetime attestation")
'''
blocks.append(pure)
artifact=old[:old.index('    require([row.get("event")')]+'''
    require(EXE is not None,"Unbound ABI executable context")
    return validate_child_rows(rows,contract=contract,expected_self=str(EXE),expected_runtime=str(RUNTIME))
'''
blocks.append(artifact)
blocks.append(functions['abi_argv'])
for name,args in [('configuration','output,inputs'),('validate_role','config'),('collect_inputs',''),('prepare','')]:
    blocks.append(f'def {name}({args}):\n    authority()  # Always fails: no executable, closure, output or dispatch is authorized.\n')
blocks.append(functions['execute'])
blocks.append('''if __name__=="__main__":
    raise SystemExit("Source/pure-only unbound draft; no prepare or execute command is available")
''')
path=HERE/'run_platform_abi_observation_v1.py'
with path.open('x',encoding='utf-8',newline='\n') as out:out.write(prefix+'\n\n'+'\n\n\n'.join(blocks)+'\n')
ast.parse(path.read_text(encoding='utf-8'))
print(json.dumps(dict(source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),contract=str(contract_path),contract_sha256=contract_sha,children=0,SDK_constructors=0)))
