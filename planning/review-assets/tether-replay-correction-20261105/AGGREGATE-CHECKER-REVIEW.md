# Candidate release aggregate checker review

This is an adversarial self-audit by the checker author. It is not independent
scientific validation or an additional product/benchmark sample. A separate
read-only peer review was requested. No live full gate was polled, restarted or
executed by the invented-file tests.

`check_release_aggregate.py` verifies finished evidence and byte bindings. It
compares current package source/resources, captured build context, wheel members
and installed payloads; rechecks focused/archive/facade counts against retained
raw logs; verifies installed replay evidence; and checks preservation of the
original frozen comparison and old installed release. The live full gate can
contribute PASS only when both its terminal report and matching source bracket
exist, report successful tests/probes/offline packaging, and bind the exact
started invocation, log and complete current source inventory. Missing terminal
files yield PENDING. Failed or contradictory evidence yields FAIL.

The first partial attempt exposed a checker schema mistake: full-gate source
pins contain both `sha256` and `bytes`, rather than bare digest strings. The
underlying files had not changed. The failed result and exact pre-correction
checker are preserved; the corrected comparison validates both fields.
Subsequent partial records remain PENDING while the actual gate is unfinished.
They are not overwritten by later records.

`test_aggregate_checker.py` constructs private, explicitly fictional files for
two paired groups of checks. All **12 tests passed**, with zero skips:

- A consistent fictional finished gate passes. Removing either terminal file
  produces PENDING. Consistently resealing false passed counts, skipped tests,
  an omitted source member, a changed process identity or a nonzero terminal
  exit does not produce PASS.
- A consistent fictional previous qualification and its payloads pass.
  Altering its anchored qualification, wheel or installed file rejects.

The source-inventory probe reseals every affected declaration, so rejection
comes from independently enumerated inventory closure rather than a stale JSON
checksum. The count/skip probes likewise reseal their report and bracket,
ensuring that parsed semantic checks are exercised.

The retained `AGGREGATE-CHECKER-SELFTEST01.json` pins the checker, test source and
raw log. Checker SHA-256 is
`c22afbfd198c683f07746d4e26f983a6643a6805618b391fef69a0e0a03bd0b0`.
These 12 checker tests add **zero** to product test counts and do not establish
that the real full gate finished. The final aggregate must still be run against
the actual terminal evidence after the owning process reports completion.

## Peer-identified final-summary correction

A separate read-only peer review identified a concrete omission beyond the first
12 probes: a consistently resealed passed report could disagree with the final
unittest log outcome, and the focused-record check could borrow an earlier
standalone `OK`. The old checker and test source are preserved as
`check_release_aggregate-before-final-summary.py.txt` and
`test_aggregate_checker-before-final-summary.py.txt`.

`AGGREGATE-CHECKER-SUMMARY-RED01.json` records 17 invented-file tests with three
expected failures: conflicting final `FAILED`, final `OK (skipped=1)`, and a
focused log whose earlier `OK` masked its final failed suite. The narrowly
corrected checker now parses the last `Ran N tests` line and requires its next
nonempty line to be exactly `OK`. It does not reject earlier nested negative-test
messages. Paired examples with earlier failure text followed by a successful
final suite remain accepted.

`AGGREGATE-CHECKER-SUMMARY-GREEN01.json` records all 17 passing, with zero skips.
Final checker SHA-256 is
`71ae52971d37376b73826b12d0373d8ac5a696b58d585ad08cc3627d33a3fc06`.
These remain checker-author regression probes following an independent code
review; their counts add nothing to product-test evidence. No product/frozen
source changed, and the real unfinished full gate was neither read nor rerun.
