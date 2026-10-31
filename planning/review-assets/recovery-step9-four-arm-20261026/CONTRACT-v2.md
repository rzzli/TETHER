# Four-arm authority-bound recorded composition — contract v2

2026-10-26. Prospective engineering contract only; no implementation or execution authorized by this document. Supersedes CONTRACT-v1 without altering its bytes. Incorporates INDEPENDENT-CONTRACT-REVIEW-v1 and the completed exact-prompt token gate. The accompanying JSON fixes the machine-readable scope, signatures, limits and tests.

## Disposition and finite scope

TOKEN-QUOTE-RESULT-v2.json SHA256 `23e42fd792435435fbaee3f5a9be5481b58d3729e86f71852cde3408465c38ff` establishes 14,315 CLI-token-plus-32 input reservations, 6,144 output reservations and maximum context 3,448 of 16,384 for the six retained payloads. Six approved tokenizer children took 111.218 seconds. The original 47,753 byte-proxy failure and v1 guard failure with zero children remain retained. CLI counts are capacity evidence, not observed model usage. Neither fit nor elapsed measurement establishes that a future complete composition will finish within 300 seconds.

One invented-six-v1 universe, one literal_case_overlap_then_id_v1 retrieval policy, original selected id03/id04, unchanged request hash `fdb7c21b5d5758fabd4a17e8110b134861836bf65d0d715398a046838b40a4a5`. All candidate authority, including excluded candidates, is requalified. Six scripted cells: one AsOf interpretation and five explicitly adapted Virtual Biotech role stages; two pure baselines reserve no model calls or tokens. Actual model generation and provider spending remain zero. No real-source expansion, native run, strategy grid, MCP tool simulation or end-to-end Virtual Biotech reproduction. This is not scientific validation or closure of R09.

## Explicit trusted capacity API

Proposed additive signatures:

```
StudySession(..., capacity_policy=None)
verify_study(output, *, expected_receipt_sha256, verifier, capacity_policy=None)
TrustedTokenCapacity.describe() -> immutable descriptor
TrustedTokenCapacity.verify(request, payload, caps, quote, budget, *, deadline)
    -> immutable verified binding
TokenQuotedRecordedBackend(document, *, capacity_policy, case_deadline, interface)
    .quote(request, payload) -> Usage
    .generate(request, payload, *, timeout_seconds) -> GeneratedBytes
```

The trusted caller supplies the policy object on execution AND replay. Serialized names, backend IDs, counts or schema strings cannot instantiate/select one. Existing `_capacity` remains unchanged and is called for absent-policy legacy execution/replay. New token mode validates all the same prompt UTF-8 bytes, canonical HTTP payload bytes, response bytes, output ceiling, context, zero cost and allocated call/input/output-budget bounds; it replaces ONLY the byte+32 lower-bound calculation with an authenticated exact CLI count+32. The mode requires exact equality to the verified reservation, not merely an arbitrary larger caller count. Context includes that reservation plus `n_predict=1024`. Capacity does not establish scientific/source authority.

`TrustedTokenCapacity` is constructed by trusted code from an approved quote location and external receipt/spec/prompt/payload anchors, with current package identity and model/asset/parser identities authenticated through existing `verify_tokenization`. `describe()` binds external anchors and captured trusted implementation identity; paths are locator capabilities, not proof. `verify()` authenticates the current package, complete model/DLL/tokenizer inventory in the quote proof, exact binary-UTF8 prompt hash, whole payload hash, BOS/special/escape settings, raw trace parsed count, output allocation and quote receipt. It returns a frozen binding containing these identities, count, margin32 and reservation. No auto-tokenization, model file opening or child creation occurs in verification. Source parent authority remains independently checked by the composition.

The adapter is necessary because existing `RecordedBackend.quote` also enforces byte+32. A narrow explicit adapter reuses `_document`, `RecordedBackend.generate` one-use consumption where compatible, and the existing absolute-deadline recorded boundary. Its quote verifies the same capacity object and checks declared fixture usage does not exceed the reservation. No change to ordinary RecordedBackend. Its explicit matching StudyVerifier checks adapter class/file identity, exact scripted document/usage, policy descriptor and complete capacity binding during execution/replay; it does not infer behavior from backend_id. Declared fixture usage, conservative reserved capacity, tokenizer CPU work and actual model calls0 remain separate fields. Do not replace fixture usage with the CLI count.

## Minimal versioned artifacts and replay

Legacy configuration1/receipt1/report1 and required outputs stay unchanged. Token mode emits configuration2/receipt2/report1. Configuration2 adds required `capacity_policy` (trusted descriptor/code identity/external quote anchors) and `capacity_binding` (verified exact request/payload/token proof/reservation). Receipt2 adds required `capacity_sha256`, the canonical fingerprint of these two fields. The existing file set suffices: these fields are sealed in configuration.json, journal configuration fingerprint and receipt inventory. The verifier accepts only the exact supported schema tuples. Configuration2 without an explicit policy object fails; providing token policy for configuration1 fails rather than reinterpreting legacy byte semantics. Unknown/missing fields fail where the schema is exact. No archived class is imported.

Token mode ordering: snapshot inputs, validate source and payload, obtain/verify adapter quote and capacity binding, persist the complete configuration and prepared journal event, then reserve and dispatch. Recompute/reverify the immutable binding at finalization and replay. Legacy ordering/meaning remains unchanged. Resource proof names require exact approved packaged paths, not just matching hash sets. Parent artifact inventory retains quote proof directories, source preparation, all raw scripted responses, policies, pure results and neutral views, with explicit external receipt anchors and recomputed assignment mapping. Existing single-use, failure journaling and no-overwrite publication are reused.

Read-only `verify_tokenization(..., deadline=None)` may gain an optional absolute deadline; absent preserves existing behavior. The current helper otherwise starts its own 300-second read budget, so passing the parent deadline is required for this composition, with before/after checks around cooperative legacy helpers. This is cooperative deadline enforcement, not a hard CPU sandbox. No new process controller, scheduler or general plugin dispatch is introduced.

## Source authority, history and current-version proof

The accepted current0.3.5 parent and sizing receipts are historical feasibility evidence. After all future code/resources are frozen, create fresh CURRENT-package deterministic retrieval preparation and token receipts. Old0.3.5 quote/source package proofs cannot be removed or relabeled to authorize a future version. Requalify full invented corpus/policy and all original typed records, compare complete selected source envelope and exact parity hash. Preserve case, question, scientific fields, source references, original alias/order, coverage denominators and missingness. Do not pass this source through the old fixed-two-fixture public allowlist, fake its identity or modify those gates.

Before each child, verify accepted same-run/same-arm predecessor receipts and compute only their approved source-ID projection. No caller-supplied history, failed/unrun predecessor, generated narrative, gold or reference answer becomes evidence. Freeze scripted responses prospectively before implementation execution. Each actual stage payload then needs its own exact current quote. The full-ID hypothetical histories measured here are not universal BPE maxima. If predetermined accepted projections equal them, prove byte equality; otherwise quote the actual payload within the same bounded schedule. No repairs, source changes or budget increases after a failure; no quote subprocess on replay.

## Frozen pure baseline policy

Both methods see exactly the same full original source envelope as the six cells. A separate authority-aware wrapper authenticates it before reusing pure `_policy`/`_select` logic; the older public baseline gates remain intact. Lexical query is exactly verified `request.question.text` (the full genetic-study-report.v1 question), with no additions from case terms, histories or responses. Extractive query is null. Only each original scientific_record `/statement` is ranked/quoted; other fields stay available and preserved, not treated as extra independent evidence.

Lexical tokens are unique sets from Unicode NFKC, casefold, then Python `re.findall(r"\w+", text)`. Score is intersection cardinality, never evidence strength. Stable order is descending score, observation ID, original pointer. Zero-overlap is excluded explicitly. Extractive order is observation ID then pointer. Both: maximum3 whole excerpts; maximum8,192 UTF-8 bytes per quote; request and result each at most1,048,576 canonical bytes. These caps must also satisfy unchanged request bounds; mismatch fails, no clipping. Count/size/empty/zero-overlap exclusions remain visible, without absence claims.

Original GroundedObservation fingerprint and scientific-record Observation fingerprint have distinct named fields (`grounded_sha256`, `scientific_record_sha256`). The existing synthetic baseline's admitted_sha256 convention must not be silently reused as though it hashes the same object. Whole text, original pointer, character/UTF8 bounds, text hash and original source reference bind each quote. Empty generated interpretations/features and null probabilities remain; scientific_answer_status is not_attempted. Pure results and neutral reviewer projections/assignment are independently recomputed; labels do not assert scientific blinding.

## One unchanged budget and timing boundary

Exactly one Budget():16 calls,32,000 input,8,000 output,$0,300 seconds,max_retries1. No retry actually scheduled. Six recorded consumption attempts maximum; pure methods zero. Set parent monotonic start BEFORE fresh source qualification, code/resource proof capture, tokenizer spec/asset preparation and quote setup; finish only after all preparation, six cells, pure results, verification and sealing. Start no work first and subtract it later. Every token child is bounded by min(30seconds,remaining parent time); one per actual stage, maximum6, no search. Record setup/child/pure/cell/sealing timings separately, all inside the same total.

Parent reserves verified exact quotes before consumption, maintains aggregate reservations without refunding them to create another arm, and allocates child ceilings/deadlines from remaining shared capacity. Recorded consumption has an immediate absolute-deadline check. Recheck after long proof operations, before each quote/dispatch, and before success sealing; next remaining seconds cannot exceed prior allocation minus its elapsed time. Quote setup exceeding the shared deadline leaves readable failure/partial files, no success receipt or automatic retry. Earlier111.218-second sizing is reported separately, not execution credit; future setup must be measured anew. Replay may use its own caller-supplied finite verification deadline, but recomputes and checks the sealed execution accounting rather than claiming historical wall time is observed again.

## Gate and regressions before acceptance

Independent v2 review and explicit root implementation authorization precede runtime edits. Tests must cover unchanged legacy byte defaults; forged/lower quote without policy; old/wrong package, receipt, source, prompt, payload, spec, assets, parser or count; missing explicit replay policy; backend-ID/class-name spoofing; mutated caller data; same-run predecessor/history tampering; baseline query/hash/pointer/quote/neutral-view tampering; full-source equality; shared later-stage exhaustion including quote setup and final sealing; timeout/interruption/write failure with no duplicate consumption. Current frozen installed verifiers continue verifying their old artifacts. Installed replay must start no tokenizer, model, network or archived code.

Only after freeze and fresh current proofs may the finite invented recorded composition run. Human/scientific acceptance and the R07 native stop are not changed by this engineering contract.
