# Task 1: cohort and transition-label audit

Completed October 17, 2026 (local date). The original v0.4 cohort, labels and seals
are preserved. The v0.5 sensitivity protocol was frozen before the new ontology joins.

The fixed 4,419-program / 98-link audit found 1,330 programs with a unique exact
ontology mapping, 257 with ambiguous mappings and 2,832 unmapped. There are 41 exact
healthy-participant entries and 57 broad condition entries. Mapping alone does not
establish clinical diagnosis or eligibility: Open Targets includes phenotypes,
processes and measurements as well as diseases.
[Provider documentation](https://platform-docs.opentargets.org/disease-or-phenotype).

367 programs have prior-risk alerts. Four programs with recorded registry transitions
have alerts: psilocybin/TRD (estimated prior Phase 3), guselkumab/ulcerative colitis
(prior mixed Phase 2/3 under an exact synonym), lecanemab/Alzheimer disease (mixed-phase
and role-qualified prior records), and mazdutide/type 2 diabetes (estimated prior
Phase 3). An alert does not establish exclusion, experimental dosing or clinical
population equivalence. Hierarchy relations never become equivalent disease aliases.

All 98 original links retain matched-arm and separate study-wide context: route,
age words, setting, prior treatment, extension/regional context and non-drug partners.
The audit does not impute full eligibility, actual age bounds, dose/genotype equivalence
or arm-specific enrollment. Prior-risk projections were checked against original rows;
3,516 original source rows were rehashed. All 21 parent seal files passed streaming
hash verification. No training labels, recall or scientific accuracy were inferred.

Validation: eight new regression tests; full suite **194 tests, zero skips/failures/errors**,
required probes, PowerShell syntax and dependency-free installed-wheel demo passed.
See `task1-validation.json` and `task1-summary.json` in the evidence folder.
Canonical output: `data/benchmark/cohorts/registry-scope-20261018T025216Z`.
Anchor: `data/manifests/public/2026-10-17-registry-scope.json`.

Task 1 is complete for development cohort construction and source/scope auditing.
Independent scientific and locked-test evaluation remain Task 7. Task 2 follows:
measure dependent sample sizes, power scenarios and clinical feasibility using these
uncertainties. No new downloads, restored-server starts or model-provider calls.

## Task 2: sample size, power and clinical feasibility

Completed after correcting a failed small-sample calibration check. The original
v0.1 asymptotic run is retained at commit c7f6105 and its diagnostic seal; false-null
rejection reached 6.9% and 7.3% at intended alpha 5%. No frozen v0.1 result was rewritten.

Frozen v0.2 uses independent parametric null references and finite-rank Monte Carlo
p-values. These are synthetic normal-score experiments, not model predictions or a
permutation of clinical data. The paired ROC statistic follows
[DeLong et al.](https://pubmed.ncbi.nlm.nih.gov/3203132/); finite-rank Monte Carlo
construction is described in [SciPy's method documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.monte_carlo_test.html).
No SciPy dependency was installed. Exact-rank/tie, brute-force covariance, dependency,
determinism and tampered-source regressions passed.

The measured base graph has 1,001 units: 19 with recorded-start proxies, 953 with no
recorded-start proxies and 29 unresolved. Adding target links gives 627 units; adding
target and sponsor links gives 261 units, only six with recorded starts. These are
explicit dependence graphs, not identified effective sample sizes. The uncertainty-hold
view retains 3,960 programs and 16 positive base units; it is not adjudicated exclusion.

All 120 power scenarios finished. At current base sizes, estimated power spans
6.2–46.7% across the prespecified AUC/correlation/error assumptions. Sponsor/target
stress spans 3.9–16.2%; the 16-unit uncertainty-hold view spans 7.3–40.4%. Current
scenarios do not achieve the 80% planning target. Illustrative no-label-error results
at baseline AUC .65 and a .05 AUC difference:

| Positive units | No-recorded units | Correlation 0.3 | Correlation 0.7 | Correlation 0.9 |
| ---: | ---: | ---: | ---: | ---: |
| 19 | 953 | 10.0% | 14.9% | 38.5% |
| 50 | 1000 | 20.0% | 31.6% | 77.6% |
| 100 | 1000 | 27.4% | 53.2% | 97.2% |
| 200 | 1000 | 52.4% | 76.8% | 100.0% |
| 400 | 1000 | 67.8% | 98.6% | 100.0% |

Grid points are hypothetical independently scored units and cannot be converted to
registry-trial requirements using unvalidated prevalence. Estimated power and Wilson
Monte Carlo intervals are conditional on the score distribution, unit endpoint and
finite null reference; they exclude reference/distribution/label-validity uncertainty.
Independent null checks returned 5.05%, 4.9% and 4.7%; all pass the frozen inflation
check accounting for both Monte Carlo samples. No actual AUROC/AP/calibration was measured.

Two-reviewer pilot costs span 30.8–240 reviewer-hours for 185–240 cases and assumed
5–30 minutes per reviewer/case. These are scenarios, not measured adjudication time.
Clinical readiness remains unresolved: no independent scientific reference, verified
negatives/censoring, full regimen/population qualification or locked chronology.
Decision: **revise before clinical training or locked evaluation**; continue to the
Task 3 chronology/window audit. This measures feasibility rather than asserting that
T1 is impossible. Clinical probabilities and training labels remain unset.

Validation: **201 tests passed, zero skips/failures/errors**, required probes,
PowerShell syntax and installed-wheel checks. The corrected run's eight files passed
seal verification. See task2-corrected-validation.json and task2-summary.json.
Canonical output: `data/benchmark/cohorts/registry-power-calibrated-20261018T030335Z`.


## Task 3 - validated local chronology/protocol decision

Completed after 208 full-suite tests, required probes, PowerShell checks and wheel
verification. See `Evaluation Chronology and Local Preregistration 2026-10-17.md`,
`protocols/evaluation-v0.1.json`, its public freeze anchor, and task3-validation.json.
The official Qwen September 2024 immutable weights support a candidate January
2025-January 2026 window. Exact training cutoff is unknown, not invented. Three
Q4_K_M shards total 8,988,110,496 bytes; download/runtime validation belongs Task 4.
A fresh January 2026 full archive hash/member CRC and PostgreSQL TOC check passed;
zero clinical outcome queries, no database restoration. Open Targets 24.09 release
and archive layout were checked, not collected/parsed. No current annotation fallback.

This freezes local development registration and a gated clinical design, not an OSF
submission or a locked clinical evaluation. Seven clinical activation gates remain
unmet, including independent labels, historical inputs, qualified new-window power
and origin selection. The original window remains exposed development. Virtual
Biotech with common local weights will be explicitly labeled an adapted comparison.
Proceed to Task 4's bounded development pilot; clinical execution remains disabled.


## Task 4 - validated bounded local specialist

The 229-test full suite, required probes, PowerShell and wheel checks passed. Four
hosted Windows/Linux core/full jobs passed at 48359ca. Official pinned Qwen14B Q4_K_M
weights and llama.cpp b11717 Vulkan ran locally with $0 provider spending. Ten original
dossiers passed separate-process source-inclusive verification; all owned servers
stopped. The original format admitted one candidate per call, so it is retained as
a diagnostic rather than a selection-quality benchmark. Its 22 calls used 61,022
input and 1,247 output tokens; native time summed to 64.797 seconds, versus 3,075.469
seconds end to end including source work. Inputs span 8,256,817,498 unique bytes.

Lossless common-field transport preserves every scientific field and exact request
fingerprint on reconstruction. All-ten capacity probes fit 66 versus 22 candidates
at unchanged byte limits; 20 of 24 populated categories fit multiple candidates.
Three cases, fixed before new-format inference in evaluation-v0.2, passed fresh
source-inclusive verification and the frozen multi-candidate acceptance checks.
No two formats are pooled as comparative or independent scientific evaluation.

A new regression reproduced missing native prompt-truncation rejection, then passed
after correction. All original responses report no truncation and pass the stronger
archived response/retrieval checks. Exact OSMR replay reproduced ledger, features
and null prediction with zero model calls. Reports/seal-path bugs found during real
summary validation were fixed and covered by portable-path and incomplete/seal tests.
See `Local Model Specialist Pilot 2026-10-17.md` and task4-* evidence. All real
probabilities remain null and numerical features unmeasured. Proceed to Task 5.


## Task 5 - conditional feasibility decision validated; training deferred

Rehashed the full-cis IL6R bundle's 38 sealed files and checked 2,979 variants /
503 EUR external-reference samples. Independently recomputed 4,096 LD entries;
maximum absolute difference 3.4416913763379853e-15. Thirteen targeted genetics/QC
and power regressions passed. No originals, QC arrays or prior sealed summaries
were rewritten. See task5-feasibility.json and task5-validation.json.

Predictive genetics features and clinical scorer derivation/training are **not
feasible under the current qualifications**, so the task's conditional branch is
explicitly deferred. The one transcript-exposure region does not validate protein
perturbation or drug inhibition. Publisher metadata mismatch, study-specific LD,
cohort overlap, per-variant GWAS N/EAF, scientific interpretation and historical
eligibility remain unresolved. There are zero qualified clinical training labels,
no adjudicated negatives/censoring and no independent clinical reference.

## Task 6 - blocked; ordered execution stopped

The requested scientific comparison cannot be completed from the available inputs.
All real predictions are withheld, there is no validated/scientifically qualified
scorer, clinical reference or locked origin cohort, and conditional proxy-size power
does not reach the planning target. Source-copy consistency, metadata, synthetic
scores and AI-assisted judgments cannot substitute for those artifacts.

No Virtual Biotech performance, clinical AUROC/Brier, scientific ablation effect or
independent T6 quality result is claimed. Engineering timing/packet measurements
remain usable within their stated scope. Task 6 is unchecked and blocked, and
Tasks 7-8 remain unchecked/unstarted. This is the user's prescribed stop-on-blocker
exception, not completion of the whole project. See task6-blocker.json.

Required resolution: independently adjudicated outcomes/negative-or-censoring rules
and an exposure-audited origin cohort; qualify historical predictors and re-size the
new window, then freeze/train/calibrate and compare only if those gates pass.
A separate independent T6 reference is needed for scientific H5 claims. These needs
are independent of $0 local inference and cannot be manufactured by additional calls.


## Files and preservation

Runtime changes: `src/tether_engine/local_model.py`, `retrieval.py`, `wire.py`, `workflow.py`,
`artifacts.py` and `cli.py`. Feasibility utilities add fixed-cohort scope, conditional
power and chronology checks. Framework utilities prepare pinned assets, own the
local server, run/replay cases, probe transport and verify pilot summaries. Regression
coverage, protocol/freeze manifests, README/framework documentation and project memory
were updated. Original proposals, old fixtures and sealed scientific outputs remain.

The final 229-test suite passed with no skips/failures/errors, plus required probes,
PowerShell syntax and installed-wheel/demo checks. The regional gate also passed
13 targeted tests and the retained-byte/independent-LD recheck. See closeout-validation.

Private incremental recovery is uploaded at the ordered-execution-20261017 release.
Downloaded assets restored and rehashed all 308 files / 181,211,105 bytes and six
sealed products; code clone and Git fsck passed. The ZIP is 72,142,241 bytes. The
independently retained asset index SHA-256 is
`707d55079a39bdf0c0c401183d597696ade347a654d829b28b19194d72815185`.
This supplements the prior recovery-20261017 and registry-sizing-20261017 releases.
It excludes bulk originals, full AACT archives/databases, model/native binaries and
credentials, and does not establish new scientific validation. The backed source
checkpoint is b31d1d56583ba23c64adf23d39fe70517ee4adf9; later handoff metadata is in
private Git and recorded separately. See incremental-recovery-verification.json.


## October 18 resumption — Task 6 development diagnostics verified

The earlier Task 6 stop above is preserved as dated history. On resumption,
implemented exact-request lexical/provider-score baselines and deterministic
no-literature/no-perturbation masks, plus a pinned Virtual Biotech configuration
and local-directory compatibility audit. The 29 archived calls all selected every
candidate offered and never had more than three candidates.

Four fixed wider-candidate cases then passed fresh source-inclusive verification
under evaluation-v0.3. Of 11 requests, five required prioritization. Model/lexical
selection sets matched 11/11 and model/provider-score sets 8/11; no accuracy or
quality inference follows. Independent diagnostic regeneration checked 40 requests
in three separate groups. All 246 tests, required probes, packaging and four hosted
CI jobs passed. The owned server stopped; probabilities null; provider spending $0.

Task 6 stays unchecked: matched adapted Virtual Biotech execution and scientific
reference/scoring/chronology/power qualifications are incomplete. Tasks 7–8 remain
unstarted. See [[Task 6 Development Comparisons 2026-10-18]] and the new retained
`planning/review-assets/task6-resumption-20261018/task6-blocker-recheck.json`.
