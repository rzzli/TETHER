# Verifier adapters: design for review

This proposes the missing real adapter and checker layer. Implementation and
live file work remain held. The accepted orchestration component stays unchanged;
its fake passes do not establish archive/core correctness or a real bootstrap.

The key change is a **same-owner bootstrap handoff**. A frozen entry starts its
monotonic clock before helper reads, hashing, source/import validation or factory
setup. After minimal trusted inline file/output setup, it reserves the fixed new
output and journal, freshly captures approved source bytes, then compiles those
exact bytes. The engine adopts the original origin, output ownership, journal,
lease slots and captured records. It cannot call `run_once` and start again.
Interpreter startup before the first entry action remains outside this clock.

The bootstrap is an explicit source trust base pinned by a separate root
invocation. An external root-decision size/hash pin avoids a source/self-hash cycle.
The decision and every required original still receive fresh checks under the
one clock. There is no reusable receipt, metadata TTL or serialized ready flag.
Frozen helper code is loaded from its captured bytes through a finite module map;
ordinary loader fallback and traceback source-file reads are excluded.

File acquisition must split ownership from identity inspection. A bounded owner
slot exists before `CreateFileW`. The raw return enters it immediately, before
querying identity, converting handles, allocating records or checking time.
The platform port recognizes invalid sentinels; the engine receives only an
explicit owned-slot transfer or a typed no-handle failure. Later identity failure
or lateness leaves the slot owned for one close. The old wrappers cannot be
called unchanged because they allocate before registration and close internally.

The same ordering applies to reads: save success/defined counts into preallocated
state before copying or hashing. Known bytes, hash-updated bytes and unknown tails
are separate. The existing roles helper updates the digest too early for this
contract. Its admission rules and API declarations are useful source references,
not permission to execute it or weaken exact roles. All original leases remain
live through the data checks; no final payload reread is proposed.

The real checker work is explicit:

- Archive: exact authority/build/protocol/relative locators, conditional universe,
  receipt and seal DAG, failure precedence and captured-byte hash reconciliation.
- Journal: bounded byte-based chain/framing/order checks. The existing path-based
  `read_chain` cannot be used because it reopens the file and has no owner checks.
- Resources: pure raw 48-byte accounting and 136-byte PID decoding, report/journal
  reconciliation, exact source counters/PID/limits/EOF/exit/reaping/cleanup scope.
- Core: a versioned decoder, strict gate and separate full negative observer.
  Existing pure primitives are reusable only under their exact contract; the old
  189-case/six-prefix parser cannot validate the new Unicode profile.

The Unicode profile remains draft: 84 full-response cases, four stage/payload
instances, complete piece arrays and whole-corpus deterministic selectors. Its
new pack/wire/parser must freeze separately. Metadata eligibility, generation
expectations, native observations and harness dispositions remain distinct. Pure
piece reconstruction never substitutes for tokenizer replay or scientific truth.

The output sink must preserve raw ownership/partial writes and produce an acyclic
candidate → cleanup/journal → receipt → terminal-seal graph. Its seal remains
nonfinal until the returned final-clock acknowledgment. Missing returns, late
seals and every veto prevent completion. No added postdeadline I/O budget forces
a favorable artifact; failure may remain an in-memory veto and nonzero return.

The limits stay 300 seconds total, work ending at 295, 256 originals, 2,048 events,
64 MiB capture and the existing role/row/pack/call bounds. Exact bootstrap,
source, archive and profile leaves must fit the actual roster and joint event
reservation. The contract proposes derived finite file-read caps for review;
it does not change target-call limits or promise runtime fit.

Only retained source and archive metadata were read for this design. No original
source was rehashed, no CPU/GGUF/pack was opened, and no adapter, SDK, target or
compiler ran. The old negative experiment and its incomplete external timeout
remain unchanged. The machine contract lists the targeted synthetic vectors and
separate review/activation gates required next.
