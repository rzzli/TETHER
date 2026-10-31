"""Retained JSON/pin review only; imports no subject or authored test code."""
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'ENTRY-E08-SUITE-BRANCH-CONSISTENCY-PROOF-v1.json'
checks = []
verified = {}


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read(value):
    actual = pin(value['path'])
    if actual['bytes'] != value['bytes'] or actual['sha256'] != value['sha256']:
        raise RuntimeError('changed retained metadata/source pin: ' + value['path'])
    verified[actual['path']] = actual
    return json.loads(Path(value['path']).read_bytes()) if value['path'].endswith('.json') else None


def strict(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return set(a) == set(b) and all(strict(a[k], b[k]) for k in a)
    if type(a) is list:
        return len(a) == len(b) and all(strict(x, y) for x, y in zip(a, b))
    return a == b


def check(name, okay, details=None):
    checks.append(dict(name=name, passed=bool(okay), details=details))


def no_io(world):
    return not world['actual_original_calls'] and not world['compiler_callbacks'] and not world['output_callbacks']


def error_code(value):
    return None if value is None else value['code']


def snapshot(world, suffix='first_wrapper_observed.json'):
    ref = next(a for a in world['artifacts'] if a['path'].endswith(suffix))
    # The separate Grammar byte lane verifies every artifact hash. Only these
    # few retained snapshot metadata objects are read for branch semantics.
    return json.loads(Path(ref['path']).read_bytes())


proof_ref = dict(path=str(HERE / 'ENTRY-E08-SUITE-PROOF-v1.json'), bytes=14195595,
    sha256='f1c1e9803e1128acbfd6343aa038d1ba81c902c075c770c3f8adf4b3f35073db')
proof = read(proof_ref)
binding = read(proof['binding'])
inputs = read(proof['inputs'])
freeze = read(proof['freeze'])
prep = read(proof['preparation'])
pause = read(proof['source_pause'])
read(binding['execution_scope'])
for value in list(proof['source_map'].values()) + list(prep['harness'].values()):
    read(value)
corpus = read(inputs['literal_corpus'])
scenarios = read(inputs['integration_scenarios'])
check('corrected_metadata_v2_active', proof['freeze']['sha256'] ==
      'cf4d6aac69665e5829f00004225058028d6af67792e31429b859323e460fc36d')
check('exact_source_and_harness_binding', proof['source_map'] == inputs['source_map'] ==
      freeze['source_map'] == binding['source_map'] and prep['harness'] == binding['harness'])
check('actual_source4_tcb_and_full_helper_prefix', inputs['kernel_pre_entry_tcb_bytes'] == 145042 and
      inputs['kernel_tcb']['pin']['sha256'] == proof['source_map']['preflight_entry_kernel_v4']['sha256'] and
      sum(v['bytes'] for v in inputs['helpers']) == 99000)
rows = proof['rows']
check('all122_exact_ordered_dispatches', len(rows) == 122 and
      [(r['branch'], r['group'], r['case'], r['variant'], r['coverage_class']) for r in rows] ==
      [(r['branch'], r['group'], r['case'], r['variant'], r['coverage_class']) for r in inputs['suite_branches']])
check('all122_actual_passes_no_hidden_errors', all(r['outcome'] == r['action_outcome'] == 'PASS' and
      not any(r[k] for k in ('first_error', 'deferred_reason', 'cleanup_errors', 'evidence_errors',
                            'source_world_constructor_errors')) for r in rows))
check('root_deadline_and_setup_clean', not any(proof[k] for k in ('setup_error', 'deadline_error',
      'cooperative_deadline_late', 'audit_denials', 'changed_pins')) and proof['elapsed_seconds'] < 60)
groups = {g: [r for r in rows if r['group'] == g] for g in proof['declared_groups']}
worlds = [w for r in rows for w in r['worlds']]
cores = [w for w in worlds if w['core_present']]
check('world_entry_core_totals', len(worlds) == 128 and
      sum(w['actual_entry_attempts'] for w in worlds) == 123 and len(cores) == 119)
check('same_original_binding_and_policy_attempt', all(w['policy_observation']['attempted'] is True and
      w['policy_observation']['selected_original_binding'] is True for w in cores))
check('honest_identity_comparison_availability', sum(w['source_identity_comparison_available'] for w in worlds) == 63 and
      all(w['source_identity_stable'] is (True if w['source_identity_comparison_available'] else None) for w in worlds))
policy_counts = dict(attempted=len(cores), prepared=sum(w['policy_observation']['prepared_report'] is not None for w in cores),
    issued=sum(w['policy_observation']['issued_report'] is not None for w in cores),
    eligible=sum(w['policy_observation']['execution_eligible'] for w in cores),
    original_policy_errors=sum(w['policy_observation']['original_error'] is not None for w in cores))
check('policy_axes_totals', policy_counts == dict(attempted=119, prepared=72, issued=70, eligible=64, original_policy_errors=49))

literal_summary = []
for row, golden in zip(groups['LITERALS'], corpus['vectors']):
    w = row['worlds'][0]; p = w['policy_observation']; e = golden['expected']
    okay = (row['case'] == golden['id'] and len(row['worlds']) == 1 and w['core_present'] and
            w['actual_entry_attempts'] == 1 and w['first_clock']['value'] == 100 and no_io(w) and
            w['policy_only'] and w['full_geometry'] is None and
            strict(w['policy_entry_basis_pins'], golden['entry_basis_pins']))
    if e['kind'] == 'REPORT':
        okay = okay and strict(p['prepared_report'], e['report']) and strict(p['issued_report'], e['report']) and \
            p['prepared_and_issued_same_object'] is True and p['original_error'] is None
        if e['report']['mode'] == 'EXECUTION':
            okay = okay and p['execution_eligible'] is True and error_code(w['policy_entry_error']) == 'INVALID_INPUT'
        else:
            okay = okay and p['execution_eligible'] is False and w['policy_entry_error'] is None
    else:
        okay = okay and p['prepared_report'] is None and p['issued_report'] is None and not p['execution_eligible'] and \
            error_code(p['original_error']) == error_code(w['policy_entry_error']) == e['code']
    check('literal/' + golden['id'], okay)
    literal_summary.append(dict(id=golden['id'], expected=e['kind'], policy_code=error_code(p['original_error']),
        report_status=None if p['issued_report'] is None else p['issued_report']['status'],
        later_entry_error=error_code(w['policy_entry_error']), full_entry_claim=False))
check('literal_10_reports_42_refusals_6exec_4authoring',
      collections.Counter(v['expected'] for v in literal_summary) == {'REPORT': 10, 'REFUSAL': 42} and
      collections.Counter(v['report_status'] for v in literal_summary if v['expected'] == 'REPORT') ==
      {'EXECUTION_BASIS_VALIDATED': 6, 'AUTHORING_ONLY': 4})

integration = {(r['case'], r['variant']): r for r in groups['INTEGRATION']}
check('integration_exact15_strings', list(integration) ==
      [(s['id'], b) for s in scenarios['scenarios'] for b in s['branches']])
iw = lambda case, variant: integration[(case, variant)]['worlds']
w = iw('I01', 'original_entry_order')[0]
check('I01_original_clock_then_real_helpers', w['first_clock']['value'] == 100 and
      w['source_identity_stable'] is True and len(w['compiler_callbacks']) == 3 and
      w['policy_observation']['execution_eligible'] is True)
w = iw('I02', 'authoring_only_barrier')[0]
check('I02_authoring_public_barriers', no_io(w) and w['policy_observation']['issued_report']['status'] == 'AUTHORING_ONLY' and
      w['policy_observation']['execution_eligible'] is False)
w = iw('I03', 'execution_same_core_handoff')[0]
check('I03_actual_same_core_complete', w['source_identity_stable'] is True and
      {v['module'] for v in w['compiler_callbacks']} == {h['module'] for h in inputs['helpers']} and
      len(w['actual_original_calls']) == 37 and sum(w['close_attempts'].values()) == 5 and
      snapshot(w)['data']['pure_seam_complete'] is True)
for variant in ('caller_container_alias', 'ordinary_rebinding'):
    w = iw('I04', variant)[0]
    check('I04/' + variant, w['source_identity_stable'] is True and w['policy_observation']['execution_eligible'] is True)
a, b = iw('I04', 'foreign_equal_source_binding')
check('I04_actual_foreign_namespace', a['core_present'] and error_code(a['policy_observation']['original_error']) ==
      'FOREIGN_POLICY_BINDING' and no_io(a) and not b['core_present'] and b['actual_entry_attempts'] == 0)
a, b = iw('I05', 'once_only_and_cold_observation')
check('I05_cached_and_failure_once_only', a['policy_observation']['prepared_and_issued_same_object'] is True and
      error_code(b['policy_observation']['original_error']) == 'POLICY_FORBIDDEN_ANCESTRY' and no_io(b))
for case, variant, prepared, error_type, code in [
    ('I06', 'report_allocation_before_return', False, 'builtins.MemoryError', None),
    ('I07', 'prepared_then_final_work_clock', True, 'preflight_entry_kernel_v4.KernelRefusal', 'WORK_DEADLINE'),
    ('I07', 'prepared_then_issuance_bookkeeping_failure', True, 'builtins.MemoryError', None)]:
    w = iw(case, variant)[0]; p = w['policy_observation']; data = snapshot(w)['data']
    check(case + '/' + variant, no_io(w) and (p['prepared_report'] is not None) is prepared and
          p['issued_report'] is None and not p['execution_eligible'] and
          p['original_error']['type'] == error_type and error_code(p['original_error']) == code and
          strict(p['original_error'], w['original_primary']) and
          data['manifest_policy']['error_identity'] == data['errors']['primary']['identity'])
a, b, c = iw('I08', 'data_report_is_not_capability')
check('I08_data_does_not_mint_authority', no_io(a) and a['policy_observation']['execution_eligible'] is False and
      len(b['compiler_callbacks']) == 3 and c['policy_observation']['issued_report'] is None and
      error_code(c['policy_observation']['original_error']) == 'FOREIGN_POLICY_BINDING' and no_io(c))
for variant, close, now in [('fresh_cleanup_after_later_work_error', 1, 396),
                            ('cleanup_blocked_at_original_hard_end', 0, 400)]:
    w = iw('I09', variant)[0]
    check('I09/' + variant, w['policy_observation']['execution_eligible'] is True and
          w['policy_observation']['original_error'] is None and w['original_primary']['type'] == 'builtins.MemoryError' and
          sum(w['close_attempts'].values()) == close and w['origin']['start']['value'] == 100 and
          w['origin']['now']['value'] == now)
a = iw('I10', 'constructor_structural_refusal')[0]
b = iw('I10', 'valid_shell_bad_semantics_reaches_core')[0]
check('I10_real_constructor_core_split', not a['core_present'] and a['actual_entry_attempts'] == 0 and
      a['first_clock']['tag'] == 'UNOBSERVED' and no_io(a) and b['core_present'] and
      b['first_clock']['value'] == 100 and error_code(b['policy_observation']['original_error']) == 'POLICY_DOMAIN')

old_path = HERE.parent / 'recovery-step9-entry-contract-tests-20261030/ENTRY-CONTRACT-SUITE-PROOF-v2.json'
old = read(dict(path=str(old_path), bytes=6337722,
    sha256='5c193cdb20df9fca83641059ed3c2ae419ff36ba05bdfb42ab1f5ffaf9cda7a1'))
previous = {(r['case'], r['variant']): r for r in old['rows']}
def spy_shape(w):
    return [(c['api'], c['ordinal'], c['scalar_hook_completed'], c['count_hook_completed'],
             c['normal_return_prepared']) for c in w['actual_original_calls']]
for row in groups['CAUSAL']:
    prior = previous[(row['case'], row['variant'])]
    check('causal/' + row['branch'], prior['outcome'] == 'PASS' and
          len(prior['worlds']) == len(row['worlds']) and all(spy_shape(a) == spy_shape(b)
          for a, b in zip(prior['worlds'], row['worlds'])))
check('old_source3_three_defers_unchanged', old['counts']['DEFERRED'] == 3 and
      not any(r['case'] == 'E08' or (r['case'] == 'E16' and r['variant'] != 'foreign_attach')
              for r in groups['CAUSAL']))
stream = next(r for r in groups['CAUSAL'] if r['case'] == 'E32')['worlds'][0]
check('E32_actual_new_source4_stream', len(stream['actual_original_calls']) == 3842 and
      sum(c['api'] == 'ReadFile' for c in stream['actual_original_calls']) == 3812 and
      sum(stream['close_attempts'].values()) == 5 and sum(stream['delivered_bytes'].values()) == 3992098940 and
      stream['full_geometry'] == inputs['large_geometry'])
check('qualification_stays_source_pure', proof['complete_entry_gate'] is False and
      proof['metadata_report_is_full_entry_success'] is False and proof['native25'] == 'NOT_EXECUTED' and
      not any(proof['qualification'][k] for k in ('native', 'physical_io', 'real_first_entry',
              'whole_r09', 'full_real_roster', 'resource_fit', 'scientific')))

group_summary = {}
for group, group_rows in groups.items():
    values = [w for r in group_rows for w in r['worlds']]
    apis = collections.Counter(c['api'] for w in values for c in w['actual_original_calls'])
    group_summary[group] = dict(dispatches=len(group_rows), worlds=len(values),
        actual_entry_attempts=sum(w['actual_entry_attempts'] for w in values),
        cores=sum(w['core_present'] for w in values), original_callback_counts=dict(apis),
        original_callbacks=sum(apis.values()), close_attempts=sum(sum(w['close_attempts'].values()) for w in values))
result = dict(schema_version=1, status='PASS' if all(v['passed'] for v in checks) else 'HOLD',
    scope='RETAINED_SOURCE4_BRANCH_SOURCE_BINDING_POLICY_OBSERVATIONS_ONLY',
    proof=proof_ref, checker=pin(__file__), checks=checks,
    counts=dict(checks=len(checks), passed=sum(v['passed'] for v in checks), failed=sum(not v['passed'] for v in checks)),
    verified_metadata_source_harness_pins=list(verified.values()), group_summary=group_summary,
    policy_axes=policy_counts, literal_outcomes=literal_summary,
    byte_lane='Grammar independently verifies every retained artifact/hash/row/query; not duplicated here.',
    identity_limit='JSON labels do not recreate identity. Genuine is-assertions are the frozen executed test evidence; selected opaque labels are checked for consistency only.',
    activity=dict(subject_imports=0, subject_runs=0, source_calls=0, producer_replays=0, native_or_original_target_operations=0),
    qualification=False)
raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode()
with OUT.open('xb') as stream:
    stream.write(raw)
print(json.dumps(dict(status=result['status'], report=pin(OUT), counts=result['counts'], group_summary=group_summary)))
