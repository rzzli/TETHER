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
- `hosted-ci-registry.json`: all four hosted jobs passed at `f57c448`.
- `registry-recovery-verification.json`: private release downloaded, all 146 archive
  entries / 2,842,669,284 source bytes restored and rehashed, code cloned/fsck-checked,
  232,722 SQLite observations checked and all 21 milestone files verified afterward.
- `prior-risk-audit.json`: source proofs for three unresolved prior-risk programs
  without incident event IDs; no labels changed.
- `preserve_registry.py`: prepare/restore-test an exclusive registry recovery bundle;
  it performs no uploads or deletions. Uploaded assets remain private.

The verified private recovery release is
https://github.com/rzzli/drug_target_agents/releases/tag/registry-sizing-20261017 .
Its 541,153,875-byte evidence ZIP and Git bundle cover the runtime checkpoint
`f57c448`; the metadata/restore-helper closeout is separately retained in Git and a
small closeout bundle. The asset-index SHA-256 is
`bb4006c601e4ad18ddba041b44c6f8a9be1dbbd34d38106293483dd66a355080`.
Core milestone SHA-256:
`83361699b956059b01accf68d96e572928d19fc8888829872121a625cc329a0d`.

These recovery bundles exclude full original AACT archives and PostgreSQL pages.
They protect the selected evidence/workspace, not the entire data inventory.
Independent scientific validation and empirical power remain open.
