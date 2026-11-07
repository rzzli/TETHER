# Evidence-first LitQA refinement

This is a separate experimental condition following a failed refinement control.
It reuses the original questions, passages, candidate answers, critiques and
information cutoff. It presents raw evidence before the generated controls and
removes operational metadata from the model-facing projection. It makes no new
source requests and does not adopt earlier repair answers as new outputs.

The components currently implemented are:

- `model.py`: frozen ordered projection, paired requests and the original two-field answer contract.
- `projection.py`: complete input preservation and single-member actor inputs.
- `transport.py` and `cells.py`: bounded one-attempt calls with retained native responses and failures.
- `native_evaluation.py`: independent reconstruction of requests, native bytes, token counts and call journals.
- `stage.py`: durable six-case qualification or full 199-case stages with explicit failed and unexecuted slots.
- `plan.py`: source-inclusive preparation and a permanent authority keyed by original parent and new method identity.

The whole-run controller, independent process/source reconciliation and evaluation
integration are not yet qualified. These modules alone do not authorize native
execution or establish benchmark performance. A complete run requires all twelve
prospectively frozen invented controls to pass before the 398-opportunity
production comparison, along with its source, process and exact-commit CI gates.
The failed original condition remains separate negative evidence.

Component tests use invented data and captured fictional HTTP responses:

```powershell
python -B -m unittest discover -s experiments/litqa_evidence_first -t . -v
```

Preparation and permanent reservations never dispatch a model. A moved output
directory does not release an existing authority. Unknown native failures stop
execution; unused qualification slots cannot be used for prompt selection.
