# Reviewed 0.3.13 executing archive profile

This profile migration supports the reviewed archived-replay correction in the
live verifier while preserving the separate historical archive interface. It is
not an installed-release or comparison-completion certificate.

The complete prior 0.3.12 atomic-retry resource is preserved byte-for-byte as
`semantic_dependencies-0.3.12-atomic-retry.json`. The new resource's
`previous_resource_sha256` identifies those exact bytes. Its historical
predecessors and validation records remain unchanged.

Only three existing module pins change: `__init__.py` declares version 0.3.13;
`agents.py` extracts the existing immutable replay lookup into a shared pure
function without changing runtime quote/select cursor behavior; `artifacts.py`
adds the reviewed live replay verification hooks. The 19 other existing module
pins remain identical. The inventory adds `replay_validation.py`, a new reachable
dependency of the already pinned `artifacts.py`, for a conservative total of
23 top-level modules. No wildcard hash exemption or guard bypass is introduced.

The archive's Python modules, dependency minimum/function-identity checks,
allowlisted resolver, frozen v0.2 admission/semantic policy, source/receipt bytes,
and original archived Python remain unchanged. Archived Python continues to be
hashed as data and is never imported or dispatched. The new live replay verifier
is not called by `archive.core.verify_core_archive`: migration does not silently
add its stricter current-release replay guarantees to historical compatibility
results. Archive results retain the explicit `v0.2-compatibility-20261026` policy.

The live correction's finite 25-test red/green qualification and unchanged EP075
counterexample are retained in the parent directory. Migration validation must
freshly pass all archive unit tests, including relocated v1/v2 cases, rejection of
resealed source/feature/accounting corruption, approved-path controls, and the
live-dependency drift guard. Additionally, unchanged retained old-engine
fictional normal and unknown-timeout runs must verify after fresh relocation;
the retained contradictory overquote run must still reject for its validated
usage failure. These controls do not execute a model or archived verifier.

The migration record brackets archive Python and profile inputs. The fresh
validation record will distinguish source-tree qualification from the separately
required full-suite and installed 0.3.13/0.5.2 release gates. Earlier installed
qualifications continue to describe only their own retained wheel/source hashes.

## Completed source-tree qualification

`VALIDATION.json` records a successful fresh pass: all 52 archive tests passed
with no skips; the preserved original v1 demo byte receipt verified with semantic
verification explicitly unavailable; retained old-engine 0.3.11 normal and
unknown-timeout runs verified after fresh relocation; the contradictory overquote
run still rejected with `Failed local response lost its validated usage`.
The archive Python, active profile and retained old controls were unchanged
through validation. No old control was regenerated.

The previous resource SHA-256 is
`645b1fb409b11f4d0e8d5d9e96e14f2b6302b1ecb5d03c64ddf5cfc8d683d016`;
the new active resource SHA-256 is
`1f29808ea577d6c98d05e21ba8dc474b8a347350ab78803f375fea02d1e530e0`.
`PREPARED.json` and `APPLIED.json` retain the exact delta and archive Python pins.
The full release and fresh installed qualifications remain separate gates.
