# Independent follow-up: current TETHER v0.4.1 execution boundary

This is a separate follow-up to RESULTS-REVIEW.md. The results review concerns the retained P05/P09 paper experiment; this review concerns new, currently implemented TETHER v0.4.1 code. No original paper, experiment outputs, frozen engine, source packets, human submissions or clinical outcomes were changed or consumed by these probes.

## Coverage and method

Read the complete new `packages/tether/src/tether/_semantics.py`, its integration in `_presentation.py`, its targeted tests, and relevant original `src/asof/workflow.py`, `semantics.py` and `artifacts.py` execution/verification branches. Constructed fictional demo runs using the existing extractive backend, changed their traces, recomputed the hash chain, and wrote genuine local producer receipts. Calling `verify_engine` with each newly produced receipt digest distinguishes an actual semantic consistency check from a byte-tampering check. These are synthetic engineering probes, not new scientific data or adversarial model outputs.

This does not establish exhaustive state-space coverage, trusted execution, source authenticity, biological accuracy, an operating-system security boundary, or independent replication of original source mappings. The original engine and direct legacy aliases retain their old guarantees; the strengthened check is on the current TETHER facade boundary.

## Findings and corrections

| ID | Reproduction | Correction / current disposition |
|---|---|---|
| SEM-01 | Static review found that a reviewed selection was not constrained to the recorded bounded retrieval IDs. The implementation was fixed before my executed probe; no failing-before execution is claimed. | Added subset requirement. Independent execution rejected a fictional accepted selection outside its recorded request. |
| SEM-02 | Inserted `backend_failed` between accounting and review in an otherwise valid completed run. Rechained and resealed run passed the new verifier despite later review and claims. | Terminal failed-category rule added. Independent replay now rejects the event after backend failure. |
| SEM-03 | Inserted `backend_quote_failed` before dispatch in an otherwise valid completed run. Rechained and resealed run was accepted, although the producer breaks that category after quote failure. | Terminal quote-failure category rule added; independent replay rejects later dispatch. |
| SEM-04 | Created valid rejected-review retries, removed those rejected reviews, and rechained/resealed. Completed run was accepted although the earlier accounted calls had no review, failure or deadline disposition. | Each accounted active attempt must have a review or terminal disposition before transition/finalization. Independent replay rejects the missing disposition. |

These are producer-consistency defects in the new boundary, mapped to active platform corrections / R01-R02. They do not revise P05/P09 scientific results. Changes belong to the new version and must not be backported into frozen provenance merely to make old fingerprints match.

## Necessary limits on the guarantee

The journal serializes `error_class` as a name, not Python class identity/inheritance. It cannot prove arbitrary custom exception subclasses or causally establish a fatal-versus-interrupted classification from that string. Likewise, replaying consistency of a selected-ID inventory is distinct from proving an arbitrary backend actually received that request. The local structured backend has additional archived request/retrieval checks; generic backend request hashes are not a universal execution attestation. Real elapsed wall time and actual billing cannot be established by checking a producer-authored journal alone.

The positive contract is bounded: eligible source/claim bindings, selected reviewed claims and completion coverage agree under the supported recorded state transitions; deterministic dossier text reconstructs from the verified state. Preserve explicit `scientific_validity: not_established`. Neither unit-test counts nor these synthetic probes are clinical or causal validation.

## Retained evidence

- `SEMANTICS-PROBE-RECORDS.json`: before/after observed dispositions and ignored scratch paths.
- `probe_retrieval_semantics.py`, `probe_failure_semantics.py`, `probe_quote_failure_semantics.py`, `probe_missing_disposition_semantics.py`: reproducible offline fictional producer probes.
- `FAILURE-PROBE-BEFORE.txt` and `FAILURE-PROBE-AFTER.txt`: initial confirmed backend failure acceptance and later rejection.

The first attempted probe used the system temporary directory and hit an environment PermissionError before verification. Retained probes use the project ignored `data/cache` directory. That setup failure is not counted as a runtime finding.

## Final validation

All four independent fictional producer probes rejected the intended inconsistency after the platform corrections. The targeted semantic test module also passed **23 test methods, zero failures and zero errors**, with stdout retained in `SEMANTICS-TESTS.txt`. This included genuine completed, partial, failed, interrupted, bounded-retrieval, rejected-review retry, budget-exhausted and claim-prefix cases. No additional runtime modification was made by this independent reviewer. The method count belongs to this one targeted run; do not add it to a broader suite count as if the cases were distinct.

The four findings are closed for their retained fixtures. Remaining boundary limits above are intentionally not claimed as solved. Later edits require checking the code hashes recorded below and rerunning affected checks.
