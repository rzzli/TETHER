# Resource path review: accepted six-stage framework

28 October 2026 UTC. **The successful-path code performs substantial repeated verification work; its cost needs prospective profiling before optimization or integrated native feasibility claims.** This read-only AI engineering review traces accepted0.3.11 source. It changes no runtime, budget, source policy or benchmark. No case, tokenizer, SDK, model, formal verifier or GGUF was run/read; evaluator payloads were not opened.

[RESOURCE-PATH-REVIEW.json](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/RESOURCE-PATH-REVIEW.json), SHA-256 `ef70b1817450779a0573e7e730254518cd22f2fb328327e6ced93cf86412f5f6`, retains17 source pins, exact callsite/count derivations, recorded descriptors, limitations and ordered future work. The inspected source/resource bytes match wheel `b0d7573be994e3f44e3d942a1944cddb2e43e1306a64cfd6480dd05e3415a276`. No installed module or frozen evidence was modified.

## What the timing evidence establishes

The retained [stage timing audit](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-duration-20261028/STAGE-TIMING-AUDIT.json) and [resource note](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-duration-20261028/RESOURCE-RISK-NOTE.md) report one0.3.10 simulated case at **295.922/300s**, leaving **4.078s**. It used six real offline tokenizer children, six simulated HTTP responses and a simulated process; actual native startup/inference was absent. These old observations are not a newly measured0.3.11 case.

| Retained0.3.10 measure | Seconds | Interpretation |
|---|---:|---|
| Context ready through sixth acceptance |185.391| Root-clock interval containing stage preparation, quotation, child work, admission and verification |
| Sum of six quote-file intervals |102.298| Includes verification/setup and tokenizer work; not exclusive hashing time |
| Sum of six tokenizer-child intervals |2.063| Child intervals only |
| Sum of quote-ready→accepted intervals |46.688| Includes admission/finalization/verification, with simulated transport |
| Receipt sealing measurement |63.266| Includes final checks/replay; overlaps root summary→sealed interval |
| Separate replay/postcheck interval |61.203| Outside original case execution; includes helper postchecks |

These quantities overlap and must not be added. Subtracting child duration from quote duration does not identify hashing cost. No controlled cache/load/I/O/CPU comparison or real inference measurement exists here. The older0.3.9 timing difference is not a causal regression finding. Parent peak working set497,668,096B does not measure tokenizer/GPU/model peaks or future memory fit.

## Execution through the six stages

The fixed schedule is one AsOf stage followed by five adapted Virtual Biotech stages:

| Cell | Stage | Prior same-arm cells entering feedback |
|---:|---|---:|
|0|AsOf interpretation|0|
|1|Chief of staff|0|
|2|Coordinator delegate|1|
|3|Mapped specialist|2|
|4|Scientific reviewer|3|
|5|Coordinator synthesis|4|

The [controller loop](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/authority_four_arm.py:902) derives an authoritative stage and payload, prepares a token quote, authenticates capacity, creates a `StudySession`, executes once, finishes, verifies the child and accepts it. This study route uses `quote()`/`generate()`. It performs no additional `Backend.select()` transport: source IDs for later feedback are derived from retained literal-quote records at lines554–555.

Before the loop, the controller holds collected-source leases, captures a current package proof, prepares source/retrieval inputs, prepares the tokenizer specification, then holds the native-asset lease and owns one server scope ([entry](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/authority_four_arm.py:837)). Every operation shares the existing300s case deadline. No resource correction is authorized by this review before the native conformance gates.

## Complete asset hash passes

The accepted tokenizer descriptor records three GGUF shards totaling **8,988,110,496B (8.371GiB)**. These sizes and hashes were read from the existing packaged metadata; no weight file was opened. On the complete successful native/simulated-native path, the following code requires16 complete selected-model hash passes:

| Successful-path boundary | Passes | Selected model hash input bytes |
|---|---:|---:|
| Tokenizer specification preparation |1|8,988,110,496|
| Six prompt quotes: before and after each tokenizer child |12|107,857,325,952|
| Outer native-asset lease admission |1|8,988,110,496|
| Owned server executable/input proof verification |1|8,988,110,496|
| Writer's final source-inclusive verifier acquires a fresh native lease |1|8,988,110,496|
| **Total** |**16**|**143,809,767,936 (133.933GiB)**|

The relevant loops are [tokenizer-spec admission](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/tokenization.py:202), [quote pre/post checks](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/tokenization.py:465), [native lease entry](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/native_mode.py:187), [server proof checks](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/process.py:149), and [nested final verifier lease](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/authority_four_arm.py:1218).

This is **source-derived logical hash input volume**, conditional on successful completion. It is not observed physical disk traffic, RAM consumption, elapsed hashing time or a throughput estimate. Failure paths can stop partway. It excludes native tokenizer/server file reads and any demand-paging behavior. The full34-asset tokenizer inventory totals9,078,912,160B; the native descriptor adds a9,216B server executable for three of those boundaries. The JSON supplies the complete metadata arithmetic.

Quote verification is a separate path: [verify_tokenization](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/tokenization.py:548) explicitly opens archived quote members/package proofs, without model assets or a child. `TrustedTokenCapacity.reservation` and `verify` repeatedly invoke it. Native `_weights` at lines94–115 reads the bounded archived specification and compares descriptor identities; it does not rehash GGUF bytes. Those calls must not be counted as additional full model reads. A fresh independent external verification does acquire its own native lease and adds at least one model pass; it is not part of the16 writer-path passes.

## Package, source and predecessor work

[Package capture](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/proofs.py:152) inventories and hashes every executing-package `.py` plus the consumer's required resources. `verify_package_proof` at203–219 recaptures current files and compares the canonical fingerprint. The installed source inventory contains59 Python modules. A conservative successful-path lower bound is **31 full scans /1,829 Python-file hashes**: one controller capture, six tokenization captures, six session captures, six call preflights, six finishes and six immediate child verifications. Capacity proofs, source-aware native verification, predecessor checks and final replay add further work;31 is not the total measured count.

[StudySession](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/session.py:248) verifies capacity before dispatch, validates the captured response and rechecks accepted state at finish. The controller then invokes `verify_study` independently for the child. Native verification checks package/payload/source authority and the token-capacity proof again. These repeated checks have integrity purposes. Raw package byte volume alone cannot establish whether filesystem walks, parsing, canonicalization, source reconstruction or another activity dominates time.

[Source preparation](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/source_preparation.py:232) hashes primary inputs, hashes all approved authority files before and after admission, loads/reconstructs a snapshot and replays selected original rows. `verify_source_preparation` at500–558 reruns that build from original eligible inputs. Retrieval verification calls it again. Snapshot admission hashes normalized packet bytes and [ancestor/receipt proofs](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/provenance.py:105); selected-row replay reads actual mapping and evidence rows under caller-held leases. Source byte totals and row-group reread counts were not estimated by opening evaluator/source payloads in this audit.

The [source cache](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/authority_four_arm.py:277) hashes retained authority/preparation members before a cache hit. The [stage cache](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/authority_four_arm.py:361) similarly captures predecessor cell/quote members before comparing its key; a miss recursively verifies predecessors. There are10 same-arm predecessor edges in one cold top-level schedule, with more calls from payload/response validation and replay. Fresh final/external verifiers start new caches. Cache hits already have validation work and cannot be assumed free.

## Finalization and prospective candidates

[Writer sealing](D:/Projects/drug_target_agents/data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/study/authority_four_arm.py:1054) checks package/inventory, hashes every output member and invokes `_verify` while original source/native leases remain active. That fresh verifier reopens source/native capabilities, hashes every bundle artifact before and after replay and verifies all six children. Source release and final receipt publication follow. The bundle's small retained size does not bound source-inclusive verification cost.

The strongest profiling candidates are:

1. Repeated full asset checks under overlapping live leases, especially pre/post prompt tokenization and nested writer replay. Any later reuse would need a trusted current-case capability bound to exact original paths, expected hashes, required asset sets and still-live handles. External replay must independently rehash originals.
2. Repeated package proof inventories, token-proof parsing and canonicalization. Reuse would require a complete package/resource lease and an in-memory case context. The current package capture itself is not a whole-case lease.
3. Raw-source reconstruction, Parquet/mapping row reads and growing predecessor/cache-key work. Measure each separately before choosing a correction; preserve eligibility, complete ancestors, original-row fidelity and source-inclusive semantic replay.
4. Cooperative deadline granularity. `stable_read.hash_file` checks within chunks, whereas `proofs.capture_file` and `serde.sha256_file` have no per-chunk deadline parameter. This is a static boundary worth measuring/reviewing, not a demonstrated accepted-run overrun or bypass.

No optimization may trust a serialized `already_verified` flag, cache across independent runs, replace original paths with archive assertions, omit canonical receipt members, weaken the approved asset policy or treat an earlier measurement as permanent authority. Directory/file lease limitations documented by `stable_read.py` remain trust boundaries. The existing in-admission ancestor dictionary is local state, not a serialized readiness flag.

## Small ordered instrumentation plan

1. After native conformance, freeze a separately reviewed profiling protocol with fixed inputs, code, attempt count and unchanged300s budget. Add pure instrumentation/mutation/failure tests first.
2. Record bounded nested span IDs, monotonic/CPU durations, actual bytes/calls and live lease identities for hashing, package proofs, source/row replay, cache-key construction, quote/generation/admission and final replay/sealing. Keep inclusive/exclusive intervals distinct and account for instrumentation overhead. Skip no proofs.
3. Execute only the explicitly authorized fixed profiling schedule; retain timeouts and all failures. Do not rerun until a favorable wall time appears or infer physical I/O from logical bytes.
4. Select one measured bottleneck and prospectively version its smallest correction. Require unchanged canonical scientific/source artifacts, compatible receipts, mutation/deadline/failure regressions and a fresh source-inclusive independent verifier with no inherited cache.
5. Reassess actual startup plus six native answers only after those gates. Timing improvements would not resolve fresh-source, coverage, human review or biological validity requirements.

## Exact source hashes

Paths below are within `data/cache/recovery-step9-generation-wheel-20261028/environment/Lib/site-packages/asof/`; line citations above refer to these exact bytes. The JSON retains absolute-resolvable paths and all source/resource hashes.

| Source | SHA-256 |
|---|---|
| `study/authority_four_arm.py` | `31c4d5e660747b30cc3446fd8a40e199aa1fc86a14cd2cd9abbe4218d5ca60f7` |
| `study/tokenization.py` | `460e2aeaa0a2e57075f448bad71559e9d76801bbaddbbccf67ebeb202c65c711` |
| `study/token_capacity.py` | `7995a58b43829879bbf221886b59cfb332873b6d979a6ed5e5a8d61035eb39ef` |
| `study/native_mode.py` | `637cbd706936fc58614dc91c3b743eb98ed4ff0577fc25b7af6d8bab9c510e2b` |
| `study/process.py` | `5e2378eefc1ffafb21af1555a3de5de3c725cc3ae8f3365aafdd47ea51a08e91` |
| `study/session.py` | `419af810d7ca8f61d7eb46c34ff3aa2fcdfc845b9e00a14cdb491a6ff99661e1` |
| `study/proofs.py` | `4d5e7170dafb15b1c701d77e639cb1acf7ecfcdc4546f6c9ce4e7ba9ea649b0f` |
| `study/stable_read.py` | `40d71fa950422e8f19fd863952b3e7ea39237c12d1c92a9d38b0a9c23a2f4a0b` |
| `study/collected_source.py` | `04b9d4d7999d893f9a7342dc6044994b2e212ec677dfb31765cb3a40ede2ea9c` |
| `study/source_preparation.py` | `a01ae55d3a06c1130f293eec4fd10872b62dcfaf43c49b7e9da88dbee23418c1` |
| `study/retrieval_preparation.py` | `5672daf0da1b98255922a2360fdf6ed4d36edc630b25376ab2b83ffc76ea6fba` |
| `study/source_rows.py` | `977c3b898da1796a18830854ab086f3d94469597bf07c16c3204a1865aa36138` |
| `study/native_interpretation.py` | `decc0ba3dd7dca8c84883b58bf3fe8acb0b277ef0aaf5a5a7186b7864477d674` |
| `study/native.py` | `d5bee09aff10d50073a606d3bb9d806204aa7ef5f0f23b9ed6a7cc261e6bb97a` |
| `chrono.py` | `e8c994fadbef9e3007ffef549a5a9771502893ebaf5d00a04ab857df1bdc25cb` |
| `provenance.py` | `c3ed818ebd48b47bd7219a65ac495f9f86675680994fb3a0dd587fa56393b446` |
| `serde.py` | `5f5daf814e4debe49cfce22a25b2d6b71cc20b6e9184ddb6a4a4c5a4eeb5b7a8` |
