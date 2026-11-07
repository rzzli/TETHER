# Source and evaluation utilities

These tools implement source preparation, bounded extraction, review-data
contracts and evaluator-side checks. They are separate from the default agent
workflow. Many require exact protocol-bound inputs; they are not general-purpose
clinical query or prediction services.

| Area | Entry points |
|---|---|
| Supplied archive checks and restoration | [ascertainment_inputs.py](ascertainment_inputs.py), [endpoint_restore.py](endpoint_restore.py), [restore_verification.py](restore_verification.py) |
| Origin selection and source projections | [origin_review.py](origin_review.py), [outcome_inputs.py](outcome_inputs.py), [outcome_extract.py](outcome_extract.py) |
| Registry-content contracts | [registry_content.py](registry_content.py) and the associated workflow, transport and evaluation modules |
| Prospective frames | [prospective_frame.py](prospective_frame.py), [prospective_transport.py](prospective_transport.py), [prospective_capacity.py](prospective_capacity.py) |
| Genetics input requirements | [genetics_qualification.py](genetics_qualification.py) |
| T6 source prioritization | [t6_challenge.py](t6_challenge.py), [t6_reference.py](t6_reference.py), [t6_topone_evaluation.py](t6_topone_evaluation.py) |
| Claim and source binding | [t6_claim_audit.py](t6_claim_audit.py), [t6_dossier_binding.py](t6_dossier_binding.py) |

Read a module's CLI or callable contracts and its tests before preparing inputs.
Use explicit manifests, independent hashes and fresh output directories. Source
reading, restoration and model execution have different prerequisites; an
inspection or replay operation must not silently restart any of them.

Evaluator artifacts, outcomes and reference answers must stay outside agent
inputs and their ancestry. Preserve unknown mappings, missing records, date
precision, failed attempts and original row locators. A missing registry result
is not a negative clinical outcome, and agreement with an AI-authored reference
is not independent biological validation.

Several controllers retain exact historical scientific protocol pins. Their
presence is not authorization to run a new cohort or model. Use matching original
code for original-version reproduction; a changed execution needs new source,
protocol and runtime bindings. See [historical compatibility](../../docs/ARCHIVE.md).

Run the relevant invented-data unit tests under `tests/test_science_*.py` before
using these utilities. The [development guide](../../docs/MAINTENANCE.md) describes
the repository gate. Private input manifests and generated results are excluded
from the public repository.
