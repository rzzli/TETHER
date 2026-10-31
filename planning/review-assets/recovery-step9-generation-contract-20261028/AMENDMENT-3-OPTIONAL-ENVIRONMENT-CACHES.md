# Optional-environment cache qualification

28 October 2026 UTC. Prospective correction to acceptance aggregation only.
The failed v2/v3 aggregations and their helper bytes remain preserved. No
acceptance has been published. Do not change the wheel, runtime, source pins,
installed files, old copy inventory, test results or the original failed replay.

The optional extra is named `ingest` in both the existing project and wheel;
the first aggregation expected `ingestion`. Five focused metadata regressions
qualify the corrected assertion. The next aggregation correctly stopped when
five copied PyArrow bytecode files differed from the copy-time inventory.

The retained builder records hashes immediately after byte-copying the Arrow
package, without preserving source mtimes, and subsequently imports Arrow with
bytecode writing enabled. Thus its copy inventory is not a post-import immutable
environment snapshot. Its successful import does not itself explain or qualify
every changed byte. Preserve that inventory and its original status as historical
evidence; never claim all 760 files remain byte-identical.

## Required new evidence before another aggregation

Produce and independently review a separate, hash-bound post-import derivation
record. Inspect the entire three-root copied file universe for unexpected files,
missing files, unsafe paths and reparse points. Rehash every recorded file.
All non-cache files, including Python source, PYD/DLL binaries, libraries and
distribution metadata, must match the original copy inventory exactly.

Only the five observed CPython 3.11 caches may be qualified as changed:
`ipc`, `types`, `util`, `_generated_version` and `__init__` beneath
`pyarrow/__pycache__/`. Require all other 755 copied files to match. Any additional
file, changed source/binary, missing file or unexplained cache blocks this bounded
correction; this is not a general permission to ignore caches.

For each of those five caches:

1. Bind the original copied hash, current cache hash/size and corresponding
   unchanged `.py` hash/size to exact approved paths.
2. Verify CPython version/magic, flags, timestamp/size header, optimization and
   expected installed filename, including nested code-object filenames.
3. Compile the pinned source without executing it and compare the complete
   marshalled code payload byte-for-byte to the actual current payload.
4. Compare old and current decoded code fields recursively, identifying any
   differences rather than treating a matching filename or timestamp as proof.
5. Retain the copy/import/report ordering and available timestamps. Distinguish
   observed source-equivalent cache derivation from an independent attestation
   of which process wrote each byte.

No Arrow import, dependency installation, cache repair, replay, model/native-target
execution or dataset access is needed for this evidence. Inspection/compilation
of Python source must not execute those module bodies.

## Narrow acceptance adaptation

After root approves the exact derivation record and an independent read-only
review, a separately named acceptance helper may consume that explicit hash.
It must check all 760 original entries against either the unchanged original
hash (755) or the exact separately qualified cache hash (five), with exact set
equality and source bindings. No caller-selected additional exceptions or
wildcard exclusions are permitted. Retain the failed helpers/observations.

Every other acceptance gate stays unchanged: full 1,774 tests/327 source pins,
protected hash-only checks, wheel and two environments, default dependency-free
behavior, installed/relocated checks, corpus/reference scope and the ten-version
combined qualification. The final acceptance must disclose this cache derivation
and must not imply that the original copy-time inventory described unchanged
post-import bytes. Native conformance and scientific validation remain open.
