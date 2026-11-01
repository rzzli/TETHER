Historical checkpoint: references were pending at this stage. The [later source-reference completion](<Project Progress Reassessment 2026-11-01 - Source Reference Completion.md>) is current.

# Source registry completion and remaining validation work

1 November 2026, America/Los_Angeles. **The prospective source registry is built
and independently verified. Twelve source-only input packets are also sealed
and independently verified; the reference/experiment freeze remains unfinished.**
The paper and wider clinical programme are incomplete. This is a review of the
new artifacts and study pipeline, retaining earlier framework acceptances rather
than claiming a new full-repository audit or full-suite pass.

## Verified registry and resources

The [v3 protocol](review-assets/preprint-p05-20261031/REGISTRY-READY-v3.json)
was committed at `2f138db` before source-value scans. It fixes 137 originals,
2,866,248,239 compressed bytes, a contemporary information cutoff of
1 November 2026 at 07:16:26 UTC, canonical identifier requirements, known
development exclusions and an identity-only hash selection rule. No number,
measurement availability, generated performance or bespoke response selects a
case. Other project exposure remains unknown, not certified fresh.

The successful output is
`data/derived/preprint-p05-source-validation-20261101T071713Z`. It registers
every GWAS physical row: **1,753,850 total, 1,681,738 policy-eligible, 72,112
excluded**. These are data-policy counts, not validated biological associations
or independent studies. Exclusion reasons can overlap. No duplicate or missing
physical/evidence/unit identity was observed in this frame.

Twelve eligible units were selected by the frozen identity hash, with no
post-join replacement. Every selected unit has one GWAS row and one matching
credible-set row at the exact native locus key. All 25 credible files and
2,862,043 rows were scanned. A matching locus key does not resolve cross-source
study/variant identity or establish a causal gene relationship.

The [main independent audit](review-assets/preprint-p05-20261031/REGISTRY-AUDIT-v3.json)
and [metadata supplement](review-assets/preprint-p05-20261031/REGISTRY-AUDIT-CAPTURE-METADATA-v3.json)
pass **789 checks, zero findings**. Independently authored replay covers every
GWAS identity/locator/eligibility/hash, all credible selected matches and
deterministic selection, all 137 original/receipt proofs, roles, chronology,
terminal artifacts, and 59 distinct selected/mapping source rows. The checked
eligibility rules are the frozen protocol's rules, not universal scientific
validity of every source field. Read-only Git verification matches 69 frozen
code/plan/READY files to the pre-run commit.

Production took 294.406 seconds and 543,244,288 bytes process-lifetime peak
working set. Output before report/seal was 1,508,419,762 bytes; selected Arrow
data totaled 4,600 bytes. The separate audit took 102.094 seconds plus an
8.64-second supplement; main audit process peak was 604,225,536 bytes. Physical
I/O, whole-machine memory and total platform cost remain unmeasured. These
figures do not establish capacity for the full acquisition inventory.

Two earlier attempts remain recorded. V1 rejected its intended new output leaf
before reservation. V2 completed payload hashing but rejected native Windows
receipt path spelling against forward-slash metadata before parsing records.
Regression-first corrections preserve both original protocols and failure
records. V3 changes path compatibility and initialization only; scientific
selection, projections, eligibility and budgets are unchanged. Original files,
transport receipts, the old worker and stopped periodic monitor are untouched.

## Scientific limits and input separation

Among the twelve credible rows, beta is missing in 1/12, standard error in
7/12 and sample size in 10/12. Cross-source native study/variant agreement
remains unresolved for all twelve. Units, allele orientation, ancestry, genome
build and independently verified study/cohort context are not supplied by this
study projection. These inputs support native field reporting with explicit
missingness; they do not qualify MR, intervention direction, gene/action effects,
clinical probabilities or independent-cohort inference.

Stage1 raw captures and mapping/coverage audit products are evaluation-only,
unqualified and hidden from future generation. Neutral routing contains only
original-plus-plan ancestry. Both source inputs and references must reread
eligible originals; neither can consume quarantined capture values. Complete
parent lineage and current download bounds do not establish first-public or
historical annotation availability.

## Current input and reference stage

The [input protocol](review-assets/preprint-p05-20261031/INPUT-READY-v1.json)
and builder were committed at `98346a9` before the original-only input build.
Forty fictional tests and independent review pass, using real path, lock and
journal APIs. Stage2 additionally guards native annotation dates, keeps all
eligible physical locus matches and enforces existing representation limits.

The build `data/derived/preprint-p05-source-inputs-20261101T074942Z` completed
with twelve packets and zero blocked cases. It creates no reference, baseline
output, model call or biological conclusion. The [independent input audit](review-assets/preprint-p05-20261031/INPUT-AUDIT-v1.json)
passes **1,238 checks, zero findings**. It freshly verifies all 137 original
payloads/receipts, 77 exact recipe archives and 68 code pins, independently
reconstructs all twelve tasks and 180 value-free fact bindings from original
rows, and checks every neutral projection byte for byte. Production took
42.125 seconds; sampled producer RSS is unavailable. The separate audit took
7.078 seconds with 299,233,280 bytes process-lifetime peak working set. These
costs remain separate from the earlier registry build and audit.
[Value-free task definitions](review-assets/preprint-p05-20261031/NEUTRAL-TASKS-v1.json)
were projected and sealed before reference construction. The new reference
builder receives those query definitions and original sources, not packet row
values, producer audit values or prior answers.

## Whole project status and ordered next steps

| Workstream | Current disposition |
|---|---|
| P01–P04 / R01–R10 | Earlier bounded engineering and exposed studies retained; P04 negative: literal clean 2/2, model clean 0/2 each; 2,216 source-inclusive audit checks pass |
| P04b | Two fictional calls yield one pass and one malformed result. Model branch closed; no further prompt retries or model scale |
| P05a | Source registry and independent full replay complete; data-policy eligibility and missingness are explicit |
| P05b / R11 | Original-only inputs and independent replay complete; all twelve packets and 180 fact bindings checked. Technical fidelity, not biological validation |
| P05c–P05d / R11 | Original-derived references and actual experiment/analysis freeze unfinished. Twelve source units are not twelve independent studies |
| P06–P07 / R12 | Frozen technical experiments, controlled ablations and reproducible final analyses unfinished |
| P08–P10 / R16 | Manuscript, bibliography/figures, lawful portable release, exact-release validation and final package unfinished |
| R07–R09 historical routes | R07 six complete responses/zero contract passes and native FAILED/INCOMPLETE_TIMEOUT remain unchanged |
| R13–R15 and original wider scope | Clinical/scorer/MR/full Virtual Biotech/T2–T5/H6 conditional work remains separate. Keep 65 missing interpretation inputs, 36 unqualified labels, 17/32 observable primary registry states and 0/12 jointly ready packages distinct |
| HR1–HR4 | Retired; no external expert input. Prior responses and all response-aware descendants remain excluded |

Next: freeze and execute the independent reference
builder with source-inclusive wrapper verification. The wrapper must replay
normalization, precision-aware dates and complete row inventories as well as the
unchanged core verifier; base verification alone does not cover the newer guard
policy. Unsupported date forms or limits stay explicit case failures, with no
replacement. Then lock actual clean/fault/control contrasts and denominators
before producing baseline outputs or fault results. Keep biological truth and
mechanical source fidelity separate throughout the manuscript and release.
