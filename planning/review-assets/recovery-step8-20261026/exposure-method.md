# R08 exposure inventory â€” scope, method and unresolved coverage

Date: 2026-10-26. Role: **evaluation_only**; never include this inventory, its derivatives or prior-review metadata in agent-visible manifests. Current artifact: `EXPOSURE-DRAFT-v3.json`. Status: **scoped inventory completed; all-project freshness not qualified**. No model calls, new data acquisition or protected outcome reads occurred.

## Results

| Inventory unit | Count / result |
|---|---|
| Exact `case.json` files discovered and parsed under `runs/`, `data/derived/`, and packaged demos | 471 / 471; zero skipped case metadata files |
| Case metadata occurrences, including R01 entries, the later case pack and two explicit synthetic resources | 493 |
| Real-identifier metadata occurrences | 197 |
| Explicit synthetic/demo occurrences | 296 |
| Distinct normalized real hypotheses | 20 |
| Distinct real targetâ€“indication pairs | 18 |
| Synthetic hypothesis groups | 2; DEMO and SYNTHETIC identifiers remain separate from real cases |
| Sibling snapshot metadata files | 57 |
| Pinned inputs rehashed during consistency validation | 541 |
| Fresh real cases qualified | **0** |

The twenty real hypotheses comprise the original ten and the later TNF, IL23A, JAK1, TREM2, LRRK2, ANGPTL3, APOC3, SOD1, KRAS and CD19 development pack. ERBB2 and PCSK9 each have two original action/modality hypotheses, explaining twenty hypotheses but eighteen targetâ€“indication pairs. The later pack's historical `fresh` name described its status relative to the original ten at selection; it is now present in prior run artifacts and cannot be treated as fresh for a new evaluation.

The source-family inventory preserves descriptor-declared datasets (`asof_normalized_packets`, HGNC, Open Targets target/disease/evidence) and seventeen evidence partitions: cancer biomarkers/census, ClinGen, CRISPR/CRISPR screens, Europe PMC, EVA/EVA somatic, Expression Atlas, gene burden, Genomics England, GWAS credible sets, IMPC, Orphanet, Reactome, UniProt literature/variants. These are metadata associations, **not evidence coverage or biological sufficiency claims**. Referenced evidence packets were not opened.

## Local Virtual Biotech mapping coverage

The pinned compatibility artifact identifies repository revision `71f9da68c95c5ee0ef4c1d9b8f45f10693de022d` and the clinical mapping filename. The local Parquet file is receipt-matched: SHA256 `50580ad5681c87aa9f7c3741f340a3a408fbd43ccba388546a172289fcda5897`, 10,375,291 bytes. Its receipt is a local capture, **not a publisher-provided checksum**; it was left unchanged.

Schema inspection found thirteen columns, including clinical status, phase and stop reasons. Only `targetId`, `diseaseId` and `nct_id` were selected with PyArrow 21.0.0 **before Python conversion**. The other ten columns were never decoded. No label CSV or normalized-outcomes file was opened. The stream covered all **488,361 rows**, with zero missing target/indication keys, yielding **72,158 targetâ€“indication pairs**, **1,520 targets**, **2,559 indications** and **76,925 distinct trial IDs**. The retained key inventory contains pair identities and aggregate mapping/trial counts, not clinical values.

Sixteen of the twenty project hypotheses match a mapping pair. CD276â€“NSCLC, ANGPTL3â€“familial hypercholesterolemia, TREM2â€“Alzheimer disease and LRRK2â€“Parkinson disease lack an exact pair match in this file. These four are still development-exposed through project material. Nonmembership can reflect source coverage or identifier differences and establishes neither freshness nor biological absence.

This is complete coverage of the **retained published-repository mapping universe**, not proof of the exact evaluated-label subset, all article vignettes, or single-cell trial-feature case keys. The README's separately named labels file is not an admissible substitute for an independent metadata-only case list in this task. The known CD276/OSMR published-example exclusions are retained from R01, not newly validated against publication content. The README states Open Targets data are CC0; no new legal or record-specific permission determination was performed.

## Reproducible boundaries

`inventory_exposure.py` uses an exact read whitelist, refuses protected names/trees, and reads only case metadata, explicitly selected control manifests, explicit synthetic resources and sibling snapshot descriptors. No snapshot reference is followed to its evidence payload. Case fields retained are identifiers, namespace versions, action, modality, tissue, task/origin and program-at-origin metadata. R07 is recorded through its frozen control plan and request hashes; candidate response contents and reference-seal targets are not read.

Normalization handles identifier capitalization/whitespace, EFO/MONDO/HP colon-versus-underscore spelling, and token capitalization/separators. It performs no symbol mapping, disease synonym merge, tissue equivalence, or new annotation lookup. Null tissue remains null. Exact hypothesis groups retain action/modality/tissue distinctions; conservative targetâ€“indication family groups link their variants for exposure exclusion. Namespace versions remain recorded even when exposure grouping joins versions.

R01 remains unchanged and is linked by path/hash as the superseded narrower coverage inventory. The v1 draft is preserved: it completed its write, then its strict read guard blocked hashing its own unwhitelisted output. V2 computes that hash from serialized bytes, adds original source descriptors to the family inventory, and incorporates the safe Virtual Biotech projection. V3 additionally removes stale pre-projection wording and explicitly records scoped completeness. Its successful execution and a separate validation rehash all 541 inputs and confirm a complete partition of the 493 metadata occurrences.

## What remains unresolved

- Protected clinical cohorts/labels, gold/adjudication assets and completed human responses remain quarantined as families. No outcome, follow-up value or answer was used to enumerate or select cases.
- All IL6R derivatives, source qualification, R07 candidates and expert-reference preparation remain development-exposed; no action/modality variant is inferred fresh.
- Nonstandard case containers, inline cases, reference-preparation files and cache/checkpoint mirrors are not exhaustively reconciled. The exact whitelisted case-file scan is complete; the repository-wide exposure universe is not.
- A separate metadata-only list of published evaluated Virtual Biotech cases and single-cell case keys has not been qualified. Mapping membership is a conservative exclusion signal, not an outcome or benchmark-membership label.
- Source relatedness beyond targetâ€“indication grouping, annotation/alias compatibility, detailed source sufficiency, and reviewer coverage still need R08 work. No source feasibility or human scientific gate is completed here.

Next source-feasibility work should exclude these twenty hypotheses and their conservative families, retain the published mapping overlap flag, qualify any additional clean case-key inventories, and resolve outstanding exposure classes before declaring a fresh pool. Selection must remain independent of arm success. Candidate metadata may be prepared without generating responses or manufacturing human coverage.

## Artifact pins

- `EXPOSURE-DRAFT-v3.json`: `986e48cbd67e29f99a47f81a5c3416007cccf66b495c46c63a41a9eb23412186` (927,179 bytes).
- `virtual-biotech-mapping-metadata-v1.json`: `6e606804932f7792d1dcbdd435fd720d30e101742c887b9091bf144d4254b397` (2,497 bytes).
- Ignored full key inventory `data/cache/recovery-step8-exposure-20261026/virtual-biotech-identity-keys-v1.json`: `b544537bcd5922d319338ad38e2d9ee0c8ed984ce7a051f604fb5dec4d6699c2` (7,412,455 bytes).
- `exposure-validation-v2.json` retains input consistency, generator hashes and remaining qualification limits.
