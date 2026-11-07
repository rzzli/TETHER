# TETHER naming and compatibility plan

1 November 2026, America/Los_Angeles. The owner explicitly renamed the project
**TETHER — Target Evidence Tracking Harness for Evaluation and Reproducibility**.
This is the current product/research identity. It introduces no new scientific
result, model run, source acquisition or publication.

## Ordered implementation

1. Retain commit `7625f8c` and pre-rename hashes for the original engine, build
   metadata, catalog and sealed paper/reconstruction artifacts.
2. Add the canonical TETHER front door as `tether-target-agents` version0.4.0 in
   `packages/tether/`, with `tether` and `python -m tether`. Its explicit local
   dependency is the unchanged `tether-target-engine==0.3.11` compatibility engine.
   The default runtime still needs no third-party Python packages. Optional
   ingestion remains exactly PyArrow21.0.0.
3. Expose compatible `tether.*` Python access using identical legacy module and
   class objects. Do not duplicate contracts, enums, exception classes or trusted
   reference tokens. Keep an explicit bounded alias inventory and executable
   wrappers for supported module entry points.
4. Brand new user-facing execution as TETHER through a separately sealed outer
   presentation. Keep the engine run and receipt intact, bind the new launcher's
   code/version, and verify the derived dossier against the unchanged engine
   report. Record failures without redispatch or changing previous results.
5. Update current prose, commands and navigation. Archive the previous catalog
   before changing only its title/project-provider display name. Preserve dataset
   IDs, role policy, date facts and all temporal/schema keys. The new catalog has
   a genuinely new hash; old runs retain their committed catalog.
6. Rebrand current paper text with an explicit former-name note, preserve original
   scientific methods/results and issue a separately versioned TETHER PDF/packet.
   Recheck source retention, geometry, visual pages, repetition, exact allowlists,
   rights boundaries and links. The frozen P09 archive remains unchanged inside
   the new packet and is labeled as historical compatibility material.
7. Validate the implementation, update TODO/status/memory and commit locally.
   No hosted run or publication is implied.

## Required historical compatibility

`TETHER`, `TETHER`, `tether-target-engine`, schema/method/backend identifiers and
`tether_normalized_packets` remain where they identify existing scientific or
software contracts. Source paths such as `src/tether_engine/`, original storage roots and
dated planning filenames may remain as historical references. This is deliberate
compatibility, not a second current project name. Original dossiers, code pins,
receipts, READY files, PDFs, ZIPs, protocols, generated results, dated research
logs, original proposals and archived review materials are not rewritten.

The new distribution owns only `tether/` files; the legacy distribution owns
`tether_engine/`. Do not create fake distribution metadata or install overlapping package
ownership. New TETHER code must have its own proof rather than claiming coverage
by the old 100-payload/78-source inventories.

Active naming must not imply trained independent specialist expertise, clinical
prediction, causal genetics, fresh study independence or broader model validity.
Real numerical features remain empty and probabilities null in the development
dossiers. Owner author/declaration facts remain intentionally deferred. External
expert responses and protected outcomes remain excluded. The existing download
worker, receipts and stopped monitoring remain untouched; provider spending is0.

## Acceptance

- TETHER names the current interfaces, documentation, manuscript and review packet.
- Canonical commands/imports work offline with the retained compatibility engine.
- Types, resources, serialized contract IDs and old proof identities stay stable.
- New launcher/presentation bytes are independently bound and verified.
- Old sealed artifacts and frozen core/replay sources keep their original hashes.
- New catalog/paper/PDF/packet versions receive genuine new hashes and checks.
- Required regressions and artifact checks pass; remaining limitations are explicit.
