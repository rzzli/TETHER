# Native integration development findings

Chronological 0.3.9 development record. All contract validation checks described
below have now passed; final engineering acceptance is recorded separately in
acceptance.json. Earlier pending-work statements describe intermediate states.
Passing a component alone was not the milestone end state.

- Thirteen new fake-HTTP adapter regressions pass. Combined new/legacy native and
  interface coverage passes 53 tests. No actual socket, model, server or acquisition
  is performed. Measured fixture usage is simulated and not a production result.
- The adapter reuses LocalBackend's transport through a small protected deadline
  hook. The old default remains start+timeout; the new adapter clamps the earlier
  caller/parent deadline even when quotation consumed time. A regression observes
  the remaining HTTP timeout after delayed quote work.
- New binding rejects a model whose weight hashes differ from the externally
  anchored tokenizer spec. One-use/concurrent attempts, exact wrapper/model echo,
  version-two capacity provenance, retained interruption bytes and StudySession
  measured/over-quote accounting are exercised.
- A matching installed 0.3.8 probe confirms that structurally valid no-quote inputs
  could be prepared. Their admission eligibility was not established, and this
  was not an observed admitted production source. The new preflight rejects such
  inputs before any future native dispatch; core source requirements are unchanged.
- Initial unit-fixture setup reused a helper whose patch.stopall cleanup removed
  the class tokenizer-resource patch. Explicit per-test transport mocks fix that
  test isolation issue. A missing explicit Mock.assert_ready stub was also fixed.
  The failed logs are retained; no owner or asset validation was weakened.

Remaining work: concrete approved launch/asset capability and leases, existing
controller mode/receipt/accounting/history integration, whole-case fake-transport
tests, installed/relocated verification, full regressions and matching old versions.
Native grammar/actual finite execution and human scientific reviews remain
separate uncompleted gates. Do not start a live experiment from this partial work.

## Shared controller integration progress — 28 October UTC

The original remaining list above is superseded in part: the concrete approved
launch capability and controller mode are now implemented. The fixed server
resource comes from the existing R05 inventory, with no acquisition. Original
assets stay locked; launch flags and positive context/ownership are retained.
OwnedServer now optionally clamps startup/spawn/cleanup to a parent deadline,
with unchanged default behavior. A regression reproduced and corrected spawning
after asset checks exhausted the parent deadline.

The existing controller now shares source admission, actual-history quotations,
budget, baselines, finalization and replay across recorded/native modes. Native
history comes from validated materialized quote sources. A distinct declared
simulated-native scope retains fixture usage and reports zero actual model/network
calls; that scope cannot use the default real process factory. Simulation still
depends on trusted test callbacks and is not an OS sandbox or CPU attestation.

Five whole-case pipeline tests pass: six wrapper stages, two pure results,
source-inclusive replay, same-arm history, shutdown/no-repeat and run-copy
relocation. The integration group passes19 tests; later mode/accounting group15.
Recorded regressions are being checked separately. Complete-case failure tests,
guarded installed/relocated qualification and full acceptance remain unfinished.

New probes exposed counter and clock issues during implementation: foreign
request/owner/model/settings could be counted as known calls; simulated wrappers
shared native known-call counters; and native ready timestamps could move backward.
Five counter regressions now pass and model/simulation/unknown metrics are separate.
Native and shared-case chronology are checked before admission/finalization.
The original failing probes and test-harness corrections remain retained.

## Whole-case failures and validation freeze — 28 October UTC

The expanded integration/mode/accounting group passes 29 tests in 257.991 seconds
(`INTEGRATION-FAILURES-FINAL.log`). A later real InputGraph admission integration
test passes in 70.535 seconds (`LINEAGE-NATIVE-FOCUSED.log`): future-publication
and evaluator-only parents fail before quotation or server construction. Its raw
decoder is a labeled fixture seam; temporal/catalog admission uses actual code.

Root failures cover timeout, malformed answer, KeyboardInterrupt, summary-write
failure, owned cleanup failure and concurrent reservation. No success receipt is
published for these failed cases; retained journals/partial bytes and leases are
checked. A new probe reproduced a missing root failure marker when accounting
itself raised. The root now preserves the primary error and an explicitly
unavailable accounting record instead of losing both errors.

A complete retained native body can report usage even if transport close raises
before returning GeneratedBytes. A failing probe originally lost that usage;
reconciliation now exposes recovered transport usage separately. Conservative
journal reservations stay retained rather than being rewritten. Fixture usage is
still not actual model usage. Both original failing logs are retained.

Source, resources and tests are frozen for full 0.3.9 validation (expected 1,724
tests and 324 pins). All eight prior matching installed verifiers are being
checked separately. The next real-input qualification is prospectively limited
to fake process/HTTP with six actual offline tokenizer children, no model/server
or network. It cannot qualify native grammar or scientific usefulness. Installed
and guarded run-copy relocation checks remain required before acceptance.

## Frozen full result

Full validation completed successfully: 1,724 tests, zero failures/errors/skips,
1,487.641 seconds including required probes, PowerShell syntax and offline
wheel/demo checks. All 324 source/resource/test pins and both hash-only protected
outcome checks are unchanged. All eight preserved matching study versions pass.
The one prospective real-input simulated-native qualification is now declared
in SIMULATION-PROTOCOL.json; its outcome is recorded separately, not assumed here.

## Real-input simulation result

The declared case passes in 200.016 seconds; same-environment source/model-inclusive
read-only replay passes in 36.250 seconds. Six actual offline tokenizer children
reserve 24,558 input/6,144 output tokens. Six fake HTTP stages and one fake process
are labeled simulated; actual model calls/servers are zero. All five original
literature candidates qualify, one is selected, nine parent observations and 65
missing inputs remain explicit. Model/source leases are released; all original
code pins still match. No retry or budget increase occurred.

Parent peak working set including replay is 533,012,480 bytes; tokenizer child
and GPU peaks are unmeasured. The bundle is 999,314 bytes. This is an exposed
case with an unqualified source/question fit, not a model-quality experiment or
fresh scientific evaluation. Offline wheel build matches all 83 runtime/resource
members. Default installation is dependency-free; Arrow21 is copied and verified
only into the optional replay environment. Installed/relocated checks are pending.

## Installed closure

Isolated installed source/model-inclusive replay passes in 43.547 seconds and
guarded run-copy relocation in 42.219 seconds. Every guard list is empty; original
run reads, live source/development-environment reads, archived execution, model/
tokenizer dispatch and network use are denied by the helper. Explicit approved
source/model originals remain available; this is not their independent restoration.
The dependency-free environment also passes one positive/three negative native
wrapper cases, simulated accounting, twelve interface preparations and seven
legacy families. No fixture callback is imported by production replay. Native
grammar, actual model execution feasibility and human scientific gates stay open.
