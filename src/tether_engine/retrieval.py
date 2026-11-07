"""Deterministic bounded selection from already admitted records; no new source access."""
from dataclasses import dataclass, replace
import re

from .agents import SpecialistRequest
from .serde import ContractError, Frozen, canonical, fingerprint
from .wire import FORMAT, request_bytes


@dataclass(frozen=True)
class RetrievalPolicy(Frozen):
    max_records: int = 12
    max_request_bytes: int = 12000
    wire_format: str = 'canonical'

    def validate(self):
        if (type(self.max_records) is not int or not 1 <= self.max_records <= 100 or
                type(self.max_request_bytes) is not int or not 1024 <= self.max_request_bytes <= 64000):
            raise ContractError('Invalid bounded retrieval limits')
        if self.wire_format not in ('canonical', FORMAT):
            raise ContractError('Unsupported bounded retrieval transport')


def bounded_request(request: SpecialistRequest, policy: RetrievalPolicy):
    """Rank by literal case-token overlap; ties by observation ID, never provider score.

    Records remain whole and unchanged. A skipped oversized record is reported, not
    truncated into an incomplete scientific observation. Ranking is heuristic, not
    a therapeutic relevance score or evidence weight.
    """
    policy.validate()
    tokens = set(re.findall(r'[a-z0-9_]{3,}', request.case_json.casefold()))
    empty = replace(request, evidence=())
    if len(request_bytes(empty, policy.wire_format, verify=False)) > policy.max_request_bytes:
        raise ContractError('Case/instructions exceed bounded request size')
    ids = [x.observation_id for x in request.evidence]
    if len(ids) != len(set(ids)):
        raise ContractError('Duplicate retrieval observation IDs')
    ranked = sorted(request.evidence, key=lambda x: (
        -len(tokens & set(re.findall(r'[a-z0-9_]{3,}', x.statement.casefold()))), x.observation_id))
    kept, excluded = [], []
    for item in ranked:
        if len(kept) == policy.max_records:
            excluded.append({'observation_id': item.observation_id, 'reason': 'record_count_cap'})
        elif len(request_bytes(replace(request, evidence=tuple(kept + [item])), policy.wire_format, verify=False)) > policy.max_request_bytes:
            excluded.append({'observation_id': item.observation_id, 'reason': 'whole_record_exceeds_byte_cap'})
        else:
            kept.append(item)
    prepared = replace(request, evidence=tuple(kept))
    data = request_bytes(prepared, policy.wire_format)
    # Preserve the original two-field canonical policy encoding and trace hashes.
    archived_policy = {'max_records': policy.max_records, 'max_request_bytes': policy.max_request_bytes}
    if policy.wire_format != 'canonical':
        archived_policy['wire_format'] = policy.wire_format
    audit = {'policy': archived_policy, 'input_request_sha256': fingerprint(request),
        'request_sha256': fingerprint(prepared), 'available_records': len(request.evidence),
        'selected_ids': tuple(x.observation_id for x in kept), 'excluded': excluded,
        'request_bytes': len(data), 'ranking': 'literal_case_overlap_then_id',
        'interpretation': 'selected subset only; excluded records are not biological absence'}
    if policy.wire_format != 'canonical':
        audit.update(logical_request_bytes=len(canonical(prepared)), wire_roundtrip_sha256=fingerprint(prepared))
    return prepared, audit


def verify_retrieval_trace(case, store, trace, policy):
    from .agents import make_request
    from .contracts import Category, EvidenceStatus
    feedback = {}
    for event in trace:
        details = event['details']
        if event['event'] == 'review':
            feedback[details['category']] = tuple(details['problems'])
        elif event['event'] == 'bounded_retrieval':
            category = Category(details['category'])
            records = tuple(r for r in store.query(case, category) if r.observation.status == EvidenceStatus.OBSERVED)
            request = make_request(case, category, records, feedback.get(category.value, ()))
            _, audit = bounded_request(request, policy)
            if fingerprint(audit) != fingerprint({k: v for k, v in details.items() if k not in ('category', 'attempt')}):
                raise ContractError('Bounded retrieval differs from admitted source records/policy')
