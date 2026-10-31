# Preparation version compatibility boundary

The accepted 0.3.3 wheel, semantic profile and initializer remain preserved under
`data/reference/recovery-r09-comparison-verifier-033-20261026/`. Its explicit
installed verifier passes the recorded comparison with original bundle and live
source reads denied, as retained in `frozen-comparison-before.json`.

Working 0.3.4 adds separate preparation modules. Among the declared legacy semantic
helpers, only the initializer's version string changes. The versioning script
checks all 286 prior source/resource pins before that change and every other
declared legacy helper afterward. The compatibility profile records the previous
resource hash and the reviewed initializer change. It is not a new scientific or
native compatibility claim.

Acceptance still requires full tests, seven installed guarded legacy families and
matching frozen 0.3.1/0.3.2/0.3.3 verification after the new slice. Old receipts do
not automatically trust a different complete installed-package proof. Archived
code remains inert and is never executed automatically.
