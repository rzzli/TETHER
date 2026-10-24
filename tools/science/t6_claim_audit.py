"""Evaluator-only atomic claim audit. This validates reviews, not scientific truth.

Version one resolves bounded JSON originals. Parquet/PDF require separately
qualified adapters; supplied extracts cannot masquerade as original-row checks.
No runtime admission, model invocation, scoring or numerical feature writes.
"""
from collections import Counter
import hashlib
from pathlib import Path
import re

from asof.serde import ContractError, fingerprint, parse_json

MAX_SOURCE_BYTES = 64 * 1024 * 1024
ENTAILMENT = {'supported', 'contradicted', 'unsupported', 'unassessable'}
APPLICABILITY = {'applicable', 'context_mismatch', 'uncertain', 'not_claimed'}
CITATION = {'supported', 'missing', 'misattributed', 'unassessable'}
KINDS = {'resource_observation', 'scientific_interpretation'}
HYPOTHESIS_FIELDS = {'target_id', 'indication_id', 'target_namespace_version',
                     'indication_namespace_version', 'intended_action', 'modality', 'tissue'}


def require(condition, message):
    if not condition:
        raise ContractError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def pointer(document, location):
    require(isinstance(location, str) and (location == '' or location.startswith('/')),
            'Expected an RFC6901 JSON pointer')
    for part in location.split('/')[1:]:
        require(re.search(r'~(?![01])', part) is None, 'Invalid JSON pointer escape')
        part = part.replace('~1', '/').replace('~0', '~')
        try:
            if isinstance(document, list):
                require(bool(re.fullmatch(r'0|[1-9][0-9]*', part)), 'Noncanonical array index')
                document = document[int(part)]
            else:
                require(isinstance(document, dict), 'Pointer traverses a scalar')
                document = document[part]
        except (KeyError, IndexError) as exc:
            raise ContractError('Unresolvable original source pointer') from exc
    return document


def validate_question(question):
    require(isinstance(question, dict) and set(question) == HYPOTHESIS_FIELDS,
            'Audit question needs target, indication, namespace versions, action, modality and tissue')
    require(all(text(question[k]) for k in HYPOTHESIS_FIELDS - {'tissue'}),
            'Question identifiers/action/modality must be explicit')
    require(question['tissue'] is None or text(question['tissue']), 'Invalid tissue')


def validate_claims(manifest):
    require(isinstance(manifest, dict) and type(manifest.get('schema_version')) is int
            and manifest['schema_version'] == 1 and manifest.get('role') == 'evaluation_only',
            'Claim inventory must use evaluation-only schema 1')
    validate_question(manifest.get('question'))
    require(text(manifest.get('dossier_sha256')) and
            bool(re.fullmatch('[0-9a-f]{64}', manifest['dossier_sha256'])), 'Missing sealed dossier digest')
    require(manifest.get('atomization_status') == 'reviewed_complete',
            'A reviewer must attest complete atomic claim inventory, including unsupported claims')
    require(text(manifest.get('atomizer_id')), 'Missing atomizer identity')
    claims = manifest.get('claims')
    require(isinstance(claims, list), 'Missing claim inventory')
    ids, statements = [], []
    for claim in claims:
        require(isinstance(claim, dict) and text(claim.get('claim_id')) and text(claim.get('statement')),
                'Atomic claim needs identity and exact statement')
        require(isinstance(claim.get('kind'), str) and claim['kind'] in KINDS, 'Unknown claim kind')
        require(claim.get('question_sha256') == fingerprint(manifest['question']),
                'Claim question/action/modality/tissue binding differs')
        require(type(claim.get('atomicity_attested')) is bool and claim['atomicity_attested'],
                'Composite or unreviewed claims must be split before audit')
        cited = claim.get('cited_source_ids')
        require(isinstance(cited, list) and all(text(x) for x in cited) and len(set(cited)) == len(cited),
                'Invalid or duplicated claim citations')
        ids.append(claim['claim_id'])
        statements.append((claim['statement'], claim['kind'], claim['question_sha256']))
    require(len(ids) == len(set(ids)), 'Duplicate atomic claim identity')
    require(len(statements) == len(set(statements)), 'Repeated atomic statement must not inflate denominator')
    return claims


def resolve_sources(sources, approved_roots):
    """Hash every explicitly approved JSON original; never follows a URL."""
    require(isinstance(sources, list) and bool(approved_roots), 'Explicit source inventory/roots required')
    roots = [Path(p).resolve() for p in approved_roots]
    seen, resolved, originals = set(), {}, {}
    for source in sources:
        require(isinstance(source, dict) and text(source.get('source_id')), 'Invalid source identity')
        identity = source['source_id']
        require(identity not in resolved, 'Duplicate source identity')
        proof = source.get('original')
        require(isinstance(proof, dict) and text(proof.get('path')), 'Missing original proof')
        path = Path(proof['path']).resolve()
        require(any(path.is_relative_to(root) for root in roots), 'Source outside approved roots')
        require(source.get('format') == 'json', 'Unqualified source format: JSON originals only in v1')
        require(type(proof.get('bytes')) is int and 0 < proof['bytes'] <= MAX_SOURCE_BYTES,
                'Original source exceeds audit size bound')
        if path not in originals:
            require(path.is_file(), 'Original source is not a file')
            with path.open('rb') as stream:
                payload = stream.read(MAX_SOURCE_BYTES + 1)
            require(len(payload) <= MAX_SOURCE_BYTES, 'Original source exceeds audit size bound')
            originals[path] = (len(payload), hashlib.sha256(payload).hexdigest(), parse_json(payload))
        size, digest, document = originals[path]
        require(size == proof['bytes'] and digest == proof.get('sha256'), 'Original source proof changed')
        location = source.get('json_pointer')
        row = pointer(document, location)
        require(fingerprint(row) == source.get('value_sha256'), 'Original row fingerprint differs')
        unit = (proof['sha256'], location)
        require(unit not in seen, 'Same original row cannot become independent duplicate evidence')
        seen.add(unit)
        resolved[identity] = row
    return resolved


def audit_claims(manifest, review, sources, approved_roots):
    """Replay source bindings and return descriptive counts with separate denominators.

    A supported source statement can be inapplicable to the proposed intervention.
    Unsupported does not mean false. Agreement cannot establish therapeutic truth.
    """
    claims = validate_claims(manifest)
    original_rows = resolve_sources(sources, approved_roots)
    require(isinstance(review, dict) and type(review.get('schema_version')) is int and
            review['schema_version'] == 1 and review.get('role') == 'evaluation_only', 'Invalid audit review')
    require(review.get('claims_sha256') == fingerprint(manifest) and
            review.get('sources_sha256') == fingerprint(sources), 'Review inventory binding differs')
    require(text(review.get('reviewer_id')) and review.get('review_mode') == 'blinded_source_review',
            'Review needs a blinded source reviewer identity')
    require(review.get('therapeutic_truth') == 'not_established', 'Source audit cannot certify therapeutic truth')
    rows = review.get('claims')
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows) and
            [r.get('claim_id') for r in rows] == [c['claim_id'] for c in claims],
            'Review must cover every atomic claim exactly once in frozen order')
    entailment, applicability, citations = Counter(), Counter(), Counter()
    for claim, row in zip(claims, rows):
        require(not set(claim['cited_source_ids']) - original_rows.keys(), 'Claim cites absent source')
        require(isinstance(row.get('entailment'), str) and row['entailment'] in ENTAILMENT and
                isinstance(row.get('applicability'), str) and row['applicability'] in APPLICABILITY,
                'Invalid entailment or applicability state')
        require(isinstance(row.get('citation_status'), str) and row['citation_status'] in CITATION,
                'Missing citation-support judgment')
        require(text(row.get('reason')) and isinstance(row.get('uncertainty'), str) and
                row['uncertainty'] in {'low', 'moderate', 'high'},
                'Review needs rationale and explicit uncertainty')
        evidence = row.get('evidence_source_ids')
        require(isinstance(evidence, list) and all(text(i) for i in evidence) and
                len(set(evidence)) == len(evidence) and not set(evidence) - original_rows.keys(),
                'Judgment evidence must resolve to distinct verified original rows')
        require(row['entailment'] == 'unassessable' or evidence,
                'A substantive entailment judgment needs source evidence')
        if row['citation_status'] == 'supported':
            require(row['entailment'] == 'supported' and
                    bool(set(claim['cited_source_ids']) & set(evidence)),
                    'Citation support requires supported entailment and cited original evidence')
        require((row['citation_status'] == 'missing') == (not claim['cited_source_ids']),
                'Missing-citation judgment contradicts the explicit citation inventory')
        require(claim['kind'] != 'scientific_interpretation' or row['applicability'] != 'not_claimed',
                'Interpretation requires a contextual applicability assessment')
        entailment[row['entailment']] += 1
        applicability[row['applicability']] += 1
        citations[row['citation_status']] += 1
    assessed = len(claims) - entailment['unassessable']
    return dict(schema_version=1, role='evaluation_only', status='source_bindings_and_review_contract_verified',
        claims_sha256=fingerprint(manifest), review_sha256=fingerprint(review), sources_sha256=fingerprint(sources),
        claim_count=len(claims), assessable_claim_count=assessed,
        entailment={k: entailment[k] for k in sorted(ENTAILMENT)},
        applicability={k: applicability[k] for k in sorted(APPLICABILITY)},
        citation_status={k: citations[k] for k in sorted(CITATION)},
        contradiction_fraction_assessable=entailment['contradicted'] / assessed if assessed else None,
        unsupported_fraction_assessable=entailment['unsupported'] / assessed if assessed else None,
        therapeutic_truth='not_established',
        limitations='Supplied original bytes/locators and review structure verified; external source authenticity, dossier provenance, atomic completeness, entailment, blinding and applicability need separate qualification. No clinical validation or independent evidence count is inferred.')
