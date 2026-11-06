# Independent bounded review of LitQA2 preparation and retrieval

Scope: read-only review of `experiments/labbench/data_views.py`, `retrieval.py`, their fictional tests and retained schema-level reconciliation evidence. No benchmark answer rows or generated candidates were inspected. Findings were sent to the data owner and parent before source freeze.

## Confirmed boundaries

The trusted projector keeps the mixed original, references and source hints out of the answering product. Queries contain only canonical ID, question and shuffled displayed choices. All substantive and insufficient-information options are shuffled; original `ideal` is the correct option even when its literal text is `null`. The fixed seed is reproducibility metadata, not an adversarial secrecy claim. Query loading does not open references.

The external preparation gate `data/JSONL-PARQUET-RECONCILIATION-01.json` reports 199 matching IDs in identical order, all shared fields equal and no skipped rows; only Hugging Face `source: null` and `subtask` fields are extra. This proof uses pinned PyArrow 21.0.0. The reviewer inspected the aggregate proof, not the answer-containing originals. Absence of a Parquet reader in the runtime projector therefore is not an unresolved parity defect.

Retrieval is question-only. Source candidates preserve search order and duplicate article identity; no annotated benchmark URL seeds retrieval. The current verifier reconstructs first-eligible selection, full-text request order, retained source extraction, locators, byte accounting and source coverage from retained originals. It does not permit omitting an available parsed source merely by resealing an empty manifest. Search/XML licenses and explicit future publication dates are checked. Uncertain publication is retained as unknown. Paragraph extraction includes text nested within paragraph markup; revised coverage wording correctly excludes table cells without paragraph markup, image pixels and separate supplement files.

The transport has an owned process deadline covering DNS/connect/read/IPC stalls; proxy inheritance is disabled. Exclusive output reservation, retained terminal failure and no automatic resume protect uncertain attempts. Failed/unmeasured transfers retain a conservative reservation distinct from complete retained body bytes and unknown wire bytes. Partial/no-source retrieval remains incomplete evidence, never biological absence.

## Corrections requested before final freeze

1. **HTTP cap accounting:** the direct reader used a one-byte oversize sentinel beyond `byte_limit`, while the failed-transfer reservation charged only `byte_limit`. Requested either explicit sentinel accounting or conservative rejection at the exact cap without reading beyond the reservation. The owner is implementing the latter.
2. **Provider revision metadata:** `verify_views` rebuilt actual products from an externally anchored receipt but did not reconcile the manifest's human-readable Hugging Face/GitHub revisions with that receipt. Requested direct comparison so contradictory version claims cannot pass semantic verification.
3. **Child timeout classification:** socket timeout in the child was sent as `error_type=TimeoutError`, then flattened to `ContractError` before retained request accounting. Requested controlled propagation of the original timeout class, without arbitrary exception reconstruction, to preserve distinct timeout reporting.

The data owner owns fixes and regression evidence. This note records the original findings; final acceptance depends on their fresh logs and the combined component qualification, rather than this source read alone.

## Residual interpretation and verification limits

Standalone view/retrieval verification can read a journal once for its byte hash and again for chain interpretation. Admission through the new adapter holds stable original-path locks across both operations; archived independent verification should likewise capture/lock original inputs before interpreting them. Do not claim an arbitrary unsynchronized sequence of hash and reread calls proves immunity to concurrent file replacement.

Question-token retrieval is deliberately simple and its actual annotated-source recall remains unknown before execution. Successful licensed acquisition does not imply relevance, completeness, entailment or a correct answer. DOI/PMID/PMCID aliases should be resolved to canonical paper identities before reporting paper recall; otherwise name the result identifier recall. Neither valid citations nor matching annotated source identifiers are semantic-support scores.
