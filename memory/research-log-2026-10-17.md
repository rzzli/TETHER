---
name: research-log-2026-10-17
description: Five-date AACT review, complete selected literature release and regional genetics corrections
metadata:
  type: project
---

# Research log — October 17, 2026

Objective: execute the bounded long-session queue after the user supplied the three
requested AACT archives. Preserve the AsOf/Virtual Biotech-inspired separation of
agent evidence and evaluator outcomes, immutable originals, public-data scope and
$0 provider spending. Completion is based on evidence, not consuming twelve hours.

Sources: exact-NCT Europe PMC discovery for 24 frozen trial representatives,
primary manuscripts and dated sponsor/registry disclosures; user-supplied AACT
archives; Open Targets 25.09/22.11 publisher manifests/configuration; HGNC historical
archive and MONDO/EFO release metadata; BLUEPRINT methods and Ensembl phenotype
coordinates; original DICE and OneK1K descriptions. This was targeted source
validation, not a new broad literature survey or citation-network reconstruction.

Compared with the earlier two-snapshot audit, three intermediate observations narrow
registry-state intervals but do not identify therapeutic outcome events. Exact arm,
genotype, endpoint and reporting-lag distinctions explain why a trial-status classifier
cannot stand in for the proposed program-level benchmark. One incompatible trial
identifier on a retrospective paper is retained as a real linkage-conflict canary.
AI-assisted review is unblinded development evidence, not independent scientific gold.

Compared with the earlier incomplete T6 manifest, 65 additional verified inputs add
14,640 case-level literature observations without changing prior observations. The
full input set exposed the 64 MiB single-packet limit. An explicit bounded layout
retains all records under the existing v2 artifact contract; the failed build remains.
Ten source-verified dossiers, 20 distinct audited original rows, further new-literature
row checks and 149 passing tests are retained. No clinical probabilities were added.

Compared with the original one-megabase IL6R technical pilot, source-defined full-cis
coverage is two megabases and yields 2,979 QC variants. An independently recalculated
LD subset agrees numerically. This fixes coverage, not causal validity: provider MD5,
external LD, cohort overlap and missing GWAS N/EAF remain unresolved. DICE/OneK1K
replication candidates are scoped by assay/context; ancestry and access qualifications
prevent treating their published hit tables as complete compatible regional inputs.

Historical Open Targets 22.11 samples/upstream inputs now have publisher hashes and
configuration provenance. All 24 target identities agree with the reconstructed HGNC
archive, while only 42 of 150 condition occurrences have exact ontology candidates.
None are adjudicated indications. Modern object timestamps do not prove historical
availability. Source challenges and unavailable full texts remain explicit.

See [[Clinical Long Session Progress]], [[Full Cis Genetics Revision]] and the sealed
local session for exact paths, versions, hashes, failed attempts and resource measures.
Next: origin-only program/arm/indication definitions, a specified outcome estimand,
event/censoring adjudication and independent eligible counts before power or training.
No additional user download is needed immediately; request narrowly identified sources
only if public alternatives cannot resolve a material ambiguity. Current status is
recorded in [[project-goals]] and [[data-acquisition-plan]].

## Planning reconciliation after the Claude review

Read [[Claude Review and Plan_claude10172026]], the memory index/current goals,
relevant evaluator code, retained sizing/validation assets and catalog metadata.
Updated [[Updated Project Plan 2026-10-17]] in place; did not create another sealed
micro-step bundle. Current priority is local preservation and registry-scale sizing,
with a proposed v0.4 registry-observable tier and strict v0.3 retained for audit.
The 15-case qualification queue becomes an audit subtask, not the T1 feasibility gate.

Corrected the summary: all 24 cases were accounted for, but only P01/P24 authored
facts were evaluated. The review assets report 173 full-suite tests passing with no
skips; 149 remains the dated long-session result. No full-suite rerun this session.
Spot-checked Parquet metadata: OT molecule 18,119 rows; mechanism 6,332 rows. The
raw schema differs from normalized catalog fields, so the evaluator mapping adapter
still needs validation. Catalog restore/download prose remains queued for repair.

Accepted the shift toward scale and bounded selection, with corrections: crude
485–659 pair matches are not adjudicated counts/bounds; an EXPERIMENTAL arm can
contain background/rescue drugs; strict Tier B is not a perfect gold reference and
recall needs independent ascertainment of sampled non-transitions. Model cutoff
alone does not prove no contamination. Official current provider pages confirm
Sonnet 4.5's Nov 30 retirement and current-lineup June 2026 cutoffs; individual legacy
model pages were inaccessible in this check, so no legacy candidate was selected.
October 2025 plus 12 months needs an origin version and October 2026/reporting-lag
coverage; January 2026 cannot serve as that endpoint or reconstruct a locked origin.
Last-Modified metadata alone does not prove historical public availability.

This was planning/memory correction only: no code/catalog mutation, new cohort,
endpoint implementation, commit/push, backup transmission, database restart, model
call or paid activity. Independent human adjudication and publication claims remain
separate gates. Concrete remote destinations/budgets are needed only when reached.

## WP0 local preservation and v0.4 freeze executed

Committed the recoverable October 17 code/evidence-anchor state as
`f36f548d2d1459d39a14346305f83c4d045d2e39`. Added a constrained status-correction
report kind to the existing catalog writer, with two regressions covering policy/
science preservation and rejection of promotion or tampered evidence. Corrected
AACT restoration prose and the idle/incomplete ChEMBL/colocalisation observations.
Transport queues/receipts, workers, scientific-validation flags and dated acquisition
snapshots were unchanged. CRLF hash-bound bytes were retained using Git whitespace
attributes instead of reserializing old receipts or archived evaluator code.

Full validation passed: 175 tests, zero skips/failures/errors, required probes,
PowerShell syntax and installed-wheel demo. The frozen evaluator-only protocol is
`planning/protocols/registry-sizing-v0.4.json`, SHA-256
`5757670106359cbd007cc1dd9ed0b0acad44086852e81f4b2dd6494d79ac51cd`.
It fixes the ACTUAL-start sizing estimand, origin role/stage rules, uncertainty,
alias/regimen handling, phase edges, ascertainment cutoff, clustering, audit sampling
and power scenarios before registry enumeration. No new scientific labels/counts.

E: local recovery copy:
`E:/projects_data/drug_target_agents_data/backups/wp0-20261017-f36f548/`.
All 1,811 files / 719,427,970 source bytes were archived and rehashed. The 21-file
sealed milestone passed a real restore; the Git bundle cloned at the same checkpoint.
The archive is 72,528,636 bytes. Off-machine backup, remote/push and hosted CI remain
open. Bulk raw archives, database pages/credentials and large external scientific
payloads are outside this local copy; do not claim complete disaster recovery.

See `planning/review-assets/wp0-20261017/README.md` and
`data/manifests/public/2026-10-17-wp0-local-checkpoint.json`.
Next: read-only registry origin/follow-up extraction and conservative drug-role/alias
mapping under v0.4. No database restart, data download, model call, paid activity or
external transmission occurred in this step. Do not repeat the completed freeze.

## Registry-scale sizing, source audit and private hosting

The user activated the two-track completion goal. GitHub CLI sign-in was completed
locally as rzzli. Created/pushed a private repository, ran all four hosted CI jobs,
and tested actual downloaded baseline recovery assets: all 1,811 archived entries,
a sealed milestone and a Git bundle clone/fsck passed.

Under the already-frozen v0.4 protocol, extracted five existing restores read-only,
reusing three completed frames after hash checks. Two retained query plans exposed
quadratic child aggregation; controlled cancellation and a fresh set-based/session
hash-join extraction completed the remaining sources. All owned servers stopped.
Final source frames: 232,722 observations, 196,940 trial IDs, 719,992,409 bytes.

Final cohort: 4,419 programs; 27 recorded-start programs, 41 unresolved transitions,
4,351 no recorded transition. 37 unique recorded events, 19 positive dependency
components, ten positive mapped targets. 1,073 programs lack target mapping.
No training/negative/censoring labels. Fixed literal condition rules retained;
no outcome-selected synonym merging or scientific validation claim.

Source review found narrative companion-drug/cocktail omissions, later unresolved
roles, contradictory dates/withdrawals and an audit-empty-lookup counter. Added
regressions and held those ambiguities. Original-row checks cover every included
program and 98 links, rehashing 2,497 rows. Final 185-program stratified sample has
65 candidates and 120 controls; 33 AI narrative notes cite 88 distinct rows. No
independent scientific annotations, recall, precision or per-case-time inference.
The three Phase 4/estimated/comparator leads in an earlier diagnostic control sample
are not eligible events; the final deterministic sample changed with corrected
membership and has no relaxed leads. Both are limited searches, not recall evidence.

Canonical workspace `registry-sizing-20261017T202655Z/cohort-v04` and `audit-v04`;
previous builds retained as diagnostics. Final build: 141.95 seconds, ~251 MiB peak
working set. The registry report, updated roadmap and public manifest bind results.
Private final-milestone recovery/CI evidence is retained in the milestone index.
Next: condition/clinical-scope sensitivity freeze, prior-risk/population adjudication,
then dependency-aware power. No provider-model calls, training, new downloads or
changes to the original downloader/stopped periodic monitor.

Registry closeout: all four hosted jobs passed at `f57c448`. Downloaded the private
541,153,875-byte evidence ZIP and Git bundle. All 146 files / 2,842,669,284 source
bytes restored/rehashed; code clone/fsck, SQLite integrity (232,722 observations),
and the 21-file milestone seal passed. The restore helper uses immutable SQLite
mode to avoid mutating sealed WAL shared-memory sidecars. Final full local validation
passed 186 tests without skips/failures/errors, required probes and installed-wheel
checks. Separate prior-risk proofs explain the three unresolved programs without
incident event IDs. The final report retains scientific limitations and next gates.


## Ordered execution closeout (October 17 local / October 18 UTC)

Followed the user's ordered TODO. The v0.5 fixed-cohort scope audit and corrected
v0.2 conditional power study passed; base proxy-size power remains 6.2-46.7% under
assumptions, below target. Froze a local development/conditional clinical protocol
with immutable September 2024 Qwen weights, verified January 2026 archive CRC/hash/
TOC without querying outcomes, and retained OT24.09 release/layout proof only.
No public registration or clinical lock was established.

Implemented bounded loopback local-model selection, payload/response/source binding,
truncation rejection, exact offline replay and lossless shared scientific fields.
Ten original and three focused dossiers source-verified; 229 tests and four hosted
Windows/Linux jobs passed. Original single-candidate behavior is a retained diagnostic;
lossless transport fits 66 versus 22 candidates with all fields reconstructing exactly.
All model calls were local; provider spending $0, predictions null, features unmeasured.

The conditional genetics/scoring gate was reassessed: 38 full-cis files rehashed,
4,096 independent LD checks agree within 3.44e-15. Scientific qualifications, source
exceptions and zero clinical training labels prevent feature derivation/training.
Task 5's no-go branch is documented, not presented as trained science. Task 6 is
blocked by missing independent outcomes/negative-or-censoring reference, qualified
cohort/scoring and power. Tasks 7-8 remain unstarted; stop-on-blocker rule applied.
See [[Ordered Execution Progress 2026-10-17]], [[Local Model Specialist Pilot 2026-10-17]]
and TODO.md. Earlier model/data-access/milestone next actions are preserved history.
The biomedical downloader, originals and stopped periodic monitor remain untouched.
