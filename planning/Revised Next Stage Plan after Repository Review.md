---
title: Revised Next Stage Plan after Repository Review
date: 2026-10-12
timezone: America/Los_Angeles
status: stabilization-implemented-feasibility-gated
tags:
  - TETHER
  - planning
  - feasibility
  - v03
---

# Revised next-stage plan

Implementation update, October 12: A–D have been implemented; validation results and
remaining limits are recorded in [[Stabilization Completion and Feasibility Gates]].
The canonical registry and scoped catalog update now exist. [[Feasibility Gate Decision]]
records the incomplete scientific gate and prepared T6 review protocol. The original
starting-point observations below describe the state when this plan was written.

The next milestone should establish a reproducible repository and a feasible scientific evaluation before expanding the agent architecture. Close the v0.2 record, repair the verified maintenance/test gaps, then run a bounded feasibility phase. A live model adapter follows a defined evaluation and spending decision; it is not evidence of scientific progress by itself.

This plan responds to [[Full Repository Review and Verified Findings_claude10112026]] and supersedes the forward-looking sequencing in [[Project Audit and v0.2 Completion]] and [[Framework Code Review and Next Stage Plan]]. Original proposals and the independent review remain unchanged. This revision changes planning and status documentation, not runtime code, transport state or model spending.

## 1. Starting point: what is actually complete

The canonical local pilot is `runs/v02-realdata-20261012T015124Z/`, built from `data/derived/v02-contemporary-pilot-20261012T014305Z/`. Its reports now establish:

| Deliverable | Retained result |
| --- | --- |
| Input selection | 2,141 receipt-verified files; 3,752,440,123 bytes; OT 25.09 plus HGNC 2026-10-10 |
| Transformation | 14,940,949 physical evidence rows scanned; 14,207 matching accepted source rows; 16,914 case records |
| Case pack | All ten prescribed T6 hypotheses finalized; no blocked canonical identifiers |
| Verification | All ten reports record source-inclusive semantic verification, sealed request files and matching runtime code fingerprints; saved receipt anchors matched during this replanning check |
| Source review | 20 distinct original rows across all ten cases, with mappings/context/missingness checked; this is technical fidelity review, not independent biological adjudication |
| Resources | Build 255.25 seconds; peak 1,150,431,232 bytes; largest packet 60,883,175 bytes; pilot including verification/audit 242.609 seconds |
| Pilot memory | 1,544,667,136 bytes for the parent verification/audit process; not an aggregate parent-plus-child peak |
| Tests | Latest retained full run: 100 tests passed; ten current review probes passed; dependency-free demo verified |
| Scientific boundaries | All real probabilities null, real prediction features empty, provider spending $0; 65 missing inputs remain |

See the dossier index (local artifact: `runs/v02-realdata-20261012T015124Z/README.md`), pilot report (local artifact: `runs/v02-realdata-20261012T015124Z/pilot-report.json`), source audit (local artifact: `runs/v02-realdata-20261012T015124Z/source-review.json`), build report (local artifact: `data/derived/v02-contemporary-pilot-20261012T014305Z/build-report.json`), and [[data/manifests/public/2026-10-11-project-checks.json]]. These are development artifacts, not ten independent clinical outcomes. ERBB2 and PCSK9 reuse source evidence across different hypotheses.

The original incomplete snapshot and first superseded run remain retained. The later failed pilot exposed a ledger-output size issue: claim envelopes expanded a valid packet beyond 64 MiB. That was fixed and tested using a separate 256 MiB output-ledger bound; the evidence packet limit remains 64 MiB. The canonical retry above completed after that fix. Rebuilding these ten cases again is not a next-stage prerequisite unless code or input changes invalidate their guarantees.

Administrative closeout is still incomplete: the generated-product catalog status remains `planned`, README/framework status needs alignment, and there is no versioned canonical-run registry. The previously pending completion-report section was updated from retained artifacts during this replanning turn. Do not equate the remaining documentation gaps with an absent real-data build.

## 2. Disposition of the independent review

| Review finding | Revalidation and planned response |
| --- | --- |
| 1 — No version control | Confirmed. Highest-priority repository correction: initialize locally, audit the proposed tracked files, and create a baseline using an established author identity. A remote/publication is a separate decision. |
| 2 — No live model backend | Confirmed, but intentional in the approved offline v0.2 milestone. The extractive backend is a useful control. Add one bounded model adapter only after defining what it must improve and how that will be measured. |
| 3 — No real probabilities | Confirmed and intentional. Do not remove T6 abstention to manufacture a prediction deliverable. Real probabilities require a separate T1 cohort, feature derivations, trained/calibrated scorer and held-out evaluation. |
| 4 — No CI | Confirmed. Add a clean-checkout validation entry point and CI configuration; hosted enforcement only exists after a remote/runner is configured. |
| 5 — Scientific blockers unresolved | Substantively accepted. Promote historical restoration, endpoint/model chronology, independent case counts and accessible genetics into explicit decision gates before major expansion. Past 404/403 responses are failed access probes, not proof that a dataset is unavailable. |
| 6 — T6 program validation | Partly accepted; do not copy all T1 rules into T6. The approved v0.2 design explicitly kept active-phase/endpoint rules specific to T1. A withdrawn program can be valid dated T6 context. Fresh probes also accepted an empty program ID and mapping confidence 2.0: these are shared structural defects. Resolve `eligible_since` semantics explicitly; see work package C. |
| 7 — Dated output overwrite | Confirmed by source inspection. Generate immutable timestamped acquisition/inventory reports with explicit output arguments and no-clobber defaults; catalog references must point to the actual report. |
| 8 — Monitor batch-name patch | Confirmed as brittle code, but batch IDs and queue basenames need not be identical. Read the explicit queue/state identity instead of renaming IDs blindly or substituting strings. Keep monitoring stopped. |
| 9 — Prose replacement for status | Confirmed. Use structured status/blocker fields and separately rendered prose; detect unsupported legacy formats instead of silently succeeding. |
| 10 — Hardcoded preparation paths | Confirmed. Parameterize project root, raw root, queue paths, catalog input and output manifest. Preparation must be read-only with respect to the catalog and must not overwrite a frozen manifest. |
| 11 — Demo generation prerequisite | Qualify: v1 fixtures already ship in the repository, so a clean checkout need not execute `build_demo.py` first. Add explicit input/output arguments and complete prerequisite validation before any write; never automatically regenerate preserved v1 artifacts. |
| 12 — Optional probe can pass overall | Confirmed. Use explicit pass/fail/skip states and a required-check policy; required missing fixtures fail. Optional local archival checks remain visibly skipped and cannot count toward required coverage. |
| 13 — Multiple catalog writers | Confirmed. Remove catalog mutation from input preparation. Establish one validated update entry point, field ownership and atomic/concurrent-write protection. |
| 14 — Run discoverability | Confirmed. Add a versioned sanitized registry pointing to the canonical run and retained failure/supersession sidecars outside sealed output sets. Do not alter receipt-bound bytes. |
| 15 — LICENSE placeholder | Reclassify. The literal placeholder is also present in the official Apache-2.0 appendix; its presence alone is not proof of a malformed license. Preserve standard license text; add a separate project attribution only after the actual rights holder is established. |
| 16 — Conditional legacy test | Confirmed. Replace machine-local `runs/` dependence with a small portable, versioned v1 golden verification fixture. Split legacy execution rejection from receipt-compatibility coverage so neither silently disappears. |

The license comparison is against the [official Apache-2.0 text](https://www.apache.org/licenses/LICENSE-2.0.txt), whose appendix contains the example notice. This is a text/attribution correction, not a determination of ownership.

The reviewer correctly withdrew the “silent pyarrow skip” claim. Keep explicit skip reporting for a core-only install, and require the full ingestion test job to have no unexpected skips.

Two additional planning corrections follow from the source review:

- `Sync-DownloadCatalog.ps1` also overwrites the global scope with “scientific ingestion ... not [implemented]” and emits `parsed_products=0`. Its update permissions must exclude unrelated normalization/scientific status, or future syncs will undo accurate closeout.
- Preserve the original hypothesis definitions: **H3 is the popularity-confounding analysis**, and **H5 is dossier quality/error/cost**. They must not be relabeled as chronology and generic multimodal integration. Temporal validity is a cross-cutting prerequisite.

## 3. Work packages and acceptance gates

### A. Close the v0.2 record and establish version control — 0.5–1 engineering day

1. Update the completion report, README and current memory from the canonical retained artifacts. Link the 20-row audit and measured resource report; distinguish technical verification from scientific review.
2. Add `planning/run-registry.json` with relative paths, run/build IDs, receipt anchors, artifact hashes and states (`canonical`, `failed`, `superseded`, `incomplete`). Record the unknown cause of the oldest incomplete build honestly.
3. Add explanatory sidecars to abandoned directories without editing sealed files, deleting failed work or rewriting old receipts. Registry selection must be explicit, not “newest directory wins.”
4. Initialize a local Git repository. Inspect the candidate file list and secret/private-path scan before the initial commit. Verify ignores for `.venv/`, `runs/`, raw/reference/derived payloads, benchmark answers, private manifests and credentials. Include source, tests, docs, lockfile, catalog and sanitized metadata only.
5. Use the configured, confirmed author identity. Do not invent a copyright owner or publish a remote as part of this work package.

**Gate A:** A fresh checkout identifies the canonical pilot through metadata even when bulky local runs are absent; registry hashes match local retained artifacts when present; the baseline commit contains no bulk/private payload. Catalog count remains 83 providers / 178 products. Scoped collection/parsing status is corrected through work package B's single update path.

### B. Make supporting utilities reproducible and single-owner — 1.5–2.5 days

- Replace catalog side effects in `prepare_v02_inputs.py` with a read-only manifest builder. Require explicit roots/queues/output or documented project-relative defaults. Reject an existing output by default; keep the existing frozen manifest byte-for-byte unchanged.
- Introduce one catalog-update entry point. PowerShell transport inspection emits a proposed acquisition report; it does not rewrite the full catalog. The updater validates IDs, allowed fields, roles, references and report hashes; locks updates, checks the expected prior catalog hash, writes atomically and records provenance. Human-reviewed policy/dependencies/licensing cannot be overwritten by a transport status sync.
- Keep acquisition, parsing, technical QC and scientific validation separate. Record `tether_normalized_packets` as collected/parsed only for the retained ten-case release; mark independent scientific validation `not_run`. Scope other generated products or source parsing accurately instead of claiming full provider coverage.
- Use explicit paths and UTC timestamps in report filenames; retain the user-facing reporting timezone in metadata. No-clobber publication also applies to source-size inventories. Same-day repeated execution must preserve both records and consistent catalog links.
- Resolve monitor identity from explicit batch/queue metadata. Add appropriate PowerShell version declarations and validate them. Test with temporary queue/state files; do not start monitoring or change the active downloader.
- Give demo utilities argument parsing, complete input preflight and fresh-output behavior. Errors should identify missing fixture inputs before leaving partial output.

**Gate B:** Two concurrent updates cannot lose each other's changes; stale proposals fail explicitly. A transport update preserves generated-product parsing/QC and policy. Preparation leaves the catalog and frozen manifest unchanged. Repeated report generation cannot overwrite history. All tests use local fixtures and make no provider calls.

### C. Clarify program contracts and make required tests unavoidable — 1–2 days

Adopt a written distinction between **program context** and **T1 at-risk eligibility**:

| Rule | T1 | T6 when program context is supplied |
| --- | --- | --- |
| Information/mapping availability at exact cutoff | Required | Required |
| Explicit program/molecule identity and valid field domains | Required | Required |
| Mapping confidence | `0 < confidence <= 1` | Domain `[0,1]`; zero is explicitly unresolved and cannot support program-specific claims |
| Active Phase 1/2 and matching next-phase endpoint | Required | Not required; inactive/withdrawn programs may be described |
| `eligible_since` | Actual at-risk eligibility date, on/before origin | If retained, represents an occurred eligibility date and must not be future; anticipated dates require a distinct explicitly typed field, not overloading this one |

Initially keep the existing v2 non-null `eligible_since` contract: reject a future value on supplied T6 programs. A target-only dossier can omit the program. If planned programs without a past eligibility event are later required, specify a versioned context contract instead of inventing dates. Define handling of unknown sponsor, phase and status from actual source needs; do not assume all T6 context must be active or in Phase 1/2.

Write regressions first for withdrawn-but-dated T6 context, future actual eligibility, malformed identity, out-of-range/zero mapping confidence and program-specific observations. Invalid shared context must fail before backend dispatch and fail semantic verification as well. Valid T1 cases and the ten program-free dossiers must remain compatible.

Replace local archived-run dependency with a small immutable v1 golden fixture containing fictional, redistributable inputs and known receipt expectations. Verify it from a temporary checkout without D:/E: paths. Required probes must return explicit `passed`; errors, unknown states and missing required fixtures cannot produce a clean exit.

**Gate C:** Required v1 compatibility checks execute on every machine; all newly invalid cases cause zero backend calls; valid inactive T6 context still works; planned-versus-observed dates are documented. Optional integration checks are visibly separate.

### D. Add clean-checkout validation and CI — 0.5–1 day, after C

Create one local validation command, reused by CI. Use the pinned lockfile and Python 3.11 with a Windows job and a portable job where supported:

- Core job: dependency-free demo/verification and core tests; expected optional skips reported explicitly.
- Full job: install the `ingest` extra, run the full suite and required review probes; fail on unexpected skips or missing legacy coverage.
- Check catalog/reference/index consistency, Python/PowerShell syntax, packaging and exclusion of bulk/private files. Do not depend on E:, private queues, ignored real runs, credentials or provider networking during tests.
- If GitHub is selected for hosting, add push/PR workflow configuration with read-only permissions and pinned action revisions. Until a remote runner has executed it, report “CI configured; hosted execution unverified.”

**Gate D:** A fresh temporary checkout runs required checks without access to local production assets. Preserve an intentionally failing fixture test that demonstrates the CI command returns nonzero. Configuring a workflow is not proof that remote enforcement is active.

### E. Resolve scientific feasibility — 3–5 research/engineering days, plus access/expert waiting

This starts as soon as the baseline is preserved and should not wait for cosmetic utility work. It ends with a signed-off study route, not another catalog expansion.

| Decision | Bounded work | Required evidence / stop condition |
| --- | --- | --- |
| Primary claim and task | Choose T6 evidence/dossier quality as the working near-term route; assess T1 as a separate conditional track | Written estimand, unit, endpoint, comparison, data policy and claim boundary. T6 quality cannot establish clinical prediction improvement. |
| Historical trial feasibility | Select one candidate origin/follow-up pair; use authorized official access and actually restore/query both; review 20–30 program mappings/events, including censoring and unresolved cases | Checksums, schemas, dated program states, event/publication dates, mapping ambiguity and failures. An HTTP response or current API record is insufficient. No historical reconstruction is silently substituted for unavailable snapshots. |
| Model/data chronology | Select explicit model versions, verify lifecycle and training/knowledge limits, record evidence/label cutoff and reporting lag | Feasible origin + horizon + reporting-lag calendar. Distinguish model-matched adaptation from historical reproduction; current model access does not prove absence of training contamination. |
| Cohort size/power | Count eligible programs, events, target/drug/disease clusters and overlaps from restored data; simulate paired comparisons over prespecified correlation/missingness scenarios | Effective sample-size/power report tied to an actual endpoint. The earlier 504–1,762 estimate is illustrative, not a new fixed sample target. Ten dossiers provide no clinical power estimate. |
| Minimal genetics access | Try one legally accessible complete regional exposure/outcome pair and compatible LD; preserve assay, build, alleles, uncertainty, sample size, ancestry and overlap | One auditable regional QC bundle. UKB-PPP is optional if another eligible public source serves the question; a substitute changes provenance and may change coverage/estimand. No significant-hit file substitutes for a complete region. |
| Expert review capacity | Secure a concrete development rubric and reviewer availability; estimate error/coverage on a small stratified set | Reviewed gold references, disagreement handling, blinding plan and a case-level unit of analysis. Automated source fidelity does not substitute for this. |

The current official lifecycle page still lists Sonnet 4.5 retirement on **November 30, 2026** for the Claude API. Platform-specific schedules can differ. Do not make a new eight-month study depend on this model remaining callable; freeze an available-model policy and disclose any comparator adaptation. [Official model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations).

The 24-month horizon remains an arithmetic constraint: an August 2025 origin does not mature until August 2027, before reporting lag. Changing to 12 months is a new endpoint choice requiring justification before outcomes are examined. June 2027 is a conditional methods/benchmark deliverable, not a promise of mature prospective clinical results.

**Gate E decision:**

1. **Proceed with T1** only if usable dated sources, sufficient independent outcomes, a defendable model chronology and an attainable analysis calendar exist. Then specify the cohort/scorer work separately.
2. **Proceed with contemporary T6 methods evaluation** if T1 is infeasible but expert gold, accessible evidence and an informative comparison are available. State this scope change explicitly and keep clinical probabilities null.
3. **Pause expansion** if neither route has evaluable data/review capacity; retain the harness and publishable technical limitations without claiming a completed biological benchmark.

Original hypotheses keep their meanings: H1 versus Virtual Biotech, H2 versus simple baselines, H3 popularity confounding, H4 causal-genetics contribution, H5 dossier quality/error/cost, H6 single-cell reanalysis. A T6 route initially addresses part of H5; it does not claim H1–H4 or H6.

### F. Implement one bounded model-backed specialist — 3–5 days, conditional on a feasible T6 route

Start with source-bound evidence selection and a small structured assessment, using the existing `quote`/`select` interface and immutable packets. Keep the offline extractor as the comparison control. Separate any model-authored synthesis from factual ledger claims; it cannot inherit source-verbatim status automatically.

Before a paid/live run, pin provider/model version, prompt/schema, evidence manifest, sampling settings, token/request limits, retry policy, data-use terms and a finite approved spend cap. Preserve the current $0 default until that execution decision is made. Offline mocked adapter tests can be implemented without accounts or spending.

Do not send the full 60 MiB CFTR packet to a model. Use deterministic bounded retrieval/chunking, explicit coverage/truncation reporting and request fingerprints, with immutable full evidence available for verification. Output and input token reservations must fit provider limits; never silently drop evidence to make a request fit.

Require request deadlines, cancellation/process supervision where needed, rate-limit handling, request IDs, measured usage and conservative accounting for uncertain failures. Recovery must never automatically repeat a possibly billed call. Archive replayable responses and keep external evidence text explicitly untrusted.

**Gate F:** On frozen development evidence, compare the model with the extractive baseline using expert claim precision/recall or coverage, unsupported-claim rate, method validity, case-level utility, latency and measured cost. Prespecify thresholds before evaluation. Include low-coverage and conflicting-evidence cases. A short development screen can reject the adapter; ten familiar cases cannot establish generalization. Keep a separately reserved evaluation set for later claims.

Do not build eight live specialists, autonomous browsing, general tools/MCP servers or multiple competitors before this single-adapter test is informative.

## 4. Order, effort and exclusions

| Sequence | Deliverable | Planning estimate |
| --- | --- | --- |
| First | A: completion record, canonical registry, local baseline | 0.5–1 day |
| Repository stabilization | B + C + D: utility ownership, contract/test corrections, clean-checkout validation | 3–5.5 days |
| Feasibility, overlapping stabilization | E: one restored clinical example, accessible regional genetics, actual counts and written study route | 3–5 days plus external waiting |
| Conditional expansion | F: one model adapter and bounded development comparison | 3–5 days after route, reviewer and spending gates |

These are effort ranges for one engineer with available scientific input, not calendar commitments. The immediate deliverable is A–E and a go/no-go decision; approximately **7–12 person-days**, with some calendar overlap and potentially dominant access/reviewer delays. F is separately gated. Do not keep extending engineering while calling unresolved feasibility “in progress.”

Explicitly deferred: real scorer training/probabilities, large clinical cohorts, full MR/colocalization production, T2–T5, complete Virtual Biotech/other competitor execution, H6 reconstruction, bulk acquisition expansion and prospective outcome claims. Historical access tests and regional slices need their own bounded acquisition instructions; this replanning turn does not start them.

## 5. Definition of success for the next stage

The next stage succeeds when the repository is reproducible from a clean checkout, required checks cannot silently disappear, catalog/manifests have controlled ownership, the canonical v0.2 pilot is clearly discoverable, and a concrete scientific route has passed or failed explicit evidence gates. A negative feasibility decision is a useful result. A live adapter is an optional subsequent deliverable with a measurable benefit criterion, not the completion criterion for the stabilization stage.
