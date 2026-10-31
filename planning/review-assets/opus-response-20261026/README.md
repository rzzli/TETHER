# Evidence for the independent project review

Baseline: `cc0042c`. Review date: 26 October 2026 UTC. These records support the
independent project review and recovery plan; they do not validate the science.

- `audit-evidence.json`: fresh repository inventory, 213 unchanged code/test pins,
  canonical report/receipt anchors and hash-only protected-label checks.
- `engineering-audit.md`, `engineering-probes.json`, `engineering_probe.py`:
  independent code findings and synthetic reproductions.
- `engineering-validation.json`: fourteen existing local-model regressions pass.
- `science-audit.md`: independent hypothesis/data/analysis assessment.
- `full-validation.json`: fresh full-mode tests, required probes and wheel/demo
  acceptance outside the restricted sandbox, with no network acquisition.
- `expert-packet-provenance.json`: exact source/candidate parents and blank packet
  hashes; no answers or previous verdicts are included in the shareable packet.
- `expert-packet-validation.json`, `expert-browser-validation.json`: blank PDF,
  field/appearance/read-back checks and ten headless-browser interaction checks.
- `closeout.json`: final file/log hashes and documentation consistency checks.

`audit_project.py` is a read-only inventory helper. `run_validation.py` runs the
existing suite with workspace-local temporary storage and the existing portable
PowerShell. `build_expert_packet.py` and `validate_expert_packet.py` use the
Codex bundled document dependencies. They are artifact-build helpers, not new
framework runtime adapters.

Failed default-temp/sandbox validation attempts and browser-render intermediates
remain under ignored `data/cache/opus-response-*`. The sandbox workspace attempt
ran 1,262 tests with 89 errors/one failure caused by denied hard links, then hit
uv cache persistence denial. A hard-link fixture succeeds outside the sandbox;
the approved outside-sandbox full rerun passes unchanged production code. Raw
logs are hashed in the closeout. Do not relabel failed attempts as passing.

The expert form is exposed development material. Completed human reviews remain
pending. Source fidelity, independent scientific judgment and clinical validity
are distinct. Never place answer exports or the coordinator guide in agent input
manifests. Share only the individually selected files or clean share ZIP in
`docs/expert-review-20261026/`.
