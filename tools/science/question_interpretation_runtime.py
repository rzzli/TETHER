"""Durable question-contract execution and inspection; no native adapter or retry.

Verification establishes byte/mechanical/source consistency, never scientific
entailment. Adapter code is trusted; archived data never imports executable code.
"""
import ast
import hashlib
import inspect
import math
import platform
import time
import uuid
from pathlib import Path

from tether_engine.agents import Usage
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, canonical, decode, encode, fingerprint, freeze, parse_json, read_json, write_json
from tether_engine.workflow import Budget, BudgetMeter, add_usage, over_quote
from tools.science.bounded_interpretation import Generated, MAX_BYTES, MAX_RESPONSE_BYTES, checked_usage, need, nonempty
from tools.science.interpretation_questions import prepare_question, scientific_view, validate_response
from tools.science.run_comparison import pin, check_pin

ROOT = Path(__file__).resolve().parents[2]
MAX_RAW_BYTES = MAX_BYTES


def _module_path(name):
    for base in (ROOT/'src', ROOT):
        candidate = base.joinpath(*name.split('.'))
        for path in (candidate.with_suffix('.py'), candidate/'__init__.py'):
            if path.is_file(): return path.resolve()
    return None


def code_paths(*entries):
    """Conservative static local import closure, without importing archived paths."""
    pending = [Path(__file__).resolve(), *(Path(p).resolve() for p in entries)]
    found = set()
    while pending:
        path = pending.pop()
        if path in found: continue
        need(path.is_relative_to(ROOT) and path.suffix == '.py' and path.is_file(), 'Code outside project source')
        found.add(path); need(len(found) <= 1024, 'Code closure exceeds bound')
        relative = path.relative_to(ROOT/'src') if path.is_relative_to(ROOT/'src') else path.relative_to(ROOT)
        base = ROOT/'src' if path.is_relative_to(ROOT/'src') else ROOT
        parent = path.parent
        while parent != base:
            initializer = parent/'__init__.py'
            if initializer.is_file() and initializer.resolve() not in found: pending.append(initializer.resolve())
            parent = parent.parent
        parts = list(relative.with_suffix('').parts)
        package = parts[:-1]
        if parts[-1] == '__init__': parts.pop(); package = parts
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            names = []
            if isinstance(node, ast.Import): names = [x.name for x in node.names]
            elif isinstance(node, ast.ImportFrom):
                prefix = package[:len(package)-node.level+1] if node.level else []
                base = '.'.join(prefix + (node.module.split('.') if node.module else []))
                names = [base] + [base+'.'+x.name for x in node.names if x.name != '*']
            for name in names:
                target = _module_path(name)
                if target is not None and target not in found: pending.append(target)
    return tuple(sorted(found, key=lambda p:p.relative_to(ROOT).as_posix()))


def _callback_proof(callback):
    if callback is None: return None
    need(callable(callback), 'Adapter verifier must be explicitly supplied trusted code')
    return dict(code=pin(Path(inspect.getfile(callback)).resolve()), symbol=callback.__qualname__)


def _budget(value):
    budget = decode(Budget, encode(value if value is not None else Budget())); budget.validate()
    need(budget.max_cost_usd == 0, 'Recorded development has zero provider-spending budget')
    return budget


def _usage(value):
    # Usage declares a floating cost field; normalize that field through its
    # strict decoder while keeping original replay bytes untouched.
    return checked_usage(decode(Usage,encode(checked_usage(value))))


def _allowed(budget, quote, remaining):
    return (budget.max_calls > 0 and quote.input_tokens <= budget.max_input_tokens and
            quote.output_tokens <= budget.max_output_tokens and quote.cost_usd <= budget.max_cost_usd and remaining > 0)


def _read_replay(payload):
    need(len(payload) <= 2*MAX_RESPONSE_BYTES, 'Question replay exceeds input cap')
    document = parse_json(payload)
    need(isinstance(document,dict) and set(document) == {'schema_version','request_sha256','response','usage'} and
         type(document['schema_version']) is int and document['schema_version'] == 2, 'Invalid question replay')
    return document


class RecordedQuestionInterpreter:
    """One-use, exact-byte archived replay. This is not a model execution."""
    backend_id = 'recorded-question-interpretation-v2'

    def __init__(self, path):
        path = Path(path).resolve()
        with path.open('rb') as stream: payload = stream.read(2*MAX_RESPONSE_BYTES+1)
        document = _read_replay(payload)
        self.document = freeze(document); self.used = False
        self.provenance = freeze(dict(kind='recorded_question_response', document=document,
            original_utf8=payload.decode('utf-8'), sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload)))

    def quote(self, request):
        need(not self.used and self.document['request_sha256'] == fingerprint(request), 'Replay differs/exhausted')
        return checked_usage(decode(Usage,encode(self.document['usage'])))

    def generate(self, request, timeout_seconds):
        usage = self.quote(request); need(timeout_seconds > 0, 'No dispatch time remains')
        self.used = True
        return Generated(canonical(self.document['response']).decode('utf-8'), usage)


def _recorded_provenance(provenance, backend_id, adapter, request_hash):
    """Same reserved built-in contract before dispatch and during verification."""
    need(isinstance(provenance,dict) and
         set(provenance)=={'kind','document','original_utf8','sha256','bytes'} and
         provenance['kind']=='recorded_question_response' and isinstance(provenance['original_utf8'],str) and
         type(provenance['bytes']) is int, 'Invalid recorded provenance fields')
    original = provenance['original_utf8'].encode('utf-8'); replay = _read_replay(original)
    need(hashlib.sha256(original).hexdigest()==provenance['sha256'] and len(original)==provenance['bytes'] and
         fingerprint(replay)==fingerprint(provenance['document']) and backend_id==RecordedQuestionInterpreter.backend_id and
         adapter==Path(__file__).resolve() and replay['request_sha256']==request_hash,
         'Recorded input provenance/code identity differs')
    return replay, encode(checked_usage(decode(Usage,replay['usage'])))


def _account(journal, meter, attempt, usage, basis):
    meter.account(usage, measured=basis == 'adapter_reported')
    journal.append('question_accounted', attempt_id=attempt, basis=basis, usage=encode(usage))


def run_question_interpretation(case_path, snapshot_path, family, output, backend, catalog_path=None, *,
        budget=None, max_claims=12, max_observations=256, observation_ids=None, adapter_verifier=None):
    """Reserve, admit, dispatch at most once, persist failures and seal acyclically."""
    output = Path(output).resolve()
    for source in (case_path,snapshot_path,catalog_path):
        if source: need(not output.is_relative_to(Path(source).resolve().parent), 'Output overlaps input directory')
    journal = RunJournal(output,kind='build'); stage = 'preflight'
    run_id = journal.events[0]['details']['run_id']; dispatched = False; archived = False
    primary_error = None; diagnostics = []
    def record_secondary(event, issue, original):
        diagnostics.append(dict(stage=event,error_class=type(issue).__name__))
        try: journal.append(event,error_class=type(issue).__name__,original_error_class=type(original).__name__)
        except BaseException as notice_error:
            diagnostics.append(dict(stage=event+'_notice',error_class=type(notice_error).__name__))
            original.add_note('Secondary journal notice failed: '+type(notice_error).__name__)
    def failure_snapshot(error, failure_stage):
        try:
            write_json(output/'failure.json',dict(schema_version=2,run_id=run_id,stage=failure_stage,
                error_class=type(error).__name__,secondary_failures=diagnostics,
                qualification='Failure fallback, not a successful receipt or execution attestation'))
        except BaseException as snapshot_error:
            error.add_note('Failure snapshot write failed: '+type(snapshot_error).__name__)
    def archive_execution():
        nonlocal archived
        if dispatched and not archived and callable(getattr(backend,'execution_document',None)):
            archived = True
            document = backend.execution_document(); need(len(canonical(document)) <= MAX_BYTES, 'Execution archive exceeds cap')
            write_json(output/'backend-execution.json',document)
            journal.append('question_execution_archived', proof=pin(output/'backend-execution.json'))
    try:
        journal.append('question_runtime_started', schema_version=2, run_id=run_id)
        budget = _budget(budget); meter = BudgetMeter(budget)
        prepared = prepare_question(case_path,snapshot_path,family,catalog_path,max_claims=max_claims,
                                    max_observations=max_observations,observation_ids=observation_ids)
        request = prepared.request; request_hash = fingerprint(request)
        verifier_proof = _callback_proof(adapter_verifier)
        adapter_code = Path(inspect.getfile(type(backend))).resolve()
        dependencies = code_paths(adapter_code,*( [verifier_proof['code']['path']] if verifier_proof else []))
        provenance = encode(getattr(backend,'provenance',{'kind':'trusted_adapter_metadata_unavailable'}))
        need(nonempty(backend.backend_id) and isinstance(provenance,dict) and nonempty(provenance.get('kind')) and
             (provenance['kind'] in {'recorded_question_response','trusted_adapter_metadata_unavailable'} or
              adapter_verifier is not None), 'Explicit trusted verifier required for adapter provenance')
        if provenance['kind']=='recorded_question_response':
            _recorded_provenance(provenance,backend.backend_id,adapter_code,request_hash)
        config = dict(schema_version=2,run_id=run_id,request_sha256=request_hash,backend_id=backend.backend_id,
            budget=encode(budget),automatic_retries=False,python_version=platform.python_version(),
            code=[pin(p) for p in dependencies],adapter_code=pin(adapter_code),adapter_verifier=verifier_proof,
            adapter_provenance=provenance)
        for name,value in [('request.json',request),('inputs.json',prepared.archive),
                           ('scientific-view.json',scientific_view(request)),('configuration.json',config)]:
            write_json(output/name,value)
        journal.append('question_prepared', request_sha256=request_hash,
                       configuration_sha256=fingerprint(config))
        stage = 'quote'; quote = _usage(backend.quote(request))
        remaining = budget.max_seconds-(time.monotonic()-meter.started); allowed = _allowed(budget,quote,remaining)
        journal.append('question_quote',quote=encode(quote),remaining_seconds=remaining,allowed=allowed)
        status = 'abstained_budget'
        if allowed:
            attempt = str(uuid.uuid4()); stage = 'dispatch'; generated = None; accounted = False
            journal.append('question_dispatch',attempt_id=attempt,request_sha256=request_hash,reserved=encode(quote))
            dispatched = True
            try:
                generated = backend.generate(request,timeout_seconds=max(0,budget.max_seconds-(time.monotonic()-meter.started)))
                stage = 'response_capture'
                if isinstance(generated,Generated) and isinstance(generated.content_json,str):
                    payload = generated.content_json.encode('utf-8'); retained = payload[:MAX_RAW_BYTES]
                    with (output/'raw-response.txt').open('xb') as stream: stream.write(retained)
                    journal.append('question_response_captured',attempt_id=attempt,content_bytes=len(payload),
                        content_sha256=hashlib.sha256(payload).hexdigest(),retained=pin(output/'raw-response.txt'),
                        complete=len(payload) <= MAX_RAW_BYTES)
                else:
                    journal.append('question_response_unavailable',attempt_id=attempt,reason='Non-text generated envelope')
                need(isinstance(generated,Generated), 'Malformed generated envelope')
                usage = _usage(generated.usage)
                accounted = True; _account(journal,meter,attempt,usage,'adapter_reported')
                need(isinstance(generated.content_json,str), 'Generated content must be JSON text')
                need(len(payload) <= MAX_RESPONSE_BYTES, 'Raw response exceeds contract cap; retained bytes are explicit')
                need(not over_quote(usage,quote), 'Adapter exceeded quote')
                need(time.monotonic()-meter.started < budget.max_seconds, 'Question execution exceeded wall budget')
                stage = 'response_validation'; response = validate_response(request,parse_json(payload))
                journal.append('question_response_accepted',response_sha256=fingerprint(response),answer_status=response['answer_status'])
                status = 'question_contract_completed_not_scientific_validation'
            except BaseException as original:
                if not accounted:
                    measured = None
                    if isinstance(generated,Generated):
                        try: measured = _usage(generated.usage)
                        except (ContractError,ValueError,TypeError): pass
                    accounted = True
                    try: _account(journal,meter,attempt,measured or quote,'adapter_reported' if measured else 'conservative_quote')
                    except BaseException as account_error:
                        record_secondary('question_accounting_failed',account_error,original)
                raise
        else:
            response = dict(schema_version=2,kind='question_interpretation',request_sha256=request_hash,
                hypothesis_key=request['hypothesis_key'],question_key=request['question_key'],answer_status='abstained',
                claims=[],abstention_reason='Dispatch exceeds available budget.',features={},clinical_probability=None)
            response = validate_response(request,response)
        stage = 'finalization'; archive_execution()
        # Re-admit original bytes at finalization, including parents, not only top-level pins.
        _reprepare(prepared.archive,request)
        write_json(output/'response.json',response)
        report = dict(schema_version=2,run_id=run_id,status=status,request_sha256=request_hash,
            response_sha256=fingerprint(response),calls=meter.calls,measured_usage=encode(meter.measured),
            estimated_usage=encode(meter.estimated),features={},clinical_probability=None,scientific_validation='not_performed')
        if adapter_verifier is not None:
            adapter_verifier(request,config,response,read_json(output/'backend-execution.json') if
                             (output/'backend-execution.json').is_file() else None,report)
        write_json(output/'report.json',report)
        journal.append('build_completed',run_id=run_id,report=pin(output/'report.json'))
        names = ['request.json','inputs.json','scientific-view.json','configuration.json','response.json','report.json','journal.jsonl']
        names += [n for n in ['raw-response.txt','backend-execution.json'] if (output/n).is_file()]
        write_json(output/'receipt.json',dict(schema_version=2,kind='question_interpretation_receipt',
            run_id=run_id,request_sha256=request_hash,outputs={n:pin(output/n) for n in names}))
        return freeze(report)
    except BaseException as error:
        primary_error = error
        try: archive_execution()
        except BaseException as archive_error:
            record_secondary('question_execution_archive_failed',archive_error,error)
        try: journal.fail(error,stage)
        except BaseException as terminal_error:
            diagnostics.append(dict(stage='terminal_journal',error_class=type(terminal_error).__name__))
            error.add_note('Terminal journal write failed: '+type(terminal_error).__name__)
        failure_snapshot(error,stage)
        raise
    finally:
        try: journal.close()
        except BaseException as close_error:
            diagnostics.append(dict(stage='journal_close',error_class=type(close_error).__name__))
            if primary_error is None:
                failure_snapshot(close_error,'journal_close')
                raise
            primary_error.add_note('Journal close failed: '+type(close_error).__name__)
            failure_snapshot(primary_error,stage)


def _reprepare(archive, request):
    source = archive['source_archive']
    for proof in source['inputs']: check_pin(proof)
    prepared = prepare_question(source['case_path'],source['snapshot_path'],archive['question']['question_id'],
        source['catalog_path'],max_claims=source['max_claims'],max_observations=source['max_observations'],
        observation_ids=source.get('observation_ids'))
    need(fingerprint(prepared.request) == fingerprint(request) and fingerprint(prepared.archive) == fingerprint(archive),
         'Re-admitted question inputs differ')
    return prepared


def inspect_question_interpretation(output):
    """Inspect partial or failed attempts, including unresolved reservations. No dispatch."""
    output = Path(output).resolve(); events = read_chain(output/'journal.jsonl',allow_incomplete_tail=True)
    need(events[0]['event']=='build_reserved','Missing question reservation')
    attempts, accounts = {}, {}; measured = estimated = Usage(0,0,0)
    for event in events:
        details = event['details']
        if event['event']=='question_dispatch':
            key = details['attempt_id']; need(key not in attempts,'Duplicate dispatch ID')
            checked_usage(decode(Usage,encode(details['reserved']))); attempts[key] = details
        elif event['event']=='question_accounted':
            key = details['attempt_id']; need(key in attempts and key not in accounts,'Foreign/duplicate accounting')
            need(details['basis'] in {'adapter_reported','conservative_quote'},'Unknown accounting basis')
            usage = checked_usage(decode(Usage,encode(details['usage'])))
            if details['basis']=='adapter_reported': measured = add_usage(measured,usage)
            else:
                need(fingerprint(details['usage'])==fingerprint(attempts[key]['reserved']),'Conservative usage differs')
                estimated = add_usage(estimated,usage)
            accounts[key] = details
    unresolved = sorted(attempts.keys()-accounts.keys())
    for key in unresolved: estimated = add_usage(estimated,decode(Usage,encode(attempts[key]['reserved'])))
    failure = encode(events[-1]['details']) if events[-1]['event'] in {'build_failed','build_interrupted'} else None
    if (output/'failure.json').is_file():
        fallback = read_json(output/'failure.json')
        need(type(fallback.get('schema_version')) is int and fallback['schema_version']==2 and
             fallback.get('run_id')==events[0]['details']['run_id'], 'Foreign failure fallback')
        failure = fallback
    return dict(schema_version=2,kind='question_interpretation',last_event=events[-1]['event'],
        run_id=events[0]['details']['run_id'],durable_events=len(events),calls=len(attempts),
        unresolved_attempts=unresolved,measured_usage=encode(measured),estimated_upper_usage=encode(estimated),
        receipt_present=(output/'receipt.json').is_file(),failure=failure,
        recovery_action='inspect only; never automatically repeat calls')


def verify_question_interpretation(output, *, adapter_verifier=None):
    """Verify a finalized source-inclusive run without importing archived code or dispatching."""
    output = Path(output).resolve()
    need(not (output/'failure.json').exists(), 'Question execution has retained failure state')
    receipt = read_json(output/'receipt.json')
    need(set(receipt)=={'schema_version','kind','run_id','request_sha256','outputs'} and
         type(receipt['schema_version']) is int and receipt['schema_version']==2 and
         receipt['kind']=='question_interpretation_receipt','Invalid question receipt')
    required = {'request.json','inputs.json','scientific-view.json','configuration.json','response.json','report.json','journal.jsonl'}
    need(required <= receipt['outputs'].keys() and not receipt['outputs'].keys()-required-
         {'raw-response.txt','backend-execution.json'},'Missing/foreign question outputs')
    for name,proof in receipt['outputs'].items(): need(check_pin(proof)==output/name,'Foreign receipt output')
    events = read_chain(output/'journal.jsonl'); need(events[-1]['event']=='build_completed','Question run did not finalize')
    request,archive = read_json(output/'request.json'),read_json(output/'inputs.json'); _reprepare(archive,request)
    need(fingerprint(scientific_view(request))==fingerprint(read_json(output/'scientific-view.json')),'Scientific view differs')
    response = validate_response(request,read_json(output/'response.json'))
    config,report = read_json(output/'configuration.json'),read_json(output/'report.json')
    need(set(config)=={'schema_version','run_id','request_sha256','backend_id','budget','automatic_retries',
        'python_version','code','adapter_code','adapter_verifier','adapter_provenance'} and
        type(config['schema_version']) is int and config['schema_version']==2 and
        config['automatic_retries'] is False and nonempty(config['backend_id']),'Invalid question configuration')
    need(config['adapter_verifier']==_callback_proof(adapter_verifier),'Matching trusted adapter verifier required')
    adapter = check_pin(config['adapter_code'])
    expected_code = code_paths(adapter,*( [config['adapter_verifier']['code']['path']] if adapter_verifier else []))
    need(tuple(check_pin(p) for p in config['code'])==expected_code,'Missing/foreign code dependency identity')
    budget = _budget(config['budget']); run_id = events[0]['details']['run_id']; request_hash = fingerprint(request)
    need(receipt['run_id']==config['run_id']==report['run_id']==events[-1]['details']['run_id']==run_id and
         receipt['request_sha256']==config['request_sha256']==report['request_sha256']==request_hash,'Run identity differs')
    need(check_pin(events[-1]['details']['report'])==output/'report.json','Final report differs')
    need(set(report)=={'schema_version','run_id','status','request_sha256','response_sha256','calls','measured_usage',
         'estimated_usage','features','clinical_probability','scientific_validation'} and
         type(report['schema_version']) is int and report['schema_version']==2 and type(report['calls']) is int and
         report['response_sha256']==fingerprint(response) and report['features']=={} and
         report['clinical_probability'] is None and report['scientific_validation']=='not_performed','Question report differs')
    quotes = [e['details'] for e in events if e['event']=='question_quote']; need(len(quotes)==1,'Missing/duplicate quote')
    q = quotes[0]; quoted = checked_usage(decode(Usage,encode(q['quote'])))
    need(type(q['remaining_seconds']) in (int,float) and math.isfinite(q['remaining_seconds']) and
         q['remaining_seconds'] <= budget.max_seconds,'Invalid remaining time')
    allowed = _allowed(budget,quoted,q['remaining_seconds']); need(q['allowed'] is allowed,'Quote decision differs')
    summary = inspect_question_interpretation(output)
    need(not summary['unresolved_attempts'] and report['calls']==summary['calls']==int(allowed) and
         fingerprint(report['measured_usage'])==fingerprint(summary['measured_usage']) and
         fingerprint(report['estimated_usage'])==fingerprint(encode(Usage(0,0,0)))==fingerprint(summary['estimated_upper_usage']),
         'Question usage/call accounting differs')
    names = ['build_reserved','question_runtime_started','question_prepared','question_quote']
    if allowed: names += ['question_dispatch','question_response_captured','question_accounted','question_response_accepted']
    if 'backend-execution.json' in receipt['outputs']: names += ['question_execution_archived']
    names += ['build_completed']; need([e['event'] for e in events]==names,'Unexpected question event sequence')
    need(fingerprint(events[1]['details'])==fingerprint(dict(schema_version=2,run_id=run_id)) and
         fingerprint(events[2]['details'])==fingerprint(dict(request_sha256=request_hash,configuration_sha256=fingerprint(config))),
         'Prepared configuration identity differs')
    if allowed:
        dispatch,captured,account,accepted = (events[i]['details'] for i in (4,5,6,7))
        need(dispatch['request_sha256']==request_hash and fingerprint(dispatch['reserved'])==fingerprint(q['quote']) and
             dispatch['attempt_id']==captured['attempt_id']==account['attempt_id'] and
             account['basis']=='adapter_reported' and not over_quote(checked_usage(decode(Usage,encode(account['usage']))),quoted),
             'Attempt reservation/account differs')
        need('raw-response.txt' in receipt['outputs'] and captured['complete'] is True and
             fingerprint(captured['retained'])==fingerprint(receipt['outputs']['raw-response.txt']) and
             captured['content_bytes']==captured['retained']['bytes'] and captured['content_bytes']<=MAX_RESPONSE_BYTES and
             captured['content_sha256']==captured['retained']['sha256'],'Raw capture differs/incomplete')
        payload = (output/'raw-response.txt').read_bytes()
        need(fingerprint(parse_json(payload))==fingerprint(response) and fingerprint(accepted)==fingerprint(dict(
             response_sha256=fingerprint(response),answer_status=response['answer_status'])) and
             report['status']=='question_contract_completed_not_scientific_validation','Accepted response differs')
    else:
        need(report['status']=='abstained_budget' and response['answer_status']=='abstained' and
             'raw-response.txt' not in receipt['outputs'] and 'backend-execution.json' not in receipt['outputs'],
             'Budget abstention differs')
    if 'backend-execution.json' in receipt['outputs']:
        event = next(e for e in events if e['event']=='question_execution_archived')
        need(event['details']['proof']==receipt['outputs']['backend-execution.json'],'Execution archive binding differs')
    provenance = config['adapter_provenance']
    need(isinstance(provenance,dict) and nonempty(provenance.get('kind')), 'Invalid adapter provenance')
    kind = provenance['kind']
    adapter_status = 'trusted_adapter_declarations_not_execution_attestation'
    if kind=='recorded_question_response':
        replay, replay_usage = _recorded_provenance(provenance,config['backend_id'],adapter,request_hash)
        need(fingerprint(replay_usage)==fingerprint(q['quote']),'Recorded quote differs')
        if allowed:
            need(fingerprint(replay['response'])==fingerprint(response) and
                 fingerprint(replay_usage)==fingerprint(report['measured_usage']),'Recorded response/usage differs')
        adapter_status = 'exact_recorded_replay_not_model_execution'
    elif adapter_verifier is None:
        need(kind=='trusted_adapter_metadata_unavailable','Explicit trusted verifier required for this adapter kind')
    if adapter_verifier is not None:
        adapter_verifier(request,config,response,read_json(output/'backend-execution.json') if
                         'backend-execution.json' in receipt['outputs'] else None,report)
        adapter_status = 'explicit_trusted_adapter_verifier_passed'
    return dict(status='question_run_source_and_mechanical_consistency_verified',byte_integrity='verified',
        mechanical_consistency='verified',source_admission='replayed',adapter_verification=adapter_status,
        scientific_validation='not_performed',clinical_probability=None)
