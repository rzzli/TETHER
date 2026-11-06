# Closure of independent data findings and native-choice amendment

The three issues in `SCORING-PEER-REVIEW-OF-DATA.md` are closed against the final code and retained regression logs:

1. `_fetch_http_direct` reads at most its remaining reserved bytes and conservatively rejects a cap-exact body without an observed EOF. It no longer consumes an unreserved oversize sentinel. `test_direct_transport_never_reads_a_byte_beyond_reservation` passes.
2. `verify_views` compares both manifest provider revisions with the anchored acquisition receipt and validates the shuffle method name. A resealed revision-contradiction regression passes.
3. Child socket and wrapped socket timeouts remain `TimeoutError`; other controlled causes are retained as `HttpTransportError.cause_class` and request `failure_cause`. No arbitrary exception is reconstructed. The child-timeout/sanitized-cause regression passes.

Final reviewed source hashes are projector `a2421dbfd1863b61ed0564056a36e74a08308226607320be74c09285fde7fa69` and retrieval `5e8f7b80f9bbe5a49a642f78bead76a6acc4e221823368cbdfa4511a48a7eaea`. Retained final data-owner logs report **7 projection and 12 retrieval tests passing**.

## Independent actual projection metadata audit

`verify_projection_metadata.py` uses only the standard library and independently checks external manifest/acquisition anchors, current code pins, product hashes and sizes, exact source-parent identities, provider revisions, full-199 count, query-only schema, evaluation-only reference/provenance roles, completion/journal hashes and the original JSONL/Parquet reconciliation anchors. It does not import the projector or scorer. Original/reference bytes are hashed without decoding answer fields; only the task-visible query product and metadata are parsed. No candidate generation or scoring occurs.

The audit passed on its first execution:

- Preparation: `data/benchmark/labbench/preparation-20261106-attempt02`.
- External manifest SHA-256: `7c085ccf94f0e3e3270727efbc3b250e43ac52168aad009ee362662fbd58122b`.
- Receipt SHA-256: `620cf7d9d166d892b8c33da9a3f6a896d0c8d3659bbc10b4b6144fcadcd723bd`.
- Result `PROJECTION-METADATA-INDEPENDENT-01.json` SHA-256: `492c14650977e2dff76e2211ad8ade23c5810d2594081f1c6c651015beb8345a`.
- Independent helper SHA-256: `5f638098c28023d4e1eae1d0283c9a5a1f576e5f4217a6ed146e87885cccdec5`.

All 199 tasks remain. The first failed preparation is preserved. Reference hashes and role metadata reconcile; answer-label correctness is not independently reconstructed at this stage. That reconstruction remains after candidates are sealed. Metadata proof does not replace biological validation, source entailment or actual benchmark execution.

## Native duplicate-choice compatibility

The original has two rows with repeated distractor text across different indexed options. Native evaluation preserves these options. The initial strict text-uniqueness rule incorrectly rejected the corresponding query projection; it was not a data error and no task was removed or repaired.

After explicit parent authorization, a fictional indexed-choice regression first reproduced the failure in `scoring-duplicate-red01.log`. The codec now permits repeated substantive text across distinct sequential labels while retaining exact prefixes, bounds and exactly one visible unsure option. The trusted projector separately rejects ideal/refusal collisions; the answerer cannot use correct-index metadata to decide which option is a distractor.

`scoring-green04.log` reports **13 passing tests** and `policy-green04.log` reports **10 passing tests** against the updated sources. These add to, rather than overwrite, the initial qualification history. New native-contract SHA-256: `8023fc028be67a0809d055560c418f3e83241c0304f538e61c90b0a64e3a35b3`; test source SHA-256: `873cb2837c95993fbeb67e3d57d7556ed6984908d69d5a08ae26df02febf383c`. Owned sources are held for the combined qualification and model smoke.
