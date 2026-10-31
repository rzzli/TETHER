# Root review of the verifier adapter design

29 October 2026 UTC. Reviewed design contract `0327e9088f1dc1dce09f8806c5d0cf642c4700c7893385fc44e6cf58390993ef` and its readable design. This is a source design review, not an execution or fresh-original verification.

The same-owner bootstrap is the right correction to the component clock boundary. The proposed handoff preserves the original start, journal, output reservation, live leases and fresh source captures. The entry's interpreter-startup exclusion is explicit. Loading fixed helper modules from captured bytes avoids a second source-file pass; it must have no ordinary loader fallback. The externally pinned entry/decision avoids a self-hash cycle.

Immediate ownership registration, independent known/read/hashed counters and once-only uncertain cleanup address the previously reproduced defects. These are application ordering requirements after a native return; they do not provide atomicity against interpreter allocation failure, process termination or hostile Python. Pure tests must use failures at the documented boundaries and preserve that scope.

Two details need resolution before the platform binding can be accepted:

1. The six listed file APIs cover opening, inspecting and reading a file, but not the proposed ancestor checks and bounded directory enumeration. Enumerate the actual additional APIs, flags, raw-return ownership and finite call bounds. Alternatively hold those platform operations explicitly while implementing the pure interfaces. Do not introduce an implicit `Path`, `os.walk` or SDK helper route that reopens files or bypasses the registry.
2. Freeze the new file-call limits with the actual role roster. The proposed `ceil(size/65536)+16` read headroom is a bounded policy choice, not a guarantee against all short reads. Exhaustion must be incomplete, and successful short reads must remain distinguishable from retries after failed or unreturned calls.

The real archive, journal, raw-resource and new-profile checkers remain implementation work. Their accepted inputs must be captured bytes tied to live original leases, not serialized pass flags or arbitrary paths. The output seal requires the final returned clock acknowledgment; any late or unknown return vetoes completion even when a file contains a provisional positive candidate.

Disposition: architecture suitable for the next source/pure implementation after independent review and the clarifications above. No live file, SDK, compiler, model, pack or target activity is authorized by this review. The original failed profile and timed-out external verification remain unchanged.
