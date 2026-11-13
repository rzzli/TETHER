# Development and maintenance

Use Python 3.11 or later and `uv`. Full validation also requires Windows,
PowerShell 7 and the optional ingestion dependency. Run commands from the
repository root.

## Install for validation

```powershell
uv sync --locked --python 3.11 --extra ingest --no-install-project
uv pip install --no-deps . packages/tether --build-constraints tools/build-constraints.txt
uv pip check
```

Install noneditable packages for tests that qualify installed module identities.
The runtime is dependency-free; PyArrow 21.0.0 is used only by optional ingestion.
Pinned build constraints live in [tools/build-constraints.txt](../tools/build-constraints.txt).

## Validate changes

```powershell
uv run --no-sync python tools/validate.py --mode full --package
uv run --no-sync python -B -m unittest discover -s packages/tether/tests -v
```

The full gate runs structural/catalog checks, Python and PowerShell syntax checks,
repository tests, required framework probes, and an offline wheel build plus an
isolated dependency-free demo and verification. `--report <fresh-path>` retains
its result; `--failfast` stops after the first failed test. Core mode allows only
its explicitly named platform/optional-dependency skips.

Native tokenizer fixtures and their composition tests require Windows sharing
locks and skip before setup on other platforms. Core validation still runs the
portable parser, subprocess-boundary and fail-closed platform checks. Full mode
rejects these skips; a Linux core pass does not qualify Windows locking behavior.

Some compatibility fixtures read exact bytes from a pinned Git checkpoint through
[tools/history.py](../tools/history.py). A full clone contains that history; shallow
clones may need `git fetch --unshallow --tags` before running the tests. Public CI
fetches full history. Optional [experiment suites](../experiments/README.md) require
their own dependencies and prepared inputs; a core test pass does not qualify a
model or scientific benchmark.

The current-policy gate separately lists 16 frozen SC04/SC05 integration methods
in `legacy_compatibility_group`; it does not count them as passed or skipped.
Their producer creates an unregistered computed manifest, which engine 0.5.0
must reject. Current tests exercise that rejection before answer preparation and
assert that the explicit partition retains every original test method. Portable
recovery/accounting tests continue to run in the current gate.

Run the 16 historical integrations with engine 0.4.0 and wrapper 0.6.0 from their
matching source checkpoint (pre-RP02 checkpoint `3fc1050`), retaining a separate
result. Use an isolated checkout and verify its installed runtime against that
checkpoint. An old installed engine mixed with the current source tree would
record the wrong producer source inventory. From that historical checkout:

```powershell
& $legacyPython -B -m unittest `
  experiments.litqa_refinement_recovery.test_original.OriginalTests `
  experiments.litqa_refinement_recovery.test_reconstruct.ReconstructionIntegrationTests `
  experiments.litqa_refinement_recovery.test_run_integration.RecoveryNativeIntegrationTests `
  experiments.litqa_refinement_recovery.test_run_integration.CompleteRecoveryControllerTests -v
```

`$legacyPython` denotes the independently checked historical interpreter. The
maintained loader also exposes `tests.test_refinement_recovery.legacy_suite` to
identify the original methods; selecting that suite does not qualify an unmatched
runtime. A current gate pass alone does not establish historical compatibility.

## Catalog updates

Keep shared source requirements in the tracked template. Acquisition observations,
receipts and use grants belong in ignored local deployment files. First copy the
template to a new local catalog; the copy below refuses to overwrite an existing
catalog. Keep an existing deployment catalog when applying later reports.

```powershell
$localRoot = New-Item -ItemType Directory -Path data/manifests/private -Force
$localCatalog = Join-Path $localRoot.FullName 'catalog.json'
[System.IO.File]::Copy((Resolve-Path data/catalog/sources.json).Path, $localCatalog, $false)
```

The writer requires a sanitized acquisition report under `data/manifests/public/`
and the independently checked hash of the deployment catalog being updated.
Here, `public` is the sanitizer's directory convention: the whole `data/manifests/`
tree remains Git-ignored. Prepare the report at the path shown below, or use
another sanitized report within that directory:

```powershell
$localCatalog = (Resolve-Path data/manifests/private/catalog.json).Path
$catalogHash = (Get-FileHash $localCatalog -Algorithm SHA256).Hash.ToLowerInvariant()
uv run --no-sync python -m tether_engine.maintenance update-catalog `
  --catalog $localCatalog --report data/manifests/public/acquisition-report.json `
  --expected-sha256 $catalogHash
```

The updater validates references and allowed fields, takes an exclusive lock and
checks the old hash before replacement. A stale lock requires checking its recorded
process before manual recovery; it is not automatically discarded. Transport
observations cannot promote scientific validation. Bind a separate local
[artifact policy](TETHER-CATALOG-POLICY.md) to the exact deployment catalog and
keep that policy and its root map ignored. The shipped inventory-only policy is
bound to the public template and cannot authorize a changed local catalog.
Public requirement edits must keep the public deployment state empty and rebind
the public inventory policy without adding acquisition results or grants.

## Inspect a local Open Targets partition

The research utility [temporal_inventory.py](../tools/science/temporal_inventory.py)
checks an explicitly selected local partition without downloading data or decoding
row payloads. It requires the ingestion extra. Its manifest pins the release,
evaluator-only role, approved roots, transport queue, publisher checksum listing
and each original file's receipt, size and SHA-256. Use a manifest hash from the
reviewed selection; computing a new pin after an unexplained change does not
validate that change. The exact manifest fields and synthetic example are in
[the utility tests](../tests/test_science_temporal_inventory.py).

```powershell
uv run --no-sync python -m tools.science.temporal_inventory `
  --manifest data/manifests/private/selected-partition.json `
  --manifest-sha256 $reviewedManifestSha256 `
  --output data/derived/partition-inspection-01
```

The manifest, queue, publisher listing and local directory must name the same
files. Extra partial files and missing files fail inspection. Original receipts
are copied byte-for-byte into the new report directory; originals are unchanged.
File hashes and Parquet footers are checked through the same open stream. The
report records schemas, footer row counts, bytes, resource use and duplicate
content, with explicit limits on concurrent-writer and publisher authentication
guarantees. It reads no row-group statistics or scientific values.

Unsafe or unpinned inputs fail before output reservation. Later failures leave a
journal and, when writable, `failure.json`. Completion requires `report.json`
and the matching terminal journal hash; a lone terminal event is insufficient.
Output directories cannot be reused. A technical pass does not qualify date
semantics, historical availability, biological claims or clinical labels, and
does not authorize agent access to evaluator-only data.

The companion [date profiler](../tools/science/temporal_dates.py) reads exactly
eight date/source columns from a qualified OT 25.09 inventory and emits aggregate
counts. It supports the complete ChEMBL, GWAS credible-set, gene-burden and UniProt
literature partitions. Its fixed research policy compares reported calendar
intervals with January 1, 2024 and January 1, 2025; these are descriptive
reference dates, not historical prediction origins. Use the reviewed report hash
and an absolute inventory path:

```powershell
$inventoryPath = (Resolve-Path data/derived/partition-inspection-01).Path
uv run --no-sync python -m tools.science.temporal_dates `
  --inventory $inventoryPath --report-sha256 $reviewedInventoryReportSha256 `
  --output data/derived/partition-date-profile-01
```

The profiler rechecks the report/journal, original and captured metadata proofs,
and each file's hash before decoding selected columns through the same handle.
It preserves nulls, missing columns, malformed values, precision and comparison
denominators; it emits no original row values, trial identifiers, clinical phase,
status or scores. Publication, study and evidence dates stay separate and
semantically unqualified. Decoded Arrow bytes are reported separately from
original file bytes. Output and failure rules match the inventory utility; the
profile cannot be placed inside its input inventory. A passing profile does not
establish historical availability, labels or an unexposed evaluation population.

## Repository boundaries

Track source, package resources, test fixtures, reusable tools, experiment code and
public usage documentation. Keep raw data, model weights, caches, run outputs,
private root maps, generated reports and personal working notes outside the public
tracked tree. Preserve receipt-bound originals rather than editing them in place.
Use fresh output directories and inspect incomplete attempts before considering a
separate new execution; inspection must never restart a potentially billed call.

Receipt archive verification uses up to eight read attempts, separated by 10 ms,
only when Windows reports `EACCES`. This handles transient read contention without
repeating publication. Persistent denial, other errors and conflicting bytes still
fail; an input node is updated only after exact-byte verification. Source hashes
distinguish this development implementation from earlier builds. Preserve original
code and sealed outputs and qualify changed source before a new execution; this
change does not migrate or reseal an existing run.

After a reviewed engine change, check the archive's exact dependency declaration
as well as the affected function tests. A stale module pin deliberately blocks
archive verification. Update it only with a documented compatibility review and
qualify a fresh installation; a test run against an older installed wheel cannot
qualify changed checkout code.
