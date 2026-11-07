# Data workspace

The repository tracks source metadata and policy configuration, not datasets,
model weights, cached downloads or generated benchmark records. Each data source
retains its own access and reuse terms.

The catalog is a blank deployment requirements template. No product is marked
collected, parsed or scientifically validated. Historical acquisition records
remain separate; their originals are not rewritten by this template.

| Path | Purpose |
|---|---|
| [catalog/sources.json](catalog/sources.json) | Provider and product inventory: required fields, releases, roles and access metadata |
| [catalog/policy-v2.json](catalog/policy-v2.json) | Exact catalog binding and explicit artifact/use permissions |
| `raw/` | Unmodified originals, organized by dataset and release |
| `reference/` | Versioned mappings, annotations and reference material |
| `manifests/` | Explicit input manifests and provenance records |
| `derived/` | Newly computed, source-bound products |
| `benchmark/` | Evaluator-only cohorts, labels, splits and evidence references |
| `cache/` | Disposable local download, build and computation caches |

Use `raw/{dataset_id}/{release_id}/` for originals and
`derived/{snapshot_id}/{product_id}/` for new products. Large inputs may live under
an explicitly approved external root. Bind those paths in local manifests rather
than changing original receipts or committing machine-specific root maps.
Create these ignored working directories locally when needed.

## Preparing inputs

With the optional ingestion extra installed, the CLI can validate a manifest and
build normalized packets from approved local Open Targets/HGNC files:

```text
tether inspect-source --manifest <inputs.json> --catalog <local-catalog.json> --report <fresh-report.json>
tether build-snapshot --manifest <inputs.json> --catalog <local-catalog.json> --cases <cases.json> --output <fresh-directory>
```

Create a local deployment catalog from the public template using the
[maintenance guide](../docs/MAINTENANCE.md#catalog-updates). Keep acquisition
observations and a separately bound local artifact policy in ignored paths;
do not write deployment results back into the public requirements template.

Inspection checks receipts, paths, hashes and required schemas. Snapshot building
preserves lineage, original row locators and explicit coverage. Neither HTTP
success nor parsing establishes historical eligibility or scientific validity.
Individual packets are capped at 64 MiB; use `--packet-layout bounded` explicitly
when multiple complete packets per case are intended.

## Admission and isolation

The shipped catalog policy has no artifact grants or permitted uses. Register exact
sources, parents and intended use before policy-backed execution; see
[the catalog guide](catalog/README.md) and [policy interface](../docs/TETHER-CATALOG-POLICY.md).

Collection, parsing, availability and scientific validation are separate states.
Unknown context stays unknown, and incomplete collection cannot establish absence
of evidence. Evaluator-only labels and their descendants cannot become agent
inputs. Folder placement alone does not enforce that boundary.

Keep credentials, signed links, private paths, raw payloads and generated records
out of version control. Preserve immutable receipt copies whenever a receipt is
used as a source anchor. Use a new output path for every attempt.
