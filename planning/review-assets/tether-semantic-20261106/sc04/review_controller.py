"""Independent stdlib reconstruction of the fictional SC04 controller trial.

Does not import experiment code or evaluate real benchmark keys. This is an
operational qualification, not the later independent scientific analysis.
"""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[4]
PHASES=('expand','collect','rank','answer')
CHECKS=0


def need(value,message):
    global CHECKS
    CHECKS+=1
    if not value:raise ValueError(message)


def canon(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())


def proof(value):
    path=Path(value['path']);raw=path.read_bytes()
    need(len(raw)==value['bytes'] and sha(raw)==value['sha256'],'Byte proof '+str(path))
    return raw


def chain(path):
    raw=Path(path).read_bytes();need(raw.endswith(b'\n'),'Complete journal tail')
    events=[];previous=None
    for i,line in enumerate(raw.splitlines()):
        event=json.loads(line);digest=event.pop('sha256')
        need(event['sequence']==i and event['previous_sha256']==previous and sha(canon(event))==digest,'Journal chain '+str(path))
        previous=digest;event['sha256']=digest;events.append(event)
    return events


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--root-sha256',required=True);parser.add_argument('--frame-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    root=args.root.resolve();resource={};calls=Counter();usage=Counter();semantic=[];checks_by_phase={}
    try:
        raw=(root/'ROOT-RECEIPT.json').read_bytes();need(sha(raw)==args.root_sha256,'External root anchor')
        receipt=json.loads(raw);need(receipt['frame_sha256']==args.frame_sha256,'Root/frame binding')
        need(set(receipt['files'])=={p.name for p in root.iterdir() if p.is_file() and p.name!='ROOT-RECEIPT.json'},'Exact root files')
        for name,item in receipt['files'].items():
            need(Path(item['path'])==root/name,'Root proof path');proof(item)
        frame=read(root/'FRAME.json')
        need(sha((root/'FRAME.json').read_bytes())==args.frame_sha256,'Archived frame bytes')
        need(frame['purpose']=='fictional_qualification' and frame['count']==2,'Fictional-only review')
        need(frame['automatic_retry'] is False and frame['provider_spend_usd']==0,'No retry/provider spending')
        source=json.loads(proof(frame['query_products']['source_queries']));answer=json.loads(proof(frame['query_products']['answer_queries']))
        need(source==[dict(id=q['id'],question=q['question']) for q in answer],'Task role projection')
        questions={q['id']:q for q in source};answers={q['id']:q for q in answer}
        completed=read(root/'COMPLETE.json')
        need(completed['sc04_complete'] is False and completed['supplied_source_complete'] is False,'Scope remains incomplete')
        rows={};native_cells={};collections={}
        for phase in PHASES:
            before=CHECKS;p=root/phase;anchor=completed['phases'][phase]
            need(read(root/(phase+'-ANCHOR.json'))==anchor and Path(anchor['root'])==p,'Phase anchor binding')
            package=(p/'PACKAGE-RECEIPT.json').read_bytes();need(sha(package)==anchor['package_sha256'],'Phase package anchor')
            inventory=json.loads(package)
            need(inventory['phase']==phase and inventory['frame_sha256']==args.frame_sha256,'Package context')
            actual={f.relative_to(p).as_posix() for f in p.rglob('*') if f.is_file() and f!=p/'PACKAGE-RECEIPT.json'}
            need(set(inventory['files'])==actual,'Exact phase inventory')
            for name,item in inventory['files'].items():
                need(Path(item['path'])==p/name,'Package proof path');proof(item)
            for journal in p.rglob('journal.jsonl'):chain(journal)
            events=chain(p/'journal.jsonl')
            need([e['event'] for e in events]==['build_reserved','phase_worker_dispatch','phase_replay_dispatch','phase_package_verified'],'Exact phase events')
            for label in ('execution','review'):
                supervision=read(p/(label+'-SUPERVISION.json'));s=supervision['supervision']
                need(supervision['returncode']==0 and s['termination_reason']=='exited' and s['process_reaped'] and
                     all(s['pipe_eof'].values()) and not s['cleanup_errors'],'Successful supervised child')
                need(s['total_elapsed_seconds']<=s['limits']['timeout_seconds']+5,'Child deadline')
                for stream in ('stdout','stderr'):
                    need(len((p/(label+'-'+stream+'.txt')).read_bytes())==s['retained_'+stream+'_bytes']==s['observed_'+stream+'_bytes'],'Captured child output')
            worker=read(p/'worker/COMPLETE.json');review=read(p/'REPLAY.json')
            need(worker['audit_denials']==0 and worker['benchmark_questions']==0,'Fictional audited worker')
            need(review['status']=='verified' and review['stage_receipt_sha256']==anchor['stage_receipt_sha256'],'Replay anchor')
            need(sha((p/'worker/phase/STAGE-RECEIPT.json').read_bytes())==anchor['stage_receipt_sha256'],'Stage anchor')
            forbidden=frame['query_products']['answer_queries']['path'].casefold()
            for event in (json.loads(line) for line in (p/'worker/io-audit.jsonl').read_bytes().splitlines()):
                need(event['allowed'],'No denied file access')
                if phase!='answer':need((event['path'] or '').casefold()!=forbidden,'No answer choices in source/ranker worker')
            report=read(p/'worker/phase/REPORT.json');rows[phase]=report['rows']
            branches=('shared',) if phase=='expand' else ('L','E') if phase in ('collect','rank') else ('L/O','E/O','L/R','E/R')
            need(report['status']=='complete' and Counter((r['id'],r['branch']) for r in report['rows'])==
                 Counter((q['id'],b) for q in source for b in branches),'Full scheduled cohort')
            need(all(r['status']=='completed' for r in report['rows']),'Qualification slots all completed')
            resource[phase]=dict(worker_wall_seconds=worker['wall_seconds'],worker_memory=worker['worker_memory'],
                                 execution_supervision=read(p/'execution-SUPERVISION.json')['supervision']['total_elapsed_seconds'])
            if phase!='collect':
                need(worker['server_terminal']['server_stopped'],'Owned server stopped')
                samples=read(p/'worker/SERVER-RESOURCE-SAMPLES.json')
                values=[x['value'] for x in samples if x['value'] is not None]
                resource[phase]['server_peak_working_set_bytes']=max(v['process_peak_working_set_bytes'] for v in values)
                resource[phase]['server_cpu_seconds_observed']=max(v['cpu_seconds'] for v in values)
            for row in report['rows']:
                cell=p/'worker/phase/products'/f'{row["ordinal"]:04d}'
                if phase=='collect':
                    manifest=read(cell/'MANIFEST.json');collections[(row['id'],row['branch'])]=manifest
                    need(manifest['plan']['question']==questions[row['id']],'Collection question-only identity')
                    need(len(manifest['requests'])==3,'Two invented metadata and one article responses')
                    for request in manifest['requests']:
                        original=read(cell/request['receipt_path'])
                        need(original['headers']['X-TETHER-Fixture']=='invented-no-http-dispatch','Explicit synthetic HTTP marker')
                        need(sha((cell/request['body_path']).read_bytes())==request['body_sha256'],'Original response bytes')
                    article=manifest['sources'][0];tree=ET.fromstring((cell/article['original']['path']).read_bytes())
                    texts=[' '.join(''.join(p.itertext()).split()) for p in tree.findall('.//body//p')]
                    need(texts==[s['text'] for s in article['spans']],'Original XML paragraph reconstruction')
                    for passage in manifest['pool']['pool']:
                        need(passage['text'] in texts and sha(passage['text'].encode())==passage['sha256'],'Pool is raw source text')
                    continue
                calls[phase]+=1
                inp=read(cell/'INPUT.json');summary=read(cell/'SUMMARY.json');payload=read(cell/'native/payload.json')
                request=read(cell/'native/request.json');wrapper=read(cell/'native/native-response.bin')
                body=base64.b64decode(wrapper['body_base64'],validate=True);native=json.loads(body)
                tokens=read(cell/'native/tokenization/body.bin')['tokens'];decoded=json.loads(native['content'])
                need(inp['query']==(answers if phase=='answer' else questions)[row['id']],'Exact role task to model')
                need(wrapper['body_sha256']==sha(body) and wrapper['payload_sha256']==sha(canon(payload)) and
                     wrapper['request_sha256']==sha(canon(request)),'Native wrapper request binding')
                need(wrapper['owner_pid']==worker['server_terminal']['pid'] and wrapper['http_status']==200 and wrapper['complete'],'Owned native response')
                need(native['prompt']==payload['prompt'] and not native['truncated'] and native['stop'] and native['stop_type'] in ('eos','word'),'Complete exact prompt')
                need(native['model']==frame['alias'] and native['generation_settings']['n_predict']==256 and
                     native['generation_settings']['temperature']==0 and native['generation_settings']['seed']==20261106,'Native frozen generation')
                need(native['tokens_evaluated']==len(tokens)==summary['usage']['input_tokens'] and
                     native['tokens_predicted']==summary['usage']['output_tokens']<=256,'Native measured usage')
                need(summary['decoded']==(decoded['order'] if phase=='rank' else decoded),'Native output decoding')
                need(summary['status']=='completed' and summary['provider_cost_usd']==summary['usage']['cost_usd']==0,'No hidden call failure or cost')
                usage.update({k:summary['usage'][k] for k in ('input_tokens','output_tokens')})
                native_cells[(phase,row['id'],row['branch'])]=dict(inp=inp,decoded=summary['decoded'])
                if phase=='rank':
                    manifest=collections[(row['id'],row['branch'])]
                    need(inp['items']==manifest['pool']['pool'],'Ranker exact source pool')
                    need(set(decoded['order'])=={x['rank_id'] for x in inp['items']} and len(decoded['order'])==len(inp['items']),'Permutation-only ranking')
                if phase=='answer':
                    manifest=collections[(row['id'],row['branch'][0])];pool=manifest['pool']['pool']
                    order=native_cells[('rank',row['id'],row['branch'][0])]['decoded'] if row['branch'].endswith('/R') else [x['rank_id'] for x in pool]
                    by_id={x['rank_id']:x for x in pool}
                    need(inp['items']==[{k:by_id[i][k] for k in ('source_id','text','sha256')} for i in order],'Answer selected raw source order')
                    expected=0 if row['id'].endswith('901') else 2
                    semantic.append(dict(id=row['id'],arm=row['branch'],expected=expected,actual=decoded['answer_index'],match=decoded['answer_index']==expected))
                    need(set(decoded['evidence_ids'])<={s['source_id'] for s in inp['items']} and bool(decoded['evidence_ids']),'Offered cited evidence')
            checks_by_phase[phase]=CHECKS-before
        need(calls==dict(expand=2,rank=4,answer=8),'Exactly14 physical model calls')
        events=chain(root/'journal.jsonl')
        need([e['event'] for e in events]==['build_reserved']+sum((['phase_started','phase_accepted'] for _ in PHASES),[])+
             ['primary_comparison_executed','primary_report_sealed'],'Exact coordinator events')
        semantic_matches=sum(x['match'] for x in semantic)
        report=dict(status='TECHNICAL_PASS' if semantic_matches==len(semantic) else 'TECHNICAL_PASS_WITH_SEMANTIC_FAILURES',
            semantic_status='all_fixture_answers_match' if semantic_matches==len(semantic) else 'partial_failure',
            semantic_matches=semantic_matches,semantic_total=len(semantic),
            distinct_questions=2,checks=CHECKS,checks_by_phase=checks_by_phase,calls=dict(calls),measured_usage=dict(usage),
            resources=resource,fictional_answer_controls=semantic,root_sha256=args.root_sha256,frame_sha256=args.frame_sha256,
            reviewer_sha256=sha(Path(__file__).read_bytes()),benchmark_questions=0,provider_cost_usd=0,
            limitations=['Fictional sources are not real literature.','Two-passage pools do not test long-context ranking quality.',
                        'This reviewer checks controller/source/native consistency; production metrics require separate independent analysis.'])
        (args.output/'REVIEW.json').write_bytes(canon(report)+b'\n')
        print(json.dumps({k:report[k] for k in ('status','checks','calls','measured_usage')}))
    except BaseException as error:
        (args.output/'FAILURE.json').write_bytes(canon(dict(status='FAIL',checks=CHECKS,error_type=type(error).__name__,message=str(error)))+b'\n')
        raise


if __name__=='__main__':main()
