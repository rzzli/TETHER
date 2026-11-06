# Independent primary BG05 reconstruction

The frozen 109-case comparison passed independent reconstruction across all nine batches: **981/981 scheduled cells conform**, with 327/327 per arm. Each arm retained 132 expected accepts, 192 expected rejects and three inspection cases across its three repetitions. There were no false admissions, false rejections or unscored policy outcomes. All 327 native Inspect sample/request/candidate/scorer joins passed, with no native errors or missing scores.

The standard-library reader imported no Inspect, controller or policy validator. It checked the externally anchored stage/freeze, complete output inventory, case/worker/parent receipts and chains, original corpus inventory, native JSON logs and complete published count/case projections. No producer run, candidate or source was changed, and the analyzer needed no correction on the actual study.

| Arm | Median full supervised batch | Three-repeat range | Median paired time / bare independent |
|---|---:|---:|---:|
| Bare independent policy | 25.063 s | 24.922–25.250 s | 1.000 |
| Bare TETHER | 23.687 s | 22.953–23.844 s | 0.944317 |
| Inspect plus independent policy | 36.485 s | 34.828–36.875 s | 1.460396 |

The median paired Inspect/TETHER ratio is **1.546511**, range **1.470342–1.589553**. TETHER's paired batch time is about **5.6% lower** than bare independent's here. These are fresh serial batch measurements; the previous cold per-cell ratio is a different condition and must not replace them. The native framework also performs additional scheduling, scoring and logging, so this result alone does not identify wasteful code or establish general framework superiority.

Source verification covered **11,606 pinned input files / 236,179,241 logical bytes**, the exact **1,966-file / 342-directory** frozen corpus, and **278 original source-path mappings to 153 distinct archived files**. Repeated source identities are explicitly deduplicated in the archive; mappings are not independent implementations. The retained study has **4,706 output files / 18,384,895 bytes**. Global integrity declarations and the narrower per-batch pin partition reconciled; no current source mismatch was found. These are logical artifact sizes, not physical disk I/O measurements.

This supports finite archive-policy interoperability and the stated descriptive cost comparison. The 109 cases are exposed authored constructions, include a duplicated construction, and were repeated three times per arm. They are not 981 independent examples, a natural fault sample or a scientific-quality benchmark. The reader verifies the original source identities and result arithmetic; it does not independently reimplement every biomedical admission rule. Persistent runtime witnesses and their bounded synthetic feature/contribution replay are a separate unfinished analysis at this checkpoint.

Evidence:

- [RECONSTRUCTION.json](RECONSTRUCTION.json): SHA256 `33720734fb1132fdd91a215f4bc6497d540c0e2ec56b382f859bb6c9e6683ce6`.
- [SUMMARY-02.json](SUMMARY-02.json): SHA256 `dfe30cea88aeeb0c92656862ca1767617089d7011e840a9fb4da799051b23e97`, including all paired ratios and independently counted operational outcomes.
- Stage seal: `d0ea739f5e4cf004cb37802df3ffe25dcf97e1756c0ca0a1c52293a147bf1f9c`.
- Prospective freeze: `dd2e5e3d07cac7e966a02bff34b9b2e2fb1ea30507d6d861630d76b57244e6b4`.

Execution used isolated Python with bytecode writes disabled and a fresh cache prefix. No model/provider calls or automatic retries were made by reconstruction.
