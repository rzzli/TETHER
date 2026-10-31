# Version boundary review

The accepted0.3.7 wheel/profile and installed environment remain preserved. Its
source-inclusive relocated replay passes in `FROZEN-037-BEFORE.json`. All 314
previous code/resource pins and all 22 declared legacy helpers matched before
versioning. New files add a pure codec and tests; old diagnostic, payload,
transport, admission, scoring and archive code remain unchanged.

Working 0.3.8 changes the initializer version and records that sole declared legacy
helper delta in the compatibility profile. New execution needs fresh package
proofs. Historical study receipts keep their matching installed verifiers. No
archived code is imported as authority. Overall engineering acceptance still
requires full validation, installed checks, schema qualification and all seven
preserved-version verifiers; native/scientific acceptance is separate.
