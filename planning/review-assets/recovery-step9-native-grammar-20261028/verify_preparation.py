"""Verify fixed grammar preparation artifacts; this is not native conformance."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREVIOUS=HERE.parent/'recovery-step9-native-integration-20261027'
INTERFACE=HERE.parent/'recovery-step9-interface-20261027'


def load(path):return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


assert sha(PREVIOUS/'acceptance.json')=='8a77c2eaba83dece672330b72c518a8f16f1417c9a14498b54686ac990b7815b'
accepted=load(PREVIOUS/'acceptance.json')
assert all(sha(ROOT/r['path'])==r['sha256'] for r in accepted['evidence'])
assert sha(ROOT/accepted['preserved_wheel']['path'])==accepted['wheel']['sha256']
assert sha(INTERFACE/'acceptance.json')=='b95bef8731d56fd3ff2872e18170b056e6628890b1b887f8e094cbd6e4dcef41'
older=load(INTERFACE/'acceptance.json')
oracle_path=INTERFACE/'SCHEMA-QUALIFICATION-v3.json'
oracle_pin=next(r for r in older['evidence'] if r['path']==oracle_path.relative_to(ROOT).as_posix())
assert sha(oracle_path)==oracle_pin['sha256']
oracle=load(oracle_path)
original=ROOT/'data/cache/r09-interface-schema-oracle-v3-20261027/cases.json'
assert sha(original)==oracle['input_sha256']
corpus=load(HERE/'CORPUS-PREPARATION.json')
corpus_path=ROOT/corpus['corpus_path']
assert sha(corpus_path)==corpus['corpus_sha256']
cases=load(corpus_path)
assert len(cases)==109 and cases[:105]==load(original)
assert len({r['id'] for r in cases})==109
assert {r['id'] for r in cases[105:]}=={f'native_length_{kind}_{size}' for kind in ('ascii','astral') for size in (1800,1801)}
assert all(r['expected_schema_exception'] is None for r in cases[105:])
assert corpus['differences']==[dict(id='duplicate_claim_texts',expected_exception='Cross-claim text uniqueness is explicitly post-validation only')]
assert not corpus['guards']['denied'] and corpus['guards']['children']==1
assert corpus['native_conversion']==corpus['native_document_acceptance']=='not_attempted'
for name,key in [('request.json','request_sha256'),('payload.json','payload_sha256'),
        ('oracle-stdout.json','oracle_stdout_sha256'),('oracle-stderr.bin','oracle_stderr_sha256')]:
    assert sha(corpus_path.parent/name)==corpus[key]
assert all(sha(Path(r['path']))==r['sha256'] for r in corpus['oracle_dependencies']['assemblies'])
identity=load(HERE/'SOURCE-TAG-IDENTITY-authorized.json')
assert identity['status']=='public_tag_matches_retained_runtime_short_commit'
commit=identity['full_source_commit']
assert commit=='848bbda9041decd87904f7eb5a2990863ecce03b'
assert commit.startswith(identity['runtime_reported_short_commit'])
assert sha(ROOT/identity['runtime_startup_log']['path'])==identity['runtime_startup_log']['sha256']
acquisition=load(HERE/'SOURCE-TEXT-ACQUISITION.json')
source_check=load(HERE/'SOURCE-TEXT-VERIFICATION.json')
assert sha(HERE/'SOURCE-TEXT-ACQUISITION.json')==source_check['source_acquisition_sha256']
assert acquisition['commit']==commit and len(acquisition['records'])==8
for record in acquisition['records']:
    path=ROOT/record['relative_path']
    assert record['http_status']==200 and record['status']=='retained_utf8_text'
    assert path.stat().st_size==record['bytes']<=524288 and sha(path)==record['sha256']
    assert record['url']==record['final_url']
    assert record['url'].startswith(f'https://raw.githubusercontent.com/ggml-org/llama.cpp/{commit}/')
    assert record['role']=='source_reference_only'
assert sum(r['bytes'] for r in acquisition['records'])==371242<=2097152
assert source_check['external_code_executed']==source_check['external_code_imported']==False
runtime=load(HERE/'RUNTIME-DISCOVERY.json')
mirror=load(PREVIOUS/'NATIVE-MODEL-MIRROR.json')
approved={r['relative_path']:r for r in mirror['items']}
for record in runtime['records']:
    assert record['sha256']==approved[record['relative_path']]['sha256']
    assert sha(Path(runtime['approved_model_root'])/record['relative_path'])==record['sha256']
report=dict(schema_version=1,status='preparation_verified_native_grammar_not_executed',
    accepted_039_evidence_hashes=len(accepted['evidence']),preserved_wheel_verified=True,
    corpus_cases=109,original_cases_unchanged=105,source_references=8,source_bytes=371242,
    source_commit=commit,approved_dlls_rechecked=3,model_calls=0,servers=0,
    native_conversion='not_attempted',native_document_acceptance='not_attempted',
    human_reviews='pending',owner_toolchain_response='No existing C++ toolchain',
    required_before_native_check=['Compatible toolchain or provenance-qualified prebuilt bridge/validator',
        'Pinned header/build dependency closure and ABI qualification','Explicit native corpus protocol'],
    separate_correctness_work='Duration verifier correction underway under independently versioned0.3.10',
    evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in HERE.glob('*.json')])
with (HERE/'PREPARATION-VERIFICATION.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:report[k] for k in ('status','corpus_cases','source_references','source_bytes','owner_toolchain_response')}))
