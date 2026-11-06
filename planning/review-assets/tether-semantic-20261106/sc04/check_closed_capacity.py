"""Bounded read-only format/capacity check of closed SC04 collection products.

Reads only receipt-complete products and pinned visible questions/options.
No reference keys, answer outputs, network, model calls, or producer changes.
"""
import argparse
from datetime import datetime,timezone
import itertools
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from experiments.litqa_analysis import collection,native_records as native

FRAME=ROOT/'planning/review-assets/tether-semantic-20261106/sc04/production-freeze01/FRAME.json'
FRAME_SHA='bf2898bed1a1c2f0a6040dd116ec37223f514764217441e4b8cf84345e4801d0'
PRODUCTS=ROOT/'data/benchmark/litqa_comparison/primary-production-20261106-attempt01/collect/worker/phase/products'
READERS=('experiments/litqa_analysis/collection.py','experiments/litqa_analysis/native_records.py','experiments/litqa_analysis/sources.py','experiments/litqa_comparison/codecs.py')


def proof(path):
    path=Path(path).absolute();data=native.read(path)
    return dict(path=str(path),bytes=len(data),sha256=native.digest(data))


def write(path,value):
    with Path(path).open('xb') as f:f.write(native.canonical(value)+b'\n')


def passage_contribution(item):
    data=dict(source_id=item['source_id'],text=item['text'])
    return len(json.dumps(data,sort_keys=True,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').encode())


def sizes(query,pool,instruction):
    native.need(len(pool)<=16 and all(0<len(p['text'].encode())<=1000 for p in pool),'Raw pool bounds')
    lexical=collection.selection(pool)
    largest=sorted(pool,key=passage_contribution,reverse=True)[:8]
    largest=[{k:p[k] for k in ('source_id','text','sha256')} for p in largest]
    native.need(sum(len(p['text'].encode()) for p in largest)<=8000,'Eight-passage text allowance')
    lexical_bytes=len(native.prompt(query,lexical,instruction).encode())
    maximum=len(native.prompt(query,largest,instruction).encode())
    native.need(maximum>=lexical_bytes,'Maximum prompt below lexical selection')
    return dict(lexical_prompt_bytes=lexical_bytes,maximum_any_permutation_prompt_bytes=maximum,
                maximizing_source_ids=[p['source_id'] for p in largest],maximum_selected_text_bytes=sum(len(p['text'].encode()) for p in largest))


def plan_identity(plan,query,ordinal):
    native.need(plan['question']=={k:query[k] for k in ('id','question')},'Collection question schedule')
    native.need(plan['strategy'] in ('lexical','expanded') and (ordinal%2==1 or plan['strategy']=='lexical'),'Collection strategy admissible for scheduled branch')
    # E may retain a lexical plan after expansion fallback. The enclosing
    # expansion outcome/reason is deliberately outside this source-only probe.


def arithmetic_controls():
    query=dict(id='invented-capacity-control',question='An invented question <with> Unicode β?',choices=['first','second','unknown'])
    pool=[]
    for i,text in enumerate(['Short.','Longer <tag> \\ string.','β'*12,'Escaped "quote"\nand newline']):
        pool.append(dict(rank_id=f'p{i:02d}',source_id=f'PMC9000000:body:p{i:04d}',text=text,sha256=native.digest(text.encode())))
    report=sizes(query,pool,'Invented fixed instruction.');observed=[]
    for count in range(len(pool)+1):
        for selection in itertools.permutations(pool,count):
            observed.append(len(native.prompt(query,selection,'Invented fixed instruction.').encode()))
    native.need(report['maximum_any_permutation_prompt_bytes']==max(observed),'Exhaustive Unicode/escaping/permutation bound')
    native.need(sizes(query,[],'Invented fixed instruction.')['maximum_selected_text_bytes']==0,'Empty pool bound')
    larger=[dict(rank_id=f'p{i:02d}',source_id=f'PMC9000000:body:p{i:04d}',text='β'*(i+1),sha256=native.digest(('β'*(i+1)).encode())) for i in range(16)]
    report16=sizes(query,larger,'Invented fixed instruction.')
    native.need(len(report16['maximizing_source_ids'])==8 and set(report16['maximizing_source_ids'])=={p['source_id'] for p in larger[8:]},'Largest eight of sixteen')
    for ordinal,strategy in ((0,'lexical'),(1,'lexical'),(1,'expanded')):
        plan_identity(dict(question={k:query[k] for k in ('id','question')},strategy=strategy),query,ordinal)
    try:plan_identity(dict(question={k:query[k] for k in ('id','question')},strategy='expanded'),query,0)
    except ValueError:pass
    else:raise ValueError('L branch unexpectedly admitted an expanded plan')
    return dict(status='PASS',controls=['Exhaustive 65 empty/subset/permutation renders with Unicode and JSON escaping.','Empty pool.','Sixteen candidates capped at the eight largest escaped contributions.','Scheduled E permits expanded or lexical-fallback plan; L remains lexical.'],exhaustive_renders=len(observed))


def closed_inputs(examined):
    result=[];observed=[]
    for root in sorted(PRODUCTS.iterdir()):
        if not root.is_dir() or not (root/'RECEIPT.json').is_file() or not (root/'MANIFEST.json').is_file():continue
        ordinal=int(root.name)
        # Completion markers alone do not establish validity; stable parse and
        # complete status precede opening any other product content.
        try:
            raw=native.read(root/'RECEIPT.json',1048576);r=native.decode(raw)
        except (ValueError,OSError):continue
        if r.get('status')!='complete':continue
        observed.append(ordinal)
        if ordinal in examined:continue
        native.need(0<=ordinal<398,'Unexpected collection ordinal')
        manifest=proof(root/'MANIFEST.json');plan=proof(root/'PLAN.json')
        native.need(r['files']['MANIFEST.json']['sha256']==manifest['sha256'] and r['files']['MANIFEST.json']['bytes']==manifest['bytes'],'Sealed manifest')
        native.need(r['files']['PLAN.json']['sha256']==plan['sha256'] and r['files']['PLAN.json']['bytes']==plan['bytes'],'Sealed plan')
        result.append(dict(root=str(root),ordinal=ordinal,receipt=dict(path=str(root/'RECEIPT.json'),bytes=len(raw),sha256=native.digest(raw)),manifest=manifest,plan=plan))
    return result,observed


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    output=a.output.absolute();output.mkdir(parents=True,exist_ok=False);start=time.monotonic();previous=None;sequence=0;rows=[];selected=[]
    def event(stage,**details):
        nonlocal previous,sequence
        row=dict(sequence=sequence,previous_sha256=previous,event=stage,at_utc=datetime.now(timezone.utc).isoformat(),details=details)
        previous=native.digest(native.canonical(row));row['sha256']=previous;sequence+=1
        with (output/'journal.jsonl').open('ab') as f:f.write(native.canonical(row)+b'\n');f.flush();os.fsync(f.fileno())
    def timeout():
        write(output/'TIMEOUT.json',dict(status='timed_out',elapsed_seconds=time.monotonic()-start,automatic_retry=False));os._exit(124)
    timer=threading.Timer(285,timeout);timer.daemon=True;timer.start();event('reserved')
    try:
        controls=arithmetic_controls();write(output/'CONTROLS.json',controls)
        native.need(proof(FRAME)['sha256']==FRAME_SHA,'Frozen primary frame')
        frame=native.load(FRAME);query_proof=frame['query_products']['answer_queries'];native.need(proof(query_proof['path'])==query_proof,'Pinned answer queries')
        queries=native.load(query_proof['path']);native.need(len(queries)==199 and [q['id'] for q in queries]==frame['schedule'],'Question schedule')
        native.need(all(set(q)=={'id','question','choices'} for q in queries),'Visible query-only input shape')
        pins={name:proof(ROOT/name) for name in READERS};code=pins['experiments/litqa_comparison/codecs.py']
        native.need(code['sha256']==frame['code_pins']['experiments/litqa_comparison/codecs.py'],'Frozen prompt source')
        instruction=native.instruction(code);limit=frame['generation_configuration']['max_prompt_bytes'];native.need(limit==14000,'Frozen prompt limit')
        write(output/'PLAN.json',dict(kind='closed_product_capacity_and_format_check_v1',created_at_utc=datetime.now(timezone.utc).isoformat(),
            frame=proof(FRAME),visible_queries=query_proof,reader_sources=pins,helper=proof(__file__),scheduled_collections=398,
            maximum_passes=5,soft_seconds=240,outer_seconds=285,byte_limit=limit,
            selection='Every receipt-complete collection available at each of at most five immediate scans; no wait for unfinished products.',
            scope='Closed products only; local observation anchors, no finalized enclosing run guarantee, keys, answers, inference, or network.'))
        examined=set();waves=[]
        for wave in range(5):
            inputs,observed=closed_inputs(examined);waves.append(dict(wave=wave,observed_closed=len(observed),observed_ordinals=observed,newly_selected=len(inputs)))
            write(output/f'SELECTION-{wave:02d}.json',dict(wave=wave,created_at_utc=datetime.now(timezone.utc).isoformat(),inputs=inputs,closed_ordinals=observed))
            event('closed_inputs_selected',wave=wave,closed=len(observed),new=len(inputs))
            if not inputs:break
            for item in inputs:
                if time.monotonic()-start>=240:break
                root=Path(item['root']);before=time.monotonic();ordinal=item['ordinal'];selected.append(item)
                native.need(proof(root/'RECEIPT.json')==item['receipt'] and proof(root/'MANIFEST.json')==item['manifest'],'Closed product changed since selection')
                plan=native.load(root/'PLAN.json');query=queries[ordinal//2]
                plan_identity(plan,query,ordinal)
                reconstructed=collection.reconstruct(root,item['receipt']['sha256'],plan);manifest=reconstructed['manifest'];pool=manifest['pool']['pool']
                measured=sizes(query,pool,instruction)
                row=dict(ordinal=ordinal,question_id=query['id'],branch=('L','E')[ordinal%2],observed_plan_strategy=plan['strategy'],status='format_reconstructed',receipt_sha256=item['receipt']['sha256'],
                    pool_chunks=len(pool),retained_articles=len(manifest['sources']),requests=len(manifest['requests']),
                    failed_transfers=sum(r['transport_status']=='failed' for r in manifest['requests']),
                    source_decision_reasons=[d['reason'] for d in manifest['decisions']],
                    lexical_overflow=measured['lexical_prompt_bytes']>limit,possible_rank_order_overflow=measured['maximum_any_permutation_prompt_bytes']>limit,
                    seconds=time.monotonic()-before,**measured)
                native.need(proof(root/'RECEIPT.json')==item['receipt'] and proof(root/'MANIFEST.json')==item['manifest'],'Closed product changed during reconstruction')
                rows.append(row);examined.add(ordinal);event('product_checked',**row)
            if len(examined)==398 or time.monotonic()-start>=240:break
        # The final scan captures completion that occurred during the bounded
        # check; unseen products remain explicitly unexamined, never implied PASS.
        _,final_closed=closed_inputs(examined)
        native.need(all(proof(ROOT/name)==value for name,value in pins.items()),'Reader code changed')
        for item in selected:
            native.need(proof(item['receipt']['path'])==item['receipt'] and proof(item['manifest']['path'])==item['manifest'],'Previously examined product changed before finalization')
        native.need(proof(query_proof['path'])==query_proof,'Visible queries changed')
        complete=examined==set(range(398));report=dict(kind='closed_product_capacity_and_format_report_v1',status='PASS',
            whole_scheduled_collection_set_examined=complete,scope='All 398 closed collection products, not enclosing execution or scientific outcome acceptance.' if complete else 'Partial observed closed-product cohort; unexamined/incomplete products remain unknown.',
            scheduled_collections=398,examined_collections=len(rows),closed_at_final_scan=len(final_closed),unexamined_closed_ordinals=sorted(set(final_closed)-examined),
            unexamined_scheduled_ordinals=sorted(set(range(398))-examined),examined_ordinals=sorted(examined),waves=waves,
            source_files_unchanged=True,format_reconstructions_passed=len(rows),lexical_overflows=sum(r['lexical_overflow'] for r in rows),
            scheduled_expanded_branch_with_lexical_plan=sum(r['branch']=='E' and r['observed_plan_strategy']=='lexical' for r in rows),
            possible_rank_order_overflows=sum(r['possible_rank_order_overflow'] for r in rows),largest_lexical_prompt_bytes=max(r['lexical_prompt_bytes'] for r in rows),
            largest_any_order_prompt_bytes=max(r['maximum_any_permutation_prompt_bytes'] for r in rows),byte_limit=limit,
            minimum_headroom_bytes=limit-max(r['maximum_any_permutation_prompt_bytes'] for r in rows),elapsed_seconds=time.monotonic()-start,rows=rows,
            proof_argument='All candidate chunks are at most1000 UTF8 bytes, so any8 satisfy8000. Escaped JSON item contributions are additive and order independent. The largest8 therefore achieve the maximum over all permitted rank selections/orderings; fixed instruction/question/options included.',
            limits=['No answer, key, scoring, retrieval, model call, or restart occurred.','Observed closed receipts are locally pinned; final enclosing phase/root proof remains a separate gate.',
                    'Known producer capacity-abort handling remains unchanged. This measures input feasibility, not recovery behavior.',
                    'Observed E-branch lexical plans are permitted; enclosing expansion fallback provenance is not verified by this source-only check.',
                    'No claim about model correctness, token context limits, later supplied-source collections, or incomplete products.'])
        write(output/'REPORT.json',report);event('complete',examined=len(rows),whole_scheduled_collection_set_examined=complete)
        files={p.name:proof(p) for p in output.iterdir() if p.is_file()};write(output/'RECEIPT.json',dict(status='complete',files=files))
        print(json.dumps(dict(status='PASS',report=proof(output/'REPORT.json'),receipt=proof(output/'RECEIPT.json'),examined=len(rows),all398=complete,
            max_prompt=report['largest_any_order_prompt_bytes'],overflow=report['possible_rank_order_overflows'],headroom=report['minimum_headroom_bytes'])),flush=True)
    except BaseException as error:
        event('failed',error_type=type(error).__name__,message=str(error));write(output/'FAILURE.json',dict(status='failed',error_type=type(error).__name__,message=str(error),examined=len(rows),automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':main()
