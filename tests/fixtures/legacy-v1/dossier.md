# AsOf dossier: demo-program-001

Target: DEMO:TARGET1; indication: DEMO:DISEASE1.
Origin: 2023-01-01; profile: synthetic_demo; task: T1.
Workflow: completed; backend: offline-extractive-v1.

**Synthetic demonstration: the weights and observations are fixtures. This number is not a scientific prediction.**

Probability of phase_2_to_3 within 24 months: 0.4825.
Scorer: synthetic-logistic-v1; calibration: none; model-feature coverage: 100.0%.

## Frozen scorer contributions

Contributions are in log odds and describe the predictor, not biological causality.

| Feature | Value | Coefficient | Contribution | Imputed |
| --- | ---: | ---: | ---: | --- |
| direction_alignment | 0.6 | 0.4 | 0.24 | False |
| expression_relevance | 0.7 | 0.2 | 0.14 | False |
| genetic_support | 0.8 | 0.8 | 0.64 | False |
| literature_support | 0.6 | 0.3 | 0.18 | False |
| modality_feasibility | 0.5 | 0.2 | 0.1 | False |
| pathway_support | 0.3 | 0.1 | 0.03 | False |
| perturbation_support | 0.4 | 0.3 | 0.12 | False |
| safety_liability | 0.2 | -0.6 | -0.12 | False |

Intercept: -1.4.

## Grounded claims

Statements below are copied from the approved normalized records. Citation grounding does not establish that a source interpretation or method is scientifically correct.

### claim-cb170a33df15e02b331a (genetics)

> Fictional genetics observation for workflow testing; no biological finding is asserted.

Interpretation: uncertain; direction: uncertain. Dependency group: demo-cohort-genetics; declared QC: passed.
Source: synthetic_fixture/fixture-v1; artifact demo-evidence; observation demo-genetics-1.
SHA-256: `e76ba421e3cc5a31d9cb56f49d2308a8ab417e7dcc15457a31caa19baa15c919`.

Limitations: Invented fixture; not a scientific calculation.

### claim-8d3df5a40c1f6f9e4cc4 (perturbation)

> Fictional perturbation observation for workflow testing; no biological finding is asserted.

Interpretation: uncertain; direction: uncertain. Dependency group: demo-cohort-perturbation; declared QC: passed.
Source: synthetic_fixture/fixture-v1; artifact demo-evidence; observation demo-perturbation-1.
SHA-256: `e76ba421e3cc5a31d9cb56f49d2308a8ab417e7dcc15457a31caa19baa15c919`.

Limitations: Invented fixture; not a scientific calculation.

### claim-66804d6d7c643c52bacb (expression)

> Fictional expression observation for workflow testing; no biological finding is asserted.

Interpretation: uncertain; direction: uncertain. Dependency group: demo-cohort-expression; declared QC: passed.
Source: synthetic_fixture/fixture-v1; artifact demo-evidence; observation demo-expression-1.
SHA-256: `e76ba421e3cc5a31d9cb56f49d2308a8ab417e7dcc15457a31caa19baa15c919`.

Limitations: Invented fixture; not a scientific calculation.

### claim-7f81978ebe292bbcda24 (modality)

> Fictional modality observation for workflow testing; no biological finding is asserted.

Interpretation: uncertain; direction: uncertain. Dependency group: demo-cohort-modality; declared QC: passed.
Source: synthetic_fixture/fixture-v1; artifact demo-evidence; observation demo-modality-1.
SHA-256: `e76ba421e3cc5a31d9cb56f49d2308a8ab417e7dcc15457a31caa19baa15c919`.

Limitations: Invented fixture; not a scientific calculation.

### claim-6a3614910edd39cc907f (literature)

> Fictional literature observation for workflow testing; no biological finding is asserted.

Interpretation: uncertain; direction: uncertain. Dependency group: demo-cohort-literature; declared QC: passed.
Source: synthetic_fixture/fixture-v1; artifact demo-evidence; observation demo-literature-1.
SHA-256: `e76ba421e3cc5a31d9cb56f49d2308a8ab417e7dcc15457a31caa19baa15c919`.

Limitations: Invented fixture; not a scientific calculation.

### claim-4bfb46ebed099919f473 (literature)

> Fictional literature observation for workflow testing; no biological finding is asserted.

Interpretation: uncertain; direction: uncertain. Dependency group: demo-cohort-literature; declared QC: passed.
Source: synthetic_fixture/fixture-v1; artifact demo-evidence; observation demo-literature-duplicate.
SHA-256: `e76ba421e3cc5a31d9cb56f49d2308a8ab417e7dcc15457a31caa19baa15c919`.

Limitations: Invented fixture; not a scientific calculation.

### claim-e608554021cb58cc4d8e (clinical)

> Fictional clinical observation for workflow testing; no biological finding is asserted.

Interpretation: uncertain; direction: uncertain. Dependency group: demo-cohort-clinical; declared QC: passed.
Source: synthetic_fixture/fixture-v1; artifact demo-evidence; observation demo-clinical-1.
SHA-256: `e76ba421e3cc5a31d9cb56f49d2308a8ab417e7dcc15457a31caa19baa15c919`.

Limitations: Invented fixture; not a scientific calculation.

### claim-c10f5d431873789f35f4 (safety)

> Fictional safety observation for workflow testing; no biological finding is asserted.

Interpretation: uncertain; direction: uncertain. Dependency group: demo-cohort-safety; declared QC: passed.
Source: synthetic_fixture/fixture-v1; artifact demo-evidence; observation demo-safety-1.
SHA-256: `e76ba421e3cc5a31d9cb56f49d2308a8ab417e7dcc15457a31caa19baa15c919`.

Limitations: Invented fixture; not a scientific calculation.

### claim-43d6c2a22f92c7ad6487 (pathway)

> Fictional pathway observation for workflow testing; no biological finding is asserted.

Interpretation: uncertain; direction: uncertain. Dependency group: demo-cohort-pathway; declared QC: passed.
Source: synthetic_fixture/fixture-v1; artifact demo-evidence; observation demo-pathway-1.
SHA-256: `e76ba421e3cc5a31d9cb56f49d2308a8ab417e7dcc15457a31caa19baa15c919`.

Limitations: Invented fixture; not a scientific calculation.

## Coverage and exclusions

| Specialist | Run status | Available | Selected |
| --- | --- | ---: | ---: |
| genetics | completed | 1 | 1 |
| perturbation | completed | 1 | 1 |
| expression | completed | 1 | 1 |
| modality | completed | 1 | 1 |
| literature | completed | 2 | 2 |
| clinical | completed | 1 | 1 |
| safety | completed | 1 | 1 |
| pathway | completed | 1 | 1 |

perturbation: not_measured (demo-perturbation-unmeasured): The fictional primary-cell perturbation was not measured.

Excluded observation demo-future-record: available_after_origin.

Excluded artifact demo-future: available_after_origin.

Calls: 8; accounted cost: $0.0000; input/output tokens: 0/0.

No live model provider or scientific computation is invoked by the default backend. Historical retrieval controls do not certify a model's training cutoff or knowledge. OS-level isolation is required before running arbitrary agents on locked benchmarks.
