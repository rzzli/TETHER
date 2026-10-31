"""Static PE/API discovery only; no DLL loading, process, server or model."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
accepted=ROOT/'planning/review-assets/recovery-step9-native-integration-20261027'
acceptance=json.loads((accepted/'acceptance.json').read_bytes())
assert acceptance['status']=='accepted_native_adapter_controller_integration_engineering_only'
mirror=json.loads((accepted/'NATIVE-MODEL-MIRROR.json').read_bytes())
model=Path(mirror['target'])
items={p['relative_path']:p for p in mirror['items']}
acquisition=json.loads((model/'acquisition.json').read_bytes())
assert acquisition['runtime_tag']=='b11717'
guards=[]


def audit(event,args):
    if event in ('subprocess.Popen','os.system','socket.connect','socket.getaddrinfo','socket.__new__','ctypes.dlopen'):
        guards.append(event);raise RuntimeError('Static inspection only')


sys.addaudithook(audit)


def exports(raw):
    assert raw[:2]==b'MZ'
    pe=struct.unpack_from('<I',raw,0x3c)[0]
    assert raw[pe:pe+4]==b'PE\0\0'
    machine,count=struct.unpack_from('<HH',raw,pe+4)
    optional_size=struct.unpack_from('<H',raw,pe+20)[0]
    opt=pe+24;magic=struct.unpack_from('<H',raw,opt)[0]
    assert magic in (0x10b,0x20b)
    directories=opt+(112 if magic==0x20b else 96)
    export_rva,export_size=struct.unpack_from('<II',raw,directories)
    sections=[]
    for i in range(count):
        offset=opt+optional_size+40*i
        vsize,va,size,pointer=struct.unpack_from('<IIII',raw,offset+8)
        assert pointer+size<=len(raw)
        sections.append((va,vsize,size,pointer))
    def physical(rva):
        for va,vsize,size,pointer in sections:
            if va<=rva<va+max(vsize,size):
                assert rva-va<size
                return pointer+rva-va
        raise ValueError('RVA outside file-backed section')
    if not export_rva:return machine,[]
    directory=physical(export_rva)
    names_count=struct.unpack_from('<I',raw,directory+24)[0]
    names_offset=physical(struct.unpack_from('<I',raw,directory+32)[0])
    assert names_count<100000 and names_offset+4*names_count<=len(raw)
    names=[]
    for i in range(names_count):
        start=physical(struct.unpack_from('<I',raw,names_offset+4*i)[0])
        # Actual approved C++ template exports include a 2,325-byte name.
        # Bound parsing by both the input file and a 64 KiB export-name limit.
        end=raw.find(b'\0',start,min(len(raw),start+65536))
        assert end>=start
        names.append(raw[start:end].decode('ascii'))
    assert len(set(names))==len(names)
    return machine,names


records=[]
for name in ('runtime/llama-common.dll','runtime/llama.dll','runtime/llama-server-impl.dll'):
    path=model/name;raw=path.read_bytes()
    assert len(raw)==items[name]['bytes'] and hashlib.sha256(raw).hexdigest()==items[name]['sha256']
    machine,names=exports(raw)
    assert machine==0x8664 and names
    matches=[n for n in names if any(s in n.lower() for s in ('schema','grammar','llguidance'))]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==items[name]['sha256']
    records.append(dict(relative_path=name,sha256=items[name]['sha256'],bytes=len(raw),
        architecture='x86_64',named_export_count=len(names),grammar_schema_exports=matches))
tools={n:shutil.which(n) for n in ('cmake','ninja','cl','clang++','g++','dumpbin','llvm-readobj','vswhere')}
assert not guards
report=dict(schema_version=1,status='static_pinned_runtime_export_discovery',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    runtime_tag=acquisition['runtime_tag'],approved_model_root=str(model),
    acceptance_sha256=hashlib.sha256((accepted/'acceptance.json').read_bytes()).hexdigest(),
    records=records,tools_on_path=tools,model_calls=0,servers=0,dynamic_libraries_loaded=0,
    subprocesses=0,network_calls=0,provider_cost_usd=0,denied_operations=guards,
    grammar_conformance='unverified',source_to_binary_build_equivalence='not_established')
with (HERE/'RUNTIME-DISCOVERY.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report,indent=2))
