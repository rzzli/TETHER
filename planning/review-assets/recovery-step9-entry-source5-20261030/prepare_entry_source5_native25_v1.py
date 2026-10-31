"""Narrow Source5 kind guard and native25 metadata preparation; never imports subject code."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import symtable

BASE = Path(__file__).resolve().parent
ASSETS = BASE.parent
OLD = ASSETS / 'recovery-step9-native25-component-20261030'


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def pin(path):
    path = path.resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def document(path):
    return json.loads(path.read_bytes())


def write_json(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False)+'\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)
    return pin(path)


def same_ast(a, b):
    return ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)


scope_path = OLD / 'KERNEL-KIND-GUARD-SUCCESSOR-AUTHORING-SCOPE-v5.json'
old_freeze_path = OLD / 'NATIVE25-COMPONENT-FREEZE-v4.json'
old_freeze = document(old_freeze_path)
for item in old_freeze['pins'].values():
    require(pin(Path(item['path'])) == item, 'Preserved prior frozen pin: '+item['path'])
old_kernel_path = Path(old_freeze['pins']['subject_preflight_entry_kernel_v4']['path'])
old_kernel = old_kernel_path.read_bytes()
require(hashlib.sha256(old_kernel).hexdigest() == 'e389db4ec1e667f1b81694575ba1ba0d1d7ceed3e642cf43504766f331c759f8', 'Exact frozen Source4 parent')
anchor = "        need(struct.unpack_from('<I',self._bank,base+28)[0]==0 and not any(memoryview(self._bank)[base+80:base+128]),'NATIVE_STATE_NOT_REPRESENTABLE')\n        return c\n"
guard = "        for axis in _AXES:\n            expected=_scalar_kind(c.api) if axis=='scalar' else 'COUNT32' if axis=='count' else 'DWORD32' if axis=='error_value' else 'DEFINEDNESS'\n            need(struct.unpack_from('<H',self._bank,base+_AXIS_OFFSET[axis]+12)[0]==_KIND_IDS[expected],'NATIVE_STATE_NOT_REPRESENTABLE')\n"
source = old_kernel.decode('utf-8')
require(source.count(anchor) == 1, 'Unique RawCallStore._call return anchor')
source = source.replace(anchor, anchor.replace('        return c\n', guard+'        return c\n'))
require(source.replace(guard, '', 1).encode('utf-8') == old_kernel, 'Exact reverse text guard-only delta')
old_ast = ast.parse(old_kernel.decode('utf-8'))
new_ast = ast.parse(source)
normalized = copy.deepcopy(new_ast)
store = next(n for n in normalized.body if isinstance(n, ast.ClassDef) and n.name == 'RawCallStore')
method = next(n for n in store.body if isinstance(n, ast.FunctionDef) and n.name == '_call')
loops = [n for n in method.body if isinstance(n, ast.For)]
require(len(loops) == 1 and same_ast(loops[0], ast.parse(guard.lstrip()).body[0]), 'Exactly declared four-axis guard AST')
method.body.remove(loops[0])
require(same_ast(normalized, old_ast), 'Every other source AST unchanged')
kernel_path = BASE / 'preflight_entry_kernel_v5.py'
with kernel_path.open('xb') as stream:
    stream.write(source.encode('utf-8'))
kernel_pin = pin(kernel_path)
symtable.symtable(source, str(kernel_path), 'exec')
prior_control_path = OLD / 'NATIVE25-COMPONENT-PROOF-v4.json'
prior_control = pin(prior_control_path)
require(prior_control['sha256'] == 'dfe90829f1f8ac9e05aaaa7ce31304422150bb286c3cecb300ac7651f61ff63d', 'Exact retained 41PASS/2FAIL control')
delta_path = BASE / 'ENTRY-SOURCE-DELTA-v5.json'
delta = write_json(delta_path, dict(
    schema_version=5, status='NARROW_RAW_CALLSTORE_API_AXIS_KIND_GUARD',
    authoring_scope=pin(scope_path), parent_kernel=pin(old_kernel_path), selected_kernel=kernel_pin,
    changed_method='RawCallStore._call', inserted_guard=guard,
    reverse_source_text_equal=True, normalized_whole_module_AST_equal=True,
    untouched='All other statements/imports/constants/classes/methods, ABI widths, bits, epochs, clocks, limits, error and close rules.',
    compatibility_import_name='preflight_entry_kernel_v4',
    namespace='Fresh exact loader module; the stable compatibility spelling never reuses the parent Source4 module object or fingerprint.',
    observed_parent_control=prior_control,
    activity=dict(subject_imports=0, subject_runs=0, native_C_SDK_model_original_operations=0)))
old_pause_path = Path(old_freeze['pins']['source_pause']['path'])
old_pause = document(old_pause_path)
ops_pin = old_freeze['pins']['subject_preflight_owner_ops_v4']
view_pin = old_freeze['pins']['subject_preflight_file_view_v4']
codec_pin = old_freeze['pins']['subject_role_ledger_codec_v4']
pause_path = BASE / 'ENTRY-SOURCE-PAUSE-v5.json'
pause = write_json(pause_path, dict(
    schema_version=5, status='COHERENT_SOURCE5_KERNEL_WITH_UNCHANGED_CAPTURED_SOURCE4_HELPERS_BEFORE_IMPORT_OR_TEST',
    source_scope=pin(scope_path), source_delta=delta,
    sources=dict(kernel=kernel_pin, owner_ops=ops_pin, file_view=view_pin),
    source_module_map=dict(kernel=dict(module='preflight_entry_kernel_v4', **kernel_pin),
                           owner_ops=dict(module='preflight_owner_ops_v4', **ops_pin),
                           file_view=dict(module='preflight_file_view_v4', **view_pin)),
    captured_dependency=codec_pin,
    current_pre_entry_TCB=dict(source_generation=5, compatibility_import_name='preflight_entry_kernel_v4', pin=kernel_pin),
    historical_parent_source4_pause=pin(old_pause_path), historical_parent_kernel=pin(old_kernel_path),
    capture_prefix=dict(bytes=99000, unchanged=True, ordered_modules=['role_ledger_codec_v4', 'preflight_owner_ops_v4', 'preflight_file_view_v4']),
    syntax_and_symtable='PASS without subject import or execution',
    qualification=dict(synthetic_source_only=True, actual_native_backend=False, native_input_lease=False, physical=False, resources=False)))

old_inputs_path = Path(old_freeze['pins']['inputs']['path'])
old_inputs = document(old_inputs_path)
inputs = copy.deepcopy(old_inputs)
for name in ('world_inputs', 'empty_world_inputs'):
    values = inputs[name]
    require(values['module_names']['kernel'] == 'preflight_entry_kernel_v4', 'Stable compatibility module name')
    require(values['source_map']['preflight_entry_kernel_v4'] == pin(old_kernel_path), 'Historical kernel input is exact parent')
    values['source_map']['preflight_entry_kernel_v4'] = kernel_pin
    require(sum(h['bytes'] for h in values['helpers']) == 99000, 'Unchanged actual captured prefix')
    for helper in values['helpers']:
        selected = values['source_map'][helper['module']]
        require(helper['bytes'] == selected['bytes'] and helper['sha256'] == selected['sha256'], 'Captured helper bytes match active source map')
inputs['source_pause'] = pause
inputs['historical_parent_source4_pause'] = old_inputs['source_pause']
inputs['current_pre_entry_TCB'] = dict(source_generation=5, pin=kernel_pin, compatibility_import_name='preflight_entry_kernel_v4')
inputs['historical_baseline_fixture'] = inputs.pop('baseline_fixture')
inputs['historical_inherited_helper_source_pin_labels'] = 'Nested helper.source_pin values are retained historical preparation labels. Active helper authority is the unchanged source_map plus bytes/SHA matching; no inherited Source4 kernel is current.'
inputs_path = BASE / 'NATIVE25-COMPONENT-INPUTS-v5.json'
input_pin = write_json(inputs_path, inputs)
roundtrip = copy.deepcopy(inputs)
for name in ('world_inputs', 'empty_world_inputs'):
    roundtrip[name]['source_map']['preflight_entry_kernel_v4'] = pin(old_kernel_path)
roundtrip['source_pause'] = roundtrip.pop('historical_parent_source4_pause')
roundtrip['baseline_fixture'] = roundtrip.pop('historical_baseline_fixture')
del roundtrip['current_pre_entry_TCB'], roundtrip['historical_inherited_helper_source_pin_labels']
require(roundtrip == old_inputs, 'Only selected kernel pin/pause and explicit current/historical provenance changed in inputs')

old_runner_path = Path(old_freeze['pins']['runner']['path'])
old_runner = old_runner_path.read_bytes()
runner = old_runner.decode('utf-8')
replacements = []
for kind in ('ATTEMPT', 'PROOF', 'ARTIFACTS', 'FREEZE', 'BINDING'):
    before, after = 'NATIVE25-COMPONENT-'+kind+'-v4', 'NATIVE25-COMPONENT-'+kind+'-v5'
    require(runner.count(before) == 1, 'One mechanical versioned path: '+kind)
    runner = runner.replace(before, after)
    replacements.append((before, after))
reverse = runner
for before, after in replacements:
    reverse = reverse.replace(after, before)
require(reverse.encode('utf-8') == old_runner, 'Runner reverse-text equality; cases3 import unchanged')
runner_path = BASE / 'run_native25_component_v5.py'
with runner_path.open('xb') as stream:
    stream.write(runner.encode('utf-8'))
for path in (runner_path, Path(__file__).resolve()):
    code = path.read_bytes().decode('utf-8')
    ast.parse(code, filename=str(path))
    symtable.symtable(code, str(path), 'exec')

pins = dict(old_freeze['pins'])
pins['historical_parent_source4_pause'] = pins['source_pause']
pins['historical_parent_kernel4'] = pins['subject_preflight_entry_kernel_v4']
pins['historical_parent_inputs'] = pins['inputs']
pins['historical_parent_runner'] = pins['runner']
pins.update(source_pause=pause, subject_preflight_entry_kernel_v4=kernel_pin, inputs=input_pin,
            runner=pin(runner_path), source5_delta=delta, source5_authoring_scope=pin(scope_path),
            source5_preparer=pin(Path(__file__).resolve()), historical_parent_freeze=pin(old_freeze_path),
            parent_41pass_2fail_control=prior_control)
prep_path = BASE / 'NATIVE25-COMPONENT-PREPARATION-v5.json'
prep = write_json(prep_path, dict(
    schema_version=5, status='SOURCE5_AND_HARNESS_METADATA_AST_ONLY_READY_FOR_INDEPENDENT_PEER',
    pins=pins, counts=old_freeze['counts'], executable_branch_count=43,
    unchanged_classifications=48, unchanged_assertions=43,
    current_kernel_TCB=kernel_pin, current_kernel_module_name='preflight_entry_kernel_v4',
    captured_prefix_bytes=99000, fresh_namespace_required=True, unchanged_helpers_and_cases=True,
    only_source_change='Four initialized axis kind IDs must match their call API/axis in RawCallStore._call.',
    runner_reverse_text_equal=True, runner_literal_replacements=[dict(before=a, after=b) for a,b in replacements],
    parent_control=dict(pin=prior_control, passed=41, failed=2, deferred=4, static_only=1),
    corrected_successor_executed=False, separate_independent_peer_and_Root_binding_required=True,
    activity=dict(subject_imports=0, subject_runs=0, native_C_SDK_original_model_operations=0)))
pins['source5_preparation'] = prep
freeze_path = BASE / 'NATIVE25-COMPONENT-FREEZE-v5.json'
freeze = write_json(freeze_path, dict(
    schema_version=5, status='SOURCE5_SYNTHETIC_KIND_GUARD_AND_UNCHANGED_NATIVE25_ASSERTIONS_FROZEN_BEFORE_IMPORT_RUN',
    pins=pins, counts=old_freeze['counts'], executable_branch_count=43, unchanged_classifications=48,
    current_kernel_TCB=kernel_pin, captured_prefix_bytes=99000,
    unchanged_case_pin=old_freeze['pins']['cases'], all_parent_actual_controls_preserved=True,
    separate_independent_peer_and_Root_binding_required=True,
    qualification=dict(native25_complete=False, actual_native_backend=False, native_C=False, native_input_lease=False, physical=False, RSS=False)))
outline = write_json(BASE / 'NATIVE25-COMPONENT-BINDING-OUTLINE-v5.json', dict(
    schema_version=5, status='OUTLINE_ONLY_NOT_AUTHORIZED_TO_RUN',
    future_binding_filename='NATIVE25-COMPONENT-BINDING-v5.json',
    required_binding=dict(status='ROOT_BOUND_NATIVE25_COMPONENT_ONE_SHOT', run_authorized=True,
                          deadline_seconds=60, freeze=freeze,
                          execution_scope=dict(path='ROOT_TO_SUPPLY', bytes=None, sha256=None)),
    required_execution_scope_status='ROOT_AUTHORIZED_SINGLE_NATIVE25_COMPONENT_EXECUTION',
    invocation='python -I -B run_native25_component_v5.py only after exact independent source/harness peer and separate Root binding',
    outputs=['NATIVE25-COMPONENT-ATTEMPT-v5.json', 'NATIVE25-COMPONENT-ARTIFACTS-v5', 'NATIVE25-COMPONENT-PROOF-v5.json'],
    one_shot=True, qualification=False))
for name,item in pins.items():
    require(pin(Path(item['path'])) == item, 'Final pin unchanged: '+name)
print(json.dumps(dict(kernel=kernel_pin, source_delta=delta, source_pause=pause, inputs=input_pin,
                      runner=pin(runner_path), preparation=prep, freeze=freeze, outline=outline,
                      static_checks='PASS', subject_imports=0, subject_runs=0), indent=2))
