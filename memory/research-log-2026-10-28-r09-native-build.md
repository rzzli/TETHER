---
name: research-log-2026-10-28-r09-native-build
description: Verified public-C build and format-2 pack, with native execution held by process accounting
metadata:
  type: project
updated: 2026-10-28
---

# Native build checkpoint

Accepted runtime stays0.3.11; see
[[research-log-2026-10-28-r09-generation-acceptance]] and the earlier working
[[research-log-2026-10-28-r09-native-sources]]. No production source changed.

The public-C consumer of seven pinned headers compiled and linked successfully
using the installed tools without restart. Output:
`data/cache/r09-public-c-bridge-build-20261028T175036Z/`.
EXE SHA256 `9f955aec8310ded1cd26648c7d9828369751219975893d5f45b35073b6927696`,
188,416 bytes. Two owned tool attempts exited0/reaped;3.547seconds through helper
completion. Independent build verification checks193 inputs,12 files,eight journal
events,x64 COFF/PE and static imports. Recognition is disabled; the EXE has not run.
The literal machine build-status ABI_disabled label is not an ABI result; --abi
exists for a later qualified run. Source/binary/ABI/science remain distinct.

Static PE caught the original bridge's ABI OpenMP rule before compile/run:
ggml-base requires libomp. Its original source/review stay intact. The revised
consumer prehashes/leases/preloads only the required exact dependency; CPU provider
loading/registry/model remain outside ABI-only mode.

The first259867-byte pack's189 source bindings pass, but primary/161 has raw NUL
at169. It must remain a harness exclusion, never a native rejection. Prospective
format2 preserves every document/grammar/prefix byte; exactly3 pack bytes change
(magic,version,that disposition). New pack:
`data/cache/r09-native-recognition-pack-v2-20261028T183647Z/`;
SHA `f75ab9937c57b5f03c2234643a8a9c91cda852ca0cca0de0478369f793e57e5f`.
Independent verification checks113 inputs/189 bindings/four grammars/six prefixes.
Original167 pure44/123 observations remain;166 byte-front native candidates44/122
plus one harness/native-unobserved case are separate from18 newly serialized
retained authored abstentions and four byte guards. No recovered historical raw
wire, generated scientific answer or native conformance is implied.

Native containment is held. Own-source Job probe assertions passed memory/quota/
termination tests, but independent review found active2 with limit1. Its raw report
remains preserved. The first unexecuted identity diagnostic is held for actual
capture caps, atomic worker markers and SDK physical-line attribution (splitlines
also split two formfeeds). A corrected finite protocol is in preparation; no cause
or isolation claim is inferred. No new targetDLL/GGUF/tokenizer/inference/server
ran; provider spend$0, downloader/monitor untouched.

Fresh baseline checks match327 accepted source/resource hashes and two protected
hashes; protected payloads were not decoded. Full1774 tests are retained software
evidence, not tests of the new unexecuted native executable. Full-project status
is retained in the [native-build reassessment](../planning/Project%20Progress%20Reassessment%202026-10-28%20-%20Native%20Build.md). All R01-R16 and HR1-HR4 are
covered; whole R09 and scientific/human gates stay open. Next: resolve accounting,
qualify ABI-only protocol/run, then separately enable recognition and profile
full-case cost under the unchanged300-second budget. Human submissions remain pending.

## Later scoped OS result

The v2 identity diagnostic stopped before dispatch when its guard rejected the
standard ctypes kernel32 bootstrap. Its five-file failure remains preserved. A
separately declared v3 allowed only that parent bootstrap and verified the cached
module path/handle against System32 before Job calls. Its one actual worker
completed the five fixed snapshots with active0,1,1,1,0 and only PID29040; whole
child1.140s, helper1.203s, empty captures, exit87/reaped and all handles closed.
Independent result verification fd38eceb4d732fe3697c79715d93d59d21c6741137cbb5708172138976d78288
checks53 inputs,14 files,eight journal events and raw SDK/PID buffers. The old
active2 observation was not reproduced; its cause remains unresolved. This is
scoped evidence, not universal/native containment. See JOB-ACCOUNTING-DISPOSITION.md.

The SDK launcher draft remains hard-disabled. Peer review found unsupported
RunJournal kind, raw observations discarded before assertions, and cleanup that
could mask a lease failure. A separately preserved revision is in progress with
real journal integration and pure fault regressions. It will use Job assignment
at process creation plus restricted stdio inheritance and suspend-before-resume.
A harmless-worker fixture is prepared but unexecuted; its source review is not
launcher/runtime qualification. No target DLL, GGUF, tokenizer or inference ran.

## Actual harmless launcher attempt and bounded correction

The independently reviewed v3 qualification ran once under exact protocol
`eb2c1844c325dc02f8ff6546ea963e908ec8676bad36eae370d94fcc2a6e649b`.
Its output remains in `data/cache/r09-harmless-launcher-qualification-v3-20261028T200950Z/`.
The resources worker PID7276 exited0 and was reaped; it reports rejection of the
384MiB allocation and exactly one descendant attempt with OSError1816. The
parent correctly failed its strict final-accounting assertion: observed lifetime
TotalProcesses2, ActiveProcesses0, TotalTerminatedProcesses0 and empty PID list;
before-resume/running observations were total1/active1/own PID. The three later
modes remain unattempted. A terminal failure seal and original raw buffers are
retained. This is not a repeated active2 observation or an ABI execution.

Microsoft's [basic Job accounting documentation](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information)
states that a failed limit association can increment the lifetime total and
temporarily increment the active count. That documented behavior is consistent
with the intentional rejected-child test; it does not prove the sole cause of
this or the older observation. A separately declared v4 will correct only this
negative fixture's exact final expected total to2, with active0/empty PIDs and
independent worker/result checks. Generic and future ABI roles remain strict
total1. No generic1-or2 allowance, active2 acceptance, automatic retry, target
DLL/model/GGUF load or inference follows. Independent failed-result verification
and exact source/protocol review precede any new attempt.

The separately declared v4 (helper1a85332d..., protocol43dd462a...) passes13 pure
checks, all166 pins and independent source review da375f01... before its once-only
execution. Output `data/cache/r09-harmless-launcher-qualification-v4-20261028T202617Z/`
retains a **failed** terminal result. Resources satisfies its exact selected
policy, exit0 and resource checks in0.734s, with peak Job commit11,206,656 bytes.
Overflow retains65,536 bytes/observes at least69,632, triggers its intended stop,
returns125 and is reaped, but its final cumulative total is also2 with active0/
terminated0/emptyPIDs. Generic total1 correctly rejects it. Sleep and suspended
abort are unattempted. Unlike resources, the overflow branch has no reachable
Popen; static startup/source inspection has not identified the second association.
The resource explanation must not be generalized to this case. Independent
failed-result verification is pending at this working-log entry.

A small own standalone static-CRT C++ worker/design is being prepared, not built
or run, to test the same compiled-child architecture as the bridge without
Python startup. It will not retroactively repair either Python qualification or
permit a generic total2 allowance. Exact source, build and execution reviews
remain required; native ABI stays blocked. No targetDLL/GGUF/model/inference ran.

Independent v4 failure verification is now retained:
`HARMLESS-LAUNCHER-V4-RESULT-VERIFICATION.json`, SHA
`42b8b38c6e582288d7f93b64663b2eb0482c033fd3ea44f7bc9d806c55af61a3`.
All166 inputs,17 files,30 journal events,eight raw SDK snapshots and336 lease
records/close outcomes match. Supplemental QA18ec7210... checks both launch flag/
environment records and all85 installed resources against the accepted wheel.
The failure is genuine and remains failed; the overflow association is unknown.

The [launcher reassessment](../planning/Project%20Progress%20Reassessment%202026-10-28%20-%20Native%20Launcher.md)
retains all20 R/HR rows, scientific/data limits and six ordered next gates. Its
UTF-8/local-link/status QA passes; assessment SHA
`e4617f93a378b2a44355f6fc9788c45cd3c7fab53dab0c3b864dfe6cdbfe7d94`.
The own C++ fixture's prospective CRT choice was corrected before any compile:
the actual bridge uses `/MD`, so the new fixture will match `/MD`. Static CRT was
an earlier mistaken assumption, not a retained build result. Source/design and
new bounded build preparation remain unexecuted at this entry.

## Corrected own C++ worker build verified

The separately reviewed v3 build succeeds with `/MD /W4 /WX` unchanged. Source
SHA11490803... differs from v2 only by using the existing UTF-8 conversion after
64-character hexadecimal validation. Protocol7cf13e52... and rootdecision
2d26fe18... bind the new attempt; all prior failed/held artifacts remain intact.
Output is `data/cache/r09-harmless-native-build-v3-20261028T210353Z/`.
CompilerPID2304 exits0/reaped in0.860s and linkerPID9384 in0.032s; helper2.922s.
The own worker EXE is66,560B/SHA
`0100ee6004531a41a28156385ad66fd5c0bded43c4840091a846573efe6d8e49`.
It has not been executed.

Independent [build-result verification](../planning/review-assets/recovery-step9-native-recognition-20261028/HARMLESS-NATIVE-BUILD-V3-RESULT-VERIFICATION.json)
SHA`7f51e8606ba6cb624c5805ac295e5d5211ad8b5d185c619f4286ab1127c1cc21`
passes237 input pins,14 output files,eight journal events, both successful owned
commands, source/PE/import checks and the required post-cleanup terminal seal.
An initial root enumeration of17 entries included three directories;14 is the
actual file universe. Context-manager return is attested, not individual Windows
handle closure. Sixteen pure build checks pass. The source/PE admits only the
fixture's intended own-process calls and finite system/CRT imports; no worker,
ABI target, GGUF or model was run by the build.

The next pending action is an exact-role four-case C++ launcher qualification,
binding this EXE/build proof and nine explicitly named System32 input candidates.
Those candidate hashes are not an observed loaded-module inventory. Source,
pure checks, protocol and peer/root decision precede any actual worker run.
Python failures remain negative/unexplained; ABI stays held.

## Compiler-only v2 failure and pending v3 build

Working entry 2026-10-28T21:04:37.492268+00:00. The own harmless-native v2 build failed in the
compiler: PID7328 exited2 and was reaped after0.578s. `/WX` promoted the C4244
wide-to-narrow string-construction warning at CPP270 to errorC2220. No linker,
object/executable artifact, worker, ABI, target DLL or model execution followed.
The toolchain is available; this is a source compilation error. The failed
attempt and original source remain preserved.

[Independent failed-build proof](../planning/review-assets/recovery-step9-native-recognition-20261028/HARMLESS-NATIVE-BUILD-V2-RESULT-VERIFICATION.json)
has SHA-256 `e5ea27f9e67561e84c2b04a2a7e6face657853fbb1a561205385568608a8988d`.
The separately versioned source replaces that one construction with
`std::string expected = utf8(expected_w);`. Its
[source-only peer review](../planning/review-assets/recovery-step9-native-recognition-20261028/HARMLESS-NATIVE-WORKER-SOURCE-PEER-v3.json),
SHA-256 `c774ecd0ec98dd529b5494c5137679a59e7d1ae9c525920e9f884a57b1f48ebc`,
clears the one-line correction for build review only. Build v3 preparation is
pending at this entry; no build success or worker/native qualification is implied.


## Actual own C++ qualification closed failed

The exact135-pin own-native protocol e29a7bf8... was dispatched once under
rootdecision8bc2c96f.... Its output is
`data/cache/r09-harmless-native-qualification-v1-20261028T211517Z/`.
Resources PID16824 passes in0.718s: small64KiB control/release,384MiB commit
rejected/error1455, one descendant rejection1816, natural exit0/reaped and Job
peak2,248,704B. Overflow PID29880 retains65,536 bytes/observes at least69,632,
triggers its intended cap, returns125 and is reaped in0.954s, but final raw
total2/active0/terminated0/emptyPIDs fails generic total1. Its source branch has
no explicit descendant attempt; no hidden binary/OS behavior is thereby excluded.
Sleep and suspended-abort were not attempted. Both Python and C++ paths now
have this observed pattern; its cause remains unestablished.

Independent [failed-qualification verification](../planning/review-assets/recovery-step9-native-recognition-20261028/HARMLESS-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json)
SHA`939a78fca943ab19a7c3774ea08a9456882cdd0bd14986c5c228711b51df7f1f`
checks135pins,17files/fivedirectories,30events,eight raw48/136-byte SDK samples,
274closed lease records and all terminal/early/cleanup/failure anchors. No
qualification or ABI acceptance is inferred. Original SDKc111 remains disabled;
no upstream targetDLL/model/GGUF was used.

The predeclared next action is a SINGLE overflow diagnostic with a private Job
completion port and query-only handles for reported PIDs. [Design7709b18e](../planning/review-assets/recovery-step9-native-recognition-20261028/JOB-IOCP-OBSERVER-DESIGN-v1.md)
and contract5e8c41b6 bound64packets,16PID records,1024zero-time queue calls and
four stop-boundary snapshots, with observer handles held then released before
original owner cleanup. QueryFullProcessImageName returns path strings; image
files are not opened. Notifications can be absent/delayed and PIDs can be reused;
query handles can change active-count lifetime, so no inference from missing
notifications or observer-perturbed snapshots is allowed. No generic counter
waiver, replay or model work follows. Source/pure/protocol review is pending.


## Console identity observed; detached policy remains prospective

The one bounded IOCP diagnostic under rootdecisionc379330e... consumed protocol
7325c6b8... once. Output `data/cache/r09-native-job-iocp-diagnostic-v1-20261028T215831Z/`
remains negative. Main PID19276 and reported PID24584 both have NEW_PROCESS
observations before termination. The latter same opened handle reports PID24584,
path STRING `C:\Windows\System32\conhost.exe`, current membership in the exact Job
and nonsignaled wait0. No image file was opened or hashed; historical identity,
sole creation cause and a documented active-limit exemption are not established.
Raw samples show total2/active2/bothPIDs before explicit stop and active0/empty
after stop while query handles are held and after release. The counter finding
stops before stdout cap (zero bytes); main125/reaped, whole case0.328s.

Independent [IOCP verification](../planning/review-assets/recovery-step9-native-recognition-20261028/NATIVE-JOB-IOCP-V1-RESULT-VERIFICATION.json)
SHA`25c648a168c5d836acb44e080ba8c4219c2d38068d15174ab35a92701d5beec5`
checks176pins,12files/3dirs,49events,eight raw snapshots,tenPIDqueries,356lease
records and all closure/failure/seal anchors. Nine normal queue returns/three
packets were retained. The diagnostic observation-completeness flag is not a
launcher pass; all earlier failures remain failed.

The author's late hold reached root after that once-only execution. A retained
[fake counterexample70f52](../planning/review-assets/recovery-step9-native-recognition-20261028/IOCP-QUEUE-ATTEMPT-GAP-v1.json)
shows queue attempts/possible dequeues can be uncounted on an exception after
dispatch. No such exception/interruption is recorded in the actual nine returns,
but general budget/interruption guarantees are unestablished. Frozen observerv1
will not be reused; a future version requires pre-dispatch call AND conservative
packet reservations. Its post-review warning remains separate and immutable.

The new [console-identity assessment](../planning/Project%20Progress%20Reassessment%202026-10-28%20-%20Console%20Identity.md)
SHA5690b09e... covers all20R/HR statuses and six next steps; UTF8/12links/reference
QA passes. The next source-only [detached-policy contract387d](../planning/review-assets/recovery-step9-native-recognition-20261028/DETACHED-POLICY-CONTRACT-v1.json)
predeclares primary flags0x0008040C, a literal flag-only disabled SDK copy, the
same EXE and four once-only cases/caps. Generic total1 remains; only resources
final may be1or2 with exact quota/no-success/null-child/control/exit conditions.
The unchanged resource child attempt still uses NO_WINDOW; 1816 is general quota
and cannot identify which limit caused rejection. No host whitelist, Job
breakaway, model/ABI run, source rebuild or old-pass relabeling is authorized by
this preparation. Pure/source/protocol reviews and root exact decision precede
any new execution. Human/scientific gates and default0.3.11 remain unchanged.

## Detached harmless launch qualification — 22:19 UTC

The separately reviewed once-only DETACHED launch passed resources, overflow,
sleep timeout and suspended abort with the same own-compiled worker. Independent
verification `7f184e9b4d04019c6fba3bc661dabe241b7ef6a2a0ee8c713711eeeae12eb961`
checks 140 inputs, 23 files, 61 journal events, 20 raw job snapshots and 284 lease
records. Each final raw job state is total1/active0/terminated0/empty PIDs.
Overflow retains the declared cap and lower bound; sleep and suspended abort
retain exit125/reaping, with no resume for the latter. No historical failure is
relabeled. This qualifies the exact own worker, policy and observed host only;
target DLL initializers, typed ABI, grammar, model resources and science remain
unqualified. The original SDK and literal-only detached fork still have their
general execution flags disabled.

The [Detached Launch reassessment](../planning/Project%20Progress%20Reassessment%202026-10-28%20-%20Detached%20Launch.md)
records all sixteen recovery and four human statuses. Its QA verifies the twenty
rows, six gates and fourteen local links. The next bounded engineering gate is
the existing typed bridge's first ABI observation under strict total1, without
CPU DLL, model or grammar calls. A new explicit runtime closure selects four
target DLLs and sixteen System32 candidates; the compiler closure is not reopened.

## First fixed target-ABI observation — retained negative

After eleven lifecycle tests, 230 independent parser vectors and exact peer
review `1688a4a4...`, root freshly checked 147 inputs and recorded decision
`fb022e2a...` for protocol `dc7de124...`. The single actual invocation failed.
Independent proof `425a2e609f4e2ac6fb1170fbca1ecc66a637f5faa59635fc8175dabff084202a`
checks the exact thirteen output files, thirteen journal events, three raw job
snapshots and 298 lease records. Child exit2 was reaped in0.188s; the terminal
seal remains failed. It reports `required_export_missing` with only attempt,
failure and partial child records. No version, defaults or module inventory was
produced. The final Job snapshot and stdout EOF are unavailable because the
nonzero-exit path skipped those observations. Closed handles and reaping do not
substitute for that missing final snapshot.

Two independent static PE comparisons identify five GGML function lookups bound
to the wrong DLL: registry name/device count/device get and device name/type are
exported by the already-approved `ggml-base.dll`, not `ggml.dll`. All fifteen
LLAMA exports, including `llama_version`, are present in `llama.dll`. Source order
makes registry-name lookup the first missing symbol and prevents both planned
explicit query calls; this is control-flow inference, not instrumented counts.
Earlier static review missed per-DLL ownership. The failed source and output
remain unchanged. Next is a new owner-mapping regression and separate bridge /
parent correction design, followed by fresh build and ABI gates if accepted.
No automatic rerun, SDK-gate change, model access or scientific conclusion follows.

## Corrected v4 bridge build — no runtime execution

New source `2f340355...` changes only explicit DLL ownership, base-handle wiring
and owner/name diagnostics. Seven static PE regressions pass, including the old
failure and each misplaced owner. Sixteen focused build tests pass. The first
fifteen-test proof/source remains retained; a subsequent exact-role guard rejects
extra CPU/model inputs before reading them. Root and independent source review
checked the frozen helper/protocol, 194 selected input pins and25 excluded old
entries, unchanged header bytes and the hardened finalizer.

Root decision `0e8aa37c...` authorized one compiler/linker-only build. Independent
actual proof `48535ac53123db5246c95b7d7ed9211695531e687346e9854ca98d5c51d17473`
verifies194pins/14files/eight journal events, compiler exit0/reaped1.907s and
linker exit0/reaped0.047s, with terminal seal4.125s. EXE191488B has SHA-256
`c5df7b62ce1de641407d973e5994aa91ea244331e5de2d243d3f1e717997e398`.
All seven public headers and the original data pin header match byte-for-byte;
recognition remains false and the expected version remains empty. Compiler
stderr contains pass-version listings, with no warning observed. Build scope
controls the launched compiler/linker handles, not independently attested
descendants; lease closure attests context-manager outcome, not every handle.
The EXE has not run. The separate parent-v2 ABI gate remains pending its final
contract, full fake lifecycle tests, independent review and root exact decision.

Terminal-observation component v2's failed fake test is preserved: a late returned
nine-byte read was omitted from accounting. Separate component v3 `4ea2c429...`
passes19 independent tests (`99944782...`), retaining already-returned bytes/raw
data while preserving deadline errors and admitting no later OS work. Physical
pipe EOF does not establish confirmed child exit. Component acceptance does not
complete parent integration or repair the missing observations in the old run.

## Corrected ABI attempt — module-policy rejection

The final separate parent is revision4 `f3bbd60e...`, with protocol58154061... and
202 input pins. Main19 tests, independent8 methods/15 fixtures and component19
tests pass; both peer and root freshly check all inputs. Parent interruption and
old-EXE argument-helper defects remain preserved as source-only negative tests.
The qualified SDK3bf remains unchanged with its general execution flag false.

Root decision077108c2... authorized this distinct once-only attempt. Independent
actual proof `4b2a3cd7b09c14a8dc3d444ea6e815c8fefeeb9952cfa9724615af77769e9c24`
verifies202pins/13files/17events/408leases over204 paths. Child37796 exits2 and is
reaped in0.234s. Both streams reach EOF,62/0 bytes are retained, final raw Job is
1/0/0/empty and measured process/job peak is2166784B. All204 rechecks complete.
The terminal observations are complete, while the attempt correctly stays failed.

The failure is `unapproved_non_native_module`. No inventory row, rejected name /
path, version or defaults is available. Source order supports resolution before
module rejection and zero later version/default calls; counts are inferred,
not instrumented. The predicate can reject directory or basename, so the tag
cannot identify the offender. Static delay/API-set dependencies are candidates
only; no unknown inferred image was opened or allowlisted. Root authorized a
separate bounded name/path/length/truncation diagnostic before the SAME rejection,
with no policy, SDK or model-path change. Compilation/execution remain later
separately reviewed gates. The new full-project module-policy assessment13f1c...
and QA893561a0... cover20R/HR rows, six gates and13 links; science stays pending.

## Diagnostic-only bridge build — 29 October UTC / 28 October Los Angeles

Separate sourcec2b80250... adds bounded rejection context without changing the
predicate,16-name policy, abort, API ownership or recognition flag. Name256/path
2048 UTF16-unit prefixes retain numeric-unit hex plus optional UTF8, full lengths,
truncation, pair-boundary adjustment and publication outcomes. Hex means four
digits per numeric code unit, not UTF16LE byte hex. The actual module identity
remains unknown until a later controlled observation; no unknown image is opened.

Eleven model/static checks bound the worst modeled enclosing failure to23928B;
these do not execute the C++ formatter. Seven fresh owner checks and17 build
checks pass. Peer4723ad98... reviews source; peer6b62fa89... reviews compile-only
protocol371b1791... and204 input pins. The new build adds a pinned-parent equality
guard; prior builds already used that exact accepted interpreter externally.

Root decision377c20a0... authorizes one compile/link-only attempt. Independent
actual proof `5878717f9048398f4c710fdc4a2b796d81872b9f8d0b3383176108c2ffd4d0c5`
verifies204pins/14files/eight events, owned compiler/linker exit0/reaped and4.219s.
EXE202752B is SHA-256 `a7b4a102959175a674a6664b0027612f1cf0b671e8e8518e9c4cb02497ddda60`.
Same data header/16-name list and DLL-name imports remain; one additional MSVCP
unsigned-short stream-insertion import supports hex formatting. No result was
executed during the build. A separately bound diagnostic parent/protocol, fresh
fake tests and exact reviews are still required. Any future reported path remains
scoped to its new run; it cannot backfill the old v2 unknown offender.

## Bounded current-run identity observed — 29 October UTC

Source-only parent metadata preparation exposed a four-field older output record
versus three-field pin comparison. That failed precheck/source7a and its pure
fixtures remain intact. Separate parent6 ec985415... validates strict schema and
canonical anchored relative locator before any row-path open, then compares the
three integrity fields. Real239-input configuration plus20 main tests and9
independent methods/17 fixtures pass;243-input protocol88672320... and peer9b4f
remain frozen. Root's own guessed main-proof filename caused a retained preflight
failure before import/decision/dispatch; reading the actual selector corrected
only that reference. Root decision40978ab1... then authorized one observation.

Independent actual proof `a92b92376c090401a70fd5ab0e699d0bd02b478b1d3490b9a64817d30cc34221`
verifies243pins/13files/17events/490leases. Child21828 exits2/reaped0.234s; complete
stdout939B/stderr0B EOF, final rawJob1/0/0/empty, both peaks2166784B and failed
seal0.953s agree. The event's attempt-reserved state and marker/stdout returned
publication state reconcile. Full numeric UTF16 code units agree with UTF8 on
`apphelp.dll` and `C:\Windows\SYSTEM32\apphelp.dll`, lengths11/31, no truncation,
enumindex5, directory=true/listed=false. This is current child-reported lexical
metadata only. No reported-image inspection occurred; old v2 identity remains
unknown and all13 old outputs match. No full inventory/authenticity/loader-cause
or version/default query result exists. The policy and rejection are unchanged.

The new full-project Module Identity assessment6d89ff75.../QAecf51eb3... passes20
R/HR rows, six gates and15 local links. Microsoft primary documentation links
Apphelp.dll to compatibility-database APIs and describes loader-associated
matching; it does not establish why this instance loaded or whether a fix was
applied. See the retained APPHELP-CURRENT-MODULE-POLICY-ASSESSMENT-v1 record.
Next is a concrete design for one metadata-only post-core4 self-module census,
max64 rows/2MiB, zero target queries, distinct status/validator and unchanged
policy. Design is authorized; implementation and another launch remain separate.
General SDK flags, scientific/human gates, downloads and stopped monitor remain
unchanged; provider spending stays0USD.


## Census helper build verified — 29 October UTC

The source-only census review found and fixed retained-output classification and
late enumeration-result counters in separately frozen v6/v7/v8 sources. Final
child28a515c2... and wire228e8af0... pass16 boundary/static tests and3 focused
regressions; source peerc1217de6... clears their exact scope. The separate status
sealer and census parser have independent pure false-positive checks. These
prove source/data contracts, not compiled behavior or native qualification.

Build helper3e994b65.../protocolc9ceb5bd.../peer eeb347c0... and root65471faf...
produced one compile/link attempt, without running its result. Independent
actual proof51c255ec... verifies234 inputs,14 files,8 chained events, both tool
handles exit0/reaped and4.656s terminal seal. EXE249344B SHA559e4e9a... has the
same11 ordinary DLL names/no delay imports; seven MSVCP exception-pointer
imports support the explicitly pinned exception header. Three empty compiler-
created telemetry-named directories are disclosed; no descendant or network
attestation is claimed. Header/policy/recognition=false remain unchanged.

Unbound parentv1 stays frozen and disabled. Root and independent source review
identify prospective self/authority hash cycles, a subset-only nonbinary input
universe, and missing used metadata/interpreter provenance. Findings ea0e0918...
require new parentv2 with finite static authority inputs and dynamic parent/
authority/proof pins outside its body; no circular scientific approval exists.
No census, target query, vocabulary/model call or unknown-image read occurred.
Next is exact parent qualification and one separately reviewed bounded census,
then one prospective platform-policy choice or stop, without OS-forensics scope
expansion. Application0.3.11 and all human/scientific gates remain unchanged.


## Single census complete; prospective platform policy — 29 October UTC

The first bound parent preparation wrote P1 but failed when its cache-only writer
was asked to publish a phase-local report. Failure8ac10b86... and sourceafb/P130b
remain. Separately named v3 moves only metadata paths; full prepare success/fault
and repeat-veto checks pass11 methods/43vectors (08d7c731...), with14 original
mechanics ASTs unchanged. Static179 manifest70efee.../dynamic4 remain acyclic.
Independent peercfc16dcc... verifies all183pins/24,917,722B and prepared report
f7474d0a.... Driver's Boolean/int role mismatch remains as failedv1 evidence;
newc6fff0d0... passes six methods/15scenarios (b9397263...), no fake retries.

Root5af5b393... dispatched exact protocol8f011fc7... ONCE. Actual independent
verification4b628df880898e892482399585436b5fa2a068aed607947cd59e5f3d2f8b3f1e
checks183pins/11files/17events/98rows/38matched query pairs. PID11448 exits0/reaped
0.125s;68B/0B EOF, four rawJob boundaries0/0,1/1,1/1,1/0empty, peak2187264B,
185recheck+185original closes and0.594s seal agree. Seventeen complete rows are
self1/core4/listedSystem11/unlistedSystem1, with current ordinal5 apphelp.dll.
Numeric UTF16/UTF8, naturalNextfalse18, one snapshot close, classifications and
footer byte accounting reconstruct. Child structured bytes29693. No reported
image was opened; oldv2 identity, authenticity, causation and initializer effects
remain unqualified. Target-query zeros are source invariants, not instrumentation.

Root7e599031... selects prospective trusted-System32 context for SOURCE/PURE work
only, protected exactself/core4 and ggml/llama/libomp precedence, one strict shared
lexical grammar, max64 and no reported-platform file operations. This assumes a
trusted Windows host; it authenticates no image. No second diagnostic census/OS
tracing; the existing bounded ABI module guard stays. Native owns contract/vectors/
parent matcher; grammar owns newC++ policy source. No compiler/native/CPU/GGUF is
authorized by that decision. Whole-project census reassessment coversR01–R16/
HR1–HR4 and six ordered next gates; current311/defaultv2 and all scientific/human
holds remain. Downloader/stopped monitor untouched; provider spending0USD.


## Trusted-platform helper compiled and independently verified — 29 October UTC

Shared semantic policy fdd15d4f.../fingerprint807995... and73vectors b7e762b5...
exclude CPU/model eligibility and report-derived file operations. Independent
review caught common-device-stem/path-leaf-cap differences in the draft C++;
final source dbf76b19... aligns with the pure matcher. Child10model/static tests
(955e2857...), matcher6methods (9d0ab66a...) and source peersd63f9047.../50f82c2b...
pass. Unbound ABI parentcaf3e69c... adds exact policy fields on the second row;
8methods/156checks pass7b32cbd4... after a retained fixture-key-only failure.
These checks do not execute compiled negative policy vectors or qualify ABI.

The initial build preparation's transcribed checker pin failed at the intended
source gate (5655ded8...). V2 copies the hash programmatically from verified proof
and passes the same21 checks3e000429.... Build source22bf9333.../protocolc1475eb2.../
peerd93a6771... have257inputs/25old exclusions/nine copies. Rootdc1050bd... then
compiles/links ONCE, with no result execution. Actual independent057c0fb212a9b7488f71a442182808c0f728c0b54f7a0fc83eaa13b400e51580
verifies257pins/76,775,545B/14files/eight events, compiler19268/linker8640 exit0/
reaped, context-close and4.750s seal. EXE258560B SHA2feffe29... remains unrun;
ordinary imports equal prior census build, no delay imports; header/recognitionfalse
unchanged. Tool-descendant/network/individual-handle claims are not expanded.

Next is new finite static/native authority plus four dynamic parent/evidence pins,
without oldCensusEXE/compiler inputs or self/proof cycles. Cache-local preparation
and whole-publication failure tests remain required. Root has authorized source/
pure binding only; no ABI constructor, CPU provider, vocabulary, GGUF or model
call follows from this build. Application311/defaultv2, data and human/scientific
gates, downloader and stopped monitor remain unchanged; provider spending0USD.


## Fixed typed ABI observation verified — 29 October UTC

Bound parentf2682469.../contractf32dcfa3... use173static leaves+4dynamic pins,
excluding oldCensusEXE/compiler/CPU/GGUF/unknown image inputs. Before-write
header_copies generatorfailure is retaineddee33dc4... outside the frozenclosure;
working selection is programmatic against actualinputs. Binding10methods/
46vectors pass8bf13470..., cache preparation038dc177... and protocol5e175558...
remain fixed. Twelve prototype/parser andeight prior runtimeASTs match. Peer
servicecapacity interrupted finalreportpublication; reactivated reviewer reused
completed unchangedchecks and retainedb3cb074c... before dispatch. Driver507211b3...
passes6methods/20fake scenariosf5d7e14f..., explicitly matching SDK successliteral
without a nonexistent parentSTATUS attribute. No retry exists.

Root50d60ad5... then dispatched ONCE. Independent actual6f6d3be451853b7de80d00712e3ef96caa26a1e198bd341385daf3e7f1ff92c2
verifies177pins/24,944,861B/11files/17events/five rows. Observedversion0.7.0-dev
(firstactual,nineASCIIchars), all17defaults and31layoutleaves match exacttypes.
Seventeen rawmodule reports classifyself1/core4/platform12 under807995. PID10888
exits0/reaped; fourrawJobtotal/active0/0,1/1,1/1,1/0empty,59B/0B EOF,
179recheck+179original closes, peak2162688B,0.078s child and0.547s seal agree.
Pureparser/matcher under filesystemdenial reconstructs results. No replay/new
platformimage access/globalscan by verifier. Two explicit bridgequeries are
sourceinvariants, not instrumentation; initializer effects remain possible.

Rootacceptance024e0536... accepts onlyfixed version/default/layout boundary.
The old expected-version header stays empty; future source may bindobserved
0.7.0-dev alongside hashes. No broadABI/native/CPU/backend/model/vocab/EOG/grammar
or scientific acceptance is implied. New wholeproject TypedABI assessment covers
R01–R16/HR1–HR4 andsixgates; application311/defaultv2 anddata/humanholds persist.

Read-only nextplan0f3e26df.../JSONfb7dd1ed... clarifies currentABI-only core4
policy rejectsCPU, so a newmode-specific semanticFP/header/parent/parser is
needed, not a flagflip. Preserve167originals/189layered cases/rawNULharnessguard/
sixprefixes. Singleton candidates do notqualify fullvocabulary masking. Existing
COOPERATIVE_MS120000/tokenwork1M are not complete nativework/memory caps. Whole
three-shard identity hashing reads8,988,110,496B even with vocabulary-only/noalloc
computation. Integratedsimulation295.922/300s andsixteen-pass133.933GiB logical
hashinput warning stay. Nextsource/pureauthorization and all actualCPU/GGUF/native
calls remain separate. Downloader/stopped monitor untouched, providerspend0USD.

## Recognition-enabled build verified — 29 October UTC

Source-only decision20ea58d6... and preparationa90c8d1c... permit separate
recognition phasepolicy4d5e09..., typed call caps and exact metadata-only CPU /
three-shard/pack descriptors. No payload access is implied. Sourcee683cf9b...
and header0a049358... preserve the ABI807995 artifacts. Child15 and descriptor5
pure methods plus100 shared phasevectors pass; source reviews retain/correct
unknown creation cleanup dependencies rather than assume absent pointers mean
no native activity.

Builder7b46d675.../protocolc1a7de88... has24 pure checks and exact independent
peer4ad375ec... . Rootauthorizer freshly checks287pins/77,496,944B and14unchanged
helperASTs; decision4624823d... permits compile/link only. Build runs once, both
tools0/reaped, finalseal5.266s. Independent78a4d8c3... verifies287pins/14files /
eight journal events, exactsource/header/copies, unchangedPEimports/no delay,
EXE382754c8...290304B. Root also reconstructs14files/eight-eventchain directly.
No generatedEXE/helper replay or CPU/GGUF/pack payload access in this build /
verification; no universal descendant/toolchain/network or individual-close
attestation is claimed.

Parallel parent/parser review remains unfinished: preserved regressions cover
case-equivalent file-role collisions, stale ABI reporting/sealing, validated
partial-coverage counts and event-specific native setup counters. Final source
review, acyclic build/asset/protocol binding and a new once-only rootdecision are
required before model identity reads or recognition. Fullmask/resources and all
human/science gates stay open. The new [whole-project build reassessment](../planning/Project%20Progress%20Reassessment%202026-10-29%20-%20Recognition%20Build.md)
retains20status rows/sixordered gates. Application311/defaultv2 unchanged; no new
full-suite run, downloads, providercharges or downloader/monitor changes.

Subsequentsourcegate: parentv6e1901097.../validatorv3bbd98b16... independently
clear0068a99b... . Sixlatest suites total50component methods, parser40mutations
and15fake lifecycle fixtures;154syntheticfiles/14chains207events independently
checked. Three e23f findings are corrected: layercounts commitafterexact row,
event-derived setup APIcounts, and derivedreport failures/KI inside unconditional
sealing/leasecleanup. V5diskprimary wascorrect; v6also returns knownfailure/status.
Beforefailures9a2344/c734 and earlierfixturemistakes staypreserved. No actual
payload/runtime wasinvolved. Rootbindingdecision38a52f76... permits exactacyclic
staticsoftware+4dynamic+5descriptor-only inputs with60s metadata preparation;
the new runtime protocol and once-driver remain separately gated. Draftdriver
a9e115... passes8methods/25fakes and independentlyclears3157aac3... whileunbound.

## Frozen recognition attempt closed negative — 29 October UTC

Boundparentb2aafdd9.../authority97e06316.../protocolb690c63b... with188static /
4dynamic/5payload descriptors clearspeer5d7c007e... . Binding11methods/102vectors /
3publication fixtures pass; actual metadata preparation17.578s/60, no payload
access. Concrete driver71101d74... preserves all logic exceptsixbindings and
passes8methods/25fakes. Rootdecisionb6327d4a... thenauthorizes one measuredrun.

Runexitsfailed79.328s, childexit2/reaped; failure required_partial_UTF8_prefix_coverage_unavailable
at30078ms. All189retained bodies separatelymatch frozenmetadata/expectedreported
outcomes:184native results+5harness, fourfixedprefix controls rejectallsixEOG,
two naturalpartialUnicode slots unavailable. Sourcecontinuesallcases thenfails
thecoverageassertion. Nativee49e48f4... reconstructs400frames/442668explicit
attempts=returns and188samplersfreed vs190required. Model/backendcleanupreturned.
Strictsuccessparserverifies111cases/two prefixes thenrejects; no passedprofile.

Independent22cf3294... recordsonefresh213leasedhashpass197inputs+16metadata,
9017363392B158.656s, corepack/400rowaudit292.656s. Requiredreceipt/journal/rawJob
checksnotfinishedbefore300, so originalwholeverificationINCOMPLETE_TIMEOUT;
its summaryat820.437s recordsno reset, neworiginalvalidation or payloadrepeat.
RootSEPARATEposthocarchiveauditb513793d... checks13files/1219chained events,
receipt/seal outputhashes/retainedrawJob0.094s; no payload/OSqueries/targetcalls.
It doesnotqualifytheexpiredgate. Retainedcaptures83/6695B EOF, finalJob1/0empty,
peakchild/jobcommit64368640B andnorecordedcleanup/finalizationerrors agree.

Same-passpackstats showprimary110 has1800rawfourbyte scalars andprimary127two
rawtwobyte scalars; neitherASCII-only/no literalbackslashu. Onlytheir tokenends
were scanned; no piece/endoffsetledger retained. No claimvocab-wideabsence or
exactmergemechanism. Read-onlyreview6f52bf4e... recommends independentbyte/chunk
oracle thenonlyaseparateprospectivefinitecorpusprotocol, neverfavorabletokens
orrepairingoldcriteria. [Disposition](../planning/Project%20Progress%20Reassessment%202026-10-29%20-%20Recognition%20Disposition.md)
coversR01–R16/HR1–HR4; [nextplan](../planning/R09%20Unicode%20Coverage%20and%20Verifier%20Recovery%20Plan%202026-10-29.md)
orders10steps includingboundedverifierdesign, fullmask/resources/integration and
science. Currentexperimentstoppedatdocumentedblockers; application311/defaultv2,
1774retainedfulltests,327sourcepins,65missinginputs/humanholds/nullprobabilities
unchanged. No retry/newdownload/providercharge/downloader or monitorchange.

## Source-only recovery: strict byte oracle accepted — 29 October UTC

After the documented failed runtime gates, the next safe work freezes a strict
model-independent byte/chunk specification, not replacement native fixtures.
Initial96fixtures/v1HOLD9b5a... lackminimumC280/F1branch/crosschunkrestricted-byte
strata. Preservedv2specf4f38354.../corpus65428d32... adds11casesinclmiddleBOM:
107fixtures/167steps/354suppliedbytes,14literal pairs/29interiorcuts. Structural5
checks/manuala1a8a9dd... clear andfreeze285a46b3... precedes any reference/adapter.

InitialCPythonreference99c0... fails3surrogateearly-error assumptions, withno
fixtureedits. Narrow55cc... probes show delayed nonfinaldiagnosis;860d... tests
512strictfinal completions of twofixedprefixes,0accepted. Splitreference1a1c1e68...
passes104directCPython cases plus3RFCearliest/certificate cases, not107APIagreement.
Rootindependentpureoracle4e5d36af... (noreference-sourceconsumption/no codecs)
passes7methods/107cases/167steps, proof04501119... . FirstcheckerreportbugstrPath
preserveda41ae302... withunretainedtestoutcomeUNKNOWN; v2checker0dcb3a0a... only
normalizesPath/newreportname. Peer37d59537... checksall107statehashes/APIprecedence /
ordinaryimmutability; scopedacceptance1e0890b4... . Eleven comparatorcorruption
controls are notmutationtesting. Cumulativehistorycopying canbequadratic; no
generalstreamingresource/hostilePython/vendor/DLL/vocabulary/biologicalclaim.

Sourcevendorreview866c... preserves NUL-sentinel/lenient/partition-dependent
decoder domain and absent finalEOFflag; no extraction/compile/native experiment.
Verifierrecoverycontract37658254... then7bff1438... freezes main-first300/295/5,
singleprocess/no toolroundtrips, livelease/immutablecaptureownercontext andall
requiredgatesbeforefinalsealclock. Jointbound256originals/1728planned events
fits2048cap. Timing26a34e5b... records153.094spre-reservation,5.562reservation→fresh
close and134unattributedendpointinterval; notmeasuredhash/disk/parsercosts.
Orchestrationremainsdraft under peerbookkeeping/ownership fixes; no liveadapter
or originalpayloadpass. [Whole-project oracle reassessment](../planning/Project%20Progress%20Reassessment%202026-10-29%20-%20UTF8%20Oracle.md)
keepsR01–R16/HR1–HR4 andfivenextgates; application311/defaultv2/1774retainedtests /
327pins/65missinginputs/nullprobabilities/humanholds unchanged. Providerspend0,
downloader/stoppedmonitor untouched.

## Source-only verifier orchestration accepted — 29 October UTC

The controller isnow source/pure accepted28d251f4...: correctedsource98ef68ee...,
checker17ab0c8f.../prooff6ddcadf...23methods andpeer1d3b6143... . Initialdraft /
v1 sourceb151/19testproof4ac/limitedpeerCDC andHOLDb61 arepreserved. Rootsource
reviewfinds null/malformed/typednullopen resultswerewronglyclosed; before7cd...
has3fail/1lateownedpass. V2onlyregisterstypedexplicitownednon-nullreturns,
separatesknownOpenFailure frommalformedunknown, neverclosesguessedhandles,
anddurablyjournals3post-reservationfactories. Earliermutablecontext/unknownread /
latechecker/outputownership/finalseal fixesremain. A transientreviewcapacityerror
delayspublicationonly; frozenreviewresumesunchanged. No realadapter/runtime.

Acceptanceisgenericorchestration/controlflow: livefirst-clockbootstrap/exact
authority/fileidentity/read/close/output andrealarchive/journal/rawresource/core
checkers remainunimplemented/unqualified. Enginealwaysstatesrealprofilequalified
false; trustedsourceselectedcheckerports arefuture reviewboundaries, not JSON
readyflags. Futureentrymustpreserveoriginalclockthroughimports/setup. Real300s
fit, DLLUnicode, fullmask/inference/science remainopen; oldprofileFAIL andold
externalINCOMPLETE_TIMEOUT unchanged/no originalpayloadrepeat. New [whole-project controller reassessment](../planning/Project%20Progress%20Reassessment%202026-10-29%20-%20Verifier%20Orchestration.md)
retains20R/HRrows/fivecriticalnextgates. NextdistinctUnicodecontrol/prospective
protocol andrealverifierbinding design precedeanynewmodelread. Application311 /
defaultv2/1774retainedtests/327pins/65missinginputs/humanholds/nullprobabilities
andproviderspend0 stayunchanged; downloader/stoppedmonitor untouched.
