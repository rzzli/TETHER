"""Seal all paired inputs and reserve one permanent new-method authority.

Preparation has no model or acquisition API. Production inputs come only from
the independently reconstructed original parent. Qualification inputs are
explicitly invented and cannot be promoted into production by changing a flag.
"""
from datetime import datetime, timezone
from collections.abc import Mapping
from pathlib import Path
import sys

from tether_engine.serde import canonical, encode, freeze
from experiments.litqa_refinement_recovery import original
from experiments.litqa_refinement_recovery import contracts as previous_contracts
from experiments.litqa_refinement_recovery.run import code_files as parent_code_files
from . import contracts as c, model, projection

KIND = 'sc05_evidence_first_plan_v1'
MODEL_FIELDS = {'model_receipt', 'model_license', 'model_spec', 'model_provenance', 'interpreter', 'port', 'alias'}
FIELDS = {'schema_version', 'kind', 'purpose', 'parent', 'parent_identity', 'method', 'method_identity',
          'schedule', 'prepared', 'cutoff', 'source_closure', 'model', 'budgets', 'authority_registry',
          'code_files', 'automatic_retry', 'reference_keys_available', 'new_source_collection'}


def code_files():
    result = {p['path']: p for p in parent_code_files()}
    for path in Path(__file__).resolve().parent.glob('*.py'):
        if not path.name.startswith('test_'):
            value = c.capture(path)[0]; result[value['path']] = value
    return freeze([result[key] for key in sorted(result)])


def _qualification_origin(anchor):
    """Derive registry identity from anchored metadata without opening answers."""
    receipt = c.read(anchor); base = c.path(anchor['path']).parent
    c.need(Path(anchor['path']).name == 'RECEIPT.json' and
           receipt['kind'] == 'sc05_failed_production_metadata_audit_receipt_v1' and receipt['status'] == 'complete',
           'Externally pinned original inspection required')
    files = receipt['files']
    for name in ('RESULT.json', 'ORIGINAL-INVENTORY.json'):
        c.need(name in files and c.path(files[name]['path']) == base / name, 'Original inspection metadata location differs')
    result = c.read(files['RESULT.json']); inventory = c.read(files['ORIGINAL-INVENTORY.json'])
    c.need(result['kind'] == 'sc05_failed_production_metadata_forensics_v1' and
           result['status'] == 'metadata_and_byte_inventory_verified', 'Original inspection status differs')
    root = c.path(result['original_root']); frozen = c.path(result['freeze_root'])
    frame_proof = result['original_frame']
    c.need(inventory['root'] == str(root) and inventory['files']['FRAME.json'] == frame_proof and
           c.path(frame_proof['path']) == root / 'FRAME.json', 'Original frame metadata binding differs')
    frame = c.read(frame_proof)
    c.need(type(frame['schema_version']) is int and frame['schema_version'] == 1 and
           frame['kind'] == 'sc05_refinement_execution_v1' and frame['purpose'] == 'production' and
           c.path(frame['output']) == root, 'Original production frame identity differs')
    c.schedule(frame['schedule'], 'production')
    return (previous_contracts.identity(str(root), frame_proof),
            [anchor, files['RESULT.json'], files['ORIGINAL-INVENTORY.json'], frame_proof], [base, root, frozen])


def _bank(descriptor):
    c.need(set(descriptor) == {'bank', 'original_inspection'}, 'Exact invented-bank/inspection descriptor required')
    parent_id, origin_proofs, _ = _qualification_origin(descriptor['original_inspection'])
    anchor = descriptor['bank']; bank = c.read(anchor); base = Path(anchor['path']).parent
    c.need(bank['kind'] == 'tether_evidence_first_qualification_bank_v1' and type(bank['schema_version']) is int and
           bank['schema_version'] == 1 and bank['purpose'] == 'fictional_qualification' and
           type(bank['max_native_calls']) is int and bank['max_native_calls'] == 12 and
           type(bank['source_http_requests']) is int and bank['source_http_requests'] == 0 and
           tuple(bank['phase_order']) == c.PHASES, 'Invented six-pair bank scope')
    ids = c.schedule(bank['schedule'], 'fictional_qualification')
    roles = bank['role_files']
    c.need(set(roles) == {'contexts', 'ancestry', 'expectations'}, 'Separate invented input/expectation roles')
    expected_roles = {'contexts': ('ACTOR.json', 'coordinator_only'),
                      'ancestry': ('ANCESTRY.json', 'coordinator_only'),
                      'expectations': ('EVALUATOR.json', 'evaluation_only')}
    for key, (filename, role) in expected_roles.items():
        c.need(set(roles[key]) == {'proof', 'role'} and roles[key]['role'] == role and
               Path(roles[key]['proof']['path']) == base / filename, 'Bank role location differs')
    # Expected answers are not an input to preparation or any actor.
    actors = c.read(roles['contexts']['proof']); ancestry = c.read(roles['ancestry']['proof'])
    c.need(actors['kind'] == 'synthetic_refinement_contexts_v1' and actors['scope'] == 'fictional_qualification' and
           ancestry['kind'] == 'synthetic_refinement_ancestry_v1' and ancestry['actual_prior_model_calls'] == 0,
           'Invented ancestry cannot masquerade as actual model history')
    cases, origins = actors['cases'], ancestry['cases']
    c.need(tuple(row['query']['id'] for row in cases) == ids and tuple(row['id'] for row in origins) == ids,
           'Invented ordered case coverage differs')
    proofs = [*origin_proofs, anchor, roles['contexts']['proof'], roles['ancestry']['proof']]
    rows = []; cutoff = None
    c.need(len(bank['slots']) == 12, 'Twelve actor files required')
    for index, (case, origin) in enumerate(zip(cases, origins)):
        c.need(set(case) == {'query', 'candidate_context', 'critique_context', 'sources'} and
               origin['invented'] is True and origin['scope'] == 'fictional_qualification' and
               origin['prior_capture_is_actual_native'] is False and origin['critic_capture_is_actual_native'] is False,
               'Explicit invented context fields required')
        time = origin['cutoff_utc']; current = datetime.fromisoformat(time)
        c.need(current.utcoffset() is not None, 'Aware invented cutoff required')
        times = origin['current_source_available_at_utc']
        c.need(isinstance(times, Mapping) and set(times) == {source['source_id'] for source in case['sources']},
               'Exact current source-ID availability mapping required')
        for timestamp in (origin['critique_created_at_utc'], *times.values()):
            c.need(isinstance(timestamp, str), 'Aware source/critique timestamp required')
            observed = datetime.fromisoformat(timestamp)
            c.need(observed.utcoffset() is not None and observed <= current, 'Invented input after fixed cutoff')
        c.need(cutoff is None or cutoff == time, 'Bank cutoffs differ'); cutoff = time
        for phase in c.PHASES:
            name = f'actor_cases/{phase}-{index:04d}.json'; slot = bank['slots'][name]
            expected = dict(task=phase, query=case['query'], candidate_context=case['candidate_context'],
                            critique_context=case['critique_context'], sources=case['sources'] if phase == 'repair' else ())
            c.need(set(slot) == {'proof', 'role', 'phase', 'ordinal', 'id'} and
                   slot['role'] == 'single_slot_actor_input' and slot['phase'] == phase and
                   type(slot['ordinal']) is int and slot['ordinal'] == index and
                   slot['id'] == ids[index] and Path(slot['proof']['path']) == base / name and
                   canonical(c.read(slot['proof'])) == canonical(expected), 'Bank single-actor projection differs')
            proofs.append(slot['proof'])
        rows.append(dict(query=case['query'], prior=case['candidate_context'], critic=case['critique_context'],
                         sources=case['sources'], context=dict(kind='invented_evidence_first_context_v1', cutoff=time,
                         control_sha256=c.fingerprint(dict(query=case['query'], candidate=case['candidate_context'],
                                                         critique=case['critique_context'])),
                         source_scope='invented', source_ancestry=origin, scientific_support='unevaluated')))
    return ids, rows, cutoff, freeze(dict(proofs=proofs, inventories=())), parent_id


def prepare(parent, output, *, qualification_model=None):
    """Write a fresh plan; never reserve native calls during source preparation."""
    root = c.path(output)
    c.need(root != c.ROOT / 'data' and root.is_relative_to(c.ROOT / 'data'),
           'Preparation output must be a fresh project data directory')
    if set(parent) == {'bank', 'original_inspection'}:
        _, _, protected = _qualification_origin(parent['original_inspection'])
        protected = [*protected, c.path(parent['bank']['path']).parent]
    else:
        c.need(set(parent) == {'inspection', 'source_archive', 'baseline_acceptance'}, 'Exact production parent required')
        inspection = c.read(parent['inspection']); report = c.read(inspection['files']['RESULT.json'])
        baseline = parent['baseline_acceptance']
        protected = [c.path(report['original_root']), c.path(report['freeze_root']),
            c.path(parent['inspection']['path']).parent, c.path(parent['source_archive']['path']).parent,
            c.path(baseline['replay_root']), c.path(baseline['analyzer_archive']['path']).parent]
    protected.extend(c.authority_registry(purpose) for purpose in c.PURPOSES)
    for location in protected:
        c.need(not root.is_relative_to(location) and not location.is_relative_to(root),
               'Preparation cannot overlap preserved inputs or permanent authorities')
    root.mkdir(exist_ok=False)
    verified = None
    try:
        c.write(root / 'REQUEST.json', dict(parent=parent, created_at_utc=datetime.now(timezone.utc).isoformat(),
            model_or_http_execution_performed=False, reference_keys_available=False))
        pins = code_files(); method = c.write(root / 'METHOD.json', model.method_descriptor())
        if set(parent) == {'bank', 'original_inspection'}:
            purpose = 'fictional_qualification'
            c.need(qualification_model is not None and set(qualification_model) == MODEL_FIELDS,
                   'Explicit pinned qualification model required')
            ids, rows, cutoff, closure, parent_id = _bank(parent); settings = qualification_model
        else:
            purpose = 'production'
            c.need(qualification_model is None and set(parent) == {'inspection', 'source_archive', 'baseline_acceptance'},
                   'Exact genuine production parent required')
            verified = original.reconstruct(parent['inspection'], parent['source_archive'],
                                             baseline_acceptance=parent['baseline_acceptance'])
            state = original._state(verified); payload = verified.payload
            c.need(payload['purpose'] == 'production', 'An invented parent cannot authorize a production comparison')
            ids = c.schedule(payload['schedule'], purpose)
            rows = state['semantic']['prepared']; closure = state['closure']
            c.need(len(rows) == len(ids), 'Full verified paired context required')
            cutoff = rows[0]['context']['cutoff']
            settings = {key: payload['frame'][key] for key in MODEL_FIELDS}
            parent_id = previous_contracts.identity(payload['original_root'], payload['frame_proof'])
        c.need(c.capture(Path(sys.executable).resolve())[0] == settings['interpreter'], 'Exact original interpreter required')
        source = c.write(root / 'SOURCE-CLOSURE.json', closure)
        prepared = []
        (root / 'pairs').mkdir()
        for index, row in enumerate(rows):
            c.need(row['query']['id'] == ids[index], 'Parent context order changed')
            pair = projection.from_verified_context(row['query'], row['prior'], row['critic'], row['sources'],
                settings['model_provenance'], cutoff=cutoff, context=row['context'])
            folder = root / 'pairs' / f'{index:04d}'; folder.mkdir()
            entry = dict(id=ids[index], ordinal=index, control_sha256=pair['control_sha256'],
                         context=c.write(folder / 'CONTEXT.json', pair['context']))
            # Both members are fully sealed before any authority or dispatch.
            for phase in c.PHASES:
                entry[phase] = c.write(folder / (phase.upper() + '.json'), projection.actor_member(pair, phase))
            prepared.append(entry)
        if verified is not None: original.revalidate(verified)
        else: original.verify_snapshot(closure)
        c.need(code_files() == pins, 'Preparation source code changed before sealing')
        value = dict(schema_version=1, kind=KIND, purpose=purpose, parent=parent, parent_identity=parent_id,
            method=method, method_identity=c.fingerprint(model.method_descriptor()), schedule=ids,
            prepared=prepared, cutoff=cutoff, source_closure=source, model=settings, budgets=c.budgets(purpose),
            authority_registry=str(c.authority_registry(purpose)), code_files=pins,
            automatic_retry=False, reference_keys_available=False, new_source_collection=False)
        anchor = c.write(root / 'PLAN.json', value)
        c.write(root / 'COMPLETE.json', dict(status='paired_inputs_sealed', plan=anchor,
            native_calls=0, source_http_requests=0, authority_reserved=False))
        return anchor
    except BaseException as error:
        c.write(root / 'FAILURE.json', dict(error_type=type(error).__name__, message=str(error),
            model_or_http_execution_performed=False, automatic_retry=False))
        raise


def read(anchor, *, verify_sources=True, verify_code=True):
    base = c.path(anchor['path']).parent
    c.need(not any((base / name).exists() for name in ('FAILURE.json', 'DEADLINE.json', 'FINALIZATION-FAILED.json')),
           'Failed preparation cannot authorize execution')
    terminal = c.read(c.capture(base / 'COMPLETE.json')[0])
    c.need(canonical(terminal) == canonical(dict(status='paired_inputs_sealed', plan=anchor,
        native_calls=0, source_http_requests=0, authority_reserved=False)), 'Successful preparation terminal differs')
    value = c.read(anchor)
    c.need(set(value) == FIELDS and type(value['schema_version']) is int and value['schema_version'] == 1 and
           value['kind'] == KIND, 'Evidence-first plan schema')
    c.schedule(value['schedule'], value['purpose'])
    c.need(canonical(value['budgets']) == canonical(c.budgets(value['purpose'])) and value['automatic_retry'] is False and
           value['reference_keys_available'] is False and value['new_source_collection'] is False,
           'Fixed prospective scope differs')
    method = c.read(value['method'])
    c.need(value['method_identity'] == c.fingerprint(method) and
           (not verify_code or canonical(method) == canonical(model.method_descriptor())), 'Method identity differs')
    c.need(value['authority_registry'] == str(c.authority_registry(value['purpose'])), 'Stable method registry required')
    if verify_code: c.need(value['code_files'] == code_files(), 'Frozen implementation changed')
    if verify_sources: original.verify_snapshot(c.read(value['source_closure']))
    c.need(len(value['prepared']) == len(value['schedule']), 'Every scheduled pair required')
    c.need(Path(anchor['path']).name == 'PLAN.json' and Path(value['method']['path']) == base / 'METHOD.json' and
           Path(value['source_closure']['path']) == base / 'SOURCE-CLOSURE.json', 'Exact sealed plan locations')
    for index, entry in enumerate(value['prepared']):
        c.need(set(entry) == {'id', 'ordinal', 'control_sha256', 'context', 'repair', 'removal'} and
               entry['id'] == value['schedule'][index] and type(entry['ordinal']) is int and
               entry['ordinal'] == index, 'Exact prepared order')
        folder = base / 'pairs' / f'{index:04d}'
        c.need(Path(entry['context']['path']) == folder / 'CONTEXT.json', 'Exact prepared context path')
        context = c.read(entry['context']); c.need(context['cutoff'] == value['cutoff'], 'Fixed context cutoff')
        members = {}
        for phase in c.PHASES:
            c.need(Path(entry[phase]['path']) == folder / (phase.upper() + '.json'), 'Exact paired member path')
            member = c.read(entry[phase]); members[phase] = member
            c.need(member['task'] == phase and member['query']['id'] == entry['id'] and
                   member['control_sha256'] == entry['control_sha256'] and
                   member['model_provenance'] == value['model']['model_provenance'], 'Prepared member identity differs')
            c.need(phase != 'removal' or not member['sources'], 'Raw-source removal leakage')
        for key in ('query', 'candidate_context', 'critique_context', 'model_provenance', 'control_sha256'):
            c.need(members['repair'][key] == members['removal'][key], 'Paired controls differ')
    return value


def reserve(anchor):
    """A permanent registry claim survives moved/deleted output directories."""
    value = read(anchor)
    verify_parent(value)
    registry = c.authority_registry(value['purpose']); registry.mkdir(parents=True, exist_ok=True)
    key = c.identity(value['parent_identity'], value['method_identity'])
    location = registry / key; location.mkdir(exist_ok=False)
    try:
        return c.write(location / 'AUTHORITY.json', dict(schema_version=1, kind='sc05_evidence_first_authority_v1',
            identity=key, parent_identity=value['parent_identity'], method_identity=value['method_identity'],
            plan=anchor, purpose=value['purpose'], schedule=value['schedule'], budgets=value['budgets'],
            permanent=True, automatic_retry=False))
    except BaseException:
        # The directory intentionally remains claimed, including partial writes.
        raise


def verify_parent(value):
    """Rebuild semantic inputs at admission; a rewritten plan is not authority."""
    if value['purpose'] == 'production':
        parent = value['parent']
        c.need(set(parent) == {'inspection', 'source_archive', 'baseline_acceptance'}, 'Exact production parent')
        verified = original.reconstruct(parent['inspection'], parent['source_archive'],
                                         baseline_acceptance=parent['baseline_acceptance'])
        state = original._state(verified); payload = verified.payload
        c.need(payload['purpose'] == 'production', 'Genuine production parent required')
        ids = payload['schedule']; rows = state['semantic']['prepared']; closure = state['closure']
        cutoff = rows[0]['context']['cutoff']
        parent_id = previous_contracts.identity(payload['original_root'], payload['frame_proof'])
        c.need(value['model'] == freeze({key: payload['frame'][key] for key in MODEL_FIELDS}), 'Original model identity differs')
    else:
        ids, rows, cutoff, closure, parent_id = _bank(value['parent']); verified = None
    c.need(tuple(ids) == value['schedule'] and cutoff == value['cutoff'] and parent_id == value['parent_identity'] and
           closure == c.read(value['source_closure']), 'Reconstructed parent membership/closure differs')
    for row, entry in zip(rows, value['prepared']):
        pair = projection.from_verified_context(row['query'], row['prior'], row['critic'], row['sources'],
            value['model']['model_provenance'], cutoff=cutoff, context=row['context'])
        c.need(pair['context'] == c.read(entry['context']) and pair['control_sha256'] == entry['control_sha256'],
               'Original source context differs from frozen projection')
        for phase in c.PHASES:
            c.need(projection.actor_member(pair, phase) == c.read(entry[phase]),
                   'Original source-derived member differs from frozen projection')
    if verified is not None: original.revalidate(verified)
    else: original.verify_snapshot(closure)
    return verified


def verify_authority(anchor, authority, *, verify_sources=True, verify_code=True, verify_semantics=True):
    value = read(anchor, verify_sources=verify_sources, verify_code=verify_code); claim = c.read(authority)
    key = c.identity(value['parent_identity'], value['method_identity'])
    expected = dict(schema_version=1, kind='sc05_evidence_first_authority_v1', identity=key,
        parent_identity=value['parent_identity'], method_identity=value['method_identity'], plan=anchor,
        purpose=value['purpose'], schedule=value['schedule'], budgets=value['budgets'], permanent=True, automatic_retry=False)
    c.need(canonical(claim) == canonical(expected) and Path(authority['path']) ==
           c.authority_registry(value['purpose']) / key / 'AUTHORITY.json', 'Permanent method authority differs')
    if verify_semantics: verify_parent(value)
    return value, claim
