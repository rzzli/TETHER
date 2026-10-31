# Pure interpretation generation contract

Status: AsOf **0.3.11** is accepted for pure engineering preparation and validation. [Acceptance evidence](../planning/review-assets/recovery-step9-generation-contract-20261028/acceptance.json) covers full, installed and preserved-version checks; native conformance and scientific validation remain unestablished.

The `source-quote-interpretation-v3-gbnf` interface prepares a deterministic grammar and validates authored replies offline. Its generator identity is `strict-interpretation-gbnf-v1`. Preparation returns `execution_authorized: false` and `native_conformance: "unverified"`. Existing v2 preparation, the default controller route, native-wrapper behavior and archived artifacts retain their existing identities.

The public modules are [interpretation_generation](../src/asof/study/interpretation_generation.py) and [interpretation_grammar](../src/asof/study/interpretation_grammar.py). They use the standard library and perform no model dispatch.

| API | Behavior |
|---|---|
| `build_grammar(quote_texts, *, claim_limit=3)` | Builds an immutable grammar from contiguous `Q0`–`Q(n-1)` original-string references, ordered numerically. |
| `prepare_payload(request, arm, index, feedback)` | Preserves the complete request/catalog/history, adds the grammar and archives the complete acceptance schema outside the HTTP payload. |
| `request_from_payload(payload)` | Reconstructs the request and regenerates the exact prompt, grammar and options; mismatches fail. |
| `validate_output(request, payload, document)` | Applies the complete existing semantic post-validator, binds the result to v3 fingerprints and freezes the returned state. |

Preparation binds request, quote-catalog, payload, acceptance-schema and generation-contract fingerprints. `grammar_sha256` hashes UTF-8 grammar bytes; `generation_contract_sha256` fingerprints the complete grammar artifact, including its declared serialization domain and post-validation exceptions. The finite grammar uses shared, acyclic productions. Neither its graph nor its hash establishes native acceptance or scientific correctness. V2 and v3 payloads are rejected by each other's reconstruction/validation routes.

This example validates an authored synthetic abstention entirely offline:

```python
from asof.study.diagnostic import load_synthetic_request
from asof.study.interpretation_generation import prepare_payload, validate_output

request = load_synthetic_request("synthetic-context")
prepared = prepare_payload(request, "asof_interpretation", 0, [])
answer = {
    "answer_status": "abstained",
    "claims": [],
    "unresolved": [],
    "abstention_reason": "Synthetic exercise; no scientific conclusion.",
}
result = validate_output(request, prepared["payload"], answer)
assert not prepared["execution_authorized"]
assert result["features"] == {}
assert result["clinical_probability"] is None
```

The payload carries `grammar` instead of `json_schema`. Generation uses compact JSON with sorted object keys and escaped less-than characters (`\u003c`), preserving decoded values and preventing raw runtime delimiters. Generic strings support raw Unicode scalars and JSON escapes, including paired surrogate escapes. Length means decoded code points: astral characters count once; combining marks count separately. Source text, reference order and internal whitespace are preserved without normalization. Some equivalent JSON spellings fall outside this declared generation domain while remaining valid under the strict post-validator.

- **Bounds:** at most 256 quote IDs and three claims, subject to the inherited lower claim cap. Original quote text totals at most 32,768 UTF-8 bytes, a necessary bound derived from the existing prompt cap. Final prompt, grammar and complete serialized payload caps remain 32,768, 65,536 and 65,536 bytes; raw/canonical responses remain capped at 256 KiB. Oversize inputs raise `ContractError` without pruning. A quote longer than 1,800 code points retains its reference while its impossible source-report literal branch is omitted.
- **Acceptance:** answered/partial/abstained states, original quote pairing, scalar/nonblank text and collection limits remain mandatory. Text strings are capped at 1,800 code points; reasons at 512. Global claim-text uniqueness, response-byte limits and source/request/history authority remain post-validation responsibilities. Numerical features stay empty and clinical probabilities null.
- **Evidence limits:** the [reference disposition](../planning/review-assets/recovery-step9-generation-contract-20261028/SCHEMA-ORACLE-DISPOSITION.md) qualifies 162 typed schema expectations and 16 controls; five parser-edge observations remain separate. Schema acceptance does not establish strict wire parsing, entailment or clinical usefulness.

See the [contract](../planning/review-assets/recovery-step9-generation-contract-20261028/CONTRACT.md) and [bounded-input amendment](../planning/review-assets/recovery-step9-generation-contract-20261028/AMENDMENT-1-BOUNDED-INPUT.md) for design decisions. The next critical review follows the [native recognizer requirements](../planning/review-assets/recovery-step9-generation-contract-20261028/NATIVE-RECOGNIZER-REQUIREMENTS.md): qualify exact headers and vocabulary-only loading before any separately authorized native document/EOG, rejection or resource experiment. Pure preparation grants no execution authority; native conformance and scientific validation remain pending.
