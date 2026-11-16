# TETHER format contracts and second checker

This specification describes native receipt v2, journal envelopes and portable
bundle v1. It separates byte binding, execution consistency, source eligibility
and scientific validity. Passing one level never implies the next.

The second implementation, `tools/independent_verify.py`, is a standard-library
developer tool. It must not import TETHER, its renderer, admission logic or semantic
reducers. Independence here means a separate implementation against these rules,
not independent authorship, peer review or a second source of scientific truth.

From a checkout or source export, with a previously produced native run or bundle:

```sh
python -I -B tools/independent_verify.py runs/demo/engine
python -I -B tools/independent_verify.py runs/bundle --kind bundle --bytes-only
```

Supply `--anchor <saved-sha256>` when independently retained. Exit codes are 0 for
the explicitly requested supported check, 2 for rejection, and 3 for unavailable
assurance. The tool adds no runtime dependency and is not the production CLI.

## Canonical fingerprints

1. Decode UTF-8 JSON. A leading UTF-8 BOM is tolerated in input files. Reject
   duplicate keys, nonfinite numbers (including overflow such as `1e999`), invalid
   Unicode scalars and containers deeper than 128 levels.
2. Canonical logical bytes use Python 3.11 standard-library JSON serialization:
   `sort_keys=True`, `ensure_ascii=False`, `separators=(',', ':')`,
   `allow_nan=False`, encoded as UTF-8. No BOM or newline is added.
3. Integers and floats retain their parsed types: `1` differs from `1.0`, and
   `-0.0` differs from `0.0`. Strings are not Unicode-normalized. Unicode key
   ordering follows Python string ordering. This is **not RFC 8785/JCS**.
4. Logical fingerprints are lowercase SHA-256 over those canonical bytes. File
   hashes always cover the exact stored bytes, including whitespace/newlines.
5. Protocol counters require the Python/JSON integer token type; booleans and
   integral floats are not counters. A JSON Schema `integer` assertion alone
   cannot enforce this lexical distinction.

The [canonical vectors](../tests/fixtures/portable_bundle_canonical.json) publish
literal bytes and digests, including non-ASCII text, number types and large integers.
An external implementation must demonstrate agreement before claiming compatibility.

## Native receipt v2

[Receipt shape schema](../src/tether_engine/schemas/native-receipt-v2.json).

`receipt.json` is published last. Its existence prevents mutation by the owning
journal but is not a verification verdict. A partial directory without a valid
receipt is unfinished. Recovery must never automatically repeat a backend call.

The receipt declares `schema_version`, `software_version`, `admission_policy`,
`input_fingerprint`, `outputs`, `sources`, `admitted_fingerprints` and `code`.
Optional `auxiliary_outputs` binds `request.json` and/or `backend-execution.json`.
The current producer is engine `0.6.0.dev1` with `tether.derivation.v1`.
Producer version and policy must agree across receipt, run and configuration.

The required output set is exact:

```
run.json        inputs.json       ledger.json      features.json
prediction.json trace.jsonl      journal.jsonl    dossier.md
```

Each value in `outputs`/`auxiliary_outputs` is the exact file SHA-256. Filenames
outside these fixed inventories cannot authorize a read. `journal.jsonl` and
`trace.jsonl` must have identical bytes. `input_fingerprint` binds canonical
`inputs.json` and must equal `run.json.input_fingerprint`.

`inputs.json` contains case, snapshot, scorer (possibly null), effective catalog
policy, configuration, snapshot base and environment. `ledger.json` has schema
version 2 and ordered claims. Run identity, budget, plan, calls, usage partitions,
coverage and terminal status must agree with inputs and the journal. Code hashes
and dependency versions are producer declarations, not proof of exact-code replay.

Each source proof binds an artifact or lineage ID, dataset, release, path and hash.
Lineage proofs additionally bind role and parents; applicable download receipts
have their own path/hash. Full verification requires every eligible artifact and
its complete eligible ancestor closure, even when an admitted packet produces no
claim. Claims bind their admitted observation fingerprint and citation. Raw
provider bytes, receipt identity, temporal eligibility, mapping/annotation lineage
and registered computations are separate source-inclusive checks.

Native limits are 64 MiB for ordinary JSON and journals; ledger/dossier output
limits are 256 MiB. The second checker also imposes a 512 MiB aggregate read cap,
so it can abstain on a larger otherwise valid native run.

## Journal envelopes and ordering

[Envelope shape schema](../src/tether_engine/schemas/journal-envelope-v1.json).

Every JSONL record has `sequence`, `event`, `details`, `previous_sha256`, `sha256`.
Sequence starts at integer zero and increases by one. The first predecessor is
null; subsequent predecessors equal the immediately preceding record's digest.
The record hash covers the canonical object with only its own `sha256` removed.
Any envelope extension is also hashed; it does not acquire execution meaning.

Current producers write one canonical record and LF per line. Verification may
accept equivalent JSON whitespace and a complete last record without LF. A
recovery reader may discard an unterminated last line; sealed verification must
never use that recovery mode. A sealed run has one final `finalize` event with
matching status and canonical feature/prediction hashes. No event follows it.

| Stage | Required relationship |
|---|---|
| Optional preamble | At most one each of `run_reserved` and `inputs_archived`, before the plan. |
| Plan | Exactly one; binds snapshot, ordered specialist steps and configuration. |
| Retrieval, if used | Next attempt number; unique selected IDs; later accepted IDs are a subset. |
| Dispatch | Ready specialist, next attempt number, unique `category:attempt` ID, bounded reservation; earlier dispatch accounted. |
| Accounting | Exactly once for the active dispatch; either adapter-reported usage or its quoted upper bound. |
| Review | After accounting, once per attempt; identical usage; selected IDs and review problems retained. |
| Claim commit | Accepted review only; same specialist; exactly the selected prefix in order, without duplicates. |
| Retry | Rejected review only, within configured retries; no return to a completed/failed specialist. |
| Failure/budget event | Correct active attempt/disposition; terminal categories cannot dispatch again. |
| Finalize | Exactly one last event; all attempts accounted and accepted selections committed or explicitly interrupted by the commit deadline. |

Token totals are integer sums. USD accounting uses exact decimal sums of the
serialized numeric values, converted once for the reported numeric total. Measured
and estimated usage remain separate. Reservations are checked before dispatch;
actual overruns are retained, never retroactively relabeled as measurements.

`completed` requires every specialist completed, disabled, lacking observed
evidence, or having no records inside its retrieval budget. `partial` requires
failed specialists after complete traversal. `budget_exhausted`, `failed` and
`interrupted` require corresponding trace evidence. Unknown custom exception
inheritance cannot be proven from recorded class names alone.

## Portable bundle v1

The [bundle schema](../src/tether_engine/schemas/portable-bundle-v1.json) defines
the manifest and constituent contract shapes. `bundle.json` has exact top-level
fields: `format`, `admission_policy`, `source_tier`, `producer`, `objects`.
Format is `tether.portable_bundle.v1`; source tier is `included` or `receipts_only`.

The seven native output names other than `journal.jsonl` are required logical
objects. Additional names begin `packets/`, `lineage/` or `originals/`. Each maps to
`{sha256, bytes}`. Physical storage is `objects/sha256/<digest>`. Repeated digests
must declare the same size. Missing, corrupted or oversized objects fail byte
verification. Bounds: 1 MiB manifest, 256 objects, 64 MiB per object and 256 MiB
logical total, including aliases of the same physical object.

Names use relative slash-separated NFC components, at most 512 characters total
and 120 per component. Reject traversal, empty/dot components, control characters,
Windows reserved devices, alternate streams, forbidden filename characters,
trailing dots/spaces and casefold collisions. Raw metadata cannot provide physical
object paths. Linked/reparse/hardlinked bundle members are denied.
The reserved-device set includes CON/PRN/AUX/NUL/CONIN$/CONOUT$ and COM/LPT with
digits 0–9 or superscripts ¹²³, including extensions and space-padded stems.

Portable inputs remove environment and transport roots; their canonical digest
replaces the run's input fingerprint. Producer metadata preserves the original
receipt/input digests. Those producer digests are not independently supplied
anchors. `receipts_only` cannot pass source-inclusive replay. Unknown policies
can receive an explicitly requested byte-only check, never implicit semantic credit.

## Caller authority and assurance

The production verifier accepts the caller's run root, its fixed installed demo
root and explicitly supplied source roots. Roots selected by the caller can have
ancestor aliases; source descendants are checked without following links. Resolve
only caller-selected roots, never serialized source paths to discover permissions.
Windows short names do not enlarge a grant. Outputs-only checking opens no originals.

The second checker reads only the supplied static local run/bundle copy. It never
opens a serialized raw source path, imports archived code, invokes a model or uses
the network. Its filesystem threat boundary is a caller-owned stable directory;
it checks links and file identity but does not duplicate production's held-directory
Windows/POSIX race defenses. Use production verification for that boundary.

| Requested check | Second checker scope |
|---|---|
| Native bytes | Exact required/auxiliary output inventory and hashes; external receipt digest if supplied. |
| Bundle bytes | Manifest/object naming, sizes, hashes and external manifest digest if supplied. |
| Completed native consistency | Supported offline completed path: input/run identity, plan, serial dispatch/accounting/review/commit ordering, totals, selected claims, declared used lineage, final bindings. |
| Other native execution paths | Explicitly unavailable; byte validity alone does not fulfill a consistency request. |
| Bundle replay | Unavailable; the second checker never calls the production semantic replay engine. |
| Source, derivation, feature/scorer or dossier interpretation | Unavailable. Binding an output's hash is not recomputing its meaning. |
| Authenticity, historical publication or scientific truth | Not established. A caller digest can detect substitution of that anchored copy, not establish who made it or when its information existed. |

Known legacy native receipts (v1/engine0.1.0, v2/engine0.4.0, without the current
admission marker) require explicit legacy byte-only opt-in. Unknown producers
remain unsupported. Invalid or empty supplied anchors fail rather than disabling
anchoring. There is no signature/timestamp service in this milestone.

## Conformance and limitations

Public controls must include positive acceptance, exact rejection reasons and
explicit unavailable outcomes. Test canonical bytes separately from semantic
relationships: reseal tampered outputs when testing consistency so a hash mismatch
does not conceal a missing state check. Include deterministic generated variations
of event ordering, truncation, omitted parents, substituted source hashes, legacy
downgrades and forged completion. A reject-all checker must fail the positive
controls. Agreement on these vectors does not prove equivalence on all inputs.
