"""Independent stdlib review of the fictional supplied-paper controller trial."""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import runpy
import xml.etree.ElementTree as ET

HELPER=Path(__file__).with_name('review_controller.py')
review=runpy.run_path(str(HELPER))
need=review['need'];canon=review['canon'];sha=review['sha'];read=review['read'];proof=review['proof'];chain=review['chain']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--root-sha256',required=True)
    parser.add_argument('--frame-sha256',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);root=args.root.resolve();usage=Counter();semantic=[];resources={}
    try:
        need(sha((root/'ROOT-RECEIPT.json').read_bytes())==args.root_sha256,'Diagnostic external root anchor')
        receipt=read(root/'ROOT-RECEIPT.json');need(receipt['frame_sha256']==args.frame_sha256,'Diagnostic frame anchor')
        need(set(receipt['files'])=={p.name for p in root.iterdir() if p.is_file() and p.name!='ROOT-RECEIPT.json'},'Exact diagnostic root files')
        for name,item in receipt['files'].items():need(Path(item['path'])==root/name,'Root path');proof(item)
        frame=read(root/'FRAME.json');need(sha((root/'FRAME.json').read_bytes())==args.frame_sha256,'Copied frame bytes')
        need(frame['purpose']=='fictional_qualification' and frame['questions']==2 and frame['unique_dois']==1 and not frame['ordinary_retrieval'],'Only declared fictional diagnostic')
        inputs={key:json.loads(proof(value)) for key,value in frame['products'].items()}
        questions={q['id']:q for q in inputs['answer_queries']};hints={h['id']:h for h in inputs['hints']}
        need(len(questions)==len(hints)==2 and inputs['doi_schedule']==['10.1234/invented'],'Fictional input roles/cohort')
        complete=read(root/'COMPLETE.json');need(not complete['sc04_complete'] and not complete['scientific_scoring_performed'],'No scientific completion claim')
        chain(root/'journal.jsonl');source=None;source_cells={}
        for phase in ('collect','answer'):
            p=root/phase;anchor=complete['phases'][phase];raw=(p/'PACKAGE-RECEIPT.json').read_bytes()
            need(sha(raw)==anchor['package_sha256'] and Path(anchor['root'])==p,'Phase anchor')
            package=json.loads(raw);need(package['phase']==phase and package['frame_sha256']==args.frame_sha256,'Phase context')
            need(set(package['files'])=={f.relative_to(p).as_posix() for f in p.rglob('*') if f.is_file() and f!=p/'PACKAGE-RECEIPT.json'},'Exact phase file inventory')
            for name,item in package['files'].items():need(Path(item['path'])==p/name,'Phase proof path');proof(item)
            for journal in p.rglob('journal.jsonl'):chain(journal)
            need([e['event'] for e in chain(p/'journal.jsonl')]==['build_reserved','diagnostic_worker_dispatch','diagnostic_replay_dispatch','diagnostic_phase_verified'],'Exact controller phase events')
            for label in ('execution','review'):
                supervision=read(p/(label+'-SUPERVISION.json'));s=supervision['supervision']
                need(supervision['returncode']==0 and s['process_reaped'] and s['termination_reason']=='exited' and
                     all(s['pipe_eof'].values()) and not s['cleanup_errors'],'Bounded child successful')
                need(s['total_elapsed_seconds']<=s['limits']['timeout_seconds']+5,'Observed child deadline')
            worker=read(p/'worker/COMPLETE.json');maintained=read(p/'REPLAY.json')
            need(worker['status']=='complete' and worker['audit_denials']==0 and worker['purpose']=='fictional_qualification','Worker disposition')
            need(maintained['status']=='verified' and maintained['stage_receipt_sha256']==anchor['stage_receipt_sha256'],'Maintained replay anchor')
            need(sha((p/'worker/phase/STAGE-RECEIPT.json').read_bytes())==anchor['stage_receipt_sha256'],'Stage byte anchor')
            forbidden=frame['products']['answer_queries']['path'].casefold()
            for event in map(json.loads,(p/'worker/io-audit.jsonl').read_bytes().splitlines()):
                need(event['allowed'],'No denied runtime data access')
                if phase=='collect':need((event['path'] or '').casefold()!=forbidden,'Resolver does not read answer options')
            rows=read(p/'worker/phase/REPORT.json')['rows']
            need(len(rows)==(1 if phase=='collect' else 2) and all(r['status']=='completed' for r in rows),'Full diagnostic schedule')
            resources[phase]=dict(worker_wall_seconds=worker['worker_wall_seconds'],worker_memory=worker['worker_memory'])
            for row in rows:
                cell=p/'worker/phase/products'/f'{row["ordinal"]:04d}'
                if phase=='collect':
                    source=read(cell/'MANIFEST.json');source_cells[row['id']]=cell
                    need(source['plan']['doi']==row['id']=='10.1234/invented' and not source['plan']['ordinary_retrieval'],'Exact privileged DOI')
                    need(len(source['requests'])==2 and source['coverage']['article_retained'],'Metadata plus fulltext fixture')
                    for request in source['requests']:
                        record=read(cell/request['receipt_path']);body=(cell/request['body_path']).read_bytes()
                        need(record['headers']['X-TETHER-Fixture']=='invented-no-http-dispatch','Synthetic HTTP declaration')
                        need(sha(body)==request['body_sha256']==record['sha256'] and record['requested_doi']==row['id'] and
                             record['selection_role']=='supplied_source_diagnostic','Original capture/provenance role')
                    xml=(cell/source['source']['original']['path']).read_bytes();tree=ET.fromstring(xml)
                    need([' '.join(' '.join(n.itertext()).split()) for n in tree.findall('.//body//p')]==
                         [s['text'] for s in source['source']['spans']],'Original XML paragraphs')
                    continue
                context=read(cell/'CONTEXT.json');inp=read(cell/'INPUT.json');summary=read(cell/'SUMMARY.json')
                need(context['diagnostic_only'] and not context['ordinary_retrieval'] and context['selection_uses_reference_paper_identity'],'Declared privileged context')
                need(context['hint_sha256']==sha(canon(hints[row['id']])) and inp['query']==questions[row['id']],'Hint and answer question binding')
                need(len(context['source_proofs'])==3,'Both original responses and derived manifest proved')
                for item in context['source_proofs']:need(sha(Path(item['path']).read_bytes())==item['sha256'],'Source lineage file hash')
                for passage in inp['items']:
                    need(passage['text'] in [s['text'] for s in source['source']['spans']] and sha(passage['text'].encode())==passage['sha256'],'Offered raw paragraph')
                wrapper=read(cell/'native/native-response.bin');body=base64.b64decode(wrapper['body_base64'],validate=True);native=json.loads(body)
                payload=read(cell/'native/payload.json');request=read(cell/'native/request.json');decoded=json.loads(native['content'])
                need(sha(body)==wrapper['body_sha256'] and sha(canon(payload))==wrapper['payload_sha256'] and
                     sha(canon(request))==wrapper['request_sha256'],'Native exact request')
                need(native['prompt']==payload['prompt'] and native['stop'] and native['stop_type'] in ('eos','word') and not native['truncated'],'Complete native prompt/response')
                need(native['model']==frame['model']['alias'] and wrapper['owner_pid']==worker['server_terminal']['pid'],'Owned native model')
                need(native['tokens_evaluated']==len(read(cell/'native/tokenization/body.bin')['tokens'])==summary['usage']['input_tokens'] and
                     native['tokens_predicted']==summary['usage']['output_tokens']<=256,'Measured native token usage')
                need(decoded==summary['decoded'] and summary['status']=='completed' and summary['usage']['cost_usd']==0,'Native decoding/no hidden failure')
                need(set(decoded['evidence_ids'])<={s['source_id'] for s in inp['items']},'No invented citation ID')
                expected=0 if row['id'].endswith('901') else 2
                semantic.append(dict(id=row['id'],expected=expected,actual=decoded['answer_index'],match=decoded['answer_index']==expected))
                usage.update({k:summary['usage'][k] for k in ('input_tokens','output_tokens')})
            if phase=='answer':
                need(worker['server_terminal']['server_stopped'],'Owned model stopped')
                samples=[x['value'] for x in read(p/'worker/SERVER-RESOURCE-SAMPLES.json') if x['value'] is not None]
                resources[phase]['server_peak_working_set_bytes']=max(x['process_peak_working_set_bytes'] for x in samples)
                resources[phase]['server_cpu_seconds_observed']=max(x['cpu_seconds'] for x in samples)
        report=dict(status='TECHNICAL_PASS' if all(x['match'] for x in semantic) else 'TECHNICAL_PASS_WITH_SEMANTIC_FAILURES',
            checks=need.__globals__['CHECKS'],model_calls=2,semantic_matches=sum(x['match'] for x in semantic),semantic_total=2,
            outcomes=semantic,measured_usage=dict(usage),resources=resources,root_sha256=args.root_sha256,frame_sha256=args.frame_sha256,
            benchmark_questions=0,provider_cost_usd=0,reviewer_sha256=sha(Path(__file__).read_bytes()),helper_sha256=sha(HELPER.read_bytes()),
            limitations=['Fictional paper and questions only.','Technical acceptance does not erase semantic failures.','Production requires a separate complete primary parent and scientific scoring.'])
        (args.output/'REVIEW.json').write_bytes(canon(report)+b'\n')
        print(json.dumps({k:report[k] for k in ('status','checks','model_calls','semantic_matches','measured_usage')}))
    except BaseException as error:
        (args.output/'FAILURE.json').write_bytes(canon(dict(status='FAIL',checks=need.__globals__['CHECKS'],error_type=type(error).__name__,message=str(error)))+b'\n');raise


if __name__=='__main__':main()
