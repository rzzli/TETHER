# Candidate 0.5.2 facade qualification

The fresh facade suite passed **138 tests with no failures, errors or skips** in
`data/cache/tether-052-dev`, whose editable distribution metadata declares
TETHER 0.5.2 and AsOf 0.3.13. This is a source-tree facade check, separate from the
fresh isolated installed-wheel release qualification.

`STARTED.json` and `VALIDATION.json` retain exact source, resource, test,
pyproject/lock and candidate distribution-metadata hashes. All matched before and
after the run. `facade-tests.log` retains raw unittest output; its SHA-256 is
`ec754167646c3a396651e8a75e68953b8f56e6c864fc022025027fb69203c36e`.

`qualify_facade.py` ran with `-B`, workspace TEMP/TMP, a fresh dedicated temporary
directory, no source edits and no overwritten attempt. Full-suite validation is
a separate release gate and is not implied by these facade tests.
