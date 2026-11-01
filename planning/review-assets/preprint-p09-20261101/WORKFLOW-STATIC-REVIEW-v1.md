# Validation workflow static review

The corrected workflow passes local YAML syntax and duplicate-key checks using already cached PyYAML 6.0.3 without installation or bytecode writes. Core/full remain four independent Ubuntu/Windows matrix lanes; P09 has a separate Windows fictional/preparation lane. Runtime gate commands match `tools/validate.py`; P09 does not claim hosted actual-source reconstruction.

The review found a blocking initial flag error: pinned uv 0.11.2 rejects `--build-constraints` on `uv sync`. An external TOML prototype also failed enforcement: both the intended setuptools 84.0.0 constraint and an impossible 999999 constraint silently built with cached 84.2.1. Both failed probes remain retained; the prototype was moved into review assets, outside active release configuration.

The corrected two-step sequence was qualified in new isolated fictional environments using only the existing offline C: cache: `uv sync --offline --locked --no-install-project`, then `uv pip install --offline --no-deps --editable <fixture> --build-constraints <84-file>`. The installed editable WHEEL records `Generator: setuptools (84.0.0)`. An impossible 999999 constraint fails with no installed project distribution. Exact copied `pyproject.toml`/`uv.lock` remain compatible with `--locked`, both fixture locks remain unchanged, and repository project/lock/main-venv configuration hashes remain unchanged. No provider originals were read.

The detailed JSON pins the exact corrected workflow and probe. No hosted CI, Linux native source qualification or fresh runner dependency availability is claimed. The existing main timeout remains root-owned and should change only from terminal measured gate cost. Hosted execution remains future evidence; static review cannot replace it.
