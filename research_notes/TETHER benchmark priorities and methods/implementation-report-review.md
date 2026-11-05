# Implementation and current-result fact check

Reviewed 2026-11-05 against `reports/TETHER benchmark priorities and methods.md`, SHA-256 `90dc3f83d6f79e556fad4f5e18db64d2268764b587fb032890914db2c99c43c3`.

**PASS within this bounded scope.** Implementation-status claims match the retained 85-file inspection and targeted source reads. Current BG02 counts and the 1.65 descriptive time ratio match independently reconstructed records. This review did not re-evaluate the external biomedical papers or rerun comparisons.

Two actionable qualifications were requested and incorporated:

- `StudySession` is an LLM-oriented interface requiring a prompt, `n_predict` and conservative token reservation; a trained sparse baseline needs a new native-compute adapter and appropriate non-token accounting. The report now distinguishes this from reusable source, stable-read, journal and complete-accounting primitives.
- Existing BG02 validators support their declared native archive contract, not SciFact labels/rationales. The fixed-candidate proposal now requires separately qualified native-contract extensions; it does not imply ready-made benchmark support.

The report correctly separates existing dependence grouping, bounded caches and accounting from missing semantic support, stronger retrieval and calibrated semantic risk. It preserves the exposed-construction limitation, original replay defect, higher measured TETHER cost and absence of clinical-validation claims. SciFact acquisition is explicitly separate, downloaded rather than parsed or evaluated. The scorer's rationale-cap description agrees with official code, including its extension for longer gold rationales.

The separate [native-seam recommendation](scifact-native-seam.md) remains preliminary architecture advice, not implemented software or an approved projection exception. It identifies the mixed-container/purpose boundary, forbids invented training roles or extracted-file download receipts, and requires native projection/access tests before fitting. No runtime source, frozen pins, model files or result artifacts were edited for this review.
