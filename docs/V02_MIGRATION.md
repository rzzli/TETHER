---
title: AsOf v0.2 Migration
date: 2026-10-11
updated: 2026-10-16
tags:
  - asof
  - contracts
  - migration
---

# Explicit migration from v1 to v2

## Normalization 2.1 to 2.2 within v2 contracts

The context revision changes the Open Targets projection and dossier presentation;
it does not change contract schema version 2 or the seven-field hypothesis fingerprint.
Build into a new directory from the same explicit files and content-addressed archived
receipts. Retain the original build, runs and reviews. Use a newly captured contemporary
cutoff and report it in the comparison; do not present the rebuild as a historical run.

Recipe 2.2 retains source passages/sections, PMC IDs, study descriptions and clinical
significance without importing current web annotations or evaluator clinical outcomes.
Canonical compact packet JSON changes byte hashes without dropping records. The packet
limit remains 64 MiB. Existing 2.1 runs can still be verified, and the source audit uses
the context requirements of their retained recipe.

Unresolved qualifications are null coverage metadata. They do not narrow the original
hypothesis or create a validated derivation scope. Before executing a future case with
specified subtype, biomarker or genotype, extend/version the contract and fingerprint
to bind those semantics; merely editing a case name or coverage text is insufficient.

## Original v1 migration

New execution accepts only v2 cases, snapshots and evidence packets. Preserve original
v1 artifacts and prepare a new conversion directory. Changing `schema_version` alone
is insufficient: v2 requires information that v1 did not retain. Missing lineage or
availability evidence remains a blocker.

Archived v1 runs still support `asof verify`, with byte integrity and
`semantic_consistency: unavailable_legacy_v1`. Conversion cannot retroactively add v2
guarantees to a completed run. Original fictional fixtures remain in `src/asof/demo/`;
new fixtures live in `src/asof/demo/v2/`. `tools/framework/build_demo_v2.py --output <fresh-directory>` regenerates
only fictional v2 fixtures and is not a scientific-data conversion tool.

## Cases and exact cutoffs

1. Set case `schema_version: 2` and provide timezone-aware `origin_at`. Its UTC date
   must equal `origin`; use the intended cutoff rather than inventing a convenient time.
2. Preserve target/indication IDs, both namespace versions, intended action, modality and
   nullable tissue. Review mapping/annotation availability.
3. Validate any supplied program's availability for both T1 and T6. T1 still requires
   active Phase 1/2 eligibility and a matching next-phase endpoint; these endpoint
   requirements do not apply to a program-free T6 dossier.

`Hypothesis.key` computes scope from canonical identity/context. Do not reproduce it
with arbitrary JSON formatting or omit tissue, action, modality or namespace versions.

## Source graph and packets

Set snapshot and packet `schema_version: 2`. Match both snapshot origin fields to the
case. Add source nodes, raw-data root, coverage and complete references:

| V2 field | Required evidence or behavior |
| --- | --- |
| Source identity | Source ID, dataset/release, original path, exact SHA-256 and URL |
| Role | Effective catalog role; normalization inputs retain reference roles |
| Availability | Eligible information dates or verified contemporary public-download bound |
| `parents` | Every data, mapping and annotation dependency of a derived source |
| Source computation | `computed_at`, `method_id`, `method_version` for derived source nodes |
| Receipt binding | `receipt_path`, `receipt_sha256` for real originals, using archived bytes |
| Artifact `input_refs` | Complete packet ancestors |
| Observation `input_refs` | Complete observation inputs, within packet lineage |
| Observation `computed_at` | Required when `source_kind` is `computed` |
| `source_locator` | Original source/row identity when available |
| `source_metrics`, `missingness` | Descriptive values and explicit unknown-field reasons |

A verified contemporary receipt can establish `known_public_by`, with `evidence_ref`
bound to its SHA-256. This does not establish historical availability. Retain publication
dates separately and reject future information. Newly calculated results may use older
eligible data; `computed_at` does not replace lineage eligibility. Missing parents,
cycles and evaluator-only ancestors fail. Do not relabel outcome or gold products.

Use `asof_normalized_packets` only for generated products with complete catalog-resolved
parents. Seal newly written packet bytes with exact hashes. Each normalized JSON file
must fit the 64 MiB limit; oversized packets fail explicitly.

Generated ledger envelopes have a separate 256 MiB output limit. Verification and source
review use a bounded ledger reader; the 64 MiB normalized-input limit remains unchanged.

## Numerical features and scorers

Retain a feature only after its versioned derivation has been reviewed for the hypothesis.
Set `feature_scope` to the hypothesis key. Changed action/modality/tissue requires a
compatible derivation. Raw observations can remain visible while inapplicable features
are withheld from requests and aggregation.

Real contemporary Open Targets packets use empty `features`, null `feature_scope` and
descriptive provider metrics. Do not map association scores into support weights or
effect sizes. Unknown quantitative scales/context stay null with reasons. T6 clinical
probabilities remain null.

Scorers require schema version 2, `asof-features-v2` and
`mean_of_unique_dependency_groups_v2`, plus frozen applicability, imputation, coverage
and training/calibration declarations. Do not mechanically upgrade real trained weights:
revalidate changed feature semantics and their training manifest. Invalid schema/profile/
cutoffs fail before dispatch; valid inapplicable models abstain. The supplied scorer
remains a synthetic fixture.

## Backends, replay and durable outputs

`Backend.quote()` and `Backend.select()` remain unchanged. Quote a reliable upper usage
bound and return validated selections/usage. Nested records and results are immutable;
prepare a new reviewed value instead of mutating an admitted one. Ledger admission binds
the original canonical fingerprint.

Replay schema 2 binds each selection to its exact request fingerprint. Re-record against
actual v2 requests; editing only the schema version does not convert a v1 selection.
Case, context, packet or feedback changes require a new binding.

Use a fresh output directory. CLI execution reserves it before validation/dispatch,
archives the request/configuration, and journals attempts and accounting as they occur.
Measured usage and conservative estimates are separate. `inspect-run` reads incomplete
runs/builds and never repeats a potentially billed call.

V2 receipts retain eight required output hashes and complete artifact/ancestor proofs.
CLI `request.json`, when present, is bound via optional `auxiliary_outputs`; valid earlier
v2 receipts without that optional field remain verifiable. Save the receipt hash
independently. Source-inclusive verification binds current originals; `--outputs-only`
explicitly supplies the weaker archived-fingerprint check.

## Validate the converted inputs

October 18 authored case packs are optional configuration, not replacements for v2
case/snapshot/evidence contracts. `build-snapshot --cases pack.json
--cases-sha256 <sha256>` (one shell line) seals the selected schema-version-1 pack
alongside newly generated v2 cases. Old fixtures, the original default case pack,
normalization recipe 2.2 and existing receipts are preserved. Approved HGNC symbols
and supplied Ensembl/HGNC IDs must match the selected source records. Evaluator
answers and reference annotations are not eligible case-pack evidence.

October 17 ingestion extension: `build-snapshot --packet-layout bounded` can
write multiple packets under the existing v2 artifact-list contract. This is
opt-in and retains every complete observation; all packets remain within 64 MiB.
No conversion of old fixtures or snapshots is needed. New consumers should read
the listed artifact paths and hashes. In build reports, `packets[]` enumerates
them, `packet_bytes` totals them and `packet_sha256` is null for multiple packets.
The default single-packet mode and finite runtime/output budgets are unchanged.

```powershell
uv sync --python 3.11
uv run --no-sync asof run --case converted/case.json --snapshot converted/snapshot.json `
  --catalog data/catalog/sources.json --output runs/converted-v02-new
uv run --no-sync asof verify --run-dir runs/converted-v02-new
uv run --no-sync asof inspect-run --run-dir runs/converted-v02-new
```

For supported provider ingestion, install `uv sync --python 3.11 --extra ingest` and
continue with `uv run --no-sync asof inspect-source --manifest path/to/manifest.json
--catalog data/catalog/sources.json --report path/to/new-inspection.json` (one shell line).

Mechanical verification establishes retained-input and contract consistency. It does
not independently validate biological interpretation, feature design, training data,
clinical calibration or historical claims. See [[FRAMEWORK]] for current boundaries.
