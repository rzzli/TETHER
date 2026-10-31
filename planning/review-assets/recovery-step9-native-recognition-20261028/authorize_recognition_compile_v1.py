"""Root's software-only pin/config review and exclusive compile decision; no dispatch."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = {
    'build_recognition_bridge_v1.py': '7b46d67568e22e34dff048eb7a73abec3578268553d2f32c2550f2bb9919a18d',
    'RECOGNITION-BUILD-PROTOCOL-v1.json': 'c1a7de88730d9965003e35701033e12e00c4632625a4f3d54bd88a43bba6ba4f',
    'RECOGNITION-BUILD-PREPARATION-v1.json': '2a31e6183cee8e8791a7e42ec3097095d80c4c3f1b60027e3d71c6f3542e7e72',
    'RECOGNITION-BUILD-PURE-CHECKS-v1.json': 'd8c1dce125c035d92ca055a4911ac81a3d481f5c167797a566e09a63147787d6',
    'RECOGNITION-BUILD-PEER-REVIEW-v1.json': '4ad375ecfd2f9044747c386f8c7fe8c8610c98a7754074f1e58785ac08ae50fb',
    'RECOGNITION-CHILD-SOURCE-PEER-REVIEW-v2.json': '17c6e6b4faadfe6dee4724e292ae434fed8ebcc8ec63953955a71dd2c9adc39f',
    'RECOGNITION-SOURCE-ROOT-DECISION-v1.json': '20ea58d6626b82dd55c7b823ed1bd729134ecac15470fcc6c4c1ad69d92a5399',
    'RECOGNITION-BUILD-PREPARATION-ROOT-DECISION-v1.json': 'a90c8d1c8e99f803dcde99c3256de226324a7d8b119315329a965b1f09bd3e48',
}


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def main():
    output = HERE / 'RECOGNITION-BUILD-ROOT-DECISION-v1.json'
    assert not output.exists(), 'Decision already consumed'
    anchors = {}
    for name, expected in PINS.items():
        anchors[name] = pin(HERE / name)
        assert anchors[name]['sha256'] == expected, name
    config = json.loads((HERE / 'RECOGNITION-BUILD-PROTOCOL-v1.json').read_text(encoding='utf-8'))
    peer = json.loads((HERE / 'RECOGNITION-BUILD-PEER-REVIEW-v1.json').read_text(encoding='utf-8'))
    assert peer['status'] == 'clear_exact_compile_link_only_candidate_not_dispatch_permission'
    assert config['recognition_enabled'] is True
    assert all(config[k] is False for k in ('runtime_execution_authorized', 'CPU_GGUF_payload_access_authorized', 'execute_result'))
    assert config['limits'] == dict(total_seconds=60, compile_seconds=45, link_seconds=10,
        finalization_reserve_seconds=5, stdout_bytes=262144, stderr_bytes=262144,
        maximum_children=2, execute_result=False)
    assert len(config['commands']) == 2 and [x['stage'] for x in config['commands']] == ['compile', 'link']
    assert len(config['inputs']) == config['input_count'] == 287
    # Entire role domain screened before opening any configured leaf.
    for row in config['inputs']:
        path = Path(row['path'])
        text = str(path).lower().replace('/', '\\')
        assert path.drive.lower() in ('c:', 'd:')
        assert path.suffix.lower() != '.gguf'
        assert path.name.lower() != 'ggml-cpu.dll'
        assert '\\data\\benchmark\\' not in text
        assert 'recognition-pack-v2.json' not in path.name.lower()
        assert 0 <= row['bytes'] <= 128 * 1024**2
    total = 0
    for row in config['inputs']:
        actual = pin(row['path'])
        assert actual == row, row['path']
        total += row['bytes']
    current = ast.parse((HERE/'build_recognition_bridge_v1.py').read_text(encoding='utf-8'))
    previous = ast.parse((HERE/'build_trusted_platform_bridge_v2.py').read_text(encoding='utf-8'))
    funcs = lambda t: {n.name: ast.dump(n, include_attributes=False) for n in t.body if isinstance(n, ast.FunctionDef)}
    a, b = funcs(current), funcs(previous)
    unchanged = ['need', 'sha', 'basis', 'named_exports', 'verify_export_mapping', 'filtered_basis_inputs',
        'validate_parent_interpreter', 'accepted', 'collect_inputs', 'verify_pins', 'export_tables',
        'pe_policy', 'commands', 'finalize']
    assert all(a[k] == b[k] for k in unchanged)
    build_output = Path(config['output'])
    assert build_output.is_relative_to(ROOT/'data/cache') and not build_output.exists()
    parent = ROOT/'data/cache/recovery-step9-generation-wheel-20261028/environment/Scripts/python.exe'
    parent_pin = pin(parent)
    assert parent_pin['sha256'] == '43a8d6a15c6abed2f42d794b8f28d1c4b0e74bf11d42299304febe145f2ba52d'
    value = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        status='root_authorizes_one_exact_recognition_compile_link_only', anchors=anchors,
        authorizer=pin(__file__), accepted_parent=parent_pin, output=str(build_output),
        output_absent=True, fresh_input_hashes_checked=len(config['inputs']), input_bytes=total,
        unchanged_helper_ASTs=unchanged, recognition_capability_enabled=True,
        runtime_execution_authorized=False, CPU_GGUF_payload_access_authorized=False,
        execute_compiled_result=False, automatic_retry=False, maximum_compiler_linker_processes=2,
        limits=config['limits'], required_independent_output_verification=True,
        module_policy_sha256=config['module_policy_sha256'], provider_spend_usd=0,
        compiler_scope=config['process_scope'], toolchain_scope=config['toolchain_scope'],
        protected_answers_hash_only=True, target_DLL_loads=0, CPU_GGUF_model_reads=0,
        remaining='Build only. Final parent/parser/profile/asset authority and a new root decision precede any recognition execution.')
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(decision=pin(output), fresh_inputs=len(config['inputs']), bytes=total)))


if __name__ == '__main__':
    main()
