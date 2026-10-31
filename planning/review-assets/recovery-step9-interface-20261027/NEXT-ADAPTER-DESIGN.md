# Next R09 adapter integration: concrete scope and dependencies

Draft engineering design, 27 October 2026. Implement only after the new codec passes
its acceptance checks. This document does not activate native generation or a
server. R07 remains a retained negative experiment; human reviews are pending.

## Reuse the existing mechanisms

`native.LocalBackend.generate` already owns the one-use HTTP boundary, strict
loopback ownership checks, absolute watchdog, original response capture, partial
failure persistence and cleanup. It calls `self.quote` before its one-use boundary.
A narrow concrete adapter can reuse that transport while replacing its frozen
payload/quote contract. Do not copy the HTTP implementation into another module.
Keep old LocalBackend and NativeVerifier behavior and identities unchanged.

The new adapter must accept explicit trusted current token capacity, a positively
owned server and its model/launch provenance, an exact bound stage/payload and a
parent case deadline. Quote verifies the new renderer and authenticated token
proof before dispatch; generation takes the earlier parent/caller deadline.
Native bytes, echoed prompt/model/settings, complete positive stop, original
usage and ownership must replay through existing native checks. Budget quotes
remain reservations, not observed model usage. Over-quote usage is retained and
fails the case; no retry or automatic model switch follows.

`StudySession` already accepts an explicit backend/verifier and concrete optional
token authority. Reuse its accounting, failure and receipt families; serialized
backend/interface names do not choose executable behavior. The new trusted
verifier must bind exact adapter identity/capabilities/provenance, source request,
original eligible ancestors, same-run/same-arm accepted history, current payload,
token quote, native wrapper and the new response. Do not admit its generated
assertions to the evidence store or numerical scorer.

The existing four-arm composition already provides one budget/clock, fresh source
parents, all-candidate retrieval qualification, leases, actual-history quotes,
six role stages, pure baselines and final verification. Refactor only the
execution seam needed for an explicit concrete native mode; do not duplicate the
controller. Default recorded behavior and its accepted fixtures stay intact.
The newly exposed mode must identify generation distinctly in journals, usage,
receipts, reports and reviewer views. Synthetic fixture stimuli cannot become a
native answer or a scientific reference. Preparation alone never grants dispatch.

## Engineering acceptance before any actual experiment

1. Freeze exact adapter and provenance contracts, malformed-content behavior and
   source/quote/history/capacity requirements before implementing them.
2. Add fake-transport regressions for wrong owner/model/prompt/settings, future or
   evaluator-only source lineage, changed history/quote/package, budget exhaustion,
   timeout, partial response, interruption, measured over-quote usage, cleanup
   failure and concurrent one-use consumption. Invalid admission makes zero calls.
3. Run new valid/incomplete/abstained documents through StudySession and installed
   replay. Retain malformed/failed native wrapper bytes; verification never calls
   the server, executes archived code or repeats an attempt.
4. Preserve current accepted wheels. Full regressions, seven legacy families,
   matching-version checks and relocated supported receipts must pass before
   releasing that engineering mode. Do not assert unsupported relocation scope.
5. Qualify the existing runtime's JSON-Schema-to-grammar support separately. The
   external JSON Schema oracle does not prove that the pinned llama runtime
   implements const/anyOf/Unicode patterns identically. Fail incompatible grammar
   explicitly; do not silently fall back to a permissive object grammar.

## Separate prospective execution decision

Only a separately declared finite experiment can start the owned model/server.
Pin model/runtime assets, grammar settings, sources, stages, exact capacity and
all resource ceilings; include startup, source checks, tokenization, generation,
sealing and cleanup in the declared clock. Preserve failed denominators. Reusing
the existing model does not establish a stronger-capability control.

A synthetic interface diagnostic can assess mechanics without pretending to be
scientific evaluation. The already exposed IL6R annotation/question fit is
unqualified. Fresh R10/R12 outputs still require an exposure-qualified frame,
domain-matched source-only human references and a locked review protocol.
Independent scientific usefulness, H5 success and the clinical/genetics branches
cannot be established by fixture or grammar success.
