---
title: Full Repository Review and Verified Findings
date: 2026-10-11
timezone: America/Los_Angeles
status: review-complete
tags:
  - asof
  - review
  - audit
---

# Full repository review and verified findings

This is an independent, full-repository flaw/gap review requested outside the normal
development flow, covering `src/asof/`, `tools/`, `data/`, `runs/`, `tests/`, `docs/`,
`memory/` and `planning/` itself. It cross-references the existing self-reviews
([[Agentic Target-Evaluation Frameworks Critical Review]], [[AsOf Feasibility Analysis
and Peer Survey]], [[Framework Code Review and Next Stage Plan]], [[Project Audit and
v0.2 Completion]]) rather than repeating them, and adds a verification pass: the
highest-stakes claims below were re-checked by actually executing code against this
repository, not only by reading it. One finding from the first pass was corrected after
that execution; it is marked below.

## Scope and method

Direct reading of all 14 `src/asof/*.py` modules, `tools/framework/run_pilot.py`,
`tools/review/probe_framework.py`, all top-level docs, `pyproject.toml`/`.gitignore`, and
representative tests, plus three parallel explorations covering (1) the data-acquisition
pipeline and `tools/`/`runs/` outputs, (2) synthesis of the five prior planning documents
and the `memory/` log, and (3) the test suite, docs-vs-code accuracy, and project
meta/config. A second pass then re-ran the most consequential and falsifiable claims
against the real `.venv`, the real CLI, and the real system clock, rather than trusting
the static reading.

The user's unrelated global Claude Code configuration (an academic-literature-review
toolkit) does not apply to this repository — no project-level `.claude/` directory exists
here, confirmed by recursive search.

## Critical / structural findings

1. **No version control.** No `.git` directory exists (confirmed by running `git status`
   from the repo root: `fatal: not a git repository`). This exact gap was already raised
   in [[Framework Code Review and Next Stage Plan]] ("the workspace is not currently a Git
   repository... establish version control... before broader changes") and never acted
   on. Both `.gitignore` files are already correct; `git init` today would cleanly exclude
   the ~990MB of generated content already on disk (`runs/` 768MB, `data/derived/` 141MB,
   `.venv/` 81MB) with nothing to clean up first.
2. **No live model backend exists anywhere in the codebase.** `src/asof/agents.py` ships
   only `ExtractiveBackend` (a non-ML baseline that selects all visible evidence verbatim)
   and `ReplayBackend` (fixture replay for tests). Confirmed at runtime: running
   `python -m asof demo` end-to-end and inspecting the produced `run.json` and
   `dossier.md` shows `"backend_id": "offline-extractive-v1"` and the dossier's own text,
   *"No live model provider or scientific computation is invoked by the default
   backend."* `tools/framework/run_pilot.py`'s subprocess call never passes `--replay`
   either, so the real-data pilot runs used the same trivial backend. This is the literal
   "agent" in "target_agents," and it does not exist yet — only the harness it will plug
   into.
3. **No real prediction has ever been produced on real data.** Confirmed at runtime by
   reading `prediction.json` from the completed real-data pilot run
   (`runs/v02-realdata-20261012T015124Z/cftr-mondo_0009061-activate-small_molecule/`):
   `"probability": null, "status": "audit_only", "synthetic": false`. All ten real-data
   cases are built as task `T6` (`src/asof/ingest.py:428`, `program=None, endpoint=None`),
   which `src/asof/scorer.py:118-119` hard-codes to always withhold probability. The
   scored path (`T1`) has only ever run against synthetic demo fixtures — confirmed by
   running the demo, which does score (`probability: 0.4825...`) but is explicitly marked
   `"synthetic": true`.
4. **No CI.** No `.github/`, pre-commit config, tox, or Makefile anywhere. Tests run only
   via manual `python -m unittest discover`. Combined with (1), nothing enforces that
   tests pass before a change is kept.
5. **The project's own feasibility blockers remain unresolved, and engineering continued
   on a different track anyway.** [[AsOf Feasibility Analysis and Peer Survey]] found:
   AACT historical trial-snapshot restoration fails (HTTP 404); UKB-PPP access returns
   HTTP 403; the comparison LLM (Sonnet 4.5) retires November 30, 2026, inside the
   project's own working window; a 24-month post-cutoff outcome horizon cannot finish by
   the stated June 2027 target given both candidate models' training cutoffs; and an
   illustrative power calculation needs roughly 504-1,762 independent cases against a plan
   that assumed about 400. `memory/project-goals.md` (dated 2026-10-11, the most recent
   entry) still lists every one of these as unresolved. The same document explicitly
   recommended resolving these before expanding the agent architecture; the two days of
   work that followed went entirely into framework-correctness engineering instead. That
   engineering was legitimate and well executed, but the project's own top-ranked
   blockers have not moved.

## Verified code-level findings

6. **Latent contract gap in `src/asof/contracts.py:154-166` (a residual of the project's
   own previously-fixed "F01" finding), confirmed end-to-end at runtime.**
   `Case.validate()` checks `program.availability.exclusion(...)` for both task `T1` and
   `T6` (line 154), but the structural checks — phase/endpoint match, `status_at_origin ==
   "active"`, `eligible_since <= origin` — are gated behind `if self.task == "T1":`
   (lines 156-166). Verification: constructing a `T1` case with a deliberately broken
   `Program` (`status_at_origin="withdrawn"`, `eligible_since` 18 months after `origin`)
   correctly raises `ContractError: Program was not active/eligible at origin`; the
   identical broken `Program` on a `T6` case raises nothing. Pushed further: running that
   broken `T6` case through the real `run_workflow()` -> `write_run()` pipeline (exactly
   what `cli.py run` calls) **completes successfully and produces a fully receipted
   dossier with a real SHA-256** — no layer anywhere in admission, workflow, or semantic
   verification catches it. Currently dormant in production because the only real `T6`
   builder (`ingest.py`) always sets `program=None`, and no regression test exercises this
   specific combination (`tests/test_v02_regressions.py:44` only varies
   `availability.record_public_at`, which the line-154 check already covers). Worth
   closing given this exact bug class was found and fixed once before.
7. **`tools/data/Sync-DownloadCatalog.ps1:56` writes to a permanently hardcoded, dated
   output filename** (`data\manifests\public\2026-10-10-acquisition-summary.json`) even
   though line 11 computes a fresh Pacific-time date for the file's own content every run.
   Verified live: executing the script's own date-computation line against the real
   system clock today returns `2026-10-11` — running the script now would overwrite the
   `2026-10-10`-named file with mismatched content. `Measure-SourceInventory.ps1` has the
   same shape (hardcoded dated default output path, unconditional `Set-Content`, no
   clobber guard).
8. **`tools/data/Watch-DownloadBatch.ps1`**'s default `$BatchId`
   (`core-25-09-chembl35-2026-10-10`) does not match the real queue file
   (`core-2026-10-10-queue.json`); line 20 patches around the mismatch at runtime with a
   `.Replace()` instead of fixing the default — an unfinished rename.
9. **`Sync-DownloadCatalog.ps1:45`** updates status text with an exact-string
   `.Replace()` over human-authored prose — silently no-ops with no warning if that
   sentence is ever edited.
10. **`tools/framework/prepare_v02_inputs.py:41,43`** hardcodes the raw-data root and two
    queue filenames as bare constants with no override mechanism at all (the `.ps1`
    scripts at least take parameters for the same paths).
11. **`build_demo_v2.py`** has an undocumented hard dependency on `build_demo.py` having
    already run (reads its output files with no existence check or `try`/`except`) — a
    bare `FileNotFoundError` if run standalone. Also: `build_demo.py`/`build_demo_v2.py`
    have no `argparse` or error handling at all, inconsistent with `run_pilot.py` and
    `probe_framework.py` in the same directory.
12. **`tools/review/probe_framework.py:295`'s pass/fail gate, confirmed by executing the
    exact expression.** The gate is `any(result.get("passed") is False for result in
    results.values())`. The `legacy_verification` probe returns `passed: None` (not
    `False`) when its fixture directory is absent. Running that exact expression with a
    `None` result mixed in returns exit code `0` — the whole probe suite can report clean
    while silently skipping that one check. The fixture exists on this machine today, so
    nothing is currently masked, but the gate itself would not fail loudly if it went
    missing.
13. **Two uncoordinated writers of the same 1.5MB `data/catalog/sources.json`** — a
    PowerShell script and a Python script (`prepare_v02_inputs.py`) both mutate it, in
    different languages, with no locking or single owner.
14. **Run-directory discoverability gap.** The failed, superseded pilot attempt
    (`runs/v02-realdata-20261012T014305Z/`) has no in-directory marker distinguishing it
    from the canonical successful retry (`...T015124Z/`) — only private, gitignored
    manifest files (`data/manifests/private/v02-final-pilot.json`) say which is
    authoritative.
15. **LICENSE copyright line was never filled in.** The Apache-2.0 grant is complete and
    operative, but the attribution appendix is still the literal template placeholder,
    `Copyright [yyyy] [name of copyright owner]`.
16. **`tests/test_v02_hardening.py:49-56` silently no-ops half of one test's assertions,
    confirmed at runtime and genuinely indistinguishable from a full pass.** It gates
    its "v1 verification preserved" check behind `if archived.exists():` where
    `archived = ROOT / "runs/framework-v0.1-verified"` — a directory that is gitignored
    and not reproducible by any build step. Running this test with `Path.exists` patched
    to simulate that directory's absence (no real files touched) produces a plain `ok`
    with zero skip records, identical output to a full pass.

### Correction from the verification pass

An earlier draft of this review also flagged `README.md`'s quick-start (install without
the `ingest` extra, then immediately run the full suite) as causing a **silent** skip of
the pyarrow-gated tests. Running the suite exactly that way (with `pyarrow` made
unavailable) showed this was **overstated**: with `-v`, as the README specifies, each
skipped test prints an explicit, actionable message
(`skipped 'install the ingest extra for ... tests'`), and even without `-v` the summary
line reads `OK (skipped=22)`. This is friction for a reader skimming for the word "OK,"
not a silent failure, and the finding above has been corrected accordingly rather than
left to stand.

## Design strengths (for calibration)

Multi-layer temporal-leakage defense checked at admission time, at claim time, and again
via independent semantic-replay verification; hash-chained, fsynced append-only journals;
strict JSON decoding that rejects duplicate keys, unknown fields, non-finite numbers, and
bool/int coercion; deep immutability on every nested structure; path-traversal-safe file
access (`serde.safe_child`); explicit prompt-injection framing in specialist requests;
budget preflight checks that run before any backend dispatch so rejections cost nothing;
and `run_pilot.py`'s `SourceAudit`, which independently re-derives claims from the
original raw Parquet bytes rather than trusting the pipeline's own output. Documentation
(`docs/FRAMEWORK.md`, `docs/V02_MIGRATION.md`, `README.md`) is unusually accurate against
the current code. The team runs its own adversarial self-reviews and is candid in-product
about its own limits.

## Recommended remediation, if pursued

**Quick, high-leverage, low-risk:** `git init` plus a first commit; fill in the LICENSE
copyright line; fix the two stale-hardcoded-filename bugs (findings 7); fix
`probe_framework.py`'s `None`-vs-`False` pass/fail gate (finding 12); add
`#Requires -Version 7` to the PS7-dependent scripts.

**Moderate effort, real risk reduction:** close the T6+Program contract gap in
`contracts.py` (finding 6) and add the missing regression test; stand up minimal CI
(run the suite with the `ingest` extra installed, on every push); give `sources.json` a
single owner instead of two uncoordinated writers; add a `SUPERSEDED`/`FAILED` marker
convention for abandoned `runs/`/`data/derived/` attempts.

**Larger, strategic:** make an explicit, written decision on the unresolved Oct-9
blockers (finding 5) before further framework expansion, or document why proceeding
without them is acceptable; scope and begin the real LLM-backed specialist adapter;
close out [[Project Audit and v0.2 Completion]]'s dangling final section with the pilot
results that already exist on disk.
