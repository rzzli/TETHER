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
assert sys.flags.isolated and version('asof-target-agents')=='0.3.10'
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
result = dict(installed_native_wrapper=native_wrapper_exercise, installed_interpretation_interface=interface_rows, installed_retrieval_smoke=retrieval_result, installed_comparison_smoke=comparison_result, installed_baseline_smoke=baseline_result, installed_study_smoke=study_result, status='passed' if all(r['status']=='passed' for r in records) else 'failed',
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
