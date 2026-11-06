# BG04 checkpoint

6 November 2026 UTC. **In progress; no benchmark candidate generated or scored.**
BG01–BG03 are complete in their declared scopes (SciFact completion commit `5dae314`).

The original public 199-item LitQA2 family was selected before candidate performance.
Pinned acquisition: 17 files / 719,061 bytes. JSONL/Parquet shared fields independently
reconcile for all 199 records. Final preparation attempt02 retains every case and
two original duplicate-distractor rows; the overly strict first attempt is preserved.
Both the preparer and native codec now permit these original indexed choices.

| Gate | Status |
|---|---|
| Family choice, source/method review and original acquisition | Complete in public-family scope |
| Projection/reference isolation | All 199 rows in preparation-attempt02; manifest `7c085ccf94f0e3e3270727efbc3b250e43ac52168aad009ee362662fbd58122b` |
| Combined fictional components | 97 tests pass after A02; components-attempt04/VALIDATION.json; all tested source pins unchanged during qualification |
| Actual query capacity, without inference | Final canonical v2: all 199 pass with zero or eight fictional 1,000-byte ASCII passages; maximum prompt 10,333 bytes under 14,000 cap. Real escaped Unicode can still trigger explicit capacity failure. |
| Exact retrieval pipeline, nonbenchmark question | Five HTTP200 requests, three licensed full texts, 664,234 bytes, eight passages, 10.344 seconds; not benchmark coverage |
| Native model transport/helper | 17 model tests (included in 59) plus four separate helper controls pass; Windows descendant containment exercised with a tiny non-model child |
| Import/runtime source policy | Fresh empty cache prefix qualified; all 85 maintained sources equal installed copies and original audit pins |
| Actual fictional model smoke | Attempt01 failed before inference; attempt02 selected the wrong unsure option and failed sampler-type verification. Attempt03 was withdrawn before dispatch. Attempt04 passes transport and archived replay, then fails the unchanged semantic control with another wrong unsure answer. Cleanup verified; failures retained. |
| Corrected MCQ transport/prompt | Failing-first type and canonical-order regressions; 19 model tests pass. Attempt04 exercises actual native transport/replay with outgoing `temperature: 0.0` and deterministic version-two prompt. No verifier equality was relaxed. |
| Source/generation/evaluation controllers | Collector 12, generation 10 and scorer 11 fictional tests included in the 94; all-case partial records, source joins and paired replay covered |
| Final benchmark controller/configuration freeze | Sealed before benchmark acquisition: [FREEZE.json](freeze-attempt01/FREEZE.json), SHA256 `8172610c5637d7a952f80be8a2fe89d01a0c421d638ae254e30c76541886d6f7`; ten experiment modules, fixed 199 tasks, bounded collection/generation, amendment A01 |
| Actual benchmark source collection | Complete: all 199 cases, 198 with articles and one empty; 995 requests, 141,355,700 response-body bytes, zero unknown transfer reservation; both full source and independent operational audits pass |
| Actual source prompt capacity | All 199 fit; largest actual prompt 9,980 bytes under 14,000; no reference access or generation |
| Prospective generation correction A02 | Two worker cache-root checks corrected only after collection audit; maintained regression included in 97 tests. [Generation freeze](stage/generation-freeze-attempt02/GENERATION-FREEZE.json) SHA256 `4359d589205caec39085872cc72cd5799323e2285e0993b58405e7e70ccd2fe5` preserves all scientific settings |
| Benchmark answering, scoring and independent result reconstruction | Not started |

The [protocol](<../../TETHER LitQA2 Evaluation Protocol 2026-11-06.md>) and
[data qualification](data/DATA-QUALIFICATION-01.json) distinguish tests, source
access and actual scientific performance. Source alignment is not entailment.
The completed SciFact experiment and maintained core remain unchanged.

Next: execute the all-199 descriptive weak baseline under A01 and the narrow
pre-dispatch A02 launch correction. There will be no more prompt changes or
fictional model retries. The accepted collection cutoff is
`2026-11-06T01:47:57.427510+00:00`. Collection took 2,052.406 supervised seconds;
its 3,186-file inventory retains 189,016,148 product bytes. Source relevance and
answer accuracy remain unknown until post-generation evaluation. Even an
all-unsure result must remain visible as a negative measurement.
A source failure remains in the all-199 denominator. No historical model cell,
old downloader or stopped monitor is restarted. No paid provider or human gate.
