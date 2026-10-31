# R06 executing-build compatibility review

The R04 full regression result and its dependency resource remain retained. R06
adds `asof.study` modules and resources; the legacy compatibility engine does not
import them. They have their own complete installed-package/resource proofs.

The only changed R04 top-level helper is `asof/__init__.py`, whose version changes
from 0.2.0 to 0.3.0. It contains no admission, journal, scoring or verification
behavior. Package metadata and the lockfile receive the same version. The change
correctly caused the previous archive dependency guard to refuse verification;
`prior-profile-refusal.json` preserves that observation and its exact predecessor
resource hash. The new executing profile updates only this reviewed module hash.

The current archive policy remains `v0.2-compatibility-20261026`. Original code
pins, receipts, inputs and source strings are unchanged. Acceptance still requires
seven guarded installed replays under the final 0.3.0 wheel. This review alone is
not a successful compatibility test or historical executable-code attestation.
