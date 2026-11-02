# TETHER — Binding claim audits to native v2 dossiers

TETHER (Target Evidence Tracking Harness for Evaluation and Reproducibility) is the current project name. The `tether-target-agents` 0.4.2 package in `packages/tether` supplies the `tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. See [installation and compatibility](../README.md#installation-and-compatibility). Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches. Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.

`tools.science.t6_dossier_binding` adds an evaluator-only integration for existing
native AsOf v2 T6 dossiers normalized from Open Targets 25.09. It reuses the
existing original-row verifier instead of accepting a JSON extract as a Parquet
original. The standalone JSON audit API remains unchanged.

## Entry points

- `build_binding(receipt_proof, output, approved_roots=...)` reserves a new output,
  verifies the externally supplied receipt hash and replays the complete v2 run
  semantics and eligible source closure. It then audits every selected original
  row, mapping, archived download receipt, scientific context and lineage. Failures
  and interruptions leave a readable hash-chained journal. Existing output is
  neither resumed nor overwritten; output must be outside the sealed run folder.
- `verify_binding(binding_proof, approved_roots=...)` recomputes the binding from
  the actual run and original sources. An unchanged binding file or a declared
  success flag does not substitute for that replay.
- `bind_manifest(manifest, binding)` checks a supplied atomic inventory against
  exact dossier bytes. This text-checking helper alone does not establish source
  validity; use the source-inclusive entry point below for an audit report.
- `audit_bound_claims(manifest, review, binding_proof, approved_roots=...)` replays
  the binding, checks the claim spans, and applies the existing review contract
  directly to verified Parquet row projections. No converted JSON-original proxy
  is introduced.

The optional ingestion extra must supply `pyarrow==21.0.0`. The default runtime
and its `Backend.quote()`/`Backend.select()` interfaces are unchanged. This module
has no model client, network fetch, feature derivation or clinical scorer.

## What the binding proves

The caller must supply a receipt pin from its retained parent artifact, not claim
an independently trusted timestamp from a newly calculated local digest. Every
run, normalized packet, raw input and archived receipt path must fall beneath
explicit approved roots before original-source verification begins. The module
accepts native schema v2 only; it does not upgrade v1 semantic guarantees.

The current adapter requires T6 and withheld real-data probabilities/features.
It reconstructs canonical target/disease/HGNC mappings and uses
`reference_packets.audit_observation` for complete normalized-observation checks:
physical row group and offset, source identity/hash, full approved projection,
preserved context, publication eligibility, missingness and input lineage.
Excluded clinical fields and ChEMBL evidence remain excluded. Original rows are
not turned into new causal effects, independent studies or numerical features.

Each selected ledger statement must occur in a unique native dossier section,
with its exact rendered quote, one matching citation line and matching artifact
digest. A one-pass section index avoids repeated whole-dossier header scans.
Source receipts, mappings and sealed outputs are rechecked after original-row
work. The binding retains all selected source units, their physical originals and
the exact dossier/receipt hashes. A binding over 64 MiB fails without dropping rows.

This establishes local artifact and source correspondence. Scientific entailment,
external publisher authenticity beyond the retained acquisition evidence, trusted
public timestamps and therapeutic relevance require their own qualification.

## Atomic inventory integration

The existing claim manifest gains `dossier_binding_sha256`, equal to the canonical
fingerprint of `binding.json`. Its dossier digest and all seven hypothesis fields
must match the binding. Each claim gains `dossier_spans`, currently exactly one
`{start, end}` half-open UTF-8 byte interval. The exact decoded bytes must equal
the inventoried statement. Splitting UTF-8 characters, splicing separate passages,
overlapping intervals within a claim and invented text fail explicitly.

Actual source IDs are the selected observation IDs. The inventory's citations must
equal the native citations in the claim's containing section. It cannot invent a
selected citation in a different section, omit a citation that is actually present,
or cite an unselected observation. An uncited statement outside source sections
can remain in the inventory and be evaluated as uncited; it is not silently removed.

For `audit_bound_claims`, the review's `sources_sha256` binds this ordered inventory:

```python
sources = [
    {"source_id": unit["observation_id"],
     "format": "verified_opentargets_parquet",
     "source_audit": unit["source_audit"]}
    for unit in binding["source_units"]
]
```

Evidence and context ratings still come from reviewers. Binding does not infer an
entailment answer. In particular, a source annotation may be reproduced correctly
while providing insufficient evidence for the proposed intervention.

## Explicit remaining limits

The binding is a **source-unit draft**, not a claim that the dossier has been
completely or atomically inventoried. A source paragraph can contain several
assertions. Metadata, coverage statements, interpretation and unsupported prose
also need an exhaustive extraction/disposition protocol. The current validator
checks supplied claims, not NLP completeness. No source-only success count closes
the original full T6/H5 objective.

The adapter supports the native v2 formatter and the current Open Targets
normalization recipe. Comparison-arm ID-only result files, interpreted dossiers
under a future renderer, non-Open-Targets sources and PDF papers need separately
qualified bindings. Whole-dossier completeness references, blinded independent
reviews and their seals, an interpretation layer and a fresh paired study remain
next gates. Existing development runs are exposed and cannot become a fresh test.

## Real development check

The retained October 16 IL6R/antibody dossier was chosen for a finite nine-row
adapter replay, not a scientific performance sample. The October 24 build passed
and a separate complete replay passed: nine selected rows, eleven selected input
files, and a 121,550-byte binding. The first build took 12.344 seconds; this is not
the total time for the subsequent independent replay. No new model run, clinical
label, atomic inventory or scientific judgment was created.

Request and results are retained under the ignored evaluator-only tree
`data/benchmark/labels/t6-dossier-binding-20261024/`; tracked acceptance and backup
receipts live under `planning/review-assets/t6-dossier-binding-20261024/` when
final validation and checkpointing complete.
