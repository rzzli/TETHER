# SC03 checkpoint — input preparation and resident-worker qualification

**SC03 remains incomplete. No development predictions or new benchmark scores
have been generated.** SC01 and SC02 are complete; SC04–SC09 remain pending.

## Completed and verified

- Prospective [protocol](<../../../TETHER SciFact Full Context Protocol 2026-11-06.md>) fixes all300 claims, retained top-five retrieval, all five conditions, reference separation, failure accounting and the 10,000-replicate paired component bootstrap (seed20261106).
- Input functions pass19 fictional tests. The primary constructor has no reference argument; reference-informed conditions require explicit separate inputs. Synthetic sentences retain synthetic origin and never inherit publication locators.
- Source-inclusive preparation reconstructs the original release products and joins retrieval through the anchored baseline receipt. All five conditions retain300 claims/1,500 pairs. Rationale/removal affects159 annotated retrieved pairs; no inputs become empty. Each context-addition condition has1,500 marked synthetic sentences.
- Separate stdlib [input reconstruction](input-review-attempt01/INPUT-REVIEW.json) passes115,998 assertions across every request, source sentence, title, mask, locator and count; it imports neither transformer nor input-construction code.
- Worker/input tests pass31/31, including interruption, timeout propagation, exclusive output, write failure, budget exhaustion, no-reference projection and no fabricated NEI for missing input. The first run caught an exact overlength-error-message mismatch; its failing output and pre-fix worker remain in `worker-qualification-red01/`.
- An actual-model fictional rehearsal executed five pairs using the same resident-worker CLI and qualified supervisor intended for production. [Root acceptance](worker-rehearsal-acceptance01/ACCEPTANCE.json) passes263 assertions, reconstructing source pins, exact output inventory, receipt, journal chain, pair/claim identities and native assembly. No second GPU run was used for that audit.

## Artifact anchors

| Artifact | SHA-256 |
|---|---|
| `data/benchmark/scifact_comparison/preparation-20261106-attempt01/MANIFEST.json` | `90833e941e216d702873fb91786f0175778c72029fb8964453c3159e61bce8c5` |
| [Fictional worker freeze](worker-rehearsal-freeze01/MANIFEST.json) | `108eb66455d25781a61e8138ebf1379f451db6e4b349f1aa8c7311d3089314ec` |
| [Worker rehearsal acceptance](worker-rehearsal-acceptance01/ACCEPTANCE.json) | `189b54dd1083a80c255b60025655d40f9c0e4267e2ac4695974c23edcb98b8fc` |
| Fictional worker `RECEIPT.json` | `1b65514097fb05108128510a2dc0485b8386ed8e250c5d6335f3f12062721f31` |

Actual rehearsal root: `data/benchmark/scifact_comparison/worker-rehearsal-20261106-attempt01/`.
Wall27.402s, model-loading26.209s, process peak working set6,524,968,960B.
All five pairs completed. These observations qualify integration, not full
benchmark runtime or scientific validity. Provider spending remains$0.

## Next required work

1. Implement/test the external-checkpoint provenance context and paired native
   candidate checks. The original context requires a locally fitted sparse model;
   MultiVerS must not be passed off as that model. Preserve observed transformer
   input-token measurements separately from any legacy non-generative accounting
   representation. Retain all request/source/configuration/producer obligations.
2. Qualify source-inclusive production-output reconstruction, native scoring,
   interventions and component-bootstrap analysis on invented cases; freeze the
   complete production input/code/environment/evaluator frame before inference.
3. Execute all five conditions sequentially with bounded workers; keep failures
   and all scheduled denominators. No uncertain call gets an automatic retry.
4. Independently reconstruct primary raw/checked native metrics and diagnostic
   source-use effects, then retain resources/results and close SC03 only after
   the full completion gate passes.

The worker supervisor reuses the existing checked process/event protocol; its
legacy manifest kind contains the word `qualification`. A separate `purpose`
and `benchmark_inference` field identify fictional versus actual execution.
This naming compatibility never relabels a fictional run as benchmark evidence.

No active inference process remains from this checkpoint. The completed rehearsal
must not be restarted. Production is not yet frozen or authorized by a successful
scientific-output acceptance gate; the owner's overall execution authorization
remains in force and no new permission is required for routine remaining work.
