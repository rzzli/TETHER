# SC04: independent reconstruction of closed auxiliary phases

**2026-11-06 — passed within the stated partial-phase scope.** All 199 expansion slots, 398 collection products and 398 ranking slots were independently reconstructed from the completed primary phase packages. The probe took **397.328 seconds**, used the qualified analysis readers unchanged, and made no model or network calls.

This does **not** accept a completed primary root, inspect answer queries/outputs or reference keys, verify the supplied-source diagnostic, or score scientific outcomes. Final source-inclusive run verification remains required after both executions close. No prompt, producer, protocol or qualified analyzer was changed.

## What passed

- External expansion/ranking package anchors; the ranking → collection → expansion parent chain; exact file inventories and stage receipt hashes.
- All scheduled identities, phase journals, slot products, supervised completion, maintained-replay bindings and role-specific captured Python-open audits. Zero denied events were recorded.
- Every collection's original captured bytes, article/source text, collection policy, expansion-parent link and deterministic passage pool.
- Every dispatched auxiliary cell's question-only inputs, prompt, grammar, model/endpoint identity, tokenization, native response, output decoding, usage, terminal events and fallback product. Ranking inputs matched the reconstructed collection pools exactly.
- Probe artifact hashes and unchanged analysis-source fingerprints.

| Phase | Scheduled | Completed | `codec_failure` fallback | Empty pool / no call |
|---|---:|---:|---:|---:|
| Expansion | 199 | 193 | 6 | 0 |
| Collection | 398 | 398 | — | — |
| Ranking | 398 | 164 | 196 | 38 |

**196 of 360 dispatched ranking calls (54.4%) failed output validation.** Their prescribed **original pool order (lexical passage order)** fallback was retained and reconciled; these are not successful rerankings. The six expansion failures used the lexical-query fallback. No capacity-status cells occurred. This limits delivery of the intended interventions, without establishing their effect on answer correctness. Keep every scheduled case in subsequent analysis and report availability and fallback frequency alongside paired outcomes.

The 202 retained failure terminals specify only `error_type: OutputCodecError` and `stage: verification`. A **separate, subsequent diagnostic** rebound the already-audited auxiliary input/response bytes to their phase packages, re-ran the qualified decoder, and independently checked the literal outputs against the frozen rules:

- All six expansion failures repeated terms after case folding. For example, expansion slot 0044 repeated `H3K27Ac peaks` as `H3K27ac peaks` within one query.
- Of 196 ranking failures, 194 omitted offered IDs; one repeated an ID while retaining all offered IDs; one both omitted and repeated IDs. Slot 0002 returned 11 of 13 offered IDs, omitting `p01` and `p02`; slot 0087 repeated `p09`; slot 0142 omitted `p13`/`p14` and repeated `p09`.
- All 202 failures ended with native EOS; their maximum output lengths were 93 expansion tokens and 65 ranking tokens, below the 256-token cap. No failure was a valid full permutation incorrectly rejected, and none was an output-token-limit truncation.

These are concrete model-output contract failures under the prospective unique-term/full-permutation requirements. The grammar constrains syntax but does not enforce uniqueness or permutation completeness; post-generation validation correctly enforces those requirements. The retained fallback products match the frozen policy. This finding does not prove all producer behavior bug-free or explain why the model omitted items. It authorizes no production retuning. Diagnostic causes are newly reconstructed evidence, not messages preserved in the original terminals.

## Physical accounting and frozen limits

| Phase | Generation / tokenizer calls | Measured input tokens | Measured output tokens | Reserved input tokens | Reserved output tokens |
|---|---:|---:|---:|---:|---:|
| Expansion | 199 / 199 | 50,944 | 8,873 | 228,215 | 50,944 |
| Ranking | 360 / 360 | 988,860 | 20,452 | 4,011,868 | 92,160 |
| Total | 559 / 559 | 1,039,804 | 29,325 | 4,240,083 | 143,104 |

These are shared **physical** calls, not sums of per-arm logical charges. Provider spending was **$0**. Collection accounting reconciled 1,881 attempts, 1,834 captures, 47 transport failures and 1,833 HTTP-200 responses: 224,404,917 measured body bytes; 322,971,061 safety-accounted bytes; 98,566,144 unknown-transfer upper-bound bytes; and 3,110,076,416 reserved bytes. Wire overhead remains unmeasured; retries were zero.

Frozen generation limits were 16,384 context tokens, 14,000 prompt bytes, 256 output tokens, seed 20261106 and temperature 0. Expansion/collection/ranking phase limits were 3,600/7,200/7,200 seconds; replay limits were 1,800 seconds each. Worker elapsed times were 172.266/6,871.235/1,068.500 seconds. Worker CPU times and peak working sets were respectively 11.984375 seconds / 46,592,000 bytes; 81.15625 seconds / 85,618,688 bytes; and 80.5 seconds / 110,518,272 bytes. These worker measurements exclude the model server and must not be presented as total machine costs.

Source policy retained the 2026-11-06 publication cutoff, CC BY/CC0 license filter, at most two queries, ten hits per query, three articles, 20 seconds per request and 120 seconds per collection case. Metadata/article/total byte caps were 1/2/8 MiB. Ranking pools admitted at most 16 passages, 1,000 bytes each and 10,000 bytes overall; downstream selection remained capped at eight passages / 8,000 bytes. The JSON anchor retains the exact frame configuration and resource records.

## Retained anchors

The companion [SC04-CLOSED-AUXILIARY-ANCHOR.json](SC04-CLOSED-AUXILIARY-ANCHOR.json) records full source, frame, package, stage, probe, report and code fingerprints, counts, caps and limitations. The source record is the question-only product; original article and transport records are transitively bound by the complete collection package.

| Artifact | SHA-256 |
|---|---|
| Expansion package — external anchor | `1f38157fff4d6b79fa463d799f0dd57852b94756560132481746c25d7412ea3c` |
| Collection package — bound through ranking | `68f942bfe744fadb5b3623fe829c28df1f78fdcac66faa7f85908578e653f883` |
| Ranking package — external anchor | `3fb27a9d6598fbef795ae9c577bf6668584b632a041e6b1480eb51d639b9fb55` |
| Execution frame | `bf2898bed1a1c2f0a6040dd116ec37223f514764217441e4b8cf84345e4801d0` |
| Question-only source queries | `667a7c2d89d481a4bf917b6392db033d3fc1e9ea1cfcb50d12712bc2d0556390` |
| Detailed probe report | `edf22b1f8ca186de5762c0a0a9b9ce2570d784889b490453e9a314a9e1538415` |
| Probe file manifest | `918c43582ffde5d88e8aecccc671db25e0666a47d9c9d7eecdddd6e15e27514a` |
| Separate codec diagnostic report | `93feb0127a58f0455eb6e7bbfc7ac2d6f4d476f4d44748a6b78b6e98a40dfdbe` |

Detailed records remain under `data/cache/sc04-closed-auxiliary-phase-probe-20261106T231531Z/`. The later diagnostic and its source/manifest remain separately under `data/cache/sc04-auxiliary-codec-diagnostics-20261106T233053Z/`; they do not modify the successful probe. Large model weights were not rehashed; model identities were checked against the sealed frame. Python-open audit records are not OS sandbox or hardware attestation, and inherited file descriptors remain opaque. No source-completeness, biological-support or scientific-performance claim follows from this engineering pass.
