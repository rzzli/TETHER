# AsOf target-evaluation agents

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
or clinical predictive validity. The production pilot and retained source audit are being
finalized; generated artifacts determine completion.

## Run the offline demonstration

From `D:\Projects\drug_target_agents` in PowerShell:

```powershell
uv sync --python 3.11
uv run --no-sync asof demo --output runs/demo-v02-001
uv run --no-sync asof verify --run-dir runs/demo-v02-001
uv run --no-sync python -m unittest discover -s tests -v
```

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
300 seconds and one critic retry per category. No live model, MR/colocalization computation,
trained clinical scorer or competitor execution is included. T1 has a program/endpoint
interface; T6 has a dossier interface. T2–T5, historical clinical cohorts, H6 reconstruction
and locked benchmark inference remain later milestones. The separate evaluator reports
descriptive metrics for supplied cohorts.

Python interfaces are not an OS sandbox. Dataset terms remain source-specific; Apache-2.0
licenses the code, not acquired biomedical data. The download worker and the user's
stopped periodic monitoring are independent of this milestone.
