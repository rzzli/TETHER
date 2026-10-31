# Independent captured-journal review

**Hold the known-launched terminal-completeness claim.** Frozen source`5b86f70a…`
accepts five contradictory synthetic terminal bindings: nonempty terminal errors,
failed drain status, boolean poll count, missing drain status/count, and a drain
claiming `observed_pipe_EOF` whose final known availability is zero rather than
the EOF sentinel `None`. The last probe has a matching, correctly rechained
availability event and valid poll order.

These cases return`source_order_validated=True` and
`complete_known_launched_native_journal`. The profile/resource flags remain false,
but the narrower source completeness claim is still incorrect. Require a
source-normal terminal projection, empty errors, strict status/count coherence,
and explicit observed-EOF termination before this policy can be cleared.

Seven independent methods reproduce all30 frozen fixture expectations and add
rechained order/reference/bool attacks, raw framing/Unicode/duplicate-key probes,
deadline exception identity and nested immutability/input-detachment checks.
Two methods expose five failed assertions for the accepted contradictions; the
other checks pass. No material blocker was found in the bounded chain-only scope.
Raw resource correctness remains a separate gate.

The original source, fixtures and nine-method author proof are unchanged.
The author proof remains valid baseline evidence but does not cover these faults.
Only the new pure component and synthetic fixture bytes were used. No actual old
archive replay, original-source closure/rehash, payload, SDK, target or native
compiler operation occurred. No runtime/profile/scientific qualification or
repair of the original negative experiment and timeout follows.
