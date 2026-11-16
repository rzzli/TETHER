# Contributing

Use the [maintained development gates](docs/MAINTENANCE.md). Keep runtime dependencies empty; ingestion and developer tools have separate pinned environments. Install both packages noneditably before testing installed identities. Keep normalized data, receipts and private working records out of commits.

For a change, explain the failure it fixes and retain the relevant validation result. Add a regression for correctness changes. Run `tools/quality.py`, the affected tests and the maintained gate; historical tests need the original environment identified in the [migration guide](packages/tether/MIGRATION.md). Do not update old scientific hashes to make a test pass.

Coverage thresholds are reviewed baselines, not a substitute for assertions. Explain any threshold or test-scope change; never automatically lower thresholds after failure. Formatting and strict typing currently cover the explicit stage-one files, not the entire research tree. Expanding that scope is encouraged in separately reviewable changes.

Report scientific validation separately from software tests. A successful verifier does not establish an authentic publisher, independent timestamp, causal effect or clinical prediction. Keep owner declarations pending until supplied. Do not publish datasets, models, package releases or manuscript submissions without their applicable authorization.
