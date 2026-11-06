"""Independent stdlib-only metadata/byte audit; reference answers are not parsed."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
PREP=ROOT/'data/benchmark/labbench/preparation-20261106-attempt02'
MANIFEST_SHA='7c085ccf94f0e3e3270727efbc3b250e43ac52168aad009ee362662fbd58122b'
ACQUISITION_SHA='620cf7d9d166d892b8c33da9a3f6a896d0c8d3659bbc10b4b6144fcadcd723bd'
SOURCE_PINS={
    'experiments/labbench/data_views.py':'a2421dbfd1863b61ed0564056a36e74a08308226607320be74c09285fde7fa69',
    'experiments/labbench/retrieval.py':'5e8f7b80f9bbe5a49a642f78bead76a6acc4e221823368cbdfa4511a48a7eaea',
    'experiments/labbench/native_contract.py':'8023fc028be67a0809d055560c418f3e83241c0304f538e61c90b0a64e3a35b3'}


def need(value,message):
    if not value:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def pairs(values):
    output={}
    for key,value in values:
        need(key not in output,'Duplicate JSON metadata key')
        output[key]=value
    return output


def read(path):
    return json.loads(path.read_bytes(),object_pairs_hook=pairs)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def main():
    for relative,expected in SOURCE_PINS.items():need(sha((ROOT/relative).read_bytes())==expected,'Code pin changed')
    raw=(PREP/'manifest.json').read_bytes();need(sha(raw)==MANIFEST_SHA,'External projection anchor mismatch')
    manifest=read(PREP/'manifest.json')
    need(manifest['expected_count']==199 and manifest['diagnostics']['count']==199 and manifest['diagnostics']['skipped_rows']==0,'Schedule count differs')
    need(manifest['diagnostics']['duplicate_distractor_text_rows']==2,'Duplicate diagnostic differs')
    need(manifest['projector_sha256']==SOURCE_PINS['experiments/labbench/data_views.py'],'Projector source mismatch')
    need(manifest['physical_container_role']=='mixed_reference_only' and manifest['predictor_allowed_product_ids']==['queries'],'Role isolation differs')
    need(set(manifest['products'])=={'queries','references','provenance'},'Unknown product')
    original=Path(manifest['original_root'])
    receipt_raw=(original/'ACQUISITION.json').read_bytes()
    need(sha(receipt_raw)==ACQUISITION_SHA==manifest['acquisition_receipt_sha256'],'Acquisition anchor mismatch')
    receipt=json.loads(receipt_raw,object_pairs_hook=pairs)
    for key,expected in [('hf_revision','5c77cec648430f30611808808861eb86f81d5eaa'),('github_revision','998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838')]:
        need(manifest[key]==receipt[key]==expected,'Provider revision contradiction')
    proof_by_path={row['path']:row for row in receipt['files']}
    need(len(proof_by_path)==len(receipt['files']),'Duplicate acquisition paths')
    original_jsonl='github/LitQA2/litqa-v2-public.jsonl'
    parent=proof_by_path[original_jsonl]
    # Original answer-containing bytes are hashed, not decoded or printed.
    native_original_bytes=(original/original_jsonl).read_bytes()
    need(sha(native_original_bytes)==parent['sha256'] and len(native_original_bytes)==parent['bytes'],'Original byte binding differs')
    products={}
    for name,record in manifest['products'].items():
        need(record['path']==name+'.json','Unexpected product path')
        body=(PREP/record['path']).read_bytes()
        need(sha(body)==record['sha256'] and len(body)==record['bytes'],'Product byte mismatch')
        need(record['purpose']==('answerer_input' if name=='queries' else 'evaluation_only'),'Product role mismatch')
        need(record['physical_parent']=={'path':original_jsonl,'sha256':parent['sha256'],'bytes':parent['bytes']},'Product original parent differs')
        need(record['logical_fields']==(['id','question','displayed_choices'] if name=='queries' else ['original_reference_fields']),'Logical projection fields differ')
        products[name]={'sha256':sha(body),'bytes':len(body),'purpose':record['purpose'],'contents_parsed':name=='queries'}
    queries=read(PREP/'queries.json')
    need(len(queries)==199 and len({row['id'] for row in queries})==199,'Query cardinality differs')
    duplicate_rows=0
    for row in queries:
        need(set(row)=={'id','question','choices'} and str(UUID(row['id']))==row['id'],'Unprojected fields or invalid query ID')
        need(isinstance(row['question'],str) and row['question'].strip(),'Empty question')
        texts=[]
        for index,choice in enumerate(row['choices']):
            need(choice.startswith(f'({chr(65+index)}) '),'Native position label differs')
            texts.append(choice[4:])
        need(texts.count('Insufficient information to answer the question')==1,'Unsure convention differs')
        duplicate_rows+=len(texts)!=len(set(texts))
    need(duplicate_rows==2,'Displayed duplicate count differs')
    complete=read(PREP/'COMPLETE.json');journal_raw=(PREP/'journal.jsonl').read_bytes()
    need(complete=={'manifest_sha256':MANIFEST_SHA,'journal_sha256':sha(journal_raw)},'Completion binding differs')
    previous=None
    events=[]
    for line in journal_raw.splitlines():
        event=json.loads(line,object_pairs_hook=pairs); digest=event.pop('sha256')
        need(event['previous_sha256']==previous and event['sequence']==len(events) and sha(canonical(event))==digest,'Journal chain differs')
        previous=digest;events.append(event)
    need(events[-1]['event']=='build_completed' and events[-1]['details']['manifest_sha256']==MANIFEST_SHA,'Missing completion event')
    reconciliation_path=BASE/'data/JSONL-PARQUET-RECONCILIATION-01.json'
    reconciliation=read(reconciliation_path)
    need(reconciliation['pass'] and reconciliation['ids_equal'] and reconciliation['order_equal'] and not reconciliation['shared_field_differences'],'Parity gate differs')
    need(reconciliation['jsonl_sha256']==parent['sha256'],'Parity JSONL anchor differs')
    parquet=[row for row in receipt['files'] if row['path'].endswith('.parquet')]
    need(len(parquet)==1 and parquet[0]['sha256']==reconciliation['parquet_sha256'],'Parity Parquet anchor differs')
    logs={}
    for relative,count in [('data/data-views-green04.log',7),('data/retrieval-green04.log',12),('scoring-green04.log',13),('policy-green04.log',10)]:
        raw=(BASE/relative).read_bytes();text=raw.decode('utf-8-sig')
        need(re.search(r'Ran '+str(count)+r' tests in ',text) and text.rstrip().endswith('OK'),'Qualification log is not passing')
        logs[relative]={'sha256':sha(raw),'tests':count}
    need((ROOT/'data/benchmark/labbench/preparation-20261106-attempt01/FAILED.json').is_file(),'Initial failed attempt not retained')
    for relative,expected in SOURCE_PINS.items():need(sha((ROOT/relative).read_bytes())==expected,'Code changed during audit')
    result={'schema_version':1,'status':'PASS','checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'external_manifest_sha256':MANIFEST_SHA,'external_acquisition_sha256':ACQUISITION_SHA,'source_pins':SOURCE_PINS,
        'task_count':199,'duplicate_displayed_text_rows':duplicate_rows,'products':products,'qualification_logs':logs,
        'reconciliation_sha256':sha(reconciliation_path.read_bytes()),'journal_sha256':sha(journal_raw),
        'reference_answers_parsed':False,'original_answer_rows_parsed':False,'candidate_generation':False,'candidate_scoring':False,
        'limits':'Metadata and exact byte binding audit; no independent answer-label reconstruction or biological/source-support validation.'}
    with (BASE/'PROJECTION-METADATA-INDEPENDENT-01.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'status':'PASS','task_count':199,'reference_answers_parsed':False}))


if __name__=='__main__':main()
