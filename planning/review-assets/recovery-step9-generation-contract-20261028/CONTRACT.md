# Prospective generation contract: pure v3 preparation

28 October 2026 UTC. This is a new engineering version, following the terminal
[unchanged-schema converter negative](../recovery-step9-native-grammar-20261028/DISPOSITION.md).
That result, the original 109 cases, old wheels/receipts and R07 stop remain intact.
This contract authorizes pure implementation and offline validation, not another
converter call, vocabulary loading, a server or model inference.

## Purpose and version boundary

Implement `source-quote-interpretation-v3-gbnf` using a deterministic
`strict-interpretation-gbnf-v1` renderer. Keep the existing v2 renderer, payloads,
post-validator and native v2 route unchanged. New preparation must be rejected by
old payload reconstruction. The new route remains preparation-only and is not
selected by the case controller until its separate native and resource gates pass.
Accepted software remains 0.3.10 until a separately versioned 0.3.11 package passes
its full acceptance checks. Working source changes must be labeled accordingly.

Create a pure GBNF builder and a separate v3 payload/response preparation module.
The new HTTP payload uses `grammar`, without `json_schema`; the original complete
acceptance schema is archived outside the HTTP payload. The exact pinned GBNF
guide documents this server field. No permissive converter or alternate-backend
fallback is introduced. Grammar, generator/domain identities, acceptance-schema,
request, catalog and final payload fingerprints must be reproducible and bound.

The preparation artifact says `execution_authorized: false` and native conformance
unverified. It provides neither source authority nor an exact-token reservation.
No automatic dispatch follows a generated grammar string or passing pure tests.

Public pure API: `interpretation_grammar.build_grammar(quote_texts,
claim_limit=3)`, with keyword-only claim limit and a mapping of contiguous
`Q0`–`Q(n-1)` IDs to original strings. Validate exact IDs/scalar text; render in
numeric ID order independently of mapping insertion order. Return a deeply
immutable artifact with `generator`, `grammar`, `grammar_sha256`, `grammar_bytes`,
`serialization_domain`, `quote_ids`, `source_report_ids` and
`post_validation_only`. Inference reference order remains unconstrained.

`interpretation_generation.prepare_payload`, `request_from_payload` and
`validate_output` retain the v2 call signatures under the new interface identity.
Preparation includes `generation_grammar`, `acceptance_schema`,
`native_conformance: unverified` and `execution_authorized: false`. A validated
response has kind `source_quote_interpretation_v3`, the new interface/payload
identity and `generation_contract_sha256` (fingerprint of the grammar artifact).
Original response text/quotes, empty features and null probability are preserved.

## Decoded answers and serialization domain

Preserve the existing accepted decoded answer domain. Do not trim, normalize,
sort references, deduplicate, reduce sources or rewrite authored assertions.
Strings contain Unicode scalars, including controls, noncharacters, combining
marks, U+200B and U+FEFF. Paired JSON surrogate escapes decode to one scalar;
isolated surrogates cannot survive existing strict UTF-8 canonical serialization.
Length means decoded Python code points. Nonblank means at least one character
outside the existing explicit `str.strip()` whitespace set; leading/trailing
whitespace within a nonblank value remains valid.

Generation uses compact JSON with fixed sorted field order. This restricts byte
spellings/object order, not decoded answers. All decoded less-than characters
are represented by a JSON Unicode escape, never raw `<`, in known literals and
free text. This value-preserving spelling prevents runtime delimiter/stop text
from being formed across character atoms. Generic strings otherwise may use raw
valid scalars or JSON escapes, including a high/low pair as one logical character.
Known source-report literals may use one declared exact JSON spelling: every
eligible decoded literal must remain representable. Literal serialization must
avoid embedding a runtime stop/control delimiter when an equivalent JSON escape
can preserve the value. Alternate valid spellings outside the generation domain
remain accepted by the unchanged trusted post-validator; classify corpus results
by both semantic validity and declared serialization domain. Do not normalize
documents or replace the old corpus to manufacture native agreement.

| Constraint | Generation grammar | Trusted check retained |
|---|---|---|
| Exact four root/claim fields, no extra or duplicate keys | Enforce via fixed productions | Strict parsing and exact field sets |
| Answered/partial/abstained state, reason and claim-count combinations | Enforce; active cap `min(3, request.max_claims)` | Existing state validation |
| Text/limitations/unresolved nonblank and at most 1,800 code points; reason at most 512 | Enforce jointly with logical-character bounds | Existing decoded text validation |
| Zero–four limitations/unresolved; inference/caution needs one–four limitations | Enforce | Existing list/kind checks |
| Source-report literal and its one quote ID | Enforce exact pair | Original text/pointer/hash expansion |
| Inference/caution one–two distinct quote IDs, in either order | Enforce with shared finite-set rules | Exact per-ID/source-pointer uniqueness |
| Quote longer than 1,800 code points | Keep its ID available for inference/caution; omit only its impossible literal source-report branch | Existing bounds and original catalog |
| Global claim-text uniqueness, raw/canonical response bytes | Post-validation only | Unchanged complete validator |
| Source/request/history authority, temporal eligibility, scientific entailment | Outside grammar | Existing controller checks or independent scientific evaluation |

## Bounded construction

Use named, shared productions. No left recursion or unbounded repetition is
needed. A logical JSON-character atom consumes one decoded scalar: raw character,
short escape, non-surrogate BMP escape, or one complete high/low escape pair.
Whitespace and nonblank atoms partition that same decoded domain. Do not count
escape bytes or individual UTF-16 halves as separate logical characters.

For exact length `2^k`, use `A` (any), `W` (all whitespace) and `N` (nonblank):

```text
A(k) = A(k-1) A(k-1)
W(k) = W(k-1) W(k-1)
N(k) = N(k-1) A(k-1) | W(k-1) N(k-1)
```

The two N alternatives are disjoint according to whether the first half contains
a nonblank character. Base atoms have length one. For length at most `n`, let
`m` be its largest power of two. Split disjoint length ranges below/above `m`,
then split above-range strings by their first block's nonblank state. Memoize
helpers; omit an impossible nonblank length-zero branch. Never independently
bound a whitespace prefix and a suffix at `n-1`: their sum can exceed `n`.

For distinct reference pairs, build a balanced set tree. If `S=L∪R`:

```text
IDs(S) = IDs(L) | IDs(R)
Pairs(S) = Pairs(L) | Pairs(R)
         | IDs(L) comma IDs(R) | IDs(R) comma IDs(L)
```

Omit singleton pair branches. Every ordered distinct pair has exactly one
lowest-common-ancestor cross branch. This preserves both orders with linear
shared structure instead of enumerating 65,280 pairs at catalog size 256.

Construction is finite: catalog at most 256, text/reason bounds fixed, grammar
source at most 65,536 UTF-8 bytes. Keep the original 32,768-byte prompt,
65,536-byte complete serialized HTTP payload and 256 KiB raw/canonical response
limits. Measure JSON-escaped grammar cost inside the payload. Oversized requests
fail explicitly before dispatch, without pruning. The nominal catalog maximum
does not guarantee a complete request fits. Preserve old preparation preflights;
report any previously admissible case the new grammar cannot fit.

## Implementation and validation sequence

1. Retain independent design/semantic reviews and a pre-change source/version
   checkpoint. Add failing new regression tests before implementing the feature.
2. Implement pure grammar construction, separate v3 preparation/reconstruction,
   immutable artifacts and validation through the complete unchanged v2 semantic
   validator with new payload/version binding. Add no dispatcher/model adapter.
3. Check small exhaustive languages against independent finite oracles: joint
   length/nonblank properties, all ordered distinct reference pairs, and boundary
   Unicode/escape semantics. Test malformed/oversized input and mutation/binding
   rejection. Pure/structural tests do not establish native recognition.
4. Preserve all 109 old cases; freeze additional Unicode/escape/order/domain
   cases separately. Record acceptance-schema, strict-post and intended generation
   domain statuses independently, including the claim-uniqueness exception.
5. Prepare all existing synthetic stages and the six archived exposed IL6R
   requests without raw-data access, inference or new tokenizer children. Record
   prompt/grammar/serialized payload bytes and explicit coverage/missingness.
6. Qualify 0.3.11 with affected regressions, full tests/probes/package, isolated
   default-runtime preparation/validation, relocation, seven legacy families and
   all ten matching preserved 0.3.1–0.3.10 verifiers. Update documentation, TODO
   and memory only to the level supported by retained results.
7. At major acceptance or a terminal feasibility failure, reassess R01–R16/HR1–HR4
   in a new document and critically review the next native/resource gate.

## Separate next gates and stop conditions

Actual native document/EOG qualification requires a new fixed protocol. No
vocabulary-free recognizer is currently exposed by the inspected actual DLLs.
The smallest identified route uses public typed C sampler APIs and an explicitly
qualified vocabulary-only model handle. Exact header closure, loader early-return,
CPU/device behavior, model-file access, owned cleanup and resource limits must be
established before that call. A source-built character/EOF validator is different
evidence and cannot replace actual-vocabulary EOG checks.

Separately profile the existing 295.922/300-second simulated case before real
startup/inference. Preserve that observation; no larger budget, favorable-time
retry, smaller substitute or weakened hashing/admission is authorized here.
Performance corrections need prospective scope, measured causes and their own
regressions/versioned replays. Grammar success alone cannot establish case fit.

Stop this implementation if a decoded answer is lost, a required grammar
constraint is demoted, a retained supported case cannot fit, finite construction
cannot be validated, or compatibility fails after reasonable debugging. Preserve
negative evidence and revise prospectively rather than cherry-picking cases.
Human references/source sufficiency/fresh cases remain separate requirements;
pure engineering cannot activate R10/R12 or clinical/genetics/scorer branches.
