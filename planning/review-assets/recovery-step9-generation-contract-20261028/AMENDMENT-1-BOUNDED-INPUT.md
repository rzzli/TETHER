# Derived input bound for the public pure builder

28 October 2026 UTC. Prospective clarification before 0.3.11 source freeze or
acceptance. The original CONTRACT.md and implementation decision remain intact.
This does not authorize a native/vocabulary/model call.

The standalone public builder must enforce a necessary inherited precondition:
the sum of original catalog text UTF-8 bytes is at most **32,768**. This is not
a new scientific restriction or a sufficient complete-payload fit test.

Every catalog entry points to a distinct original-request string location:
statement or indexed textMiningSentences text. That string occurs at least once
in the complete original-request prompt data. Equal values at different locations
still occupy different serialized occurrences. JSON and runtime-delimiter
escaping never shorten their UTF-8 bytes. Consequently every formerly admissible
v2 preparation satisfies:

```text
sum(catalog text UTF-8 bytes) <= original prompt UTF-8 bytes <= 32,768
```

Before scanning scalar contents or encoding/hashing, validate types/IDs and reject
if the sum of decoded string lengths exceeds 32,768. UTF-8 bytes cannot be fewer
than decoded Unicode scalar characters. Then inspect/encode the bounded strings,
check total UTF-8 bytes and reject if that sum exceeds 32,768. Never truncate,
drop or replace text. Source-report eligibility at 1,800 code points remains a
separate rule; longer admissible original strings keep their reference IDs.

This bounds standalone input work and encoding buffers. Streaming alone would
bound temporary memory while permitting arbitrarily long scan/hash work. Keep
the finite grammar and complete HTTP/prompt/response caps and all post-validation
checks; this derived bound does not guarantee a request fits those limits.

Add regression evidence for rejection before oversized-string iteration/encoding,
multibyte input whose decoded count fits but UTF-8 total does not, exact boundary,
and unchanged twelve v2 fingerprints. Recheck all existing new tests and actual
production-rule pure oracles after the change. Pure proof is not native grammar
or EOG qualification.
