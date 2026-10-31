# Unicode pack codec v2 peer review

The exact v2 correction is clear for source/pure scope. It moves bounded ID copying outside the UnicodeError data-decoding catch. No other source text, interface, field or cap changed. All four protected data regions are free of clock-callback, take and hash dispatch.

Eleven independent methods pass. Four UnicodeError-family objects preserve their identity at every before/after copy checkpoint across all 90 IDs: 720 probes. Eight preserved-v1 controls reproduce the old wrapping defect. Genuine malformed ASCII and grammar UTF8 still produce the intended CodecError with the data error as cause. V1 and the earlier peer remain preserved under the root hold.

The independent reconstruction, 84-case field checks, malformed mutations, source-profile typing, callback cancellation and ordinary immutability checks still pass. The 37,766-byte in-memory pack has the unchanged `d2537df4…32c8ab` digest.

No complete pack file, original-source qualification, old pack/model/CPU read, native call or frozen-source edit occurred. Runtime, original authentication, profile acceptance and scientific flags remain false.
