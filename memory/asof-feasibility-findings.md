---
name: asof-feasibility-findings
description: Verified and unresolved AsOf feasibility findings from October 9, 2026
metadata:
  type: reference
updated: 2026-10-09
---

# AsOf feasibility findings

Linked work: [[AsOf Feasibility Analysis and Peer Survey]], [[project-goals]], [[research-log-2026-10-09]]. Source probes and counts are persisted in `planning/review-assets/access-audit.json`.

- Virtual Biotech pinned commit resolved to `71f9da68c95c5ee0ef4c1d9b8f45f10693de022d`. Six files were downloaded and hashed; no agent was executed and its entire tool inventory was not recounted.
- Its evidence-year filters allow null dates; its trial tools use live ClinicalTrials.gov; its registry grants Bash and selected web access. A masked MCP alone cannot enforce historical access. [Association source](https://github.com/harrisongzhang/TheVirtualBiotech/blob/71f9da6/src/mcp_servers/association_mcp/tools.py), [Registry](https://github.com/harrisongzhang/TheVirtualBiotech/blob/71f9da6/src/agents/registry.py).
- Released labels have 56,707 unique trials: endpoint positive 19,623; negative 9,477; unknown 7,492; blank 20,115. Progression EVER 3,026; NEVER 8,386; blank 45,295. Safety stop categories occur in 700 rows. These are raw trial counts, not eligible dated target/program cases. [Pinned label source](https://github.com/harrisongzhang/TheVirtualBiotech/blob/71f9da6/datasets/clinical_trials/clinical_trial_labels_reconciled.csv).
- On the review date, official specifications list July 2025 training cutoffs for Sonnet 4.5 and Haiku 4.5. The reliable-knowledge dates are earlier. Sonnet's official localized specifications list retirement November 30, 2026. Reverify this mutable lifecycle before experiments. [Sonnet](https://platform.claude.com/docs/es/models/sonnet-4-5/overview), [Haiku](https://platform.claude.com/docs/en/models/haiku-4-5/overview).
- Open Targets and ChEMBL archive directories, eQTL Catalogue access/license pages, and a Europe PMC metadata call returned HTTP 200. The tested legacy AACT listing returned 404; current AACT documents historical/account access. No archive was restored.
- UKB-PPP registry designates controlled access. A path-style anonymous bucket listing returned 403; that does not prove individual-object permissions. Per-protein tar processing is not proof of indexed cis-window access. [Registry](https://registry.opendata.aws/ukbppp/).
- MRAgent threshold relaxation was independently confirmed in `agent_tool.py` at `0f661b85197306418cf628b7808ff34f79bb87ac`. OriGene recency/count/source ranking was confirmed at `bc984db2cb604e7acde520af5b5940e5ec8ae0af`.
- R2E's temporal protections should be checked by evidence/model branch. BiomniBench and TxBench-PP narrow claims that process verification and drug-discovery decision benchmarks are absent. See the report and peer inventory for source limits.
- Illustrative AUC power calculations require approximately 504–1,762 independent cases under the stated assumptions, before clustering. This is not empirical cohort power. See `capacity-planning.json`.

Core research distinction: clinical-development progression, biological target validity, factual citation support, method correctness and explanation faithfulness are different outcomes. A supervised scorer should be controlled separately from agent evidence generation.
