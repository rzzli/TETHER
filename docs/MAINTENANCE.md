# Development and maintenance

Use Python 3.11, Git and `uv` for the qualified development route. Full validation also requires Windows,
PowerShell 7 and the optional ingestion dependency. Run commands from the
repository root.

## Platform support

The package metadata's Python minimum is a syntax/dependency floor, not a claim
that every newer interpreter or operating system has passed qualification.

| Platform and interpreter | Current qualification |
|---|---|
| Windows x64, CPython 3.11.15 | Installed maintained gate, clean ZIP, native controls, source-only export and relocated fictional bundle passed locally. |
| Ubuntu WSL x64, CPython 3.11 | Installed core gate passed locally: 864 collected, 751 executed without skip, 113 explicit platform/dependency skips; 319 source-export tests and installed demo/verification passed. WSL does not qualify hosted Ubuntu or Windows-native behavior. |
| macOS, CPython 3.11 | CI target; execution evidence pending. |
| Other Python versions/platforms | Unqualified for this development release; earlier component checks do not qualify this version. |

The named local runner is `windows-local-311`: Intel Core i7-14700F, 28 logical
processors, Windows x64. At `ecf124e`, its 855-test maintained installed gate took
140.515 seconds and its reversed clean-ZIP gate took 145.484 seconds. The 319-test
dependency-free source-export subset took 51.375 seconds. These are local timings,
not hosted-CI timing promises. The hosted fast-gate target is under five minutes;
runner identity, actual time and reports must be retained before claiming it passed.

The validation command selects a physical temporary directory for its fixtures
and subprocesses. This avoids macOS's system `/var` alias in tests that deliberately
reject linked ancestors. Runtime authorization still requires caller-selected
roots; metadata never grants access. Tests explicitly cover caller root aliases,
Windows short-name spelling, denied descendant links, and outputs-only verification
without reopening originals.

## Install for validation

```powershell
uv sync --locked --python 3.11 --extra ingest --no-install-project
uv pip install --no-deps . packages/tether --build-constraints tools/build-constraints.txt
uv pip check
```

Install noneditable packages for tests that qualify installed module identities.
The runtime is dependency-free; PyArrow 21.0.0 is used only by optional ingestion.
Pinned build constraints live in [tools/build-constraints.txt](../tools/build-constraints.txt).

POSIX installation and fictional quick start (use a fresh output path):

```sh
uv sync --locked --python 3.11 --no-install-project
uv pip install --no-deps . packages/tether --build-constraints tools/build-constraints.txt
mkdir -p runs
uv run --no-sync tether demo --output runs/my-first-demo
uv run --no-sync tether verify --run-dir runs/my-first-demo
```

An installed wrapper and its exact engine must agree. If verification reports
different code/version inventories, use the original matching environment for
that run; reinstalling current packages does not migrate old receipts. Prefer
noneditable installations for reproducibility. Run `uv pip check` and both
`uv lock --check` / `uv lock --project packages/tether --check` after version changes.

## Pinned quality and coverage checks

Developer tools are separate from runtime dependencies:

```powershell
uv pip install -r tools/quality-requirements.txt
python -I -B tools/quality.py --output ../tether-quality-01
```

Ruff 0.15.22 checks correctness rules E9/F63/F7/F82 across every slim runtime
Python file. Formatting and mypy 2.4.1 strict mode are staged: decimal money,
calendar/UTC bounds and caller verification policy are the initial typed
interfaces. The quality report enumerates formatting and typing scope. Imported
modules are outside that typing claim; no `py.typed` marker or fully typed SDK
claim is shipped. Frozen study source is outside this gate.

Coverage.py 7.17.3 measures the installed maintained gate in the parent process:

```powershell
python -I -B -m coverage run --rcfile tools/coverage.ini --data-file ../tether-coverage.data tools/validate.py --mode full --profile maintained --report ../tether-validation.json
python -I -B -m coverage json --rcfile tools/coverage.ini --data-file ../tether-coverage.data -o ../tether-coverage.json
python -I -B tools/coverage_gate.py --coverage ../tether-coverage.json --validation ../tether-validation.json
```

The Windows/3.11 baseline covers 6,545/8,154 statements (80.267%) and
2,186/2,930 branches (74.608%) across all 57 packaged Python files, with 862
maintained tests and no skips. Child-process execution is not measured. The gate
rejects missing files, inconsistent counts, failed/skipped tests and coverage
below the reviewed thresholds. Baseline changes need a source/test-scope rationale;
do not silently reset them after failure. Coverage is not scientific validation.

Configuration references: [Ruff](https://docs.astral.sh/ruff/configuration/),
[mypy](https://mypy.readthedocs.io/en/stable/config_file.html), and
[Coverage.py](https://coverage.readthedocs.io/en/latest/config.html).

## Errors and recovery

| Exit code | Meaning for run/verify commands | Next action |
|---|---|---|
| 0 | The selected software operation completed | Read its assurance fields; this does not establish scientific truth. |
| 2 | Input, environment, verification or engine failure | Read stderr and retained failure/attempt records; correct the cause. |
| 3 | Partial execution, including exhausted work budgets | Inspect coverage, accepted claims and accounting before choosing a fresh run. |
| 130 | Interrupted | Inspect attempts; never assume a potentially billed call is safe to repeat. |

Delegated tools can propagate their own child exit codes. Failed finalization or
storage failure may prevent a final receipt; `inspect-run` describes available
records without restarting work. Neither hash chains nor exit status establish
external authenticity. See [verification scope](TETHER-VERIFICATION-SCOPE.md).

**Terminology:** a snapshot fixes eligible inputs; a claim is an admitted
source-linked observation; a receipt binds artifact bytes; a journal records
attempts and state transitions; an anchor is a separately retained digest;
source replay checks agreement with supplied originals; scientific validation
requires a separate scientific evaluation. A collection profile is not a data-use grant.

## Validate changes

```powershell
uv run --no-sync python tools/validate.py --mode full --profile maintained --package
uv run --no-sync python -B -m unittest discover -s packages/tether/tests -v
```

The maintained full gate runs structural/catalog checks, Python and PowerShell syntax checks,
repository tests, required framework probes, and an offline wheel build plus an
isolated dependency-free demo and verification. `--report <fresh-path>` retains
its result; `--failfast` stops after the first failed test. Core mode allows only
its explicitly named platform/optional-dependency skips.

The maintained scope includes the installed wrapper tests and excludes checks
that require original Git bytes or a historical runtime. Select it explicitly;
the broader `all-current` source-development gate remains a separate option:

```powershell
python -B tools/validate.py --mode full --profile maintained --report ../tether-checks/maintained.json
```

For a clean source ZIP, add `--layout export`. This mode creates temporary Git
metadata outside the source solely to check ignore rules; it never borrows a
parent checkout or restores historical records. Git must still be installed.
`--reverse` reverses the maintained test order. `--package` additionally builds
from a scratch copy, installs the wheel offline and verifies its demo. Report and
temporary directories should be outside the exported source tree. Install both
packages first: tests do not silently add wrapper source paths to the interpreter.

The selected profile also applies to required probes. Maintained mode executes
the nine current fictional probes and records legacy byte verification separately
as `not_executed_requires_pinned_history`. The default retains that historical
probe as a required check. Validation reports embed the complete probe results;
an unexecuted historical check is never reported as passing.

Slim wheels do not contain historical study drivers. The `all-current` profile
includes source-development and migration-candidate checks that can require those
drivers; it is not an installed slim-wheel release gate. Preserve their exact
original code, full wheels and expectations as described in
[migration guidance](../packages/tether/MIGRATION.md#slim-development-wheels-november-2026).
Nine mixed-module methods for removed source-fact, tokenizer and server drivers
remain in the migration scope. Core accounting, evidence checks and installed
wrapper process-lifecycle controls stay maintained; the policy enumerates each
method. Historical tests are preserved, not reported as passing in slim wheels.
The separate source-only `portable_validate.py` gate does not claim installed
package layout. Namespace, removed-module and isolated-launcher checks execute
in the maintained installed-wheel gate and wrapper suite above, not against the
retained historical source directories.

## Inventory all test modules

The default gate does not collect every experimental suite. Before claiming
complete test coverage, collect all three test trees in isolated processes:

```powershell
python -B tools/test_inventory.py --output tmp/test-census-01
```

This command discovers source files without Git, hashes their bytes and compares
every directly declared test method with the collected cases. Each module gets a
fresh Python process and scratch directory; import-side environment, path or audit
hook changes cannot affect the next module. It executes no test methods. The
inventory reports imported/inherited duplicates separately through its total and
unique counts. Missing dependencies, timeouts and omitted methods fail collection;
they are not counted as passing tests. Per-module output survives later failures.

For optional suites, `--environments <local.json>` accepts a mapping from test
path prefixes (for example `experiments/scifact`) to local Python executables.
The longest matching path prefix wins. Use separately prepared environments with
the suite's pinned dependencies; the command installs nothing. `-I` prevents
inherited `PYTHONPATH` and user-site settings from supplying missing dependencies.
Repository source paths are added explicitly inside each worker. Collection is
for trusted repository tests, not an execution sandbox. A complete census does
not establish execution, historical compatibility or scientific validity.

An explicit [test-scope policy](../tools/test-profiles.json) maps every test file
to the component designations in the verification-scope document. Method overrides
keep original-runtime and original-Git-byte checks separate within mixed modules.
Reconcile a fresh census with that policy:

```powershell
python -m tools.test_profiles --inventory tmp/test-census-01/inventory.json --output tmp/test-scope-01.json
```

Changed source hashes, missing file classifications, omitted methods and obsolete
overrides fail reconciliation. The result lists every unique method and its scope;
all execution statuses remain unqualified by this census. The classifications are
`maintained`, `migration_current`, `historical_research`,
`historical_inputs_current_runtime` and `original_runtime`. Migration candidates
remain in the existing full gate. This policy does not remove checks, turn a failed
historical experiment into a pass, or replace the full or installed-package gates.

The 16 November 2026 qualification at `c32ed72` passed 836 maintained methods
from a clean ZIP with installed wheels in forward, reversed and 71 isolated-module
runs, without skipped tests or source-tree writes. The reversed public gate,
including probes and offline packaging, took 167.641 seconds on the tested Windows
Python 3.11 installation. The broader default gate at `e173cda` passed 3,175 tests
without skips; the subsequent probe-profile change passed 39 focused controls and
all ten default probes. These overlapping runs are not additive unique-test counts.
The complete census classified 4,694 unique methods; classification does not claim
execution of every historical experiment or qualification on other platforms.

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
