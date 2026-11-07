# Interrupted refinement recovery

This adapter continues **untouched calls** from a failed LitQA refinement run.
It preserves the original failure, completed outputs, source cutoff and paired
requests. It creates a separate version-two execution record.

| Component | Responsibility |
|---|---|
| `original.py` | Independently verify the failed parent, source archive, native responses, roles and untouched slots. |
| `contracts.py`, `plan.py` | Derive remaining budgets and reserve permanent, exclusive continuation authority. |
| `run.py` | Supervise eligible repair/removal calls and retain attempts, failures and accounting. |
| `native_failure.py` | Authenticate the specific captured token-limit failure without accepting its partial answer. |
| `reconstruct.py` | Join original and continued records into a distinct verified recovery capability. |
| `evaluation.py` | Open evaluator-only inputs after reconstruction; apply the unchanged native metrics and fixed statistical endpoints. |

Completed and entered calls are never retried. A new output directory alone does
not authorize another continuation. The permanent authority is tied to the
original execution; it is not released automatically after a process exits.

Failed calls remain in the scheduled denominator with null predictions. Qualified
token measurements, independently checked but unqualified reported usage, and
conservative reservation bounds remain separate. New computation consumes the
remaining original time and call budgets. It adds no retrieval, source refresh,
threshold fitting or provider spending.

Run invented-data regressions from the repository root:

```powershell
python -B -m unittest tests.test_refinement_recovery -v
```

These tests are also discovered by the repository core/full validation gates.
Tests that exercise Windows sharing locks and process jobs require Windows;
the portable contract, accounting and parser tests also run on Ubuntu. Windows
full validation requires every discovered test to run without skips.
Their success does not qualify a model, a real continuation or scientific claims.
An actual continuation additionally requires externally anchored source/input
proofs, a qualified frame, native controls and the exact-commit validation gates.
Local frames, authorities, outputs and evaluator inputs stay outside the public
repository.

Original version-one artifacts remain unchanged. Earlier source-bound replays
require their matching checkpoint. The current verifier sizes reads to each
checked file while retaining file-size, identity and reparse checks; that change
does not transfer an earlier source qualification to the new implementation.
Archived Python is read as evidence and never executed by this adapter. A
successful recovered execution does not retroactively make its parent successful,
establish citation entailment or validate therapeutic benefit.
