"""Archive and inspect pinned public competitor source without importing/running it.

Downloads source text only. Never reads credentials or initializes a model SDK.
Directory inventory is presence/size information, not receipt qualification.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import ast
import urllib.request

from tether_engine.serde import ContractError, sha256_file, write_json


REVISION = '71f9da68c95c5ee0ef4c1d9b8f45f10693de022d'
BASE = f'https://raw.githubusercontent.com/harrisongzhang/TheVirtualBiotech/{REVISION}/'
MEMBERS = ('README.md', 'src/config/datasets.py', 'src/config/models.py', 'src/agents/registry.py', 'environment.yml')


def literal_assignment(text, name):
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ContractError('Pinned source does not contain expected literal: ' + name)


def agent_configuration(text):
    """Read AgentDefinition keyword literals/inherited-model expressions via AST."""
    agents = {}
    for node in ast.walk(ast.parse(text)):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and
                isinstance(node.value.func, ast.Name) and node.value.func.id == 'AgentDefinition'):
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Subscript):
            continue
        name = ast.literal_eval(target.slice)
        kwargs = {k.arg: k.value for k in node.value.keywords}
        model = kwargs.get('model')
        agents[name] = {'model': ast.literal_eval(model) if isinstance(model, ast.Constant) else ast.unparse(model),
            'tools': ast.literal_eval(kwargs['tools']) if 'tools' in kwargs else [],
            'source_line': node.lineno}
    if not agents:
        raise ContractError('No agent definitions found in pinned source')
    return agents


def audit(output, data_root):
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'status.json', {'status': 'running', 'revision': REVISION})
    try:
        sources = []
        for name in MEMBERS:
            with urllib.request.urlopen(BASE + name, timeout=30) as response:
                payload = response.read(2 * 1024 * 1024 + 1)
            if len(payload) > 2 * 1024 * 1024:
                raise ContractError('Upstream source file exceeds audit limit')
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(payload)
            sources.append({'path': name, 'url': BASE + name, 'bytes': len(payload), 'sha256': sha256_file(path)})
        text = lambda name: (output / name).read_text(encoding='utf-8')
        datasets = literal_assignment(text('src/config/datasets.py'), 'OPEN_TARGETS_DATASETS')
        default = literal_assignment(text('src/config/models.py'), 'DEFAULT_MODEL_ID')
        agents = agent_configuration(text('src/agents/registry.py'))
        inventory = []
        for name in datasets:
            directory = data_root / name
            files = list(directory.rglob('*.parquet')) if directory.is_dir() else []
            inventory.append({'dataset': name, 'directory_present': directory.is_dir(),
                'parquet_files_present': len(files), 'file_bytes_present': sum(p.stat().st_size for p in files),
                'qualification': 'presence_only_not_receipt_hash_schema_or_release_validation'})
        result = {'schema_version': 1, 'status': 'pinned_source_compatibility_audited_not_executed',
            'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'repository': 'https://github.com/harrisongzhang/TheVirtualBiotech',
            'revision': REVISION, 'sources': sources, 'default_model': default, 'agents': agents,
            'required_dataset_count': len(datasets), 'local_data_root': str(data_root), 'local_inventory': inventory,
            'directories_with_parquet': sum(x['parquet_files_present'] > 0 for x in inventory),
            'sdk_initialized': False, 'credentials_read': False, 'model_calls': 0, 'provider_spend_usd': 0,
            'unmodified_execution_status': 'blocked_by_current_offline_zero_provider_spend_boundary',
            'adapted_local_execution_status': 'not_implemented_requires_explicit_adapter_and_containment_validation',
            'adaptation_requirements': [
                'Replace provider execution for coordinator, specialists, chief-of-staff and scientific-reviewer with the same pinned eligible local weights',
                'Expose identical admitted source packets and budgets; remove known_drug, ChEMBL and evaluator-only/outcome sources',
                'Contain filesystem, shell and network capabilities for every role; application hooks alone do not establish historical isolation',
                'Record all deviations, prompts, tool outputs, usage and failures; validate canaries and semantic source binding before inference',
                'Label result adapted, not original reproduction; no scientific-quality or clinical metric without qualified truth'],
            'scientific_performance': None}
        write_json(output / 'audit.json', result)
        write_json(output / 'status.json', {'status': result['status']})
        write_json(output / 'evidence-manifest.json', {'schema_version': 1, 'files': [
            {'path': p.relative_to(output).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha256_file(p)}
            for p in sorted(output.rglob('*')) if p.is_file()], 'audit_code_sha256': sha256_file(Path(__file__))})
        return result
    except BaseException as exc:
        write_json(output / 'status.json', {'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.output, args.data_root)
    print(result['status'], result['required_dataset_count'], result['directories_with_parquet'])
