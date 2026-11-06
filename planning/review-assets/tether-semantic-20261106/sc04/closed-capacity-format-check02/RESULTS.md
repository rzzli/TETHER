# All 398 source products: format and prompt capacity

**All 398 individually closed primary collection products passed source-format reconstruction and answer-prompt byte checks.** This covers input feasibility only; phase/root acceptance, model-native reconstruction, answer scoring, and scientific interpretation remain separate gates.

The sealed first observation covered ordinals **0000–0387**. After the parent controller reported collection closure, a fresh supplemental check reconstructed only **0388–0397**. The combined report binds both external observation receipts. A final read-only check confirmed that all **398** individual MANIFEST and complete RECEIPT files still matched the captured hashes. The earlier 388 original XML/response bodies were not unnecessarily reparsed.

| Check | Result |
|---|---:|
| Source/format reconstructions | 398 / 398 |
| Complete individual markers rechecked | 398 / 398 |
| Lexical prompt overflows | 0 / 398 |
| Possible overflows over any permitted eight-passage selection/order | 0 / 398 |
| Largest lexical prompt | 10,008 bytes |
| Largest possible permitted prompt | 10,135 bytes |
| Frozen prompt limit | 14,000 bytes |
| Minimum headroom | 3,865 bytes |

The bound includes the system instruction, visible question/options, source identifiers, JSON escaping, and selected passage text. Because each raw chunk is at most 1,000 UTF-8 bytes, any eight satisfy the 8,000-byte text allowance. Choosing the eight largest independently escaped passage contributions achieves the maximum over permitted rankings; the total is independent of their order. This calculation neither predicts nor executes ranking or answer generation.

Original-source reconstruction checks inventories, captured HTTP receipts/accounting, metadata/XML identities and rights, balanced article allocation, source paragraphs, candidate pools and missingness. Observed lexical fallback plans in E are allowed and recorded; this check does not infer why expansion failed or substitute for parent/native verification.

Retained receipts:

| Observation | Output under `data/cache/` | Receipt SHA-256 |
|---|---|---|
| First 388 | `sc04-closed-capacity-format-attempt02` | `f0dc95d178b37a343433c9c0ad3b0426f10926926a74bed7ad2ff3e762b4583f` |
| Final 10 | `sc04-closed-capacity-supplement-attempt01` | `837ce18fab0e9fdcaf1ed9e5caea0c69f917c3cef5a582bb3c5adc7f71305532` |
| Combined 398 and marker check | `sc04-closed-capacity-combined-attempt01` | `9c008aa0e8a3fd55f207bf8cccb2f856e066e2ee0b9b2a623e4f660ffcc5a3c0` |

The combined summary SHA-256 is `726fc32f59c015ab784b521212786f6c2f500f579bf06f071a948e254c56a46d`. `REVIEW.json` retains these anchors, exact ordinal coverage, reader hashes, and the marker-check proof. Helpers are `../check_closed_capacity.py`, `../check_remaining_capacity.py`, and `../combine_closed_capacity.py`. Use an existing Python interpreter with `-I -B`, fresh output paths, and the explicitly retained prior/supplement receipt hashes.

This does **not** repair the frozen producer’s capacity-abort behavior, prove token-context feasibility, validate later supplied-source collections, establish answer quality, or constitute final whole-run acceptance. No model, retrieval, network, scoring, restart, source modification, or provider spending occurred. Previous failed/partial observations remain preserved.
