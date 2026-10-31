# Policy scope after the single census

The goal is typed ABI/grammar correctness, with the Windows host trust assumption stated explicitly. After the one declared census, choose a policy or stop the gate; add no baseline, loader tracing, repeated census or shim-causation work. No policy is changed by this note.

A finite reviewed extra-System32 set keeps current-host pins reproducible, but adds pin/header churn and can remain brittle as Windows startup/API hosts vary. One basic static pin batch may support that choice; recursive OS authentication is unnecessary.

Treating normalized reported System32 DLL paths as platform context is the proportional alternative when OS trust is accepted. Exact core4/self pins, wrong-path core/libomp rejection, protected ggml/llama/CPU application namespaces and rejection of other outside-System32 modules remain. This is a declared platform boundary, not image authentication or proof of unshimmed/native initializer behavior.

Minimum next decision: review the one complete durable untruncated census once; if it contains only the declared self/core plus platform context, choose and freeze one policy across child/parent/contract/protocol before another ABI attempt. An incomplete census or unexpected native/outside-platform entry keeps the gate failed. Prior failures remain, and no eligibility or scientific/ABI acceptance comes from census completion alone.
