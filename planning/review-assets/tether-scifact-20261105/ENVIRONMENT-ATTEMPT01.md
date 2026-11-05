# First SciFact environment attempt

The sandboxed `uv venv` command failed before producing a usable interpreter:
Windows denied updating PE resources in the sandbox temporary directory.
An ensuing offline installation attempt reported no interpreter at the requested
path and installed nothing. The partial directory is retained.

Next attempt uses a fresh environment and workspace temporary directory with
authorized elevated execution. This is an environment setup failure, not a
solver or benchmark result. The five acquired dependency wheels remain pinned
and unchanged under `data/cache/tether-scifact-wheels-attempt01/`.
