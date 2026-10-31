# R07 minimal native consumer design — 2026-10-26

Read-only investigation; no model/server was started, no HTTP or remote request was
made, and the existing HOLD is unchanged. This note proposes implementation and
qualification, not permission to dispatch. Pending human review limits scientific
interpretation; a technically qualified diagnostic can separately measure mechanics.

## Existing exact assets

Root: `E:\projects_data\drug_target_agents_data\models\qwen25-14b-q4km-20261018T032528Z`.
Receipt: `acquisition.json`, SHA256
`cc95c56ce1f497b36d6b9ed62b22721d8af7eaccc0a8c50da91439c5b076acbf`.
R05 `inventory.json` freshly checked all 56 asset hashes; repeat verification before
launch because an earlier hash is not a current byte proof.

| Relative path | Bytes | SHA256 |
|---|---:|---|
| qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf | 3991999872 | a09ea5e7b1eafb1b30b241726c3cc3c905c96f14ad41e246ffa5f44e53904f68 |
| qwen2.5-14b-instruct-q4_k_m-00002-of-00003.gguf | 3989373504 | 21b9457d079680d284e90ef69607c4b2d8ef64a09d4729cb7b5e1357bdba41ae |
| qwen2.5-14b-instruct-q4_k_m-00003-of-00003.gguf | 1006737120 | c8d37006760a387a35216e070e6664d7da927f10be8eb870fef2e3d4833d9976 |
| runtime\llama-server.exe | 9216 | d5055c9523ef34fdc62d7c5836d105e32be54628704250343638be0092429359 |

The small EXE loads pinned DLLs; pinning the EXE alone is insufficient. Preserve all
acquisition runtime file proofs, split weights and exact argv bindings. Do not allow
an arbitrary `--model` path outside the verified three-shard set. No substitutions,
quantization changes or fresh downloads are part of this proposal.

Proposed argv follows the previously used b11717 launcher, with explicit caller paths
and a newly reserved loopback port:

```text
<root>\runtime\llama-server.exe
--model <root>\qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf
--host 127.0.0.1 --port <reserved-port>
--ctx-size 16384 --parallel 1 --n-gpu-layers 99 --threads 8
--alias asof-interpretation-development --no-webui --offline
```

The model alias is provenance, not proof of model identity; the owned executable,
all runtime/weight proofs and argv establish the local launch claim. Existing code
only checks the echoed native model string is nonblank, so strengthening alias
equality requires checking the pinned runtime's actual echo before claiming support.
Do not infer GPU fit from R05 free-memory observations. Retain startup allocations,
actual context/offload, measured runtime and memory where instrumentation is available;
otherwise retain null with a reason.

## Two small new modules, preserving accepted R06 bytes

1. `asof.study.native`: a one-use loopback backend, pure native-response verifier,
   bounded transport capture, and Windows listener-ownership callback. Reuse the
   accepted `OwnedServer`, `ServerSpec`, proof helpers and diagnostic codecs; import
   no old `tools/` launcher. Copy/version only the small native binding/completeness
   predicates from existing trusted transport. No controller redesign.
2. `asof.study.native_diagnostic`: explicit consumer/command for three R05 requests,
   A/B once each, with one owned server and a parent lifecycle journal. Feed the
   byte-identical R05 payloads into `StudySession`. Supply real IL6R request via an
   explicit pin; load synthetic source-only resources through their authenticated
   loader. No evaluator reference or previous answer is passed to the backend.

Each adapter quote reserves UTF-8 prompt bytes + 32 and 2048 output tokens, $0.
`GeneratedBytes.content` should retain the **original native response envelope**, not
only assistant text; parse/materialize only in the trusted verifier. The verifier
parses `native.content` JSON and calls `diagnostic.validate_output(request, interface,
document)`. A returns the structured question response; B returns the distinct flat
response without invented proposition fields. Exact payload round-trip is verified
again before dispatch. Failed native completion or malformed JSON stays a failure.

### Binding, completeness and accounting checks

- Require echoed prompt to equal the complete prepared prompt exactly. Require native
  generation settings seed/temperature/n_predict/stop/stream to match exact payload
  values and types. The archive retains the native schema and complete sent HTTP body;
  do not pretend an unechoed schema field was independently attested by the server.
- Require `truncated` to be exactly false. Reject token-limit stopping. Modern
  `stop_type` must be `eos` or `word`, `stop` true, and no conflicting legacy stop flags.
  Word stop must be exactly `<|im_end|>`; EOS must have no stopping word. Legacy response
  mode must explicitly show `stopped_limit=false` and consistent EOS/word flags.
- Native `tokens_evaluated` and `tokens_predicted` must be nonnegative integer usage,
  not booleans; compare with reservations and retained session accounting. Do not
  replace unknown usage with fabricated measurements. Invalid/missing native usage
  keeps the conservative quote and explicit unknown-measurement reason.
- Retain native response bytes before translation. For ordinary parse failures, return
  captured bytes with usage null so the session can preserve them before rejection.
  HTTP timeout/interruption can occur before `GeneratedBytes` is returned: the new
  adapter must independently persist bounded partial capture plus completeness/error
  metadata under the parent-owned transport directory, then preserve the original
  exception. Include these transport artifacts in the parent receipt. Do not overwrite
  the session's own `raw-response.bin` or report an incomplete prefix as complete.
- Keep response capture capped at the existing 1 MiB native bound and match backend
  capabilities. Retain at most the explicit prefix on overflow and reject. No automatic
  replay after an unknown call. A timeout is included in the attempted-cell denominator.
- Transport remains explicit `127.0.0.1`, no proxies or redirects, one completion POST,
  bounded connect/read time and bytes. Apply the remaining absolute deadline throughout
  reads, not merely a new full timeout on each read. No tools or remote endpoints.

## Windows ownership qualification is currently context-limited

The old helper uses `Get-NetTCPConnection ... OwningProcess` (a CIM-backed route).
Prior CIM queries were denied. A new read-only Win32
`GetExtendedTcpTable(AF_INET, TCP_TABLE_OWNER_PID_LISTENER=3)` size query in the current
managed context returned **ERROR_ACCESS_DENIED (5)**. `netstat.exe -ano -p tcp` exited
zero but returned only headings and no listener rows. Neither establishes ownership
visibility; an empty listing is not evidence that a port is free or owned.

`ownership_probe.py` is prepared for the coordinating agent's selected execution
context. It creates exactly one temporary **caller-owned** 127.0.0.1 listener, reads
the IPv4 PID-listener table, retains only rows for that newly assigned port, requires
an exact host/port/LISTEN/PID match to `os.getpid()`, and closes only its own socket.
It makes no HTTP, model or remote request and contains no elevation or fallback.
Run it in the intended context; a permitted separate-context result qualifies only
that context. Access failure remains a failure, never an owner=True callback.

An eventual ownership callback should use the qualified Win32 route, reject malformed
or oversized tables and ambiguity, and return exactly True only for the retained child
PID and expected loopback endpoint. `OwnedServer` checks ownership **before health**,
again after health and immediately before completion dispatch. The earlier fake-process
unit tests validate control flow, not OS ownership. Native-readiness qualification must
actually demonstrate the real owned PID/endpoint in the execution context. Only the
retained Popen handle is terminated; no discovery-by-port killing.

## Budgets, sequencing and stop conditions

Keep the R05 three-slot, two-arm design and frozen payload bytes. For each case, A/B
share the existing 300-second wall ceiling, with at most 150 seconds allocated each,
32000 aggregate input reservation and 8000 output tokens. Six total potential calls;
zero retries, provider spend and downloads. One 180-second server startup, 30-second
termination and 10-second kill bounds fit within the proposed 20-minute overall
diagnostic cap. Verification/startup costs are recorded separately; do not reset a
case's budget for its second arm. If a remaining budget cannot fit its reservation,
record the cell undispatched. Terminate only the owned server and retain terminal proof.

Required pre-dispatch gates: new-module adversarial tests and installed smoke; actual
ownership qualification; all asset/code/resource pins; exact six-payload parity; proper
partial-response retention and unknown accounting; frozen invocation/budgets; explicit
root decision about the existing hold. No stronger model is available, so even successful
A/B mechanics cannot resolve model capacity. Independent genetics/MR source-only human
review remains pending; mechanism orientation preparation does not satisfy it. Report
technical outcomes separately and make no scientific qualification or H5 claim.
