# LitQA2 native scoring and source-policy qualification

The new optional experiment modules are qualified on invented inputs only. No public LitQA2 reference row, actual benchmark candidate or model generation was used in this component qualification. Core TETHER and SciFact code were not changed. Tests are isolated under `experiments/labbench/tests/`.

## Retained validation

- `scoring-red01.log`: initial missing-module failure, before implementation; the test was subsequently moved out of root discovery.
- `scoring-green01.log`: nine tests passed. `scoring-green02.log`: eleven passed. **`scoring-green03.log`: twelve passed**.
- `policy-red01.log`: initial missing-adapter failure before implementation.
- `policy-green01.log`: retained failed implementation attempt, despite the filename: eight errors from supplying a keyword-only stable-lock deadline positionally.
- `policy-green02.log`: eight passed after correcting the call. **`policy-green03.log`: ten passed**.
- Interpreter: existing `data/cache/tether-052-dev/Scripts/python.exe`, `-B`, with a workspace-local temporary directory. This qualification adds no dependency or network call. Retrieval tests substitute fictional HTTP responses while exercising actual acquisition output, original parsing, receipts, stable Windows reads and core `InputGraph` verification.

The tests cover exact native query/answer shape, Boolean and range rejection, duplicate JSON/citation identifiers, unknown fields, immutable copy, six operational-failure types, complete ordered schedules, native unsure, missing cases, source-backed substantive admission, source-free unsure, wrong-but-provenance-valid answers, original-byte changes, evaluator-only parent policy, future receipt eligibility, substituted requests, unknown publication dates, and durable generic journal decisions.

The six-case hand-scored fixture has raw accuracy 2/6, precision 2/3 and coverage 3/6; checked accuracy 1/6, precision 1/2 and coverage 2/6. One correct substantive answer is rejected. Timeout is not a successful unsure. A literal substantive choice `null` remains distinct from the visible refusal option, following the pinned original LAB-Bench convention rather than a different PaperQA2 task variant.

Malformed-output handling is a declared operational-unanswerable projection: parse failures stay in the all-scheduled accuracy denominator but outside attempted precision/coverage. The upstream scorer can count an arbitrary returned non-unsure string as attempted. A fixture explicitly distinguishes 2/3 from that hypothetical 2/4 denominator. Output metadata preserves this difference, parse-failure counts and known returned-output status counts; transport must separately report partial error/timeout bytes. Zero-attempt precision is reported as zero with `precision_defined=False`.

`incorrect_and_admitted` means native-key mismatch and includes admitted unsure; `incorrect_substantive_and_admitted` excludes unsure. `correct_not_admitted` covers rejection, check errors and unchecked output, while `correct_but_rejected` specifically counts policy rejection. This avoids labeling a valid refusal a false scientific claim or hiding failed checks.

## Policy boundary

`capture_context(...)` validates the pinned retrieval manifest and original extraction under stable original-path locks. It constructs an actual TETHER input DAG with raw search/XML receipts and a derived extraction manifest, checks every admitted original's role and availability, verifies source/receipt hashes, and captures immutable selected text, character bindings and the exact model request. Computation time is separate from source availability. Unknown publication dates remain unknown; current downloads do not prove historical availability.

The query is a trusted field-only projection. The raw answer-containing benchmark product remains supervisor-only and is not relabeled as eligible agent evidence. Model/runtime receipt validation and raw producer response binding belong to the separately sealed transport/session. `CapturedContext` is a trusted in-memory output, not a safe constructor for arbitrary archived reports. Archived verification must independently recapture the original roots using external anchors and compare sources, requests, roles and eligibility.

`verify_candidate(...)` accepts wrong native answers when they meet the declared source policy. Substantive answers must cite at least one offered, verified passage; unsure can have no evidence. It establishes neither native correctness nor semantic entailment. The report explicitly states that these native-task obligations are not the full BG02 or therapeutic contract.

## Owned source hashes at handoff

| File | SHA-256 |
|---|---|
| `experiments/labbench/native_contract.py` | `0b0c28f167a22d081ace31fa4113b80f822bc4a7c224af38bd92d2faa92d98dd` |
| `experiments/labbench/evaluate.py` | `8a0dcc3ff8e6c462305bcc504317d8e2a064daca511a1e0240e3d19942145075` |
| `experiments/labbench/tether_adapter.py` | `ad43f3f68819c2ddaa65cb0f98bd01cb7e8449307c9329bd28ba94d655b97456` |
| `experiments/labbench/tests/test_scoring.py` | `bb2c06f18eb50567225e000a7310e6e1ffcc1bd483d496fc248f5e00aadd347a` |
| `experiments/labbench/tests/test_policy.py` | `802825e4b58fe65784ba301ad30f2ec60b78860cf0c2003e663aab7571c8f673` |

The parent qualification will freeze the final combined runtime and independently reconstruct actual outputs. This component report is not evidence that the 199-case stage has run or passed.
