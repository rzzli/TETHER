# IL6R / rheumatoid arthritis: a real offline example

**Question:** what does one pinned Open Targets annotation say about this target–disease pair?
The example preserves the proposed hypothesis—**inhibit IL6R with an antibody,
tissue unspecified**—without claiming that the source validates that intervention.

| Included | Deliberately unestablished |
|---|---|
| One OT25.09 genetic-association annotation | Therapeutic benefit, causal effect and intervention direction |
| Same-release IL6R and rheumatoid arthritis identifier rows | A complete literature or biological evidence review |
| Descriptive provider score, reported PMID/date, original row locators | Validated numerical prediction features or clinical probability |
| Explicit missingness and source-linked execution record | Independent scientific validation or publisher authentication |

The source slice has **three exact original files, 15,010,826 bytes**, plus 2,296
receipt bytes. It is separate from the slim default wheels. The offline commands
below make no download, live-model or paid call. The current Open Targets Platform
[licence](https://platform-docs.opentargets.org/licence) marks its data CC0; these
terms do not extend to separately obtained article full text or upstream datasets.

## Prepare the inputs

Use the installed packages from the repository quick start, Python 3.11, and
`pyarrow==21.0.0` for preparation and the optional original-row audit. A source
root must already contain the originals and archived receipts listed in
[the exact input manifest](../tools/examples/il6r_ot2509.json), with those relative
paths and hashes. The repository supplies the original receipt witnesses and a
recipe for retrieving the three files.

An optional `tools/examples/fetch_il6r.py --output <fresh-source-root> --allow-network`
can retrieve only those three hash-pinned originals, capped at 16 MiB of response
payload. The command requires explicit opt-in and rejects HTTP redirects. The
checked-in 2,296-byte receipts are prior-acquisition witnesses. Fresh retrieval
has a separate journal and timestamps.

From the source checkout, substitute your source root and choose new sibling
output directories. Their parent must already exist:

```powershell
uv pip install pyarrow==21.0.0
New-Item -ItemType Directory -Path runs -Force | Out-Null
uv run --no-sync python -I tools/examples/prepare_il6r.py --source-root E:/projects_data/drug_target_agents_data --output runs/il6r-inputs
```

Preparation verifies exact bytes and row projections, copies the three originals
into the new input directory, and writes a narrowly scoped local artifact policy.
Invoking it selects that example use; it does not amend the public blank policy
or old permissions. The gene symbol is checked against the same-release target
file, **not an HGNC crosswalk**. Download timestamps establish contemporary upper
availability bounds; they do not make this a historical benchmark. The printed
frame hash binds the fixed selected hypothesis and rows. Retain it separately.

## Run, read and relocate

The typed recipe uses `tether.api` and the existing supervised policy path:

```powershell
uv run --no-sync python -I tools/examples/run_offline.py --inputs runs/il6r-inputs --output runs/il6r-run --bundle-output runs/il6r-bundle --frame-sha256 <saved-frame-hash>
```

Read **`runs/il6r-run/dossier.md`**. Structured claims, coverage, features and the
null prediction are under `runs/il6r-run/engine/`. The command also verifies and
exports the source-inclusive bundle. Retain its printed manifest hash. Copy that
bundle to a different directory or machine and verify without original inputs:

```powershell
uv run --no-sync tether bundle-verify --bundle-dir <copied-bundle> --manifest-sha256 <saved-manifest-hash>
```

For a concise HTML reading view and an independent exact-row audit, use the
printed outer and native receipt hashes:

```powershell
uv run --no-sync python -I tools/examples/audit_il6r.py --inputs runs/il6r-inputs --run-dir runs/il6r-run --output runs/il6r-reading --receipt-sha256 <saved-receipt-hash> --engine-receipt-sha256 <saved-engine-receipt-hash>
```

Open **`runs/il6r-reading/reading-view.html`**. Its companion JSON contains exact
source URLs, hashes and row locators; `audit.json` binds the reading view's bytes.
This separate view does not alter or inherit the native dossier seal. Source
text is rendered literally; unknown context and incomplete collection stay visible.

## What verification means

Native verification checks the artifact-use policy, source bytes and supported
execution semantics. Bundle verification checks portable source/claim consistency,
not the outer use grant or exact producer replay. The original-row audit separately
checks the Parquet projections; there is no registered runtime Parquet derivation.
None establishes biological truth, prediction quality or a clinically useful drug.

At commit `b2117eb`, Windows x64, Ubuntu x64 and macOS 15 Intel each retrieved the
three pinned files, audited the three selected rows and replayed the relocated
bundle. Installed run, export and verification took 6.05, 4.05 and 20.05 seconds
respectively, excluding preparation and dependency installation. [Hosted example qualification](https://github.com/rzzli/TETHER/actions/runs/44344125809)
