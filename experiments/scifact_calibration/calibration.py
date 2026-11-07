"""Fixed SC05 confidence mapping; pure float64 arithmetic, no file or model I/O.

The caller independently verifies all native/source/outcome proofs before using
these functions. Proof shapes and identity joins here do not verify file bytes.
"""
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import sys
import time

CLIP = 1e-6
RIDGE = .01
RESIDUAL_TOLERANCE = 1e-8
MAX_UPDATES = 200000
FIT_SECONDS = 120.0
LABELS = ('CONTRADICT', 'NEI', 'SUPPORT')
CONSTANTS = (CLIP, RIDGE, RESIDUAL_TOLERANCE, MAX_UPDATES, FIT_SECONDS)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    def plain(item):
        if isinstance(item,Mapping):return {key:plain(child) for key,child in item.items()}
        if isinstance(item,(list,tuple)):return [plain(child) for child in item]
        return item
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def number(value, name):
    need(type(value) in (int, float) and math.isfinite(value), 'Finite '+name+' required')
    return float(value)


def probability(value):
    value = number(value, 'probability')
    need(0 <= value <= 1, 'Probability outside [0,1]')
    return value


def proof_digest(value):
    need(isinstance(value,Mapping) and set(value) == {'path', 'bytes', 'sha256'} and
         isinstance(value['path'], str) and value['path'].strip() and
         type(value['bytes']) is int and value['bytes'] >= 0 and
         isinstance(value['sha256'], str) and len(value['sha256']) == 64 and
         all(c in '0123456789abcdef' for c in value['sha256']), 'Missing or malformed source/outcome proof')
    return digest(value)


def logit(score):
    score = probability(score)
    clipped = min(1-CLIP, max(CLIP, score))
    return math.log(clipped)-math.log1p(-clipped), clipped != score


def sigmoid(value):
    value = number(value, 'linear predictor')
    if value >= 0:
        return 1/(1+math.exp(-value))
    exponential = math.exp(value)
    return exponential/(1+exponential)


def softplus(value):
    value = number(value, 'linear predictor')
    return max(value, 0)+math.log1p(math.exp(-abs(value)))


@dataclass(frozen=True)
class Confidence:
    claim_id: int
    document_ids: tuple
    score: float | None
    logit: float | None
    clipped: bool | None
    status: str
    reason: str | None
    native_fingerprint: str | None
    pair_proofs: tuple
    source_proofs: tuple
    selected_probabilities: tuple


def extract_confidence(claim_id, document_ids, pair_records, *, pair_proofs, source_proofs):
    """Preserve unavailable scores as null; never infer zero from a failed pair.

Proof maps are keyed by native integer abstract ID. Completed pair wrappers use
the existing claim_id/abstract_id/status/prediction structure without relabeling.
"""
    documents = ()
    try:
        documents = tuple(document_ids)
        need(type(claim_id) is int and claim_id > 0, 'Canonical claim ID')
        need(len(documents) == len(set(documents)) == 5 and
             all(type(d) is int and d > 0 for d in documents), 'Exactly five unique scheduled documents')
        need(isinstance(pair_records, (list, tuple)) and len(pair_records) == 5 and
             all(type(p['claim_id']) is int and type(p['abstract_id']) is int for p in pair_records) and
             [(p['claim_id'], p['abstract_id']) for p in pair_records] == [(claim_id, d) for d in documents],
             'Missing, duplicate or reordered native pairs')
        need(set(pair_proofs) == set(source_proofs) == set(documents), 'Complete pair/source proofs required')
        pp = tuple(proof_digest(pair_proofs[d]) for d in documents)
        sp = tuple(proof_digest(source_proofs[d]) for d in documents)
        selected = []
        for doc, pair in zip(documents, pair_records):
            need(pair['status'] == 'completed' and isinstance(pair['prediction'], Mapping), 'Native pair unavailable')
            pred = pair['prediction']
            need(type(pred['claim_id']) is int and type(pred['abstract_id']) is int and
                 pred['claim_id'] == claim_id and pred['abstract_id'] == doc, 'Native prediction identity differs')
            ps = pred['label_probs']
            need(isinstance(ps, (list, tuple)) and len(ps) == 3, 'Three native probabilities required')
            ps = tuple(probability(p) for p in ps)
            need(abs(math.fsum(ps)-1) <= 1e-5, 'Native probabilities do not sum to one')
            index = max(range(3), key=ps.__getitem__)
            need(pred['predicted_label'] == LABELS[index], 'Native first-argmax label differs')
            rationale=pred['rationale_probs']
            need(isinstance(rationale,(list,tuple)), 'Native rationale probabilities required')
            rationale=tuple(probability(p) for p in rationale)
            need(isinstance(pred['predicted_rationale'],(list,tuple)) and
                 all(type(i) is int for i in pred['predicted_rationale']) and
                 tuple(pred['predicted_rationale'])==tuple(i for i,p in enumerate(rationale) if p>=.5),
                 'Native fixed rationale threshold differs')
            selected.append(ps[index])
        score = min(selected); x, clipped = logit(score)
        return Confidence(claim_id, documents, score, x, clipped, 'available', None,
                          digest(pair_records), pp, sp, tuple(selected))
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        return Confidence(claim_id, documents, None, None, None, 'unavailable', str(error), None, (), (), ())


@dataclass(frozen=True)
class CalibrationRow:
    id: int
    confidence: Confidence
    produced: bool
    admitted: bool
    strict_success: int
    outcome_proof: str


def calibration_row(claim_id, confidence, *, produced, admitted, strict_success, outcome_proof):
    need(type(claim_id) is int and claim_id > 0 and isinstance(confidence, Confidence) and
         confidence.claim_id == claim_id, 'Outcome/confidence identity differs')
    need(type(produced) is bool and type(admitted) is bool and (produced or not admitted), 'Production/admission states')
    need(type(strict_success) is int and strict_success in (0, 1) and
         (not strict_success or produced and admitted), 'Strict success requires production and admission')
    return CalibrationRow(claim_id, confidence, produced, admitted, strict_success, proof_digest(outcome_proof))


def objective_gradient(xs, ys, a, b):
    """Stable loss plus exact gradient of the specified regularized objective."""
    zs = tuple(a+b*x for x in xs)
    residuals = tuple(sigmoid(z)-y for z, y in zip(zs, ys))
    value = math.fsum(softplus(-z) if y else softplus(z) for z, y in zip(zs, ys))/len(xs)
    value += RIDGE/2*(a*a+(b-1)*(b-1))
    gradient = (math.fsum(residuals)/len(xs)+RIDGE*a,
                math.fsum(r*x for r, x in zip(residuals, xs))/len(xs)+RIDGE*(b-1))
    need(math.isfinite(value) and all(math.isfinite(g) for g in gradient), 'Nonfinite objective/gradient')
    return value, gradient


@dataclass(frozen=True)
class FitResult:
    status: str
    reason: str | None
    a: float | None
    b: float | None
    objective: float | None
    residual: float | None
    updates: int
    lipschitz_bound: float | None
    elapsed_seconds: float
    constant_score: bool
    one_class: bool
    boundary_slope: bool


def fit_coefficients(xs, ys, *, clock=time.monotonic):
    """One fixed projected-gradient fit; callers enforce scientific membership.

No tuning arguments exist. A failed fit returns no applicable coefficients.
"""
    started = clock(); updates = 0; bound = value = residual = None
    constant = one_class = False
    try:
        need(sys.float_info.mant_dig == 53, 'Binary64 arithmetic required')
        xs = tuple(number(x, 'logit') for x in xs)
        need(xs and max(abs(x) for x in xs) <= abs(logit(CLIP)[0])+1e-9, 'Bounded clipped logits required')
        # Bound depends only on this fit's scalar inputs, never its outcomes.
        bound = .25*math.fsum(1+x*x for x in xs)/len(xs)+RIDGE
        need(math.isfinite(bound) and bound > 0, 'Finite positive smoothness bound')
        ys = tuple(ys)
        need(len(xs) == len(ys) and all(type(y) is int and y in (0, 1) for y in ys), 'Complete binary fit outcomes')
        constant, one_class = len(set(xs)) == 1, len(set(ys)) == 1
        a, b = 0., 1.; value, gradient = objective_gradient(xs, ys, a, b)
        for updates in range(1, MAX_UPDATES+1):
            elapsed = clock()-started
            need(math.isfinite(elapsed) and 0 <= elapsed <= FIT_SECONDS, 'Optimizer deadline exceeded')
            next_a, next_b = a-gradient[0]/bound, max(0., b-gradient[1]/bound)
            old_residual = bound*max(abs(next_a-a), abs(next_b-b))
            next_value, next_gradient = objective_gradient(xs, ys, next_a, next_b)
            need(next_value-value <= 1e-12*max(1., abs(value)), 'Optimizer objective increased')
            a, b, value, gradient = next_a, next_b, next_value, next_gradient
            # Recompute the projected residual at the retained solution.
            residual = bound*max(abs((a-gradient[0]/bound)-a), abs(max(0., b-gradient[1]/bound)-b))
            if old_residual <= RESIDUAL_TOLERANCE and residual <= RESIDUAL_TOLERANCE:
                elapsed = clock()-started
                need(math.isfinite(elapsed) and 0 <= elapsed <= FIT_SECONDS, 'Optimizer deadline exceeded')
                return FitResult('complete', None, a, b, value, residual, updates, bound, elapsed,
                                 constant, one_class, b == 0.)
        raise ValueError('Optimizer did not converge within the fixed update limit')
    except (ValueError, OverflowError, ZeroDivisionError) as error:
        elapsed = clock()-started
        return FitResult('failed', str(error), None, None, value, residual, updates, bound,
                         elapsed, constant, one_class, False)


@dataclass(frozen=True)
class FittedMap:
    a: float
    b: float
    training_ids: tuple
    scalar_sha256: str
    label_sha256: str
    group_sha256: str
    lineage_sha256: str
    fit: FitResult
    constants: tuple = CONSTANTS

    def payload(self):
        return dict(schema_version=1, kind='sc05_fixed_monotone_sigmoid_v1', **asdict(self))

    @property
    def fingerprint(self):
        return digest(self.payload())


def apply_mapping(mapping, score, *, expected_fingerprint):
    need(isinstance(mapping, FittedMap) and mapping.fingerprint == expected_fingerprint and
         mapping.constants == CONSTANTS and mapping.fit.status == 'complete' and
         type(mapping.training_ids) is tuple and
         all(type(v) in (int,float) and math.isfinite(v) for v in (mapping.a,mapping.b)) and
         (mapping.a, mapping.b) == (mapping.fit.a, mapping.fit.b) and mapping.b >= 0 and
         mapping.fit.residual <= RESIDUAL_TOLERANCE, 'Immutable qualified mapping identity differs')
    if score is None:
        return None
    return sigmoid(mapping.a+mapping.b*logit(score)[0])


def mapping_from_payload(payload, *, expected_fingerprint):
    """Restore an externally sealed map without refitting or modifying it."""
    fields={'schema_version','kind','a','b','training_ids','scalar_sha256','label_sha256',
            'group_sha256','lineage_sha256','fit','constants'}
    need(type(payload) is dict and set(payload)==fields and digest(payload)==expected_fingerprint and
         payload['schema_version']==1 and payload['kind']=='sc05_fixed_monotone_sigmoid_v1', 'Sealed map payload differs')
    values={k:v for k,v in payload.items() if k not in ('schema_version','kind')}
    values['training_ids']=tuple(values['training_ids']);values['constants']=tuple(values['constants'])
    need(values['training_ids'] and len(set(values['training_ids']))==len(values['training_ids']) and
         all(type(i) is int and i>0 for i in values['training_ids']), 'Sealed training identities')
    for key in ('scalar_sha256','label_sha256','group_sha256','lineage_sha256'):
        need(isinstance(values[key],str) and len(values[key])==64 and all(x in '0123456789abcdef' for x in values[key]),
             'Sealed mapping input fingerprint')
    need(type(values['fit']) is dict and set(values['fit'])==set(FitResult.__dataclass_fields__), 'Sealed optimizer diagnostics')
    values['fit']=FitResult(**values['fit']);fit=values['fit']
    need(fit.status=='complete' and fit.reason is None and type(fit.updates) is int and 1<=fit.updates<=MAX_UPDATES and
         all(type(v) in (int,float) and math.isfinite(v) for v in
             (fit.a,fit.b,fit.objective,fit.residual,fit.lipschitz_bound,fit.elapsed_seconds)) and
         fit.objective>=0 and 0<=fit.residual<=RESIDUAL_TOLERANCE and fit.lipschitz_bound>0 and
         0<=fit.elapsed_seconds<=FIT_SECONDS and all(type(v) is bool for v in
             (fit.constant_score,fit.one_class,fit.boundary_slope)) and fit.boundary_slope==(fit.b==0.),
         'Sealed optimizer did not satisfy fixed limits')
    mapping=FittedMap(**values)
    apply_mapping(mapping,.5,expected_fingerprint=expected_fingerprint)
    return mapping


@dataclass(frozen=True)
class CalibrationSuite:
    status: str
    reason: str | None
    main: FittedMap | None
    deletion_maps: tuple
    held_out_scores: tuple
    attempts: tuple
    coefficient_ranges: tuple
    elapsed_seconds: float
    case_statuses: tuple
    component_assignments: tuple


def _validate_calibration_row(row):
    need(isinstance(row,CalibrationRow) and type(row.id) is int and row.id>0 and
         isinstance(row.confidence,Confidence), 'Canonical calibration row required')
    c = row.confidence
    need(type(c.claim_id) is int and c.claim_id == row.id and c.status == 'available' and c.reason is None and
         all(type(values) is tuple for values in (c.document_ids,c.pair_proofs,c.source_proofs,c.selected_probabilities)) and
         len(c.document_ids) == len(set(c.document_ids)) == len(c.pair_proofs) == len(c.source_proofs) == len(c.selected_probabilities) == 5 and
         all(type(d) is int and d>0 for d in c.document_ids) and
         c.native_fingerprint is not None, 'Every calibration claim needs five valid bound pairs')
    need(all(isinstance(h,str) and len(h)==64 and all(x in '0123456789abcdef' for x in h)
             for h in c.pair_proofs+c.source_proofs+(c.native_fingerprint,)), 'Immutable native/proof binding')
    need(c.score == min(probability(p) for p in c.selected_probabilities), 'Whole-claim minimum differs from native selected probabilities')
    x, clipped = logit(c.score)
    need(c.logit == x and type(c.clipped) is bool and c.clipped == clipped and
         type(row.produced) is bool and type(row.admitted) is bool and
         (row.produced or not row.admitted) and type(row.strict_success) is int and row.strict_success in (0,1) and
         (not row.strict_success or row.produced and row.admitted) and isinstance(row.outcome_proof, str) and
         len(row.outcome_proof) == 64 and all(x in '0123456789abcdef' for x in row.outcome_proof), 'Bound confidence/outcome inconsistent')


def validate_suite(suite, calibration_rows):
    """Reconstruct fit inputs and derived diagnostics from the admitted rows.

    This is arithmetic consistency, not filesystem provenance verification. The
    caller independently admits the original native/source/outcome proof bytes.
    No fit is repeated, and no supplied score or summary is trusted as truth.
    """
    need(isinstance(suite,CalibrationSuite) and suite.status=='complete' and suite.main is not None,
         'Complete calibration suite required')
    rows=tuple(calibration_rows)
    for row in rows:_validate_calibration_row(row)
    ids=tuple(i for i,_ in suite.case_statuses);components=dict(suite.component_assignments)
    need(ids==suite.main.training_ids and tuple(r.id for r in rows)==ids and len(set(ids))==len(ids) and
         tuple(components)==ids and len(suite.component_assignments)==len(ids) and
         all(isinstance(g,str) and g for g in components.values()) and
         all(status=='available' for _,status in suite.case_statuses) and
         tuple(i for i,_ in suite.held_out_scores)==ids,'Complete suite input and held-out membership')
    groups=tuple(sorted(set(components.values())))
    need(tuple(g for g,_ in suite.deletion_maps)==groups and
         tuple(g for g,_ in suite.attempts)==(None,)+groups and len(groups)>=2,'Exact deletion component schedule')
    maps=((None,suite.main),)+suite.deletion_maps
    for (group,mapping),(attempt,fit) in zip(maps,suite.attempts):
        need(group==attempt and mapping.fit==fit and fit.status=='complete' and
             mapping.training_ids==tuple(i for i in ids if components[i]!=group) and
             mapping.group_sha256==digest([(i,components[i]) for i in mapping.training_ids]),
             'Deleted-component training membership or optimizer report differs')
        mapping_from_payload(mapping.payload(),expected_fingerprint=mapping.fingerprint)
        training=tuple(row for row in rows if components[row.id]!=group)
        xs=tuple(row.confidence.logit for row in training);ys=tuple(row.strict_success for row in training)
        need(mapping.scalar_sha256==digest(xs) and mapping.label_sha256==digest(ys) and
             mapping.lineage_sha256==digest([asdict(row) for row in training]),
             'Original calibration scalars, outcomes or lineage differ')
        bound=.25*math.fsum(1+x*x for x in xs)/len(xs)+RIDGE
        value,gradient=objective_gradient(xs,ys,mapping.a,mapping.b)
        residual=bound*max(abs((mapping.a-gradient[0]/bound)-mapping.a),
                           abs(max(0.,mapping.b-gradient[1]/bound)-mapping.b))
        need(fit.lipschitz_bound==bound and fit.objective==value and fit.residual==residual and
             residual<=RESIDUAL_TOLERANCE and fit.constant_score==(len(set(xs))==1) and
             fit.one_class==(len(set(ys))==1), 'Retained fit objective or stationarity differs')
    deleted=dict(suite.deletion_maps)
    held=tuple((row.id,apply_mapping(deleted[components[row.id]],row.confidence.score,
        expected_fingerprint=deleted[components[row.id]].fingerprint)) for row in rows)
    need(suite.held_out_scores==held, 'Held-out scores differ from the original rows and deletion maps')
    ranges=tuple((name,min(getattr(m,name) for _,m in suite.deletion_maps),
                  max(getattr(m,name) for _,m in suite.deletion_maps)) for name in ('a','b'))
    need(suite.coefficient_ranges==ranges, 'Deletion coefficient ranges differ')
    return ids,components


def fit_calibration(rows, ids, components, *, purpose='production', clock=time.monotonic):
    """Validate the entire schedule before the main fit and all deletion fits.

    Only a complete suite exposes maps. A failed fold does not drop other folds;
    exhausted overall time leaves explicit unexecuted attempts. No failed map is
    exposed for application. Caller retains the original rows and proof objects.
    """
    started = clock(); attempts = []; cases = (); assignments = ()
    try:
        rows, ids = tuple(rows), tuple(ids)
        cases = tuple((r.id, r.confidence.status) for r in rows if isinstance(r, CalibrationRow))
        need(purpose in ('production', 'fictional_qualification'), 'Explicit calibration purpose')
        need(ids and len(ids) == len(set(ids)) and all(type(i) is int and i > 0 for i in ids) and
             all(isinstance(r, CalibrationRow) for r in rows) and tuple(r.id for r in rows) == ids,
             'Complete ordered calibration schedule')
        need(set(components) == set(ids) and all(isinstance(components[i], str) and components[i] for i in ids),
             'Complete frozen component mapping')
        groups = tuple(sorted(set(components.values())))
        assignments=tuple((i,components[i]) for i in ids)
        need(len(groups) >= 2, 'At least two calibration components required')
        if purpose == 'production':
            need(len(ids) == 69 and len(groups) == 49 and
                 Counter(Counter(components.values()).values()) == {1:32, 2:15, 3:1, 4:1}, 'Full 69-claim/49-component production calibration')
        for row in rows:
            _validate_calibration_row(row)
        maps = []; held = {}
        for omitted in (None,)+groups:
            elapsed = clock()-started
            if not math.isfinite(elapsed) or not 0 <= elapsed <= FIT_SECONDS*(len(groups)+1):
                attempts.append((omitted, FitResult('unexecuted', 'Calibration suite deadline exceeded',
                    None, None, None, None, 0, None, 0., False, False, False)))
                continue
            training = tuple(r for r in rows if components[r.id] != omitted)
            xs = tuple(r.confidence.logit for r in training); ys = tuple(r.strict_success for r in training)
            result = fit_coefficients(xs, ys, clock=clock); attempts.append((omitted, result))
            if result.status != 'complete':
                continue
            mapping = FittedMap(result.a, result.b, tuple(r.id for r in training), digest(xs), digest(ys),
                digest([(r.id, components[r.id]) for r in training]), digest([asdict(r) for r in training]), result)
            maps.append((omitted, mapping))
            if omitted is not None:
                for row in rows:
                    if components[row.id] == omitted:
                        held[row.id] = apply_mapping(mapping, row.confidence.score, expected_fingerprint=mapping.fingerprint)
        need(all(fit.status=='complete' for _,fit in attempts), 'One or more fixed calibration fits are incomplete')
        need(set(held) == set(ids), 'Every held-out calibration claim requires a deletion prediction')
        deletion = tuple(maps[1:])
        ranges = tuple((name, min(getattr(m, name) for _,m in deletion), max(getattr(m, name) for _,m in deletion))
                       for name in ('a','b'))
        return CalibrationSuite('complete', None, maps[0][1], deletion, tuple((i,held[i]) for i in ids),
                                tuple(attempts), ranges, clock()-started, cases, assignments)
    except (ValueError, TypeError, KeyError) as error:
        return CalibrationSuite('incomplete', str(error), None, (), (), tuple(attempts), (), clock()-started, cases, assignments)
