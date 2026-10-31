# Comparison engineering compatibility delta

The accepted0.3.2 wheel, initializer and legacy profile are preserved under
`data/reference/recovery-r09-verifier-032-20261026/`. Its synthetic baseline bundle
was restored and verified without access to its original bundle or live sources.
The separately preserved0.3.1 installed verifier continues to check R07.

Working0.3.3 adds synthetic recorded comparison modules. The previous compatibility
profile first rejects the changed initializer. The update helper asserts that
the initializer changes only its version string and that every other declared
legacy semantic module is byte-identical. The new profile records its predecessor
and this review. There is no source/receipt rewrite or new semantic exception.

Acceptance still requires the new full regressions/package checks, seven installed
legacy replays and explicit matching-version replay of retained0.3.1/0.3.2 study
artifacts. A current package is not falsely described as matching an old study's
complete package proof. This does not assert independent R07 relocation or
automatic trust/execution of run-provided code.
