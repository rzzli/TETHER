# Read-only peer review of the replay correction

No material blocker was identified in the reviewed change. This is a source review with reuse of the correction owner's retained qualification, not a second test execution or a corrected-corpus result.

Reviewed `src/asof/agents.py`, `src/asof/artifacts.py`, `src/asof/replay_validation.py`, `tests/test_replay_archive_verification.py`, the workflow's quote/dispatch/review sequence, and the final failed-quote follow-up. The retained [green02 receipt](../tether-replay-correction-20261105/green02.json) reports 25 passing tests with no failures, errors or skips. Its SHA-256 is `acbda7e33f0ed9f8297bf90efb5c35c9c024bf822070047f7d9f23904370064b`.

- `replay_selection` preserves the previous `_next` entry lookup, request-fingerprint comparison and usage validation. Cursor advancement remains in `select`.
- The new publication hook verifies replay bindings before creating the output directory. The read hook runs after the common execution and semantic checks, so its local event checks complement the existing state machine.
- Source-inclusive verification reconstructs the request using the current request builder and admitted observations; matching two fabricated retained hashes is insufficient. Retry entries use review feedback and consume their category's sequence in order.
- Legitimate failed quotes remain distinct from missing consumed responses. A category with a terminal quote failure cannot restart. Failed-quote request reconstruction is included in the reported count. Unused extra entries/roles remain allowed, consistent with `ReplayBackend`.
- Archived-only verification explicitly reports weaker binding to retained dispatch fingerprints. It does not claim source reconstruction. The original replay path is not reopened, and its original-byte hash remains explicitly described as an opaque declaration rather than reconstructed from normalized JSON.
- Legacy-v1 receipt scope remains separate. No live model, original replay-file dependency, or inference of scientific validity is added.

Reviewed source pins:

| File | SHA-256 |
|---|---|
| `src/asof/agents.py` | `d6517766232959f2fc0f9d5d84b3fc181c35774cb4dac32df2d88f99bcc4d2fc` |
| `src/asof/artifacts.py` | `bb8027adea7bc2719f24895db9afbe05b44281231ee0a7a3e29592047290cd98` |
| `src/asof/replay_validation.py` | `9ac7442fe07d5d82c6516d2e2bc214d68354c8e2e1e216ed40dc872cb5c45905` |
| `tests/test_replay_archive_verification.py` | `7c4b1c7b51b210b84bf4bfbdf90bc9f0365804f1dde52467ec09b83dc972b3c7` |

Release qualification, a newly installed corrected runtime and a new corpus freeze/comparison remain separate gates. This review does not revise the original frozen decisions or claim that the original EP075 result exercised replay binding.
