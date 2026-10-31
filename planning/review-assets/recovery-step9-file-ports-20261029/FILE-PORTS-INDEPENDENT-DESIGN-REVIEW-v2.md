# File-port design v2 review

The exact v2 design resolves the earlier drive-root gap and is clear for design scope. `CanonicalDriveRoot` is a separate metadata-only descriptor derived from the admitted C/D ancestor roster, counted once in `U`, and limited to the existing directory-attribute observation. It cannot become an original/output leaf, namespace leaf, scan root or new authority. Failed or unknown attributes still prevent completion.

The metadata comparison confirms only the six declared semantic top-level fields changed. File-leaf grammar, roles, 14 exports/layouts/flags, original inspection/read rules, owner clocks, slot ownership, source/seal DAG, event/call formulas and output quotas are unchanged. The added registry-only observations, pending late-write hashes and long-path limit statements match the previously reviewed clarifications.

Eleven literal regex probes match the declared syntax. Syntax alone is not admission: another drive may match `[A-Z]` but remains excluded by the finite C/D roster. Future code must validate and normalize the new directory descriptor directly rather than pass a drive root to the old file-leaf validator.

No further material design discrepancy was found. This review performs no file-port implementation, ctypes/API call, source qualification, directory scan or payload operation. Closed fixtures, source implementation, harmless platform tests, production integration and profile authority remain separately pending.
