# Independent validator component qualification

This directory retains development unit evidence for BG02's independently
implemented validator. These are fictional component controls, **not scored
benchmark cases or evidence of held-out accuracy**. The independently authored
oracle, policy freeze, native materialization and paired execution belong to
the coordinating stage and remain separate.

## Implementation boundary

- `experiments/equal_policy/independent.py`: source admission, temporal and
  lineage checks, source/receipt byte identity, deterministic features/scorer,
  core artifact verification, execution accounting/state and recovery inspection.
- `independent_schema.py`: explicit standalone wire schema tables and normalized
  JSON representations, including strict integer/boolean distinctions.
- `independent_local.py`: local request/retrieval, canonical/shared-field wire,
  prompt, retained response/usage checks, plus archived replay request binding.
- `independent_render.py`: deterministic dossier reconstruction from fields.
- `tests/test_equal_policy_independent.py`: fictional unit controls.

These modules import no TETHER/AsOf implementation, admission, serialization,
fingerprint, feature, scorer or verification helpers. A retained AST test checks
that import boundary. The implementation author read the supported contracts
and runtime code to recover exact policies; this is **not a clean-room or blind
scientific replication**. Contractual literal strings and wire field names must
agree. Dependency grouping uses an explicit undirected graph traversal and
feature means use rational accumulation, separate from the runtime helper.

The schema-two artifact-policy/outer-launcher implementation belongs to the
other assigned implementation agent. The core delegates that boundary to
`independent_policy.py` rather than silently excluding its obligations.

## Unit evidence

| Record | Tests | Result | Scope |
| --- | ---: | --- | --- |
| `unit01.json` | 37 | Pass | Initial source/feature/scorer/archive/local/recovery controls |
| `unit02.json` | 38 | Pass | Added declared archived replay binding and diagnostic code pins |
| `unit03.json` | 42 | Pass | Added accepted source-linked claims, rehashed claim/journal tampering and bare-core code diagnostic |
| `worker-red01.json` | 52 | Fail: one | Isolated worker exposed editable development environment source paths |
| `worker-green01.json` | 52 | Pass | Worker removes repository product source paths and reports this boundary |
| `worker-green02.json` | 52 | Pass | Worker also restores the calling process's import paths after embedded unit checks |

Successful records have zero failures, errors and skips. JSON records pin the modules,
test file, driver and complete log; source hashes before and after each run
match. Earlier records remain retained after later development changes. No
provider, network, downloader, model or protected scientific payload was used.

Reproduce with a new evidence name, from the repository root and with `TEMP`
and `TMP` set to a writable fresh project cache directory:

```powershell
& data/cache/tether-051-dev/Scripts/python.exe -B `
  planning/review-assets/tether-equal-policy-20261102/independent/run_units.py new-name
```

## Deliberate distinctions

- Preparation admits inputs and preflights configuration. It does not synthesize
  workflow output, quote/consume budgets or claim an execution result.
- Excluded future or unavailable records differ from malformed input rejection.
- T6 and inapplicable scorer abstention differ from invalid scorer configuration.
- Generic internal exceptions return `error`; they are not credited as correct
  policy rejections. Explicit policy failures carry obligation IDs.
- Bare-core code inventory mismatch is diagnostic. The outer launcher has the
  stronger matching-version requirement.
- Legacy v1 is outside the current-v2 comparison and reports unsupported scope;
  this does not declare historical receipt-only archives invalid.
- Retained replay documents are sufficient for request/selection reconstruction;
  original replay-file hashes are declarations when exact original bytes are not
  part of the archive. The original file path is not a new prerequisite.
- Archived replay reconstruction is a declared obligation even though the
  product verifier currently omits it. The comparison must retain the resulting
  gap rather than weaken the independent validator.
- Inspect-only recovery reads durable prefixes and never redispatches a call.

Passing these units is not full policy parity. Full native outer-policy
integration now has its separately retained qualification. Frozen corpus
execution, independent analysis and the final stage audit remain required before
BG02 can be marked complete.

## Isolated worker and diagnostic controls

`experiments/equal_policy/worker.py` accepts `--implementation`, `--root`,
`--descriptor`, and an absent `--scratch` directory. It creates scratch
exclusively, imports only the experiment tree, and uses the interpreter's
installed product packages. `-I -B` is part of the tested invocation. The parent
runner owns the hard deadline, output cap, terminal dispositions and atomic
publication. Caller TEMP/TMP must be separate from scratch.

The worker returns the decision separately from wall/process CPU time, Python
allocation peaks and the available OS process-lifetime memory peak. Lazy imports
are charged to the operation; instrumentation overhead is included. Logical
bundle byte volume comes from file metadata, deduplicating file identities where
available. It is not a measurement of reads, cache misses or physical disk I/O.
The worker's audit hook denies network connects/binds/DNS and oracle JSON reads.

`controls.py` retains a deliberately weaker hash/schema diagnostic and a
reject-all sanity arm. Units demonstrate that the first can accept a future
hypothesis or rehashed accounting contradiction while the policy validator
rejects it. Neither control is called policy-equivalent. No performance result
or prevalence conclusion follows from these component demonstrations.

The initial worker failure is retained: `-I` alone did not remove editable
development-environment `.pth` entries for repository product sources. The worker
now removes those entries and reports removed paths and loaded product-module
locations. Paired execution still requires the separately pinned installed
interpreter; this correction does not turn an editable environment into a
qualified installed release.

## Resumption qualification — 5 November 2026

The exact seven-key envelope alignment and final policy peer review had completed
before interruption. Fresh review found one remaining adapter defect: preparation
of the artifact-policy variant did not explicitly require the catalog, policy,
roots, use and frame controls before file I/O. Missing controls could reach a
generic lookup failure instead of a declared policy rejection. Eight failing
subcontrols are retained in `worker-resume-red01`, together with the exact prior
source. The correction adds the required-field guard; it changes no product
runtime, fictional source, oracle or scientific result.

Current records are `worker-resume-green01` (53 component/worker methods),
`../independent-policy/unit-resume01` (17 policy methods) and
`../independent-policy/native-resume01` (five actual native integration methods).
They all pass with unchanged source brackets. The native suite uses the pinned
installed attempt02 interpreter with `-I`. The six earlier policy peer probes
still bind the unchanged current policy module. `RESUMPTION-QUALIFICATION-20261105.json`
checks each log, terminal count and source hash, including preserved red evidence.
These scopes overlap and are not added into an independent sample size. No paired
comparison was executed during this qualification.
