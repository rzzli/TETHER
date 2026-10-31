"""Pin only the retained-input identity correction; no subject execution."""
import ast
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def pub(n,v):
    b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
    with (H/n).open('xb') as f:f.write(b)
    return pin(H/n)
def functions(p):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}

def main():
    assert pin(H/'run_role_aware_independent_v3.py')['sha256']=='dd909a12e68c1073e1814519316940000ea39930dfb83e01827cc2a8932bfe89'
    old=functions(H/'run_role_aware_independent_v3.py');new=functions(H/'run_role_aware_independent_v4.py')
    assert set(old)==set(new) and [k for k in old if old[k]!=new[k]]==['main']
    v=json.loads((H/'ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v3.json').read_bytes())
    v.pop('intended_binding_basename')
    v.update(status='UNBOUND_V4_FIXED_PHASE_INPUTS_NOT_EXECUTION_BINDING',
        actual_runner=pin(H/'run_role_aware_independent_v4.py'),
        required_argument='--phase CODEC_FIRST|LEGACY48_FIRST; exact equality with binding.phase',
        intended_phase_bindings={p:str(H/('ROLE-AWARE-INDEPENDENT-'+p+'-SOURCE-BINDING-v4.json')) for p in ('CODEC_FIRST','LEGACY48_FIRST')},
        retention='Each phase input is created exclusively once and permanently retained. Switching phase selects a different fixed HERE filename, never overwrites/heals the prior proof input. Source and harness pins stay exact.')
    for p in v['harness_pins'].values():assert pin(Path(p['path']))==p
    outline=pub('ROLE-AWARE-INDEPENDENT-BINDING-OUTLINE-v4.json',v)
    preparation=pub('ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v4.json',dict(schema_version=1,
        status='PHASE_SPECIFIC_RETAINED_INPUT_FIX_FROZEN_UNEXECUTED',runner=pin(H/'run_role_aware_independent_v4.py'),outline=outline,
        preserved_runner=pin(H/'run_role_aware_independent_v3.py'),preserved_preparation=pin(H/'ROLE-AWARE-INDEPENDENT-HARNESS-PREPARATION-v3.json'),
        prior_static_peer=pin(H/'ROLE-AWARE-RUNNER-INDEPENDENT-STATIC-REVIEW-v3.json'),
        preparer=pin(H/'prepare_role_aware_runner_v4.py'),freeze_author=pin(Path(__file__).resolve()),
        unchanged_harness_pins=v['harness_pins'],dependencies=v['dependencies'],
        static_delta=dict(only_changed_existing_function='main',facade_helpers_source_loading_audit_identity_AST_equal=True,
            changes=['Required --phase from closed choices','Select fixed phase-specific binding filename under HERE','Require CLI phase equals binding phase','Separate version4 attempt/proof paths'],
            no_fixture_or_subject_API_change=True,no_source_or_harness_map_change=True),
        phase_inputs=v['intended_phase_bindings'],
        cooperative_deadline='The identical original started+60 facade and common post-suite late veto remain; no finally check masks an original exception. No owned outer watchdog/hard callback-free hang claim.',
        extensions_phase='Single-phase extension runner/binding and all extension test bytes remain unchanged.',
        activity=dict(subject_source_reads=0,subject_imports=0,subject_runs=0,original_payload_native_physical_operations=0),
        pending=['Native narrow retained-binding delta peer','coherent four-source pause','root execution scope and exclusive per-phase binding publication','immutable first actual results'],
        qualification={k:False for k in ['real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']}))
    print(json.dumps(dict(preparation=preparation,outline=outline,runner=pin(H/'run_role_aware_independent_v4.py'))))

if __name__=='__main__':main()
