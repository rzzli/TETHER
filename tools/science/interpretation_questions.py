"""Question-bound interpretation contracts and reversible scientific-first views.

No execution, model adapter or scientific truth validation. Only prepare_question
performs source admission; binding, codecs and validators check structure alone.
Legacy modules and archived responses are deliberately unchanged.
"""
from tether_engine.contracts import Case
from tether_engine.serde import ContractError, canonical, decode, encode, fingerprint, freeze
from tools.science.bounded_interpretation import (
    MAX_BYTES, MAX_RESPONSE_BYTES, Prepared, need, nonempty,
    prepare_input as prepare_sources, validate_response as validate_legacy_claims)


QUESTIONS = freeze({
    'mechanism-report.v1': dict(schema_version=1, question_id='mechanism-report.v1',
        family='mechanism', text=(
            'What experimental or observational mechanism context is reported in the offered sources? '
            'Identify reported manipulation or exposure, model and population, comparator, measured '
            'endpoint and timing when supplied. Distinguish reported findings from the source authors\' '
            'proposals and from your inference. State how context limits applicability to the case '
            'hypothesis. Missing fields remain unprovided; do not assume absent biology or clinical benefit.')),
    'genetic-study-report.v1': dict(schema_version=1, question_id='genetic-study-report.v1',
        family='genetics', text=(
            'What genetic exposure/outcome evidence is reported in the offered sources? Identify '
            'exposure and outcome orientation, study design, instruments/proxies, discovery and '
            'replication where reported, estimates/units and uncertainty when supplied. Separate '
            'cited prior findings from the present study. Explain supported conclusions and limits '
            'of transfer to the intended intervention, modality and tissue. Do not equate '
            'nonsignificance with absence, infer an unknown scale or convert a genetic exposure '
            'association into a drug effect.')),
})


def question_template(family):
    need(isinstance(family, str) and family in QUESTIONS, 'Unknown question family/version')
    return freeze(QUESTIONS[family])


def _scope(source):
    need(isinstance(source, dict) and nonempty(source.get('snapshot_id')) and
         isinstance(source.get('evidence'), list), 'Missing source snapshot/evidence')
    need(all(isinstance(row, dict) and nonempty(row.get('observation_id')) and
             isinstance(row.get('scientific_record'), dict) for row in source['evidence']),
         'Incomplete source scope record')
    return dict(snapshot_id=source['snapshot_id'], observations=[
        dict(observation_id=row['observation_id'],
             scientific_record_sha256=fingerprint(row['scientific_record']))
        for row in source['evidence']])


def validate_request(request):
    """Structure/binding check, NOT evidence admission or temporal verification."""
    request = encode(request)
    need(isinstance(request, dict) and set(request) == {'schema_version', 'role', 'question',
        'question_key', 'hypothesis_key', 'source_scope', 'source_request'}, 'Invalid question request fields')
    need(type(request['schema_version']) is int and request['schema_version'] == 2 and
         request['role'] == 'agent_evidence', 'Wrong question request version/role')
    question = request['question']
    need(isinstance(question, dict) and isinstance(question.get('question_id'), str), 'Missing question identity')
    expected = question_template(question['question_id'])
    need(fingerprint(question) == fingerprint(expected) and request['question_key'] == fingerprint(expected),
         'Question differs from reviewed template')
    source = request['source_request']
    need(isinstance(source, dict) and set(source) == {'schema_version', 'role', 'case', 'hypothesis_key',
         'snapshot_id', 'evidence', 'coverage', 'bounds', 'instructions'}, 'Invalid retained source request')
    need(type(source['schema_version']) is int and source['schema_version'] == 1 and
         source['role'] == 'agent_evidence' and nonempty(source['snapshot_id']) and
         nonempty(source['instructions']), 'Invalid retained source context')
    case = decode(Case, source['case']); case.validate()
    need(case.task == 'T6' and request['hypothesis_key'] == source['hypothesis_key'] == case.hypothesis.key,
         'Question hypothesis/task differs')
    rows = source['evidence']
    need(isinstance(rows, list) and len(rows) <= 1024, 'Invalid question evidence bound')
    identities = set()
    for row in rows:
        need(isinstance(row, dict) and set(row) == {'observation_id', 'admitted_sha256', 'source_ref',
             'statement', 'scientific_record'} and nonempty(row['observation_id']) and
             row['observation_id'] not in identities, 'Invalid/duplicate question source')
        identities.add(row['observation_id'])
        science = row['scientific_record']
        need(isinstance(science, dict) and science.get('observation_id') == row['observation_id'] and
             science.get('statement') == row['statement'] and isinstance(row['statement'], str) and
             science.get('features') == {} and science.get('category') != 'clinical',
             'Invalid visible scientific record')
    coverage = source['coverage']
    need(isinstance(coverage, dict) and type(coverage.get('observations_visible')) is int and
         coverage['observations_visible'] == len(rows) and coverage.get('absence_claim') is False,
         'Coverage differs from selected sources')
    missing = coverage.get('missing_input_count')
    need('missing_input_count' in coverage and (missing is None or type(missing) is int and missing >= 0),
         'Invalid missing-input declaration')
    need(coverage.get('missing_count_basis') == ('snapshot_declaration' if missing is not None else 'not_measured'),
         'Missing-input basis differs')
    if 'observations_available' in coverage:
        need(type(coverage['observations_available']) is int and coverage['observations_available'] >= len(rows),
             'Available source count differs')
    bounds = source['bounds']
    need(isinstance(bounds, dict) and set(bounds) == {'max_claims', 'max_text_bytes', 'max_quotes_per_claim'} and
         type(bounds['max_claims']) is int and 1 <= bounds['max_claims'] <= 64 and
         type(bounds['max_text_bytes']) is int and bounds['max_text_bytes'] == 8192 and
         type(bounds['max_quotes_per_claim']) is int and bounds['max_quotes_per_claim'] == 8,
         'Question bounds differ from source contract')
    need(fingerprint(request['source_scope']) == fingerprint(_scope(source)), 'Selected source scope differs')
    need(len(canonical(request)) <= MAX_BYTES, 'Question request exceeds 64 MiB')
    return freeze(request)


def bind_question(source_request, family):
    """Bind an existing source request; this function does not admit evidence."""
    source = encode(source_request); question = question_template(family)
    need(isinstance(source, dict) and isinstance(source.get('evidence'), list), 'Missing source evidence')
    request = dict(schema_version=2, role='agent_evidence', question=encode(question),
        question_key=fingerprint(question), hypothesis_key=source.get('hypothesis_key'),
        source_scope=_scope(source), source_request=source)
    return validate_request(request)


def prepare_question(case_path, snapshot_path, family, catalog_path=None, *, max_claims=12,
                     max_observations=256, observation_ids=None):
    """Run unchanged complete admission, then copy/freeze question and provenance."""
    question_template(family)  # Unknown templates fail before source loading.
    prepared = prepare_sources(case_path, snapshot_path, catalog_path, max_claims=max_claims,
                               max_observations=max_observations, observation_ids=observation_ids)
    request = bind_question(prepared.request, family)
    return Prepared(request, dict(schema_version=2, kind='question_interpretation_inputs',
        question=encode(request['question']), question_key=request['question_key'],
        source_archive=encode(prepared.archive)))


def scientific_view(request):
    """Reorder original fields without selecting, interpreting or losing data."""
    original = encode(validate_request(request)); source = original.pop('source_request')
    records = []
    for row in source.pop('evidence'):
        science = row.pop('scientific_record')
        present = 'source_metrics' in science; metrics = science.pop('source_metrics', None)
        is_object = isinstance(metrics, dict)
        passages_present = is_object and 'textMiningSentences' in metrics
        passages = metrics.pop('textMiningSentences') if passages_present else None
        records.append(dict(reported_passages=passages, scientific_context=science,
            provider_metadata=metrics, annotation=row, source_metrics_present=present,
            source_metrics_is_object=is_object, passages_present=passages_present))
    view = dict(format='question-scientific-first-v1', request_sha256=fingerprint(request),
                request_context=original, source_request_context=source, records=records)
    need(fingerprint(expand_view(view)) == fingerprint(request), 'Scientific view lost original fields')
    need(len(canonical(view)) <= MAX_BYTES, 'Scientific view exceeds 64 MiB; no truncation')
    return freeze(view)


def expand_view(view):
    """Reconstruct exact original request; local hashes do not prove admission."""
    view = encode(view)
    need(isinstance(view, dict) and set(view) == {'format', 'request_sha256', 'request_context',
         'source_request_context', 'records'} and view['format'] == 'question-scientific-first-v1',
         'Invalid scientific view')
    context, source = view['request_context'], view['source_request_context']
    need(isinstance(context, dict) and 'source_request' not in context and
         isinstance(source, dict) and 'evidence' not in source and isinstance(view['records'], list),
         'Scientific view context collision')
    rows = []
    keys = {'reported_passages', 'scientific_context', 'provider_metadata', 'annotation',
            'source_metrics_present', 'source_metrics_is_object', 'passages_present'}
    for item in view['records']:
        need(isinstance(item, dict) and set(item) == keys and all(type(item[k]) is bool for k in
             ('source_metrics_present', 'source_metrics_is_object', 'passages_present')),
             'Invalid scientific view record/flags')
        science, row, metrics = item['scientific_context'], item['annotation'], item['provider_metadata']
        need(isinstance(science, dict) and 'source_metrics' not in science and
             isinstance(row, dict) and 'scientific_record' not in row, 'Scientific view field collision')
        if not item['source_metrics_present']:
            need(not item['source_metrics_is_object'] and not item['passages_present'] and
                 metrics is None and item['reported_passages'] is None, 'Absent source metrics gained fields')
        else:
            need(item['source_metrics_is_object'] is isinstance(metrics, dict), 'Metric object flag differs')
            if item['source_metrics_is_object']:
                need('textMiningSentences' not in metrics, 'Passage field duplicated')
                if item['passages_present']: metrics['textMiningSentences'] = item['reported_passages']
                else: need(item['reported_passages'] is None, 'Absent passages gained a value')
            else:
                need(not item['passages_present'] and item['reported_passages'] is None,
                     'Opaque metrics cannot supply fabricated passages')
            science['source_metrics'] = metrics
        row['scientific_record'] = science; rows.append(row)
    source['evidence'] = rows; context['source_request'] = source
    result = validate_request(context)
    need(fingerprint(result) == view['request_sha256'], 'Scientific view request fingerprint differs')
    return result


def validate_response(request, response):
    """Check v2 state/identity and exact legacy claims, never scientific entailment."""
    request = encode(validate_request(request)); response = encode(response)
    need(isinstance(response, dict) and set(response) == {'schema_version', 'kind', 'request_sha256',
         'hypothesis_key', 'question_key', 'answer_status', 'claims', 'abstention_reason',
         'features', 'clinical_probability'}, 'Invalid question response fields')
    need(type(response['schema_version']) is int and response['schema_version'] == 2 and
         response['kind'] == 'question_interpretation', 'Wrong question response version/kind')
    need(response['request_sha256'] == fingerprint(request) and
         response['hypothesis_key'] == request['hypothesis_key'] and
         response['question_key'] == request['question_key'], 'Question response identity differs')
    need(response['features'] == {} and response['clinical_probability'] is None,
         'Question response cannot supply predictive features/probability')
    need(len(canonical(response)) <= MAX_RESPONSE_BYTES, 'Question response exceeds bound')
    claims, reason, state = response['claims'], response['abstention_reason'], response['answer_status']
    need(isinstance(claims, list) and isinstance(state, str) and
         state in {'answered', 'partial', 'abstained'}, 'Invalid question answer state')
    need(reason is None or nonempty(reason) and len(reason.encode('utf-8')) <= 8192, 'Invalid abstention reason')
    need((state == 'answered' and bool(claims) and reason is None) or
         (state == 'partial' and bool(claims) and nonempty(reason)) or
         (state == 'abstained' and not claims and nonempty(reason)), 'Claims contradict answer state')
    need(all(isinstance(c, dict) and isinstance(c.get('kind'), str) and
             c['kind'] in {'source_report', 'scientific_inference', 'caution'} for c in claims),
         'Abstention is not an endorsed claim kind')
    source = request['source_request']
    legacy = dict(schema_version=1, kind='generated_interpretation', request_sha256=fingerprint(source),
        hypothesis_key=request['hypothesis_key'], claims=claims, abstention_reason=reason,
        features={}, clinical_probability=None)
    try:
        validate_legacy_claims(source, legacy)  # Transient; never archived as a v1 response.
    except (TypeError, KeyError) as error:
        raise ContractError('Malformed question claim fields') from error
    return freeze(response)
