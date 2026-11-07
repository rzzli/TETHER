# B0 registry-content audit: contract and schema preparation

October 22, 2026. This stage implements the first part of the
[reassessment plan](Clinical%20Validation%20Design%20and%20Data%20Feasibility%20Plan%202026-10-22.md):
endpoint contracts, regression guards and retained-schema compatibility. **No
database execution or real cohort selection occurred.** Source-inclusive execution
binding and origin membership remain the next implementation stage.

The [new frozen protocol](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/protocols/registry-content-feasibility-v0.1.json) names
`registry_outcome_measurement_appearance_v1`, with January2025 origin, January2026
endpoint and a separate April2026 sensitivity. It caps origin screening at128 and
selected membership at32, preserves the old order/exclusions, and freezes a90%
January source-state observability threshold. This is an operational coverage rule,
not clinical validation or statistical significance. Prior clinical protocols,
their cutoffs and the inactive next-twelve design are unchanged.

## Implemented behavior

The new [pure contract module](../tools/science/registry_content.py) generates
allowlisted read-only SQL and validates complete envelopes. It projects only
study/version/result-posting dates, result IDs and outcome/group linkage fields.
It excludes efficacy measurements, statistical significance, status and stop reasons.
The generated output explicitly says execution is unauthorized: it has no service,
database driver, network access, automatic retry or general-SQL dispatcher.

For a complete source envelope, consistent linked measurements propose `present`;
zero measurements without conflicting metadata propose `absent_in_snapshot`.
Missing NCTs/tables/mandatory columns, orphan or conflicting links, duplicate source
keys and conflicting dates become record-level `unknown`, even when a valid
measurement exists elsewhere in that record. Incorrect projection, unrequested NCT,
count mismatch, explicit overflow and malformed extraction fail the affected batch.
Internally consistent partial results can count as present, without any claim that
the posted results are complete or concern a primary efficacy objective.

The contrast admits only origin-absent records. January absence→presence proposes
operational1; absence→absence proposes operational0; unknowns remain null. April
cannot fill a January result. Content corrections can create an appearance even
when the recorded public-posting date predates origin: B0 measures snapshot content,
not first-ever public results. Every output keeps clinical labels/probabilities null
and numerical features empty. Pure contract output is not a source-qualified label;
the future runner must validate transport and source ancestry before admission.

## Source inspection scope

Fresh hashes match all three retained `technical-audit.json` identities from approved
earlier source plans. Their technical column metadata contains every required B0
column in `studies`, `outcomes`, `result_groups` and `outcome_measurements`. Schemas
also match the source schemas retained in those earlier request plans. Candidate
and both prior exclusion pack hashes match their frozen references; these files
were hashed without opening new-member records or parsing outcome labels.

Artifacts are under
`data/benchmark/labels/registry-content-20261022/contracts-v1/`: a hash-chained
preparation journal, `source-manifest.json`, the three source schemas, synthetic
unexecuted query templates and copies of the executed helper/contract/test code.
Template IDs are unqueried placeholders, not selected membership. The manifest
explicitly marks full archive/restore revalidation and a new runner as outstanding.
Prior dump/archive references are retained but were **not freshly rehashed** here.
No complete restore qualification, actual SQL execution or result-table coverage
is inferred from schema inspection.

## Validation and remaining work

The initial20 contract regressions pass. A separate agent added six independent
synthetic tests, including exhaustive mandatory-column omissions and source-conflict
cases; all26 combined tests pass. A broader full validation run passed678 tests
before the six peer tests entered discovery; its report remains preserved. The
expanded full validation passes **684 tests with no skips**, required probes,
PowerShell syntax and the packaged dependency-free demo. Independent manifest
review rehashed27 named files, regenerated all three templates and verified the
six-event journal. It reconstructed69 relations/505 columns for origin and71/515
for each follow-up from retained audits. Imported support code is archived in a
separate supplement; the original schema manifest is preserved. The retained
stage acceptance artifact binds these checks. These checks do not validate scientific
outcomes or a real SQL response. No real B0 outcome labels have been generated.

Next implement and test a B0 runner that verifies exact source/restore/code pins,
the candidate order and both exclusion packs, and origin query receipts. It must
reserve fresh outputs, preserve terminal failures/accounting, enforce read-only
transactions and revalidate input bytes before sealing. Then screen origin only,
seal the up-to32-member roster and its complete ancestry, and validate that seal
before any follow-up dispatch. Do not weaken existing twelve-member guards.

The later stage will audit new source states, measure missingness/runtime/memory,
and apply the prefrozen scale/stop rule. Existing72 clinical endpoint labels,
clinical fitting and scoring remain unchanged; the wider project is unfinished.
