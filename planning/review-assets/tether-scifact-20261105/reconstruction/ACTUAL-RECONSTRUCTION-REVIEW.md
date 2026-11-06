# Independent reconstruction of the first native SciFact stage

**Result: PASS for result reconstruction; weak scientific prediction performance.** The separate standard-library analysis reproduced all retained primary results on its first actual-stage attempt. No producer rerun, retuning, case exclusion or analyzer correction was required.

The stage remains `data/benchmark/scifact/native-20261105T234805Z-attempt01`. Its externally supplied receipt SHA-256 remains `3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968`.

Independent outputs are under `data/benchmark/scifact/reconstruction-20261105-attempt01`. The reconstruction imports no producer, runner, projector, evaluator-wrapper or policy implementation. It executes the unchanged pinned official evaluator CLI and independently rebuilds schedules, strict correctness, counts, rates, source components and resource totals.

| Result | Reconstructed value |
|---|---:|
| Scheduled / produced / policy accepted | 300 / 300 / 300 |
| Operational failure or rejection placeholders | 0 |
| Strict correct and admitted | 27/300 (9.00%) |
| SUPPORT strict correct | 1/124 |
| CONTRADICT strict correct | 0/64 |
| NEI strict correct | 26/112 |
| Successfully produced native NEI predictions | 53 |
| Development source/exact-text components | 247 |
| Selected retrieval depth / rationale threshold | 5 / 0.25 |
| Annotated claim/document pairs retrieved | 159/209 (76.08%) |
| Nonempty-gold claims with complete evidence-document set retrieved | 147/188 (78.19%) |

NEI cases have null retrieval recall, rather than artificial perfect recall. Source-component counts within reference classes overlap and must not be summed to obtain the 247 distinct development components.

| Official metric | Raw F1 | Checked F1 |
|---|---:|---:|
| Abstract label only | 0.13506013 | 0.13506013 |
| Abstract rationalized | 0.08695652 | 0.08695652 |
| Sentence selection | 0.07861991 | 0.07861991 |
| Sentence label | 0.04807692 | 0.04807692 |

All twelve precision/recall/F1 fields match exactly for both arms, as do all nine tuning configurations and their declared selection tie-break. All 300 paired candidates are identical across the producer/checker handoff. Across tuning and development, 10,110 retrieved-document occurrences and 12,777 returned-sentence occurrences were checked against original source fields. These are occurrences, not counts of unique articles or sentences.

The result supports a narrow statement: provenance and execution-accounting checks preserved the native candidate outputs and metrics. It does not show improved semantic accuracy. Only one case with a nonempty gold evidence set met the strict case rule. The fact that 147 such cases had the complete gold document set retrieved makes a pure retrieval explanation insufficient; label/rationale decisions and extra-evidence predictions remain material limitations. This is a descriptive diagnosis, not a causal ablation.

| Measured phase | Sum of wall seconds |
|---|---:|
| Fitting | 3.413 |
| Nine tuning setups | 1.867 |
| 738 tuning predictions | 14.092 |
| Nine tuning scorers | 0.509 |
| Development setup | 0.210 |
| 300 development predictions | 4.344 |
| Checker setup / source reconstruction | 2.590 |
| 300 candidate checks | 0.271 |
| Checker verification | 2.606 |
| Development scorer | 0.089 |
| Recorded controller operations | 500.203 |

The stage elapsed time was 587.287 seconds and provider spending was $0. Recorded controller work, including repeated source/runtime verification, dominates these measurements. Cell costs do not sum to the end-to-end elapsed time: process startup, controller work and other orchestration overhead have separate scopes. The largest recorded process-lifetime memory peak across the reported panels was 304,451,584 bytes (290.35 MiB).

Input/output byte fields are logical declared product sizes, not physical disk I/O. Checker setup input bytes cover its candidate-array product and do not enumerate every source-context read. Checker verification input/output sizes remain unknown, explicitly counted as unknown in the report. Memory peaks are maxima, not additive allocations. Independent summation cannot remeasure historical timings.

Remaining limits: this uses public development annotations rather than a private test set; no independent biological adjudication or claim of clinical validity is made; the prototype's strict-case accuracy is low; the policy deliberately accepts semantically incorrect but provenance-valid outputs; the managed-Python access audit is not an OS sandbox; source/package hashes do not attest every host component or transient runtime state. Descriptive class/source strata have no inferential confidence intervals. Retuning on these development outcomes would require a new declared experiment and an appropriate untouched evaluation set.

Retained hashes:

- `RECONSTRUCTION.json`: `35c589e3ea7706844196830305c61944dd6c66336e76f13d5a3da0bc470d3d07`
- Reconstruction `RECEIPT.json`: `07e9d33fa0d8d989c458edd1a956b3a9e7b4701f5665e10e3fcdc0cf5fa30bed`
- `rebuilt-evaluation.json`: `531267c23f67f9e56a348e610749f68a7c456d5a3b2bc592b4b720ec6a777d34`
- `paired-candidates.json`: `bb0083c7dfec0cc1ac43aa2f2f680d6383a661cff75e6ae9a4f6ccb5c3dbbeef`
- `source-class-strata.json`: `503b796005aede1f85ca73cc1422204849d4acbe8854b330a469e43ed72b4a3f`
- `retrieval-coverage.json`: `83a050593631ea8b29465851e508376807ba61ec27064060ff0d8655dec03d86`

The helper was qualified with eighteen fictional tests before actual reconstruction; the earlier seventeen-test qualification remains preserved. The separate three-case bytecode peer check also passed without changing native caches or executing their module code.
