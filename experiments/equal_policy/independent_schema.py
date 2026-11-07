"""Independent JSON contract tables for the equal-policy experiment.

These tables are written from the declared wire contract. They neither import
nor introspect the product implementation. Normalization is explicit because
the contract hashes decoded numeric/date/default representations, not raw JSON.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import math


class PolicyError(ValueError):
    def __init__(self, obligation, message):
        self.obligation = obligation
        super().__init__(message)


def require(condition, obligation, message):
    if not condition:
        raise PolicyError(obligation, message)


CATEGORIES = ('genetics', 'perturbation', 'expression', 'modality', 'literature',
              'clinical', 'safety', 'pathway')
FEATURES = {
    'genetic_support': 'genetics', 'direction_alignment': 'genetics',
    'perturbation_support': 'perturbation', 'expression_relevance': 'expression',
    'modality_feasibility': 'modality', 'literature_support': 'literature',
    'safety_liability': 'safety', 'pathway_support': 'pathway',
}
SIGNED_FEATURES = {'direction_alignment', 'perturbation_support', 'literature_support'}
ENUMS = {
    'Profile': ('historical_benchmark', 'contemporary_assessment', 'synthetic_demo'),
    'Temporal': ('verified_historical', 'reconstructed', 'contemporary_only', 'unverified'),
    'Category': CATEGORIES,
    'Status': ('observed', 'absent', 'not_measured', 'failed_qc', 'access_denied', 'outside_applicability'),
    'Polarity': ('supports', 'refutes', 'uncertain'),
}

# Tuple entries are (type, default); every other field is required. [] and {}
# describe homogeneous lists and string-keyed dictionaries. ? means nullable.
SCHEMAS = {
    'Availability': dict(first_public_at='date?', release_public_at='date?',
        record_public_at='date?', annotation_public_at='date?', retrieved_at='date',
        basis='str', uncertainty='str?', known_public_by=('datetime?', None), evidence_ref=('str?', None)),
    'Hypothesis': dict(target_id='str', indication_id='str', target_namespace_version='str',
        indication_namespace_version='str', intended_action='str', modality='str', tissue='str?', availability='Availability'),
    'Program': dict(program_id='str', molecule_id='str', sponsor='str', phase_at_origin='int',
        status_at_origin='str', eligible_since='date', mapping_confidence='float', trial_ids='[str]', availability='Availability'),
    'Endpoint': dict(name='str', horizon_months='int'),
    'Case': dict(schema_version='int', case_id='str', task='str', origin='date', hypothesis='Hypothesis',
        program='Program?', endpoint='Endpoint?', origin_at=('datetime?', None)),
    'Artifact': dict(artifact_id='str', dataset_id='str', release_id='str', path='str', sha256='str',
        role='str', access_approved='bool', temporal_classification='Temporal', availability='Availability',
        source_url='str', input_refs=('[str]', [])),
    'Source': dict(source_id='str', dataset_id='str', release_id='str', path='str', sha256='str', role='str',
        availability='Availability', temporal_classification='Temporal', source_url='str', parents=('[str]', []),
        computed_at=('datetime?', None), method_id=('str?', None), method_version=('str?', None),
        receipt_path=('str?', None), receipt_sha256=('str?', None)),
    'Snapshot': dict(schema_version='int', snapshot_id='str', profile='Profile', origin='date',
        allow_reconstructed='bool', artifacts='[Artifact]', sources=('[Source]', []), raw_root=('str?', None),
        coverage=('{any}', {}), origin_at=('datetime?', None)),
    'Context': dict(species='str?', ancestry='str?', tissue='str?', disease_state='str?', intervention='str?',
        comparator='str?', cohort_ids='[str]'),
    'Quantitative': dict(effect='float?', scale='str?', standard_error='float?', ci_lower='float?', ci_upper='float?',
        sample_size='int?', adjusted_p_value='float?'),
    'Method': dict(code_id='str', version='str', parameters='{any}', qc_status='str', limitations='[str]'),
    'Observation': dict(observation_id='str', target_id='str', indication_id='str', program_id='str?',
        category='Category', source_kind='str', statement='str', status='Status', polarity='Polarity',
        mechanism_direction='str', study_id='str?', dependency_group='str?', context='Context',
        quantitative='Quantitative', method='Method', availability='Availability', features='{float}',
        feature_scope=('str?', None), input_refs=('[str]', []), computed_at=('datetime?', None),
        source_locator=('{any}', {}), source_metrics=('{any}', {}), missingness=('{str}', {}),
        publication_date=('date?', None), publication_year=('int?', None)),
    'Packet': dict(schema_version='int', observations='[Observation]'),
    'Citation': dict(artifact_id='str', dataset_id='str', release_id='str', artifact_sha256='str', source_url='str'),
    'Grounded': dict(observation='Observation', citation='Citation'),
    'Claim': dict(claim_id='str', specialist='Category', evidence='Grounded', extraction_mode='str', admitted_fingerprint=('str', '')),
    'Feature': dict(value='float?', status='str', dependency_groups='int', observation_ids='[str]',
        excluded_groups='[str]', missing_reasons=('[str]', [])),
    'FeatureVector': dict(schema_version='str', aggregation='str', values='{Feature}'),
    'Scorer': dict(schema_version='int', model_id='str', kind='str', feature_schema='str', aggregation='str',
        endpoint='str', horizon_months='int', phases='[int]', modalities='[str]', intended_actions='[str]',
        target_namespace_versions='[str]', indication_namespace_versions='[str]', training_origin_max='date',
        training_label_available_max='date', calibration_label_available_max='date?', training_manifest_sha256='str',
        calibration='str', intercept='float', coefficients='{float}', required_features='[str]', missing_values='{float}',
        minimum_coverage='float'),
    'Contribution': dict(value='float', coefficient='float', log_odds='float', imputed='bool', observation_ids='[str]'),
    'Prediction': dict(case_id='str', origin='date', endpoint='str?', horizon_months='int?', status='str',
        probability='float?', reason='str?', scorer_id='str?', synthetic='bool', calibration='str?',
        feature_coverage='float?', intercept='float?', contributions='{Contribution}'),
    'Usage': dict(input_tokens='int', output_tokens='int', cost_usd='float'),
    'Budget': dict(max_calls=('int', 16), max_input_tokens=('int', 32000), max_output_tokens=('int', 8000),
        max_cost_usd=('float', 0), max_seconds=('float', 300), max_retries=('int', 1)),
    'Selection': dict(observation_ids='[str]', usage='Usage'),
    'ReplayEntry': dict(request_sha256='str', selection='Selection'),
    'ReplayDocument': dict(schema_version='int', responses='{[ReplayEntry]}'),
    'EvidenceView': dict(observation_id='str', statement='str', source_ref='str', scientific_record_json='str'),
    'Request': dict(case_json='str', category='Category', evidence='[EvidenceView]', instructions='str', feedback='[str]'),
    'PlanStep': dict(category='Category', observed_records='int', initial_status='str'),
    'Exclusion': dict(item_id='str', level='str', reason='str'),
}


def timestamp(value):
    require(type(value) is str, 'EP-WIRE-01', 'Timestamp must be a string')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise PolicyError('EP-WIRE-01', 'Invalid timestamp') from error
    require(parsed.tzinfo is not None, 'EP-WIRE-01', 'Timestamp requires timezone')
    return parsed.astimezone(timezone.utc)


def decode(kind, value, location='input'):
    """Validate and normalize through a private, explicit schema vocabulary."""
    wire = 'EP-WIRE-01'
    if kind.endswith('?'):
        return None if value is None else decode(kind[:-1], value, location)
    if kind.startswith('['):
        require(type(value) is list, wire, location + ': array required')
        return [decode(kind[1:-1], item, location + '[]') for item in value]
    if kind.startswith('{'):
        require(type(value) is dict, wire, location + ': object required')
        require(all(type(key) is str for key in value), wire, 'Non-string JSON key')
        return {key: decode(kind[1:-1], item, location + '.' + key) for key, item in value.items()}
    if kind in SCHEMAS:
        require(type(value) is dict, wire, location + ': object required')
        schema = SCHEMAS[kind]
        require(not set(value) - schema.keys(), wire, location + ': unknown fields')
        result = {}
        for key, specification in schema.items():
            if isinstance(specification, tuple):
                field_type, default = specification
                result[key] = decode(field_type, value[key], location + '.' + key) if key in value else deepcopy(default)
            else:
                require(key in value, wire, location + ': missing ' + key)
                result[key] = decode(specification, value[key], location + '.' + key)
        return result
    if kind in ENUMS:
        require(type(value) is str and value in ENUMS[kind], wire, location + ': invalid enum')
        return value
    if kind == 'any':
        if type(value) is dict:
            return decode('{any}', value, location)
        if type(value) is list:
            return decode('[any]', value, location)
        require(type(value) in (str, int, bool, float, type(None)), wire, location + ': not JSON')
        require(type(value) is not float or math.isfinite(value), wire, 'Nonfinite number')
        return value
    if kind == 'datetime':
        return timestamp(value).isoformat()
    if kind == 'date':
        require(type(value) is str and len(value) == 10, wire, location + ': YYYY-MM-DD required')
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as error:
            raise PolicyError(wire, location + ': invalid date') from error
    if kind == 'float':
        require(type(value) in (int, float) and math.isfinite(value), wire, location + ': finite number required')
        return float(value)
    if kind in ('str', 'int', 'bool'):
        expected = {'str': str, 'int': int, 'bool': bool}[kind]
        require(type(value) is expected, wire, location + ': incorrect scalar type')
        return value
    raise RuntimeError('Unimplemented private schema: ' + kind)
