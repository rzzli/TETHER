# P05 independent original-source reference wrapper

Status: DRAFT implementation and fictional checks only. No actual original source
values or generation packets were read by this implementation task. No actual
P05 reference build is authorized by this document or the DRAFT plan.

`tools/science/build_source_validation_references.py` requires explicit `--build`,
a separately root-authored `REFERENCE-READY-v1.json`, and its independently
supplied exact byte hash. READY must bind the exact DRAFT bytes, all active code
pins, environment, neutral configuration and original-frame descriptor at cutoff
`2026-11-01T07:16:26.101448+00:00`. Later build timestamps do not establish older
information availability. The exclusive output parent is
`data/benchmark/gold_evidence/preprint-p05-references-UTC` and must already be
git-ignored. The actual raw root remains the owner-approved E: data root.

The allowed neutral task directory is
`data/derived/preprint-p05-neutral-tasks-20261101T075541Z`; its seal byte hash is
`5bf827df9921a01712d9739d7d04f59e8b0aa3554a9ebc9eaf87d6e240aadace`.
Only its seal, task definitions, unchanged source snapshot and selected-case plan
are opened. Origin packet paths in that seal are never followed. That seal binds
the already sealed source-generation batch; it supplies configuration and no
measurement expected values. Neutral configuration remains outside InputGraph.

The wrapper has an independent author and performs separate original rereads.
This is provenance isolation, not algorithmic independence: it shares the pure
stage-1 mapping/precision-date functions and the source-input builder's original
scanner, eligibility, normalization and task-construction helpers. All shared
dependencies are pinned and archived with all 66 `src/asof` Python files and the
wrapper. The existing `compile_reference` and `verify_reference` are unchanged.
An independent audit that reconstructs tasks and literal facts directly from
originals without these producer helpers remains separate evidence; this wrapper
does not establish that audit or a fully independent implementation.

Every build admits all 137 original payloads and exact receipts before source
value reads, checks catalog roles and the frozen source graph, rereads original
HGNC/target/disease mapping tables, and scans the complete selected GWAS and
credible candidate frame under real Windows stable file locks. Publication
precision intersections, evidence/release guards, annotation-date guards,
canonical uniqueness and exposed-symbol exclusions precede the compiler.
Physical duplicate rows remain separate. Each GWAS anchor uses an exact locus
`one_to_many` join to every eligible physical credible row. Native study/variant
identities remain separate; beta is a source study/variant statistic. Units,
ancestry, effect/reference allele, genome build, action, modality and tissue are
unknown where the fixed task does not literally supply them.

The independently reconstructed task and snapshot must exactly equal the
unchanged neutral definitions. All twelve fixed selected technical source units
remain present. A date/API, finite-numeric, common-wire or fixed-cap failure is
an explicit blocked disposition; no rows are truncated and no case is replaced.
The core limits remain 64 records, 512 fields and 32 joins. There is no date
coercion, synthetic identity, computed p-value, inferred allele/build or new
clinical, causal, independent-study or adjudicated-gold claim. Outputs are always
`evaluation_only`, `agent_visible=false`, `adjudicated_gold=false`.

`verify_p05_references` requires an independently retained wrapper fingerprint
and READY byte hash. While holding stable locks over current reviewed code, it
checks retained exact DRAFT/READY bytes, active code/environment policy, archived
neutral seal/tasks/snapshot/selected-plan/catalog/frame/acquisition bytes and all
authoritative redundant manifest bindings before opening originals. It does not
reopen a live READY or live catalog path. Ordered original/receipt declarations
are compared with fresh admitted proofs before row parsing. It then repeats the
same mapping, candidate inventory, exclusion/date guards and normalization, and
calls unchanged base verification. Base verification alone is insufficient.
This implementation verifies only its exact reviewed code/environment; an older
run requires its matching reviewed implementation. Archived code is not executed
dynamically, and neither mode constitutes scientific validation.

The recipe list is explicitly descriptive archive inventory. Standalone source
replay does not authenticate archive files; the retained output seal does that.
The exact retained authorization/query/catalog context and frozen code pins are
the standalone verifier's authorities. The output seal requires a terminal
`build_completed` record binding that seal and absence of `failure-seal.json`.
Stable-lock cleanup and journal close happen before success-seal publication.
Failure journaling, journal close and failure-seal publication are attempted
independently, including cleanup failure; partial directories are inspect-only.
Declared build time must be a UTC timestamp between the information cutoff and
the current replay time.

Fresh compressed originals are bounded at 4 GiB, output at 512 MiB, and the
cooperative deadline at 2400 seconds. Resource reports retain elapsed time,
sampled process RSS/Windows peak working set, wrapper logical hash/scan bytes,
and completed base-API hash-pass bytes derived from retained source proofs.
Partial hash work in failed base calls is explicitly unmeasured. Physical I/O
bytes remain unknown. Provider cost and model calls are zero. These are
cooperative checks rather than an OS watchdog.

Fictional checks use the actual unchanged compiler/verifier, actual Windows
sharing locks and actual ignored production output parent. Full execute tests
substitute only trusted fictional configuration; they do not bypass reservation,
path validation, locks, receipt formats, core compilation or verification.
Fixtures have native backslash receipt paths and exact receipt-byte archives.
Checks cover multiplicity, future and precision-date exclusion, annotation replay,
unknown/zero data, finite/type QC, mapping/scope/role/ancestry rejection, fixed
caps, wire strings, task/READY/context/code/environment tampering, authoritative
manifest consistency, no generation-output reads, complete success and terminal
lock/journal cleanup failures. All fixture directories are removed only after
their resolved paths are checked under the intended fictional/production roots.

Validation command:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s planning/review-assets/preprint-p05-20261031 -p test_build_source_validation_references.py -q
```

Final implementation check: 41 fictional tests passed in 22.793 seconds. The
independent peer review and any actual source build/audit are separate records.
