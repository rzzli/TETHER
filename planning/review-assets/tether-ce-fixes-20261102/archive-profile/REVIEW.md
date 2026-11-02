# Reviewed 0.3.12 executing archive profile

This is an executing-helper profile migration, not a rewrite of archived runs or
permission to ignore the semantic dependency guard. The compatibility policy stays
`v0.2-compatibility-20261026`; all archive Python logic and all 22 module names remain
unchanged. Nineteen module pins are identical. Exactly three reviewed pins change:

| Module | Reviewed reason |
| --- | --- |
| `__init__.py` | Engine version becomes 0.3.12. |
| `local_model.py` | CE02 preserves validated over-reservation usage, stops later dispatch and reconciles failed response/accounting bindings. Valid normal and unknown-failure archives remain supported; old contradictory overquote archives must fail stronger verification. |
| `provenance.py` | CE03 extracts the existing used-ancestor receipt relationship into a shared pure helper. The existing relocated ArchiveGraph keeps its original explicit receipt checks; the current outer policy boundary now also checks unused supplied raw inputs. |

The exact old/new module hashes are in `PREPARED.json`. The original resource is
retained byte-for-byte as `semantic_dependencies-0.3.11.json`, SHA-256
`f30b24c24af91523d67e98c0daec50a78aba1e637db89fd8d21c20386988dba5`.
The proposed resource identifies that hash in `previous_resource_sha256`; its own
SHA-256 is `27282ad12814df284cb9a81c25f935f0c47177ead845c9e831bc687c64d85e59`.
The proposed executing profile is `tether-ce-corrections-0.3.12-20261102`.

## Compatibility boundary

New verification must not pretend the 0.3.12 helpers are byte-identical to the old
executing implementation. Old archived code remains data checked against original
pins and is never executed by the relocated verifier. Valid old receipts, source
bytes, quoted unknown usage and admitted evidence retain their original semantics.
An old failed response that already contains validated usage above its reservation
but records a smaller estimate is contradictory; it is explicitly rejected rather
than grandfathered into a new successful semantic claim. This is the intended
correction, not a promise to accept every archive that older code accepted.

The early full-gate failures occurred because the guard still declared the 0.3.11
executing hashes. The guard correctly rejected the changed implementation. Those
failures remain in the original full-gate attempt. No guard bypass, weakened test
or archive Python change is proposed.

## Application and acceptance

Preparation does not authorize publication or establish acceptance. Root must
confirm the old full-gate process has terminated, review these bytes, then apply
the exact candidate resource. Do not update arbitrary pins to silence failures.

After application, run `run_archive_regressions.py` with the aligned development
interpreter and retained old interpreter. It requires the active resource to match
the audited candidate before importing archive code. Acceptance requires all
`test_archive*.py` regressions plus relocated fictional old-engine normal,
unknown-failure and overquote controls. The first two must verify; the last must
reject specifically for lost validated usage. Existing monkeypatched dependency
and missing-original-code negative controls must continue to reject.

The full gate, facade gate, exact installed-wheel qualification and final BG01
evidence checker must then pass. No benchmark, model inference, scientific
requalification, new clinical data or external expert process is introduced.
