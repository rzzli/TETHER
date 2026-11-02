# Independent CE03 review

**Scoped pass; no new correctness finding.** The reviewed code moves the existing
receipt-time relationship into a shared pure helper and calls it for every raw
inventory entry in both preparation and replay. The full policy validator
requires raw receipt bindings and exact grant/inventory equality, so an unused
grant cannot evade this check by being outside an evidence packet's ancestry.
Generated nodes cannot claim transport receipt proofs. Receipt bytes, identities
and source URLs are checked before the added relationship check.

The original `InputGraph.verify` condition is unchanged in substance: a
`public_download_receipt` bound must exist, be no earlier than completion, name
the exact receipt hash, and agree on the source URL. Parsing keeps timezone-aware
comparison; the existing outer receipt parser additionally requires UTC. Earlier
availability supported by a separately declared historical basis retains its
existing rules. This preserves valid alternate-basis behavior without treating a
later retrieval as evidence of earlier availability. The declared basis and
provenance remain trusted metadata assumptions, not authenticated publisher truth.

The existing CE03 tests were read for before-dispatch and resealed-archive
coverage. Additional independently constructed peer controls used only the
unchanged generic fictional-frame builder, not the colleague's new extra-node or
resealing helpers. All **12 relationship cases** passed in the source-aligned
TETHER 0.5.1 / AsOf 0.3.12 environment:

- Used and unused inputs accept equal instants written as `Z` versus `+00:00`.
- Both reject a bound one microsecond before receipt completion.
- Both reject an incorrect evidence reference and a conflicting receipt URL.
- Both reject a timezone-naive completion timestamp.
- Both retain a valid separate historical basis despite later download time.

Accepted cases prepare and verify with four input proofs. Instrumentation sees
the extra node's outer relationship check during preparation, the preparation's
internal verification, and an additional verification call regardless of
reachability. Two valid instrumentation runs, with just the new outer helper
enabled versus disabled, make identical hash-call sequences: ten calls to the
outer hash function and six to the engine hash function. This is evidence of no
extra hash calls from this correction in the fixture, not a throughput benchmark
or universal performance proof. The disabled arm is explicitly a fictional
instrumentation control, not a valid old-version/scientific run.

[results.json](results.json) retains every outcome, call sequence, source paths,
source hashes and package versions; it is byte-identical to the original under
`data/cache/tether-ce03-peer-20261102-attempt01/results.json`.
[peer_controls.py](peer_controls.py) reproduces the controls into a fresh
caller-selected output directory. Runtime, package tests and source fixtures were
not edited. No backend, model, network, protected-data or benchmark execution took
place. The check covers the current shared-helper and all-input policy boundary;
it does not certify source-history truth or replace broader integration tests.
