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
