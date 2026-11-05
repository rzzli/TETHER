"""Check the source-tree correction against the retained post-hoc EP075 copy."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT / 'src'), str(PROJECT / 'experiments')]
from asof.artifacts import verify_run
from asof.serde import ContractError
from equal_policy import run_comparison


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    corpus = PROJECT / 'data/benchmark/tether-equal-policy-20261102-attempt03'
    frozen = json.loads((corpus / 'FROZEN.json').read_bytes())
    diagnostic = PROJECT / 'planning/review-assets/tether-equal-policy-result-review-20261105/ep075-causal-attempt01'
    before = run_comparison.check_frozen(corpus, frozen)
    original = json.loads((diagnostic / 'RESULT.json').read_bytes())
    original_pins = {p.relative_to(diagnostic).as_posix(): sha(p) for p in diagnostic.rglob('*') if p.is_file()}
    observed = {}
    for source_bound in (True, False):
        try:
            result = verify_run(diagnostic / 'copied-bundle/run', verify_sources=source_bound)
        except ContractError as error:
            result = dict(decision='reject', error_class=type(error).__name__, reason=str(error))
        else:
            result = dict(decision='accept', result=result)
        observed['source_inclusive' if source_bound else 'archived_only'] = result
    after = run_comparison.check_frozen(corpus, frozen)
    retained_unchanged = original_pins == {p.relative_to(diagnostic).as_posix(): sha(p) for p in diagnostic.rglob('*') if p.is_file()}
    passed = (all(before.values()) and all(after.values()) and retained_unchanged and
        original['after_dossier_refresh']['tether']['decision'] == 'accept' and
        all(v['decision'] == 'reject' and 'request fingerprint' in v['reason'] for v in observed.values()))
    record = dict(schema_version=1, status='PASS' if passed else 'FAIL',
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Post-hoc source-tree correction check; original scored comparison is unchanged',
        original_diagnostic_sha256=sha(diagnostic / 'RESULT.json'),
        original_diagnostic_unchanged=retained_unchanged, frozen_checks_before=before, frozen_checks_after=after,
        observed=observed, source_sha256={name: sha(PROJECT / name) for name in
            ('src/asof/agents.py', 'src/asof/artifacts.py', 'src/asof/replay_validation.py')},
        checker_sha256=sha(Path(__file__)), python=sys.executable, isolated=bool(sys.flags.isolated))
    with Path(__file__).with_name('RETAINED-COUNTEREXAMPLE-RESULT.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(record, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
