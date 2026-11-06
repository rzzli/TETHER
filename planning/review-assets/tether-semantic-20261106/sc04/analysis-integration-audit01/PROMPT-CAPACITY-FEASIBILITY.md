# Current-pool answer capacity feasibility

A second read-only probe at **21:59 UTC, 6 November 2026** examined all **219
receipt-complete collection products** present at selection. It used the frozen
visible questions/options and common answer prompt, never reference keys or
model outputs.

| Check | Result |
|---|---:|
| Lexical selections exceeding 14,000 prompt bytes | 0 / 219 |
| Pools with any possible eight-passage ranking selection exceeding that limit | 0 / 219 |
| Largest lexical prompt | 10,008 bytes |
| Largest possible ranking-selection prompt | 10,135 bytes |

The upper bound includes source IDs, JSON escaping, question/options and system
instructions. Every pool chunk is at most 1,000 UTF-8 bytes, so any eight chunks
fit the 8,000-byte raw-text allowance. Selecting the eight largest independently
escaped passage contributions therefore bounds every rank permutation for that
captured pool. This predicts neither the ranker's order nor its answer.

These results reduce the immediate capacity concern for the examined inputs but
**do not resolve the frozen producer's end-to-end capacity-handling limitation**.
Incomplete/unseen collection products can differ. This is a feasibility subset,
not whole-run verification or scientific evaluation. No live input was changed,
and no network/model call or restart occurred.

Retained ignored artifacts:
`data/cache/sc04-prompt-capacity-probe-20261106T215946488Z/`

The directory contains the reproducer, prospectively selected receipt hashes,
reader source pins, per-collection journal and final report. Report SHA-256:
`2fbf5b567235e41010cfa1ef01288a7ba08724b87e9ed2ceba0695b6af2aace2`.
