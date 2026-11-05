"""Bounded completion evidence index; no validator, analyzer or reconstruction call."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent


def load(path):
    return json.loads(Path(path).read_bytes())


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def check_pin(path, proof):
    actual = pin(path)
    assert actual['sha256'] == proof['sha256'] and actual['bytes'] == proof['bytes'], str(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.parent == HERE and not output.exists()
    state_path = 'planning/review-assets/tether-equal-policy-v2-20261105/EXECUTION-STATE.json'
    commit = subprocess.check_output(['git', 'rev-parse', '2f1b5eb'], cwd=ROOT, text=True).strip()
    committed = subprocess.check_output(['git', 'show', commit + ':' + state_path], cwd=ROOT)
    state = json.loads(committed)
    commit_time = subprocess.check_output(['git', 'show', '-s', '--format=%cI', commit], cwd=ROOT, text=True).strip()
    assert state['status'] == 'both_frozen_unscored_waiting_for_full_gate'
    evidence = dict(schema_version=1, checked_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Read-only completion evidence index; no validators or score/resource reanalysis',
        external_anchor=dict(commit=commit, commit_time=commit_time, path=state_path,
            committed_bytes_sha256=hashlib.sha256(committed).hexdigest()), runs={}, qualifications=[])
    policy_path = ROOT / 'planning/review-assets/tether-equal-policy-20261102/policy-spec.json'
    coverage_path = ROOT / 'planning/review-assets/tether-equal-policy-20261102/COVERAGE-QUALIFICATION-v2.md'
    obligations = {item['id'] for item in load(policy_path)['obligations']}
    mapped = set(re.findall(r'^\| (EP-[A-Z]+-\d+) \|', coverage_path.read_text(encoding='utf-8'), re.M))
    assert len(obligations) == 27 and mapped == obligations
    evidence['policy'] = dict(specification=pin(policy_path), coverage=pin(coverage_path),
        obligation_count=len(obligations), coverage_map_ids=sorted(mapped),
        limitation='Family labels and finite controls do not establish every clause or all-input equivalence')
    independent_paths = []
    for label in ('original', 'patched'):
        entry = state[label]
        assert entry['executed'] is False
        run = ROOT / entry['directory']
        frozen = load(run / 'FROZEN.json')
        start = load(run / 'comparison/STARTED.json')
        terminal = load(run / 'comparison/EXECUTION.json')
        analysis = load(run / 'ANALYSIS.json')
        assert pin(run / 'FROZEN.json')['sha256'] == entry['freeze_sha256'] == start['freeze_pin']['sha256']
        assert datetime.fromisoformat(commit_time) < datetime.fromisoformat(start['started_at_utc'])
        assert frozen['settings']['provider_cost_usd'] == 0
        assert len(frozen['sources']) == 103
        for relative, proof in frozen['sources'].items():
            check_pin(ROOT / relative, proof)
        for absolute, proof in frozen['runtime_proofs'].items():
            check_pin(Path(absolute), proof)
        assert terminal['status'] == 'executed' and len(terminal['after_checks']) == 10
        assert all(value is True for value in terminal['after_checks'].values())
        expected = {f"{case['control_id']}-r{rep}-{arm}" for case in frozen['cases']
                    for rep in range(1, frozen['settings']['repetitions'] + 1) for arm in frozen['implementations']}
        recorded = [item['cell'] for item in terminal['records']]
        assert len(recorded) == len(set(recorded)) == len(expected) == 1308
        assert set(recorded) == expected and terminal['expected_cells'] == terminal['terminal_cells'] == 1308
        assert len(analysis['rows']) == analysis['cells'] == 1308
        assert {row['cell'] for row in analysis['rows']} == expected
        oracle = load(run / 'oracle.json')
        assert len(oracle['cases']) == len(frozen['cases']) == 109
        assert {case['construction_stratum'] for case in oracle['cases']} == {'exposed_authored_construction'}
        oracle_obligations = {key for case in oracle['cases'] for key in case['obligation_ids']}
        assert oracle_obligations == obligations
        independent_records = []
        for item in terminal['records']:
            if not item['cell'].endswith('-independent'):
                continue
            path = run / 'comparison' / item['cell'] / 'RESULT.json'
            check_pin(path, item)
            record = load(path)
            assert record['runtime']['loaded_product_modules'] == {}
            assert record['runtime']['repository_product_source_on_path'] is False
            assert record['runtime']['isolated'] is True
            assert record['argv'][1:3] == ['-I', '-B']
            independent_records.append(record['disposition'])
        assert len(independent_records) == 327
        reconstruction_path = run / 'INDEPENDENT-RECONSTRUCTION.json'
        if reconstruction_path.exists():
            reconstructed = load(reconstruction_path)
            assert reconstructed['status'] == 'reconstructed' and reconstructed['terminal_cells'] == 1308
            assert reconstructed['primary_analysis_concordance']['status'] == 'agrees'
            reconstruction = dict(status='PASS', record=pin(reconstruction_path),
                concordance=reconstructed['primary_analysis_concordance'])
        else:
            reconstruction = dict(status='PENDING', reason='Independent reconstruction not retained yet')
        evidence['runs'][label] = dict(directory=entry['directory'], freeze=pin(run / 'FROZEN.json'),
            start=pin(run / 'comparison/STARTED.json'), started_at_utc=start['started_at_utc'],
            terminal=pin(run / 'comparison/EXECUTION.json'), analysis=pin(run / 'ANALYSIS.json'),
            sources_checked=103, runtime_proofs_checked=len(frozen['runtime_proofs']),
            unique_cases=109, oracle_counts=dict(Counter(case['decision'] for case in oracle['cases'])),
            scheduled_cells=1308, terminal_cells=1308, analysis_rows=1308,
            after_checks=terminal['after_checks'], independent_runtime_records_checked=327,
            independent_dispositions=dict(Counter(independent_records)),
            declared_primary_totals=analysis['totals'], reconstruction=reconstruction,
            preflight=pin(ROOT / entry['prefreeze_review']))
        independent_paths.extend(ROOT / relative for relative in frozen['sources']
            if Path(relative).name.startswith('independent') and relative.endswith('.py'))
    static_modules = []
    for path in sorted(set(independent_paths)):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        imports, dynamic = [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append('.' * node.level + (node.module or ''))
            elif isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
                if name in {'exec', 'eval', '__import__', 'import_module', 'Popen', 'run', 'check_output'}:
                    dynamic.append(dict(name=name, line=node.lineno))
        assert not any(name.split('.')[0] in {'asof', 'tether', 'subprocess'} for name in imports)
        assert not dynamic, str(path)
        static_modules.append(dict(**pin(path), imports=sorted(set(imports)), dynamic_execution_calls=dynamic))
    assert len(static_modules) == 8
    evidence['independent_implementation'] = dict(files=static_modules,
        actual_worker_records_without_product_modules=654,
        limitation='Code review and recorded runtime imports; not a hostile-code sandbox or independent authorship claim')
    paths = (
        'planning/review-assets/tether-equal-policy-v2-20261105/runner/QUALIFICATION-CLOSURE-20261105.json',
        'planning/review-assets/tether-equal-policy-result-review-20261105/CORPUS-V2-QUALIFICATION.json',
        'planning/review-assets/tether-equal-policy-result-review-20261105/INDEPENDENT-V2-QUALIFICATION.json',
        'planning/review-assets/tether-equal-policy-v2-20261105/reconstruction/QUALIFICATION-20261105-attempt02.json',
        'planning/review-assets/tether-replay-correction-20261105/RELEASE-AGGREGATE-FINAL01.json',
    )
    for relative in paths:
        value = load(ROOT / relative)
        assert value['status'].startswith('PASS')
        evidence['qualifications'].append(dict(**pin(ROOT / relative), status=value['status']))
    evidence['status'] = 'EVIDENCE_CHECKS_PASS_CAUSAL_REVIEW_PENDING'
    evidence['pending'] = ['Both version-specific supplemental causal reports and final manual first-reason review',
                           'Final scoped BG02 report/status update after all completion evidence is reviewed']
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(evidence, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=evidence['status'], output=pin(output),
        runs={key: dict(terminal_cells=value['terminal_cells'], reconstruction=value['reconstruction']['status'])
              for key, value in evidence['runs'].items()}), indent=2))


if __name__ == '__main__':
    main()
