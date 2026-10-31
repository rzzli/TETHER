# Eight-file follow-up: exact protocol peer clearance

The frozen helper
`d9fe3d0807d997bc1c1493b518237b55f2e75f65cdc1a537caa896f5fdd57c47`
and protocol
`f2036eea64d02e61fed222615c830cd79a34798d14eb9e308dd474149c5b862d`
have no material blocker within this source-only scope. Root must issue a
separate exact-hash execution decision. The proposed output remains unconsumed.

The eight paths and URLs match root's pinned scope at commit
`848bbda9041decd87904f7eb5a2990863ecce03b`: `ggml-alloc.h`, `gguf.cpp`,
`llama-model-loader.h`, `llama-mmap.h/.cpp`, `ggml.c`, `models/models.h` and
`models/qwen2.cpp`, at their exact declared repository locations. The qwen2
selection is bound to retained sealed metadata, not a fresh weights/GGUF read.

All **269 input pins** and **330 distinct path components** verify, without
symlink/reparse violations. The sole external pin is the exact canonical base
Python executable. The first source batch's successful receipt and all failed
attempts remain unchanged. The preparation record hashes to
`0f2f26844f5850bcdddc80c18f50ecbe5550a2953754d9cd92e21f547aeb833c`.

Independent AST comparison confirms twelve functions unchanged from the
successful v3 helper, including `child_one`, `run_child`, `collect`, path checks
and worker identity. The full remaining diff changes fixed scope, authority,
retained evidence, maximum-eight dispatch and journal count. Worker PID/PPID
checks, canonical interpreter/controlled venv context, owned cleanup, capture
caps, unknown-receipt stop and finalization failure veto remain in place.

The count-specific pure fixture has valid worker/reservation/capture evidence.
Its two-event journal verifies the intended `Incomplete/unbound source receipt`
rejection, unknown 1 MiB reservation and seven remaining requests stopped, with
zero actual children or requests. It avoids the earlier missing-identity
fixture path.

Bounds remain 1 MiB per body, 4 MiB aggregate retained bodies, twenty seconds
per whole child, 300 seconds aggregate with thirty seconds reserved for
finalization, and 64 KiB per diagnostic stream. Acquisition is sequential and
once-only, with no redirect, proxy, credentials, retry, substitute or include
crawl. These are retained-body limits, not measured traffic charges; local-I/O
timing uses cooperative checkpoints.

[The companion record](FOLLOWUP-PROTOCOL-PEER-REVIEW.json) retains exact checks.
No helper was imported or executed for this review. No request, compile,
native call, model/tokenizer load or GGUF access occurred. Successful acquisition
would still require static review before any header/loader/runtime qualification.
