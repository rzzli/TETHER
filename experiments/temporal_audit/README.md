# Temporal evidence and registry audit

Reproduce the aggregate measurements behind TETHER's descriptive comparison of Open Targets releases and selected AACT snapshots. The archived evidence products, development trail selection and registry comparisons use separate units. The study did not release a forecasting benchmark. [Results and limits](../../docs/RESULTS.md)

## Recompute the tables

Use Python 3.11+ from a clean source export. This command needs no installed TETHER distribution, Git history, source data or network.

```text
python -I -B experiments/temporal_audit/replay.py --output temporal-tables
```

The output directory must be fresh. `archive.csv` contains twelve release/source/date-field cells and their denominators. `endpoint.csv` contains four finite-source states by horizon and the extreme-assignment fractions for unresolved units. `registry.csv` distinguishes requested trial IDs from repeated row-to-trial links. `flow.csv` holds the denominators for the cohort figure. `summary.json` binds all four CSVs to the released aggregate and retained report digests. These checks establish arithmetic reproducibility from supplied counts.

To regenerate all tables and both figures in one command, use an environment with matplotlib (tested 3.6.2). The figures and their manifest appear under `temporal-study/figures/`.

```text
python -I -B experiments/temporal_audit/replay.py --output temporal-study --figures
```

The source-export suite passed on Windows and Ubuntu with Python 3.11. The figure build and four-column source replay were verified on Windows. The exact public-roster replay took 13.469 seconds using 129,179,976 bytes of local compressed input. The replay emits aggregate counts and uses separate working memory for decoded Arrow batches and pair sets.

## Replay the nine Open Targets partitions

The [roster](open-targets-roster.json) contains 1,500 provider-relative file names, lengths and SHA-256 digests. Obtain the exact files from the official release archive and arrange them under a local root using the listed paths. The three source partitions are gene burden, UniProt literature and Expression Atlas for 22.11, 24.09 and 25.09. The archived layout uses `output/etl/parquet/evidence/`; 25.09 uses `output/evidence/`. The compressed originals total 129,179,976 bytes. Allow separate working memory for Arrow and pair sets. Source terms and attribution apply to the originals. [Official archive](https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/) · [Open Targets release notes](https://platform-docs.opentargets.org/release-notes) · [Data terms](https://platform-docs.opentargets.org/licence)

With PyArrow 21.0.0 from TETHER's optional `ingest` extra, supply the directory containing the three release folders and a new output file outside it.

```text
python -I -B experiments/temporal_audit/replay_open_targets.py --manifest experiments/temporal_audit/open-targets-roster.json --manifest-sha256 efe9b7eae38f62164b0577e11d4bcc9dd49c48b771eb2c8f8d85f2ccb19dc2c8 --root LOCAL_OT_ROOT --output temporal-source-check.json
```

The replay hashes each source and reads only `targetId`, `diseaseId`, `evidenceDate` and `publicationDate`. Check the 12 filtered cells against `archive.csv`. The report also includes all nine full comparisons. Compare the counts and pair sets' cardinalities. Execution time and machine-specific manifest and code hashes can vary. The exact public roster reproduced 815,991 rows and all 21 pair comparisons. Publisher completeness outside the roster and the causes of release differences remain unresolved.

## Study protocol

For each source, compare complete literal target and disease IDs without remapping. Filter the 25.09 records separately on `evidenceDate` and `publicationDate`. The exclusive calendar cutoffs are November 25, 2022 for release 22.11 and September 19, 2024 for release 24.09. A row is selected only when its full reported calendar interval precedes the cutoff. The 12 cells retain their date disposition counts and the six `evidenceDate` cells form the primary descriptive comparison.

The endpoint frame uses the earliest resolvable exact phase-2 entry per target–disease pair in 2016–2019. The published counts cover the 6,550 development pairs, with separate 36- and 60-month windows measured from each entry. The dispositions distinguish prior higher-phase origin exclusions, a recorded phase-3 candidate, no qualifying record in the finite source and unresolved cases. Literal drug–target–disease triples use separately reconstructed origins in the development projection. The 99 exploratory reserve pairs supply no outcome counts. The selected registry audit retains all 100 trails, including 18 withheld from registry expansion by the bridge rule. Joint registry start agreement requires a coherent reported actual start, interventional type, exact phase and equal or overlapping start intervals. Exact product and condition names are counted separately.

## Registry scope

The public registry counts cover January 1, 2023, January 1, 2025 and April 1, 2026. The exact 226-ID/299-link selection and raw snapshots remain outside this release. Exact source reproduction requires provider access to the versioned archives and the authorized evaluator-only selection, mappings and query configuration. In the retained run, six tables were restored at each date and the 54 indexed query batches reproduced their result bytes. The public command reproduces reported registry arithmetic. It cannot independently reconstruct which trails were selected or qualify clinical labels. [AACT access](https://aact.ctti-clinicaltrials.org/landing)

## Reading the numbers

- Set Jaccard is shared pairs divided by the union within one source and release cell. The primary and sensitivity fields share inputs. The comparison concerns stored keys and reported dates.
- The endpoint ranges assign all unresolved eligible units to either extreme. They are finite-source classification ranges. Registry and source counts do not establish clinical incidence.
- ID and link rows use different denominators. The joint-start and exact-name predicates are separate. Neither supplies a qualified programme transition by itself.
- Clinical labels, historical actor inputs and independent test eligibility remain unqualified. See the [portable bundle guide](../../docs/PORTABLE-BUNDLE.md) for evidence and run verification on a separate technical example.
