# AsOf target-evaluation agents

The October22 [primary report lookup](planning/Primary%20Report%20Lookup%20and%20Source%20Readiness%202026-10-22.md)
authenticated the official poster0507 program entry and May14 schedule. The NCT
bridge, target DOI, primary results text and analysis/decision dates remain
unqualified. Independent reviews recommend revise/defer; this bounded same-case
lookup stops. Next is clinical-design/acquisition feasibility reassessment before
more searches or cohort activation. Labels and probabilities remain null.

The October22 [public-chronology review](planning/Public%20Chronology%20and%20Primary%20Report%202026-10-22.md)
verified eight registry dates: results submitted January26, QC-qualified May5,
and first publicly posted May29,2026, after the April1 cutoff. Three searches
and four page actions recovered a secondary abstract lead, without an authenticated
primary report. Mapping and review-scope errors are preserved/disclosed; labels
stay null. Next is a bounded publisher/DOI lookup of that lead. Earlier next-step
statements below describe their dated checkpoints.

The October22 [historical-document metadata check](planning/Existing-trial%20Document%20History%202026-10-22.md)
verified the existing trial's January/April extraction: both document tables were
queried and empty. Historical PDF availability remains unqualified; this is an
exposed local diagnostic, not an absence claim. Public chronology and authentic
primary-report evidence are the next scientific priority.

The October22 [existing-trial protocol audit](planning/Existing-trial%20Protocol%20Audit%202026-10-22.md)
collected and reviewed all20 pages of the selected protocol/SAP. Endpoint and
analysis provisions are now documented; the full decision rule, prospective
authenticity and historical availability remain unqualified.658 tests/four CI
jobs pass. The next bounded check uses retained historical document metadata.

The October21 [publisher-discovery amendment](planning/Publisher%20Discovery%20Amendment%202026-10-21.md)
recovered two exact originals and passed the sponsor-poster control. Current
registry version changes and a blocked corporate redirect keep cohort acquisition
inactive.647 full tests pass. A newly listed, uncollected protocol/SAP is the next
bounded existing-trial source-review lead; clinical qualification remains open.

The October21 [retrieval calibration](planning/Exact-trial%20Retrieval%20Calibration%202026-10-21.md)
completed four exact-hash original downloads and structured protocol/SAP projection.
The frozen sponsor-report discovery control failed, so the next twelve-case
source-readiness design remains inactive. No new clinical labels were assigned.
All635 full tests and dependency-free validation pass; the retained report describes
the blocker and the required prospective discovery amendment.

The October21 [fixed-member follow-up assessment](planning/Endpoint-specific%20Follow-up%20Feasibility%202026-10-21.md)
completed both snapshots,36 bounded searches,16 original artifacts and AI
cross-review. All36 new endpoint labels remain null; no training is activated.
Source verification and616 full tests/four hosted jobs pass. Next is source-readiness
feasibility for authentic rules, scope and decision timing.


The October21 [endpoint-specific origin sample](planning/Endpoint-specific%20Origin%20Sample%202026-10-21.md)
freezes separate efficacy-decision, advancement and dosing rules. An origin-only
128-trial screen yielded36 maturity-eligible candidates; the first12 are sealed
before follow-up. Independent source/packet checks pass; clinical labels remain
null.597 full tests and four hosted jobs pass. Step1 clinical qualification remains open.


AsOf v0.2 turns approved, dated evidence into auditable target-evaluation dossiers.
It combines a deterministic planner, bounded extraction backend, grounding critic,
immutable evidence ledger, hypothesis-bound features and a separate frozen scorer.
The default backend runs offline and makes no model-provider requests.

New execution requires **v2 cases, snapshots and evidence packets**. Original v1 fixtures
and archived receipts remain available; v1 semantic verification is unavailable. See
[migration guidance](docs/V02_MIGRATION.md) and the [framework reference](docs/FRAMEWORK.md).

The bundled demonstration uses fictional observations and scorer weights. Contemporary
real-data T6 dossiers use descriptive source evidence, empty numerical prediction features
and null probabilities. Mechanical verification does not establish biological correctness
or clinical predictive validity. The production pilot is complete: ten finalized dossiers
and a retained audit of 20 distinct original rows. The versioned
[run registry](planning/run-registry.json) identifies the canonical artifacts and retained
failed attempts. See the [stabilization report](planning/Stabilization Completion and Feasibility Gates.md).

The October 18 Task 6 [development comparison tools](planning/Task%206%20Development%20Comparisons%202026-10-18.md)
provide exact-request lexical/provider-score baselines, explicit evidence masks and
a pinned Virtual Biotech configuration audit. These diagnose selection behavior;
independent scientific quality and clinical performance remain unmeasured.

The [Science 7 matched comparison](planning/Matched%20T6%20Comparison%20Execution%202026-10-20.md)
completed 60 case-arm runs, source-inclusive verification and a 20-original-row audit.
All seven bounded science assessments are closed, including genetics defer and scorer
no-fit. Its 551-test checkpoint passed full/core validation (57 expected core skips),
required probes, packaging and four hosted jobs. Provider spending remains $0.

AsOf selected every offered candidate (37/37); this demonstrates source fidelity and
execution controls, not ranking quality or scientific superiority. The source-derived
Virtual Biotech adaptation exhausted its budget in seven cases. The failed first
attempt and response-informed v0.2 correction remain disclosed. Historical predictors,
qualified clinical outcomes, power, genetics, scoring and clinical lock remain unmet;
all real probabilities are null. See the report's remaining-gates table and [TODO](TODO.md).

The October21 [clinical-label diagnostic](planning/Clinical%20Label%20Readiness%202026-10-21.md)
completed the missing reported-result extraction for the same twelve trials across
January/April2026:995 source rows per snapshot, two result-bearing trials, no new
qualified labels. All36 old endpoints remain unresolved. Negative-ascertainment
and result-linkage guards were corrected;577 full tests, core validation and four
hosted jobs pass. The later same-day endpoint-local design and origin-only sample
are now sealed; the separate follow-up assessment is complete with null labels. Scientific gates stay false.

The current adapter uses **normalization recipe 2.2** within the unchanged v2 contracts.
It retains reported literature passages/sections, PMC IDs, study overviews and variant
clinical significance. Dossiers distinguish resource annotations from unassessed
therapeutic relevance and display unresolved hypothesis qualifications. See the
[context revision report](planning/Context Revision Completion.md) for the rebuild,
comparison and remaining scientific limitations.

The completed [long-session report](planning/Clinical Long Session Progress.md) covers
five restored AACT dates, 24 trial timelines and the full-window genetics technical
revision. A separate complete-input T6 release now has 2,206 files, zero missing selected
inputs and ten source-verified dossiers; the registry identifies it explicitly. Clinical
feasibility evidence remains evaluator-only, with no validated outcome labels. Larger
collections can opt into `build-snapshot --packet-layout bounded`; every packet retains
the 64 MiB limit, and every observation is preserved.

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
legacy fixture and all review probes. Windows/Linux core/full hosted CI has passed
for the private repository checkpoint. See the [registry milestone evidence](planning/review-assets/registry-sizing-20261017/README.md)
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
| `tools/review/probe_framework.py` | Temporary v2 review probes and legacy verification |
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
