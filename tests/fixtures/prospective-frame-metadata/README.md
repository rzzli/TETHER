# ClinicalTrials.gov schema fixtures

These four small public metadata responses contain schema/documentation, not
trial records. They are byte-identical to the October 24, 2026 UTC captures
referenced by `planning/protocols/prospective-endpoint-readiness-v0.1.json`.

- `01-openapi.yaml`: https://clinicaltrials.gov/api/oas/v2
- `02-metadata.json`: https://clinicaltrials.gov/api/v2/studies/metadata
- `03-search-areas.json`: https://clinicaltrials.gov/api/v2/studies/search-areas
- `04-version.json`: https://clinicaltrials.gov/api/v2/version

Original receipts and hashes are referenced by
`planning/review-assets/prospective-endpoint-readiness-20261023/metadata-source-check.json`.
The tests copy these bytes into temporary roots and verify the original protocol's
parent hashes. This keeps offline and clean-checkout tests independent of ignored
download directories. Version metadata is a fixture, not a current API check.
