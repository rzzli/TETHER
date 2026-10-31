"""Read-only local asset/resource inspection. Never launches model executables."""
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
MODEL = Path(r'E:\projects_data\drug_target_agents_data\models\qwen25-14b-q4km-20261018T032528Z')
receipt = json.loads((MODEL/'acquisition.json').read_bytes())
def pin(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''): digest.update(chunk)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest.hexdigest())
assets = []
for entry in receipt['items'] + receipt['runtime_files']:
    row = pin(MODEL/(entry.get('name') or entry['path']))
    row['matches_acquisition'] = row['sha256'] == entry['sha256'] and row['bytes'] == entry['bytes']
    assets.append(row)
class Memory(ctypes.Structure):
    _fields_ = [('length',ctypes.c_ulong),('load',ctypes.c_ulong)] + [(name,ctypes.c_ulonglong) for name in
        ('total_physical','available_physical','total_page_file','available_page_file','total_virtual','available_virtual','extended_virtual')]
memory = Memory(); memory.length = ctypes.sizeof(memory)
ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
gpu = subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.free,driver_version','--format=csv,noheader'],capture_output=True,text=True)
result = dict(schema_version=1,role='planning_evidence',collected_at_utc=datetime.now(timezone.utc).isoformat(),
    model_calls=0,downloads=0,provider_spend_usd=0,acquisition=pin(MODEL/'acquisition.json'),assets=assets,
    available_model_directories=[p.name for p in MODEL.parent.iterdir() if p.is_dir()],
    gpu={'command':'nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader',
         'returncode':gpu.returncode,'stdout':gpu.stdout.strip(),'stderr':gpu.stderr.strip()},
    memory=dict(api='GlobalMemoryStatusEx',success=bool(ok),total_physical=memory.total_physical if ok else None,
                available_physical=memory.available_physical if ok else None),
    cpu=dict(logical_processors=os.cpu_count(),identifier=os.environ.get('PROCESSOR_IDENTIFIER')),
    limits=['CIM hardware queries denied; read-only Win32 API fallback used.',
            'Free memory is a momentary observation, not model admission or peak-memory proof.',
            'Only project model root inventoried; no external provider or other user model accounts inspected.'])
with (OUT/'inventory.json').open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2)
print(json.dumps({'assets':len(assets),'all_match':all(a['matches_acquisition'] for a in assets),'memory':result['memory'],'gpu':result['gpu']}))
