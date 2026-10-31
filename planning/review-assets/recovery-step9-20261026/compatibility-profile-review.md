# R09 legacy compatibility profile delta

The0.3.1 profile and module initializer are preserved as original bytes alongside
the reviewed0.3.1 wheel under `data/reference/recovery-r07-verifier-031-20261026/`.
The pre-change installed verifier passes the actual R07 terminal run while live
project sources/editable environment, repository-only imports, archived execution
and network/child dispatch are unavailable. This is explicit operator use of a
reviewed installed verifier, not automatic execution of code selected by a run.

The live package advances to0.3.2 for the synthetic deterministic baseline API.
The previous legacy guard correctly rejects the changed initializer before this
profile update; see `prior-profile-refusal.json`. Every other declared legacy
semantic dependency must hash-identically match the0.3.1 profile. The initializer
must differ only by its version string. The update helper enforces both checks.
New baseline modules are outside the legacy semantic engine's imports. No old
receipt, source or semantic acceptance rule changes.

The new profile records its predecessor hash and reviewed version delta. Full
regressions and seven installed legacy replays must pass before engineering
acceptance. The frozen0.3.1 verifier must also reverify R07 after the new package
is installed. Current0.3.2 is not falsely claimed to match R07's0.3.1 package
proof. Independent relocation of that new native receipt family remains outside
the legacy archive guarantee; original-path source availability is still required.
