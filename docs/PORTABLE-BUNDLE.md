# Portable offline evidence runs

A TETHER bundle carries one sealed offline run with normalized evidence, its eligible lineage and the policy used to admit it. Verification works from a copied directory with the original run and data directories unavailable. Version 1 supports fictional cases and unscored contemporary T6 cases without clinical program context. It accepts v2 native runs sealed with the safe dossier format. Historical, local-model and replay runs retain their existing verification routes. [Archive verification](ARCHIVE.md)

## Try the fictional example

Use Python 3.11 or newer from a checkout or source archive. The engine and the portable gate use the standard library. The examples below use PowerShell and fresh directories outside the demo inputs.

```powershell
$env:PYTHONPATH = 'src'
python -m tether_engine demo --output demo-native
python -m tether_engine bundle-export --run-dir demo-native --source-root src/tether_engine/demo/v2 --output demo-bundle
python -m tether_engine bundle-inspect --bundle-dir demo-bundle
python -m tether_engine bundle-verify --bundle-dir demo-bundle
```

`tether` exposes the same bundle commands. A run created through `tether demo` keeps its native artifacts in the `engine/` subdirectory. `--source-root` may be repeated for a run with a separate raw-data root. `--receipt-sha256` checks the original receipt against an independently retained digest at export. Omitting `--output` uses a fresh UTC-named folder. `bundle-inspect` reads only the manifest. `bundle-verify --manifest-sha256 <saved-digest>` checks a previously retained bundle digest. Save it through a channel independent of the copy if substitution matters.

Use `--omit-originals` when originals cannot travel. That tier carries the exact eligible packets and applicable download receipts and checks their declared identities. Source-inclusive replay requires the original bytes. The exporter copies the eligible closure only, but source records and free-text fields can contain sensitive content. Check publication rights and inspect all payloads before sharing. The exporter removes the defined absolute transport roots and omits the path-bound native receipt, inputs and request bytes. It does not anonymize arbitrary source text, URLs or raw provider data.

## Format and checks

The directory holds `bundle.json` and immutable objects in `objects/sha256/<sha256>`. Each manifest key identifies a logical object with a SHA-256 and byte length. Fixed run names identify the portable inputs, run record, ledger, features, prediction, trace and dossier. `packets/`, `lineage/` and `originals/` distinguish eligible normalized packets or computed nodes, receipt witnesses and raw parents. Native raw relative paths are preserved for receipt reconciliation. The snapshot roots are replaced with verifier-owned temporary directories populated only from verified bundle objects. No network or backend call is needed.

The manifest is written last, after preflight verifies the exported closure. Fresh output reservation prevents overwrites. A failed export can leave an incomplete directory. Inspect it or start a new export in a fresh directory. Use a trusted, stable local parent for output and verification staging. Bundle reads reject symlink, junction, reparse-point and hardlink members and consume bounded bytes from held file descriptors. On POSIX, traversal uses no-follow directory descriptors. On Windows, traversal opens reparse points without following them and holds parent and read handles. These controls assume a local filesystem and trusted OS, and the exporter does not coordinate concurrent changes to the chosen output parent.

| Check | What it establishes |
|---|---|
| Byte integrity | Every declared object matches its SHA-256 and length. `--bytes-only` makes this independent of replay. |
| Source-inclusive consistency | With original bytes and a supported policy, re-admits inputs and checks exclusions, coverage, claims, accounting, trace, features, predictions and deterministic prose. |
| Supported derivation replay | Checks built-in registered transforms if present. Unknown policies or methods are reported as unavailable. A provider's Parquet normalization is outside the registered JSON derivation registry. |
| Exact producer replay | Not performed by the bundle verifier. Code hashes, runtime versions and the native receipt digest are producer metadata. Use the sealed native run and its original environment for exact-producer checks. |
| External anchor and authenticity | A supplied digest can match the manifest. Producer identity, source truth and publication time require evidence outside the bundle. |
| Scientific validation | Not established by any bundle check. |

Known-policy replay rejects malformed or inconsistent results. It does not require byte-identical current Python code. For untrusted bundles, the optional anchor is the protection against coordinated replacement of manifest and all matching objects. Maximums are 1 MiB for the manifest, 256 logical objects, 64 MiB per object and 256 MiB logical total. Version 1 supports directories. TAR restoration remains a separate historical workflow.

Portable bundle v1 wraps the existing case, evidence and snapshot v2 contracts and registered derivation v1. Native receipt v1/v2 guarantees are unchanged. The [JSON Schema](../src/tether_engine/schemas/portable-bundle-v1.json) describes the transport shapes. The runtime additionally checks graph closure, aliasing, byte bounds, chronology and computed equality. Canonical JSON used for logical fingerprints is UTF-8, sorted by key, compact and finite, with no byte-order mark or trailing newline. Bundle object hashes always cover the exact stored bytes. [Canonicalization vectors](../tests/fixtures/portable_bundle_canonical.json)

## Validate a source archive

From an extracted source archive, run `python -I -B tools/portable_validate.py --output portable-validation`. The report inventories discovered and executed tests and records failures or skips. The separate full-clone validation still covers Git history, optional ingestion and native studies. See [maintenance](MAINTENANCE.md) for those requirements.
