"""Deterministic bounded selection from already admitted records; no new source access."""
from collections import Counter
from dataclasses import dataclass, replace
import math
import re
import unicodedata

from .agents import SpecialistRequest
from .generated_claims import ClaimSource, GeneratedRequest, make_span_catalog
from .serde import ContractError, Frozen, canonical, fingerprint
from .wire import FORMAT, request_bytes

QUESTION_BM25 = 'question_bm25_v1'
QUESTION_THREE_TERM_OVERLAP = 'question_three_term_overlap_v1'
_CONNECTOR_TRANSLATION = str.maketrans({c: '-' for c in '\u2010\u2011\u2012\u2013\u2014\u2212'})
_TERM = re.compile(r'[^\W_]+(?:[-._:/+*][^\W_]+)*')
_FUNCTION_WORDS = frozenset(
    'a an and are as at be by can did do does for from had has have how in into is it of on or '
    'that the their these they this to was were what when where which who why will with'.split()
)


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


def question_terms(text: str) -> tuple[str, ...]:
    """Tokenize exact source and question text with the same lexical rules."""
    normalized = unicodedata.normalize('NFKC', text).casefold().translate(_CONNECTOR_TRANSLATION)
    return tuple(term for term in _TERM.findall(normalized) if term not in _FUNCTION_WORDS)


def _bm25(terms: tuple[str, ...], documents: list[Counter[str]]) -> list[float]:
    lengths = [sum(document.values()) for document in documents]
    total = sum(lengths)
    if not total or not terms:
        return [0.0] * len(documents)
    count = len(documents)
    average = total / count
    query = set(terms)
    frequency = Counter(term for document in documents for term in document.keys() & query)
    weights = {term: math.log1p((count - frequency[term] + 0.5) / (frequency[term] + 0.5))
               for term in terms}
    k1, b = 1.2, 0.75
    scores = []
    for document, length in zip(documents, lengths):
        normalizer = k1 * (1 - b + b * length / average)
        scores.append(math.fsum(weights[term] * (k1 + 1) * document[term] / (document[term] + normalizer)
                                for term in terms if term in document))
    return scores


def bounded_question_request(request: GeneratedRequest, policy: RetrievalPolicy, *,
                             strategy: str = QUESTION_BM25) -> tuple[GeneratedRequest, dict[str, object]]:
    """Rank a pre-admitted question view, preserving whole sources and their identity."""
    policy.validate()
    if policy.wire_format != 'canonical':
        raise ContractError('Question retrieval requires a canonical request budget')
    if request.question is None:
        raise ContractError('Question retrieval requires an explicit question')
    if strategy not in (QUESTION_BM25, QUESTION_THREE_TERM_OVERLAP):
        raise ContractError('Unknown question retrieval strategy')
    catalog = make_span_catalog(request)
    empty = replace(request, sources=())
    size = len(canonical(empty))
    if size > policy.max_request_bytes:
        raise ContractError('Empty question request exceeds byte cap')

    eligible = tuple(request.sources[offer.source_index] for offer in catalog.offers)
    ids = {source.observation_id for source in eligible}
    excluded = [{'observation_id': source.observation_id, 'reason': 'not_offerable'}
                for source in request.sources if source.observation_id not in ids]
    terms = tuple(dict.fromkeys(question_terms(request.question)))
    documents = [Counter(question_terms(source.text)) for source in eligible]
    if strategy == QUESTION_BM25:
        terms = tuple(sorted(terms))
        scores = _bm25(terms, documents)
    else:
        terms = tuple(sorted(terms, key=len, reverse=True)[:3])
        scores = [sum(term in source for term in terms) for source in documents]

    ranked = sorted(zip(eligible, scores), key=lambda item: (-item[1], item[0].observation_id))
    kept: list[ClaimSource] = []
    for source, score in ranked:
        if not score:
            reason = 'no_query_overlap'
        elif len(kept) == policy.max_records:
            reason = 'record_count_cap'
        else:
            candidate_size = size + len(canonical(source)) + bool(kept)
            if candidate_size <= policy.max_request_bytes:
                kept.append(source)
                size = candidate_size
                continue
            reason = 'whole_record_exceeds_byte_cap'
        excluded.append({'observation_id': source.observation_id, 'reason': reason})
    prepared = replace(request, sources=tuple(kept))
    return prepared, {
        'schema_version': 1, 'ranking': strategy, 'policy': policy,
        'query_terms': terms, 'query_count': 1, 'input_request_sha256': catalog.request_sha256,
        'request_sha256': fingerprint(prepared), 'available_records': len(request.sources),
        'offerable_records': len(eligible), 'request_bytes': size,
        'selected_ids': tuple(source.observation_id for source in kept), 'excluded': excluded,
    }


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
