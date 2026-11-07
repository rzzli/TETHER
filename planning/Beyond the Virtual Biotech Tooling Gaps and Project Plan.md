# Beyond the Virtual Biotech: Tooling Gaps and Project Plan

Oct 8, 2026 · @R

## Bottom line

Build a time-locked target-evaluation system (working name **TETHER**) and a benchmark on which TETHER and the Virtual Biotech run with the same model, data and as-of date. Claim "better" only if pre-registered tests pass.

**What the audit found.** 78 of Virtual Biotech's 105 tools are lookups into one Open Targets release. Its strengths are process: planning, review, provenance and replay. Four gaps leave room to beat it on public data:

1. **No computation on genetic summary statistics:** no cis-MR, no direction-of-effect call, no phenome-wide safety scan.
2. **Perturbation evidence is cancer-only:** DepMap and Tahoe-100M.
3. **No sense of time:** one data release, live trials and live web; undated evidence passes year filters.
4. **No number to score:** confidence is a word, so discrimination and calibration were never measured.

**Deliverables**

- **Repo** (Apache-2.0): TETHER, plus a harness that runs Virtual Biotech, Biomni, OriGene and baselines unchanged.
- **TETHER-Bench** (CC BY-SA 4.0): time-locked (target, indication) pairs, leakage tests and a leaderboard.
- **Preprint** on bioRxiv by June 2027, about eight months after start, with an OSF pre-registration; journal submission follows.

**Decision needed now:** approve Phase 0, six weeks to size the post-cutoff label set, simulate power and file the pre-registration. Everything after depends on that count.

## What Virtual Biotech can do today

Virtual Biotech (commit `71f9da6`, 16 Sep 2026) is, in tooling terms, one Open Targets release plus single-cell, perturbation and live clinical APIs: 78 of its 105 local tools read the Open Targets 25.09 dump. Its distinctive strength is process (planning, review, provenance), not data breadth.

| MCP server | Tools | Backing data | Lookup or compute |
| --- | --- | --- | --- |
| target | 16 | Open Targets: annotations, tractability, safety, mouse KO, constraint, probes, prioritisation scores | Lookup |
| association | 11 | Open Targets associations, evidence strings, literature metadata and embeddings | Lookup + similarity |
| genetics | 10 | Open Targets credible sets, L2G, colocalisation, variants, studies, enhancer–gene links | Lookup |
| pathway | 10 | Reactome, GO, Sequence Ontology (from Open Targets) | Lookup + enrichment |
| drug | 9 | Open Targets ChEMBL drugs, indications, warnings, openFDA significant AEs, pharmacogenomics | Lookup |
| functional genomics | 9 | DepMap essentiality via Open Targets (5); Tahoe-100M pseudobulk DE (4) | Lookup |
| single cell | 11 | CELLxGENE Census, Tabula Sapiens v2 | Data retrieval for agent-written analysis |
| expression | 6 | Open Targets baseline (GTEx RNA, HPA protein IHC) | Lookup |
| clinical trials | 8 | ClinicalTrials.gov live API (4), cBioPortal (4) | Live lookup |
| interaction | 5 | Open Targets interactions | Lookup + network hops |
| provenance | 4 | The run's own manifest and trace | Validation |
| fda\_gxl (remote) | n/a | FDA regulatory documents, API key required | Live lookup |

**Process features worth keeping**

- **Planning and review:** the CSO writes an analysis plan before dispatch; a read-only reviewer grades question fit, evidence strength and thoroughness.
- **Provenance:** claims are validated on write against the manifest and trace; `verify.py` re-hashes artifacts, can re-run agent-written scripts, and diffs a replay.
- **Open-ended analysis:** every specialist has Bash and code execution, so agents can download datasets the tools don't cover (the Visium and TCGA analyses were done this way).
- **Skills:** four, two of them single-cell (analysis, data prep and QC), plus evidence citation and run organization.
- **Web access:** five agents (single-cell, safety, clinical trialist, chief of staff, trial matching) have live web search and fetch.

**What the outputs look like:** a markdown and JSON report whose `confidence` field is a word (strong, moderate) chosen by the LLM. There is no numeric score, no calibration, and no batch evaluation mode.

## Tooling gaps that remain

The largest gaps are computation on genetic summary statistics, non-cancer perturbation evidence, date-bounded literature and clinical history; all can be filled from public data. Because every Virtual Biotech agent has Bash, it can sometimes reach these ad hoc. The gap is the lack of a tested, reproducible tool, not physical access.

| Capability | Virtual Biotech today | Gap | Public data to fill it | Priority |
| --- | --- | --- | --- | --- |
| Drug-target Mendelian randomization | Precomputed colocalization lookups only | No summary-statistic tooling: no cis-MR, no re-fine-mapping, no LD reference | UKB-PPP pQTLs (Synapse, AWS Open Data), deCODE pQTLs, eQTL Catalogue, GTEx; outcome GWAS from FinnGen, Pan-UKB, GWAS Catalog | P1 |
| Direction of effect | LoF/GoF assumptions sit inside raw evidence strings | Nothing aggregates them into an inhibit-or-activate call | Open Targets direction-of-effect assessments (gene burden, ClinVar, Gene2Phenotype, Orphanet, IMPC, clinical precedence); sign of cis-MR | P1 |
| Genetic-proxy safety scan | gnomAD constraint, mouse knockouts | No phenome-wide scan of what perturbing the target does | FinnGen, Pan-UKB, Genebass, AstraZeneca PheWAS portal | P1 |
| Rare-variant burden and allelic series | Reachable only as evidence strings | No dose–response model across variant classes | Genebass, AstraZeneca PheWAS portal, gnomAD | P2 |
| Perturbation outside oncology | DepMap and Tahoe-100M; the agent is declared "cancer only" | No evidence from primary cells, neurons, immune cells | BioGRID ORCS screens, genome-wide Perturb-seq (K562, RPE1), CRISPRbrain, LINCS L1000 | P1 |
| Disease-signature reversal | None | Cannot test whether perturbing the target reverses the disease state | CMap/LINCS, CELLxGENE disease atlases, Tahoe-100M | P3 |
| Protein and surface expression | Open Targets baseline (GTEx RNA, HPA IHC) | No tumor-vs-normal surface ratio for antibody, ADC or cell-therapy targets | HPA, CPTAC proteomics, surfaceome atlases, UKB-PPP plasma levels | P2 |
| Spatial context | Ad hoc downloads plus agent-written code | Not a tool, so not repeatable across runs | CELLxGENE spatial collections, HTAN, public Visium and Xenium sets | P3 |
| Structure and ligandability | Tractability buckets, chemical probes | No pockets, no compound potency, no covalent ligandability | AlphaFold DB, PDB, fpocket or P2Rank, ChEMBL bioactivities, CysDB, PROTAC-DB | P2 |
| Modality feasibility | Tractability for small molecule, antibody, PROTAC | No oligonucleotide delivery logic, no topology or extracellular-domain check | UniProt topology, HPA, curated delivery rules (for example GalNAc to hepatocytes) | P2 |
| Literature | Open Targets text mining; live web search | No date-bounded search, no study-design grading, no retraction filter | Europe PMC and PubMed APIs with date filters, bioRxiv API, Crossref retraction data | P1 |
| Clinical history and base rates | Live ClinicalTrials.gov; Open Targets known drugs | No as-of trial state; no prior success rates by area, modality or target class; its own 56,707 labels are not a tool | AACT monthly archives, dated ChEMBL releases, Virtual Biotech labels, CTO labels | P1 |
| Human safety signals | Open Targets significant FAERS reactions, drug warnings | No label-derived adverse events or class effects | openFDA FAERS, OnSIDES or SIDER, Drugs@FDA labels | P3 |
| Patents and pipeline | Web search only | No structured patent or competitor view | SureChEMBL, Google Patents public data, ChEMBL, ClinicalTrials.gov sponsors | P3 |

P1 items are the ones the head-to-head claim rests on; P2 improve modality and safety calls; P3 can follow the preprint.

## Process and evaluation gaps

The gaps that most limit a credible "better than" claim are about time and scoring, not tools.

1. **No as-of enforcement.** Everything reads one Open Targets release (25.09) plus live ClinicalTrials.gov and live web. `query_evidence` has an optional year filter, but it lets undated evidence through. Precomputed association scores already include later evidence and known-drug (clinical) evidence, which partly encodes the outcome.
2. **No numeric decision.** Confidence is a word chosen by the LLM. Nothing can be scored for discrimination or calibration.
3. **No evaluation harness.** There is no batch mode, no held-out task set, and no ablation of the reviewer, the chief-of-staff briefing or individual specialists.
4. **Verification checks provenance, not judgment.** `verify.py` re-hashes artifacts and can re-run scripts. Nothing checks whether an analysis choice was right (replicates in pseudobulk DE, multiple testing, confounder adjustment).
5. **Single-vendor runtime.** The Claude Agent SDK ties system design to one model family, so model gains and design gains cannot be separated.
6. **Untested bias.** Performance on poorly studied targets is unmeasured, so literature popularity may be doing much of the work.
7. **Fixed cost profile.** About $46–54 per dossier with no budget-limited mode, which makes large-N evaluation expensive for anyone, including us.

## Related efforts to borrow from or compare against

The project should reuse other groups' best parts and run every open competitor as a baseline, so the result reads as a fair field test rather than a one-on-one.

| Effort | What to take | Role in the project |
| --- | --- | --- |
| [Virtual Biotech](https://github.com/harrisongzhang/TheVirtualBiotech) | Orchestration, reviewer, provenance, 56,707 trial labels | Primary baseline at pinned commit; label source |
| [Open Targets Platform and MCP](https://github.com/opentargets/open-targets-platform-mcp) | Canonical evidence, direction-of-effect assessments, archived releases | Data backbone; association-score baseline |
| [R2E](https://arxiv.org/html/2402.04068v4) | Rank-every-gene framing, time split, evidence attribution, popularity correction | Design template; score on its released clinical-outcome set |
| [Alvessa](https://github.com/ksenia007/alvessa_agent) | Statement-level verifier | Re-implement the pattern (license is academic-only) |
| [OriGene](https://github.com/GENTEL-lab/OriGene) and TRQA | Broad tool layer; competitive-landscape questions | Agent baseline; TRQA-db as a sanity check |
| [Biomni](https://www.labmanager.com/biomedical-ai-agent-connects-more-than-150-research-tools-35884) | General biomedical agent, open codebase | General-agent baseline |
| [TargetBench 1.0](https://www.biorxiv.org/content/10.1101/2025.08.06.668866.full.pdf) | Clinical-target retrieval over 38 diseases; no temporal split | Report for comparability; show how its scores move under time-locking |
| [CTO](https://arxiv.org/html/2406.10292v3) | About 125,000 weakly labeled trials, F1 91–94 vs humans | Label source after linking trials to targets |
| Minikel 2024; Razuvayevskaya 2024 | Genetic-support effect on success and stoppage | Baselines to replicate on public labels |
| [DeepRare](https://github.com/magic-ai4med/DeepRare) | Multi-dataset evaluation, expert head-to-head, reasoning audit | Evaluation design template |
| [MRAgent](https://github.com/xuwei1997/MRAgent) | Agent-driven MR pipeline | Starting point for cis-MR module, with fixed thresholds |
| [Pham and Hy 2026](https://arxiv.org/abs/2607.27556) | Function–Evidence–Validation reporting | Reporting standard for the preprint |

## Project thesis and hypotheses

**Thesis.** With the same model, the same data and the same as-of date, a system that computes causal genetics, records typed evidence, and scores it with a model trained only on earlier outcomes will rank (target, indication) pairs by later clinical success better than the Virtual Biotech, at lower cost, with every claim auditable. Working name for the system: **TETHER**.

Hypotheses are registered on OSF before test labels are unlocked. The preprint claims "better" only if H1 and H2 both pass; otherwise it reports the benchmark and the negative result.

| ID | Hypothesis | Test | Pass criterion |
| --- | --- | --- | --- |
| H1 (primary) | TETHER discriminates later success better than Virtual Biotech | Paired DeLong on locked post-cutoff test set; Brier score as co-primary | AUROC gain > 0, one-sided p < 0.05; smallest effect of interest 0.05 |
| H2 | TETHER beats simple baselines | Same test vs genetics-only and time-masked Open Targets association score | AUROC gain > 0 vs both |
| H3 | Gains are not popularity | H1 repeated within the bottom tercile of target publication count | Gain retains sign; CI reported |
| H4 | Computed causal genetics adds signal | Ablate cis-MR and direction-of-effect features | AUROC drop > 0 with bootstrap CI excluding 0 |
| H5 | Dossiers are better and cheaper | Blinded expert panel preference; audited claim error rate; cost per dossier | Panel preference > 50% (sign test); lower error rate and cost |
| H6 (re-analysis) | Virtual Biotech's single-cell findings survive stricter tests | Refit with drug-level clustering, target-family adjustment, and out-of-time prediction | Two-sided; reported whichever way it falls |

H6 is not a bet against the Virtual Biotech; it is an independent check of its main scientific result, and it is publishable either way.

## System design

TETHER keeps Virtual Biotech's strengths (specialists, review, provenance, open-ended code) and adds the three things it lacks: a time gate on every input, a typed ledger instead of prose, and a scorer trained on past outcomes.

&#91;embedded content: TETHER architecture · time gate, 8 specialists, ledger, critics, scorer\]

Specialists never set the final number. They write evidence into the ledger; critics can send work back; the scorer turns the ledger into a probability, and the LLM only explains it.

## Benchmark design (TETHER-Bench)

Each item is a (target, indication) pair frozen at an as-of date T0 and labeled by what happened next; every input any system sees is filtered to what was public before T0.

**Tasks**

| Task | Question | Label source | Primary metric |
| --- | --- | --- | --- |
| T1 Next transition (primary) | Pair in Phase 1 or 2 at T0: does it advance by T1? | AACT snapshots at T0 and T1; dated ChEMBL releases; Virtual Biotech and CTO endpoint labels; stop-reason categories | AUROC, Brier, calibration slope |
| T2 Matched pairs | Same indication, one success and one failure: which wins? | Subset of T1 | Paired accuracy (McNemar) |
| T3 Rank every target | For a disease at T0, rank all genes; score targets that enter the clinic after T0 | ChEMBL and AACT diffs | Recall at K, MRR |
| T4 Mechanism direction | Should the target be inhibited or activated? | Mechanism of drugs that advance after T0 | Accuracy |
| T5 Safety | Will the program stop for safety, and in which organ class? | Stop reasons; Virtual Biotech serious-AE rates | AUROC per class |
| T6 Dossier audit | Are the claims in a full dossier true and supported? | Expert-written gold evidence for about 50 pairs | Claim error rate |

**Time splits**

- **Rolling origins** (for example T0 = 2019, 2021, 2023): train and validate the scorer with no LLM in the loop.
- **Locked agent test:** T0 = the model's training-data cutoff; outcomes from T0 to the label freeze stay hidden until the analysis plan runs.
- **Prospective log:** hashed, time-stamped predictions for readouts expected in the next 12–24 months, scored as they arrive.

**Leakage controls**

1. **Data:** evidence filtered by publication year, study date and trial dates. Undated evidence is dropped, not passed. Association scores are recomputed from masked evidence; the clinical (known-drug) datatype never enters features.
2. **Trials:** status comes from the AACT snapshot at T0, never live ClinicalTrials.gov.
3. **Literature:** date-bounded Europe PMC and PubMed only; web search off or date-bounded.
4. **Model:** training cutoff before T0, plus a contamination probe: ask the bare model each outcome and report results with and without pairs it already knows.
5. **Canaries:** planted synthetic "future" facts must never surface in any run.
6. **Labels:** 200 labels double-annotated; Cohen's kappa reported.

**Size.** Virtual Biotech's linkage file already maps 488,361 trial–drug–target–disease rows to 72,158 target–indication pairs (1,520 targets, 2,559 diseases). Decisive post-cutoff pairs will be far fewer, probably hundreds; Phase 0 measures the number and sets the power gate.

**Licenses to respect.** Open Targets is CC0; ChEMBL is CC BY-SA 3.0, so derived labels inherit share-alike; Virtual Biotech labels are MIT; R2E's set is CC BY-NC-SA (compare, don't redistribute); CTO's license must be confirmed.

## Head-to-head protocol

Virtual Biotech runs exactly as released, on the same masked data and the same model as TETHER; the only addition is the question we ask it.

**Fairness rules**

1. **Pinned code.** Virtual Biotech at commit `71f9da6` (MIT license). Masking keeps the Open Targets 25.09 schema, so its loaders run unchanged.
2. **Same model.** Both systems use Virtual Biotech's defaults (Claude Sonnet 4.5 for reasoning, Haiku 4.5 for infrastructure). TETHER is also run on an open-weight model to show the gain comes from design.
3. **Same world.** Web search is off for both, as in Virtual Biotech's own B7-H3 case. Live ClinicalTrials.gov is replaced by an AACT-at-T0 shim with identical tool signatures.
4. **Same question.** "Evaluate {target} for {indication} as of {T0}; end with the probability it advances to the next phase within 24 months." No system prompt is edited. Its categorical confidence is also scored as an ordinal, as a sensitivity check.
5. **Variance.** Three seeds per system on a 100-pair subset.
6. **Open review.** The harness and analysis plan are shared with the Virtual Biotech authors before the lock.

**Baselines**

| ID | Baseline | Why it is there |
| --- | --- | --- |
| B0 | Base rate by therapeutic area, modality and phase | Floor any system must beat |
| B1 | Genetics only (credible-set and L2G support at T0) | The established predictor |
| B2 | Time-masked Open Targets association score, clinical datatype removed | What a scientist gets without agents |
| B3 | Literature-frequency ranker | Measures popularity bias |
| B4 | Same LLM, no tools | Isolates the value of tools |
| B5 | Virtual Biotech | Primary comparator |
| B6 | Biomni; OriGene | Other agents, on a cost-capped subset |
| A1–A5 | TETHER minus cis-MR and direction of effect; minus scorer (LLM states probability); minus critics; minus perturbation; minus literature | Ablations for H4 and design claims |

**Metrics and statistics**

- Discrimination and calibration: AUROC, AUPRC, Brier score, calibration slope and intercept, relative success in the top decile.
- Cost: dollars, tokens and wall-clock per pair.
- Inference: paired DeLong for AUROC; bootstrap CIs resampled by indication cluster; Holm correction across secondary hypotheses; McNemar for matched pairs (T2).
- Power: simulated in Phase 0 from the realized pair count and baseline AUROCs.

**Expert panel (H5).** Six target-assessment scientists rate 40 pairs. Each sees two anonymized dossiers, normalized by a neutral formatter and shown in random order, and scores correctness, completeness, calibration, actionability and overall preference. Inter-rater agreement is reported.

**Published cases revisited.** Both systems rerun Virtual Biotech's three cases (B7-H3 in lung cancer, OSMR in ulcerative colitis, the trial-feature study). The B7-H3 rerun checks whether each system surfaces that a B7-H3 ADC was already in Phase 2 in October 2023.

## Budget and compute estimate

The direct cost is roughly $90k–110k over nine months, and running Virtual Biotech itself is the largest line. These are planning estimates; the per-run figure for Virtual Biotech comes from its paper ($46–54 per case), the rest are assumptions to confirm in Phase 0.

| Item | Basis | Estimate |
| --- | --- | --- |
| Virtual Biotech runs | \~400 test pairs + 200 repeat-seed runs, \~$50 each | \~$30k |
| TETHER runs | Same 600 runs at a target of ≤ $15 each | \~$9k |
| Ablations | Mostly re-scoring saved ledgers; some reruns | \~$5k |
| Biomni and OriGene | 100-pair subset each | \~$4k |
| Development LLM spend | Building and debugging agents and tools | $10k–15k |
| Compute and storage | One large-memory server or cloud equivalent for 8 months; \~5 TB storage. UKB-PPP is streamed by cis window from AWS rather than downloaded (the full regional set is about 9 TB) | $10k–18k |
| Expert panel | 6 experts × \~15 h | \~$13k |
| Label audit | 200 double-annotated labels | \~$3k |
| Open-access fee | Journal dependent | $3k–12k |

**People.** One to two full-time computational biologist or ML engineers, a statistician at about 20%, and a drug-discovery advisor at about 10%.

**Ways to cut cost.** Apply for model-provider research credits; shrink the repeat-seed subset; run Biomni and OriGene on 50 pairs; reuse cached tool outputs across systems where tool calls are identical.

## Roadmap

The preprint is targeted for June 2027, about eight months after a mid-October 2026 start; the journal submission follows once the locked results are in, and the prospective log keeps scoring into 2028.

&#91;embedded content: TETHER roadmap · 4 phases, 4 gates, 3 milestones\]

Each phase ends at a gate. A failed gate changes scope, not the publication plan:

| Gate | Pass criterion | If it fails |
| --- | --- | --- |
| G0 | Enough decisive post-cutoff pairs for 80% power at a 0.05 AUROC gap; label audit kappa ≥ 0.8 | Add matched pairs and Phase 1→2 transitions; extend the label freeze |
| G1 | Virtual Biotech runs unchanged on masked data; all canaries stay hidden | Fix the masking layer before any comparison |
| G2 | Scorer beats the genetics-only baseline on rolling-origin folds | Drop the scorer claim; compare LLM-stated probabilities instead |
| G3 | Locked H1 and H2 analyses run as registered | Report the null with the benchmark and H6 re-analysis |

Predictions for the prospective log are registered by the end of Phase 1, so readouts during 2027 can be scored before the journal submission.

## Repo, preprint and venues

Three public outputs come from one repo: the TETHER system, the TETHER-Bench benchmark with its harness, and the preprint with every figure regenerable from a script.

**Repo layout**

```
tether_engine/
  chrono/    as-of data layer: masked Open Targets, AACT snapshots, dated ChEMBL, date-bounded literature
  tools/     MCP servers: cis-MR, direction of effect, PheWAS safety, perturbation, structure, base rates, literature
  agents/    model-agnostic orchestrator, specialists, critics
  ledger/    typed evidence schema, validated on write
  scorer/    calibrated model trained on rolling origins
  bench/     pairs, labels, splits, canaries, contamination probes
  harness/   adapters for Virtual Biotech, Biomni, OriGene, bare LLM
  eval/      metrics, statistics, figure scripts
  cases/     B7-H3, OSMR and trial-feature re-analysis
  prereg/    OSF analysis plan; hashes of locked predictions
  paper/     manuscript source
  docker/    container recipes (Docker and Apptainer)
  tests/     tool unit tests and leakage tests
```

**Licenses.** Code under Apache-2.0. Benchmark labels under CC BY-SA 4.0, because ChEMBL-derived labels must stay share-alike. Each data source gets a data card with its own terms.

**Preprint outline**

1. Tooling audit of Virtual Biotech and the field (inventory and gaps).
2. TETHER-Bench: construction, label audit, leakage tests (canaries, contamination probe).
3. TETHER architecture.
4. Head-to-head: discrimination, calibration and cost against Virtual Biotech and baselines, including the low-literature stratum.
5. Ablations: computed causal genetics, ledger-plus-scorer versus LLM-stated probability, critics.
6. Expert panel and claim-level error audit.
7. Re-analysis of Virtual Biotech's single-cell trial findings (H6).
8. Published cases revisited, plus the prospective prediction log.

Working title: *Time-locked evaluation of agentic target assessment*.

**Venues, in order**

- **Preprint:** bioRxiv, linked to the OSF pre-registration and a Zenodo DOI for code and data.
- **Benchmark paper:** NeurIPS Datasets and Benchmarks track (deadline usually late spring).
- **Journal:** Nature Biotechnology (Analysis format) or Nature Methods first; Cell Systems or Nature Communications as fallbacks. The prospective log can carry a follow-up paper.

## Risks and mitigations

The biggest risk is too few decisive post-cutoff outcomes to separate two good systems; the plan treats that as a gate, not a surprise.

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Too few decisive post-cutoff pairs for H1 | High | Measure in Phase 0; add Phase 1→2 transitions and matched pairs (T2) for power; extend the label freeze; lean on rolling-origin results for the scorer |
| TETHER does not beat Virtual Biotech | Medium | Pre-registration makes a null publishable; the benchmark, leakage tests and H6 re-analysis stand alone |
| Pretraining leakage inflates both systems | High | Model cutoff before T0; contamination probe; report with and without known pairs |
| Masking breaks Virtual Biotech or changes its behavior | Medium | Keep the 25.09 schema; run its own test suite on masked data; share the harness with its authors |
| Label noise in trial outcomes | Medium | Combine sources; double-annotate 200; sensitivity analysis excluding ambiguous multi-arm trials |
| Cost overrun | Medium | Hard per-run budget caps; credits; smaller repeat-seed subset |
| Data access terms (UKB-PPP, deCODE, Alvessa, OriGene) | Medium | Use only summary statistics with public terms; reimplement patterns instead of copying non-commercial code |
| Moving target: Virtual Biotech updates | Medium | Pin commit `71f9da6`; report later versions as a secondary run |
| Perceived as adversarial | Low–medium | Frame as evaluation and extension; credit its assets; offer co-review before posting |

## Sources

**Code inspected**

- [TheVirtualBiotech](https://github.com/harrisongzhang/TheVirtualBiotech), commit `71f9da6` (16 Sep 2026): MCP servers, agent registry, prompts, provenance and verification modules, trial-label and linkage datasets
- [open-targets-platform-mcp](https://github.com/opentargets/open-targets-platform-mcp)
- [OriGene](https://github.com/GENTEL-lab/OriGene) · [alvessa\_agent](https://github.com/ksenia007/alvessa_agent) · [MRAgent](https://github.com/xuwei1997/MRAgent) · [DeepRare](https://github.com/magic-ai4med/DeepRare)

**Papers and pages opened**

- [The Virtual Biotech, bioRxiv](https://www.biorxiv.org/content/10.64898/2026.02.23.707551v1.full)
- [Retrieve to Explain, arXiv v4](https://arxiv.org/html/2402.04068v4)
- [TargetBench 1.0 and TargetPro, bioRxiv](https://www.biorxiv.org/content/10.1101/2025.08.06.668866.full.pdf)
- [CTO clinical trial outcome benchmark, arXiv](https://arxiv.org/html/2406.10292v3)
- [Open Targets evidence documentation (direction of effect)](https://platform-docs.opentargets.org/evidence)
- [UKB-PPP download documentation](https://ukbppp-dl.readthedocs.io)
- [AACT download page](https://aact.ctti-clinicaltrials.org/download)
- [Biomni status report](https://www.labmanager.com/biomedical-ai-agent-connects-more-than-150-research-tools-35884)
- [Pham and Hy, Function–Evidence–Validation framework](https://arxiv.org/abs/2607.27556)
- [Merck and Daiichi Sankyo DXd ADC collaboration, October 2023](https://www.merck.com/news/daiichi-sankyo-and-merck-announce-global-development-and-commercialization-collaboration-for-three-daiichi-sankyo-dxd-adcs/)
- [Previous review: Agentic Target-Evaluation Frameworks](https://claude.ai/code/artifact/b42edb2a-b5a4-4f10-b26d-f91074355491)

Public datasets named in the gap table (FinnGen, Pan-UKB, Genebass, BioGRID ORCS, LINCS, CysDB and others) are cited from prior knowledge; their current terms are confirmed in Phase 0.
