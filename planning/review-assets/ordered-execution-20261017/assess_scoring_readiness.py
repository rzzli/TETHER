"""Revalidate retained regional QC and decide the conditional scoring feasibility gate.

No acquisition, source rewrites, instrument selection, MR, colocalization or training.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from asof.serde import read_json, safe_child, sha256_file


def main():
    out = Path('planning/review-assets/ordered-execution-20261017/task5-feasibility.json')
    if out.exists():
        raise FileExistsError(out)
    anchor_path = Path('data/manifests/public/2026-10-17-full-cis-revision.json')
    anchor = read_json(anchor_path); pin = anchor['evidence_anchor']; root = Path(pin['root'])
    seal = root / pin['manifest']
    if sha256_file(seal) != pin['sha256']:
        raise ValueError('Full-cis source seal changed')
    seen = set()
    for item in read_json(seal)['files']:
        relative = item['path'].replace('\\', '/'); p = safe_child(root, relative)
        if relative in seen or p.stat().st_size != item['bytes'] or sha256_file(p) != item['sha256']:
            raise ValueError('Changed/duplicate full-cis evidence')
        seen.add(relative)
    if len(seen) != pin['files']:
        raise ValueError('Full-cis evidence count differs')
    sys.path.insert(0, 'E:/projects_data/drug_target_agents_data/cache/numpy-2.3.4-win-cp311')
    import numpy as np
    if np.__version__ != '2.3.4':
        raise ValueError('Unexpected isolated NumPy version')
    variants = read_json(root / 'qc/variant-order.json'); samples = read_json(root / 'qc/sample-order.json')
    dosage = np.load(root / 'qc/dosages.alt-oriented.npy', allow_pickle=False)
    ld = np.load(root / 'qc/ld.alt-oriented.npy', allow_pickle=False)
    if dosage.shape != (2979, 503) or ld.shape != (2979, 2979) or len(variants) != 2979 or len(samples) != 503:
        raise ValueError('Unexpected regional matrix shape/order')
    if not np.isin(dosage, [0, 1, 2]).all() or not np.isfinite(ld).all():
        raise ValueError('Invalid dosage or LD value')
    indices = np.unique(np.linspace(0, len(variants) - 1, 64, dtype=int))
    independent = np.corrcoef(dosage[indices].astype(float))
    error = float(np.max(np.abs(independent - ld[np.ix_(indices, indices)])))
    if error >= 1e-12:
        raise ValueError('Independent LD recomputation differs')
    power_path = Path('planning/review-assets/ordered-execution-20261017/task2-summary.json')
    power = read_json(power_path); clinical = power['clinical_readiness']
    if power['training_labels'] != 0 or power['decision'] != 'revise_before_clinical_training_or_locked_evaluation':
        raise ValueError('Review new clinical readiness evidence before using this fixed gate decision')
    gate = {
        'reviewed_causal_genetics_feature_contract': anchor['summary']['scientific_validation'] == 'established',
        'qualified_independent_clinical_reference': clinical['independent_scientific_review'],
        'adjudicated_negatives_or_censoring': clinical['adjudicated_negatives_or_censoring'],
        'full_regimen_population_equivalence': clinical['full_regimen_population_equivalence'],
        'eligible_calibration_labels_available': power['training_labels'] > 0,
        'qualified_power_gate_passed': False,
    }
    if any(gate.values()):
        raise ValueError('Readiness changed; a new scientific review is required')
    result = {'status': 'conditional_feasibility_assessment_passed_training_deferred',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'evidence': [{'path': str(anchor_path), 'sha256': sha256_file(anchor_path)},
                     {'path': str(power_path), 'sha256': sha256_file(power_path)}],
        'regional_files_rehashed': len(seen), 'qc_variants': len(variants), 'external_eur_ld_samples': len(samples),
        'independent_ld_entries_checked': int(len(indices) ** 2), 'max_ld_absolute_difference': error,
        'technical_qc': 'passed_with_retained_source_exceptions', 'scientific_validation': 'not_established',
        'source_exceptions_and_limits': anchor['summary']['remaining'], 'gates': gate,
        'decision': 'Do not derive predictive causal-genetics features or train/calibrate a clinical scorer from these inputs',
        'training_labels': 0, 'new_numeric_prediction_features': 0, 'trained_or_calibrated_models': 0,
        'provider_spend_usd': 0, 'source_files_modified': False,
        'scope': 'One transcript-exposure/RA technical region is not validation of protein perturbation, drug blockade or cross-target clinical features'}
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'regional_files_rehashed', 'independent_ld_entries_checked', 'max_ld_absolute_difference')}))


if __name__ == '__main__':
    main()
