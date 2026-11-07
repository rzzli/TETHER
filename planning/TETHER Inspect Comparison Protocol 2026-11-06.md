# TETHER and Inspect: equivalent-policy implementation comparison

Protocol prepared before the BG05 comparison. Status: preparation; execution is authorized only after the qualification record, exact source inventory and schedule are sealed. This implements stage BG05 of the [execution plan](<TETHER Benchmark Execution Plan 2026-11-02.md>). It does not reopen SciFact, LitQA2 or earlier model attempts.

## Questions and scope

1. Can a real Inspect Task, solver and scorer enforce the same declared archive policy as TETHER and the independent validator on identical inputs?
2. Which execution obligations require extension code, and which facilities come from Inspect?
3. What are the observed costs and maintenance surfaces of the three implementations under the same execution conditions?

Correctness here means conformity to the exposed policy constructions. It does not establish scientific entailment, useful biomedical answers, clinical validity, adversarial isolation or natural fault prevalence. The 109 cases include a duplicated construction; repetitions measure execution variability, not additional independent evidence. The separate scripted runtime witnesses test execution properties, not model quality or provider billing.

The [port design](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/policy/PORT-DESIGN.md) and [27-obligation matrix](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/policy/OBLIGATION-MATRIX.json) enumerate the complete policy and identify native versus extension responsibilities. Every row must have an executed result or an explicit remaining gap. Finite case coverage cannot prove every possible boundary condition.

## Fixed inputs and environment

Use the unchanged patched BG02 corpus at `data/benchmark/tether-equal-policy-v2-patched-20261105-attempt01`:

| Object | SHA256 |
|---|---|
| `FROZEN.json` | `3ec7625fa601a517d8e2dd302228f9f465f35e877f79cd1a587a3a63b394a4fc` |
| `oracle.json` | `99706490490bc485614ba2690ff39e91cc0862366c1af811592c338f3aafa5b7` |
| `trusted-runtime.json` | `ec137020fb115a1325f5ef5bd6510fe530cc0ace46f3214df57949533421e664` |

The frozen corpus inventory binds all descriptors, originals, candidates, directory identities and runtime proofs. Verify the complete inventory before and after execution. Do not regenerate a candidate, rewrite a trusted path, weaken a proof or substitute newer source information. Preparation writes only to new caller-owned scratch directories outside the frozen bundles.

Use Python 3.11.15 and `inspect-ai==0.3.287` in the separately qualified environment, with the exact TETHER 0.5.2 / TETHER 0.3.13 wheels. The [environment qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/environment/attempt02/ENVIRONMENT-QUALIFICATION.json) retains dependency metadata, wheel hashes, installed RECORD verification, the complete installed-file inventory and the native mock smoke. Old trusted runtime locations remain read-only source identities. The independently implemented policy code reads those locations as data; it does not import TETHER's validator.

Each worker starts a fresh interpreter with isolated import mode, bytecode writes disabled and a fresh cache prefix. Explicitly add only the pinned experiment import root. The independent and Inspect workers must not import `TETHER` or `tether`; native TETHER is imported only in its own comparison worker. The common parent supervisor may use qualified TETHER process code, which is counted as shared infrastructure rather than an Inspect-native guarantee.

No external model/API calls, new weights or scientific datasets are required. A Python network audit permits the recorded Windows asyncio internal loopback socketpair and denies external connections/DNS. This is a trusted-code runtime check, not an operating-system sandbox. The restricted execution environment independently hangs during Windows stdlib asyncio initialization; qualified loopback-capable execution is therefore required. The original failed smoke and timeout remain retained.

## Primary comparison

Three arms execute all 109 cases serially in one fresh process per batch:

- `bare_independent`: independent v2 validator and the common durable archive wrapper.
- `bare_tether`: TETHER's v2 reference adapter and the same wrapper.
- `inspect`: real Inspect Task/solver/scorer calling the same independent validator in process, producing native evaluation logs and the common case records.

Run three repetitions, rotating arm order: independent → TETHER → Inspect; TETHER → Inspect → independent; Inspect → independent → TETHER. This yields **981 scheduled cells**, 327 per arm. Within each batch, retain the frozen case order. There are no hidden tuning cases, parallel samples, automatic retries, cache hits or outcome-driven exclusions. Set both Inspect sample retries and provider retries to zero. A failed worker remains one scheduled batch; recovery inspects it without dispatching replacement calls.

Do not present historical BG02 fresh-process-per-case timings as matched measurements of this batch design. They include different import and instrumentation costs. This protocol does not execute a separate cold-case subset. Any later cold experiment requires a separate stated condition.

Task inputs contain only case IDs, bundle roots and descriptor proofs. `Sample.target` is empty; no expected decision or observable is sent to a solver/provider. The trusted scorer reads the separately pinned oracle only after the candidate is sealed. Shared-process access control is an information-flow convention, not protection from malicious Python code.

The oracle defines a decision and a selected observable projection. Mapping-valued expectations constrain their declared keys; additional actual feature keys are not automatically failures. Missing values remain distinct from explicit null, booleans from numbers. Native `error`, `unsupported`, missing and unscored results cannot count as correct rejection. Preserve each full native result, not only its projected pass/fail score.

## Measurements and denominators

Report all 981 scheduled dispositions and the three 109-case paired comparisons. For each arm/repetition, count normative accept/reject/inspect-only, actual decisions, exact decision agreement, full observable agreement, false admissions among the 64 expected rejects, false rejections among the 44 expected accepts, inspection behavior, errors, unsupported results, unstarted/missing and unscored cells. Report native verdict-conditioned accuracy separately from correct/all scheduled. An operational error is an operational error even if the oracle expected rejection.

Time separate quantities: environment/input verification; fresh-worker startup/import/setup; validator operation; durable per-case handling; native scoring/log finalization; parent supervision; result construction and sealing. Explicitly identify any interval not measured directly. Retain wall and process CPU time; label peak memory as process-level or sampled and state which processes are included. Logical input bytes and file counts do not measure physical disk reads. Source pinning, package verification and repeated work are separate from the marginal cost of a policy decision.

Use descriptive totals, medians, ranges and paired ratios on comparable positive timing intervals. Do not infer population significance from three repetitions or 109 authored cases, and do not manufacture confidence intervals. Machine/cache/order effects remain limitations. If an arm fails, publish its denominator and failure cost alongside successful timing summaries.

The common owned-child supervisor bounds execution and pipe EOF with a separately limited cleanup allowance. Freeze concrete deadlines/output caps in the execution manifest. It does not promise process-tree containment or preemptible OS process creation. Final report generation must not be silently included in a timer that actually stops before serialization.

## Separate runtime witnesses

Freeze the fictional fixture bytes, scripts, expected observables and code before their retained qualification execution. The twelve groups IX01–IX12 in the port design cover real native generation/scoring/logging; zero-call admission and budget gates; request binding; nested mutations; measured/estimated and overquote accounting; actual interrupted child recovery; non-authoritative hook failures; concurrent output reservation; process cap/deadline/EOF; bounded claim commits; write failures and contradictory records; and read-only replay.

Retain native reported usage as telemetry even when content is malformed. Under the unchanged EP-EXEC-02 policy, an invalid or unqualified response retains unknown quoted usage in policy accounting; a fully qualified response, including a valid overquote, retains measured adapter-reported usage. Keep these two scopes separate instead of silently changing the parity target. A potentially dispatched call without a usable response retains a conservative reservation/estimate, not invented measured zero. Reported scripted counts are test inputs, not measured language-model tokenization. No automatic retry may repeat an uncertain call.

The minimal claim-commit witness uses invented admitted native records, unique offered IDs, immutable canonical fingerprints, write-time eligibility and a deadline check before each insertion. A controlled clock can demonstrate partial-prefix behavior, but must be labeled as injected; real wall-time supervision is tested separately. It does not implement or claim the entire therapeutic specialist scheduler. Raw context may remain eligible across different actions/modalities while incompatible numerical features are suppressed.

Ordinary Inspect hook exceptions can be warnings. Authoritative admission/reservation belongs in the solver/provider wrapper. Required telemetry failures must be detectable in final reconciliation; silently swallowed exceptions cannot establish policy success. Native logs and extension records must agree on sample/candidate/usage/failure identities where those fields exist. Preserve partial diagnostics on interruption or write failure without claiming that a failing disk can durably record its own failure.

Qualification controls may discover implementation defects. Retain the failing evidence, fix the demonstrated defect and rerun the affected qualification before freezing the comparison. Do not silently edit an executed comparison. A discrepancy after the freeze requires a retained finding and separately versioned correction, never rewriting the earlier outputs.

## Complexity and interpretation

Count the independent validator's full eight-file transitive implementation (2,642 physical lines), new runtime integration, shared controller/analysis utilities, tests, product code and upstream dependencies separately. Report dependency/wheel/installed sizes and source counts with exact scopes. Wrapper line counts alone cannot establish a simpler complete system; the full unrelated Inspect or TETHER package surface is not a minimal-equivalent estimate either. Developer time was not prospectively measured and must not be invented.

Archive parity supports interoperability of this policy on the exposed cases. Runtime witness parity supports only the exercised extension behavior. A smaller or faster alternative is a valid result even if it weakens the argument for a separate TETHER framework. Conversely, unavoidable custom lineage and scientific policy code cannot be credited to Inspect merely because it hosts the code. No result can promote provenance conformity into answer correctness.

## Completion and preservation

BG05 requires the frozen schedule/input/code/environment pins; complete all-scheduled results/native logs and failure records; independent reconstruction; the filled policy matrix with any gaps; resource and complexity accounting; and a scoped conclusion. Retain current tests and the original SciFact/LitQA2/clinical/paper artifacts. Update the current report, TODO and memory only after validation, then make a timestamped local commit. BG06 separately audits the full authorized five-stage goal. Deferred author facts/publication and conditional clinical/MR/T2–T5/H6 work remain outside this execution.
