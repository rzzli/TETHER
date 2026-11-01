# AsOf target-evaluation agents

AsOf turns dated evidence into auditable target-evaluation dossiers. It provides
strict temporal and lineage admission, immutable evidence, bounded execution,
failure/usage journals and semantic re-verification. The default backend runs
offline and makes no model-provider requests.

**Current software: 0.3.11, with v2 execution contracts.** The retained acceptance
has 1,774 tests; 326 accepted source/resource pins remain unchanged. The validation
gate has one reviewed correction preserving an exact-hash failed-source archive.
The source includes optional study preparation, recorded comparison and bounded
model interfaces. Recorded fixtures and passing software tests are not scientific
performance measurements.

## Current status and next step

The [preprint readiness review and completion plan](<planning/Preprint Readiness Review and Completion Plan 2026-10-31.md>) is the current execution roadmap. The bounded multicase technical experiment and reproducible results are complete. The [current working-draft checkpoint](<planning/Project Progress Reassessment 2026-11-01 - Manuscript Working Draft.md>) records the manuscript, supplement and thirteen-entry bibliography, passing 118 independent content checks and a separate positioning review. The 17-page PDF passes text/visual/repeat checks. On 1 November the owner deferred factual declarations: P08 remains incomplete while independent P09 release/replay qualification proceeds. P10 final packaging and declarations follow. Read the [paper draft](paper/README.md). This is a source-reporting/methods paper, with no validated clinical-prediction or expert-equivalence claim.

The earlier [P02 feasibility result](<planning/Project Progress Reassessment 2026-10-31 - Source Fact Feasibility.md>) retains the identity/date projection ceiling and partial-input limits. [P02a data completion](<planning/Project Progress Reassessment 2026-10-31 - Credible Set Completion.md>) now verifies all 23 new files and the complete 25-file credible-set join: one exposed development locus has beta/SE/p-value components. Sample size, units, ancestry and upstream-study verification remain unresolved; no causal genetics or fresh cohort is qualified. Thirteen integrity/numeric regression shapes pass. Original worker/state/receipts and stopped monitor remain unchanged.

The [P03 source-reporting evaluator](<planning/Project Progress Reassessment 2026-10-31 - Source Fact Evaluator.md>) is now implemented: 173 targeted tests pass (99 new/74 legacy, zero skips), one actual source row replays, and a dependency-free installed smoke passes outside the checkout. See the [contract and API](docs/SOURCE_FACT_EVALUATION.md). These are mechanical engineering results, not a model-quality comparison or qualified scientific measurement endpoint.

P04 is complete as a **negative exposed development pilot**: all twelve cells retained, five model calls, zero accepted model-generated reports, and literal clean-case completion 2/2. The independent source-inclusive audit passes 2,216 checks. Two earlier zero-dispatch setup failures remain retained. The subsequent two fictional conformance controls yielded one pass and one malformed report; the model branch is now closed under its frozen rule. See the [technical-paper scope](<planning/Project Progress Reassessment 2026-10-31 - Deterministic Paper Scope.md>), [P04 acceptance](planning/review-assets/preprint-p04-20261031/P04-ACCEPTANCE-v1.json) and [conformance audit](planning/review-assets/preprint-p04b-20261031/RUN-AUDIT-v1.json).

The [current source-reference checkpoint](<planning/Project Progress Reassessment 2026-11-01 - Source Reference Completion.md>) verifies a prospective registry of 1,753,850 physical GWAS rows and twelve identity-ranked source units. Independent registry/input/reference audits pass 789, 1,238 and 1,163 checks respectively; all twelve references and 180 facts match 24 distinct original rows. Forty-one reference-builder regressions pass. Producer memory for reference preparation is unmeasured; the experiment runner must qualify its fallback. P05 is now frozen in the [technical study checkpoint](<planning/Project Progress Reassessment 2026-11-01 - Technical Study Freeze.md>): 36 runner, 25 auditor and 17 analyzer preparation methods pass; the persistent fictional qualification creates zero native outputs. The [single executed study](<planning/Project Progress Reassessment 2026-11-01 - Technical Study Result.md>) now passes 2,414 independent source-audit checks across all 38 outputs and 90 decisions. The [audited paper results](<planning/Project Progress Reassessment 2026-11-01 - Audited Paper Results.md>) now include eleven CSV/Markdown tables and three vector figures, passing 351 independent checks and a byte-identical local rebuild. Manuscript and lawful release qualification remain unfinished. Exposure and independent-study status are unqualified; these are technical source-fidelity results. The [AI-only policy](<planning/AI Only Evaluation Plan 2026-10-31.md>) requires no external expert input. Original expert-preference H5 is untested. See [TODO](TODO.md) for the full paper checklist.

- Ten canonical contemporary development dossiers and their retained source audit exist; see the [run registry](planning/run-registry.json).
- R07's technical diagnostic remains negative: six complete responses, zero frozen-contract passes. The former human gate is retired; a separate AI retrospective assessment is planned. A stronger-model control remains unqualified.
- Source5 corrects two API/axis-kind guards: 43 executable controls pass, four branches remain deferred and one static. The separate C79 fake-target component passed; the installed C++ tools work without restart.
- Further private native-bank/physical14/new84 proof work is deferred pending a demonstrated study need. It is not a prerequisite for reporting the existing extractive framework and negative feasibility result.
- Scientific H5 and clinical H1–H4 remain open. Real numerical features stay empty and probabilities null. The frozen interpretation slice has 65 missing inputs; the clinical route has 36 unqualified endpoints and 0/12 jointly source-ready cases.

The original native recognition result remains FAILED and whole verification
INCOMPLETE_TIMEOUT. Failed attempts are retained, with no automatic replay or
answer repair. Provider spending remains $0; the downloader and stopped monitor
are unchanged. Python interfaces are not an OS sandbox.

## Navigation

| Resource | Purpose |
|---|---|
| [TODO](TODO.md) | Current accepted work and incomplete scientific/optional engineering gates |
| [Recovery plan](<planning/Project Recovery and Evaluation Plan 2026-10-26.md>) | Original ordered dependencies and stop rules |
| [Progress assessments](<planning/Project Progress Reassessments.md>) | Dated evidence and limitations |
| [Framework](docs/FRAMEWORK.md) / [migration](docs/V02_MIGRATION.md) | v2 interfaces, temporal/semantic guarantees and v1 limitations |
| [Study runtime](docs/STUDY_RUNTIME.md) / [interpretation](docs/INTERPRETATION_INTERFACE.md) | Packaged research mechanics and their claim boundaries |
| [Data plan](data/DATA_PLAN.md) / [catalog](data/catalog/sources.json) | Dataset products, versions, permissions and acquisition requirements |
| [Prior README](docs/history/README-before-scientific-priority-20261031.md) | Exact pre-reassessment history, preserved at its original checkpoint |

## Run the offline demonstration

From `D:\Projects\drug_target_agents` in PowerShell:

```powershell
uv sync --python 3.11
uv run --no-sync asof demo --output runs/demo-v02-001
uv run --no-sync asof verify --run-dir runs/demo-v02-001
uv run --no-sync python -m unittest discover -s tests -v
```

For the shared local/CI validation command, use `uv run --no-sync python tools/validate.py
--mode core --package`. Full validation requires the ingestion extra and PowerShell 7:
`uv run --no-sync python tools/validate.py --mode full --package`. Full mode rejects all
skips; core mode permits only named optional-dependency skips. Both require the portable
legacy fixture and all review probes. Older private-repository checkpoints passed
Windows/Linux core/full hosted CI; the current commits have not been pushed or
qualified by hosted CI. See the [registry milestone evidence](planning/review-assets/registry-sizing-20261017/README.md)
for exact commits and hosted results.

Choose a new output directory for each execution. `dossier.md` is the readable report;
`ledger.json`, `features.json`, `prediction.json`, `inputs.json`, `run.json`,
`trace.jsonl`, `journal.jsonl` and `receipt.json` retain evidence and accounting.
CLI runs also archive `request.json`. Save the printed receipt hash independently:

```powershell
uv run --no-sync asof verify --run-dir runs/demo-v02-001 --receipt-sha256 <saved-hash>
uv run --no-sync asof inspect-run --run-dir runs/demo-v02-001
```

Verification reports byte integrity, semantic consistency, source binding and scientific
validity separately. Without an independently retained hash, local verification cannot
detect wholesale replacement of both a run and its receipt. `inspect-run` reads durable
attempts and build progress; it never reissues a potentially billed call.

## Inspect local data and build a snapshot

Ingestion is optional and pins `pyarrow==21.0.0`; the default runtime has no third-party
dependencies. Install the extra once and retain it with `uv run --no-sync`:

```powershell
uv sync --python 3.11 --extra ingest
uv run --no-sync asof inspect-source --manifest data/manifests/private/v02-inputs.json `
  --catalog data/catalog/sources.json --report data/manifests/private/inspection-new.json
uv run --no-sync asof build-snapshot --manifest data/manifests/private/v02-inputs.json `
  --catalog data/catalog/sources.json --output data/derived/contemporary-pilot-new
```

These commands read files explicitly named in a manifest. The adapter pins Open Targets
25.09 target, disease and nonclinical evidence products and HGNC dated 2026-10-10.
Bulk originals remain under `E:\projects_data\drug_target_agents_data`; normalized
packets remain in ignored `data/derived/` directories. Receipt, hash, schema, role and
path checks precede admission. The builder preserves lineage and selected-subset coverage,
excludes ChEMBL and known-drug evidence, and fails above the 64 MiB packet limit.

The fixed pilot contains ten hypotheses across CD276, OSMR, ERBB2, PCSK9, IL6R, CFTR,
GLP1R and SCN9A. ERBB2 and PCSK9 each have two action/modality hypotheses. Tissue is
unspecified; reported source contexts remain distinct. Missing canonical IDs block the
affected case. A present-day receipt proves a present-day availability bound only.

## Run a prepared v2 case

```powershell
uv run --no-sync asof run --case path/to/case.json --snapshot path/to/snapshot.json `
  --catalog data/catalog/sources.json --output runs/pilot-case-new
```

The input is a normalized packet with complete source lineage, not provider raw data.
Every mapping, annotation and source ancestor must be eligible at the exact UTC cutoff.
Catalog roles apply to ancestors: generated products cannot make evaluator-only labels
or gold answers agent-visible.

Omitting `--scorer` yields explicit abstention. T6 always withholds clinical probabilities.
A scorer supplied for T1 must pass schema, profile and training/calibration cutoff checks
before dispatch. Applicability mismatches abstain. Recorded selections supplied with
`--replay` must match exact request fingerprints. New demo fixtures live under
`src/asof/demo/v2/`; the original `src/asof/demo/` fixtures are preserved.

## Project map and limits

| Location | Purpose |
| --- | --- |
| `src/asof/` | Immutable contracts, provenance, workflow, ingestion and CLI |
| `docs/FRAMEWORK.md` | Interfaces, guarantees, failures and deferred work |
| `docs/V02_MIGRATION.md` | Explicit v1-to-v2 conversion requirements |
| `tests/` | Temporal, provenance, semantic, budget, failure and adapter regressions |
| `tools/framework/build_demo_v2.py` | Regenerate only fictional v2 fixtures |
| `tools/review/probe_framework.py` | Required review probes and legacy verification |
| `data/` | Requirements, catalog, acquisition and coverage documentation |
| `planning/` | Preserved original proposals and dated reviews |
| `memory/` | Current decisions and implementation history |

Defaults remain 16 calls, 32,000 input tokens, 8,000 output tokens, $0 provider spending,
300 seconds and one critic retry per category. An optional explicit loopback model
adapter is available through `--local-model config.json`; the default stays offline.
MR/colocalization computation and a trained clinical scorer remain gated. T1 has a program/endpoint
interface; T6 has a dossier interface. T2–T5, qualified historical clinical benchmarks, H6 reconstruction
and locked benchmark inference remain later milestones. The separate evaluator reports
descriptive metrics for supplied cohorts.

Python interfaces are not an OS sandbox. Dataset terms remain source-specific; Apache-2.0
licenses the code, not acquired biomedical data. The download worker and the user's
stopped periodic monitoring are independent of this milestone.

The seven ordered science assessments have passed within their stated scopes,
including conditional genetics defer, an evidence-backed no-fit and supported
development comparisons. Clinical scientific qualification remains withheld.
See [TODO.md](TODO.md), the
[science execution report](planning/Scientific%20Prerequisites%20Execution%202026-10-18.md)
and the [current matched-comparison checkpoint](planning/Matched%20T6%20Comparison%20Execution%202026-10-20.md).
The [October 17 execution report](planning/Ordered%20Execution%20Progress%202026-10-17.md)
and [local-model pilot](planning/Local%20Model%20Specialist%20Pilot%202026-10-17.md)
remain dated history.
