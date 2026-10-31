"""One real-input case with explicitly simulated native I/O, actual offline quotes."""
from datetime import datetime,timezone
import ctypes
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from asof.contracts import Category
from asof.serde import canonical,encode,parse_json
from asof.study import native
from asof.study.authority_four_arm import smoke,verify
from asof.study.collected_source import CollectedSourceInput
from asof.study.interpretation_interface import request_from_payload
from asof.study.native_mode import NativeExecutionConfig,ALIAS

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
protocol_path=HERE/'SIMULATION-PROTOCOL.json'
protocol=json.loads(protocol_path.read_bytes())
assert metadata.version('asof-target-agents')=='0.3.9' and metadata.version('pyarrow')=='21.0.0'
assert not (HERE/'SIMULATION-QUALIFICATION.json').exists() and not (HERE/'SIMULATION-FAILURE.json').exists()


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


assert sha(__file__)==protocol['helper_sha256']
validation=ROOT/protocol['code_validation']['path']
assert sha(validation)==protocol['code_validation']['sha256']
checked=json.loads(validation.read_bytes());pins=checked['source_pins']
assert checked['status']=='passed' and all(sha(ROOT/n)==h for n,h in pins.items())
authority_path=ROOT/protocol['source_authority']['path']
assert sha(authority_path)==protocol['source_authority']['sha256']
authority=json.loads(authority_path.read_bytes())
roots=dict(project=ROOT,raw=Path(protocol['raw_root']))
allowed={os.path.normcase(str(roots[p['root_id']].joinpath(*p['relative_path'].split('/')))) for p in authority['files'].values()}
model=Path(protocol['model_root'])
argv=[str(model/'runtime/llama-tokenize.exe'),'--offline','--model',str(model/'qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf'),
    '--no-escape','--no-bos','--stdin','--ids','--show-count']
state=dict(phase='execution',children=0,network=[],unapproved=[],simulated_posts=0,simulated_servers=0)


def audit(event,args):
    if event in ('os.system','socket.connect','socket.getaddrinfo','socket.__new__'):
        state['network'].append(event);raise RuntimeError('No real network or server')
    if event=='subprocess.Popen':
        expected=subprocess.list2cmdline(argv) if isinstance(args[1],str) else argv
        if state['phase']!='execution' or state['children']>=6 or args[0] not in (None,argv[0]) or args[1]!=expected or Path(args[2])!=Path(argv[0]).parent:
            raise RuntimeError('Only six exact tokenizer children permitted')
        state['children']+=1
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if '\\data\\benchmark\\' in path:raise RuntimeError('Evaluation payloads excluded')
        if path.startswith('e:'):
            mode=args[1] if len(args)>1 else None
            flags=args[2] if len(args)>2 and isinstance(args[2],int) else 0
            if path not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND) or (isinstance(mode,str) and any(c in mode for c in 'wax+')):
                state['unapproved'].append(path);raise RuntimeError('Only pinned original E inputs may be read')


class SimulatedProcess:
    pid=4242001
    def __init__(self,argv,**kwargs):
        state['simulated_servers']+=1;self.code=None
        kwargs['stderr'].write(b'SIMULATED TRANSPORT FIXTURE ONLY\nn_slots = 1, n_ctx_slot = 16384\n');kwargs['stderr'].flush()
    def poll(self):return self.code
    def terminate(self):self.code=0
    def kill(self):self.code=-1
    def wait(self,timeout):return self.code


class SimulatedSocket:
    def settimeout(self,value):pass
    def shutdown(self,value):pass
    def close(self):pass


class Response:
    status=200
    def __init__(self,body):self.body=body;self.length=len(body)
    def read1(self,count):
        part=self.body[:count];self.body=self.body[count:];self.length-=len(part);return part
    def close(self):pass


class SimulatedConnection:
    def __init__(self,*args,**kwargs):self.sock=SimulatedSocket()
    def connect(self):pass
    def request(self,method,path,body,headers):
        assert state['phase']=='execution' and state['simulated_posts']<6
        payload=parse_json(body);original=request_from_payload(payload)
        text=original['source_request']['evidence'][0]['statement']
        document=dict(answer_status='partial',claims=[dict(kind='source_report',text=text,quote_refs=['Q0'],
            limitations=['Deterministic simulated transport; not a model or scientific interpretation.'])],
            unresolved=['Scientific source/question sufficiency remains unreviewed.'],
            abstention_reason='Fixture only; no independently assessed answer was generated.')
        self.response=Response(canonical(dict(prompt=payload['prompt'],model=ALIAS,
            generation_settings={k:encode(payload[k]) for k in ('seed','temperature','n_predict','stop','stream')},
            truncated=False,stop=True,stop_type='eos',stopped_limit=False,stopping_word='',
            tokens_evaluated=64,tokens_predicted=64,content=canonical(document).decode())))
        state['simulated_posts']+=1
    def getresponse(self):return self.response
    def close(self):pass


sys.addaudithook(audit)
out=ROOT/'data/cache'/('r09-native-simulation-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
report=dict(schema_version=1,version='0.3.9',role='engineering_simulated_transport_qualification',output=str(out),
    protocol_sha256=sha(protocol_path),actual_model_calls=0,actual_native_servers=0,actual_network_requests=0,
    provider_spend_usd=0,new_downloads=0,scientific_validation='not_attempted',fresh_case=False)
started=time.monotonic()
try:
    source=CollectedSourceInput(authority_path,protocol['source_authority']['sha256'],roots,Category.LITERATURE)
    config=NativeExecutionConfig(model,55581,execution_scope='simulated_native_transport',process_factory=SimulatedProcess,
        availability_probe=lambda *_:None,listener_owner=lambda *_:True,health_probe=lambda *_:True)
    with patch.object(native.http.client,'HTTPConnection',SimulatedConnection):
        result=encode(smoke(out,dict(inventory=dict(root_id='project',relative_path=protocol['inventory_path']),
            acquisition=dict(root_id='model',relative_path='acquisition.json')),dict(project=ROOT,model=model),
            collected_source=source,native_execution=config))
    execution_seconds=time.monotonic()-started
    assert execution_seconds<300 and state['children']==state['simulated_posts']==6 and state['simulated_servers']==1
    assert result['actual_model_calls']==result['native_processes']==result['recorded_calls']==0
    assert result['simulated_native_calls']==6 and result['pure_invocations']==2
    assert result['simulated_transport_usage']==dict(input_tokens=384,output_tokens=384,cost_usd=0.0)
    assert source._active==config._active==0
    state['phase']='replay';replay_started=time.monotonic()
    with patch.object(native.http.client,'HTTPConnection',side_effect=AssertionError('No replay I/O')):
        replay=encode(verify(out,result['receipt_sha256'],source_roots=roots,native_roots={'model':model},deadline=replay_started+299))
    assert replay==result and state['children']==6 and not state['network'] and not state['unapproved']
    assert all(sha(ROOT/n)==h for n,h in pins.items())
    coverage=json.loads((out/'preparation/literal_case_overlap_then_id_v1/coverage.json').read_bytes())
    assert coverage['declared_candidates']==coverage['raw_qualified_candidates']==5 and coverage['selected_count']==1
    assert coverage['parent_observations_available']==9 and coverage['missing_input_count']==65
    class Memory(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in
            ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
             'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    memory=Memory();memory.cb=ctypes.sizeof(memory)
    ctypes.windll.kernel32.GetCurrentProcess.restype=ctypes.c_void_p
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Memory),ctypes.c_ulong]
    ok=ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(memory),memory.cb)
    report.update(status='qualified_real_inputs_simulated_native_case',result=result,coverage=coverage,
        execution_seconds=execution_seconds,replay_seconds=time.monotonic()-replay_started,tokenizer_children=6,
        simulated_posts=6,simulated_servers=1,guards=state,source_pins_unchanged=len(pins),
        peak_parent_working_set_bytes=memory.PeakWorkingSetSize if ok else None,
        child_peak_memory_bytes=None,child_memory_reason='Tokenizer children not independently instrumented',
        retained_bundle_bytes=sum(p.stat().st_size for p in out.rglob('*') if p.is_file()))
    with (HERE/'SIMULATION-QUALIFICATION.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({k:report[k] for k in ('status','output','execution_seconds','replay_seconds','actual_model_calls')}))
except BaseException as error:
    report.update(status='failed',error_class=type(error).__name__,message=str(error),elapsed_seconds=time.monotonic()-started,guards=state)
    with (HERE/'SIMULATION-FAILURE.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    raise
