---
name: research-log-2026-10-28-r09-native-component
description: Working native v2 component passes fake-transport tests; full case integration remains unfinished
metadata:
  type: project
updated: 2026-10-28
---

# Working native adapter component

The previous [[research-log-2026-10-27-r09-interface]] slice is accepted 0.3.8:
1,681 full tests/316 unchanged pins,105 schema cases, twelve installed preparations,
seven legacy families and seven matching old verifiers. Acceptance SHA
b95bef8731d56fd3ff2872e18170b056e6628890b1b887f8e094cbd6e4dcef41.
Its wheel/profile/initializer remain preserved. Before native work all 316 old
pins matched. Editable working version is now 0.3.9, not accepted.

New `native_interpretation.TokenQuotedNativeBackend` inherits the existing owned
HTTP transport. It binds exact stage/payload, model weights to quoted tokenizer
identity, concrete capacity, original native bytes/usage and one-use attempts.
The protected default transport deadline hook preserves legacy start+timeout,
while the new adapter clamps the earlier caller/parent end after quote work.
New replay helpers validate v2 response and native execution without connection.
Source/history/launch authority is deliberately still a controller requirement.

Thirteen new tests and 53 combined adapter/legacy-native/interface tests pass with
fake HTTP only. A matching old 0.3.8 pure-codec probe confirms empty quote catalogs
could be prepared from structural, unadmitted fixture inputs; working 0.3.9 rejects
those before dispatch. Initial fixture patch-isolation and explicit owner-mock
setup errors are recorded and corrected, with no weakened validation.

Contract: planning/review-assets/recovery-step9-native-integration-20261027/CONTRACT.md.
Do not narrow completion to the backend component. Still required: approved launch
configuration/asset leases, source/history/native mode in the existing four-arm
controller, root measured accounting and shutdown, whole-case fake-transport
regressions, installed/relocated replay and full acceptance/matching versions.
No full validation is running for 0.3.9 yet. No live server, model, new download,
provider spending or human scientific acceptance has occurred. Human reviews
remain pending and the original R07 native version remains stopped.
