"""Verify retained replay provenance without reopening or executing its backend.

The source-inclusive path reconstructs requests with the real request builder.
Archived-only verification can bind entries to recorded dispatch fingerprints,
but cannot establish their correspondence to unavailable original evidence.
Unused entries and roles remain permitted, as they are in ReplayBackend.
"""
from collections.abc import Mapping

from .agents import ReplayDocument, Usage, critique, make_request, replay_selection
from .contracts import Category, EvidenceStatus
from .serde import ContractError, decode, encode, fingerprint


def _need(condition, message):
    if not condition:
        raise ContractError('Replay archive: ' + message)


def verify_replay_archive(case, configuration, trace, store=None):
    """Check consumed replay responses; no quote/select or original-path access."""
    try:
        return _verify(case, encode(configuration), encode(trace), store)
    except ContractError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ContractError('Replay archive has malformed provenance or events') from error


def _verify(case, configuration, trace, store):
    proof = configuration.get('backend_provenance')
    _need(isinstance(proof, Mapping) and {'path', 'sha256', 'document'} <= proof.keys(),
          'retained replay provenance is missing')
    _need(isinstance(proof['path'], str) and bool(proof['path']) and
          isinstance(proof['sha256'], str) and len(proof['sha256']) == 64 and
          all(c in '0123456789abcdefABCDEF' for c in proof['sha256']),
          'invalid original replay path/hash declaration')
    document = decode(ReplayDocument, proof['document'])
    _need(document.schema_version == 2, 'retained replay requires schema version 2')
    # The original file hash is intentionally opaque: retained JSON encoding need
    # not reproduce original whitespace, and that original file may be gone.
    records = {}
    feedback = {}
    indices = {}
    failed_quotes = set()
    category_order = {category.value: index for index, category in enumerate(Category)}
    last_category = -1
    active = None
    budget_denied = False
    requests_checked = dispatches = 0
    quote_failures_unreconstructed = 0

    def request_hash(category):
        if store is None:
            return None
        if category not in records:
            records[category] = tuple(item for item in store.query(case, Category(category))
                if item.observation.status == EvidenceStatus.OBSERVED)
        return fingerprint(make_request(case, Category(category), records[category], feedback.get(category, ())))

    def entry(category, expected_hash):
        index = indices.get(category, 0)
        if expected_hash is None:
            # Archived-only budget/quote events have no retained request hash.
            # Still validate entry existence and usage; do not claim reconstruction.
            responses = document.responses.get(category, ())
            if index >= len(responses):
                raise ContractError(f'No recorded response for {category} attempt {index + 1}')
            expected_hash = responses[index].request_sha256
        return replay_selection(document.responses, category, index, expected_hash)

    for event in trace:
        kind, details = event['event'], event['details']
        if kind in ('dispatch', 'backend_quote_failed', 'budget_denied'):
            category = details['category']
            _need(category in category_order and category_order[category] >= last_category,
                  'requests are outside specialist traversal order')
            _need(category not in failed_quotes, 'request follows a terminal quote failure')
            _need(not budget_denied, 'request follows terminal budget denial')
            if active is not None:
                _need(active['accounted'], 'new request precedes previous accounting')
                if category == active['category']:
                    _need(active['reviewed'] and active['problems'] and configuration['review_enabled'],
                          'retry lacks a rejected review')
            last_category = category_order[category]
            expected_hash = request_hash(category)
            if store is not None:
                requests_checked += 1
            if kind == 'backend_quote_failed':
                try:
                    entry(category, expected_hash)
                except ContractError:
                    _need(details['error_class'] == 'ContractError', 'quote failure class differs from replay validation')
                else:
                    if store is not None:
                        raise ContractError('Replay archive: quote failed despite a valid replay entry')
                    # A wrong request fingerprint can explain this failure, but
                    # this mode lacks evidence needed to reconstruct that request.
                    quote_failures_unreconstructed += 1
                active = None
                failed_quotes.add(category)
                continue
            if kind == 'dispatch':
                if expected_hash is not None:
                    _need(details['request_sha256'] == expected_hash, 'dispatch request fingerprint differs from source request')
                else:
                    expected_hash = details['request_sha256']
            selection = entry(category, expected_hash)
            quoted = decode(Usage, details['reserved'] if kind == 'dispatch' else details['quote'])
            _need(quoted == selection.usage, 'reserved quote differs from recorded usage')
            if kind == 'budget_denied':
                budget_denied = True
                active = None
                continue
            index = indices.get(category, 0)
            _need(details['attempt'] == index + 1 and details['attempt_id'] == f'{category}:{index + 1}',
                  'dispatch does not consume replay entries in order')
            active = dict(category=category, attempt_id=details['attempt_id'], selection=selection,
                          accounted=False, reviewed=False, problems=())
            indices[category] = index + 1
            dispatches += 1
        elif kind == 'attempt_accounted':
            _need(active is not None and details['attempt_id'] == active['attempt_id'] and not active['accounted'],
                  'accounting does not match the current replay attempt')
            _need(decode(Usage, details['usage']) == active['selection'].usage,
                  'accounted usage differs from recorded response')
            active['accounted'] = True
        elif kind == 'review':
            _need(active is not None and details['category'] == active['category'] and
                  active['accounted'] and not active['reviewed'], 'review does not match replay attempt')
            selection = active['selection']
            _need(tuple(details['selected']) == selection.observation_ids,
                  'reviewed selections differ from recorded response')
            _need(decode(Usage, details['usage']) == selection.usage, 'review usage differs from recorded response')
            problems = tuple(details['problems'])
            if store is not None:
                candidates = records[active['category']]
                expected_problems = critique(selection, candidates)
                if set(selection.observation_ids) - {r.observation.observation_id for r in candidates}:
                    expected_problems += ('Selection outside the actual bounded request',)
                _need(problems == expected_problems, 'review feedback differs from recorded selection and source candidates')
            active.update(reviewed=True, problems=problems)
            feedback[active['category']] = problems
    if active is not None:
        _need(active['accounted'], 'replay attempt has no accounting')
    return dict(method='retained_replay_v2', status='verified', dispatches_checked=dispatches,
        request_binding='source_reconstructed' if store is not None else 'archived_dispatch_fingerprints',
        requests_reconstructed=requests_checked, quote_failures_unreconstructed=quote_failures_unreconstructed,
        original_replay_path_accessed=False, original_byte_hash='opaque_retained_declaration')
