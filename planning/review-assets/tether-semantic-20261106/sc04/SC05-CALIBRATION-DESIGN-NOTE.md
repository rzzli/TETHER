# SC05 calibration design recommendation - not activation or final freeze

Prospective specification recorded on 6 November 2026 while SC04 is active.
This document removes design ambiguity for the separate SciFact calibration
component. It does not start SC05 or supersede the execution gate. No calibration
or development outcomes, native probability files, or per-case predictions were
inspected for this recommendation. No scalar confidence, fitting, model inference
or production analysis was performed. The inputs were retained prerequisite
reports and implementation source, plus primary methodological publications.

## One score and one endpoint

Keep the qualified SC03 `fever_sci` checkpoint, FP32, frozen top-five retrieval,
4,096-token maximum, label order `CONTRADICT, NEI, SUPPORT`, argmax with the first
label winning ties, and sentence threshold `>= 0.5`. Do not alter predictions.

For each claim and its five retrieved documents, let `p[j,k]` be the preserved
three-class probabilities, and `k[j]` the native decoded label. Use exactly:

```
s = min(p[j, k[j]] for j in the five scheduled documents)
x = log(clip(s, 1e-6, 1-1e-6) / (1-clip(s, 1e-6, 1-1e-6)))
```

Keep unmodified `s` and the clipping flag. This is a confidence proxy for the
whole claim; it includes NEI distractors and omits rationale confidence and
unretrieved documents. Do not multiply probabilities, add rationale features,
or select another aggregation after looking at correctness.

The binary target `y` is **successful production and admission plus exact
claim-level correctness**: identical gold/predicted evidence-document sets,
correct label for every evidence document, and at least one complete permitted
gold rationale within the native prefix. For document `d`, that prefix length is
`max(3, min(length of each gold rationale for d))`. Empty gold and empty predicted
evidence count as correct only with successful production/admission. This is the
existing supplemental strict endpoint, not native aggregate F1. Reconstruct it
independently against both retained scoring implementations.

All 69 calibration IDs and 49 source/text components remain scheduled. Require
five valid, identity-bound native pairs for every claim before fitting. Missing
pairs, capacity/transport failure, malformed probabilities or missing source
proofs leave `s` and calibrated probability **null**, with the attempt incomplete;
never fit just the successful subset or impute confidence zero. Retain every
scheduled terminal status and evaluable strict outcome; an unproduced claim has
operational strict success zero, not a fabricated biological answer. No automatic
redispatch. A later authorized recovery uses a fresh attempt and preserves prior
records. Valid numerical candidates that fail admission retain `y=0`; selection
still requires admission, irrespective of score.

## Fixed mapping, objective and optimizer

Use a two-parameter monotone logistic mapping of this single input:

```
q(s) = sigmoid(a + b*x), with b >= 0
J(a,b) = mean_i[softplus(a+b*x_i) - y_i*(a+b*x_i)]
         + 0.01/2 * (a*a + (b-1)*(b-1))
```

The mean gives each claim equal weight; preserve components for uncertainty.
The fixed ridge penalty shrinks toward identity on the clipped probability scale
and regularizes both parameters, including complete separation. This is a
project-specific regularized sigmoid calibrator, not a claim to reproduce an
unmodified Platt or temperature-scaling implementation. No search over penalties,
priors, bins, endpoints, score definitions or class weights is allowed. Scaling
methods motivate a low-parameter mapping; they do not validate this particular
strict endpoint. [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html).

Use float64 and stable sigmoid/softplus. Deterministic projected gradient descent:

1. Initialize `(a,b)=(0,1)`; sum examples in frozen claim-ID order using accurate
   summation. Once per fit, calculate `L=0.25*mean_i(1+x_i*x_i)+0.01` from that
   fit's scalar inputs only, before using its labels. Require finite positive
   `L` and retain it. For a leave-one-component-out fit, use only its training
   components to calculate this deterministic bound.
2. Let `g` be the exact two-component objective gradient. Update
   `theta_next = project_b_nonnegative(theta - g/L)`.
3. Stop when `L * max(abs(theta_next-theta)) <= 1e-8`; recompute that projected
   gradient residual at the retained solution before success. At most 200,000
   updates and 120 seconds per fit. The fixed step is a global smoothness bound;
   no outcome-dependent line search or optimizer selection is needed.
4. Require finite objective/parameters and no objective increase exceeding
   `1e-12 * max(1, abs(previous_objective))`. A bound breach, nonfinite value,
   deadline or failed convergence records failure and publishes no usable map.
   Do not substitute a different optimizer or silently relax tolerances.

The tighter bound is valid globally in `(a,b)`, not just near initialization.
Write `v_i=(1,x_i)` and `q_i=sigmoid(a+b*x_i)`. The Hessian is
`H=mean_i[q_i*(1-q_i)*v_i*v_i^T]+0.01*I`. Since
`0 <= q_i*(1-q_i) <= 1/4`, positive-semidefinite ordering gives
`H <= 0.25*mean_i[v_i*v_i^T]+0.01*I`. The largest eigenvalue of a
positive-semidefinite matrix is at most its trace, so
`lambda_max(H) <= 0.25*mean_i(1+x_i*x_i)+0.01 = L`.
Thus `1/L` is a fixed safe projected-gradient step in exact arithmetic and
uses no label-dependent tuning. The existing numerical decrease/convergence
checks remain necessary. The penalty makes the objective strongly convex on
the convex feasible set `b>=0`, giving a unique exact minimizer. This replaces
the earlier worst-case clipping-bound step without changing that objective or
minimizer; finite-precision iterates need not be byte-identical. The new `L` is
no greater than the earlier bound because every clipped `abs(x_i)` is at most
`log((1-1e-6)/1e-6)`. No actual scalar or step size was calculated for this
mathematical refinement.

Seal coefficients, objective, residual, iterations, input/label/group hashes,
constants and code/environment before applying the map to the 300 retained
SC03 primary predictions. No new development inference is needed. A constant
score, one-class calibration outcome, or `b=0` is retained and flagged as
degenerate rather than triggering another method. Regularization makes fitting
finite; it cannot supply empirical discrimination absent from the data.

## Selection and reliability reporting

Use **0.90 as the prespecified primary probability cutoff**. Report the complete
fixed grid `{0.00, 0.50, 0.70, 0.90, 0.95}` for both raw `s` and calibrated `q`.
Accept only successfully produced/admitted cases with available score `>= t`;
all others are withheld. Never select a threshold from calibration or development
performance. The numeric cutoff is not a guaranteed error ceiling.

At each cutoff report scheduled/available/accepted claims and distinct components,
correct and incorrect accepted, correct and incorrect withheld, coverage,
strict-correct yield, and conditional error/precision. Zero accepted claims means
**undefined** conditional risk and precision, with zero coverage/yield. Preserve
operational failure separately from semantic rejection.

On the full available 300-case score set report paired raw/calibrated Brier score
and log loss; log loss alone clips inputs to `[1e-6,1-1e-6]` and reports clip counts.
Any score missingness stays visible against the scheduled denominator; do not
label available-case proper scores full-cohort scores. Use five fixed reliability
bins `[0,.2), [.2,.4), [.4,.6), [.6,.8), [.8,1]`, showing count, distinct components,
mean score and empirical strict correctness. Empty bins remain empty. ECE may be
shown descriptively with this exact binning, never as proof of calibration.
[Calibration-evaluation cautions](https://proceedings.mlr.press/v89/vaicenavicius19a.html),
[finite-sample estimation limits](https://proceedings.neurips.cc/paper_files/paper/2019/hash/f8c0c968632845cd133308b1a494967f-Abstract.html).

Monotone `q` preserves clipped-score ordering when `b>0`; it cannot create better
discrimination. Clipping can merge extreme-score ties, so exact risk-coverage
curve equality applies only when that tie structure is unchanged. It can improve
probability accuracy and change fixed numerical operating points. A flat `b=0`
collapses ordering. Do not claim
selection-ranking improvement from a relabelled confidence scale. This is
descriptive selective prediction, not a reproduction of a risk-guaranteed
procedure. [Selective classification](https://arxiv.org/abs/1705.08500).

## Dependence, fitting uncertainty and small-sample limits

For development results, use the immutable preparation's source/text components
(the existing SC03 code expects 247), verified without selecting by outcome.
Draw that many whole components with replacement 10,000 times using seed
`20261106`; keep all member claims and recompute claim-weighted ratios per draw.
Use identical draws for raw/calibrated differences and linear-interpolated 2.5%
and 97.5% percentiles. These intervals are **conditional on the one fitted map**;
they do not include calibration-set estimation, source-group misspecification,
model exposure or future distribution shift.

For conditional risk/bin correctness, show the number of undefined bootstrap
replicates. Publish an interval only when at least two observed components
contribute to that denominator and all 10,000 draws have a positive denominator;
otherwise leave it undefined. Coverage/yield retain their full denominators.
Keep every fixed operating point, including sparse or empty ones; do not promote
the best-performing cutoff or claim simultaneous guarantees across the grid.

Add exactly 49 leave-one-component-out fits with the same constants: predict each
held-out calibration component from the other 48, then aggregate all 69 held-out
scores descriptively. No settings change from this diagnostic. Retain coefficient
ranges and the range of development operating-point results obtained by applying
these 49 maps as **deletion sensitivity, not a confidence interval**. Overlapping
training folds prevent treating their scores as 49 independent fitted models.
Do not bootstrap these fitted-map ranges into a formal total-uncertainty claim.
Any failed fold leaves the full diagnostic incomplete; no fold is dropped.

The main fit plus 49 diagnostics requires 50 tiny fits, no additional model
forwards, with a conservative 100-minute total optimizer deadline ceiling. Actual
fit time must be measured on invented controls before the final protocol. The
69 claims comprise 32 singleton, 15 two-claim, one three-claim and one four-claim
groups; 49 groups are insufficient for reliable fine-grained tail calibration.
Source exposure and unknown pretraining overlap remain as recorded in the
eligibility audit. No calibration result here transfers to LitQA2, clinical
probabilities or therapeutic benefit.

## Before activation and retained evidence

After SC04 acceptance, qualify role-separated inference/calibration/evaluation,
stable fitting against independent invented-data checks, boundary scores, ties,
constant scores, one-class labels, projected-boundary convergence, missing pairs,
empty selection, group resampling and immutable parameter application. Preserve
the existing runtime; implement the new controller under its explicit `calibrate`
grant. Freeze this prospective design only after those engineering checks, without
using actual outcomes to select settings.

Fresh SHA-256 values recorded at `2026-11-06T22:43:10.519947Z`; all paths below are
relative to `D:\Projects\drug_target_agents`:

| Input | SHA-256 |
|---|---|
| `planning/review-assets/tether-semantic-20261106/sc04/SC05-FEASIBILITY-NOTE.md` | `f8d1e00d8ad7a0e49fe4742a6914503d1ccc7a2f04ab9fc3a8fcb34a11283dc0` |
| `planning/review-assets/tether-semantic-20261106/sc04/SC05-CALIBRATION-ELIGIBILITY-AUDIT.md` | `7e273a7f80136718731aa96c0c7b4ab6dbeb5f79fa1a5abe31ed42d82e48a98d` |
| `planning/review-assets/tether-semantic-20261106/sc04/sc05-calibration-audit01/SUMMARY.json` | `fbe4d6119b338a9fc04c03f044d878d018e2e9c4274cb83863eddc7ca89d3d23` |
| `experiments/scifact_comparison/policy.py` | `fafc3ae3a954a2591a2fce890d6315bd934b1fc17a60594aaa2a6d3ab9d47879` |
| `experiments/scifact_comparison/statistics.py` | `1d215072cfdfd58f53712b7fcf3ad0be0ab365af273f5713a0bcbbd524749a03` |
| `experiments/scifact/evaluate.py` | `945c6a9ca1f42d89ada671026178f50dac431a8e77e7b9f9c69652b818909bd8` |

Only this documentation file is added. The eligibility audit's retained results
are cited, not rerun; no new scientific measurement is claimed.
