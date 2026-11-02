"""Synthetic independent probe; retain attempts in ignored workspace scratch."""
from pathlib import Path
import sys, tempfile, shutil, json
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'packages/tether/src'))
from asof.agents import ExtractiveBackend
from asof.artifacts import write_run
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.scorer import ScorerArtifact
from asof.serde import read_json, decode, encode, fingerprint
from asof.workflow import run_workflow
from tether._presentation import verify_engine

class B(ExtractiveBackend):
    def prepare_request(self, req):
        return req, {'selected_ids':[x.observation_id for x in req.evidence], 'method':'fictional'}

root=Path(tempfile.mkdtemp(prefix='tether-independent-state-',dir=ROOT/'data/cache'))
shutil.copytree(ROOT/'src/asof/demo/v2',root/'fixtures')
case=decode(Case,read_json(root/'fixtures/case.json'))
model=decode(ScorerArtifact,read_json(root/'fixtures/scorer.json'))
store=load_snapshot(root/'fixtures/snapshot.json',case)
result=run_workflow(case,store,B(),model)
trace=encode(result.trace); coverage=encode(result.coverage)
event=next(x for x in trace if x['event']=='bounded_retrieval')
cat=event['details']['category']; event['details']['selected_ids']=['fictional-not-in-request']
coverage[cat]['retrieval']['selected_ids']=['fictional-not-in-request']
prior=None
for e in trace:
    e.pop('sha256',None); e['previous_sha256']=prior; e['sha256']=prior=fingerprint(e)
changed=replace(result,trace=trace,coverage=coverage)
digest=write_run(root/'run',changed,store,model)
try:
    out=verify_engine(root/'run',digest); status='ACCEPTED_CONTRADICTORY_RETRIEVAL'
except Exception as e:
    status=type(e).__name__+': '+str(e)
print(json.dumps({'probe':status,'category':cat,'retained_run':str(root)}))
