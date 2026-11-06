# SC04 independent reader audit and corrections

The first independent answer reader accepted five deliberately inconsistent
fictional records. These were verifier defects, not evidence that the production
run contained those inconsistencies. The runtime and its maintained replay were
not changed. The original scientific outputs remain unchanged.

| Reproduced defect | Correction |
|---|---|
| A resealed reservation event declared generation already entered and invented usage of999 input tokens,999 output tokens and$123. | Reconstruct and compare every reservation, tokenizer, generation and terminal event's details. |
| A native wrapper named a non-loopback endpoint. | Require a canonical loopback endpoint, native/tokenizer equality, and comparison with the caller-supplied frozen endpoint. |
| Tokenizer requests disabled special-token handling. | Require the exact tokenizer request, including all three special-token flags. |
| Native generation settings reported streaming despite a non-streaming request. | Compare echoed stop/stream settings, reject contradictory stop causes and check token/context bounds. |
| A source manifest repeated an identical paragraph ID. | Reject duplicate paragraph identities before comparing the complete original XML paragraph map. |

The [pre-fix results](analysis-reader-corrections01/PRE-FIX-PROBES.json) retain all
five accepts. [Probe source](analysis-reader-corrections01/pre_fix_probe.py) is a
historical reproducer; its original input reader bytes remain in the ignored
`data/cache/sc04-analysis-audit-20261106-attempt01/before/` archive and repository
history. Running that script against the corrected reader is expected to reject
the mutations, not reproduce its original accepts.

Additional checks now independently rebuild the MCQ grammar from the visible
choices and source IDs, bind terminal request hashes and exact prompt token counts,
and enforce original native/tokenizer body limits. File reads reject observed
symlinks or reparse ancestors and compare file identity before opening, through
the open handle, and after reading. This does not provide exclusive filesystem
ownership or an OS sandbox.

## Expansion and ranking

`experiments/litqa_analysis/auxiliary_native.py` independently reconstructs both
auxiliary task types. It reads literal instructions and the expansion grammar
from externally pinned source using AST parsing without executing that source.
Question-only payloads, rank-pool identities and hashes, ranking grammar, exact
permutations and canonical expansion terms are rebuilt independently. The answer
and auxiliary readers share the corrected native transport/event checks; neither
imports the inference implementation. Their tests use explicitly fictional
transport fixtures.

## Validation

- [34 focused tests](analysis-reader-corrections01/TEST-RESULTS.txt) pass with zero
  failures/errors:24 answer/source checks and10 auxiliary checks. They include
  malformed output, prompt-capacity abstention, substituted grammars, context
  budgets, hash/usage/event changes, unsafe terms and invalid ranking permutations.
- [Ten original actual-model fictional answer records](analysis-native-reader-attempt04/QUALIFICATION.json)
  reconstruct after the shared-check refactor.
- [Six original actual-model fictional auxiliary records](analysis-auxiliary-reader-attempt01/QUALIFICATION.json)
  reconstruct:two expansions and four rankings, including original prompts,
  grammars, outputs, exact token counts and event details.
- No model or network calls were made. Known fictional semantic failures remain
  unchanged. No production answer score was inspected for these changes.

These are component gates. Complete run/package anchors, original task/reference
joins, source-parent lineage, retrieval selection and paired scientific analysis
remain responsibilities of the integrated independent analyzer. The public answer
reader interface remains unchanged; final callers should supply `expected_endpoint`
from the independently verified server specification. SC04 is not complete merely
because these readers pass.
