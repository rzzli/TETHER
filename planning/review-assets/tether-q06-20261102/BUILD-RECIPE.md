# Q06 reuse and build recipe

Current prepared stage: `D:/Projects/drug_target_agents/data/cache/tether-q06/working-v2`.
`STAGE-PREPARATION-working-v2.json` binds every copied source, staged byte digest, and exact Markdown link transformation. Expected final archive closure is 78 members: 18 matching Python source files plus 60 fixed document/result/software/metadata members. PDF, outer qualification, and packet manifest were deliberately left pending by stage preparation. No fake PDF or qualification placeholder was created.

The first stage and its report remain intact. Root's first PDF build failed before publication because the original formatter recognized relative `.md` links but not the new `.json` proof link. Root retained `PDF-ATTEMPT-1.json`, made a separately versioned one-regex correction, and recorded `FORMATTER-DELTA-CHECK.json`. No paper text changed. `STAGE-V1-V2-DELTA.json` establishes identical source/staged hashes for all 80 nonformatter inputs. The actual executed v1 preparer was copied before editing to `revisions/prepare_working_stage_v1.py`; its SHA-256 `f0bc6758dc0a48854e22e7476d8606c3176c4a074ffb999757ce11f873af6d50` matches the contemporaneous v1 preparation report. The old recipe is preserved as `revisions/BUILD-RECIPE-before-v2.md`.

## Existing formatter and available runtime

The current corrected formatter is `tools/presentation/build_tether_manuscript_v2.py`, SHA-256 `c695400bf7a411f661d0b3bd8f1771eee3d550bd793e178ad6bd29318916b719`, staged under that exact filename. The original `build_tether_manuscript.py` remains unchanged at SHA-256 `07330d35414b61d78e4039c03d1ab31e5530f9949e5180d51af9f6f29ed1569b`. The sole v2 correction recognizes relative `.json` links alongside `.md`; root's focused regression checks cover the old failure and four cases. Both interfaces use `--check-inputs`, `--build`, or `--self-test`, plus `--marker-confirmed`, `--repeat-check`, and `--preview-root`. There are no source/output-path options. The root is derived from script location, so the fresh staged copy resolves all fixed output paths inside the new workspace.

The project `.venv` has no ReportLab, pypdf, pdfplumber, Pillow, or other inspected PDF packages. No installation is needed: the bundled runtime Python already has ReportLab 4.4.9, pypdf 6.10.0, pdfplumber 0.11.9, and Pillow 12.3.0. The pinned Poppler executable, Arial/Consolas fonts, and PDF-operation marker all exist. The ordinary `python` WindowsApps alias is unusable here; use the explicit executable below.

The formatter's `paper/results/ARTIFACTS.json` remains pinned to `84d4a31e842d3085133d384429729ef2501425d33bf2b92f65d9c64699a87428`. The packet's separate portable-results manifest is pinned to `da802210539141fd7e25418d1440b1f749c3e5d16e6b62ddc7562db01cc11eb4`. They must remain in separate stage locations. The formatter reads only its declared manuscript/supplement and verified vector figures; it does not rerun the study.

## Root-owned rendering commands

These are reuse commands, not commands executed by the preparation subtask. First confirm the intended paper revision hashes still match the staging report; later editorial changes require a fresh named stage rather than silently replacing this stage's provenance.

```powershell
$q06Repo = 'D:\Projects\drug_target_agents'
$q06Stage = Join-Path $q06Repo 'data\cache\tether-q06\working-v2'
$q06PdfPython = 'C:\Users\zzric\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$q06Node = 'C:\Users\zzric\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$q06Marker = 'C:\Users\zzric\.codex\plugins\cache\openai-primary-runtime\pdf\26.1026.10807\skills\pdf\container_tools\mark_artifact_operation_started.mjs'
$q06Formatter = Join-Path $q06Stage 'tools\presentation\build_tether_manuscript_v2.py'
$q06Preview = Join-Path $q06Stage 'tmp\pdfs\q06-pages'
& $q06PdfPython $q06Formatter --check-inputs --preview-root $q06Preview
```

The PDF-operation marker already succeeded exactly once before the first authoring attempt. Do not rerun it for this corrected attempt. Root retains its successful invocation; `--marker-confirmed` refers to that actual prior marker, not a new claim.

```powershell
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
