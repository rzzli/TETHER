# TETHER: equivalent-policy Inspect comparison

6 November 2026 UTC. BG05 tests whether TETHER's specified evidence obligations can run inside an established evaluator. The primary comparison and persistent runtime controls are complete and independently reconstructed in the scopes below. The [prospective protocol](<TETHER Inspect Comparison Protocol 2026-11-06.md>) and all frozen inputs remain unchanged.

## Finding

An actual Inspect Task/solver/scorer extension implements the same archive policy on all 109 exposed authored cases. TETHER, an independent validator and Inspect each conform on 327/327 scheduled cells across three repetitions, with no false admissions, false rejections or unscored cells. These are 109 constructions repeated, not 981 independent scientific examples. The original set includes a documented duplicate construction.

The extension demonstrates feasibility. It does **not** demonstrate a simpler full replacement for TETHER: it reuses 2,642 physical lines of independent policy code, adds 1,010 lines of policy/runtime integration, shares a TETHER process supervisor, and does not port the complete specialist scheduler or positive selection-review retry. In this serial batch condition, Inspect's median paired time is 1.55 times TETHER's. Neither this timing nor line counts measure maintenance effort or scientific answer quality.

## Matched primary experiment

Inspect 0.3.287 runs in an isolated Python 3.11.15 environment with the exact TETHER 0.5.2 / TETHER 0.3.13 wheels. Eighty-four distributions and all 9,014 installed files were inventoried. The original 109-case BG02 corpus is reused without changing its policies, oracle or candidate artifacts. Each repetition has 44 expected accepts, 64 rejections and one inspect-only case. Arm order rotates; each batch gets a fresh worker, with serial samples, no model calls and no retries.

All arms use a common durable result wrapper. Inspect uses native Tasks, solvers, scorers and evaluation logs; it is not merely a subprocess calling TETHER's verifier. Inspect and independent workers forbid TETHER/TETHER imports. The common parent nevertheless uses the installed `tether._process` supervisor: this is not a wholly TETHER-free stack. Reference labels are absent from solver inputs and `Sample.target`; the scorer joins them after a candidate result is sealed. This is a trusted shared-process convention, not hostile-code isolation.

| Measure | Independent validator | TETHER | Inspect extension |
|---|---:|---:|---:|
| Scheduled / fully conforming | 327 / 327 | 327 / 327 | 327 / 327 |
| Correct rejections | 192 | 192 | 192 |
| False admission / false rejection / unscored | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Batch elapsed seconds, repetitions 1 / 2 / 3 | 25.063 / 24.922 / 25.250 | 23.687 / 22.953 / 23.844 | 34.828 / 36.485 / 36.875 |
| Median batch seconds | 25.063 | 23.687 | 36.485 |
| Median worker CPU seconds | 22.641 | 20.906 | 28.703 |
| Worker peak memory range, bytes | 296,906,752–297,123,840 | 304,492,544–304,803,840 | 401,149,952–401,727,488 |
| Native Inspect samples / correct / errors | Not applicable | Not applicable | 327 / 327 / 0 |

The median **paired** batch ratios are Inspect/independent 1.4604, Inspect/TETHER 1.5465 and TETHER/independent 0.9443. They are computed from each repetition's ratio, not the ratio of medians. Three repeated batches support descriptive timing only. BG02's earlier fresh-process-per-case TETHER/independent ratio of 1.65 remains valid for its different condition; it must not be pooled with these warm-within-batch timings. The reversal shows sensitivity to the experimental condition; changed wrappers, imports and execution granularity prevent attributing the difference to one cause.

Primary wall time through command return was 410.430 seconds. The internal before-seal total was 410.094 seconds, including 9.823 seconds of finalization. Complete global input audits took 18.225 and 23.961 seconds. The sealed result contains 4,706 files / 18,384,895 bytes. Complete input proofs cover 11,606 files / 236,179,241 logical bytes; repeated logical bytes are not unique disk allocation or transfer volume.

The [independent reconstruction](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/reconstruction/actual01/REVIEW.md) rereads originals, archived sources, outcomes, native samples and timing records without importing either verifier or Inspect. Its [summary](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/reconstruction/actual01/SUMMARY-02.json) reports all denominators and ratios. The primary stage seal is `d0ea739f5e4cf004cb37802df3ffe25dcf97e1756c0ca0a1c52293a147bf1f9c`; the independent reconstruction hash is `33720734fb1132fdd91a215f4bc6497d540c0e2ec56b382f859bb6c9e6683ce6`.

## Runtime controls and boundaries

A separately frozen runtime experiment exercises real Inspect provider entry, hooks, native logs, reservations, usage and claim commits with scripted responses. It has 19 logical cases: 16 ordinary cases, one interruption group containing an interrupted first and unexecuted second case, and one output-ownership race with two physical workers. These are constructed controls, not 19 new model answers or independent studies.

The completed launch retained all dispositions: four completed cases (including the race owner), three budget-exhausted cases, ten error/timeout cases, one interrupted-unresolved case and one unexecuted case. Expected rejection/failure is the desired response to the injected fault. The ordinary group covers future program/scorer dates, zero budget, request mutation, nested-state mutation, provider failure, timeout, malformed response, overquote, optional/required hook failures, partial commit, duplicate/unoffered selection and wrong category. Interruption preserves an unresolved dispatch without automatic replay. The ownership race must preserve exactly one dispatch and one committed result; independent reconstruction is the authority for those assertions.

Runtime outer wall time was 77.251 seconds. Parent time before its final seal was 63.928 seconds / 36.688 CPU seconds. Input proof checks account for 19.456 seconds before and 18.721 seconds after; times for the three owned top-level helper processes were 8.438, 6.953 and 9.484 seconds, including their contained work. The through-output-inventory timer was 64.024 seconds. Its 13.227-second difference from the outer timer includes startup, pre-stage parsing/path checks, remaining sealing and return work; that difference was not separately apportioned. No complete runtime-stage peak-memory or process-tree CPU measure was collected. Primary comparison memory is reported separately above.

The runtime-stage seal is `92d8f5754a2e119844df01964103c7f1f09d71e5bee5e70d6cec3ab1b344158f`. A [root anchor](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/stage/ROOT-RUNTIME-ANCHOR-01.json) was recorded after execution and before independent reconstruction; it is not a pre-execution output attestation or independent timestamp service. [Launch and outer timing](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/stage/RUNTIME-OUTER-TIMING-01.json) retain the successful process exit.

Specific limits matter:

- Token counts are scripted provider reports, not measured inference or tokenization. Reservations, provider entry and actual dispatch counts are distinct. Invalid/unqualified responses retain conservative quoted policy usage under the unchanged EP-EXEC-02 rule; separately exposed native telemetry does not silently change that rule. Qualified overquote usage is retained and blocks further dispatch.
- Inspect's ordinary hook failures can be warnings. The extension checks mandatory telemetry authoritatively before committing claims. An optional injected failure remains visible without pretending it necessarily stops execution. [Upstream hook semantics](https://inspect.aisi.org.uk/extensions-hooks.html) are separate from extension enforcement.
- The independent feature/scorer reconstruction is deliberately limited to the synthetic genetic-support fixture. It is not a general replacement for TETHER's feature engine or a validated clinical score.
- Full eight-specialist scheduling, a positive review/retry path, the live schema-two facade, and a persistent native IX11 write-failure scenario were not ported/executed. Component write-failure and copied-artifact tamper tests cover narrower obligations. These gaps prevent full production-runtime equivalence claims.
- Limits terminate the owned child, not arbitrary descendant process trees. Parent proof/sealing overhead is measured but not hard-preempted. Python audit hooks deny external connections in the trusted workload; a recorded Windows loopback is allowed for asyncio. This is not OS-level hostile-code containment.
- Full environment content/inventory is checked at stage boundaries; core/source/corpus checks bracket each primary batch. Third-party content is not continuously attested. Runtime helper checks known pins. The separate [exact-membership postcheck](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/stage/POSTFLIGHT-EXACT-INVENTORY-01.json) passes: all 9,451 proofs, exact 9,014 installed files, 175 prepared-tree files plus recipe, 167 original/archive mappings, 23 stage outputs and 124 witness outputs. It does not attest transient additions or empty-directory identity.

## Implementation and efficiency assessment

The [source inventory](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/stage/IMPLEMENTATION-INVENTORY-01.json) reports physical line counts with file hashes and grouped dependencies at its declared freeze-based scope:

| Code group | Files | Physical lines | Interpretation |
|---|---:|---:|---|
| New policy and Inspect runtime integration | 8 | 1,010 | Includes common wrapper/record code also used by bare arms |
| Reused independent validator | 8 | 2,642 | Full transitive policy closure; cannot be omitted from complexity comparison |
| Common experiment controller | 1 | 628 | Measurement orchestration, not minimal product runtime |
| Scripted witness helpers | 3 | 353 | Constructed control machinery |
| Maintained tests | 8 | 875 | Not production runtime |
| Reused reference adapters | 2 | 533 | Includes unused materialization code |
| Independent analysis and tests | 7 | 1,421 | Separate audit implementation |
| Measurement, acquisition and review support | 27 | 2,253 | Includes preserved superseded helpers |
| Full installed project | 85 | 24,177 | Includes unrelated studies; not a matched denominator |
| Full upstream Inspect Python tree | 851 | 258,794 | Includes unrelated providers; excludes dependencies/non-Python files |

These are reproducible surface inventories, not a minimality proof. The inventory predates the postexecution outer-runtime audit glue, exact-postflight and closure helpers; it does not enumerate every final review/support file. Summing unrelated package lines or ignoring reused policy code would give a misleading simplicity claim. The runtime port is incomplete, so a 3,652-versus-24,177 comparison cannot establish equal-feature maintainability.

One measured inefficiency was corrected **before** primary execution. A fictional rehearsal rehashed the entire installed environment before and after each tiny batch: 18 correct cells took 333.735 seconds through sealing. The qualified revision kept complete global brackets while retaining bounded source/corpus checks per batch; the next rehearsal took 66.077 seconds for the same 18 cells. These are different frozen rehearsals, not independent performance samples or a controlled causal estimate. Exact source copies, failures and qualification logs are preserved. A later failing-first fix also detected added corpus files/directories before the primary freeze.

Native integration exposed and corrected additional request/oracle binding, duplicate-claim, timeout-reporting, output-collision and failure-accounting defects before execution. The [integration qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/integration/INTERFACE-AND-QUALIFICATION.md) and [controller qualification](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/controller/QUALIFICATION.md) retain their scopes and unsuccessful attempts. Overlapping test suites are not summed into an inflated independent-test count. Frozen product/benchmark code and original output bytes were not retroactively repaired.

## Decision and relationship to peer work

The study supports an optional Inspect integration for the tested evidence policy. It does not justify replacing the standalone runner yet, nor does it establish a runtime speed or maintenance advantage. A future migration would need the missing runtime paths, actual local-model/provider integration, real operation counts and comparable maintenance changes. Keeping evidence admission/replay as a reusable policy component remains a reasonable architecture hypothesis, rather than a demonstrated benefit.

Inspect already supplies orchestration, logs, limits and scorer infrastructure. TETHER's defensible narrower subject is the explicit temporal/source-role/lineage contract and source-inclusive reconstruction, not invention of those general runner capabilities. The [peer comparison](<../reports/TETHER benchmark comparison update 2026-11-06.md>) separates this engineering question from the weak [SciFact](<TETHER SciFact Native Evaluation Results 2026-11-05.md>) and [LitQA2](<TETHER LitQA2 Native Evaluation Results 2026-11-06.md>) answer results. Equal policy conformity does not establish correct scientific interpretation.

All execution used zero paid provider calls and $0 provider charges. Local compute and platform costs were not priced. Independent reconstruction means a separate implementation and review path in the same AI-assisted project; it is not external human adjudication or a separate laboratory replication. No old downloader, stopped monitor, human-review archive or owner-deferred author declaration was changed.

## Completion evidence

The [independent runtime reconstruction](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/reconstruction/runtime-actual01/RUNTIME-RECONSTRUCTION.json) passes all 19 logical cases. Its hash is `c1f3507eaa98e398c91bfaa7db9a851a09e5d9360e1612a2676257487dcf4f7b`. It checks all 16 ordinary native records, exact source/claim/accounting joins, bounded synthetic feature/contribution arithmetic, the actual interruption and the controlled ownership race. The [runtime review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/reconstruction/runtime-actual01/REVIEW.md) accounts for 15 reserved workflow attempts, 15 provider entries, 14 scripted dispatches and nine committed source-linked claims; five commit states have rebuilt feature/contribution/abstention arithmetic. The interrupted first case remains unresolved, the next case unexecuted, and only one race participant dispatches. This is expected failure behavior under these stimuli, not successful recovery of an unknown billed call. Held prospective readers and postexecution outer-audit glue are identified separately.

The separate exact postflight passes with hash `45dd026586ef7eeb305c8e1ab4999eaaec73cfde48343976b7206684134a8d8b`. The [final obligation coverage](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-inspect-20261106/integration/RESULT-COVERAGE-FINAL.md) maps all 27 policy obligations to exact primary cases, runtime controls, qualified tests and gaps. Archive-policy conformance is complete over the declared set; runtime portability is partial and explicitly bounded. This distinction is the result of BG05, not an omitted negative finding.

The primary and runtime output directories are sealed and must not be rerun. BG06 follows with the cross-stage requirements audit and documentation/memory closure. Scientific capability improvements and full production migration remain separate future work.
