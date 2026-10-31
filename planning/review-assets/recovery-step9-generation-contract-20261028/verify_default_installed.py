"""Installed-wheel restoration test with denied original reads and archived execution."""
import ctypes
import hashlib
import importlib.abc
import json
import os
import sys
import time
from pathlib import Path

# The verifier is installed separately. Run with -I; no repository sys.path edits.
BASE = Path(sys.argv[1]).resolve()
REPORT = Path(sys.argv[2]).resolve()
REPORT.parent.mkdir(exist_ok=True, parents=True)
materialization = json.loads((BASE/'materialization.json').read_text(encoding='utf-8'))
envelope = json.loads((BASE/'envelope.json').read_text(encoding='utf-8'))
environment = Path(sys.prefix).resolve()
from importlib.metadata import version
assert sys.flags.isolated and version('asof-target-agents')=='0.3.11'
try:
    version('pyarrow')
except Exception as error:
    from importlib.metadata import PackageNotFoundError
    assert isinstance(error, PackageNotFoundError)
else:
    raise AssertionError('Default installed environment must remain dependency-free')
script = Path(__file__).resolve()
old_roots = [r['logical_root'] for r in envelope['roots']]
forbidden_reads, forbidden_execution, forbidden_imports, forbidden_network = [], [], [], []
v3_original_root = None
v3_original_denial_enabled = False


def under(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fspath(path)))


approved = [normalized(BASE), normalized(environment), normalized(script), normalized(REPORT.parent)]
old = [normalized(p) for p in old_roots]
restored_code = [normalized(Path(roots['project'])) for roots in materialization['approved_root_candidates'].values()]


def audit(event, args):
    if event in ('open', 'os.listdir', 'os.scandir') and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = normalized(os.fsdecode(args[0]))
        if v3_original_denial_enabled and under(path, v3_original_root):
            forbidden_reads.append(dict(event=event,path=path))
            raise PermissionError('Original synthetic v3 JSON unavailable after relocation')
        if path.startswith('e:') or '\\data\\benchmark\\' in path:
            forbidden_reads.append(dict(event=event,path=path))
            raise PermissionError('Original assets and benchmark payloads unavailable')
        if any(under(path, root) for root in old) and not any(under(path, root) for root in approved):
            forbidden_reads.append(dict(event=event, path=path))
            raise PermissionError('Original-root access denied by restoration guard')
    if event == 'exec' and args:
        filename = args[0].co_filename
        if filename and not filename.startswith('<') and any(under(normalized(filename), root) for root in restored_code):
            forbidden_execution.append(filename)
            raise PermissionError('Archived source execution denied')
    if event in ('socket.connect', 'subprocess.Popen'):
        forbidden_network.append(event)
        raise PermissionError('Network/child dispatch denied during verification')


class NoTools(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'tools' or fullname.startswith('tools.'):
            forbidden_imports.append(fullname)
            raise ImportError('Repository-only tools package forbidden in installed verification')


sys.meta_path.insert(0, NoTools())
sys.addaudithook(audit)
from asof.archive.restore import verify
import asof.archive.core as core

assert Path(core.__file__).resolve().is_relative_to(environment)
from asof.study.__main__ import smoke
study_result = smoke(REPORT.parent / 'study-smoke-installed')
from asof.study.baseline_smoke import smoke as baseline_smoke
from asof.serde import encode
baseline_result = encode(baseline_smoke(REPORT.parent / 'baseline-smoke-installed'))
from asof.study.fixed_evidence_smoke import smoke as comparison_smoke
comparison_result = encode(comparison_smoke(REPORT.parent / 'comparison-installed'))
from asof.study.retrieval_smoke import smoke as retrieval_smoke
retrieval_result = encode(retrieval_smoke(REPORT.parent / 'retrieval-installed'))
assert study_result['status'] == 'recorded_smoke_passed'
from asof.study.interpretation_interface import prepare_payload, request_from_payload, validate_output
from asof.study.diagnostic import load_synthetic_request
from asof.study.diagnostic_codec import pointer
from asof.serde import ContractError, fingerprint, canonical
interface_rows=[]
for fixture in ('synthetic-context','synthetic-orientation'):
    request=load_synthetic_request(fixture)
    for arm,count in (('asof_interpretation',1),('adapted_virtual_biotech_interpretation',5)):
        history=[]
        for index in range(count):
            prepared=prepare_payload(request,arm,index,history)
            assert fingerprint(request_from_payload(prepared['payload']))==fingerprint(request)
            quote=prepared['semantic_data']['quote_catalog'][0]
            document=dict(answer_status='answered',claims=[dict(kind='source_report',
                text=pointer(encode(request),quote['request_pointer']),quote_refs=[quote['quote_id']],limitations=[])],
                unresolved=[],abstention_reason=None)
            response=validate_output(request,prepared['payload'],document)
            assert encode(response['response'])==document and response['features']=={} and response['clinical_probability'] is None
            assert response['quotes'][0]['text']==document['claims'][0]['text']
            for state in ('partial','abstained'):
                alternative=dict(document,answer_status=state,abstention_reason='Invented incomplete source.')
                if state=='abstained':alternative['claims']=[]
                validate_output(request,prepared['payload'],alternative)
            try:
                validate_output(request,prepared['payload'],dict(document,abstention_reason='Contradiction.'))
            except ContractError:
                pass
            else:
                raise AssertionError('Contradictory state accepted')
            interface_rows.append(dict(fixture=fixture,arm=arm,index=index,request_sha256=fingerprint(request),
                payload_sha256=prepared['payload_sha256'],response_sha256=fingerprint(response),states_checked=3))
            history.append(dict(stage=prepared['semantic_data']['stage'],source_ids=['E0']))
assert len(interface_rows)==12


# Prospective v3 preparation and semantic validation only. These are synthetic
# values; no recognizer, tokenizer, native adapter, model or child is invoked.
from collections.abc import Mapping
from asof.study import interpretation_generation as generation
from asof.study import interpretation_grammar as grammar_module
from asof.study import interpretation_interface as legacy_interface
assert Path(generation.__file__).resolve().is_relative_to(environment)
assert Path(grammar_module.__file__).resolve().is_relative_to(environment)
assert generation.INTERFACE=='source-quote-interpretation-v3-gbnf'
assert grammar_module.GENERATOR=='strict-interpretation-gbnf-v1'


def deeply_frozen(value):
    if isinstance(value, Mapping):
        before=fingerprint(value)
        try:value['__installed_mutation_probe__']=True
        except TypeError:pass
        else:raise AssertionError('Mutable accepted v3 mapping')
        assert fingerprint(value)==before
        for child_value in value.values():deeply_frozen(child_value)
    elif isinstance(value,(tuple,list)):
        assert isinstance(value,tuple),'Mutable accepted v3 sequence'
        for child_value in value:deeply_frozen(child_value)


def must_reject_v3(label, operation):
    try:operation()
    except ContractError:return label
    raise AssertionError('Invalid new/old v3 binding or bound accepted: '+label)


generation_rows=[]
generation_rejections=[]
relocation_fixture=None
for fixture in ('synthetic-context','synthetic-orientation'):
    request=load_synthetic_request(fixture)
    for arm,count in (('asof_interpretation',1),('adapted_virtual_biotech_interpretation',5)):
        history=[]
        for index in range(count):
            prepared=generation.prepare_payload(request,arm,index,history)
            legacy=legacy_interface.prepare_payload(request,arm,index,history)
            payload=prepared['payload']
            artifact=prepared['generation_grammar']
            assert prepared['schema_version']==3 and not prepared['execution_authorized']
            assert prepared['native_conformance']==artifact['native_conformance']=='unverified'
            assert prepared['payload_sha256']==fingerprint(payload)!=legacy['payload_sha256']
            assert prepared['generation_contract_sha256']==fingerprint(artifact)
            assert prepared['acceptance_schema_sha256']==fingerprint(legacy['payload']['json_schema'])
            assert fingerprint(prepared['acceptance_schema'])==fingerprint(legacy['payload']['json_schema'])
            assert prepared['quote_catalog_sha256']==legacy['quote_catalog_sha256']
            assert fingerprint(generation.request_from_payload(payload))==fingerprint(request)
            assert 'json_schema' not in payload and payload['grammar']==artifact['grammar']
            assert len(payload['prompt'].encode('utf-8'))<=32768 and len(canonical(payload))<=65536
            assert artifact['grammar_bytes']==len(artifact['grammar'].encode('utf-8'))<=65536
            assert artifact['grammar_sha256']==hashlib.sha256(artifact['grammar'].encode('utf-8')).hexdigest()
            assert artifact['post_validation_only'] and artifact['serialization_domain']['unicode_normalization']=='none'
            quote=prepared['semantic_data']['quote_catalog'][0]
            document=dict(answer_status='answered',claims=[dict(kind='source_report',
                text=pointer(encode(request),quote['request_pointer']),quote_refs=[quote['quote_id']],limitations=[])],
                unresolved=[],abstention_reason=None)
            validated=generation.validate_output(request,payload,document)
            assert encode(validated['response'])==document and validated['features']=={} and validated['clinical_probability'] is None
            assert validated['native_conformance']=='unverified' and validated['scientific_validation']=='not_established'
            assert validated['payload_sha256']==fingerprint(payload)
            assert validated['generation_contract_sha256']==prepared['generation_contract_sha256']
            assert validated['acceptance_schema_sha256']==prepared['acceptance_schema_sha256']
            assert validated['quotes'][0]['text']==document['claims'][0]['text']
            states=[]
            for state in ('answered','partial','abstained'):
                alternative=encode(document)
                alternative.update(answer_status=state,abstention_reason=None if state=='answered' else 'Invented incomplete source.')
                if state=='abstained':alternative['claims']=[]
                result=generation.validate_output(request,payload,alternative)
                assert encode(result['response'])==alternative and result['features']=={} and result['clinical_probability'] is None
                assert result['native_conformance']=='unverified'
                states.append(dict(state=state,response_sha256=fingerprint(result)))
            before=fingerprint(prepared)
            response_before=fingerprint(validated)
            deeply_frozen(prepared)
            deeply_frozen(validated)
            mutated=encode(document)
            mutation_result=generation.validate_output(request,payload,mutated)
            mutated['claims'][0]['text']='Caller mutation.'
            assert fingerprint(mutation_result)==response_before
            assert fingerprint(prepared)==before and fingerprint(validated)==response_before
            prefix=f'{fixture}/{arm}/{index}/'
            for label,operation in (
                ('old_reconstruct_new',lambda:legacy_interface.request_from_payload(payload)),
                ('new_reconstruct_old',lambda:generation.request_from_payload(legacy['payload'])),
                ('old_validate_new',lambda:legacy_interface.validate_output(request,payload,document)),
                ('new_validate_old',lambda:generation.validate_output(request,legacy['payload'],document)),
                ('contradictory_state',lambda:generation.validate_output(request,payload,dict(document,abstention_reason='Contradiction.'))),
            ):
                generation_rejections.append(must_reject_v3(prefix+label,operation))
            tampered=encode(payload)
            tampered['grammar']+='\n# changed binding'
            generation_rejections.append(must_reject_v3(prefix+'changed_grammar',lambda:generation.request_from_payload(tampered)))
            generation_rows.append(dict(fixture=fixture,arm=arm,index=index,request_sha256=fingerprint(request),
                payload_sha256=prepared['payload_sha256'],generation_contract_sha256=prepared['generation_contract_sha256'],
                grammar_sha256=artifact['grammar_sha256'],grammar_bytes=artifact['grammar_bytes'],
                prompt_bytes=len(payload['prompt'].encode('utf-8')),payload_bytes=len(canonical(payload)),
                response_sha256=response_before,states=states,deeply_immutable=True,native_conformance='unverified'))
            if relocation_fixture is None:
                relocation_fixture=dict(schema_version=1,kind='synthetic_v3_pure_preparation_and_response',
                    preparation=encode(prepared),authored_response=encode(document),validated_response=encode(validated))
            history.append(dict(stage=prepared['semantic_data']['stage'],source_ids=['E0']))
assert len(generation_rows)==12 and len(generation_rejections)==72
generation_rejections.append(must_reject_v3('oversized_original_quote_no_pruning',
    lambda:grammar_module.build_grammar({'Q0':'x'*32769})))
generation_rejections.append(must_reject_v3('oversized_raw_response',
    lambda:generation.validate_output(request,payload,b' '*262145)))

# Relocate data only. The receipt's expected hash is anchored outside both data
# directories before copying; it is never learned from the copied receipt.
original_v3=REPORT.parent/'generation-v3-original'
copied_v3=REPORT.parent/'generation-v3-relocated'
original_v3.mkdir(exist_ok=False)
copied_v3.mkdir(exist_ok=False)
fixture_bytes=canonical(relocation_fixture)
fixture_sha256=hashlib.sha256(fixture_bytes).hexdigest()
json_receipt=dict(schema_version=1,kind='pure_v3_json_fixture_receipt',files={'fixture.json':fixture_sha256},
    preparation_sha256=fingerprint(relocation_fixture['preparation']),
    validated_response_sha256=fingerprint(relocation_fixture['validated_response']),native_conformance='unverified')
receipt_bytes=canonical(json_receipt)
external_expected_receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest()
external_anchor=REPORT.parent/'generation-v3-external-anchor.json'
with external_anchor.open('xb') as stream:
    stream.write(canonical(dict(receipt_sha256=external_expected_receipt_sha256,fixture_sha256=fixture_sha256,
        role='same-run synthetic expected hash outside relocated artifact; not independent native or scientific evidence')))
for name,contents in (('fixture.json',fixture_bytes),('receipt.json',receipt_bytes)):
    with (original_v3/name).open('xb') as stream:stream.write(contents)
    with (copied_v3/name).open('xb') as stream:stream.write((original_v3/name).read_bytes())
v3_original_root=normalized(original_v3)
v3_original_denial_enabled=True
copied_receipt_bytes=(copied_v3/'receipt.json').read_bytes()
assert hashlib.sha256(copied_receipt_bytes).hexdigest()==external_expected_receipt_sha256
copied_receipt=json.loads(copied_receipt_bytes)
assert copied_receipt['files']=={'fixture.json':fixture_sha256}
copied_fixture_bytes=(copied_v3/'fixture.json').read_bytes()
assert hashlib.sha256(copied_fixture_bytes).hexdigest()==copied_receipt['files']['fixture.json']
copied_fixture=json.loads(copied_fixture_bytes)
copied_preparation=copied_fixture['preparation']
restored_request=generation.request_from_payload(copied_preparation['payload'])
restored_data=copied_preparation['semantic_data']
reconstructed=generation.prepare_payload(restored_request,restored_data['arm'],restored_data['stage_index'],
    restored_data['prior_source_id_feedback'])
assert fingerprint(reconstructed)==fingerprint(copied_preparation)==copied_receipt['preparation_sha256']
revalidated=generation.validate_output(restored_request,reconstructed['payload'],copied_fixture['authored_response'])
assert fingerprint(revalidated)==fingerprint(copied_fixture['validated_response'])==copied_receipt['validated_response_sha256']
assert revalidated['native_conformance']=='unverified' and not reconstructed['execution_authorized']
deeply_frozen(reconstructed)
deeply_frozen(revalidated)
generation_exercise=dict(role='pure_synthetic_v3_preparation_and_semantic_validation_only',stages=generation_rows,
    stage_count=len(generation_rows),state_validations=sum(len(row['states']) for row in generation_rows),
    rejected=generation_rejections,negative_case_count=len(generation_rejections),
    native_conformance='unverified',execution_authorized=False,actual_model_calls=0,
    tokenizer_calls=0,native_processes=0,network_calls=0,scientific_validation='not_established',
    relocation=dict(kind='plain_json_pure_artifact_relocation_only',original=str(original_v3),copied=str(copied_v3),
        external_anchor=str(external_anchor),external_anchor_sha256=hashlib.sha256(external_anchor.read_bytes()).hexdigest(),
        external_expected_receipt_sha256=external_expected_receipt_sha256,fixture_sha256=fixture_sha256,
        preparation_sha256=fingerprint(reconstructed),validated_response_sha256=fingerprint(revalidated),
        original_json_reads_denied=True,archived_code_executed=False,new_native_or_dossier_family=False))


# Explicitly invented native-wrapper bytes; no HTTP adapter or process is started.
import base64
from contextlib import closing
from asof.journal import RunJournal
from asof.study import native
from asof.study.native_interpretation import validate_native_response
from asof.study.native_accounting import accounting
original=load_synthetic_request('synthetic-orientation')
stage=dict(original_request=encode(original),fixture='installed_wrapper_only')
payload=prepare_payload(original,'asof_interpretation',0,[])['payload']
document=dict(answer_status='abstained',claims=[],unresolved=[],abstention_reason='Invented wrapper only.')
body=dict(prompt=payload['prompt'],model='fixture',
    generation_settings={k:encode(payload[k]) for k in ('seed','temperature','n_predict','stop','stream')},
    truncated=False,stop=True,stop_type='eos',stopped_limit=False,stopping_word='',
    tokens_evaluated=20,tokens_predicted=5,content=canonical(document).decode())
raw=canonical(body)
wrapper=dict(schema_version=1,kind=native.PROTOCOL,request_sha256=fingerprint(stage),payload_sha256=fingerprint(payload),
    owner_pid=4242,endpoint='http://127.0.0.1:55581',http_status=200,body_base64=base64.b64encode(raw).decode(),
    body_sha256=hashlib.sha256(raw).hexdigest(),complete=True,error_class=None,elapsed_seconds=0.01)
response=validate_native_response(stage,payload,canonical(wrapper),model_alias='fixture')
assert response['response']['answer_status']=='abstained' and response['features']=={} and response['clinical_probability'] is None
rejected=[]
for key,value in (('request_sha256','a'*64),('body_sha256','b'*64),('complete',False)):
    try:validate_native_response(stage,payload,canonical(dict(wrapper,**{key:value})),model_alias='fixture')
    except ContractError:rejected.append(key)
    else:raise AssertionError('Invalid wrapper accepted')
account_root=REPORT.parent/'native-wrapper-accounting'
with closing(RunJournal(account_root,kind='build')) as journal:
    journal.append('native_context_qualified',context=dict(endpoint=wrapper['endpoint'],owner_pid=4242,model_alias='fixture',model_provenance={}))
child=account_root/'cells/00'
child.parent.mkdir()
with closing(RunJournal(child,kind='build')) as journal:
    journal.append('study_dispatch',request_sha256=fingerprint(stage),payload_sha256=fingerprint(payload))
    journal.append('study_accounted',usage=dict(input_tokens=20,output_tokens=5,cost_usd=0.0),basis='adapter_reported')
(child/'request.json').write_bytes(canonical(stage))
(child/'payload.json').write_bytes(canonical(payload))
(child/'raw-response.bin').write_bytes(canonical(wrapper))
native_fixture_accounting=accounting(account_root,'simulated_native_transport')
assert native_fixture_accounting['actual_model_calls']==native_fixture_accounting['known_http_attempts']==0
assert native_fixture_accounting['known_simulated_model_calls']==1
assert native_fixture_accounting['simulated_transport_usage']==dict(input_tokens=20,output_tokens=5,cost_usd=0.0)
native_wrapper_exercise=dict(role='invented_wrapper_only',positive_cases=1,negative_cases=rejected,
    accounting=native_fixture_accounting,actual_native_servers=0,network_calls=0)


from asof.study.native_interpretation import verify_native_duration
from asof.workflow import Budget
duration_configuration=dict(budget=encode(Budget()))
duration_cases=[]
for name,elapsed,configuration,report,expected in [
    ('zero',0.0,duration_configuration,dict(elapsed_seconds=0.0),True),
    ('enclosed',0.01,duration_configuration,dict(elapsed_seconds=0.02),True),
    ('report_equal',0.01,duration_configuration,dict(elapsed_seconds=0.01),True),
    ('over_budget',9999.0,duration_configuration,dict(elapsed_seconds=0.02),False),
    ('at_budget',300.0,duration_configuration,dict(elapsed_seconds=300.0),False),
    ('above_report',0.01,duration_configuration,dict(elapsed_seconds=0.0),False),
    ('missing_budget',0.0,{},dict(elapsed_seconds=0.02),False),
    ('missing_report',0.0,duration_configuration,None,False),
]:
    try:
        verify_native_duration(dict(elapsed_seconds=elapsed),configuration,report=report)
        accepted=True
    except ContractError:accepted=False
    assert accepted==expected,name
    duration_cases.append(dict(id=name,accepted=accepted,expected=expected))
native_wrapper_exercise['duration_cases']=duration_cases

records = []
started = time.monotonic()
for run in envelope['runs']:
    run_started = time.monotonic()
    try:
        result = verify(materialization['envelope'], materialization['envelope_sha256'], run['run_id'],
                        materialization['approved_root_candidates'][run['run_id']],
                        receipt_sha256=run.get('receipt_sha256'), journal_sha256=run.get('journal_sha256'))
        records.append(dict(run_id=run['run_id'], status='passed', result=result,
                            elapsed_seconds=time.monotonic()-run_started))
    except Exception as error:
        records.append(dict(run_id=run['run_id'], status='failed', error_class=type(error).__name__, message=str(error)))
    REPORT.write_text(json.dumps(dict(status='verification_in_progress', results=records), indent=2)+'\n', encoding='utf-8')

class Memory(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
        (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
        'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]

memory = Memory()
memory.cb = ctypes.sizeof(memory)
ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Memory), ctypes.c_ulong]
ctypes.windll.psapi.GetProcessMemoryInfo.restype = ctypes.c_int
ok = ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(memory), memory.cb)
assert not any((forbidden_reads,forbidden_execution,forbidden_imports,forbidden_network))
result = dict(installed_generation_v3=generation_exercise, installed_native_wrapper=native_wrapper_exercise, installed_interpretation_interface=interface_rows, installed_retrieval_smoke=retrieval_result, installed_comparison_smoke=comparison_result, installed_baseline_smoke=baseline_result, installed_study_smoke=study_result, status='passed' if all(r['status']=='passed' for r in records) else 'failed',
              installed_module=str(core.__file__), isolated_mode=bool(sys.flags.isolated),
              verifier_environment=str(environment), results=records, elapsed_seconds=time.monotonic()-started,
              peak_working_set_bytes=memory.PeakWorkingSetSize if ok else None,
              original_root_access_attempts=forbidden_reads, archived_execution_attempts=forbidden_execution,
              repository_tools_import_attempts=forbidden_imports, network_or_child_attempts=forbidden_network,
              receipt_bytes_rewritten=False, historical_program_execution='not_performed',
              scientific_validation='not_established')
REPORT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['status']=='passed' else 1)
