# Historical mapping input qualification

**Pass for the four explicitly approved mapping projections.** This does not
complete Science 3 or qualify predictive biological features. The selected
integrated Open Targets 24.09 release predates the January 1, 2025 UTC origin.
The [official release announcement](https://community.opentargets.org/t/24-09-platform-release-now-live/1556)
is dated September 18, 2024. A conservative next-day availability bound is retained;
retrieval in October 2026 is recorded separately and does not supply that bound.

The project acquired 805 files totaling 121,968,718 bytes into a new E: namespace,
including all 200 original Parquet partitions of each selected product. Every
Parquet parent matched the publisher SHA-1 manifest, whose own published SHA-1
also matched. SHA-256 and immutable separate receipts identify the locally retained
bytes. Every one of 115,821 projected rows was subsequently compared with its
original physical Parquet row. Original download workers, receipts and stopped
monitor were untouched. No AACT endpoint data were read or joined.

| Product | Rows | Permitted information |
|---|---:|---|
| targets | 63,121 | Historical Ensembl IDs, names, synonyms and identifier cross-references |
| diseases | 28,327 | Disease IDs, names, synonyms, cross-references and obsolete terms |
| molecule | 18,041 | ChEMBL IDs, names, synonyms, trade names, cross-references, parent/child IDs and drug type |
| mechanismOfAction | 6,332 | Resource-annotated drug-to-target mechanisms, target IDs, action type and references |

Clinical phase, approval/withdrawal, linked diseases/clinical indications, clinical
trial fields, drug warnings, known-drug evidence and association scores are excluded
from projected records. Original mixed-column molecule parents remain quarantined;
only the approved columns were decoded. Complete partition coverage of these four
products is not complete coverage of the Platform's biological evidence.

The [archived configuration](https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/24.09/conf/platform.conf)
declares ChEMBL **34** and Ensembl **112**. Its literal data_version is **24.09dev**;
that publisher inconsistency is retained rather than silently rewritten. Release
identity is instead fixed by the dated announcement, official 24.09 archive path
and complete matching publisher manifest. The [archived input manifest](https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/24.09/input/manifest.json)
declares EFO **v3.68.0**, MONDO **v2021-12-30** and an HGNC capture created
2024-08-16T16:50:06+00:00. No separately numbered HGNC release is declared. Historical
HGNC labels and IDs already in the integrated targets output suffice for this
mapping projection; HGNC 2026 is not used. ChEMBL 35 and OT25.09 are not substituted.

Upstream capture dates, dataset release, paper publication, per-record annotation
and retrieval are distinct. Individual annotation/publication dates are not supplied
and remain unknown. Frozen integrated annotations are bounded by the dataset release.
The input manifest labels its own resource validation NOT_VALIDATED and may retain
checksums of pre-transformation captures. Those declarations are not represented as
independent re-verification of every original upstream distribution. Actual archived
integrated Parquet bytes, publisher checksums and row locations are the direct
admission parents. No annotation field is refreshed from a live upstream endpoint.

Mapping text supports a historical lexical/extractive baseline. Mechanism matches
remain candidate resource annotations; synonym collision, regimen identity, target
complexes, salts/parents, modality and indication equivalence require separate
adjudication. This package does not assign clinical program mappings automatically.
An association baseline would minimally require associationByDatasourceDirect plus
explicit source exclusions and score semantics; genetics requires method-specific
evidence qualification. Both remain withheld. Missing contemporary adapter fields
must remain unavailable, with no current-release fallback.

The actual manifest and lineage/projection contract are under
`data/derived/science-prerequisites-20261018/historical-inputs-20261018T173300Z/`.
Sanitized counts, limits and verification are in `historical-input-report.json` and
`historical-input-validation.json`. Seven focused tests cover forbidden clinical
fields/products, future dates, malformed/path-unsafe publisher manifests, no-clobber
receipts, changed physical parents and rehashed forbidden projection fields.

There is no file/access blocker for this mapping scope. Remaining scientific feature
qualification is an agent-assessment task, not a request for a human-provided file.
