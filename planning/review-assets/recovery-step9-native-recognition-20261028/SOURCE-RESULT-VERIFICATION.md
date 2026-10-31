# Source acquisition result: independent verification

The actual v3 result passes independent local consistency checks. Receipt
`cf2a70a3488d4dd96320d893a22e1b7706d6f913e8f5f238c9e68d4de1405f90`
binds **111 outputs**, exactly the cache file universe excluding the receipt
itself. All output hashes, **139 input pins**, approved root-decision anchors
and the **51-event journal** verify. There is no failure marker or unlisted file.

The twelve fixed-commit source files total **726,350 bytes**. Each response
record is HTTP 200 at its exact approved URL with plain-text content; every
retained file is nonempty UTF-8 without NUL bytes. Raw child reports, stdout,
empty stderr, cumulative read progress and final source hashes agree. All files
are below 1 MiB; total retained bodies are below 4 MiB. Unknown receipts and
unresolved reservations are zero. No source file was fetched again for review.

For all twelve calls, atomic launch markers, child-start records, reservations,
attempt logs and journal events agree on actual worker/Popen PID and owner PPID.
The canonical base interpreter, accepted venv context, version 0.3.11 and `-I -B`
flags match the protocol. All twelve actual-worker handles are recorded reaped,
with zero return codes, no parent exceptions, no capture errors/truncation and
full child times at most **1.000 second**, within the twenty-second limits.
No process-tree containment claim is made.

The retained terminal report measures **10.141 seconds before finalization**.
Root's execution output reports approximately 10.5 seconds through completion;
that total was not independently timed or rerun. Source bytes are retained-body
counts, not measured transport traffic. The prior failed/rejected attempts remain
preserved through the pinned inputs.

[The full verification record](SOURCE-RESULT-VERIFICATION.json) contains source
hashes, worker IDs, bounds and limitations. Acquisition did not compile or
execute fetched code, open GGUF data, load a target DLL/vocabulary/model, tokenize,
infer or start a server. This review made no network or native calls and does
not establish native grammar conformance or scientific validation.
