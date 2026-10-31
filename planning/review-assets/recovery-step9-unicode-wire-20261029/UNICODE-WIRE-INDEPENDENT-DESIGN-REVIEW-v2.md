# Corrected Unicode wire design review

**Clear for the next literal framing specification and fixture stage only.**
Proposal`ddf9fd36…`/semantic`9a313df2…` resolves the v1 design findings. Footer
JSONL rows each retain their8,192-byte cap; the64KiB failure marker is separate.
Geometry QC/full ledgers remain independent of native token/EOG outcomes. The
fixed sizing envelope is6,408bytes and API-name unions use actual JSON null.

The setup schedule has15 occurrences using11 closed body families, each with a
full25-entry cumulative vector. Its exact17default/17effective parameters and
31layout leaves are present. Native-call zeros, CPU/backend/model transitions
and the vocabulary-dependent EOG count are explicit. Per-case piece calls are
`N + count(length>1)`: zero/one-byte pieces each require one call. Later grammar
rejection does not discard or reduce the precomputed full token/piece ledger.

Four setup rows contain module inventories, plus the batch footer. These are
nested arrays, not an allocation of64extra rows per phase. A whole row exceeding
8,192bytes must fail. No universal fit, split-row shortcut or additional setup
allocation is established. A complete sequence has`188+U<=192`rows, within the
unchanged276-row reservation.

Before implementation, the next framing contract/fixtures must make status/reason
enums and harness observation shape explicit, bind their normative fingerprints,
and test row/aggregate boundaries, zero-piece retries, source counter deltas,
write acknowledgments, partial/unknown outcomes and failure vetoes. Literal pack
fragments are sufficient for this next step; no full pack builder is needed.

This is design and arithmetic review. It authorizes no bridge, parser, pack,
parent, OS/native/model/SDK/compiler or runtime operation and establishes no time,
memory, profile or scientific result. The v1 review and original negative
experiment and external timeout remain preserved.
