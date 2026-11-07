"""Read-only authentication of a captured, rejected token-limit completion.

This is not native answer admission. The caller supplies externally anchored
file proofs and independently reconstructed source/pair inputs. No task codec,
model, transport dispatch, retry or writer is invoked here. The original native
completion validator and original failure records remain unchanged.
"""
from collections.abc import Mapping
import base64
import math
import os
from pathlib import Path
import re
import time
from uuid import UUID

from tether_engine.serde import canonical, encode, fingerprint, freeze, parse_json
from tether_engine.study import native
from experiments.labbench import model as mcq
from experiments.litqa_analysis import native_records as records
from experiments.litqa_refinement import contracts, model

KIND = 'sc05_authenticated_native_limit_failure_v1'
FILES = frozenset((
    'INPUT.json', 'FAILURE.json', 'journal.jsonl',
    'native/request.json', 'native/payload.json', 'native/native-response.bin',
    'native/failure.json', 'native/tokenization/request.json',
    'native/tokenization/result.json', 'native/tokenization/body.bin',
))
MAX_FILE_BYTES = 2 * 1024**2
MAX_TOTAL_BYTES = 8 * 1024**2
CALL_SECONDS = 120
need = contracts.need


def _path(value):
    need(isinstance(value, (str, Path)), 'Explicit original path required')
    path = Path(value)
    need(path.is_absolute() and '..' not in path.parts, 'Absolute nontraversing original path required')
    need(all(not part.endswith(('.', ' ')) for part in path.parts if part != path.anchor),
         'Aliased original path component')
    checked = records.safe_path(path)
    need(os.path.normcase(str(checked.resolve())) == os.path.normcase(str(path)),
         'Noncanonical original path')
    return checked


def _end(deadline):
    now = time.monotonic()
    if deadline is None:
        return now + CALL_SECONDS
    need(type(deadline) in (int, float) and math.isfinite(deadline) and now < deadline <= now + 300,
         'Finite bounded verification deadline required')
    return deadline


def _check_time(end):
    need(time.monotonic() < end, 'Failure verification deadline exceeded')


def _inventory(root):
    expected = {
        '': {'INPUT.json', 'FAILURE.json', 'journal.jsonl', 'native'},
        'native': {'request.json', 'payload.json', 'native-response.bin', 'failure.json', 'tokenization'},
        'native/tokenization': {'request.json', 'result.json', 'body.bin'},
    }
    for name, children in expected.items():
        directory = _path(root / name)
        need(directory.is_dir() and {p.name for p in directory.iterdir()} == children,
             'Exact failed-cell inventory required; no completed or unlisted product')


def _capture(root, files, end):
    need(isinstance(files, Mapping) and set(files) == FILES, 'Complete anchored failed-cell proofs required')
    _inventory(root)
    data = {}
    total = 0
    for name in sorted(FILES):
        _check_time(end)
        value = files[name]
        need(isinstance(value, Mapping) and set(value) == {'path', 'bytes', 'sha256'}, 'Exact captured proof fields')
        need(type(value['bytes']) is int and 0 <= value['bytes'] <= MAX_FILE_BYTES,
             'Failed-cell file byte bound')
        contracts.digest(value['sha256'])
        path = _path(value['path'])
        need(path == root / name, 'Failed-cell proof location differs')
        raw = records.read(path, limit=MAX_FILE_BYTES)
        need(len(raw) == value['bytes'] and records.digest(raw) == value['sha256'], 'Failed-cell proof bytes differ')
        total += len(raw)
        need(total <= MAX_TOTAL_BYTES, 'Failed-cell total byte bound')
        data[name] = raw
    return data


def _journal(raw):
    need(raw.endswith(b'\n'), 'Incomplete failed-cell journal tail')
    events = []
    previous = None
    for line in raw.splitlines():
        value = parse_json(line)
        need(isinstance(value, dict) and set(value) == {'sequence', 'event', 'details', 'previous_sha256', 'sha256'},
             'Exact failed-cell journal fields')
        need(type(value['sequence']) is int and value['sequence'] == len(events)
             and value['previous_sha256'] == previous and isinstance(value['details'], dict),
             'Failed-cell journal sequence')
        digest = value['sha256']
        need(fingerprint({k: v for k, v in value.items() if k != 'sha256'}) == digest,
             'Failed-cell journal hash chain')
        previous = digest
        events.append(value)
    names = ('build_reserved', 'refinement_cell_reserved', 'refinement_call_reserved',
             'mcq_tokenize_attempt', 'mcq_tokenize_terminal', 'refinement_generation_attempt',
             'refinement_call_failed', 'build_failed')
    need(tuple(e['event'] for e in events) == names, 'Exact single failed native attempt required')
    return events


def _duration(value):
    need(type(value) in (int, float) and math.isfinite(value) and 0 <= value < CALL_SECONDS,
         'Bounded native/tokenizer/failure duration required')
    return value


def verify_cell_limit_failure(cell_root, *, files, expected_inputs, expected_request,
                              expected_payload, execution_id, owner_pid, alias,
                              server_spec, bindings, deadline=None):
    """Authenticate one rejected 256-token attempt; return no usable answer.

    ``files`` must come from an external parent inventory, or from the caller's
    just-finished owned cell after its actor scope exits. The enclosing verifier
    must establish scientific source lineage, model assets and process ownership;
    this helper binds those expected identities to the captured cell. JSON is
    parsed as a transport envelope only; assistant content is never task-decoded,
    returned, used for classification, or converted into a prediction.
    """
    end = _end(deadline)
    root = _path(cell_root)
    files, expected_inputs, expected_request, expected_payload = (
        freeze(encode(v)) for v in (files, expected_inputs, expected_request, expected_payload))
    need(isinstance(execution_id, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', execution_id),
         'Original execution identity required')
    need(type(owner_pid) is int and owner_pid > 0, 'Original owned process identity required')
    model.validate_binding(expected_request, expected_payload)
    spec, bindings = freeze(encode(server_spec)), freeze(encode(bindings))
    mcq._server_binding(spec, bindings, expected_request, alias)
    endpoint = native._endpoint(f"http://{spec['host']}:{spec['port']}")[0]
    data = _capture(root, files, end)
    parsed = {name: parse_json(data[name]) for name in FILES if name.endswith('.json')}
    inputs, request, payload = (parsed[name] for name in ('INPUT.json', 'native/request.json', 'native/payload.json'))
    for actual, expected in ((inputs, expected_inputs), (request, expected_request), (payload, expected_payload)):
        need(canonical(actual) == canonical(expected), 'Source-bound original input/member differs')
    need(request['task'] in ('repair', 'removal') and inputs.get('task') == request['task'],
         'Only frozen repair/removal limit failures are eligible')
    context_fields = ('task', 'query', 'candidate_context', 'critique_context', 'sources', 'model_provenance')
    need(set(inputs) == set(context_fields) | {'prepared_member', 'control_sha256'}
         and all(canonical(inputs[key]) == canonical(request[key]) for key in context_fields),
         'Captured source/control context must join the exact native request')
    need(canonical(inputs['prepared_member']) == canonical(dict(status='ready', request=request, payload=payload))
         and inputs['control_sha256'] == fingerprint(dict(query=inputs['query'], candidate=inputs['candidate_context'],
                                                         critique=inputs['critique_context'])),
         'Original pre-generation member/control binding differs')
    need(payload['n_predict'] == 256, 'Original output cap must remain 256')
    quote = parsed['native/tokenization/result.json']
    count = mcq._token_result(quote, payload)
    need(quote['owner_pid'] == owner_pid and quote['endpoint'] == endpoint, 'Tokenizer original owner differs')
    need(canonical(parsed['native/tokenization/request.json']) == canonical(quote['tokenizer_request']),
         'Original tokenizer request differs')
    token_body = base64.b64decode(quote['body_base64'], validate=True)
    need(token_body == data['native/tokenization/body.bin']
         and base64.b64encode(token_body).decode() == quote['body_base64'], 'Original tokenizer bytes differ')
    wrapper, body = native._wrapper(data['native/native-response.bin'], request, payload)
    need(wrapper['owner_pid'] == owner_pid and wrapper['endpoint'] == endpoint, 'Native original owner differs')
    response = parse_json(body)
    need(isinstance(response, dict) and response.get('prompt') == payload['prompt'] and response.get('model') == alias,
         'Native echoed prompt/model differs')
    settings = response.get('generation_settings')
    need(isinstance(settings, dict), 'Native settings missing')
    for key in ('seed', 'temperature', 'n_predict', 'stop', 'stream'):
        need(key in settings and canonical(settings[key]) == canonical(payload[key]), 'Native setting differs: ' + key)
    for key in ('grammar', 'cache_prompt'):
        need(key not in settings or canonical(settings[key]) == canonical(payload[key]), 'Native setting differs: ' + key)
    need(response.get('truncated') is False and response.get('stop') is True
         and response.get('stop_type') == 'limit' and response.get('stopping_word') in (None, ''),
         'Positive untruncated token-limit cause required')
    for key, expected in (('stopped_limit', True), ('stopped_eos', False), ('stopped_word', False)):
        need(key not in response or response[key] is expected, 'Conflicting native limit/stop flags')
    need(isinstance(response.get('content'), str), 'Native content field must retain its transport string type')
    # Do not call native._native or model.decode: the original completion remains
    # rejected, and the possibly partial assistant string has no use here.
    usage = native._usage(response)
    need(usage.input_tokens == count and usage.output_tokens == payload['n_predict'],
         'Limit usage must match original token quote and exact output cap')
    need(usage.input_tokens <= len(payload['prompt'].encode('utf-8')) + 32,
         'Native prompt usage exceeds original byte reservation')
    reservation = dict(input_tokens=max(len(payload['prompt'].encode('utf-8')) + 32, count),
                       output_tokens=payload['n_predict'], cost_usd=0.0)
    need(reservation['input_tokens'] + reservation['output_tokens'] <= request['configuration']['context_tokens'],
         'Original context reservation exceeded')
    failure = parsed['native/failure.json']
    base = dict(status='failed', execution_id=execution_id, task=request['task'],
                request_sha256=fingerprint(request), payload_sha256=fingerprint(payload), generation_entered=True,
                measured_usage=encode(usage), provider_cost_usd=0, conservative_reserved_output_tokens=256,
                call_seconds_cap=CALL_SECONDS, conservative_reserved_input_tokens=reservation['input_tokens'],
                exact_prompt_tokens=count, usage_verified=False, stage='verification', error_type='ContractError')
    need(isinstance(failure, dict) and set(failure) == set(base) | {'wall_seconds'}
         and canonical({k: failure[k] for k in base}) == canonical(base), 'Original failed-call state/accounting differs')
    elapsed = _duration(failure['wall_seconds'])
    need(_duration(wrapper['elapsed_seconds']) + _duration(quote['elapsed_seconds']) <= elapsed,
         'Native/tokenizer timing exceeds original call')
    cell_failure = dict(error_type='ContractError', execution_id=execution_id, automatic_retry=False)
    need(canonical(parsed['FAILURE.json']) == canonical(cell_failure), 'Original cell failure missing or changed')
    events = _journal(data['journal.jsonl'])
    opening = events[0]['details']
    need(set(opening) == {'created_at_utc', 'owner_pid', 'run_id'} and type(opening['owner_pid']) is int
         and opening['owner_pid'] > 0 and str(UUID(opening['run_id'])) == opening['run_id'], 'Cell reservation identity')
    contracts.utc(opening['created_at_utc'])
    reserved = dict(status='started', execution_id=execution_id, task=request['task'],
                    request_sha256=fingerprint(request), payload_sha256=fingerprint(payload), generation_entered=False,
                    measured_usage=None, provider_cost_usd=0, conservative_reserved_output_tokens=256,
                    call_seconds_cap=CALL_SECONDS, path=str(root / 'native'))
    details = (
        dict(execution_id=execution_id, input_sha256=fingerprint(inputs), task=request['task']),
        reserved,
        dict(owner_pid=owner_pid, payload_sha256=fingerprint(payload),
             request_sha256=records.digest(data['native/tokenization/request.json'])),
        dict(elapsed_seconds=quote['elapsed_seconds'], error_class=None, proof_sha256=fingerprint(quote), token_count=count),
        dict(execution_id=execution_id, request_sha256=fingerprint(request), reservation=reservation),
        failure,
        dict(error_class='ContractError', stage='refinement_cell', message=(
            'Native output hit token limit' if response.get('stopped_limit') is True else 'Unqualified native completion cause')),
    )
    need(all(canonical(event['details']) == canonical(expected) for event, expected in zip(events[1:], details)),
         'Original attempt/journal/failure binding differs')
    need(_capture(root, files, end) == data, 'Original failed cell changed during verification')
    _check_time(end)
    return freeze(dict(kind=KIND, status='authenticated_limit_failure', reason='native_completion_limit',
                       producer_status='error', check_status='not_run', prediction=None,
                       execution_id=execution_id, task=request['task'], owner_pid=owner_pid, endpoint=endpoint,
                       input_sha256=fingerprint(inputs), request_sha256=fingerprint(request),
                       payload_sha256=fingerprint(payload), native_response_sha256=files['native/native-response.bin']['sha256'],
                       original_usage_verified=False, raw_reported_usage=encode(usage), raw_usage_checked=True,
                       qualified_usage=None, conservative_reservation=reservation,
                       original_failure=files['native/failure.json'], original_proofs=files,
                       journal_last_sha256=events[-1]['sha256'], automatic_retry=False,
                       source_lineage_scope='caller-reconstructed source/pair identity; no new scientific adjudication'))
