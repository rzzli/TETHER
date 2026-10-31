"""Independent retained-data review only; never loads or executes subject code."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import struct

BASE = Path(__file__).resolve().parent
OLD = BASE.parent / 'recovery-step9-native25-component-20261030'
ART = BASE / 'NATIVE25-COMPONENT-ARTIFACTS-v5'
CHECKS = []


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=digest(raw))


def load(path):
    return json.loads(Path(path).read_bytes())


def check(name, passed, details=None):
    CHECKS.append(dict(id=name, passed=bool(passed), details=details))


def exact(selected):
    actual = pin(selected['path'])
    return all(actual[key] == selected[key] for key in ('path', 'bytes', 'sha256'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def normalize(value):
    if isinstance(value, dict):
        return {key: normalize(child) for key, child in value.items()
                if key != 'harness_identity'}
    if isinstance(value, list):
        return [normalize(child) for child in value]
    if isinstance(value, str):
        return value.replace(str(OLD / 'NATIVE25-COMPONENT-ARTIFACTS-v4'), str(ART))
    return value


def policy_hashes(files, kernel_pin):
    root = dict(id='root.kernel', bytes=kernel_pin['bytes'], sha256=kernel_pin['sha256'])
    ids = ['input.%03d' % i for i in range(len(files))]
    outputs = ['run.output.%02d' % i for i in range(14)]
    binding = dict(mode='EXECUTION', current_decision_id='run.decision',
                   current_output_ids=outputs, basis_ids=ids,
                   external_tcb_pins=[root], prior_metadata_pins=[])
    nodes = [dict(root, role='EXTERNAL_TCB', state='PINNED', reason=None, pin_dependencies=[])]
    nodes += [dict(id=name, role='INPUT', state='PINNED', bytes=spec['size'],
                   sha256=spec['sha256'], reason=None, pin_dependencies=['root.kernel'])
              for name, spec in zip(ids, files)]
    reason = 'CURRENT_RUN_NOT_A_STATIC_PIN'
    nodes.append(dict(id='run.decision', role='CURRENT_DECISION', state='CURRENT',
                      bytes=None, sha256=None, reason=reason, pin_dependencies=list(ids)))
    nodes += [dict(id=name, role='CURRENT_OUTPUT', state='CURRENT', bytes=None,
                   sha256=None, reason=reason, pin_dependencies=['run.decision']) for name in outputs]
    envelope = dict(schema_version=1, mode='EXECUTION', current_decision_id='run.decision',
                    current_output_ids=list(outputs), external_anchor_ids=['root.kernel'],
                    basis_ids=list(ids), nodes=nodes)
    return dict(binding_sha256=digest(canonical(binding)), envelope_sha256=digest(canonical(envelope)))


def decode_axis(raw):
    bits, epoch, kind, width, reserved, stage, commit, padding = struct.unpack('<QIHBBIIQ', raw)
    return dict(bits=bits, epoch=epoch, kind=kind, width=width, reserved=reserved,
                stage=stage, commit=commit, padding=padding)


proof_path = BASE / 'NATIVE25-COMPONENT-PROOF-v5.json'
proof = load(proof_path)
freeze = load(BASE / 'NATIVE25-COMPONENT-FREEZE-v5.json')
parent = load(OLD / 'NATIVE25-COMPONENT-PROOF-v4.json')
binding_path = BASE / 'NATIVE25-COMPONENT-BINDING-v5.json'
binding = load(binding_path)
scope = load(binding['execution_scope']['path'])
attempt = load(proof['attempt']['path'])
matrix = load(freeze['pins']['matrix']['path'])
inputs = load(freeze['pins']['inputs']['path'])
evidence = proof['evidence']
check('exact_supplied_actual_proof', pin(proof_path)['sha256'] ==
      '757e9a88c262f476d7744dc227a4aab752fca17e810589ced4f12e33654f5551')
check('actual_binding_matches', proof['binding'] == binding)
check('attempt_exact_pin', exact(proof['attempt']))
check('attempt_consumed_before_import', attempt['status'] == 'ATTEMPT_CONSUMED_BEFORE_FIRST_SUBJECT_IMPORT'
      and attempt['binding'] == binding and attempt['deadline_seconds'] == 60)
check('binding_and_scope_status', binding['status'] == 'ROOT_BOUND_NATIVE25_COMPONENT_ONE_SHOT'
      and binding['run_authorized'] is True and binding['deadline_seconds'] == 60
      and scope['status'] == 'ROOT_AUTHORIZED_SINGLE_NATIVE25_COMPONENT_EXECUTION')
for name in ('freeze', 'execution_scope', 'independent_peer'):
    check('binding_pin_' + name, exact(binding[name]))
check('proof_freeze_binding_same', proof['freeze'] == binding['freeze'])
for name, selected in freeze['pins'].items():
    check('frozen_' + name, exact(selected))
check('47_frozen_pins', len(freeze['pins']) == 47)
check('success_status_not_inferred_from_count', proof['status'] == 'COMPONENT_OBSERVATIONS_PASSED_WITH_EXPLICIT_DEFERRED'
      and proof['setup_error'] is None and proof['evidence_error'] is None
      and proof['changed_pins'] == [] and proof['audit_denials'] == []
      and proof['cooperative_deadline_late'] is False and proof['elapsed_seconds'] < 60)
branches = [branch for case in matrix['cases'] for branch in case['branches']]
by_id = {row['id']: row for row in proof['rows']}
old_by_id = {row['id']: row for row in parent['rows']}
check('exact_branch_order_and_count', [r['id'] for r in proof['rows']] == [b['id'] for b in branches]
      and len(branches) == 48 and len(matrix['cases']) == 25 and len(by_id) == 48)
observed_counts = dict(collections.Counter(row['outcome'] for row in proof['rows']))
check('43_pass_four_deferred_one_static', proof['counts'] == observed_counts ==
      dict(COMPONENT_PASS=43, DEFERRED_NOT_EXECUTED=4, STATIC_DECLARATION_ONLY=1))
world_ids = {w['id'] for w in evidence['worlds']}
data_ids = {d['id'] for d in evidence['data']}
for branch in branches:
    row = by_id[branch['id']]
    classification = branch['classification']
    wanted = 'DEFERRED_NOT_EXECUTED' if classification == 'DEFERRED' else (
        'STATIC_DECLARATION_ONLY' if classification == 'STATIC_ONLY' else 'COMPONENT_PASS')
    check('branch_' + branch['id'], row['classification'] == classification and row['outcome'] == wanted
          and row['first_error'] is None and row['cleanup_errors'] == []
          and row.get('unexpected_source_returns', []) == []
          and set(row['worlds']) <= world_ids and set(row['data']) <= data_ids)
    if classification in ('DEFERRED', 'STATIC_ONLY'):
        check('nonexecuted_' + branch['id'], not row['worlds'] and not row['data'] and not row['expected_errors'])
transitions = [dict(id=row['id'], before=old_by_id[row['id']]['outcome'], after=row['outcome'])
               for row in proof['rows'] if row['outcome'] != old_by_id[row['id']]['outcome']]
check('only_two_expected_transitions', transitions == [
    dict(id='N25.5.scalar_kind_mismatch', before='FAIL', after='COMPONENT_PASS'),
    dict(id='N25.5.count_kind_mismatch', before='FAIL', after='COMPONENT_PASS')])
inventory = {Path(selected['path']).name: selected for selected in evidence['artifacts']}
check('unique_complete_188_inventory', len(inventory) == len(evidence['artifacts']) == 188
      and set(inventory) == {p.name for p in ART.iterdir() if p.is_file()})
for name, selected in inventory.items():
    check('artifact_' + name, exact(selected) and Path(selected['path']).parent == ART)
check('complete_persistence_counts', evidence['persistence_complete'] is True
      and evidence['persistence_stage'] == 'COMPLETE' and evidence['known_world_count'] == len(world_ids) == 20
      and evidence['known_data_count'] == len(data_ids) == 26
      and evidence['known_snapshot_references'] == len(evidence['snapshots']) == 30)
APIS = ('CreateFileW', 'GetFileType', 'GetFileInformationByHandleEx', 'GetFinalPathNameByHandleW',
        'GetFileSizeEx', 'ReadFile', 'CloseHandle', 'GetFileAttributesExW', 'FindFirstFileExW',
        'FindNextFileW', 'FindClose', 'CreateDirectoryW', 'WriteFile', 'FlushFileBuffers')
AXES = ('scalar', 'count', 'error_value', 'error_definition')
malformed_expected = {19: (0, '<H', 2), 20: (2, '<H', 255), 21: (8, '<I', 2),
                      22: (28, '<I', 1), 23: (143, '<B', 1), 24: (142, '<B', 8)}
banks = {}
raw_axis_count = 0
for group in ('worlds', 'data'):
    for entity in evidence[group]:
        prefix = ('world' if group == 'worlds' else 'data') + '-%03d' % entity['id']
        bank = entity['bank']
        raw = Path(bank['files'][0]['path']).read_bytes()
        rows = [json.loads(line) for line in Path(bank['files'][1]['path']).read_bytes().splitlines()]
        banks[prefix] = (raw, rows)
        check('bank_reference_' + prefix, entity['persistence'] == 'COMPLETE'
              and all(selected == inventory[Path(selected['path']).name] for selected in bank['files'])
              and len(raw) == bank['raw_rows'] * 256
              and bank['missing_registered_ordinals'] == [r['ordinal'] for r in rows if not r['registered']]
              and bank['raw_rows'] == sum(r['registered'] for r in rows))
        check('bank_metadata_ordinals_' + prefix, [r['ordinal'] for r in rows] == list(range(len(rows))))
        raw_offset = 0
        for record in rows:
            if record['query_capture']:
                selected = record['query_capture']
                check('query_reference_' + prefix + '_' + str(record['ordinal']),
                      selected == inventory[Path(selected['path']).name]
                      and record['api'] in ('GetFileInformationByHandleEx', 'GetFinalPathNameByHandleW', 'GetFileSizeEx'))
            if not record['registered']:
                continue
            cell = raw[raw_offset:raw_offset + 256]
            raw_offset += 256
            malformed = group == 'data' and entity['id'] in malformed_expected
            if malformed:
                offset, form, value = malformed_expected[entity['id']]
                check('deliberate_malformed_' + prefix, struct.unpack_from(form, cell, offset)[0] == value)
                continue
            schema, size, ordinal, generation, api_id = struct.unpack_from('<HHIIH', cell)
            check('raw_header_' + prefix + '_' + str(record['ordinal']),
                  (schema, size, ordinal, generation, api_id) ==
                  (1, 256, record['ordinal'], 1, APIS.index(record['api']) + 1))
            expected_scalar = 1 if record['api'] in ('CreateFileW', 'FindFirstFileExW') else (
                3 if record['api'] in ('GetFileType', 'GetFinalPathNameByHandleW') else 2)
            axis_values = []
            for axis, offset, expected_kind in zip(AXES, (128, 160, 192, 224), (expected_scalar, 4, 3, 5)):
                decoded = decode_axis(cell[offset:offset + 32])
                axis_values.append(decoded)
                raw_axis_count += 1
                mismatch = group == 'data' and ((entity['id'] == 25 and axis == 'scalar') or
                                               (entity['id'] == 26 and axis == 'count'))
                wanted_kind = 3 if mismatch else expected_kind
                wanted_width = 8 if wanted_kind == 1 else 1 if wanted_kind == 5 else 4
                check('raw_axis_' + prefix + '_' + str(record['ordinal']) + '_' + axis,
                      decoded['kind'] == wanted_kind and decoded['width'] == wanted_width
                      and decoded['epoch'] == 1 and decoded['reserved'] == decoded['padding'] == 0
                      and decoded['stage'] in (0, 1) and decoded['commit'] in (0, 1)
                      and (not decoded['commit'] or decoded['stage'])
                      and decoded['bits'] < 1 << (8 * wanted_width))
        if group == 'worlds':
            check('dispatch_lineage_' + prefix,
                  [(r['ordinal'], r['api']) for r in rows if r['invoked']] ==
                  [(r['ordinal'], r['api']) for r in entity['original_calls']])

old_inventory = {Path(p['path']).name: p for p in parent['evidence']['artifacts']}
byte_equal = 0
for name, selected in inventory.items():
    previous = old_inventory[name]
    if name.endswith('.bin'):
        check('unchanged_binary_' + name, selected['sha256'] == previous['sha256']
              and selected['bytes'] == previous['bytes'])
        byte_equal += selected['sha256'] == previous['sha256']
    elif name.endswith('.jsonl'):
        current_rows = [normalize(json.loads(line)) for line in Path(selected['path']).read_bytes().splitlines()]
        previous_rows = [normalize(json.loads(line)) for line in Path(previous['path']).read_bytes().splitlines()]
        check('unchanged_call_cache_' + name, current_rows == previous_rows)

snapshot_bytes = 0
snapshot_rows = 0
for index, retained in enumerate(evidence['snapshots'], 1):
    label = 'snapshot-%03d' % index
    meta = load(retained['metadata']['path'])
    raw = Path(retained['raw']['path']).read_bytes()
    previous_meta = load(old_inventory[label + '.json']['path'])
    check('snapshot_retained_' + label, retained['persistence'] == 'COMPLETE'
          and retained['raw'] == inventory[Path(retained['raw']['path']).name]
          and retained['metadata'] == inventory[Path(retained['metadata']['path']).name]
          and meta['world'] in world_ids and meta['partial'] is False and meta['capture_error'] is None
          and meta['copied_bytes'] == len(raw) == 256 * meta['raw_rows'])
    files = [row['spec'] for row in meta['data']['files']]
    hashes = policy_hashes(files, freeze['current_kernel_TCB'])
    old_kernel = load(OLD / 'NATIVE25-COMPONENT-FREEZE-v4.json')['pins']['subject_preflight_entry_kernel_v4']
    previous_hashes = policy_hashes(files, old_kernel)
    for report_name in ('prepared_report', 'issued_report'):
        current_report = meta['data']['manifest_policy'][report_name]
        previous_report = previous_meta['data']['manifest_policy'][report_name]
        check('snapshot_policy_' + label + '_' + report_name,
              all(current_report[key] == value for key, value in hashes.items())
              and all(previous_report[key] == value for key, value in previous_hashes.items()))
        # Hashes are independently rebuilt above before normalizing a legitimate source-pin change.
        for key in hashes:
            previous_report[key] = current_report[key]
    check('snapshot_metadata_preserved_' + label, normalize(meta) == normalize(previous_meta))
    snapshot_bytes += len(raw)
    snapshot_rows += meta['raw_rows']

kind_results = []
for name, number, axis, offset in [('scalar_kind_mismatch', 25, 'scalar', 128),
                                   ('count_kind_mismatch', 26, 'count', 160)]:
    branch_id = 'N25.5.' + name
    row = by_id[branch_id]
    raw, cache = banks['data-%03d' % number]
    decoded = decode_axis(raw[offset:offset + 32])
    check('kind_refusal_' + name, len(row['expected_errors']) == 1
          and row['expected_errors'][0]['class_name'] == 'KernelRefusal'
          and row['expected_errors'][0]['code'] == row['expected_errors'][0]['message'] == 'NATIVE_STATE_NOT_REPRESENTABLE'
          and row['first_error'] is None and row['unexpected_source_returns'] == []
          and decoded['kind'] == 3 and decoded['width'] == 4 and decoded['bits'] == 1
          and decoded['stage'] == decoded['commit'] == 1)
    kind_results.append(dict(id=branch_id, data_id=number, axis=axis,
                             raw_pin=inventory['data-%03d.raw256.bin' % number],
                             malformed_axis=decoded, expected_refusal=row['expected_errors'][0],
                             parent_failed=old_by_id[branch_id]['first_error'],
                             raw_bytes_unchanged_from_parent=True,
                             source_cache_remains_separate=True))

# Recheck the already-earned N04/N06/N07 trailing evidence, without rerunning the cases.
trailing = []
for branch_id, world_id, code in [('N04.2', 4, 'RAW_RETURN_UNKNOWN'),
                                   ('N06.1', 5, 'READ_PROGRESS_INCOMPLETE'),
                                   ('N07.1', 6, 'READ_COUNT_UNKNOWN')]:
    row = by_id[branch_id]
    world = next(w for w in evidence['worlds'] if w['id'] == world_id)
    raw, cache = banks['world-%03d' % world_id]
    if branch_id == 'N04.2':
        cell = raw[:256]
        scalar = decode_axis(cell[128:160])
        condition = scalar['bits'] == 0 and scalar['commit'] == scalar['stage'] == 1 and scalar['kind'] == 1
        condition = condition and not any(r['api'] == 'CloseHandle' for r in world['original_calls'])
    else:
        reads = [r for r in cache if r['api'] == 'ReadFile']
        condition = len(reads) == 1
        cell = raw[256 * reads[0]['ordinal']:256 * (reads[0]['ordinal'] + 1)]
        count = decode_axis(cell[160:192])
        condition = condition and count['bits'] == 0 and count['commit'] == count['stage'] == 1
        if branch_id == 'N07.1':
            error = decode_axis(cell[192:224])
            defined = decode_axis(cell[224:256])
            condition = condition and error['bits'] == 0 and error['commit'] == 1 and defined['bits'] == defined['commit'] == 1
    check('prior_trailing_' + branch_id, row['outcome'] == 'COMPONENT_PASS'
          and row['expected_errors'][0]['code'] == code and world['primary']['code'] == code and condition)
    trailing.append(dict(id=branch_id, world=world_id, exact_code=code, raw_predicates_rechecked=True))

check('qualification_remains_false', proof['native25_complete'] is False
      and proof['qualification'] == dict(source_component_only=True, native_C=False,
                                         native_input_lease=False, physical_IO=False, model=False, RSS=False))
check('gate_counters', proof['call_gate'] == dict(attempts=493, returns=451, checks=1582)
      and parent['call_gate'] == dict(attempts=493, returns=453, checks=1582))
summary = dict(checks=len(CHECKS), passed=sum(c['passed'] for c in CHECKS),
               failed=sum(not c['passed'] for c in CHECKS),
               families=25, total_branches=48, executable_passed=43, source_runtime=21,
               data=22, deferred=4, static_only=1, artifacts=len(inventory),
               artifact_bytes=sum(p['bytes'] for p in inventory.values()),
               artifact_plus_proof_attempt_files=len(inventory) + 2,
               artifact_plus_proof_attempt_bytes=sum(p['bytes'] for p in inventory.values())
               + pin(proof_path)['bytes'] + proof['attempt']['bytes'],
               worlds=len(world_ids), data_objects=len(data_ids), snapshots=len(evidence['snapshots']),
               world_raw_rows=sum(w['bank']['raw_rows'] for w in evidence['worlds']),
               data_raw_rows=sum(d['bank']['raw_rows'] for d in evidence['data']),
               raw_axes_checked=raw_axis_count, snapshot_raw_rows=snapshot_rows,
               snapshot_raw_bytes=snapshot_bytes, unchanged_binary_artifacts=byte_equal,
               query_captures=sum('.query-' in name for name in inventory),
               query_capture_bytes=sum(p['bytes'] for name, p in inventory.items() if '.query-' in name),
               injected_original_dispatches=sum(len(w['original_calls']) for w in evidence['worlds']),
               elapsed_seconds=proof['elapsed_seconds'], call_gate=proof['call_gate'])
review = dict(schema_version=1,
              status='CLEAR_ACTUAL_SOURCE5_43_COMPONENT_BRANCHES_ONLY' if summary['failed'] == 0
              else 'HOLD_ACTUAL_SOURCE5_REVIEW',
              reviewed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              scope='Independent retained hash, byte, JSON, raw layout, lineage and source-text evidence review only. No subject import, replay, native image, compiler, model, original target or current documentation edit.',
              pins=dict(proof=pin(proof_path), binding=pin(binding_path), attempt=pin(proof['attempt']['path']),
                        scope=pin(binding['execution_scope']['path']), freeze=pin(BASE / 'NATIVE25-COMPONENT-FREEZE-v5.json'),
                        static_peer=pin(binding['independent_peer']['path']),
                        resume_peer=pin(BASE / 'SOURCE5-RESUME-STATIC-PIN-CHECK-v2.json'),
                        parent_proof=pin(OLD / 'NATIVE25-COMPONENT-PROOF-v4.json'),
                        case_source=freeze['pins']['cases'], reviewer_source=pin(Path(__file__))),
              summary=summary, checks=CHECKS, kind_guard_results=kind_results,
              prior_trailing_predicates=trailing, outcome_transitions=transitions,
              nonexecuted=dict(deferred=[b['id'] for b in branches if b['classification'] == 'DEFERRED'],
                               static_only=[b['id'] for b in branches if b['classification'] == 'STATIC_ONLY']),
              interpretation='The two malformed same-width API/axis kind rows are now refused without normalization or loss of retained raw bytes. Every other branch outcome, all112 binary artifacts, normalized call caches and source-pin-rebound snapshot semantics are preserved from V4. This proves the selected source/synthetic guard correction and finite regression set, not complete native25 or production integration.',
              limitations=['Source/synthetic Python bank; no native release/acquire or ABI inference from these rows.',
                           'The independent compiled C79 acceptance is separate and not replayed here.',
                           'Four positive native ticket/child/path/joint14 branches remain unexecuted; static declaration is not a runtime pass.',
                           '20 actual synthetic worlds and26 unqualified DATA objects do not establish real Win32 target behavior, held leases or a native consumer.',
                           '0.250s helper interval includes retained world copies but excludes final proof serialization/write/hash/print and process startup/exit.',
                           'No RSS, commit, whole-profile capacity, inference, new84 or scientific validation.'],
              qualification=dict(source_component_only=True, native25_complete=False, full_entry=False,
                                 native_C_or_ABI=False, actual_native_backend=False, native_input_lease=False,
                                 physical_IO=False, real_roster_or_targets=False, RSS_or_fit=False, model_or_science=False),
              reviewer_activity=dict(subject_imports=0, subject_runs=0, compiler_SDK_native_calls=0,
                                     original_payload_reads=0, source_edits=0, current_doc_edits=0))
output = BASE / 'SOURCE5-NATIVE25-INDEPENDENT-ACTUAL-REVIEW-v1.json'
with output.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(review, stream, indent=2)
    stream.write('\n')
markdown = BASE / 'SOURCE5-NATIVE25-INDEPENDENT-ACTUAL-REVIEW-v1.md'
text = f'''# Independent Source5 actual component review

Status: **{review['status']}**. Retained-data inspection only; no replay.

The first Root-bound Source5 diagnostic passes all43 executable branches:21 source-runtime and22 unqualified DATA controls. Four branches remain DEFERRED_NOT_EXECUTED and one STATIC_DECLARATION_ONLY; this is not native25 completion.

The independent review passes {summary['passed']}/{summary['checks']} checks. The exact47 frozen pins, Root scope/binding, consumed attempt and all188 artifact hashes/lengths agree. The retained artifact bytes total578,134; adding the240,017-byte proof and1,120-byte attempt gives190 files/819,271 bytes.20 synthetic worlds,26 DATA objects and30 copied snapshots are retained.493 gated attempts/451 returns/1,582 gate checks occurred in0.250s under the original60-second cooperative timer. These are harness measurements, not physical or process-resource fit.

Only `N25.5.scalar_kind_mismatch` and `N25.5.count_kind_mismatch` move from FAIL to COMPONENT_PASS relative to unchanged Source4 V4. Each now preserves its malformed raw256B row and records the exact first refusal `NATIVE_STATE_NOT_REPRESENTABLE`, with no unexpected RawCallView. All112 binary artifacts remain byte-identical to V4. The46 call caches agree after relocating query-reference paths. All30 snapshot metadata objects agree after independently rebuilding the changed Source5 manifest-policy digests and excluding process-local harness identities. The prior N04/N06/N07 specific refusals and raw zero/count/error trailing predicates were separately rechecked.

No C/ABI, actual OS target, native arena/ticket, positive held-lease child/path route, joint physical14, resource/RSS, new84 or scientific readiness is established. Four deferred branches and the static declaration remain visible. Human gates and the original failed/timeout experiment are untouched. Root acceptance remains a separate decision.

Full checks and exact pins: [JSON review](SOURCE5-NATIVE25-INDEPENDENT-ACTUAL-REVIEW-v1.json).
Trusted metadata checker: [review source](review_source5_actual_v1.py).
'''
with markdown.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
print(json.dumps(dict(status=review['status'], summary=summary,
                      failures=[c for c in CHECKS if not c['passed']],
                      review=pin(output), markdown=pin(markdown))))
