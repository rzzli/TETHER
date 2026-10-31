# Actual v3 accounting diagnostic: independent result verification

**The retained one-worker OS-only diagnostic verifies within its declared finite scope. The earlier active2 observation was not reproduced; its cause remains unresolved.** No helper, Windows API, child, compiler, native target or model was executed by this reviewer.

Report SHA256 is `b4840f6e53f54077544a0268bd18c69759c7ccd12554309915735826aaeb9709`; receipt SHA256 is `e5f65eea14d335b69b5389d3e103396b3dcbfebf0b35504cb04d6314e0d0bba6`. Own Python hashing/parsing validates the exact14-file output universe, all13 receipt output pins, byte-identical effective protocol, all53 input pins, eight-event journal chain/tip/order and all five standalone/report/journal snapshot bindings. failure.json and pending markers are absent. Original16-file probe and failed five-file v2 cache remain intact.

| Snapshot | Active / total | Assigned / listed | Job PIDs |
|---|---:|---:|---|
| configured_empty | 0 / 0 | 0 / 0 | none |
| assigned_before_authorization | 1 / 1 | 1 / 1 | 29040 |
| child_ready | 1 / 1 | 1 / 1 | 29040 |
| steady_one_second | 1 / 1 | 1 / 1 | 29040 |
| after_wait_and_process_handle_close | 0 / 1 | 0 / 0 | none |

All five raw48-byte accounting buffers independently decode as four little-endian64-bit times followed by four32-bit counters at SDK offsets32/36/40/44. All five136-byte PID-list buffers decode to two32-bit headers and sixteen64-bit entries at offset8; returned lengths are8 for empty or16 for one PID, unused entries are zero, and decoded values exactly equal the reported structures. All four pinned SDK excerpts still match physical LF lines. TotalTerminatedProcesses is0 in every raw record, including the final one; it is preserved without reinterpretation.

The three metadata observations identify only PID29040, opened PID29040, canonical pinned base Python image, strict parent8256 and stable creation time134376876044298665. All three metadata handles are recorded closed. Complete started/ready markers are byte-identical and match report identity; assigned authorization and journal owner/spawn records agree on PID, parent, protocol and child deadline. The sole recorded spawn argv is canonical base Python with -I -B and this exact helper/worker protocol. No pending markers remain; atomic publication is supported by the frozen source, not by an external runtime trace.

The recorded cached-module proof names System32/KERNEL32.DLL, resolves to the exact expected System32/kernel32.dll, has matching32-character UTF16 length below32768, and records explicit-handle equality. Configured flags0x2108, active limit1 and64MiB process commit agree with the protocol and pinned SDK. Actual stdout/stderr files and all observed/retained/actual-retained counters are zero with empty SHA256s, no truncation or drain error. Report records one dispatch, no denied activity, exit87, worker reaped, process/job handles closed and no cleanup errors.

The ready-to-steady interval is1.000s. Whole child is1.140s, below8s; pre-seal elapsed is1.172s, below45s. Snapshot times are monotonic and before the recorded child deadline. Root separately observed exit0, final elapsed1.203s and tool wall1.670s; those invocation values were not independently measured by this read-only reviewer.

These are sequential, non-atomic observations of this one sleep-worker sequence. They do not establish a complete lifetime process census or universal containment, explain the older active2 result, qualify a target DLL/model native run, or complete scientific work. This verification grants no new runtime permission and requests no rerun.
