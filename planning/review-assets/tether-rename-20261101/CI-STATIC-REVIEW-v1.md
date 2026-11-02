# TETHER CI static review

**PASS_STATIC_REVIEW_AFTER_PARENT_FIX.** Fifteen static checks pass; no unresolved finding. No hosted job, installation, network call or test execution occurred in this review.

The initial new job assumed ignored/untracked `runs/` existed, while the front door requires an existing parent. Root inserted `New-Item -ItemType Directory -Path runs -Force -ErrorAction Stop` before the demo and corrected the README example. Removing just that CI line restores initial workflow SHA `aa4b3a1840f432044abf9a8313f6200939fb7ffd47cc3f892fa0d6f2a1128857`. Final workflow SHA: `9094361f43eb55bd990732ff61e30159a8e474b3cf43c56a71467bc5622bfeaf`. Parent's retained local correction smoke passes; this does not establish hosted success.

The Windows/CPython 3.11.15 job installs core 0.3.11 then TETHER 0.4.0 into the same environment with pinned build constraints, checks dependencies, collects the correct new tests and calls the canonical console entrypoint. Metadata and lock agree; Arrow 21 is optional. The subproject local core path is correct. Existing isolated two-wheel and canonical-project checks are consistent.

The CI job uses root locked sync plus editable pip installs; it does not itself exercise locked subproject sync. Its final smoke omits an external outer receipt hash and thus checks unanchored integrity; the separately retained isolated check covers explicit external anchoring. The existing 49 TETHER/115 legacy local methods remain their own scopes and are not a current hosted or new native-source result.

| Check | Finding |
|---|---|
| Windows scope | New interface job uses Windows, CPython 3.11.15 and a 15-minute limit; no native Linux or hosted success inferred. |
| Action setup | Checkout/setup-uv use full 40-hex pins; checkout disables persisted credentials; workflow permission is contents:read. Action availability/release labels not externally reverified. |
| Root dependency resolution | Root locked core-only sync precedes exact core installation; no ingest extra/model command is selected. |
| Ordered installation | Core then canonical TETHER editable installation target the same .venv interpreter and both use pinned build constraints. |
| Version identity | Project,root namespace,lock and isolated record agree on TETHER 0.4.0/core 0.3.11. |
| Default dependency boundary | The only mandatory new dependency is the legacy project; Arrow 21 is optional in metadata and lock, not a default requirement. |
| Local source route | Both ../.. and ../../ resolve from packages/tether to unchanged root engine. |
| Console entrypoint | tether=tether._cli:main and python-m tether delegate the same canonical main; new CLI version/demo/verify commands match. |
| Dependency check | uv pip check explicitly checks the same .venv after no-deps installs. |
| Unit collection | Job collects packages/tether/tests with -B and no-sync; retained local 49 tests are separate evidence, not newly rerun here. |
| Missing parent corrected | New-Item runs precedes demo; output leaf remains fresh/no-clobber. Removing only that added line exactly restores the initially reviewed workflow SHA. |
| Failure propagation | The pwsh version/demo/verify block explicitly checks every native exit code; parent creation uses ErrorActionStop. |
| Local installed consistency | Existing isolated two-wheel record shows all calls 0, no Arrow/checkout imports, same class/token authority and genuine engine/outer verification. |
| Canonical lock coverage | The new lock is statically aligned and existing local canonical project sync is retained; this CI job itself uses root sync plus pip installs rather than subproject locked sync. |
| No hosted qualification | No job executed in this review. Local full/core 49, legacy 115 and isolated smoke do not prove current hosted success or native-source replay. |

Pinned metadata and local evidence:

- `.github/workflows/validate.yml`: `9094361f43eb55bd990732ff61e30159a8e474b3cf43c56a71467bc5622bfeaf`.
- `packages/tether/pyproject.toml`: `2e33b3fde62d219bf4e547499f09bf788c08f3e8cd51ff5fb401c82f0d081662`.
- `packages/tether/uv.lock`: `4f76e49137b5418250c3b1b8a81ab0ea3cf6579644f40314b34abbbeb65f609a`.
- `packages/tether/src/tether/__init__.py`: `433f499047da9335cf76fa24a417708888af602c60aedfec205ee650334cd874`.
- `packages/tether/src/tether/__main__.py`: `83fdeda07fb949ee59280d17045284db653cb239ae8099fafa0698fad12c0e2b`.
- `packages/tether/src/tether/_cli.py`: `fdd15b7067dcc71b1a0305eb8bdc6b93702ef33aea39eae9aad434495db49817`.
- `packages/tether/src/tether/_presentation.py`: `747c8467e5bb9019134e9949a0027eb4c96b8fdbe273010a2330d240320e070c`.
- `paper/release/build-constraints.txt`: `dfc2947f4dce3fa1c1905ef60bd8ee5b286177f603a13645cc2f003188c7d70c`.
- `planning/review-assets/tether-rename-20261101/ISOLATED-INSTALLED-QUALIFICATION.json`: `dbb269606cb39239f9d943d93429b868b01103adb7acd1fddc35c4e76cdb6054`.
- `planning/review-assets/tether-rename-20261101/CANONICAL-PROJECT-SYNC.txt`: `12ea52cae811cc0e729653a9a5ffb7c573c478a95d853a39b89613f0b689021a`.
- `planning/review-assets/tether-rename-20261101/CI-PARENT-SMOKE-v1.txt`: `c135721fe80a3cb2437ef2422c363629b47e3e60cdefb4bd952244b2d7621bb6`.

Static review cannot qualify hosted setup/action availability, future runner timing, native Linux/source replay or scientific validity. No runtime/source or packet input was changed by this reviewer.
