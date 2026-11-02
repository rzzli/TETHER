# Q06 reuse and build recipe

Prepared stage: `D:/Projects/drug_target_agents/data/cache/tether-q06/working-v1`.
`STAGE-PREPARATION-working-v1.json` binds every copied source, staged byte digest, and exact Markdown link transformation. Expected final archive closure is 78 members: 18 matching Python source files plus 60 fixed document/result/software/metadata members. PDF, outer qualification, and packet manifest were deliberately left pending. No fake PDF or qualification placeholder exists on disk.

## Existing formatter and available runtime

The unchanged formatter is `tools/presentation/build_tether_manuscript.py`, SHA-256 `07330d35414b61d78e4039c03d1ab31e5530f9949e5180d51af9f6f29ed1569b`. Its options are `--check-inputs`, `--build`, or `--self-test`, plus `--marker-confirmed`, `--repeat-check`, and `--preview-root`. It has no source/output-path options. Its root is derived from its location, and publication defaults bind output filenames at import time; using a byte-identical copy at the same relative path inside the new stage avoids changing the formatter or overwriting the current paper/PDF/build.

The project `.venv` has no ReportLab, pypdf, pdfplumber, Pillow, or other inspected PDF packages. No installation is needed: the bundled runtime Python already has ReportLab 4.4.9, pypdf 6.10.0, pdfplumber 0.11.9, and Pillow 12.3.0. The pinned Poppler executable, Arial/Consolas fonts, and PDF-operation marker all exist. The ordinary `python` WindowsApps alias is unusable here; use the explicit executable below.

The formatter's `paper/results/ARTIFACTS.json` remains pinned to `84d4a31e842d3085133d384429729ef2501425d33bf2b92f65d9c64699a87428`. The packet's separate portable-results manifest is pinned to `da802210539141fd7e25418d1440b1f749c3e5d16e6b62ddc7562db01cc11eb4`. They must remain in separate stage locations. The formatter reads only its declared manuscript/supplement and verified vector figures; it does not rerun the study.

## Root-owned rendering commands

These are reuse commands, not commands executed by the preparation subtask. First confirm the intended paper revision hashes still match the staging report; later editorial changes require a fresh named stage rather than silently replacing this stage's provenance.

```powershell
$q06Repo = 'D:\Projects\drug_target_agents'
$q06Stage = Join-Path $q06Repo 'data\cache\tether-q06\working-v1'
$q06PdfPython = 'C:\Users\zzric\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$q06Node = 'C:\Users\zzric\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$q06Marker = 'C:\Users\zzric\.codex\plugins\cache\openai-primary-runtime\pdf\26.1026.10807\skills\pdf\container_tools\mark_artifact_operation_started.mjs'
$q06Formatter = Join-Path $q06Stage 'tools\presentation\build_tether_manuscript.py'
$q06Preview = Join-Path $q06Stage 'tmp\pdfs\q06-pages'
& $q06PdfPython $q06Formatter --check-inputs --preview-root $q06Preview
```

Immediately before the first actual PDF authoring command, run the existing PDF skill's marker once. Do not rerun the marker for layout corrections. Do not pass `--marker-confirmed` without the successful marker execution.

```powershell
& $q06Node $q06Marker --operation-kind create --expected-output-count 1 --output-format pdf
& $q06PdfPython $q06Formatter --build --marker-confirmed --repeat-check --preview-root $q06Preview
```

The resulting new files are stage-local `paper/tether-source-reporting-preprint.pdf` and `paper/TETHER-PDF-BUILD.json`. The root agent owns final placement of an exclusively created reviewed copy under `paper/revisions/20261102/`. Existing main-checkout source files, PDFs, build manifests, and ZIPs must remain byte-identical. Preserve any failed candidate stage and choose a fresh stage name for another distinct revision.

The build automatically performs ordered visible-source retention, page-boundary and vector checks, source/figure/font/library binding, and a same-environment repeat check. It also renders every page. Independent visual inspection of all rendered pages is still required; automated text retention alone is not visual QA. Do not carry forward the old 18-page count or old PDF audit as a claim about the corrected PDF.

## Packet interface and closure

The separate builder `tools/presentation/package_tether_review_v2.py` retains the v1 safe helpers but explicitly binds TETHER 0.5.0, compatibility engine 0.3.11, and qualification/manifest method v2. The original builder remains unchanged. The v2 source delta and pins are recorded separately in `PACKAGER-V2-DELTA.json` and `PACKAGER-V2.diff`.

Its exact CLI requires `--workspace-root`, `--results-root`, `--wheel`, `--legacy-zip`, `--qualification`, `--qualification-sha256`, and `--output`. The output and `.partial` path must not exist; output must be under the supplied workspace's `data/cache` or `data/derived`, outside immutable input trees. Parent output directories must already exist. The writer uses exclusive creation, deterministic stored ZIP members, readback/CRC/physical-byte closure, and no-replacement publication.

After the reviewed PDF and new qualification are ready, root may use:

```powershell
$q06Python = Join-Path $q06Repo '.venv\Scripts\python.exe'
$q06Qualification = Join-Path $q06Stage 'TETHER-QUALIFICATION.json'
$q06QualificationHash = (Get-FileHash -LiteralPath $q06Qualification -Algorithm SHA256).Hash.ToLowerInvariant()
& $q06Python (Join-Path $q06Repo 'tools\presentation\package_tether_review_v2.py') `
  --workspace-root $q06Stage `
  --results-root (Join-Path $q06Stage 'inputs\portable-results') `
  --wheel (Join-Path $q06Stage 'inputs\wheels\tether_target_agents-0.5.0-py3-none-any.whl') `
  --legacy-zip (Join-Path $q06Stage 'inputs\legacy\asof-research-artifact-0.1.0.zip') `
  --qualification $q06Qualification --qualification-sha256 $q06QualificationHash `
  --output (Join-Path $q06Stage 'data\derived\tether-review-0.5.0-q06.zip')
```

The qualification must be newly prepared from `source_inventory(...)` after PDF review, with exact payload hashes/bytes/roles and working-draft scope flags. It is not supplied by this preparation task. Keep owner declarations deferred, author acceptance pending, submission readiness false, publication unauthorized, and scientific validity/study independence unestablished.

The positive allowlist includes six paper sources plus the PDF; root README; 39 portable historical result files; four original P09 reproduction items; the qualified 0.5.0 wheel; four project support files plus 18 Python sources; and exactly two extra documents, `documentation/CURRENT-SOFTWARE.md` and `documentation/SOFTWARE-QUALIFICATION.json`. Qualification and packet manifest close the remaining two members. The software proof is independently pinned to `65db5977e93281b1e186590ba1116a204ca396052251805798abda9247435e35`, validated against a closed field schema, screened for private fields/paths, and tied to the admitted wheel/source bytes.

The new outer layer excludes raw provider/source-row files, Q01/Q02 originals, Q03 excerpts, human/expert returns, clinical payloads, policy/root-map files, private metadata, environments, and broad repository directories. The original P09 ZIP is an explicit opaque exception under its historical allowlist, which includes its already-admitted CC0 HGNC original/project receipts and evaluator reproduction material. Nothing inside that archive is newly reclassified or rewritten.

## Source and publication checks

Before final publication, independently compare the ZIP's exact member set and roles with the closed preparation inventory plus reviewed PDF/qualification/manifest; verify every member digest, CRC, physical closure, and fresh whole-ZIP digest. Verify wheel RECORD/namespace/source equality and the 0.5.0 software proof. Preserve original nested P09 and all 37 historical numerical payload commitments. Audit local Markdown link closure and public metadata without copying local policies or private records. Verify old source/PDF/ZIP hashes again after the operation.

`PACKAGER-V2-TESTS.json` records 17 fictional-only boundary tests. `PACKAGER-V2-SOURCE-BYTE-PROBE.json` adds a same-namespace/same-length Python-source substitution rejection. These test the new packaging boundaries; they do not repeat Q02 installed software tests or a historical/source study. Stage preparation used only explicit copied public artifacts and metadata, made no PDF/ZIP, and performed no model calls, downloads, or backend dispatch.
