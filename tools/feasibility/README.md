# Data-feasibility utilities

These modules inspect explicit clinical or genetic sources and retain technical
feasibility records. Their outputs are evaluator-side development artifacts,
not agent-visible evidence, scientific gold labels or clinical probabilities.
Many modules implement fixed study-specific contracts rather than generic APIs.

| Area | Entry points |
|---|---|
| Registry extraction and cohorts | [registry_extract.py](registry_extract.py), [registry_cohort.py](registry_cohort.py), [registry_audit.py](registry_audit.py) |
| Scope, dependency structure and power | [registry_scope.py](registry_scope.py), [registry_power.py](registry_power.py) |
| Chronology and program relations | [chronology_policy.py](chronology_policy.py), [advancement_rules.py](advancement_rules.py), [program_outcomes.py](program_outcomes.py) |
| Snapshot comparisons and timelines | [compare_clinical_snapshots.py](compare_clinical_snapshots.py), [build_clinical_timeline.py](build_clinical_timeline.py) |
| Source discovery | [harvest_trial_publications.py](harvest_trial_publications.py), [retain_public_sources.py](retain_public_sources.py) |
| Regional genetics | [fetch_genetics_region.py](fetch_genetics_region.py), [qc_genetics_region.py](qc_genetics_region.py) |
| Restore and source checks | [restore_intermediate_aact.py](restore_intermediate_aact.py), [verify_intermediate_aact.py](verify_intermediate_aact.py), [verify_pilots.py](verify_pilots.py) |

Read each module's `--help`, input schema and tests before using it. Required
protocols, database restores, indexed regional data and credentials are not
bundled. Some helpers require optional NumPy, pysam or ingestion dependencies.
Provide credentials through the tool's supported protected mechanism, never
through a public manifest or printed command.

Use a fresh output location. An interrupted extraction or import must be inspected
before a separate recovery decision; an existing destination is not permission
to resume. Database helpers may start and stop only servers whose ownership they
establish. Inspect sealed SQLite outputs with a read-only immutable URI or work
on a separate copy, so reader sidecars cannot alter the preserved artifact tree.

Preserve source versions, original dates and eligibility holds. Directory HTTP
success, parsing or a matching local hash does not establish historical public
availability. Registry phase/status changes do not supply adjudicated program
success, failure or censoring. Genetic QC does not establish a causal effect or
substitute for MR/colocalization with eligible complete inputs.

Historical fixed-cohort tools require their matching original code and protocol;
see [compatibility guidance](../../docs/ARCHIVE.md). The public repository supplies
code and tests, not a completed dataset or qualified clinical evaluation.
