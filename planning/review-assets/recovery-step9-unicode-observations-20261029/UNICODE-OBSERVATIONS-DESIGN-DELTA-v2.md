# Observation design v2 clarification

V1 and its independent review remain unchanged. V2 closes the finite review batch before any trace authoring or validator implementation.

Normal completion uses sequential samples: the body time is no earlier than the previous completed row and no later than its common root time. All samples are strict unsigned 64-bit milliseconds. Positive consistency requires the explicit setup/case/coverage/selection/prefix event set at or below 117,000 ms, and every completed row—including cleanup, batch and both normal-completion samples—at or below 120,000 ms. Late cleanup/failure evidence is retained as negative/partial; these reported values never prove the actual owner clock.

Failure identity uses one reservation sample shared by the failure row root and marker. That sample and the reserved sequence enter the canonical primary-ID hash. A present failure row must match marker PID, sequence, sample, class and reason. Without a completed failure row, a marker's bounded reserved sequence remains a claim rather than being defaulted to the LF count after an unknown write. Marker elapsed time is not its publication-completion time.

At most one completed `failure` row may follow any validated normal prefix, including a complete-looking normal sequence. It is the next sequence and last completed row. A marker-only failure is distinct and remains a veto. None of these branches creates a missing success footer or establishes positive coverage.

EXE/runtime/PID/model descriptors are externally declared future context; the codec does not contain or authenticate them. The declared new-pack digest must equal the callback-bounded deterministic in-memory codecv2 encoding of its exact profile and the accepted digest. No pack file is written or authenticated by this equality.

The wire author confirmed the negative-prefix interpretation and reviewed the prospective timing choices. These are future source/validator requirements, not claims about implemented or old-run behavior. All source, parent, archive, resource, clock, runtime and scientific gates remain separate; root and peer review still precede fixture generation.
