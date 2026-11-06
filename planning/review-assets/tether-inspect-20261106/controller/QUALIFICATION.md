# BG05 three-arm controller qualification

This is engineering qualification on invented inputs. It is not the 109-control benchmark result, a biological task result, or a model evaluation. Actual EP corpus execution remains a separate frozen stage.

## Implemented boundary

The [controller](../../../../experiments/inspect_policy/controller.py) freezes one full corpus schedule, rotates three arm orders across three repetitions, and creates one fresh interpreter for each arm/repetition. Bare independent and Inspect workers reject imports of `asof` and `tether`; the bare TETHER worker deliberately loads the existing native comparator. All three use the same sealed archive-operation wrapper. Bare worker recipes contain no oracle. Native Inspect receives an empty sample target and opens the oracle through its scorer after the case result has sealed; trusted parent scoring also occurs after each returned worker or retained prefix.

Existing outputs are never resumed or overwritten. Output paths overlapping the frozen corpus, preparation or qualified environment are rejected before reservation. Case, batch and stage bounds are explicit. Interrupted or failed operations keep their journal and any completed prefix. Errors, unsupported operations, missing candidates and unstarted cases are not successful rejections. Parent policy conformance and completion of the native Inspect logging/scoring pipeline remain separate quantities.

The installed `tether._process` supervisor is shared infrastructure and counts as reused code. It supervises one owned child, stdout/stderr limits, EOF and deadlines; this is not a process-tree containment claim. The local network guard denies external connection/DNS operations while allowing the qualified Windows stdlib asyncio loopback self-pipe. It is a code-level guard, not an OS security sandbox. Artifact-size checks occur at declared boundaries; per-case and parent process deadlines provide separate time bounds.

## Source checks and the prospective optimization

Rehearsal01 measured roughly 18 seconds per complete environment check, compared with approximately 0.6 seconds for a two-case bare worker. With root approval, rehearsal02 moved the full installed-environment content and inventory checks to the beginning and end of the whole stage. Every batch still checks corpus files, original runtime inputs, current implementation, archived source bytes and qualification receipts before and after dispatch. Workers separately check their Python source closure. The complete inventory remains frozen; third-party payload content is bracketed rather than continuously attested. A failed final global check marks the stage partial while preserving all actually completed outcomes and scores.

Every new preparation now copies source and explicitly supplied protocol inputs into a content-addressed `source-archive/`, with original path, byte count and SHA-256 mappings in the freeze. Rehearsal01 predated that feature. Its exact 55 Python files are retained separately in [code-rehearsal01/ARCHIVE.json](code-rehearsal01/ARCHIVE.json). One test changed after the independent review released its hold; the initial mismatch is retained, and the recovered prior bytes were accepted only after matching the original frozen hash exactly. Neither old run outputs nor its freeze were rewritten.

## Retained controls

- [Initial new regressions](../controller-tests05-red.log): missing global-postflight integrity reporting and absent historical source archiving fail before implementation.
- [Optimization gate](../controller-tests06-green.log): all 11 tests pass. Coverage includes output collisions, protected paths, finite limits, oracle exclusion, denominators, changed source detection, valid-prefix recovery after postflight failure, final global mutation after all nine batches, source-copy identity, real fatal case deadlines, and the installed supervisor.
- A final review identified that hashing existing bundle files did not reject a newly added file or empty directory. The [failing-first control](../controller-tests07-inventory-red.log) reproduced that gap. The final global audit now compares exact bundle files and directories against the anchored original corpus freeze. All [12 current controller tests pass](../controller-tests08-inventory-green.log). A separate [read-only positive audit](INVENTORY-QUALIFICATION-01.json) verifies 2,181 pinned original inputs and the exact 1,966 bundle files / 342 directories; it executes zero cases. This audit-only change follows the complete native rehearsal02 and does not relabel its older source hash as the final version.
- Supervisor controls exercise exact output cap, cap plus one, ordinary deadline, EOF before process exit, and a finite grandchild holding inherited stdout after its parent exits. They do not assert arbitrary descendant cleanup.
- Policy-owner IX06/IX08 controls are separate: [actual process evidence](../integration/runtime-process-tests01.log) covers interruption after reservation and competing exclusive reservations. Their source and result qualifications are reported by that owner.

## Complete real-component rehearsals

Both use the same two invented examples: one valid prepare operation and one invalid task. Each executes nine fresh workers and three real Inspect native logs. No real model calls, provider charges or actual EP cases occur.

| Check | Rehearsal01 | Rehearsal02 |
|---|---:|---:|
| Scheduled cells | 18 | 18 |
| Completed, fully conforming cells | 18 | 18 |
| Fresh workers / native Inspect logs | 9 / 3 | 9 / 3 |
| Through-stage-seal wall time | 333.735 s | 66.077 s |
| Whole rehearsal wall time | 347.281 s | 80.376 s |
| Full pinned inputs | 9,103 | 9,163 |
| Per-batch pinned inputs | 9,103 | 234 |
| Source files copied inside preparation | 0; separate later archive | 57 |

These timings demonstrate the qualification bottleneck and its correction; they are not the primary benchmark performance estimates. Rehearsal02 global hash checks measured 15.544 and 16.754 seconds; environment-name inventory checks and all finalization work also occur within the separately measured whole-stage boundary. Per-batch hash checks measured 0.244–0.420 seconds. Inspect's lazy framework import occurs within its execution interval, while the bare validator import occurs before that interval; the complete supervised batch is the matched timing quantity. Operation-only values are diagnostics.

Rehearsal01:

- [Qualification](../../../../data/cache/tether-inspect-controller-rehearsal-attempt01/QUALIFICATION.json).
- Stage seal SHA-256: `d6a99b7160dfc611212fde18a268b4bfd93ca2d24dbda584af15503c36cee983`.
- Freeze SHA-256: `2da2031da4346c44fa1f348f3ab9faa7be720fd34fd18914545619f9679f46f9`.
- Independent [reconstruction](../reconstruction/FICTIONAL-STAGE-01.json) passed all 18 cells, nine workers, three native logs and full frozen input verification. Its SHA-256 is `c7e3f8deb600b7955b4280efeb24e71732365208946906ac0ab63db493ef59f2`.

Rehearsal02:

- [Qualification](../../../../data/cache/tether-inspect-controller-rehearsal-attempt02/QUALIFICATION.json).
- Stage seal SHA-256: `651736cecef3fbd2e41683fc5e4394298ca59ebcba95f7bddb6ed332683cb385`.
- Freeze SHA-256: `b84dcfb59f8db066b352404e78d632a67af9b8ac1f57e442509c24c77884253b`.
- Independent [whole-stage reconstruction](../reconstruction/FICTIONAL-STAGE-02.json) passed all 18 cells, nine workers, three native logs, the complete environment and archived source inputs. Its SHA-256 is `1b5d91a20843ebebf8ab4ac7cf31a21f3b38376001f92d6375fc27186ffdad7f`.

Rehearsal02 controller SHA-256: `4a4dcbf0768709513f0f1a85d4d675218e4af1f143415705e51487ccf3e39e14`; its exact bytes remain in that preparation's source archive. Final qualified controller SHA-256 after the narrow inventory correction: `f3cef96b1b0e011cc4da877565a55743261316e2b45c138b06e5347ba28e99ab`. Current controller-test SHA-256: `5e13f77b5c0f674abd5c01aff848b16d97d69c628ed2cf72b412d15c9208d280`.

The actual 109-control, three-arm, three-repetition execution requires root's complete qualification review and prospective freeze. No conclusions about broader agent-framework superiority follow from these invented-input checks.
