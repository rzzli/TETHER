# Feasibility-review evidence

Review date: October 9, 2026 (America/Los_Angeles).

- `access-audit.json`: actual small HTTP probes, hashes of six downloaded Virtual Biotech files at commit `71f9da68c95c5ee0ef4c1d9b8f45f10693de022d`, and counts from its released CSV. Raw files were cached in the operating system temporary directory; those paths are local conveniences, not portable artifacts.
- `audit-sources.ps1`: repeatable public-source inspection. It downloads approximately 6 MB of labels plus small source files and documentation pages. It does not request credentials, create accounts, execute agents, or download full biomedical datasets.
- `capacity-planning.ps1` and `capacity-planning.json`: reproducible illustrative sample-size calculations, with assumptions and limitations.
- `peer-survey.csv`: focused paper/system inventory. A code-inspection finding is not an end-to-end performance result. Publication metrics have not been reproduced.
- `framework-review-2026-10-10.json`: October 10 runtime source fingerprints and ten fictional probes reproducing five correctness issues and four integration gaps. Reproduce with `uv run python tools/review/probe_framework.py --output planning/review-assets/framework-review-2026-10-10.json` from the project root. Probe success means the behavior was observed, not that the defect is fixed; runtime source is unchanged. See [[Framework Code Review and Next Stage Plan]].

Run the PowerShell scripts from any working directory. They write their JSON outputs next to the script unless `-OutputPath` is specified. HTTP failures are recorded rather than treated as proof that a resource does not exist. An S3 listing failure does not establish object-level download permissions.

The recorded second S3 probe used the path-style endpoint after the first endpoint encountered an SSL error. The corrected CSV field names are `primary_endpoint_result` and `virtualbiotech_stop_reason_categories`.
