"""Versioned offline proposal review. Generated claims never enter the selection ledger."""

from __future__ import annotations

import base64
from collections import Counter
from dataclasses import dataclass, fields
from enum import StrEnum
import hashlib
from pathlib import Path
import re

from .atomic import publish_bytes
from .contracts import Case, Category, Citation, GroundedObservation
from .serde import ContractError, Frozen, canonical, decode, fingerprint, parse_json


MAX_RESPONSE_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_SOURCES = 256
MAX_CLAIMS = 32
MAX_QUOTES = 8
MAX_TEXT_BYTES = 8192
_CLAIM_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}')
_SHA256 = re.compile(r'[0-9a-f]{64}')


class Uncertainty(StrEnum):
    LOW = 'low'
    MODERATE = 'moderate'
    HIGH = 'high'
    UNKNOWN = 'unknown'


class Support(StrEnum):
    NOT_ASSESSED = 'not_assessed'
    SUPPORTED = 'supported'
    INSUFFICIENT = 'insufficient'
    CONTRADICTED = 'contradicted'
    MIXED = 'mixed'
    INCOMPATIBLE_SCOPE = 'incompatible_scope'


@dataclass(frozen=True)
class ClaimSource(Frozen):
    observation_id: str
    text: str
    text_sha256: str
    citation: Citation


@dataclass(frozen=True)
class GeneratedRequest(Frozen):
    schema_version: int
    case: Case
    category: Category
    sources: tuple[ClaimSource, ...]

    def validate(self) -> None:
        _source_bytes(self)


@dataclass(frozen=True)
class QuoteSpan(Frozen):
    observation_id: str
    source_sha256: str
    start_byte: int
    end_byte: int
    quote: str


@dataclass(frozen=True)
class ClaimProposal(Frozen):
    claim_id: str
    text: str
    hypothesis_sha256: str
    uncertainty: Uncertainty
    quotes: tuple[QuoteSpan, ...]


@dataclass(frozen=True)
class GeneratedResponse(Frozen):
    schema_version: int
    request_sha256: str
    claims: tuple[ClaimProposal, ...]


_RESPONSE_KEYS = frozenset(field.name for field in fields(GeneratedResponse))
_SELECTION_KEYS = _RESPONSE_KEYS | {'offer_sha256'}


@dataclass(frozen=True)
class SpanOffer(Frozen):
    span_id: str
    source_index: int
    start_byte: int
    end_byte: int


@dataclass(frozen=True)
class SpanCatalog(Frozen):
    """Addresses in the request's ordered, hash-verified sources."""

    request_sha256: str
    offers: tuple[SpanOffer, ...]


@dataclass(frozen=True)
class _SpanSelection(Frozen):
    claim_id: str
    text: str
    hypothesis_sha256: str
    uncertainty: Uncertainty
    span_ids: tuple[str, ...]


@dataclass(frozen=True)
class SupportReview(Frozen):
    """Caller-supplied assessment of one complete proposition in one request."""

    request_sha256: str
    proposal_sha256: str
    method: str
    verdict: Support


@dataclass(frozen=True)
class ProposalResult(Frozen):
    index: int
    proposal: ClaimProposal | None
    disposition: str
    quote_status: str
    support: Support = Support.NOT_ASSESSED
    reason: str | None = None
    review: SupportReview | None = None


@dataclass(frozen=True)
class ClaimAssessment(Frozen):
    schema_version: int
    request_sha256: str
    raw_response: bytes
    envelope_error: str | None
    proposals: tuple[ProposalResult, ...]

    @property
    def accepted(self) -> tuple[ClaimProposal, ...]:
        return tuple(item.proposal for item in self.proposals
                     if item.disposition == 'accepted' and item.proposal is not None)


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _need(condition: bool, reason: str) -> None:
    if not condition:
        raise ContractError(reason)


def _utf8(text: str) -> bytes:
    try:
        return text.encode('utf-8')
    except UnicodeError as error:
        raise ContractError('invalid_utf8_text') from error


def _source_bytes(request: GeneratedRequest) -> dict[str, tuple[ClaimSource, bytes]]:
    _need(type(request.schema_version) is int and request.schema_version == 1, 'unsupported_request_version')
    request.case.validate()
    _need(isinstance(request.category, Category), 'invalid_category')
    _need(len(request.sources) <= MAX_SOURCES, 'too_many_sources')
    sources: dict[str, tuple[ClaimSource, bytes]] = {}
    total = 0
    for source in request.sources:
        _need(bool(source.observation_id.strip()) and source.observation_id not in sources, 'invalid_source_id')
        payload = _utf8(source.text)
        total += len(payload)
        _need(total <= MAX_SOURCE_BYTES, 'source_bytes_exceeded')
        _need(_hash(payload) == source.text_sha256, 'source_text_hash_mismatch')
        _need(bool(source.citation.artifact_id.strip()) and
              _SHA256.fullmatch(source.citation.artifact_sha256) is not None, 'invalid_source_citation')
        sources[source.observation_id] = (source, payload)
    return sources


def make_generated_request(case: Case, category: Category,
                           admitted: tuple[GroundedObservation, ...]) -> GeneratedRequest:
    """Project one already-admitted specialist view. This is not an admission API."""
    _need(len(admitted) <= MAX_SOURCES, 'too_many_sources')
    sources = []
    for item in admitted:
        observation = item.observation
        _need(observation.category == category and observation.target_id == case.hypothesis.target_id
              and observation.indication_id == case.hypothesis.indication_id
              and case.permits_program(observation.program_id), 'source_outside_specialist_scope')
        sources.append(ClaimSource(observation.observation_id, observation.statement,
                                   _hash(_utf8(observation.statement)), item.citation))
    result = GeneratedRequest(1, case, category, tuple(sources))
    _source_bytes(result)
    return result


def _span_catalog(request_sha: str, sources: dict[str, tuple[ClaimSource, bytes]]) -> SpanCatalog:
    offers = tuple(SpanOffer(f's{index + 1:03d}', index, 0, len(payload))
                   for index, (source, payload) in enumerate(sources.values())
                   if len(payload) <= MAX_TEXT_BYTES and source.text.strip())
    return SpanCatalog(request_sha, offers)


def make_span_catalog(request: GeneratedRequest) -> SpanCatalog:
    """Offer each eligible complete statement, preserving order and exact UTF-8."""
    sources = _source_bytes(request)
    return _span_catalog(fingerprint(request), sources)


def _resolve_selection(proposal: _SpanSelection, offers: dict[str, SpanOffer],
                       request: GeneratedRequest) -> ClaimProposal:
    _need(0 < len(proposal.span_ids) <= MAX_QUOTES, 'invalid_quote_count')
    quotes = []
    for span_id in proposal.span_ids:
        offer = offers.get(span_id)
        if offer is None:
            raise ContractError('unknown_span_id')
        source = request.sources[offer.source_index]
        quotes.append(QuoteSpan(source.observation_id, source.text_sha256,
                                offer.start_byte, offer.end_byte, source.text))
    return ClaimProposal(proposal.claim_id, proposal.text, proposal.hypothesis_sha256,
                         proposal.uncertainty, tuple(quotes))


def _verify_quotes(proposal: ClaimProposal, sources: dict[str, tuple[ClaimSource, bytes]]) -> None:
    _need(0 < len(proposal.quotes) <= MAX_QUOTES, 'invalid_quote_count')
    locations = set()
    for span in proposal.quotes:
        entry = sources.get(span.observation_id)
        if entry is None:
            raise ContractError('unknown_evidence_id')
        source, payload = entry
        _need(span.source_sha256 == source.text_sha256, 'quote_source_hash_mismatch')
        _need(0 <= span.start_byte < span.end_byte <= len(payload), 'quote_offset_out_of_range')
        location = (span.observation_id, span.start_byte, span.end_byte)
        _need(location not in locations, 'duplicate_quote_span')
        locations.add(location)
        quoted = _utf8(span.quote)
        _need(bool(span.quote.strip()) and len(quoted) <= MAX_TEXT_BYTES, 'invalid_quote_text')
        _need(payload[span.start_byte:span.end_byte] == quoted, 'quote_text_mismatch')


def assess_generated_response(request: GeneratedRequest, raw: bytes, *,
                              reviews: tuple[SupportReview, ...] = ()) -> ClaimAssessment:
    """Check grounding and scope before applying any independent support verdict.

    An in-limit raw response survives malformed-envelope and per-claim failures.
    The provider payload has no support field. Even a valid exact quote receives
    no support credit without one caller-supplied, request/proposal-bound review.
    """
    return _assess(request, raw, reviews, select_spans=False)


def assess_span_selection(request: GeneratedRequest, raw: bytes, *,
                          reviews: tuple[SupportReview, ...] = ()) -> ClaimAssessment:
    """Resolve the v2 provider's IDs to host-offered spans before support review."""
    return _assess(request, raw, reviews, select_spans=True)


def _assess(request: GeneratedRequest, raw: bytes, reviews: tuple[SupportReview, ...], *,
            select_spans: bool) -> ClaimAssessment:
    _need(type(raw) is bytes and len(raw) <= MAX_RESPONSE_BYTES, 'invalid_or_oversize_generated_response')
    sources = _source_bytes(request)
    request_sha = fingerprint(request)
    catalog = _span_catalog(request_sha, sources) if select_spans else None
    version = 2 if select_spans else 1
    trusted: dict[str, SupportReview] = {}
    _need(len(reviews) <= MAX_CLAIMS, 'too_many_support_reviews')
    for review in reviews:
        _need(review.request_sha256 == request_sha and _SHA256.fullmatch(review.proposal_sha256) is not None
              and bool(review.method.strip()) and isinstance(review.verdict, Support), 'invalid_support_review')
        _need(review.proposal_sha256 not in trusted, 'duplicate_support_review')
        trusted[review.proposal_sha256] = review

    try:
        envelope = parse_json(raw)
        keys = _SELECTION_KEYS if select_spans else _RESPONSE_KEYS
        _need(type(envelope) is dict and envelope.keys() == keys, 'invalid_response_fields')
        _need(type(envelope['schema_version']) is int and envelope['schema_version'] == version,
              'unsupported_response_version')
        _need(envelope['request_sha256'] == request_sha, 'response_request_mismatch')
        if catalog is not None:
            _need(envelope['offer_sha256'] == fingerprint(catalog), 'response_offer_mismatch')
        claims = envelope['claims']
        _need(type(claims) is list and len(claims) <= MAX_CLAIMS, 'invalid_claim_count')
    except ContractError as error:
        return ClaimAssessment(version, request_sha, raw, str(error), ())

    offers = {offer.span_id: offer for offer in catalog.offers} if catalog is not None else {}
    ids = Counter(item['claim_id'] for item in claims if isinstance(item, dict) and type(item.get('claim_id')) is str)
    results = []
    for index, item in enumerate(claims):
        proposal = None
        try:
            candidate = decode(_SpanSelection if select_spans else ClaimProposal, item, f'claim[{index}]')
            if isinstance(candidate, ClaimProposal):
                proposal = candidate
            _need(_CLAIM_ID.fullmatch(candidate.claim_id) is not None, 'invalid_claim_id')
            _need(ids[candidate.claim_id] == 1, 'duplicate_claim_id')
            _need(bool(candidate.text.strip()) and len(_utf8(candidate.text)) <= MAX_TEXT_BYTES, 'invalid_claim_text')
            _need(_SHA256.fullmatch(candidate.hypothesis_sha256) is not None, 'invalid_hypothesis_hash')
        except ContractError as error:
            results.append(ProposalResult(index, proposal, 'rejected', 'not_checked', reason=str(error)))
            continue
        if candidate.hypothesis_sha256 != request.case.hypothesis.key:
            results.append(ProposalResult(index, proposal, 'rejected', 'not_checked', Support.INCOMPATIBLE_SCOPE,
                                          'hypothesis_scope_mismatch'))
            continue
        try:
            proposal = _resolve_selection(candidate, offers, request) if select_spans else candidate
            _verify_quotes(proposal, sources)
        except ContractError as error:
            results.append(ProposalResult(index, proposal, 'rejected', 'invalid', reason=str(error)))
            continue
        review = trusted.get(fingerprint(proposal))
        verdict = review.verdict if review is not None else Support.NOT_ASSESSED
        if verdict == Support.SUPPORTED:
            disposition = 'accepted'
        elif verdict == Support.NOT_ASSESSED:
            disposition = 'pending_review'
        else:
            disposition = 'rejected'
        results.append(ProposalResult(index, proposal, disposition, 'valid', verdict, review=review))
    return ClaimAssessment(version, request_sha, raw, None, tuple(results))


def archive_assessment(path: Path, request: GeneratedRequest, assessment: ClaimAssessment) -> None:
    """Publish the admitted view, exact raw bytes and decisions as one record."""
    _need(assessment.request_sha256 == fingerprint(request), 'assessment_request_mismatch')
    _need(type(assessment.schema_version) is int and assessment.schema_version in (1, 2),
          'unsupported_assessment_version')
    record = {
        'schema_version': assessment.schema_version,
        'request': request,
        'request_sha256': assessment.request_sha256,
        'raw_response_sha256': _hash(assessment.raw_response),
        'raw_response_base64': base64.b64encode(assessment.raw_response).decode('ascii'),
        'envelope_error': assessment.envelope_error,
        'proposals': assessment.proposals,
        'accepted_claim_ids': tuple(item.claim_id for item in assessment.accepted),
        'scientific_validation': 'not_established',
    }
    if assessment.schema_version == 2:
        record['span_catalog'] = make_span_catalog(request)
    publish_bytes(path, canonical(record) + b'\n')
