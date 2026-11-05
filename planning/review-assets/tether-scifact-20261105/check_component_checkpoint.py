"""Validate documentation/component checkpoint without fitting or reading answers."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    gate_path = BASE / 'components-attempt03/VALIDATION.json'
    gate = json.loads(gate_path.read_text(encoding='utf-8'))
    assert gate['status'] == 'PASS' and gate['sources_unchanged']
    assert gate['failures'] == gate['errors'] == gate['skips'] == 0
    assert all(digest(ROOT / name) == value for name, value in gate['source_pins'].items())
    old = json.loads((ROOT / 'research_notes/TETHER benchmark priorities and methods/implementation-scope.json').read_text(encoding='utf-8'))
    assert all(digest(ROOT / name) == value for name, value in old['source_files'].items())
    docs = ('README.md', 'TODO.md', 'memory/project-goals.md', 'memory/MEMORY.md',
            'memory/research-log-2026-11-05-scifact-components.md',
            'planning/review-assets/tether-scifact-20261105/STATUS.md')
    todo = (ROOT / 'TODO.md').read_text(encoding='utf-8')
    for stage in ('BG03', 'BG04', 'BG05', 'BG06'):
        assert f'- [ ] {stage}' in todo
    required = ('data/QUALIFICATION-20261105.json', 'scoring/QUALIFICATION.json',
                'ENVIRONMENT-QUALIFICATION-02.json', 'policy/red-watchdog-marker01.log',
                'policy/green-watchdog-marker01.log')
    for name in required:
        assert (BASE / name).is_file()
    report = {'schema_version': 1, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS', 'scope': 'component_checkpoint_not_native_evaluation',
              'tests': gate['tests'], 'test_gate_sha256': digest(gate_path),
              'maintained_core_facade_sources_unchanged': len(old['source_files']),
              'documents': {name: digest(ROOT / name) for name in docs},
              'remaining': ['controller_rehearsal', 'real_fit_tune_dev', 'independent_reconstruction',
                            'LAB_Bench', 'Inspect', 'final_goal_audit']}
    out = BASE / 'CHECKPOINT-COMPONENTS-20261105.json'
    with out.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
