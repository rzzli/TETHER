# Q03 critical route review

2 November 2026 UTC. Independent route review after Q02 commit `89d00f5`.
This reviewer has prior-project/results context and is therefore **not** a fresh
answer constructor. The source-only task designer and source-feasibility analyst
have separate, restricted inputs. No prior candidate outputs, reference answers,
human responses or clinical outcomes were sent to them by this reviewer.

## Decision

**Proceed with the bounded source-feasibility checkpoint; do not yet authorize a
new model experiment.** The proposed exact-source composition question can reveal
whether TETHER faithfully accounts for related provider records, missing identity
fields and incomplete coverage. Its scientific ceiling is source consistency and
provenance-aware reporting. It cannot establish independent genetic replication,
causal target identity, therapeutic value or a benefit from agent orchestration.

The transparent deterministic baseline in the new specification can produce the
entire required answer. Two targets and multiple records add composition, but do
not by themselves provide a discriminating model endpoint. If the field audit
supports only this task, retaining the narrow technical paper is a successful
route decision, not a scientific validation claim or a reason to reopen old runs.

## Material reviewed and limits

- [Current corrective plan](../../../TETHER%20Corrective%20Execution%20Plan%202026-11-02.md),
  Q03–Q06, and the Q02 progress assessment.
- [Full project critical review](../../../TETHER%20Full%20Project%20Critical%20Review%202026-11-02.md),
  [results review](../../full-project-review-20261102/results/RESULTS-REVIEW.md),
  and [paper errata](../../../../paper/REVIEW-ERRATA-20261102.md).
- [Initial source-only specification](../task-spec/SOURCE-ONLY-TASK.md), SHA-256
  `25e6d7e577cd0bad3fbb029f0f7b54a8497783f36f22b334ca18de86ade59847`.
- [Design clarification 01](../task-spec/DESIGN-ADDENDUM-01.md), SHA-256
  `8eab5cdb540a5e9a65c3bdd23dc20671539dc9102807ea3b14654b1a6252bbb6`.
- Source-only `SOURCE-INVENTORY.json` and `SOURCE-SCHEMAS.json`: schemas and
  metadata, with `row_values_read: 0` in the initial inventory.

This review does not inspect biological row values, construct a reference answer,
count eligible target pairs or independently verify all raw-source hashes. It
does not run a backend, benchmark, model, new download or literature survey. The
source-feasibility report, when finalized, owns its actual field/row findings.
Recommendations below do not depend on desired model performance.

The schema audit observes 100 GWAS-evidence files, 25 credible-set files across
two locations, ten target files, one disease file and sixteen L2G files. It finds
no local study directory/completed study receipt and four partial colocalisation
files rather than completed ones. These are metadata observations, not proof of
complete release acquisition, populated fields or scientifically usable joins.

## What this would add

The retained paper's native task reports supplied fields; its literal baseline
reaches the ceiling. The new task requires exact filtering, a left join, set
partitioning, preservation of unresolved matches and explicit reuse accounting.
That is a different **technical operation**. It could establish that a declared
source-composition contract works on the selected provider data, or expose why
the available data cannot support that contract.

It would add little empirical information if the only experiment were to copy
the deterministic answer through another model or to demonstrate rejection of
the same already-known malformed fields. Neither more identifiers nor a longer
answer makes the evidence scientifically independent. A new provider join also
does not repair missing upstream phenotype/cohort/allele/build information.

The frozen task correctly limits `A_only` and `B_only` to observed membership in
an exact disease/release slice. Those names cannot become claims of biological
uniqueness. A shared provider object is reuse; distinct provider identifiers are
not proof of independent studies or participants. Exact field equality is a
reporting fact, not a harmonized genetic-effect comparison.

## Minimum useful estimand before any new experiment

The minimum useful technical question is: **for a fixed, source-backed query
frame, what fraction of required, assessable composition decisions is returned
correctly, and how often are unsupported decisions asserted, under the same
input and resource envelope?** A decision should be an actual set-membership,
join-resolution or identity-comparison proposition, not every redundant printed
identifier. Protocol authors must declare the relevant proposition inventory
before candidate execution.

Use distinct denominators:

| Quantity | Denominator and interpretation |
| --- | --- |
| Correct answerable coverage | All assessable requested propositions, including those left unanswered by the system |
| Unsupported-assertion frequency | All issued substantive propositions; also report the number of attempted query instances with any unsupported assertion |
| Unknown handling | All prespecified non-assessable propositions, with correct abstention, unsupported assertion and omitted disposition separate |
| Complete instance success | All planned query instances, including malformed outputs, errors, timeouts and abstentions |
| Constructed fault rejection | Each declared fault class separately; not an estimate of natural error prevalence |
| Valid-input rejection | Valid complete and valid partial cases separately, not only deliberately complete positives |

No single precision/coverage scalar should hide these differences. In particular,
a missing source field is not a false biological finding, and an honest partial
answer is not equivalent to an invalid output.

If a deterministic implementation is already exact on all native propositions,
faithfulness/abstention superiority has no headroom under that endpoint. A new
model branch then requires an independently justified alternative endpoint, such
as a measured resource/verification trade-off or a separately specified querying
interface. Natural-language convenience, user comprehension or usability cannot
be inferred from AI judgment of prose. No external expert review is required by
this route; absent a defensible non-human objective endpoint, simply do not claim
those benefits.

For the current Q03, this remains a design criterion, not a frozen experiment or
a requirement to build all these metrics. A resource-only experiment should be
small and test a concrete implementation change; it need not involve a model.

## Design risks and required dispositions

| Risk | Why it matters | Required disposition |
| --- | --- | --- |
| Row-driven pair selection | Choosing convenient pairs after observing overlap or missingness creates a selected demonstration | Freeze distinct target IDs or a deterministic pair-universe/selection rule before selection; retain unsuccessful eligibility checks and exposure status |
| A multi-record threshold mistaken for difficulty | At least two objects guarantees a join/set operation, not baseline errors or agent value | Call it composition eligibility; measure a justified baseline/property before deciding on Q04 |
| One global coverage flag | Complete evidence files with incomplete credible sets can still lose join targets | Record evidence-slice completeness and credible-set join coverage separately, preserving supplied-subset labels |
| Ambiguous counts | Missing-ID rows, distinct unresolved object IDs and failed row-level joins are different units | Freeze each denominator and reconcile totals; do not add overlapping counts |
| Conflicting duplicate IDs | Deduplication can silently fabricate a uniquely resolved link or target membership | Retain conflicting projected rows/locators; report observed membership and ambiguity; never select the convenient alternative |
| Unavailable identity treated as agreement | A provider object key can join even when study/variant comparisons are unavailable | Allow the source-object statement; abstain from the missing identity assertion without filling from other rows |
| Opaque IDs treated as studies | Different signals, fine-mapping outputs or provider study labels can share inputs | Report source groups and reuse; do not use object count as independent sample size |
| Circular reference/checker | A second invocation of the producer reproduces its mistake | Implement expected set/left-join decisions separately from the candidate; test literal small cases; disclose shared primitives and source assumptions |
| Same-frame exposure called holdout | Fresh agents do not erase earlier project exposure to source frames | Retain an exposure register; unknown study/cohort grouping precludes independence claims; describe selected-case results when disjoint groups cannot be established |
| Constructed faults treated as natural errors | Hand-written challenge frequency is controlled by the author | Separate native data from labeled mutations and report per-family technical outcomes; do not claim prevalence or general sensitivity |
| Historical meaning inferred from a current release | Release/download dates and current annotations do not prove historical availability | Keep this contemporary task; no retrospective clinical/genetic inference without its own qualified chronology |
| Extra data acquired without an estimand | A study table may improve traceability but not create a useful comparison or prove participant independence | Name the precise blocked statement/field and bounded acquisition before requesting anything; no speculative expansion |

These are scientific-design gates, not requests for more generic platform audit
layers. Hashing and catalog grants remain necessary integrity/authorization
controls and are insufficient as scientific qualification.

## Review of the fresh specification

The initial specification correctly preserves unresolved links, missing fields,
direct-disease scope, related-provider dependence and provider-ID versus
biological interpretation. It does not request causal effects or rank targets.
Its per-field comparisons and partial answers are preferable to treating a
single missing study field as failure of every observed membership fact.

Four bounded clarifications were sent to the fresh task designer without prior
answers/results: require distinct targets and a predeclared selection rule;
separate evidence/join coverage; define row/ID/object count denominators; and
remove any implied model-benefit expectation at a complete deterministic
baseline. The initial file should remain unchanged; any clarification belongs in
a dated addendum. This review does not select target IDs or supply answer values.

The separate design addendum now resolves all four concerns: distinct ordered
targets and frozen lexicographic selection, separate evidence/credible-set
coverage, explicit row/object accounting identities, and a conformance/resource
claim ceiling. I reviewed its logic and found no further correction necessary
for this bounded task. The selected instance will still be a feasibility
demonstration; deterministic selection does not make it an independent-study
sample or demonstrate model headroom.

## Stop/go rule and claim ceiling

1. **Source feasibility only:** finish the bounded original-row field check and
   enumerate which statements the admitted subset supports. Do not convert a
   schema field name into a claim that it is populated or compatible.
2. **If reproducible source membership cannot be established:** stop the new task
   and retain the exact blocker. Unknown provenance, missing membership keys or
   irreducible ambiguous scope cannot be repaired with model inference.
3. **If membership is reproducible but scientific identities remain incomplete:**
   retain composition/reporting-only scope with per-field abstention. Missing
   upstream study metadata does not block honest source-object reporting; it
   blocks stronger identity/independence/effect statements that need it.
4. **If the deterministic baseline fully answers the useful contract and no new
   discriminating technical property is defined:** stop before Q04/Q05. Finish
   Q06 as a revised narrow technical paper with the retained negative results,
   new software guarantees versioned separately and owner facts still deferred.
5. **Only if a concrete, nonredundant property remains:** freeze one bounded Q04
   protocol with matched inputs, independent-unit/exposure limits, meaningful
   denominators, honest partial answers and resource feasibility before running
   Q05. A model experiment is optional, not the default consequence of Q03.

Even a perfect source-composition result would justify only faithful composition
on the declared frame. Broader scientific claims require independently qualified
inputs and an evaluation designed for those claims. There is no requirement to
recruit experts, reopen retired human-return inputs or rerun the closed study to
reach this route decision.

## Validation of this review

The review is checked for local reference resolution, preservation of the frozen
initial task hash and absence of raw answer/reference construction. It is an
argument and scope assessment, not a new software-test or experimental result.
The final Q03 checkpoint should link the source audit separately and record the
actual branch selected; it should not count this document as a scientific sample.
