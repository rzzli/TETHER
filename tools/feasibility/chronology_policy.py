"""Validate frozen evaluation chronology; readiness is separate from protocol validity."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from tether_engine.serde import ContractError, read_json, sha256_file


def utc(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as exc:
        raise ContractError('Invalid chronology timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ContractError('Chronology timestamps require explicit UTC')
    return parsed


def validate_protocol(protocol):
    if protocol['schema_version'] != 1 or protocol['provider_spend_usd'] != 0:
        raise ContractError('Unsupported protocol or spending boundary')
    frozen = utc(protocol['frozen_at_utc'])
    clinical = protocol['clinical']
    origin, end = utc(clinical['origin_at']), utc(clinical['endpoint_at'])
    if end <= origin or clinical['horizon_months'] != 12:
        raise ContractError('Invalid prespecified clinical window')
    if clinical['lock_status'] != 'not_locked' or clinical['qualified_label_count'] is not None:
        raise ContractError('This protocol cannot certify qualified labels or a locked set')
    if protocol['registration']['publicly_registered'] or not protocol['registration']['local_only']:
        raise ContractError('Public registration is not established by a local freeze')
    roles = set()
    for model in protocol['models']:
        if not re.fullmatch('[a-f0-9]{40}', model['revision']):
            raise ContractError('Model needs an immutable revision')
        if utc(model['released_at_upper_bound']) >= origin:
            raise ContractError('Model release is not earlier than clinical origin')
        if model['later_finetune_permitted']:
            raise ContractError('Later model adaptation breaks the chronology route')
        roles.update(model['roles'])
        for asset in model['files']:
            if not re.fullmatch('[a-f0-9]{64}', asset['sha256']) or asset['bytes'] <= 0:
                raise ContractError('Missing immutable model asset pin')
        if not model['files']:
            raise ContractError('No pinned model assets')
    if roles != {'specialist', 'reviewer', 'chief_of_staff'}:
        raise ContractError('All contributing model roles must qualify')
    for source in clinical['predictor_sources']:
        if source['role'] != 'agent_visible' or source['evaluator_only']:
            raise ContractError('Evaluator source cannot become a predictor')
        if utc(source['released_at_upper_bound']) >= origin:
            raise ContractError('Later predictor source')
        if source['current_version_fallback']:
            raise ContractError('No current annotations may fill historical gaps')
    gates = protocol['clinical']['activation_gates']
    required = {'origin_selection_sealed', 'historical_inputs_qualified', 'independent_labels',
                'dependence_and_power', 'predictions_sealed_before_label_join',
                'model_runtime_hashes', 'registration_decision'}
    if set(gates) != required or any(type(v) is not bool for v in gates.values()):
        raise ContractError('Incomplete clinical activation gates')
    if any(gates.values()):
        raise ContractError('Activation requires a new qualified protocol with supporting artifacts')
    if not protocol['comparison']['virtual_biotech_adapted']:
        raise ContractError('Changing comparator models must be labeled adapted')
    if not protocol['development']['probabilities_withheld']:
        raise ContractError('Unvalidated development probabilities must remain withheld')
    if frozen <= origin:
        raise ContractError('Retrospective protocol chronology is mislabeled')
    return {'status': 'valid_frozen_local_protocol', 'clinical_ready': all(gates.values()),
            'clinical_lock_status': 'not_locked',
            'unmet_clinical_gates': sorted(k for k, v in gates.items() if not v),
            'public_registration': False, 'chronology_basis': 'immutable_pre_origin_weights_not_claimed_training_cutoff'}


def validate_frozen(protocol_path, freeze_path, base=Path('.')):
    freeze = read_json(freeze_path)
    if sha256_file(protocol_path) != freeze['protocol']['sha256']:
        raise ContractError('Frozen protocol changed')
    for item in freeze['proofs']:
        if sha256_file(base / item['path']) != item['sha256']:
            raise ContractError('Chronology proof changed: ' + item['path'])
    return validate_protocol(read_json(protocol_path))
