# R09 requirement audit and finite continuation

Date: 2026-10-26. Read-only audit during the frozen 0.3.2 full validation.
The 34 focused tests pass; full/package/installed acceptance is still pending.
No source or test file was changed; no sealed candidate response, clinical label
or reviewer answer was read. **The whole of R09 is not complete.**

## Governing boundary

The recovery plan line31 says missing humans block independent H5 qualification,
not remaining engineering. Its line64 gives R09 dependencies as R04, relevant R06
and R07; it does not add R08 or HR3 as prerequisites for all implementation.
R10 explicitly requires R08/R09/HR2–HR3 and references before generation.

R07 `DISPOSITION.md` lines13–16 stop **this version of native interpretation**,
twenty-case expansion, retries and answer repair. Lines66–70 explicitly require a
separately versioned design with aligned references/state/instructions and
deterministic fixtures before any future experiment. The retained interface review
section “Bounded next action and stopping rules” already proposes that offline
work. Thus prospective design and recorded synthetic implementation are allowed;
they do not activate a new native experiment or override human scientific gates.

## Requirement-by-requirement status

| Requirement | Existing evidence | Still required; implementability |
|---|---|---|
| **9.1 Separate interpretation and exact quotes** | New `study.baselines.run_baseline` copies full source strings with pointers/hashes and empty generated interpretations. Installed `diagnostic_codec.validate_legacy_claims`, `validate_response` and `diagnostic.validate_output` already distinguish claim kinds and enforce verbatim `source_report` content. | The baseline does not implement generated interpretation. A prospective common comparison envelope must keep generated text unchanged and materialized literal quotations separate. Explicit quote lookup and rendered instructions can be prepared/tested now using recorded invented responses. Mechanical validation cannot establish entailment. |
| **9.2 Answered/partial/abstained and independent validation** | Current/simplified diagnostic validators enforce state/claim/reason relationships. Baseline `complete/partial/empty` describes extraction only, with scientific answer status not attempted. | Preserve both meanings rather than mapping extraction completion to an answered question. Align the prospective guide and active limits with the existing postvalidator; fixture all legal states and observed rejection cases. This is implementable without human submissions. Native compliance and scientific usefulness remain unmeasured for a redesigned interface. |
| **9.3 Separate fixed-evidence and end-to-end tracks** | The synthetic baseline provides fixed-input selection. `retrieval.bounded_request` and `verify_retrieval_trace` support bounded selection over a supplied store. Older `tools/science/comparison_workflow.py` bounds category packets. | Neither is a complete end-to-end interpretation comparison. Freeze separate input identities, stages and output/denominator semantics now. Do not relabel a fixed packet as end-to-end search. Actual retrieval/source manifests and a qualified question/case frame remain separate prerequisites for real comparisons. |
| **9.4 Four arms** | Deterministic extractive and lexical mechanics now exist. Recorded generative fixtures and generic study execution already exist. A pinned older five-stage source-derived Virtual Biotech selection adaptation exists in repository tools. | AsOf interpretation and an explicitly adapted Virtual Biotech **interpretation** arm remain unfinished. The old ID-selection workflow does not become a dossier-generation comparator through renaming. Its bounded stage/data contracts can inform prospective recorded implementation now. Model efficacy comparisons require later activation and scientific references. |
| **9.5 Freeze adaptations, access, budgets and identity** | R07 freezes its failed diagnostic, which must stay unchanged. `adapter-role-policy-r1.json` pins upstream revision/files and enumerates deviations. New baseline policy/proofs bind its finite synthetic scope. | Create a prospective comparison specification covering all four arms and both track labels, with actual implemented/unimplemented status. Preserve the old adaptation's response-informed amendment and selection-only limitation. Original SDK/orchestrator, models and tools remain unreproduced. Shared source access and aggregate stage budgets can be machine-checked now; unavailable model/source choices remain explicitly unavailable. |
| **9.6 Configurable recorded retrieval, controlled changes** | Baseline policy records extraction/lexical selection, exact query, tokenizer, bounds and trace. No embeddings or new data are used. | Connect that policy to the separate comparison tracks and arm preparation, with controlled differences and reported whole-stage budget accounting. Do not call lexical overlap a learned relevance/evidence-strength estimate or claim one-factor isolation for a multi-role adaptation. Engineering is possible now; scientific ranking quality is not established. |

The initial two-fixture allowlist is an intentionally limited engineering gate,
not completion of real-source admission. A top-level `agent_evidence` role,
`known_source` label or hash-consistent request does not prove eligible ancestors.
Real execution ultimately needs the existing case/snapshot/catalog admission and
complete lineage checks, with a separately qualified input compiler; that remains
an explicit missing capability, not an arbitrary permanent exclusion from R09.

## One bounded next action after current acceptance

**Implement a prospectively versioned, fixed-evidence comparison preparation and
recorded-contract slice, covering the unfinished generated/comparator interface.**
Reuse the retained R07 interface findings; do not repeat the investigation or
start another grammar/converter search.

1. Freeze one compact comparison specification: four arm identities, fixed-input
   track active for fixtures only, end-to-end track explicitly unimplemented,
   strict source equality, active output limits and aggregate stage ceilings.
   Keep old failures/payloads and the accepted baseline contracts unchanged.
2. Prepare a revised, versioned guide/payload with an explicit alias-to-original-
   pointer table, consistently named `abstention_reason`, all three legal answer
   states and the verbatim-source rule. Clearly distinguish inherited input bounds
   from the active response cap. Reuse the existing strict simplified validator
   where its semantics suffice; do not weaken it to accept archived failures.
3. Produce exact-source quotation presentation separately from unchanged generated
   text. Materializing approved quote references is allowed; completing an answer,
   inventing context or repairing reasoning is not. Do not force the deterministic
   baseline through model-style accounting.
4. Specify the source-derived comparator's role/stage signatures and deviations
   using the existing pinned policy as evidence. Its current contract is ID
   selection only: explicitly define any new interpretation stage before calling
   it an interpretation arm. Preserve shared fixed source access and bound every
   stage and prior-stage input. Missing original dependencies remain disclosed.
5. Use the same two invented fixture requests for deterministic preparation and
   recorded success/failure tests. Reuse `StudySession` and explicit verifier
   callbacks for **recorded generative fixtures**, not for baseline computation.
   Reuse its failure accounting rather than writing a controller. Recorded tokens
   are fixture metadata, never measured native-model usage. Verify that malformed
   states/pointers, foreign premises, changed evidence, oversized feedback and
   exceeded aggregate ceilings fail without repair or additional dispatch.

This is one finite contract/preparation deliverable with recorded verification,
not a four-arm scientific run. No native adapter change or model call is required.
No real-case candidate, new source selection, acquisition or clinical access is
authorized by it. Installed tests must use packaged modules/resources, not import
the old tools stack. Any semantic resource changes need versioned proofs and the
same preserved-archive checks used for the current slice.

## Reuse and actual external gates

- `study.diagnostic_codec.validate_request`, `quote_choices` and strict response
  validation supply structural bindings and source pointers; they do not admit
  temporal lineage. `diagnostic.prepare_payload` is the frozen old interface,
  not an API to silently modify in place.
- `study.session.StudySession`, `StudyVerifier`, `verify_study` and `inspect_study`
  provide existing execution/replay/failure mechanics. `study.recorded.RecordedBackend`
  illustrates fingerprint-bound fixture execution; its existing verifier binds the
  old payload, so a new trusted verifier must explicitly bind any new payload.
- `study.baselines` and `baseline_smoke` retain pure zero-model computation;
  canonical serialization, atomic publication and static proof helpers remain
  shared. No second general controller is justified.
- `tools/science/interpretation_questions.prepare_question` demonstrates the older
  source compiler; `comparison_workflow` and `role_backend` demonstrate bounded
  role selection. These are architectural references, not permitted installed
  runtime imports or proof that the new comparison is implemented.

Actual external requirements are qualified human references/ratings and domain
coverage, a source/exposure-qualified real frame and any genuinely unavailable
model/data access. They block scientific activation/acceptance, not the prospective
synthetic work above. Further native execution additionally needs a new explicit
prospective experiment satisfying R07's stop rules. Source chronology, model
capacity and stronger-model availability are not resolved by recorded fixtures.
