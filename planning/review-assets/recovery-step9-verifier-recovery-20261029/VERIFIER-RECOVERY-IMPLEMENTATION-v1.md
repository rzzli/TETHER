# Deterministic verifier orchestration: source and pure tests

The new component implements the approved 300-second owner clock, with a
295-second work boundary and five seconds reserved for closure/publication. It
has no filesystem adapter, CLI, SDK calls or real archive/core checkers. Nothing
here completes the earlier timed-out verification or qualifies a profile.

`deterministic_verifier_v1.py` starts its invocation clock before constructing
any injected factory. It checks the output-key shape, requires exclusive output
ownership, admits the exact trusted roster, hashes originals through injected
ports, retains bounded captured bytes, and calls the fixed archive, journal,
resource and core checker ports. Every gate requires the current owner-local
context. The context and its byte/digest maps are immutable and cannot be
serialized as reusable authority. Source-bound factories and checker correctness
remain a separate review boundary; this is not a hostile-Python sandbox.

Returned handles and defined byte counts enter the ledger before clock,
journal or hash work can throw. Known returned bytes and hash-updated bytes are
separate. Late returns remain observations; they cannot complete a gate.
Undefined failed-read accounting remains unknown. Known original handles have
one close reservation each; an uncertain close is never retried. Required
closure failures, late finalization and missing/foreign seal acknowledgments
prevent a complete result.

Finalization and seal attempts have bounded journal reservations before their
dispatch. A seal contains a nonfinal candidate. Only the returned owner result,
after all fixed gates, known successful closes, seal return and final same-clock
check, can be complete. Failure/veto publication is best effort and can preserve
late evidence, but never adds a completed gate. A consistent source-negative
result remains negative and never a profile pass. All results explicitly deny
real profile qualification.

The joint maximum is 256 originals and 2,048 events: six per original plus
64 fixed events and 128 failure/publication slots require at most 1,728.
Capture, role-size and descriptor/collision bounds are checked before opening
originals. Future integration must preserve the full approved role graph;
the generic engine does not replace its source-bound admission checker.

The retained proof records 19 passing synthetic methods. They exercise clock,
ownership, unknown/late return, immutable-context, missing-gate, cleanup,
publication, primary-error and cap boundaries. Archive/resource contradictions
use synthetic checker stubs; they do not validate the real archive or native
semantics. The proof's measured elapsed value of zero reflects clock resolution,
not zero computation cost; the preceding direct test run reported 0.016 seconds.

The initial draft is preserved. Its defect replay was run after review and after
the corrected draft's first 17-method pass. It is a reproduction against saved
source, not a historically pre-fix test run.

A future real first-clock bootstrap, source-bound checker set and original-file
adapter require separate review and authorization. Their source/import checks
and all file work must stay under the same original clock. No live adapter,
payload pass, runtime protocol or target execution is authorized by this work.
