# Role-aware producer: F1 storage closure (design v2)

The [v2 proposal](ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v2.json) preserves [v1](ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v1.json) and its single-finding peer HOLD. It changes only phase lifetime, real byte consumption and storage accounting. No implementation or runtime authority is added.

Original captured inputs keep a separate 32 MiB total / 8 MiB per-file pool. Generated evidence has its own closed 40,139,776-byte store. Candidate and terminal ledgers are distinct immutable snapshots, additional to live canonical tables. Source-bound checkers receive and parse the actual same-owner stored bytes; an iterator, digest, reported count or ready flag cannot stand in for byte evidence.

| Generated artifact | Maximum bytes |
| --- | ---: |
| candidate-ledger.bin | 14,800,384 |
| terminal-ledger.bin | 14,800,384 |
| journal.jsonl | 2,293,760 |
| producer-report.json | 8,192 |
| candidate.json / cleanup.json / failure.json / receipt.json / seal.json | 8,192 each |
| child/result.partial.jsonl | 7,995,392 |
| child/attempt.json | 4,096 |
| child/failure.json | 65,536 |
| stdout.bin / stderr.bin | 65,536 each |

The child structured subtotal is 8,065,024 bytes. The extra 131,072 bytes are only stdout and stderr. Membership remains conditional: reservation never means that an artifact exists or completed successfully.

One generated-artifact assembly is bounded by the largest ledger, 14,800,384 bytes. The immutable result occupies its store slot while that assembly may still be live. A failed freeze discards/unissues the partial snapshot; it cannot yield a checker capability. Unknown release quarantines the single assembly and prevents another build. Known raw facts, original exceptions and close rights survive. Healthy snapshots do not alias live tables or each other, and later closes cannot mutate candidate bytes.

The revised named payload reservation is 113,985,546 bytes, including a potentially retained 8 MiB failed-input assembly, the entire generated store, one generated assembly, a 1 MiB hash/slice transient and 128 KiB one-at-a-time path comparison workspace. The healthy output phase after original assembly release is 105,596,938 bytes; admission reserves the larger bound. Journal/packets/report are counted once in the generated store. Original paths live once in the UTF-8 pool; final paths remain in their complete raw query frames rather than an additional retained decoded string pool.

These are encoded/named payload bounds, not measured Python heap or RSS. Exact enum/offset fixtures, complete future roster and consumers, physical write/flush/close/readback reservations, real first-entry/FFI and actual 256 MiB/clock qualification remain open. The old N4 profile, 48-history oracle, 64 KiB calculator and all scientific ceilings remain unchanged. No source, fixtures, originals or runtime were executed or modified for this amendment.
