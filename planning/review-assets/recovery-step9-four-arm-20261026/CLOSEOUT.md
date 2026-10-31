# 0.3.6 correction and acceptance report

Accepted 27 October 2026 UTC. Scope is one authority-bound invented recorded
comparison, not whole R09 or scientific acceptance. [Acceptance JSON](acceptance.json)
SHA256: `eec489c6296256501578241cee9004a174444926c681351e9ceab6ca82af701c`.

## What changed and why

The existing retrieval bridge authenticated source subsets but did not execute all
four arms from them. The new composition connects a single predeclared invented
subset to one AsOf stage, five adapted Virtual Biotech stages and two pure
baselines. Whole original records, source references and coverage stay identical.
Pure selection reuses existing deterministic helpers with an exact frozen query;
grounded and scientific-record fingerprints retain distinct names.

The complete prompts exceeded byte-proxy reservations despite fitting the pinned
tokenizer. An explicit trusted token-capacity object now authenticates exact
prompt/payload/spec/receipt anchors during execution and replay. Default byte
behavior and old fixture gates retain their meanings. Configuration2/receipt2
prevent implicit reinterpretation of old runs. Replay invokes no tokenizer or
archived class. Both setup and final sealing remain within one default budget.

## Corrections and evidence

| Finding | Correction and verification |
|---|---|
| Caller timeout shorter than parent deadline could expire before recorded consumption | Use the earlier deadline through quotation and check immediately before one-use consumption; retained failing-before peer test passes |
| A predecessor claiming a future cell could recurse before rejection | Check exact predecessor request identity before recursive replay; retained peer regression passes |
| The final receipt read could finish after the replay deadline | Add a terminal deadline check; retained peer regression passes |
| A direct child could reseal swapped resource paths | Bind exact consumer resource names/paths before recursive validation; retained peer regression passes |
| Token-backed execution could be presented as legacy configuration | Require schema2 and consistent descriptor/binding in the token verifier; retained owner regression and final full suite pass |
| Expiry while hashing/publishing a cell receipt could leave success | Proactive pre/post-publication checks and withdrawal of only its own unchanged receipt; independent tests pass, without a fabricated failing-before claim |

[Independent engineering review](INDEPENDENT-ENGINEERING-REVIEW.md) distinguishes
the 13 peer passes before the last narrow owner patch from the subsequent 34
focused and 1,646 full passes. Mechanical success does not adjudicate entailment.

## Validation and resource report

- Full: **1,646 tests, no failures/errors/skips**, required probes and package/demo
  checks; all **312** source/resource pins and two hash-only protected checks match.
- Current installed wheel and restored bundle pass; seven installed legacy
  families pass. Matching frozen 0.3.1–0.3.5 verifiers all pass with clean guards.
- Successful case: **192.703 seconds** inclusive execution, **29.359 seconds** for
  subsequent read-only replay; pre-sealing summary is 162.796 seconds. Sealing
  accounts for 29.891 seconds. Pure extraction/lexical work is 0.047/0.032 seconds.
- Input reservation: **14,315**; output: **6,144**. Declared fixture usage is
  384/384; observed model usage, model calls and provider cost are **zero**.
- Retained bundle: **619,912 bytes**; parent peak working set: **36,966,400 bytes**.
  Child peak memory is explicitly unmeasured. These are one-case measurements.

[Qualification](QUALIFICATION.json) binds the successful receipt
`d637c2ca382740500f7f849a603a101ec58a47258d019dbc0618b09447b05697`.
Installed and relocation checks deny original assets, live source/archived
execution and dispatch in their stated scopes; copy operations precede relocation
guards. Python guards are not exhaustive OS auditing or a hostile-user sandbox.

## Failures preserved

The first E: attempt exceeded 300 seconds after two tokenizer children and two
accepted scripted cells; the third quote failed during asset hashing. The whole
run remains failed. [Partial verification](QUALIFICATION-FAILURE-CLOSEOUT-v1.json)
passes for those two cells, without new children or model calls.

One [declared storage remediation](STORAGE-REMEDIATION.md) copied the same 34 assets
plus acquisition metadata to D:, preserving E: originals. The 9,078,923,323-byte
mirror took 20.531 seconds to copy and independently verify. It acquired no new
model/data or license. Fresh spec/asset checks still occur inside the successful
case clock. The two qualification attempts total eight tokenizer children; the
failed attempt is not erased or labeled successful. A third attempt is not
authorized by this remediation.

The first relocation harness invocation supplied an incorrect external receipt
hash and was rejected before copying. Its log is retained. Reading the hash
directly from the retained qualification report fixed the harness input; the
second read-only invocation passed. No response, source or runtime code was repaired.

## Remaining work

Overall R09 remains open: a one-real-record adapter check does not evaluate
nontrivial real retrieval; invented/scripted success does not qualify model quality.
Fresh-case/source-only references and independent human judgments remain pending.
R07's native version remains stopped. R10–R16 and conditional clinical/genetics/
T2–T5/H6 branches retain their original dependencies. No clinical probabilities,
trained scorer, MR result or biological conclusion is introduced here.

Subsequent follow-up: the [five-record real access check](../recovery-step9-real-retrieval-20261027/CLOSEOUT.md)
now qualifies admission/selection mechanics over an existing exposed collection.
Both policies retain the same one record under the byte bound; relevance/source
sufficiency and scientific/native evaluation are still not established.
