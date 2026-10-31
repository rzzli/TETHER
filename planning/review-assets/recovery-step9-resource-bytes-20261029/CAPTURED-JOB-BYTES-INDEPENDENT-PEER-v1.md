# Captured Job bytes: independent source and pure review

The exact decoder `fd655c8b…` has no material blocker within the frozen contract's narrow byte/selected-phase scope. This is not a live Job, source-provenance, process-ownership or resource qualification.

I read the complete component, contract, fixture expectations and author checker/proof. My [separate checker](check_captured_job_bytes_peer_v1.py) passed seven methods: all 16 frozen captures and 18 phase expectations, plus 49 independent vectors. The [retained proof](CAPTURED-JOB-BYTES-INDEPENDENT-PROOF-v1.json) binds the exact source/evidence and confirms no changes to the author's files.

The independent vectors construct bytes with explicit little-endian `int.to_bytes` fields. They check signed64 time extremes, unsigned32 counter maximum, unsigned64 PID extremes, byte offsets, reverse-endian corruption, 16-PID capacity, variable returned lengths and nonzero unused tails. An empty list may report eight bytes; a one-PID list may report 16. The contract permits other lengths within the complete-prefix/allocated-frame range; this review does not assert which lengths an OS will produce.

False API returns retain undefined fields despite plausible bytes/error0. Missing queries remain missing; an independently valid other query remains decoded. Bad flags/hex/lengths stay bounded and malformed. Source summary booleans cannot match integer fields through Python coercion. Invalid query windows retain decoded data while blocking raw completeness. Valid sequential-but-inconsistent accounting/PID tuples remain mismatches with race/unknown-cause scope.

The selected-phase checker requires the exact decoder-result type, a declared phase and a strict PID. It retains immutable state with fresh detached dictionaries/lists. Its matched result is only a match to the selected tuple; resource qualification is always false, atomic-snapshot evidence is always false, and non-atomic race possibility remains true. Public Python dataclasses are ordinary API types, not hostile-Python isolation or source-authentication capabilities.

There was no actual SDK/OS query, child, native/model call, original payload or old-report replay. A future report gate must still bind captured bytes to source/owner/journal/phase chronology, raw limits/peaks, output accounting, reaping, cleanup, clock and terminal seals. Existing negative experiments and incomplete external verification remain unchanged.
