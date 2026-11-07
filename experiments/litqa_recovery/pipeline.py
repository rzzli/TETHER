"""Full recovered diagnostic answer schedule, with source preflight and replay.

The supervised controller must reserve the parent's exclusive answer authority
before supplying a model callback. This module never owns a model or network
client and never resumes an existing output. A source failure during preflight
leaves every answer unexecuted; it does not manufacture an abstention.
"""
from datetime import datetime
from pathlib import Path
import time

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical, encode, freeze
from experiments.labbench.native_contract import validate_query
from experiments.litqa_comparison import codecs, schedule, pipeline as primary, replay as native_replay
from experiments.litqa_recovery import admission


def _configuration(prepared, queries, hints, cutoff):
    queries = tuple(validate_query(q) for q in queries)
    hints = tuple(hints)
    codecs.need(isinstance(prepared, admission.PreparedCollection), 'Verified recovered collection required')
    codecs.need(canonical(queries) == canonical(prepared.queries) and
                canonical(hints) == canonical(prepared.hints), 'Complete recovered question/hint schedule required')
    cutoff = datetime.fromisoformat(cutoff) if isinstance(cutoff, str) else cutoff
    codecs.need(isinstance(cutoff, datetime) and cutoff.tzinfo is not None, 'Aware recovered evidence cutoff')
    return queries, hints, dict(kind='sc04_recovered_answer_configuration_v2',
        collection_identity=encode(prepared.collection_identity), cutoff=cutoff.isoformat(),
        question_ids=[q['id'] for q in queries], hint_sha256=codecs.digest(canonical(hints)),
        automatic_retry=False, ordinary_retrieval=False, provider_cost_usd=0,
        preflight='All source contexts must pass before any answer dispatch')


def _disposition(query, call, context):
    summary = call['summary']
    if summary['status'] == 'completed':
        codecs.need(summary['request_sha256'] == codecs.digest(canonical(context.request)),
                    'Recovered request differs from admitted context')
        decision = admission.check(context, summary['decoded'], context.request)
        disposition = dict(id=query['id'], producer_status='produced',
            check_status='accepted' if decision['accepted'] else 'rejected',
            prediction=summary['decoded'], reason=decision['reason'])
    else:
        decision = None
        disposition = dict(id=query['id'],
            producer_status='parse_failure' if summary['status'] == 'codec_failure' else 'input_unavailable',
            check_status='not_run', prediction=None, reason=summary['status'])
    return disposition, decision


def _product(query, hint, call, context, context_path, prepared):
    disposition, decision = _disposition(query, call, context)
    return dict(call=call, disposition=disposition, decision=decision,
        context=primary.proof(context_path), hint_sha256=codecs.digest(canonical(hint)),
        collection_identity=encode(prepared.collection_identity), diagnostic_only=True,
        recovery_contract='sc04_recovered_source_context_v2')


def answer(queries, hints, prepared, output, *, seconds, cutoff, model_provenance, call_model):
    """Preflight every context, then enter each answer exactly once."""
    queries, hints, config = _configuration(prepared, queries, hints, cutoff)
    stage = schedule.Stage(tuple(q['id'] for q in queries), 'supplied', output, seconds=seconds)
    preflight = None
    preflight_closed = False
    try:
        publish_bytes(stage.root / 'RECOVERY.json', canonical(config))
        (stage.root / 'products').mkdir()
        preflight = RunJournal(stage.root / 'preflight', kind='build')
        contexts = []
        for index, (query, hint) in enumerate(zip(queries, hints)):
            codecs.need(time.monotonic() < stage.deadline - 10, 'Recovered source preflight exceeded deadline')
            preflight.append('context_check_started', ordinal=index, id=query['id'])
            context = admission.capture(query, hint, prepared, cutoff, model_provenance,
                                        deadline=min(stage.deadline - 10, time.monotonic() + 120))
            path = preflight.output / f'{index:04d}.json'
            publish_bytes(path, canonical(context.report))
            contexts.append(context)
            preflight.append('context_checked', ordinal=index, context=primary.proof(path))
        preflight.append('all_contexts_checked', questions=len(contexts))
        preflight.close()
        preflight_closed = True

        def operation(slot, end):
            index = slot['ordinal']
            query, hint, context = queries[index], hints[index], contexts[index]
            root = stage.root / 'products' / f'{index:04d}'
            call = primary._model_result(
                call_model('answer', query, context.sources, root, min(end - 10, time.monotonic() + 120)),
                'answer', query, context.sources)
            codecs.need(Path(call['root']).resolve() == root.resolve(),
                        'Recovered model cell escaped its scheduled output')
            publish_bytes(root / 'CONTEXT.json', canonical(context.report))
            return dict(status='completed', reason=None,
                        product=_product(query, hint, call, context, root / 'CONTEXT.json', prepared))

        for _ in stage.schedule:
            stage.call(operation)
        admission.revalidate(prepared, deadline=stage.deadline - 10)
        return stage.finish()
    except BaseException as error:
        stage.failed = True
        try:
            publish_bytes(stage.root / 'ANSWER-FAILURE.json', canonical(dict(
                error_type=type(error).__name__, entered=stage.cursor, scheduled=len(stage.schedule),
                automatic_retry=False, scientific_scoring=False)))
            if preflight is not None and not preflight_closed:
                preflight.fail(error, 'recovered_answer')
        except BaseException as secondary:
            error.add_note('Recovery answer failure retention: ' + type(secondary).__name__)
        if not stage.closed:
            try:
                stage.finish()
            except BaseException as secondary:
                error.add_note('Recovery answer partial finalization: ' + type(secondary).__name__)
        raise
    finally:
        if preflight is not None:
            preflight.close()


def replay_answers(root, receipt_sha, queries, hints, prepared, *, cutoff, model_info):
    """Rebuild contexts/native products and exact preflight events without calls."""
    queries, hints, config = _configuration(prepared, queries, hints, cutoff)
    root = Path(root).resolve()
    codecs.need(canonical(native_replay.load(root / 'RECOVERY.json')) == canonical(config),
                'Recovered answer configuration differs')
    rows = primary.parent_rows(root, receipt_sha, 'supplied', tuple(q['id'] for q in queries))
    from experiments.litqa_analysis.native_records import journal
    events = journal(root / 'preflight/journal.jsonl')
    codecs.need(len(events) == 2 + 2 * len(queries) and events[0]['event'] == 'build_reserved',
                'Recovered preflight event count')
    for index, (query, hint) in enumerate(zip(queries, hints)):
        cell = root / 'products' / f'{index:04d}'
        context = admission.capture(query, hint, prepared, cutoff, model_info['provenance'])
        preflight_path = root / 'preflight' / f'{index:04d}.json'
        codecs.need(canonical(native_replay.load(preflight_path)) == canonical(context.report) ==
                    canonical(native_replay.load(cell / 'CONTEXT.json')), 'Recovered source context replay')
        started, checked = events[1 + 2 * index:3 + 2 * index]
        codecs.need(started['event'] == 'context_check_started' and started['details'] ==
                    dict(ordinal=index, id=query['id']) and checked['event'] == 'context_checked' and
                    checked['details'] == dict(ordinal=index, context=primary.proof(preflight_path)),
                    'Recovered preflight journal binding')
        call = native_replay.model_cell(cell, 'answer', query, context.sources, model_info)
        expected = _product(query, hint, call, context, cell / 'CONTEXT.json', prepared)
        row = rows[(query['id'], 'shared')]
        codecs.need(row['status'] == 'completed' and row['reason'] is None and
                    canonical(row['product']) == canonical(expected), 'Recovered native answer product differs')
    codecs.need(events[-1]['event'] == 'all_contexts_checked' and events[-1]['details'] ==
                dict(questions=len(queries)), 'Recovered preflight completion binding')
    admission.revalidate(prepared)
    return freeze(dict(status='verified', questions=len(queries), diagnostic_only=True,
        ordinary_retrieval=False, recovery_contract='sc04_recovered_source_context_v2',
        scientific_correctness='Not evaluated by maintained replay'))
