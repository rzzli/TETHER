# Source-audit support: origin and limits

These helpers support the retained deterministic source-validation diagnostic.
They reconstruct expected source projections separately from its producer,
assembler and scorer. They still share core contracts and filesystem utilities;
this is not an independent implementation of the entire verification system.

Selected definitions were copied from the following private historical files.
The originals were not edited. Their SHA-256 values identify the extraction inputs:

| File under `planning/review-assets/preprint-p05-20261031/` | SHA-256 | Current module |
|---|---|---|
| `audit_source_registry_v3.py` | `88a10f870ff75ca7445ba5fe4e6823afe9b7575e80e74e53210fd67c217f61fa` | `registry.py` |
| `audit_source_inputs_v1.py` | `785158a9ecd424bbec5da6897a55dfc996bcfc1387e1265b6c983a06829dd592` | `inputs.py` |
| `audit_source_references_v1.py` | `66ccea39a7b2acaeb89f8dd6958de88eac141d892f5c82ee2fbe179bb017b272` | `references.py` |

Only the functions/constants needed by the current auditor were extracted;
archive command-line orchestration was omitted. Imports and code-identity names
use the maintained TETHER namespace. The current auditor no longer dynamically
executes private audit scripts. Its execution inventory pins these new modules.
The historical driver still needs its frozen planning inputs and historical test
pins. This extraction does not establish clean-export support for that driver.

The retained 25.09 file counts, row counts, cutoff, exposure list and query rules
describe that diagnostic alone. They are not defaults for a new historical study.
New source versions need new manifests, source qualification and a fresh freeze.
Old READY files and results do not authorize execution with changed code hashes.

Current fictional controls declare `registered_parent_v2`: the evaluator-only
parent control now has an otherwise executable registered derivation. The auditor
also recognizes `legacy_v1` for archived fixture interpretation. This does not
upgrade legacy failure-stage agreement to reason-correct conformance. The current
integration test checks all fourteen fictional scenarios against separate audit
recipes; the evaluator-parent test additionally verifies the actual rejection
reason and an otherwise valid positive counterpart. No biological qualification
or real-source scan follows from these fixture tests.
