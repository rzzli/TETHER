# P05 stage-2 original-only input builder — draft v1

Status: implementation and fictional validation only; actual build UNEXECUTED.
No actual original value records were read while authoring this component.
No reference, expected-fact document, baseline, candidate answer, model call,
network request, or new download was produced. No producer, `src/`, P04 or P04b
file was changed by this component.

The neutral DRAFT is `INPUT-PLAN-DRAFT-v1.json`, SHA256
`4d1cfd81f9755a8f63bc737c3aab71b7756c100982724c482c44a7c03b37814c`.
The builder SHA256 is
`ec91e0bb288f3bf6747e34d05c61fafdae075be2983fa9bcf0a5c19b881afad3`.
The fictional-test SHA256 is
`be3c7c52614f294a3834b3b1ea903215292872749823f9b64e29bb1f61685994`.
The DRAFT pins all 66 active `src/asof` Python files, the unchanged stage-1
helper, this tool, the actual Windows workspace `.venv` Python 3.11.15/Arrow
21.0.0 environment, and the exact 137-original metadata frame. Its status is
`DRAFT` and `actual_build_authorized` is false.

## Root execution gate

Root must independently write `INPUT-READY-v1.json` containing:

```json
{
  "schema_version": 1,
  "status": "READY",
  "scope": "p05_source_only_stage2_inputs",
  "frozen_by": "root",
  "actual_build_authorized": true,
  "plan_sha256": "<exact DRAFT file SHA256>",
  "code_sha256": "<the complete DRAFT code_sha256 object>",
  "environment": "<the complete DRAFT environment object>",
  "row_guard_cutoff_utc": "2026-11-01T07:16:26.101448+00:00",
  "stage1_case_plan_sha256": "<DRAFT authentication.stage1_case_plan_sha256>"
}
```

The quoted objects above are placeholders for actual JSON objects, not strings.
The caller must supply an independent exact READY hash. The tool will not write
or infer that authorization. The public entry is:

```powershell
.\.venv\Scripts\python.exe tools/science/prepare_source_validation_inputs.py --build --output D:\Projects\drug_target_agents\data\derived\preprint-p05-source-inputs-<UTC> --ready-sha256 <exact-root-READY-SHA256>
```

The ignored approved output parent must already exist and contain no links or
reparse components. The prospective leaf must be absent. `RunJournal` reserves
it with an exclusive mkdir; the created leaf is revalidated inside failure
handling. Existing directories are inspection-only, with no resume or overwrite.

All neutral metadata, READY/DRAFT, and all 68 active code files are held under
real Windows stable-read locks through the build. Archived code is checked
against frozen pins. All 137 original payload hashes precede receipt parsing;
all original and receipt hashes, exact identities, catalog roles and receipt
availability precede source value parsing. Original/receipt locks remain held
through original scans and success-artifact hashing. Locks and journal close
must succeed before a success seal is published. A cleanup failure produces a
terminal failure seal where filesystem access permits; partial-file hashing
failures are recorded individually and do not prevent terminal metadata.

## Input and scientific boundary

Stage-1 `selected-case-plan.json` supplies only case routing identities, original
release, and the frozen unit hash. Its exact bytes are authenticated from stage-1
seal hash metadata and copied unchanged. The stage-1 SQLite registry,
`selected-originals`, mapping, coverage, audit reports and other capture values
are never opened. Human responses and descendants, old candidate answers,
private gold, P02 joins, references and descendants are outside the input frame.

The builder freshly reads original target, disease and HGNC records, rechecks
exact approved canonical identity and uniqueness, then scans the entire pinned
100-file GWAS and 25-file credible frame. It uses the unchanged stage-1 native
precision rules, publication interval intersections, independent release/evidence
guards and exposure policy. It additionally applies that same precision rule to
`annotationDate`, which the unchanged core reads automatically. Ineligible
physical duplicates retain only locators and reason labels, never excluded
biological values. Missing dates remain explicit limitations.

Each representable case gets every eligible physical GWAS anchor and every
eligible physical credible row at the exact `studyLocusId`, with one declared
`one_to_many` locus join per anchor. Duplicate and conflicting physical rows
remain separate. This neither establishes composite study/variant identity nor
asserts a gene/action, intervention, causal or clinical effect. The cases are
technical source units, not independent studies.

Credible `beta`, `standardError`, `pValueMantissa`, `pValueExponent` form one
measurement group per physical credible row. Native `studyId` and `variantId`
are requested separately as identity fields, including unknown/null/empty cases.
No numeric availability selection, decimal-p-value conversion, SE calculation,
scale or allele harmonization is performed. Scope action/modality/tissue are
null; namespace versions, units/scales, effect/reference alleles, genome build,
study ancestry and absent study identity carry explicit unknown reasons.

Only the original raw rows, new original mapping proof, full original nodes and
hash/receipt proofs, neutral task, and value-free fact IDs/source bindings enter
the packet. No compiler/reference unknown reasons or expected-value projection
is constructed. A pure length counter proves a conservative 256-KiB output
space bound from native field lengths plus structural allowance. Failure to
prove fit blocks the case explicitly. The unchanged core's pure date, source
binding, field-value and task guards also run before packet visibility.

Core limits remain 64 records, 512 fields, 32 joins and 1 MiB task bytes. Invalid
native date forms, finite-number/type failures, scope mismatches, missing mapping
authority and unsupported widths retain the case as blocked coverage, with no
coercion, replacement, truncation, sharding or dropped candidates. Zero credible
matches create no measurement slots and no measurement coverage/pass claim.

`neutral_metadata` remains validated routing/config outside `InputGraph`; it is
never relabeled as an allowed raw graph role. The `Snapshot` uses the actual
approved E: original root, all original dependencies and the frozen information
cutoff. Later computation timestamps do not change source availability. Each
packet names all 137 original parents plus the input plan and exact neutral
selected-case plan. Generation and the later reference branch must each derive
their values directly from originals in separate executions.

## Retention and limits

The exclusive output contains per-case packets, unchanged neutral case plan,
exact receipt archives, recipe archives covering neutral configuration and all
active code, original snapshot/proofs, new lineage, technical coverage/exclusion
locators, cooperative resource counters, hash-chained journal, and a success or
failure seal. Full original-frame provenance is retained even for files with no
selected match. Total compressed input is capped at 4 GiB and 137 files; build
time at 1200 seconds; total output at 512 MiB; each packet at 64 MiB. Native batch
size is 8192 rows. Logical hash/scan byte counters, batch Arrow bytes and sampled
process RSS are reported. Physical I/O is explicitly unmeasured; there is no hard
OS watchdog. A 100,000 matching-row safety bound per case fails the build rather
than silently retaining an incomplete inventory.

## Fictional verification

The command below passed 40 tests, with no failures, errors or skips:

```powershell
.\.venv\Scripts\python.exe planning/review-assets/preprint-p05-20261031/test_prepare_source_validation_inputs.py -v
```

Coverage includes a complete five-original fictional execute with real Windows
path validation, locks, receipts, Arrow scans, journal, source immutability and
seal; real row-group/row-in-group locators; physical duplicate/conflict retention;
missing identity and explicit unknowns; future duplicate and annotation exclusion;
publication precision conflicts and unsupported native date formats; native
numeric types; exact canonical mapping failures; Windows receipt separators;
role/hash/freeze gates; task and aggregate wire bounds; exclusive reservation;
and injected lock-exit, journal-close, journal-failure-append and partial-hash
failures. AST checking confirms no reference/compiler/scoring/capture calls.

Independent pre-execution review is GREEN: an independent agent reran all 40
fictional tests, reproduced the exact metadata-only DRAFT, and checked all 68
code pins, with no remaining review blockers and no actual value reads. Root
must freeze current exact bytes and alone orchestrate the actual original build. Reference
construction, baseline formatting, grading and technical contrasts remain later
phases.
