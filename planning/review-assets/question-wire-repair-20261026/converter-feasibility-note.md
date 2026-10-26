# Pinned converter observation

The b11717 help-only probe accepts disjoint state branches. It warns that the
nonblank `\S` pattern and lookahead pattern are unsupported and permits any string
instead. These successful exit codes do not qualify those constraints. No model
path, server or generation was used; original fixture/output hashes are retained
in pinned-converter-diagnostics.json and its referenced report.

The pinned [argument parser](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11717/common/arg.cpp)
converts the schema before the help exit. Its
[converter](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11717/common/json-schema-to-grammar.cpp)
records unsupported patterns as incomplete conversion; the string pattern path
also precedes the length-bound path. A supported, bounded, nonblank Unicode
representation still needs proof. No constraint is silently dropped, no validator
is relaxed and no new generation is approved by these diagnostics.
