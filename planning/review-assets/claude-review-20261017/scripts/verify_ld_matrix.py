"""Recompute the entire full-cis IL6R LD matrix from the stored dosages and compare with the stored matrix.

NumPy is not a project dependency; run with PYTHONPATH pointing at the previously verified cache:
  PYTHONPATH=E:/projects_data/drug_target_agents_data/cache/numpy-2.3.4-win-cp311 python verify_ld_matrix.py
Prints JSON.
"""
import json

import numpy as np

BASE = r"E:\projects_data\drug_target_agents_data\derived\regional_genetics\il6r-ra-full-cis-20261017T071600Z\qc"
dosages = np.load(BASE + r"\dosages.alt-oriented.npy")          # (variants, samples), int8
stored = np.load(BASE + r"\ld.alt-oriented.npy")                # (variants, variants), float64
recomputed = np.corrcoef(dosages.astype(np.float64))            # rows are variables
report = {
    "numpy": np.__version__,
    "dosage_shape": list(dosages.shape),
    "dosage_values": [int(v) for v in np.unique(dosages)],
    "ld_shape": list(stored.shape),
    "ld_finite": bool(np.isfinite(stored).all()),
    "ld_symmetry_max_abs_diff": float(np.abs(stored - stored.T).max()),
    "ld_diagonal_min": float(np.diag(stored).min()),
    "ld_diagonal_max": float(np.diag(stored).max()),
    "zero_variance_variants": int((dosages.astype(np.float64).var(axis=1) == 0).sum()),
    "entries_recomputed": int(recomputed.size),
    "max_abs_diff_vs_stored": float(np.abs(recomputed - stored).max()),
    "matrix_rank_tol_1e-8": int(np.linalg.matrix_rank(stored, tol=1e-8)),
    "max_possible_rank_with_503_samples": 502,
    "stored_file_bytes_consistent_with_float64_square": 2979 * 2979 * 8 + 128,
}
print(json.dumps(report, indent=1))
