# Development findings before interface acceptance

27 October 2026. These are code-author engineering findings, not independent
scientific review. The current accepted package remains0.3.7 while0.3.8 is tested.

1. Initial test discovery failed because the new module did not exist. The first
   implementation passed17 of 18 new tests; the Unicode fixture changed original
   science without rebinding its structural source scope. Correcting the fixture
   with the existing binder made that test meaningful; limits tests also rebind
   before exercising their intended failure boundary. No source-admission rule
   was loosened.
2. The first external schema-engine probe exposed Unicode nonblank mismatches:
   `\S` did not reject all whitespace that Python `str.strip` rejects. An explicit
   Unicode whitespace set replaced that shorthand. The 104-case rerun checks all 29
   Python whitespace codepoints in text and reasons. A final105-case check adds a
   valid quote ID paired with another source's text. Only the documented
   cross-claim text-uniqueness difference remains; post-validation rejects it.
3. The inherited source request can allow64 claims, while this interface allows
   at most 3. Reusing the diagnostic entry point would reject such a request even
   when its output respected3. The new code validates the original request and
   active cap, then reuses the existing strict flat state/text/reference validator
   directly. It does not rewrite assertions or retrofit old R07 replies.
4. An expanded regression invocation used the sandbox's default C: temporary
   directory. Legacy fixture creation/cleanup failed with WinError5. The retained
   failed log is `FOCUSED-FINAL.log`. The focused33-test codec run uses an explicit
   writable D: temp directory; full validation does likewise. Do not characterize
   the sandbox error as a runtime or biological failure, or quietly discard it.
5. The old validation helper prepended a now-absent portable 7.4 directory. The
   actual available oracle is the installed PowerShell 7.6.5 binary; its exact path,
   hash and output version are retained. No new software was downloaded and no
   native grammar compatibility is inferred from JSON Schema validation.

Existing source, source/history authority, token capacity, session, process and
native transport modules remain unchanged. The new interface is pure and cannot
admit data or dispatch a model. Future adapter integration still needs those
authorities, current exact token proofs and a separately declared experiment.
