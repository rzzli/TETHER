# TETHER catalog identity and history

TETHER means **Target Evidence Tracking Harness for Evaluation and Reproducibility**.
The [active master catalog](sources.json) retains its existing schema, provider and
dataset IDs, roles, date fields, acquisition facts and scientific-status values.
The rename changes only its top-level title and the project-generated-assets
provider display name. It does not promote collection, parsing or validation.

The exact pre-rename bytes are preserved at
[sources-pre-tether-20261101.json](history/sources-pre-tether-20261101.json):
`3c3108e6318e791985892fecea6ca9ea6185af7810a5ffd4a6311be3ca6f6109` (SHA-256; 1,229,616 bytes).
The cosmetically renamed catalog is
`eafd955cad30dd36bd7417de165a508b1e891f90f42e2cc4bcb573043eaa65ac` (SHA-256; 1,229,620 bytes).
Historical snapshots, receipts and READY authorities continue to bind their
original catalog bytes; editing a display name does not preserve that byte hash.
New builds must bind their genuine current catalog fingerprint.

Legacy keys such as `asof_release_date` and `asofDate` express temporal/contract
semantics. The `asof_normalized_packets` dataset ID, archived paths and all other
identifiers remain unchanged. They are not instructions to use a new source role
or replace a sealed artifact. The canonical package is `tether-target-agents`
0.4.0 in `packages/tether`; its CLI/import aliases retain the frozen AsOf 0.3.11
engine. See [installation and compatibility](../../README.md#installation-and-compatibility).

The history copy is evidence, not an acquisition queue or a new reference/generation
input. Existing P05/P06/P09/P10 results, old releases and failed attempts remain
unchanged. Provider rights still apply independently of the project name.
