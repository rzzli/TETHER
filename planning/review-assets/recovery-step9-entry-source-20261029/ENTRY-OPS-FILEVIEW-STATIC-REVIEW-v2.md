# Frozen entry integration static review, v2

HOLD for two source defects. V1 review and all5594/source1 bytes are preserved. No subjects were imported or run.

1. Ops line132 calls `sink.close_journal`; kernel SinkFacade lines146–153 exposes `close` instead. The backend close callback is never reached, preventing the normal journal ACK/receipt/seal path.
2. Root identified that AdoptionHooks assigns `c.scalar/count/error/error_definition` before publishing to the authoritative synthetic native bank (kernel995–1082). `observe` stages then commits (257–262), so a precommit failure leaves populated Python fields with noncommitted native authority. `handle` (893), `defined` (898) and cold projection still trust those fields; reconciliation (1549–1553) does not undo them. Quarantine stops work but cannot justify a close right or known-count observation from staged data.

The F2 correction must also preserve the converse: committed bank facts remain known for cleanup/cold reports if a subsequent cache store fails. Native bank state is authoritative; distinct Python delivery evidence may be retained separately. Cold reporting must not heal a failed fold or retry work.

Root plans finite unchanged-source pre-fix probes, then a separately named coherent correction. The reviewer authored the kernel and did not author Ops/FileView; this is not an independent whole-kernel proof. Native owns that separate evidence lane. All physical/native/full-roster/resource/scientific qualifications remain false.
