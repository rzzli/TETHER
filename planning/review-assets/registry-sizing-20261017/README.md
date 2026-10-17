# Registry-sizing milestone evidence

See [the decision report](../../Registry-scale%20Cohort%20and%20Label%20Audit%20v0.4.md).
The report and `data/manifests/public/2026-10-17-registry-sizing.json` identify the
canonical evaluator-only products; diagnostics are retained separately.

- `sizing-summary.json`: final counts, mapping/role exclusions and missingness.
- `technical-audit.json`: original-row checks and final 185-program sample accounting.
- `semantic-audit.json`: 33 AI-assisted source-narrative annotations, not independent gold.
- `resource-report.json`: measured frame/index/audit bytes, wall time and process memory.
- `validation-completion.json`: final full local tests/probes/installed-wheel checks;
  the other validation files retain earlier successful passes.
- `off-machine-recovery-verification.json`: downloaded baseline recovery test.
- `hosted-ci-baseline.json`: four passing jobs at `d069dcd`.
- `preserve_registry.py`: prepare/restore-test an exclusive registry recovery bundle;
  it performs no uploads or deletions. Uploaded assets remain private.

Final-registry remote recovery and hosted CI are pending until their retained result
files are added here. A prepared ZIP alone is not a verified off-machine backup.
