"""Finite source/token preparation. No native adapter, server or answer generation."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import time

from asof.atomic import publish_bytes
from asof.serde import canonical, encode, fingerprint, freeze, parse_json
from asof.study.preparation_payloads import prepare_payloads
from asof.study.source_preparation import prepare_source_request, verify_source_preparation
from asof.study.tokenization import prepare_tokenizer_spec, tokenize_prompt, verify_tokenization
from asof.study.stable_read import deadline_check

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
MODEL = Path(r'E:\projects_data\drug_target_agents_data\models\qwen25-14b-q4km-20261018T032528Z')
RAW = MODEL.parents[1]
AUTH = '8a98d96c14193e5298384f90982ae30943de6927de80654c6b99eed9ae7f027a'
EXPECTED = '14b735ef940bde56c04ea964cf145f3f7d1e343b2fe1e35de157cc8a5af2d61a'
protocol_raw = (HERE/'REAL-PREPARATION-PROTOCOL-v2.json').read_bytes()
protocol = parse_json(protocol_raw)
assert protocol['source_authority_sha256'] == AUTH
OUT = ROOT / 'data/cache' / ('r09-token-aware-preparation-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir(exist_ok=False)
stage = 'source_preparation'
started = time.monotonic()
deadline = started + 300
state = dict(schema_version=1, status='running', output=str(OUT),
             generation_calls=0, provider_spend_usd=0, children=[], protected_read_attempts=[],
             network_attempts=[], native_execution_authorized=False, scientific_validation='not_performed')


def save(name, value):
    publish_bytes(OUT/name, canonical(value))


def guard(event, args):
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).absolute()
        if {'benchmark', 'gold_evidence', 'adjudication', 'completed-responses'}.intersection(p.lower() for p in path.parts):
            state['protected_read_attempts'].append(str(path))
            raise PermissionError('Protected evaluation payload unavailable to preparation')
        if path.is_relative_to(RAW):
            mode, flags = args[1:3]
            if isinstance(mode, str) and any(c in mode for c in 'wax+') or isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
                raise PermissionError('Original data root is read-only for this preparation')
    if event == 'socket.connect':
        state['network_attempts'].append(event)
        raise PermissionError('No network in finite preparation')
    if event == 'subprocess.Popen':
        exe, argv = args[:2]
        expected = subprocess.list2cmdline(list(spec['argv'])) if isinstance(argv, str) else list(spec['argv'])
        if stage != 'token_quotation' or argv != expected or len(state['children']) >= 6:
            raise PermissionError('Only six approved offline tokenizer children allowed')
        state['children'].append(dict(executable=str(exe), argv=list(spec['argv'])))


sys.addaudithook(guard)
save('protocol.json', protocol)
try:
    source = prepare_source_request(HERE/'SOURCE-AUTHORITY-v1.json', AUTH,
        {'project': ROOT, 'raw': RAW}, OUT/'source', deadline=deadline)
    request = parse_json((OUT/'source/request.json').read_bytes())
    assert fingerprint(request) == EXPECTED == source['request_sha256']
    payloads = prepare_payloads(request)
    save('payloads.json', payloads)
    state.update(source_receipt_sha256=source['receipt_sha256'], request_sha256=EXPECTED)
    stage = 'asset_preparation'
    spec = prepare_tokenizer_spec(
        {'inventory': {'root_id': 'project', 'relative_path': 'planning/review-assets/recovery-step5-20261026/inventory.json'},
         'acquisition': {'root_id': 'model', 'relative_path': 'acquisition.json'}},
        {'project': ROOT, 'model': MODEL}, deadline=deadline)
    save('tokenizer-spec.json', spec)
    records = []
    for index, cell in enumerate(payloads):
        deadline_check(deadline)
        stage = 'token_quotation'
        quote = tokenize_prompt(cell['payload']['prompt'], spec, deadline,
                                OUT/f'token-{index:02d}', payload_sha256=cell['payload_sha256'])
        count = quote['quote']['token_count']
        assert count + 32 + 1024 <= 16384
        records.append(dict(index=index, arm=cell['arm'], stage_name=cell['stage_name'],
            prompt_sha256=hashlib.sha256(cell['payload']['prompt'].encode()).hexdigest(),
            payload_sha256=cell['payload_sha256'], receipt_sha256=quote['receipt_sha256'],
            token_count=count, input_reservation=count+32,
            output_reservation=1024, prompt_utf8_bytes=cell['prompt_utf8_bytes'],
            http_payload_bytes=cell['http_payload_bytes']))
        with (OUT/'progress.jsonl').open('ab') as stream:
            stream.write(canonical(records[-1])+b'\n')
        print(cell['stage_name'], count, flush=True)
    deadline_check(deadline)
    total = sum(r['input_reservation'] for r in records)
    assert total <= 32000 and sum(r['output_reservation'] for r in records) <= 8000
    state.update(status='prepared', elapsed_preparation_seconds=time.monotonic()-started,
                 records=records, input_reservation=total, output_reservation=6144,
                 tokenizer_spec_sha256=fingerprint(spec),
                 history_scope='exact_hypothetical_only_not_a_token_maximum',
                 original_source_complete=True, raw_row_reconstruction='whole_method2.2_equal')
    save('preparation.json', state)
    # Verification has a separate clock; it is not hidden inside the preparation budget.
    stage = 'read_only_verification'
    verify_started = time.monotonic()
    source_replay = verify_source_preparation(OUT/'source', source['receipt_sha256'], AUTH,
        {'project': ROOT, 'raw': RAW}, deadline=time.monotonic()+300)
    for record in records:
        verify_tokenization(OUT/f"token-{record['index']:02d}", record['receipt_sha256'],
            record['prompt_sha256'], fingerprint(spec), expected_payload_sha256=record['payload_sha256'])
    assert len(state['children']) == 6 and not state['protected_read_attempts'] and not state['network_attempts']
    result = dict(state, status='source_and_token_preparation_verified',
                  source_replay=source_replay, verification_seconds=time.monotonic()-verify_started,
                  output=str(OUT), protocol_sha256=hashlib.sha256(protocol_raw).hexdigest(),
                  source_authority_sha256=AUTH, whole_R09_complete=False,
                  independent_human_review='pending', numerical_features={}, clinical_probability=None)
    save('qualification.json', result)
    receipt = dict(schema_version=1, kind='finite_real_preparation', files={})
    for member in sorted(OUT.rglob('*')):
        if member.is_file():
            receipt['files'][member.relative_to(OUT).as_posix()] = dict(
                sha256=hashlib.sha256(member.read_bytes()).hexdigest(), bytes=member.stat().st_size)
    save('receipt.json', receipt)
    result['receipt_sha256'] = hashlib.sha256((OUT/'receipt.json').read_bytes()).hexdigest()
    with (HERE/'REAL-PREPARATION.json').open('x', encoding='utf-8') as stream:
        json.dump(encode(freeze(result)), stream, indent=2)
    print(json.dumps({k: result[k] for k in ('status','input_reservation','output_reservation','elapsed_preparation_seconds','verification_seconds','receipt_sha256','output')}))
except BaseException as error:
    failure = dict(state, status='failed', stage=stage, error_class=type(error).__name__,
                   error=str(error), elapsed_seconds=time.monotonic()-started)
    save('failure.json', failure)
    with (HERE/'REAL-PREPARATION-FAILURE-v2.json').open('x', encoding='utf-8') as stream:
        json.dump(encode(freeze(failure)), stream, indent=2)
    raise
