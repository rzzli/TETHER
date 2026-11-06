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
| Combined fictional components | 94 tests pass; components-attempt03/VALIDATION.json; all tested source pins unchanged |
| Actual query capacity, without inference | Final canonical v2: all 199 pass with zero or eight fictional 1,000-byte ASCII passages; maximum prompt 10,333 bytes under 14,000 cap. Real escaped Unicode can still trigger explicit capacity failure. |
| Exact retrieval pipeline, nonbenchmark question | Five HTTP200 requests, three licensed full texts, 664,234 bytes, eight passages, 10.344 seconds; not benchmark coverage |
| Native model transport/helper | 17 model tests (included in 59) plus four separate helper controls pass; Windows descendant containment exercised with a tiny non-model child |
| Import/runtime source policy | Fresh empty cache prefix qualified; all 85 maintained sources equal installed copies and original audit pins |
| Actual fictional model smoke | Attempt01 failed before inference; attempt02 selected the wrong unsure option and failed sampler-type verification. Attempt03 was withdrawn before dispatch. Attempt04 passes transport and archived replay, then fails the unchanged semantic control with another wrong unsure answer. Cleanup verified; failures retained. |
| Corrected MCQ transport/prompt | Failing-first type and canonical-order regressions; 19 model tests pass. Attempt04 exercises actual native transport/replay with outgoing `temperature: 0.0` and deterministic version-two prompt. No verifier equality was relaxed. |
| Source/generation/evaluation controllers | Collector 12, generation 10 and scorer 11 fictional tests included in the 94; all-case partial records, source joins and paired replay covered |
| Final benchmark controller/configuration freeze | Sealed before benchmark acquisition: [FREEZE.json](freeze-attempt01/FREEZE.json), SHA256 `8172610c5637d7a952f80be8a2fe89d01a0c421d638ae254e30c76541886d6f7`; ten experiment modules, fixed 199 tasks, bounded collection/generation, amendment A01 |
| Actual benchmark retrieval, answering, scoring, independent reconstruction | Not started |

The [protocol](<../../TETHER LitQA2 Evaluation Protocol 2026-11-06.md>) and
[data qualification](data/DATA-QUALIFICATION-01.json) distinguish tests, source
access and actual scientific performance. Source alignment is not entailment.
The completed SciFact experiment and maintained core remain unchanged.

Next: freeze configuration/code and execute the all-199 descriptive weak baseline
under protocol amendment A01. There will be no more prompt changes or fictional
model retries. Operational qualification and failed semantic controls remain
separate. Native task accuracy is unknown; even an all-unsure result must remain
visible as a negative measurement. Source acquisition and generation are not yet
started at this checkpoint.
A source failure remains in the all-199 denominator. No historical model cell,
old downloader or stopped monitor is restarted. No paid provider or human gate.
