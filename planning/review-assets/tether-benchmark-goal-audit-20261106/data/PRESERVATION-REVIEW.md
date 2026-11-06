# BG06 selected-source and artifact preservation review

**Result: PASS within the declared scope; no unresolved preservation blockers.** This read-only review found no byte-hash mismatches in the selected BG01–BG05 artifacts, current qualified product sources, or protected catalog/downloader files. It did not rerun experiments, models, validators or tests, and did not modify the reviewed originals.

The [first pass](PRESERVATION-MANIFEST-01.json) performed 45,561 proof checks over 33,908 unique files and 857,972,826 logical bytes in 89.35 seconds. Its six reported findings were audit-reader assumptions: four collection module paths needed the `experiments/labbench/` base, and two journals are sealed separately from the output maps. The [targeted closure](PRESERVATION-CLOSURE-01.json) verifies the correct source paths, separately sealed journal hashes and complete inventories. The first report and log remain unchanged. No production defect, data repair or experiment rerun was needed to close these findings.

| Evidence | SHA-256 |
|---|---|
| First preservation manifest | `6574d819ab6ccc02c4d0423f5be4735b164a1ae75dd15ade2c2337560a9c7e13` |
| Targeted preservation closure | `5898d8f51b00c1856cb2fa19625efb9570b3fb57873e6b720673e294e9578249` |

## What was checked

| Stage or boundary | Current-byte checks and practical limit |
|---|---|
| BG01 correctness and release | Retained aggregate and its 57 input proofs, selected original releases, wheels, PDFs and qualification evidence. These are preservation checks of prior results, not a new test run. |
| BG02 equal-policy comparison | Original and patched 109-case freezes, exact bundle file/directory inventories, frozen source and oracle/runtime proofs, and all 1,308 declared terminal records in each run. Independent reconstruction anchors remain intact. This review does not independently rederive policy decisions. |
| BG03 SciFact | All 1,601 native-run outputs and 72 reconstruction outputs, exact output inventories, current frozen task code, installed dependency payloads, pinned evaluator/protocol and original acquisition/license members. |
| BG04 LitQA2 | All 3,598 generation outputs, seven evaluation outputs plus its separately sealed journal, 3,186 declared collection outputs plus metadata/journal inventory, frozen task code, and the 17 original acquisition products. The retained model acquisition receipt was checked; multi-gigabyte model weights were not rehashed again. |
| BG05 Inspect | All 4,706 primary outputs, 11,606 primary input proofs, 23 runtime-stage outputs, 9,451 runtime proof entries and 124 witness outputs. Current installed and repository product Python sources match the 85 qualified files. Full source/environment inventories remain anchored in the earlier execution and reconstruction records. |
| Catalog | `sources.json` still has schema version 1, 83 providers and 178 datasets. IDs are unique and provider/dependency references resolve. Catalog bytes match the pre-benchmark Git baseline. |
| Acquisition utilities | Protected start/watch/status/catalog-sync scripts match the retained hashes and Git baseline. The authorized BG01 correction to `Test-DownloadBatch.ps1` is explicitly excluded from an unchanged claim. No downloader or monitor was invoked or altered. |
| Monitor configuration | Configuration records `monitor_enabled: false` with null process/session IDs. This observes configuration; it is not live or historical process attestation. |

The full manifest records the exact paths, expected hashes, observed hashes and inventory boundaries. It deliberately avoids a repository-wide or drive-wide preservation claim.

## Documentation correction and test provenance

The four explicitly mutable documentation paths were excluded from frozen-run preservation claims. Root repaired a docs-only UTF-8 decoding error from the `eda8118` checkpoint using the prior UTF-8 bytes plus intended status edits. At the correction checkpoint, strict UTF-8 parsing, absence of the known mojibake markers and the intended Git diff were confirmed. [BG05 acceptance 02](../../tether-inspect-20261106/stage/STAGE-ACCEPTANCE-02.json) passed its 60 checks and 34 links against corrected documentation; the original acceptance 01 remains historical evidence. Root subsequently updated current TODO/README/memory for BG06. Those later mutable status bytes are covered by the final root validation, rather than by this earlier document snapshot.

Prior test counts are version-specific. BG01's retained full-suite result applies to TETHER 0.5.1 / AsOf 0.3.12; BG02's corrected result applies to 0.5.2 / 0.3.13. Overlapping focused suites must not be added to full-suite totals. The earlier replay false-admission result remains retained. Preservation of a log establishes that the evidence is unchanged, not that a different source version inherits its result. No fresh tests are claimed here.

## Rights, exposure and reproducibility limits

- **SciFact:** the retained source license assigns claims/evidence annotations to CC BY 4.0, corpus abstracts to the S2ORC ODC-By 1.0 terms, and code to Apache 2.0. The evaluator's Apache license is also retained. These component terms should remain distinct in any redistribution. The 300 public development claims, source-group split and shared unlabeled corpus do not constitute an unseen private test set. Trusted preparation inspected labels; worker inputs were separately restricted.
- **LAB-Bench:** original dataset/code license files declare CC BY-SA 4.0. Retrieved article rights are separate: the prospective collector allowed CC BY/CC0 and retained original XML and attribution. HTTP success alone does not prove a license, scientific support or entailment. Question-only retrieval withheld per-question reference sources and key passages from the producer; public-data/model pretraining exposure remains unresolved.
- **Inspect:** the pinned Inspect 0.3.287 MIT license and dependency metadata/wheels are retained. The finite authored policy corpus is exposed and constructed, so conformance does not estimate natural failure prevalence or full runtime equivalence.
- **Catalog scope:** the 178-product biological inventory includes products with different access and redistribution conditions. This review does not clear those rights, validate every raw dataset, or authorize public redistribution. SciFact and LAB-Bench currently use experiment-specific acquisition/projection manifests rather than new catalog entries. That is an indexing limitation; their experiment provenance is retained.
- **Independent review scope:** the independent reconstructions are separate AI-assisted implementations within this project, not external human replication. They support the stated finite checks rather than independent biological validation.
- **Storage scope:** broad biological raw stores, every legacy receipt, model weights and current live process state were outside this bounded pass. Existing source-inclusive execution/reconstruction evidence remains the basis for those earlier guarantees. File-hash checks also do not provide continuous attestation between observations.

There are **zero unresolved preservation findings**. The indexing, licensing, exposure, runtime-coverage and scientific limitations above remain explicit limits on publication claims and later work, rather than unreported failed preservation checks.
