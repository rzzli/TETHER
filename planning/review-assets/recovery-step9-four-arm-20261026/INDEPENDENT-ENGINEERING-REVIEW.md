# Independent engineering review: token capacity and four-arm composition

2026-10-26. **The reviewed implementation is suitable for the parent's freeze and full validation gates.** This is an engineering disposition, not release acceptance or completion of R09. The independent tests used invented tokenizer assets and fake process objects; they made no actual tokenizer, model, native-server, network or paid calls and read no protected outcome payloads.

## Reproduced defects and corrections

| Finding | Before evidence | Correction and independent outcome |
|---|---|---|
| A shorter `generate(timeout_seconds=...)` allocation could expire during quote verification while a later parent deadline still allowed recorded consumption. | `data/cache/four-arm-capacity-short-timeout-before.log`: regression failed because no TimeoutError was raised. | Owner applies the minimum of the parent deadline and call-start plus timeout throughout quote verification and immediately before consumption. Nine capacity peer tests passed. |
| A resealed predecessor request claiming a later cell entered recursive verification before identity reconciliation. | `data/cache/four-arm-composition-peer-before.log`: the bounded probe observed more than four recursive verifier entries, then stopped deliberately. It did not wait for stack exhaustion. | Owner checks retained predecessor run/cell/arm/index/name and full expected request before recursive replay. Final peer regression passed. |
| The final parent-receipt read could cross the replay deadline and still return success. | Same composition before log: expected expiry exception was absent. | Owner checks the same absolute deadline after the final read and before returning. Final peer regression passed. |
| A resealed final child with a generic-valid package proof could swap required resource paths and pass direct replay. | `data/cache/four-arm-composition-peer-after-v1.log`: resource-alias regression failed; the three earlier probes passed. | Explicit composition verifier now checks the child's exact required resource mapping before its own recursive validation. Final peer regression passed. |

The owner also corrected token-cell finalization across output hashing and receipt publication before my failing-before probe ran. Both independent expiry/receipt-withdrawal tests passed; this is verified proactive hardening, not an independently reproduced before defect.

## Retained test results and final patch distinction

- `tests/test_study_token_capacity_peer.py`: **9 passed in 19.327 seconds**, retained in `data/cache/four-arm-capacity-peer-final.log`.
- `tests/test_study_authority_four_arm_peer.py`: **4 passed in 146.633 seconds**, retained in `data/cache/four-arm-composition-peer-final.log`.
- Ruff check passed for both peer test modules. Earlier transient package-proof failures occurred while owners were editing shared source; these were rerun on stable files and are not counted as defects or passing acceptance evidence.

Those **13 peer passes preceded one final owner-discovered schema-downgrade correction**. The owner reproduced that token-specific execution verification could accept a configuration marked schema1, then required integer schema2, the exact capacity descriptor and request/payload/descriptor binding fingerprints. I inspected that narrow correction and agree with it. I did not rerun the two-minute composition fixture after this final change; the owner explicitly assigned that rebuild to full validation. At report creation, the owner's post-fix 34-test run and complete release gates were pending. Do not describe all 13 peer tests as run against the final patched token-capacity bytes.

The accompanying JSON retains both the source/test hashes observed during the 13 passing peer tests and the final reviewed hashes, with the exact changed-file list. It also pins the relevant before/after logs. Full-suite, installed-package, frozen-version replay and actual finite qualification evidence belong to the parent's acceptance report.

## Reviewed boundaries and remaining limits

The concrete trusted policy carries external receipt/spec/prompt/payload anchors and an immutable locator-free descriptor. Execution and replay require the explicit object; serialized names and backend IDs do not select it. Ordinary RecordedBackend, legacy byte `_capacity` behavior and the two-fixture public admission gates remain separate. New configuration2/receipt2 bindings are checked against authenticated exact token reservations, and fixture usage remains distinct from token counts and zero actual model calls.

The composition requalifies its one invented retrieval parent, retains complete selected source records, derives history only from verified accepted same-run/same-arm predecessor source IDs and recomputes pure baselines and reviewer projections. It uses six recorded cells and two zero-call pure arms under one default aggregate budget. Parent/source/quote verification shares the finite caller deadline; replay starts no process. The source preparation, tokenization setup, pure work, cell work and sealing are included in the live case timing boundary.

Deadline checks remain cooperative, not hard CPU preemption or a hostile-OS sandbox. Fake-tokenizer fixture success does not prove that the real pinned tokenizer plus complete composition will finish inside 300 seconds. Historical 0.3.5 sizing proofs do not authorize a new package: fresh current-package parents and exact actual-history quotes are still required after acceptance. This review establishes no biological correctness, independent human reference, real-source four-arm performance, native-model readiness or end-to-end Virtual Biotech reproduction. Human/scientific acceptance and the remainder of R09 stay open.

No further peer source or test edits are planned. The remaining action is the parent's final validation and acceptance process, including the final schema-downgrade patch.
