# HGNC exact-replay and neutral-query addendum

Status: DRAFT_LOCAL_BUNDLE_RECOMMENDATION. Date: 2026-11-01. This addendum refines the earlier external-HGNC default without changing the original rights cards or audit. It is not legal certification or publication authorization. No source file was opened or copied during this metadata-only review.

## Recommended HGNC exception

**Allow one exact HGNC original into the generated local release bundle, outside Git and the wheel.** This is the current recommendation where the earlier cards used an external-HGNC default. Keep the 136 Open Targets 25.09 Parquet originals external at their versioned provider URLs, subject to exact-file hash verification and access limitations. The complete native reconstruction still requires all 137 actual-format originals; the HGNC exception improves access to one dependency rather than changing that scope.

The [official HGNC licence](https://www.genenames.org/about/license/), rechecked 2026-11-01, places all HGNC data under CC0 and recommends attribution. That dataset-wide statement supports including the retained complete-set TSV. Preserve the [CC0 1.0 identifier/legal-code link](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en), HGNC attribution and `RRID:SCR_002827`, and the provider's [citation guidance](https://www.genenames.org/about/license/#attribution). This exception covers the HGNC file, not unrelated linked products or other source families.

| Bundle identity field | Required value |
| --- | --- |
| Suggested portable bundle path | `sources/hgnc/snapshot_2026-10-10/hgnc_complete_set.txt` |
| Provider / dataset | HGNC / `hgnc_symbols` complete-set TSV |
| Local acquisition designation | `snapshot_2026-10-10`; not a certified HGNC annotation release |
| Exact bytes | 16,973,159 |
| Exact SHA-256 | `64fcdfcdf9bc0853ec502e0e4c7d6eb12647b2ca8b0e635ea04bdb584856baf7` |
| Recorded acquisition URL | `https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt` |
| Recorded receipt completion | `2026-10-11T01:57:36.1068058+00:00` |
| Receipt qualification | `cache_hit=true`; completion metadata is not proof of first acquisition time |
| Checksum origin | Local capture; no publisher checksum or independent object-version identifier supplied |

The existing independent source-input audit records this exact full-file byte count/hash, matching the transport receipt. This addendum relies on that retained audit and does not claim a new original-byte verification. When constructing the local bundle, the builder should copy only the explicitly allowlisted original, verify source and copied byte count/hash against the values above, and abort on mismatch. Preserve the source URL, receipt identifier/hash, licence/citation/access date, and a statement that the TSV is unmodified. Use portable paths in distributable metadata; a sanitized receipt projection is a new metadata artifact with its own hash, not the original receipt bytes. Do not include installed environments, credentials, other source files or source-derived packets by recursive copying.

## Why the current URL is insufficient for exact replay

The receipt uses an unversioned current endpoint. It carries no cloud object generation, ETag or last-modified/version identifier. HGNC's [archive help](https://www.genenames.org/download/archive/), rechecked 2026-11-01, describes month/quarter snapshots, not a guarantee that a 10 October acquisition matches one of them. No archived payload was downloaded or matched here. Therefore exact public reacquisition is **not established**, rather than proven impossible. A current or adjacent archived file must not silently replace the retained file. The proposed exact local copy avoids depending on that unproven equivalence. Fresh retrieval of the 136 external Open Targets originals remains separately untested.

## Neutral queries and hashes versus excluded payloads

These classes should be distinct in the release allowlist:

| Class | Proposed treatment |
| --- | --- |
| Frozen case routing: `case_id`, public canonical `targetId`, `diseaseId`, selected `studyLocusId`, `release_id`, selection seed/order rule, `unit_hash` | Allow explicitly reviewed query metadata. These identify what to look up; they are not measurement answers or an asserted study/variant agreement. |
| File/task/code/plan hashes, original byte sizes, formats, provider URLs, portable logical paths, namespace/version declarations | Allow reviewed provenance metadata. A digest does not reproduce the hashed payload or certify its rights/science. |
| Source-derived dates, exposure tags or physical-row counts carried alongside routing | Classify and review separately as provenance/selection metadata. Do not call the whole file a minimal query-only projection merely because its IDs are neutral. |
| Parquet rows, HGNC record extracts, native numeric values and null/empty/absent measurement facts, generation packets, expected references and raw report fact payloads | Continue default exclusion unless an exact file receives a separate explicit disposition. The one whole-file HGNC exception above does not admit these other payloads. |
| Historical human/answer or protected/outcome-aware ancestry | Remains excluded; an identifier or hash field name does not change its ancestry. |

The existing sealed selected-case plan contains routing fields together with dates/counts/exposure metadata. This review inspected its keys and hash, not the actual query identifiers. A separately projected public query manifest must have its own schema and hash, with the original sealed plan hash retained as provenance; it must not be represented as the original byte-identical plan or passed through an unchanged exact-hash gate under that claim. Conversely, a deliberately reviewed complete neutral/provenance plan may be allowlisted as such after confirming its field content and ancestry. Do not blanket-exclude public query IDs, and do not blanket-admit every object that contains an `id` or `sha256` field.

Evidence pins and the preserved original-audit hash are in `planning/review-assets/preprint-p09-20261101/RIGHTS-SOURCE-AUDIT-ADDENDUM-v1.md`.
