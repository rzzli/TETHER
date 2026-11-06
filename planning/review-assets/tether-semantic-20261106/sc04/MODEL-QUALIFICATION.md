# SC04 fictional qualification and fixed prompt decision

The new local query/ranking/answer transport works with the pinned existing
Qwen/Vulkan assets. **Scientific accuracy is not qualified.** SC04 production
is still pending source acquisition, replay qualification and the final freeze.

The first six-call attempt completed normally. Both expansion outputs included
the requested names somewhere, both rankings placed the useful passage first,
and the unsupported MCQ selected insufficient information. The supported
Lumen-7 color question incorrectly selected insufficient information while
citing its direct evidence. Its source copies, 68-file inventory and report
are preserved in [review01](model-qualification-review01/REVIEW.json).

Two changes were made using only these fictional inputs: discourage combining
aliases into one quoted search phrase, and remove duplicated option listings
from the common answer prompt while explicitly allowing direct support in an
invented example. The original LAB-Bench modules and results remain unchanged.
The fixed new answer prompt will be common to all new arms; the old baseline
therefore remains historical for both retrieval and prompt differences.

The second attempt used a prospectively frozen expanded set of13 controls:

| Kind | Declared outcome matches | Limitation |
|---|---:|---|
| Expansion | 1/2 | Lumarin was emitted as `protein Lumarin`, failing the stricter exact-term check; aliases were no longer concatenated. |
| Ranking | 3/3 | Includes a full16-candidate permutation with the useful passage last in original order. Fictional relevance only. |
| Supported answers | 4/5 | The original Lumen-7 question still incorrectly abstains. |
| Unsupported answers | 3/3 | No claim of calibrated uncertainty. |

The11/13 tally is not comparable with the earlier5/6: the controls and expansion
criterion changed. In particular, the original answer failure was **not fixed**.
The expanded controls establish that the answer path can produce supported
substantive answers and abstentions, rather than being structurally incapable
of answering. No further prompt tuning is planned before the actual evaluation.
Retain the known weakness and measure all199 questions without changing answers
or excluding failed cases. A negative result remains scientifically reportable.

All13 native calls completed with no retry, truncation or token-limit stop,
and normal owned-server cleanup. The second worker took17.453 seconds,
consuming4,646 input and286 output tokens. The first worker took258.328 seconds,
including a full9.1GB asset check before startup. File-system caching likely
contributes to the timing difference; this is an inference, not an isolated
timing experiment. No whole-device GPU-memory or energy measurement was made.
Provider spending was$0.

There are34 passing invented codec/transport tests. The first transport-test
attempt hit sandbox temporary-directory permissions and accidentally discovered
the imported fixture class. The fixed runner confines test files to the workspace
and imports helpers through their module. Failed logs and pre-fix sources remain
in codec-controls-attempt02; codec-controls-attempt04 passes without skips.

[Independent reconstruction](model-qualification-review03/REVIEW.json) passes
624 checks without production imports: source pins, native bytes, exact input
tokens, output usage, all13 declared outcomes, exact journal order and cleanup
bindings. Its first attempt expected older optional `stopped_eos` flags. The
actual pinned runtime returns `stop_type`/`stop`; the corrected checker verifies
those positive terminal fields and rejects contradictory optional flags. The
failed check and its source remain in model-qualification-review02. No inference
was repeated to repair that checker.

Frozen recipe SHA-256:
`5a5392c76885b3f801dccc2cc1b84707f6f700d1bbceaa480624d2ca8187bf5b`.
Local output: `data/cache/sc04-model-qualification-attempt02/`.
Both qualification execution sessions26731 and94567 are closed with exit0.
The actual benchmark has not been dispatched.
