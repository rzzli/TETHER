---
name: research-log-2026-10-27-r09-interface
description: Accepted original-path quote-ID interface; full, schema, installed and compatibility checks pass
metadata:
  type: project
updated: 2026-10-27
---

# Accepted versioned interpretation interface

Continuation after [[research-log-2026-10-27-r09-collected]]. The current accepted
package is 0.3.8, adding a pure `source-quote-interpretation-v2` codec,
not a native adapter or model experiment. No original R07 answer is repaired.

The complete original request is offered without moving reported passages. Quote
IDs bind exact original source/path pairs, observation IDs and UTF-8 hashes.
Generated assertions remain unchanged; exact materialized quotations are separate.
The existing stage/history and strict flat semantic checks are reused. Per-request
schema branches align answered/partial/abstained states and whole source-report
text/reference pairs. Cross-claim text uniqueness is explicitly post-validation.

Twenty-one new regressions and 33 focused codec/legacy tests pass. The initial
external schema probe found Unicode whitespace mismatches in `\S`; the explicit
Python whitespace set fixes them. Final105-case PowerShell 7.6.5/JsonSchema.NET
oracle passes with only the declared duplicate-text difference. Its binary and
loaded dependency hashes are retained. Native schema-to-grammar support remains
unverified; no permissive fallback or live call is authorized by these checks.

One broad focused invocation failed in legacy fixture creation/cleanup because it
used the sandbox C: temp root. The clean focused check and full helper explicitly
use D: temporary storage. Preserve the failure log; do not loosen runtime rules.
The formerly prepended portable 7.4 directory is absent; current available pwsh is
the app-installed 7.6.5 runtime. All seven matching preserved-version verifiers
pass, including the previous real-input run under its 0.3.7 installed verifier.

Full validation now passes 1,681 tests with no failures/errors/skips and 316 unchanged
source/resource pins. Twelve installed stage preparations check all three states;
seven installed legacy families and all seven matching preserved versions pass.
Acceptance SHA b95bef8731d56fd3ff2872e18170b056e6628890b1b887f8e094cbd6e4dcef41.
See planning/review-assets/recovery-step9-interface-20261027/CONTRACT.md and
NEXT-ADAPTER-DESIGN.md. Next adapter work must reuse owned transport and session
accounting, bind source/history/capacity and preserve the R07 negative baseline.
Independent human reviews, source sufficiency and overall scientific gates remain
pending; model calls and provider spending remain zero in this slice.
