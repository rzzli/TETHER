"""Independent stdlib reconstruction of the 13-call fictional qualification.

No production imports and no inference. Verifies transport byte bindings and
declared fictional outcomes; it does not certify literature-answer accuracy.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
RECIPE_SHA='5a5392c76885b3f801dccc2cc1b84707f6f700d1bbceaa480624d2ca8187bf5b'


def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fp(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    checks=0;report=dict(status='FAIL')
    def check(ok,why):
        nonlocal checks
        checks+=1
        if not ok:raise ValueError(why)
    def journal(p):
        rows=[json.loads(x) for x in p.read_bytes().splitlines()];previous=None
        for i,event in enumerate(rows):
            check(event['sequence']==i and event['previous_sha256']==previous,'Journal order/hash parent')
            check(fp({k:v for k,v in event.items() if k!='sha256'})==event['sha256'],'Journal hash')
            previous=event['sha256']
        return rows
    try:
        recipe_path=ROOT/'planning/review-assets/tether-semantic-20261106/sc04/model-qualification-freeze02/RECIPE.json'
        check(sha(recipe_path)==RECIPE_SHA,'Recipe anchor')
        recipe=read(recipe_path)
        for name,digest in recipe['code_pins'].items():check(sha(ROOT/name)==digest,'Changed source: '+name)
        root=ROOT/'data/cache/sc04-model-qualification-attempt02';worker=root/'worker'
        done=read(root/'COMPLETE.json');terminal=read(worker/'COMPLETE.json');summary=read(worker/'REPORT.json')
        check(done['status']=='completed' and done['recipe_sha256']==RECIPE_SHA and done['worker_complete_sha256']==sha(worker/'COMPLETE.json'),'Parent completion')
        check(terminal['report_sha256']==sha(worker/'REPORT.json'),'Worker report binding')
        outer=journal(root/'journal.jsonl');events=journal(worker/'journal.jsonl')
        check([e['event'] for e in outer]==['build_reserved','worker_dispatch','qualification_parent_completed'],'Exact parent events')
        call_events=['structured_call_reserved','mcq_tokenize_attempt','mcq_tokenize_terminal','structured_generation_attempt','structured_call_completed']
        check([e['event'] for e in events]==['build_reserved','server_started','server_ready']+call_events*13+['server_terminal','qualification_completed'],'Exact worker event inventory')
        check(terminal['journal_terminal_sha256']==events[-1]['sha256'],'Terminal journal binding')
        supervision=read(root/'SUPERVISION.json')
        check(supervision['returncode']==0 and supervision['supervision']['process_reaped'] and
              supervision['supervision']['termination_reason']=='exited' and not supervision['supervision']['cleanup_errors'],'Supervised normal termination')
        model=read(worker/'MODEL.json');owner=summary['server_terminal']['pid']
        check(summary['server_terminal']['server_stopped'] and not summary['server_terminal']['secondary_failures'],'Owned server stopped')
        check(summary['fixtures']==len(recipe['fixtures'])==recipe['max_generation_calls']==13,'Full declared fixture schedule')
        results=[];tokens_in=tokens_out=0
        for i,fixture in enumerate(recipe['fixtures']):
            cell=worker/f'fixture-{i:02d}'
            request,payload,result=read(cell/'request.json'),read(cell/'payload.json'),read(cell/'result.json')
            raw=read(cell/'native-response.bin');quote=read(cell/'tokenization/result.json')
            check(request['query']==fixture['query'] and request['task']==fixture['task'],'Fixture task identity')
            check(request['model_provenance']==model['provenance'],'Actual model binding')
            check(request['payload_sha256']==fp(payload)==raw['payload_sha256']==quote['payload_sha256'] and raw['request_sha256']==fp(request),'Request/payload chain')
            check(raw['owner_pid']==quote['owner_pid']==owner and raw['endpoint']==quote['endpoint'],'Native owner binding')
            body=base64.b64decode(raw['body_base64'],validate=True)
            check(hashlib.sha256(body).hexdigest()==raw['body_sha256'] and raw['http_status']==200 and raw['complete'] and raw['error_class'] is None,'Complete native bytes')
            native=json.loads(body)
            check(native['prompt']==payload['prompt'] and native['model']=='tether-sc04-fictional-qwen14b-v1','Native echoed prompt/model')
            for key in ('seed','temperature','n_predict','stop','stream','grammar','cache_prompt'):
                check(key not in native['generation_settings'] or native['generation_settings'][key]==payload[key],'Native setting '+key)
            check(native['stopped_eos'] or native['stopped_word'],'Native terminal stop')
            check(not native['truncated'] and not native['stopped_limit'],'No truncated/limit-stopped answer')
            token_body=base64.b64decode(quote['body_base64'],validate=True)
            check(hashlib.sha256(token_body).hexdigest()==quote['body_sha256'] and token_body==(cell/'tokenization/body.bin').read_bytes(),'Exact tokenizer bytes')
            count=len(json.loads(token_body)['tokens'])
            check(count==native['tokens_evaluated']==quote['token_count']==result['measured_usage']['input_tokens'],'Input token accounting')
            check(native['tokens_predicted']==result['measured_usage']['output_tokens']<=256 and result['measured_usage']['cost_usd']==0,'Output/provider accounting')
            tokens_in+=count;tokens_out+=native['tokens_predicted']
            answer=json.loads(native['content'])
            if fixture['task']=='expand':
                decoded=answer
                check(set(answer)=={'queries'} and len(answer['queries'])==2,'Expansion shape')
                terms={term.casefold() for group in answer['queries'] for term in group}
                matched=all(t in terms for t in fixture['expected_terms'])
            elif fixture['task']=='rank':
                decoded=answer['order'];ids=[p['rank_id'] for p in fixture['pool']]
                check(set(answer)=={'order'} and len(decoded)==len(ids) and set(decoded)==set(ids),'Complete ranking permutation')
                check(request['pool']==fixture['pool'],'Raw ranker pool unchanged')
                matched=decoded[0]==fixture['expected_first']
            else:
                decoded=answer
                check(set(answer)=={'answer_index','evidence_ids'} and type(answer['answer_index']) is int and
                      0<=answer['answer_index']<len(fixture['query']['choices']),'Native answer contract')
                check(len(set(answer['evidence_ids']))==len(answer['evidence_ids']) and
                      set(answer['evidence_ids'])<={s['source_id'] for s in fixture['sources']},'Offered evidence IDs only')
                check(request['sources']==fixture['sources'],'Raw answer sources unchanged')
                matched=answer['answer_index']==fixture['expected_index']
            check(decoded==result['decoded'] and result['status']=='completed','Decoded result')
            recorded=read(worker/f'fixture-{i:02d}-summary.json')
            check(recorded==summary['results'][i] and recorded['semantic_fixture_match']==matched,'Independent fictional outcome')
            ev=events[3+5*i:8+5*i]
            check(ev[0]['details']['request_sha256']==fp(request)==ev[3]['details']['request_sha256']==ev[4]['details']['request_sha256'],'Exact call journal binding')
            check(ev[4]['details']['result_sha256']==fp(result),'Journal result binding')
            results.append(dict(index=i,task=fixture['task'],semantic_match=matched,decoded=decoded))
        check(sum(r['semantic_match'] for r in results)==summary['semantic_fixtures_passed']==11,'All outcomes including two failures')
        report.update(status='PASS',scope='Independent byte/native/fictional-outcome reconstruction; known semantic failures retained.',
            model_accuracy_claim=False,production_modules_imported=False,results=results,
            semantic_matches=11,fixtures=13,input_tokens=tokens_in,output_tokens=tokens_out,
            worker_wall_seconds=summary['wall_seconds'],recipe_sha256=RECIPE_SHA,
            original_file_hashes={str(p.relative_to(root)).replace('\\','/'):sha(p) for p in root.rglob('*') if p.is_file()},
            source_pins=recipe['code_pins'],provider_cost_usd=0)
    except BaseException as error:report.update(error_type=type(error).__name__,error=str(error))
    report.update(checks=checks,reviewer_sha256=sha(__file__))
    (args.output/'REVIEW.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k in ('status','checks','error','fixtures','semantic_matches','input_tokens','output_tokens')}))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
