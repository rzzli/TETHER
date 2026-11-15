"""Reason-qualified software controls, separate from archived decision agreement.

The caller must freeze specific reasons before evaluating responses. Legacy
oracles without reasons cannot be promoted to this metric by inference.
"""
from tether_engine.serde import ContractError


def score_conformance(expected, observed):
    def index(rows):
        result = {}
        for row in rows:
            key = row.get('case_id')
            if not isinstance(key, str) or not key or key in result:
                raise ContractError('Unique conformance case IDs required')
            result[key] = row
        return result
    oracle, results = index(expected), index(observed)
    if not oracle or set(results) - set(oracle):
        raise ContractError('Conformance requires a nonempty fixed scheduled population')
    rows = []
    for key, want in oracle.items():
        decision, reason = want.get('decision'), want.get('reason_code')
        if decision not in ('accept', 'reject') or (decision == 'accept' and reason is not None) or (
                decision == 'reject' and (not isinstance(reason, str) or not reason.strip())):
            raise ContractError('Conformance oracle requires a specific rejection reason')
        actual = results.get(key, {'decision': 'no_decision', 'reason_code': None})
        if actual.get('decision') not in ('accept', 'reject', 'error', 'no_decision'):
            raise ContractError('Unknown conformance decision')
        match = actual.get('decision') == decision and actual.get('reason_code') == reason
        rows.append({'case_id': key, 'expected_decision': decision, 'expected_reason': reason,
                     'decision': actual.get('decision'), 'reason_code': actual.get('reason_code'),
                     'strict_match': match})
    def rate(selected):
        numerator = sum(row['strict_match'] for row in selected)
        return {'numerator': numerator, 'denominator': len(selected),
                'rate': numerator / len(selected) if selected else None}
    valid = rate([row for row in rows if row['expected_decision'] == 'accept'])
    invalid = rate([row for row in rows if row['expected_decision'] == 'reject'])
    return {'metric': 'reason_qualified_conformance_v1', 'scheduled_cases': len(rows),
            'valid_acceptance': valid, 'reason_correct_rejection': invalid,
            'strict_case_agreement': rate(rows),
            'balanced_rate': (valid['rate'] + invalid['rate']) / 2 if valid['denominator'] and invalid['denominator'] else None,
            'qualification_passed': bool(valid['denominator'] and invalid['denominator'] and all(row['strict_match'] for row in rows)),
            'rows': rows, 'scientific_validation': 'not_established'}
