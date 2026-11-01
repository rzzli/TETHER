# P09 HGNC exact-replay rights audit addendum v1

Status: DRAFT_METADATA_ONLY_LOCAL_BUNDLE_RECOMMENDATION. Review date: 2026-11-01. The original `RIGHTS-SOURCE-AUDIT-v1.md` remains unchanged at SHA-256 `d80910d19c72ff76794af35fc733de429063caa3bcdd464f8706a984cae22053`. The original five cards also remain unchanged. This addendum records a narrow revised packaging recommendation, not a completed copy, publication or legal certification.

## Evidence and result

The original transport receipt identifies a completed HGNC complete-set TSV, locally named `snapshot_2026-10-10`, 16,973,159 bytes and SHA-256 `64fcdfcdf9bc0853ec502e0e4c7d6eb12647b2ca8b0e635ea04bdb584856baf7`. It gives the unversioned [current TSV endpoint](https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt), receipt completion `2026-10-11T01:57:36.1068058+00:00`, `cache_hit=true`, and `checksum_origin=local_capture_only`; publisher/expected-hash verification are false. There are no recorded GCS generation, ETag or source object version fields. The completion timestamp does not establish the first network acquisition time or a provider release date.

The retained independent `INPUT-AUDIT-v1.json`, status `PASS_ORIGINAL_SOURCE_INPUTS_AND_NEUTRAL_TASKS`, records the identical byte count/hash for HGNC `original-126`. This is stronger retained identity evidence than the earlier preflight, which expressly had not rehashed the payload. No original was reread or rehashed for this addendum. No current/archive replacement was downloaded.

The [official HGNC licence](https://www.genenames.org/about/license/) and [archive help](https://www.genenames.org/download/archive/) were rechecked on 2026-11-01. The former supplies dataset-wide CC0 evidence; the latter does not establish a byte-identical monthly/quarterly copy of this acquisition. The [official CC0 1.0 legal code](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en) was also checked; it concerns the affirmer's copyright/related rights and does not clear unrelated third-party rights. No release-specific historical licence-page capture was established, and no contact or expert opinion was sought.

**Recommendation: explicitly admit only this exact HGNC TSV to the generated local release bundle, with its CC0/citation/hash/receipt metadata; exclude it from Git and wheels.** A bundle builder must verify the original and copied bytes against the fixed identity before admitting it. The other 136 Open Targets originals remain external versioned-URL dependencies with frozen hashes. This is an operational response to an unversioned HGNC endpoint; it does not claim present public reacquisition of any exact file, and it does not license packet/reference/result payloads by association.

## Metadata-only local reads

| Evidence artifact | Bytes | SHA-256 | Inspected scope |
| --- | ---: | --- | --- |
| HGNC original transport receipt, identifier `hgnc-snapshot-2026-10-10` | 755 | `2bb6c48fd9d5585b8ed5690ad69046cf4ed55ffd2de47f525332e69eeab92076` | Receipt metadata only; original machine root omitted here |
| `planning/review-assets/preprint-p05-20261031/INPUT-AUDIT-v1.json` | 80,458 | `08f8c7ae7703a6d43533a97500f30f56b5c0946cb80b6ae7b3de38d29a12fd01` | Status, original hash/count metadata and audit pins; report declares no raw scientific values |
| `data/derived/preprint-p05-source-inputs-20261101T074942Z/seal.json` | 39,093 | `5b151d07b2203952b84057a2d376e278df11c33251b2df882d51a025998b18cb` | Seal status, artifact descriptors, no source rows |
| `data/derived/preprint-p05-source-inputs-20261101T074942Z/selected-case-plan.json` | 4,927 | `0c898976042749dcd6a52ba1d0c43164d1073e9bd2f5f5b9b1ef0d23d8225628` | Hash, top/row field names and types; no identifier/date/count values printed |

Ancillary read-only evidence included the previously pinned frame metadata, input DRAFT/READY/launch metadata and `INPUT-BUILDER-NOTES-v1.md`. No source snapshot, raw packet, expected reference, original TSV/Parquet body, human response or protected input was read. One read-only text search initially used a Windows-incompatible glob and was corrected with `rg`'s `-g` option; it caused no file change. No scientific or execution result is added.

## Query-metadata distinction

The sealed case-plan keys include `case_id`, `targetId`, `diseaseId`, `studyLocusId`, `release_id` and `unit_hash`, along with `availableAt`, `publicationDate`, `eligible_physical_rows`, exposure and historical-eligibility metadata. The first group can be explicitly allowlisted as public source-query routing; the companion dates/counts are separate provenance/selection fields, not numeric measurement values but also not a minimal query-only schema. A public projection is a new artifact, and cannot inherit the original file's byte hash. Retained task/reference hashes are descriptors, not bundled facts or authorization to open their contents.

The new card distinguishes those classes from excluded row/measurement payloads and answer/human ancestry. It retains actual-format reconstruction: all 137 full originals must match the frozen inventory, with this one exact HGNC file potentially bundled and 136 Open Targets files supplied externally. It does not downgrade the claim to fictional tests or claim that the 24 used rows reconstruct full-file hashes.

Produced card: `paper/release/cards/HGNC-EXACT-REPLAY-ADDENDUM-v1.md`, 6,202 bytes, SHA-256 `380c130a0261a2248c2008118bd914da4e5f24b794b44a855e9c93035ea2f82d`. A final read-only check confirmed the original audit and all five original card hashes unchanged, valid UTF-8 and table borders for both addenda. Only the two new Markdown addenda were written.
