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
