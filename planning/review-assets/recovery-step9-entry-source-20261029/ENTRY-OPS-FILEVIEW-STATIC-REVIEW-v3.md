# Frozen entry integration static review, v3

HOLD for three statically confirmed source-integration defects. All source1 bytes and the v1/v2 reviews remain preserved. No subject import or execution occurred.

- **F3, earliest gate:** `_BootstrapPrimitives.__post_init__` (kernel1156) checks `backend.invoke`, but exact `SyntheticRawBackend` exposes only `invoke_reserved` (114). KernelState passes that object at1413, so valid entry construction cannot return to assign `attempt.state` at1820.
- **F1:** Ops132 invokes `sink.close_journal`; canonical SinkFacade exposes `close`. Healthy owned finalization cannot obtain the journal-close callback ACK or reach receipt/seal.
- **F2:** Python `c.*` delivery assignments precede synthetic native-bank commit. An interrupted commit can leave staged data trusted by handle/count authority. Root identified this; committed bank facts must drive rights/cold lower bounds independently of interrupted caches, while distinct Python delivery observations remain separate.

F3 gates ordinary valid entry before the deeper F1/F2 paths. Root selects the finite first-evidence and coherent successor order; this reviewer applies no workaround or source change. Kernel authorship is disclosed, and Native's independent full-source/harness lane remains separate. All real entry/native/physical/full-roster/resource/science gates remain open.
