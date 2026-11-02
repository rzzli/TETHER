# Q02 sealed execution integration — TETHER 0.5.0

The new artifact-policy path is implemented and locally qualified. **129 package tests pass**, including 29 pure policy/reconciliation tests and 14 executable binding tests. An isolated installed 0.5.0 wheel executes and verifies a fictional policy-bound run, denies a mismatched frame before child dispatch, and preserves the preceding process supervision checks. This does not rerun or scientifically qualify a real cohort, dossier, genetics feature or paper result.

## Supported interface

`tether run` accepts the original schema-1 `--catalog` together with `--catalog-policy`, `--policy-use`, `--policy-roots` and `--policy-frame-sha256`. All are required for the stronger path. The roots document has `schema_version: 1` and a `roots` mapping; `metadata` is mandatory, alongside the raw/snapshot aliases selected by the use. The source catalog path must match its declared path beneath `metadata`.

The path supports offline extractive execution with no scorer, replay or local-model configuration. Policy flags on demo, ingestion, inspection or verification commands are unsupported and rejected. A synthetic-demo snapshot is also rejected for policy execution: the frozen engine intentionally ignores catalogs for that profile. Ordinary demo and ordinary schema-1 runs remain available with explicit weaker policy scope. Direct legacy Python aliases do not inherit the new guarantee.

The implementation is split between `_catalog_policy.py` (pure schema and authorization checks, owned by the data reviewer) and `_catalog_binding.py` (stable reads, copies, original receipt checks, execution redirection and replay). `_presentation.py` reserves an outer attempt first and calls the binding layer before appending an engine-dispatch event. `_cli.py` validates the supported flag combinations. Version and finite namespace registration are 0.5.0; frozen `src/asof` remains unchanged.

## What is bound

1. **Original policy authority:** exact schema-2 policy bytes, exact schema-1 source-catalog bytes/hash, source metadata fingerprint, explicit use, caller-selected frame hash and roots mapping.
2. **Complete supplied inventory:** every source node and normalized artifact, including unused nodes; exact dataset/release/root/path/hash/size/role identities and actual parent edges. Evaluator ancestry cannot be converted into a validation-only dependency to admit it.
3. **Retained provenance:** selected artifacts' declared neutral evidence files are read under `roots.metadata`, hash-checked and copied by content hash. They remain policy evidence, not additional agent-input ancestors. Unselected blocked products' evidence is not opened by this operation.
4. **Executed controls:** case, snapshot, normalized packets and locally computed mapping inputs are copied atomically without overwriting. Relative packet/mapping layouts are preserved. The child receives the copied controls and a deterministic use-specific schema-1 projection; nonselected products have deny-only roles. The original catalog is not rewritten.
5. **Raw bytes and receipts:** raw payloads remain at their approved external roots and are streamed for hash/size checks. Receipt bytes are copied into the outer attempt and identity-checked through the shared reconciler. Only path separators normalize for legacy transport receipt paths; case, dataset/release/receipt IDs, URLs, bytes and hashes remain strict. Receipt bytes are not rewritten.
6. **Finalization and replay:** the wrapper rederives the decision and projection from archived controls, checks the copied inventory and original raw/receipt bindings, repeats engine admission, and compares the actual engine case/snapshot/catalog/base/backend/scorer with the prepared values. The outer manifest and journal bind the policy descriptor. Canonical verification reports artifact-policy consistency separately from core semantics and scientific validity.

The frozen engine requires source payloads and receipt paths under the same `raw_root`. Consequently, it still reads the original pinned receipt paths; the wrapper's copied receipts do not redirect those reads. Original receipt bytes are checked against archived copies before dispatch, at finalization and during verification. This scoped solution avoids copying every raw payload or modifying the frozen engine. It is not exclusive filesystem ownership, a hostile-local-user sandbox, or a promise that external originals remain available indefinitely.

## Temporal behavior and failures

All raw informational nodes are checked, including unused ones. A newer computation date is allowed when its full informational ancestry is eligible. Record publication checks still occur while admitting the copied packets before dispatch. A future publication is excluded from the evidence store, with an explicit exclusion; an artifact grant does not override that gate. The integration regression verifies this distinction. No missing information becomes biological absence or a numerical feature by virtue of policy admission.

Invalid policy, source-catalog anchor, selected frame, provenance bytes, source/receipt identity or unsupported configuration rejects before engine dispatch. A receipt changed after preparation but before the child starts fails the child's source admission before any backend `dispatch` event. Original mutable control/packet/mapping/provenance files changed after sealing do not alter the child, which uses their copies. Concurrent attempts have one output owner; copying failures preserve the failure stage without a success receipt. Inspection never repeats a call.

Each preparation or verification pass has bounded reads and a 300-second I/O deadline. Controls are limited to 16 MiB and copied normalized inputs to 64 MiB per file. Raw originals are streamed, but repeated source-inclusive admission/verification can entail substantial I/O. These implementation limits are not measured feasibility guarantees for the entire real inventory, and the process supervisor's child deadline does not cover in-process policy preparation or post-child verification.

## Retained validation

| Check | Result | Evidence |
|---|---|---|
| Executable binding tests | 14 passed; nested copies, original-control mutation, receipt mutation, future-publication exclusion, no-clobber, write failure and concurrent ownership | `BINDING-TESTS-v5.txt`; final combined suite also uses legacy backslash receipt paths |
| Full current package suite | **129 passed in 39.013 seconds** | `PACKAGE-TESTS-FINAL.txt` |
| Independent wrapper probes | 29 assertions passed, including genuine copied-input execution, zero-dispatch rejection and resealed projection/missing-policy/cross-frame rejection | `../peer/BINDING-PROBES-20261102T084227464737Z.json` |
| Offline installed wheel | 24 members, full CRC/RECORD closure and 18 runtime source files equal current sources; original core wheel; isolated installed imports; no PyArrow | `WHEEL-QUALIFICATION.json` |
| Installed stronger path | Fictional policy run + anchored verification pass; wrong frame produces no engine-dispatch event; demo explicitly reports compatibility scope | Same wheel report |
| Prior process envelope | Actual installed timeout/overflow, capped captures, single dispatch, reaping and read-only inspection pass | Same wheel report |
| Preservation | No `src/asof` differences from `78f807c`; historical report/build files untouched by this implementation | Parent preservation checks and working diff |

Final wheel: `data/cache/tether-050-qualified-build/wheels/tether_target_agents-0.5.0-py3-none-any.whl`, **46,380 bytes**, SHA-256 **`b28f2680c675b6266c6ea6cc9cfd2002191af9f7d20396b5b2ec629a9909f8d8`**. Qualification is local Windows execution. It is not a rebuilt historical paper package or hosted CI certification; older outer artifacts require their pinned launcher versions.

The first integration tests exposed two fixture/interface errors: selected products had not yet received their explicit fictional frame-review state, and the synthetic-demo profile caused the frozen engine to ignore the projected catalog. Both failures are retained in `BINDING-TESTS-FIRST.txt` and `BINDING-TESTS-v2.txt`; the latter led to the explicit synthetic-profile rejection and a contemporary-profile fictional fixture. No source data was fabricated to complete a real dossier.

## Remaining scope

This reviewer did not execute the new wrapper against actual project dossiers or rehash the original provider inventory. The separate data review imports and checks neutral metadata; its results must not be described as a fresh original-byte verification or a scientific status promotion. Schema-2 ingestion, post-build artifact registration, scorer/training chronology, replay/model-backed execution and direct legacy-API enforcement remain unsupported on this path. Protected outcomes, expert responses, source biological rows and closed experiment runs were not opened or rerun here. New model calls, provider downloads and provider spending were zero.
