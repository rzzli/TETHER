import base64, json, pathlib, sys, tempfile, time
ROOT=pathlib.Path.cwd();sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]
OUT=ROOT/'data/cache/sc04-analysis-audit-20261106-attempt01'; tempfile.tempdir=str(OUT)
from experiments.litqa_analysis.test_native_records import NativeRecordTests
from experiments.litqa_analysis.test_sources import SourceTests
from experiments.litqa_analysis import native_records as n, sources as s
results=[]
def rewrite_journal(cell, mutate):
    events=n.journal(cell/'journal.jsonl');mutate(events);last=None
    for e in events:
        e.pop('sha256');e['previous_sha256']=last;e['sha256']=n.digest(n.canonical(e));last=e['sha256']
    (cell/'journal.jsonl').write_bytes(b''.join(n.canonical(e)+b'\n' for e in events))
def journal_mutation(cell):
    rewrite_journal(cell,lambda es: es[1]['details'].update(measured_usage={'input_tokens':999,'output_tokens':999,'cost_usd':123},generation_entered=True))
def endpoint_mutation(cell):
    p=cell/'native/native-response.bin';v=n.load(p);v['endpoint']='https://external.example.invalid';p.write_bytes(n.canonical(v))
def tokenizer_mutation(cell):
    p=cell/'native/tokenization/result.json';v=n.load(p);v['tokenizer_request']['add_special']=False;v['tokenizer_request']['parse_special']=False;p.write_bytes(n.canonical(v));(cell/'native/tokenization/request.json').write_bytes(n.canonical(v['tokenizer_request']))
def stream_mutation(cell):
    p=cell/'native/native-response.bin';v=n.load(p);body=n.decode(base64.b64decode(v['body_base64']));body['generation_settings']['stream']=True;raw=n.canonical(body);v['body_base64']=base64.b64encode(raw).decode();v['body_sha256']=n.digest(raw);p.write_bytes(n.canonical(v))
for name,mutate in [('contradictory_reserved_event',journal_mutation),('non_loopback_native_endpoint',endpoint_mutation),('wrong_tokenizer_special_flags',tokenizer_mutation),('contradictory_echoed_stream',stream_mutation)]:
    fixture=NativeRecordTests('runTest');fixture.setUp()
    try:
        cell=fixture.f.root/'cell';fixture.f.call('answer',fixture.query,fixture.sources,cell,time.monotonic()+10);fixture.reconstruct(cell)
        mutate(cell)
        try: fixture.reconstruct(cell);outcome='ACCEPTED'
        except Exception as e:outcome=f'REJECTED:{type(e).__name__}:{e}'
        results.append({'probe':name,'independent_reader':outcome})
    finally:fixture.doCleanups()
f=SourceTests('runTest');f.setUp()
try:
    f.source['spans'].append(dict(f.source['spans'][0]));s.read_article(f.root,f.source)
    results.append({'probe':'duplicate_identical_manifest_span','independent_reader':'ACCEPTED'})
finally:f.doCleanups()
(OUT/'FINDINGS.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
print(json.dumps(results,indent=2))
