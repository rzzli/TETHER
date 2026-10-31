# Entry suite retained accounting

This is an accounting interpretation by the Kernel3/runner author, not an independent correctness acceptance. No subject was imported or rerun.

The 594 retained artifacts contain 18,955,766 bytes. The 6,337,722-byte proof brings that to 595 files / 25,293,488 bytes; including the 397-byte first-attempt record gives 596 files / 25,293,885 bytes. Existing source/preparation/reference files and this review are excluded.

| Retained content | Files | Bytes |
|---|---:|---:|
| Source-generated immutable bytes copied by harness |48|2,744,667|
| Immutable snapshot raw256 copies |59|1,147,648|
| Immutable snapshot row metadata |59|6,942,360|
| Immutable snapshot observation metadata |59|803,184|
| Query witness copies |273|747,838|
| Latest bank raw256 copies |48|1,141,760|
| Latest canonical row metadata |48|5,428,309|

Generated ledger/journal/packet bytes originated in the source, but these physical files are harness evidence copies outside ACTIVE. Snapshot/bank/query copies are not additional reads. The run records 4,460 synthetic original dispatches and 4,461 reservations, including one explicitly unregistered row. Across worlds, source-reported known bytes exceed the spy completed-delivery counter by 116 bytes: two committed 58-byte E21 returns interrupt before the spy increment. The counters describe different observation boundaries.

E32 actually streamed 3,991,999,872 procedural bulk bytes, with 3,992,098,940 total known/hashed bytes and 99,068 captured helper/metadata bytes. Its 3,842 original calls include five once-only closes. Candidate/terminal ledgers are 1,029,226 / 1,030,506 bytes. The one read buffer is reported as 1 MiB; logical raw peak 1,196,936 is not RSS. The separately represented native bank, immutable snapshots, generated store, Python heap, compiled code, fixtures and driver retention cannot be inferred from that metric or disk totals.

The reported 9.172 seconds includes per-world evidence persistence. Final proof serialization/write and process startup/exit are outside or unmeasured; it is a cooperative 60-second suite, not a whole-process/physical/native timing qualification. The result is 50 assertion passes (one static), three explicit deferrals, and native25 not executed.

Close E08's missing external decision/output content-pin policy before treating entry admission as complete. Source3 has a captured import DAG guard but no executable current-run manifest-pin validator. The next finite slice should define that metadata schema and reject direct/transitive self/mutual current-output/decision cycles before original opens, using externally pinned TCB roots and stable prior metadata. Future CPP/parent/shim/pack nodes stay unbuilt/null until authored and built; final binary hashes must not circularly block source authoring. Native25 fixture work can proceed in parallel, while the two E16 historical invocations stay explicitly excluded/deferred. Real native leases/child/image/path lifetime, physical output budgets, full new84 roster and scientific gates remain pending.
