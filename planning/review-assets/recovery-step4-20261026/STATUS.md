# R04 framework correction record

Status: **accepted** in `acceptance.json`. Full validation passes 1,357 tests,
zero failures/errors/skips, required probes, package/demo and unchanged code pins
in 646.437 seconds. Both protected outcome hashes remain unchanged. All seven
guarded installed archive checks pass with no forbidden access or dispatch.
The current executing dependency profile is
`recovery-r04-20261026`. R03 remains a separate retained historical result.

## Corrections

| Boundary | Correction | Verification |
|---|---|---|
| Publication precision | Reject inconsistent publication date/year and explicit future dates. Preserve same-year or missing publication metadata when complete availability/lineage admission is sufficient. Never invent an exact publication date. | New store/temporal tests plus existing lineage, eligibility and source-inclusive verification tests |
| Store construction | Initialize an explicit optional snapshot base. Query-only stores remain supported; execution/finalization require a captured absolute live directory before backend preparation, quoting or dispatch. Archived stores remain read-only. | Direct construction, normal loaders, relative-base capture, missing directory, zero-backend-use and finalization tests |
| Transport/protocol errors | Local adapter normalizes known URL/HTTP failures to ConnectionError and malformed response envelopes to ContractError. Preserve original diagnostics, interruptions and fatal unknown OSError behavior. | Fake transport and full-workflow continuation tests; accounting equals dispatches; no automatic retry |
| Payload preflight | Validate the complete escaped/framed native prompt during preparation. Keep retrieval allowance, prompt bytes and token reservation distinct. Valid existing payload bytes are unchanged. | Near-cap, larger-policy/small-request, escaped/control-token and native-envelope tests |
| Contract diagnostics | Use mapping default factories while preserving canonical empty maps and strict explicit-null rejection. Retain each failed union branch in the exception cause. | Contract diagnostic tests and unchanged successful serialization/fingerprints |
| Atomic publication | Publish complete fsynced staging bytes without overwriting: Windows same-directory rename; POSIX hard link. Serialize in-process directory creation; propagate actual filesystem failures. | Concurrent publishers, destination preservation, failure cleanup and 640-call directory initialization stress |
| Windows paths | Normalize equivalent extended drive/UNC spelling without relaxing containment or unsupported device/ADS checks. | Portable identity cases on every platform; actual Windows containment and escape tests |
| Archive read bounds | Enforce declared, stat, opened and streamed JSON size limits before buffering; authenticate large parent files by streaming hashes. | Bounded-read regressions, tampering tests and seven installed relocated-run checks |

The original same-year fixture is not proof of historical leakage: an independent
information-availability bound may already qualify it. The correction is to
publication metadata consistency and explicit future information, not a blanket
ban on year-only metadata or newly computed results using older eligible inputs.

## Compatibility

The previous dependency guard correctly refused changed live helpers. That refusal
is retained in `prior-profile-refusal.json`. The compatibility review describes
the changes before updating the executing-build profile. The archived v0.2
publication gate remains copied and versioned in `asof.archive.core`; original
source, response, code pins and receipt bytes have not been rewritten.

`verify_installed.py` verifies the original seven restored run families from the
new wheel with original-root reads, archived source execution, repository tools
imports and network/child-process dispatch denied. Legacy v1 still has byte
verification only. The native failed-question artifact is inspected as a failure,
not converted into a successful replay. Historical executable code is never run.

## Retained evidence

- Before-fix temporal and contract diagnostics: `data/cache/store-temporal-before-20261026.log`
  and `data/cache/contracts-before-20261026.log` where present; exact retained
  inventory and hashes are recorded in `acceptance.json` after validation.
- Adapter before/after logs: `data/cache/backend-hardening-20261026/`.
- Atomic/path before/after logs: `data/cache/recovery-archive-design-20261026/`.
- Integrated final checks: `data/cache/recovery-step4-integrated-final-20261026.log`
  (72 tests pass).
- Independent final review: `data/cache/recovery-step4-final-peer-20261026/`.
- Full regression/probe/package and code-identity reports:
  `data/cache/recovery-step4-validation-20261026/`.
- Installed wheel: `data/cache/recovery-step4-wheel-20261026/`.

## Limits and next gates

No inference, new data collection, paid access, clinical-label inspection,
downloader change or monitor restart is part of R04. Provider spending remains
zero. Scientific reference qualification, stronger-model capacity, successful
native-question callback archive replay, hosted cross-platform CI and off-machine
durability remain separate open gates. Serialization optimization is deferred
until measured bounds justify it. No clinical or causal conclusion is added.
