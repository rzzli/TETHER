---
title: Framework Code Review and Next Stage Plan
date: 2026-10-10
status: reviewed-plan-proposed
tags:
  - TETHER
  - code-review
  - implementation-plan
---

# Framework code review and next-stage plan

The current implementation is a useful offline workflow foundation. It should pass a
correctness and provenance milestone before real model spending or scientific benchmark
use. The next release should deliver a small, reproducible real-data dossier pipeline,
with historical cohort construction as a separate gated work package.

The existing **51 tests pass**. Ten additional synthetic probes reproduced **five
correctness issues and four integration gaps**, including a T6 temporal bypass and
mutable evidence that can change a prediction while source integrity still verifies.
Passing the original suite therefore establishes the tested behavior, not readiness
for real scientific validation.

This review adds a plan and reproducible probes. Runtime code, original planning
documents, download queues and monitoring configuration are unchanged. No biomedical
analysis, provider request, authenticated source restoration or download-progress check
was performed.

## Review scope and evidence

Reviewed the thirteen top-level Python modules in `src/tether_engine/`, the tests, fixtures,
packaging and implementation documentation. Findings are tied to the source hashes in
[[planning/review-assets/framework-review-2026-10-10.json|the review evidence]].
The retained probe program is `tools/review/probe_framework.py`:

```powershell
uv run python -m unittest discover -s tests -q
uv run python tools/review/probe_framework.py --output planning/review-assets/framework-review-2026-10-10.json
```

The probe program reports current behavior on temporary fictional fixture copies.
`gap_reproduced: true` is evidence of an issue or missing future capability, not a passing
correctness assertion. Its findings should become targeted regression tests during
implementation. The descriptive evaluator's permissive input format and lack of
scientific tools are already documented limitations; they are not represented here as
undisclosed production failures.

Useful choices to retain: a small provider-independent orchestrator, strict JSON
contracts, conservative date gates, exact packet-byte hashes, explicit catalog roles,
separate hypotheses/programs, verbatim claims, budget reservations, explicit abstention,
known-dependence grouping and an evaluator that is not imported by the workflow.

## Findings, in priority order

### F01 — P1 correctness: T6 bypasses program temporal validation

Location: [Case.validate](D:/Projects/drug_target_agents/src/tether_engine/contracts.py:127) and
[request serialization](D:/Projects/drug_target_agents/src/tether_engine/agents.py:138).

Program availability and eligibility checks sit entirely inside `if self.task == "T1"`.
A T6 case can still contain a program, and the entire case is serialized for every
backend request. With origin `2023-01-01`, the probe supplied program record availability
and eligibility `2024-01-01`. The run completed and sent both future dates to the backend.

Validate the availability of every supplied program for every task. Keep T1-specific
active-phase/endpoint eligibility conditional on T1; a historical dossier may legitimately
describe a stopped program. Reject or explicitly exclude future/unverified program
context before any request. Test both supplied-program and program-free T6 cases.

### F02 — P1 correctness: mutable records break source and prediction consistency

Location: [observation dictionaries](D:/Projects/drug_target_agents/src/tether_engine/contracts.py:219),
[store queries](D:/Projects/drug_target_agents/src/tether_engine/chrono.py:32),
[feature vector](D:/Projects/drug_target_agents/src/tether_engine/features.py:28) and
[verification](D:/Projects/drug_target_agents/src/tether_engine/artifacts.py:110).

Frozen dataclasses contain mutable dictionaries for features and method parameters.
Store queries/lookups return those same objects. Changing an admitted genetic-support
value from `0.8` to `1.0` changes the scored feature while the unchanged source file still
contains `0.8`. A newly written run passes verification, including an independently
retained receipt hash.

A second probe changed the returned feature vector to `0.1` after scoring. The prediction
still used `0.8`, and the trace's final feature fingerprint no longer matched the features
file. Verification still returned `integrity_verified`: it checks byte hashes and the
trace chain without checking these semantic bindings.

Make admitted records and finalized run state deeply immutable or return defensive
copies backed by sealed canonical records. Validate each ledger commit against the
admitted record fingerprint. Before publication and during verification, compare the
final trace fingerprints with output objects, rebuild deterministic features from the
ledger, and check prediction contributions/probability against the frozen scorer.
Report byte integrity and semantic consistency as separate checks.

### F03 — P1 correctness: case-dependent features lack hypothesis binding

Location: [retrieval matching](D:/Projects/drug_target_agents/src/tether_engine/chrono.py:32) and
[observation schema](D:/Projects/drug_target_agents/src/tether_engine/contracts.py:202).

Matching uses target ID, indication ID, category and optional program ID. It does not
bind a feature to intended action, modality, tissue or identifier namespace version.
Observations have no explicit hypothesis key. In the probe, changing intended action
from inhibition to activation retained the same feature fingerprint and positive
`direction_alignment: 0.6`, although the record describes an inhibition intervention.

Raw biological observations can remain relevant to multiple hypotheses; they need not
be discarded solely because the intervention differs. However, a case-dependent feature
such as direction alignment cannot be reused without an audited transformation or an
applicability decision. Add a versioned hypothesis key, observation subject/context,
and feature derivation scope. Preserve contextual evidence in dossiers while withholding
or recomputing inapplicable numerical features. Test opposite actions, multiple modalities,
different tissues and program-specific measurements against the same target/indication.

### F04 — P1 correctness: provider errors can lose attempts, usage and run artifacts

Location: [backend exception handling](D:/Projects/drug_target_agents/src/tether_engine/workflow.py:147)
and [final artifact creation](D:/Projects/drug_target_agents/src/tether_engine/cli.py:89).

The workflow catches `BackendFailure`, `ContractError` and `RuntimeError`. A backend
`TimeoutError` or ordinary `ValueError` escapes after an attempted call without returning
a `RunResult`. The CLI catches an `OSError` such as a timeout as a generic error, but it
does not persist the attempted call. Artifact creation occurs only after the workflow
returns; an interruption can similarly lose the whole in-memory trace.

Create an exclusive run record before execution, persist attempt/reservation events,
and finalize failures in a controlled error boundary. Adapters should convert expected
provider failures into typed errors with measured or conservatively estimated usage.
Distinguish programming errors from retryable provider errors; do not endlessly retry
unknown exceptions. Persist interruptions and report incomplete attempts on recovery.
Reserving the output directory before dispatch also prevents duplicate concurrent runs
from spending money before discovering that their output paths collide.

### F05 — P1 correctness: scorer cutoff checks happen after all backend calls

Location: [scoring eligibility](D:/Projects/drug_target_agents/src/tether_engine/scorer.py:116) and
[workflow final scoring](D:/Projects/drug_target_agents/src/tether_engine/workflow.py:201).

The CLI validates scorer structure early, but training/calibration cutoffs, profile and
case applicability are checked later inside `score`. A model with a `2024-01-01` training
label cutoff for a `2023-01-01` origin was rejected only after eight backend calls. No
final result was returned. It correctly withheld a probability, but would waste live
usage and lose work under the current final-only artifact flow.

Perform pure configuration/profile/cutoff/applicability preflight before dispatch.
Invalid cutoffs must fail with zero backend calls. An inapplicable scorer should produce
a documented dossier-only path or an early rejection, according to an explicit run mode.
Feature coverage remains a post-extraction check because it depends on available evidence.

### F06 — P1 before locked evaluation: predictions are not linked to registered runs

Location: [evaluator inputs](D:/Projects/drug_target_agents/src/tether_engine/cli.py:60) and
[cohort matching](D:/Projects/drug_target_agents/src/tether_engine/evaluation.py:41).

The descriptive evaluator accepts standalone prediction JSONs. There is no receipt,
registered cohort artifact, prediction freeze, input-policy/model identity or independent
prediction anchor to validate. The probe supplied edited fictional probabilities and
obtained AUROC `1.0` without any run receipts. This is acceptable for the documented pilot
metric utility; it cannot serve as the locked benchmark evaluator.

Retain an explicitly unverified pilot mode. Add a locked mode consuming registered
cohort/prediction manifests and verified run receipts. Verify expected origins, endpoints,
models, policies, source/feature schemas, run status and every prediction hash before
reading labels. Keep abstentions, retries, exclusions and failures in the denominator.
For retrospective work, a freeze prevents further tuning after a controlled label unlock;
it does not prove the outcomes were historically unknown. Prospective claims additionally
need a prediction anchor that predates the relevant observed outcomes.

### F07 — P2 integration: receipts omit parts of the input-policy/backend provenance

Location: [catalog loading](D:/Projects/drug_target_agents/src/tether_engine/chrono.py:59) and
[run input/receipt construction](D:/Projects/drug_target_agents/src/tether_engine/artifacts.py:84).

Receipts include admitted normalized packets and Python file hashes, but do not snapshot
or hash the admission catalog, replay document, interpreter/build environment, or future
provider model/configuration. Changing the catalog to deny a dataset does not affect
verification of the recorded run because the originally used policy was never captured.
This does not mean every later policy update should invalidate a historical run; the
missing element is the original, archived admission policy.

Persist canonical effective configuration and the exact policy used, plus raw-input and
normalized-output lineage, replay/provider metadata, prompt/response hashes, model
version, sampling parameters and environment/dependency fingerprints. Verify the archived
policy rather than silently consulting today's policy. Use logical source IDs and hash
resolvers for portable verification; private absolute paths are local conveniences.

### F08 — P2 before scorer training: feature-level missingness loses reasons

Location: [feature construction](D:/Projects/drug_target_agents/src/tether_engine/features.py:69).

The run's coverage records preserve `absent` versus `access_denied`, but both become
`Feature(value=null, status="not_measured")`. These reasons therefore disappear from the
scorer-facing feature vector. Artifact-level exclusion reasons also lack a typed mapping
to expected source capabilities/categories. Current required-feature abstention avoids
treating these as a negative signal, but future training/imputation would conflate them.

Add structured missingness/applicability reasons and expected source capability coverage
to the feature contract. Preserve separate biological findings, access state, QC failure,
context mismatch and collection incompleteness. Decide which missingness indicators, if
any, enter the predictor only through the training protocol; they are not automatically
biological evidence. Do not convert a partly downloaded source into “no evidence.”

### F09 — P1 architecture before computed tools: output creation and input availability are conflated

Location: [availability rule](D:/Projects/drug_target_agents/src/tether_engine/contracts.py:63) and
[record admission](D:/Projects/drug_target_agents/src/tether_engine/chrono.py:121).

Every observed result, including `source_kind="computed"`, must have record-public
availability before origin. A newly calculated result dated October 2026 is excluded
from a 2023 origin even when its declared scientific inputs are from 2019. The probe
demonstrates this gate behavior, not an actual MR computation or verified input lineage.

The feasibility review explicitly allows new deterministic methods on historically
eligible information. Model this through an input-lineage DAG: immutable input sources
and information-bearing annotations/models must pass the origin policy, while the
current computation has its own `computed_at`, method/container version and parameters.
Do not falsify a result's publication date to fit the old contract. Still exclude newer
scientific observations, later-informed mappings, labels and information-bearing model
assets. A new code implementation and a newer scientific input are different dependencies.

## Other gaps affecting the next stage

- The backend only selects IDs; it does not extract facts from provider records or audit
  scientific interpretations. The critic checks duplicates and grounding, not study
  design, contradiction handling or method validity. An empty selection can complete
  successfully without recording why available records were omitted.
- Numerical features currently depend on which claims the backend selects. Selective
  omission can change the predictor. For the first real-data pilot, use deterministic
  scientific eligibility/aggregation for primary features and evaluate model-assisted
  selection as an explicit separate variant; always report omitted counterevidence.
- The eight normalized support features are fixture-era contracts. There is no validated
  rule for converting arbitrary studies into these 0–1 values, no trained scorer and no
  verified training manifest. Do not invent support values for real inputs to get a score.
- No provider ingestion, historical trial restoration, program/molecule/target mapping,
  batch experiment runner, scientific computation or OS containment exists yet. The
  current source hash covers a normalized JSON packet, not a complete chain to its raw
  provider inputs.
- Packaging has a floating build dependency and no CI. The workspace is not currently a
  Git repository. Preserve this reviewed file-hash baseline, then establish version control,
  ignore rules, environment fingerprints and Windows/Linux checks before broader changes.

## Next release objective: TETHER v0.2

**Deliver ten development dossiers from real, pinned public data with auditable lineage,
hypothesis-aware applicability, durable execution and an optional bounded selection
backend. Keep real clinical probabilities withheld until a trained scorer exists.**

Use contemporary T6 cases for the first dossier gate. This permits productive real-data
work without waiting for historical trial access. Treat dated historical T1 cohorts as a
separate gate; contemporary Open Targets 25.09 or the current HGNC snapshot cannot be
substituted for older releases. All development cases, including the original B7-H3 and
OSMR examples if used, remain outside the locked test.

Assume one engineer and part-time biological review. Work packages A–C are an estimated
**10–16 engineering days**, approximately **2–4 weeks** with review/rework. Historical
cohort/evaluation work adds an estimated **5–8 days after usable snapshots are available**.
These are effort estimates, not validated staffing or access commitments.

### A. Correctness and durable runs — 3–5 engineering days

Resolve F01, F02, F04 and F05; establish the version-two contract changes required by F03
and F09 before adding adapters. Maintain compatibility for verifying already-created
version-one runs and fictional fixtures. Do not silently migrate a locked run's inputs.

Proposed modules: `preflight.py`, `journal.py` and a versioned provenance/applicability
contract, with changes to `contracts.py`, `ledger.py`, `artifacts.py` and the workflow.

Acceptance checks:

1. Every task rejects/excludes future program/mapping context before backend dispatch.
2. Admitted records and finalized outputs cannot be changed through a query result or
   nested dictionary. Source-to-claim and trace-to-feature/prediction bindings verify.
3. Invalid scorer dates/profile fail before any call. Inapplicability produces the selected
   early-rejection/dossier-only behavior; missing evidence still abstains after extraction.
4. Timeout, malformed response, reported/unknown usage, interruption and disk-write failures
   retain a readable run record. Reservations and measured/estimated charges are distinct.
5. A run directory is reserved once before execution; two processes targeting it cannot
   both dispatch. Journal recovery reports incomplete attempts without duplicate billing.
6. Existing tests and new targeted regression tests pass. Source control captures the
   reviewed baseline and changes; private data/credentials remain ignored.

### B. Real-data normalization and provenance — 4–6 engineering days

Create an optional ingestion layer outside the dependency-free runtime. Start with bounded
Open Targets target/disease/evidence slices and identifier normalization. Add dated
ChEMBL mechanisms/program metadata when the exact product is usable. Inspect only
explicitly selected, receipt-verified files; exclude partial files and record source
completeness rather than assuming the entire transport wave finished.

Apache Arrow's dataset interface supports explicit file lists, selected columns, filters
and batch iteration, which suits bounded local Parquet processing. Use it first and pin
a tested build in an ingestion extra/environment. Add a query/index layer only after
measuring repeated-scan costs. This is an implementation recommendation, not a measured
performance result. [Apache Arrow dataset documentation](https://arrow.apache.org/docs/python/dataset.html)

Proposed modules: `ingest/opentargets.py`, `ingest/identifiers.py`, `ingest/chembl.py`,
`provenance.py` and `applicability.py`. Proposed commands: `inspect-source` and
`build-snapshot`, with dry-run input selection and reviewed manifests.

Each product follows: **raw input/version → normalized records and row locators → dated
mapping/applicability decisions → sealed packet → validation/coverage report**. Capture
raw file hash, provider/release/schema, contributing row identifiers, transformation
version/parameters, terms and availability evidence. Capture all parents for derived
records; reject lineage cycles and evaluation-only ancestors.

The HGNC catalog product has `reference` role only. It belongs in the controlled
normalization/mapping step, not as a relabeled specialist-evidence packet. Preserve
reference versions and their dates. VBT labels/linkage remain evaluation-only; neither
can enter agent inputs merely by wrapping them in a generated-product dataset ID.

Start with a contemporary origin and documented availability bounds. When an immutable
public release proves that original records/annotations existed by release, record that
explicitly as an upper-bound derivation. A retrieval timestamp or year-shaped folder
does not prove earlier publication. Later scientifically informed mapping/annotation
cannot be treated as an old input. Keep `computed_at` separate from information eligibility.

Acceptance checks:

1. Ten real development hypotheses produce dossiers from at least two input families
   (e.g. Open Targets plus identifier reference), with validated IDs and full input lineage.
2. Manually inspect at least twenty resulting source-linked statements, including a
   conflicting record and unavailable/context-inapplicable cases. Record errors and fixes.
3. Opposite action/modality/tissue cases preserve useful raw facts and prevent reuse of
   case-conditioned features without the appropriate applicability/transformation rule.
4. Feature missingness retains distinct reasons and expected-source completeness. Clinical,
   known-drug/outcome and evaluator-derived data are excluded from prediction features.
5. No invented support weights or real clinical probabilities. Use actual quantitative
   measurements/context in the ledger; introduce numerical features only with documented,
   validated derivations.
6. An explicit fixture/raw-byte/schema change invalidates its derived lineage. Document
   record/date coverage and any source assumptions; do not mark all provider data parsed.
7. Measure elapsed time, peak memory, selected bytes, output sizes and scratch space.
   Enforce configurable input/output limits; no full-provider mirror or unbounded expansion.

### C. Bounded model adapter and extraction-quality pilot — 3–5 engineering days

Implement one provider adapter against the stable selection interface, with a versioned
request/response schema. Provider/model choice and live-run spending cap remain unselected;
default execution stays offline and $0. Adapter construction and recorded-response tests
can proceed independently of live calls.

Record model/API version, prompt/request fingerprint, sampling settings, tokenizer/pricing
basis, input/output limits, retries, response hash and per-attempt usage. Replay records
must bind to request fingerprints, not only a category name. Reverify official model
lifecycle/training-cutoff information before choosing an experimental model; the planning
document's earlier defaults are not a current availability guarantee.

Keep selections grounded in sealed packets. Add structured reasons for selection/omission
and applicability, including empty selections and counterevidence. Keep model-generated
interpretations separate from factual ledger entries until a support audit is implemented.
Do not add unrestricted shell, download or web tools to this pilot.

Acceptance checks:

1. Recorded timeout/rate-limit/malformed/over-budget cases leave durable accounted attempts.
2. Overlong requests are rejected or deterministically chunked with complete coverage;
   generation/retry limits are enforceable and cache keys include case/policy/model/schema.
3. On the ten development dossiers, compare deterministic and model-assisted selections
   using source grounding, omission/contradiction coverage, date compliance, failures,
   calls, tokens, wall time and actual/estimated cost. Record the denominators.
4. Every selected ID is in the approved request; future/label canaries are absent. This
   establishes interface behavior, not model training cleanliness or OS containment.
5. Human review assesses factual correctness and relevance separately from provenance.
   A prettier report or higher self-confidence is not a validation endpoint.

If no live model is configured, release the hardened real-data offline pipeline with
recorded adapter tests and keep the live quality pilot explicitly pending.

### D. Historical T1 cohort and trustworthy evaluation — 5–8 days after access

Access/restoration is a separate dependency. Two official AACT pages could not be retrieved
by the browser during this review; no historical snapshot was restored. This does not
establish that the data are unavailable. Resolve one exact origin/follow-up snapshot pair
and permitted access before committing to a historical cohort. No stable historical API
is assumed, and live ClinicalTrials.gov is not substituted for past state.

Use one registered program endpoint, initially documented Phase 2-to-Phase 3 transition
within a fixed horizon. A 24-month horizon is a candidate from the original design, not
an automatically finalized protocol. Select the retrospective origin after finding
compatible historical snapshots, dated mechanisms/IDs and mature reporting. Current-model
runs on old origins must be labeled retrospective and potentially contaminated; a genuine
post-cutoff/prospective test has a different origin and maturation schedule.

Proposed modules: `cohort.py`, `bench_manifest.py`, `batch.py`, and evaluator locked-mode
support. A label-free experiment registry contains ordered case IDs, permitted policy,
systems/scorers, variants, seeds/retry rules and expected runs. Evaluator-only storage
contains adjudicated mappings/outcomes, label source/event/publication dates, censoring,
uncertainty and label-freeze evidence.

Acceptance checks:

1. Restore and parse the selected snapshots; record exact hashes, schema and dates.
   No current-data backfill. If restoration remains blocked, continue the contemporary
   dossier milestone and report the historical gate as unresolved.
2. Construct 10–25 development programs with as-of molecule/target/action/indication
   mappings, origin eligibility and duplicate-trial/program rules. Report unresolved
   mappings and why cases are excluded. Review every pilot label independently.
3. Define what constitutes progression, complete observation, a safety/efficacy stop and
   uncertainty. Trial phase/status fields alone do not adjudicate biological efficacy.
4. Freeze registered cohort and predictions before controlled outcome evaluation.
   Locked evaluation rejects altered/missing/duplicate predictions, incompatible policy,
   endpoints/origins or unverified receipts. Pilot mode remains explicitly unverified.
5. Report failure, abstention, eligibility, missingness and censoring coverage for every
   system. A completed-case metric is not the full-cohort performance claim.
6. Establish target/drug/program/indication dependence identifiers and future rolling
   training/validation/test boundaries. Fit and calibrate only on earlier available
   labels; verify the actual manifests, not merely their declared dates.

This pilot estimates label/mapping errors, attainable cohort counts and operational
cost. It is not a powered superiority test or a sufficient dataset to validate a
high-dimensional predictor. Scorer training, clustered inference/power and final H1/H2
pass rules follow as separate v0.3/protocol work.

## Resources and release gates

Use E: for immutable provider originals and D: for selected normalized packets, indices
and private runs. The earlier capacity assessment is a dated planning input; this review
did not refresh drive capacity or download status. Begin adapters with explicit small
slices and measure expanded/index/cache footprint before increasing scope. Do not count
compressed archive size as working storage or assume all queued files are usable.

The v0.2 release gate is A plus the real-data checks in B; recorded adapter checks in C
support an optional model interface. D is required before historical T1 evaluation.
Probability calibration, causal genetics and any claim of improvement over Virtual
Biotech require later scientific validation. Keep deterministic extraction, shared
scorer comparisons and model-matched evidence packets in that protocol to distinguish
data/scorer gains from agent-design gains.

Defer new autonomous specialists, MCP wrapping, cross-disease MR/PheWAS, spatial analyses,
full competitor execution, T2–T5 and H6 until this pipeline works on reviewed real cases.
Before locked competitor/agent runs, establish read-only approved mounts, separate
evaluator/credential access, controlled model egress and attempted-access audits.
Folder placement and Python protocols remain insufficient containment.

## First implementation tickets

| Ticket | Work | Depends on | Completion evidence |
| --- | --- | --- | --- |
| N01 | Fix task-independent program date checks (F01) | Reviewed baseline | Future T6 context rejected before dispatch; valid T6 context still accepted |
| N02 | Seal admitted/finalized records and semantic verification (F02) | N01; schema design | Mutation probes cannot alter accepted state; trace/features/prediction agreement checked |
| N03 | Add hypothesis/applicability and derived-input temporal contracts (F03/F09) | N02 | Opposite-action case tests; new computation with eligible old inputs allowed; later inputs rejected |
| N04 | Preflight scorer configuration (F05) | N01 | Invalid scorer incurs zero calls; explicit dossier-only scope mismatch |
| N05 | Durable journal, typed failures and early output reservation (F04) | N02/N04 | Interrupted/timeout/concurrent runs retain accounted attempts without duplicate dispatch |
| N06 | Archive effective policy/configuration and versioned missingness (F07/F08) | N03/N05 | Original policy is reproducible; access/QC/absence/context remain distinct |
| N07 | Build bounded Open Targets/identifier ingestion and real packets | N03/N06 | Ten real dossiers, raw-to-packet hashes/row locators and twenty reviewed statements |
| N08 | Add provider/replay request binding and selection reasons | N05–N07 | Recorded failures/budgets pass; ten-case comparison with coverage and cost |
| N09 | Restore historical snapshots and curate a development cohort | Exact source access; N06/N07 | 10–25 audited dated programs and outcome/coverage manifest |
| N10 | Add registered batch and locked evaluation (F06) | N05/N06/N09 | Edited/missing predictions rejected; failures/censoring retained; locked labels isolated |

N01/N02/N04 are the immediate correctness batch. N03/N05/N06 establish the contracts
needed for a meaningful real-data integration. This order keeps later model and scientific
work from depending on provisional temporal or provenance guarantees.

