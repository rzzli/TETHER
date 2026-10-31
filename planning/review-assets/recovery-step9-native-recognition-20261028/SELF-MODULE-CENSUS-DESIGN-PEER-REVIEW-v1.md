# Self-census design peer review

**CLEAR for root's implementation decision only:** design `79096837`, contract `5bcde648`. No implementation, build or execution is authorized by this review.

The design matches the selected single post-core4 observation: current child only, one snapshot, at most 64 rows/2MiB, no baseline phase, and unconditional census return before Api construction or any target export/query. Unknown entries remain data and do not stop collection. All raw rows precede classification, with no unknown image file opens/hashes/pins.

Completion requires natural end plus durable lossless untruncated metadata, exact counts, bounded outputs and existing parent cleanup/seal checks. These states remain separate from eligibility. A distinct census parser/status and separately pinned one-literal sealer copy prevent ABI success labels; SDK 3bf remains untouched. Source and pure tests must still verify those proposed components, byte reserve accounting, 64th-Next/65th-entry behavior, query/error/hex relations, cancellation and publication/late-close/postseal vetoes.

Current apphelp metadata remains current reported context only. The unchanged sixteen-name list stays unchanged; any later file eligibility read or finite policy revision requires separate selection/review. The census does not establish loader cause, lifetime/global inventory, trusted unknown-image identity, initializer safety or ABI/scientific acceptance.
