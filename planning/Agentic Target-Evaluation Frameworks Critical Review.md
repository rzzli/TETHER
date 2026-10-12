# Agentic Target-Evaluation Frameworks: Critical Review

Oct 8, 2026 · @R

## Bottom line

None of the eight frameworks has shown that it ranks targets better than a genetics-plus-tractability baseline on held-out clinical outcomes. The space has strong plumbing (MCP data layers, provenance, statement verification) and weak evaluation of the actual decision.

**Three gaps matter most.**

1. **No leakage-controlled benchmark for target decisions.** Benchmarks are factual QA (TRQA, GenomeArena, Karenina), generated from the same databases the agent queries (GenomeArena), or case studies (Virtual Biotech, OriGene). Only R2E ran a time-split clinical-outcome test, and it reached AUROC 0.633.
2. **Causal genetics is thin or done unsafely.** Among the agents, only Virtual Biotech has dedicated credible-set, locus-to-gene and QTL-colocalization tools, all lookups of Open Targets precomputes; the Open Targets MCP exposes the same data only as raw GraphQL. MRAgent runs phenotype-level Mendelian randomization and silently relaxes instrument thresholds to 5e-5. Nobody runs cis-pQTL MR or reasons about direction of effect (loss vs gain of function).
3. **Outputs are narratives, not calibrated decisions.** No framework emits a probability of success with uncertainty and explicit evidence weights. OriGene's candidate ranking is driven by how often a gene appears in tool output, a popularity bias that R2E measured and corrected.

**Highest-leverage opportunity:** an open, time-sliced target-decision benchmark. Freeze every data source at an as-of date, score (target, indication) pairs against later trial outcomes, and require calibrated scores plus faithful evidence attribution. The labels already exist: Virtual Biotech released 56,707 source-tracked trial outcome rows, and R2E released its clinical-outcome set. Pair it with an agent that writes a typed evidence ledger, which a transparent model turns into a score.

## Scope and method

Each framework was judged by reading its paper and its code, and by profiling its released data where any exists. Claims about behavior come from the source code, not the README.

- **Code read:** Virtual Biotech, OriGene and OrigeneMCP, Alvessa, Open Targets Platform MCP, MRAgent, DeepRare and DrugAgent were cloned and inspected. R2E's code and weights are proprietary; only its evaluation datasets are public.
- **Data profiled:** all three TRQA files (172 + 1,108 + 641 questions), the TRQA scorer, Virtual Biotech's trial-label release, DrugAgent's kinase and Tox21 ground truth plus its knowledge graph, and Alvessa's benchmark generators.
- **Not done:** no agent was run end to end. Most need paid API keys plus 45 GB to 100 GB+ of local databases.

**Rubric.** Three questions per framework, after the Function–Evidence–Validation split proposed by Pham and Hy (2026):

1. **Function:** what does it actually do for target evaluation (retrieve, analyze, rank, decide)?
2. **Evidence:** which layers does it reach (causal genetics, functional genomics, cell-type expression, safety, tractability, clinical precedent)?
3. **Validation:** how strong is the proof, from V0 (illustrative output) through V3 (evaluated against a benchmark or experts) to V4 (prospective test)? Ratings in this doc are my own assessment.

Reuse terms (license, data footprint, model lock-in) are noted because they decide what can be built on.

## Landscape at a glance

Only three of the eight are built for target evaluation (Virtual Biotech, OriGene, R2E); the rest are components or adjacent tasks.

| Framework | Role for target evaluation | Core design | Evidence reach | Headline evaluation | Validation (my rating) | Reuse terms |
| --- | --- | --- | --- | --- | --- | --- |
| [Virtual Biotech](https://github.com/harrisongzhang/TheVirtualBiotech) (Stanford, *Science* 2026) | End-to-end target due diligence with primary-data analysis | Claude Agent SDK; CSO + 11 specialists + scientific reviewer; 12 MCP servers, 105 tools | Broadest: GWAS credible sets, L2G, single-cell, Tahoe-100M, DepMap, safety, trials | 3 case studies; trial-annotation concordance 89.7% (n=100) | V2 for target calls; V3 for trial curation | MIT; local Open Targets dump; Claude-only |
| [OriGene](https://github.com/GENTEL-lab/OriGene) (SJTU) | Target discovery and Q&A over aggregated databases | 5 agents + retrieved "ThinkTemplates"; OrigeneMCP (\~440 tool functions) | Wide but shallow; no fine-mapping, L2G or colocalization tools | TRQA: MCQ 60.08%, short-answer recall 82.76%; wet lab on 2 picks | V3 on QA; anecdotal wet lab | CC BY-NC-SA 4.0 |
| [Alvessa](https://github.com/ksenia007/alvessa_agent) (Princeton/Flatiron) | Grounded answers on genes, variants, ligandability | LangGraph; ensemble NER; statement-level verifier | Deep variant-to-function; ChEMBL, AlphaFold, pockets | GenomeArena 0.964 vs Claude 0.537 | V3, but self-generated benchmark | Academic non-commercial |
| [Open Targets MCP](https://github.com/opentargets/open-targets-platform-mcp) (EMBL-EBI) | Canonical data access layer | 5 tools: schema, query, batch, search | Whole Open Targets Platform | Internal 140-question Karenina set | V1 | Apache-2.0; hosted endpoint |
| [MRAgent](https://github.com/xuwei1997/MRAgent) (Macao Polytechnic) | Literature-mined Mendelian randomization | Fixed 9-step pipeline; TwoSampleMR in R | Phenotype-level MR via OpenGWAS | LLM comparison + proof of concept | V1–V2 | Apache-2.0 |
| [DeepRare](https://github.com/magic-ai4med/DeepRare) (SJTU, *Nature* 2026) | Adjacent: rare-disease diagnosis | Host + memory + agent servers; 40+ tools incl. Exomiser | Phenotype + genotype for diagnosis | Recall@1 57.18% on 6,401 cases; beats 5 physicians | V3, strongest in set | CC BY-NC 4.0 |
| [R2E](https://arxiv.org/abs/2402.04068) (BenevolentAI, ICML 2024) | Ranks all 19,176 genes per disease query | Retriever + set-transformer reasoner; Shapley attribution | Literature + templated genetics | Time-split trial outcomes AUROC 0.633 | V3, only leakage-controlled outcome test | Datasets CC BY-NC-SA; code closed |
| [DrugAgent](https://github.com/inoue0426/DrugAgent) (Inoue et al.) | Adjacent: drug–target interaction | ML + KG + literature agents, reasoning agent | BindingDB-trained DeepPurpose, KG paths, PubMed | F1 0.514 vs 0.355 (n=250 kinase pairs) | V3, small and leaky | MIT |

## Virtual Biotech

The most complete open stack for multi-scale target due diligence, with the best provenance design in the set, but its target-evaluation quality is shown only through three case studies.

**How it works.** A Chief Scientific Officer agent clarifies the question, gets a field briefing from a chief-of-staff agent, writes an analysis plan, and delegates to specialists in four divisions (target identification, safety, modality, clinical). A scientific reviewer grades outputs and can send work back. Default models are Claude Sonnet 4.5 for reasoning roles and Haiku 4.5 for infrastructure.

- **Data layer:** 12 local MCP servers; I count 105 registered tools. Open Targets is loaded from a local Parquet dump (tested on release 25.09), plus Tahoe-100M pseudobulk DE, Tabula Sapiens v2, CELLxGENE Census, GTEx, Reactome, STRING, ClinicalTrials.gov, cBioPortal and an FDA document API.
- **Real analysis, not just retrieval:** the environment ships scanpy, decoupler, LIANA, lifelines and R lme4 via rpy2. Agents run pseudobulk DE, ligand–receptor inference, spatial mixed models and Cox survival.
- **Provenance MCP:** `record_claims` checks every claim's evidence pointer against the run manifest and trace, and rejects claims citing files or tool calls that never happened.

**Strengths**

- The 55,984-trial study produced a reusable asset: the repo ships 56,707 rows of source-tracked outcome labels (endpoint met, stop reason, serious AE rates by organ). Human concordance on 100 trials was 89.7% (primary endpoint), 83.9% (secondary) and 92.4% (AE rates).
- It replicated the known genetics–success link before adding new features, which is the right order.
- Cost is low: $46 for the B7-H3 analysis and $54 for the OSMR failure analysis, each under a day.

**Critical issues**

1. **No quantitative test of target judgment.** There is no comparison with other agents, human target teams or a simple baseline. The reviewer agent's contribution is never ablated.
2. **The B7-H3 "independent validation" is weak.** B7-H3 ADCs were a known strategy well before the January 2025 model cutoff: in October 2023 Merck paid $4B upfront for ifinatamab deruxtecan and two other DXd ADCs, when that B7-H3 ADC was already in a Phase 2 small-cell lung cancer trial. Nominating an ADC is recall; the novel part (fibroblast-centric mechanism) is untested.
3. **The data layer is not time-sliced.** Web search was disabled, but the repo is tested on Open Targets 25.09 (September 2025), whose ChEMBL clinical data post-dates the cutoff. The paper does not state which release the case study used.
4. **Trial-feature effects are modest and confound-prone.** Odds ratios are 1.11–1.27 per SD. Cell-type specificity tracks target class and modality; modality is a random effect, but target family, sponsor and indication base rates are not. Many trials share one drug, so rows are not independent.
5. **Heavy, single-vendor footprint.** It needs the full Open Targets dump, Tahoe-100M and a 1M-token context CSO on the Claude Agent SDK.

**Verdict:** the best reference architecture to build on, and the trial-label release is the field's most useful public asset. Treat its target conclusions as hypotheses until it is benchmarked.

## OriGene and the TRQA benchmark

OriGene has the broadest retrieval layer and the only wet-lab follow-up in the set, but its released target-ranking logic is popularity-weighted, and TRQA measures fact retrieval rather than target judgment.

**How it works.** Five agents (coordinator, planner, reasoner, critic, reporter) share a memory bank. The coordinator retrieves "ThinkTemplates", reasoning recipes mined from bioinformatics papers; the shipped template store holds 199. The code is a fork of the open-source local-deep-research project. GPT-4.1 is the default model, with DeepSeek and Claude options; embeddings run on SiliconFlow and Volcano Engine APIs.

- **OrigeneMCP** advertises 600+ tools (the paper says 568). I count about 440 decorated tool functions across 15 servers, led by Ensembl (104) and ChEMBL (102) REST wrappers.
- Open Targets is reached through name-based wrappers. A search of both repos found no fine-mapping, locus-to-gene, colocalization or MR tools.

**What the target-discovery code actually does.** In report mode, `search_system.py` harvests gene-like symbols from raw tool text with a regex. It ranks them by most recent mention, mention count and number of tools that returned them. The top batch is then "validated" with three Open Targets lookups: GO cellular component, target class and top associated diseases. Defaults are 2 iterations of 2 sub-questions. Frequently mentioned genes rise; there is no weighting of causal or safety evidence.

**TRQA, profiled file by file**

| Subset | Size | How it was built | Scoring |
| --- | --- | --- | --- |
| TRQA-lit choice | 172 multi-select MCQs | LLM-generated from one review per target (90 targets); questions a Doubao model answered correctly were removed | LLM judge |
| TRQA-lit short answer | 1,108 | Same pipeline | LLM-extracted keyword recall |
| TRQA-db | 641 | Commercial pipeline databases (PharmaCube NextPharma, PatSnap Synapse); 3 disease areas | LLM-extracted keyword recall |

TRQA-db contains 100 patent look-ups, 100 "highest development stage as of April 2025" questions and 50 trial-ID look-ups.

**Critical issues**

1. **Recall-only scoring rewards verbosity.** The released scorer has an LLM extract keywords from the gold answer and counts how many the agent's answer covers. Extra or wrong content is never penalized.
2. **TRQA-db is not reproducible or durable.** Ground truth comes from paid databases and is frozen at April 2025.
3. **Adversarial filtering against one model** biases TRQA-lit against that model family.
4. **No question asks for a ranking or a go/no-go.** High TRQA scores show retrieval breadth, not judgment.
5. **Wet lab has no denominator.** GPR160 in liver cancer (from 125 candidates) and ARG2 in colorectal cancer (from 86) were tested. Both were chosen on tumor overexpression plus survival association, which a plain DE screen also yields; hit rate versus a baseline is unknown. The GPR160 inhibitor is undisclosed and the mouse study is n=5 per group.

**Results reported:** TRQA-lit MCQ 60.08% (above human experts with about two minutes per question), short-answer recall 82.76%, TRQA-db recall 72.05%, GPQA 78.2%, DbQA 50.0%.

**Verdict:** a strong tool aggregator and a useful source of competitive-landscape questions. Neither the agent nor TRQA yet tests what target evaluation is for.

## Alvessa

Alvessa has the best grounding and verification pattern in the set and deep variant-to-function coverage, but its headline benchmark is generated from its own databases and it does not make target decisions.

**How it works.** A LangGraph workflow runs four nodes: tool selection, tool execution, answer generation and evidence verification. Entities are found by an ensemble (Claude Sonnet 4.5, HunFlair2, GLiNER, regex and protein-sequence matching). Answers may use only retrieved records, with a citation per statement.

- **Tools:** 23 modules, including dbSNP, GENCODE, GWAS Catalog, ClinVar, AlphaMissense, Sei, HumanBase, ReMap, Reactome, MSigDB, GO, UniProt, BioGRID, OMIM, Open Targets, miRDB, ChEMBL v35, openFDA, DrugCentral, AlphaFold DB, FPocket and CysDB. Local databases are 45 GB.
- **Verifier:** each statement gets a deterministic check (e.g., identifiers absent from evidence) plus an LLM review, and is labeled supported, partial or unsupported. An answer fails if 30% or more of statements are unsupported.

**Results reported:** GenomeArena (720 MCQs) 0.964 versus Claude Sonnet 4.5 at 0.537 and ChatGPT 5.1 at 0.528; LAB-Bench DbQA 0.704. Against Biomni on small subsets: 0.986 vs 0.806 (n=72) and 0.798 vs 0.787 (n=89). Injected-error detection with evidence access was 92–100%.

**Critical issues**

1. **Circular benchmark.** GenomeArena questions are sampled from the same local database snapshot Alvessa queries. For example, `opentargets_questions.py` draws essential versus non-essential genes from the local Open Targets essentiality table. The gap over plain LLMs mostly measures "has the table" versus "doesn't".
2. **Verification checks support, not truth.** It catches claims absent from retrieved records. It cannot catch a wrong retrieval, a stale record or a misleading omission. It was tested on injected errors, not naturally occurring ones.
3. **No decision layer.** The target case (SMAD2 vs SMAD3 ligandability in the ActRII pathway) is one illustration with no experiment.
4. **License:** Princeton academic, non-commercial use only; companies need a separate license.

**Verdict:** adopt the verifier pattern and the ligandability evidence (CysDB, pockets, ChEMBL) as components. Do not read GenomeArena scores as evidence of target-evaluation skill.

## Open Targets Platform MCP

The official MCP is the right canonical data layer for any target agent, but it is deliberately generic: it gives access, not assessment, and it serves only the current release.

**What it is.** Open Targets announced it on 12 January 2026 as a first iteration; the README still marks it experimental. It is Apache-2.0, hosted at `https://mcp.platform.opentargets.org/mcp`, and runnable locally via uvx or Docker.

- **Five tools:** fetch a schema subset by category (21 categories, from genetic associations to drug safety), fetch type dependencies, run a GraphQL query, run a batch query, and search entities to resolve names to Ensembl, EFO/MONDO and ChEMBL IDs.
- **Useful touches:** optional server-side jq filtering to cut tokens, rate limiting, and an explicit three-step strategy (learn schema, resolve IDs, query).
- **Coverage:** since Genetics merged into the Platform, credible sets, locus-to-gene and colocalization are reachable through the same schema.

**Critical issues**

1. **No assessment layer.** There is no "summarize genetic support" or "list safety liabilities" tool; the LLM must write correct GraphQL each time. The team's own 140-question Karenina benchmark found generic wrappers struggle with aggregations, multi-entity queries and result interpretation.
2. **No time travel.** The public endpoint serves the latest release. Leakage-free evaluation needs a self-hosted archived release, with `OTP_MCP_API_ENDPOINT` pointed at it.
3. **Association scores are circular for outcome prediction.** They include known-drug (ChEMBL clinical) evidence and literature mining, so they partly encode the outcome. They are also ranks, not calibrated probabilities.
4. **No computation.** It returns precomputed results; it cannot run MR, re-weight evidence or test a new hypothesis.

**Verdict:** use it as the default data backbone and put an opinionated, time-aware assessment layer on top. Karenina is a good seed for a shared tool-use test.

## MRAgent

MRAgent shows that an agent can run statistical genetics end to end, but in its current form it is a high-throughput hypothesis generator with liberal defaults, not a safe source of causal evidence for target decisions.

**How it works.** Published in *Briefings in Bioinformatics* (2025); Apache-2.0; pip-installable; last commit July 2025. Given a disease, a fixed nine-step pipeline:

1. Retrieves PubMed abstracts (100 by default) and has an LLM extract exposure–outcome pairs.
2. Searches PubMed for prior MR studies of each pair, optionally grades them against STROBE-MR, and expands synonyms.
3. Matches traits to OpenGWAS study IDs from a bundled list of about 50,000 GWAS.
4. Runs TwoSampleMR in R (IVW and companions, heterogeneity, Egger pleiotropy), optionally MRlap for sample overlap.
5. Has an LLM interpret the results and write the report.

**Critical issues (from the code)**

1. **Automatic threshold relaxation.** If fewer than 11 instruments pass p < 5e-8, the R template retries at 5e-6, then 5e-5. That invites weak-instrument bias and winner's curse, with no F-statistic filter.
2. **No multiplicity control.** It tests the cross-product of literature pairs and matching GWAS IDs, then lets an LLM narrate the significant ones. That is p-hacking at scale unless results are corrected.
3. **Missing standard checks:** no Steiger directionality test and no colocalization.
4. **Wrong flavor of MR for targets.** It tests trait-to-disease causality (for example, a biomarker on a disease). Target evaluation needs drug-target MR: cis-pQTL or cis-eQTL instruments at the gene, which give the expected effect of perturbing that protein.
5. **Evaluation:** different LLMs were compared on running the pipeline, plus a proof-of-concept case. Causal-claim accuracy against trials or replicated MR was not measured.

**Verdict:** a useful pattern to fork, not a tool to trust. Rebuild it as a cis-MR plus colocalization agent with a pre-registered analysis plan and fixed thresholds.

## DeepRare

DeepRare is not a target-evaluation tool, but it is the best-evaluated agent in the set and the evaluation template target evaluation lacks.

**How it works.** Published in *Nature* (2026); CC BY-NC 4.0. A central host with long-term memory coordinates agent servers with 40+ tools:

- **Phenotype side:** free text to HPO terms, PhenoBrain, PubCaseFinder, similar-case retrieval re-ranked with MedCPT, and zero-shot LLM inference.
- **Genotype side:** Exomiser over VCFs.
- **Knowledge side:** OMIM and Orphanet normalization, PubMed, web and clinical-reference search.
- **Self-reflection:** if every hypothesis is ruled out, it widens the search and repeats, then returns a ranked list with a rationale.

**Results reported:** 6,401 cases across 8 datasets and 2,919 diseases. Mean Recall@1 was 57.18% versus 33.39% for the next-best method (Claude 3.7 Sonnet thinking). With exome data on 109 hospital cases, Recall@1 was 70.6% versus Exomiser's 53.2%. On 163 cases, it beat five rare-disease physicians (Recall@1 64.4% vs 54.6%). Clinicians audited 180 reasoning chains and judged 95.4% of references reliable and relevant.

**Why it matters for target evaluation**

1. **Evaluation design to copy:** many datasets, 15 baselines, an in-house hospital cohort, a head-to-head with experts, and an audit of the reasoning itself.
2. **Reusable evidence machinery:** gene–phenotype ranking from patients is causal human evidence for rare and monogenic indications, and phenotype breadth from knockout-like patients informs on-target safety.

**Critical issues**

1. **Contamination risk.** Some benchmark cases were curated from published case reports, while the case-search tools retrieve published cases. The stated limitations do not address this.
2. **Fragile and restricted retrieval.** Parts of search rely on ChromeDriver page scraping, and the license is non-commercial.
3. **No prospective clinical test** has been reported.

**Verdict:** borrow the evaluation playbook and the genotype–phenotype components; it does not address target evaluation directly.

## Retrieve to Explain (R2E)

R2E is the methodological anchor of the space: it frames target identification as ranking every gene and tests it on time-split clinical outcomes. It is not an LLM agent, and its code is closed.

**How it works.** BenevolentAI (Patel et al.), ICML 2024. A query is a cloze sentence ("\[MASK\] is a promising drug target for osteoporosis"); all 19,176 protein-coding genes are candidates.

- **Corpus:** about 160 million entity-linked sentences from PubMed, PMC and publisher full text, with each gene masked. Genetics associations are turned into 77,645 templated sentences.
- **Model:** a 10M-parameter retriever pulls 64 passages per gene; a 2M-parameter set transformer scores query–evidence match. The answer is seen only through its evidence.
- **Explanation:** Shapley values over passages, so each score is attributed to specific evidence by construction.
- **Popularity correction:** a tunable term discounts genes that are frequent in the corpus.

**Results reported (clinical-trial outcomes, temporal split at 2005, 1,449 successes and 4,222 failures):**

| Model | AUROC |
| --- | --- |
| Industry genetics baseline | 0.545 |
| R2E, genetics only | 0.579 |
| R2E, literature (frequency-corrected) | 0.632 |
| R2E, literature + genetics | 0.633 |
| R2E + GPT-4 evidence audit | 0.638 |

The paper also reports beating a few-shot, retrieval-augmented GPT-4 baseline.

**Strengths**

- The only framework here with a leakage-controlled outcome test.
- Exhaustive ranking avoids an LLM picking from memory.
- It measured popularity bias and corrected it, which every LLM agent here ignores.

**Critical issues**

1. **Absolute performance is modest:** 0.63 AUROC, and adding genetics to literature barely helps.
2. **Not reproducible:** training corpus, code and weights are proprietary; only the three evaluation sets are public (CC BY-NC-SA).
3. **Narrow input:** one generic query template, no expression, safety or tractability evidence, and no analysis.

**Verdict:** copy its task framing, temporal split and attribution; combine them with an agent's evidence breadth.

## DrugAgent (Inoue et al.)

DrugAgent predicts whether a compound binds a protein, a chemistry question rather than a target-evaluation one; its main lesson for this space is how easily knowledge-graph evidence leaks the label.

**How it works.** arXiv 2408.13378 (v4), ICLR 2025 workshop; MIT license; repo updated July 2026. A coordinator routes a drug–target pair to an ML agent (DeepPurpose MPNN-CNN trained on BindingDB), a KG agent (paths up to length 4 over DrugBank, CTD, STITCH and DGIdb), and a literature agent (Bing in the paper, PubMed RAG in the current repo). A reasoning agent combines their scores and writes an explanation.

**Results reported:** on 250 kinase–drug pairs from a 2011 kinase-profiling study, F1 was 0.514 versus 0.355 for GPT-4o mini, but AUROC was nearly identical (0.941 vs 0.938). Removing the ML agent dropped F1 to 0.274. Explanations were shown as examples, with no systematic quality test in the paper.

**Critical issues (from the data shipped in the repo)**

1. **Label leakage through the KG.** The current ground truth holds 900 kinase pairs labeled Strong, Moderate or Weak, plus 500 Tox21 androgen-receptor pairs. For 423 of the 900 kinase pairs (47%), the KG has a direct edge, and edges carry BindingDB affinities. Example: JAK1 with JNJ-7706621 is labeled Strong, and its KG edge reads Kd 21 nM. The authors balance direct edges across classes, but the edge text still states the answer.
2. **Likely ML leakage too.** DeepPurpose was trained on BindingDB, which probably contains many of the same kinase measurements.
3. **Gains look like thresholding.** Equal AUROC with higher F1 means better calibration of a cut-off, not better discrimination.
4. **Small and narrow:** 250 pairs in the paper, kinases only.

**Verdict:** relevant only as a template for a chemical-tractability sub-agent. Its leakage pattern (the evidence source contains the label) recurs across the space.

## Cross-cutting gaps

The frameworks that reach broad evidence are validated weakly, and the one validated on outcomes reaches narrow evidence. Nothing sits where both are strong.

&#91;embedded content: framework positions · evidence breadth × validation of the target claim\]

The broad frameworks sit low and the validated one sits left. DeepRare is left off because its strong validation is for diagnosis, not target evaluation.

1. **The task is undefined.** No framework commits to an output a decision-maker can score: a probability of success per (target, indication), a go/no-go, or a ranked modality choice. Outputs are reports; benchmarks are QA.
2. **Benchmarks don't test the decision, and most leak.**
   - TRQA: LLM-generated from reviews, ground truth from paid databases, recall-only scoring.
   - GenomeArena: sampled from the agent's own databases.
   - Karenina: 140 questions, tool-use only.
   - TargetBench 1.0 (Insilico, 2025): rediscovery of clinical-stage targets, which LLMs largely memorize.
   - Only R2E time-splits. No data layer here is time-sliced: Virtual Biotech runs on Open Targets 25.09, and the Open Targets MCP serves the latest release.
3. **Causal genetics is shallow.** Precomputed L2G and colocalization lookups exist (Virtual Biotech, Open Targets). Nobody runs cis-pQTL MR, uses allelic series for dose-response, or infers whether to inhibit or activate. MRAgent's MR is phenotype-level with relaxed thresholds.
4. **Evidence weighting is left to the LLM.** Conflicting evidence is reconciled in prose, so weights are implicit and unstable. Popularity bias goes unmeasured: OriGene ranks by mention count, while R2E showed frequency correction matters.
5. **Verification stops at citations.** Alvessa checks statements against records; Virtual Biotech checks that cited artifacts exist. Nobody re-runs the statistics, checks analysis assumptions, or ablates the reviewer agent.
6. **Safety and modality reasoning is thin.** Safety mostly means Open Targets liabilities and FAERS. Only Virtual Biotech reasons over cell-type expression; only Alvessa reaches cysteine ligandability and pockets.
7. **No prospective, blinded test against people.** OriGene's wet lab covers two hand-picked targets; Virtual Biotech's external check is a known drug. Only DeepRare, an adjacent task, competed with experts on held-out cases.
8. **Reuse is constrained.** Four of eight carry non-commercial terms or closed code (OriGene, Alvessa, DeepRare, R2E). Footprints run to 45–100+ GB of local data. Virtual Biotech is tied to one model vendor; OriGene to China-hosted embedding APIs.
9. **Private data is out of scope.** None connects to internal assay data, electronic lab notebooks or patent full text; competitive intelligence falls back to web search.

## Opportunities, ranked

The first two items unlock everything else: without a time-sliced benchmark and data layer, no claim of better target judgment can be tested.

| Rank | Opportunity | Gaps it closes | Builds on | Effort |
| --- | --- | --- | --- | --- |
| 1 | **Time-sliced target-decision benchmark.** (Target, indication) pairs scored against phase transitions after an as-of date; agents see only pre-cutoff data. Metrics: AUROC, Brier score, relative success in the top decile, faithfulness of attribution. | 1, 2, 4 | Virtual Biotech's 56,707 trial labels; R2E's outcome set and temporal protocol; Open Targets archived releases | Medium |
| 2 | **As-of data layer.** One date parameter enforced across tools: archived Open Targets releases, literature by publication date, trials by start date. | 2 | Open Targets MCP's configurable endpoint; Virtual Biotech's local loaders | Low–medium |
| 3 | **Drug-target causal-genetics agent.** cis-pQTL and cis-eQTL MR plus colocalization, fixed thresholds, F-statistics, Steiger, multiplicity control, and a pre-registered plan. Output: effect direction, magnitude and whether to inhibit or activate. | 3 | MRAgent's pipeline pattern; Open Targets credible sets; UKB-PPP and deCODE pQTLs | Medium |
| 4 | **Typed evidence ledger plus a transparent scorer.** Agents fill a schema (evidence type, direction, strength, source, as-of date); a model trained on historical outcomes turns it into a calibrated probability. The LLM explains; it does not weigh. | 1, 4 | Virtual Biotech's claims MCP; Alvessa's verifier | Medium–high |
| 5 | **Verification of analyses, not just citations.** Re-run code in a sandbox, check stated assumptions, and add a pre-mortem agent that argues why the target fails. Ablate it to prove value. | 5 | Virtual Biotech reviewer; Alvessa verifier | Medium |
| 6 | **Popularity-aware ranking.** Report performance by literature volume; apply frequency correction; build a "dark genome" subset. | 4 | R2E frequency term | Low |
| 7 | **Safety and modality sub-agents with real models.** Cell-type on-target exposure, essentiality, LoF tolerance, knockout phenotypes, ligandability and surface localization. | 6 | Virtual Biotech single-cell stack; Alvessa CysDB/FPocket; DrugAgent as chemistry template | Medium |
| 8 | **Prospective, public prediction log.** Register calibrated predictions for Phase 2 and 3 trials reading out in the next 12–24 months; score them on readout. | 7 | Opportunities 1 and 4 | Low to start, slow to pay off |
| 9 | **Blinded agent-versus-team review.** Same dossier inputs, expert panel scores both, outcomes tracked later; audit reasoning chains as DeepRare did. | 7 | DeepRare's evaluation design | High |
| 10 | **Commercially reusable, private-data-ready stack.** MIT/Apache components (Virtual Biotech, Open Targets MCP, MRAgent, DrugAgent) plus adapters for internal assays, ELNs and patents. | 8, 9 | Those four repos | Medium |

## Proposed evaluation protocol

A target-evaluation agent should pass six tiers, each scored separately, before anyone trusts its rankings; today's frameworks stop at tier 1 or 2.

| Tier | What it tests | How | Metric | Leakage control |
| --- | --- | --- | --- | --- |
| 0. Tool correctness | IDs resolve; queries return the right rows | Deterministic unit tests, Karenina-style queries | Exact match | None needed |
| 1. Evidence retrieval | Finds the facts that matter | QA with gold answers, scored for precision and recall | F1; unsupported-claim rate | Questions not generated from the agent's own tables |
| 2. Analysis correctness | Runs statistics correctly | Reproduce published analyses (e.g., genetic support roughly doubling success) | Effect size within the published CI | Published results withheld from context |
| 3. Retrospective decision | Ranks (target, indication) pairs by later success | Freeze all data at a cutoff; predict later phase transitions | AUROC, Brier score, relative success in top decile, by literature-volume stratum | As-of data layer; known-drug evidence removed; model knowledge cutoff before the as-of date |
| 4. Explanation faithfulness | Cited evidence actually drives the score | Delete the top-attributed evidence and re-score; expert audit of a sample | Score drop; audit agreement | Same as tier 3 |
| 5. Prospective | Works on the unknown | Public, time-stamped predictions for upcoming readouts; blinded agent-vs-team review | Calibration on readout; panel preference | Predictions logged before results |

**Required baselines for tier 3:** Open Targets association score with clinical evidence removed; genetics-only (L2G and credible-set support); a literature-frequency ranker; and the same LLM without tools. An agent that cannot beat the genetics-only baseline adds cost, not judgment.

**Report every run with** model and version, data release, as-of date, cost, wall-clock time, and the full trace, so results can be replayed.

## Sources

**Repositories read (cloned and inspected)**

- [TheVirtualBiotech](https://github.com/harrisongzhang/TheVirtualBiotech) and its [environment.yml](https://github.com/harrisongzhang/TheVirtualBiotech/blob/main/environment.yml)
- [OriGene](https://github.com/GENTEL-lab/OriGene) and [OrigeneMCP](https://github.com/GENTEL-lab/OrigeneMCP)
- [alvessa\_agent](https://github.com/ksenia007/alvessa_agent)
- [open-targets-platform-mcp](https://github.com/opentargets/open-targets-platform-mcp)
- [MRAgent](https://github.com/xuwei1997/MRAgent)
- [DeepRare](https://github.com/magic-ai4med/DeepRare)
- [DrugAgent](https://github.com/inoue0426/DrugAgent)

**Papers, datasets and pages opened**

- [The Virtual Biotech, bioRxiv preprint](https://www.biorxiv.org/content/10.64898/2026.02.23.707551v1.full) · [project site](https://virtualbiotech.ai/) · [Science article](https://www.science.org/doi/10.1126/science.aeg6779) · [publication date report](https://dealroom.co/news/154191-stanfords-virtual-biotech-turns-37-000-ai-agents-into-a-drug-discovery-f)
- [OriGene, bioRxiv preprint](https://www.biorxiv.org/content/10.1101/2025.06.03.657658v1.full) · [TRQA on Hugging Face](https://huggingface.co/datasets/GENTEL-Lab/TRQA)
- [Alvessa, bioRxiv preprint](https://www.biorxiv.org/content/10.64898/2025.12.30.697073v1.full)
- [Official Open Targets MCP announcement](https://blog.opentargets.org/official-open-targets-mcp/)
- [MRAgent publication record](https://research.mpu.edu.mo/en/publications/mragent-an-llm-based-automated-agent-for-causal-knowledge-discove/)
- [DeepRare, arXiv](https://arxiv.org/html/2506.20430v1) · [coverage of the Nature paper](https://lifespan.io/news/ai-tool-sets-new-standard-in-diagnosing-rare-diseases/)
- [Retrieve to Explain, arXiv v4](https://arxiv.org/html/2402.04068v4)
- [DrugAgent, arXiv v4](https://arxiv.org/html/2408.13378v4)
- [Pham and Hy, Evaluating Agentic Bioinformatics through Function, Evidence, and Validation](https://arxiv.org/abs/2607.27556)
- [Insilico TargetPro and TargetBench 1.0 announcement](https://insilico.com/news/v49bfcu0r1-transforming-drug-target-discovery-insil)
- [Merck and Daiichi Sankyo DXd ADC collaboration, October 2023](https://www.merck.com/news/daiichi-sankyo-and-merck-announce-global-development-and-commercialization-collaboration-for-three-daiichi-sankyo-dxd-adcs/)
