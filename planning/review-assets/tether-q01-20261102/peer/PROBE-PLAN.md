# Independent Q01 process supervision checks

Scope: current TETHER launcher and canonical CLI only. These fixtures contain no
provider data, models, network calls, protected outcomes or expert returns. They
are not a scientific experiment or proof of operating-system sandboxing.

The process policy is separate from the frozen workflow budget. A process deadline
must not reset when output arrives; stdout and stderr share one byte allowance.
Completion requires the child to exit and both pipes to reach EOF within the
deadline. Exact-cap output is valid; the next byte must fail explicitly.

## Independent fixtures and expected behavior

| Fixture | Required observable result |
| --- | --- |
| Silent block | Timeout, bounded cleanup, no automatic second launch. |
| Small continuous trickle | Same absolute timeout despite regular output. |
| Stdout flood / stderr flood / simultaneous flood | Output-limit failure without pipe deadlock; retained bytes bounded in aggregate. |
| Exactly the cap split across both streams | Success, exact original bytes, no false truncation. |
| Cap plus one split across streams | Failure, retained prefix bounded, limit reason preserved. |
| Nonzero exit | Original return code and both streams retained; never success. |
| Parent exits with short descendant holding pipes | Deadline still covers pipe EOF; report only ownership/reaping of the direct child. |
| Terminate failure, then successful kill | Original limit/timeout cause retained alongside cleanup error. |
| Pending synthetic call before timeout | Failure inspect shows unresolved call and conservative reserved usage, with no redispatch. |
| Accounted synthetic call before timeout | Measured usage remains measured; no double-counted reservation. |
| Genuine demo outer run | New process policy/report retained and verified; deterministic dossier semantics still checked. |
| Failed outer run | No success receipt; failure verification rejects and inspection remains read-only. |
| Invalid bound values | Reject before launch or output reservation; include boolean/non-finite/negative checks where exposed. |
| In-process verify/outer inspect | Do not imply child supervision applies; explicit process flags rejected if unsupported. |

Implementation-specific checks will use the supported supervisor entry point and
small fixture limits. Separate timing tolerance accommodates Windows scheduling;
test timing is an observed result, not a guarantee against OS hangs or blocked
process creation. Descendant fixture lifetime is finite. Cleanup failure injection
will retain ownership of a real child and still kill it safely.

Readiness claims must distinguish synthetic local Windows checks, installed-wheel
qualification and untested POSIX execution. Failure handling cannot promise durable
metadata under forced termination, disk failure or unavailable process-control APIs.

Original experiment outputs and old TETHER launcher artifacts remain unchanged.
