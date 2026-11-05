# BG02 focused causal review after the frozen comparison

Date: 2026-11-05. Reviewer: separate code-reading agent; this is an engineering
review, not independent scientific validation. All observations are fictional.

**The frozen comparison finished, but matching decisions do not establish complete
policy parity. A copied-bundle diagnostic confirms an archived-replay verification
gap in the qualified TETHER runtime, masked by an unrelated dossier-order defect
in EP075. EP077 also has an inconsistent observable oracle.**

The 1,296 scored cells, oracle, frozen code and package payloads are unchanged.
The recorded TETHER/independent decision agreement remains 108/108 unique cases;
each has 107/108 full-observable matches under the original oracle. Three
repetitions are repeated executions, not independent examples. The diagnosis
below must accompany those figures; it must not silently replace scored cells.

## EP075: a confounded reject masks missing archived replay verification

Frozen intended obligation: EP-EXEC-02, “Recorded selection binds the request
fingerprint.” The declared mutation changes the first retained replay entry's
`request_sha256` to 64 `f` characters, updates the retained replay proof and
configuration, and reseals affected artifacts. The genuine dispatch request hash
is `4be711d8d6d4763809d2bbeb52e261f76b8f01dd4d4d6497334acd768920cf80`.

All three frozen repetitions return these different reasons:

| Implementation | Decision | Actual reason |
| --- | --- | --- |
| TETHER | reject | `TETHER execution semantics: dossier prose differs from deterministic rendering` |
| Independent | reject | `Replay/request fingerprint mismatch`, EP-EXEC-02 |
| Hash/schema diagnostic | accept | Semantic replay binding is unchecked |

The confound is precise. `materialize.py:109` changes the configuration and
rewrites `run.json` using sorted-key canonical JSON. This alphabetizes the
insertion order of its `coverage` mapping. The installed dossier renderer
iterates that mapping in insertion order, while the previously generated dossier
still lists specialists in the original order. The retained
[`dossier-only.diff`](ep075-causal-attempt01/dossier-only.diff) contains only this
specialist-table row-order difference. The unrelated failure is not stale
configuration prose.

The installed `asof/artifacts.py:228` explicitly checks local-model execution
archives but has no analogous recorded-replay provenance reconstruction branch.
`ReplayBackend._next` in installed `asof/agents.py:124` checks the request during
new quote/select execution. That runtime check does not validate a later sealed
archive whose replay document has been modified and consistently resealed.
The independent verifier does reconstruct recorded requests through
`independent.py:1016` and `independent_local.verify_replay`.

A retained **post-hoc diagnostic**, not a new scored observation, copied the
whole EP075 bundle to this review directory. It used the qualified installed
interpreter with `-I -B`, reconstructed the deterministic dossier from the copied
archive, and changed only these copied files:

- `run/dossier.md`: refreshed deterministic table order;
- `run/receipt.json`: updated only the dossier output checksum;
- `descriptor.json`: updated the external receipt anchor for this diagnostic.

The invalid replay fingerprint and all source/replay/configuration/journal bytes
remained unchanged. TETHER then **accepted**, reporting source-inclusive
`semantic_consistency: verified`; the independent validator still rejected the
replay mismatch. Every frozen source, bundle, directory, oracle, trusted-runtime,
installed-runtime and interpreter check passed before and after the diagnostic.
Absolute source references in the copied archive continue to read the unchanged
original corpus; no product source or installed package was modified.

Evidence: [`ep075_causal_probe.py`](ep075_causal_probe.py),
[`RESULT.json`](ep075-causal-attempt01/RESULT.json). This demonstrates an
actual qualified-runtime gap against the frozen EP-EXEC-02 specification, not
merely a possible missing test. The original EP075 TETHER rejection cannot be
credited as exercising replay binding. A later correction needs a fresh fixture
version that keeps unrelated derived views consistent, positive recorded-run
controls, changed request/selection/usage controls, and an updated release/run.
The current failure must remain visible.

## EP077: the reject decision is correct; the observable oracle is inconsistent

EP077 corrupts the final complete `dispatch` event's reserved input-token count
without updating its hash. The line ends with a newline. It is neither a valid
event nor an unterminated partial tail eligible for inspection-only truncation.
TETHER rejects `Trace hash-chain failure`; independent and hash/schema reject
`Journal chain mismatch`, consistently in all repetitions.

`cases.py:300` assigns `unresolved_attempts: ["genetics:1"]` and
`recovery_may_dispatch: false` to **every** `unresolved_dispatch` producer,
including the corrupt EP077 case. Those observables appropriately describe valid
EP076, but EP077's only dispatch is the very event whose integrity was invalidated.
Neither the common result contract nor EP-FAIL-01 requires a recovery result from
a rejected corrupt chain. Reporting that attempt as established would rely on the
invalid event. The current adapters return empty observables on rejection.

Thus the original full-observable mismatch is a real frozen-oracle mismatch, but
it is not evidence that the implementations redispatched or lost a valid recovery
result. Preserve the original 321/324 fully conformant cells per equal-policy
implementation. Explain the defect rather than retroactively deleting EP077,
changing its expected fields, or counting it as fully conformant. A later oracle
revision should limit recovery observables to valid inspect-only cases and retain
separate corrupt-chain rejection cases. No implementation change is justified
merely to invent recovery data that the corrupt journal cannot establish.

## EP057: the hash/schema arm's three errors are one repeated file-kind defect

The raw source path `input/source.json` is a directory. The hash/schema arm calls
`controls._hashed` → `independent.file_digest` → `Path.open('rb')`. The helper
translates missing files into policy errors but does not translate directory or
Windows `PermissionError` failures. The arm's broad unexpected-exception handler
therefore correctly labels the observed exception `error`, not `reject`.

All three error cells are EP057 repetitions 1–3, and all report this same
`PermissionError`. This is a control implementation/file-kind handling defect,
not a timeout, model failure, or three distinct cases. TETHER rejects via its
source checksum/file-kind guard; independent likewise rejects source-byte
mismatch. Their decisions establish rejection of this input, though the reason
codes do not isolate a dedicated file-kind exception.

The primary analysis retains the hash/schema errors in the denominator and does
not count them as successful rejections. Preserve that reporting. A later version
may add explicit regular-file checks and a directory regression to the diagnostic
arm; do not repair or rerun it within this freeze.

## Retained evidence and next gate

[`FOCUSED-RESULT-EVIDENCE.json`](FOCUSED-RESULT-EVIDENCE.json) retains the 36
relevant terminal results, their file hashes, schedules and primary-analysis
projections; [`collect_focused_findings.py`](collect_focused_findings.py) creates
that extract without rescoring. Its SHA-256 is
`3ce4103627809c3c18883d9f24e0ee5d1d774a327adc9a65ee0d242b34d07a7a`.
The frozen comparison anchor is
`26b30fef132fc6ce6acd6f1844a41521da47fb091d53e513d4b14588db476736`.

The copied diagnostic executed successfully with all five causal assertions
true. It made no provider call, changed no protected outcome, and left the frozen
comparison intact. These findings prevent a full equal-policy conformance claim
for this release despite 108/108 decision agreement. Independent reconstruction
of all scored outputs and the remaining coverage review are separate obligations.
