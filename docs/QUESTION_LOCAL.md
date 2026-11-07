# TETHER — Question-bound local interpretation

The current interface is `tether-target-agents` **0.6.0**, with the `tether` CLI
and public namespace over `tether-target-engine` **0.4.0** (`tether_engine`). See
[installation](../README.md#quick-start) and the [namespace migration
boundary](../packages/tether/MIGRATION.md). Public aliases share the new engine's
module and class identities; they do not certify earlier execution fingerprints.

The component history below retains earlier versioned observations and test
counts. Those qualifications belong to their original code and dates, preserved
in the [historical checkpoint](ARCHIVE.md). Names and example paths here use the
current namespace for readability; exact original identifiers and reproduction
commands are in that checkpoint. The naming migration is not a scientific rerun
or a transfer of historical qualification to the new release. The semantic
experiment remains **paused**; this guide does not reactivate it or retired
study and expert-review branches.

The optional question renderer and loopback transport implement the version-two
question contract without changing the sealed legacy interpreter or recorded
runtime. Scientific validity remains a separate gate. Tests use fake HTTP only;
they do not attest a model, generate a biological answer or qualify a dossier.

## Lossless prompt and source aliases

`question_interpretation_render.render_prompt` presents the generic family question
first and complete reported passages before their metadata. Its reversible view
preserves original JSON types, missing fields, arrays and every selected source
field. Chat control tokens are escaped only inside JSON data. Actual newlines and
literal backslash sequences survive reconstruction without global replacements.

The complete UTF-8 prompt must fit 14,200 bytes by default. There is no truncation
or automatic context increase. The 16,384 context bound includes a conservative
input reservation of prompt bytes plus32 and at most2,048 output tokens. Current
real-source development prompts measure14,149 and12,785 bytes; the smallest
remaining byte margin is51. Together they reserve26,998 input and4,096 output
tokens, within unchanged shared-case defaults of32,000/8,000. Byte reservations
are conservative estimates, not measured tokenizer counts.

Native answers identify exact quote locations through source aliases such as E0
and original JSON pointers. `materialize` resolves these to complete original
strings, UTF-8 spans and admitted observation identities. It adds only trusted
request/hypothesis/question bindings; it does not repair scientific assertions.
Answered, partial and abstained states use the existing version-two validator.
Features remain empty and clinical probabilities null.

## Explicit transport and offline verification

`LocalQuestionInterpreter(config_path)` accepts the existing strict loopback-only
configuration and pins its original bytes. It sends a single `/completion` POST
with redirects and proxies disabled, deterministic settings and a bounded JSON
schema. One backend object allows at most one attempted dispatch; failure does not
reset that allowance. No retries, launcher, asset download or provider are added.

Pass `verify_local_execution` explicitly as `adapter_verifier` to both
`run_question_interpretation` and `verify_question_interpretation`. The durable
runtime pins the callback and adapter code closure. Verification rebuilds the exact
payload, compares original native bytes with their parsed object, repeats prompt,
typed-setting and completion checks, re-materializes the answer and reconciles
measured usage. Verification makes no HTTP request. A zero-call budget abstention
is verified without an execution archive.

Native raw responses are capped at1MiB. Oversized responses retain a bounded prefix
marked incomplete. Partial reads retain available bytes and remain failed. Raw-byte
and translated-response hashes are separate. Typed native usage is preserved even
when the generated content or stop flags are invalid; the runtime rejects a
diagnostic envelope while retaining that measured usage. Timeouts and unmeasured
failures retain conservative reservation accounting. Interruptions are re-raised.

Configuration asset hashes and echoed model names are declarations, not proof of
execution. A separately frozen owned launcher must verify local assets before any
pilot. No remote execution attestation or independently validated science follows
from source-inclusive mechanical verification.

## Remaining release gates

Independent methods review and full unchanged-code validation pass:1,239 full tests,
required probes/package,276 isolated and184 dependency-free tests. The renderer has
20 focused tests/seven independent probe groups; transport has21/eight. All legacy
and completed core/runtime pins, plus protected outcome-file hashes, are unchanged.
Retained acceptance: planning/review-assets/question-native-transport-20261025/acceptance.json.
Earlier failing review versions remain retained. These checks do not execute a model.

The next pilot still needs its separately frozen owned launcher and protocol. It must keep
the same cases, questions, selected sources and budgets, make at most one call per
question, retain failures and stop its owned server. Independent scientific review
and adjudication follow generation. Previous failed scientific qualifications,
the65 missing inputs, full T6/H5 and original scientific Tasks6–8 remain open.
