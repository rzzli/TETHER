# Task 6 development comparisons — October 18, 2026

Task 6's development comparison tools, four-case challenge and pinned competitor
configuration audit are implemented and validated. Scientific comparison remains incomplete:
there is no independent T6 quality reference, qualified clinical reference or
validated clinical scorer. Tasks 7–8 have not started.

## What the archived comparison establishes

`development-comparison-v0.1.json` specifies a post hoc, exposed-development
diagnostic. It compares selections on the exact requests already shown to the
local model. Request fingerprints, candidate scientific records, responses,
selection IDs and measured accounting must agree with the sealed source-verified
parent runs. The new diagnostic rechecks archived proofs, not the raw originals.

| Separate transport group | Cases | Requests | Model selected every candidate | Candidate sets larger than the three-ID output cap |
| --- | ---: | ---: | ---: | ---: |
| Original canonical diagnostic | 10 | 22 | 22 | 0 |
| Focused lossless-wire diagnostic | 3 | 7 | 7 | 0 |

In each group the lexical top-three and applicable provider-score top-three
baselines return the same selection sets as the model. Agreement is **not
accuracy**. These requests do not force prioritization: every candidate set fits
the output cap. The uncapped extractive reference returns every offered candidate
and is explicitly distinguished from the two baselines with matched output caps.

Provider-score selection applies only when every candidate has a finite numeric
score and belongs to the same known datasource. Otherwise it abstains; scores
from different sources are not rescaled or silently compared. Provider scores
remain descriptive metrics, never effects, evidence weights or predictions.

The tool also computes no-literature and no-perturbation post-selection masks.
These are actual deterministic retention calculations, **not** end-to-end model
ablation runs or scientific effects. The archived attempts have no retries, so a
no-reviewer-retries comparison is uninformative. Causal-genetics and scorer
ablations remain inapplicable because their scientific inputs are unqualified.

## Fixed wider-candidate challenge

`evaluation-v0.3.json` freezes four exposed cases before new inference:
PCSK9/antibody, IL6R/antibody, CFTR/small molecule and GLP1R/peptide. The retained
all-ten capacity probe identified at least one request with four or five candidates
for each. Only one PCSK9 modality is included. This selection uses measured request
width, not quality labels or outcomes.

The source world, eligible records, Qwen revision, runtime, three-ID selection cap,
12,000-byte lossless wire cap, existing budgets and $0 provider spending are
unchanged. Numerical prediction features stay unset and probabilities null.
Each new dossier must pass a fresh source-inclusive verification in a separate
process. Subsequent baseline comparison is conditional on its exact sent requests.
This is an engineering challenge on already exposed hypotheses; it does not create
independent cases, quality truth or a locked clinical evaluation.

All four cases finalized and passed separate-process source-inclusive semantic
verification. The owned server stopped. The challenge made 11 local calls with
46,773 input and 1,519 output tokens. Native prompt/generation time totaled
40.171877 seconds; total launch-to-shutdown time was 1,301.016 seconds (21.7 minutes),
including asset hashing, source admission and verification. No provider was billed.
A process-memory high-water sample is retained with its timing limitation; no
continuous GPU or final whole-process memory peak is claimed.

| Challenge case | Requests | Requests offering more than three candidates | Model/lexical identical selection sets |
| --- | ---: | ---: | ---: |
| PCSK9 antibody | 2 | 1 | 2/2 |
| IL6R antibody | 2 | 1 | 2/2 |
| CFTR small molecule | 4 | 2 | 4/4 |
| GLP1R peptide | 3 | 1 | 3/3 |

The model matched lexical top-three sets on **11/11** challenge requests and
provider-score top-three sets on **8/11**. Five requests required prioritization;
the remaining six fit the cap. The uncapped extractive reference matched six sets,
as expected when all candidates fit. These are observed selection agreements on
four exposed hypotheses, with no hypothesis test, relevance accuracy or superiority
claim. This pilot establishes no selection-set advantage over the lexical rule.

No-literature masks removed three selected statements per challenge case.
No-perturbation masks removed two for CFTR and GLP1R and zero for PCSK9 and IL6R.
These counts are retained evidence changes, not changes in biological validity,
quality or clinical prediction. No reviewer retries occurred.

`development-comparison-v0.2.json` retains all three transport/challenge groups
separately. Independent regeneration checked 40 paired request analyses and their
masks across the three groups. It rechecked archived receipts/proofs; the four new
dossiers had already passed fresh original-source verification in separate processes.

Retained anchors:

- Challenge seal: `bfc3a472797aba837ce3b9354ae5dbdccb4d3bab6c3299388b1781c8f6771667`.
- Comparison seal: `3500928aca5be00e96d6677368eda04b9418030085c8d13c4f7bb89c3a9ed022`.
- Public provenance pointer: `data/manifests/public/2026-10-18-development-comparison.json`.
- New dossiers: `runs/local-wire-pilot-20261018T153612Z/<case_id>/dossier.md`.

## Virtual Biotech compatibility

The audit archives five official files from commit
`71f9da68c95c5ee0ef4c1d9b8f45f10693de022d`, records their byte hashes, and parses
configuration with Python AST without importing or executing competitor code.

The pinned [model configuration](https://github.com/harrisongzhang/TheVirtualBiotech/blob/71f9da68c95c5ee0ef4c1d9b8f45f10693de022d/src/config/models.py)
defaults to Sonnet 4.5. The [agent registry](https://github.com/harrisongzhang/TheVirtualBiotech/blob/71f9da68c95c5ee0ef4c1d9b8f45f10693de022d/src/agents/registry.py)
fixes chief-of-staff and scientific-reviewer to Haiku and grants filesystem/shell
tools, with web tools for some roles. Its documented live workflow needs API
access; unmodified execution cannot meet this session's offline, $0-provider
boundary. No competitor SDK was initialized and no credentials were read.

The [dataset configuration](https://github.com/harrisongzhang/TheVirtualBiotech/blob/71f9da68c95c5ee0ef4c1d9b8f45f10693de022d/src/config/datasets.py)
requires 38 directories. The selected local 25.09 output root has Parquet files
under 34. `variant`, `study`, `colocalisation_coloc` and
`colocalisation_ecaviar` have no Parquet files there. This inventory establishes
presence and sizes only; it does not qualify completeness, receipts, hashes or
schemas, and does not alter catalog collection status.

A future adapted local arm must replace execution for every contributing role,
constrain tools and source access, match the admitted evidence world and budgets,
exclude known-drug/ChEMBL/outcome leakage, and pass canary/source-binding tests.
It must be labeled **adapted**, with all deviations retained. Renaming the AsOf
selector or using upstream role names would not establish a Virtual Biotech run.

## Tools, evidence and outstanding gates

New utilities are `tools/framework/compare_development.py` and
`tools/framework/audit_virtual_biotech.py`. The comparison retains status on
failure, refuses an existing output directory, archives its executed source, seals
outputs, and can regenerate paired rows and masks during verification. Regression
tests cover source identity, missing/incomparable scores, cap and chronology-task
boundaries, mutation, response binding, truncation, incomplete runs and report
accounting. The audit never runs fetched code.

Retained summaries and anchors are under
`planning/review-assets/task6-resumption-20261018/`. The first comparison attempt
failed because older canonical pilot reports omitted the optional wire-format
field. Its failure output remains untouched. The corrected reader uses the
verified archived configuration and has a regression test.

All 246 full-suite tests passed with zero failures/errors/skips, plus required
probes, PowerShell syntax and installed-wheel/demo checks. Seventeen new regression
tests cover the comparison/audit utilities. All four Windows/Linux core/full hosted
jobs passed at code checkpoint `457fcb7329c69d5841efd9702c43bcba971cde1a`.

## Why ordered execution stops here

The technical development substeps are finished. The complete requested Task 6 is
**not** finished. Its adapted Virtual Biotech execution arm is not implemented;
unmodified provider execution is outside the current boundary. A scientifically
meaningful matched implementation and its canary/containment validation remain
work, not an achieved comparator result.

There are also no independent T6 reference judgments, qualified clinical outcomes/
negatives/censoring, activated historical prediction cohort, qualified scorer or
adequately powered clinical comparison. The labels and gold-evidence directories
still contain placeholders only. AI-assisted review and model agreement cannot
supply those references. Repeating more model calls on this exposed pack would
not resolve that limitation. The prior feasibility and training no-go decisions
remain in force.

Under the user's stop-on-blocker rule, stop at Task 6 after the validated development
work. Keep Task 6 and Tasks 7–8 unchecked. Resume the scientific comparison after
reference qualification and the relevant chronology/scoring/power gates; qualify
the adapted comparator against those same cases, inputs and budgets. No task is
silently skipped and no whole-project completion is claimed.

Task 6 remains unchecked until a matched executable comparator and the appropriate
qualified scientific references support the requested analyses. Clinical AUROC/
Brier remain unavailable; independent relevance/error metrics remain unavailable.
Tasks 1–5 retain their documented scopes and conditional decisions. The downloader,
transport receipts and stopped periodic monitor are untouched.


## Preservation and final checks

All four hosted Windows/Linux jobs also passed at the artifact/documentation
checkpoint `66634ae903e8f14b030e19195b8d2f73d7805a2b`. The private
`task6-development-20261018` recovery release was downloaded and restored: all
119 retained files (31,921,594 bytes), four product seals, the source clone and
Git fsck passed. Compressed evidence is 5,908,482 bytes. Independently retained
asset-index SHA-256:
`dc2ce6ad6b84eb57c4f60720ba06e3bc31794e5439c1c65c0ce24ab482c259c8`.

This is an increment depending on previous recovery releases. Full biological
originals, AACT archives/databases, model/native binaries and credentials are
excluded; it is not a complete original-data backup or new scientific validation.
The final handoff metadata is retained separately in private Git. The owned
loopback server port was independently confirmed closed. See `closeout.json` and
`incremental-recovery-verification.json` in the retained Task 6 evidence directory.
