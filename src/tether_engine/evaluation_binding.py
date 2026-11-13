"""Evaluator-only cohort/producer bindings around descriptive clinical metrics.

Supplied hashes bind selected bytes. They do not authenticate authorship, establish
pre-label registration, attest model execution independently, or validate science.
No agent, downloader or model is invoked by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
from pathlib import Path
import re
import stat
from uuid import UUID

from .artifacts import ADMISSION_POLICY, receipt_policy, verify_run
from .contracts import Case
from .evaluation import EvaluationPolicy, Outcomes, evaluate
from .scorer import Prediction
from .serde import (ContractError, Frozen, MAX_NORMALIZED_JSON_BYTES,
                    decode, encode, fingerprint, parse_json, safe_child, sha256_file)


@dataclass(frozen=True)
class CohortMember(Frozen):
    case_id: str
    case_fingerprint: str
    origin: date
    endpoint: str
    horizon_months: int
    cluster_id: str


@dataclass(frozen=True)
class CohortManifest(Frozen):
    schema_version: int
    kind: str
    cohort_id: str
    label_freeze: date
    policy: EvaluationPolicy
    members: tuple[CohortMember, ...]


@dataclass(frozen=True)
class _FileReference(Frozen):
    path: str
    sha256: str


@dataclass(frozen=True)
class _DeclaredReference(Frozen):
    role: str
    reference: str | None
    sha256: str | None
    reason: str | None


@dataclass(frozen=True)
class _Chronology(Frozen):
    training_cutoff: date | None
    calibration_cutoff: date | None
    generated_at: datetime | None
    unknown_reason: str | None


@dataclass(frozen=True)
class _ExternalProducer(Frozen):
    method_id: str
    method_version: str
    synthetic: bool
    references: tuple[_DeclaredReference, ...]
    chronology: _Chronology


@dataclass(frozen=True)
class _ExternalPrediction(Frozen):
    case_id: str
    case_fingerprint: str
    origin: date
    endpoint: str
    horizon_months: int
    status: str
    probability: float | None
    reason: str | None


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _text(value, name):
    _need(type(value) is str and bool(value.strip()), name + ' must be a nonempty string')
    return value


def _hash(value):
    _need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
          'An exact lowercase SHA-256 is required')
    return value


def _object(value, names, name):
    _need(type(value) is dict and set(value) == set(names), name + ' fields differ')
    return value


def _version(value):
    _need(type(value) is int and value == 1, 'Unsupported evaluation binding schema')


def _path(base, value):
    path = Path(_text(value, 'Artifact path'))
    return path.resolve() if path.is_absolute() else safe_child(base, value)


class _PinnedInputs:
    """Bounded captured JSON bytes plus final rereads, not a hostile-user sandbox."""
    def __init__(self):
        self.pins = {}

    def pin(self, path, expected):
        path, expected = Path(path).resolve(), _hash(expected)
        _need(path not in self.pins or self.pins[path] == expected, 'Conflicting evaluation input hashes')
        self.pins[path] = expected
        return path

    def read(self, path, expected, maximum=MAX_NORMALIZED_JSON_BYTES):
        path = self.pin(path, expected)
        try:
            before = path.stat()
            _need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum,
                  'Evaluation input is not a bounded regular file')
            with path.open('rb') as stream:
                payload = stream.read(maximum + 1)
            after = path.stat()
        except OSError as error:
            raise ContractError('Evaluation input is unavailable: ' + str(path)) from error
        _need(len(payload) <= maximum and len(payload) == before.st_size == after.st_size
              and (before.st_dev, before.st_ino, before.st_mtime_ns)
              == (after.st_dev, after.st_ino, after.st_mtime_ns), 'Evaluation input changed during capture')
        _need(hashlib.sha256(payload).hexdigest() == expected, 'Evaluation input SHA-256 differs: ' + str(path))
        return payload

    def json(self, path, expected):
        return parse_json(self.read(path, expected))

    def recheck(self):
        for path, expected in self.pins.items():
            try:
                actual = sha256_file(path)
            except OSError as error:
                raise ContractError('Evaluation input became unavailable: ' + str(path)) from error
            _need(actual == expected, 'Evaluation input changed after verification: ' + str(path))


def _cohort(document):
    cohort = decode(CohortManifest, document, 'cohort')
    _version(cohort.schema_version)
    _need(cohort.kind == 'fixed_horizon_binary_cohort', 'Unsupported cohort kind')
    _text(cohort.cohort_id, 'Cohort ID')
    cohort.policy.validate()
    members = {}
    for member in cohort.members:
        _text(member.case_id, 'Case ID')
        _text(member.cluster_id, 'Dependence cluster')
        _hash(member.case_fingerprint)
        _need(member.case_id not in members, 'Duplicate cohort member')
        _need(member.endpoint == cohort.policy.endpoint and member.horizon_months == cohort.policy.horizon_months,
              'Cohort member endpoint or horizon differs from policy')
        _need(member.origin <= cohort.label_freeze, 'Cohort member origin is after label freeze')
        members[member.case_id] = member
    return cohort, members


def _membership(records, members):
    _need(type(records) is list, 'Producer records must be an array')
    ids = []
    for row in records:
        _need(type(row) is dict, 'Producer record must be an object')
        ids.append(_text(row.get('case_id'), 'Producer case ID'))
    _need(len(ids) == len(set(ids)) and set(ids) == set(members),
          'Producer records must cover every cohort member exactly once')
    return {row['case_id']: row for row in records}


def _forecast_identity(prediction, member):
    _need((prediction.case_id, prediction.origin, prediction.endpoint, prediction.horizon_months)
          == (member.case_id, member.origin, member.endpoint, member.horizon_months),
          'Prediction case, origin, endpoint or horizon differs from cohort')


def _null_prediction(member, reason, *, synthetic=False):
    return Prediction(member.case_id, member.origin, member.endpoint, member.horizon_months,
                      'abstained', None, reason, None, synthetic, None, None, None, {})


def _tether_predictions(document, base, members, pins):
    _object(document, ('schema_version', 'kind', 'arm_id', 'cohort_sha256', 'records'), 'TETHER producer manifest')
    records = _membership(document['records'], members)
    predictions, bindings, run_ids = [], [], set()
    for member in members.values():
        row = records[member.case_id]
        state = row.get('state')
        common = dict(case_id=member.case_id, case_fingerprint=member.case_fingerprint, state=state)
        if state == 'declared_missing':
            _object(row, ('case_id', 'state', 'reason'), 'Missing prediction declaration')
            reason = _text(row['reason'], 'Missing prediction reason')
            predictions.append(_null_prediction(member, reason))
            bindings.append(dict(common, provenance='unverified_missing_declaration', status='abstained',
                                 probability=None, reason=reason))
            continue
        _need(state == 'sealed_run', 'Unsupported TETHER producer record state')
        _object(row, ('case_id', 'state', 'run_dir', 'run_id', 'receipt_sha256', 'prediction_sha256'),
                'Sealed run binding')
        try:
            run_id = str(UUID(_text(row['run_id'], 'Run ID')))
        except ValueError as error:
            raise ContractError('Invalid run identity UUID') from error
        _need(run_id == row['run_id'] and run_id not in run_ids, 'Duplicate or noncanonical run identity')
        run_ids.add(run_id)
        output = _path(base, row['run_dir'])
        receipt = pins.json(output/'receipt.json', row['receipt_sha256'])
        _need(receipt_policy(receipt) == 'current', 'Production evaluation requires current derivation-policy receipts')
        _need(type(receipt.get('outputs')) is dict, 'Receipt output inventory is missing')
        _need(receipt['outputs'].get('prediction.json') == row['prediction_sha256'],
              'Prediction bytes differ from producer or run receipt')
        for name, digest in receipt['outputs'].items():
            pins.pin(safe_child(output, name), digest)
        auxiliary = receipt.get('auxiliary_outputs', {})
        _need(type(auxiliary) is dict, 'Invalid auxiliary output inventory')
        for name, digest in auxiliary.items():
            pins.pin(safe_child(output, name), digest)
        required = ('inputs.json', 'run.json', 'journal.jsonl')
        _need(all(name in receipt['outputs'] for name in required), 'Incomplete production output inventory')
        inputs = pins.json(output/'inputs.json', receipt['outputs']['inputs.json'])
        run = pins.json(output/'run.json', receipt['outputs']['run.json'])
        prediction = decode(Prediction, pins.json(output/'prediction.json', row['prediction_sha256']), 'prediction')
        journal = pins.read(output/'journal.jsonl', receipt['outputs']['journal.jsonl'])
        events = [parse_json(line) for line in journal.splitlines()]
        _need(events and all(type(event) is dict for event in events), 'Missing run reservation journal')
        reservations = [event for event in events if event.get('event') == 'run_reserved']
        _need(len(reservations) == 1 and events[0] == reservations[0]
              and type(reservations[0].get('details')) is dict
              and reservations[0]['details'].get('run_id') == run_id, 'Run identity differs from durable reservation')
        _need(type(inputs) is dict and 'case' in inputs and fingerprint(inputs['case']) == member.case_fingerprint,
              'Producer full case fingerprint differs from cohort')
        case = decode(Case, inputs['case'], 'run case')
        _need(case.task == 'T1' and case.endpoint is not None, 'Clinical evaluation requires a T1 case endpoint')
        _need((case.case_id, case.origin, case.endpoint.name, case.endpoint.horizon_months)
              == (member.case_id, member.origin, member.endpoint, member.horizon_months),
              'Run case origin, endpoint or horizon differs from cohort')
        _forecast_identity(prediction, member)
        try:
            verified = verify_run(output, row['receipt_sha256'], verify_sources=True)
        except OSError as error:
            raise ContractError('Source-inclusive producer verification failed') from error
        _need(verified.get('byte_integrity') == 'verified'
              and verified.get('semantic_consistency') == 'verified'
              and verified.get('derivation_verification') == 'verified'
              and verified.get('source_binding') == 'current_originals'
              and verified.get('source_inventory_completeness') == 'verified'
              and verified.get('admission_policy') == ADMISSION_POLICY
              and verified.get('external_anchor_checked') is True
              and verified.get('receipt_sha256') == row['receipt_sha256'],
              'Production run verification scope is insufficient')
        predictions.append(prediction)
        bindings.append(dict(common, provenance='source_inclusive_tether_run_receipt', status=prediction.status,
            probability=prediction.probability, reason=prediction.reason, run_id=run_id, run_status=run['status'],
            receipt_sha256=row['receipt_sha256'], prediction_sha256=row['prediction_sha256'],
            engine_verification=verified))
    return tuple(predictions), bindings, None


def _external_predictions(document, base, members, pins):
    _object(document, ('schema_version', 'kind', 'arm_id', 'cohort_sha256', 'prediction_file', 'producer'),
            'External baseline manifest')
    producer = decode(_ExternalProducer, document['producer'], 'external producer')
    _text(producer.method_id, 'External method ID')
    _text(producer.method_version, 'External method version')
    roles = [reference.role for reference in producer.references]
    _need(len(roles) == 3 and set(roles) == {'code', 'configuration', 'model'},
          'External producer must declare code, configuration and model references exactly once')
    for reference in producer.references:
        if reference.reference is not None:
            _text(reference.reference, 'Declared reference')
        else:
            _need(reference.sha256 is None, 'A reference hash requires a declared locator')
        if reference.sha256 is not None:
            _hash(reference.sha256)
        if reference.reference is None or reference.sha256 is None:
            _text(reference.reason, 'Unknown or inapplicable reference explanation')
        elif reference.reason is not None:
            _text(reference.reason, 'Reference explanation')
    chronology = producer.chronology
    if chronology.generated_at is not None:
        _need(all(value is None or value <= chronology.generated_at.date()
                  for value in (chronology.training_cutoff, chronology.calibration_cutoff)),
              'External training or calibration cutoff is after declared prediction generation')
    if any(value is None for value in (chronology.training_cutoff, chronology.calibration_cutoff, chronology.generated_at)):
        _text(chronology.unknown_reason, 'Unknown chronology explanation')
    elif chronology.unknown_reason is not None:
        _text(chronology.unknown_reason, 'Chronology explanation')
    reference = decode(_FileReference, document['prediction_file'], 'external predictions file')
    payload = pins.json(_path(base, reference.path), reference.sha256)
    _object(payload, ('schema_version', 'records'), 'External prediction table')
    _version(payload['schema_version'])
    records = _membership(payload['records'], members)
    predictions, bindings = [], []
    for member in members.values():
        row = decode(_ExternalPrediction, records[member.case_id], 'external prediction')
        _need(row.case_fingerprint == member.case_fingerprint, 'External full case fingerprint differs from cohort')
        _forecast_identity(row, member)
        _need(row.status in ('scored', 'abstained', 'failed'), 'Unsupported external prediction status')
        if row.status == 'scored':
            _need(row.probability is not None and 0 <= row.probability <= 1 and row.reason is None,
                  'Scored external prediction requires probability and no failure reason')
        else:
            _need(row.probability is None, 'Unscored external prediction cannot carry a probability')
            _text(row.reason, 'Unscored external prediction reason')
        predictions.append(Prediction(row.case_id, row.origin, row.endpoint, row.horizon_months,
            row.status, row.probability, row.reason, producer.method_id, producer.synthetic, None, None, None, {}))
        bindings.append(dict(case_id=row.case_id, case_fingerprint=row.case_fingerprint,
            state='external_prediction', provenance='external_producer_declaration', status=row.status,
            probability=row.probability, reason=row.reason))
    declaration = encode(producer)
    declaration['completeness'] = dict(all_required_roles_documented=True,
        references_with_declared_hash=sum(reference.sha256 is not None for reference in producer.references),
        unknown_unhashed_or_inapplicable_roles=[reference.role for reference in producer.references
                                              if reference.reference is None or reference.sha256 is None],
        reference_bytes_verified=False)
    declaration['chronology_qualification'] = dict(status='declared_only_not_historically_qualified',
        training_reaches_origin=[member.case_id for member in members.values()
                                 if chronology.training_cutoff is not None and chronology.training_cutoff >= member.origin],
        calibration_reaches_origin=[member.case_id for member in members.values()
                                    if chronology.calibration_cutoff is not None and chronology.calibration_cutoff >= member.origin])
    return tuple(predictions), bindings, declaration


def evaluate_bound(cohort_path, cohort_sha256, producer_path, producer_sha256, labels_path, labels_sha256,
                   *, allow_synthetic=False, expected_producer_kind='tether_run_predictions'):
    """Verify selected producer bytes before reading labels; never dispatch or repair.

    Engine source-inclusive semantics and external producer declarations are
    separate guarantees. Local anchors do not establish who produced the data
    or when anyone first viewed labels. Legacy outer-launcher replay is outside
    this engine-level evaluation interface.
    """
    _need(type(allow_synthetic) is bool, 'Synthetic evaluation opt-in must be boolean')
    _need(expected_producer_kind in ('tether_run_predictions', 'external_baseline_predictions'),
          'Unsupported evaluation producer kind')
    for digest in (cohort_sha256, producer_sha256, labels_sha256):
        _hash(digest)
    pins = _PinnedInputs()
    cohort, members = _cohort(pins.json(Path(cohort_path), cohort_sha256))
    producer_path = Path(producer_path).resolve()
    producer = pins.json(producer_path, producer_sha256)
    _need(type(producer) is dict, 'Producer manifest must be an object')
    _version(producer.get('schema_version'))
    _need(producer.get('kind') == expected_producer_kind, 'Producer kind differs from selected evaluation route')
    _need(producer.get('cohort_sha256') == cohort_sha256, 'Producer cohort SHA-256 differs')
    _text(producer.get('arm_id'), 'Producer arm ID')
    loader = _tether_predictions if expected_producer_kind == 'tether_run_predictions' else _external_predictions
    predictions, cases, declaration = loader(producer, producer_path.parent, members, pins)
    # Check the exact captured versions before opening any outcome values.
    pins.recheck()
    labels = decode(Outcomes, pins.json(Path(labels_path), labels_sha256), 'outcomes')
    _need(labels.label_freeze == cohort.label_freeze, 'Outcome label freeze differs from cohort')
    _need(len(labels.outcomes) == len(members) and {row.case_id for row in labels.outcomes} == set(members),
          'Outcome membership differs from complete registered cohort')
    for row in labels.outcomes:
        member = members[row.case_id]
        _need((row.origin, row.endpoint, row.horizon_months, row.cluster_id)
              == (member.origin, member.endpoint, member.horizon_months, member.cluster_id),
              'Outcome origin, endpoint, horizon or cluster differs from cohort')
    metrics = evaluate(predictions, labels, allow_synthetic, policy=cohort.policy)
    pins.recheck()
    return dict(schema_version=1, kind='producer_bound_evaluation', role='evaluation_only',
        cohort_id=cohort.cohort_id, arm_id=producer['arm_id'], producer_kind=expected_producer_kind,
        metrics=metrics, cases=cases, binding=dict(cohort_sha256=cohort_sha256, producer_sha256=producer_sha256,
            labels_sha256=labels_sha256,
            prediction_provenance=('source_inclusive_tether_run_receipts' if expected_producer_kind == 'tether_run_predictions'
                                   else 'external_producer_declaration'),
            verified_sealed_runs=sum(row['provenance'] == 'source_inclusive_tether_run_receipt' for row in cases),
            declared_missing_cases=sum(row['provenance'] == 'unverified_missing_declaration' for row in cases),
            source_verification_scope=('at_each_source_inclusive_run_check' if expected_producer_kind == 'tether_run_predictions'
                                       else 'not_performed_external_declaration'),
            final_reread_scope='captured_evaluation_inputs_and_declared_run_artifacts',
            exclusive_or_transactional_source_ownership=False,
            producer_declaration=declaration, independent_authentication=False, prelabel_registration_verified=False,
            scientific_validity='not_established',
            scope='Supplied-anchor byte consistency and stated engine/declaration checks; no independent authorship, timestamp or biological validation.'))
