"""Retain exact helpers/source/header snapshots for each build; execute none."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pin(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


records = []
for suffix, helper in (('', 'build_typed_converter_bridge.py'), ('-v2', 'build_typed_converter_bridge_v2.py'),
                       ('-v3', 'build_typed_converter_bridge_v3.py')):
    report_path = HERE / ('TYPED-CONVERTER-BRIDGE-BUILD' + suffix + '.json')
    report = json.loads(report_path.read_bytes())
    out = Path(report['output'])
    source = out / 'typed_converter_bridge.cpp'
    assert source.is_file() and (out / 'headers').is_dir()
    helper_path = HERE / helper
    if report['status'] != 'failed':
        assert sha(source) == report['compiled_source']['sha256']
        assert sha(helper_path) == report['helper']['sha256']
        assert all(sha(h['copied']['path']) == h['copied']['sha256'] for h in report['headers'])
    copied = []
    for name, original in (
        ('build-helper.py', helper_path),
        ('BUILD-CONTRACT.md', HERE / 'CONVERTER-BRIDGE-BUILD-CONTRACT.md'),
        ('HEADER-CLOSURE.json', HERE / 'CONVERTER-HEADER-CLOSURE.json'),
        ('BUILD-RESULT.json', report_path),
    ):
        target = out / name
        with target.open('xb') as stream:
            stream.write(original.read_bytes())
        assert sha(target) == sha(original)
        copied.append(pin(target))
    artifacts = [pin(source), pin(out/'approved_runtime.hpp'), pin(out/'llama-common-typed.def'),
                 pin(out/'llama-common-typed.lib')]
    artifacts += [pin(path) for path in sorted((out/'headers').glob('*'))]
    if report['status'] != 'failed':
        artifacts += [pin(out/'typed_converter_bridge.exe'), pin(out/'typed_converter_bridge.obj')]
    records.append(dict(build=suffix or 'v1', status=report['status'], result=pin(report_path),
                        cache=str(out), copied_records=copied, immutable_build_inputs_outputs=artifacts,
                        note='Older authored_source pointer is historical; exact compiled source is preserved in this cache'))
final = json.loads((HERE/'TYPED-CONVERTER-BRIDGE-BUILD-v3.json').read_bytes())
assert final['status'] == 'typed_actual_converter_bridge_built_not_executed'
assert final['resulting_bridge_executions'] == final['native_libraries_loaded'] == 0
assert all(sha(p['path']) == p['sha256'] for p in final['tools']+final['existing_tool_inputs'])
report = dict(schema_version=1, status='three_build_attempts_preserved_v3_static_build_passed', records=records,
              final_executable=final['executable'], bridge_executions=0, llama_libraries_loaded=0,
              compiler_processes_terminal=True, execution_authorization='Not granted',
              abi_compatibility='unverified', native_grammar_conformance='unverified')
with (HERE/'BRIDGE-BUILD-PRESERVATION.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps({k:report[k] for k in ('status','final_executable','bridge_executions','compiler_processes_terminal')}))
