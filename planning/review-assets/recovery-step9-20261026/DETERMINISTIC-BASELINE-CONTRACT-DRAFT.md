# R09 deterministic baselines — engineering contract proposal

Status: proposal before runtime changes. Source inspection only; no model, real-case baseline candidate, publication comparison or scientific acceptance. Existing 0.3.1 runtime/resources remain unchanged until the coordinator confirms the installed native guard archive.

## Reuse the existing execution boundary

`StudySession` already accepts explicit `StudyBackend` and `StudyVerifier` objects and records raw bytes, package proofs, configuration, reservations, measured usage and replay. Add one narrow `asof.study.baselines` module and dedicated tests; do not add a controller, modify diagnostic/native codecs or select behavior by backend ID. Existing package proof capture should include the new module on the subsequent version, while archived 0.3.1 stays intact.

**Peer qualification:** the existing session also mandates positive `n_predict`, conservative model-style token reservations and a dispatch counter. Prefer implementing pure computation plus deterministic verification first. Session adapter classes below are conditional integration options, not approval to manufacture model usage. A tiny synthetic artifact publisher can reuse atomic writes and package proofs without introducing a controller. The coordinator must choose and document the accounting route before adapter implementation; do not change the frozen session merely to fit a baseline.

Suggested API:

```python
prepare_payload(request, *, method, limits, query=None) -> FrozenMapping
deterministic_response(request, *, method, limits, query=None) -> FrozenMapping
class DeterministicBackend:  # StudyBackend: quote/generate, single-use
    def __init__(self, *, method, limits, query=None): ...
class DeterministicVerifier:  # StudyVerifier, explicitly supplied
    def __init__(self, *, method, limits, query=None): ...
```

Methods are `extractive` and `lexical`; no aliases or dynamic imports. Freeze a strict limits object containing maximum excerpts, per-excerpt UTF-8 bytes and total response bytes. All bounds are positive exact integers (bool rejected). Initial limits must also respect the source request's max_claims and text bounds. The lexical query is explicit and immutable, included in payload and provenance; defaulting to the exact question text is acceptable only if documented in serialized config. No evaluator answer, source-result label or expected interpretation can contribute to the query.

For the first finite milestone, execute only the two authenticated packaged synthetic request fixtures. Matching requires full request fingerprint equality, not a `SYNTHETIC:` prefix or caller assertion. A pure quote/ranking helper may be tested with invented Unicode/boundary strings without making such inputs admitted executable cases. Future real-data support requires a separate explicit source-admission design; this proposal does not infer admission from hashes.

## Input checks and literal extraction

Use the existing request structure validator, then additionally require `admitted_sha256 == fingerprint(scientific_record)` for each offered row. The current codec validates source-scope fingerprints but does not explicitly check that equality. Confirm fixture source references exactly identify the synthetic unadmitted fixture kind; evaluator-only/reference/gold ancestors or undeclared extra source-reference fields fail closed. A top-level agent_evidence role alone is insufficient. Do not recursively treat arbitrary prose words as roles; enforce roles at structural metadata boundaries.

Initial eligible quote path is the explicit `/statement` string within each row's scientific_record. Do not traverse all arbitrary string leaves: IDs, fixture notices, source metrics, answer-like annotations and unknown schema fields are not quotation content. Its text must equal the bound row statement. Future nested passage extraction must use an explicit, versioned eligible-pointer policy, not a heuristic recursive collector.

Quotes retain observation ID, admitted/source-record fingerprint, original source reference, exact JSON pointer, UTF-8 byte span `[0, len(text.encode('utf-8'))]`, literal original text and text SHA256. Empty or oversized source strings produce explicit selection dispositions, never clipped text, repaired markup or invented missingness. Original Unicode normalization and HTML characters remain unchanged. Full strings only in this first contract.

Stable extractive order: observation ID, then pointer. Stable lexical order: descending integer intersection size between unique casefolded Unicode word tokens in the explicit query and in the eligible original text; then the same observation-ID/pointer tie-break. Declare the exact tokenizer (e.g. Python Unicode regex `\w+`, no stemming, no normalization and no ontology expansion). Record lexical scores as algorithmic retrieval metadata, never biological support weights. Zero overlap is explicit; choose whether to retain zero-score sources or abstain prospectively, not after seeing results. Recommended: zero-score sources are ineligible for lexical selection and receive `zero_overlap`, making this a meaningful retrieval baseline.

## Distinct response contract

Use a new schema/kind such as `exact_source_baseline.v1`, not the generative diagnostic response schema. Bind request, question, hypothesis, source-scope and policy/configuration fingerprints. Fields should include:

- Literal `excerpts` with the source/quote binding above.
- `generated_inference: []`, `features: {}`, `clinical_probability: null`.
- A deterministic selection audit for every offered eligible string: rank/score and selected, empty, too_large, zero_overlap or count_bound disposition; clear denominator and incomplete-coverage flag.
- Exact copied source coverage and missing-input declaration. Never convert unselected or missing material into absence of evidence.
- `selection_state: complete | partial | empty` and explicit reasons; these describe the extraction operation, not whether the scientific question was answered. Do not label literal copying an answered biological interpretation.

Serialize complete response first and enforce total UTF-8 byte capacity, including JSON escaping, hashes and audit overhead. Recommended fail closed if the whole result exceeds capacity; do not silently drop audit records or trim a selected quote until JSON fits. A per-excerpt bound can produce a retained omission disposition, but a full-envelope overflow is a failed cell. Limits and all rules are identical across methods except the declared lexical rank/zero-overlap rule.

Reviewer-visible projection must be separate from the audit envelope: neutral externally assigned label, original literal quotes/source references, generated-inference absence and coverage, without method names, scores, backend IDs or internal status hints. Keep the masking map evaluator-only. R09 need only show that this projection is mechanically possible using synthetic fixtures; do not generate real comparison material.

## Session accounting and replay

Use the existing prompt/payload fields solely as a serialization/reservation bridge; include the same complete source request for both methods, with policy/config separately bound. The `prompt` field is local data, never dispatched to a model. Both payloads must recover an exactly equal semantic request. Preserve StudySession's conservative quote accounting while measured provider/model token usage is explicitly zero (`Usage(0, 0, 0.0)`). State that a session call counts one local algorithm invocation, not an LLM call. Wall time and output bytes can be measured separately; do not invent model token counts or claim zero CPU cost.

Verifier reconstructs the complete expected result from bound request plus trusted policy and compares canonical bytes, not only hashes. Validate quote pointers/spans/text and source fingerprints independently as defense in depth. Execution replay also checks adapter class/code identity, exact provenance/capabilities and zero measured token/provider usage. Unknown/missing policy fields or altered policy version fail. Recorded code/resources are authenticated through existing package proofs; no archived JSON controls imported symbols.

## Meaningful regression tests before implementation

1. Two fixture requests pass unchanged; real-context and evaluator-role variants fail before backend generate. Rehashed mutations do not bypass the authenticated fixture gate.
2. Both methods round-trip the identical request bytes and source coverage. Changing prompt escaping, query, bounds, question/hypothesis/source hashes or payload options is rejected.
3. Independently recompute excerpt strings from source pointers/spans. Tamper pointer, source reference, observation ID, text, UTF-8 span or source fingerprint; reseal outer hashes and require replay failure.
4. Pure helper fixtures cover multibyte Unicode, combining characters, literal HTML, escaped slash/tilde pointers, empty strings and duplicate exact text with distinct provenance. No normalization or deduplication is silent.
5. Reverse input order and tie lexical scores. Results follow declared stable IDs, not dict/list incidental order; selected duplicates keep distinct source identity and do not imply independent studies.
6. Lexical query absent/empty/zero-match produces declared behavior; no fallback to extractive or biomedical synonym guessing. Scores recompute exactly and remain retrieval metadata.
7. Per-quote bound at N and N−1 UTF-8 bytes; count bound; full JSON response boundary including escaping/audit. Fail or record omission exactly per policy, without dropping required audit fields.
8. Missing inputs null versus measured zero remain distinct. Empty selection retains absence_claim=false and cannot acquire generated reasoning, probability or prediction features.
9. Single-use backend cannot dispatch twice; quote does not consume. Use finite synthetic session to prove journal, artifacts and source-inclusive replay succeed with measured zero model tokens/provider cost.
10. Reseal altered ranking, omissions, contributions/state, measured usage or provenance and demand verifier failure. Replay never executes another generation.
11. Tampered/omitted packaged fixture resource and module proof fail. Wheel-installed execution works without importing planning/tools or reading original source roots.
12. Maskable projection preserves literal source content and denominators while omitting method/backend/score metadata. Assignment keys remain outside source request and candidate projection.

Implementation ownership suggestion: one agent owns the new baselines module and its pure tests; coordinator owns installed guard/version/packaging and minimal synthetic session integration; peer independently tests resealed tampering and role/path/resource rejection. No modifications until the coordinator releases the frozen runtime boundary.
