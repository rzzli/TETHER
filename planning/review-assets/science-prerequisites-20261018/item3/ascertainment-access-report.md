# Ascertainment source access and coverage plan

Checked 2026-10-18, evaluator-only. Candidate origin: 2025-01-01 00:00 UTC; occurrence interval: (origin, 2026-01-01 00:00 UTC]; proposed ascertainment boundary: 2026-04-01 00:00 UTC. The 90 calendar days are a proposed reporting allowance, not evidence of complete reporting or mature follow-up. This report does not amend the protocol or label any program.

## Finding

**The reporting-lag source remains unavailable for qualification.** The local raw archive inventory contains six ZIPs, dated by existing qualified metadata to 2023-01-01, 2023-07-02, 2024-01-01, 2024-07-01, 2025-01-01 and 2026-01-01. There is no April 2026 archive. The unlabeled top-level `t28miw7docut6vcrht1ff6ci630i.zip` is the previously qualified January 2023 archive, not a new follow-up source. This run inspected ZIP central-directory metadata only and reused clearly labeled prior hash verification evidence.

The supplied January 2026 ZIP has the previously verified SHA-256 `7fb923dacecae1dfec864c3e21fbed669add8a64b6bd1664ce973c24a514035c`, size 2,344,676,979 bytes, full ZIP-member CRC reads and dump TOC qualification. That prior technical check did not restore the database. January 2026 cannot cover disclosures during January–March 2026. The parent task separately owns any subsequent restoration after sealing the origin cohort.

## Official access checks

| Route | Observed response | Consequence |
|---|---|---|
| [AACT landing](https://aact.ctti-clinicaltrials.org/landing) | 200; says account creation enables full snapshot downloads | Official historical-download capability is documented; specific April dates remain unlisted publicly |
| [AACT snapshots](https://aact.ctti-clinicaltrials.org/snapshots) | 302 to `/session/new` | Unauthenticated archive listing is unavailable |
| [AACT API snapshots](https://aact.ctti-clinicaltrials.org/api/v1/snapshots) | 401, `invalid_api_key`: invalid or missing API key | Metadata listing is inaccessible within authorized unauthenticated scope; API schema and filtering behavior unqualified |
| [Legacy 2026 PostgreSQL listing](https://aact.ctti-clinicaltrials.org/downloads/snapshots?type=pgdump&year=2026) | 404 | No usable public listing at this route |
| [ClinicalTrials.gov API documentation](https://clinicaltrials.gov/data-api/api) and [about API](https://clinicaltrials.gov/data-api/about-api) | 200 client-rendered shells in direct retrieval | Reachable, but retained shells do not establish a supported historical-version API |
| [ClinicalTrials.gov API version](https://clinicaltrials.gov/api/v2/version) | 200; current API metadata retained | Describes current refresh, not an April 2026 historical view |
| `https://clinicaltrials.gov/api/v2/openapi.json` | 404 | This probed specification path provides no historical-version contract |

Requests used no credentials, login, registration, account changes or access bypass. No archive was downloaded, no database restored, no clinical table queried, and no endpoint join performed by this task. Original worker and transport receipts were untouched. Retained response bodies omit public form CSRF values and receipts omit cookies; no signed download URL was obtained or reported.

## Exact missing input and destination

The required source is the **AACT PostgreSQL database snapshot dated 2026-04-01**, with its publisher's displayed date, exact displayed filename and download metadata retained. **The exact publisher filename is unknown** because both official listings require account access. No filename is invented here, and this report cannot verify that the exact date exists. A file named by convention alone would not establish identity.

The accepted user delivery directory, matching the parent task's request and the prior user-download layout, is:

`E:\projects_data\drug_target_agents_data\raw\aact_snapshots\apr2026zip\`

The user-provided archive can remain at that original path, with its receipt bound there. No file needs to be moved or renamed. The following new project-qualified-history destination is only an optional post-verification organization proposal:

`E:\projects_data\drug_target_agents_data\raw\project-qualified-history-20261018\aact_snapshots\2026-04-01\`

Preserve the original downloaded filename, including an opaque storage filename if the site uses one. Retain the visible snapshot/date selection or a non-secret receipt showing the publisher label; no password or token is needed. If April 1 is unavailable, retain the list of available dates from April 1 through April 8, 2026 and identify the earliest available date in that **proposed seven-day access-search bound**. No bounded-near-after archive has been observed or selected. This bound is a file-search proposal, not an extension to the scientific ascertainment boundary.

After lawful local receipt, a new evaluator-only receipt must record retrieval clock, archive bytes and SHA-256; complete ZIP CRC/member reads; safe member names; dump SHA-256 and TOC creation metadata; publisher version label and timing precision. A dump created after April 1 00:00 UTC, or a day-only label with unknown timezone, does not automatically represent the exact proposed cutoff. A near-after source can support strict-cutoff reconstruction only with qualified record-version publication timestamps; otherwise it requires an explicit protocol decision or a separately labeled sensitivity analysis. It cannot silently add post-cutoff disclosures.

## Timing distinctions

The filename's version date, dump creation timestamp, ZIP member timestamps, source first-public availability and local retrieval time are separate facts. ZIP/DMP clocks without a timezone do not become UTC merely because the analytic boundaries use UTC. HTTP `Date` proves retrieval-response timing, not the historical snapshot's first publication. File modification time indicates local possession, not source publication. The January 2026 archive's exact first-public availability remains unverified.

Event occurrence must fall wholly within the frozen occurrence interval. Reporting allowance admits eligible disclosures through the separately frozen ascertainment boundary; it does not admit events after the occurrence horizon. Month/year-only event dates need intervals and cannot be resolved by midpoint imputation. Public registry submission dates and quality-control processing are not automatically public version-post dates. Later retrieval can preserve a qualified historical public version; current content alone cannot establish its contents as of April 2026.

## Planned coverage after the origin seal

The origin manifest and its SHA-256 must be sealed before endpoint tables, candidate outcome pages or candidate histories are inspected. The following is a coverage specification with **all candidate coverage counts unmeasured**, not a performed search.

| Named endpoint | Planned source coverage | Conditions before qualification |
|---|---|---|
| `registry_next_phase_enrollment_v1` | January 2026 occurrence-horizon snapshot plus April 2026 ascertainment snapshot; all frozen NCT/program aliases and eligible next-phase scope; historical registry versions for corrections and boundary disputes | Actual start/enrollment date, eligible numerical phase, comparable population/regimen and program linkage; version publication at/before cutoff; complete defined registry-search audit |
| `experimental_arm_first_dosing_v1` | Frozen NCT/arm scope plus dated official sponsor or study reports documenting first experimental-arm dosing; registry histories provide supporting chronology | Experimental-arm dosing explicitly documented, source timing and occurrence interval qualified; study enrollment/start alone insufficient |
| `clinical_efficacy_success_v1` | Qualified registry results versions, protocol/SAP versions and dated public primary-analysis reports in the frozen efficacy scope | Prespecified objective, population, analysis and decision/multiplicity rule; eligible final result and source availability; registry status/result posting alone insufficient |

For each program and endpoint, retain source/alias searches, dates searched, version identifiers, public-posting evidence, source hashes and locators, inaccessible or absent sources, linkage/comparability judgments, event-date bounds and the latest qualified observation. Report denominators and numbers with accessible histories, complete defined registry searches, unknown precision, missing scope/linkage, and unavailable sources. Missing counts remain null until execution; a zero count would falsely imply a completed search.

Lag evidence should record occurrence-to-first-eligible-disclosure intervals, including bounded or unknown delays and disclosures after the proposed allowance where discovered under a separately declared search. Observed delays are conditional on discoverable reported events and cannot establish the lag distribution of unreported events. Qualifying a snapshot's date and integrity only qualifies source access. It does not certify 90 days as universally sufficient or global ascertainment completeness.

An unavailable or unresolved record remains unresolved. A no-qualifying-registry-record state requires a frozen, completed, qualified registry search and supports only that operational endpoint. It is never clinical efficacy failure. A clinical-efficacy negative requires an eligible analysis explicitly failing its prespecified decision rule. Censoring and competing events require their own source-supported rules.

## ClinicalTrials.gov alternative

Official indexed [record-history UI](https://clinicaltrials.gov/study/NCT02812264?tab=history) metadata demonstrates that users can select dated versions and compare versions. Only generic UI capability is relied on here; that illustrative behavioral-study page is not a candidate outcome source. The displayed history ordering is by **submitted date**, which alone cannot establish public availability at the cutoff. The present access check did not download candidate records, candidate history content or study results.

Public per-record histories are therefore a possible evaluator-side route after the origin seal, requiring exact version/posting evidence, retained page content and reproducible coverage across every frozen ID. A supported stable historical-version API, bulk historical completeness, per-version publication-clock precision and download behavior have **not** been qualified. Undocumented internal routes, current API queries or today's current bulk download must not be treated as historical reconstruction. This alternative remains partial/unqualified until those access and coverage requirements pass.

## Retained evidence

Actual metadata is under `data/derived/science-prerequisites-20261018/ascertainment-access-20261018T173212Z/`: HTTP receipts and bodies, local ZIP central-directory inventory, hash-linked prior evidence and explicit zero-activity scope. `ascertainment-access-report.json` is the machine-readable disposition. This task's source-access audit is complete; the reporting-lag source and candidate ascertainment coverage remain unqualified pending the missing input and post-seal work.
