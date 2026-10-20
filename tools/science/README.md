# Scientific qualification utilities

These evaluator-side tools preserve source identity and distinguish input readiness
from qualified scientific conclusions. They use the Python standard library and the
local AsOf package. The ingestion extra is not required for their fixture tests.
Use fresh output directories; failed or completed outputs are never overwritten.

`ascertainment_inputs` checks a user-supplied AACT ZIP before restoration. It bounds
archive expansion, rejects unsafe member names, hashes the original and each member,
reads every CRC, checks the exact PostgreSQL dump date with `pg_restore --list`, and
archives the executed utility. For example, from `D:\Projects\drug_target_agents`:

```powershell
.venv/Scripts/python.exe -m tools.science.ascertainment_inputs `
  --archive E:/path/to/supplied.zip --output E:/path/to/new-qualification `
  --pg-restore E:/path/to/pg_restore.exe --requested-date 2026-04-01
```

The real April archive is already qualified. This example is not an instruction to
repeat its acquisition or restoration. Ancillary files are integrity-checked only;
an empty schema image or unreadable HTML does not become qualified documentation.

`endpoint_restore.restore(...)` reserves a technical restore, checks the sealed
origin ancestry and exact route decision, and dispatches the existing local restorer
once. April additionally requires a pinned archive qualification and the unchanged
April1 midnight-UTC ascertainment cutoff. The only cohort query is literal `[]` SQL.
It does not activate endpoint searches, labels, model calls or clinical evaluation.

`restore_verification` independently verifies a **completed** technical restore:

```powershell
.venv/Scripts/python.exe -m tools.science.restore_verification `
  --restore-root E:/path/to/completed-restore --output E:/path/to/new-verification `
  --origin-path D:/path/to/frozen-origin.json --decision-path D:/path/to/decision.json `
  --requested-date 2026-04-01 --owned-port 55438 `
  --expected-report-sha256 ACTUAL_REPORT_SHA256
```

It checks both journals, complete output inventory, source/member/qualification
proofs, origin ancestors, measured byte counts and source-TOC constraint/index
coverage. Exact LF and CRLF forms of the empty query are accepted; raw copies and
hashes must agree. The verifier only probes the specified loopback port and reads
files. It never queries, starts or stops PostgreSQL.

`ascertainment_policy.version_eligibility(...)` provides a declared conservative
civil-date reconstruction. It assumes an unspecified conventional UTC offset in
[-12,+14] hours, retaining the interval `[D00UTC-14h,(D+1)00UTC+12h)`. A source DATE
is not a verified timezone or original-version timestamp. March31/April1 postings
remain held at the April1 midnight cutoff; initial registration cannot backdate
later content. A held version does not remove an origin member or create a negative.

`origin_review` freezes source-only selection criteria before scanning the sealed
origin universe. The current twelve-trial pack is a deterministic purposive subset,
not an independent sample-size or performance claim. It preserves all original
qualification holds and contains no follow-up labels:

An exact alias is unique only within the selected resource. It does not certify a
biological formulation, and resource target annotations remain candidates rather
than verified therapeutic targets. A source-operational search candidate is not a
qualified at-risk program. Review these distinctions against the original rows.

```powershell
.venv/Scripts/python.exe -m tools.science.origin_review `
  --origin-seal D:/path/to/origin-freeze.json --origin-sha256 ACTUAL_ORIGIN_SHA256 `
  --output D:/path/to/new-origin-review-pack
```

The original seven-stage protocol, amendments and current execution status are under
`planning/` and `TODO.md`. Passing a utility, receiving a source or agreeing across
agent reviewers never independently validates a clinical conclusion.

`outcome_inputs` builds deterministic, explicit evaluator SQL and validates its
outputs. It retains all requested-member missingness, checks child links, preserves
original date precision and separates raw quarantined versions from eligible views.
The sixteen-table metadata projection contains planned outcomes and document links;
it does not contain reported result tables. Exact drug-name/secondary-name discovery
has no outcome or phase filter. Matches are leads, and candidate caps fail explicitly.

`outcome_extract` accepts a byte-pinned, previously generated plan through
`--plan`, `--expected-sha256` and a fresh `--output`. The plan must bind the actual
twelve-member origin pilot, frozen aliases/policy/cap amendment, approved restored
cluster, mandatory source proofs and executing helper code. SQL is regenerated and
compared before dispatch. This is a project-scoped evaluator tool, not a general
SQL runner. It checks two identical reads, typed rows and temporal dispositions;
uses an exclusive source lease and a unique PostgreSQL-created ownership PID file;
and records failures without automatically retrying. It refuses to stop a server
whose startup ownership cannot be established. Source-reading completion does not
establish clinical linkage, outcome truth or scientific validation.

`genetics_qualification.review_method_plan` checks declared method inputs without
running MR/colocalization or admitting a feature. ABF beta/variance, P-value and
SuSiE routes have different input needs. Historical ancestors require identity,
SHA256, permitted predictor/reference role and an availability bound. A passing
declaration is not payload verification or independent biological validation.
