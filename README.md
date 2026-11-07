# TETHER

**Trace every drug-target claim back to its evidence.**

TETHER is an **agent execution and evaluation harness** for drug-target research. Give it a hypothesis and versioned evidence; get a dossier of **source-linked claims, evidence gaps, and a verifiable execution record**.

*Target Evidence Tracking Harness for Evaluation and Reproducibility*

[Try it](#quick-start) · [Status & results](#current-results) · [Docs](#explore)

<a id="how-it-works"></a>

## How it works

> **Illustrative input:** Evaluate IL6R inhibition by an antibody for rheumatoid arthritis, using evidence available by a specified date.

```mermaid
flowchart LR
    H["Your hypothesis"] --> C
    E[("Versioned evidence")] --> C
    C["Check inputs<br/>Identity · dates · lineage"] --> W
    W["Run evidence workflows<br/>Specialists · budgets · claim checks"] --> D
    D["Research dossier<br/>Claims · citations · gaps"]
    C -.-> A["Execution record<br/>Inputs · calls · decisions · failures"]
    W -.-> A
    D -.-> A
    style D fill:#dcfce7,stroke:#15803d,color:#14532d
    style A fill:#eff6ff,stroke:#2563eb,color:#1e3a8a
```

| Component | What it does |
|---|---|
| **Evidence** | Tracks source versions, dates, and relationships between inputs. |
| **Execution** | Routes evidence through specialists, limits work, and records accepted claims. |
| **Evaluation** | Checks run consistency and measures scientific answers on benchmarks. |

Specialist routes include genetics, expression, perturbation, pathways, modality, literature, clinical, and safety. Available capabilities depend on the inputs and backend.

<a id="installation-and-compatibility"></a>
<a id="try-it"></a>

## Quick start

**Python 3.11+ · uv · PowerShell** — run from the repository root:

```powershell
uv sync --project packages/tether --python 3.11 --locked
New-Item -ItemType Directory -Path runs -Force | Out-Null
uv run --project packages/tether --no-sync tether demo --output runs/my-first-demo
uv run --project packages/tether --no-sync tether verify --run-dir runs/my-first-demo
```

**Deterministic offline demo · fictional evidence · no API key.** Installation may need network access. Use a fresh output directory each time.

<a id="tether-cli-run-layout"></a>

**Read the result:** `runs/my-first-demo/dossier.md`.

For stronger integrity checking, save the printed receipt hash separately and pass `--receipt-sha256 <saved-hash>` to verification.

<a id="what-works-today"></a>
<a id="current-results"></a>

## Status & results

- **Built:** offline execution and verifiable runs; [historical 10-case pilot](planning/run-registry.json).
- **Measured:** [SciFact](<planning/TETHER SciFact Full Context Results 2026-11-06.md>) and [initial LitQA2](<planning/TETHER LitQA2 Native Evaluation Results 2026-11-06.md>) results, including failures and limitations.
- **Under development:** stronger retrieval and scientific answering. [Roadmap →](TODO.md)

**A verified run is not a validated scientific conclusion.** Clinical probabilities and therapeutic benefit remain unvalidated.

## Explore

[CLI guide](packages/tether/README.md) · [Architecture](docs/FRAMEWORK.md) · [Verification limits](docs/TETHER-VERIFICATION-SCOPE.md) · [Data](data/README.md) · [Experiments](experiments/) · [Working paper](paper/README.md) · [History](docs/ARCHIVE.md)

[Apache-2.0](LICENSE). Data has separate terms; bulk datasets and model weights are excluded. The evidence engine lives in `src/tether_engine/`.
