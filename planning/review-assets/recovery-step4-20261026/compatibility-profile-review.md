# Compatibility profile review for the framework corrections

The prior archive dependency guard correctly refuses the changed live helper
modules; `prior-profile-refusal.json` retains that observation. Updating a guard
without examining semantics would hide drift. This review identifies the changes
before a new executing-build profile is captured and all old replays are rerun.

| Module | Change | Effect on archived v0.2 verification |
|---|---|---|
| chrono | Explicit optional snapshot base, execution readiness, publication consistency helper | Archive uses its own v0.2 observation admission rule; graph/query behavior unchanged; archive constructor supplies physical base but retains original logical identity |
| contracts | Mapping default factories replace misleading None defaults | Canonical values stay empty mappings after freezing; strict explicit-JSON-null rejection unchanged |
| serde | Union exception causes and equivalent Win32 extended path normalization | Successful JSON values/fingerprints unchanged; normalized physical locations retain containment checks; archived logical identities are never rewritten |
| workflow | Snapshot-base preflight before backend use | Archive uses unchanged Budget/add_usage and independent journal reconciliation; no archive dispatch |
| artifacts | Snapshot-base guard before final output writes | Archive verification does not call live write_run |
| local_model | Typed malformed/transport failures and full payload preflight | Valid response selections, token accounting and prompt/payload bytes unchanged; archive verifier never quotes/dispatches |
| ingest / maintenance / new atomic | Shared no-overwrite byte publication and in-process directory-init lock | Verification reads preserved receipt bytes; it does not publish or rewrite originals |

The old publication/admission function in `asof.archive.core` stays versioned.
Independent reviews distinguish actual information availability from imprecise
publication metadata: the original same-year positive fixture remains valid,
not a demonstrated leakage event. New execution excludes conflicting publication
date/year metadata and malformed direct-constructor years. No exact date is invented.

The new executing-build profile must pin the current helper bytes, retain the
previous resource hash and list these compatibility deltas. Its resource hash is
reported independently of the original archived code pins. Acceptance requires
all seven original representative artifacts to replay again under the installed
corrected verifier, along with focused/full regressions. No original archived
code, source packet, response or receipt is changed to make that replay pass.

Scientific validation, native successful-question callback support, hosted CI and
off-machine durability are separate unchanged gates.
