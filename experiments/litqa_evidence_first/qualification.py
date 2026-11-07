"""Pure qualification-bank metadata and answer checks, never run attestation.

Inputs are captured bytes supplied by an independent reader. This module cannot
issue a run capability, write a receipt, dispatch inference or verify filesystem
identity. A caller must obtain the independently issued execution capability
before using the internal comparison to accept an actual qualification run.
"""
from collections.abc import Mapping
from datetime import datetime
import hashlib
from pathlib import PurePosixPath, PureWindowsPath

from tether_engine.serde import canonical, encode, fingerprint, freeze, parse_json
from experiments.labbench.native_contract import validate_prediction, visible_unsure_index
from experiments.litqa_refinement import contracts

PHASES = ('repair', 'removal')
LABELS = {'increase': 'Increased', 'decrease': 'Decreased', 'no_change': 'Unchanged'}
ACTOR_FIELDS = {'task', 'query', 'candidate_context', 'critique_context', 'sources'}
EXPECTED_FIELDS = {'phase', 'ordinal', 'id', 'answer_index', 'answer_text', 'semantic_role',
                   'allowed_citation_ids', 'required_any_citation_ids', 'empty_citations_required',
                   'allowed_native_outcome', 'producer_status', 'check_status', 'supporting_quotes'}
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024


def _need(ok, why):
    if not ok:
        raise ValueError(why)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    _need(type(raw) is bytes and len(raw) <= MAX_DOCUMENT_BYTES, 'Bounded captured JSON bytes required')
    return parse_json(raw)


def _proof(value):
    _need(isinstance(value, Mapping) and set(value) == {'path', 'sha256', 'bytes'}, 'Exact document proof')
    contracts.digest(value['sha256'])
    _need(type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_DOCUMENT_BYTES, 'Bounded proof size')
    text = value['path']
    _need(isinstance(text, str) and text and '\x00' not in text, 'Document path string')
    path = PureWindowsPath(text) if PureWindowsPath(text).drive else PurePosixPath(text)
    _need(path.is_absolute() and '..' not in path.parts and not text.startswith(('\\\\', '//')), 'Absolute local logical proof path')
    _need(all(not part.endswith((' ', '.')) for part in path.parts[1:]), 'No ambiguous logical path segment')
    return path


def _time(value):
    return datetime.fromisoformat(contracts.utc(value))


def validate_bank_bundle(bank_raw, documents, *, expected_bank_sha256, expected_decision_sha256):
    """Validate exact captured bank bytes and lineage; perform no file I/O.

    ``documents`` maps fifteen declared logical filenames to captured bytes.
    The externally approved decision hash is supplied separately; its source
    document and original role permissions remain the reader's responsibility.
    """
    contracts.digest(expected_bank_sha256)
    contracts.digest(expected_decision_sha256)
    bank = _json(bank_raw)
    _need(_digest(bank_raw) == expected_bank_sha256, 'External bank anchor differs')
    _need(type(bank['schema_version']) is int and bank['schema_version'] == 1 and
          bank['kind'] == 'tether_evidence_first_qualification_bank_v1' and bank['purpose'] == 'fictional_qualification', 'Bank scope')
    _proof(bank['decision'])
    _need(bank['decision']['sha256'] == expected_decision_sha256, 'Approved decision identity differs')
    _need(bank['phase_order'] == list(PHASES) and type(bank['max_native_calls']) is int and bank['max_native_calls'] == 12 and
          type(bank['source_http_requests']) is int and bank['source_http_requests'] == 0, 'Exact twelve-slot zero-retrieval scope')
    _need(canonical(bank['rules']) == canonical(dict(complete_schedule_required=True, all_controls_must_pass=True, automatic_retry=False,
          removal_actor_can_read_full_bank=False, per_slot_only_actor_grants=True, archived_code_executed=False)), 'Complete bank and role rules')
    independence = bank['independence']
    _need(canonical(independence) == canonical(dict(new_prompt_implementation_read=False, benchmark_questions_or_keys_read=False,
          model_or_network_calls=0, expected_answers_shared_with_prompt_author_before_sealing=False, external_human_review=False))
          and type(independence['model_or_network_calls']) is int, 'Independent prospective authorship metadata')
    _time(bank['created_at_utc'])
    names = {'contexts': ('ACTOR.json', 'coordinator_only'), 'ancestry': ('ANCESTRY.json', 'coordinator_only'),
             'expectations': ('EVALUATOR.json', 'evaluation_only')}
    slots = {f'actor_cases/{phase}-{i:04d}.json' for phase in PHASES for i in range(6)}
    _need(isinstance(documents, Mapping) and set(documents) == slots | {x[0] for x in names.values()}, 'Exact fifteen captured documents')
    _need(set(bank['role_files']) == set(names) and set(bank['slots']) == slots, 'Exact role/slot manifest')
    base = None
    seen_paths = set()

    def document(name, proof):
        nonlocal base
        path = _proof(proof)
        if base is None:
            base = path.parent
        expected_path = base.joinpath(*name.split('/'))
        _need(path == expected_path and str(path).casefold() not in seen_paths, 'Distinct declared document location')
        seen_paths.add(str(path).casefold())
        raw = documents[name]
        value = _json(raw)
        _need(len(raw) == proof['bytes'] and _digest(raw) == proof['sha256'], 'Captured document bytes differ')
        return value

    bodies = {}
    for key, (name, role) in names.items():
        entry = bank['role_files'][key]
        _need(set(entry) == {'proof', 'role'} and entry['role'] == role, 'Coordinator/evaluator role separation')
        bodies[key] = document(name, entry['proof'])
    context, ancestry, evaluator = (bodies[k] for k in ('contexts', 'ancestry', 'expectations'))
    _need(set(context) == {'kind', 'scope', 'cases'} and context['kind'] == 'synthetic_refinement_contexts_v1' and
          context['scope'] == 'fictional_qualification', 'Context recipe cannot contain gold metadata')
    _need(ancestry['kind'] == 'synthetic_refinement_ancestry_v1' and ancestry['scope'] == 'fictional_qualification' and
          type(ancestry['actual_prior_model_calls']) is int and ancestry['actual_prior_model_calls'] == 0, 'Invented ancestry scope')
    _need(evaluator['kind'] == 'synthetic_refinement_expectations_v1' and evaluator['role'] == 'evaluation_only', 'Expectation role')
    cases, parents, expected = context['cases'], ancestry['cases'], evaluator['expectations']
    schedule = bank['schedule']
    _need(isinstance(schedule, list) and len(schedule) == len(set(schedule)) == len(cases) == len(parents) == 6 and len(expected) == 12,
          'Full six-case/twelve-slot denominator')
    _need([x['query']['id'] for x in cases] == [x['id'] for x in parents] == schedule, 'Case membership/order')
    _need(all(type(x['ordinal']) is int for x in expected) and
          [(x['phase'], x['ordinal'], x['id']) for x in expected] == [(p, i, key) for p in PHASES for i, key in enumerate(schedule)],
          'Expected slot membership/order')
    counts = {key: 0 for key in (*LABELS, 'unresolved_conflict', 'empty')}
    positive_positions, unsure_positions, prior_types = set(), set(), set()
    stale_resolved = 0
    for i, (case, parent) in enumerate(zip(cases, parents)):
        _need(set(case) == ACTOR_FIELDS - {'task'}, 'Only typed context inputs')
        query, current = contracts.raw_sources(case['query'], case['sources'])
        _, previous = contracts.raw_sources(query, parent['prior_sources'])
        prior = contracts.validate_candidate(query, case['candidate_context'], [p['source_id'] for p in previous])
        critique = contracts.validate_critique(query, prior, case['critique_context'], previous)
        _need(parent['scope'] == 'fictional_qualification' and parent['invented'] is True and
              parent['prior_capture_is_actual_native'] is False and parent['critic_capture_is_actual_native'] is False, 'No synthetic-to-native promotion')
        pc, cc = parent['prior_capture'], parent['critic_capture']
        _need(pc == dict(kind='invented_prior_capture_v1', actual_model_call=False, query=encode(query), prediction=encode(prior['prediction'])) and
              cc == dict(kind='invented_critic_capture_v1', actual_model_call=False, query=encode(query), prior=encode(prior), sources=encode(previous), decoded=encode(critique['decoded'])),
              'Invented capture context lineage')
        _need(prior['native_call_sha256'] == (None if prior['prediction'] is None else fingerprint(pc)) and
              critique['native_call_sha256'] == fingerprint(cc), 'Invented capture hashes')
        unsure = visible_unsure_index(query)
        unsure_positions.add(unsure)
        prior_types.add('absent' if prior['prediction'] is None else 'uncertain' if prior['prediction']['answer_index'] == unsure else 'substantive')
        cutoff, critic_at = _time(parent['cutoff_utc']), _time(parent['critique_created_at_utc'])
        availability = parent['current_source_available_at_utc']
        _need(set(availability) == {s['source_id'] for s in current} and critic_at <= cutoff and
              all(_time(value) <= cutoff for value in availability.values()), 'Complete eligible synthetic chronology')
        for phase in PHASES:
            name = f'actor_cases/{phase}-{i:04d}.json'
            entry = bank['slots'][name]
            _need(set(entry) == {'proof', 'role', 'phase', 'ordinal', 'id'} and entry['role'] == 'single_slot_actor_input' and
                  type(entry['ordinal']) is int and (entry['phase'], entry['ordinal'], entry['id']) == (phase, i, query['id']), 'Slot identity/role')
            actor = document(name, entry['proof'])
            sources = encode(current) if phase == 'repair' else []
            _need(set(actor) == ACTOR_FIELDS and actor == dict(task=phase, query=encode(query), candidate_context=encode(prior), critique_context=encode(critique), sources=sources),
                  'Exact paired projection with no evaluator metadata or removal evidence')
            wanted = expected[(0 if phase == 'repair' else 6) + i]
            _need(set(wanted) == EXPECTED_FIELDS and type(wanted['answer_index']) is int and
                  0 <= wanted['answer_index'] < len(query['choices']) and query['choices'][wanted['answer_index']][4:] == wanted['answer_text'], 'Exact native option index')
            ids = [s['source_id'] for s in sources]
            required = wanted['required_any_citation_ids']
            _need(wanted['allowed_citation_ids'] == ids and wanted['empty_citations_required'] is (not sources) and
                  wanted['allowed_native_outcome'] == 'completed' and wanted['producer_status'] == 'produced' and wanted['check_status'] == 'accepted' and
                  isinstance(required, list) and len(required) == len(set(required)) and set(required) <= set(ids), 'Frozen native/admission/citation requirements')
            if phase == 'removal':
                _need(wanted['answer_index'] == unsure and wanted['semantic_role'] == 'raw_evidence_removed' and
                      not required and not wanted['supporting_quotes'], 'Removal cannot qualify as substantive evidence')
                continue
            relation = wanted['semantic_role']
            _need(relation in counts, 'Declared semantic role')
            counts[relation] += 1
            if relation in LABELS:
                _need(wanted['answer_text'] == LABELS[relation] and wanted['answer_index'] != unsure and required, 'Positive answer cannot abstain')
                positive_positions.add(wanted['answer_index'])
                _need({q['source_id'] for q in wanted['supporting_quotes']} == set(required), 'Required citation rationale binding')
                for quote in wanted['supporting_quotes']:
                    _need(set(quote) == {'source_id', 'text'} and isinstance(quote['text'], str) and quote['text'] and
                          any(s['source_id'] == quote['source_id'] and quote['text'] in s['text'] for s in sources), 'Supporting quote must occur in exact source')
                    stale_resolved += critic_at < _time(availability[quote['source_id']])
            else:
                _need(wanted['answer_index'] == unsure and not required and not wanted['supporting_quotes'], 'Unresolved contexts require uncertainty')
                _need(len(sources) == 2 if relation == 'unresolved_conflict' else not sources, 'Conflict and empty are distinct conditions')
    _need(sum(counts[k] for k in LABELS) == 4 and all(counts[k] > 0 for k in LABELS) and counts['unresolved_conflict'] == counts['empty'] == 1,
          'Four positives with all relation types, one conflict, one empty')
    _need(len(positive_positions) >= 2 and len(unsure_positions) >= 2 and stale_resolved > 0 and
          prior_types == {'absent', 'uncertain', 'substantive'}, 'Varied options/priors and stale critique coverage')
    return freeze(dict(kind='validated_synthetic_bank_metadata_v1', bank_sha256=expected_bank_sha256,
        decision_sha256=expected_decision_sha256, document_sha256={name: _digest(raw) for name, raw in documents.items()},
        schedule=schedule, cases=cases, expectations=expected, counts=counts, execution_capability=False))


def _compare_expectations(metadata, rows):
    """Pure internal comparison. A matching answer list is not qualification."""
    _need(metadata['kind'] == 'validated_synthetic_bank_metadata_v1' and metadata['execution_capability'] is False, 'Bank metadata only')
    expected, cases = metadata['expectations'], metadata['cases']
    _need(isinstance(rows, (list, tuple)) and len(rows) == len(expected) == 12, 'All twelve responses required')
    fields = {'phase', 'ordinal', 'id', 'status', 'producer_status', 'check_status', 'prediction'}
    for row, wanted in zip(rows, expected):
        _need(isinstance(row, Mapping) and set(row) == fields and type(row['ordinal']) is int and
              (row['phase'], row['ordinal'], row['id']) == (wanted['phase'], wanted['ordinal'], wanted['id']), 'Exact response identity/order')
        _need(row['status'] == 'completed' and row['producer_status'] == 'produced' and row['check_status'] == 'accepted', 'Only complete admitted responses')
        prediction = validate_prediction(row['prediction'], cases[wanted['ordinal']]['query'], wanted['allowed_citation_ids'])
        _need(prediction['answer_index'] == wanted['answer_index'], 'Frozen expected answer differs')
        citations = set(prediction['evidence_ids'])
        _need(not wanted['empty_citations_required'] or not citations, 'No citations without raw evidence')
        _need(not wanted['required_any_citation_ids'] or bool(citations & set(wanted['required_any_citation_ids'])), 'Positive answer requires supporting citation')
    return freeze(dict(status='expectations_matched_only', controls=12, native_integrity_verified=False,
        source_execution_verified=False, process_integrity_verified=False, qualification_issued=False))
