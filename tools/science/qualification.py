"""Explicit scientific qualification contracts; proof validity is not scientific truth.

These evaluator-side checks enforce scope, temporal chronology and provenance.
They do not infer a clinical outcome, certify a reviewer's expertise or train a model.
"""
from datetime import datetime
from pathlib import Path
import re

from asof.serde import ContractError, read_json, safe_child, sha256_file


ENDPOINTS = {'registry_next_phase_actual_start', 'verified_experimental_dosing', 'clinical_success'}
LEVELS = {'unreviewed', 'ai_source_adjudicated', 'independently_adjudicated'}
STATES = {'pending', 'passed', 'deferred', 'blocked'}
STAGES = ('science_1', 'science_2', 'science_3', 'science_4', 'science_5', 'science_6', 'science_7')


def utc(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as error:
        raise ContractError('Scientific chronology needs explicit UTC') from error
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ContractError('Scientific chronology needs explicit UTC')
    return parsed


def require_hash(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ContractError('Missing scientific artifact fingerprint')


def verify_proof(proof, base):
    require_hash(proof['sha256'])
    path = safe_child(base, proof['path'])
    if not path.is_file() or sha256_file(path) != proof['sha256']:
        raise ContractError('Scientific proof bytes differ: ' + proof['path'])
    return path


def validate_source_refs(sources):
    if not sources:
        raise ContractError('Scientific assertion lacks source evidence')
    for source in sources:
        if not isinstance(source, dict):
            raise ContractError('Scientific source evidence needs a structured fingerprint and locator')
        require_hash(source.get('artifact_sha256'))
        if not source.get('locator') or not source.get('url') or not source.get('retrieved_at'):
            raise ContractError('Source evidence needs a stable locator, retrieval date and URL')


def validate_register(register, base=Path('.'), verify_proofs=True):
    if register.get('schema_version') != 1 or register.get('provider_spend_usd') != 0:
        raise ContractError('Unsupported scientific qualification register')
    utc(register['created_at_utc'])
    if verify_proofs:
        for proof in register.get('contract_artifacts', []):
            verify_proof(proof, base)
    if set(register['endpoints']) != ENDPOINTS:
        raise ContractError('Progression, dosing and clinical success must remain separate')
    if register['original_H1_endpoint'] != 'clinical_success':
        raise ContractError('A registry surrogate cannot silently replace H1 clinical success')
    stages = register['stages']
    if [s['id'] for s in stages] != list(STAGES):
        raise ContractError('Scientific stages must be unique and ordered')
    prior, passed = set(), set()
    for stage in stages:
        if stage['status'] not in STATES or set(stage['depends_on']) - prior:
            raise ContractError('Invalid scientific stage state or dependency')
        if not stage['acceptance_checks'] or not stage['deliverables']:
            raise ContractError('Scientific acceptance checks and deliverables are required')
        if stage['status'] == 'passed' and not stage['proofs']:
            raise ContractError('Passed stage lacks retained validation evidence')
        if stage['status'] == 'passed' and set(stage['depends_on']) - passed:
            raise ContractError('Passed scientific stage has unmet dependencies')
        if stage['status'] in ('blocked', 'deferred') and not stage.get('reason'):
            raise ContractError('Scientific blocker/deferral needs a reason')
        if verify_proofs:
            for proof in stage['proofs']:
                verify_proof(proof, base)
        prior.add(stage['id'])
        if stage['status'] == 'passed':
            passed.add(stage['id'])
    return {'status': 'register_valid', 'stages': {s['id']: s['status'] for s in stages},
            'scientific_validation': 'not_inferred_from_contract_validation'}


def validate_reference(reference):
    required = {'schema_version', 'reference_id', 'case_id', 'hypothesis_sha256', 'source_row_sha256',
        'statement', 'answer', 'context', 'source_evidence', 'reviews', 'adjudication',
        'reference_level', 'role', 'validation_claim', 'version_applicability'}
    if not required <= reference.keys() or reference['schema_version'] != 1:
        raise ContractError('Incomplete scientific reference contract')
    if (reference['role'] != 'evaluation_only' or reference['reference_level'] not in LEVELS or
            reference['validation_claim'] not in ('development_only', 'source_grounded_ai_reference',
                                                  'independently_validated_scientific_truth')):
        raise ContractError('Scientific references must remain evaluator-only with explicit level')
    require_hash(reference['hypothesis_sha256']); require_hash(reference['source_row_sha256'])
    if reference['answer'] not in ('supported', 'contradicted', 'uncertain', 'unavailable'):
        raise ContractError('Unknown evidence answer')
    if not reference['statement'] or not reference['source_evidence']:
        raise ContractError('Reference lacks a statement or source evidence')
    validate_source_refs(reference['source_evidence'])
    if reference['version_applicability']['status'] not in ('exact', 'crosswalk_verified', 'stale', 'unknown'):
        raise ContractError('Unknown reference version applicability')
    reviews = reference['reviews']
    if len({r['reviewer_id'] for r in reviews}) != len(reviews):
        raise ContractError('Duplicate reviewer identity')
    for review in reviews:
        if review['reviewer_kind'] not in ('ai_agent', 'human', 'curated_external'):
            raise ContractError('Unknown reviewer provenance')
        if type(review['blinded_to_arm_outputs']) is not bool:
            raise ContractError('Reviewer blinding must be explicit')
        if review['reviewer_kind'] == 'ai_agent' and not review.get('model_provenance'):
            raise ContractError('AI review must identify its model/procedure')
    if reference['reference_level'] != 'unreviewed':
        if len(reviews) < 2 or not reference['adjudication'].get('rationale'):
            raise ContractError('Adjudicated reference needs two reviews and a rationale')
    if reference['reference_level'] == 'independently_adjudicated':
        if (not reference['adjudication'].get('independence_evidence') or
                not any(r['reviewer_kind'] in ('human', 'curated_external') for r in reviews)):
            raise ContractError('Separate AI agents alone cannot certify external scientific independence')
    elif reference['validation_claim'] == 'independently_validated_scientific_truth':
        raise ContractError('Review validation level overclaimed')
    applicable = reference['version_applicability']['status'] in ('exact', 'crosswalk_verified')
    return {'status': 'reference_contract_valid', 'reference_level': reference['reference_level'],
            'eligible_for_source_grounded_comparison': applicable and reference['reference_level'] != 'unreviewed',
            'eligible_for_independent_scientific_claim': applicable and reference['reference_level'] == 'independently_adjudicated',
            'version_status': reference['version_applicability']['status']}


def validate_outcome(label):
    required = {'schema_version', 'case_id', 'endpoint_id', 'value', 'status', 'origin_at', 'horizon_at',
        'ascertainment_at', 'event_at', 'publicly_available_at', 'observed_until', 'source_evidence',
        'same_program_scope', 'negative_ascertainment', 'reference_level'}
    if not required <= label.keys() or label['schema_version'] != 1:
        raise ContractError('Incomplete scientific outcome contract')
    if label['endpoint_id'] not in ENDPOINTS or label['reference_level'] not in LEVELS:
        raise ContractError('Unknown outcome endpoint/reference level')
    origin, horizon, ascertainment = map(utc, (label['origin_at'], label['horizon_at'], label['ascertainment_at']))
    observed = utc(label['observed_until'])
    if not origin < horizon <= ascertainment or not origin <= observed <= ascertainment:
        raise ContractError('Outcome horizon/ascertainment chronology contradicts observation')
    if label['status'] not in ('resolved', 'censored', 'unresolved', 'competing_event'):
        raise ContractError('Unknown scientific outcome state')
    if label['status'] != 'resolved':
        if label['value'] is not None:
            raise ContractError('Unresolved/censored/competing event cannot become a binary negative')
        return {'status': 'outcome_contract_valid', 'binary_eligible': False}
    if type(label['value']) is not int or label['value'] not in (0, 1):
        raise ContractError('Resolved scientific outcome must be an explicit binary integer')
    if not label['source_evidence'] or label['same_program_scope'] is not True:
        raise ContractError('Resolved outcome needs retained evidence and qualified program scope')
    validate_source_refs(label['source_evidence'])
    available = utc(label['publicly_available_at'])
    if not origin < available <= ascertainment:
        raise ContractError('Outcome publication outside qualified ascertainment')
    if label['value'] == 1:
        if not label['event_at'] or not origin < utc(label['event_at']) <= min(horizon, observed, available):
            raise ContractError('Positive outcome lacks an eligible occurred/public event')
        if label['endpoint_id'] == 'clinical_success' and not label.get('success_criterion_evidence'):
            raise ContractError('Clinical success requires explicit success-criterion evidence')
        if label['endpoint_id'] == 'verified_experimental_dosing' and not label.get('dosing_evidence'):
            raise ContractError('Enrollment alone does not establish experimental dosing')
    else:
        if observed < horizon or available < horizon or not label['negative_ascertainment']:
            raise ContractError('Negative needs full qualified follow-up and explicit ascertainment')
        if label['event_at'] is not None and utc(label['event_at']) <= horizon:
            raise ContractError('Negative contradicts an in-window event')
        if label['endpoint_id'] == 'clinical_success' and not label.get('failure_criterion_evidence'):
            raise ContractError('No recorded progression is not evidence of clinical failure')
    return {'status': 'outcome_contract_valid', 'binary_eligible': label['reference_level'] != 'unreviewed',
            'scientific_validation': label['reference_level']}


def validate_feature_chronology(feature_origin_at, input_lineage, models=(), label_available_at=None, prediction_origin_at=None):
    origin = utc(feature_origin_at)
    if not input_lineage:
        raise ContractError('Historical feature derivation lacks complete input lineage')
    for source in input_lineage:
        require_hash(source['sha256'])
        if source['role'] not in ('agent_evidence', 'reference') or utc(source['available_by']) >= origin:
            raise ContractError('Later or evaluator-only information cannot become historical predictors')
    for model in models:
        require_hash(model['weights_sha256'])
        if utc(model['released_by']) >= origin or model.get('later_finetune', False):
            raise ContractError('Model contributor is later than this feature origin')
    if label_available_at is not None:
        if prediction_origin_at is None or utc(label_available_at) >= utc(prediction_origin_at):
            raise ContractError('Training/calibration label is unavailable before test prediction origin')
    return {'status': 'feature_chronology_valid', 'new_computation_on_old_inputs_allowed': True}
