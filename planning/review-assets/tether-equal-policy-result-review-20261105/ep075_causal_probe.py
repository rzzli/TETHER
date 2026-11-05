"""Post-hoc diagnostic only: remove stale prose from a copied EP075 bundle.

This never changes the frozen comparison or contributes scored observations.
Original absolute source references remain read-only references to that corpus.
"""
from __future__ import annotations

from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / 'experiments'))
from equal_policy import independent, materialize, reference, run_comparison
from tether import _semantics


def inventory(root):
    return {p.relative_to(root).as_posix(): materialize.file_hash(p)
            for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    corpus = PROJECT / 'data/benchmark/tether-equal-policy-20261102-attempt03'
    source = corpus / 'bundles/EP075'
    frozen = materialize.load(corpus / 'FROZEN.json')
    before = run_comparison.check_frozen(corpus, frozen)
    if not all(before.values()):
        raise RuntimeError('Frozen comparison pins changed before diagnostic')
    target = Path(__file__).parent / 'ep075-causal-attempt01'
    target.mkdir(exist_ok=False)
    bundle = target / 'copied-bundle'
    shutil.copytree(source, bundle)
    copied_before = inventory(bundle)
    descriptor = materialize.load(bundle / 'descriptor.json')
    baseline = {name: module.validate_bundle(bundle, descriptor)
                for name, module in [('tether', reference), ('independent', independent)]}
    run_dir = bundle / 'run'
    run = materialize.load(run_dir / 'run.json')
    inputs = materialize.load(run_dir / 'inputs.json')
    ledger = materialize.load(run_dir / 'ledger.json')
    trace = [json.loads(line) for line in (run_dir / 'trace.jsonl').read_bytes().splitlines()]
    # Match the installed check_engine_semantics reconstruction exactly; only
    # deterministic dossier bytes are refreshed, not replay configuration.
    fields = {k: run[k] for k in ('snapshot_id', 'profile', 'backend_id', 'status',
              'budget', 'calls', 'usage', 'plan', 'coverage', 'measured_usage', 'estimated_usage')}
    fields.update(case=inputs['case'], claims=ledger['claims'],
        features=materialize.load(run_dir / 'features.json'),
        prediction=materialize.load(run_dir / 'prediction.json'), trace=trace,
        configuration=inputs['configuration'])
    for key, kind in (('case', _semantics.Case), ('claims', tuple[_semantics.Claim, ...]),
        ('features', _semantics.FeatureVector), ('prediction', _semantics.Prediction),
        ('budget', _semantics.Budget), ('plan', tuple[_semantics.PlanStep, ...]),
        ('usage', _semantics.Usage), ('measured_usage', _semantics.Usage),
        ('estimated_usage', _semantics.Usage)):
        fields[key] = _semantics.decode(kind, fields[key])
    result = _semantics.RunResult(**fields)
    store = SimpleNamespace(snapshot=_semantics.decode(_semantics.Snapshot, inputs['snapshot']),
        exclusions=_semantics.decode(tuple[_semantics.Exclusion, ...], run['exclusions']))
    original = (run_dir / 'dossier.md').read_text(encoding='utf-8')
    replacement = _semantics.dossier(result, store)
    (target / 'dossier-only.diff').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), replacement.splitlines(True),
        fromfile='frozen-EP075/dossier.md', tofile='diagnostic-copy/dossier.md')), encoding='utf-8')
    (run_dir / 'dossier.md').write_bytes(replacement.encode('utf-8'))
    receipt = materialize.load(run_dir / 'receipt.json')
    receipt['outputs']['dossier.md'] = materialize.file_hash(run_dir / 'dossier.md')
    materialize.save(run_dir / 'receipt.json', receipt)
    descriptor['anchors']['receipt_sha256'] = materialize.file_hash(run_dir / 'receipt.json')
    materialize.save(bundle / 'descriptor.json', descriptor)
    observed = {name: module.validate_bundle(bundle, descriptor)
                for name, module in [('tether', reference), ('independent', independent)]}
    copied_after = inventory(bundle)
    changed = [p for p in copied_before if copied_before[p] != copied_after[p]]
    invalid_fingerprint = next(iter(inputs['configuration']['backend_provenance']['document']['responses'].values()))[0]['request_sha256']
    after = run_comparison.check_frozen(corpus, frozen)
    report = dict(schema_version=1, diagnostic='EP075 stale-prose masking',
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Post-hoc copied-bundle causal diagnostic; never a scored corpus observation',
        interpreter=sys.executable, isolated=bool(sys.flags.isolated),
        freeze_sha256=materialize.file_hash(corpus / 'FROZEN.json'),
        script_sha256=materialize.file_hash(Path(__file__)),
        frozen_checks_before=before, frozen_checks_after=after,
        baseline=baseline, after_dossier_refresh=observed,
        changed_copy_files=changed, invalid_replay_request_sha256=invalid_fingerprint,
        unchanged_original_source_references=True,
        no_provider_calls=True,
        assertion=dict(tether_accepts=observed['tether']['decision'] == 'accept',
            independent_rejects=observed['independent']['decision'] == 'reject',
            fingerprint_remains_invalid=invalid_fingerprint == 'f' * 64,
            only_dossier_and_seals_changed=sorted(changed) == ['descriptor.json', 'run/dossier.md', 'run/receipt.json'],
            frozen_inputs_unchanged=all(before.values()) and all(after.values())))
    materialize.save(target / 'RESULT.json', report)
    print(json.dumps(report, indent=2))
    return 0 if all(report['assertion'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
