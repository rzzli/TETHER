"""Freeze existing cases plus four explicit length probes; no native grammar execution."""
import copy
import hashlib
from importlib import metadata
import json
from pathlib import Path
import subprocess
import sys
import time

from asof.serde import ContractError,canonical,encode
from asof.study.diagnostic import load_synthetic_request
from asof.study.interpretation_interface import prepare_payload,validate_output
import asof.study.interpretation_interface as interface

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'recovery-step9-interface-20261027'
ACCEPTED=HERE.parent/'recovery-step9-native-integration-20261027'
CACHE=ROOT/'data/cache/r09-native-grammar-corpus-20261028'
assert sys.flags.isolated and metadata.version('asof-target-agents')=='0.3.9'
assert Path(interface.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


code=json.loads((ACCEPTED/'code-validation.json').read_bytes())
assert code['status']=='passed' and all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
assert sha(interface.__file__)==code['source_pins']['src/asof/study/interpretation_interface.py']
old_report=json.loads((OLD/'SCHEMA-QUALIFICATION-v3.json').read_bytes())
old_input=ROOT/'data/cache/r09-interface-schema-oracle-v3-20261027/cases.json'
assert sha(old_input)==old_report['input_sha256']
cases=json.loads(old_input.read_bytes());assert len(cases)==105
request=load_synthetic_request('synthetic-context')
payload=prepare_payload(request,'asof_interpretation',0,[])['payload']
schema=canonical(payload['json_schema']).decode()
assert all(row['schema_json']==schema for row in cases)
for row in cases:
    try:validate_output(request,payload,json.loads(row['document_json']));accepted=True
    except ContractError:accepted=False
    assert accepted==row['python_accepted'],row['id']
base=json.loads(cases[0]['document_json'])
for kind,character in (('ascii','x'),('astral',chr(0x1f600))):
    for size in (1800,1801):
        document=copy.deepcopy(base)
        document['claims'][0].update(kind='caution',text=character*size,limitations=['Invented boundary fixture.'])
        try:validate_output(request,payload,document);accepted=True
        except ContractError:accepted=False
        assert accepted==(size==1800)
        cases.append(dict(id=f'native_length_{kind}_{size}',document_json=canonical(document).decode(),
            schema_json=schema,python_accepted=accepted,expected_schema_exception=None))
assert len(cases)==109 and len({r['id'] for r in cases})==109
dependencies=json.loads((OLD/'ORACLE-DEPENDENCIES.json').read_bytes())
assert all(sha(Path(r['path']))==r['sha256'] for r in dependencies['assemblies'])
exe=Path(old_report['executable']);assert sha(exe)==old_report['executable_sha256']
script=OLD/'schema_oracle.ps1';assert sha(script)==old_report['oracle_script_sha256']
CACHE.mkdir(exist_ok=False)
input_path=CACHE/'cases.json'
input_path.write_bytes(canonical(cases))
(CACHE/'request.json').write_bytes(canonical(encode(request)))
(CACHE/'payload.json').write_bytes(canonical(encode(payload)))
argv=[str(exe),'-NoProfile','-NonInteractive','-File',str(script),str(input_path)]
state=dict(children=0,denied=[])


def audit(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.__new__','os.system'):
        state['denied'].append(event);raise RuntimeError('No network/system execution')
    if event=='subprocess.Popen':
        expected=subprocess.list2cmdline(argv) if isinstance(args[1],str) else argv
        assert state['children']==0 and args[1]==expected
        state['children']+=1


sys.addaudithook(audit)
started=time.monotonic()
result=subprocess.run(argv,capture_output=True,timeout=120)
(CACHE/'oracle-stdout.json').write_bytes(result.stdout)
(CACHE/'oracle-stderr.bin').write_bytes(result.stderr)
assert result.returncode==0 and len(result.stdout)<1048576
oracle=json.loads(result.stdout)
assert oracle['powershell_version']=='7.6.5' and len(oracle['results'])==109
by_id={r['id']:r['accepted'] for r in oracle['results']}
differences=[]
for row in cases:
    if by_id[row['id']]!=row['python_accepted']:
        differences.append(dict(id=row['id'],expected_exception=row['expected_schema_exception']))
assert differences==[dict(id='duplicate_claim_texts',expected_exception='Cross-claim text uniqueness is explicitly post-validation only')]
assert state['children']==1 and not state['denied']
report=dict(schema_version=1,status='frozen_corpus_and_schema_oracle_passed_native_grammar_pending',
    cases=109,reused_cases=105,explicit_ascii_astral_length_cases=4,
    original_corpus_sha256=sha(old_input),corpus_path=input_path.relative_to(ROOT).as_posix(),corpus_sha256=sha(input_path),
    schema_sha256=hashlib.sha256(schema.encode()).hexdigest(),payload_sha256=sha(CACHE/'payload.json'),
    request_sha256=sha(CACHE/'request.json'),installed_interface_sha256=sha(interface.__file__),
    oracle_stdout_sha256=sha(CACHE/'oracle-stdout.json'),oracle_stderr_sha256=sha(CACHE/'oracle-stderr.bin'),
    oracle_executable_sha256=sha(exe),oracle_script_sha256=sha(script),oracle_dependencies=dependencies,
    oracle_argv=argv,oracle_elapsed_seconds=time.monotonic()-started,
    differences=differences,version='0.3.9',isolated_installed=True,model_calls=0,servers=0,
    tokenizer_calls=0,oracle_processes=1,provider_cost_usd=0,guards=state,
    native_conversion='not_attempted',native_document_acceptance='not_attempted',scientific_validation='not_attempted')
with (HERE/'CORPUS-PREPARATION.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:report[k] for k in ('status','cases','oracle_elapsed_seconds','differences')}))
