# TETHER namespace migration

The public repository is [rzzli/TETHER](https://github.com/rzzli/TETHER).
The current interface is `tether-target-agents` 0.6.0 (`tether`); the engine is
`tether-target-engine` 0.4.0 (`tether_engine`, command `tether-engine`).
Imports, entry points, wire identifiers, package metadata, tools, tests,
documentation and the current paper presentation use these identities.
The migration was published in
[commit 17dc59d](https://github.com/rzzli/TETHER/commit/17dc59d3c6a0672caf2b5c653b9a81df58f0e57f).

## Preservation boundary

The original 10,226-file checkpoint is preserved exactly at
[tether-pre-namespace-migration-20261106](https://github.com/rzzli/TETHER/tree/tether-pre-namespace-migration-20261106).
Its local backup was checked against every Git blob. Frozen proof bundles and
original release recipes are absent from the current published tree; their
unchanged originals remain available through that tag. See [archive guidance](ARCHIVE.md).

The ten-case historical run registry and all 38 paper result outputs retain
their original bytes. The rebuilt 23-page paper preserves its numerical results,
table rows and bibliography. Its [presentation review](../paper/PRESENTATION-REVIEW.json)
records all-page visual inspection and ordered text checks. Author declarations
remain pending.

The current catalog has 178 products and deliberately starts with zero artifact
grants or approved uses. The original 266-artifact, 17-use policy is archived.
New runs need new source-bound grants; a namespace edit cannot authorize old
packets or certify old scientific executions. Generic version-one byte checks
remain available. Older semantic proofs need their original software.

## Validation

Final repository-wide validation passed: **2,112 tests**, zero failures, errors
or skips, all ten required probes, PowerShell syntax checks and an offline wheel
build, installation, demo and verification. The complete gate took 1,581.469
seconds. Its [retained result](TETHER-NAMESPACE-VALIDATION.json) is an exact copy
of the final local report, SHA-256
`bc4d06385f55ddcbb67e3119c10cf01977559e38ddcd4166834bb3fc50641e00`.

The following component suites also pass with zero skips. Counts overlap where
a focused suite is also in the broad repository gate; they are not a combined
count of distinct tests. The experiment suites total 905 test executions.

| Suite | Passing tests |
|---|---:|
| Public interface | 143 |
| Equal-policy comparison | 203 |
| Prospective fixtures / readiness | 110 / 53 |
| LAB-Bench fixtures | 97 |
| LitQA comparison / supplied-source / analysis | 89 / 30 / 146 |
| Inspect policy fixtures | 53 |
| SciFact numerical fixtures | 148 |
| MultiVerS invented-weight fixtures | 24 |
| Remaining comparison, diagnostic, supervision and transport fixtures | 115 |

Numerical and Inspect tests reuse existing optional dependencies read-only with
the final engine and interface packages. Native isolated workers retain their
own isolation rules. These checks do not qualify an old scientific environment
as a newly installed production runtime. Third-party `anyio` resource warnings
remain visible in the Inspect log.

The broad gate is `python -I -B tools/validate.py --mode full --package`.
It requires noneditable current packages, PyArrow 21.0.0, PowerShell 7, `uv`,
cached build dependencies and the original Git checkpoint used by historical
fixture tests. The [CI workflow](../.github/workflows/validate.yml) records the
installation sequence and fetches the required history.

The final engine and interface wheels have exactly 93 and 18 source/resource
files, respectively, all byte-identical to the current source tree and staged
Git blobs. They contain only their intended namespaces. Wheel hashes:

- Engine: `b2bfab39257ba09ec85bfb7b07201dcedd3acc20797f45f275ce2316041ee623`.
- Interface: `0a9da77e7b55f2c99149203d1c5dd8ea890919b6a7565abf72a77d3616da90b2`.

The installed offline demo passes externally anchored, source-inclusive
verification. Its receipt is
`c7b0139b8182a2a7af6d013bd19a5fb28506ffcbfd33bcab09665c86bcafdf1b`.
The [package qualification](../packages/tether/MIGRATION-VALIDATION.json)
binds these wheels, logs and installed-source checks.

## Corrections made during validation

- Rejected a wheel contaminated by a stale build directory, preserved that
  attempt, rebuilt from clean directories and added namespace allowlist tests.
- Restored exact historical test inputs through a bounded Git checkpoint reader.
  Current contract tests use explicitly invented fixtures instead of rewriting
  sealed model responses, protocols or receipts.
- Updated current version and projection assertions in experiment tests, while
  keeping historical release and qualification claims tied to original code.
- Re-pinned two invented prompt fingerprints and their byte-reservation
  expectations. Reversing only the renamed arm/stage text reproduced all 12
  archived payload fingerprints: ten stay unchanged and two change. The
  affected prompt reservation increases by exactly two UTF-8 bytes; budget
  limits and historical measurements are unchanged.
- Corrected current documentation scope and replaced removed proof links with
  links to the immutable checkpoint.
- Corrected a test that assumed a real Windows replacement always succeeds on
  its first call. A bounded diagnostic observed access error 5 followed by a
  successful retry; its underlying cause was not established. The deterministic
  no-error unit case now uses a simulated successful call, and a separate real
  write checks content and cleanup. Native held-handle and retry tests remain.

Earlier failed or interrupted attempts remain in the ignored local migration
archive. Missing optional dependencies and sandbox filesystem/socket restrictions
are distinguished from code defects; assertions were not weakened to obtain passes.

## Scientific status

The semantic-capability goal remains paused. The unfinished supplied-source
diagnostic was stopped with 93 collected slot files and no root receipt; its
partial evidence remains unchanged. No model-backed scientific execution was
restarted, no datasets were acquired, and provider spending for this migration
was $0. Renaming and fictional regression tests establish no new scientific result.
