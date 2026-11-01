# P09 rights source audit v1

Status: DRAFT_OFFICIAL_SOURCE_REVIEW; not legal certification and not public-release authorization. Review/access date: **2026-11-01**. Owner declarations remain deferred. This review changes only draft cards and this audit, not source data, results, manuscript or PDF.

## Method and retained boundaries

Read official provider/licensor pages using the web tool and existing neutral acquisition/build metadata. No new datasets, model weights, font copies, paid access, expert contact, inference, whole-genome downloads or experiments were performed. No actual row values, expected reference facts, historical human responses, protected clinical originals or outcome archives were consulted. Source-format scope remains the actual P05 Parquet/TSV products. Browser fetch success is not an archive deposit; the links below may change. Full web-page bytes were not archived or hash-pinned by this review.

| Official source URL | Observed date/version | Finding and retrieval limit |
| --- | --- | --- |
| [Open Targets licence](https://platform-docs.opentargets.org/licence) and [Markdown](https://platform-docs.opentargets.org/licence.md) | Current page, no explicit revision date observed | Data/code distinction and source licence table; see OT card |
| [Open Targets terms](https://platform-docs.opentargets.org/licence/terms-of-use) | Updated June 2021 | Retrieved after recovering the correct nested URL from the official documentation index; preserves original-owner/third-party rights |
| [Open Targets 25.09 announcement](https://blog.opentargets.org/open-targets-platform-25-09-release/) | 2025-09-17 | Release identity/date, not field-level historical eligibility |
| [Open Targets access documentation](https://platform-docs.opentargets.org/data-access) | Current page | Provider-supported downloads/API routes; no payload fetched |
| [GWAS Catalog licensing](https://www.ebi.ac.uk/gwas/docs/about/#licensing-information) | Current page, no explicit revision date observed | Dataset-specific exception boundary; see OT card |
| [EMBL-EBI terms](https://www.ebi.ac.uk/about/terms-of-use/) | Last revised 2026-10-14 | Current host/service terms; no historical release-specific licence proof inferred |
| [HGNC licence](https://www.genenames.org/about/license/) | Current page, no explicit revision date observed | CC0/attribution evidence; see HGNC card |
| [HGNC archive help](https://www.genenames.org/download/archive/) | Current retention policy | Monthly/quarterly policy; no archived payload match tested |
| [Qwen exact revision tree](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/tree/b466e1f8c07172155743e8e1307507d8a4f91fbd), [README](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/blob/b466e1f8c07172155743e8e1307507d8a4f91fbd/README.md), [commit](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/commit/b466e1f8c07172155743e8e1307507d8a4f91fbd) | Commit date displayed 2024-09-20 | Apache-2.0 metadata and listed LICENSE; no model bytes read |
| [Qwen GGUF current LICENSE](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/blob/main/LICENSE) | Current main; file history labels update `8f337b5` | Full licence text accessible; exact historical-byte equivalence untested |
| [Qwen upstream Instruct current LICENSE](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct/blob/main/LICENSE) | Current upstream repository | Corroborating separate product only, not a substitute for the exact GGUF licence |
| [Apache authoritative text](https://www.apache.org/licenses/LICENSE-2.0) | Version 2.0, January 2004 | Redistribution conditions; see code/font card |
| [Microsoft font FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq) | Updated 2024-11-19 | Document embedding differs from font-file redistribution |
| [Microsoft OS/2 embedding flags](https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fstype) | OpenType 1.9.1 page | Technical interpretation of the observed local font flags |

The following requests failed through the web tool and were not treated as absence of rights: [OT25.09 directory listing](https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/output/); the initially guessed [OT terms URL](https://platform-docs.opentargets.org/terms-of-use) and its `.md` variant; the correct terms page's [.md variant](https://platform-docs.opentargets.org/licence/terms-of-use.md); guessed `data-access/data-download.md`; and Qwen's exact-revision [LICENSE blob](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/blob/b466e1f8c07172155743e8e1307507d8a4f91fbd/LICENSE), [raw](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/raw/b466e1f8c07172155743e8e1307507d8a4f91fbd/LICENSE) and [resolve](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/resolve/b466e1f8c07172155743e8e1307507d8a4f91fbd/LICENSE) URLs. Errors were tool retrieval/cache errors; no claim is made that those resources do not exist. The correct OT terms page and Qwen current-main LICENSE were subsequently retrieved. Microsoft's pages showed an authorization notice in extracted boilerplate but the cited FAQ/specification body was readable; no sign-in was attempted.

## Local metadata anchors

The following are the primary local evidence anchors. Ancillary read-only discovery also covered the public P05 register's count/unknown metadata and project README/packaging licence references. Source originals were not reread. SHA-256 values bind this local observation; they are not third-party permission certificates.

| Path | SHA-256 | Purpose |
| --- | --- | --- |
| `LICENSE` | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` | Declared project Apache-2.0 text |
| `planning/review-assets/preprint-p05-20261031/FRAME-METADATA-PREFLIGHT-v1.json` | `c9af0da5ff7a07b95372383d73c493faef0ba4081a34768d88393a881ff26551` | Family formats/counts/byte sizes and source URL metadata |
| `planning/review-assets/preprint-p05-20261031/ACQUISITION-METADATA-v1.json` | `428ab3be53abffb24f8d2e95e457f603012b8e66a3ee02575e696f996b00a405` | Complete credible-set inventory/count/bytes |
| `paper/manuscript.md` | `b01d42fccaf046ad0db52d0becd36be994eac440759f23aefaa0673bf7a9ce29` | Frozen stated scope and retained source/model identities |
| `paper/supplement.md` | `977aba2fc3cab68513a78fde08b3cacf0a375af52c908c0fd46bbf1818337200` | Frozen acquisition/model/reconstruction qualifications |
| `paper/PDF-BUILD.json` | `f920afd5ea4259ca8f8f4da4255dc43a0d317978cffabf7434dc8ac4ba77dcb5` | Font-file hashes and subset-when-used policy |
| `paper/asof-source-reporting-preprint.pdf` | `4f19060e0bb67fdd932780de9765a415f42c518cde74895302aa45b942ead588` | Read-only font-resource inspection, no re-render |

Metadata arithmetic: `180049263 + 2588111695 + 75568567 + 5545555 + 16973159 = 2866248239` bytes; file counts `100 + 25 + 10 + 1 + 1 = 137`. This is a source inventory, not an independent-sample count. Parquet full-file hash verification requires originals, not only the 24 used rows. Existing local hashes/receipts do not imply that the provider published those hashes.

For `arial.ttf` (1,045,720 bytes) and `arialbd.ttf` (989,780 bytes), a read-only standard-library SFNT directory/OS/2 metadata probe returned `fsType=8`; SHA-256 values matched `PDF-BUILD.json` and are printed in the code/font card. Read-only pypdf inspection found embedded Arial regular/bold TrueType subsets and unembedded Base-14 Helvetica, Helvetica-Bold and Times-Roman resources. No unused loaded font was described as embedded. No installed-font ownership/entitlement finding is made.

## Decision and limits

The five cards under `paper/release/cards/` recommend external original sources plus reviewed portable URL/hash manifests, model metadata only, no model/font/runtime payloads, and an explicit file allowlist for project code and reviewed presentation artifacts. HGNC CC0 inclusion remains a possible later explicit choice; OT CC0 is recorded without converting it into blanket clearance of independently sourced upstream products. Source-derived payloads require their own classification. Fresh exact-source accessibility and a complete dependency/record-level rights map remain unestablished.

No third parties were contacted and no external expert review was requested. This draft adds no author, funding, institutional, clinical or scientific-validity facts. It is sufficient to make release choices reviewable; it is not a public deposit, a licence opinion or permission to expand the closed model branch.

## Produced draft cards

All paths below are under `paper/release/cards/`. A read-only check verified UTF-8 decoding, draft labels, Markdown table borders and absence of internal web citation IDs. The frozen manuscript, supplement, renderer and PDF were unchanged; the PDF still has the hash above. No execution test is appropriate for these documentation-only additions.

| Card | Bytes | SHA-256 |
| --- | ---: | --- |
| `OPEN-TARGETS-25.09-DATA-CARD-DRAFT-v1.md` | 4,827 | `8154d619a7c0efa10e86e85a204e78903cf6f17349a19a7f3007a6283c7cc2cd` |
| `HGNC-REFERENCE-DATA-CARD-DRAFT-v1.md` | 2,855 | `93238605bc4abb03e96dcae2d2735c175ed2d4455463bf88ad5b53440bb65d21` |
| `QWEN2.5-14B-INSTRUCT-GGUF-MODEL-CARD-DRAFT-v1.md` | 2,913 | `39a7e1962b61b2b60a045ae56132e890dae54fa95dec53f67520baf8775e10b6` |
| `PROJECT-CODE-AND-PDF-FONTS-RIGHTS-DRAFT-v1.md` | 3,546 | `e16451c1799b4d3b3ea5839d3f7ba684f60b22f94c583136919f30a7a18df90c` |
| `RIGHTS-DISPOSITIONS-DRAFT-v1.md` | 4,247 | `2424e86efede286952ce7c38c2fc1d80b7f4c92a087f72be14ab3035c5267035` |
