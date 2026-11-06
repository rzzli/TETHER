"""Check retained BG03 closure evidence without rerunning inference or scoring."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    review_path = BASE / 'policy/FINAL-REPORT-REVIEW-20261105.json'
    review = json.loads(review_path.read_text(encoding='utf-8'))
    report = ROOT / 'planning/TETHER SciFact Native Evaluation Results 2026-11-05.md'
    acceptance_path = BASE / 'actual-attempt01/ROOT-ACCEPTANCE.json'
    acceptance = json.loads(acceptance_path.read_text(encoding='utf-8'))
    assert review['status'] == 'PASS_independent_final_report_review'
    assert digest(report) == review['report_sha256']
    assert digest(acceptance_path) == review['root_acceptance_sha256']
    assert acceptance['counts']['produced'] == acceptance['counts']['accepted'] == 300
    assert acceptance['counts']['correct_raw'] == acceptance['counts']['correct_and_admitted'] == 27
    assert acceptance['raw_metrics'] == acceptance['checked_metrics']
    integration = json.loads((BASE / 'integration-attempt01/VALIDATION.json').read_text())
    assert integration['tests'] == 148
    assert integration['failures'] == integration['errors'] == integration['skips'] == 0
    for relative, expected in integration['source_pins'].items():
        assert digest(ROOT / relative) == expected, relative
    qualification = json.loads((BASE / 'reconstruction/qualification-attempt02/QUALIFICATION.json').read_text())
    assert qualification['returncode'] == 0 and qualification['status'] == 'PASS'
    assert qualification['sources_before'] == qualification['sources_after']
    for relative, expected in qualification['sources_after'].items():
        assert digest(BASE / 'reconstruction' / relative) == expected['sha256'], relative
    state = json.loads((BASE / 'actual-attempt01/EXECUTION-STATE.json').read_text())
    assert state['status'] == 'completed_independently_reconstructed_and_report_reviewed'
    todo = (ROOT / 'TODO.md').read_text(encoding='utf-8')
    for stage in ['BG01', 'BG02', 'BG03']:
        assert f'- [x] {stage} ' in todo
    for stage in ['BG04', 'BG05', 'BG06']:
        assert f'- [ ] {stage} ' in todo
    docs = ['README.md', 'TODO.md', 'memory/MEMORY.md', 'memory/project-goals.md',
            'memory/research-log-2026-11-02-benchmark-execution.md',
            'memory/research-log-2026-11-05-scifact-components.md',
            'memory/research-log-2026-11-06-scifact-results.md', 'paper/README.md']
    result = {
        'schema_version': 1, 'status': 'PASS_BG03_scoped_completion',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'report_sha256': digest(report), 'root_acceptance_sha256': digest(acceptance_path),
        'independent_report_review_sha256': digest(review_path),
        'integration_source_pins_current': len(integration['source_pins']),
        'reconstruction_source_pins_current': len(qualification['sources_after']),
        'current_documentation': {name: digest(ROOT / name) for name in docs},
        'status_document_sha256': digest(BASE / 'STATUS.md'),
        'execution_state_sha256': digest(BASE / 'actual-attempt01/EXECUTION-STATE.json'),
        'validator_sha256': digest(Path(__file__)),
        'remaining_goal_stages': ['BG04', 'BG05', 'BG06'],
        'scope': 'Closure consistency and unchanged qualified code; original execution, source inventories and metrics are independently checked by the referenced acceptance/review. No new inference or score measurement.'}
    with (BASE / 'COMPLETION.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print('PASS: BG03 scoped completion; BG04-BG06 remain pending.')


if __name__ == '__main__':
    main()
