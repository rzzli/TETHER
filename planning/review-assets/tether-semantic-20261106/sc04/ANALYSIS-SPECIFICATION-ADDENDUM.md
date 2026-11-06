# SC04 reporting convention clarification

Prepared while ordinary source collection is still active, before primary answer
generation. The original analysis specification remains unchanged because its
bytes are already referenced by a fictional diagnostic execution frame.

The retained native scorer (`experiments/labbench/evaluate.py`) reports zero
precision when no substantive answer exists, accompanied by
`precision_defined=False`. Preserve that field/convention in the native-compatible
result object. Also report the statistical ratio as null and display it as
undefined in readable tables. A zero-attempt result is not a measured precision
of zero. This resolves the original specification's null-only presentation with
the requirement to retain the native reporting convention; it changes no case
classification, numerator, denominator, outcome, threshold or confidence interval.

All other analysis settings remain those in [the original specification](ANALYSIS-SPECIFICATION.md).
