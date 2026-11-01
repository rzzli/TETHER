# AsOf local research artifact 0.1.0

This package contains the frozen source-reporting reconstruction artifact and its
separate local qualification record. It is prepared for research review. It is
not a public deposit or a submission-ready paper; owner declarations remain
deferred. No upload, publication or hosted-CI result is claimed.

Start with `artifact/README.md` for the exact Windows environment, external inputs,
installation, reconstruction, independent audit and presentation commands.
Use **`python -B -I`** for source tests. This prevents bytecode cache files inside
the bundle, whose whole file inventory must remain unchanged. The command is:

```powershell
& $python -B -I -m unittest discover -s (Join-Path $bundle 'source/replay/tests') -v
if ($LASTEXITCODE -ne 0) { throw 'Installed fictional tests failed.' }
```

`RELEASE-MANIFEST.json` lists each archive member's hash, byte count and role.
`qualification.json` records actual terminal local checks and their evidence hashes.
Evaluation metadata is evaluator-only and must not become agent-visible inputs.

The independently retained reconstruction protocol SHA-256 is:

```text
650859b151bee4a98d6da8c779a7b498720929bfe1e7218d5e6f426f78cea123
```

Check the complete ZIP hash against its separate release record before trusting
this copy. Recomputing a hash supplied only by an untrusted archive is insufficient.
No declaration of scientific correctness follows from a matching hash.

## What is reproduced

The installed Windows reconstruction reproduces all 38 retained output byte
hashes and 90 policy decisions from the original deterministic study. It uses
all 137 complete, exact originals and their receipts. The source-inclusive
independent auditor passes 6,862 checks. The additional 2,400-check sealed-file
review checks metadata and artifacts; it is not another provider-source replay.

The new reproduction took 229.422 seconds; its separate audit took 14.953 seconds.
These are post-result qualification operations. The frozen P06 study retains its
original 203.828-second production and 7.125-second audit measurements. Policy-only
I/O counters exclude repeated compiler reads; total physical I/O and platform
cost remain unknown. All operations here make zero model/provider calls.

The minimal public catalog produces genuine new reference fingerprints. Historical
reference comparison removes only `method.catalog_sha256`. New G0 authenticates
the new protocol, code, sources and outputs. It does not verify unavailable old
private journal/seal archives. Shared core dependencies remain disclosed; an
independent implementation audit is not independent scientific adjudication.

## Data and document boundaries

This copy includes the exact CC0 HGNC snapshot and exact project receipt metadata.
The 136 Open Targets 25.09 originals remain external and mandatory. Fresh exact-byte
reacquisition from their URLs has not been tested. A 24-row extract cannot replace
complete input files. See `artifact/cards/` and the pinned source policy before
obtaining any missing inputs. Model weights and font binaries are not included.

The inner `artifact/paper/` is the working paper snapshot sealed with the protocol.
Its earlier release-limitations wording records its status at that freeze. Later
P10 manuscript/PDF revisions are separate versions and do not change this frozen
artifact. The retained manuscript PDF's original renderer/font environment is not
bundled. The separate portable figure/table renderer recreates 37 exact historical
payloads; its README and manifest are explicitly new portable metadata versions.

Native nulls and unknown context remain visible. This selected, exposed technical
study does not establish genetic causality, clinical prediction, independent-study
generalization, model superiority or expert equivalence. Numerical prediction
features remain empty and clinical probabilities null. Historical human responses,
their descendants, protected outcomes and private operational logs are excluded.

Supported local qualification is Windows x64, CPython 3.11.15 and PyArrow 21.0.0.
Core/full framework gates, installed fictional tests and package tests have their
separate scopes in `qualification.json`. Native Linux replay and current hosted
jobs are not qualified by those local checks. Provider spend is zero; total
platform cost is not estimated. Author metadata and factual declarations must be
confirmed before final manuscript preparation or publication.
