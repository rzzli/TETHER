"""Bind two disjoint source checks and recheck all398 closed product markers."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import time

spec=importlib.util.spec_from_file_location('closed_capacity',Path(__file__).with_name('check_closed_capacity.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);n=b.native


def sealed(root,anchor):
    value=b.proof(root/'RECEIPT.json');n.need(value['sha256']==anchor,'Observation external receipt')
    receipt=n.load(root/'RECEIPT.json');n.need(receipt['status']=='complete','Observation complete')
    n.need(receipt['files']=={p.name:b.proof(p) for p in root.iterdir() if p.is_file() and p.name!='RECEIPT.json'},'Observation exact inventory')
    n.journal(root/'journal.jsonl');return value


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,required=True);p.add_argument('--previous-sha256',required=True)
    p.add_argument('--supplement',type=Path,required=True);p.add_argument('--supplement-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    out=a.output.absolute();out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    try:
        previous=a.previous.absolute();supplement=a.supplement.absolute();p1=sealed(previous,a.previous_sha256);p2=sealed(supplement,a.supplement_sha256)
        old=n.load(previous/'REPORT.json');new=n.load(supplement/'REPORT.json');n.need(new['previous_receipt']==p1,'Supplement prior anchor')
        rows=old['rows']+new['rows'];n.need(old['examined_ordinals']==list(range(388)) and new['newly_examined_ordinals']==list(range(388,398)),'Disjoint observation cohorts')
        n.need(len(rows)==398 and sorted(r['ordinal'] for r in rows)==list(range(398)) and all(r['status']=='format_reconstructed' for r in rows),'Complete398 format coverage')
        pins=n.load(previous/'PLAN.json')['reader_sources'];n.need(pins==n.load(supplement/'PLAN.json')['reader_sources'] and all(b.proof(b.ROOT/name)==v for name,v in pins.items()),'Unchanged reader code')
        inputs=[item for file in sorted(previous.glob('SELECTION-*.json')) for item in n.load(file)['inputs']]+n.load(supplement/'PLAN.json')['inputs']
        n.need(len(inputs)==398 and sorted(v['ordinal'] for v in inputs)==list(range(398)),'Exact selected product set')
        checks=[]
        for item in sorted(inputs,key=lambda x:x['ordinal']):
            n.need(time.monotonic()-start<120,'Combined marker-check deadline')
            root=Path(item['root']);r=b.proof(root/'RECEIPT.json');n.need(r==item['receipt'],'Original product receipt unchanged')
            marker=n.load(root/'RECEIPT.json');n.need(marker['status']=='complete','Individual product not complete')
            manifest=b.proof(root/'MANIFEST.json');n.need(manifest==item['manifest'] and manifest['sha256']==marker['files']['MANIFEST.json']['sha256'] and manifest['bytes']==marker['files']['MANIFEST.json']['bytes'],'Original product manifest unchanged')
            checks.append(dict(ordinal=item['ordinal'],receipt=r,manifest=manifest,status='complete_unchanged'))
        b.write(out/'MARKER-CHECK.json',dict(status='PASS',products=checks,raw_xml_reparsed=False))
        maximum=max(r['maximum_any_permutation_prompt_bytes'] for r in rows);limit=old['byte_limit'];n.need(new['byte_limit']==limit==14000,'Common limit')
        report=dict(kind='combined_closed_source_capacity_summary_v1',status='PASS',created_at_utc=datetime.now(timezone.utc).isoformat(),
            previous_receipt=p1,supplement_receipt=p2,previous_report=b.proof(previous/'REPORT.json'),supplement_report=b.proof(supplement/'REPORT.json'),
            marker_check=b.proof(out/'MARKER-CHECK.json'),helper=b.proof(__file__),reader_sources=pins,
            examined_collections=398,examined_ordinals=list(range(398)),format_reconstructions_passed=398,all_individual_complete_markers_rechecked=True,
            largest_lexical_prompt_bytes=max(r['lexical_prompt_bytes'] for r in rows),largest_any_permitted_order_prompt_bytes=maximum,byte_limit=limit,minimum_headroom_bytes=limit-maximum,
            lexical_overflows=sum(r['lexical_overflow'] for r in rows),possible_rank_order_overflows=sum(r['possible_rank_order_overflow'] for r in rows),
            scheduled_expanded_branch_lexical_plans=sum(r['branch']=='E' and r['observed_plan_strategy']=='lexical' for r in rows),
            elapsed_seconds=time.monotonic()-start,full_experiment_acceptance=False,scientific_scoring=False,model_calls=0,network_calls=0,
            scope='All398 closed source products covered by two disjoint observations and final marker hashes; no answer/native/phase/root acceptance.',
            limits=old['limits'])
        b.write(out/'SUMMARY.json',report);b.write(out/'RECEIPT.json',dict(status='complete',files={p.name:b.proof(p) for p in out.iterdir() if p.is_file()}))
        print(json.dumps(dict(status='PASS',summary=b.proof(out/'SUMMARY.json'),receipt=b.proof(out/'RECEIPT.json'),products=len(checks),maximum_prompt=maximum)),flush=True)
    except BaseException as error:
        b.write(out/'FAILURE.json',dict(status='failed',error_type=type(error).__name__,message=str(error),automatic_retry=False));raise


if __name__=='__main__':main()
