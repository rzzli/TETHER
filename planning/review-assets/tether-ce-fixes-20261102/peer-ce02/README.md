# Independent CE02 review

No actionable correctness finding was reproduced in the reviewed CE02 scope.
The reviewed `local_model.py` SHA-256 is
`1bdd8f50e2db729cd8854e1ba3859e71de70833ac70a11a9ff3d0a24a56697e4`.
No production source was changed during this review.

The review inspected parsing/type checks, the dual `BackendFailure`/`ContractError`
exception, failed-response archive reconciliation, reservation/account identities,
the workflow stop condition and the full run verifier's execution reconciliation.
Standalone legacy verifier fixtures can omit journal-only fields; full sealed-v2
verification separately requires dispatch and account identities through
`check_execution`. This distinction does not weaken the tested sealed-run controls.

## Independent controls

`check_sealed_usage.py` uses its own in-memory fake HTTP transport. No model,
server, network access or closed scientific attempt was invoked.

- `new-v2.json`: three complete write/seal/source-inclusive verification paths.
  A fully valid response reporting 1,000,000 input tokens produces one call, one
  usage violation, zero claims, full adapter-reported accounting and a
  `budget_exhausted` result. A boolean token count remains unqualified; timeout
  has no known usage. Both unknown cases retain quoted accounting and one failed
  attempt per available category, without same-call retries.
- The same record retains four rejected mutations: wrong attempt identity,
  changed reservation, swapped account associations, and changed unknown usage.
- `old-v1.json`: the frozen installed engine 0.3.11 independently produced two
  fictional failed-run archives (boolean count and timeout), with receipts.
- `old-reverified-v1.json`: engine 0.3.12 accepts both old archives against their
  unchanged external receipt hashes and original sources. It correctly reports
  `code_matches_current=false`; byte identity does not pretend old code is new.

`new-v1-failure.json` retains an initial peer-assertion mistake: the script indexed
a frozen `Usage` object as a dictionary. Encoding the trace before dictionary
comparisons fixed the harness; no runtime fix was required. Its generated files
remain in their original cache directory.

These controls complement, not replace or add independent scientific observations
to, the implementation agent's test suite. They cover the canonical local
selection adapter and core run artifact path, not all alternate adapters or an
operating model server. Adapter-reported token counts are not independent physical
usage attestations. The approved malformed-content/count policy still treats
unqualified responses as unknown estimates.

## Reproduction

Use the aligned 0.3.12 development interpreter with `-I` and mode `produce-new`;
use the retained installed 0.3.11 interpreter with mode `produce-old`. Then use
0.3.12 with `reverify-old`. Each invocation takes a fresh cache directory (or the
old directory for re-verification) and an exclusive results filename. Retained
compact JSON records identify all generated run directories and receipt hashes.
