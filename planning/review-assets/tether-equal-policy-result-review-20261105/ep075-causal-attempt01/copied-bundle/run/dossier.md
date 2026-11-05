# AsOf dossier: FICTIONAL:CASE-1

Target: FICTIONAL:TARGET-1; indication: FICTIONAL:DISEASE-1.
Intended action: inhibit; modality: small_molecule; tissue: fictional tissue.
Origin: 2024-06-30; profile: synthetic_demo; task: T1.
Workflow: completed; backend: recorded-selection-replay-v1.

**Synthetic demonstration: the weights and observations are fixtures. This number is not a scientific prediction.**

Probability of phase_2_to_3 within 24 months: 0.7006.
Scorer: fictional-logistic-v1; calibration: none; model-feature coverage: 100.0%.

## Frozen scorer contributions

Contributions are in log odds and describe the predictor, not biological causality.

| Feature | Value | Coefficient | Contribution | Imputed |
| --- | ---: | ---: | ---: | --- |
| genetic_support | 0.75 | 0.8 | 0.6 | False |

Intercept: 0.25.

## Grounded claims

Statements below are copied from the approved normalized records. Citation grounding does not establish that a source interpretation or method is scientifically correct.

### claim-a6c5da38e7196fb1832f (genetics)

> Fictional study reports a normalized support value of 0.75; this is a software fixture.

Interpretation: supports; direction: inhibit. Dependency group: fictional-group-1; declared QC: passed.
Source: fixture_evidence/fictional-v1; artifact packet-1; observation obs-1.
SHA-256: `38bc6c3f89be726aae561a7fefef1b71ed5bb79891e016c7ac286ce5d454d2d8`.

Limitations: Synthetic conformance control; no scientific result.

Unknown fields: species: Not reported by fictional source.

## Coverage and exclusions

| Specialist | Run status | Available | Selected |
| --- | --- | ---: | ---: |
| clinical | no_observed_evidence | 0 | 0 |
| expression | no_observed_evidence | 0 | 0 |
| genetics | completed | 1 | 1 |
| literature | no_observed_evidence | 0 | 0 |
| modality | no_observed_evidence | 0 | 0 |
| pathway | no_observed_evidence | 0 | 0 |
| perturbation | no_observed_evidence | 0 | 0 |
| safety | no_observed_evidence | 0 | 0 |

Source coverage: `{"scientific_validation":"not_established","source_completeness":"selected_subset"}`.

Calls: 1; accounted cost: $0.0000; input/output tokens: 0/0.

Measured cost: $0.0000; conservatively estimated upper cost: $0.0000.

No live model provider or scientific computation is invoked by the default backend. Historical retrieval controls do not certify a model's training cutoff or knowledge. OS-level isolation is required before running arbitrary agents on locked benchmarks.
