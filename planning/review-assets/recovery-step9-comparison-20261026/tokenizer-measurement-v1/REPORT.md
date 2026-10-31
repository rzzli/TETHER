# Offline tokenizer measurement: actual token counts fit; runtime admission remains unchanged

The unchanged real IL6R six-stage prompt set contains **28,049 pinned CLI tokens**, or **28,241 with 32 additional reservation units per stage**. This is below 32,000. Its 85,173 UTF-8-byte reservations are a deliberately conservative proxy, not evidence that the actual tokenized request exceeds 32,000. This measurement corrects that feasibility interpretation without changing either the accepted byte-based runtime policy or the prior reports.

## Execution and identity

The prospective MEASUREMENT-PLAN-v2 was retained before any model/tokenizer prompt execution. V1 is preserved: its synthetic fixture names were transposed when assigning the six provided expected numbers; the retained numeric R07 audit corrected that mapping before execution. Exactly 24 CLI processes ran (18 fixed literal stage prompts and six original R07 controls), with no variants, retries, prompt alterations, server, generation, network or paid provider call. Each used a 30-second timeout, exact binary UTF-8 stdin and the dedicated `llama-tokenize.exe` with `--offline --no-escape --no-bos --stdin --ids --show-count`; parse-special used its documented enabled default. Token-ID list length equaled the independently printed count for every call.

All 34 selected R05 asset pins—tokenizer executable, all runtime DLLs, and all three GGUF shards—were freshly rehashed: 9,078,912,160 bytes in 6.906 seconds. Every hash/size matched. The runtime DLL inventory was also checked for extra unpinned DLL files. Raw stdout/stderr and exact prompt bytes are retained under ignored `data/cache/r09-tokenizer-measurement-v1/`; prompt/payload/stdout/stderr hashes and elapsed times are in RESULT.json. The terminal seal and each original control payload were checked. All 12 synthetic payload files match their retained preparation pins and exact authenticated original fixture requests; all six real reconstructed payload hashes match the retained literal-design measurement.

## Results

| Input | Six-stage CLI tokens | CLI tokens + 32 each | Existing byte reservations | Output reservation |
|---|---:|---:|---:|---:|
| exposed-il6r | 28,049 | 28,241 | 85,173 | 6,144 |
| synthetic-context | 8,987 | 9,179 | 31,715 | 6,144 |
| synthetic-orientation | 8,093 | 8,285 | 28,503 | 6,144 |

Real stage counts range from 4,650 to 4,706 tokens; their UTF-8 prompt lengths remain 14,054–14,298 bytes. Tokenized context plus the fixed 1,024 output allocation is below the 16,384 context ceiling per stage. The current 6,368 **byte** prompt bound still fails; it is not silently reinterpreted as a token bound.

| R07 empirical control | Retained native input tokens | CLI tokens | Exact parity |
|---|---:|---:|---|
| exposed-il6r-genetics-current | 4377 | 4377 | Yes |
| exposed-il6r-genetics-simplified | 4507 | 4507 | Yes |
| synthetic-orientation-current | 1241 | 1241 | Yes |
| synthetic-orientation-simplified | 1371 | 1371 | Yes |
| synthetic-context-current | 1397 | 1397 | Yes |
| synthetic-context-simplified | 1527 | 1527 | Yes |

The exact six-control parity supports this utility/model/settings combination for these existing prompts. It is not a universal proof of every server preprocessing route or future tokenizer version. Counts here remain **CLI tokenization measurements**, separate from the previously observed native generation usage. No candidate answer content was read. The sealed startup metadata reports add_bos_token=false; explicit no-BOS and enabled special-token parsing empirically reproduce all six controls. No missing BOS, escaping or stdin discrepancy was observed.

## What this changes—and the remaining gate

There is a concrete engineering path to investigate: a prospectively specified, pinned tokenizer-aware reservation contract could retain the full source request and unchanged 32,000 aggregate token ceiling. Source clipping, a new lossless representation, stage deletion or a larger budget are not demonstrated necessary by this input. This is still only one already-exposed real request and two invented fixtures, not broad real-source scalability or scientific acceptance.

No production token-accounting policy, per-stage byte cap, runtime resource inventory, source allowlist, native stop, or comparison schema was changed. The existing guide still says three claims while the real request/schema allow two; that needs explicit alignment. Before real admission, a narrowly scoped contract proposal must specify trusted tokenization/asset identity, exact byte-to-token binding, preprocessing/BOS/special behavior, count caching and mutation rejection, failure/timeout behavior, accounting provenance, and how the explicit byte-size safeguard coexists with model-token/context limits. A source-inclusive admission path and relevant scientific/source review remain separate requirements. Empirical token fit is not authorization for inference and does not reproduce original Virtual Biotech retrieval or establish answer quality.

## Retained evidence

- MEASUREMENT-PLAN.json and superseding MEASUREMENT-PLAN-v2.json, both preserved.
- ASSET-CHECK.json: fresh hash inventory and measurement.
- RESULT.json: all 24 exact counts, payload hashes, controls and totals. SHA256 `aefbaf540d3ff9dc6921ac1a01b0ca1c77500e3934ba76f0520ceaa8da4bd7f8`.
- SOURCE-PIN-CHECK.json: retained synthetic file pins and authenticated request equality.
- run_measurement.py: bounded offline-only helper.

Actual generation calls: **0**. Provider spending: **$0**. Scientific validation: **not performed**.
