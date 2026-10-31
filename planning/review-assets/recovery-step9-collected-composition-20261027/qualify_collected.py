"""One fresh real-input recorded four-arm qualification; zero model generation."""
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

from asof.contracts import Category
from asof.serde import encode
from asof.study.authority_four_arm import smoke,verify
from asof.study.collected_source import CollectedSourceInput

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
protocol_path=HERE/'QUALIFICATION-PROTOCOL.json'
protocol=json.loads(protocol_path.read_bytes())
assert metadata.version('asof-target-agents')=='0.3.7' and metadata.version('pyarrow')=='21.0.0'
assert not (HERE/'QUALIFICATION.json').exists() and not (HERE/'QUALIFICATION-FAILURE.json').exists()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


assert sha(__file__)==protocol['helper_sha256']
validation=ROOT/protocol['code_validation']['path']
assert sha(validation)==protocol['code_validation']['sha256']
pins=json.loads(validation.read_bytes())['source_pins']
assert all(sha(ROOT/n)==h for n,h in pins.items())
authority_path=ROOT/protocol['source_authority']['path']
assert sha(authority_path)==protocol['source_authority']['sha256']
source_authority=json.loads(authority_path.read_bytes())
source_roots={'project':ROOT,'raw':Path(protocol['raw_root'])}
model=Path(protocol['model_root'])
allowed_source={os.path.normcase(str(source_roots[p['root_id']].joinpath(*p['relative_path'].split('/'))))
                for p in source_authority['files'].values()}
argv=[str(model/'runtime/llama-tokenize.exe'),'--offline','--model',
      str(model/'qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf'),
      '--no-escape','--no-bos','--stdin','--ids','--show-count']
state=dict(phase='execution',children=0,network=[],unapproved=[])


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fsdecode(path)))


def audit(event,args):
    if event in ('os.system','socket.connect','socket.getaddrinfo','socket.__new__'):
        state['network'].append(event)
        raise RuntimeError('No model/network/system dispatch')
    if event=='subprocess.Popen':
        command=subprocess.list2cmdline(argv) if isinstance(args[1],str) else argv
        if state['phase']!='execution' or state['children']>=6 or args[0] not in (None,argv[0]) or args[1]!=command or Path(args[2])!=Path(argv[0]).parent:
            raise RuntimeError('Only six exact pinned tokenizer children allowed')
        state['children']+=1
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        path=normalized(args[0])
        if '\\data\\benchmark\\' in path:
            raise RuntimeError('Evaluation/outcome payloads excluded')
        if path.startswith('e:'):
            flags=args[2] if len(args)>2 and isinstance(args[2],int) else 0
            mode=args[1] if len(args)>1 else None
            if path not in allowed_source or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND) or (isinstance(mode,str) and any(c in mode for c in 'wax+')):
                state['unapproved'].append(path)
                raise RuntimeError('Only existing pinned source inputs can be read on E')


sys.addaudithook(audit)
out=ROOT/'data/cache'/('r09-collected-qualified-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
report=dict(schema_version=1,version='0.3.7',output=str(out),protocol_sha256=sha(protocol_path),
    model_calls=0,provider_spend_usd=0,new_downloads=0,scientific_validation='not_attempted',fresh_case=False)
started=time.monotonic()
try:
    source=CollectedSourceInput(authority_path,protocol['source_authority']['sha256'],source_roots,Category.LITERATURE)
    result=encode(smoke(out,dict(inventory=dict(root_id='project',relative_path=protocol['inventory_path']),
        acquisition=dict(root_id='model',relative_path='acquisition.json')),
        dict(project=ROOT,model=model),collected_source=source))
    elapsed=time.monotonic()-started
    assert elapsed<300 and state['children']==6 and source._active==0
    state['phase']='replay'
    replay_started=time.monotonic()
    replay=encode(verify(out,result['receipt_sha256'],deadline=replay_started+299,source_roots=source_roots))
    replay_seconds=time.monotonic()-replay_started
    assert replay==result and state['children']==6
    assert all(sha(ROOT/n)==h for n,h in pins.items()) and not state['network'] and not state['unapproved']
    request=json.loads((out/'preparation/literal_case_overlap_then_id_v1/request.json').read_bytes())
    coverage=json.loads((out/'preparation/literal_case_overlap_then_id_v1/coverage.json').read_bytes())
    assert coverage['declared_candidates']==coverage['raw_qualified_candidates']==5
    assert coverage['selected_count']==1 and coverage['parent_observations_available']==9 and coverage['missing_input_count']==65
    statements={r['scientific_record']['statement'] for r in request['source_request']['evidence']}
    cells=[]
    for i in range(6):
        response=json.loads((out/'cells'/f'{i:02d}'/'response.json').read_bytes())
        assert response['features']=={} and response['clinical_probability'] is None
        assert all(c['kind']=='source_report' and c['text'] in statements for c in response['response']['claims'])
        quote=json.loads((out/'quotes'/f'{i:02d}'/'quote.json').read_bytes())
        cells.append(dict(cell=i,token_count=quote['token_count'],input_reserved=quote['input_reservation'],
            quote_seconds=quote['elapsed_seconds'],child_seconds=quote['child']['elapsed_seconds']))
    class Memory(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in
            ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
             'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    memory=Memory()
    memory.cb=ctypes.sizeof(memory)
    ctypes.windll.kernel32.GetCurrentProcess.restype=ctypes.c_void_p
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Memory),ctypes.c_ulong]
    ok=ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(memory),memory.cb)
    report.update(status='qualified_collected_source_recorded_four_arm',result=result,coverage=coverage,cells=cells,
        execution_outer_seconds=elapsed,replay_seconds=replay_seconds,tokenizer_children=6,replay_children=0,
        source_pins_unchanged=len(pins),guards=dict(unapproved=state['unapproved'],network=state['network']),
        original_input_roots={k:str(v) for k,v in source_roots.items()},
        peak_parent_working_set_bytes=memory.PeakWorkingSetSize if ok else None,
        child_peak_memory_bytes=None,child_memory_reason='Not independently instrumented',
        retained_bundle_bytes=sum(p.stat().st_size for p in out.rglob('*') if p.is_file()))
    with (HERE/'QUALIFICATION.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2)
    print(json.dumps(dict(status=report['status'],output=str(out),seconds=elapsed,replay_seconds=replay_seconds,
        input_reserved=result['input_reserved'],output_reserved=result['output_reserved'])))
except BaseException as error:
    report.update(status='failed',error_class=type(error).__name__,message=str(error),
        elapsed_seconds=time.monotonic()-started,tokenizer_children=state['children'],guards=state)
    with (HERE/'QUALIFICATION-FAILURE.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2)
    raise
