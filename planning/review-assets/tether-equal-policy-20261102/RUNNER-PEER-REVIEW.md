# Comparison runner peer review

**The unchanged 15 peer tests now pass.** They use invented UNIT-A/UNIT-B records and deterministic fake child lifecycles. This review did not run the paired corpus or obtain expected decisions from either implementation.

The initial runner failed 10 assertions, grouped into five defects:

| Finding | Red evidence | Correction reviewed |
|---|---|---|
| Analysis accepted changed frozen evidence | Altered oracle, code and input bundle each still produced analysis | Recheck frozen pins and the execution's freeze anchor before analysis |
| Declared counts concealed missing cells | A duplicate terminal reference or a shortened record list passed | Require the exact unique case × repetition × implementation grid and matching cell identity |
| Freeze accepted changed expectations or preparation inventory | Changed oracle decisions or duplicated preparation rows passed | Compare the full oracle against the independently authored schedule; require exact ordered preparation identities and descriptor pins |
| Fast completed children bypassed output thresholds | Oversized stdout/stderr followed by immediate process completion was classified as returned | Recheck sizes after child completion; retain an explicit output-limit error terminal |
| Missing observations could equal explicit null | Omitted scorer-preflight and feature-value fields projected to `None` | Use distinct missing-value sentinels |

The positive controls preserve a complete denominator, literal observable projections, exclusive output creation and terminal timeout records without retries. Error/unsupported worker results remain distinct from rejection and cannot count as a successful policy refusal. The root also added a separate invalid-inspection-acceptance counter, so an inspection accepted against a reject oracle remains visible.

The corrected runner SHA-256 is `1b54382c14d02f899d6cd5f34442a4b67879d8a8d308e84c3b07ff005e5ec343`. The peer-test source is unchanged from red to green: `1d2dc2b271ddd2976671481e0c885e7cab1c7d8f988ce7707d27ada87593fc57`. [RUNNER-PEER-RED.json](RUNNER-PEER-RED.json) and [RUNNER-PEER-GREEN.json](RUNNER-PEER-GREEN.json) bind both logs and the exact original runner retained in `runner-before-peer.py.txt`.

The tests inject lifecycle objects instead of executing validators or timing a benchmark. They demonstrate the runner's terminal-record logic, not physical process-kill latency or OS containment. The runner writes child output directly to files and polls; its output limits are qualification thresholds with possible overshoot, not hard retained-byte ceilings. This limit is stated in the execution protocol. Timing and performance claims still require actual frozen paired execution and independent reconstruction.

Read-only inspection of `reference.py` and `materialize.py` confirmed separate preparation and validation, consumption of the preconstructed input bytes, and explicit semantic mutations whose container hashes are resealed without selecting an oracle answer. The previously reported pending-mutation string/dict mismatch and common-envelope validation gap were addressed by the root. This does not substitute for qualification of every materialized native case.

No case/oracle, runtime package, original data, retained result or live preparation input was modified by this peer-review step. BG02 remains unfinished until its materialized cases, final freeze, complete paired execution and independent result reconstruction are retained.
