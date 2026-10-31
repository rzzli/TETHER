"""Compare the new schema with an installed independent JSON Schema engine."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

from asof.serde import ContractError,canonical,encode
from asof.study.diagnostic import load_synthetic_request
from asof.study.interpretation_interface import prepare_payload,validate_output

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=ROOT/'data/cache/r09-interface-schema-oracle-v2-20261027'
CACHE.mkdir(exist_ok=False)
request=load_synthetic_request('synthetic-context')
prepared=prepare_payload(request,'asof_interpretation',0,[])
payload=prepared['payload']
catalog=prepared['semantic_data']['quote_catalog']
from asof.study.diagnostic_codec import pointer
base=dict(answer_status='answered',claims=[dict(kind='source_report',
    text=pointer(encode(request),catalog[0]['request_pointer']),quote_refs=['Q0'],limitations=[])],
    unresolved=[],abstention_reason=None)
cases=[]


def add(name,change=lambda d:None,expected=None,exception=None):
    document=copy.deepcopy(base)
    change(document)
    try:
        validate_output(request,payload,document)
        accepted=True
    except ContractError:
        accepted=False
    if expected is not None:
        assert accepted==expected,name
    cases.append(dict(id=name,document_json=canonical(document).decode(),schema_json=canonical(payload['json_schema']).decode(),
        python_accepted=accepted,expected_schema_exception=exception))


add('whole_source_report',expected=True)
add('inference',lambda d:d['claims'][0].update(kind='scientific_inference',text='An invented inference.',limitations=['Not a fact.']),True)
add('caution',lambda d:d['claims'][0].update(kind='caution',text='A hypothetical caveat.',limitations=['Invented fixture.']),True)
add('two_source_quotes',lambda d:d['claims'][0].update(kind='caution',text='Two supplied passages.',quote_refs=['Q0',catalog[-1]['quote_id']],limitations=['Not independent studies.']),True)
for state in ('answered','partial','abstained'):
    for has_claim in (True,False):
        for reason in (None,'Incomplete scope.','   '):
            def change(d,state=state,has_claim=has_claim,reason=reason):
                d.update(answer_status=state,abstention_reason=reason)
                if not has_claim:d['claims']=[]
            add(f'state_{state}_{has_claim}_{reason!r}',change)
add('unknown_reference',lambda d:d['claims'][0].update(quote_refs=['Q999']),False)
add('duplicate_reference',lambda d:d['claims'][0].update(kind='caution',limitations=['Unknowns.'],quote_refs=['Q0','Q0']),False)
add('missing_reference',lambda d:d['claims'][0].update(quote_refs=[]),False)
add('wrong_literal',lambda d:d['claims'][0].update(text=d['claims'][0]['text']+' '),False)
add('no_inference_limits',lambda d:d['claims'][0].update(kind='scientific_inference',text='A conclusion.'),False)
add('extra_root',lambda d:d.update(features={}),False)
add('extra_claim',lambda d:d['claims'][0].update(source_ids=['E0']),False)
add('duplicate_claim_texts',lambda d:d['claims'].append(copy.deepcopy(d['claims'][0])),False,
    exception='Cross-claim text uniqueness is explicitly post-validation only')
for value in ('',' ', '\u2003','\x1c','ðŸ˜€'*1800,'ðŸ˜€'*1801):
    add('text_'+repr(value[:8])+str(len(value)),lambda d,value=value:d['claims'][0].update(kind='caution',text=value,limitations=['Invented only.']))
for value in ('',' ', '\u2003','\x1c','x'*512,'x'*513):
    add('reason_'+repr(value[:8])+str(len(value)),lambda d,value=value:d.update(answer_status='partial',abstention_reason=value))
for codepoint in range(0x110000):
    value=chr(codepoint)
    if value.isspace():
        add('unicode_whitespace_text_'+str(codepoint),lambda d,value=value:d['claims'][0].update(kind='caution',text=value,limitations=['Scope.']),False)
        add('unicode_whitespace_reason_'+str(codepoint),lambda d,value=value:d.update(answer_status='partial',abstention_reason=value),False)

for field in ('limitations','unresolved'):
    for count in (4,5):
        def change(d,field=field,count=count):
            if field=='limitations':d['claims'][0][field]=['Scope.']*count
            else:d[field]=['Unknown.']*count
        add(field+str(count),change,count==4)

input_path=CACHE/'cases.json'
input_path.write_text(json.dumps(cases,ensure_ascii=False),encoding='utf-8')
exe=Path(r'C:\Users\zzric\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
assert exe.is_file()
result=subprocess.run([str(exe),'-NoProfile','-NonInteractive','-File',str(HERE/'schema_oracle.ps1'),str(input_path)],
    capture_output=True,timeout=120)
(CACHE/'stdout.json').write_bytes(result.stdout)
(CACHE/'stderr.bin').write_bytes(result.stderr)
assert result.returncode==0,result.stderr.decode(errors='replace')
oracle=json.loads(result.stdout)
assert len(oracle['results'])==len(cases)
by_id={r['id']:r['accepted'] for r in oracle['results']}
differences=[]
for row in cases:
    row['schema_accepted']=by_id[row['id']]
    if row['schema_accepted']!=row['python_accepted']:
        differences.append(row)
report=dict(schema_version=1,status='passed' if all(r['expected_schema_exception'] for r in differences) else 'failed',
    cases=len(cases),oracle='installed PowerShell Test-Json / JsonSchema.NET',powershell_version=oracle['powershell_version'],
    executable=str(exe),executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
    interface_module_sha256=hashlib.sha256((ROOT/'src/asof/study/interpretation_interface.py').read_bytes()).hexdigest(),
    input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
    model_calls=0,new_downloads=0,provider_spend_usd=0,scientific_validation='not_attempted',
    differences=differences,all_results=cases)
with (HERE/'SCHEMA-QUALIFICATION-v2.json').open('x',encoding='utf-8') as stream:
    json.dump(report,stream,indent=2)
print(json.dumps({k:report[k] for k in ('status','cases','powershell_version','differences')},ensure_ascii=True))
assert report['status']=='passed'
