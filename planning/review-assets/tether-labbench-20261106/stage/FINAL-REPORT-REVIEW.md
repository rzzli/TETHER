# LitQA2 final report: independent reporting review

**Pass within the declared reporting scope.** The reviewed result document is
`planning/TETHER LitQA2 Native Evaluation Results 2026-11-06.md`, 15,605 bytes,
SHA-256 `95cf2839c0e6693a1506c9f2cfc496d0a47c2a4048cc51ee6be502316cc18305`.
No material reporting correction remains in that version. This is completion of
the declared measurement and its accounting checks, not scientific qualification
of the answerer, an independent biological review, or proof of clinical utility.

The retained check is [FINAL-REPORT-VALIDATION-01.json](FINAL-REPORT-VALIDATION-01.json),
SHA-256 `96580931cf685dcbc767dc40d84b8d5700f1d08b765cc766c649135f9ac8dda6`.
The [review script](validate_final_report.py) is a separate standard-library
implementation, SHA-256
`36746d37517f34643f8ede66568e6c540cba325d3eb7a3556a0ad8873163f102`.
It imports no production scorer, does not reopen original answer-key files,
and makes no model or network calls. It reads anchored aggregate/audit products
and already scored case outcomes; it does not repeat the full source/model audit
or the independently implemented answer-key reconstruction. Nine local report
links resolve. The initial helper's assumption of a top-level operational-audit
status was corrected to the actual separate collection/generation fields; the
[initial reader error](FINAL-REPORT-VALIDATOR-INITIAL-ERROR.txt) is retained.

## Counts and interpretation checked

| Claim | Check and result |
|---|---|
| Complete denominator | All 199 unique scored IDs exactly match the independent DOI audit's 199 IDs; all are produced and accepted. |
| Native performance | Both arms have 12/199 correct (6.03%), 21/199 substantive (10.55%), and 12/21 precision (57.14%). Recount and independently reconstructed aggregates agree. |
| Unsure versus false claims | 178 unsure plus 9 wrong substantive answers account for the 187 answer-key-incorrect admitted entries. They are not 187 substantive false claims. |
| Effect of admission | Every original candidate passed; there is no change in accuracy or coverage and no demonstrated incremental scientific accuracy benefit. A fixed-candidate filter cannot increase correct answers per scheduled question. |
| Annotated-source coverage | Independently summed 10/205 selected DOI pairs and 10/205 retained DOI pairs, across 10/199 hit questions. Some eligible text for 198 cases is a different and much weaker retrieval criterion. |
| Source instances | 538 retained article instances, 406 selected article instances, and 42 article instances missing metadata DOI reconcile. These are not independent cases. |
| Dependence | The 186 observed components sum to 199 questions, but neither unresolved aliases nor broader scientific dependence are excluded. No independent-sample interpretation or confidence interval is inferred. |
| Post hoc contingency | Independent join gives 10 hit questions: 6 correct, 2 wrong substantive, 2 unsure; 189 no-hit questions: 6 correct, 7 wrong substantive, 176 unsure. These exactly match the retained root join. |
| Analytical references | Chance expectations and always-unsure arithmetic are unexecuted references with distinct coverage; no invented runtimes, matched-treatment claim or significance claim is attached. |
| Failed fictional control | The same fictional item was answered incorrectly in two attempts under evolving implementation. The report preserves these failures and the prospective weak-baseline amendment rather than relabeling capability qualification. |

The primary evaluator seal, independent native reconstruction, native comparison,
DOI audit, DOI comparison, independent operational audit and completed resource
scope were checked against their supplied external hashes. The exact evaluation
case file is bound through the anchored evaluation seal. The post hoc root
contingency was independently recounted without importing its implementation.

## Corrections made during this review

Two narrow wording changes were requested and are now present in the reviewed
report:

1. Independent agreement is limited to per-question DOI-pair and question-hit
   counts. The independent DOI parser does not reproduce the broader alias graph
   or independently establish the primary scorer's 16-item resolved subset.
   Consequently 10/16 (62.5%) remains a selected, metadata-conditioned statistic;
   the all-annotation coverage is 10/205 (4.88%).
2. The post hoc source-answer association does not identify causal bottlenecks.
   Decisive-passage access and interpretation remain unmeasured candidate failure
   points. The run does not distinguish question difficulty, search, access,
   licensing, passage selection, prior knowledge or answer interpretation as
   causes of the observed outcomes.

The completed resource-scope link and anchor now refer to snapshot 02 rather than
the earlier snapshot taken while scoring was still running.

## Resource and efficiency limits retained

[RESOURCE-SCOPE-02.json](RESOURCE-SCOPE-02.json), SHA-256
`8c39c654b6711e4c03c3ab4b1a476f65ede8f7277f46a0d19b3df665122c5218`, preserves snapshot
01 and adds the completed scorer's measurements. Its [readable companion](RESOURCE-SCOPE-02.md)
has SHA-256 `fde7accbd8f4bcfce2a24f3687e9bb9e9cde22b0cad98d41a4394a679de52f82`.

- The generation usage is measured as 443,470 input and 34,279 output tokens,
  with 199 tokenizations, 199 generations, no unresolved usage and zero external
  provider charges. Electricity, depreciation and labour remain unmeasured.
- The 1,161.953-second generation figure is the supervised worker's duration.
  Parent resources were captured before unbounded finalization; total generation
  latency and finalization have no retained outer monotonic measurement. The
  approximately 29.4-minute filesystem chronology is not an attested stopwatch.
- The reported native-process peak is the maximum sampled OS process-lifetime
  peak working set, not incremental memory, a complete process-tree peak or GPU
  memory. Sampling can miss current-working-set spikes.
- The completed evaluator wrapper took 882.172 seconds and 817.953125 seconds
  of controller CPU. Its internal pre-publication elapsed field is 881.797
  seconds; the process-lifetime peak working set is 579,141,632 bytes. These
  cover source/model/session replay, scoring and reporting, not marginal admission.
- The evaluator's 9,112,208,256 unique verified model/runtime/receipt bytes,
  collection response-body bytes and sealed product bytes measure different
  quantities. None is a physical-I/O or wire-transfer total.
- Blind native reconstruction took 17.203 seconds with fewer obligations. It
  is not a policy-equivalent speed comparison against the complete evaluator.
- The 512 MiB read-allocation microprobe identifies a concrete efficiency issue
  but is not a profile of the parent process and assigns no fraction of measured
  runtime to that issue. Frozen source and original timings remain unchanged.

## Remaining scope limits

The raw arm already shares source collection, grammar, transport and TETHER
controls; it is not an end-to-end workflow without TETHER. The sourced local
route is also not the upstream tool-free condition. Public-task contamination
and prior knowledge are unknown. The input audit is a trusted-code hook rather
than an OS-level isolation proof. Source identity does not establish passage
entailment. The independent checks are separate AI-assisted implementations
within this project, not external human scientific adjudication.

The report accurately presents a reproducible weak-baseline measurement with
full scheduled accounting. It does not establish improved answer capability,
scientific judgment, clinical performance, or competitive superiority. No new
benchmark run, source modification, model call or reference-answer acquisition
was introduced by this review.
