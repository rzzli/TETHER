# BG04 operational resource scope — snapshot 02

This [new resource snapshot](RESOURCE-SCOPE-02.json) preserves [snapshot 01](RESOURCE-SCOPE-01.json) and adds the completed source-inclusive evaluator. The externally supplied evaluator seal SHA-256 is `118711b7e7552750e441380b7abf8f60b68096ae98ef3163cf96754e7423fa6f`. Its bound `resources.json` and aggregate `REPORT.json` were hash-checked; the completed outer-control record was captured and reconciled against the same generation anchor and aggregate identity. Its SHA-256 is `1050b77e9f073159ee4a0bbc4a5b62def5137d9fa76a6516d80e958158447302`. No raw answer-reference file, new inference or new retrieval was used in this resource extraction.

| Completed evaluator quantity | Value | Measurement scope |
|---|---:|---|
| Outer evaluator elapsed | 882.172 s | Wrapper from before evaluator call through its return; excludes earlier imports and final controller-record serialization. |
| Outer controller CPU | 817.953125 s | Same wrapper interval. |
| Internal evaluator elapsed | 881.797 s | Resource field captured before final evaluator product/journal/seal publication. |
| Internal evaluator CPU | 817.640625 s | Same internal capture boundary. |
| Reported process-lifetime peak working set | 579,141,632 bytes | OS process-lifetime value, not incremental evaluator memory or GPU memory. Current working set at capture was 48,377,856 bytes. |
| Unique model/runtime/receipt bytes verified | 9,112,208,256 bytes | Sum of unique declared asset sizes, not physical I/O, additional download volume or a separate hashing timer. |
| New model calls / retrieval calls | 0 / 0 | Post-seal replay, reference reconstruction and scoring only. |
| External-provider charges | $0 | Electricity, hardware depreciation and labour remain unmeasured. |

The approximately 14.7-minute evaluator includes full source/model/session replay, native answer scoring and reporting. **It is not the marginal cost of the admission predicate.** `verify_candidate` was not separately timed in generation, and its marginal latency remains unknown. Separate independent operational auditing and blind native reconstruction are additional procedures; their costs are not invented or folded into this evaluator timer.

All snapshot 01 boundaries remain: the generation worker's 1,161.953 seconds excludes later parent finalization; the pre-seal parent timer excludes final recovery/inventory/sealing; no outer monotonic total-generation timer was retained. The declared-start-to-seal-filesystem interval is descriptive chronology only. Do not sum overlapping parent, worker, native-process and evaluator timers as if they were independent cost measurements, and do not call the worker deadline a hard bound on the entire workflow.

Previously established operational quantities are unchanged: 199 generations and 199 tokenizer attempts, 443,470 input and 34,279 output tokens, normal server cleanup, 141,355,700 known source-body bytes, 189,016,148 collection product bytes, and 57,770,725 generation inventory bytes. Body bytes exclude protocol overhead; retained products are not physical I/O. Native-process CPU/RAM sampling remains scoped to snapshot 01, with GPU memory and energy unknown.

The extraction used only bounded operational/aggregate reads through [the retained script](summarize_resources02.py); it did not alter frozen production code. This resource note does not replace independent native-metric agreement, source-alignment reconstruction or the final completion audit.
