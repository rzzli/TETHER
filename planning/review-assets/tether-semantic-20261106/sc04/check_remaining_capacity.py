"""Supplement the sealed 388-product check with only ordinals0388–0397."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import threading
import time

spec=importlib.util.spec_from_file_location('closed_capacity',Path(__file__).with_name('check_closed_capacity.py'))
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
n=base.native


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,required=True);p.add_argument('--previous-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    output=a.output.absolute();output.mkdir(parents=True,exist_ok=False);start=time.monotonic();sequence=0;previous=None
    def event(stage,**details):
        nonlocal previous,sequence
        record=dict(sequence=sequence,previous_sha256=previous,event=stage,at_utc=datetime.now(timezone.utc).isoformat(),details=details)
        previous=n.digest(n.canonical(record));record['sha256']=previous;sequence+=1
        with (output/'journal.jsonl').open('ab') as f:f.write(n.canonical(record)+b'\n');f.flush();os.fsync(f.fileno())
    def timeout():
        base.write(output/'TIMEOUT.json',dict(status='timed_out',automatic_retry=False));os._exit(124)
    timer=threading.Timer(120,timeout);timer.daemon=True;timer.start();event('reserved')
    try:
        prior=a.previous.absolute();rp=base.proof(prior/'RECEIPT.json');n.need(rp['sha256']==a.previous_sha256,'Prior external receipt anchor')
        receipt=n.load(prior/'RECEIPT.json');actual={p.name:base.proof(p) for p in prior.iterdir() if p.is_file() and p.name!='RECEIPT.json'}
        n.need(receipt['status']=='complete' and receipt['files']==actual,'Prior exact sealed inventory')
        prior_events=n.journal(prior/'journal.jsonl');old=n.load(prior/'REPORT.json');old_plan=n.load(prior/'PLAN.json')
        n.need(old['status']=='PASS' and old['examined_ordinals']==list(range(388)) and len(old['rows'])==388 and old['format_reconstructions_passed']==388,'Expected prior388 cohort')
        n.need(sorted(r['ordinal'] for r in old['rows'])==list(range(388)),'Prior row coverage')
        n.need(base.proof(base.__file__)==old_plan['helper'],'Prior helper unchanged')
        pins={name:base.proof(base.ROOT/name) for name in base.READERS};n.need(pins==old_plan['reader_sources'],'Qualified source readers unchanged')
        n.need(base.proof(base.FRAME)['sha256']==base.FRAME_SHA,'Frozen frame');frame=n.load(base.FRAME)
        qp=frame['query_products']['answer_queries'];n.need(qp==old_plan['visible_queries'] and base.proof(qp['path'])==qp,'Visible query lineage')
        queries=n.load(qp['path']);n.need(len(queries)==199 and [q['id'] for q in queries]==frame['schedule'],'Pinned visible question schedule')
        instruction=n.instruction(pins['experiments/litqa_comparison/codecs.py']);limit=frame['generation_configuration']['max_prompt_bytes'];n.need(limit==14000,'Prompt limit')
        selected=[]
        for ordinal in range(388,398):
            root=base.PRODUCTS/f'{ordinal:04d}'
            n.need((root/'MANIFEST.json').is_file() and (root/'RECEIPT.json').is_file(),'All final ten products must be closed before this check')
            raw=n.read(root/'RECEIPT.json',1048576);r=n.decode(raw);n.need(r['status']=='complete','Incomplete supplemental receipt')
            manifest=base.proof(root/'MANIFEST.json');plan=base.proof(root/'PLAN.json')
            n.need(r['files']['MANIFEST.json']['sha256']==manifest['sha256'] and r['files']['PLAN.json']['sha256']==plan['sha256'],'Sealed supplemental products')
            selected.append(dict(ordinal=ordinal,root=str(root),receipt=dict(path=str(root/'RECEIPT.json'),bytes=len(raw),sha256=n.digest(raw)),manifest=manifest,plan=plan))
        base.write(output/'PLAN.json',dict(kind='supplemental_closed_capacity_check_v1',created_at_utc=datetime.now(timezone.utc).isoformat(),
            previous_receipt=rp,previous_report=base.proof(prior/'REPORT.json'),helper=base.proof(__file__),base_helper=old_plan['helper'],reader_sources=pins,
            visible_queries=qp,inputs=selected,byte_limit=limit,outer_seconds=120,scope='Only final ten closed source products; earlier388 use retained anchored report, not repeated parsing.'))
        base.write(output/'CONTROLS.json',base.arithmetic_controls());event('supplement_selected',count=10)
        rows=[]
        for item in selected:
            before=time.monotonic();root=Path(item['root']);ordinal=item['ordinal'];query=queries[ordinal//2]
            n.need(base.proof(root/'RECEIPT.json')==item['receipt'] and base.proof(root/'MANIFEST.json')==item['manifest'],'Changed supplemental input')
            plan=n.load(root/'PLAN.json');base.plan_identity(plan,query,ordinal)
            value=base.collection.reconstruct(root,item['receipt']['sha256'],plan);manifest=value['manifest'];pool=manifest['pool']['pool'];measured=base.sizes(query,pool,instruction)
            row=dict(ordinal=ordinal,question_id=query['id'],branch=('L','E')[ordinal%2],observed_plan_strategy=plan['strategy'],status='format_reconstructed',
                receipt_sha256=item['receipt']['sha256'],pool_chunks=len(pool),retained_articles=len(manifest['sources']),requests=len(manifest['requests']),
                failed_transfers=sum(r['transport_status']=='failed' for r in manifest['requests']),source_decision_reasons=[d['reason'] for d in manifest['decisions']],
                lexical_overflow=measured['lexical_prompt_bytes']>limit,possible_rank_order_overflow=measured['maximum_any_permutation_prompt_bytes']>limit,
                seconds=time.monotonic()-before,**measured)
            n.need(base.proof(root/'RECEIPT.json')==item['receipt'] and base.proof(root/'MANIFEST.json')==item['manifest'],'Changed during supplemental reconstruction')
            rows.append(row);event('product_checked',**row)
        for item in selected:
            n.need(base.proof(item['receipt']['path'])==item['receipt'] and base.proof(item['manifest']['path'])==item['manifest'],'Changed supplemental product before finalization')
        n.need(all(base.proof(base.ROOT/name)==proof for name,proof in pins.items()) and base.proof(prior/'RECEIPT.json')==rp and base.proof(qp['path'])==qp,'Changed code/prior/query proof')
        combined=old['rows']+rows;n.need(sorted(r['ordinal'] for r in combined)==list(range(398)),'Disjoint complete398 coverage')
        report=dict(kind='supplemental_closed_capacity_report_v1',status='PASS',previous_receipt=rp,previous_report=base.proof(prior/'REPORT.json'),
            newly_examined_collections=10,newly_examined_ordinals=list(range(388,398)),combined_examined_collections=398,combined_examined_ordinals=list(range(398)),
            combined_format_reconstructions_passed=398,combined_lexical_overflows=sum(r['lexical_overflow'] for r in combined),
            combined_possible_rank_order_overflows=sum(r['possible_rank_order_overflow'] for r in combined),
            combined_largest_lexical_prompt_bytes=max(r['lexical_prompt_bytes'] for r in combined),combined_largest_any_order_prompt_bytes=max(r['maximum_any_permutation_prompt_bytes'] for r in combined),
            combined_minimum_headroom_bytes=limit-max(r['maximum_any_permutation_prompt_bytes'] for r in combined),byte_limit=limit,
            scheduled_expanded_branch_with_lexical_plan=sum(r['branch']=='E' and r['observed_plan_strategy']=='lexical' for r in combined),
            rows=rows,elapsed_seconds=time.monotonic()-start,source_files_unchanged=True,
            scope='All398 collection products covered by two disjoint sealed observations; no final enclosing execution/scientific outcome acceptance.',
            limits=old['limits'])
        base.write(output/'REPORT.json',report);event('complete',new=10,combined=398)
        base.write(output/'RECEIPT.json',dict(status='complete',files={p.name:base.proof(p) for p in output.iterdir() if p.is_file()}))
        print(json.dumps(dict(status='PASS',report=base.proof(output/'REPORT.json'),receipt=base.proof(output/'RECEIPT.json'),combined=398,maximum=report['combined_largest_any_order_prompt_bytes'],overflows=report['combined_possible_rank_order_overflows'])),flush=True)
    except BaseException as error:
        event('failed',error_type=type(error).__name__,message=str(error));base.write(output/'FAILURE.json',dict(status='failed',error_type=type(error).__name__,message=str(error),automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':main()
