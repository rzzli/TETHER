"""Supplemental exact-event-coverage gate, independent of the production auditor.

The production auditor checks every expected commit but does not exclude every
possible extra terminal event. This gate closes that gap without changing the
frozen producer or analysis source while inference runs.
"""
import hashlib
import json
import math
from pathlib import Path
import unittest


def expect(condition,message):
    if not condition:
        raise ValueError(message)


def verify_order(journal_events, requests, pairs):
    expected = [('inputs_admitted',None,None)]
    for request in requests:
        cid = request['id']
        expected.append(('claim_started',cid,None))
        for doc in request['documents']:
            did = doc['doc_id']
            record = pairs[(cid,did)]
            if record['status']=='input_unavailable':
                expected.append(('pair_unavailable',cid,did))
            else:
                expected.append(('pair_started',cid,did))
                expected.append(('pair_completed' if record['status']=='completed' else 'pair_failed',cid,did))
            expected.append(('pair_committed',cid,did))
        expected.append(('claim_committed',cid,None))
    expected.append(('condition_completed',None,None))
    observed = [(e['event'],e['details'].get('claim_id'),e['details'].get('abstract_id')) for e in journal_events]
    expect(observed==expected,'Unexpected, contradictory, duplicate, missing or reordered journal event')
    return len(expected)


def verify_signals(signals,requests,claims,supervisor):
    expected = [('started',None),('model_load_started',None),('models_loaded',None)]
    for request in requests:
        expected += [('case_started',str(request['id'])),('case_completed',str(request['id']))]
    expected += [('completed',None)]
    expect([(e['event'],e.get('case_id')) for e in signals]==expected,'Supervisor signal inventory/order differs')
    stamps = [e['monotonic_seconds'] for e in signals]
    expect(all(type(x) in (float,int) and math.isfinite(x) for x in stamps) and stamps==sorted(stamps),'Signal clocks differ')
    expect(stamps[-1]-stamps[0]<=1800,'Signal whole-process interval exceeds cap')
    expect(len(signals)==supervisor['events_observed'],'Observed supervisor count differs')
    expect(supervisor['cases']==[dict(case_id=str(r['id']),status='completed') for r in requests],'Supervisor case coverage differs')
    expect(signals[-1]['status']=='passed','Signal terminal status differs')
    for i,request in enumerate(requests):
        start,finish = signals[3+2*i:5+2*i]
        expect(finish['monotonic_seconds']-start['monotonic_seconds']<=120,'Claim interval exceeds cap')
        expect(finish['prediction_status']==claims[request['id']]['status'],'Signal prediction status differs from committed claim')


class EventControls(unittest.TestCase):
    def setUp(self):
        self.requests=[dict(id=1,documents=[dict(doc_id=2)])]
        self.pairs={(1,2):dict(status='completed')}
        order=[('inputs_admitted',{}),('claim_started',dict(claim_id=1)),
               ('pair_started',dict(claim_id=1,abstract_id=2)),('pair_completed',dict(claim_id=1,abstract_id=2)),
               ('pair_committed',dict(claim_id=1,abstract_id=2)),('claim_committed',dict(claim_id=1)),
               ('condition_completed',{})]
        self.events=[dict(event=k,details=v) for k,v in order]

    def test_expected(self):
        self.assertEqual(verify_order(self.events,self.requests,self.pairs),7)

    def test_contradictory_extra_terminal(self):
        self.events.insert(4,dict(event='pair_failed',details=dict(claim_id=1,abstract_id=2)))
        with self.assertRaises(ValueError): verify_order(self.events,self.requests,self.pairs)

    def test_unexpected_claim(self):
        self.events.insert(1,dict(event='claim_started',details=dict(claim_id=99)))
        with self.assertRaises(ValueError): verify_order(self.events,self.requests,self.pairs)

    def test_completed_before_dispatch(self):
        self.events[2],self.events[3]=self.events[3],self.events[2]
        with self.assertRaises(ValueError): verify_order(self.events,self.requests,self.pairs)

    def test_missing_terminal(self):
        self.events.pop()
        with self.assertRaises(ValueError): verify_order(self.events,self.requests,self.pairs)


def run(frame_path,anchors_path,output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    stream=__import__('io').StringIO()
    controls=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(EventControls))
    (output/'TEST-RESULTS.txt').write_text(stream.getvalue(),encoding='utf-8',newline='\n')
    report=dict(status='FAIL',tests=controls.testsRun,failures=len(controls.failures),errors=len(controls.errors))
    try:
        expect(controls.wasSuccessful(),'Supplemental event controls failed')
        frame=json.loads(Path(frame_path).read_bytes())
        anchors=json.loads(Path(anchors_path).read_bytes())
        prepared=json.loads(Path(frame['prepared']['path']).read_bytes())
        conditions={}
        hashes={}
        for name in frame['condition_order']:
            manifest=json.loads(Path(frame['conditions'][name]['path']).read_bytes())
            root=Path(manifest['qualification_output'])
            requests=[json.loads(line) for line in Path(prepared['conditions'][name]['requests']['path']).read_bytes().splitlines()]
            journal=[json.loads(line) for line in (root/'journal.jsonl').read_bytes().splitlines()]
            pairs={(r['id'],d['doc_id']):json.loads((root/f'pairs/{r["id"]}-{d["doc_id"]}.json').read_bytes()) for r in requests for d in r['documents']}
            claims={r['id']:json.loads((root/f'claims/{r["id"]}.json').read_bytes()) for r in requests}
            signals=[json.loads(line) for line in (root/'events.jsonl').read_bytes().splitlines()]
            supervisor=json.loads(Path(anchors['conditions'][name]['supervisor_outcome']['path']).read_bytes())
            count=verify_order(journal,requests,pairs)
            verify_signals(signals,requests,claims,supervisor)
            for tree in (root,Path(manifest['launch_output'])):
                for path in tree.rglob('*'):
                    if path.is_file():
                        with path.open('rb') as handle:
                            hashes[str(path.resolve())]=hashlib.file_digest(handle,'sha256').hexdigest()
            conditions[name]=dict(journal_events=count,supervisor_signals=len(signals),claims=len(claims),pairs=len(pairs))
        report.update(status='PASS',conditions=conditions,observed_file_hashes=hashes,
            scope='Supplemental exact event coverage and post-execution byte inventory; not continuous host attestation.')
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error))
    report['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (output/'STRICT-EVENT-REVIEW.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k!='observed_file_hashes'}))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--frame',required=True)
    parser.add_argument('--anchors',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    raise SystemExit(run(args.frame,args.anchors,args.output))
