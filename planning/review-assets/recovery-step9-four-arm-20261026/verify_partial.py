"""Read-only verification of accepted cells in the failed first attempt."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from asof.journal import read_chain
from asof.serde import encode
from asof.study.authority_four_arm import AuthorityRecordedVerifier
from asof.study.session import verify_study

HERE=Path(__file__).resolve().parent
failure=json.loads((HERE/'QUALIFICATION-FAILURE-v1.json').read_bytes())
root=Path(failure['output'])
assert failure['status']=='failed' and failure['tokenizer_children']==2 and failure['generation_calls']==0
assert not (root/'receipt.json').exists()
events=read_chain(root/'journal.jsonl')
assert events[-1]['event']=='build_failed'
accepted=[e['details'] for e in events if e['event']=='cell_accepted']
assert [e['cell'] for e in accepted]==[0,1]
observed_children=[p for p in (root/'quotes').glob('*/child.json')
                   if json.loads(p.read_bytes())['started']]
assert len(observed_children)==2


def guard(event,args):
    if event in ('subprocess.Popen','os.system','socket.connect','socket.getaddrinfo'):
        raise RuntimeError('Partial replay cannot dispatch')
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if path.startswith('e:') or '\\data\\benchmark\\' in path:
            raise RuntimeError('Partial replay uses no original model assets or outcomes')


sys.addaudithook(guard)
started=time.monotonic()
verifier=AuthorityRecordedVerifier(root,events[0]['details']['run_id'],deadline=started+299)
records=[]
for event in accepted:
    cell=event['cell']
    stage=verifier.stage(cell)
    payload=verifier.payload(stage)
    policy=verifier.capacity(cell,payload)
    result=verify_study(root/'cells'/f'{cell:02d}',expected_receipt_sha256=event['receipt_sha256'],
        verifier=verifier,capacity_policy=policy,deadline=started+299)
    quote=json.loads((root/'quotes'/f'{cell:02d}'/'quote.json').read_bytes())
    records.append(dict(cell=cell,receipt_sha256=event['receipt_sha256'],verification=encode(result),
        token_count=quote['token_count'],reserved_input=quote['input_reservation'],
        quotation_seconds=quote['elapsed_seconds'],tokenizer_child_seconds=quote['child']['elapsed_seconds']))
report=dict(schema_version=1,status='verified_partial_cells_not_completed_case',
    failed_attempt=str(root),whole_case_accepted=False,accepted_cells=records,
    prior_tokenizer_children=2,new_tokenizer_children=0,actual_model_calls=0,provider_spend_usd=0,
    elapsed_seconds=time.monotonic()-started,
    failure_report_sha256=hashlib.sha256((HERE/'QUALIFICATION-FAILURE-v1.json').read_bytes()).hexdigest(),
    scientific_validation='not_established')
with (HERE/'QUALIFICATION-FAILURE-CLOSEOUT-v1.json').open('x',encoding='utf-8') as stream:
    json.dump(report,stream,indent=2)
print(json.dumps(dict(status=report['status'],accepted_cells=2,elapsed_seconds=report['elapsed_seconds'])))
