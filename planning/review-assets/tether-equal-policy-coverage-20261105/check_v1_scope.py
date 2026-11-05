"""Unscored archived-v1 scope control, outside the v2 denominator."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'experiments'))
from equal_policy import independent, reference


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = ROOT / 'planning/review-assets/tether-equal-policy-coverage-20261105/V1-SCOPE-CONTROL.json'
    if output.exists():
        raise FileExistsError(output)
    original = ROOT / 'tests/fixtures/legacy-v1'
    run = ROOT / 'data/cache/tether-equal-policy-v1-scope-20261105/run'
    run.parent.mkdir(exist_ok=False)
    shutil.copytree(original, run)
    before = {p.name: digest(p) for p in run.iterdir() if p.is_file()}
    descriptor = dict(schema_version=1, control_id='SCOPE-LEGACY-V1', operation='verify_run',
        variant='core_v2_catalog1', paths={'run_dir': 'run'}, options={}, anchors={})
    from asof.agents import ExtractiveBackend
    with patch.object(ExtractiveBackend, 'quote', side_effect=AssertionError('No backend permitted')) as quote, \
         patch.object(ExtractiveBackend, 'select', side_effect=AssertionError('No backend permitted')) as select:
        responses = {name: module.validate_bundle(run.parent, descriptor)
                     for name, module in [('reference', reference), ('independent', independent)]}
        assert quote.call_count == select.call_count == 0
    after = {p.name: digest(p) for p in run.iterdir() if p.is_file()}
    passed = before == after and all(row['decision'] == 'unsupported' for row in responses.values())
    record = dict(schema_version=1, status='PASS' if passed else 'FAIL',
        scope='Separate archived-v1 interface control; excluded from every primary v2 performance/accuracy denominator',
        expected_decision='unsupported', observed=responses, descriptor=descriptor,
        original_fixture='tests/fixtures/legacy-v1', copied_fixture=str(run), fixture_sha256=before,
        unchanged=before == after, backend_quote_calls=quote.call_count, backend_select_calls=select.call_count,
        reference_sha256=digest(ROOT / 'experiments/equal_policy/reference.py'),
        independent_sha256=digest(ROOT / 'experiments/equal_policy/independent.py'),
        checker_sha256=digest(Path(__file__)), runtime=reference.runtime_identity(),
        limitation='This checks explicit scope handling; the adapters do not semantically verify v1. Existing v1 receipt-integrity qualification remains separate.')
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': record['status'], 'decisions': {k: v['decision'] for k, v in responses.items()}}))
    return not passed


if __name__ == '__main__':
    raise SystemExit(main())
