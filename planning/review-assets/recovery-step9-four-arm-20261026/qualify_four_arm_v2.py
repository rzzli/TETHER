"""One prospective six-tokenizer invented composition, then dispatch-free replay."""
from datetime import datetime, timezone
import ctypes
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from asof.serde import encode, fingerprint
from asof.study.authority_four_arm import smoke, verify

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
protocol_path=HERE/'QUALIFICATION-PROTOCOL-v2.json'
protocol=json.loads(protocol_path.read_bytes())
assert not (HERE/'QUALIFICATION.json').exists(), 'Qualification already retained; do not repeat'
assert not (HERE/'QUALIFICATION-FAILURE-v2.json').exists(), 'Prior failure retained; no automatic retry'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


assert metadata.version('asof-target-agents')=='0.3.6'
assert digest(__file__)==protocol['helper_sha256']
assert digest(ROOT/protocol['source_pins']['path'])==protocol['source_pins']['sha256']
pins=json.loads((ROOT/protocol['source_pins']['path']).read_bytes())
assert all(digest(ROOT/n)==h for n,h in pins.items())
inventory=json.loads((ROOT/protocol['inventory_path']).read_bytes())
model=Path(protocol['model_root'])
assets=[a for a in inventory['assets'] if a['path'].lower().endswith(('.dll','.gguf','llama-tokenize.exe'))]
assert len(assets)==34


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fsdecode(path)))


allowed=set()  # The verified mirror is entirely on D; deny every E open.
directories=set()
argv=[str(model/'runtime/llama-tokenize.exe'),'--offline','--model',
    str(model/'qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf'),
    '--no-escape','--no-bos','--stdin','--ids','--show-count']
state=dict(phase='execution',children=0,network=[],denied=[],E_files=set())


def child_matches(executable,command,cwd):
    expected=subprocess.list2cmdline(argv) if isinstance(command,str) else argv
    return command==expected and executable in (None,argv[0]) and Path(cwd)==Path(argv[0]).parent


# Exercise the Windows rendered-command representation before any actual child.
assert child_matches(None,subprocess.list2cmdline(argv),Path(argv[0]).parent)
assert child_matches(argv[0],list(argv),Path(argv[0]).parent)
assert not child_matches(None,subprocess.list2cmdline(argv+['--bad']),Path(argv[0]).parent)


def audit(event,args):
    if event in ('os.system','socket.connect','socket.getaddrinfo','socket.__new__'):
        state['network'].append(event)
        raise RuntimeError('No network or system calls')
    if event=='subprocess.Popen':
        if state['phase']!='execution' or state['children']>=6 or not child_matches(args[0],args[1],args[2]):
            raise RuntimeError('Only six pinned tokenizer children during execution')
        state['children']+=1
    if event in ('open','os.listdir','os.scandir') and args and isinstance(args[0],(str,bytes,os.PathLike)):
        name=normalized(args[0])
        if '\\data\\benchmark\\' in name:
            state['denied'].append(name)
            raise RuntimeError('Outcome/gold trees excluded')
        if name.startswith('e:'):
            if state['phase']!='execution':
                state['denied'].append(name)
                raise RuntimeError('Replay does not read original E assets')
            if event=='open':
                mode=args[1] if len(args)>1 else None
                flags=args[2] if len(args)>2 and isinstance(args[2],int) else 0
                if name not in allowed or (isinstance(mode,str) and any(c in mode for c in 'wax+')) or flags&(os.O_WRONLY|os.O_RDWR|os.O_APPEND|os.O_TRUNC|os.O_CREAT):
                    state['denied'].append(name)
                    raise RuntimeError('Unapproved E read/write')
                state['E_files'].add(name)
            elif name not in directories:
                state['denied'].append(name)
                raise RuntimeError('Unapproved E directory')


sys.addaudithook(audit)
suffix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=ROOT/'data/cache'/('r09-four-arm-qualified-'+suffix)
report=dict(schema_version=1,package_version='0.3.6',role='engineering_qualification',
    protocol_sha256=digest(protocol_path),output=str(out),source_pin_count=len(pins),
    generation_calls=0,server_startups=0,provider_spend_usd=0,retries=0,
    protected_payloads_read=False,scientific_validation='not_attempted',
    qualification_attempt=2,prior_failed_attempt_tokenizer_children=2,
    storage_mirror_sha256=protocol['mirror_sha256'],model_root=str(model))
try:
    started=time.monotonic()
    result=encode(smoke(out,dict(inventory=dict(root_id='project',relative_path=protocol['inventory_path']),
        acquisition=dict(root_id='model',relative_path='acquisition.json')),dict(project=ROOT,model=model)))
    report['execution_outer_seconds']=time.monotonic()-started
    assert state['children']==6
    preflight=json.loads((HERE/'PREFLIGHT-RESULT.json').read_bytes())
    cells=[]
    for i in range(6):
        path=out/'cells'/f'{i:02d}'
        request=json.loads((path/'request.json').read_bytes())
        payload=json.loads((path/'payload.json').read_bytes())
        quote=json.loads((out/'quotes'/f'{i:02d}'/'quote.json').read_bytes())
        assert request['original_request_sha256']==preflight['request_sha256']
        assert fingerprint(payload)==preflight['cells'][i]['payload_sha256']
        cells.append(dict(cell=i,payload_sha256=fingerprint(payload),source_request_sha256=request['original_request_sha256'],
            count=quote['token_count'],reservation=quote['input_reservation'],quote_elapsed_seconds=quote['elapsed_seconds'],
            child_seconds=quote['child']['elapsed_seconds']))
    state['phase']='replay'
    replay_start=time.monotonic()
    replay=encode(verify(out,result['receipt_sha256'],deadline=replay_start+299))
    replay_seconds=time.monotonic()-replay_start
    assert state['children']==6 and result==replay
    assert len(state['E_files'])==0
    assert all(digest(ROOT/n)==h for n,h in pins.items())
    class Memory(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in
            ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
             'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    memory=Memory()
    memory.cb=ctypes.sizeof(memory)
    ctypes.windll.kernel32.GetCurrentProcess.restype=ctypes.c_void_p
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Memory),ctypes.c_ulong]
    ok=ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(memory),memory.cb)
    report.update(status='passed',result=result,cells=cells,all_original_payloads_identical=True,
        replay_seconds=replay_seconds,replay_child_count=0,source_pins_unchanged=True,
        tokenizer_children=state['children'],observed_E_file_count=len(state['E_files']),
        denied_access=state['denied'],network_attempts=state['network'],
        peak_parent_working_set_bytes=memory.PeakWorkingSetSize if ok else None,
        child_peak_memory_bytes=None,child_memory_reason='Not independently instrumented',
        retained_bundle_bytes=sum(p.stat().st_size for p in out.rglob('*') if p.is_file()))
    (HERE/'QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','output','execution_outer_seconds','replay_seconds','tokenizer_children')}))
except BaseException as error:
    report.update(status='failed',error_class=type(error).__name__,message=str(error),
        execution_outer_seconds=time.monotonic()-started,
        tokenizer_children=state['children'],denied_access=state['denied'],network_attempts=state['network'])
    (HERE/'QUALIFICATION-FAILURE-v2.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    raise
