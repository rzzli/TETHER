# Ten-case contemporary T6 identity freeze

Frozen at **2026-10-18T17:00:35.108116+00:00**, before biological source research or new system outputs. This is a deliberately selected development pack, not a population sample or a claim of model-training novelty.

Case pack: `data/benchmark/gold_evidence/science-prerequisites-20261018/case-freeze/casepack.json`.

SHA256: `3d9e5763e5b9a48bd333dc67697becf1badf00d83ed166fc5a018c40dac62f90`.

| Symbol | HGNC | Ensembl | Disease ID |
|---|---|---|---|
| TNF | HGNC:11892 | ENSG00000232810 | EFO_0000685 |
| IL23A | HGNC:15488 | ENSG00000110944 | EFO_0000676 |
| JAK1 | HGNC:6190 | ENSG00000162434 | EFO_0000729 |
| TREM2 | HGNC:17761 | ENSG00000095970 | MONDO_0004975 |
| LRRK2 | HGNC:18618 | ENSG00000188906 | MONDO_0005180 |
| ANGPTL3 | HGNC:491 | ENSG00000132855 | EFO_0004911 |
| APOC3 | HGNC:610 | ENSG00000110245 | EFO_0004211 |
| SOD1 | HGNC:11179 | ENSG00000142168 | MONDO_0004976 |
| KRAS | HGNC:6407 | ENSG00000133703 | EFO_0002618 |
| CD19 | HGNC:1633 | ENSG00000177455 | EFO_0000403 |

All twelve identity sources (ten OT25.09 target partitions, one disease partition and HGNC snapshot_2026-10-10) and their archived receipt bytes were rehashed. Source paths, hashes, receipt hashes, known-public bounds and exact selected row locators/projection hashes are retained in the pack. Only identity columns were read from OT Parquet; no biological evidence tables were opened. HGNC source rows were used for approved identities and declared family metadata. Contemporary normalization does not qualify historical predictor versions.

Root explicitly selected the disease EFO rheumatoid-arthritis identity over HP_0001370 and MONDO ALS identity over HP_0007354; alternatives and rationale remain visible. No automatic disease replacement occurred. Before freezing, CD19 CAR-T action changed from ADC-style `delivery_antigen` to `antigen_directed_cell_killing`; modality is `car_t`. Tissue remains null/unspecified for every case.

Compared with the original prescribed ten-case pack, all ten targets and target/indication pairs are fresh. This check does not assert that no identifier occurs elsewhere in the repository or that pretrained models have never seen these topics. Disease overlap with prior cases and shared biology remain possible. No shared pinned HGNC family IDs were observed among the selected rows; the ten singleton declared groups do not establish ten independent scientific observations. Shared publications, evidence, pathways and model knowledge need separate dependence handling.

Validation: nine `tests.test_science_fresh_cases` tests passed before freezing, covering approved-symbol and Ensembl mismatch, missing/ambiguous disease identities, explicit alternative rationale, duplicate scopes, prior-target exposure, transitive family dependence, action/tissue constraints and refusal to overwrite an existing freeze. Production freeze confirmed ten complete identities and twelve receipt-verified sources. Provider spending: **$0**. Source originals and transport receipts were not modified.
