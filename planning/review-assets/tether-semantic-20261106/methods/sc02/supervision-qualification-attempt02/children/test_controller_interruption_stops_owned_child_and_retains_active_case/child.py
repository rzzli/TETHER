import argparse,json,time,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output');p.add_argument('--mode');a=p.parse_args()
if a.mode=='prestart_hang': time.sleep(10)
if a.mode=='import_failure': print('invented import failure',file=sys.stderr);sys.exit(17)
root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
f=(root/'events.jsonl').open('xb',buffering=0)
def event(kind,**kw):
    f.write((json.dumps(dict(event=kind,monotonic_seconds=time.monotonic(),**kw))+'\n').encode())
event('started');event('model_load_started');event('models_loaded')
for cid in ('a','b','c'):
    if cid=='b' and a.mode=='partial_start':
        f.write(b'{"event":"case_started","case_id":"b"');time.sleep(10)
    event('case_started',case_id=cid)
    if cid=='b' and a.mode=='case_hang':time.sleep(10)
    time.sleep(.01)
    event('case_completed',case_id=cid)
    if cid=='a' and a.mode=='between_hang':time.sleep(10)
if a.mode!='missing_terminal':event('completed',status='passed')
f.close()
