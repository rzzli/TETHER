# Critical results, study-design and release review

Reviewed against commit `21f64e7`, 2 November 2026 UTC. This review reads current
manuscript/supplement, all eleven result CSVs, result/input manifests, the frozen
38-output ledger and retained output bytes; it inspects the source-reporting
compiler/adapter/scorer, selection/runner/auditor/analyzer and installed-replay
boundaries. It is not a fresh audit of all provider originals, an independent
biomedical adjudication, a new literature survey or a line-by-line certification
of every release module. No original source, experiment, paper or package changed.

## Judgment

The principal numerical statements in the current paper are reproducible from
the retained results. I found no arithmetic discrepancy in the audited claims.
The work supports an unusually explicit **technical source-reporting artifact**.
It does not yet establish the original therapeutic-assessment/agent-evaluation
research objective. The paper largely admits this correctly. The planning danger
is treating technical completion, repeated audit counts and a polished package as
closure of the scientific programme or evidence of publishable novelty.

The independent read-only script `recompute_results.py` passes 104 checks. It
verifies current bytes for all 38 manifest payloads and five input descriptors,
all 38 raw output bindings, then recomputes table/ledger accounting and native
availability without importing the producer or scorer. It reads no provider
originals or human/clinical outcome data. These checks verify arithmetic and
retained bytes, not the biomedical correctness of upstream assertions.

## Recomputed quantities

| Quantity | Independent result |
| --- | --- |
| Table files / rows | 11 / 392 |
| Output cells / policy decisions | 38 / 90 |
| Output terminals | 36 returned, 2 deliberately malformed |
| Decision totals | 57 admitted, 33 rejected |
| Native requested facts | 180: 132 identity, 48 measurement |
| Native populated facts | 148: 108 identity, 40 measurement |
| Native nulls | 32: 24 identity, 8 measurement |
| Literal / abstain completion | 12/12 / 0/12 |
| Constructed invalid admissions | FULL 0/10; WITHOUT_WRAPPER 2/10; WIRE_ONLY 7/10 |
| Constructed valid rejections | 0/4 under each policy |
| Verification share of original production wall time | 197.812 / 203.828 = 97.0485% |
| Production logical hashing / selected original bytes | 140,452,303,784 / 2,866,248,239 = 49.0021 times |

The last two calculations describe the retained production implementation. They
are not physical disk traffic, a predictor of another machine's runtime or an
independent benchmark against the audit implementation.

## Prioritized findings and remedies

### RES-01 — Native 80% and 100% thresholds are mathematically redundant (P2, new design finding)

Every native unit has one measurement group with only two, three or four
answerable components. Reaching 80% therefore requires respectively two, three
or four exact components: exactly the 100% requirement. This holds for every
possible partial match count, not merely the observed perfect literal outputs.
The distribution is one two-component, six three-component and five four-component
units. The paper's 60/80/100 statements are numerically true, but do not constitute
three informative native sensitivity analyses.

Evidence: `paper/manuscript.md:71`, `paper/supplement.md:71`,
`paper/results/tables/native_missingness.csv`,
`src/asof/study/source_fact_evaluation.py:169`, and `RECOMPUTED-RESULTS.json`.
Fix: add this threshold-resolution statement to the next manuscript version and
current planning; keep original results unchanged. For a new task, specify
meaningful atomic information units and threshold operating points before data
selection. Do not inflate a benchmark by splitting one p-value into more fields
just to obtain intermediate fractions. Acceptance: a small enumeration of attainable
coverage values accompanies the frozen endpoint.

### RES-02 — The primary task has no room to show agent value (P1 scientific-priority limitation, already disclosed)

The native experiment is field copying with source bindings already supplied.
The literal assembler reaches the ceiling by construction; abstention is a
zero-information control. There is no model on these twelve units, no task-aware
retrieval comparison and no executed Virtual Biotech comparator. More native
copying units or more checks of this same endpoint will improve software coverage
but cannot demonstrate reasoning or orchestration benefit.

Evidence: `paper/manuscript.md:21`, `paper/manuscript.md:63`,
`paper/manuscript.md:129`, `tools/science/run_source_validation_experiment.py:190`.
Fix: explicitly choose a technical-artifact paper as the current output. Any
stronger research claim needs a separately frozen task where the system must
select applicable evidence among competing dated/contextual records, resolve a
mechanically defined multi-record query, or improve a meaningful task outcome.
Acceptance: the simple baseline's ceiling is measured before locking the new
study and the proposed advantage can in principle exceed it. This is future
research, not a reason to relabel or discard the existing negative result.

### RES-03 — Designed policy contrasts do not qualify real-world error detection or partial-answer acceptance (P2)

All fourteen controls were exposed and qualified before the study. Removing a
guard required to catch a named synthetic error predictably changes its verdict.
The three policies reuse one candidate and guard outcomes; they are not complete
alternative workflows with independently measured runtime. FULL also requires
strict exact reporting: an honest partial answer can meet a coverage rule yet
be rejected for not being an `answered` exact report. The 0/4 false-rejection
result concerns four deliberately complete technically valid controls, not
calibrated partial reporting, realistic noise or naturally occurring errors.

Evidence: `paper/manuscript.md:65`, `paper/manuscript.md:67`,
`paper/manuscript.md:71`, `tools/science/run_source_validation_experiment.py:218`,
`tools/science/run_source_validation_experiment.py:657`.
Fix: keep the original control result as conformance evidence. A new evaluation
should hold out fault families/combinations and include technically valid partial,
missing and conflicting-source cases. Name source admission, schema validity,
exactness and coverage completion separately. Acceptance: all planned cases,
including unknown/failed ones, remain counted; no natural-prevalence or sensitivity
claim is made from a hand-built control set.

### RES-04 — Verification dominates cost and repeatedly hashes the same frame (P2, measured performance concern)

The 97.05% verification share and roughly 49 full-frame equivalents of logical
hashing are the clearest optimization target. Native generation pairs take
0.186 seconds in total and native scoring 0.079 seconds; these are subphases,
not extra quantities to add to production. Scaling data or the number of cases
without removing repeated checks can make the platform expensive while doing
almost no additional scientific work.

Evidence: `paper/results/tables/resource_phases.csv`,
`paper/manuscript.md:117`, `tools/science/run_source_validation_experiment.py:757`.
Fix: design a new, separately versioned verified-input session that hashes each
immutable source once per bounded session, binds the verification result to exact
file identity and detects mutation/replacement before reuse. Do not introduce a
cache keyed solely by path/mtime or weaken input proofs. Acceptance: identical
accepted/rejected outputs on adversarial mutation tests, measured lower logical
hash volume and end-to-end wall time on the same source frame. Preserve frozen
P06/P09 costs and packages.

### RES-05 — Negative model probes do not test a functioning two-stage specialist (P2, qualification gap)

The actual P04 report has five dispatches: three `plain`, two `proposal`, zero
`audit` dispatches. Proposal failure prevented the critic stage from running.
The rendering preflight records 3,225/3,240-byte literal outputs and prompt bytes,
while the execution cap is 2,048 output tokens; it supplies no exact expected-output
token proof. This does not prove that either output was too large. It means
serialization/token feasibility and task/model ability are not causally separated.

Evidence: `runs/preprint-p04-typed-report-20261101T053531Z/report.json`,
`planning/review-assets/preprint-p04-20261031/RENDERING-PREFLIGHT-v1.json`,
`tools/science/run_source_fact_pilot.py:150`, `paper/manuscript.md:123`.
Fix: retain the closed branch and phrase its result as interface/task conformance
failure. Before any newly authorized model branch, qualify exact wire-size/token
fit and a complete two-stage lifecycle using synthetic inputs with declared
budgets. Native structured decoding, short binding aliases or another format are
possible new conditions, not retrospective repairs. No model rerun is performed
or requested by this review.

### RES-06 — Local reconstruction is strong, external reproducibility remains conditional (P2, release limitation)

The qualified route needs all 137 exact originals; 136 Open Targets files remain
external. Installed Windows reconstruction, code pins and a local repeat do not
establish current public acquisition or Linux execution. The frozen engine/core
dependency is intentional, but modifying it in place breaks the old authorities;
future platform fixes need new source/version inventories and separate release
qualification. Owner declarations remain deferred and are not scientific input.

Evidence: `paper/manuscript.md:145`, `paper/release/qualification.json`,
`paper/release/code/src/asof_p05_replay/authority_v1.py:46`,
`paper/release/tether/README.md:44`.
Fix: state the supported environment and exact-source dependency in every current
release summary. Before a public reproducibility claim, run the documented route
from a fresh clean environment with lawfully reacquired exact inputs or a separately
qualified redistributable reduced fixture. A reduced fixture cannot claim to
reproduce full-file hashes. Hosted CI/publication are separate actions, not silently
enabled by this audit.

### RES-07 — Source-study identity is a scientific prerequisite, not an optional annotation (P2, scientific blocker)

All twelve outputs carry source-bound native values, but GWAS-side study/variant
slots are null and the credible-set side supplies its own identifiers. Locus-only
matching cannot certify common study, allele or effect interpretation. Ten selected
records lack sample size. The finite negative-standard-error control illustrates
why accepted reporting is not an admissible scientific estimate.

Evidence: `paper/supplement.md:41`, retained native output field bindings,
`paper/manuscript.md:133`. No variant mismatch was inferred from a missing value.
Fix: before genetics/MR/scoring, require authoritative study metadata, allele/build
and phenotype definition, sample size/ancestry and cohort overlap, compatible LD,
and direction/units QC. Missing requirements lead to abstention or exclusion, not
scientific status promotion. Human-return data are not required for these source
and computation checks.

### RES-08 — Independent arithmetic/projection is narrower than independent scientific validation (P2, proof-interpretation risk)

The direct-projection auditor avoids calling the producer/scorer for expected
values, which is useful. It still shares core provenance, contracts, canonical
encoding and related primitives; the installed audit explicitly documents this.
Audit counts overlap heavily. Their agreement supports reproducible software
behavior within the declared trust model, not an independent source-study count,
biomedical truth, publisher authenticity or a statistical reliability bound.

Evidence: `tools/science/audit_source_validation_experiment.py:30`,
`paper/release/code/src/asof_p05_replay/audit_v1.py:6`,
`paper/manuscript.md:115`, `paper/manuscript.md:141`.
Fix: maintain a claim-to-proof map with subject, code/input anchors, tested failure
families, shared dependencies, limitations and supersession. Prefer closing a
specific untested failure boundary over accumulating more overlapping check
counts. Existing paper wording is largely appropriate; current planning should
enforce it consistently.

## Stage-by-stage disposition

| Stage | Critical assessment | Required next action |
| --- | --- | --- |
| P01 / R01–R02 | Technical scope is honest; original therapeutic hypotheses remain open | Use separate engineering/scientific/publication status columns |
| P02 / R05,R08 | Feasibility found a copying ceiling; local source availability is not scientific adequacy | Retain the result and choose a new estimand before expansion |
| P02a / R13–R14 | Credible-set collection completed; complete local join is not qualified genetics | Study/allele/build/units/cohort qualification before causal features |
| P03 / R04,R06 | Typed scoring and immutable source bindings are implemented | Document threshold resolution and distinguish partial completion from exactness |
| P04/P04b / R07,R09–R10 | Negative conformance result; no completed critic stage | Keep branch closed; require a separately designed feasibility gate for future generation |
| P05 / R08,R11 | Selected/exposed twelve units and known controls; no holdout or independent-study inference | Freeze new source groups and unseen challenge families for broader claims |
| P06 / R12 | Complete 38/90 accounting and retained failures are sound | Preserve outputs; avoid reexecution merely for confidence in old results |
| P07 / R12 | Arithmetic/manifest bindings pass; native80/100 sensitivity is redundant | Add the analytical clarification in a new paper version |
| P08 / R12 | Credible technical-note draft, incremental novelty unresolved | Clarify contribution; retain limits; owner facts remain pending |
| P09 / R03,R16 | Windows installed reconstruction works in retained qualification; public exact reacquisition untested | Fresh acquisition/install qualification only for the scope actually advertised |
| P10 / R16 | Local working packet completed, submission-ready status false | Owner-author facts/acceptance, then new versioned final artifact checks |
| N01–N06 | Naming/interface updates do not change the science | Treat legacy proof identity as preserved history, not a veto on versioned future fixes |
| R13–R15, T2–T5, H6 | Scientific programmes remain conditional/uncompleted | Keep them off the current technical paper's completion checklist |
| HR1–HR4 | Retired human-response dependencies | Do not revive or use response-derived answers as new references |

## Practical next sequence

1. Correct the active plan to expose the threshold redundancy, verification cost,
   no completed two-stage generation and local-only reproduction scope. Preserve
   the original paper/results; issue a new version if paper wording changes.
2. Finish demonstrated runtime defects from the parallel code review in a new
   version, with targeted regression cases and unchanged archived proofs.
3. Choose whether the current deliverable is a technical artifact paper or a
   stronger empirical agent paper. The first can proceed after truthful revisions
   and deferred owner facts. The second requires a new task/protocol and evidence.
4. For the stronger route, first qualify a bounded source-selection/composition
   challenge with useful baseline headroom, source-only references, group-aware
   exposure/dependence accounting and informative coverage levels. Qualify model
   interface feasibility before any actual comparison; do not resume old cells.
5. Measure one meaningful benefit/error tradeoff on the frozen new task. Broader
   clinical prediction and MR remain gated on their own missing data and validation.

No new general unit-test run was justified in this results-only subreview: there
was no runtime edit or newly reproduced scorer defect. The independent arithmetic
script is the fresh validation performed here. Parallel platform/data reviewers
own code correctness and current provider inventory checks.
