"""Root-scoped callback declaration correction; metadata/AST only, no subject import."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import symtable

BASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read_json(path):
    return json.loads(path.read_bytes())


def write_json(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False)+'\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)
    return pin(path)


def check(ok, message):
    if not ok:
        raise AssertionError(message)


scope = BASE / 'NATIVE25-CALLBACK-CORRECTION-AUTHORING-SCOPE-v3.json'
prior_freeze_path = BASE / 'NATIVE25-COMPONENT-FREEZE-v2.json'
prior_freeze = read_json(prior_freeze_path)
for item in prior_freeze['pins'].values():
    check(pin(Path(item['path'])) == item, 'Preserve prior frozen pin: '+item['path'])
old_cases_path = BASE / 'native25_component_cases_v1.py'
old_cases = old_cases_path.read_bytes()
case_text = old_cases.decode('utf-8')
original_tree = ast.parse(case_text)
hooks = [node for node in ast.walk(original_tree) if isinstance(node, ast.FunctionDef) and node.name == 'hook']
check(len(hooks) == 7, 'Exactly seven hook declarations')
check(all(len(node.args.args) == 5 and node.args.args[0].arg == 'point' for node in hooks), 'Original five argument hook declarations')
expected_lines = {node.lineno for node in hooks}
lines = case_text.splitlines(keepends=True)
for number in expected_lines:
    line = lines[number-1]
    check(line.count('def hook(point,') == 1, 'Exact declaration text')
    lines[number-1] = line.replace('def hook(point,', 'def hook(_world, point,', 1)
new_cases = ''.join(lines).encode('utf-8')
new_tree = ast.parse(new_cases.decode('utf-8'))
normalized = copy.deepcopy(new_tree)
for node in ast.walk(normalized):
    if isinstance(node, ast.FunctionDef) and node.name == 'hook':
        check(node.args.args[0].arg == '_world', 'Leading actual EntryWorld argument')
        del node.args.args[0]
check(ast.dump(normalized, include_attributes=False) == ast.dump(original_tree, include_attributes=False), 'All assertion/body/expression ASTs unchanged')
check(len(new_cases) == len(old_cases)+7*8, 'Only seven eight-byte argument additions')
new_cases_path = BASE / 'native25_component_cases_v2.py'
with new_cases_path.open('xb') as stream:
    stream.write(new_cases)

old_runner_path = BASE / 'run_native25_component_v2.py'
old_runner = old_runner_path.read_bytes()
runner_text = old_runner.decode('utf-8')
replacements = []
for name in ('ATTEMPT', 'PROOF', 'ARTIFACTS', 'FREEZE', 'BINDING'):
    before = 'NATIVE25-COMPONENT-'+name+'-v2'
    after = 'NATIVE25-COMPONENT-'+name+'-v3'
    check(runner_text.count(before) == 1, 'Unique fresh output/binding name: '+name)
    runner_text = runner_text.replace(before, after)
    replacements.append((before, after))
before = "'native25_component_cases_v1'"
after = "'native25_component_cases_v2'"
check(runner_text.count(before) == 1, 'Unique corrected case module loading name')
runner_text = runner_text.replace(before, after)
replacements.append((before, after))
reverse = runner_text
for before, after in replacements:
    reverse = reverse.replace(after, before)
check(reverse.encode('utf-8') == old_runner, 'Runner reverse text equality; accepted logic unchanged')
new_runner_path = BASE / 'run_native25_component_v3.py'
with new_runner_path.open('xb') as stream:
    stream.write(runner_text.encode('utf-8'))
for path in (new_cases_path, new_runner_path, Path(__file__).resolve()):
    text = path.read_bytes().decode('utf-8')
    ast.parse(text, filename=str(path))
    symtable.symtable(text, str(path), 'exec')

first_proof = BASE / 'NATIVE25-COMPONENT-PROOF-v2.json'
proof_pin = pin(first_proof)
check(proof_pin['sha256'].startswith('2519c0b1'), 'Exact retained first diagnostic proof')
delta_path = BASE / 'NATIVE25-COMPONENT-CALLBACK-DELTA-v3.json'
delta = write_json(delta_path, dict(
    schema_version=3, status='STATIC_CALLBACK_DECLARATION_DELTA_ONLY',
    authoring_scope=pin(scope), prior_cases=pin(old_cases_path), cases=pin(new_cases_path),
    prior_runner=pin(old_runner_path), runner=pin(new_runner_path), first_diagnostic=proof_pin,
    hook_count=7, old_positional_arguments=5, new_positional_arguments=6,
    leading_parameter='_world', declaration_source_lines=sorted(expected_lines),
    cases_bytes_added=56, normalized_cases_AST_equal=True,
    assertion_body_expression_AST_changes=0, runner_reverse_text_equal=True,
    runner_literal_replacements=[dict(before=a, after=b) for a,b in replacements],
    source_changes=0, source_imports=0, source_runs=0,
    expectation='No xfail: the two source kind-guard failures remain ordinary failures if reproduced. The ten previously masked runtime branch outcomes remain unknown before the separately bound control.'))

pins = dict(prior_freeze['pins'])
pins.update(cases=pin(new_cases_path), runner=pin(new_runner_path),
            callback_correction_scope=pin(scope), callback_correction_preparer=pin(Path(__file__).resolve()),
            prior_frozen_cases=pin(old_cases_path), prior_accepted_runner=pin(old_runner_path),
            prior_freeze=pin(prior_freeze_path), first_diagnostic=proof_pin, callback_delta=delta)
counts = dict(prior_freeze['counts'])
counts.pop('executed', None)
counts['executed_by_this_preparation'] = 0
prep_path = BASE / 'NATIVE25-COMPONENT-PREPARATION-v3.json'
prep = write_json(prep_path, dict(
    schema_version=3, status='METADATA_AST_ONLY_READY_FOR_INDEPENDENT_CALLBACK_DELTA_PEER',
    pins=pins, counts=counts, executable_branch_count=43,
    unchanged=['Kernel4', 'OwnerOps4', 'FileView4', 'codec4', 'support', 'world', 'inputs', 'matrix', 'assertions', 'runner logic'],
    historical_first_diagnostic=dict(proof=proof_pin, passed=31, failed=12, deferred=4, static_only=1,
                                     callback_masked_runtime_failures=10, source_kind_failures=2),
    prior_diagnostic_preserved=True,
    activity=dict(subject_imports=0, subject_runs=0, C_SDK_native_original_model_operations=0),
    independent_peer_required=True, separate_Root_execution_binding_required=True,
    qualification=dict(native25_complete=False, native_C=False, physical=False, real_resources=False, RSS=False)))
pins['callback_preparation'] = prep
freeze_path = BASE / 'NATIVE25-COMPONENT-FREEZE-v3.json'
freeze = write_json(freeze_path, dict(
    schema_version=3, status='FROZEN_AFTER_FIRST_DIAGNOSTIC_BEFORE_CORRECTED_CALLBACK_CONTROL',
    pins=pins, counts=counts, executable_branch_count=43,
    scope='Seven callback declaration parameters and mechanical runner names only; all Source4 subjects and expectations unchanged.',
    historical_first_diagnostic_preserved=True, corrected_control_executed=False,
    no_subject_changes=True, independent_peer_required=True, separate_Root_execution_binding_required=True,
    qualification=dict(native25_complete=False, native_C=False, physical=False, real_resources=False, RSS=False)))
outline_path = BASE / 'NATIVE25-COMPONENT-BINDING-OUTLINE-v3.json'
outline = write_json(outline_path, dict(
    schema_version=3, status='OUTLINE_ONLY_NOT_AUTHORIZED_TO_RUN',
    future_binding_filename='NATIVE25-COMPONENT-BINDING-v3.json',
    required_binding=dict(status='ROOT_BOUND_NATIVE25_COMPONENT_ONE_SHOT', run_authorized=True,
                          deadline_seconds=60, freeze=freeze,
                          execution_scope=dict(path='ROOT_TO_SUPPLY', bytes=None, sha256=None)),
    required_execution_scope_status='ROOT_AUTHORIZED_SINGLE_NATIVE25_COMPONENT_EXECUTION',
    invocation='python -I -B run_native25_component_v3.py only after independent exact callback-delta peer and Root binding',
    outputs=['NATIVE25-COMPONENT-ATTEMPT-v3.json', 'NATIVE25-COMPONENT-ARTIFACTS-v3', 'NATIVE25-COMPONENT-PROOF-v3.json'],
    one_shot=True, expected_failures_remain_failures=True, source_successor_authorized=False, qualification=False))
for key,item in pins.items():
    check(pin(Path(item['path'])) == item, 'Final frozen pin unchanged: '+key)
print(json.dumps(dict(cases=pin(new_cases_path), runner=pin(new_runner_path), delta=delta,
                      preparation=prep, freeze=freeze, outline=outline,
                      static_checks='AST/symtable and exact deltas PASS; no subject imports/runs'), indent=2))
