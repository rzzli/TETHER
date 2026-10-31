"""Two-policy recorded integration; source access manifests remain preparation-only.

One default budget includes both retrieval preparations and two scripted consumer
cells. No model, tokenizer, native process, live adapter or scientific score.
"""
import argparse
from dataclasses import replace
import hashlib
from importlib import resources
import json
import math
import os
from pathlib import Path
import re
import time

from asof.journal import RunJournal, read_chain
from asof.serde import canonical, decode, encode, fingerprint, freeze, parse_json
from asof.workflow import Budget
from .baseline_smoke import _prepare_parent, _read, _write
from .diagnostic import validate_output
from .diagnostic_codec import need
from .fixed_evidence import DeadlineRecordedBackend, INTERFACE, PLAN_RESOURCE
from .preparation_payloads import prepare_payloads
from .proofs import _no_links, capture_file, capture_package_proof, verify_package_proof
from .recorded import RecordedBackend, RecordedVerifier
from .retrieval_preparation import (
    REQUIRED_RESOURCES as RETRIEVAL_RESOURCES, authority_anchor, fixture_authority,
    policy_for, prepare_retrieval, verify_retrieval_preparation,
)
from .session import StudySession, _identity, verify_study

STRATEGIES = ('id_order_v1', 'literal_case_overlap_then_id_v1')
STIMULI = 'resources/retrieval-recorded-stimuli-v1.json'
STIMULI_SHA256 = '2ab511433dd05129db4e129f4c27bbdc045d855cfba91a9b97d434cb18f51b62'
REQUIRED_RESOURCES = tuple(dict.fromkeys((*RETRIEVAL_RESOURCES, PLAN_RESOURCE, STIMULI)))
TRACK = 'bounded_collected_corpus_recorded_integration'
PARENT_FILES = {'authority.json','policy.json','universe.json','retrieval.json','request.json',
                'coverage.json','access-manifest.json','package-proof.json','journal.jsonl','receipt.json'}
CELL_FILES = {'request.json','payload.json','configuration.json','raw-response.bin',
              'response.json','report.json','journal.jsonl','receipt.json'}


def _resources():
    return {name:'study/'+name for name in REQUIRED_RESOURCES}


def _stimuli():
    raw = resources.files('asof.study').joinpath(STIMULI).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == STIMULI_SHA256, 'Recorded retrieval stimuli differ')
    value = parse_json(raw)
    need(value['schema_version'] == 1 and value['role'] == 'evaluation_only_fixture'
         and set(value['responses']) == set(STRATEGIES), 'Invalid recorded retrieval stimuli')
    return value


def _strategy(strategy):
    need(isinstance(strategy,str) and strategy in STRATEGIES, 'Unknown fixed retrieval strategy')
    return strategy


def _document(stage,payload):
    stimuli = _stimuli()
    strategy = _strategy(stage['strategy'])
    return freeze(dict(schema_version=1,role='evaluation_only_fixture',
        request_sha256=fingerprint(stage),payload_sha256=fingerprint(payload),
        content_utf8=canonical(stimuli['responses'][strategy]).decode('utf-8'),
        usage=stimuli['usage'],outcome='return'))


def _members():
    return {'journal.jsonl','package-proof.json','summary.json'} | {
        f'preparation/{strategy}/{name}' for strategy in STRATEGIES for name in PARENT_FILES
    } | {f'cells/{strategy}/{name}' for strategy in STRATEGIES for name in CELL_FILES}


def _inventory(root):
    _no_links(root)
    members, directories = set(), set()
    for directory, children, names in os.walk(root,followlinks=False):
        for name in children:
            path = Path(directory)/name
            _no_links(path)
            directories.add(path.relative_to(root).as_posix())
        for name in names:
            path = Path(directory)/name
            _no_links(path)
            need(path.is_file(),'Unexpected integration artifact type')
            members.add(path.relative_to(root).as_posix())
    expected = {p.as_posix() for name in _members() for p in Path(name).parents if p != Path('.')}
    need(directories == expected,'Unexpected integration directories')
    return members


def _package_check(package):
    need({k:v.get('relative_path') for k,v in package.get('resources',{}).items()} == _resources(),
         'Integration resource paths differ')
    verify_package_proof(package,required_resources=REQUIRED_RESOURCES)


class RetrievalRecordedVerifier(RecordedVerifier):
    """Explicit source-parent authority, separate from fixed-evidence fixture gates."""
    required_resources = REQUIRED_RESOURCES

    def __init__(self,root,run_id,*,deadline=None):
        super().__init__(INTERFACE)
        self.root,self.run_id = Path(root).absolute(),run_id
        self.deadline = deadline

    def _events(self):
        if self.deadline is not None:
            _remaining(self.deadline)
        _no_links(self.root)
        events = read_chain(self.root/'journal.jsonl')
        need(events[0]['event'] == 'build_reserved' and events[0]['details']['run_id'] == self.run_id,
             'Integration root identity differs')
        return events

    def prepare_stage(self,strategy):
        strategy = _strategy(strategy)
        ready = [e['details'] for e in self._events() if e['event'] == 'retrieval_ready'
                 and e['details'].get('strategy') == strategy]
        need(len(ready) == 1,'Missing or duplicate authoritative retrieval parent')
        parent = self.root/'preparation'/strategy
        authority = fixture_authority()
        anchor = authority_anchor(authority)
        result = verify_retrieval_preparation(parent,ready[0]['receipt_sha256'],anchor,
                                               deadline=self.deadline if self.deadline is not None else time.monotonic()+299)
        original,proof = _read(parent,'request.json')
        receipt,_ = _read(parent,'receipt.json')
        need(canonical(proof) == canonical(receipt['files']['request.json'])
             and fingerprint(original) == ready[0]['request_sha256'] == result['request_sha256'],
             'Verified retrieval request bytes differ')
        policy,_ = _read(parent,'policy.json')
        need(canonical(policy) == canonical(policy_for(strategy)),'Retrieval parent policy differs')
        if self.deadline is not None:
            _remaining(self.deadline)
        return freeze(dict(schema_version=1,kind='recorded_retrieval_consumer_request',
            integration_run_id=self.run_id,strategy=strategy,authority_sha256=anchor,
            retrieval_receipt_sha256=ready[0]['receipt_sha256'],
            original_request_sha256=fingerprint(original),original_request=original))

    def prepare_payload(self,stage):
        need(isinstance(stage,dict) or hasattr(stage,'items'),'Missing retrieval consumer request')
        expected = self.prepare_stage(stage.get('strategy'))
        need(canonical(stage) == canonical(expected),'Retrieval consumer source/run binding differs')
        return prepare_payloads(expected['original_request'])[0]['payload']

    def validate_payload(self,request,payload):
        expected = self.prepare_payload(request)
        need(canonical(payload) == canonical(expected),'Retrieval consumer payload differs')

    def validate_response(self,request,content):
        self.prepare_payload(request)
        need(isinstance(content,bytes) and len(content) <= 65536,'Recorded response exceeds bound')
        return validate_output(request['original_request'],'simplified',parse_json(content))

    def verify_execution(self,request,payload,content,configuration,usage):
        self.validate_payload(request,payload)
        need(encode(configuration['adapter_code']) == _identity(DeadlineRecordedBackend),
             'Wrong recorded deadline adapter')
        provenance = encode(configuration['adapter_provenance'])
        starts = [e['details'] for e in self._events() if e['event'] == 'integration_started']
        need(len(starts) == 1 and set(provenance) == {'kind','document','parent_case_end_monotonic'}
             and provenance['parent_case_end_monotonic'] == starts[0]['case_end_monotonic'],
             'Recorded parent deadline differs')
        delegated = encode(configuration)
        delegated['adapter_code'] = _identity(RecordedBackend)
        delegated['adapter_provenance'] = {k:v for k,v in provenance.items() if k != 'parent_case_end_monotonic'}
        super().verify_execution(request,payload,content,freeze(delegated),usage)
        need(canonical(provenance['document']) == canonical(_document(request,payload)),
             'Recorded retrieval fixture differs')


def _remaining(end):
    remaining = end-time.monotonic()
    need(math.isfinite(remaining) and 0 < remaining <= 300,'Shared integration deadline exceeded')
    return remaining


def _caller(run_id,strategy):
    return dict(integration_run_id=run_id,strategy=strategy,
                usage_scope='declared_fixture_usage_not_observed_model_tokens')


def _summary(run_id,input_reserved,output_reserved,elapsed):
    return dict(schema_version=1,role='evaluation_only',run_id=run_id,track=TRACK,
        status='recorded_contract_completed_not_scientific_validation',
        retrieval_preparations=2,recorded_adapter_cells=2,
        four_arm_manifests='preparation_only_no_four_arm_outputs',
        input_reserved=input_reserved,output_reserved=output_reserved,
        fixture_declared_usage=dict(input_tokens=128,output_tokens=128,cost_usd=0.0),
        actual_model_calls=0,observed_model_usage=dict(input_tokens=0,output_tokens=0,cost_usd=0.0),
        tokenizer_processes=0,native_processes=0,scientific_validation='not_attempted',
        automatic_retries=False,elapsed_seconds=elapsed)


def smoke(output):
    start = time.monotonic()
    end = start+Budget().max_seconds
    root = Path(output).absolute()
    _prepare_parent(root.parent)
    journal = RunJournal(root,kind='build')
    run_id = journal.events[0]['details']['run_id']
    accepted,attempted = [],[]
    published = False
    failure = None
    try:
        _no_links(root)
        package = capture_package_proof(_resources(),REQUIRED_RESOURCES)
        _write(root,'package-proof.json',package)
        journal.append('integration_started',start_monotonic=start,case_end_monotonic=end,
                       budget=encode(Budget()),package_proof_sha256=fingerprint(package))
        authority = fixture_authority()
        anchor = authority_anchor(authority)
        for strategy in STRATEGIES:
            _remaining(end)
            policy = policy_for(strategy)
            journal.append('retrieval_preparing',strategy=strategy,policy_sha256=fingerprint(policy))
            parent = root/'preparation'/strategy
            result = prepare_retrieval(authority,anchor,policy,parent,deadline=end)
            _remaining(end)
            journal.append('retrieval_ready',strategy=strategy,receipt_sha256=result['receipt_sha256'],
                           request_sha256=result['request_sha256'],elapsed_seconds=time.monotonic()-start)
        verifier = RetrievalRecordedVerifier(root,run_id,deadline=end)
        input_reserved=output_reserved=calls=0
        for strategy in STRATEGIES:
            _remaining(end)
            stage = verifier.prepare_stage(strategy)
            payload = verifier.prepare_payload(stage)
            in_quote,out_quote = len(payload['prompt'].encode('utf-8'))+32,payload['n_predict']
            need(input_reserved+in_quote <= 32000 and output_reserved+out_quote <= 8000 and calls < 16,
                 'Shared recorded integration capacity exceeded')
            journal.append('cell_preparing',strategy=strategy,request_sha256=fingerprint(stage),
                           payload_sha256=fingerprint(payload))
            document = _document(stage,payload)
            budget = replace(Budget(),max_calls=16-calls,max_input_tokens=32000-input_reserved,
                             max_output_tokens=8000-output_reserved,max_seconds=_remaining(end))
            cell = root/'cells'/strategy
            _prepare_parent(cell.parent)
            attempted.append(strategy)
            with StudySession(cell,budget=budget,configuration=_caller(run_id,strategy),
                              resources=_resources(),required_resources=REQUIRED_RESOURCES) as session:
                _remaining(end)
                budget = replace(budget,max_seconds=end-session.started)
                need(0 < budget.max_seconds <= 300,'Invalid child shared deadline')
                session.budget = decode(Budget,encode(budget))
                journal.append('cell_reserved',strategy=strategy,input_reservation=in_quote,
                    output_reservation=out_quote,allocated_budget=encode(budget),
                    request_sha256=fingerprint(stage),payload_sha256=fingerprint(payload))
                input_reserved+=in_quote
                output_reserved+=out_quote
                calls+=1
                _remaining(end)
                session.call_once(request=stage,payload=payload,
                    backend=DeadlineRecordedBackend(document,case_end=end),verifier=verifier)
                session.finish()
            receipt_sha = capture_file(cell/'receipt.json','receipt.json')['sha256']
            verify_study(cell,expected_receipt_sha256=receipt_sha,verifier=verifier)
            _remaining(end)
            journal.append('cell_accepted',strategy=strategy,receipt_sha256=receipt_sha,
                fixture_declared_usage=dict(input_tokens=64,output_tokens=64,cost_usd=0.0),actual_model_calls=0)
            accepted.append(strategy)
        elapsed = 300-_remaining(end)
        summary = _summary(run_id,input_reserved,output_reserved,elapsed)
        _write(root,'summary.json',summary)
        journal.append('integration_completed',summary_sha256=fingerprint(summary))
        journal.close()
        _package_check(package)
        _remaining(end)
        need(_inventory(root) == _members(),'Integration inventory differs before sealing')
        artifacts = {name:encode(capture_file(root/name,name)) for name in sorted(_members())}
        _remaining(end)
        receipt = dict(schema_version=1,kind=TRACK,role='evaluation_only',run_id=run_id,artifacts=artifacts)
        anchor = fingerprint(receipt)
        result = _verify(root,anchor,prospective_receipt=receipt,deadline=end)
        _remaining(end)
        _write(root,'receipt.json',receipt)
        published = True
        _remaining(end)
        return result
    except BaseException as primary:
        failure = primary
        if published:
            try:
                need(_read(root,'receipt.json')[1]['sha256'] == anchor,'Published integration receipt changed')
                (root/'receipt.json').unlink()
            except BaseException as secondary:
                primary.add_note('Integration receipt withdrawal: '+type(secondary).__name__)
        try:
            journal.fail(primary,'retrieval_recorded_integration')
        except BaseException as secondary:
            primary.add_note('Integration journal failure: '+type(secondary).__name__)
        try:
            _write(root,'failure.json',dict(schema_version=1,role='evaluation_only',run_id=run_id,
                error_class=type(primary).__name__,accepted_cells=accepted,attempted_cells=attempted,
                actual_model_calls=0,automatic_retries=False,recovery='inspect only; never repeat automatically'))
        except BaseException as secondary:
            primary.add_note('Integration failure retention: '+type(secondary).__name__)
        raise
    finally:
        try:
            journal.close()
        except BaseException as secondary:
            if failure is None:
                raise
            failure.add_note('Integration journal close: '+type(secondary).__name__)


def verify(path,sha256):
    """Read-only replay requires an externally retained completed receipt anchor."""
    return _verify(path,sha256)


def _verify(path,sha256,*,prospective_receipt=None,deadline=None):
    root = Path(path).absolute()
    deadline = time.monotonic()+299 if deadline is None else deadline
    _remaining(deadline)
    need(isinstance(sha256,str) and re.fullmatch('[0-9a-f]{64}',sha256),'External integration anchor required')
    if prospective_receipt is None:
        need(_inventory(root) == _members() | {'receipt.json'},'Integration inventory differs')
        receipt,proof = _read(root,'receipt.json')
        need(proof['sha256'] == sha256,'External integration anchor differs')
    else:
        need(_inventory(root) == _members(),'Prospective integration inventory differs')
        receipt = encode(prospective_receipt)
        need(fingerprint(receipt) == sha256,'Prospective integration anchor differs')
    need(set(receipt) == {'schema_version','kind','role','run_id','artifacts'}
         and receipt['schema_version'] == 1 and receipt['kind'] == TRACK and receipt['role'] == 'evaluation_only'
         and set(receipt['artifacts']) == _members(),'Invalid integration receipt')
    for name,pin in receipt['artifacts'].items():
        need(canonical(capture_file(root/name,name)) == canonical(pin),'Integration member changed')
    package,_ = _read(root,'package-proof.json')
    _package_check(package)
    events = read_chain(root/'journal.jsonl')
    need(events[0]['event'] == 'build_reserved' and events[0]['details']['run_id'] == receipt['run_id'],
         'Integration run identity differs')
    run_id = receipt['run_id']
    expected_events = ['build_reserved','integration_started']
    start = events[1]['details']
    need(set(start) == {'start_monotonic','case_end_monotonic','budget','package_proof_sha256'}
         and canonical(start['budget']) == canonical(Budget())
         and type(start['start_monotonic']) in (int,float) and math.isfinite(start['start_monotonic'])
         and start['case_end_monotonic'] == start['start_monotonic']+300
         and start['package_proof_sha256'] == fingerprint(package),'Integration shared budget differs')
    prep_elapsed = 0
    for strategy in STRATEGIES:
        expected_events.extend(['retrieval_preparing','retrieval_ready'])
        preparing = [e['details'] for e in events if e['event'] == 'retrieval_preparing' and e['details'].get('strategy') == strategy]
        ready = [e['details'] for e in events if e['event'] == 'retrieval_ready' and e['details'].get('strategy') == strategy]
        need(len(preparing) == len(ready) == 1
             and canonical(preparing[0]) == canonical(dict(strategy=strategy,policy_sha256=fingerprint(policy_for(strategy)))),
             'Retrieval preparation journal differs')
        item = ready[0]
        need(set(item) == {'strategy','receipt_sha256','request_sha256','elapsed_seconds'}
             and type(item['elapsed_seconds']) in (int,float) and math.isfinite(item['elapsed_seconds'])
             and prep_elapsed <= item['elapsed_seconds'] < 300,'Retrieval preparation timing differs')
        prep_elapsed = item['elapsed_seconds']
    verifier = RetrievalRecordedVerifier(root,run_id,deadline=deadline)
    calls=input_reserved=output_reserved=0
    last_remaining=300-prep_elapsed
    cell_elapsed=0
    for strategy in STRATEGIES:
        expected_events.extend(['cell_preparing','cell_reserved','cell_accepted'])
        groups = {name:[e['details'] for e in events if e['event'] == name and e['details'].get('strategy') == strategy]
                  for name in ('cell_preparing','cell_reserved','cell_accepted')}
        need(all(len(values) == 1 for values in groups.values()),'Duplicate or missing recorded cell events')
        stage = verifier.prepare_stage(strategy)
        payload = verifier.prepare_payload(stage)
        in_quote,out_quote = len(payload['prompt'].encode('utf-8'))+32,payload['n_predict']
        need(canonical(groups['cell_preparing'][0]) == canonical(dict(strategy=strategy,
            request_sha256=fingerprint(stage),payload_sha256=fingerprint(payload))),'Cell preparation binding differs')
        reservation = groups['cell_reserved'][0]
        seconds = reservation['allocated_budget']['max_seconds']
        need(type(seconds) in (int,float) and math.isfinite(seconds) and 0 < seconds <= last_remaining+1e-6,
             'Shared cell deadline reset or overlap')
        budget = replace(Budget(),max_calls=16-calls,max_input_tokens=32000-input_reserved,
                         max_output_tokens=8000-output_reserved,max_seconds=seconds)
        need(canonical(reservation) == canonical(dict(strategy=strategy,input_reservation=in_quote,
            output_reservation=out_quote,allocated_budget=encode(budget),request_sha256=fingerprint(stage),
            payload_sha256=fingerprint(payload))),'Shared cell reservation differs')
        need(input_reserved+in_quote <= 32000 and output_reserved+out_quote <= 8000 and calls < 16,
             'Shared case token/call budget exceeded')
        accepted = groups['cell_accepted'][0]
        need(canonical(accepted) == canonical(dict(strategy=strategy,receipt_sha256=accepted['receipt_sha256'],
            fixture_declared_usage=dict(input_tokens=64,output_tokens=64,cost_usd=0.0),actual_model_calls=0)),
             'Fixture accounting differs')
        cell = root/'cells'/strategy
        config,_ = _read(cell,'configuration.json')
        need(canonical(config['budget']) == canonical(decode(Budget,encode(budget)))
             and canonical(config['caller_configuration']) == canonical(_caller(run_id,strategy)),
             'Child allocation/run binding differs')
        verify_study(cell,expected_receipt_sha256=accepted['receipt_sha256'],verifier=verifier)
        report,_ = _read(cell,'report.json')
        cell_elapsed+=report['elapsed_seconds']
        input_reserved+=in_quote
        output_reserved+=out_quote
        calls+=1
        last_remaining=seconds-report['elapsed_seconds']
    expected_events.append('integration_completed')
    need([e['event'] for e in events] == expected_events,'Integration journal order differs')
    summary,_ = _read(root,'summary.json')
    elapsed = summary['elapsed_seconds']
    need(type(elapsed) in (int,float) and math.isfinite(elapsed) and 0 <= elapsed < 300
         and elapsed+1e-6 >= prep_elapsed+cell_elapsed and elapsed+1e-6 >= 300-last_remaining,
         'Shared elapsed accounting differs')
    need(canonical(summary) == canonical(_summary(run_id,input_reserved,output_reserved,elapsed))
         and events[-1]['details'] == freeze(dict(summary_sha256=fingerprint(summary))),
         'Integration summary differs')
    for name,pin in receipt['artifacts'].items():
        need(canonical(capture_file(root/name,name)) == canonical(pin),'Integration changed during replay')
    _remaining(deadline)
    if prospective_receipt is None:
        need(_read(root,'receipt.json')[1]['sha256'] == sha256,'Integration receipt changed during replay')
    return freeze(dict(summary,receipt_sha256=sha256))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    commands.add_parser('smoke').add_argument('--output',type=Path,required=True)
    check = commands.add_parser('verify')
    check.add_argument('--path',type=Path,required=True)
    check.add_argument('--sha256',required=True)
    args = parser.parse_args(argv)
    result = smoke(args.output) if args.command == 'smoke' else verify(args.path,args.sha256)
    print(json.dumps(encode(result),indent=2))


if __name__ == '__main__':
    main()
