# Native MCQ model component qualification

Status at this checkpoint: **17 fictional model-component tests and four smoke-helper controls pass. Actual model smoke and benchmark execution remain undispatched by this component reviewer.** The implementation is held for the root's final qualification and explicitly bounded first smoke attempt.

| Artifact | SHA-256 |
|---|---|
| `experiments/labbench/model.py` | `ef4470b8be436481399d49443ffc8c64daea607da58c77f0ebb2ccc4fdf8c75a` |
| `experiments/labbench/tests/test_model.py` | `1fdad519484ac33b7b726793aa98e5f728a80aaab381d9254d3a423b683c477c` |
| `model-tests-attempt03.log` | `d45854b3e9c38ac6561a64ec1f44c27b3cd1e7bd98a7ca641a337cb377113a2a` |
| `model_smoke.py` | `4c89a847be3182152627d67b14e564d829aa05986aaf1dd59ba665f082a3c70c` |
| `test_model_smoke.py` | `9486841472b49c217fa4fc49c899fd4d93847a04be0685564cd517b94c4e5160` |
| `model-smoke-helper-tests-attempt04.log` | `0b966b520ac5c6e683fecc90c2cddadb02f5586066e20f5d94d4db26cd4b6d11` |

The [17-test log](model-tests-attempt03.log) includes a complete generic `StudySession` seal using fictional transport, exact native answer parsing, native replay, separate exact-token and conservative reservations, model/owner/command/payload binding, source hashes and strict minimal fields, input immutability, explicit prompt limits, interrupted generation, retained token-capture write failure, no duplicate attempt, output collision, bounded receipt reading, and asset verification before fake process launch. The first test attempt exposed a fixture using unlabelled options; the fixture was corrected and native `validate_query` reused during preflight. The original failed log is retained.

The [four-helper-control log](model-smoke-helper-tests-attempt04.log) includes a **real, tiny non-model Python process** contained in a Windows job, with its descendant confirmed stopped after the existing TETHER parent supervisor's two-second deadline. This qualifies the containment mechanism on this host; it does not qualify the model, Vulkan, hardware capacity, native grammar, answer quality, or every failure path. Other helper tests use mocks and never load weights. An initial helper test found the distribution names were `asof-target-agents`/`tether-target-agents`, not import-module names; that failed log is retained.

The final helper command used for tests was:

```powershell
& 'data/cache/tether-scifact-env-attempt02/environment/Scripts/python.exe' -I -B -X 'pycache_prefix=D:\Projects\drug_target_agents\data\cache\labbench-smoke-tests-import-attempt04' 'planning/review-assets/tether-labbench-20261106/test_model_smoke.py' -v
```

The root separately reported the combined 57 component controls passing under the qualified fresh-empty-cache policy in [components-attempt01/VALIDATION.json](components-attempt01/VALIDATION.json). This note does not replace that source-bracketed record. The model source stayed unchanged throughout that bracket; the smoke helper was finalized afterward and is separately pinned above.

The proposed smoke uses the existing receipt and all model/runtime proofs, one fictional Lumen-7 color question, one `/tokenize` request and at most one `/completion` request. Its native refusal option is in the middle, and the expected substantive answer is index two. It has a 900-second outer worker bound, 180-second owned startup bound after asset verification, and one shared 120-second tokenizer/generation/cell-finalization deadline. Port 55606 passed a temporary bind probe; that socket was immediately released, and actual startup must recheck availability. Model configuration remains temperature zero, seed 20261106, 16,384-token context, 256 output tokens, eight CPU threads and up to 99 GPU layers, all pending fictional runtime qualification.

`OwnedServer` performs the single authoritative full asset verification pass. Its timing is combined with owned startup; no separate hash-only timing is fabricated. Model CPU/RAM are sampled after readiness, worker usage is measured separately, and GPU memory/energy remain unknown. Ordinary cleanup must be verified before successful receipts. Windows kill-on-close job containment is a fallback after worker failure; it does not turn forced or unverified cleanup into success. Parent and worker use `-I -B` with a fresh empty `-X pycache_prefix` and retain before/after emptiness.

No historical P04/P04b/R07 launcher or active pointer was invoked. No benchmark question, key, source retrieval or real model output was used in these controls. The next allowed action is root review, fresh full code/environment preflight, and one explicit new fictional smoke attempt; a failed or uncertain model call is not automatically repeated.

## Native duplicate-option correction and current qualification

The scorer owner subsequently corrected the native codec to preserve repeated substantive option text across distinct labeled slots, as required by the pinned task records. The exact single visible refusal and sequential option labels remain required. Current native codec SHA-256 is `8023fc028be67a0809d055560c418f3e83241c0304f538e61c90b0a64e3a35b3`. The model module already permits distinct displayed labels with repeated underlying text and required no edit.

Against that corrected dependency, [all 17 model tests passed again](model-tests-attempt04.log), and [all four helper controls passed again](model-smoke-helper-tests-attempt05.log), both with fresh import prefixes and `-I -B`. Root also retained the [59-test combined qualification](components-attempt02/VALIDATION.json) and [85-file installed-source parity check](INSTALLED-SOURCE-PARITY-01.json). The earlier 57-test bracket and logs remain historical evidence. The model and helper source hashes above are unchanged; the actual smoke must use the new native codec hash, not the earlier one.
