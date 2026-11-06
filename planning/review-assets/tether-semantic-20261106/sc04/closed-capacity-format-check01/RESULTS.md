# Closed-product capacity and source-format check

**388 of 398 scheduled collection products passed the extended check.** This is an explicitly partial observation of the ongoing primary run, not final execution acceptance or a scientific benchmark result.

The bounded read-only check examined ordinals **0000–0387** in 84.375 seconds on November 6, 2026 UTC. Its first scan selected 385 receipt-complete products; an immediate second scan added three newly closed products. The final scan found no additional closed products. Ordinals **0388–0397 remain unexamined** in this retained observation.

| Check | Result |
|---|---:|
| Complete original-source/format reconstructions | 388 / 388 |
| Lexical selections exceeding the 14,000-byte prompt limit | 0 / 388 |
| Pools with any permitted eight-passage ordering exceeding the limit | 0 / 388 |
| Largest lexical answer prompt | 10,008 bytes |
| Largest possible answer prompt for any permitted selection/order | 10,135 bytes |
| Minimum observed prompt headroom | 3,865 bytes |
| Scheduled expanded-branch products with a lexical plan | 6 |

The independent source reader checked exact collection inventories, transport receipts and accounting, metadata and XML rights/identities, query-balanced allocation, original paragraphs, raw candidate pools, and coverage. Each product was read only after its MANIFEST and complete RECEIPT were present. Receipt and manifest hashes were captured before reconstruction and checked again afterward and before finalization. Reader-source hashes remained unchanged.

Prompt sizing used the pinned visible questions and choices plus the frozen common answer instruction. It did not read answer keys or generated answers. Every candidate chunk is at most 1,000 UTF-8 bytes, so every permitted eight-item selection meets the 8,000-byte text allowance. Escaped JSON item contributions are additive and invariant to order. Selecting the eight largest contributions therefore achieves the maximum over all permitted selections/orderings, including source IDs, escaped text, fixed formatting, question, choices and instructions. Product **0108** produced both maxima. No ranking was predicted or executed.

Controls checked all 65 empty/subset/permutation renders of a four-item invented pool containing Unicode and JSON-sensitive characters, an empty pool, selection of the largest eight contributions from sixteen items, and permitted lexical fallback in an expanded branch. The first probe stopped on its own overly strict branch assumption at product0089; that failed probe and its helper remain preserved. The frozen producer explicitly permits this fallback. Its six observed lexical plans are recorded without claiming to verify the enclosing expansion-native status or reason.

The final report, exact examined ordinals, per-product receipt hashes, maximizing passage IDs, prospective selection records, hash-chained journal, controls and inventory receipt are retained in:

`data/cache/sc04-closed-capacity-format-attempt02/`

- Report SHA-256: `78e19a09a7a59718f38d3b04bbfe828a49800bd4b88d5d5909eb52df577f12ce`
- Receipt SHA-256: `f0dc95d178b37a343433c9c0ad3b0426f10926926a74bed7ad2ff3e762b4583f`
- Tracked summary: `SUMMARY.json` in this directory.
- Reproducer: `../check_closed_capacity.py`; invoke with the existing Python interpreter using `-I -B` and `--output <fresh-directory>`.

The known producer capacity-abort limitation is unchanged. These observations reduce the input-capacity concern for the examined products; they do not prove graceful capacity recovery, token-context feasibility, correctness of answers, scientific entailment, future supplied-source capacity, or validity of incomplete/unexamined products. Final enclosing phase/root verification remains required. No inference, scoring, retrieval, restart, provider spending, or frozen-source edits occurred.
