# SC08 forward feasibility - not activation or an execution freeze

Read-only preparation on 6 November 2026 while SC04 is active. No dataset/model
acquisition, inference, installation, source-code or catalog change occurred.
**The public R2E task data do not currently establish an executable exact R2E
reproduction.** A declared TETHER ranker can be evaluated on the released task,
but the full candidate universe and eligible corpus must first be established.
Do not fill these gaps by silently narrowing the candidates or using the clinical
outcomes product as a different, easier benchmark.

## Verified upstream facts

R2E uses 19,176 protein-coding gene candidates and 160 million entity-linked
sentences, including paid Springer/Wiley/Elsevier full text. The authors explicitly
do not release proprietary training data, code or weights. Native ranking metrics
are MRR, mean rank, hits@10 and hits@200; Gene Description Facts uses per-gene macro
averaging. The literature test has 14,429/14,859/15,074 queries for 2020/2021/2022
(44,362 total); gene facts has 60,839. Clinical outcomes has 1,449 successes and
4,222 failures and uses AUROC. Literature training/retrieval precedes 2020;
updated retrieval precedes each query year. Clinical literature precedes 2005;
gene facts uses no temporal split. Native retrieval/reasoning uses 64 sentences
per candidate. Reported fast exact retrieval assumed about 300 GB index RAM.
These are paper-described facts, not locally verified record counts or measured
TETHER throughput. [Final paper and appendices](https://arxiv.org/html/2402.04068v4).

The public repository lists four TSVs: literature test, literature validation,
gene-description facts and clinical outcomes. Targets are `gene_name`, assigned
from Ensembl name or HGNC symbol, not stable Ensembl IDs. Literature includes
PubMed ID and test publication year. Facts/clinical products state CC BY-NC-SA
4.0; facts additionally derive from UniProt CC BY 4.0. Literature sentences are
credited to NLM. Clinical labels mean phase-II/III-to-approval progression, not
measured efficacy. Citeline permission covers the released subset, not its entire
database. [Official product schemas and terms](https://github.com/BenevolentAI/r2e-evaluation-data).

## Exact candidate universe and data gaps

The number 19,176 is established; the authoritative ordered IDs, ontology release,
aliases and complete membership are **not established**. The README lists
evaluation columns, not a candidate-vocabulary manifest. A repository root view
was accessible, but the recursive-tree API and nested listing/raw-license pages
failed in the web reader. Those failures do not prove authentication is required
or that the missing artifact does not exist. No immutable repository revision or
dataset bytes were acquired in this task.

The ACL landing page exposed no supplementary-asset link in its rendered text;
the paper points back to the public repository. This limited navigation result
does not establish that no supplementary candidate file exists. A later metadata
tree/attachment inspection must settle that before task preparation.
[ACL publication record](https://aclanthology.org/2025.acl-long.167/).

Candidate reconstruction from the union of evaluation labels is not automatically
valid: it can omit candidates that have no sampled query. Current HGNC/Ensembl
protein-coding lists can add, merge or retire entries and are not an equivalent
universe. Required evidence is the original vocabulary or a versioned mapping
whose membership is proven equal to it. Preserve original strings alongside
stable IDs; report ambiguous aliases, duplicate mappings, one-to-many mappings,
unresolved labels and candidates with no eligible evidence. Missing candidates
must remain scheduled; don't erase them from rank denominators.

Current catalog `r2e_outcomes` covers only the clinical comparison product and is
still planned/not parsed. It cannot stand in for the two ranking products, the
validation split or an evidence-corpus manifest. At activation, separate products
and role policies are needed, including evaluator-only target labels and explicit
rights. No catalog mutation is made by this note.

## Full-scope implementation route, conditional on inputs

The exact plan requires R2E target-side ranking with a fixed candidate universe,
qualified identifiers and a declared corpus. It does not promise access to the
proprietary R2E model. This allows a transparently named TETHER ranking condition;
it does not allow claiming published R2E model replication or quietly replacing
the task with pair classification.

1. Pin upstream revision/TSV hashes; inspect and enumerate all records in each
   promised ranking family. Recommend retaining **all literature-test and all
   gene-fact records**, with validation separate and no outcome-driven choice of
   the easier family. Confirm actual counts before freezing IDs.
2. Resolve the complete original candidate vocabulary and mapping provenance.
   If that cannot be obtained or proven, pause the exact-universe gate. A new
   universe can only be a separately authorized changed benchmark, not completion
   of this requirement.
3. Freeze a rights-qualified public evidence corpus and its lineage. Exclude query
   sentences and their source documents from retrieval where required, keep labels
   inaccessible during scoring, and prevent gene-description gold text or clinical
   outcomes from entering the corpus. Record publication versus first availability
   and model-training exposure separately. A modern Qwen model cannot establish
   historical prediction merely because retrieved evidence is old.
4. Build a ranker that scores every scheduled candidate. A scalable sparse/dense
   retrieval baseline can assign deterministic scores to no-match candidates,
   with predeclared tie handling. A restricted reranker may be a supplemental
   condition only if the full candidate ranking and tail policy remain explicit;
   top-k candidate recall does not replace full-universe MRR. Qualify synthetic
   ties, absent gold, aliases, duplicate names, empty evidence and interrupted
   shards against an independent metric reader before production.
5. Fit/select only on allowed validation inputs; freeze candidate order, corpus,
   scores, tie policy, source caps, output schema and all budgets before test
   answers. Compute native metrics by publication year, with gene-macro facts
   aggregation, and preserve operational failures in the scheduled denominator.
6. Retain raw query/candidate scores, source manifests, source chronology,
   ambiguity counts, coverage, measured resource use and independent reconstruction.
   Report comparisons to literature values as differing model/corpus conditions,
   not matched-data superiority. Clinical progression remains a separate endpoint.

The public-corpus route preserves task coverage but changes the original evidence
condition. It needs a source inventory; the existing ten T6 target packets and
LitQA paper collection are not genome-scale corpus substitutes. Original paid
full text, proprietary entity linking and trained model are unavailable in the
reviewed release. That is an actual exact-reproduction limitation. No credential
or manual-file requirement for the evaluation TSVs has been demonstrated, and no
external expert input is required or assumed.

A concrete public-source candidate is a date-filtered PMC Open Access collection
with article-level permitted reuse and stable sentence provenance, supplemented
by permitted PubMed abstracts. PMC explicitly distinguishes its OA subset from
all PMC text and specifies approved automated retrieval services. NLM hosting
does not make every incorporated abstract/article public domain. Such a corpus
must be sized and audited for all-candidate coverage; use it as a declared new
condition, without claiming coverage of the original proprietary corpus.
[PMC subset and services](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/),
[NCBI copyright policy](https://www.ncbi.nlm.nih.gov/home/about/policies/).

## Compute foreseeability

Using documented counts, the two ranking families imply
`(44,362 + 60,839) * 19,176 = 2,017,334,376` candidate scores. This is a streaming/scalable ranker
problem, not a suitable separate Qwen generation call for each candidate.
Native 300 GB index residency does not fit 32 GB host RAM. Sharded exact search
could preserve a score definition with higher I/O, but needs measured throughput
and proof of identical rankings. A modern alternative encoder changes the model
condition. No public weights means the small native network sizes alone do not
make original-model inference available.

Dataset transfer bytes, public-corpus size, index size, full-family runtime and
checkpoint access remain unknown; do not infer them from available disk space.
No expensive benchmark should start until a no-label performance qualification
produces an extrapolated complete-family budget with explicit failure handling.

## Retained local evidence

Fresh hashes on `2026-11-06T22:14:48.325269Z`, paths relative to
`D:\Projects\drug_target_agents`:

| Path | SHA-256 |
|---|---|
| `planning/TETHER Semantic Capability Execution Plan 2026-11-06.md` | `085ed3bb65c995db134946ad16773e25196f36933a800b7dfa4772c9da9ebbb7` |
| `data/catalog/sources.json` | `eafd955cad30dd36bd7417de165a508b1e891f90f42e2cc4bcb573043eaa65ac` |
| `reports/TETHER benchmark priorities and methods.md` | `90dc3f83d6f79e556fad4f5e18db64d2268764b587fb032890914db2c99c43c3` |
| `reports/TETHER benchmark comparison update 2026-11-06.md` | `480782a5ffbc9b70ac6ce4a9d165ca789ce9f80f156312b7c6e6a671a1aa0448` |

The bounded local checks listed in [SC07's note](SC07-FEASIBILITY-NOTE.md) found no
R2E-named direct child in the inspected raw/cache/benchmark/model roots. This is
not a global filesystem absence proof. Upstream pages were read; no full TSV,
candidate list, source corpus or model bytes were inspected. All gates above
remain pending, and SC08 remains inactive.
