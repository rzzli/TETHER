# R07 source-fidelity and scientific-reporting triage

Review date: 2026-10-26. Role: **evaluation_only**. Coder: **cardiometabolic_review**.
Reviewer type: **ai_assisted**. Status: **AI development assessment; not independently
validated or human-adjudicated**.

**All six responses failed the output contract. That does not make all their factual
content false.** The four synthetic responses retain the main supplied facts; their
failures are predominantly interface/citation encoding, with some structured-field
imprecision. Both real IL6R responses also have material source-reporting problems:
the current interface understates available information, and the simplified interface
blurs cited prior findings with the present study while omitting important qualifiers.
Neither real answer becomes scientifically adequate merely by fixing its JSON fields.

## Scope, exposure and provenance

I read each cell's retained `request.json` and decoded the original `native.content`
from `raw-response.bin` → wrapper `body_base64` → native JSON. I also read the terminal
execution report. I did not alter, repair, complete or revalidate modified candidate
answers. No external retrieval, MR computation, model call or rerun occurred.

Run: `runs/r07-native-diagnostic-20261026T165505Z`.
The terminal seal file's SHA256 was freshly checked and matches
`863bf2a9cfb8d4fd01a5223b993d87fbe2ac06992e7206d3d32ef4c712cf2d41`.
This pass checked that digest and the retained request/response bytes; it did not
repeat the entire source-proof or terminal semantic-verification procedure.

This coder has seen both interface conditions, helped implement the diagnostic
codecs, and prepared the separate source-only genetics form. This is **not an
independent or blinded scientific rating**. The severity descriptions below are
post-hoc development triage, not a preregistered score or a new gold reference.
Synthetic correctness is assessed against the invented facts supplied in the
corresponding requests. Real-source reporting is assessed only against the offered
excerpts, not against an independently reviewed full paper or underlying biology.

All six failures remain in the attempted-cell denominator. The retained report says
the owned server stopped; it reports no accepted response, null clinical probability
and empty prediction features. This triage does not change those statuses.

## Cell-level disposition

| Cell | Potentially useful retained content | Material problem beyond mechanical acceptance | AI development disposition |
|---|---|---|---|
| IL6R / current | Qualitative sIL6R → RA orientation and negative association | Overbroad claims of missing estimates, uncertainty, replication and proxy detail; prior/current attribution not separated | **Major reporting concern** plus state-contract failure |
| IL6R / simplified | Negative association and variant detail recognizable in the source | PheWAS/prior-study attribution conflated; replication and numerical uncertainty omitted; paraphrase labeled literal source report | **Major attribution/coverage concern** plus citation-contract failures |
| Synthetic orientation / current | Correct X → Y direction, both beta estimates and CIs, unknown units/intervention effects acknowledged | Awkward structured predicate and exposure-as-intervention field; unknown context encoded as strings | Useful source summary with **minor structured-field concerns**; state-contract failure |
| Synthetic orientation / simplified | Full source passage reproduced, including both estimates and missing units/intervention effects | No substantive source-fidelity error identified in the text; citation encoding and reason-key failure | **Predominantly interface failure**, not demonstrated factual failure |
| Synthetic context / current | Both source passages retained; mouse liver/transcript/24-hour/vehicle context and unrelated human skin study kept separate | Some proposition slots misassigned despite accurate prose | Useful source summary with **minor structured-field concerns**; state-contract failure |
| Synthetic context / simplified | Both passages reproduced without borrowing the unrelated source as evidence for Z | Limitations fields omitted; broad missingness wording could be more explicitly tied to Z/X | **Predominantly interface failure**, with a minor scope-qualification concern |

I did not identify an invented numerical estimate, reversed exposure/outcome direction,
or assertion of drug efficacy in these six answers. That narrow observation does not
establish scientific validity or rule out problems outside this source-bounded review.

## 1. Exposed IL6R genetics — current interface

The answer places genetically determined sIL6R on the exposure side and RA risk on
the outcome side. A negative association is present in the offered material. However,
its two cited pointers are `/source_metrics/textMiningSentences/0/text` and `/1/text`:
the former explicitly attributes a result to Rosa and a colleague, and the latter is
a results heading. The answer does not retain that prior-study attribution or distinguish
it from the current article's reported analyses. Other offered passages may support a
similar broad direction, but I did not silently substitute those passages as citations.

The main sentence says detailed information is unavailable across design, instruments,
replication, estimates/units and uncertainty. This bundles genuine gaps with information
that **is** offered:

- Passage index **11** reports two-sample MR; indices **1/3** mention gender-stratified
  analysis. These labels do not validate design assumptions, but they are reportable.
- Indices **5/9** include the RA estimate **−0.020**, CI **−0.0320 to −0.008** and
  **p=1.18E−03**. They also include AS numbers. Calling estimates and uncertainty
  unavailable loses supplied quantitative information. Effect scale/exposure units
  can remain unresolved without discarding the reported numbers.
- Index **8** explicitly reports no genetic association in the replicated MR analysis.
  The excerpt does not supply the replication's numerical estimate, precision, cohort
  identity or evidence of independent samples. Those missing details justify a caveat,
  **not a blanket claim that replication information is absent**. The answer's narrower
  wording about independent samples is not itself disproven by the excerpt; its general
  omission of the supplied replication statement remains a reporting problem.
- Index **2** names rs4129267 and its LD relationship with rs2228145, reported as
  r²=1; index **10** contains a statement about rs2228145 and variance in sIL6R levels.
  This does not establish a complete instrument list or instrument validity. It does
  mean proxy-related details should not be treated as wholly absent.

Tissue uncertainty is appropriately left unresolved. There is no direct antibody-effect
claim. Nevertheless, omission of the reported replication result and numerical uncertainty,
combined with overbroad missingness language, materially reduces usefulness for the
question actually asked. **Severity: major reporting/coverage concern; no independent
claim about whether the underlying genetic association is causal.**

Mechanical failure: `answer_status="partial"` accompanies `abstention_reason=null`.
No corrected reason was supplied by this review.

## 2. Exposed IL6R genetics — simplified interface

The text combines a negative sIL6R–RA association with a PheWAS/genetic-IV description
and the rs2228145 variance/susceptibility statement. These phrases are recognizable in
the offered excerpts, so this is not a wholly invented answer. The attribution is the
main concern: indices **0/4** attribute the genetic-IV/PheWAS result to Rosa and a
colleague, while index **10** cites another referenced finding. Saying simply “the study
used” that analysis and “found” the variant result does not distinguish prior findings
from the article's own reported two-sample MR. The source excerpts alone do not justify
collapsing these into one current-study analysis.

The answer omits the RA numerical estimate, CI, p-value and the explicit replication
statement. It also omits limitations on units, population/context and transfer to an
IL6R-inhibiting antibody. `answered` with empty limitations and unresolved arrays is
therefore not a useful representation of the requested scope, even though parts of
the sentence track source wording. The direct-drug-effect inference was not made;
the necessary transfer caveat was simply not supplied.

Mechanical/citation problems are separate and substantial:

- A paraphrase combining multiple passages is labeled `source_report`, whose contract
  requires a literal source passage. This is a **non-verbatim quotation category**, not
  proof that every paraphrased clause is false.
- Five `quote_pointers` entries are section/offset objects, not the required source
  pointer strings. They exceed the two-reference cap and do not pair with the single
  `source_ids` entry. These objects cannot be accepted as valid citations or repaired
  automatically to selected passages.

**Severity: major attribution and coverage concern, plus citation/interface failure.**
The simplified interface did not remove the need for scientific reporting discipline.

## 3. Synthetic orientation — current interface

The prose preserves the supplied orientation (**genetically predicted X → outcome Y**),
discovery beta **0.20**, CI **0.05–0.35**, and replication beta **0.03**, CI **−0.10–0.16**.
The limitations explicitly retain the synthetic setting and the absence of reported
effect units or intervention effects. It does not turn the replication interval into
proof of no effect or turn the genetic exposure into a claimed drug benefit. The E0
`/statement` pointer correctly identifies the offered source.

The structured proposition is less useful than the prose: its predicate “was the
exposure and outcome” is awkward and potentially ambiguous when read alone, while the
dedicated orientation fields correctly separate X and Y. Placing the genetic exposure
in `intervention` can blur that distinction; the explicit limitation prevents this from
becoming an actual treatment-effect assertion in the full answer. Comparator, tissue
and timing are represented by the string “unspecified” rather than null. These are
**minor structured-field/unknown-value concerns**, not invented concrete study facts.

Mechanical failure: `partial` with a null abstention reason. Its useful numeric/source
content should not be relabeled false because of that state error. No fields were fixed.

## 4. Synthetic orientation — simplified interface

The claim text reproduces the complete offered statement, including orientation, both
estimates and intervals, and the fact that effect units and intervention effects were
not reported. The separate limitation is consistent with that source. No substantive
source-fidelity error was identified in this text.

The interface still fails: it emits `reason` rather than `abstention_reason` and encodes
the citation as an object containing an observation ID and `/scientific_context/statement`,
instead of the required pointer-string array containing the original `/statement` pointer.
Manual recognition of the source does not make that encoded citation contract-valid.

**Disposition: predominantly interface/citation encoding failure.** The factual content
offers development evidence of successful extraction on this tiny invented example;
it is not an accepted model output or a measure of real scientific competence.

## 5. Synthetic context — current interface

Both claim texts preserve their offered passages. The first retains **cultured mouse
liver cells**, **compound Z**, **transcript X**, **24 hours**, the **vehicle** comparator,
and unmeasured human efficacy/protein abundance/adverse effects. The second retains
the unrelated human skin-cell study measuring W and not X or Z. E0/E1 `/statement`
citations are correctly separated; the answer does not use E1 as human confirmation
of the effect of Z on X.

Some structured fields need caution: the first proposition's `outcome` is “after
24 hours” even though that is timing (the object and timing fields retain the intended
measurement/context). The second calls an unrelated study an `intervention`, although
the source does not specify an intervention for it. These slot-assignment errors make
the structured representation less reliable than the accompanying prose. The second
limitation's “transcript X” wording is more specific than E1's bare “X”; the central
unrelated-source distinction remains intact.

**Severity: minor structured-field concerns; no major source contradiction identified.**
Mechanical failure is again `partial` with a null reason. Do not retrofit a reason or
silently move the misassigned fields to claim a successful response.

## 6. Synthetic context — simplified interface

Both source-report texts are verbatim. E0/E1 remain distinct, and the stated unresolved
scope does not assert human efficacy or safety. Its broad wording about missing protein
abundance should be read cautiously: E1 does report a measurement of W, while it offers
no X/Z support. A clearer scope would distinguish **X/Z-relevant** missing measurements
from all protein measurements in all sources. That is a qualification concern, not
evidence that the candidate invented a treatment benefit.

Mechanical failures: `reason` replaces `abstention_reason`; required `limitations`
fields are absent; and quote pointers address the rendered `/records/...` structure
rather than the allowed original `/statement` pointers. Those pointers are intelligible
as an attempted reference to visible data but are not valid original-source citations.

**Disposition: predominantly interface/citation failure, with a minor missingness-scope
qualification.** This review leaves the original answer exactly as retained.

## Bounded next decision

**Do not launch a twenty-case interpretation batch or accept repaired copies of these
six answers.** Retain the negative result: zero contract-accepted outputs, useful
synthetic content, and material reporting weaknesses on the exposed real source.

First complete an offline interface review using retained fixtures: make the original
pointer namespace and answer-state requirements unambiguous, check a concise response
skeleton, and exercise exact source-attribution/coverage checks against the supplied
real passages. This review identifies possible changes; it does not authorize or carry
out any change, replay or new generation. Keep the evidence and evaluation boundaries
fixed if a future small diagnostic is approved, and retain these failures in the record.

A future bounded experiment must distinguish two questions: can the interface produce
contract-valid records, and can the model preserve attribution, estimates, uncertainty
and replication qualifiers from a longer source? Fixing only missing keys will not
address the real-case findings above. Stronger-model capacity remains unresolved
without an available matched control; these three exposed/invented case slots provide
no general model ranking or causal capacity estimate.

Human source-only genetics/MR references remain pending. The separate expert form
contains all 13 offered passages and must remain free of these candidates and this
triage. Its independent completion is a separate scientific-review workstream. No
candidate material has been added to that share bundle by this review.

## Retained byte identities

Each hash below is the original `cells/<cell>/raw-response.bin` wrapper SHA256. Decoding
was read-only; no repaired outputs or replacement response records were written.

| Cell | Wrapper SHA256 |
|---|---|
| exposed-il6r-genetics-current | 432444d1603229a61d44b24d2aca65e4684315e600f7e4b40a15799321b227bf |
| exposed-il6r-genetics-simplified | 3b20e146317fd85909df94af808205fa43bd0b16bd4db9148af2352bf5bf55fa |
| synthetic-orientation-current | 9a5e8fe52aaea4cb783e26b0da46f146367a1d519d8e42cbb0808e52183b0808 |
| synthetic-orientation-simplified | cdbcb42d63af6906f05360e848dfa212eb0d9970efdba094653d2f90b58bf164 |
| synthetic-context-current | bcec666f61623508a31d208558050f39128a6f20f889bf3b9ee1b0423a91a67c |
| synthetic-context-simplified | 209c671d17d464c9758e6be9f6589e47e7dd2ef7394dae99240ee1adbd31dc92 |

Within each pair the original request-file bytes match. Request-file SHA256 values:

- IL6R: `359ab80760e101fd092387b93b960c11e90b1a0b15643ef87cdb5512fe74091e`.
- Synthetic orientation: `1f75c0a711842911948e40b966eee8723429317d9843c827bac7ced3cab70a8d`.
- Synthetic context: `881588e1ac0d820704e89d8f58d3303b9cb1b963af64dba61fb35cde386a4e84`.

File hashes are distinct from canonical semantic fingerprints. They identify the bytes
reviewed; they do not establish the scientific truth of either sources or candidates.
