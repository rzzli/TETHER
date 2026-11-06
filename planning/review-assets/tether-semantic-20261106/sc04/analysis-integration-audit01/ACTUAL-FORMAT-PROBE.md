# Selected real-source format probe

On 6 November 2026 at 21:58 UTC, a read-only probe selected **40 equally spaced
products from the 214 receipt-complete primary collection products then present**.
The selected ordinals and receipt hashes were fixed before reconstruction.

All **40/40** reconstructed successfully in **5.625 seconds**, including:

- 102 retained article occurrences (not necessarily distinct publications).
- 192 recorded HTTP attempts, including three retained transfer failures.
- Eight missing/invalid PMC-ID decisions, seven identity/rights/XML rejections,
  and three HTTP-unavailable decisions.

The check rebuilt queries, balanced candidate allocation, original HTTP receipts,
article eligibility/extraction, raw passage pools and transport accounting for
those selected products. It found no actual-format incompatibility in this
subset. All observed analysis source files were unchanged across the probe.

The primary run remains incomplete. These were locally captured receipt hashes,
**not a finalized externally anchored whole-run verification**. No outcome keys,
answer metrics or biological conclusions were evaluated; the subset does not
establish whole-cohort completion. No network/model call, live-output edit or
restart occurred.

Retained ignored artifact directory:
`data/cache/sc04-collection-format-probe-20261106T215806027Z/`

- `probe.py`: reproducible reader with a 285-second watchdog.
- `PLAN.json`: selection, input receipt/manifest hashes and reader source pins.
- `journal.jsonl`: each examined ordinal, question ID, receipt hash and result.
- `REPORT.json`: complete selected-format report.

Report SHA-256:
`b82446d08eb847f4f96c2db43a6e581524632aafe6effbe38c4e41c0ee5948ee`
