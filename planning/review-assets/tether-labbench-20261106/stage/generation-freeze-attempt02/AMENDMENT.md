# Prospective generation amendment A02

The first source collection completed under its original frozen code. Before
benchmark generation, a path check found that the worker's import-cache guard
accepted only `data/cache`, while its own parent deliberately creates the fresh
worker prefix within the reserved `data/benchmark` generation directory. This
would prevent startup before any model call.

The correction changes two worker checks to authorize the reserved generation
directory, `Path(output).parent`. The exact expected prefix, isolated interpreter,
disabled bytecode writes, and empty-before/after checks remain required. The
parent's cache remains restricted to `data/cache`. The failing-first controls
exercise the real cache guard in isolated child interpreters; this is not a
relaxation of the native model, source or response verifier.

Apply the change only after the completed collection passes its full source
verification and independent audit. Retain the original and corrected source
bytes, add the regression to ordinary test discovery, and pass the complete
component suite before sealing `GENERATION-FREEZE.json` and its dispatch recipe.
That machine-readable record binds the accepted collection and both code versions.

The question population, permutation, source collection, model weights, prompt,
generation settings, budgets, alias, and intended output directory remain
unchanged. No benchmark candidate has been generated and no answer key has been
read by the answering workflow. The prior failed fictional semantic control is
unchanged; A01's descriptive weak-baseline scope remains in force.

This amendment does not alter the original collection freeze, rerun collection,
replace a failed model result, or establish scientific capability. Completion of
the proposed correction is recorded by the subsequent test and freeze records,
not by this preparatory explanation alone.
