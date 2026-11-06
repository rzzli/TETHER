# BG04 operational resource scope — snapshot 01

The [resource JSON](RESOURCE-SCOPE-01.json) was derived from the generation seal, its manifest/worker terminal/journal records, and the collection manifest/seal after checking the external hashes supplied by the root. The generation freeze was also externally anchored. The [extraction script](summarize_resources.py) reads actual bounded file sizes and imports no production code. This is verification of selected operational records, **not** a full inventory rehash or independent scientific-result audit. Answer references, native correctness and scorer results were not opened. No new inference or retrieval occurred.

| Operational quantity | Retained value | Scope |
|---|---:|---|
| Collection cases | 199 completed | 198 with retained eligible sources; one completed without sources. This says nothing about relevance or answer support. |
| Collection wall time | 2,051.906 s | Collector field captured before final manifest/journal/seal publication. |
| Collection controller CPU | 55.515625 s | HTTP-child CPU and collection peak memory are uninstrumented. |
| Generation attempts / tokenizer attempts | 199 / 199 | All producer cases completed and all 199 candidates admitted; correctness is not part of this resource review. |
| Measured native input / output tokens | 443,470 / 34,279 | Estimated token charges and unresolved generation counts are zero in the anchored operational records. |
| Supervised generation worker elapsed | 1,161.953 s | Parent supervisor measurement; worker exited zero, pipes closed, cleanup errors empty. Covers the supervised worker, not subsequent parent finalization. |
| Internal worker wall / CPU | 1,161.359 s / 364.515625 s | Worker controller CPU excludes native child-process CPU. Timers overlap other layers; do not sum wall times. |
| Owned setup including asset verification | 12.797 s | Combined server context entry/verification/startup; earlier source verification is outside this timer. No isolated hashing or model-load duration is available. |
| Parent pre-seal wall / CPU | 1,162.156 s / 18.796875 s | Captured before `_seal`; excludes final recovery, publication, inventory and sealing. |

The complete generation seal declares **3,598 files / 57,770,725 bytes**, excluding `SEALED.json` itself. The collection product inventory declares **3,186 files / 189,016,148 bytes**, with metadata outside that product inventory accounted separately by its manifest/seal structure. Neither quantity is physical disk I/O.

Collection records contain **141,355,700 known response-body bytes**, zero conservative unknown-transfer allowance, and **1,361,055 selected text bytes**. Body bytes exclude HTTP headers, TLS and other wire overhead. Selected text is a derived subset; it must not be counted as additional external transfer. Retained product bytes include transformations and records, so they are not interchangeable with downloaded body bytes.

The native process was sampled every 0.5 seconds after server readiness through the case loop: **2,180 sample records**, with no recorded sampling errors. Maximum sampled current working set was **16,614,191,104 bytes**; maximum reported OS process-lifetime peak working set was **16,633,806,848 bytes**. The latter may include startup peaks before the first poll; current-working-set sampling can miss short peaks. Neither is GPU memory. The first and last sampled cumulative native CPU readings were 3.84375 and 290.390625 seconds, giving a 286.546875-second observed sampling-window increase. These are process CPU readings, not complete workflow CPU or GPU time. GPU memory, energy and finalization peak memory remain unknown.

There is **no separately instrumented marginal admission-check timer**: `verify_candidate` shares a case wall record with other work. The saved parent resource field also does not measure total end-to-end latency. The parent reservation UTC timestamp is `2026-11-06T01:54:42.954135+00:00`; the generation seal's observed filesystem modification time is `2026-11-06T02:24:04.397615+00:00`. Their 1,761.44348-second interval is descriptive filesystem/declarative chronology, not an attested monotonic stopwatch. Exact finalization duration and measured total-stage wall time remain null. The worker's 10,800-second limit does not hard-bound subsequent finalization.

At this snapshot, `SCORE-CONTROL-01.json` was still zero bytes. Scorer/reconstruction elapsed time and CPU are therefore pending, not zero; no native metrics were inspected. A later resource snapshot can add completed outer-control measurements after authorization without rewriting this point-in-time record.

The anchored generation and collection records report **$0 external-provider charges**. Electricity, hardware depreciation and labour are unmeasured; this does not establish zero total cost. Earlier fictional controls, development and failed attempts remain separate costs, not hidden within or fabricated as part of this actual evaluation.
