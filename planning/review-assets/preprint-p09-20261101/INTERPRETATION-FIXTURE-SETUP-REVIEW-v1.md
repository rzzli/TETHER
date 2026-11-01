# Interpretation fixture setup correction

The original intermittent setup failure did **not** recur in the unmodified targeted run: the quote test plus complete module passed 33 invocations in 7.722 seconds. The partial core log also records that same quote test passing, while the full log records one setup `PermissionError` at replacement of the copied case. The source fixture is Archive32 without a read-only flag, and its JSON read closes before replacement. The original transient cause remains unknown.

A controlled Windows handle experiment reproduces the exact `WinError 5` path: after copying the fixture, hold a read handle permitting read/write sharing but denying delete sharing on the copied `case.json`. The old setup fails at `os.replace` before the quote test executes. This establishes an equivalent failure mechanism, not the identity of the original lock owner or an antivirus diagnosis.

Only `tests/test_science_bounded_interpretation.py` changed. Its setup excludes `case.json` from the copy, reads the original case, and creates the identical adapted T6/endpoint=None payload once at its destination. An absence assertion prevents accidental reintroduction of copied-destination replacement. The other six files remain byte-identical copies, and the complete input inventory is unchanged. The case transformation is preserved; only the unnecessary overwrite disappears.

The same controlled handle probe now passes setup and the quote/foreign-premise rejection behavior. All **32 unchanged module tests pass in 7.017 seconds**. No test-body assertion was weakened, no method added/removed, no retry or suppression introduced, and no `src/asof` or production tool changed. Later deliberate test mutations continue to use the unchanged production writer and fail normally on errors.

The JSON binds before/after code pins, retained logs, controlled-fault evidence and payload-equivalence checks. Broader second core/full gate qualification remains root-owned; this targeted result does not assert its outcome. No provider originals or model were used.
