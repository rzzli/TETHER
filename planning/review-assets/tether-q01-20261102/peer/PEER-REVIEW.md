# Independent Q01 process and CLI review

Final review: 2 November 2026 UTC. Current source is TETHER 0.4.2 with the unchanged AsOf 0.3.11 engine. This review is limited to the new owned-child process supervisor, its canonical CLI integration and declared verification properties. No original experiment or provider-data build was rerun. No model, network, protected-outcome or human-response inputs were used.

## Result

**116 assertions passed across three independent fixture scripts on local Windows.** These assertions exercise distinct execution properties and include related checks of the same child run; they are not independent observations, scientific evidence or a whole-project test total. Earlier exploratory runs remain retained and are not added to that final count.

| Probe group | Final checks | Observed behavior |
| --- | ---: | --- |
| `probe_supervisor.py` | 87 | Block and trickle reach an absolute deadline; stdout, stderr and dual floods reach a combined byte cap; exact-cap output succeeds and cap+1 fails; nonzero exit retains both streams. |
| `probe_boundary.py` | 19 | A genuine CLI demo completes and verifies with its policy and raw accepted invocation hash. Five rehashed/resealed process declarations are rejected. In-process paths reject explicit process controls; abbreviations fail before reservation/dispatch. |
| `probe_interrupt_delegate.py` | 10 | KeyboardInterrupt retains its original cause and reaps the child; a non-outer delegate failure prints bounded supervision diagnostics without inventing durable output or retrying. |

The supervisor group also tests a parent that exits while a finite descendant retains pipe handles, a real child whose terminate operation is injected to fail before successful kill, ten invalid-bound preflight cases and outer failure accounting. A pending synthetic call remains unresolved with a conservative 7-input/11-output reservation. An accounted synthetic call retains 3-input/5-output measured usage with no extra reservation. Failed outer runs retain terminal journals and failure records, have no success receipt, reject success verification and remain inspectable without redispatch.

## Independent implementation review

Read the complete new `_process.py` and the affected launcher/CLI integration, alongside the previously reviewed semantic boundary. The single-thread loop reads both unbuffered pipes in bounded chunks. Its aggregate allowance includes both streams; one additional counted byte proves overflow and is not retained. The monotonic deadline is checked before polling and again before accepting exit/EOF. Cleanup uses a separate deadline, preserves the primary failure and owns only the launched child. Successful outer verification binds effective limits, the supervision declaration, stream byte counts, raw accepted CLI invocation, launcher source and the existing source-inclusive dossier checks.

Three details were corrected during implementation review: numeric values could initially compare equal to Boolean EOF declarations; argparse could accept abbreviated wrapper controls that exact-token stripping would miss; and the raw CLI invocation initially lost process flags before hashing. These were static/prospective review observations; no executed failing-before claim is made for them here. The final checks reject numeric EOF declarations and abbreviated controls, and confirm the raw accepted invocation hash. Runtime changes were made by the platform agent, not this reviewer.

The five resealed negative declarations change elapsed time beyond the bound, retained byte count, Boolean EOF type, reaping status or embedded policy. Their internal hashes and new external receipt anchors are recomputed. Rejection therefore tests consistency rather than only detecting changed bytes against an older anchor.

## Scope of the guarantee

The exercised deadlines were 0.3, 0.6, 2 and 30 seconds; aggregate capture tests used 128 and 32,768 bytes. The default one-hour process envelope was not timed for an hour, and no 64 MiB output stress test is claimed. Each actual test duration is retained in its report where measured. Linux/POSIX behavior was read but not executed. Separate installed-wheel qualification belongs to the platform record.

Process creation and OS control calls cannot be forcibly interrupted by this Python loop. Cleanup bounds assume those calls return. Descendants are not terminated or contained; the fixture descendant exits independently after 1.5 seconds. A failed attempt may retain only bounded partial output and observed-byte lower bounds. A declared successful report is consistency evidence, not a trusted wall-clock, source-authenticity or billing attestation.

The child envelope applies to delegated child commands. In-process verification and outer inspection are explicitly excluded. Workflow budgets, filesystem read limits and process limits remain different controls. Generic direct legacy API calls do not acquire the canonical CLI supervisor. Hard termination or unavailable storage can still prevent final failure metadata. No unattended-hostile-execution or operating-system sandbox guarantee is established.

The final `docs/TETHER-VERIFICATION-SCOPE.md` capability table accurately separates engine versions, direct aliases, current canonical CLI verification, outputs-only checks and inspection. Its execution paragraph identifies the 0.4.2 process policy and excludes in-process verification, outer postprocessing and arbitrary embedded multithreaded Windows use. The stated single-reader CLI qualification matches these probes; installed-wheel qualification remains separately evidenced by the platform record. Biological truth, therapeutic efficacy, causal inference and model superiority remain unestablished.

## Retained evidence

`FINAL-PEER-RECORD.json` lists the three final reports, exact source/script hashes and this report. Earlier runs are retained separately. The final 116 assertions pass with no unresolved defect demonstrated in the tested Windows scope; this is a bounded independent review, not exhaustive state-space or adversarial-OS validation.

## Final documentation-only delta

The final process-module docstring clarifies the Windows single-reader/unshared-handle assumption and the unqualified arbitrary multithreaded embedding case. Replacing only those four new docstring lines with the two prior lines reproduces the exact module hash used by the final probes (`87f1948b3b1453f3c552b1e2226afb1eb6597f98ccc06d36b5ab20a31d15d3e9`). Current module hash is `37c5878f0bc51a4d3a884da19be5179a12ad89ffb2b8133aeb204aa20dfec426`. No runtime behavior changed, so the unchanged 116 assertions were not rerun solely for this documentation change.

At the final retention inventory, the peer directory contained 251 files / 1,883,368 bytes before this final note. Most bytes are two fictional demo/control trees (~0.894 MB each). Existing evidence was neither removed nor relocated; future generated trees can use an ignored fixture directory while retaining compact reports and failing cases here.
