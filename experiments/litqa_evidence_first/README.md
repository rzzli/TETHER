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
- `release.py`: offline checks of all four CI jobs and runtime source bytes against the exact committed revision.
- `run.py` and `supervise.py`: isolated admission, per-phase workers and a separately retained outer controller process.
- `reconstruct.py`: independent source, native, role, process and accounting joins; only issued capabilities can reach evaluation.
- `qualification.py`: comparison against a prospectively sealed six-case control bank after complete execution verification.
- `evaluation.py` and `arithmetic.py`: original fixed endpoints, native-score agreement and separate arithmetic checks.

The complete engineering integration is tested with invented data, native HTTP
responses and process records. It does not establish actual model performance.
Actual native controls and the production comparison remain pending. A complete
run requires all twelve
prospectively frozen invented controls to pass before the 398-opportunity
production comparison, along with its source, process and exact-commit CI gates.
The failed original condition remains separate negative evidence.

Component tests use invented data and captured fictional HTTP responses:

```powershell
python -B -m unittest discover -s experiments/litqa_evidence_first -t . -v
```

Stage-replay tests require native Windows sharing locks. Portable core CI
skips those explicitly; the required Windows full gate runs them without skips.
Stage writing, codec and planning tests also run in portable core CI.

Preparation and permanent reservations never dispatch a model. A moved output
directory does not release an existing authority. Unknown native failures stop
execution; unused qualification slots cannot be used for prompt selection.

Qualification preparation takes `{bank, original_inspection}`: both values are
file proofs containing `path`, `sha256` and `bytes`. The inspection receipt binds
the original production frame through its metadata report and inventory. Its
root and frame digest determine the parent identity; a caller-supplied identity
string cannot create another call allowance. Expected qualification answers stay
outside preparation and actor grants. Production uses the full independently
verified parent instead.

A plan becomes eligible only after its successful `COMPLETE.json` binds that
exact plan. Failure markers dominate completion. Release checks require the
`validate.yml` workflow on a `main` push and four successful jobs from the same
commit and run attempt.

Independent reconstruction takes an externally pinned descriptor containing
`root`, `receipt_sha256` and `controller: {root, receipt_sha256}`. The controller
receipt binds its nested producer, exact command, process limits and terminal
status. A direct controller directory without that outer proof is insufficient.
Expected control answers and benchmark references are never worker inputs.

New physical costs include only repair and removal. Reused baseline, critique
and source costs are attributed separately; the whole earlier failed condition,
including its unverified failed-call usage, remains visible as historical exposure.
Logical condition costs overlap and must not be added together as physical work.
