# One additional vocabulary implementation reference

28 October 2026 UTC. Prospective source-only scope correction before acquisition.
The [local inventory](LOCAL-SOURCE-INVENTORY.md) remains the preserved eleven-file
proposal; none of its proposed files has been fetched by this phase yet.

Read-only public API review found that the retained header documents negative
required counts for `llama_tokenize`, but does not establish equivalent sizing
or error behavior for `llama_token_to_piece`. Neighboring detokenization comments
cannot be transferred to that different API. A null/zero-capacity sizing call
must not be assumed safe without inspecting the implementation.

Add exactly one candidate reference to the prospective batch:
[src/llama-vocab.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/src/llama-vocab.cpp)
at the same pinned commit `848bbda9041decd87904f7eb5a2990863ecce03b`.
Its contents, remote availability, size and hash are still unverified. It is
needed to locate the public token/piece wrappers and inspect buffer lengths,
special rendering, lstrip behavior and vocabulary/EOG semantics. Any delegated
behavior not established by the retained implementation remains unknown.

The proposed batch now contains **twelve exact paths**: the original eleven plus
this one. Keep the 1 MiB per-file and 4 MiB aggregate retained-body limits,
20-second whole-child and 300-second aggregate bounds with a 30-second final
reserve, sequential once-only requests and fail-closed partial accounting.
Remote failures or oversize files remain explicit; do not fetch substitutes,
raise caps silently or crawl includes automatically.

Only preparation is currently permitted. Root/peer review of the exact helper
and protocol hash precedes any request. No compilation, native DLL/GGUF access,
vocabulary handle, context, tokenizer execution, inference or server is authorized
by this text-reference addition.
