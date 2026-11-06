import json,time,tracemalloc
from pathlib import Path
p=Path('experiments/labbench/run.py')
results=[]
for cap in (512*1024**2,64*1024**2,p.stat().st_size):
    tracemalloc.start()
    started=time.perf_counter()
    for _ in range(5):
        with p.open('rb') as stream:
            value=stream.read(cap+1)
    elapsed=time.perf_counter()-started
    current,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    results.append({'cap':cap,'actual_bytes':len(value),'reads':5,'elapsed_seconds':elapsed,'traced_peak_bytes':peak})
print(json.dumps({'scope':'Read-only synthetic allocation diagnosis using current run.py as a small ordinary file; no project imports or benchmark content','results':results}))
