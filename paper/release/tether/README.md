# TETHER local review packet

This guide is installed as `README.md` at the packet root; its relative links
resolve in that standalone layout.

TETHER means **Target Evidence Tracking Harness for Evaluation and
Reproducibility**. The project was previously named AsOf. This naming and software
front-door revision follows the experiments; it changes no original scientific
result, protocol identifier or measured study cost.

Start with the current [TETHER paper](paper/manuscript.md),
[supplement](paper/supplement.md) and
[TETHER working PDF](paper/tether-source-reporting-preprint.pdf). The
[qualification](TETHER-QUALIFICATION.json) records the actual local software and
presentation checks; [PACKET-MANIFEST.json](PACKET-MANIFEST.json) binds all members
except itself. Verify this ZIP against its separately retained external SHA-256
before trusting its contents. A hash supplied only by the same untrusted ZIP is
insufficient.

This is a local working-draft review artifact, not a public deposit, scientific
validation or submission-ready paper. Author facts, declarations and final author
acceptance remain deferred. No funding, conflict or authorship facts are inferred.
No external expert response is required. Upload/publication is a separate action.

## What is included

- Current editable paper, thirteen-reference bibliography, source audit,
  unfilled declaration checklist and the reviewed TETHER PDF. Earlier P10/P08
  AsOf PDFs and snapshots are history, not the current outer paper.
- [Results](paper/results/README.md): 37 exact historical numerical/table/figure
  payloads and their two retained portable metadata files. These retain historical
  names and measured P06 costs; they are not new experiments or TETHER benchmarks.
- The immutable [AsOf P09 archive](reproduction/asof-research-artifact-0.1.0.zip),
  [release record](reproduction/RELEASE-RECORD.json),
  [qualification](reproduction/qualification.json) and
  [instructions](reproduction/README.md). Legacy filenames and identifiers are
  deliberate compatibility records, not renamed or repaired evidence.
- The [TETHER 0.4.0 wheel](software/tether_target_agents-0.4.0-py3-none-any.whl)
  and [project source](software/source/packages/tether/README.md), including its
  pyproject, lockfile, license and Python files. Tests, caches, environments, raw
  PDF build manifests, font files, model weights, private outputs and human-response
  descendants are outside this outer allowlist.

The TETHER wheel contains only its own namespace. It depends on the unchanged
`asof-target-agents==0.3.11` engine. Python aliases preserve the same legacy classes
and module objects; old wire IDs, proof paths, package fingerprints and sealed
AsOf artifacts remain valid compatibility identities. The current TETHER PDF
does not replace the earlier paper inside the immutable P09 archive.

## Offline default installation and synthetic demonstration

Use a locally available CPython 3.11.15 and uv, an empty work folder outside this
read-only packet, and PowerShell. Nothing below downloads a dependency. The
default demonstration needs no Arrow or model library. Do not modify the nested
archive or run tests/builds inside its frozen file tree.

```powershell
$packet = (Resolve-Path '.').Path
$work = Join-Path (Split-Path -Parent $packet) 'tether-local-work'
New-Item -ItemType Directory -Path $work -ErrorAction Stop
Expand-Archive -LiteralPath (Join-Path $packet 'reproduction/asof-research-artifact-0.1.0.zip') -DestinationPath (Join-Path $work 'legacy-release') -ErrorAction Stop
$bundle = Join-Path $work 'legacy-release/artifact'
uv venv --offline --python '3.11.15' (Join-Path $work 'env')
if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed.' }
$python = Join-Path $work 'env/Scripts/python.exe'
uv pip install --offline --no-index --no-deps --python $python (Join-Path $bundle 'wheels/asof_target_agents-0.3.11-py3-none-any.whl') (Join-Path $packet 'software/tether_target_agents-0.4.0-py3-none-any.whl')
if ($LASTEXITCODE -ne 0) { throw 'Offline project installation failed.' }
& $python -B -I -m tether --version
& $python -B -I -m tether demo --output (Join-Path $work 'demo')
if ($LASTEXITCODE -ne 0) { throw 'Demo failed; retain its attempt and inspect it.' }
```

Save the printed **outer** receipt hash independently, then verify and inspect:

```powershell
& $python -B -I -m tether verify --run-dir (Join-Path $work 'demo') --receipt-sha256 '<saved-outer-receipt-sha256>'
if ($LASTEXITCODE -ne 0) { throw 'TETHER verification failed.' }
& $python -B -I -m tether inspect-run --run-dir (Join-Path $work 'demo')
```

`tether` is the equivalent console command in that environment. For an explicitly
approved normalized case, use `tether run --case <case.json> --snapshot
<snapshot.json> --catalog <catalog.json> --output <fresh-output>`. Default evidence
selection is deterministic and offline. Local-model configuration is explicit
opt-in; this packet authorizes no new model experiment or retry of the closed
development branch.

An outer run contains unchanged engine artifacts under `engine/`, a TETHER dossier
that changes only the exact first header, and separate launcher manifest/receipt
and attempt journal. Outer verification checks the original sources and both
layers; `--outputs-only` is rejected for an outer run. Direct legacy run APIs retain
their compatibility format. TETHER metadata/journals have a 64 MiB read limit and
dossiers a 256 MiB limit. Stable per-read checks and bounded cleanup are not an OS
sandbox or exclusive ownership across later engine reads. Failure records retain
cleanup errors/partial bytes; inspect without redispatch and choose a new output
for any future authorized attempt.

## Source layout and offline builds

The shipped new source is under `software/source/packages/tether`. Its local
`tool.uv.sources` engine path is `../..`. To build from source, make a separate
working copy with the legacy core project at that root. Keep this copy under the
same outside-work tree and copy only the stated public source subtrees:

```powershell
$sourceWork = Join-Path $work 'source-work'
New-Item -ItemType Directory -Path $sourceWork -ErrorAction Stop
foreach ($name in @('pyproject.toml', 'uv.lock', 'LICENSE', 'src')) {
    Copy-Item -LiteralPath (Join-Path $bundle "source/core/$name") -Destination $sourceWork -Recurse -ErrorAction Stop
}
New-Item -ItemType Directory -Path (Join-Path $sourceWork 'packages') -ErrorAction Stop
Copy-Item -LiteralPath (Join-Path $packet 'software/source/packages/tether') -Destination (Join-Path $sourceWork 'packages/tether') -Recurse -ErrorAction Stop
```

The resulting layout is:

```text
source-work/
  pyproject.toml          # unchanged asof-target-agents 0.3.11 project
  uv.lock
  LICENSE
  src/asof/
  packages/tether/
    pyproject.toml        # tether-target-agents 0.4.0
    uv.lock
    README.md
    LICENSE
    src/tether/
```

Build from each copied project's own directory, using the legacy bundle's
constraints and a separate outside-work wheel output:

```powershell
foreach ($project in @($sourceWork, (Join-Path $sourceWork 'packages/tether'))) {
    Push-Location -LiteralPath $project
    try {
        uv build --offline --build-constraints (Join-Path $bundle 'build-constraints.txt') --python $python --wheel --out-dir (Join-Path $work 'rebuilt-wheels')
        if ($LASTEXITCODE -ne 0) { throw 'Offline source build failed.' }
    } finally { Pop-Location }
}
```

This needs locally cached build tools (setuptools 84.0.0). If those tools are
absent, stop and provide them separately;
there is no automatic package-index fallback. Never copy new TETHER code into
`src/asof` or replace old code/wheel metadata to satisfy a proof. New wheels are
engineering build products, not newly qualified scientific study results.

## Historical source-inclusive reconstruction and limits

The nested P09 instructions retain the exact separately anchored protocol, both
project wheels, complete source/receipt inventory, independent auditor and portable
result renderer. Native replay needs all 137 exact originals and 137 receipts;
136 Open Targets originals remain external, while the specific exact CC0 HGNC
original is included under its own rights boundary. Fresh exact-byte external
reacquisition remains untested. Use a separately available local Arrow 21.0.0
wheel for that native path, following the nested instructions; no generic download
or selected-row substitute is supplied here.

The original 38 outputs/90 decisions and P06 203.828/7.125-second production/audit
remain distinct from post-result P09 289.938/15.187-second reconstruction/audit.
The 6,862-check source audit and 3,481-check metadata review have separate scopes.
Native qualification is Windows x64/CPython 3.11.15/Arrow 21.0.0; current hosted CI,
native Linux replay and external reacquisition are not established by this packet.
The new TETHER smoke/tests are software checks, not another study or biomedical
adjudication. Locus-only linkage, unknown study/variant/context agreement, exposed
controls and shared dependencies remain limits. No clinical prediction, causal
genetics, model superiority, expert equivalence or independent-study claim follows.
Provider spend is zero where measured; total physical I/O/platform cost remain
unknown. Retained manuscript PDF regeneration is not a portable font distribution.
