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

## Original candidate universe and data gaps

The number 19,176 is established; the authoritative ordered IDs, ontology release,
aliases and complete membership are **not established**. The README lists
evaluation columns, not a candidate-vocabulary manifest. Initial web-reader tree
requests failed, but the official GitHub API follow-up below succeeded and pinned
both the default branch and the published release. Their complete recursive
trees contain no separate candidate-vocabulary file. No dataset payload was
downloaded or parsed, so this does not determine whether the union of TSV target
strings happens to cover every original candidate; that union is not documented
as an authoritative vocabulary.

The ACL page's retrieved HTML exposes the paper PDF but no supplementary-asset
link. The README links an official Zenodo release record containing one
repository ZIP attachment and no separately listed vocabulary attachment.
The ZIP was not downloaded. These checks establish the contents of the examined
repository trees and attachment listings, not universal absence of a candidate
file elsewhere.
[ACL publication record](https://aclanthology.org/2025.acl-long.167/).

Candidate reconstruction from the union of evaluation labels is not automatically
valid: it can omit candidates that have no sampled query. Current HGNC/Ensembl
protein-coding lists can add, merge or retire entries and are not an equivalent
universe. Exact published-universe reproduction requires the original vocabulary
or a versioned mapping proven equal to it. That is a comparability limitation,
not an additional hard requirement for the prospective TETHER condition below.
Preserve original strings alongside
stable IDs; report ambiguous aliases, duplicate mappings, one-to-many mappings,
unresolved labels and candidates with no eligible evidence. Missing candidates
must remain scheduled; don't erase them from rank denominators.

**Scope correction after independent review:** the authoritative SC08 plan and
its parent comparison report require a **fixed candidate universe, qualified
identifiers, a declared corpus and native masked-gene ranking metrics**. They do
not require recovering the authors' exact ontology or reproducing proprietary
weights. The earlier wording in this note incorrectly promoted exact-universe
reproduction into a completion gate. A complete, independently sourced public
human protein-coding universe is an eligible prospective condition if its release,
membership and mapping policy are frozen independently of evaluation labels.
This is not a reference-label union, target-only shortlist or top-k substitute.
Keep every candidate, including those without collected evidence, and every
released scheduled query. Report changed-universe/corpus/model conditions plainly;
no claim of exact published-score comparability follows.

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
2. Qualify and freeze a complete public human protein-coding universe and mapping
   provenance at a declared identifier-release date. Prefer the original universe
   if its membership can be established, but do not make unavailable author
   assets an invented prerequisite. Preserve original names, mapping ambiguity
   and all candidates. Missing, ambiguous or out-of-universe reference targets
   remain explicit in full-schedule accounting; never fabricate an ordinal rank.
   Native rank metrics need their actual evaluable denominators, alongside
   separately labelled all-scheduled success/failure measures. Do not tune
   membership after inspecting reference labels or candidate scores.
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
   Report comparisons to literature values as differing universe/model/corpus conditions,
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

Using the authors' documented counts as a sizing scenario, the two ranking families imply
`(44,362 + 60,839) * 19,176 = 2,017,334,376` candidate scores. This is a streaming/scalable ranker
problem, not a suitable separate Qwen generation call for each candidate. Recompute
the full budget from the qualified public universe before freezing production.
Native 300 GB index residency does not fit 32 GB host RAM. Sharded exact search
could preserve a score definition with higher I/O, but needs measured throughput
and proof of identical rankings. A modern alternative encoder changes the model
condition. No public weights means the small native network sizes alone do not
make original-model inference available.

Upstream metadata now reports 21,376,819 bytes across the four TSV blobs and a
7,576,090-byte Zenodo repository ZIP. These are declared upstream sizes, not
locally verified dataset payloads or measured transfer use. Public-corpus size,
index size, full-family runtime and usable author-checkpoint access remain
unestablished; do not infer them from available disk space.
No expensive benchmark should start until a no-label performance qualification
produces an extrapolated complete-family budget with explicit failure handling.

## Official metadata follow-up: 6 November 2026, 22:28-22:31 UTC

Read-only GitHub API access succeeded using the installed CLI after the initial
sandbox connection failed. Only repository/ref/commit/tree/release metadata,
the 3,518-byte README, Zenodo record JSON and ACL landing-page HTML were retained.
No TSV, ZIP, model, paper PDF or dataset record was downloaded; no experiment ran.

| Identity | Verified upstream value |
|---|---|
| Repository | `BenevolentAI/r2e-evaluation-data` |
| Default branch | `main` |
| Immutable default-branch commit | `55dbe0390423cba052661b58340a32fb7536d10d` |
| Default-branch tree | `6fb98e740cd28053ebda49ecd363767fd1a91ac7` |
| Published release | `v1.0.0`; the single returned release has zero uploaded assets |
| Immutable release commit | `54a74aaa5492a70e4fe0dcec9408cd0c46827c82` |
| Release tree | `db06d650e2513e057d41ddc5cf56aa3393b92e46` |
| Tree completeness | Both official recursive responses report `truncated: false` |
| Zenodo concept / version | `10.5281/zenodo.12088286` resolves to version `10.5281/zenodo.12088287` |

Both trees contain exactly six files: `LICENSE`, `README.md` and the four TSVs
below, with one `datasets/` directory. The two revisions have identical TSV and
license Git blob IDs; their README differs because the newer commit adds the
Zenodo DOI. The complete tree and release results can be reviewed through the
[official immutable tree API](https://api.github.com/repos/BenevolentAI/r2e-evaluation-data/git/trees/6fb98e740cd28053ebda49ecd363767fd1a91ac7?recursive=1)
and [published release](https://github.com/BenevolentAI/r2e-evaluation-data/releases/tag/v1.0.0).

| Dataset path beneath `datasets/` | GitHub-declared blob bytes |
|---|---:|
| `heldout_biomedical_literature_test.tsv` | 9,705,190 |
| `heldout_biomedical_literature_validation.tsv` | 3,142,230 |
| `gene_description_facts.tsv` | 7,897,809 |
| `clinical_trial_outcomes.tsv` | 631,590 |

The [official Zenodo record](https://zenodo.org/records/12088287) lists only
`BenevolentAI/r2e-evaluation-data-v1.0.0.zip`, with declared size 7,576,090 bytes
and MD5 `627d1cd0a1dd0f4d462433474cf1c6e0`, and identifies the GitHub `v1.0.0`
tree as its related software. This is attachment metadata, not verification of
the archive bytes or internal contents. The repository README provides no
additional candidate-list or ontology-version link.

**Consequence:** public access to the evaluation-release metadata is established;
the exact 19,176-member author candidate universe remains unresolved. Author
weights and proprietary evidence still limit exact reproduction of the authors'
model, but their absence does not itself block development of a declared TETHER
ranker. That ranker still needs its own proven full candidate universe and qualified public
corpus to complete the planned full-universe evaluation. Reading the four TSVs
and checking label coverage is a future preparation step, not permission to
equate their label union with the original universe.

Raw metadata, decoded README and SHA-256 proofs are retained under
`data/cache/sc08-r2e-public-metadata-20261106T222856643824Z/`.
Its `SUMMARY.json` SHA-256 is
`14295668718ee55db774ac551307a223016903aaf8b9f156e6ffeb651624475b`.
The summary binds 15 metadata/manifest files (85,988 bytes), including both
recursive trees, the release record, Zenodo listing and ACL HTML. Original Git
blob identities are preserved separately from locally calculated SHA-256 hashes;
none is presented as a verified TSV payload hash. The unsuccessful first API
attempt is retained in its own timestamped cache directory.

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
not a global filesystem absence proof. Upstream pages and the metadata follow-up
above were read; no full TSV, candidate list, source corpus or model bytes were
inspected. The metadata-access gate is resolved; the candidate-universe, corpus,
execution and scientific-validation gates remain pending. SC08 remains inactive.
