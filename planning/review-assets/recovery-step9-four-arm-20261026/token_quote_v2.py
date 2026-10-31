"""Prospectively bounded six-prompt offline CLI quotation; no capacity code changes."""
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import subprocess
from pathlib import Path
import sys
import time

from asof.atomic import publish_bytes
from asof.journal import RunJournal
from asof.serde import canonical, encode, fingerprint
from asof.study.tokenization import prepare_tokenizer_spec, tokenize_prompt, verify_tokenization

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parents[2]
PROTOCOL_PATH = HERE/'TOKEN-QUOTE-PROTOCOL-v2.json'
protocol_raw = PROTOCOL_PATH.read_bytes()
protocol = json.loads(protocol_raw)
started = time.monotonic()
deadline = started+300
state = {'phase':'source_pin_checks','tokenizer_attempts':0,'network_attempts':0,
         'denied_E_opens':[],'observed_E_files':set()}
report = {'schema_version':1,'role':'planning_only','experiment':'finite_six_pinned_prompt_token_quotes_v2',
          'protocol_sha256':hashlib.sha256(protocol_raw).hexdigest(),'cells':[],
          'generation_calls':0,'server_startups':0,'provider_spend_usd':0,'retries':0,
          'runtime_policy_changed':False,'package_version':metadata.version('asof-target-agents')}
journal = None
out = None


def need(condition,message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def source_pins():
    manifest = ROOT/protocol['source_pin_manifest']['path']
    need(digest(manifest) == protocol['source_pin_manifest']['sha256'],'Source-pin manifest changed')
    pins = json.loads(manifest.read_bytes())
    accepted = ROOT/protocol['accepted_code_validation']['path']
    need(digest(accepted) == protocol['accepted_code_validation']['sha256'],'Accepted code validation changed')
    need(pins == json.loads(accepted.read_bytes())['source_pins'] and len(pins) == 305,
         'Source-pin map differs from accepted305inventory')
    mismatches = [name for name,expected in pins.items() if digest(ROOT/name) != expected]
    need(not mismatches,'Source/resource pins changed: '+repr(mismatches))
    return {'count':len(pins),'all_unchanged':True}


model = Path(protocol['model_root'])
inventory_path = ROOT/protocol['inventory_path']
inventory = json.loads(inventory_path.read_bytes())
assets = [a for a in inventory['assets'] if a['path'].lower().endswith(('.dll','.gguf','llama-tokenize.exe'))]
allowed_E = {str(Path(a['path'])).replace('\\','/').casefold() for a in assets}
allowed_E.add(str(model/'acquisition.json').replace('\\','/').casefold())
allowed_E_directories = {str(model).replace('\\','/').casefold(), str(model/'runtime').replace('\\','/').casefold()}
argv = [str(model/'runtime/llama-tokenize.exe'),'--offline','--model',
        str(model/'qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf'),
        '--no-escape','--no-bos','--stdin','--ids','--show-count']


def subprocess_matches(executable, command, cwd, approved):
    # Windows audits the rendered command line and may retain executable=None.
    # The exact approved first command token still names the pinned executable.
    expected = subprocess.list2cmdline(approved) if isinstance(command, str) else list(approved)
    return (command == expected and executable in (None, approved[0])
            and Path(cwd) == Path(approved[0]).parent)


def pure_guard_checks():
    runtime = model/'runtime'
    assert subprocess_matches(None, subprocess.list2cmdline(argv), runtime, argv)
    assert subprocess_matches(argv[0], list(argv), runtime, argv)
    assert not subprocess_matches(None, subprocess.list2cmdline(argv+['--changed']), runtime, argv)
    assert not subprocess_matches('arbitrary.exe', list(argv), runtime, argv)
    assert not subprocess_matches(None, list(argv), model, argv)
    assert state['tokenizer_attempts'] == 0
    return {'list_representation':True,'Windows_commandline_representation':True,
            'wrong_argv_executable_cwd_rejected':True,'actual_children_counted':0}


report['pure_guard_checks_before_E_reads'] = pure_guard_checks()


def guard(event,args):
    if event in ('os.system','socket.connect','socket.getaddrinfo','socket.__new__'):
        state['network_attempts']+=1
        raise RuntimeError('No network/system execution in token quotation')
    if event == 'subprocess.Popen':
        need(state['phase'] == 'token_quotation','No subprocess during pin checks or read-only replay')
        need(state['tokenizer_attempts'] < 6 and subprocess_matches(args[0], args[1], args[2], list(spec['argv'])),
             'Only six exact approved tokenizer invocations are authorized')
        state['tokenizer_attempts']+=1
    if event in ('open','os.listdir','os.scandir') and args and isinstance(args[0],(str,bytes)):
        name = args[0].decode() if isinstance(args[0],bytes) else args[0]
        normalized = name.replace('\\','/').casefold()
        if '/data/benchmark/' in normalized:
            raise RuntimeError('No benchmark/outcome/gold payload reads in token quotation')
        if normalized.startswith('e:'):
            if event == 'open':
                if normalized not in allowed_E:
                    state['denied_E_opens'].append(normalized)
                    raise RuntimeError('Unapproved E data read')
                state['observed_E_files'].add(normalized)
            else:
                need(normalized in allowed_E_directories,'Unapproved E directory inventory')


sys.addaudithook(guard)
try:
    need(report['package_version'] == '0.3.5','This finite experiment requires current accepted0.3.5')
    need(digest(Path(__file__)) == protocol['helper_sha256'],'Prospective helper changed')
    preflight_path = HERE/'PREFLIGHT-RESULT.json'
    need(digest(preflight_path) == protocol['preflight_sha256'],'Fixed preflight result changed')
    preflight = json.loads(preflight_path.read_bytes())
    need(preflight['aggregate_input_reservation'] == 47753 and not preflight['byte_proxy_fits']
         and preflight['selected_ids'] == ['id03','id04']
         and preflight['policy'] == 'literal_case_overlap_then_id_v1','Original fixed preflight differs')
    report['source_pins_before'] = source_pins()
    cells = []
    for pin,original in zip(protocol['cells'],preflight['cells']):
        path = HERE/pin['file']
        need(digest(path) == pin['file_sha256'] == original['file_sha256'],'Exact payload file differs')
        wrapper = json.loads(path.read_bytes())
        cell = wrapper['cell']
        need(wrapper['role'] == 'planning_only' and wrapper['execution_authorized'] is False
             and cell['execution_authorized'] is False and fingerprint(cell['payload']) == original['payload_sha256']
             and cell['payload_sha256'] == original['payload_sha256']
             and cell['history_scope'] == 'exact_hypothetical_only_not_a_token_maximum',
             'Payload/source/history binding changed')
        cells.append(cell)
    need(len(cells) == 6 and len(assets) == 34,'Fixed six-prompt/34asset scope differs')
    suffix = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT/'data/cache'/('r09-four-arm-tokenquotes-v2-'+suffix)
    journal = RunJournal(out,kind='build')
    report['output'] = str(out)
    journal.append('token_quote_protocol',protocol_sha256=report['protocol_sha256'],deadline_monotonic=deadline)
    authority = {'inventory':{'root_id':'project','relative_path':protocol['inventory_path']},
                 'acquisition':{'root_id':'model','relative_path':'acquisition.json'}}
    state['phase']='asset_spec'
    spec_started = time.monotonic()
    spec = prepare_tokenizer_spec(authority,{'project':ROOT,'model':model},deadline=deadline)
    report['asset_spec_seconds'] = time.monotonic()-spec_started
    report['spec_sha256'] = fingerprint(spec)
    need(list(spec['argv']) == argv, 'Fixed approved spec argv differs')
    state['phase']='token_quotation'
    for index,cell in enumerate(cells):
        need(time.monotonic() < deadline,'Shared300second quotation deadline expired')
        payload = cell['payload']
        child = out/f'{index:02d}-{cell["stage_name"]}'
        journal.append('quote_preparing',index=index,payload_sha256=cell['payload_sha256'])
        result = tokenize_prompt(payload['prompt'],spec,deadline,child,payload_sha256=cell['payload_sha256'])
        quote = encode(result['quote'])
        context_with_margin = quote['input_reservation']+payload['n_predict']
        item = {'index':index,'stage':cell['stage_name'],'arm':cell['arm'],
                'payload_file':protocol['cells'][index], 'payload_sha256':cell['payload_sha256'],
                'prompt_sha256':quote['prompt_sha256'],'prompt_utf8_bytes':quote['prompt_utf8_bytes'],
                'token_count':quote['token_count'],'input_reservation':quote['input_reservation'],
                'output_reservation':payload['n_predict'],'context_reservation':context_with_margin,
                'context_fits':context_with_margin <= 16384,
                'receipt_sha256':result['receipt_sha256'],'quote_directory':str(child),
                'tokenization_seconds':quote['elapsed_seconds'],
                'history_scope':cell['history_scope']}
        report['cells'].append(item)
        journal.append('quote_accepted',index=index,receipt_sha256=result['receipt_sha256'],token_count=quote['token_count'])
        publish_bytes(out/f'{index:02d}-external-anchor.json',canonical(item))
    need(time.monotonic() < deadline and state['tokenizer_attempts'] == 6,'Quotation budget/count differs')
    report['quotation_seconds'] = time.monotonic()-started
    report['aggregate_input_reservation'] = sum(x['input_reservation'] for x in report['cells'])
    report['aggregate_output_reservation'] = sum(x['output_reservation'] for x in report['cells'])
    report['token_input_fits'] = report['aggregate_input_reservation'] <= 32000
    report['output_fits'] = report['aggregate_output_reservation'] <= 8000
    report['all_contexts_fit'] = all(x['context_fits'] for x in report['cells'])
    report['source_pins_after_quotation'] = source_pins()
    state['phase']='read_only_replay'
    replay_started = time.monotonic()
    attempts_before = state['tokenizer_attempts']
    for cell,item in zip(cells,report['cells']):
        verified = verify_tokenization(Path(item['quote_directory']),item['receipt_sha256'],
            item['prompt_sha256'],report['spec_sha256'],expected_payload_sha256=item['payload_sha256'])
        need(verified['token_count'] == item['token_count'] and time.monotonic()-replay_started < 300,
             'Read-only quotation replay differs or exceeded separate replay deadline')
    report['read_only_replay'] = {'status':'passed','seconds':time.monotonic()-replay_started,
                                'tokenizer_invocations':state['tokenizer_attempts']-attempts_before}
    report['source_pins_after_replay'] = source_pins()
    for pin in protocol['cells']:
        need(digest(HERE/pin['file']) == pin['file_sha256'],'Payload file changed during experiment')
    need(digest(preflight_path) == protocol['preflight_sha256'],'Preflight changed during experiment')
    report.update(status='completed_feasibility_only',tokenizer_invocations=state['tokenizer_attempts'],
                  network_attempts=state['network_attempts'],denied_E_opens=state['denied_E_opens'],
                  E_files_read=len(state['observed_E_files']),fresh_future_package_quotes_required=True,
                  execution_authorized=False,scientific_validation='not_attempted')
    journal.append('token_quote_complete',input_reservation=report['aggregate_input_reservation'],
                   replay_tokenizer_invocations=report['read_only_replay']['tokenizer_invocations'])
    journal.close()
    publish_bytes(out/'result.json',canonical(report))
    publish_bytes(HERE/'TOKEN-QUOTE-RESULT-v2.json',canonical(report))
    print(json.dumps({k:v for k,v in report.items() if k != 'cells'},indent=2),flush=True)
except BaseException as error:
    report.update(status='failed_stop_no_retry',phase=state['phase'],error_class=type(error).__name__,
                  error=str(error),tokenizer_attempts=state['tokenizer_attempts'],execution_authorized=False)
    if journal is not None:
        try:
            journal.fail(error,state['phase'])
        except BaseException as secondary:
            error.add_note('Parent journal retention: '+type(secondary).__name__)
    if out is not None:
        try:
            publish_bytes(out/'failure.json',canonical(report))
        except BaseException as secondary:
            error.add_note('Failure retention: '+type(secondary).__name__)
    publish_bytes(HERE/'TOKEN-QUOTE-FAILURE-v2.json',canonical(report))
    raise
finally:
    if journal is not None:
        journal.close()
