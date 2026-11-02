"""Synthetic producer inconsistency: review/claims after an accounted failure."""
from pathlib import Path
import sys,tempfile,shutil,json
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'packages/tether/src'))
from asof.agents import ExtractiveBackend
from asof.artifacts import write_run
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.scorer import ScorerArtifact
from asof.serde import read_json,decode,encode,fingerprint
from asof.workflow import run_workflow
from tether._presentation import verify_engine

root=Path(tempfile.mkdtemp(prefix='tether-independent-terminal-',dir=ROOT/'data/cache'))
shutil.copytree(ROOT/'src/asof/demo/v2',root/'fixtures')
case=decode(Case,read_json(root/'fixtures/case.json'))
model=decode(ScorerArtifact,read_json(root/'fixtures/scorer.json'))
store=load_snapshot(root/'fixtures/snapshot.json',case)
result=run_workflow(case,store,ExtractiveBackend(),model)
trace=encode(result.trace)
pos=next(i for i,e in enumerate(trace) if e['event']=='review')
trace.insert(pos,dict(event='backend_failed',details={'category':trace[pos]['details']['category'],'error_class':'TimeoutError'}))
prior=None
for i,e in enumerate(trace):
    e.pop('sha256',None);e['sequence']=i;e['previous_sha256']=prior;e['sha256']=prior=fingerprint(e)
changed=replace(result,trace=trace)
digest=write_run(root/'run',changed,store,model)
try:
    verify_engine(root/'run',digest)
    result='ACCEPTED_REVIEW_AND_CLAIMS_AFTER_BACKEND_FAILURE'
except Exception as e:
    result=type(e).__name__+': '+str(e)
print(json.dumps({'probe':result,'retained_run':str(root)}))
