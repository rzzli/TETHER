# Three-view research contract

The experimental reducer in [research_views.py](../tools/science/research_views.py)
constructs archived, contemporary date-filtered and contemporary unfiltered views
over a fixed hypothesis universe. It is separate from production agent admission.
The pure reducer operates on caller-supplied rows: **a passing reducer test does
not qualify local datasets or authorize a real-data experiment.** The optional
[Arrow reader](../tools/science/research_parquet.py) checks exact original bytes,
uses caller-approved roots and selects approved columns with `pyarrow==21.0.0`.
It filters candidate target/disease IDs before converting rows to Python. Its
batches preserve physical row-group offsets and account for omitted rows; their
payload hashes must match the reducer's source declarations.

Every view retains the same decision origin, complete hypothesis identifiers,
namespace versions, action, modality, tissue and method fingerprint. Both current
views use exactly the same evidence sources and mapping ancestors. Their difference
is a fixed `publicationDate` filter: the reported calendar interval must lie wholly
before the UTC-midnight origin. Unknown dates remain excluded from the filtered
view and visible in its counts. This date describes a reported publication, not
when the assembled evidence or annotation became available.

The archived view requires an availability bound at or before origin for every
declared ancestor, including identifier mappings. Unknown publication dates may
remain unknown when a qualified archived release bounds their availability;
explicitly later publication conflicts are excluded. Newer ancestors retain their
true clocks in the contemporary views. They remain ineligible under the unchanged
production temporal check even when a row passes the research date filter.

The reducer accepts only the selected nonclinical sources `gene_burden`,
`uniprot_literature` and `expression_atlas`, with their expected raw datatypes.
Its explicit projection excludes clinical status, outcomes and aggregate scores.
It rejects evaluator-only ancestors, labels and clinical products before consuming
rows. A producer cannot qualify such a parent by renaming a generated child.
Historical acquisition receipts and evaluator projections remain unchanged.

The caller must separately authenticate original bytes, physical row locators,
mapping membership and artifact-specific use permissions. The reducer reports
these as requiring external verification; its declared-lineage temporal verdict
is not a provenance certificate. A receipt proves neither a new use grant nor
earlier public availability. [source_receipts.py](../tools/science/source_receipts.py)
checks both retained transport formats without rewriting either format or granting
actor access. Missing receipt roles remain unknown.

Coverage reconciles physical rows, failed row checks, rows outside the selected
case universe, selected rows, duplicates, conflicts, date exclusions and accepted
records. Conflicting selected records with the same source/evidence ID are all
withheld. Identical duplicates contribute one record. A source row may correspond
to multiple action/modality hypotheses; case-record counts are reported separately
and never imply action-specific support. Numerical prediction features stay empty
and probabilities stay null. No selected input is not biological absence.
Rows outside the selected hypothesis universe receive no scientific QC verdict;
their other fields need not be converted. The reader's in-memory counters record
failure/interruption and do not substitute for the enclosing run journal.

The implemented reducer and receipt checks have invented-data regression tests in
[test_research_views.py](../tests/test_research_views.py) and
[test_source_receipt_qualification.py](../tests/test_source_receipt_qualification.py).
The [durable research driver](../tools/science/research_build.py) binds an
independently selected request hash and owner-approved grant hash to exact
originals, catalog permissions, implementation fingerprints and mapping inputs.
It reserves output before inspection, journals progress/failures, checks source
receipts and mappings, and seals three bounded views. A failed directory is
preserved; a retry requires a fresh directory. `inspect-run` describes build
journals without restarting them. Each view has a 64 MiB limit.

High-precision UTC receipt times are rounded upward to microseconds only for
availability bounds; original timestamp strings remain in provenance. Public
download times do not establish historical availability. Old collection roles
remain unchanged, and only the separately approved original artifacts receive
the isolated research-use role. Production admission is unchanged.

Real-data construction, source-inclusive audit and a retained feasibility
decision are required before P11 can pass. P13–P15 separately qualify the
scientific method, freeze its protocol and execute the resulting study. A sealed
development build is neither an independently replayed result nor a scientific
validation claim.

The [identifier-index builder](../tools/science/research_mapping.py) independently
replays target and disease IDs from the pinned 24.09 originals. It checks complete
publisher-listed partition membership, receipt and payload hashes, the retained
release notice, physical row counts and unique canonical IDs. Only `id` plus
`approvedSymbol` or `name` are decoded. A fresh output directory contains a
hash-chained journal, source-linked index and terminal seal; failures remain
unsealed. This diagnostic supplies identifier membership and never grants a new
use permission or upgrades scientific validation.
