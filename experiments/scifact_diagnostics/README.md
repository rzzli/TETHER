# Frozen SciFact baseline diagnostics

This separate package describes retained public-development errors. It does not change the sealed BG03 baseline, acquire data, run a model, tune a threshold, modify a prediction, or replace the official metrics. Its output does not establish biological or clinical truth.

`analyze.py` reuses the unchanged native contract validators and `experiments.scifact.evaluate.strict_correct`. Each recomputed raw and checked strict result must equal its retained evaluation case result. A complete schedule is required; actual mode requires all 300 claims, including NEI and operational failures. The command verifies a caller-supplied manifest hash and explicit hashes and byte counts for every input and the complete local imported source closure, then rechecks them before publishing. An existing output directory is rejected. JSON and Markdown outputs are UTF-8 with LF endings.

## Manifest and command

The root creates and freezes the actual manifest only after qualification and independent review. Fields are `schema_version: 1`, `kind: "scifact_descriptive_decomposition_inputs"`, `mode: "actual"`, `expected_claim_count: 300`, `inputs`, `source_pins`, `authority_pins`, and `baseline_identity`. Every input/source/authority pin has exactly `path` (absolute), `sha256`, and `bytes`. The root's authority preflight must bind these pins to the original stage receipt and preparation/source authorities; checking fresh file hashes alone does not establish the historical baseline identity. That preflight and original authorities belong in `authority_pins` and their identities in `baseline_identity`.

The six input keys are:

| Key | Retained input |
|---|---|
| `freeze` | `DEV-FROZEN.json`, using `dev_schedule` |
| `references` | Prepared `restricted/references_dev.jsonl` |
| `corpus` | Prepared `views/corpus.jsonl` |
| `dispositions` | Stage `dispositions.json` |
| `candidates` | Stage `check-inputs/candidates.json`, using each completed candidate's unchanged prediction and ordered retrieved records |
| `evaluation` | Stage `evaluation.json`, using every retained native case result |

`SOURCE_CLOSURE` in the analyzer lists its eight required local Python files, including the unchanged native scorer/contract and their TETHER dependencies. Standard-library interpreter identity is recorded by root qualification. The CLI is designed for a qualified fresh interpreter with `-I -B`, a fresh workspace `-X pycache_prefix=...`, and workspace `TEMP` and `TMP`:

```text
python -I -B -X pycache_prefix=<fresh-workspace-path> experiments/scifact_diagnostics/analyze.py --manifest <absolute-manifest> --manifest-sha256 <frozen-sha256> --output <fresh-absolute-output-directory>
```

Outputs are `DECOMPOSITION.json`, `REPORT.md`, an exact `INPUT-MANIFEST.json` copy, and a no-clobber `RECEIPT.json` containing output hashes. Failed validation creates no output directory. An I/O failure during publication can leave a partial fresh directory without a successful receipt; never reuse it.

## Meaning of the decomposition

The per-claim object retains retrieved and selected documents; annotation-relative false negatives and false positives; omission of gold documents that were retrieved; labels on selected annotated documents; ordered full/capped rationale sentences; missing sentences for every alternative gold rationale; and extras outside the union of gold rationale sentences. Non-gold retrieved documents use the field `non_gold_documents`, because retrieval over an incompletely annotated corpus does not establish universal biological negatives.

Native strict correctness requires an exact evidence-document set, each correct document label, and **any one complete** gold rationale contained in the original predicted list prefix of length `max(3, min(gold rationale lengths))`. It does not require every alternative or the union. Extra rationale sentences alone do not fail strict correctness. Full-list completeness with cap incompleteness is reported separately from incompleteness even in the full list. Labels and rationales of omitted documents are unobserved, not automatically classified as incorrect.

Overlapping flags preserve simultaneous errors. A separate mutually exclusive partition uses this fixed order: operational failure, retrieval miss, selection omission, selection extra, label mismatch, rationale incomplete, strict correct. This order is an explicit descriptive convention, not a causal ranking or an estimate of what an intervention would repair. Selected documents must be a subset of the retained retrieval for this baseline. Checker rejection does not change the raw prediction's first-failure category; raw/checked strict results and the `not_admitted` flag remain separate.

NEI is split into produced-empty correct, produced-nonempty false positive, and operational failure. Its retrieval recall/completeness is null, not perfect recall. Missing predictions are never projected to substantive NEI answers. For operational failures, selection arrays and raw strict correctness are null; false overlapping content-error flags mean unobserved, not successful semantic requirements. Strata and document counts retain explicit denominators; sentence extras only concern selected gold documents and non-gold selected sentences are retained separately.

## Invented qualification

Tests were written and first run before the analyzer existed; the retained red-phase record identifies the expected import failure. Tests cover alternative rationales, longer rationale caps, sentence order, extra selected documents, concurrent errors, NEI, operational failures, checker rejection, native bounds, duplicate/overlapping inputs, explicit pin mismatches, duplicate JSON keys, and no-clobber output. `qualify.py --output <fresh-directory>` runs the suite and retains a two-claim fictional end-to-end manifest/output. It does not read the actual development artifacts.
