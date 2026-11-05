# Independent schema2 and outer validator qualification

This is unscored development evidence. It does not contain the paired benchmark
results, establish biological correctness, or establish complete policy coverage.
The unchanged frozen specification and its coverage ledger remain authoritative.

`experiments/equal_policy/independent_policy.py` implements schema2 product,
dependency, artifact, selected-use, receipt, temporal-bound and immutable-control
checks, plus native outer presentation/process envelope and retained policy
binding verification. It uses Python standard library and experiment-owned core
helpers. It imports no TETHER or AsOf module. The original source-inclusive inner
verification is delegated to the independently implemented `verify_core`, not the
product verifier. Different versions of the retained qualification records are
preserved; each record pins the exact source and test bytes it exercised.

The fictional unit suite covers successful preparation and retained-copy
readback, complete grant ancestry, unreferenced raw-source receipt contradictions,
alternative availability bases, transport identity, strict scalar types, path and
size limits, deadline and link rechecking, outer whole-file/directory inventory,
current-runtime identity, exact presentation projection, process reporting and
inspection accounting from one captured journal buffer. Only outer-envelope unit
isolation stubs the inner verifier, and the records label this limitation.

The native integration suite runs with the BG01 installed qualification attempt02
Python using `-I`. Only the experiment directory is added to Python's search path.
Fresh, explicitly named UNIT inputs are materialized once with the native
producer, then the independent validator reads those exact files. Tests include
scored and recorded core runs, complete schema1/schema2 outer runs and policy
bindings, externally anchored/current-code verification, source-preserving
preflight copies with backend methods forbidden, unresolved dispatch inspection,
and resealed copied-control/projection/dossier failures. Requested policy variants
must match the actual sealed surface in both directions. These tests do not read
the scored corpus's case specifications or oracle. No scientific data, server,
model, or network transport is used.

Peer review identified missing post-read link/deadline checks and permissive
boolean aliasing in the trusted-runtime schema version; these were corrected
before implementation freeze. Static review also replaced ordinary dictionary
equality with canonical-byte comparison for native proof sizes, preventing
integer/boolean/float aliasing. Whole-manifest hashing streams arbitrary retained
assets; individual JSON, journal and dossier parsers retain their declared size
limits. Inspection diagnostic exception names are intentionally normalized and
are not scored as exact strings; inspection never authorizes redispatch.

`run_qualification.py` publishes new log/result files exclusively, records all
relevant experiment source hashes before and after each run, and fails on a
changed source set, failed command, missing unittest terminal summary or failed
test result. `unit01` and `native01` retain earlier passing development states;
later records are required for any subsequently changed source pins. Unit counts
are test-method counts, not independent biological observations or estimates of
natural error rates. Native fixture files use temporary workspace paths and are
removed after these tests; the scored corpus has a separate retained preparation
and freeze process owned by the root runner.
