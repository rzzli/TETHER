# AsOf deterministic source-reporting research artifact

This is a working-draft artifact. Release qualification is in progress. Author
declarations are deferred; no publication or scientific validation is claimed.
The retained experiment is described in `paper/manuscript.md` and the combined
working PDF. This package reconstructs its deterministic source-reporting result,
with no model call, clinical probability, new cohort, MR or scorer training.

## Contents and authority

`protocol.json` is the versioned reconstruction authority. Obtain its exact SHA-256
through the separately retained release record; a hash computed from an untrusted
copy alone does not establish authority. The executable requires an explicitly
authorized READY protocol and checks every listed bundle member and complete
installed package payload inventory before source processing. A DRAFT protocol
cannot execute. Keep the bundle read-only: environments, inputs, outputs and logs
belong in separate sibling folders.

`config/source-policy.json` contains neutral queries and complete input hashes,
schema/row expectations, dates and source-role rules. `evaluation/comparison.json`
is evaluator-only. Generation uses source-only inputs; the comparator is parsed
only after generated outputs and references are sealed. Do not expose comparison
answers to a future generative agent. No human-response descendants are included.

`source/core/` is AsOf 0.3.11; `source/replay/` is the separate reconstruction
distribution 0.1.0. `wheels/` contains those two project wheels. Dependency wheels,
model weights and font binaries are not included. `cards/` records source, model,
code, font and redistribution boundaries. All rights remain subject to their
stated upstream terms; an HTTP response alone is not a usability or rights check.

## Exact inputs

The native reconstruction requires **137 complete originals / 2,866,248,239 bytes**
and all 137 exact receipt files. These are 100 GWAS evidence, 25 credible-set,
10 target, one disease and one HGNC file. A 24-row extract cannot replace them.
Every logical name, byte hash, receipt hash and schema is in the source policy.

`included-originals/` supplies exact project transport receipts and the exact
16,973,159-byte CC0 HGNC snapshot. Copy its contents into an otherwise separate
input root, preserving relative paths. Place the **136 external Open Targets
25.09 originals** there at their policy-relative names. The official URLs are
recorded per input. This package includes no automatic acquisition command;
obtain missing originals subject to source terms, then check hashes. Do not
substitute current HGNC or later Open Targets releases. Public download time is
an availability bound for this contemporary artifact, not historical availability.

## Installed Windows replay

Fresh exact-byte reacquisition of the 136 external originals has not been tested.
Local reconstruction uses previously receipt-verified copies; it cannot establish
that every external URL will continue serving those bytes.

The qualification target is **Windows x64, CPython 3.11.15, PyArrow 21.0.0**. Native
stable file locking fails closed on unsupported platforms. Fictional POSIX tests
are not native Linux qualification. Use a fresh environment outside this bundle,
the source checkout and the original input directories. The example assumes
PowerShell, a locally available Python 3.11.15 and uv. Replace the three absolute
paths below with new local locations; keep all outputs separate.

```powershell
$bundle = (Resolve-Path './asof-artifact').Path
$work = Join-Path (Get-Location) 'asof-work'
$originals = Join-Path (Get-Location) 'asof-originals'
$protocolSha = '<SHA-256 from the separately trusted release record>'
New-Item -ItemType Directory -Path $work -ErrorAction Stop
uv venv --offline --python '3.11.15' (Join-Path $work 'env')
if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed.' }
$python = Join-Path $work 'env/Scripts/python.exe'
```

Install the separately acquired PyArrow 21.0.0 wheel and the two project wheels
from a local wheelhouse. Use the correct CPython 3.11 Windows x64 Arrow wheel;
retain its hash. The following uses no index and no network resolution:

```powershell
uv pip install --offline --no-index --no-deps --python $python '<local-pyarrow-21.0.0-wheel>'
if ($LASTEXITCODE -ne 0) { throw 'Arrow installation failed.' }
uv pip install --offline --no-index --no-deps --python $python (Join-Path $bundle 'wheels/asof_target_agents-0.3.11-py3-none-any.whl') (Join-Path $bundle 'wheels/asof_p05_replay-0.1.0-py3-none-any.whl')
if ($LASTEXITCODE -ne 0) { throw 'Project wheel installation failed.' }
& $python -I -m asof_p05_replay reconstruct --protocol (Join-Path $bundle 'protocol.json') --protocol-sha256 $protocolSha --bundle-root $bundle --originals-root $originals --output (Join-Path $work 'reconstruction')
if ($LASTEXITCODE -ne 0) { throw 'Reconstruction failed; retain the directory and journal.' }
& $python -I -m asof_p05_replay audit --protocol (Join-Path $bundle 'protocol.json') --protocol-sha256 $protocolSha --bundle-root $bundle --originals-root $originals --reconstruction-root (Join-Path $work 'reconstruction') --output (Join-Path $work 'audit')
if ($LASTEXITCODE -ne 0) { throw 'Independent audit failed; retain the directory and journal.' }
```

Never restart a failed operation into the same directory. Read its journal and
failure record first. Fixes require a newly reviewed code/protocol authority and
a fresh output; no command automatically repeats a model or potentially billed
call. Time, memory and output limits are cooperative checkpoints, not an OS sandbox.
Physical I/O and platform charges remain unknown where unmeasured.

Success requires both a sealed reconstruction and an independent audit reporting
`PASS_INDEPENDENT_SOURCE_RECONSTRUCTION_AUDIT`. Expect 38 raw outputs / 90 decisions,
12 genuine rebuilt references and retained coverage/missingness. Two deliberately
malformed controls are expected study outputs. They are not missing execution.

## Compatibility limits

The minimal public catalog changes genuine reference fingerprints. The sole
historical reference comparison projection removes `method.catalog_sha256`;
all remaining facts, provenance and method fields must match. No old identity is
spoofed. New G0 verifies this protocol, code, inputs and generated files. It does
not byte-verify unavailable old private journals or sealed trees. Original archive
integrity and original matching-version acceptance remain separate claims.

The reconstruction is a reproduction after exposure to the historical result,
not a fresh prospective scientific test. Literal values and native nulls do not
establish genetic causality, study independence, expert equivalence or clinical
usefulness. Scientific validation remains unestablished.

## Tables and figures

`source/presentation/README.md` gives the standalone renderer command and exact
metadata arguments. It uses the pinned comparison/source policy plus the two
`presentation-inputs/` files, Python 3.12, ReportLab 4.4.9, pypdf 6.10.0,
Pillow 12.3.0 and Poppler. No private ledger or installed AsOf import is required.
All **37 numerical/table/figure payloads** match the retained historical bytes.
A new portable results README and manifest replace the original machine-path
versions; those two metadata files are not claimed identical to the originals.
See `paper/results/ARTIFACTS.json` for exact presentation commitments.

For source builds use `build-constraints.txt` (setuptools 84.0.0) with each source
project. Replay tests under `source/replay/tests/` need both installed packages
and Arrow, and write only under the configured system temporary directory. Test
fixtures are invented; their passing does not substitute for the actual-input
reconstruction and independent audit above.

```powershell
& $python -I -m unittest discover -s (Join-Path $bundle 'source/replay/tests') -v
if ($LASTEXITCODE -ne 0) { throw 'Installed fictional tests failed.' }
```

The retained manuscript PDF is supplied as an output. Its original renderer and
font environment are not bundled, so PDF regeneration is a separate operation.
