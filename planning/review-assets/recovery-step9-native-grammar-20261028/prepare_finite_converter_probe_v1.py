"""Freeze two diagnostic calls and inputs only. Never execute the native bridge."""
from datetime import datetime,timezone
import hashlib
from importlib import metadata
import importlib.util
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile
from asof.serde import canonical,parse_json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PHASE=HERE.parent/'recovery-step9-native-duration-20261028'
EXPECTED_ACCEPTANCE='27f33a36fd01d48b79e1492ad6b4b185a60e4bd662bb1ee0d955e5a284079cdc'
EXPECTED_BRIDGE='ea5064b8e2b68aa193efb0e129ef1da6087809d1a6fb21facccefaad70c362ca'
assert sys.flags.isolated and metadata.version('asof-target-agents')=='0.3.10'
assert importlib.util.find_spec('pyarrow') is None


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def pin(path):
    path=Path(path).absolute()
    return dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)


def write_new(path,raw):
    with path.open('xb') as stream:stream.write(raw)


acceptance_path=PHASE/'acceptance.json'
assert sha(acceptance_path)==EXPECTED_ACCEPTANCE
acceptance=parse_json(acceptance_path.read_bytes())
assert acceptance['status']=='accepted_native_duration_consistency_engineering_only'
environments=parse_json((PHASE/'WHEEL-ENVIRONMENTS.json').read_bytes())
assert os.path.normcase(environments['default_python'])==os.path.normcase(sys.executable)
wheel=Path(environments['wheel'])
assert sha(wheel)==environments['wheel_sha256']==acceptance['wheel']['sha256']
installed=Path(sys.prefix)/'Lib/site-packages'
installed_files=[]
with ZipFile(wheel) as archive:
    for name in sorted(n for n in archive.namelist() if n.startswith('asof/') and n.endswith(('.py','.json'))):
        path=installed/name
        assert path.read_bytes()==archive.read(name)
        installed_files.append(pin(path))
assert len(installed_files)==83
build_path=HERE/'TYPED-CONVERTER-BRIDGE-BUILD-v3.json'
build=parse_json(build_path.read_bytes())
assert build['status']=='typed_actual_converter_bridge_built_not_executed'
bridge=Path(build['executable']['path'])
assert sha(bridge)==EXPECTED_BRIDGE==build['executable']['sha256']
assert build['resulting_bridge_executions']==build['native_libraries_loaded']==0
assert set(build['static_delay_imports'])=={'llama-common.dll'} and len(build['static_delay_imports']['llama-common.dll'])==4
assert not any('llama' in name.lower() or 'ggml' in name.lower() for name in build['static_ordinary_imports'])
mirror_path=HERE.parent/'recovery-step9-native-integration-20261027/NATIVE-MODEL-MIRROR.json'
assert sha(mirror_path)==build['model_mirror_report']['sha256']
mirror=parse_json(mirror_path.read_bytes())
model_root=Path(mirror['target'])
native_root=model_root/'runtime'
runtime=[]
for row in mirror['items']:
    if not row['relative_path'].startswith('runtime/'):continue
    path=model_root/row['relative_path']
    assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
    runtime.append(pin(path))
assert len(runtime)==32 and len([r for r in runtime if r['path'].lower().endswith('.dll')])==30
corpus_report_path=HERE/'CORPUS-PREPARATION.json'
corpus_report=parse_json(corpus_report_path.read_bytes())
corpus_path=ROOT/corpus_report['corpus_path']
assert sha(corpus_path)==corpus_report['corpus_sha256']
corpus=parse_json(corpus_path.read_bytes());assert len(corpus)==109
schemas={r['schema_json'] for r in corpus};assert len(schemas)==1
schema=next(iter(schemas)).encode('utf-8')
assert hashlib.sha256(schema).hexdigest()==corpus_report['schema_sha256'] and len(schema)<=65536
fixture=dict(null_value=None,bool_values=[True,False],integer_values=[-7,0,2147483647],floating_values=[1.25,-.5],
    unicode_text='AsOf caf\u00e9 \U0001f9ea',escaped='quotes: " / slash \\ / newline\n',
    array=[None,dict(kind='synthetic',count=3)],empty_object={},empty_array=[])
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
inputs=ROOT/'data/cache'/('r09-finite-converter-inputs-'+stamp)
output=ROOT/'data/cache'/('r09-finite-converter-execution-'+stamp)
assert not output.exists()
inputs.mkdir(exist_ok=False)
write_new(inputs/'roundtrip.json',canonical(fixture))
write_new(inputs/'convert.json',schema)
stages=[]
for index,mode in enumerate(('roundtrip','convert')):
    directory=output/'stages'/f'{index:02d}-{mode}'
    source=inputs/f'{mode}.json'
    assert source.stat().st_size<=65536
    stages.append(dict(mode=mode,input=pin(source),cwd=str(directory),argv=[str(bridge),mode,str(native_root),
        str(output/'inputs'/f'{mode}.json'),str(directory/'result.json')]))
provenance=[build_path,HERE/'CONVERTER-BRIDGE-BUILD-CONTRACT.md',HERE/'CONVERTER-HEADER-CLOSURE.json',
    HERE/'SOURCE-TAG-IDENTITY-authorized.json',HERE/'CORPUS-PREPARATION.json',HERE/'BRIDGE-BUILD-PRESERVATION.json',
    Path(build['compiled_source']['path']),Path(build['helper']['path']),Path(build['import_definition']['path']),
    Path(build['approved_runtime_manifest']['path']),Path(build['import_library']['path']),mirror_path,
    PHASE/'WHEEL-ENVIRONMENTS.json',HERE/'prepare_finite_converter_probe.py']
provenance += [Path(row['copied']['path']) for row in build['headers']]
for row in build['headers']:assert sha(row['copied']['path'])==row['copied']['sha256']
crt=[]
for name in ('msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll','ucrtbase.dll'):
    path=Path(os.environ['SystemRoot'])/'System32'/name
    crt.append(dict(name=name,proof=pin(path) if path.is_file() else None,
        version=None,reason='Hash-only preparation environment snapshot; not actual child module attestation'))
protocol=dict(schema_version=1,kind='finite_actual_converter_probe_v1',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    scope='Two native engineering calls only; not grammar/EOS conformance, model quality or scientific validation',
    execution_authorization='Not executed or authorized by preparation; root must approve exact protocol hash and subsequently call --execute',
    helper=pin(HERE/'run_finite_converter_probe.py'),preparation_helper=pin(__file__),
    accepted_software=dict(version='0.3.10',acceptance=pin(acceptance_path),wheel=pin(wheel),
        installed_python=sys.executable,python=pin(sys.executable),installed_files=installed_files,
        python_version=sys.version,python_cache_tag=sys.implementation.cache_tag,default_runtime_dependencies=[]),
    bridge=pin(bridge),bridge_build=pin(build_path),native_root=str(native_root),runtime_files=runtime,
    corpus=pin(corpus_path),corpus_preparation=pin(corpus_report_path),schema_sha256=corpus_report['schema_sha256'],
    provenance_files=[pin(path) for path in provenance],roundtrip_fixture=fixture,
    system_crt_environment_snapshot=crt,source_commit='848bbda9041decd87904f7eb5a2990863ecce03b',
    output=str(output),execution_claim=str(inputs/'execution-claimed.json'),stages=stages,
    limits=dict(max_children=2,per_child_seconds=30,global_seconds=120,max_input_bytes=65536,
        max_stdout_bytes=1048576,max_stderr_bytes=1048576,max_native_output_bytes=4194304),
    force_gbnf=False,automatic_retry=False,stop_on_any_native_diagnostics=True,
    no_vocabulary_or_model_stage=True,actual_model_calls=0,servers=0,provider_spend_usd=0,
    classification_policy=['ABI roundtrip semantic/type or native-process failure: stop before conversion',
        'Any diagnostics/timeout/partial capture/cleanup failure: stop without repeating',
        'Converter warning/incomplete conversion/exception/empty or unknown backend: close negative before vocabulary',
        'Clean converter return permits no vocabulary stage in this protocol and proves no grammar/EOS conformance'])
protocol_path=HERE/'FINITE-CONVERTER-EXECUTION-PROTOCOL.json'
write_new(protocol_path,canonical(protocol)+b'\n')
print(json.dumps(dict(status='finite_converter_protocol_prepared_not_executed',protocol_sha256=sha(protocol_path),
    inputs=str(inputs),output=str(output),native_children=0,bridge_sha256=EXPECTED_BRIDGE,
    schema_sha256=protocol['schema_sha256'])))
