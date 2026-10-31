"""Three source-specific refusal-code errata; metadata/AST only, no subject run."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import symtable

BASE = Path(__file__).resolve().parent
ASSETS = BASE.parent


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def document(path):
    return json.loads(path.read_bytes())


def write_json(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False)+'\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)
    return pin(path)


def require(ok, message):
    if not ok:
        raise AssertionError(message)


prior_freeze_path = BASE / 'NATIVE25-COMPONENT-FREEZE-v3.json'
prior_freeze = document(prior_freeze_path)
for item in prior_freeze['pins'].values():
    require(pin(Path(item['path'])) == item, 'Preserved prior frozen pin: '+item['path'])
base_contract_path = ASSETS / 'recovery-step9-production-preflight-20261029' / 'NATIVE-RAW-CARRIER-AND-BULK-LEASE-CONTRACT-v1.json'
kernel_path = Path(prior_freeze['pins']['subject_preflight_entry_kernel_v4']['path'])
accepted_cases_path = ASSETS / 'recovery-step9-entry-source4-20261030' / 'entry_contract_cases_source4_v1.py'
accepted_root_path = ASSETS / 'recovery-step9-entry-source4-20261030' / 'ENTRY-E08-SUITE-ROOT-ACCEPTANCE-v1.json'
first_control_path = BASE / 'NATIVE25-COMPONENT-PROOF-v3.json'
first_control_pin = pin(first_control_path)
require(first_control_pin['sha256'] == 'bca943d0e85c32c6575b4e0225fd152777200041bb81a983d8ed01bb431f0892', 'Exact first corrected-callback control')

old_cases_path = BASE / 'native25_component_cases_v2.py'
old_cases = old_cases_path.read_bytes()
text = old_cases.decode('utf-8')
changes = [
    ("    refused(ctx, lambda: ctx.call(w.state.port.acquire, w.specs[-2]), 'INVALID_INPUT')",
     "    refused(ctx, lambda: ctx.call(w.state.port.acquire, w.specs[-2]), 'RAW_RETURN_UNKNOWN')"),
    ("    refused(ctx, lambda: ctx.call(w.state.port.hash_capture, ref), 'INVALID_INPUT')",
     "    refused(ctx, lambda: ctx.call(w.state.port.hash_capture, ref), 'READ_COUNT_UNKNOWN' if false else 'READ_PROGRESS_INCOMPLETE')"),
]
for before, after in changes:
    require(text.count(before) == 1, 'Unique expected-code assertion site')
    text = text.replace(before, after)
original_ast = ast.parse(old_cases.decode('utf-8'))
changed_ast = ast.parse(text)
normalized = copy.deepcopy(changed_ast)
normalized_sites = 0
for function in normalized.body:
    if isinstance(function, ast.FunctionDef) and function.name in ('n04_runtime', 'read_case'):
        calls = [node for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'refused']
        require(len(calls) == 1 and len(calls[0].args) == 3, 'One exact refusal assertion in '+function.name)
        code = calls[0].args[2]
        if function.name == 'n04_runtime':
            require(isinstance(code, ast.Constant) and code.value == 'RAW_RETURN_UNKNOWN', 'N04 exact code')
        else:
            require(ast.dump(code, include_attributes=False) == ast.dump(ast.parse("'READ_COUNT_UNKNOWN' if false else 'READ_PROGRESS_INCOMPLETE'", mode='eval').body, include_attributes=False), 'N06/N07 exact conditional code')
        calls[0].args[2] = ast.Constant(value='INVALID_INPUT')
        normalized_sites += 1
require(normalized_sites == 2, 'Two code-expression AST sites covering three branches')
require(ast.dump(normalized, include_attributes=False) == ast.dump(original_ast, include_attributes=False), 'Every other assertion/input/body AST unchanged')
new_cases_path = BASE / 'native25_component_cases_v3.py'
with new_cases_path.open('xb') as stream:
    stream.write(text.encode('utf-8'))

old_runner_path = BASE / 'run_native25_component_v3.py'
old_runner = old_runner_path.read_bytes()
runner = old_runner.decode('utf-8')
runner_changes = []
for kind in ('ATTEMPT', 'PROOF', 'ARTIFACTS', 'FREEZE', 'BINDING'):
    before = 'NATIVE25-COMPONENT-'+kind+'-v3'
    after = 'NATIVE25-COMPONENT-'+kind+'-v4'
    require(runner.count(before) == 1, 'One fresh runner literal: '+kind)
    runner = runner.replace(before, after)
    runner_changes.append((before, after))
before, after = "'native25_component_cases_v2'", "'native25_component_cases_v3'"
require(runner.count(before) == 1, 'One case-module load name')
runner = runner.replace(before, after)
runner_changes.append((before, after))
reverse = runner
for before, after in runner_changes:
    reverse = reverse.replace(after, before)
require(reverse.encode('utf-8') == old_runner, 'Runner logic reverse-text equality')
new_runner_path = BASE / 'run_native25_component_v4.py'
with new_runner_path.open('xb') as stream:
    stream.write(runner.encode('utf-8'))
for path in (new_cases_path, new_runner_path, Path(__file__).resolve()):
    source = path.read_bytes().decode('utf-8')
    ast.parse(source, filename=str(path))
    symtable.symtable(source, str(path), 'exec')

errata_path = BASE / 'NATIVE25-EXPECTED-CODE-ERRATA-v4.json'
errata = write_json(errata_path, dict(
    schema_version=1, status='NORMATIVE_SPECIFIC_CODE_ERRATA_READY_FOR_INDEPENDENT_REVIEW',
    authorization='Root direct task: independently assess N04.2/N06.1/N07.1 normative support; if supported author only three exact-code corrections with Source4 unchanged. This record is delegated-author provenance, not an execution scope.',
    evidence=dict(base_contract=pin(base_contract_path), unchanged_source4_kernel=pin(kernel_path),
                  prior_accepted_source4_E22=pin(accepted_cases_path), prior_acceptance=pin(accepted_root_path),
                  prior_matrix=prior_freeze['pins']['matrix'], callback_control=first_control_pin),
    corrections=[
        dict(branch='N04.2', old='INVALID_INPUT', exact='RAW_RETURN_UNKNOWN',
             normative='N04_committed_native_NULL expected committed native NULL, usable_handle false, and ownership UNKNOWN_OR_REFUSED; no INVALID_INPUT code is prescribed.',
             implementation='Unchanged Source4 _BootstrapPrimitives.acquire line1621 requires usable(c.scalar) with RAW_RETURN_UNKNOWN after retaining the committed raw scalar. NULL gives no close right.',
             prior_accepted='Actual accepted Source4 E22 handle_NULL/handle0 cases catch semantic refusal without requiring INVALID_INPUT and assert exact native/Python delivery plus no usable close right.',
             unchanged='Native zero retained, no close reservation/right, no CloseHandle call.'),
        dict(branch='N06.1', old='INVALID_INPUT', exact='READ_PROGRESS_INCOMPLETE',
             normative='N06_true_count_zero explicitly requires count_defined true, known_count0, progress0 and remaining_nonzero READ_PROGRESS_INCOMPLETE.',
             implementation='Unchanged Source4 hash_capture line1688 accepts defined true count0, then line1689 rejects count<=0 with READ_PROGRESS_INCOMPLETE before hash/copy progress or retry.',
             prior_mapping_error='Frozen matrix v2 N06 branch prose and preparation expectation footer incorrectly said existing kernel INVALID_INPUT. Its normative_expected and the earlier base contract already name READ_PROGRESS_INCOMPLETE. Preserve the matrix unchanged and apply this explicit source-code mapping erratum.',
             unchanged='Count COMMITTED0/defined true, known bytes/hash/capture0, no complete hash, exactly one read/no retry.'),
        dict(branch='N07.1', old='INVALID_INPUT', exact='READ_COUNT_UNKNOWN',
             normative='N07_false_count_zero requires count_defined false, raw_count0, progress0, error_value_defined true, and error word0 observed rather than unknown; it does not prescribe INVALID_INPUT.',
             implementation='Unchanged Source4 hash_capture line1688 rejects undefined count through READ_COUNT_UNKNOWN before the positive-progress guard. The scalar failure, raw COUNT0 and independent error DWORD0/definitionTrue remain retained.',
             unchanged='Count COMMITTED0/defined false, progress/hash/capture0, error DWORD0 independently observed and defined, exactly one read/no retry.')],
    materiality='These are exact specific refusals, not accepted-code sets, xfail, dropped cases or source normalization. Two N25 API/axis kind-guard failures remain unmodified diagnostic failures.',
    source_changes=0, subject_imports=0, subject_runs=0))
delta_path = BASE / 'NATIVE25-COMPONENT-EXPECTED-CODE-DELTA-v4.json'
delta = write_json(delta_path, dict(
    schema_version=4, status='THREE_EXACT_EXPECTED_CODE_CORRECTIONS_ONLY',
    prior_cases=pin(old_cases_path), cases=pin(new_cases_path), prior_runner=pin(old_runner_path), runner=pin(new_runner_path),
    errata=errata, changed_branches=['N04.2', 'N06.1', 'N07.1'], code_expression_sites=2,
    normalized_whole_cases_AST_equal=True, all_other_state_input_no_retry_assertions_unchanged=True,
    runner_reverse_text_equal=True, runner_literal_replacements=[dict(before=a, after=b) for a,b in runner_changes],
    first_callback_control_preserved=first_control_pin, source4_unchanged=True, subject_imports=0, subject_runs=0))
pins = dict(prior_freeze['pins'])
pins.update(cases=pin(new_cases_path), runner=pin(new_runner_path),
            expected_code_preparer=pin(Path(__file__).resolve()), expected_code_errata=errata,
            expected_code_delta=delta, prior_callback_cases=pin(old_cases_path), prior_callback_runner=pin(old_runner_path),
            prior_callback_freeze=pin(prior_freeze_path), first_callback_control=first_control_pin,
            base_native_contract=pin(base_contract_path), prior_accepted_E22=pin(accepted_cases_path), prior_source4_acceptance=pin(accepted_root_path))
counts = dict(prior_freeze['counts'])
prep_path = BASE / 'NATIVE25-COMPONENT-PREPARATION-v4.json'
prep = write_json(prep_path, dict(
    schema_version=4, status='METADATA_AST_ONLY_THREE_EXACT_CODE_ERRATA_PREPARATION', pins=pins,
    counts=counts, executable_branch_count=43,
    prior_callback_control=dict(proof=first_control_pin, passed=38, failed=5, deferred=4, static_only=1),
    corrected_control_executed=False, kind_guard_expectations_unchanged=True,
    separate_independent_errata_peer_and_Root_execution_binding_required=True,
    activity=dict(subject_imports=0, subject_runs=0, source_changes=0, C_SDK_native_original_model_operations=0)))
pins['expected_code_preparation'] = prep
freeze_path = BASE / 'NATIVE25-COMPONENT-FREEZE-v4.json'
freeze = write_json(freeze_path, dict(
    schema_version=4, status='FROZEN_EXPECTED_CODE_ERRATA_BEFORE_SECOND_HARNESS_CONTROL', pins=pins,
    counts=counts, executable_branch_count=43, prior_both_actual_controls_preserved=True,
    source4_unchanged=True, kind_guard_expectations_unchanged=True,
    corrected_control_executed=False, separate_independent_peer_and_Root_binding_required=True,
    qualification=dict(native25_complete=False, native_C=False, physical=False, real_resources=False, RSS=False)))
outline = write_json(BASE / 'NATIVE25-COMPONENT-BINDING-OUTLINE-v4.json', dict(
    schema_version=4, status='OUTLINE_ONLY_NOT_AUTHORIZED_TO_RUN',
    future_binding_filename='NATIVE25-COMPONENT-BINDING-v4.json',
    required_binding=dict(status='ROOT_BOUND_NATIVE25_COMPONENT_ONE_SHOT', run_authorized=True,
                          deadline_seconds=60, freeze=freeze,
                          execution_scope=dict(path='ROOT_TO_SUPPLY', bytes=None, sha256=None)),
    required_execution_scope_status='ROOT_AUTHORIZED_SINGLE_NATIVE25_COMPONENT_EXECUTION',
    invocation='python -I -B run_native25_component_v4.py only after independent errata peer and Root binding',
    outputs=['NATIVE25-COMPONENT-ATTEMPT-v4.json', 'NATIVE25-COMPONENT-ARTIFACTS-v4', 'NATIVE25-COMPONENT-PROOF-v4.json'],
    one_shot=True, kind_guard_failures_remain_failures=True, source_successor_authorized=False, qualification=False))
for name,item in pins.items():
    require(pin(Path(item['path'])) == item, 'Final pin unchanged: '+name)
print(json.dumps(dict(cases=pin(new_cases_path), runner=pin(new_runner_path), errata=errata,
                      delta=delta, preparation=prep, freeze=freeze, outline=outline,
                      AST_and_symtable='PASS', subject_imports=0, subject_runs=0), indent=2))
