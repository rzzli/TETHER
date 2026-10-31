---
name: research-log-2026-10-28-r09-native-sources
description: Working native source prerequisites, verified twelve-file fetch and remaining header/loader gates
metadata:
  type: project
updated: 2026-10-28
---

# Native source prerequisite checkpoint

Accepted software remains 0.3.11; see
[[research-log-2026-10-28-r09-generation-acceptance]]. The next R09 work is source
qualification before any typed build or actual-vocabulary execution. New phase:
`planning/review-assets/recovery-step9-native-recognition-20261028/`.

The first actual twelve-reference batch succeeds under frozen v3 source controls.
Cache: `data/cache/r09-native-recognition-source-20261028T161554Z/`.
Receipt SHA256: `cf2a70a3488d4dd96320d893a22e1b7706d6f913e8f5f238c9e68d4de1405f90`.
All twelve sources at commit `848bbda9041decd87904f7eb5a2990863ecce03b` total
726,350 bytes; operator execution takes 10.5 seconds. Independent verification
checks 111 output files, 139 input pins, 51 journal events, exact worker identities,
caps, progress and source hashes. No missing/unknown receipt, failure marker,
native target, GGUF read, compilation, inference or server occurs in that batch.

Preserve the unexecuted v1 preparation and actual failed v2 output. V2 stopped
before urllib/HTTP because the Windows venv Python launcher inserted a process
between Popen and the Python worker. The corrected transport invokes the canonical
hash-pinned base interpreter with a controlled accepted-venv context, strict
PID/PPID handshake and unchanged 85 installed package files. Harmless identity and
one-second timeout probes verify that configuration. Prior Python wrapper records
prove launched-handle reaping, not general descendant termination; no orphan is
demonstrated and successful replay outputs remain unchanged. Details are retained
in `PYTHON-WORKER-OWNERSHIP-NOTE.md`. The original wrong-path no-network fixture is
preserved; a separate peer-reviewed supplement reaches the actual incomplete-
receipt guard, retains the unknown 1 MiB reservation and stops later requests.

Static reviews establish remaining prerequisites rather than native conformance:

- The five direct GGML headers are retained, but `ggml-backend.h:4` requires
  missing `ggml/include/ggml-alloc.h`; its descendants remain unreviewed.
- `vocab_only` skips the explicit tensor-loading path, but follows loader/shard
  metadata construction and device preparation. A non-null empty device array
  with split NONE avoids default model-device enumeration; it does not qualify
  DLL initialization or backend discovery.
- `llama_backend_init` can invoke broad backend discovery. Its safe initialization
  policy remains unresolved; do not copy the example tokenizer, which requests a
  context even after vocabulary-only loading. Backend/model free calls do not
  prove full backend unloading.
- Token/piece sizing, special handling, UTF8, raw NUL and EOG need the exact
  source-qualified procedure in `VOCAB-TOKEN-REVIEW.md`. Use non-null buffers;
  preserve bytes; EOG inside document tokens is a separate harness disposition.
  Finite logits make rejection observable; grammar apply iterates every provided
  candidate. Source observations do not prove properties of the actual vocabulary.

A bounded eight-file follow-up is proposed, **not yet fetched at this checkpoint**:
`ggml-alloc.h`, `gguf.cpp`, `llama-model-loader.h`, `llama-mmap.h/.cpp`, `ggml.c`,
`models/models.h` and `models/qwen2.cpp`. See `FOLLOWUP-SOURCE-SCOPE.json`.
The qwen2 choice is supported by a prior sealed server metadata line and matching
recorded three-shard asset identities, not filename inference or a new GGUF read;
future native use must reverify exact assets and architecture. All caps, source-only
scope, no automatic crawl/retry and root/peer review remain required.

This is a working prerequisite checkpoint, not completion of header closure,
loader safety, ABI, native grammar/EOG or resource qualification. The preserved
295.922/300-second simulation, fresh source/case suitability, HR1–HR4 and later
clinical/genetics/scoring/T2–T5/H6 work remain open. Provider spending stays $0;
the downloader and stopped monitoring remain untouched. See [[project-goals]].

## Verified follow-up checkpoint

The eight proposed follow-up references were subsequently fetched once, with
receipt `6e479bdaf3a0cf58b3afd1869c2317b9799e7dfa2e92c1fc9332730e7a7f86e9`.
The 490,241 retained bytes/75 outputs/269 pins/35 journal events verify, and all
eight actual worker handles were reaped. The public repository header graph is
now closed at seven headers and thirteen quoted include edges, with no missing
repository include. This is not a compiler/system-header or ABI guarantee.

The delegated parser explicitly skips weight-blob reads under no-allocation;
metadata, tensor descriptors, vocabulary allocations, file opening and size
checks remain. No zero OS weight-I/O claim is made. The selected initialization
design will explicitly load one exact CPU provider, require its registry identity,
then call the public initializer without automatic discovery. Two focused source
references are being prepared before that decision. No new native or GGUF call
has run. The original failed attempts and earlier checkpoint above remain intact.

## Source scope complete; runtime containment held

The two CPU references were subsequently retained and independently checked.
All three batches now total22 new source files/1,242,387 bytes; root qualification
`ace2041e0da3830945317b39e3970afaf440e44693d48bff8a746cb984f34f0c`
checks207 output hashes. Static CPU identity/conditional discovery avoidance is
supported; delegated initialization/build/DllMain limits remain. Acquisition stops
at this finite scope. The first typed consumer passes text review, but static PE
inspection subsequently finds core ggml-base imports libomp, conflicting with its
ABI-mode module rule. No compile/target call occurred; preserve the first source
and prepare a separately reviewed minimal revision and pin header.

An own-source OS-only containment probe passed its initial assertions, including
64MiB commit rejection, quota1816, explicit termination and last-job-handle closure.
Independent verification then found active-process counts2 with configured limit1
in two pretermination snapshots. Its original report remains unchanged; unqualified
containment is held pending a separately prepared finite identity diagnostic. No
new target DLL, GGUF, tokenizer, inference or server has run. The189-case pack
preparation returned successfully; independent binary/source validation is pending.
Its18 abstentions are NEW declared serializations of retained parsed fixtures, never
recovered historical wire. Human reviews remain pending.
