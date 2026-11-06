# Scope of the paired native comparison

Recorded while generation is running, without opening answer keys or computing
interim native scores. This clarifies interpretation; it changes no frozen
producer, input, scorer, policy or budget.

Raw and checked arms share the source collection, source-eligibility preparation,
model, prompt, grammar and captured candidate bytes. The raw arm is therefore not
an end-to-end system that never uses TETHER. It is the same candidate before the
additional admission decision. Reporting an incremental checking duration does
not measure all shared provenance, source-verification, transport or runner costs.

The grammar already constrains answer indices and offered evidence identifiers;
native parsing further constrains the response before the admission check. A high
admission rate on these constructed valid interfaces is expected and does not
establish semantic correctness or a benefit over unconstrained generation.
Incorrect-but-source-bound answers may be admitted. With identical candidates,
the filter cannot increase correct answers per scheduled task; it can change
retained coverage, selective precision and policy violation rates.

The finite malformed/invalid fixtures and BG02 policy constructions test rejection
behavior under explicit faults. They are not estimates of natural fault prevalence
in scientific work. Conversely, the native task measures the exact producer's
answer-key agreement and data-access limitations, not the entire therapeutic
contract or scientific source entailment.

Keep four quantities distinct in reporting: total workflow cost, shared source and
generation cost, directly measured additional checking cost, and useful native
answers retained or lost. A later equal-policy Inspect study addresses runner
portability and complexity. A separately frozen retrieval or repair intervention
is required to test production of better answers.
