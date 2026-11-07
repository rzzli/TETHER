# TETHER: Source Reporting and Scoped Verification for Therapeutic Evidence

Working research draft. Presentation revised 6 November 2026 from the corrected 2 November manuscript. The study results and historical software qualifications below belong to the archived execution checkpoint; this edition adds no experiment or scientific validation. Author identities, affiliations, correspondence, funding, conflicts, contributions and author acceptance remain pending. This draft is not ready for submission.

TETHER expands to Target Evidence Tracking Harness for Evaluation and Reproducibility. Historical execution used the code retained in the [archival checkpoint](https://github.com/rzzli/TETHER/tree/tether-pre-namespace-migration-20261106). The current namespace migration does not change the reported outcomes, identifiers, code commitments or costs, and does not show that the new software reproduced the study.

## Abstract

Biomedical agent reports can preserve a citation while changing a number, importing later information or concealing an unavailable field. We present TETHER, a versioned evidence-workflow implementation, and a bounded technical study of literal source reporting. The study tests source fidelity and admission policy, rather than therapeutic judgment. Before execution, we fixed twelve units selected by identity from archived Open Targets 25.09 data, source-only generation inputs, separately reconstructed references, an all-output schedule and a descriptive analysis. Each unit requests eleven identity fields and four native measurement fields; forty of forty-eight measurement slots are populated. A deterministic literal assembler produces verified exact reports in twelve of twelve units and completes every answerable measurement group at the frozen 60%, 80% and 100% thresholds. The 80% and 100% criteria are mathematically identical for all twelve native units, so they are not separate robustness evidence. An always-abstain control completes zero of twelve. In fourteen exposed constructed scenarios, the full policy admits none of ten deliberately invalid reports and rejects none of four technically valid reports. Removing the study-specific eligibility wrapper admits two invalid scenarios; retaining only byte anchoring and output-schema checks admits seven. All thirty-eight outputs and ninety policy decisions are retained. Production takes 203.828 seconds, of which 97.0485% is source verification, followed by a separate 7.125-second source-inclusive audit. Earlier local generator probes failed their declared contracts and remain negative development evidence; no audit-stage model call occurred. The separately qualified post-study TETHER 0.5.0 release includes scoped verification, child supervision and artifact-specific admission; those guarantees are not attributed to the frozen experiment. The evidence supports reconstructable reporting on this selected set, not clinical accuracy, causal genetic interpretation, independent-study generalization, model superiority or provider authenticity. Numerical prediction features remain empty and clinical probabilities null.

## 1. Introduction

Therapeutic assessment combines sources with different release dates, identifiers, biological contexts and permissions. A report can be faithful to its retained bytes yet use an ineligible source or convey an unsupported conclusion. A missing measurement is also different from an absent biological effect. An auditable workflow therefore needs to distinguish byte integrity, mechanical consistency and scientific validity.

Biomedical agents already access domain tools and coordinate complex tasks. GeneGPT uses genomic tools [1]; Biomni reports broad biomedical workflow execution [2]; The Virtual Biotech organizes agents around therapeutic-development functions [3]. Existing approaches also evaluate evidence support. Alvessa checks generated statements against retrieved records and exercises corruption controls [4]. ALCE separates answer and citation quality [5], ARES evaluates retrieval-augmented systems with learned judges and human calibration [6], and biomedical quotation assessment distinguishes quotations from supported interpretation [7]. Structured deterministic grading and process-level evaluation are represented by TxBench-PP [8] and BiomniBench [9]. TETHER does not establish priority for any of these individual ideas.

Our narrower question is whether a local implementation can preserve a declared source-reporting contract through source selection, normalization, generation, reference construction, scoring and retained execution records. The implemented contract treats source availability, hypothesis scope, evaluator ancestry and exact field bindings as first-class constraints. We evaluate native-field copying and deliberately designed failures; we do not evaluate target ranking, experiment design, mechanism inference or therapeutic recommendations.

The contribution is an inspectable combination of versioned evidence admission, immutable source-bound records, explicit missingness, separate generation and evaluation roles, durable execution accounting and source-inclusive replay. Its empirical support is a small technical feasibility study and a negative model-development result. The perfect literal baseline is an expected ceiling for a copying task. It is evidence that this reporting path works on the selected inputs, not evidence of biomedical reasoning or a general advantage over other agents.

## 2. Implementation and threat model

The frozen study implementation and its later software releases are distinct objects. Sections 3–4 report the unchanged experiment and its separate source auditor. Historical TETHER facade releases 0.4.1, 0.4.2 and 0.5.0 were qualified after that study; their additional checks and execution limits are described explicitly below and in Supplement S10. No later software test upgrades an earlier run's guarantee.

### 2.1 Evidence, time and hypothesis scope

TETHER separates cases, source snapshots, evidence packets, input-lineage nodes and execution artifacts. The default Python runtime has no third-party dependencies; actual-format Parquet ingestion uses the optional pinned PyArrow 21.0.0 dependency. Version-two evidence is copied and recursively frozen on admission. Ledger commitments are checked against admitted canonical fingerprints. Features bind to a hypothesis fingerprint covering canonical target and indication identifiers, namespace versions, intended action, modality and tissue. Raw observations can remain contextual when a numerical feature is inapplicable.

Information availability is separate from computation time. A result newly computed from eligible older inputs can qualify; an ancestor containing later information or an evaluation-only artifact cannot. Mapping and annotation parents belong in the same eligibility graph. Public download dates provide present-day upper bounds on observed availability, not proof of historical first availability. Null dates or unresolved source context are not silently supplied from a newer release. The present experiment uses a contemporary cutoff and does not establish a historically uncontaminated clinical forecast.

The implementation checks declared identifiers, roles, dates, hashes and source contents under trusted local configuration. It does not authenticate a provider's original assertion, defend against a hostile administrator, prove correctness of supplied metadata or provide an operating-system security sandbox. A signed provider provenance chain is outside the study. Temporal checks are only as informative as the retained source metadata.

### 2.2 Durable execution and verification

Output directories are reserved before dispatch. Journals preserve attempts, reservations, terminal results and accounting; receipt hashes bind finalized outputs. Measured usage is distinguished from conservative reservations. Recovery inspects retained attempts rather than automatically repeating a potentially billed call. Byte verification and source/semantic replay have separate dispositions; neither is labeled scientific validation. Archived version-one runs retain their original, more limited verification guarantees.

Post-study adversarial review found that the legacy version-two verifier did not reconstruct all coverage terminal states, review-selection versus committed-record relationships, or dossier prose. An internally consistent receipt therefore did not prove those properties. Direct legacy APIs, including compatibility aliases, retain that earlier scope. From TETHER 0.4.1, the canonical CLI additionally reconstructs category states, review/commit consistency, bounded-request membership, known terminal dispositions and deterministic dossier rendering. These checks concern declared inputs and relationships; they cannot reveal undeclared real-world ancestry, establish custom exception-class inheritance from a serialized name, or certify every scientific statement.

Verification must retain its interface/version, source binding and external anchor. Engine `--outputs-only` verification checks archived fingerprints without rereading current originals; a TETHER outer run requires source-inclusive verification and rejects that flag. An independently retained original receipt hash is needed to detect replacement of an entire self-consistent artifact tree. Historical outer runs require the matching launcher source and version.

For the paper experiment, a separately frozen runner records all scheduled outputs, guard results, decisions and resource checkpoints. It forbids automatic retries and retains failures. A separate auditor reconstructs native facts from original source rows, rechecks the controls and reconciles the complete schedule. This audit uses a distinct projection implementation rather than treating the producer's expected values as its oracle. Authoring and audit agents are software collaborators, not external expert adjudicators or statistically independent judges.

### 2.3 Typed reporting and scoring

A report fact contains a stable fact identifier, typed value, unit, source binding and unknown reason. Bindings identify the full source file hash, release, physical row locator and field. Task identity includes hypothesis scope. Booleans cannot impersonate numerical measurements. Native null, a field absent from schema and a native empty value have different reasons. Incomplete collection cannot support a biological absence statement.

The source compiler reconstructs expected facts from originals. Generation receives source-only rows and value-free fact bindings, without expected-reference values. References and evaluation artifacts remain evaluator-only. In-process verified objects are immutable; serialized results acquire their guarantees through replay, not by trusting their own stored status. This is procedural and programmatic isolation, not proof of independent model errors or a hostile-process barrier.

### 2.4 Archived post-study software qualifications

This section describes historical facade releases in the archival checkpoint. The new TETHER engine 0.4.0 and facade 0.6.0 are a separate namespace migration under implementation; this paper assigns them no new qualification or scientific result.

The archived TETHER facade 0.5.0 retains the canonical verification additions and the child supervision introduced in 0.4.2. The locally qualified Windows CLI applies an absolute deadline and a combined stdout/stderr cap to its owned child, with retained failure/accounting records and no automatic redispatch. It does not bound blocked operating-system process creation, contain descendants, or supervise in-process outer verification after the child returns. Arbitrary embedded multithreaded and POSIX execution are outside this qualification. Workflow budgets, bounded reads and child supervision are distinct limits.

The explicit schema-2 policy path in 0.5.0 checks exact artifact identity, use, release, temporal context and supplied parents before offline extractive execution. It archives controls and receipt copies, produces a restricted schema-1 compatibility projection, and rederives that projection against the actual engine inputs during verification. A projection alone is not authorization. Direct legacy APIs and schema-1 compatibility runs retain their earlier scope; model/replay/scorer use is unsupported by this policy path. Catalog collection and scientific statuses remain unchanged. These are separate local software qualifications, not a rerun of the paper experiment or evidence that its sources are scientifically sufficient.

## 3. Study design

### 3.1 Source frame and selection

We pinned Open Targets 25.09 evidence, credible-set, target and disease files [10] and the locally downloaded HGNC normalization snapshot dated 10 October 2026 [11]. The HGNC date is a retained acquisition designation, not a provider-certified annotation release. The frozen frame contains 137 original files totaling 2,866,248,239 bytes: 100 GWAS evidence files, 25 credible-set files, ten target files, one disease file and one HGNC file. All source bytes and download receipts were verified. The complete credible-set input contains 2,862,043 physical rows.

The registry enumerates 1,753,850 physical GWAS evidence rows. Its fixed identity, temporal, mapping and eligibility rules retain 1,681,738 rows and exclude 72,112; individual exclusion reasons can overlap. A deterministic identity-only rank over target, disease and locus selects twelve units. Nine previously used target symbols are excluded. Selection does not rank numerical values, source answerability or candidate performance. Each retained unit has one exact locus-identifier match in the complete credible-set table. A locus match is a technical join and does not establish shared study, cohort, allele orientation or biological mechanism. Cross-source variant-identifier agreement is also unresolved: this is a locus-only match, not a qualified composite study-and-variant match.

Broader prior project exposure is unknown for all twelve selected units. They are not certified fresh cases or twelve independent studies. One repeated disease-identifier group is recorded; source-study and cohort dependence remain unresolved. After execution their identities and results are exposed development material. We preserve the pre-run exposure register rather than rewriting it with hindsight.

The rank is ascending SHA-256 of the UTF-8 string seed|release|targetId|diseaseId|studyLocusId, with seed preprint-p05-deterministic-v1 and release 25.09. Lexical target, disease, locus and release fields break hash ties. Missing, conflicting or blocked selected units retain their position and disposition; they are not replaced or reranked to improve answerability or results.

### 3.2 Inputs and independent references

Each unit requests fifteen fields across its original GWAS and matched credible-set rows: eleven identity/linkage fields and four measurement fields. The measurement components are beta, standard error, p-value mantissa and p-value exponent, all in one declared measurement group per unit. We report these native components without calculating a p-value, assigning effect units, interpreting direction or converting provider scores into support weights. Sample size and other context can be retained without becoming graded facts.

These are reporting components, not independent biological observations. The p-value mantissa and exponent encode one p-value, and beta and standard error describe related properties of an estimate. Identity fields account for most requested slots. Equal weighting is a declared reporting contract, not a measure of independent evidence or clinical informativeness.

Source-only input packets were sealed before reference construction. A separate source-only branch rebuilt the references from eligible originals, without generation outputs, human responses or prior answer-aware derivatives. An independent audit then directly checked all 180 requested facts against 24 distinct original rows. The reference producer and its own replay share algorithms; the additional direct-projection audit is the separate implementation check. These references establish native field fidelity, not adjudicated biomedical truth.

### 3.3 Arms, policies and constructed scenarios

The two native arms are a deterministic literal assembler and an always-abstain control. The assembler reads only the generation packet and copies each requested native field with its binding and missingness reason. The abstention arm emits no assertions. No model is run on these twelve units. Native literal outputs receive three policy projections; native abstentions receive the full policy only. Fourteen constructed generic-JSON scenarios receive all three policies. The resulting schedule contains 38 distinct outputs and 90 policy decisions.

The full policy requires five guards: G0 retained-byte/hash anchoring; G1 source-role and ancestor admissibility; G2 the P05 mapping, temporal and inventory wrapper; G3 the base source compiler; and G4 complete exact reporting with output-schema checks. WITHOUT_WRAPPER omits only G2, preserving the base guards. WIRE_ONLY requires G0 and the G4 schema check. These policies are projections over retained guard outcomes, not independent full executions or recommended scientific methods. Source admission through G0-G3 and report exactness at G4 are separate outcomes.

The constructed set has four technically valid and ten deliberately invalid scenarios. Faults cover changed source bytes, evaluator-only ancestry, future release metadata, incomplete inventory, altered number, wrong locator, wrong unknown reason, duplicate JSON keys, Boolean measurement and oversized output. The valid controls include explicit missingness, multiple groups and an entirely unavailable measurement group. C02 tests an absent field through the generic JSON/core path; it does not qualify native absent-column handling, because the unchanged P05 Parquet scanner requires the declared measurement columns. One valid control copies a finite negative standard error: its technical fidelity is correct while its scientific interpretation is unqualified. Controls were exposed and qualified before the study. Their results measure behavior on designed examples, not sensitivity, specificity or natural error prevalence.

### 3.4 Endpoints, accounting and resources

For each answerable record/family/group, coverage is the fraction of exact matched non-null components. Family coverage averages these fractions equally across answerable groups. Native nulls are excluded from reporting denominators and separately counted. An all-unknown group has undefined coverage, not zero or automatic success. Completion requires an eligible answered/partial report, correct collection status, no mechanically identified critical errors and at least 80% primary measurement coverage. Frozen sensitivities use 60% and 100%. Exact-report verification requires status answered and exactly one correct emission of every declared fact, including correct unknown reasons. A partial report may satisfy coverage but cannot be exact under this stricter rule.

Every native measurement group contains two, three or four answerable components. For each possible size n, ceil(0.8n) = n; therefore the 80% and 100% criteria require exactly the same number of correct components for every attainable native outcome in all twelve units. Their identical results are structural redundancy, not independent sensitivity evidence. The prespecified thresholds and results are retained. The 60% criterion can differ for groups of three or four, although the literal reports complete every component at all thresholds.

The primary accounting includes every scheduled output and decision. Failed, malformed, interrupted, timed-out or unexecuted cells cannot disappear from a favorable subset. A core-scored subset is secondary and explicitly labeled. We use descriptive counts and paired decision tables only. We report no confidence interval, power calculation, significance test or independent-study inference for this selected set.

The execution protocol was frozen in a committed READY file before native output construction. It binds runtime and extra code pins, sources, receipts, task and reference seals, denominator register, fictional qualification, schedule, budgets and analyzer. Limits include 3,600 seconds for execution and a separate 3,600 seconds for audit, 2 GiB checkpoint process memory and 256 MiB study output. Logical completed hash reads, row enumerations, CPU, wall time and memory checkpoints are retained. Repeated hash reads are logical work, not measured physical disk traffic. No new model call, network transfer or provider charge occurs in this experiment.

![Source-to-report flow and the separate evaluation branch. Shared generation and guard projections are not independent executions.](results/figures/figure1-flow.pdf)

## 4. Results

### 4.1 Native availability and reporting

All twelve native units finalize. Of 180 requested facts, 148 are populated and 32 are native nulls: 108/132 identity slots and 40/48 measurement slots are populated. There are no missing-schema or native-empty measurement slots in this set. One unit has two answerable measurement components, six have three, and five have four. Beta is null in one unit and standard error in seven. Sample size is missing in ten units but is not a graded measurement component.

The literal assembler emits all fifteen requested facts per unit with exact bindings and correct unknown reasons. It achieves verified exact reporting and measurement completion in 12/12 units at each frozen threshold. The abstention control completes 0/12, emitting no fact assertions and incurring no factual mismatch errors. Abstention therefore provides error avoidance without useful completion. These contrasts establish the expected copy ceiling and the explicit coverage cost of abstention on this task.

| Native outcome | Literal assembler | Always abstain |
| --- | --- | --- |
| Scheduled outputs | 12 | 12 |
| Verified exact reports | 12/12 | 0/12 |
| Measurement completion at 80% | 12/12 | 0/12 |
| Completion at 60% and 100% | 12/12 at both | 0/12 at both |
| Mechanically identified factual errors | 0 | 0 |
| Emitted fact entries | 180, including 32 unknowns | 0 |

Source availability of 40/48 measurement slots is distinct from 100% reporting coverage over the answerable components. Missing fields remain unavailable rather than being supplied from another source or inferred from related measurements.

![Native source availability, separate from reporting coverage. Forty of forty-eight measurement slots are populated.](results/figures/figure2-availability.pdf)

### 4.2 Constructed policy contrasts and full accounting

The full policy admits 0/10 invalid scenarios. WITHOUT_WRAPPER admits 2/10: future-release metadata and incomplete inventory. WIRE_ONLY admits 7/10, demonstrating that a well-formed retained report can remain unsupported under stronger requirements. All three policies reject 0/4 technically valid controls. The all-unknown measurement control remains an exact report with undefined measurement coverage and does not count as completed. All 42 constructed policy decisions are retained.

| Constructed outcome | FULL | WITHOUT_WRAPPER | WIRE_ONLY |
| --- | --- | --- | --- |
| Invalid scenarios admitted | 0/10 | 2/10 | 7/10 |
| Technically valid scenarios rejected | 0/4 | 0/4 | 0/4 |

The 38-output schedule has 36 returned outputs and two deliberately malformed outputs: duplicate JSON keys and an oversized report. All 90 decisions reach a terminal disposition, with 57 admissions and 33 rejections. The 35 genuinely core-scored outputs are a secondary subset; they are not substituted for the complete schedule. Pairwise constructed-policy discordance is 2/14 for FULL versus WITHOUT_WRAPPER, 7/14 for FULL versus WIRE_ONLY and 5/14 for WITHOUT_WRAPPER versus WIRE_ONLY. These paired differences concern fixed designed controls, not independent clinical observations.

![Invalid admissions under the three policies. All fourteen scenarios were constructed and exposed before the study.](results/figures/figure3-controls.pdf)

### 4.3 Verification and resource use

The separate source-inclusive auditor passes 2,414 checks with no unresolved finding. It independently reconstructs original-row projections, constructed controls, policy decisions, source proofs and all-output accounting. The frozen analyzer runs once against the pinned ledger and audit. A separate presentation audit passes 351 checks over quantities, tables, captions, data and figure geometry. A fresh-directory local rebuild reproduces all 39 result-bundle files byte-for-byte. Check counts describe implementation verification effort; they are not biomedical sample sizes or an estimate of general correctness.

Production takes 203.828 seconds wall time and 198.984 seconds CPU, with checkpoint-observed process-lifetime peak memory 305,827,840 bytes. The 197.812-second source-verification wrapper is included within production, not an additional phase to sum. The separate audit takes 7.125 seconds and peaks at 333,893,632 bytes. Completed logical hash reads total 140,452,303,784 bytes in production and 2,897,268,566 in the audit; the two phases enumerate source rows twice in total. Physical I/O, partial failed-read bytes and platform costs are unmeasured. Provider spending is $0, which is not a claim of zero overall cost.

Source verification accounts for 97.0485% of production wall time (197.812/203.828). Production's completed logical hash bytes equal 49.0021 source-frame equivalents (140,452,303,784/2,866,248,239). These are a nested wall-time share and a logical-byte ratio, respectively. They measure neither physical disk transfers nor agent-only inference cost. The repeated verification work dominates the reported production time; no performance improvement is inferred from a later software release.

Reference construction is a separate preparatory phase: 342.750 seconds, with producer memory unmeasured. Its later audit memory does not recover that missing measurement. Native literal/abstain generation shares a source-packet read per unit, and policy decisions reuse guard outcomes. We do not attribute total process memory to an individual arm or treat projections as independent runtime trials.

### 4.4 Negative model development, separate from the native study

Before narrowing scope, a frozen twelve-cell development comparison used two literature contexts with deterministic, plain local-model and proposal/check arms plus a controlled missing-input condition. Five actual local-model calls yielded four malformed responses and one output-limit failure; none satisfied the strict report contract. Neither model arm completed either clean context, while the literal baseline completed 2/2. The model was Qwen2.5-14B-Instruct in pinned Q4_K_M GGUF form, served through an ordinary completion interface. Grammar-constrained generation was not used in this probe.

The five dispatches were three plain calls and two proposal calls; there were zero audit-stage dispatches. Failure before that stage cannot measure critic efficacy. The configured output cap was 2,048 tokens, but output-byte estimates did not establish that an exact valid serialization fit that token cap. A future generator study would need the actual tokenizer, framing and escaping to establish feasibility under its unchanged resource contract before execution. This requirement does not authorize retries of the closed cells.

A subsequent predeclared two-call fictional conformance probe passed its two-fact control and failed its eight-fact control on the value/unknown-reason rule. The frozen stop rule closed this model branch. No further prompt retries, model scaling or model evaluation on the twelve native units followed. These are exposed development observations under one model/interface/configuration. They do not identify whether task design, prompting, serialization, model capacity or their interaction caused failure, and they do not establish broad LLM inability. Earlier zero-call setup failures are also retained.

## 5. Discussion

The study supports a limited engineering conclusion: selected native fields can be reported exactly while eligibility, source ancestry, missingness, failure and resource records remain replayable. Explicit policies make it possible to show which designed faults a weaker policy admits. Exact copying alone already reaches the task's ceiling, so adding an agent cannot demonstrate superior biomedical interpretation on this endpoint. The useful object is the inspectable reporting and verification contract, including its limits.

Prior work supplies substantial adjacent capabilities. The pinned Virtual Biotech implementation supports headless execution and explicitly distinguishes artifact integrity from evidence coverage [12]. Alvessa already verifies retrieved-record statements [4]. TxBench-PP addresses structured preclinical decisions [8], and BiomniBench reports process rubrics [9]; we do not inherit their task validity or judge calibration. Retrieve to Explain evaluates evidence-driven target prediction against different endpoints [13]. None was executed here. Missing feature assessments are not evidence of competitor deficiencies. Our bounded contribution is therefore an implementation and source-reporting feasibility result, with incremental utility and scientific value still to establish.

The missing context is substantive. Exact locus matches and literal beta/standard-error components do not establish compatible study identity, ancestry, genome build, allele orientation, units, intervention direction or causal effect. A reference assembled from a public database can faithfully reproduce an upstream error. The constructed finite negative standard-error example makes this distinction explicit. A clinical predictor, Mendelian-randomization analysis or therapeutic ranking would require additional data qualification and scientific validation before an outcome study.

A subsequent source-only feasibility checkpoint, Q03, considered exact direct-disease evidence composition for two targets. Its selected slice supported source-object membership and reuse reporting, while absent evidence-side study and variant IDs made the corresponding cross-table identity checks unassessable. This was a source-selected feasibility audit, not an extension of the frozen study, a holdout set or independent genetic support. A deterministic filter/join/set baseline fully answers the scoped contract, leaving no demonstrated model advantage on its required outputs. At that checkpoint, Q04 evaluation freezing and Q05 new-study execution remained unactivated, not completed. Supplement S11 records the limited result and its execution-history caveats.

## 6. Limitations

The twelve units were identity-ranked from a local archived subset, not randomly sampled from all biomedical evidence. Their prior exposure is unresolved, source-study independence is unqualified and the selected rows contain sufficient literal measurements. There is no certified holdout set, no generalization interval and no clinical outcome evaluation. Public-download timestamps do not establish historical availability. The missing Open Targets study input prevents upstream study-context verification.

The fourteen controls are known, designed and previously qualified. Passing them establishes only the exercised behavior; unmodeled corruptions, adversarial combinations and real-world error prevalence remain unmeasured. WIRE_ONLY and WITHOUT_WRAPPER are diagnostic projections, not complete alternative agents. Multiple decisions from one output and multiple components from one unit are dependent. The copying baseline is deliberately simple and its perfect performance is expected.

The later CLI counterexamples further limit any blanket semantic-verification claim. The frozen paper's separate original-row and schedule audit still supports its stated mechanical result; it does not imply that the legacy engine verified all coverage states or dossier assertions. Passing post-study regression tests qualifies only the named software paths and exercised conditions. It does not supply unseen-fault generalization or a new scientific sample.

Role separation, code pins and independent projection checks reduce identifiable implementation errors but do not provide an operating-system sandbox, cryptographic provider identity or independent scientific adjudication. AI agents assisted implementation, auditing, literature checking and writing. They are not external experts, and their agreement does not certify biomedical correctness. Historical bespoke responses and answer-aware descendants are excluded from this study rather than reused as references or labels.

The local model results are small negative development probes and cannot support model-family comparisons or a general workflow ranking. The source study uses no model. Full Virtual Biotech reproduction, clinical scoring, historical cohorts, MR, tasks T2-T5 and the H6 reanalysis remain separate uncompleted programmes. Wider project data gaps are not resolved by finishing this technical experiment.

The P06 study and its results and costs remain frozen: primary production took 203.828 seconds and its source audit took 7.125 seconds. A separately versioned, post-result P09 adapter has qualified installed, relocated reconstruction on Windows x64 with CPython 3.11.15 and PyArrow 21.0.0. The native replay used all 137 exact originals; the complete adapter reproduced 38 outputs and 90 decisions across twelve native units and fourteen constructed controls. Reconstruction took 289.938 seconds, and the separate source-inclusive independent audit passed 6,862 checks in 15.187 seconds. The minimal public catalog creates new reference fingerprints; historical equivalence removes only `method.catalog_sha256`. New G0 checks public protocol, code, input and output byte bindings under independently retained authority, without establishing publisher authenticity or verifying old private journals or sealed trees. Fresh exact-byte reacquisition of the 136 external Open Targets originals remains untested. This local technical qualification establishes neither scientific validity nor public availability; author facts remain deferred.

## 7. Availability and declarations

The current repository contains the implementation, this editable presentation, bibliography, supplementary methods and unchanged result tables/figures. Original protocols, failures, execution source, qualification records and release packets are preserved in the [archival checkpoint](https://github.com/rzzli/TETHER/tree/tether-pre-namespace-migration-20261106), not rewritten as records of the current implementation. At draft time, no public artifact deposit, permanent identifier or publication is claimed. A public release must use an explicit allowlist; original datasets, model weights, credentials, historical response archives and private or outcome-aware artifacts are not implicitly licensed by the repository's Apache-2.0 code license. The supplement identifies local reconstruction requirements and exact study anchors. Local file locations are implementation details, not public access guarantees.

AI assistance: Codex-hosted agents supported software development, source checking, technical auditing and manuscript preparation. The retained scientific report has no external-expert validation. Separate local-model probes and their failures are disclosed above. Platform-model identity, hidden compute and platform cost are not fully metered. No AI system is an author; human authors must verify and accept responsibility for the final text and disclosures.

Author names, affiliations, correspondence, contributions, funding, competing interests, acknowledgments and any required ethics/data-governance declarations require owner-confirmed facts. They are unresolved submission metadata, not requests for external scientific experts. No statement of absent funding, conflicts or oversight is inferred from missing information. No patients were recruited or clinical recommendations issued by this technical experiment.

## References

[1] Jin Q, Yang Y, Chen Q, Lu Z. GeneGPT: augmenting large language models with domain tools for improved access to biomedical information. Bioinformatics. 2024;40:btae075. https://doi.org/10.1093/bioinformatics/btae075

[2] Huang K, et al. Autonomous biomedical research with an artificial intelligence agent. Science. 2026;393:eadz4351. https://doi.org/10.1126/science.adz4351

[3] Zhang HG, Eckmann P, Miao J, Mahon AB, Zou J. The Virtual Biotech: A multi-agent AI framework for therapeutic discovery and development. Science. 2026;394:eaeg6779. https://doi.org/10.1126/science.aeg6779

[4] Sokolova K, et al. An Evidence-Grounded Research Assistant for Functional Genomics and Drug Target Assessment. bioRxiv. 2025. Preprint, version 1. https://doi.org/10.64898/2025.12.30.697073

[5] Gao T, Yen H, Yu J, Chen D. Enabling Large Language Models to Generate Text with Citations. EMNLP. 2023:6465-6488. https://doi.org/10.18653/v1/2023.emnlp-main.398

[6] Saad-Falcon J, Khattab O, Potts C, Zaharia M. ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. NAACL. 2024:338-354. https://doi.org/10.18653/v1/2024.naacl-long.20

[7] Windisch P, et al. Show Your Work: Verbatim Evidence Requirements and Automated Assessment of Large Language Models for Biomedical Text Processing of Trial Eligibility Criteria. Cureus. 2026;18:e108666. https://doi.org/10.7759/cureus.108666

[8] Le H, et al. TxBench-PP: Analyzing AI Agent Performance on Small-Molecule Preclinical Pharmacology. arXiv. 2026. Preprint, version 2. https://arxiv.org/abs/2606.19245v2

[9] Qu Y, et al. BiomniBench: Process-level Evaluation of LLM Agents for Real-world Biomedical Research. bioRxiv. 2026. Preprint, version 2; indexed primary metadata/abstract checked, direct full text inaccessible in this review. https://doi.org/10.64898/2026.05.12.724604

[10] Open Targets. Platform release 25.09, archived output. https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/output/

[11] HUGO Gene Nomenclature Committee. Archived data download documentation. https://www.genenames.org/download/archive/

[12] The Virtual Biotech contributors. Implementation revision 71f9da68c95c5ee0ef4c1d9b8f45f10693de022d. https://github.com/harrisongzhang/TheVirtualBiotech/tree/71f9da68c95c5ee0ef4c1d9b8f45f10693de022d

[13] Patel R, et al. Retrieve to Explain: Evidence-driven Predictions for Explainable Drug Target Identification. ACL. 2025:3328-3370. https://doi.org/10.18653/v1/2025.acl-long.167
