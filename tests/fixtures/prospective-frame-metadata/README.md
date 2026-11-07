# ClinicalTrials.gov schema fixtures

These four small public metadata responses contain schema/documentation, not
trial records. They are byte-identical to the October 24, 2026 UTC captures
referenced by the [archived protocol](https://github.com/rzzli/TETHER/blob/b492a8fca9bb1aa500d2939b3e2d19242a55cb96/planning/protocols/prospective-endpoint-readiness-v0.1.json).

- `01-openapi.yaml`: https://clinicaltrials.gov/api/oas/v2
- `02-metadata.json`: https://clinicaltrials.gov/api/v2/studies/metadata
- `03-search-areas.json`: https://clinicaltrials.gov/api/v2/studies/search-areas
- `04-version.json`: https://clinicaltrials.gov/api/v2/version

Original receipts and hashes are referenced by the
[archived metadata check](https://github.com/rzzli/TETHER/blob/b492a8fca9bb1aa500d2939b3e2d19242a55cb96/planning/review-assets/prospective-endpoint-readiness-20261023/metadata-source-check.json).
These working records are preserved in the historical checkpoint, outside the
current public tree; [tools/history.py](../../../tools/history.py) reads their
exact bytes for compatibility tests.
The tests copy these bytes into temporary roots and verify the original protocol's
parent hashes. This keeps offline and clean-checkout tests independent of ignored
download directories. Version metadata is a fixture, not a current API check.
