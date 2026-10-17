---
title: Long Run Data Preflight
date: 2026-10-16
tags: [planning, data, feasibility]
---

# Long-run data preflight

Preflight checked October 16, 2026 Pacific / October 17 UTC. This is a preparation plan, not a started twelve-hour execution or a promise of continuous availability. The existing January 2023 and January 2025 restorations support substantial next-stage work without another manual download.

## Inputs already available

| Input | Verified scope and remaining limit |
| --- | --- |
| January 1, 2023 AACT | Restored and sealed; 437,548 studies. Nine stored-record relationship exceptions retained. Exact first-public availability remains unverified. |
| January 1, 2025 AACT | Restored and sealed; 520,688 studies. All 24 frozen trial representatives compared with origin. Both database servers cleanly stopped. |
| Clinical pilot | Twelve provisional candidates, five exclusions and seven requiring separation/review. No candidate has registry results posted by the endpoint; external publications still need review. Outcomes, event dates and censoring remain unadjudicated. |
| Regional genetics | IL6R/RA contemporary technical pilot: 1,690 QC-passing SNPs and 503 EUR LD samples. Metadata checksum discrepancy, LD documentation inconsistency, overlap and proxy-LD limitations remain explicit. No MR or colocalization result. |
| Contemporary T6 | Ten source-verified dossiers, retained source audit and AI-assisted development review. No independent biological validation or numerical prediction. |

See [[AACT January 2025 Follow-up]], [[Clinical and Genetics Feasibility Pilot]] and [[Context Revision Completion]]. Existing tests were last reported passing at 130; this documentation-only preflight did not rerun them.

The `raw/aact_snapshots/jan2026zip/` directory exists but was empty at inspection, including hidden/nested contents. No January 2026 archive is assumed available. A later snapshot would support a separately defined extended endpoint, not replacement of the frozen January 2025 state.

## Manual preparations in priority order

AACT currently requires an account for full snapshot downloads. Its official site describes historical versions, but availability of the individual dates below has not been confirmed inside the user's account: [AACT access information](https://aact.ctti-clinicaltrials.org/landing).

| Priority | Requested input | Why / fallback |
| --- | --- | --- |
| Recommended minimum | January 1, 2024 versioned AACT PostgreSQL ZIP | Adds an intermediate observation to the 2023–2025 window. Public record histories/publications can be investigated without it; no stable historical-version API is assumed. |
| Useful preparation | July 1, 2023 and July 1, 2024 versioned ZIPs | Six-month observation intervals improve timing bounds. Not required to start the outcome protocol or literature audit. |
| Later, conditional | Additional monthly snapshots around specific unresolved transitions | Request only after the actual ambiguity is identified. Do not download every month preemptively. |
| Optional later endpoint | January 1, 2026 ZIP | Could examine outcome maturation after 2025 under a separate protocol. Not necessary for the current two-year audit. |

Keep the original ZIPs in separate folders beneath `E:\projects_data\drug_target_agents_data\raw\aact_snapshots\`, preferably `2023-07-01`, `2024-01-01`, and `2024-07-01`. Retain the listing's snapshot date/original filename when possible; do not share credentials, tokens or signed download links. If a requested date is unavailable, record that fact; do not silently substitute another release.

These observations only bracket registry changes. They do not by themselves establish an exact first-public transition date, efficacy, biological failure or independent program outcome. Publication and event dates require separate adjudication.

Three additional ZIPs are provisionally budgeted at 6–10 GB compressed and roughly 70–85 GB including three full restorations and working overhead, extrapolating from the two measured restores. These are planning estimates, not verified sizes of the requested releases. Measured free space at preflight was approximately 1.62 TiB on D: and 1.66 TiB on E:, sufficient for this scoped work, not proof that the full catalog fits. Keep the external E: drive connected and powered during execution.

## Gaps that do not require the user now

| Gap | Independent next action / boundary |
| --- | --- |
| Open Targets incomplete literature partition | All 65 frozen missing paths belong to the public 25.09 Europe PMC partition. Sixteen now exist on disk and 49 are absent. Presence is not receipt/hash verification. Inspect existing receipts and acquire/validate exact-release public files as needed under prior public-download authorization; leave the active worker untouched. Any updated manifest/build must be a new version; preserve the frozen build's 65 missing-input record. |
| Dated clinical outcome evidence | Search primary publications, open manuscripts and dated sponsor disclosures for the frozen 24 trials. Record exact NCT/program/arm linkage, event date, first-public date, endpoint, unresolved results and sources. Request a specific lawful paper copy only if open alternatives fail. |
| Historical evidence for a future T1 benchmark | Inventory and verify pre-origin Open Targets, ChEMBL and identifier/ontology releases. Contemporary local releases cannot silently fill historical gaps. Public archives can be checked without user accounts; actual compatibility/availability may still fail. |
| Genetics source exceptions | Investigate existing checksum/metadata discrepancies, assay and allele definitions, ancestry, cohort overlap and LD compatibility. Preserve original bytes and unresolved exceptions. Technical QC does not authorize causal interpretation. |
| Additional public genetics | Scope complete regional inputs only after fixing target, molecular phenotype, outcome and ancestry. Check product-level access and complete regional coverage before acquisition. The current eQTL pilot is not a protein or pharmacologic-inhibition surrogate. |

UKB-PPP is a possible later account-mediated dependency: the [AWS registry](https://registry.opendata.aws/ukbppp/) lists its summary-statistics bucket as controlled access. No new account or controlled individual-level data is needed for the immediate public-data route. [deCODE's official summary-data page](https://www.decode.com/summarydata/) exposes public products, some extremely large; verify the chosen product and subset feasibility rather than treating the entire provider as inaccessible. Do not request full proteome collections, paid GTEx transfer, MedDRA licensing or restricted optional sources for this work package.

Live model evaluation would require a separate model/provider/spending decision and secure local credential setup. It is outside the current $0-provider route. AI-assisted judgments remain development review rather than independently adjudicated gold; independent scientific validation remains a later gate.

## Proposed execution order for the next long session

1. Freeze a versioned program/arm-level outcome, timing and censoring protocol before adding labels. Keep origin rules and January 2025 endpoint fixed; handle reporting lag, stale UNKNOWN states, nonbiological stops and competing outcomes explicitly.
2. Review dated public primary evidence for the existing 24 records; resolve the seven complex mappings where possible and retain uncertain cases. Do not replace cases based on favorable observed outcomes. Save source receipts and structured evidence separately from agent-visible inputs.
3. Restore any supplied intermediate snapshots into separate directories, audit them and compare only the frozen cohort. If none arrive, continue public-source chronology and report interval uncertainty.
4. Assess eligible independent program/event counts and follow-up completeness. Report feasibility or a justified no-go; do not manufacture labels or a power estimate from 24 trial representatives.
5. Resolve or retain regional-genetics QC exceptions; scope the next public regional replication. Do not start MR, scorer training or historical inference merely to fill execution time.
6. Verify public literature inputs and historical archive access if time remains. Add regression tests only for substantive new code, run required checks, seal new artifacts and update the current status.

This queue has useful independent work even without new user files. Completion is evidence-based, not a requirement to consume twelve hours. If one branch needs user-only access, record the blocker and proceed on another authorized branch. Checkpoint each completed step so interruption is recoverable without repeating potentially billed or destructive actions.

## Execution limits

[Official long-running-work guidance](https://learn.chatgpt.com/docs/long-running-work) describes goals and checkpointed work. A goal can define completion and boundaries, but uninterrupted twelve-hour execution is not guaranteed; session/usage limits, connectivity, app availability, host sleep and the external drive can interrupt local work. Keep the workspace available and resume from the saved status if interrupted.

No goal or recurring monitor was started by this preflight. No bulk download, database restart, account registration, paid query or live model call occurred. The existing downloader and stopped periodic monitoring remain untouched. Public-data work retains the existing $0 provider-spending default and leaves outcome probabilities null.
